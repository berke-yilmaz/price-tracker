# api/management/commands/process_products.py
import os
import time
import urllib.request
import io
from PIL import Image # PIL is still needed for validation, but not passed to cached functions
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from api.models import Product
from api.util import (
    categorize_by_color,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    build_vector_index,
)

class Command(BaseCommand):
    help = 'Process products: extract colors and visual features from their remote images.'

    def add_arguments(self, parser):
        """Adds command-line arguments for customizing the script's behavior."""
        parser.add_argument(
            '--batch-size', 
            type=int, 
            default=10, 
            help='Number of products to process in each database transaction.'
        )
        parser.add_argument(
            '--limit', 
            type=int, 
            default=0, 
            help='Maximum number of products to process (0 means all).'
        )
        parser.add_argument(
            '--force', 
            action='store_true', 
            help='Reprocess all products, even those already marked as "completed".'
        )
        parser.add_argument(
            '--color-only', 
            action='store_true', 
            help='Only perform color analysis for products missing it.'
        )
        parser.add_argument(
            '--features-only', 
            action='store_true', 
            help='Only extract visual features for products missing them.'
        )

    def handle(self, *args, **options):
        """The main execution method for the command."""
        self.batch_size = options['batch_size']
        self.limit = options['limit']
        self.force = options['force']
        self.color_only = options['color_only']
        self.features_only = options['features_only']

        self.stdout.write(self.style.SUCCESS('🎨 Starting AI Product Processing'))

        # Build the initial queryset to find products that need processing.
        query = Product.objects.exclude(image_url='').exclude(image_url__isnull=True)
        
        if not self.force:
            # If not forcing, only select products that are pending, failed,
            # or missing one of the key AI features.
            query = query.filter(
                Q(processing_status__in=['pending', 'failed']) |
                Q(color_category='unknown') |
                Q(visual_embedding__isnull=True)
            )

        # Apply limit if specified.
        if self.limit > 0:
            query = query[:self.limit]

        total = query.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("✅ All products are already processed. Nothing to do!"))
            return
            
        self.stdout.write(f"📊 Found {total} products to process.")
        
        stats = { 'processed': 0, 'errors': 0, 'color_analyzed': 0, 'features_extracted': 0 }
        start_time = time.time()

        # Process the products in batches for efficiency.
        for i in range(0, total, self.batch_size):
            # Select a batch of products from the queryset.
            batch_qs = query[i:i + self.batch_size]
            self.stdout.write(self.style.HTTP_INFO(f"\n🔄 Processing Batch {i//self.batch_size + 1}/{ (total + self.batch_size - 1) // self.batch_size }..."))

            for product in batch_qs:
                try:
                    # Each product is processed within its own atomic transaction.
                    with transaction.atomic():
                        self._process_product(product, stats)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Critical error for '{product.name}': {e}"))
                    stats['errors'] += 1
                    # Mark the product as failed in the database.
                    product.processing_status = 'failed'
                    product.processing_error = str(e)
                    product.save(update_fields=['processing_status', 'processing_error'])
            
            elapsed = time.time() - start_time
            rate = stats['processed'] / elapsed if elapsed > 0 else 0
            self.stdout.write(f"   Progress: {stats['processed']}/{total} ({rate:.1f} products/sec)")

        # Final summary.
        elapsed_mins = (time.time() - start_time) / 60
        self.stdout.write(self.style.SUCCESS(f"\n🎉 Complete! {stats['processed']} products processed in {elapsed_mins:.1f} minutes."))
        self.stdout.write(f"   - 🎨 Colors Analyzed: {stats['color_analyzed']}")
        self.stdout.write(f"   - 🧠 Features Extracted: {stats['features_extracted']}")
        self.stdout.write(self.style.WARNING(f"   - ❌ Errors: {stats['errors']}"))
        
        # Rebuild the FAISS index if new features were extracted.
        if not self.color_only and stats['features_extracted'] > 0:
            self.stdout.write("\n🔄 Rebuilding search index with new data...")
            build_vector_index()
            self.stdout.write(self.style.SUCCESS("✅ Search index is now up-to-date!"))

    def _process_product(self, product, stats):
        """Downloads the image and runs all AI processing for a single product."""
        # Download the image and keep it as raw bytes.
        image_bytes = self._download_image_bytes(product.image_url)
        if not image_bytes:
            raise Exception("Image download failed or was empty.")

        changes_made = False

        # --- Color Analysis ---
        if not self.features_only and (product.color_category == 'unknown' or self.force):
            # Pass bytes to the cached utility function.
            color_info = categorize_by_color(image_bytes)
            product.color_category = color_info['category']
            product.color_confidence = color_info['confidence']
            product.dominant_colors = color_info.get('colors', [])
            
            stats['color_analyzed'] += 1
            changes_made = True
            self.stdout.write(f"   🎨 '{product.name}': Color is {color_info['category']} ({color_info['confidence']:.2f})")

        # --- Visual Feature Extraction ---
        if not self.color_only and (not product.visual_embedding or self.force):
            # Pass bytes to the cached utility function.
            visual_features = extract_visual_features_resnet(image_bytes, product.color_category)
            product.visual_embedding = visual_features.tolist()
            stats['features_extracted'] += 1
            changes_made = True
            self.stdout.write(f"   🧠 '{product.name}': Visual features extracted.")

        # --- Text Embedding ---
        # This can be run on every valid processing run.
        if not self.color_only and not self.features_only:
            text_embedding = get_color_aware_text_embedding(product.name, product.color_category)
            product.color_aware_text_embedding = text_embedding.tolist()
            changes_made = True

        # If any AI data was generated, update the product status and save.
        if changes_made:
            product.processing_status = 'completed'
            product.processed_at = timezone.now()
            product.processing_error = None
            product.save()
            stats['processed'] += 1

    def _download_image_bytes(self, url: str) -> bytes | None:
        """Downloads an image from a URL and returns its raw bytes."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                # Basic validation: ensure the downloaded file isn't tiny or invalid.
                if len(img_data) < 1000:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Skipped (image too small): {url}"))
                    return None
                
                # Further validation with PIL to ensure it's a valid image.
                with Image.open(io.BytesIO(img_data)) as img:
                    if img.width < 50 or img.height < 50:
                         self.stdout.write(self.style.WARNING(f"   ⚠️  Skipped (dimensions too small): {url}"))
                         return None
                
                return img_data
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   ⚠️  Download failed for {url}: {e}"))
            return None
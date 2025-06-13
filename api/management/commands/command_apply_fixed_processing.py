# api/management/commands/apply_fixed_processing.py
import os
import time
import urllib.request
import io
from PIL import Image
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from api.models import Product, ProcessingJob
from api.util import (
    categorize_by_color,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    build_enhanced_vector_index
)

class Command(BaseCommand):
    help = 'Apply fixed processing to all products'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
        parser.add_argument('--limit', type=int, default=0, help='Maximum products to process (0=all)')
        parser.add_argument('--force-reprocess', action='store_true', help='Reprocess all products')
        parser.add_argument('--save-processed', action='store_true', help='Save processed images')

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        force_reprocess = options['force_reprocess']
        save_processed = options['save_processed']
        
        # Import the fixed processing functions
        try:
            from api.util_enhanced_fixed import process_product_image_fixed
            self.stdout.write(self.style.SUCCESS("✅ Fixed processing functions loaded"))
        except ImportError:
            self.stdout.write(self.style.ERROR("❌ Could not import fixed processing functions"))
            return
        
        self.stdout.write(self.style.SUCCESS('🔧 Applying Fixed Product Processing'))
        
        # Create processed directory
        if save_processed:
            os.makedirs('processed_fixed', exist_ok=True)
            self.stdout.write(f"📁 Processed images will be saved to: processed_fixed/")
        
        # Build query
        query = Product.objects.exclude(image_url='').exclude(image_url__isnull=True)
        
        if not force_reprocess:
            # Only process products that need reprocessing
            from django.db import models
            query = query.filter(
                models.Q(visual_embedding__isnull=True) |
                models.Q(processing_status='failed') |
                models.Q(processing_status='pending')
            )
        
        if limit > 0:
            query = query[:limit]
        
        total_products = query.count()
        self.stdout.write(f"📊 Products to process: {total_products}")
        
        if total_products == 0:
            self.stdout.write(self.style.WARNING("No products to process!"))
            return
        
        # Initialize statistics
        stats = {
            'processed': 0,
            'errors': 0,
            'color_analyzed': 0,
            'features_extracted': 0,
            'detection_success': 0,
            'detection_methods': {},
            'color_distribution': {}
        }
        
        start_time = time.time()
        
        # Process in batches
        for i in range(0, total_products, batch_size):
            batch = query[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            self.stdout.write(f"\n🔄 Processing batch {batch_num}: products {i+1}-{min(i+batch_size, total_products)}")
            
            for product in batch:
                try:
                    self._process_single_product_fixed(product, save_processed, stats)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error processing {product.name}: {e}"))
                    stats['errors'] += 1
            
            # Show progress
            elapsed = time.time() - start_time
            rate = stats['processed'] / elapsed if elapsed > 0 else 0
            remaining = (total_products - (i + len(batch))) / rate if rate > 0 else 0
            
            self.stdout.write(f"✅ Progress: {i + len(batch)}/{total_products}")
            self.stdout.write(f"📈 Rate: {rate:.1f} products/sec, ETA: {remaining/60:.1f} min")
            self.stdout.write(f"🎯 Detection success: {stats['detection_success']}")
            self.stdout.write(f"🎨 Color analyzed: {stats['color_analyzed']}")
            self.stdout.write(f"🧠 Features extracted: {stats['features_extracted']}")
            self.stdout.write(f"❌ Errors: {stats['errors']}")
        
        # Final results
        elapsed = time.time() - start_time
        self.stdout.write(f"\n🎉 Fixed Processing Complete in {elapsed/60:.1f} minutes!")
        self.stdout.write(f"✅ Successfully processed: {stats['processed']}")
        self.stdout.write(f"❌ Errors: {stats['errors']}")
        
        # Detection statistics
        if stats['detection_success'] > 0:
            success_rate = stats['detection_success'] / stats['processed'] * 100 if stats['processed'] > 0 else 0
            self.stdout.write(f"🎯 Detection success rate: {success_rate:.1f}%")
            
            if stats['detection_methods']:
                self.stdout.write("Detection methods used:")
                for method, count in stats['detection_methods'].items():
                    self.stdout.write(f"   {method}: {count}")
        
        # Rebuild index if features were extracted
        if stats['features_extracted'] > 0:
            self.stdout.write("\n🔄 Rebuilding enhanced vector index...")
            try:
                build_enhanced_vector_index()
                self.stdout.write(self.style.SUCCESS("✅ Enhanced vector index rebuilt"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Index rebuild failed: {e}"))

    def _process_single_product_fixed(self, product, save_processed, stats):
        """Process a single product with fixed pipeline"""
        
        with transaction.atomic():
            try:
                # Download image
                image = self._download_image(product.image_url, product.name)
                if not image:
                    raise Exception("Image download failed")
                
                # Apply fixed processing pipeline
                from api.util_enhanced_fixed import process_product_image_fixed
                
                processing_results, success = process_product_image_fixed(
                    image,
                    product_id=str(product.id),
                    save_processed=save_processed,
                    processed_dir='processed_fixed' if save_processed else None
                )
                
                if not success:
                    raise Exception(f"Fixed processing failed: {processing_results.get('error', 'Unknown error')}")
                
                # Extract results
                preprocessing_info = processing_results['preprocessing_info']
                color_info = processing_results['color_info']
                visual_features = processing_results['visual_features']
                
                # Update statistics
                detection_result = preprocessing_info.get('detection_result')
                if detection_result:
                    stats['detection_success'] += 1
                    method_used = detection_result.get('method', 'unknown')
                    stats['detection_methods'][method_used] = stats['detection_methods'].get(method_used, 0) + 1
                
                # Track color distribution
                color = color_info['category']
                stats['color_distribution'][color] = stats['color_distribution'].get(color, 0) + 1
                
                # Update product with results
                product.color_category = color_info['category']
                product.color_confidence = color_info['confidence']
                if color_info.get('colors'):
                    product.dominant_colors = color_info['colors']
                
                if visual_features:
                    product.visual_embedding = visual_features
                    stats['features_extracted'] += 1
                
                # Generate color-aware text embedding
                try:
                    text_embedding = get_color_aware_text_embedding(
                        product.name, 
                        color_info['category']
                    )
                    product.color_aware_text_embedding = text_embedding.tolist()
                except Exception as e:
                    self.stdout.write(f"⚠️  Text embedding failed for {product.name}: {e}")
                
                # Update processing status
                product.processing_status = 'completed'
                product.processed_at = timezone.now()
                product.save()
                
                stats['processed'] += 1
                stats['color_analyzed'] += 1
                
                # Log success
                detection_info = ""
                if detection_result:
                    method_used = detection_result.get('method', 'unknown')
                    confidence = detection_result.get('confidence', 0)
                    detection_info = f" [{method_used}: {confidence:.2f}]"
                
                self.stdout.write(
                    f"✅ {product.name}: {color_info['category']} "
                    f"({color_info['confidence']:.2f}){detection_info}"
                )
                
            except Exception as e:
                # Handle errors
                product.processing_status = 'failed'
                product.processing_error = str(e)
                product.save()
                
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"❌ {product.name}: {e}"))

    def _download_image(self, url, product_name):
        """Download image with error handling"""
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                
                if len(img_data) < 1000:
                    return None
                
                image = Image.open(io.BytesIO(img_data)).convert('RGB')
                
                if image.size[0] < 50 or image.size[1] < 50:
                    return None
                
                return image
                
        except Exception as e:
            return None

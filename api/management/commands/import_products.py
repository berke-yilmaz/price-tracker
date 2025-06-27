# ===== COMMAND 2: import_products.py =====
# api/management/commands/import_products.py
import pandas as pd
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from api.models import Product
from api.util import (
    categorize_by_color,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    build_vector_index
)

class Command(BaseCommand):
    help = 'Import products from CSV/JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='CSV or JSON file path')
        parser.add_argument('--batch-size', type=int, default=20, help='Batch size')
        parser.add_argument('--limit', type=int, default=0, help='Max products (0=all)')
        parser.add_argument('--skip-existing', action='store_true', help='Skip existing products')
        parser.add_argument('--process-images', action='store_true', help='Process images during import')

    def handle(self, *args, **options):
        file_path = options['file_path']
        batch_size = options['batch_size']
        limit = options['limit']
        skip_existing = options['skip_existing']
        process_images = options['process_images']

        self.stdout.write(self.style.SUCCESS(f'📥 Importing from {file_path}'))

        # Load data
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                self.stdout.write(self.style.ERROR("Unsupported file format"))
                return

            # Clean NaN values
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna('')

            total = len(df)
            if limit > 0 and limit < total:
                df = df.head(limit)
                total = limit

            self.stdout.write(f"📊 {total} products to import")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"File loading error: {e}"))
            return

        stats = {
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'processed': 0
        }

        # Import in batches
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i + batch_size]
            self.stdout.write(f"\n🔄 Batch {i//batch_size + 1}: {len(batch)} products")

            for _, row in batch.iterrows():
                try:
                    self._import_product(row, skip_existing, process_images, stats)
                except Exception as e:
                    self.stdout.write(f"❌ Import error: {e}")
                    stats['errors'] += 1

        # Results
        self.stdout.write(f"\n🎉 Import complete!")
        self.stdout.write(f"✅ Imported: {stats['imported']}")
        self.stdout.write(f"⏭️ Skipped: {stats['skipped']}")
        self.stdout.write(f"🎨 Processed: {stats['processed']}")
        self.stdout.write(f"❌ Errors: {stats['errors']}")

        # Rebuild index if needed
        if process_images and stats['processed'] > 0:
            self.stdout.write("\n🔄 Rebuilding index...")
            build_vector_index()
            self.stdout.write("✅ Index rebuilt!")

    def _import_product(self, row, skip_existing, process_images, stats):
        """Import single product"""
        barcode = self._format_barcode(row.get('barcode'))
        
        # Check existing
        if skip_existing and barcode:
            try:
                Product.objects.get(barcode=barcode)
                stats['skipped'] += 1
                return
            except Product.DoesNotExist:
                pass

        # Prepare data
        product_data = {
            'name': row['name'],
            'barcode': barcode,
            'brand': row.get('brand', ''),
            'category': row.get('category', ''),
            'weight': row.get('weight', ''),
            'ingredients': row.get('ingredients', ''),
            'image_url': row.get('image_url', ''),
            'image_front_url': row.get('image_front_url', ''),
        }

        # Clean empty values
        for key in product_data:
            if pd.isna(product_data[key]):
                product_data[key] = ''

        # Fill empty brand
        if not product_data['brand'] and ' ' in product_data['name']:
            product_data['brand'] = product_data['name'].split(' ')[0]

        # Process image if requested
        if process_images and product_data['image_url']:
            try:
                image = self._download_image(product_data['image_url'])
                if image:
                    # Color analysis
                    color_info = categorize_by_color(image)
                    product_data.update({
                        'color_category': color_info['category'],
                        'color_confidence': color_info['confidence'],
                        'dominant_colors': color_info.get('colors', [])
                    })

                    # Visual features
                    visual_features = extract_visual_features_resnet(image, color_info['category'])
                    product_data['visual_embedding'] = visual_features.tolist()

                    # Text embedding
                    text_embedding = get_color_aware_text_embedding(
                        product_data['name'], color_info['category']
                    )
                    product_data['color_aware_text_embedding'] = text_embedding.tolist()

                    product_data.update({
                        'processing_status': 'completed',
                        'processed_at': timezone.now()
                    })
                    
                    stats['processed'] += 1
                    self.stdout.write(f"🎨 Processed: {product_data['name']}")

            except Exception as e:
                self.stdout.write(f"⚠️ Processing failed for {product_data['name']}: {e}")

        # Create product
        with transaction.atomic():
            if barcode:
                product, created = Product.objects.get_or_create(
                    barcode=barcode,
                    defaults=product_data
                )
                if not created:
                    # Update existing
                    for key, value in product_data.items():
                        setattr(product, key, value)
                    product.save()
            else:
                # No barcode, create new
                product = Product.objects.create(**product_data)

            stats['imported'] += 1
            self.stdout.write(f"✅ {product.name}")

    def _format_barcode(self, barcode):
        """Format barcode"""
        if not barcode or pd.isna(barcode):
            return None
        barcode = str(barcode).strip()
        if barcode.isdigit() and 8 <= len(barcode) <= 14:
            return barcode
        return None

    def _download_image(self, url):
        """Download image"""
        try:
            import urllib.request
            import io
            from PIL import Image
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                img_data = response.read()
                if len(img_data) < 1000:
                    return None
                return Image.open(io.BytesIO(img_data)).convert('RGB')
        except Exception:
            return None

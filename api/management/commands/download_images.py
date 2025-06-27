# api/management/commands/download_images.py
import os
import urllib.request
import time
import io
from PIL import Image as PILImage
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db.models import Q
from api.models import Product

class Command(BaseCommand):
    help = 'Download and save product images locally'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of downloads')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite existing images')
        parser.add_argument('--resize', type=int, default=800, help='Resize images to max width/height')
        parser.add_argument('--quality', type=int, default=85, help='JPEG quality (1-100)')

    def handle(self, *args, **options):
        limit = options['limit']
        overwrite = options['overwrite']
        max_size = options['resize']
        quality = options['quality']

        # Get products with URLs but no local images (unless overwriting)
        query = Product.objects.filter(
            Q(image_url__isnull=False) | Q(image_front_url__isnull=False)
        ).exclude(image_url='').exclude(image_front_url='')

        if not overwrite:
            query = query.filter(Q(image='') | Q(image__isnull=True))

        if limit > 0:
            query = query[:limit]

        total = query.count()
        self.stdout.write(f"📥 Downloading {total} product images...")

        stats = {'downloaded': 0, 'errors': 0, 'skipped': 0}

        for i, product in enumerate(query, 1):
            try:
                self.stdout.write(f"\n{i}/{total}: {product.name}")
                
                # Get image URL (prefer image_url over image_front_url)
                image_url = product.image_url or product.image_front_url
                if not image_url:
                    stats['skipped'] += 1
                    continue

                # Download and process image
                image_data = self._download_image(image_url, max_size, quality)
                if not image_data:
                    stats['errors'] += 1
                    continue

                # Save to model
                filename = f"product_{product.id}_{int(time.time())}.jpg"
                product.image.save(filename, ContentFile(image_data), save=True)
                
                stats['downloaded'] += 1
                self.stdout.write(f"✅ Downloaded and saved")

                # Small delay to be nice to servers
                time.sleep(0.5)

            except Exception as e:
                self.stdout.write(f"❌ Error: {e}")
                stats['errors'] += 1

        # Results
        self.stdout.write(f"\n🎉 Download complete!")
        self.stdout.write(f"✅ Downloaded: {stats['downloaded']}")
        self.stdout.write(f"⏭️ Skipped: {stats['skipped']}")
        self.stdout.write(f"❌ Errors: {stats['errors']}")

    def _download_image(self, url, max_size, quality):
        """Download and optionally resize image"""
        try:
            req = urllib.request.Request(
                url, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                
                # Validate image size
                if len(img_data) < 1000:
                    self.stdout.write(f"   ⚠️  Image too small: {len(img_data)} bytes")
                    return None

                # Process image
                image = PILImage.open(io.BytesIO(img_data)).convert('RGB')
                
                # Validate dimensions
                if image.width < 50 or image.height < 50:
                    self.stdout.write(f"   ⚠️  Image too small: {image.size}")
                    return None
                
                # Resize if needed
                if max_size and (image.width > max_size or image.height > max_size):
                    image.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)
                    self.stdout.write(f"   🔧 Resized to: {image.size}")

                # Save to bytes
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=quality, optimize=True)
                return output.getvalue()

        except Exception as e:
            self.stdout.write(f"   ❌ Download failed: {e}")
            return None
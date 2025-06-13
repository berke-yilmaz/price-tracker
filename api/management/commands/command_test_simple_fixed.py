# api/management/commands/test_simple_fixed.py
import os
import time
import urllib.request
import io
from PIL import Image
from django.core.management.base import BaseCommand
from api.models import Product

class Command(BaseCommand):
    help = 'Test the simple fixed processing pipeline'

    def add_arguments(self, parser):
        parser.add_argument('--product-id', type=int, help='Test specific product ID')
        parser.add_argument('--limit', type=int, default=3, help='Number of products to test')

    def handle(self, *args, **options):
        product_id = options.get('product_id')
        limit = options.get('limit', 3)
        
        self.stdout.write(self.style.SUCCESS("🧪 Testing Simple Fixed Processing"))
        
        if product_id:
            products = Product.objects.filter(id=product_id)
        else:
            products = Product.objects.exclude(image_url='')[:limit]
        
        if not products.exists():
            self.stdout.write(self.style.WARNING("No products found"))
            return
        
        # Create output directory
        os.makedirs('test_simple_fixed', exist_ok=True)
        self.stdout.write(f"📁 Testing {products.count()} products...")
        
        for i, product in enumerate(products, 1):
            self.stdout.write(f"\n{i}. {product.name}")
            
            try:
                # Download image
                image = self._download_image(product.image_url)
                if not image:
                    continue
                
                self.stdout.write(f"   Original: {image.size}")
                
                # Test processing
                start_time = time.time()
                
                from api.util_enhanced_fixed import process_product_image_simple_fixed
                
                results, success = process_product_image_simple_fixed(
                    image,
                    product_id=str(product.id),
                    save_processed=True,
                    processed_dir='test_simple_fixed'
                )
                
                processing_time = time.time() - start_time
                
                if success:
                    self.stdout.write(f"   ✅ Success in {processing_time:.2f}s")
                    self.stdout.write(f"   Final: {results['preprocessing_info']['final_size']}")
                    self.stdout.write(f"   Color: {results['color_info']['category']}")
                    if results.get('visual_features'):
                        self.stdout.write(f"   Features: {len(results['visual_features'])} dims")
                else:
                    self.stdout.write(f"   ❌ Failed: {results.get('error')}")
                
            except Exception as e:
                self.stdout.write(f"   💥 Error: {e}")
        
        self.stdout.write(f"\n🎉 Test completed! Check test_simple_fixed/ for results")

    def _download_image(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                if len(img_data) < 1000:
                    return None
                return Image.open(io.BytesIO(img_data)).convert('RGB')
        except Exception as e:
            self.stdout.write(f"   ❌ Download failed: {e}")
            return None

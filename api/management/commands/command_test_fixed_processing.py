# api/management/commands/test_fixed_processing.py
import os
import time
import urllib.request
import io
from PIL import Image
from django.core.management.base import BaseCommand
from api.models import Product

class Command(BaseCommand):
    help = 'Test the fixed processing pipeline on existing products'

    def add_arguments(self, parser):
        parser.add_argument('--product-id', type=int, help='Test specific product ID')
        parser.add_argument('--limit', type=int, default=5, help='Number of products to test')
        parser.add_argument('--save-results', action='store_true', help='Save processed images')

    def handle(self, *args, **options):
        product_id = options.get('product_id')
        limit = options.get('limit', 5)
        save_results = options.get('save_results', False)
        
        # Import the fixed processing functions
        try:
            from api.util_enhanced_fixed import (
                enhanced_product_preprocessing_fixed,
                process_product_image_fixed
            )
            self.stdout.write(self.style.SUCCESS("✅ Fixed processing functions loaded"))
        except ImportError:
            self.stdout.write(self.style.ERROR("❌ Could not import fixed processing functions"))
            return
        
        if product_id:
            products = Product.objects.filter(id=product_id)
        else:
            products = Product.objects.exclude(image_url='')[:limit]
        
        if not products.exists():
            self.stdout.write(self.style.WARNING("No products found to test"))
            return
        
        self.stdout.write(f"🧪 Testing fixed processing on {products.count()} products...")
        
        # Create output directory
        if save_results:
            os.makedirs('test_fixed_processing', exist_ok=True)
            self.stdout.write("📁 Results will be saved to: test_fixed_processing/")
        
        for i, product in enumerate(products, 1):
            self.stdout.write(f"\n{i}. Testing: {product.name}")
            
            try:
                # Download image
                self.stdout.write(f"   📥 Downloading: {product.image_url}")
                image = self._download_image(product.image_url)
                if not image:
                    continue
                
                self.stdout.write(f"   📏 Original size: {image.size}")
                
                # Test complete pipeline
                self.stdout.write(f"   🚀 Testing complete fixed pipeline...")
                start_time = time.time()
                
                try:
                    results, success = process_product_image_fixed(
                        image,
                        product_id=str(product.id),
                        save_processed=save_results,
                        processed_dir='test_fixed_processing'
                    )
                    processing_time = time.time() - start_time
                    
                    if success:
                        self.stdout.write(f"      ✅ Complete pipeline success in {processing_time:.2f}s")
                        
                        # Show results
                        preprocessing_info = results['preprocessing_info']
                        color_info = results['color_info']
                        
                        self.stdout.write(f"      🎨 Color: {color_info['category']} "
                                        f"(confidence: {color_info['confidence']:.2f})")
                        self.stdout.write(f"      🔧 Steps: {preprocessing_info['steps_applied']}")
                        
                        if results.get('visual_features'):
                            self.stdout.write(f"      🧠 Visual features: {len(results['visual_features'])} dims")
                        
                        if preprocessing_info.get('detection_result'):
                            detection = preprocessing_info['detection_result']
                            self.stdout.write(f"      🎯 Detection: {detection.get('method')} "
                                            f"(confidence: {detection.get('confidence', 0):.2f})")
                    else:
                        self.stdout.write(f"      ❌ Pipeline failed: {results.get('error')}")
                
                except Exception as e:
                    self.stdout.write(f"      💥 Exception: {e}")
                
            except Exception as e:
                self.stdout.write(f"   💥 Product test failed: {e}")
        
        # Summary
        self.stdout.write(f"\n🎉 Fixed processing test completed!")
        
        if save_results:
            saved_files = [f for f in os.listdir('test_fixed_processing') if f.endswith('.png')]
            self.stdout.write(f"📊 {len(saved_files)} processed images saved")

    def _download_image(self, url):
        """Download image with error handling"""
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                
                if len(img_data) < 1000:
                    self.stdout.write(f"      ⚠️  Image too small: {len(img_data)} bytes")
                    return None
                
                image = Image.open(io.BytesIO(img_data)).convert('RGB')
                
                if image.size[0] < 50 or image.size[1] < 50:
                    self.stdout.write(f"      ⚠️  Image dimensions too small: {image.size}")
                    return None
                
                return image
                
        except Exception as e:
            self.stdout.write(f"      ❌ Download failed: {e}")
            return None

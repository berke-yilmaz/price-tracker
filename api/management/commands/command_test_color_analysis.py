# api/management/commands/test_color_analysis.py
from django.core.management.base import BaseCommand
from api.models import Product
from api.util import categorize_by_color
import urllib.request
import io
from PIL import Image

class Command(BaseCommand):
    help = 'Test color analysis on existing products'

    def add_arguments(self, parser):
        parser.add_argument('--product-id', type=int, help='Test specific product ID')
        parser.add_argument('--limit', type=int, default=5, help='Number of products to test')

    def handle(self, *args, **options):
        product_id = options.get('product_id')
        limit = options.get('limit', 5)
        
        if product_id:
            products = Product.objects.filter(id=product_id)
        else:
            products = Product.objects.exclude(image_url='')[:limit]
        
        self.stdout.write(f"🧪 Testing color analysis on {products.count()} products...")
        
        for i, product in enumerate(products, 1):
            self.stdout.write(f"\n{i}. Testing: {product.name}")
            self.stdout.write(f"   Current color: {product.color_category} (confidence: {product.color_confidence})")
            
            try:
                # Download image
                self.stdout.write(f"   Downloading: {product.image_url}")
                req = urllib.request.Request(
                    product.image_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                
                with urllib.request.urlopen(req, timeout=15) as response:
                    img_data = response.read()
                    
                if len(img_data) < 1000:
                    self.stdout.write(f"   ❌ Image too small: {len(img_data)} bytes")
                    continue
                
                # Convert to PIL Image
                image = Image.open(io.BytesIO(img_data)).convert('RGB')
                self.stdout.write(f"   Image size: {image.size}")
                
                # Test color analysis
                self.stdout.write("   🎨 Analyzing color...")
                color_info = categorize_by_color(image)
                
                self.stdout.write(f"   ✅ Detected color: {color_info['category']} (confidence: {color_info['confidence']:.3f})")
                self.stdout.write(f"   Dominant colors: {len(color_info.get('colors', []))} colors found")
                
                if 'color_votes' in color_info:
                    self.stdout.write(f"   Color votes: {color_info['color_votes']}")
                
                # Update product if different
                if color_info['category'] != product.color_category:
                    self.stdout.write(f"   🔄 Updating product color: {product.color_category} -> {color_info['category']}")
                    product.color_category = color_info['category']
                    product.color_confidence = color_info['confidence']
                    if color_info.get('colors'):
                        product.dominant_colors = color_info['colors']
                    product.save()
                    self.stdout.write("   ✅ Product updated!")
                
            except Exception as e:
                self.stdout.write(f"   ❌ Error: {str(e)}")
                continue
        
        self.stdout.write(f"\n📊 Final results:")
        self.stdout.write("Run 'python manage.py processing_stats' to see updated statistics")
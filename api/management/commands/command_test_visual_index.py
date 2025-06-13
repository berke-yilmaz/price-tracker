# api/management/commands/test_visual_index.py
from django.core.management.base import BaseCommand
from api.util import get_enhanced_vector_index
from api.models import Product
import time

class Command(BaseCommand):
    help = 'Test the enhanced visual index functionality'

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Enhanced Visual Index")
        self.stdout.write("=" * 40)
        
        try:
            # Test index loading
            self.stdout.write("1. Testing index loading...")
            start_time = time.time()
            index = get_enhanced_vector_index()
            load_time = time.time() - start_time
            
            self.stdout.write(f"   ✅ Index loaded in {load_time:.3f} seconds")
            
            # Check index statistics
            self.stdout.write("\n2. Index Statistics:")
            total_indexed = 0
            color_breakdown = {}
            
            for color, color_data in index.color_indices.items():
                count = color_data['index'].ntotal
                if count > 0:
                    color_breakdown[color] = count
                    total_indexed += count
            
            self.stdout.write(f"   Total indexed products: {total_indexed}")
            
            if color_breakdown:
                self.stdout.write("   Color distribution:")
                for color, count in sorted(color_breakdown.items(), key=lambda x: x[1], reverse=True):
                    color_display = dict(Product.COLOR_CHOICES).get(color, color)
                    self.stdout.write(f"     {color_display}: {count} products")
            else:
                self.stdout.write("   No products indexed yet")
            
            # Test search functionality
            self.stdout.write("\n3. Testing search functionality...")
            
            if total_indexed > 0:
                # Get a sample product for testing
                sample_product = Product.objects.filter(visual_embedding__isnull=False).first()
                
                if sample_product:
                    self.stdout.write(f"   Testing with: {sample_product.name}")
                    
                    # Perform search
                    results = index.search(
                        sample_product.visual_embedding,
                        color_category=sample_product.color_category,
                        k=5
                    )
                    
                    self.stdout.write(f"   ✅ Search returned {len(results)} results")
                    
                    for i, result in enumerate(results[:3], 1):
                        try:
                            product = Product.objects.get(id=result['product_id'])
                            self.stdout.write(f"     {i}. {product.name} (distance: {result['distance']:.3f})")
                        except Product.DoesNotExist:
                            self.stdout.write(f"     {i}. Product ID {result['product_id']} not found")
                else:
                    self.stdout.write("   ⚠️  No products with visual embeddings found for testing")
            else:
                self.stdout.write("   ⚠️  No products indexed - cannot test search")
            
            # Performance test
            self.stdout.write("\n4. Performance Test:")
            if total_indexed > 0:
                import numpy as np
                
                # Generate random query vector
                query_vector = np.random.random(2048).astype(np.float32)
                
                # Time multiple searches
                search_times = []
                for _ in range(10):
                    start_time = time.time()
                    results = index.search(query_vector, k=5)
                    search_times.append(time.time() - start_time)
                
                avg_time = sum(search_times) / len(search_times)
                self.stdout.write(f"   Average search time: {avg_time*1000:.2f} ms")
                self.stdout.write(f"   Searches per second: {1/avg_time:.0f}")
            else:
                self.stdout.write("   Cannot test performance - no indexed products")
            
            self.stdout.write(f"\n✅ Visual index test completed!")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Test failed: {str(e)}")
            )
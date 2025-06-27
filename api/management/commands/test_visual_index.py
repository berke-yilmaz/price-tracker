# api/management/commands/test_visual_index.py
from django.core.management.base import BaseCommand
from api.util import get_vector_index
from api.models import Product
import numpy as np

class Command(BaseCommand):
    help = 'Test the visual index functionality'

    def add_arguments(self, parser):
        parser.add_argument('--detailed', action='store_true', help='Show detailed statistics')
        parser.add_argument('--test-search', action='store_true', help='Test visual search with a sample product')

    def handle(self, *args, **options):
        detailed = options['detailed']
        test_search = options['test_search']

        self.stdout.write(self.style.SUCCESS('🔍 Testing Visual Index'))

        try:
            # Test index loading
            index = get_vector_index()
            self.stdout.write("✅ Index loaded successfully!")

            # Count indexed products
            total_indexed = 0
            color_breakdown = {}
            
            for color, color_index in index.color_indices.items():
                count = color_index['index'].ntotal
                total_indexed += count
                color_breakdown[color] = count

            total_in_db = Product.objects.count()
            
            self.stdout.write(f"\n📊 Index Statistics:")
            self.stdout.write(f"   Total products in database: {total_in_db}")
            self.stdout.write(f"   Total products indexed: {total_indexed}")
            self.stdout.write(f"   Index coverage: {(total_indexed/total_in_db*100):.1f}%")

            # Color breakdown
            if detailed:
                self.stdout.write(f"\n🎨 Color Index Breakdown:")
                for color, count in sorted(color_breakdown.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:
                        color_display = dict(Product.COLOR_CHOICES).get(color, color)
                        self.stdout.write(f"   {color_display}: {count} products")

            # Test search functionality
            if test_search:
                self._test_search_functionality(index)

            # Overall status
            if total_indexed > 0:
                self.stdout.write(self.style.SUCCESS(f"\n✅ Visual index is working! Ready for mobile app development."))
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ No products indexed. Run: python manage.py manage_data --rebuild-index"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Index test failed: {e}"))
            self.stdout.write(self.style.WARNING("Try rebuilding with: python manage.py manage_data --rebuild-index"))

    def _test_search_functionality(self, index):
        """Test the search functionality with a sample product"""
        self.stdout.write(f"\n🔍 Testing Search Functionality:")
        
        try:
            # Find a product with visual features
            test_product = Product.objects.filter(
                visual_embedding__isnull=False
            ).first()
            
            if not test_product:
                self.stdout.write("   ⚠️ No products with visual features found")
                return

            self.stdout.write(f"   Testing with: {test_product.name}")
            
            # Get the visual features
            visual_features = np.array(test_product.visual_embedding, dtype=np.float32)
            
            # Search for similar products
            results = index.search(
                visual_features,
                color_category=test_product.color_category,
                k=5,
                search_similar_colors=True
            )
            
            if results:
                self.stdout.write(f"   ✅ Found {len(results)} similar products")
                self.stdout.write(f"   Top match distance: {results[0]['distance']:.2f}")
                
                # Show top 3 results
                for i, result in enumerate(results[:3]):
                    try:
                        product = Product.objects.get(id=result['product_id'])
                        similarity = 1.0 - min(result['distance'] / 100.0, 1.0)
                        self.stdout.write(f"     {i+1}. {product.name} (similarity: {similarity:.2f})")
                    except Product.DoesNotExist:
                        continue
            else:
                self.stdout.write("   ⚠️ Search returned no results")

        except Exception as e:
            self.stdout.write(f"   ❌ Search test failed: {e}")

    def add_arguments(self, parser):
        parser.add_argument('--detailed', action='store_true', help='Show detailed color breakdown')
        parser.add_argument('--test-search', action='store_true', help='Test search functionality with sample product')
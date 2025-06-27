# api/management/commands/manage_data.py
import time  # Add this import at the top
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from api.models import Product, Price, ProcessingJob
from api.util import build_vector_index

class Command(BaseCommand):
    help = 'Manage product data: stats, cleanup, rebuild index'

    def add_arguments(self, parser):
        parser.add_argument('--stats', action='store_true', help='Show statistics')
        parser.add_argument('--clean-duplicates', action='store_true', help='Remove duplicates')
        parser.add_argument('--clean-incomplete', action='store_true', help='Remove incomplete products')
        parser.add_argument('--rebuild-index', action='store_true', help='Rebuild vector index')
        parser.add_argument('--reset-all', action='store_true', help='Delete all data')
        parser.add_argument('--confirm', action='store_true', help='Confirm destructive operations')

    def handle(self, *args, **options):
        stats = options['stats']
        clean_duplicates = options['clean_duplicates']
        clean_incomplete = options['clean_incomplete']
        rebuild_index = options['rebuild_index']
        reset_all = options['reset_all']
        confirm = options['confirm']

        # Default to stats if no action specified
        if not any([stats, clean_duplicates, clean_incomplete, rebuild_index, reset_all]):
            stats = True

        self.stdout.write(self.style.SUCCESS('📊 Data Management'))

        # Show statistics
        if stats:
            self._show_stats()

        # Clean duplicates
        if clean_duplicates:
            if not confirm:
                self.stdout.write(self.style.WARNING("Use --confirm to clean duplicates"))
                return
            self._clean_duplicates()

        # Clean incomplete
        if clean_incomplete:
            if not confirm:
                self.stdout.write(self.style.WARNING("Use --confirm to clean incomplete products"))
                return
            self._clean_incomplete()

        # Rebuild index
        if rebuild_index:
            self._rebuild_index()

        # Reset all data
        if reset_all:
            if not confirm:
                self.stdout.write(self.style.WARNING("⚠️ Use --confirm to delete ALL data"))
                return
            self._reset_all()

    def _show_stats(self):
        """Show comprehensive statistics"""
        total_products = Product.objects.count()
        
        if total_products == 0:
            self.stdout.write("📭 No products in database")
            return

        # Basic stats
        color_analyzed = Product.objects.exclude(color_category='unknown').count()
        with_visual = Product.objects.filter(visual_embedding__isnull=False).count()
        with_images = Product.objects.exclude(image_url='').count()
        completed = Product.objects.filter(processing_status='completed').count()

        self.stdout.write(f"\n📈 Database Statistics:")
        self.stdout.write(f"   Total products: {total_products}")
        self.stdout.write(f"   With images: {with_images}")
        self.stdout.write(f"   Color analyzed: {color_analyzed}")
        self.stdout.write(f"   Visual features: {with_visual}")
        self.stdout.write(f"   Fully processed: {completed}")

        # Color distribution
        color_stats = Product.objects.values('color_category').annotate(
            count=Count('id')
        ).order_by('-count')

        self.stdout.write(f"\n🎨 Color Distribution:")
        for stat in color_stats:
            color = stat['color_category']
            count = stat['count']
            percentage = (count / total_products) * 100
            color_display = dict(Product.COLOR_CHOICES).get(color, color)
            self.stdout.write(f"   {color_display}: {count} ({percentage:.1f}%)")

        # Processing status
        status_stats = Product.objects.values('processing_status').annotate(
            count=Count('id')
        ).order_by('-count')

        self.stdout.write(f"\n⚙️ Processing Status:")
        for stat in status_stats:
            status = stat['processing_status']
            count = stat['count']
            self.stdout.write(f"   {status}: {count}")

        # Price stats
        total_prices = Price.objects.count()
        stores_count = Price.objects.values('store').distinct().count()
        
        self.stdout.write(f"\n💰 Price Data:")
        self.stdout.write(f"   Total price entries: {total_prices}")
        self.stdout.write(f"   Stores with prices: {stores_count}")

    def _clean_duplicates(self):
        """Remove duplicate products"""
        self.stdout.write("🧹 Cleaning duplicates...")
        
        deleted_total = 0

        # 1. Same barcode duplicates
        duplicate_barcodes = Product.objects.exclude(barcode__isnull=True).exclude(
            barcode=''
        ).values('barcode').annotate(count=Count('barcode')).filter(count__gt=1)

        for item in duplicate_barcodes:
            barcode = item['barcode']
            duplicates = Product.objects.filter(barcode=barcode).order_by('-id')
            keep = duplicates.first()
            to_delete = duplicates.exclude(id=keep.id)
            count = to_delete.count()
            to_delete.delete()
            deleted_total += count
            self.stdout.write(f"   Removed {count} duplicates for barcode {barcode}")

        # 2. Same name+brand duplicates
        duplicate_names = Product.objects.values('name', 'brand').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        for item in duplicate_names:
            name = item['name']
            brand = item['brand']
            duplicates = Product.objects.filter(name=name, brand=brand).order_by('-id')
            if duplicates.count() > 1:
                keep = duplicates.first()
                to_delete = duplicates.exclude(id=keep.id)
                count = to_delete.count()
                to_delete.delete()
                deleted_total += count
                self.stdout.write(f"   Removed {count} duplicates for {name} ({brand})")

        self.stdout.write(f"✅ Removed {deleted_total} duplicate products")

    def _clean_incomplete(self):
        """Remove incomplete products"""
        self.stdout.write("🧹 Cleaning incomplete products...")

        # Products without essential data
        incomplete = Product.objects.filter(
            Q(name='') | Q(name__isnull=True) |
            (Q(image_url='') & Q(image_front_url='')) |
            (Q(image_url__isnull=True) & Q(image_front_url__isnull=True))
        )

        count = incomplete.count()
        if count > 0:
            incomplete.delete()
            self.stdout.write(f"✅ Removed {count} incomplete products")
        else:
            self.stdout.write("✅ No incomplete products found")

    def _rebuild_index(self):
        """Rebuild vector index"""
        self.stdout.write("🔄 Rebuilding vector index...")
        try:
            start_time = time.time()
            build_vector_index()
            elapsed = time.time() - start_time
            self.stdout.write(f"✅ Index rebuilt in {elapsed:.1f}s")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Index rebuild failed: {e}"))

    def _reset_all(self):
        """Delete all data"""
        self.stdout.write(self.style.WARNING("🗑️ Deleting ALL data..."))

        deleted_counts = {}

        try:
            with transaction.atomic():
                # Delete in proper order
                count = ProcessingJob.objects.count()
                ProcessingJob.objects.all().delete()
                deleted_counts['ProcessingJob'] = count

                count = Price.objects.count()
                Price.objects.all().delete()
                deleted_counts['Price'] = count

                count = Product.objects.count()
                Product.objects.all().delete()
                deleted_counts['Product'] = count

                self.stdout.write("✅ All data deleted successfully")
                
                for model, count in deleted_counts.items():
                    self.stdout.write(f"   {model}: {count} deleted")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Deletion failed: {e}"))
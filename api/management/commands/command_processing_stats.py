# api/management/commands/processing_stats.py
from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q
from api.models import Product, ProcessingJob

class Command(BaseCommand):
    help = 'Get processing statistics'

    def handle(self, *args, **options):
        try:
            total_products = Product.objects.count()
            
            stats = {
                'total_products': total_products,
                'color_analyzed': Product.objects.exclude(color_category='unknown').count(),
                'with_visual_features': Product.objects.filter(visual_embedding__isnull=False).count(),
                'fully_processed': Product.objects.filter(
                    processing_status='completed'
                ).count(),
                'processing_failed': Product.objects.filter(
                    processing_status='failed'
                ).count(),
                'pending_processing': Product.objects.filter(
                    processing_status='pending'
                ).count(),
            }
            
            self.stdout.write("📊 Processing Statistics:")
            self.stdout.write(f"   Total products: {stats['total_products']}")
            self.stdout.write(f"   Color analyzed: {stats['color_analyzed']}")
            self.stdout.write(f"   With visual features: {stats['with_visual_features']}")
            self.stdout.write(f"   Fully processed: {stats['fully_processed']}")
            self.stdout.write(f"   Processing failed: {stats['processing_failed']}")
            self.stdout.write(f"   Pending processing: {stats['pending_processing']}")
            
            # Color distribution
            color_stats = Product.objects.values('color_category').annotate(
                count=Count('id'),
                avg_confidence=Avg('color_confidence')
            ).order_by('-count')
            
            self.stdout.write("\n🎨 Color Distribution:")
            for stat in color_stats:
                color = stat['color_category']
                count = stat['count']
                avg_conf = stat['avg_confidence'] or 0.0
                percentage = (count / total_products * 100) if total_products > 0 else 0
                
                color_display = dict(Product.COLOR_CHOICES).get(color, color)
                self.stdout.write(f"   {color_display}: {count} products ({percentage:.1f}%) - avg confidence: {avg_conf:.2f}")
            
            # Processing job statistics (if they exist)
            try:
                job_stats = ProcessingJob.objects.values('status').annotate(
                    count=Count('id')
                )
                if job_stats.exists():
                    self.stdout.write("\n⚙️ Processing Job Statistics:")
                    for item in job_stats:
                        self.stdout.write(f"   {item['status']}: {item['count']} jobs")
            except:
                pass  # ProcessingJob model might not exist
            
            # Confidence distribution
            confidence_ranges = [
                (0.0, 0.3, 'Low'),
                (0.3, 0.6, 'Medium'),
                (0.6, 0.8, 'High'),
                (0.8, 1.0, 'Very High')
            ]
            
            self.stdout.write("\n🎯 Color Confidence Distribution:")
            for min_conf, max_conf, label in confidence_ranges:
                count = Product.objects.filter(
                    color_confidence__gte=min_conf,
                    color_confidence__lt=max_conf
                ).count()
                self.stdout.write(f"   {label} ({min_conf}-{max_conf}): {count} products")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
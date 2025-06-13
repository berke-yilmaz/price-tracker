# api/management/commands/clean_database.py
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Product, Price, ProcessingJob, ColorAnalysisStats
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Completely clean the database for fresh start'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', 
                            help='Confirm the deletion (required)')
        parser.add_argument('--keep-users', action='store_true',
                            help='Keep user accounts')
        parser.add_argument('--products-only', action='store_true',
                            help='Only delete products and related data')

    def handle(self, *args, **options):
        confirm = options['confirm']
        keep_users = options['keep_users']
        products_only = options['products_only']
        
        if not confirm:
            self.stdout.write(self.style.ERROR(
                "⚠️  DİKKAT: Bu işlem veritabanını tamamen temizleyecek!\n"
                "Onaylamak için --confirm parametresini kullanın.\n"
                "Örnek: python manage.py clean_database --confirm"
            ))
            return
        
        self.stdout.write(self.style.WARNING("🗑️  Veritabanı temizleniyor..."))
        
        deleted_counts = {}
        
        try:
            with transaction.atomic():
                # Delete in proper order to respect foreign keys
                
                # 1. Processing Jobs
                count = ProcessingJob.objects.count()
                ProcessingJob.objects.all().delete()
                deleted_counts['ProcessingJob'] = count
                self.stdout.write(f"✅ {count} processing job silindi")
                
                # 2. Color Analysis Stats
                count = ColorAnalysisStats.objects.count()
                ColorAnalysisStats.objects.all().delete()
                deleted_counts['ColorAnalysisStats'] = count
                self.stdout.write(f"✅ {count} renk istatistiği silindi")
                
                # 3. Prices (depends on Product)
                count = Price.objects.count()
                Price.objects.all().delete()
                deleted_counts['Price'] = count
                self.stdout.write(f"✅ {count} fiyat kaydı silindi")
                
                # 4. Products
                count = Product.objects.count()
                Product.objects.all().delete()
                deleted_counts['Product'] = count
                self.stdout.write(f"✅ {count} ürün silindi")
                
                # 5. Users (if not keeping them and not products-only)
                if not keep_users and not products_only:
                    count = User.objects.count()
                    User.objects.all().delete()
                    deleted_counts['User'] = count
                    self.stdout.write(f"✅ {count} kullanıcı silindi")
                
                self.stdout.write(self.style.SUCCESS("\n🎉 Veritabanı başarıyla temizlendi!"))
                
                # Show summary
                self.stdout.write("\n📊 Silinen Kayıtlar:")
                for model, count in deleted_counts.items():
                    self.stdout.write(f"   {model}: {count}")
                
                # Show remaining
                remaining_products = Product.objects.count()
                remaining_users = User.objects.count()
                self.stdout.write(f"\n📈 Kalan Kayıtlar:")
                self.stdout.write(f"   Ürünler: {remaining_products}")
                self.stdout.write(f"   Kullanıcılar: {remaining_users}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Temizlik sırasında hata: {str(e)}"))
            raise
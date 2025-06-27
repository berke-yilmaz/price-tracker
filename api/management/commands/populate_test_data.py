# api/management/commands/populate_test_data.py
import random
import re
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from api.models import Product, Store, Price
from django.db.models import Count

class Command(BaseCommand):
    help = 'Populate database with realistic Turkish stores and prices'

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=100, help='Number of products to select')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
        parser.add_argument('--reset', action='store_true', help='Reset all stores and prices first')

    def handle(self, *args, **options):
        product_count = options['products']
        dry_run = options['dry_run']
        reset = options['reset']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))

        self.stdout.write(self.style.SUCCESS(f'🏪 Populating test data for {product_count} products in Gebze, Turkey'))

        if reset and not dry_run:
            self._reset_data()

        stores = self._create_gebze_stores(dry_run)
        products = self._select_turkish_products(product_count)
        self._create_realistic_prices(products, stores, dry_run)
        self._show_summary(products, stores, dry_run)

    def _reset_data(self):
        """Reset stores and prices"""
        self.stdout.write('🗑️ Resetting existing stores and prices...')
        with transaction.atomic():
            Price.objects.all().delete()
            Store.objects.all().delete()
        self.stdout.write('✅ Reset complete')

    def _create_gebze_stores(self, dry_run=False):
        """Create realistic stores in Gebze, Turkey"""
        self.stdout.write("\nCreating/Verifying Stores...")
        gebze_stores = [
            {'name': 'Migros Gebze AVM', 'address': 'Cumhuriyet Mahallesi, Gebze Center, 41400 Gebze/Kocaeli', 'latitude': 40.8058, 'longitude': 29.4314},
            {'name': 'BİM Gebze Merkez', 'address': 'Hacı Halil Mahallesi, Atatürk Caddesi No:45, 41400 Gebze/Kocaeli', 'latitude': 40.8025, 'longitude': 29.4289},
            {'name': 'A101 Gebze Şubesi', 'address': 'Cumhuriyet Mahallesi, İnönü Caddesi No:78, 41400 Gebze/Kocaeli', 'latitude': 40.8041, 'longitude': 29.4331},
            {'name': 'ŞOK Market Gebze', 'address': 'Mehmet Akif Ersoy Mahallesi, Gebze Bulvarı No:123, 41400 Gebze/Kocaeli', 'latitude': 40.8091, 'longitude': 29.4278},
            {'name': 'CarrefourSA Gebze', 'address': 'Pelitli Mahallesi, D-100 Karayolu Üzeri, 41400 Gebze/Kocaeli', 'latitude': 40.7998, 'longitude': 29.4356}
        ]
        stores = []
        for store_data in gebze_stores:
            if dry_run:
                self.stdout.write(f"   (dry-run) Would use store: {store_data['name']}")
                stores.append(store_data)
            else:
                store, created = Store.objects.get_or_create(
                    name=store_data['name'],
                    defaults={'address': store_data['address'], 'latitude': store_data['latitude'], 'longitude': store_data['longitude']}
                )
                stores.append(store)
                status = "✅ Created" if created else "📝 Exists"
                self.stdout.write(f"   {status}: {store.name}")
        return stores

    def _select_turkish_products(self, count):
        """Select Turkish products from database using smart filtering"""
        self.stdout.write(f"\nSelecting {count} Turkish products from database...")
        turkish_keywords = [
            'ülker', 'eti', 'torku', 'sütaş', 'pınar', 'börek', 'baklava', 'lokum', 'helva', 'pekmez', 'salça', 'turşu',
            'ayran', 'kefir', 'yogurt', 'peynir', 'zeytin', 'zeytinyağı', 'bulgur', 'pirinç', 'nohut', 'mercimek', 'çay',
            'coca cola', 'pepsi', 'nestle', 'magnum', 'nutella', 'kinder', 'doritos', 'lays', 'süt', 'ekmek', 'yumurta',
            'tavuk', 'et', 'balık', 'domates', 'soğan', 'patates', 'elma', 'muz', 'makarna', 'şeker', 'tuz', 'yağ', 'un'
        ]
        from django.db.models import Q
        search_conditions = Q()
        for keyword in turkish_keywords:
            search_conditions |= (Q(name__icontains=keyword) | Q(brand__icontains=keyword))
        matching_products = Product.objects.filter(search_conditions).distinct()
        self.stdout.write(f"🔍 Found {matching_products.count()} products matching Turkish criteria.")

        if matching_products.count() >= count:
            selected_products = random.sample(list(matching_products), count)
        else:
            selected_products = list(matching_products)
            remaining_count = count - len(selected_products)
            if remaining_count > 0:
                remaining_products = Product.objects.exclude(id__in=[p.id for p in selected_products]).order_by('?')[:remaining_count]
                selected_products.extend(list(remaining_products))

        self.stdout.write(f"✅ Selected {len(selected_products)} products.")
        return selected_products

    def _create_realistic_prices(self, products, stores, dry_run=False):
        """Create realistic prices for products in a variable number of stores."""
        user = None
        if not dry_run:
            user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
        
        price_categories = {
            'beverage': {'min': 3.50, 'max': 25.00, 'keywords': ['cola', 'pepsi', 'fanta', 'su', 'içecek', 'ayran']},
            'snacks': {'min': 5.00, 'max': 45.00, 'keywords': ['chips', 'doritos', 'lays', 'kraker', 'bisküvi', 'gofret']},
            'dairy': {'min': 10.00, 'max': 80.00, 'keywords': ['milk', 'süt', 'peynir', 'cheese', 'yogurt', 'yoğurt']},
            'sweets': {'min': 5.00, 'max': 90.00, 'keywords': ['chocolate', 'çikolata', 'şeker', 'albeni', 'eti', 'ülker', 'nutella']},
            'bakery': {'min': 7.50, 'max': 50.00, 'keywords': ['bread', 'ekmek', 'börek', 'simit']},
            'protein': {'min': 50.00, 'max': 450.00, 'keywords': ['meat', 'et', 'tavuk', 'chicken', 'balık', 'sucuk']},
            'pantry': {'min': 15.00, 'max': 150.00, 'keywords': ['rice', 'pirinç', 'makarna', 'un', 'şeker', 'tuz', 'yağ', 'oil']},
            'general': {'min': 10.00, 'max': 60.00, 'keywords': []}
        }

        def get_product_category(product):
            product_text = f"{product.name} {product.brand}".lower()
            for category, data in price_categories.items():
                if any(keyword in product_text for keyword in data['keywords']):
                    return category
            return 'general'

        def get_base_price(category_data):
            base = random.uniform(category_data['min'], category_data['max'])
            return Decimal(f"{int(base)}.{random.choice([0, 25, 50, 75, 90, 95])}")

        def get_store_multiplier(store_name):
            store_name_lower = store_name.lower()
            if 'migros' in store_name_lower: return 1.1
            if 'carrefour' in store_name_lower: return 1.05
            if 'bim' in store_name_lower: return 0.9
            if 'a101' in store_name_lower: return 0.92
            if 'şok' in store_name_lower: return 0.88
            return 1.0

        total_prices_created = 0
        self.stdout.write(f"\n💰 Creating a variable number of prices for {len(products)} products...")
        
        with transaction.atomic():
            for product in products:
                category = get_product_category(product)
                category_data = price_categories[category]
                base_price = get_base_price(category_data)
                
                # *** NEW LOGIC: Assign prices to a random subset of stores ***
                # This ensures some products have few prices, and others have more.
                # We'll choose between 2 and the total number of available stores.
                num_stores_for_product = random.randint(2, len(stores))
                selected_stores = random.sample(stores, num_stores_for_product)

                if dry_run:
                    self.stdout.write(f"   Product: {product.name} (Base Price: ₺{base_price}) -> will be priced in {num_stores_for_product} stores.")

                for store in selected_stores:
                    store_name = store['name'] if dry_run else store.name
                    store_multiplier = get_store_multiplier(store_name)
                    variation = Decimal(str(random.uniform(0.97, 1.03)))
                    final_price = (base_price * Decimal(str(store_multiplier)) * variation).quantize(Decimal('0.01'))
                    
                    if dry_run:
                        self.stdout.write(f"     -> {store_name}: ~₺{final_price}")
                    else:
                        Price.objects.update_or_create(
                            product=product,
                            store=store,
                            defaults={'price': final_price, 'user': user}
                        )
                        total_prices_created += 1

        if not dry_run:
            self.stdout.write(f"✅ Created/Updated {total_prices_created} price entries across {len(products)} products.")

    def _show_summary(self, products, stores, dry_run=False):
        """Show summary of what was created"""
        self.stdout.write(self.style.SUCCESS('\n📊 SUMMARY'))
        self.stdout.write(f"🏪 Stores considered: {len(stores)}")
        self.stdout.write(f"📦 Products considered: {len(products)}")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\n✅ ACTUAL DATABASE STATE:"))
            self.stdout.write(f"   Total stores in DB: {Store.objects.count()}")
            self.stdout.write(f"   Total products in DB: {Product.objects.count()}")
            self.stdout.write(f"   Total prices in DB: {Price.objects.count()}")
            
            self.stdout.write(self.style.SUCCESS("\n💡 Sample price checks:"))
            products_to_check = Product.objects.filter(id__in=[p.id for p in products]).annotate(price_count=Count('prices')).order_by('-price_count')[:3]
            for p in products_to_check:
                self.stdout.write(f"   - '{p.name}' has {p.price_count} price(s) recorded.")

        self.stdout.write(self.style.SUCCESS('\n🎉 Test data population complete!'))
        if dry_run:
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply these changes.'))
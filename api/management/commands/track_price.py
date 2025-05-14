#!/usr/bin/env python3
# api/management/commands/track_price.py
from django.core.management.base import BaseCommand
from api.models import Product, Store, Price
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.utils import timezone
import decimal
import datetime

class Command(BaseCommand):
    help = 'Ürün fiyatlarını takip etmek için komut'

    def add_arguments(self, parser):
        parser.add_argument('--barcode', type=str, help='Fiyat eklenecek ürünün barkodu')
        parser.add_argument('--product-id', type=int, help='Fiyat eklenecek ürünün ID\'si')
        parser.add_argument('--product-name', type=str, help='Fiyat eklenecek ürünün adı')
        parser.add_argument('--store', type=str, required=True, help='Mağaza adı')
        parser.add_argument('--price', type=str, required=True, help='Ürün fiyatı (örn: 12.99)')
        parser.add_argument('--date', type=str, help='Fiyat tarihi (YYYY-MM-DD formatında, default: bugün)')
        parser.add_argument('--location', type=str, help='Lokasyon bilgisi (koordinat veya adres)')
        parser.add_argument('--user', type=str, help='Kaydeden kullanıcı adı (default: admin)')
        parser.add_argument('--create-if-not-exists', action='store_true', help='Ürün bulunamazsa yeni ürün oluştur')
        parser.add_argument('--force', action='store_true', help='Aynı gün için fiyat zaten varsa güncelle')

    def handle(self, *args, **options):
        barcode = options.get('barcode')
        product_id = options.get('product_id')
        product_name = options.get('product_name')
        store_name = options.get('store')
        price_value = options.get('price')
        date_str = options.get('date')
        location = options.get('location')
        username = options.get('user', 'admin')
        create_if_not_exists = options.get('create_if_not_exists', False)
        force_update = options.get('force', False)
        
        # Fiyatı decimal'e dönüştür
        try:
            price_value = decimal.Decimal(price_value)
        except decimal.InvalidOperation:
            self.stdout.write(self.style.ERROR(f"Geçersiz fiyat formatı: {price_value}. Örnek: 12.99"))
            return
        
        # Tarihi parse et
        if date_str:
            try:
                date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Geçersiz tarih formatı: {date_str}. Doğru format: YYYY-MM-DD"))
                return
        else:
            date = timezone.now().date()
        
        # Kullanıcıyı bul veya oluştur
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if username == 'admin':
                # Admin kullanıcısı yok, oluştur
                user = User.objects.create_superuser(username='admin', email='admin@example.com', password='admin')
                self.stdout.write(self.style.WARNING(f"Admin kullanıcısı otomatik oluşturuldu."))
            else:
                self.stdout.write(self.style.ERROR(f"Kullanıcı bulunamadı: {username}"))
                return
        
        # Mağazayı bul veya oluştur
        store, created = Store.objects.get_or_create(name=store_name)
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"Yeni mağaza oluşturuldu: {store_name}"))
            
        # Mağaza konum bilgilerini güncelle (eğer verilmişse)
        if location:
            # Konum formatını kontrol et - "lat,lon" formatında mı?
            if ',' in location and len(location.split(',')) == 2:
                try:
                    lat, lon = map(float, location.split(','))
                    store.latitude = lat
                    store.longitude = lon
                    store.save()
                    self.stdout.write(self.style.SUCCESS(f"Mağaza konum bilgileri güncellendi: {lat}, {lon}"))
                except ValueError:
                    # Konum sayısal değil, adres olarak kaydet
                    store.address = location
                    store.save()
                    self.stdout.write(self.style.SUCCESS(f"Mağaza adresi güncellendi: {location}"))
            else:
                # Konum bilgisi lat,lon formatında değil, adres olarak kaydet
                store.address = location
                store.save()
                self.stdout.write(self.style.SUCCESS(f"Mağaza adresi güncellendi: {location}"))
        
        # Ürünü bul
        product = None
        
        if barcode:
            try:
                product = Product.objects.get(barcode=barcode)
                self.stdout.write(self.style.SUCCESS(f"Ürün bulundu (barkod): {product.name}"))
            except Product.DoesNotExist:
                if not create_if_not_exists:
                    self.stdout.write(self.style.ERROR(f"Bu barkoda sahip ürün bulunamadı: {barcode}"))
                    return
        elif product_id:
            try:
                product = Product.objects.get(id=product_id)
                self.stdout.write(self.style.SUCCESS(f"Ürün bulundu (ID): {product.name}"))
            except Product.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Bu ID'ye sahip ürün bulunamadı: {product_id}"))
                return
        elif product_name:
            # İsme göre arama yaparken, tam eşleşme veya içeren şeklinde arama yapabiliriz
            products = Product.objects.filter(name__icontains=product_name)
            if products.count() > 1:
                self.stdout.write(self.style.WARNING(f"Birden fazla ürün bulundu. Lütfen daha spesifik olun:"))
                for i, p in enumerate(products[:5], 1):
                    self.stdout.write(f"{i}. {p.name} (ID: {p.id}, Barkod: {p.barcode})")
                if products.count() > 5:
                    self.stdout.write(f"... ve {products.count() - 5} ürün daha")
                return
            elif products.count() == 1:
                product = products.first()
                self.stdout.write(self.style.SUCCESS(f"Ürün bulundu (isim): {product.name}"))
            else:
                if not create_if_not_exists:
                    self.stdout.write(self.style.ERROR(f"Bu isme sahip ürün bulunamadı: {product_name}"))
                    return
        else:
            self.stdout.write(self.style.ERROR("Ürün belirtilmedi. --barcode, --product-id veya --product-name parametrelerinden birini kullanın."))
            return
        
        # Ürün bulunamadı ve create_if_not_exists aktif, yeni ürün oluştur
        if not product and create_if_not_exists:
            if not product_name:
                self.stdout.write(self.style.ERROR("Yeni ürün oluşturmak için ürün adı gereklidir (--product-name)."))
                return
                
            # Yeni ürün oluştur
            product = Product.objects.create(
                name=product_name,
                barcode=barcode,
                brand='',  # Boş bırak, daha sonra güncellenebilir
                category='Diğer'  # Varsayılan kategori
            )
            self.stdout.write(self.style.SUCCESS(f"Yeni ürün oluşturuldu: {product.name} (ID: {product.id})"))
        
        # Fiyat kaydı oluştur/güncelle
        if product:
            try:
                with transaction.atomic():
                    # Aynı gün, aynı mağaza ve aynı ürün için kayıt var mı?
                    existing_price = Price.objects.filter(
                        product=product,
                        store=store,
                        date=date
                    ).first()
                    
                    if existing_price:
                        if force_update:
                            # Mevcut kaydı güncelle
                            existing_price.price = price_value
                            existing_price.user = user
                            existing_price.save()
                            self.stdout.write(self.style.SUCCESS(f"Fiyat bilgisi güncellendi: {price_value} TL"))
                        else:
                            self.stdout.write(self.style.WARNING(
                                f"Bu ürün için bu tarihte zaten bir fiyat kaydı var: {existing_price.price} TL. "
                                f"Güncellemek için --force parametresini kullanın."
                            ))
                    else:
                        # Yeni fiyat kaydı oluştur
                        price_obj = Price.objects.create(
                            product=product,
                            store=store,
                            price=price_value,
                            user=user,
                            date=date
                        )
                        self.stdout.write(self.style.SUCCESS(f"Fiyat kaydı oluşturuldu: {price_value} TL"))
                        
                        # Fiyat geçmişi hakkında bilgi ver
                        past_prices = Price.objects.filter(product=product).order_by('-date')
                        if past_prices.count() > 1:
                            self.stdout.write("\nFiyat Geçmişi:")
                            for i, p in enumerate(past_prices[:5], 1):
                                self.stdout.write(f"{i}. {p.date}: {p.price} TL ({p.store.name})")
            
            except IntegrityError as e:
                self.stdout.write(self.style.ERROR(f"Veritabanı hatası: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Beklenmeyen hata: {e}"))
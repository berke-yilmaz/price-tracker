from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Product
from api.util import extract_visual_features, get_vector_index, remove_background
import os
import argparse
from PIL import Image
import time

class Command(BaseCommand):
    help = 'Bir görsele en benzer ürünleri bul'

    def add_arguments(self, parser):
        parser.add_argument('image_path', type=str, help='Aranacak görselin dosya yolu')
        parser.add_argument('--remove-bg', action='store_true', help='Arka planı kaldır')
        parser.add_argument('--top-k', type=int, default=5, help='Gösterilecek sonuç sayısı')
        parser.add_argument('--detail', action='store_true', help='Detaylı bilgileri göster')
        parser.add_argument('--threshold', type=float, default=0.0, help='Benzerlik eşiği (0-1 arası)')

    def handle(self, *args, **options):
        image_path = options['image_path']
        remove_bg = options['remove_bg']
        top_k = options['top_k']
        detail = options['detail']
        threshold = options['threshold']
        
        if not os.path.exists(image_path):
            self.stdout.write(self.style.ERROR(f"Dosya bulunamadı: {image_path}"))
            return
        
        # FAISS indeksini kontrol et
        try:
            vector_index = get_vector_index()
            self.stdout.write(self.style.SUCCESS(f"Indeks yüklendi ({vector_index.index.ntotal} ürün)"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Indeks hatası: {e}"))
            return
        
        # Görseli işle
        try:
            self.stdout.write("Görsel özellikler çıkarılıyor...")
            start_time = time.time()
            
            # Görseli yükle
            img = Image.open(image_path).convert('RGB')
            
            # Arka planı kaldır (isteğe bağlı)
            if remove_bg:
                self.stdout.write("Arka plan kaldırılıyor...")
                try:
                    img_processed = remove_background(img)
                    visual_features = extract_visual_features(img_processed, remove_bg=False)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Arka plan kaldırma hatası: {e}"))
                    visual_features = extract_visual_features(img, remove_bg=False)
            else:
                visual_features = extract_visual_features(img, remove_bg=False)
            
            process_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f"Görsel işlendi ({process_time:.2f} sn)"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Görsel işleme hatası: {e}"))
            return
        
        # Benzer ürünleri ara
        self.stdout.write("Benzer ürünler aranıyor...")
        search_start = time.time()
        results = vector_index.search(visual_features, k=top_k)
        search_time = time.time() - search_start
        
        # Sonuçları göster
        self.stdout.write(self.style.SUCCESS(f"Arama tamamlandı! ({search_time:.4f} sn)"))
        self.stdout.write("\nEn benzer ürünler:")
        
        for i, result in enumerate(results):
            product_id = result['product_id']
            distance = result['distance']
            similarity = 1.0 - min(distance / 100.0, 1.0)  # Normalize (0-1 arası)
            
            # Eşik değerini kontrol et
            if similarity < threshold:
                continue
                
            try:
                product = Product.objects.get(id=product_id)
                self.stdout.write(f"\n{i+1}. {product.name} ({product.brand})")
                self.stdout.write(f"   Benzerlik: {similarity:.4f} ({distance:.2f})")
                
                if detail:
                    self.stdout.write(f"   Kategori: {product.category}")
                    self.stdout.write(f"   Barkod: {product.barcode}")
                    self.stdout.write(f"   ID: {product.id}")
                    self.stdout.write(f"   URL: {product.image_url}")
                    
                    # Fiyat bilgisi varsa göster
                    prices = product.prices.all().order_by('price')[:3]
                    if prices:
                        self.stdout.write("   Fiyatlar:")
                        for price in prices:
                            self.stdout.write(f"     - {price.price} TL ({price.store.name})")
            except Product.DoesNotExist:
                self.stdout.write(f"{i+1}. Ürün bulunamadı (ID: {product_id})")
        
        if not results:
            self.stdout.write(self.style.WARNING("Benzer ürün bulunamadı!"))
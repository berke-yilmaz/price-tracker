from django.core.management.base import BaseCommand
import os
import urllib.request
import io
import time
from PIL import Image
from api.models import Product
from api.util import (
    extract_visual_features, 
    remove_background,
    save_processed_image,
    build_vector_index
)
import logging
import sys
from django.db.models import Q

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Mevcut ürün görsellerini işle (arka plan kaldırma ve özellik çıkarma)'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', type=str, default='processed_images', 
                            help='İşlenmiş görsellerin kaydedileceği dizin')
        parser.add_argument('--batch-size', type=int, default=20, 
                            help='Kaç ürün işledikten sonra raporlanacak')
        parser.add_argument('--limit', type=int, default=0, 
                            help='İşlenecek maksimum ürün sayısı (0=tümü)')
        parser.add_argument('--filter', type=str, choices=['none', 'missing', 'all'], default='missing',
                            help='none: Tüm ürünler, missing: Sadece eksik olanlar, all: Tümü')
        parser.add_argument('--category', type=str, default=None,
                            help='Sadece belirli bir kategorideki ürünleri işle')

    def _show_progress(self, current, total, prefix='', suffix='', length=50, fill='█'):
        """İlerleme çubuğu göster"""
        percent = int(100 * (current / float(total)))
        filled_length = int(length * current // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
        sys.stdout.flush()
        if current == total:
            sys.stdout.write('\n')

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        batch_size = options['batch_size']
        limit = options['limit']
        filter_option = options['filter']
        category = options['category']
        
        # Çıktı dizinini oluştur
        os.makedirs(output_dir, exist_ok=True)
        
        # Ürünleri filtrele
        if filter_option == 'missing':
            queryset = Product.objects.filter(Q(visual_embedding__isnull=True) & ~Q(image_url=''))
        elif filter_option == 'all':
            queryset = Product.objects.filter(~Q(image_url=''))
        else:  # 'none'
            queryset = Product.objects.all()
        
        # Kategori filtresi ekle
        if category:
            queryset = queryset.filter(category__icontains=category)
            
        # Limit uygula
        if limit > 0:
            queryset = queryset[:limit]
            
        total = queryset.count()
        
        self.stdout.write(self.style.SUCCESS(f"Toplam {total} ürün işlenecek"))
        
        # İstatistikler
        stats = {
            'processed': 0,
            'errors': 0,
            'backgrounds_removed': 0,
            'features_extracted': 0,
            'image_downloads': 0
        }
        
        # İşleme başla
        start_time = time.time()
        
        for idx, product in enumerate(queryset):
            try:
                # İlerleme göster
                self._show_progress(idx+1, total, prefix='İlerleme:', suffix=f'({idx+1}/{total})')
                
                # Görsel URL'si kontrol et
                img_url = product.image_url if product.image_url else product.image_front_url
                
                if not img_url:
                    continue
                
                # URL'den görüntü indir
                try:
                    req = urllib.request.Request(
                        img_url,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        img_data = response.read()
                        img = Image.open(io.BytesIO(img_data)).convert('RGB')
                        stats['image_downloads'] += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"\nGörüntü indirme hatası ({product.name}): {e}"))
                    stats['errors'] += 1
                    continue
                
                # Arka planı kaldır
                try:
                    img_processed = remove_background(img)
                    processed_path = save_processed_image(img_processed, product.id, output_dir)
                    stats['backgrounds_removed'] += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"\nArka plan kaldırma hatası ({product.name}): {e}"))
                    # Orijinal görüntüyle devam et
                    img_processed = io.BytesIO()
                    img.save(img_processed, format='PNG')
                    img_processed.seek(0)
                
                # Görsel özelliklerini çıkar
                try:
                    visual_features = extract_visual_features(img_processed, remove_bg=False)
                    
                    # Ürünü güncelle
                    product.visual_embedding = visual_features.tolist()
                    product.save()
                    stats['features_extracted'] += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"\nÖzellik çıkarma hatası ({product.name}): {e}"))
                    stats['errors'] += 1
                    continue
                
                # Başarılı işlem
                stats['processed'] += 1
                
                # Batch tamamlandığında ara rapor
                if stats['processed'] % batch_size == 0:
                    elapsed = time.time() - start_time
                    rate = stats['processed'] / elapsed if elapsed > 0 else 0
                    remaining = (total - stats['processed']) / rate if rate > 0 else 0
                    
                    self.stdout.write(f"\nİlerleme: {stats['processed']}/{total} ({rate:.1f} ürün/sn, tahmini kalan süre: {remaining/60:.1f} dk)")
                    self.stdout.write(f"İndirilen: {stats['image_downloads']}, Arka Plan Kaldırma: {stats['backgrounds_removed']}, Özellik Çıkarma: {stats['features_extracted']}, Hatalar: {stats['errors']}")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nBeklenmeyen hata ({product.name}): {e}"))
                stats['errors'] += 1
                continue
        
        # İşlemi tamamla ve FAISS indeksini yeniden oluştur
        elapsed = time.time() - start_time
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"İşlem tamamlandı ({elapsed/60:.1f} dk):"))
        self.stdout.write(f"✓ {stats['processed']} ürün başarıyla işlendi")
        self.stdout.write(f"✓ {stats['image_downloads']} görsel indirildi")
        self.stdout.write(f"✓ {stats['backgrounds_removed']} ürün için arka plan kaldırıldı")
        self.stdout.write(f"✓ {stats['features_extracted']} ürün için özellik vektörü çıkarıldı")
        self.stdout.write(f"✗ {stats['errors']} hata")
        
        # FAISS indeksini yeniden oluştur
        self.stdout.write("\nFAISS indeksi oluşturuluyor...")
        try:
            build_vector_index()
            self.stdout.write(self.style.SUCCESS("FAISS indeksi başarıyla oluşturuldu"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FAISS indeks hatası: {e}"))
#!/usr/bin/env python3
# api/management/commands/import_products.py
import os
# CUDA uyarılarını bastır
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np


import tensorflow as tf
import json
import pandas as pd
import numpy as np
import urllib.request
import io
import time
import sys
import gc
import torch
import re
from django.core.management.base import BaseCommand
from api.models import Product
from api.util import (
    extract_visual_features, 
    get_text_embedding, 
    remove_background, 
    save_processed_image,
    build_vector_index
)
import logging
tf.get_logger().setLevel(logging.ERROR)

from PIL import Image
from django.db import transaction
from django.db.models import Q


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("product_processing.log"),
        logging.StreamHandler()
    ]
)

class Command(BaseCommand):
    help = 'Dışarıdan JSON veya CSV dosyasından ürünleri içe aktar ve işle'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='İçe aktarılacak JSON veya CSV dosyasının yolu')
        parser.add_argument('--images-dir', type=str, help='Görsellerin bulunduğu dizin (varsa)')
        parser.add_argument('--batch-size', type=int, default=50, help='İşlenecek batch boyutu')
        parser.add_argument('--skip-existing', action='store_true', help='Mevcut ürünleri atla')
        parser.add_argument('--skip-images', action='store_true', help='Görsel işlemeyi atla')
        parser.add_argument('--skip-text', action='store_true', help='Metin embedding hesaplamasını atla')
        parser.add_argument('--process-background', action='store_true', help='Arka planları kaldır')
        parser.add_argument('--processed-dir', type=str, default='processed_images', help='İşlenmiş görsellerin kaydedileceği dizin')
        parser.add_argument('--limit', type=int, default=0, help='İşlenecek maksimum ürün sayısı (0=tümü)')
        parser.add_argument('--turkish-only', action='store_true', help='Sadece Türkçe ürünleri içe aktar')
        parser.add_argument('--require-visual', action='store_true', help='Görsel embedding olmadan ürünleri kaydetme')
        parser.add_argument('--clean-duplicates', action='store_true', help='Mükerrer ürünleri temizle')

    def _show_progress(self, current, total, prefix='', suffix='', length=50, fill='█'):
        """İlerleme çubuğu göster"""
        percent = int(100 * (current / float(total)))
        filled_length = int(length * current // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
        sys.stdout.flush()
        if current == total:
            sys.stdout.write('\n')
    
    def _is_turkish_text(self, text):
        """Metnin Türkçe olup olmadığını kontrol et"""
        if not text:
            return False
            
        # Türkçe karakterler
        turkish_chars = 'çğıöşüÇĞİÖŞÜ'
        
        # Türkçe karakterlerden biri varsa Türkçe olarak kabul et
        for char in turkish_chars:
            if char in text:
                return True
        
        # Türkçe olma olasılığı olan kelimeler
        turkish_common_words = ['ve', 'ile', 'veya', 'için', 'içerik', 'içindekiler', 'adet', 'kg', 'gram', 'litre', 'ml']
        
        # Metinden tüm alfasayısal olmayan karakterleri kaldır
        text_words = re.sub(r'[^\w\s]', ' ', text.lower()).split()
        
        # Yaygın Türkçe kelimelerden biri varsa Türkçe olarak kabul et
        for word in turkish_common_words:
            if word in text_words:
                return True
        
        # Türkçe olma olasılığını sorgulayan başka bir kriter
        non_turkish_chars = 'wxqWXQ'
        turkish_chars_count = sum(1 for c in text if c in turkish_chars)
        non_turkish_chars_count = sum(1 for c in text if c in non_turkish_chars)
        
        # Eğer metnin uzunluğu belirli bir eşiğin üzerindeyse ve Türkçe karakterler daha fazlaysa veya yabancı karakter yoksa
        if len(text) > 10 and (turkish_chars_count > non_turkish_chars_count or non_turkish_chars_count == 0):
            # Metnin %80'inden fazlası Latin alfabesindeyse
            latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
            if latin_chars / len(text) > 0.8:
                return True
        
        # Kategori kontrolü
        if 'Süt & Kahvaltı' in text or 'İçecek' in text or 'Atıştırmalık' in text or 'Temel Gıda' in text:
            return True
            
        return False
        
    def _format_barcode(self, barcode):
        """Barkodu doğru formata dönüştür"""
        if not barcode or pd.isna(barcode):
            return None
            
        # Barkodu string'e dönüştür
        barcode = str(barcode).strip()
        
        # Boş string ise None döndür
        if not barcode:
            return None
            
        # Sadece sayılardan oluşuyorsa ve makul uzunluktaysa geçerli bir barkod olarak kabul et
        if barcode.isdigit() and 8 <= len(barcode) <= 14:
            return barcode
            
        # Biçimlendirme hatalarını düzelt
        if barcode.startswith("'") and barcode.endswith("'"):
            barcode = barcode[1:-1]
            
        return barcode if barcode else None

    def handle(self, *args, **options):
        # CUDA uyarı mesajlarını bastır
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        
        # GPU belleğini temizle
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            self.stdout.write(self.style.SUCCESS("GPU belleği temizlendi"))
            
        file_path = options['file_path']
        images_dir = options.get('images_dir')
        batch_size = options['batch_size']
        skip_existing = options['skip_existing']
        skip_images = options['skip_images']
        skip_text = options['skip_text']
        process_background = options['process_background']
        processed_dir = options['processed_dir']
        limit = options['limit']
        turkish_only = options['turkish_only']
        require_visual = options['require_visual']
        clean_duplicates = options['clean_duplicates']
        
        # Dosyayı yükle (JSON veya CSV)
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # JSON'ı DataFrame'e dönüştür
                    df = pd.DataFrame(data)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                self.stdout.write(self.style.ERROR(f"Desteklenmeyen dosya formatı: {file_path}"))
                return
            
            # Başlamadan önce temizlik yap
            if clean_duplicates:
                self._clean_duplicates()
            
            # İlk temizlik: NaN değerleri dönüştür
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna('')
            
            # Türkçe olmayanları filtrele
            if turkish_only:
                initial_count = len(df)
                df['is_turkish'] = df['name'].apply(self._is_turkish_text)
                df = df[df['is_turkish']]
                filtered_count = initial_count - len(df)
                self.stdout.write(self.style.WARNING(f"{filtered_count} Türkçe olmayan ürün filtrelendi. Kalan: {len(df)}"))
            
            total = len(df)
            if limit > 0 and limit < total:
                df = df.head(limit)
                total = limit
                
            self.stdout.write(self.style.SUCCESS(f"Dosya yüklendi: {total} ürün işlenecek"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Dosya yükleme hatası: {e}"))
            return
        
        # İşlenmiş görseller için dizin oluştur
        if process_background and not skip_images:
            os.makedirs(processed_dir, exist_ok=True)
        
        # İstatistikler
        stats_data = {
            'total': total,
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'image_processed': 0,
            'text_embedded': 0,
            'backgrounds_removed': 0,
            'invalid_barcodes': 0,
            'no_visual_skipped': 0
        }
        
        # İşleme başla
        start_time = time.time()
        
        for idx, row in df.iterrows():
            try:
                # İlerleme göster
                if idx % 10 == 0:
                    self._show_progress(idx+1, total, prefix='İlerleme:', suffix=f'({idx+1}/{total})')
                
                # Barkodu al ve formatla
                barcode = self._format_barcode(row.get('barcode'))
                if not barcode:
                    stats_data['invalid_barcodes'] += 1
                
                # Türkçe kontrolü (turkish_only seçeneği işaretlenmemişse burada kontrol et)
                if not turkish_only and not self._is_turkish_text(row['name']):
                    stats_data['skipped'] += 1
                    continue
                
                # Mevcut ürünü kontrol et
                if skip_existing and barcode:
                    try:
                        Product.objects.get(barcode=barcode)
                        stats_data['skipped'] += 1
                        continue
                    except Product.DoesNotExist:
                        pass
                
                # Ürün verilerini hazırla
                product_data = {
                    'name': row['name'],
                    'barcode': barcode,
                    'brand': row.get('brand', ''),
                    'category': row.get('category', ''),
                    'image_url': row.get('image_url', ''),
                    'image_front_url': row.get('image_front_url', ''),
                    'weight': row.get('weight', ''),
                    'ingredients': row.get('ingredients', '')
                }
                
                # Boş değilse dönüştür
                for key in product_data:
                    if pd.isna(product_data[key]):
                        product_data[key] = ''
                
                # Boş marka alanını doldur (ismin ilk kelimesi genellikle markadır)
                if not product_data['brand'] and ' ' in product_data['name']:
                    product_data['brand'] = product_data['name'].split(' ')[0]
                
                # Görseli işle ve visual embedding oluştur
                visual_features = None
                if not skip_images:
                    # İlk olarak bellirtilen görseli kontrol et
                    image_path = row.get('image_path', None)
                    
                    # Eğer görselin tam yolu yoksa, ama images_dir belirtilmişse görseli bul
                    if not image_path and images_dir:
                        potential_paths = [
                            os.path.join(images_dir, f"{barcode}.jpg") if barcode else None,
                            os.path.join(images_dir, f"{row.get('id')}_image.jpg") if row.get('id') else None,
                            os.path.join(images_dir, f"{row.get('id')}_front.jpg") if row.get('id') else None,
                            os.path.join(images_dir, f"{row.get('id')}.jpg") if row.get('id') else None
                        ]
                        # None değerleri filtrele
                        potential_paths = [p for p in potential_paths if p]
                        
                        for path in potential_paths:
                            if os.path.exists(path):
                                image_path = path
                                break
                    
                    # Görseli işle
                    if image_path and os.path.exists(image_path):
                        try:
                            # Görseli yükle
                            img = Image.open(image_path).convert('RGB')
                            
                            # Arka planı kaldır (isteğe bağlı)
                            if process_background:
                                try:
                                    img_processed = remove_background(img)
                                    # İşlenmiş görseli kaydet
                                    processed_path = save_processed_image(img_processed, barcode or f"temp_{idx}", processed_dir)
                                    stats_data['backgrounds_removed'] += 1
                                    
                                    # Görsel özelliklerini çıkar
                                    visual_features = extract_visual_features(img_processed, remove_bg=False)
                                except Exception as e:
                                    self.stdout.write(self.style.WARNING(f"Arka plan kaldırma hatası ({product_data['name']}): {e}"))
                                    # Orijinal görselden devam et
                                    visual_features = extract_visual_features(img, remove_bg=False)
                            else:
                                # Normal görsel işleme
                                visual_features = extract_visual_features(img, remove_bg=False)
                            
                            stats_data['image_processed'] += 1
                            
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Görsel işleme hatası ({product_data['name']}): {e}"))
                    # URL'den indirmeyi dene
                    elif product_data['image_url'] or product_data['image_front_url']:
                        img_url = product_data['image_url'] if product_data['image_url'] else product_data['image_front_url']
                        try:
                            # URL'den görüntü indir
                            req = urllib.request.Request(
                                img_url,
                                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                            )
                            with urllib.request.urlopen(req, timeout=10) as response:
                                img_data = response.read()
                                img = io.BytesIO(img_data)
                                
                                # Arka planı kaldır (isteğe bağlı)
                                if process_background:
                                    try:
                                        img_processed = remove_background(img)
                                        # İşlenmiş görseli kaydet
                                        processed_path = save_processed_image(img_processed, barcode or f"temp_{idx}", processed_dir)
                                        stats_data['backgrounds_removed'] += 1
                                        
                                        # Görsel özelliklerini çıkar
                                        visual_features = extract_visual_features(img_processed, remove_bg=False)
                                    except Exception as e:
                                        self.stdout.write(self.style.WARNING(f"Arka plan kaldırma hatası ({product_data['name']}): {e}"))
                                        # Orijinal görselden devam et
                                        visual_features = extract_visual_features(img, remove_bg=False)
                                else:
                                    # Normal görsel işleme
                                    visual_features = extract_visual_features(img, remove_bg=False)
                                
                                stats_data['image_processed'] += 1
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"URL'den görsel indirme hatası ({product_data['name']}): {e}"))
                
                # Görsel embedding yoksa ve gerekiyorsa, ürünü atla
                if require_visual and visual_features is None:
                    stats_data['no_visual_skipped'] += 1
                    continue
                
                # Metin özelliklerini hesapla
                text_embedding = None
                if not skip_text:
                    try:
                        text_embedding = get_text_embedding(product_data['name'])
                        stats_data['text_embedded'] += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Metin gömme hatası ({product_data['name']}): {e}"))
                
                # Ürünü oluştur veya güncelle
                with transaction.atomic():
                    if barcode:
                        product, created = Product.objects.get_or_create(
                            barcode=barcode,
                            defaults=product_data
                        )
                        
                        if not created:
                            # Güncelle
                            for key, value in product_data.items():
                                setattr(product, key, value)
                    else:
                        # Barkod yoksa, aynı isimli ve markalı ürünü kontrol et
                        try:
                            product = Product.objects.get(
                                name=product_data['name'],
                                brand=product_data['brand']
                            )
                            # Ürünü güncelle
                            for key, value in product_data.items():
                                setattr(product, key, value)
                        except Product.DoesNotExist:
                            # Yeni ürün oluştur
                            product = Product(**product_data)
                    
                    # Embedding'leri ayarla
                    if visual_features is not None:
                        product.visual_embedding = visual_features.tolist()
                    
                    if text_embedding is not None:
                        product.text_embedding = text_embedding.tolist()
                    
                    # Kaydet
                    product.save()
                
                stats_data['processed'] += 1
                
                # Batch tamamlandığında ara rapor
                if stats_data['processed'] % batch_size == 0:
                    elapsed = time.time() - start_time
                    rate = stats_data['processed'] / elapsed if elapsed > 0 else 0
                    remaining = (stats_data['total'] - stats_data['processed']) / rate if rate > 0 else 0
                    
                    self.stdout.write(f"\nİlerleme: {stats_data['processed']}/{stats_data['total']} ({rate:.1f} ürün/sn, tahmini kalan süre: {remaining/60:.1f} dk)")
                    self.stdout.write(f"Görsel: {stats_data['image_processed']}, Metin: {stats_data['text_embedded']}, Arka plan: {stats_data['backgrounds_removed']}, Atlandı: {stats_data['skipped']}")
                    self.stdout.write(f"Geçersiz barkod: {stats_data['invalid_barcodes']}, Görseli olmadığı için atlanan: {stats_data['no_visual_skipped']}")
                    
                    # Bellek temizliği
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\nHata: {e}"))
                stats_data['errors'] += 1
                # Çok fazla hata varsa dur
                if stats_data['errors'] > 50:
                    self.stdout.write(self.style.ERROR("Çok fazla hata, işlem durduruluyor"))
                    break
                continue
        
        # İşlemi tamamla ve FAISS indeksini yeniden oluştur
        elapsed = time.time() - start_time
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"İşlem tamamlandı ({elapsed/60:.1f} dk):"))
        self.stdout.write(f"✓ {stats_data['processed']} ürün başarıyla işlendi")
        self.stdout.write(f"✓ {stats_data['image_processed']} ürün için görsel özellikleri hesaplandı")
        self.stdout.write(f"✓ {stats_data['text_embedded']} ürün için metin özellikleri hesaplandı")
        self.stdout.write(f"✓ {stats_data['backgrounds_removed']} ürün için arka plan kaldırıldı")
        self.stdout.write(f"- {stats_data['skipped']} ürün atlandı")
        self.stdout.write(f"- {stats_data['invalid_barcodes']} geçersiz barkod")
        self.stdout.write(f"- {stats_data['no_visual_skipped']} görseli olmadığı için atlanan ürün")
        self.stdout.write(f"✗ {stats_data['errors']} hata")
        
        # FAISS indeksini yeniden oluştur
        self.stdout.write("\nFAISS indeksi oluşturuluyor...")
        try:
            build_vector_index()
            self.stdout.write(self.style.SUCCESS("FAISS indeksi başarıyla oluşturuldu"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FAISS indeks hatası: {e}"))
        
        # Veritabanı durumu raporu
        self.stdout.write("\nVeritabanı durumu:")
        self.stdout.write(f"✓ Toplam ürün: {Product.objects.count()}")
        self.stdout.write(f"✓ Görsel embeddingi olan: {Product.objects.filter(visual_embedding__isnull=False).count()}")
        self.stdout.write(f"✓ Metin embeddingi olan: {Product.objects.filter(text_embedding__isnull=False).count()}")
        self.stdout.write(f"✓ Barkodu olan: {Product.objects.exclude(barcode='').exclude(barcode__isnull=True).count()}")
    
    def _clean_duplicates(self):
        """Mükerrer ürünleri temizle"""
        from django.db.models import Count
        
        self.stdout.write("Mükerrer ürünler temizleniyor...")
        
        # 1. Aynı barkodlu ürünleri bul
        duplicate_barcodes = Product.objects.exclude(barcode='').exclude(barcode__isnull=True).values('barcode').annotate(
            count=Count('barcode')).filter(count__gt=1).values_list('barcode', flat=True)
        
        self.stdout.write(f"{len(duplicate_barcodes)} adet mükerrer barkod bulundu")
        
        for barcode in duplicate_barcodes:
            duplicates = Product.objects.filter(barcode=barcode).order_by('-id')
            # En yeni ürünü koru, diğerlerini sil
            keep_product = duplicates.first()
            duplicates.exclude(id=keep_product.id).delete()
        
        # 2. Aynı isim ve markalı ürünleri bul
        duplicate_names = Product.objects.values('name', 'brand').annotate(
            count=Count('id')).filter(count__gt=1).values_list('name', 'brand')
        
        self.stdout.write(f"{len(duplicate_names)} adet mükerrer isim/marka bulundu")
        
        for name, brand in duplicate_names:
            duplicates = Product.objects.filter(name=name, brand=brand).order_by('-id')
            # En yeni ürünü koru, diğerlerini sil
            keep_product = duplicates.first()
            duplicates.exclude(id=keep_product.id).delete()
        
        self.stdout.write(self.style.SUCCESS("Temizlik tamamlandı"))
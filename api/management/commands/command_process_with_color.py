# api/management/commands/process_with_color.py - FIXED VERSION
import os
import time
import urllib.request
import io
from PIL import Image, ImageStat
import numpy as np
from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.utils import timezone
from api.models import Product, ProcessingJob, ColorAnalysisStats
from api.util import (
    categorize_by_color,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    build_enhanced_vector_index
)

try:
    from api.util_enhanced import (
        enhanced_product_preprocessing,
        extract_visual_features_enhanced,
        process_product_image_enhanced,
        EnhancedProductDetector
    )
    ENHANCED_DETECTION_AVAILABLE = True
    print("✅ Enhanced detection available")
except ImportError:
    ENHANCED_DETECTION_AVAILABLE = False
    print("⚠️ Enhanced detection not available, using standard methods")

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("product_processing.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process products with enhanced color categorization and robust background removal'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=10, 
                            help='Kaç ürün aynı anda işlenecek')
        parser.add_argument('--color-only', action='store_true',
                            help='Sadece renk analizi yap')
        parser.add_argument('--features-only', action='store_true',
                            help='Sadece görsel özellik çıkarma yap')
        parser.add_argument('--limit', type=int, default=0,
                            help='İşlenecek maksimum ürün sayısı (0=tümü)')
        parser.add_argument('--force-reprocess', action='store_true',
                            help='Zaten işlenmiş ürünleri tekrar işle')
        parser.add_argument('--color-filter', type=str,
                            help='Sadece belirli renk kategorisindeki ürünleri işle')
        parser.add_argument('--gpu', action='store_true', default=True,
                            help='GPU kullan (varsayılan: True)')
        parser.add_argument('--skip-bg-removal', action='store_true',
                            help='Arka plan kaldırmayı atla (sorunlu durumlarda)')
        parser.add_argument('--clean-first', action='store_true',
                            help='Önce tüm ürünleri sil')
        parser.add_argument('--use-enhanced', action='store_true', default=True,
                        help='Use enhanced detection (default: True)')
        parser.add_argument('--preprocessing-method', type=str, 
                        choices=['auto', 'crop_only', 'bg_removal', 'full'],
                        default='auto',
                        help='Enhanced preprocessing method')
        parser.add_argument('--test-detection', action='store_true',
                        help='Test enhanced detection on a few products')

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        color_only = options['color_only']
        features_only = options['features_only']
        limit = options['limit']
        force_reprocess = options['force_reprocess']
        color_filter = options['color_filter']
        use_gpu = options['gpu']
        skip_bg_removal = options['skip_bg_removal']
        clean_first = options['clean_first']
        
        self.use_enhanced = options.get('use_enhanced', True) and ENHANCED_DETECTION_AVAILABLE
        self.preprocessing_method = options.get('preprocessing_method', 'auto')
        test_detection = options.get('test_detection', False)
    
        if test_detection:
            self._test_enhanced_detection()
            return
    
        if self.use_enhanced:
            self.stdout.write(self.style.SUCCESS('🤖 Enhanced detection enabled'))
        else:
            self.stdout.write(self.style.WARNING('📷 Using standard detection'))

        self.stdout.write(self.style.SUCCESS('🎨 Geliştirilmiş Renk-Aware Ürün İşleme Başlıyor...'))
        
        # Clean database first if requested
        if clean_first:
            self._clean_database()
        
        # Base query
        query = Product.objects.all()
        
        # Filter logic
        if not force_reprocess:
            if color_only:
                query = query.filter(color_category='unknown')
            elif features_only:
                query = query.filter(visual_embedding__isnull=True)
            else:
                query = query.filter(
                    models.Q(color_category='unknown') |
                    models.Q(visual_embedding__isnull=True) |
                    models.Q(color_aware_text_embedding__isnull=True)
                )
        
        # Color filter
        if color_filter:
            if color_filter != 'unknown':
                query = query.filter(color_category=color_filter)
        
        # Only products with images
        query = query.exclude(image_url='').exclude(image_url__isnull=True)
        
        # Apply limit
        if limit > 0:
            query = query[:limit]
        
        total_products = query.count()
        self.stdout.write(f"📊 Toplam işlenecek ürün: {total_products}")
        
        if total_products == 0:
            self.stdout.write(self.style.WARNING("İşlenecek ürün bulunamadı!"))
            return
        
        # Initialize statistics
        stats = {
            'processed': 0,
            'color_analyzed': 0,
            'features_extracted': 0,
            'errors': 0,
            'skipped': 0,
            'bg_removed_successfully': 0,
            'bg_removal_failed': 0,
            'color_distribution': {},
        }
        
        start_time = time.time()
        
        # Process in batches
        for i in range(0, total_products, batch_size):
            batch = query[i:i + batch_size]
            self.stdout.write(f"\n🔄 Batch {i//batch_size + 1}: {len(batch)} ürün işleniyor...")
            
            self._process_batch_sequential(batch, color_only, features_only, use_gpu, skip_bg_removal, stats)
            
            # Progress report
            elapsed = time.time() - start_time
            rate = stats['processed'] / elapsed if elapsed > 0 else 0
            remaining = (total_products - stats['processed']) / rate if rate > 0 else 0
            
            self.stdout.write(
                f"✅ İşlenen: {stats['processed']}/{total_products} "
                f"({rate:.1f} ürün/sn, kalan: {remaining/60:.1f} dk)"
            )
            
            # Show background removal stats
            total_bg_attempts = stats['bg_removed_successfully'] + stats['bg_removal_failed']
            if total_bg_attempts > 0:
                success_rate = stats['bg_removed_successfully'] / total_bg_attempts * 100
                self.stdout.write(f"🖼️  Arka plan: {stats['bg_removed_successfully']} başarılı, {stats['bg_removal_failed']} başarısız ({success_rate:.1f}% başarı)")
            
            # Show color distribution
            if stats['color_distribution']:
                color_summary = ", ".join([
                    f"{color}: {count}" 
                    for color, count in sorted(stats['color_distribution'].items())
                ])
                self.stdout.write(f"🎨 Renk dağılımı: {color_summary}")
        
        # Final results
        self._show_final_results(stats, start_time)
        
        # Rebuild vector index
        if not color_only and stats['features_extracted'] > 0:
            self.stdout.write("\n🔄 FAISS indeksi yeniden oluşturuluyor...")
            try:
                build_enhanced_vector_index()
                self.stdout.write(self.style.SUCCESS("✅ FAISS indeksi güncellendi"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ FAISS indeks hatası: {e}"))
        
        # Update statistics
        self._update_color_stats()

    def _clean_database(self):
        """Clean all products from database"""
        self.stdout.write(self.style.WARNING("🗑️  Veritabanındaki tüm ürünler siliniyor..."))
        
        try:
            deleted_count = Product.objects.all().delete()[0]
            self.stdout.write(self.style.SUCCESS(f"✅ {deleted_count} ürün silindi"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Silme hatası: {e}"))

    def _process_batch_sequential(self, batch, color_only, features_only, use_gpu, skip_bg_removal, stats):
        """Process batch sequentially with improved error handling"""
        for product in batch:
            try:
                self._process_single_product(product, color_only, features_only, use_gpu, skip_bg_removal, stats)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Ürün işleme hatası ({product.name}): {e}"))
                stats['errors'] += 1

    def _process_single_product(self, product, color_only, features_only, use_gpu, skip_bg_removal, stats):
        """Enhanced processing with intelligent detection - FIXED VERSION"""
        use_enhanced = getattr(self, 'use_enhanced', True) and ENHANCED_DETECTION_AVAILABLE
        preprocessing_method = getattr(self, 'preprocessing_method', 'auto')
        
        with transaction.atomic():
            try:
                # Download image
                image = self._download_image(product)
                if not image:
                    stats['errors'] += 1
                    return
                
                changes_made = False
                detection_info = {}
                
                # Enhanced processing pipeline
                if use_enhanced and not color_only:
                    try:
                        # Use complete enhanced processing
                        processing_results, success = process_product_image_enhanced(
                            image,
                            product_id=str(product.id),
                            save_processed=True,
                            processed_dir='processed_enhanced'
                        )
                        
                        if success:
                            # Extract results from enhanced processing
                            preprocessing_info = processing_results['preprocessing_info']
                            color_info = processing_results['color_info']
                            visual_features = processing_results['visual_features']
                            
                            # Update product with enhanced results
                            product.color_category = color_info['category']
                            product.color_confidence = color_info['confidence']
                            if color_info.get('colors'):
                                product.dominant_colors = color_info['colors']
                            
                            if visual_features:
                                product.visual_embedding = visual_features
                                stats['features_extracted'] += 1
                            
                            # Generate color-aware text embedding
                            try:
                                text_embedding = get_color_aware_text_embedding(
                                    product.name, 
                                    color_info['category']
                                )
                                product.color_aware_text_embedding = text_embedding.tolist()
                            except Exception as e:
                                logger.warning(f"Text embedding failed for {product.name}: {e}")
                            
                            # Track detection information
                            detection_result = preprocessing_info.get('detection_result')
                            if detection_result:
                                detection_info = {
                                    'method': detection_result.get('detection_method'),
                                    'confidence': detection_result.get('confidence', 0),
                                    'bbox': detection_result.get('bbox')
                                }
                                stats['bg_removed_successfully'] += 1
                            else:
                                stats['bg_removal_failed'] += 1
                            
                            stats['color_analyzed'] += 1
                            changes_made = True
                            
                            self.stdout.write(f"🤖 Enhanced: {product.name}: {color_info['category']} "
                                            f"({color_info['confidence']:.2f}) "
                                            f"[{detection_result.get('detection_method', 'no-detection') if detection_result else 'no-detection'}]")
                        else:
                            raise Exception(f"Enhanced processing failed: {processing_results.get('error')}")
                            
                    except Exception as e:
                        logger.warning(f"Enhanced processing failed for {product.name}: {e}")
                        use_enhanced = False  # Fall back to standard processing
                
                # Standard processing (fallback or if enhanced disabled)
                if not use_enhanced:
                    # Step 1: Color Analysis
                    if not features_only and (product.color_category == 'unknown' or not product.has_color_analysis):
                        color_info = categorize_by_color(image)
                        
                        product.color_category = color_info['category']
                        product.color_confidence = color_info['confidence']
                        if color_info['colors']:
                            product.dominant_colors = color_info['colors']
                        
                        stats['color_analyzed'] += 1
                        color = color_info['category']
                        stats['color_distribution'][color] = stats['color_distribution'].get(color, 0) + 1
                        changes_made = True
                        
                        self.stdout.write(f"🎨 Standard: {product.name}: {color} (confidence: {color_info['confidence']:.2f})")
                    
                    # Step 2: Visual Features
                    if not color_only and not product.has_visual_features:
                        try:
                            if skip_bg_removal:
                                feature_image = image
                                self.stdout.write(f"🖼️  {product.name}: Background removal skipped")
                            else:
                                # Use enhanced preprocessing even in standard mode
                                if ENHANCED_DETECTION_AVAILABLE:
                                    feature_image, preprocessing_info = enhanced_product_preprocessing(
                                        image, method='crop_only'
                                    )
                                    detection_result = preprocessing_info.get('detection_result')
                                    if detection_result:
                                        stats['bg_removed_successfully'] += 1
                                        self.stdout.write(f"🖼️  {product.name}: Enhanced crop applied")
                                    else:
                                        stats['bg_removal_failed'] += 1
                                        self.stdout.write(f"⚠️  {product.name}: Standard crop applied")
                                else:
                                    feature_image = image
                            
                            # Extract visual features
                            visual_features = extract_visual_features_resnet(
                                feature_image, 
                                remove_bg=False,
                                use_gpu=use_gpu,
                                color_category=getattr(product, 'color_category', 'unknown')
                            )
                            
                            product.visual_embedding = visual_features.tolist()
                            stats['features_extracted'] += 1
                            changes_made = True
                            
                            self.stdout.write(f"🧠 {product.name}: Visual features extracted ({len(visual_features)} dims)")
                            
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"⚠️ Feature extraction error ({product.name}): {e}"))
                    
                    # Step 3: Color-Aware Text Embedding
                    if not color_only and not features_only:
                        try:
                            color_category = getattr(product, 'color_category', 'unknown')
                            text_embedding = get_color_aware_text_embedding(
                                product.name, 
                                color_category
                            )
                            product.color_aware_text_embedding = text_embedding.tolist()
                            changes_made = True
                            
                            self.stdout.write(f"📝 {product.name}: Color-aware text embedding created")
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"⚠️ Text embedding error ({product.name}): {e}"))
                
                # Update product status
                if changes_made:
                    product.processing_status = 'completed'
                    product.processed_at = timezone.now()
                    product.save()
                    stats['processed'] += 1
                else:
                    stats['skipped'] += 1
                
                # Create processing job AFTER all processing is done
                try:
                    processing_job = ProcessingJob.objects.create(
                        product=product,
                        job_type='enhanced_processing' if use_enhanced else 'standard_processing',
                        status='completed',
                        started_at=timezone.now(),
                        completed_at=timezone.now(),
                        result_data={
                            'color_category': str(product.color_category),
                            'color_confidence': float(product.color_confidence) if product.color_confidence else 0.0,
                            'has_visual_features': bool(product.has_visual_features),
                            'has_color_analysis': bool(product.has_color_analysis),
                            'background_removed': bool(not skip_bg_removal and stats.get('bg_removed_successfully', 0) > 0),
                            'enhanced_processing': bool(use_enhanced),
                            'detection_info': detection_info
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to create processing job for {product.name}: {e}")
                
            except Exception as e:
                # Handle errors
                product.processing_status = 'failed'
                product.processing_error = str(e)
                product.save()
                
                stats['errors'] += 1
                raise
   
    def _download_image(self, product):
        """Download image from URL with better error handling"""
        try:
            img_url = product.image_url or product.image_front_url
            if not img_url:
                return None
            
            req = urllib.request.Request(
                img_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                
                # Validate image data
                if len(img_data) < 1000:  # Too small, likely invalid
                    return None
                
                image = Image.open(io.BytesIO(img_data)).convert('RGB')
                
                # Validate image dimensions
                width, height = image.size
                if width < 50 or height < 50:  # Too small
                    return None
                
                return image
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ Görsel indirme hatası ({product.name}): {e}"))
            return None

    def _show_final_results(self, stats, start_time):
        """Show final processing results with background removal stats"""
        elapsed = time.time() - start_time
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🎉 İşleme Tamamlandı!"))
        self.stdout.write(f"⏱️  Toplam süre: {elapsed/60:.1f} dakika")
        self.stdout.write(f"✅ İşlenen ürün: {stats['processed']}")
        self.stdout.write(f"🎨 Renk analizi: {stats['color_analyzed']}")
        self.stdout.write(f"🧠 Görsel özellik: {stats['features_extracted']}")
        
        # Background removal stats
        total_bg_attempts = stats['bg_removed_successfully'] + stats['bg_removal_failed']
        if total_bg_attempts > 0:
            success_rate = stats['bg_removed_successfully'] / total_bg_attempts * 100
            self.stdout.write(f"🖼️  Arka plan kaldırma: {stats['bg_removed_successfully']}/{total_bg_attempts} başarılı ({success_rate:.1f}%)")
        
        self.stdout.write(f"⏭️  Atlanan: {stats['skipped']}")
        self.stdout.write(f"❌ Hata: {stats['errors']}")
        
        if stats['processed'] > 0:
            avg_time = elapsed / stats['processed']
            self.stdout.write(f"📊 Ortalama işleme süresi: {avg_time:.2f} saniye/ürün")
        
        # Show color distribution
        if stats['color_distribution']:
            self.stdout.write("\n🎨 Renk Kategorisi Dağılımı:")
            for color, count in sorted(stats['color_distribution'].items(), key=lambda x: x[1], reverse=True):
                color_name = dict(Product.COLOR_CHOICES).get(color, color)
                percentage = (count / sum(stats['color_distribution'].values())) * 100
                self.stdout.write(f"   {color_name}: {count} ürün ({percentage:.1f}%)")

    def _update_color_stats(self):
        """Update color analysis statistics"""
        try:
            from django.db.models import Count, Avg
            
            # Get statistics per color category
            color_stats = Product.objects.values('color_category').annotate(
                count=Count('id'),
                avg_confidence=Avg('color_confidence')
            ).exclude(color_category='unknown')
            
            for stat in color_stats:
                color = stat['color_category']
                
                # Calculate success rate (products with confidence > 0.5)
                total_color_products = Product.objects.filter(color_category=color).count()
                successful_products = Product.objects.filter(
                    color_category=color,
                    color_confidence__gt=0.5
                ).count()
                success_rate = successful_products / total_color_products if total_color_products > 0 else 0
                
                # Update or create stats
                ColorAnalysisStats.objects.update_or_create(
                    color_category=color,
                    defaults={
                        'total_products': stat['count'],
                        'avg_confidence': stat['avg_confidence'] or 0.0,
                        'success_rate': success_rate,
                        'last_updated': timezone.now()
                    }
                )
            
            self.stdout.write(self.style.SUCCESS("📊 Renk istatistikleri güncellendi"))
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ İstatistik güncelleme hatası: {e}"))

    def _test_enhanced_detection(self):
        """Test enhanced detection on sample products"""
        if not ENHANCED_DETECTION_AVAILABLE:
            self.stdout.write(self.style.ERROR("Enhanced detection not available"))
            return
        
        self.stdout.write("🧪 Testing enhanced detection...")
        
        # Get sample products
        test_products = Product.objects.exclude(image_url='').exclude(image_url__isnull=True)[:3]
        
        detector = EnhancedProductDetector()
        
        for i, product in enumerate(test_products, 1):
            self.stdout.write(f"\n{i}. Testing: {product.name}")
            
            try:
                # Download image
                image = self._download_image(product)
                if not image:
                    continue
                
                self.stdout.write(f"   Original size: {image.size}")
                
                # Test detection
                detection_result = detector.detect_product(image)
                
                if detection_result:
                    method = detection_result.get('detection_method', 'unknown')
                    confidence = detection_result.get('confidence', 0)
                    bbox = detection_result.get('bbox', [])
                    
                    self.stdout.write(f"   ✅ Detected using {method} (confidence: {confidence:.3f})")
                    
                    if bbox:
                        x1, y1, x2, y2 = bbox
                        width = x2 - x1
                        height = y2 - y1
                        area_ratio = (width * height) / (image.width * image.height)
                        self.stdout.write(f"   📐 Product area: {width}x{height} ({area_ratio:.1%} of image)")
                else:
                    self.stdout.write(f"   ❌ No product detected")
                
                # Test enhanced preprocessing
                processed_image, processing_info = enhanced_product_preprocessing(image, method='auto')
                self.stdout.write(f"   🔧 Processing steps: {processing_info['steps_applied']}")
                self.stdout.write(f"   📏 Final size: {processed_image.size}")
                
            except Exception as e:
                self.stdout.write(f"   💥 Test failed: {e}")
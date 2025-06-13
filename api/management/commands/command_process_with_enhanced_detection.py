# api/management/commands/process_with_enhanced_detection.py
import os
import time
import urllib.request
import io
import logging
from PIL import Image
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from api import models
from api.models import Product, ProcessingJob
from api.util_enhanced import (
    enhanced_product_preprocessing,
    extract_visual_features_enhanced,
    process_product_image_enhanced,
    EnhancedProductDetector
)
from api.util import (
    categorize_by_color,
    get_color_aware_text_embedding,
    build_enhanced_vector_index
)
import numpy as np


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process products with enhanced detection and intelligent cropping'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=10, 
                            help='Number of products to process at once')
        parser.add_argument('--limit', type=int, default=0,
                            help='Maximum products to process (0=all)')
        parser.add_argument('--force-reprocess', action='store_true',
                            help='Reprocess already processed products')
        parser.add_argument('--preprocessing-method', type=str, 
                            choices=['auto', 'crop_only', 'bg_removal', 'full'],
                            default='auto',
                            help='Preprocessing method to use')
        parser.add_argument('--gpu', action='store_true', default=True,
                            help='Use GPU for processing')
        parser.add_argument('--processed-dir', type=str, default='processed_enhanced',
                            help='Directory to save processed images')
        parser.add_argument('--save-processed', action='store_true',
                            help='Save processed images to disk')
        parser.add_argument('--test-detection', action='store_true',
                            help='Test detection on a few products first')

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        limit = options['limit']
        force_reprocess = options['force_reprocess']
        preprocessing_method = options['preprocessing_method']
        use_gpu = options['gpu']
        processed_dir = options['processed_dir']
        save_processed = options['save_processed']
        test_detection = options['test_detection']
        
        self.stdout.write(self.style.SUCCESS('🚀 Enhanced Product Detection Processing'))
        self.stdout.write(f"Preprocessing method: {preprocessing_method}")
        self.stdout.write(f"GPU enabled: {use_gpu}")
        
        # Create processed directory if saving images
        if save_processed:
            os.makedirs(processed_dir, exist_ok=True)
            self.stdout.write(f"Processed images will be saved to: {processed_dir}")
        
        # Test detection first if requested
        if test_detection:
            self._test_detection()
            return
        
        # Build query
        query = Product.objects.exclude(image_url='').exclude(image_url__isnull=True)
        
        if not force_reprocess:
            # Only process products without visual embeddings or with failed processing
            query = query.filter(
                models.Q(visual_embedding__isnull=True) |
                models.Q(processing_status='failed') |
                models.Q(processing_status='pending')
            )
        
        if limit > 0:
            query = query[:limit]
        
        total_products = query.count()
        self.stdout.write(f"📊 Products to process: {total_products}")
        
        if total_products == 0:
            self.stdout.write(self.style.WARNING("No products to process!"))
            return
        
        # Initialize statistics
        stats = {
            'processed': 0,
            'errors': 0,
            'detection_success': 0,
            'detection_failed': 0,
            'color_analyzed': 0,
            'features_extracted': 0,
            'preprocessing_methods': {},
            'detection_methods': {},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        start_time = time.time()
        
        # Process in batches
        for i in range(0, total_products, batch_size):
            batch = query[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            self.stdout.write(f"\n🔄 Processing batch {batch_num}: products {i+1}-{min(i+batch_size, total_products)}")
            
            for product in batch:
                try:
                    self._process_single_product_enhanced(
                        product, preprocessing_method, use_gpu, 
                        save_processed, processed_dir, stats
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error processing {product.name}: {e}"))
                    stats['errors'] += 1
            
            # Show progress
            elapsed = time.time() - start_time
            rate = stats['processed'] / elapsed if elapsed > 0 else 0
            remaining = (total_products - (i + len(batch))) / rate if rate > 0 else 0
            
            self.stdout.write(f"✅ Progress: {i + len(batch)}/{total_products}")
            self.stdout.write(f"📈 Rate: {rate:.1f} products/sec, ETA: {remaining/60:.1f} min")
            self._show_interim_stats(stats)
        
        # Final results
        self._show_final_results(stats, start_time)
        
        # Rebuild index if features were extracted
        if stats['features_extracted'] > 0:
            self.stdout.write("\n🔄 Rebuilding enhanced vector index...")
            try:
                build_enhanced_vector_index()
                self.stdout.write(self.style.SUCCESS("✅ Enhanced vector index rebuilt"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Index rebuild failed: {e}"))

    def _test_detection(self):
        """Test detection on a few products"""
        self.stdout.write("🧪 Testing enhanced detection on sample products...")
        
        # Get 5 products with images for testing
        test_products = Product.objects.exclude(image_url='').exclude(image_url__isnull=True)[:5]
        
        detector = EnhancedProductDetector()
        
        for i, product in enumerate(test_products, 1):
            self.stdout.write(f"\n{i}. Testing: {product.name}")
            
            try:
                # Download image
                image = self._download_image(product.image_url, product.name)
                if not image:
                    continue
                
                self.stdout.write(f"   Original size: {image.size}")
                
                # Test detection
                detection_result = detector.detect_product(image)
                
                if detection_result:
                    method = detection_result.get('detection_method', 'unknown')
                    confidence = detection_result.get('confidence', 0)
                    bbox = detection_result.get('bbox', [])
                    
                    self.stdout.write(f"   ✅ Detection successful!")
                    self.stdout.write(f"   Method: {method}")
                    self.stdout.write(f"   Confidence: {confidence:.3f}")
                    self.stdout.write(f"   Bounding box: {bbox}")
                    
                    if len(bbox) == 4:
                        x1, y1, x2, y2 = bbox
                        width = x2 - x1
                        height = y2 - y1
                        area_ratio = (width * height) / (image.width * image.height)
                        self.stdout.write(f"   Product area: {width}x{height} ({area_ratio:.2%} of image)")
                else:
                    self.stdout.write(f"   ❌ No product detected")
                
                # Test preprocessing
                processed_image, processing_info = enhanced_product_preprocessing(
                    image, method='auto'
                )
                
                self.stdout.write(f"   Preprocessing steps: {processing_info['steps_applied']}")
                self.stdout.write(f"   Final size: {processed_image.size}")
                
            except Exception as e:
                self.stdout.write(f"   ❌ Test failed: {e}")

    def _process_single_product_enhanced(self, product, preprocessing_method, use_gpu, 
                                       save_processed, processed_dir, stats):
        """Process a single product with enhanced detection"""
        
        with transaction.atomic():
            # Create processing job
            job = ProcessingJob.objects.create(
                product=product,
                job_type='enhanced_processing',
                status='running',
                started_at=timezone.now()
            )
            
            try:
                # Download image
                image = self._download_image(product.image_url, product.name)
                if not image:
                    raise Exception("Image download failed")
                
                # Enhanced processing pipeline
                processing_results, success = process_product_image_enhanced(
                    image,
                    product_id=str(product.id),
                    save_processed=save_processed,
                    processed_dir=processed_dir
                )
                
                if not success:
                    raise Exception(f"Enhanced processing failed: {processing_results.get('error', 'Unknown error')}")
                
                # Extract results
                preprocessing_info = processing_results['preprocessing_info']
                color_info = processing_results['color_info']
                visual_features = processing_results['visual_features']
                
                # Update statistics
                detection_result = preprocessing_info.get('detection_result')
                if detection_result:
                    stats['detection_success'] += 1
                    method = detection_result.get('detection_method', 'unknown')
                    stats['detection_methods'][method] = stats['detection_methods'].get(method, 0) + 1
                    
                    confidence = detection_result.get('confidence', 0)
                    if confidence > 0.7:
                        stats['confidence_distribution']['high'] += 1
                    elif confidence > 0.4:
                        stats['confidence_distribution']['medium'] += 1
                    else:
                        stats['confidence_distribution']['low'] += 1
                else:
                    stats['detection_failed'] += 1
                
                # Track preprocessing methods used
                for step in preprocessing_info['steps_applied']:
                    stats['preprocessing_methods'][step] = stats['preprocessing_methods'].get(step, 0) + 1
                
                # Update product with results
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
                
                # Update processing status
                product.processing_status = 'completed'
                product.processed_at = timezone.now()
                product.save()
                
                # Update job
                job.status = 'completed'
                job.completed_at = timezone.now()
                job.result_data = {
                    'preprocessing_info': preprocessing_info,
                    'color_category': color_info['category'],
                    'color_confidence': color_info['confidence'],
                    'detection_successful': detection_result is not None,
                    'detection_method': detection_result.get('detection_method') if detection_result else None,
                    'detection_confidence': detection_result.get('confidence') if detection_result else 0
                }
                job.save()
                
                stats['processed'] += 1
                stats['color_analyzed'] += 1
                
                # Log success
                detection_info = ""
                if detection_result:
                    method = detection_result.get('detection_method', 'unknown')
                    confidence = detection_result.get('confidence', 0)
                    detection_info = f" [{method}: {confidence:.2f}]"
                
                self.stdout.write(
                    f"✅ {product.name}: {color_info['category']} "
                    f"({color_info['confidence']:.2f}){detection_info}"
                )
                
            except Exception as e:
                # Handle errors
                product.processing_status = 'failed'
                product.processing_error = str(e)
                product.save()
                
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = timezone.now()
                job.save()
                
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"❌ {product.name}: {e}"))

    def _download_image(self, url, product_name):
        """Download image with error handling"""
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                
                if len(img_data) < 1000:
                    return None
                
                image = Image.open(io.BytesIO(img_data)).convert('RGB')
                
                if image.size[0] < 50 or image.size[1] < 50:
                    return None
                
                return image
                
        except Exception as e:
            logger.error(f"Image download failed for {product_name}: {e}")
            return None

    def _show_interim_stats(self, stats):
        """Show interim statistics"""
        detection_success_rate = 0
        if stats['detection_success'] + stats['detection_failed'] > 0:
            detection_success_rate = stats['detection_success'] / (stats['detection_success'] + stats['detection_failed']) * 100
        
        self.stdout.write(f"🎯 Detection success rate: {detection_success_rate:.1f}%")
        self.stdout.write(f"🎨 Color analyzed: {stats['color_analyzed']}")
        self.stdout.write(f"🧠 Features extracted: {stats['features_extracted']}")
        self.stdout.write(f"❌ Errors: {stats['errors']}")

    def _show_final_results(self, stats, start_time):
        """Show final processing results"""
        elapsed = time.time() - start_time
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🎉 Enhanced Processing Complete!"))
        self.stdout.write("="*60)
        
        self.stdout.write(f"⏱️  Total time: {elapsed/60:.1f} minutes")
        self.stdout.write(f"✅ Successfully processed: {stats['processed']}")
        self.stdout.write(f"❌ Errors: {stats['errors']}")
        
        # Detection statistics
        total_attempts = stats['detection_success'] + stats['detection_failed']
        if total_attempts > 0:
            success_rate = stats['detection_success'] / total_attempts * 100
            self.stdout.write(f"\n🎯 Product Detection Results:")
            self.stdout.write(f"   Success rate: {success_rate:.1f}% ({stats['detection_success']}/{total_attempts})")
            
            if stats['detection_methods']:
                self.stdout.write("   Detection methods used:")
                for method, count in sorted(stats['detection_methods'].items(), key=lambda x: x[1], reverse=True):
                    self.stdout.write(f"     {method}: {count}")
            
            # Confidence distribution
            conf_total = sum(stats['confidence_distribution'].values())
            if conf_total > 0:
                self.stdout.write("   Confidence distribution:")
                for level, count in stats['confidence_distribution'].items():
                    percentage = count / conf_total * 100
                    self.stdout.write(f"     {level}: {count} ({percentage:.1f}%)")
        
        # Preprocessing statistics
        if stats['preprocessing_methods']:
            self.stdout.write(f"\n🔧 Preprocessing Steps Applied:")
            for step, count in sorted(stats['preprocessing_methods'].items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"   {step}: {count}")
        
        # Processing statistics
        self.stdout.write(f"\n📊 Processing Results:")
        self.stdout.write(f"   Color analyzed: {stats['color_analyzed']}")
        self.stdout.write(f"   Visual features extracted: {stats['features_extracted']}")
        
        if stats['processed'] > 0:
            avg_time = elapsed / stats['processed']
            self.stdout.write(f"   Average time per product: {avg_time:.1f} seconds")
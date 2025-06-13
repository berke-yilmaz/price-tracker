
import numpy as np


# SIMPLE APPROACH - Add after imports
def simple_product_focus(image):
    """Focus on center area where product usually is"""
    try:
        from PIL import Image, ImageEnhance
        
        # Ensure RGB
        if image.mode != 'RGB':
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert('RGB')
        
        # Focus on center 75% of image
        width, height = image.size
        crop_size = min(width, height) * 0.75
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        
        focused = image.crop((int(left), int(top), int(right), int(bottom)))
        
        # Resize to consistent size
        focused = focused.resize((384, 384), Image.Resampling.LANCZOS)
        
        # Light enhancement
        enhancer = ImageEnhance.Contrast(focused)
        enhanced = enhancer.enhance(1.2)
        
        return enhanced
        
    except Exception as e:
        print(f"Simple focus failed: {e}")
        return image

# Override the complex functions
import api.util as util_module

# Replace the complex background removal with simple focus
original_bg_removal = getattr(util_module, 'smart_background_removal', None)
def simple_bg_replacement(image):
    try:
        processed = simple_product_focus(image)
        # Convert to BytesIO for compatibility
        import io
        result_io = io.BytesIO()
        processed.save(result_io, format='PNG')
        result_io.seek(0)
        return result_io, True
    except Exception as e:
        print(f"Simple processing failed: {e}")
        # Return original
        original_io = io.BytesIO()
        image.save(original_io, format='PNG')
        original_io.seek(0)
        return original_io, False

util_module.smart_background_removal = simple_bg_replacement

# Also override feature extraction to use simple preprocessing
original_extract = getattr(util_module, 'extract_visual_features_resnet', None)
def simple_feature_extraction(image, remove_bg=True, use_gpu=True, color_category=None):
    try:
        # Apply simple focus instead of background removal
        if remove_bg:
            image = simple_product_focus(image)
        
        # Use original extraction with processed image
        if original_extract:
            return original_extract(image, remove_bg=False, use_gpu=use_gpu, color_category=color_category)
        else:
            # Fallback
            import numpy as np
            return np.zeros(2048, dtype=np.float32)
            
    except Exception as e:
        print(f"Simple feature extraction failed: {e}")
        import numpy as np
        return np.zeros(2048, dtype=np.float32)

util_module.extract_visual_features_resnet = simple_feature_extraction



def _process_single_product(self, row, process_background, require_visual, 
                               processed_dir, use_gpu, skip_existing, stats):
        """Process a single product with full pipeline including color categorization"""
        
        # Prepare product data
        barcode = self._format_barcode(row.get('barcode'))
        product_data = {
            'name': row['name'],
            'barcode': barcode,
            'brand': row.get('brand', ''),
            'category': row.get('category', ''),
            'weight': row.get('weight', ''),
            'ingredients': row.get('ingredients', ''),
            'image_url': row.get('image_url', ''),
            'image_front_url': row.get('image_front_url', ''),
        }
        
        # Clean empty values
        for key in product_data:
            if pd.isna(product_data[key]):
                product_data[key] = ''
        
        # Fill empty brand from product name
        if not product_data['brand'] and ' ' in product_data['name']:
            product_data['brand'] = product_data['name'].split(' ')[0]
        
        process_msg = f"🔄 Processing: {product_data['name']}"
        self.log_and_print(process_msg, 'INFO')
        self.logger.debug(f'PRODUCT_START: {product_data}')
        
        # Check if product already exists
        if skip_existing and barcode:
            try:
                existing_product = Product.objects.get(barcode=barcode)
                skip_msg = f"⏭️  Skipping existing product: {existing_product.name}"
                self.log_and_print(skip_msg, 'INFO')
                self.logger.info(f'PRODUCT_SKIP: Existing product with barcode {barcode}')
                stats['existing_skipped'] += 1
                return
            except Product.DoesNotExist:
                pass
        
        # Download and process image
        image_url = product_data['image_url'] or product_data['image_front_url']
        if not image_url:
            warning_msg = f"⚠️  No image URL for {product_data['name']}"
            self.log_and_print(warning_msg, 'WARNING', 'WARNING')
            self.logger.warning(f'PRODUCT_NO_IMAGE: {product_data["name"]}')
            if require_visual:
                stats['skipped'] += 1
                return
            # Continue without image processing
            image = None
        else:
            self.logger.debug(f'IMAGE_DOWNLOAD_START: {image_url}')
            image = self._download_image(image_url, product_data['name'])
            if image is None:
                self.logger.error(f'IMAGE_DOWNLOAD_FAILED: {image_url}')
                if require_visual:
                    stats['skipped'] += 1
                    return
            else:
                stats['images_downloaded'] += 1
                self.logger.debug(f'IMAGE_DOWNLOAD_SUCCESS: {image_url}')
        
        # Initialize processing job
        processing_job = None
        
        try:
            # STEP 1: COLOR ANALYSIS (always use original image)
            if image:
                try:
                    self.logger.debug('COLOR_ANALYSIS_START')
                    color_info = categorize_by_color(image)
                    product_data.update({
                        'color_category': color_info['category'],
                        'color_confidence': color_info['confidence'],
                        'dominant_colors': color_info.get('colors', [])
                    })
                    stats['color_analyzed'] += 1
                    
                    # Track color distribution
                    color = color_info['category']
                    stats['color_distribution'][color] = stats['color_distribution'].get(color, 0) + 1
                    
                    # Track confidence distribution
                    confidence = color_info['confidence']
                    if confidence >= 0.7:
                        stats['confidence_distribution']['high'] += 1
                    elif confidence >= 0.4:
                        stats['confidence_distribution']['medium'] += 1
                    else:
                        stats['confidence_distribution']['low'] += 1
                    
                    color_msg = f"🎨 Color: {color} (confidence: {confidence:.2f})"
                    self.log_and_print(color_msg, 'DEBUG')
                    self.logger.info(f'COLOR_ANALYSIS_SUCCESS: {color} confidence={confidence:.3f}')
                    
                except Exception as e:
                    error_msg = f"⚠️  Color analysis failed: {e}"
                    self.log_and_print(error_msg, 'WARNING', 'WARNING')
                    self.logger.error(f'COLOR_ANALYSIS_FAILED: {str(e)}')
                    product_data.update({
                        'color_category': 'unknown',
                        'color_confidence': 0.0,
                        'dominant_colors': []
                    })
            else:
                product_data.update({
                    'color_category': 'unknown',
                    'color_confidence': 0.0,
                    'dominant_colors': []
                })
                self.logger.info('COLOR_ANALYSIS_SKIP: No image available')
            
            # STEP 2: SMART BACKGROUND REMOVAL (if requested)
            processed_image = image
            if image and process_background:
                try:
                    self.logger.debug('BACKGROUND_REMOVAL_START')
                    processed_image_io, bg_success = smart_background_removal(image)
                    if bg_success:
                        stats['backgrounds_removed'] += 1
                        processed_image = Image.open(processed_image_io)
                        
                        # Save processed image
                        save_path = save_processed_image(
                            processed_image_io, 
                            barcode or f"product_{idx}", 
                            processed_dir
                        )
                        if save_path:
                            save_msg = f"💾 Saved: {os.path.basename(save_path)}"
                            self.log_and_print(save_msg, 'DEBUG')
                            self.logger.info(f'BACKGROUND_REMOVAL_SUCCESS: Saved to {save_path}')
                    else:
                        stats['background_removal_failed'] += 1
                        processed_image = image
                        warning_msg = f"⚠️  Background removal too aggressive, using original"
                        self.log_and_print(warning_msg, 'WARNING')
                        self.logger.warning('BACKGROUND_REMOVAL_FAILED: Too aggressive, using original')
                except Exception as e:
                    error_msg = f"⚠️  Background removal failed: {e}"
                    self.log_and_print(error_msg, 'WARNING', 'WARNING')
                    self.logger.error(f'BACKGROUND_REMOVAL_ERROR: {str(e)}')
                    stats['background_removal_failed'] += 1
                    processed_image = image
            
            # STEP 3: VISUAL FEATURE EXTRACTION (ResNet50)
            if processed_image:
                try:
                    self.logger.debug('VISUAL_FEATURES_START')
                    visual_features = extract_visual_features_resnet(
                        processed_image, 
                        remove_bg=False,  # Already processed
                        use_gpu=use_gpu,
                        color_category=product_data.get('color_category', 'unknown')
                    )
                    product_data['visual_embedding'] = visual_features.tolist()
                    stats['visual_features_extracted'] += 1
                    
                    features_msg = f"🧠 Visual features: {len(visual_features)} dimensions"
                    self.log_and_print(features_msg, 'DEBUG')
                    self.logger.info(f'VISUAL_FEATURES_SUCCESS: Extracted {len(visual_features)} dimensions')
                    
                except Exception as e:
                    error_msg = f"⚠️  Visual feature extraction failed: {e}"
                    self.log_and_print(error_msg, 'WARNING', 'WARNING')
                    self.logger.error(f'VISUAL_FEATURES_FAILED: {str(e)}')
                    if require_visual:
                        stats['skipped'] += 1
                        return
            
            # STEP 4: COLOR-AWARE TEXT EMBEDDING
            try:
                self.logger.debug('TEXT_EMBEDDING_START')
                color_category = product_data.get('color_category', 'unknown')
                text_embedding = get_color_aware_text_embedding(product_data['name'], color_category)
                product_data['color_aware_text_embedding'] = text_embedding.tolist()
                stats['text_embeddings_created'] += 1
                
                text_msg = f"📝 Color-aware text embedding created"
                self.log_and_print(text_msg, 'DEBUG')
                self.logger.info(f'TEXT_EMBEDDING_SUCCESS: Color-aware embedding for {color_category}')
                
            except Exception as e:
                error_msg = f"⚠️  Text embedding failed: {e}"
                self.log_and_print(error_msg, 'WARNING', 'WARNING')
                self.logger.error(f'TEXT_EMBEDDING_FAILED: {str(e)}')
            
            # STEP 5: SAVE TO DATABASE
            with transaction.atomic():
                self.logger.debug('DATABASE_SAVE_START')
                
                # Check for existing product (by barcode or name+brand)
                existing_product = None
                if barcode:
                    try:
                        existing_product = Product.objects.get(barcode=barcode)
                    except Product.DoesNotExist:
                        pass
                
                if existing_product:
                    # Update existing product
                    for key, value in product_data.items():
                        setattr(existing_product, key, value)
                    existing_product.processing_status = 'completed'
                    existing_product.processed_at = timezone.now()
                    existing_product.save()
                    product = existing_product
                    
                    update_msg = f"🔄 Updated existing product"
                    self.log_and_print(update_msg, 'INFO')
                    self.logger.info(f'DATABASE_UPDATE: Updated existing product ID {existing_product.id}')
                else:
                    # Create new product
                    product_data.update({
                        'processing_status': 'completed',
                        'processed_at': timezone.now()
                    })
                    product = Product.objects.create(**product_data)
                    
                    create_msg = f"✨ Created new product"
                    self.log_and_print(create_msg, 'INFO')
                    self.logger.info(f'DATABASE_CREATE: Created new product ID {product.id}')
                
                # Create processing job record
                processing_job = ProcessingJob.objects.create(
                    product=product,
                    job_type=job_type,
                    status='completed',
                    started_at=timezone.now(),
                    completed_at=timezone.now(),
                    result_data={
                        'color_category': str(product.color_category),
                        'color_confidence': float(product.color_confidence) if product.color_confidence else 0.0,  # ← FIX HERE
                        'has_visual_features': bool(product.has_visual_features),
                        'has_color_analysis': bool(product.has_color_analysis),
                        'background_removed': bool(process_background and stats.get('backgrounds_removed', 0) > 0),
                        'enhanced_processing': bool(use_enhanced),
                    }
                )
                stats['processing_jobs_created'] += 1
                
                stats['processed'] += 1
                success_msg = f"✅ Saved: {product.name} (ID: {product.id})"
                self.log_and_print(success_msg, 'INFO')
                self.logger.info(f'PRODUCT_COMPLETE: Successfully processed {product.name} (ID: {product.id})')
                
        except Exception as e:
            error_msg = f"❌ Database save failed: {e}"
            self.log_and_print(error_msg, 'ERROR', 'ERROR')
            self.logger.error(f'DATABASE_SAVE_FAILED: {str(e)}')
            
            # Update processing job status if it was created
            if processing_job:
                processing_job.status = 'failed'
                processing_job.error_message = str(e)
                processing_job.completed_at = timezone.now()
                processing_job.save()
                self.logger.error(f'PROCESSING_JOB_FAILED: Updated job status for {processing_job.id}')
            
            stats['errors'] += 1# api/management/commands/import_products_enhanced.py
import os
import time
import urllib.request
import io
import pandas as pd
from PIL import Image, ImageStat
import numpy as np
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.utils import timezone
from api.models import Product, ProcessingJob
from api.util import (
    categorize_by_color,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    smart_background_removal,
    save_processed_image,
    build_enhanced_vector_index
)

class Command(BaseCommand):
    help = 'Enhanced product import with integrated color categorization and processing'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = None
        self.log_file_path = None

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='CSV or JSON file path')
        parser.add_argument('--batch-size', type=int, default=15, help='Batch size for processing')
        parser.add_argument('--process-background', action='store_true', help='Apply smart background removal')
        parser.add_argument('--clean-duplicates', action='store_true', help='Clean duplicate products before import')
        parser.add_argument('--require-visual', action='store_true', help='Only save products with visual features')
        parser.add_argument('--processed-dir', type=str, default='processed_images', help='Directory for processed images')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of products (0=all)')
        parser.add_argument('--gpu', action='store_true', default=True, help='Use GPU for processing')
        parser.add_argument('--turkish-only', action='store_true', help='Only import Turkish products')
        parser.add_argument('--skip-existing', action='store_true', help='Skip products that already exist')
        parser.add_argument('--rebuild-index', action='store_true', default=True, help='Rebuild FAISS index after import')
        parser.add_argument('--log-dir', type=str, default='logs', help='Directory for log files')
        parser.add_argument('--use-enhanced', action='store_true', default=True, help='Use enhanced detection')
        parser.add_argument('--save-processed', action='store_true', help='Save processed images to disk')

    def setup_logging(self, log_dir):
        """Setup comprehensive logging with timestamped files"""
        # Create logs directory
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate timestamp for log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(log_dir, f'import_enhanced_{timestamp}.log')
        
        # Setup logger
        self.logger = logging.getLogger('import_enhanced')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler with detailed formatting
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Detailed formatter for file
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Simple formatter for console
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        return self.log_file_path

    def log_and_print(self, message, level='INFO', style=None):
        """Log message and print to console with optional styling"""
        # Log to file
        if self.logger:
            getattr(self.logger, level.lower())(message)
        
        # Print to console with styling
        if style:
            self.stdout.write(getattr(self.style, style.upper())(message))
        else:
            self.stdout.write(message)

    def handle(self, *args, **options):
        import pandas as pd
        
        # Setup logging first
        log_dir = options.get('log_dir', 'logs')
        log_file = self.setup_logging(log_dir)
        
        file_path = options['file_path']
        batch_size = options['batch_size']
        process_background = options['process_background']
        clean_duplicates = options['clean_duplicates']
        require_visual = options['require_visual']
        processed_dir = options['processed_dir']
        limit = options['limit']
        use_gpu = options['gpu']
        turkish_only = options['turkish_only']
        skip_existing = options['skip_existing']
        rebuild_index = options['rebuild_index']
        use_enhanced = options.get('use_enhanced', True)
        save_processed = options.get('save_processed', False)
        # Log startup information
        self.log_and_print('🚀 Enhanced Product Import with Integrated Color Processing', 'INFO', 'SUCCESS')
        self.log_and_print(f'📝 Log file: {log_file}', 'INFO')
        self.log_and_print(f'📁 Input file: {file_path}', 'INFO')
        
        # Log configuration
        config_info = [
            f'Batch size: {batch_size}',
            f'Process background: {process_background}',
            f'Clean duplicates: {clean_duplicates}',
            f'Require visual: {require_visual}',
            f'Processed dir: {processed_dir}',
            f'GPU enabled: {use_gpu}',
            f'Turkish only: {turkish_only}',
            f'Skip existing: {skip_existing}',
            f'Rebuild index: {rebuild_index}',
            f'Limit: {limit if limit > 0 else "No limit"}'
            f'Use enhanced: {use_enhanced}',
            f'Save processed: {save_processed}',
        ]
        
        for config in config_info:
            self.logger.info(f'CONFIG: {config}')
        
        # Clean duplicates first if requested
        if clean_duplicates:
            self.log_and_print('🧹 Starting duplicate cleanup...', 'INFO')
            self._clean_duplicates()
        
        # Load CSV/JSON
        try:
            self.log_and_print(f'📊 Loading data from {file_path}...', 'INFO')
            
            if file_path.endswith('.json'):
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                self.logger.info('File format: JSON')
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
                self.logger.info('File format: CSV')
            else:
                error_msg = f"❌ Unsupported file format: {file_path}"
                self.log_and_print(error_msg, 'ERROR', 'ERROR')
                return
            
            # Clean NaN values
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna('')
            
            self.logger.info(f'Loaded {len(df)} rows with columns: {list(df.columns)}')
            
            # Filter Turkish products if requested
            if turkish_only:
                initial_count = len(df)
                df['is_turkish'] = df['name'].apply(self._is_turkish_text)
                df = df[df['is_turkish']]
                filtered_count = initial_count - len(df)
                filter_msg = f"Filtered {filtered_count} non-Turkish products. Remaining: {len(df)}"
                self.log_and_print(filter_msg, 'INFO', 'WARNING')
            
            total = len(df)
            if limit > 0 and limit < total:
                df = df.head(limit)
                total = limit
                self.logger.info(f'Applied limit: processing {total} products')
                
            self.log_and_print(f"📊 Ready to process: {total} products", 'INFO')
            
        except Exception as e:
            error_msg = f"❌ File loading error: {e}"
            self.log_and_print(error_msg, 'ERROR', 'ERROR')
            return
        
        # Create processed images directory
        if process_background:
            os.makedirs(processed_dir, exist_ok=True)
            self.log_and_print(f"📁 Created directory: {processed_dir}", 'INFO')
        
        # Initialize comprehensive statistics
        stats = {
            'total': total,
            'processed': 0,
            'skipped': 0,
            'existing_skipped': 0,
            'errors': 0,
            'images_downloaded': 0,
            'backgrounds_removed': 0,
            'background_removal_failed': 0,
            'color_analyzed': 0,
            'visual_features_extracted': 0,
            'text_embeddings_created': 0,
            'processing_jobs_created': 0,
            'color_distribution': {},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        # Log initial stats
        self.logger.info('STATS_INIT: Starting with empty statistics')
        
        start_time = time.time()
        self.logger.info(f'PROCESS_START: Beginning batch processing at {datetime.now()}')
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i + batch_size]
            batch_num = i//batch_size + 1
            batch_msg = f"🔄 Processing batch {batch_num}: products {i+1}-{min(i+batch_size, total)}"
            self.log_and_print(f"\n{batch_msg}", 'INFO')
                        
            batch_start_time = time.time()
            self._process_batch(batch, process_background, require_visual, processed_dir, 
                            use_gpu, skip_existing, stats, use_enhanced, save_processed)
            batch_elapsed = time.time() - batch_start_time
            
            # Log batch completion
            self.logger.info(f'BATCH_COMPLETE: Batch {batch_num} completed in {batch_elapsed:.1f}s')
            
            # Progress report
            elapsed = time.time() - start_time
            rate = stats['processed'] / elapsed if elapsed > 0 else 0
            remaining_products = total - (i + len(batch))
            remaining_time = remaining_products / rate if rate > 0 else 0
            
            progress_msg = f"✅ Batch complete. Progress: {i + len(batch)}/{total}"
            rate_msg = f"📈 Rate: {rate:.1f} products/sec, ETA: {remaining_time/60:.1f} min"
            
            self.log_and_print(progress_msg, 'INFO')
            self.log_and_print(rate_msg, 'INFO')
            
            # Log detailed progress stats
            self.logger.info(f'PROGRESS: {stats["processed"]}/{total} processed, {stats["errors"]} errors')
            
            # Show current stats
            if process_background:
                bg_attempts = stats['backgrounds_removed'] + stats['background_removal_failed']
                bg_success_rate = (stats['backgrounds_removed'] / bg_attempts * 100) if bg_attempts > 0 else 0
                bg_msg = f"🖼️  Background removal: {stats['backgrounds_removed']} success, {stats['background_removal_failed']} failed ({bg_success_rate:.1f}% success)"
                self.log_and_print(bg_msg, 'INFO')
            
            stats_msg = [
                f"🎨 Colors analyzed: {stats['color_analyzed']}",
                f"🧠 Visual features: {stats['visual_features_extracted']}",
                f"📝 Text embeddings: {stats['text_embeddings_created']}"
            ]
            
            for msg in stats_msg:
                self.log_and_print(msg, 'INFO')
        
        # Final results and cleanup
        self.logger.info('PROCESS_END: Batch processing completed')
        self._show_final_results(stats, start_time, processed_dir)
        
        # Rebuild FAISS index if requested
        if rebuild_index and stats['visual_features_extracted'] > 0:
            self._rebuild_index()
        
        # Final log message
        total_time = time.time() - start_time
        self.log_and_print(f'\n🎉 Import completed successfully in {total_time/60:.1f} minutes!', 'INFO', 'SUCCESS')
        self.log_and_print(f'📝 Full log saved to: {log_file}', 'INFO', 'SUCCESS')

    def _process_batch(self, batch, process_background, require_visual, processed_dir, 
                    use_gpu, skip_existing, stats, use_enhanced, save_processed):
        """Process a batch of products with integrated color processing"""
        for idx, row in batch.iterrows():
            try:
                self._process_single_product(row, process_background, require_visual, 
                                        processed_dir, use_gpu, skip_existing, stats,
                                        use_enhanced, save_processed)  # Add the new params
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Product processing error: {e}"))
                stats['errors'] += 1

    def _process_single_product(self, row, process_background, require_visual, 
                        processed_dir, use_gpu, skip_existing, stats,
                        use_enhanced, save_processed, color_only=False): 
        """Process a single product with full pipeline including color categorization"""
        
        # Prepare product data
        barcode = self._format_barcode(row.get('barcode'))
        product_data = {
            'name': row['name'],
            'barcode': barcode,
            'brand': row.get('brand', ''),
            'category': row.get('category', ''),
            'weight': row.get('weight', ''),
            'ingredients': row.get('ingredients', ''),
            'image_url': row.get('image_url', ''),
            'image_front_url': row.get('image_front_url', ''),
        }
        
        # Clean empty values
        for key in product_data:
            if pd.isna(product_data[key]):
                product_data[key] = ''
        
        # Fill empty brand from product name
        if not product_data['brand'] and ' ' in product_data['name']:
            product_data['brand'] = product_data['name'].split(' ')[0]
        
        self.stdout.write(f"🔄 Processing: {product_data['name']}")
        
        # Check if product already exists
        if skip_existing and barcode:
            try:
                existing_product = Product.objects.get(barcode=barcode)
                self.stdout.write(f"⏭️  Skipping existing product: {existing_product.name}")
                stats['existing_skipped'] += 1
                return
            except Product.DoesNotExist:
                pass
        
        # Download and process image
        image_url = product_data['image_url'] or product_data['image_front_url']
        if not image_url:
            self.stdout.write(f"⚠️  No image URL for {product_data['name']}")
            if require_visual:
                stats['skipped'] += 1
                return
            # Continue without image processing
            image = None
        else:
            image = self._download_image(image_url, product_data['name'])
            if image is None:
                if require_visual:
                    stats['skipped'] += 1
                    return
            else:
                stats['images_downloaded'] += 1
        
        # Initialize processing job
        processing_job = None
        
        try:
            # STEP 1: COLOR ANALYSIS (always use original image)
            if image:
                try:
                    color_info = categorize_by_color(image)
                    product_data.update({
                        'color_category': color_info['category'],
                        'color_confidence': color_info['confidence'],
                        'dominant_colors': color_info.get('colors', [])
                    })
                    stats['color_analyzed'] += 1
                    
                    # Track color distribution
                    color = color_info['category']
                    stats['color_distribution'][color] = stats['color_distribution'].get(color, 0) + 1
                    
                    # Track confidence distribution
                    confidence = color_info['confidence']
                    if confidence >= 0.7:
                        stats['confidence_distribution']['high'] += 1
                    elif confidence >= 0.4:
                        stats['confidence_distribution']['medium'] += 1
                    else:
                        stats['confidence_distribution']['low'] += 1
                    
                    self.stdout.write(f"🎨 Color: {color} (confidence: {confidence:.2f})")
                except Exception as e:
                    self.stdout.write(f"⚠️  Color analysis failed: {e}")
                    product_data.update({
                        'color_category': 'unknown',
                        'color_confidence': 0.0,
                        'dominant_colors': []
                    })
            else:
                product_data.update({
                    'color_category': 'unknown',
                    'color_confidence': 0.0,
                    'dominant_colors': []
                })
            
            # Early exit if only color analysis is requested
            if color_only:
                self.stdout.write(f"🎯 Color-only mode: skipping further processing")
                # Save basic product data with color info
                # ... (continue to database save step)
            
            # ENHANCED PROCESSING PIPELINE
            elif use_enhanced and image:
                try:
                    self.stdout.write(f"🚀 Starting enhanced processing pipeline...")
                    
                    # Use complete enhanced processing
                    processing_results, success = process_product_image_enhanced(
                        image,
                        product_id=barcode or f"temp_{hash(product_data['name'])}",
                        save_processed=save_processed,
                        processed_dir=processed_dir if save_processed else None
                    )
                    
                    if success:
                        self.stdout.write(f"✨ Enhanced processing completed successfully")
                        
                        # Update product data with enhanced results
                        if 'visual_features' in processing_results:
                            product_data['visual_embedding'] = processing_results['visual_features'].tolist()
                            stats['visual_features_extracted'] += 1
                            self.stdout.write(f"🧠 Enhanced visual features: {len(processing_results['visual_features'])} dimensions")
                        
                        if 'background_removed' in processing_results and processing_results['background_removed']:
                            stats['backgrounds_removed'] += 1
                            self.stdout.write(f"🖼️  Background successfully removed")
                        
                        if 'segmentation_mask' in processing_results:
                            stats['segmentation_created'] = stats.get('segmentation_created', 0) + 1
                            self.stdout.write(f"🎭 Segmentation mask created")
                        
                        if 'quality_score' in processing_results:
                            product_data['image_quality_score'] = processing_results['quality_score']
                            self.stdout.write(f"📊 Image quality score: {processing_results['quality_score']:.2f}")
                        
                        # Enhanced processing includes its own feature extraction
                        processed_image = processing_results.get('processed_image', image)
                        
                    else:
                        self.stdout.write(f"⚠️  Enhanced processing failed, falling back to standard pipeline")
                        # Fall back to standard processing
                        processed_image = image
                        
                except Exception as e:
                    self.stdout.write(f"❌ Enhanced processing error: {e}")
                    stats['errors'] += 1
                    processed_image = image
            
            # STANDARD PROCESSING PIPELINE (fallback or when enhanced is disabled)
            else:
                processed_image = image
                
                # STEP 2: SMART BACKGROUND REMOVAL (if requested)
                if image and process_background:
                    try:
                        processed_image_io, bg_success = smart_background_removal(image)
                        if bg_success:
                            stats['backgrounds_removed'] += 1
                            processed_image = Image.open(processed_image_io)
                            
                            # Save processed image
                            if save_processed:
                                save_path = save_processed_image(
                                    processed_image_io, 
                                    barcode or f"product_{hash(product_data['name'])}", 
                                    processed_dir
                                )
                                if save_path:
                                    self.stdout.write(f"💾 Saved: {os.path.basename(save_path)}")
                        else:
                            stats['background_removal_failed'] += 1
                            processed_image = image
                            self.stdout.write(f"⚠️  Background removal too aggressive, using original")
                    except Exception as e:
                        self.stdout.write(f"⚠️  Background removal failed: {e}")
                        stats['background_removal_failed'] += 1
                        processed_image = image
                
                # STEP 3: VISUAL FEATURE EXTRACTION (ResNet50)
                if processed_image and not color_only:
                    try:
                        visual_features = extract_visual_features_resnet(
                            processed_image, 
                            remove_bg=False,  # Already processed
                            use_gpu=use_gpu,
                            color_category=product_data.get('color_category', 'unknown')
                        )
                        product_data['visual_embedding'] = visual_features.tolist()
                        stats['visual_features_extracted'] += 1
                        self.stdout.write(f"🧠 Visual features: {len(visual_features)} dimensions")
                    except Exception as e:
                        self.stdout.write(f"⚠️  Visual feature extraction failed: {e}")
                        if require_visual:
                            stats['skipped'] += 1
                            return
            
            # STEP 4: COLOR-AWARE TEXT EMBEDDING (unless color-only mode)
            if not color_only:
                try:
                    color_category = product_data.get('color_category', 'unknown')
                    text_embedding = get_color_aware_text_embedding(product_data['name'], color_category)
                    product_data['color_aware_text_embedding'] = text_embedding.tolist()
                    stats['text_embeddings_created'] += 1
                    self.stdout.write(f"📝 Color-aware text embedding created")
                except Exception as e:
                    self.stdout.write(f"⚠️  Text embedding failed: {e}")
            
            # STEP 5: SAVE TO DATABASE
            with transaction.atomic():
                # Check for existing product (by barcode or name+brand)
                existing_product = None
                if barcode:
                    try:
                        existing_product = Product.objects.get(barcode=barcode)
                    except Product.DoesNotExist:
                        pass
                
                if existing_product:
                    # Update existing product
                    for key, value in product_data.items():
                        setattr(existing_product, key, value)
                    existing_product.processing_status = 'completed'
                    existing_product.processed_at = timezone.now()
                    existing_product.save()
                    product = existing_product
                    self.stdout.write(f"🔄 Updated existing product")
                else:
                    # Create new product
                    product_data.update({
                        'processing_status': 'completed',
                        'processed_at': timezone.now()
                    })
                    product = Product.objects.create(**product_data)
                    self.stdout.write(f"✨ Created new product")
                
                # Create processing job record
                job_type = 'color_analysis' if color_only else ('enhanced_processing' if use_enhanced else 'standard_processing')
                processing_job = ProcessingJob.objects.create(
                    product=product,
                    job_type=job_type,
                    status='completed',
                    started_at=timezone.now(),
                    completed_at=timezone.now(),
                    result_data={
                        'color_category': str(product.color_category),
                        'color_confidence': float(product.color_confidence) if product.color_confidence else 0.0,  # ← FIX HERE
                        'has_visual_features': bool(product.has_visual_features),
                        'has_color_analysis': bool(product.has_color_analysis),
                        'background_removed': bool(process_background and stats.get('backgrounds_removed', 0) > 0),
                        'enhanced_processing': bool(use_enhanced),
                    }
                )
                stats['processing_jobs_created'] += 1
                
                stats['processed'] += 1
                self.stdout.write(f"✅ Saved: {product.name} (ID: {product.id})")
                
        except Exception as e:
            self.stdout.write(f"❌ Database save failed: {e}")
            # Update processing job status if it was created
            if processing_job:
                processing_job.status = 'failed'
                processing_job.error_message = str(e)
                processing_job.completed_at = timezone.now()
                processing_job.save()
            stats['errors'] += 1

    def _download_image(self, url, product_name):
        """Download image from URL with comprehensive error handling and logging"""
        try:
            self.logger.debug(f'IMAGE_DOWNLOAD_ATTEMPT: {url}')
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                img_data = response.read()
                
                if len(img_data) < 1000:
                    warning_msg = f"⚠️  Image too small: {len(img_data)} bytes"
                    self.log_and_print(warning_msg, 'WARNING')
                    self.logger.warning(f'IMAGE_TOO_SMALL: {url} - {len(img_data)} bytes')
                    return None
                
                image = Image.open(io.BytesIO(img_data)).convert('RGB')
                
                if image.size[0] < 50 or image.size[1] < 50:
                    warning_msg = f"⚠️  Image dimensions too small: {image.size}"
                    self.log_and_print(warning_msg, 'WARNING')
                    self.logger.warning(f'IMAGE_DIMENSIONS_SMALL: {url} - {image.size}')
                    return None
                
                self.logger.debug(f'IMAGE_DOWNLOAD_SUCCESS: {url} - {image.size} - {len(img_data)} bytes')
                return image
                
        except Exception as e:
            error_msg = f"⚠️  Image download failed for {product_name}: {e}"
            self.log_and_print(error_msg, 'WARNING')
            self.logger.error(f'IMAGE_DOWNLOAD_ERROR: {url} - {str(e)}')
            return None

    def _format_barcode(self, barcode):
        """Format barcode properly"""
        if not barcode or pd.isna(barcode):
            return None
        
        barcode = str(barcode).strip()
        if not barcode or barcode == 'nan':
            return None
        
        # Clean formatting
        if barcode.startswith("'") and barcode.endswith("'"):
            barcode = barcode[1:-1]
        
        if barcode.isdigit() and 8 <= len(barcode) <= 14:
            return barcode
        
        return None

    def _is_turkish_text(self, text):
        """Check if text is Turkish"""
        if not text:
            return False
            
        import re
        
        # Turkish characters
        turkish_chars = 'çğıöşüÇĞİÖŞÜ'
        
        # Check for Turkish characters
        for char in turkish_chars:
            if char in text:
                return True
        
        # Turkish common words
        turkish_words = ['ve', 'ile', 'veya', 'için', 'içerik', 'adet', 'kg', 'gram', 'litre', 'ml']
        text_words = re.sub(r'[^\w\s]', ' ', text.lower()).split()
        
        for word in turkish_words:
            if word in text_words:
                return True
        
        # Check for Turkish food categories
        if any(cat in text for cat in ['Süt & Kahvaltı', 'İçecek', 'Atıştırmalık', 'Temel Gıda']):
            return True
            
        return False

    def _clean_duplicates(self):
        """Clean duplicate products before import with logging"""
        from django.db.models import Count
        
        self.log_and_print("🧹 Cleaning duplicate products...", 'INFO')
        self.logger.info('DUPLICATE_CLEANUP_START')
        
        # Remove duplicate barcodes
        duplicate_barcodes = Product.objects.exclude(barcode='').exclude(barcode__isnull=True).values('barcode').annotate(
            count=Count('barcode')).filter(count__gt=1).values_list('barcode', flat=True)
        
        total_deleted = 0
        for barcode in duplicate_barcodes:
            duplicates = Product.objects.filter(barcode=barcode).order_by('-id')
            keep_product = duplicates.first()
            deleted_count = duplicates.exclude(id=keep_product.id).delete()[0]
            total_deleted += deleted_count
            
            delete_msg = f"   Removed {deleted_count} duplicate products for barcode: {barcode}"
            self.log_and_print(delete_msg, 'INFO')
            self.logger.info(f'DUPLICATE_REMOVED: Barcode {barcode} - kept ID {keep_product.id}, deleted {deleted_count}')
        
        cleanup_msg = f"✅ Duplicate cleanup completed - removed {total_deleted} products"
        self.log_and_print(cleanup_msg, 'INFO', 'SUCCESS')
        self.logger.info(f'DUPLICATE_CLEANUP_COMPLETE: Total deleted {total_deleted}')

    def _show_final_results(self, stats, start_time, processed_dir):
        """Show comprehensive final results with detailed logging"""
        elapsed = time.time() - start_time
        
        # Log final statistics
        self.logger.info('FINAL_RESULTS_START')
        self.logger.info(f'TOTAL_TIME: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)')
        
        for key, value in stats.items():
            if isinstance(value, dict):
                self.logger.info(f'STATS_{key.upper()}: {value}')
            else:
                self.logger.info(f'STATS_{key.upper()}: {value}')
        
        # Console output
        self.log_and_print("\n" + "="*60, 'INFO')
        self.log_and_print("🎉 ENHANCED IMPORT WITH COLOR PROCESSING COMPLETED!", 'INFO', 'SUCCESS')
        self.log_and_print("="*60, 'INFO')
        
        # Time and performance
        self.log_and_print(f"⏱️  Total time: {elapsed/60:.1f} minutes", 'INFO')
        if stats['processed'] > 0:
            avg_time = elapsed / stats['processed']
            self.log_and_print(f"📊 Average: {avg_time:.1f} seconds per product", 'INFO')
        
        # Processing statistics
        self.log_and_print(f"\n📈 Processing Results:", 'INFO')
        self.log_and_print(f"   ✅ Successfully processed: {stats['processed']}", 'INFO')
        self.log_and_print(f"   ⏭️  Existing products skipped: {stats['existing_skipped']}", 'INFO')
        self.log_and_print(f"   ⏭️  Other skipped: {stats['skipped']}", 'INFO')
        self.log_and_print(f"   ❌ Errors: {stats['errors']}", 'INFO')
        
        # Image processing
        self.log_and_print(f"\n🖼️  Image Processing:", 'INFO')
        self.log_and_print(f"   📥 Downloaded: {stats['images_downloaded']}", 'INFO')
        self.log_and_print(f"   ✂️  Background removed: {stats['backgrounds_removed']}", 'INFO')
        self.log_and_print(f"   ⚠️  Background removal failed: {stats['background_removal_failed']}", 'INFO')
        
        if stats['backgrounds_removed'] + stats['background_removal_failed'] > 0:
            success_rate = stats['backgrounds_removed'] / (stats['backgrounds_removed'] + stats['background_removal_failed']) * 100
            self.log_and_print(f"   📊 Background removal success rate: {success_rate:.1f}%", 'INFO')
        
        # AI processing
        self.log_and_print(f"\n🤖 AI Processing:", 'INFO')
        self.log_and_print(f"   🎨 Color analyzed: {stats['color_analyzed']}", 'INFO')
        self.log_and_print(f"   🧠 Visual features extracted: {stats['visual_features_extracted']}", 'INFO')
        self.log_and_print(f"   📝 Text embeddings created: {stats['text_embeddings_created']}", 'INFO')
        self.log_and_print(f"   ⚙️  Processing jobs created: {stats['processing_jobs_created']}", 'INFO')
        
        # Color distribution
        if stats['color_distribution']:
            self.log_and_print(f"\n🎨 Color Distribution:", 'INFO')
            for color, count in sorted(stats['color_distribution'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / sum(stats['color_distribution'].values())) * 100
                color_display = dict(Product.COLOR_CHOICES).get(color, color)
                color_msg = f"   {color_display}: {count} products ({percentage:.1f}%)"
                self.log_and_print(color_msg, 'INFO')
        
        # Confidence distribution
        conf_dist = stats['confidence_distribution']
        total_analyzed = sum(conf_dist.values())
        if total_analyzed > 0:
            self.log_and_print(f"\n🎯 Color Confidence Distribution:", 'INFO')
            self.log_and_print(f"   High (≥0.7): {conf_dist['high']} products ({conf_dist['high']/total_analyzed*100:.1f}%)", 'INFO')
            self.log_and_print(f"   Medium (0.4-0.7): {conf_dist['medium']} products ({conf_dist['medium']/total_analyzed*100:.1f}%)", 'INFO')
            self.log_and_print(f"   Low (<0.4): {conf_dist['low']} products ({conf_dist['low']/total_analyzed*100:.1f}%)", 'INFO')
        
        # File output
        if processed_dir and os.path.exists(processed_dir):
            image_files = [f for f in os.listdir(processed_dir) if f.endswith('.png')]
            self.log_and_print(f"\n📁 Processed Images:", 'INFO')
            self.log_and_print(f"   💾 {len(image_files)} images saved to: {processed_dir}", 'INFO')
        
        self.log_and_print(f"\n🎯 Next Steps:", 'INFO')
        self.log_and_print(f"   1. Run: python manage.py processing_stats", 'INFO')
        self.log_and_print(f"   2. Run: python manage.py debug_products", 'INFO')
        if processed_dir:
            self.log_and_print(f"   3. Check processed images in: {processed_dir}", 'INFO')
        self.log_and_print("="*60, 'INFO')
        
        self.logger.info('FINAL_RESULTS_COMPLETE')

    def _rebuild_index(self):
        """Rebuild the enhanced FAISS vector index with logging"""
        self.log_and_print("\n🔄 Rebuilding enhanced FAISS vector index...", 'INFO')
        self.logger.info('INDEX_REBUILD_START')
        
        try:
            start_time = time.time()
            build_enhanced_vector_index()
            elapsed = time.time() - start_time
            
            success_msg = f"✅ Enhanced vector index rebuilt successfully ({elapsed:.1f}s)"
            self.log_and_print(success_msg, 'INFO', 'SUCCESS')
            self.logger.info(f'INDEX_REBUILD_SUCCESS: Completed in {elapsed:.1f}s')
            
        except Exception as e:
            error_msg = f"❌ FAISS index rebuild failed: {e}"
            self.log_and_print(error_msg, 'ERROR', 'ERROR')
            self.logger.error(f'INDEX_REBUILD_FAILED: {str(e)}')
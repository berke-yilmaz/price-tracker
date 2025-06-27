# api/enhanced_preprocessor_clean.py - CLEAN, ROBUST VERSION
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import torch
import torchvision.transforms as transforms
from typing import Tuple, Dict, Any, Optional, Union
import logging
import io
import os
from django.conf import settings

# Try to import rembg with a fallback
try:
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    remove, new_session = None, None

logger = logging.getLogger(__name__)

class CleanProductPreprocessor:
    """
    A simple, robust, and bulletproof preprocessing pipeline for product images.
    It prioritizes isolating the product and performing gentle enhancements.
    """
    
    def __init__(self, target_size: Tuple[int, int] = (512, 512), use_gpu: bool = False):
        self.target_size = target_size
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        
        self.bg_session = None
        if REMBG_AVAILABLE and remove and new_session:
            try:
                self.bg_session = new_session('u2net')
                logger.info("Clean Preprocessor: Background removal model initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize rembg session: {e}")
                self.bg_session = None
        
        self.debug_mode = getattr(settings, 'AI_DEBUG_SAVE_STEPS', True)
        self.debug_dir = getattr(settings, 'AI_DEBUG_DIR', os.path.join(settings.BASE_DIR, 'media', 'debug_preprocessing'))
    
    def process_image(self, image_input: Union[bytes, Image.Image, np.ndarray], 
                     return_steps: bool = False) -> Dict[str, Any]:
        """
        Executes the simple and robust processing pipeline.
        """
        # --- Initialize all variables to prevent scope errors ---
        original_image = None
        processed_image = None
        results = {
            'success': False, 'error': 'Processing did not start',
            'processed_image': None, 'feature_ready_array': None,
            'processing_steps': [], 'warnings': []
        }
        
        try:
            # Step 1: Convert input to a standard PIL Image
            original_image = self._convert_to_pil(image_input)
            if not original_image:
                results['error'] = "Invalid image input format."
                return results
            
            processed_image = original_image.copy()
            results['success'] = True
            results['error'] = None
            if return_steps:
                results['intermediate_steps'] = {'original': original_image.copy()}

            # Step 2: Background Removal (High-Impact First Step)
            if self.bg_session:
                bg_removed = self._remove_background(processed_image)
                if bg_removed:
                    processed_image = bg_removed
                    results['processing_steps'].append('background_removal')
                    if return_steps:
                        results['intermediate_steps']['background_removed'] = processed_image.copy()
                else:
                    results['warnings'].append('Background removal failed or was not effective.')

            # Step 3: Gentle Enhancement on the (now cleaner) image
            enhanced_image = self._basic_enhancement(processed_image)
            processed_image = enhanced_image
            results['processing_steps'].append('basic_enhancement')
            if return_steps:
                results['intermediate_steps']['enhanced'] = processed_image.copy()
            
            # Step 4: Final Resize and Format
            final_image = self._final_standardization(processed_image)
            processed_image = final_image
            results['processing_steps'].append('final_standardization')
            if return_steps:
                results['intermediate_steps']['final'] = processed_image.copy()
            
            # Step 5: Prepare for Feature Extraction
            feature_array = self._prepare_features(processed_image)
            results['feature_ready_array'] = feature_array
            
            # Set final successful results
            results['processed_image'] = processed_image
            results['final_size'] = processed_image.size
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error in Clean preprocessor: {e}", exc_info=True)
            results['success'] = False
            results['error'] = str(e)
            results['processed_image'] = original_image # Return original on failure
            return results

    def _convert_to_pil(self, image_input) -> Optional[Image.Image]:
        try:
            if isinstance(image_input, bytes):
                return Image.open(io.BytesIO(image_input)).convert('RGB')
            elif isinstance(image_input, Image.Image):
                return image_input.convert('RGB')
            elif isinstance(image_input, np.ndarray):
                return Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
            return None
        except Exception as e:
            logger.error(f"Input conversion to PIL failed: {e}")
            return None

    def _remove_background(self, image: Image.Image) -> Optional[Image.Image]:
        try:
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            result_bytes = remove(img_bytes.getvalue(), session=self.bg_session)
            
            result_image_rgba = Image.open(io.BytesIO(result_bytes)).convert('RGBA')
            
            # Validate that the removal was effective
            alpha = np.array(result_image_rgba.getchannel('A'))
            foreground_ratio = np.count_nonzero(alpha) / alpha.size
            if foreground_ratio < 0.02 or foreground_ratio > 0.98: # Check if it removed too little or too much
                return None

            # Composite on a clean white background
            white_bg = Image.new('RGB', result_image_rgba.size, (255, 255, 255))
            white_bg.paste(result_image_rgba, mask=result_image_rgba)
            return white_bg
        except Exception as e:
            logger.warning(f"Rembg background removal failed: {e}")
            return None

    def _basic_enhancement(self, image: Image.Image) -> Image.Image:
        # Gentle contrast boost
        enhanced = ImageEnhance.Contrast(image).enhance(1.1)
        # Gentle sharpening
        enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=2))
        return enhanced

    def _final_standardization(self, image: Image.Image) -> Image.Image:
        if hasattr(Image, 'Resampling'):
            resample_filter = Image.Resampling.LANCZOS
        else:
            resample_filter = Image.ANTIALIAS
        
        resized = image.resize(self.target_size, resample_filter)
        if resized.mode != 'RGB':
            return resized.convert('RGB')
        return resized

    def _prepare_features(self, image: Image.Image) -> np.ndarray:
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        tensor = transform(image)
        return tensor.numpy()
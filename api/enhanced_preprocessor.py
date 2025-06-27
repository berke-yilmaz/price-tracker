# api/enhanced_preprocessor.py - FINAL, ROBUST, AND DEBUGGABLE VERSION
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
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

class EnhancedProductPreprocessor:
    """
    A robust, simple, and debuggable preprocessing pipeline.
    It prioritizes isolating the product and performing safe, sequential enhancements.
    """

    def __init__(self, target_size: Tuple[int, int] = (512, 512), use_gpu: bool = False):
        self.target_size = target_size
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        
        self.bg_session = None
        if REMBG_AVAILABLE and remove and new_session:
            try:
                self.bg_session = new_session('u2net')
                logger.info("Preprocessor: Background removal model initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize rembg session: {e}")
                self.bg_session = None
        
        self.debug_mode = getattr(settings, 'AI_DEBUG_SAVE_STEPS', True)
        self.debug_dir = getattr(settings, 'AI_DEBUG_DIR', os.path.join(settings.BASE_DIR, 'media', 'debug_preprocessing'))

    def process_image(self, image_input: Union[bytes, Image.Image, np.ndarray], return_steps: bool = False, product_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the robust pipeline and saves debug steps.
        """
        results = {'success': False, 'error': 'Processing did not start', 'processed_image': None, 'warnings': []}
        intermediate_steps = {}

        try:
            # Step 1: Input Conversion
            original_image = self._convert_to_pil(image_input)
            if not original_image:
                results['error'] = "Invalid image input format."
                return results
            intermediate_steps['0_original'] = original_image.copy()

            processed_image = original_image.copy()

            # Step 2: Background Removal
            if self.bg_session:
                bg_removed = self._remove_background(processed_image)
                if bg_removed:
                    processed_image = bg_removed
                    intermediate_steps['1_bg_removed'] = processed_image.copy()

            # Step 3: Gamma Correction (for lighting normalization)
            gamma_corrected = self._apply_gamma_correction(processed_image)
            processed_image = gamma_corrected
            intermediate_steps['2_gamma_corrected'] = processed_image.copy()
            
            # Step 4: Contrast Enhancement (CLAHE)
            contrast_enhanced = self._enhance_contrast(processed_image)
            processed_image = contrast_enhanced
            intermediate_steps['3_contrast_enhanced'] = processed_image.copy()

            # Step 5: Gentle Sharpening
            sharpened = processed_image.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=2))
            processed_image = sharpened
            intermediate_steps['4_sharpened'] = processed_image.copy()

            # Step 6: Final Standardization (Resize)
            final_image = self._final_standardization(processed_image)
            intermediate_steps['5_final'] = final_image.copy()

            # Prepare for feature extraction
            feature_array = self._prepare_features(final_image)

            # Success
            results.update({
                'success': True, 'error': None, 'processed_image': final_image,
                'feature_ready_array': feature_array, 'final_size': final_image.size
            })
            if return_steps:
                results['intermediate_steps'] = intermediate_steps

            # Save debug images if enabled
            if self.debug_mode and product_id:
                self._save_debug_steps(intermediate_steps, product_id)

            return results

        except Exception as e:
            logger.error(f"Critical error in preprocessor for {product_id}: {e}", exc_info=True)
            results['error'] = str(e)
            if 'original_image' in locals():
                results['processed_image'] = original_image
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
        except Exception:
            return None

    def _remove_background(self, image: Image.Image) -> Optional[Image.Image]:
        try:
            img_bytes_io = io.BytesIO()
            image.save(img_bytes_io, format='PNG')
            result_bytes = remove(img_bytes_io.getvalue(), session=self.bg_session)
            
            result_rgba = Image.open(io.BytesIO(result_bytes)).convert('RGBA')
            
            white_bg = Image.new('RGB', result_rgba.size, (255, 255, 255))
            white_bg.paste(result_rgba, mask=result_rgba)
            return white_bg
        except Exception as e:
            logger.warning(f"Rembg failed: {e}")
            return None

    def _apply_gamma_correction(self, image: Image.Image) -> Image.Image:
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        mean_brightness = np.mean(gray)
        # Apply gamma correction to normalize brightness towards a mid-level (128)
        # gamma < 1 brightens, gamma > 1 darkens.
        gamma = np.log(128) / np.log(mean_brightness) if mean_brightness > 0 else 1.0
        gamma = np.clip(gamma, 0.5, 1.8) # Prevent extreme corrections
        
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        corrected_array = cv2.LUT(img_array, table)
        return Image.fromarray(corrected_array)
        
    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        # Use CLAHE for adaptive contrast enhancement
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        limg = cv2.merge((cl, a, b))
        enhanced_cv = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return Image.fromarray(cv2.cvtColor(enhanced_cv, cv2.COLOR_BGR2RGB))

    def _final_standardization(self, image: Image.Image) -> Image.Image:
        resample_filter = Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS
        resized = image.resize(self.target_size, resample_filter)
        return resized.convert('RGB')

    def _prepare_features(self, image: Image.Image) -> np.ndarray:
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        return transform(image).numpy()

    def _save_debug_steps(self, intermediate_steps: dict, product_id: str):
        if not self.debug_mode: return
        try:
            run_dir = os.path.join(self.debug_dir, str(product_id))
            os.makedirs(run_dir, exist_ok=True)
            for step_name, step_image in intermediate_steps.items():
                filepath = os.path.join(run_dir, f"{step_name}.png")
                step_image.save(filepath, "PNG")
        except Exception as e:
            logger.error(f"Failed to save debug images for {product_id}: {e}")
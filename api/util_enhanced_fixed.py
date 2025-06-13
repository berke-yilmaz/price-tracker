# api/util_enhanced_fixed.py - SIMPLE VERSION WITHOUT RECURSION
import os
import io
import cv2
import numpy as np
from typing import Tuple, List, Dict, Optional, Union
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import logging

logger = logging.getLogger(__name__)

def simple_conservative_crop(image: Image.Image, crop_factor: float = 0.85) -> Image.Image:
    """Simple conservative cropping that preserves product integrity"""
    try:
        width, height = image.size
        
        # Never crop more than 15% from any side
        margin_x = int(width * (1 - crop_factor) / 2)
        margin_y = int(height * (1 - crop_factor) / 2)
        
        # Ensure minimum margins
        margin_x = max(margin_x, 10)
        margin_y = max(margin_y, 10)
        
        # Calculate crop coordinates
        x1 = margin_x
        y1 = margin_y
        x2 = width - margin_x
        y2 = height - margin_y
        
        # Ensure we don't crop to nothing
        if x2 - x1 < width * 0.4 or y2 - y1 < height * 0.4:
            # Use minimal crop
            margin = min(width, height) * 0.05
            x1, y1 = margin, margin
            x2, y2 = width - margin, height - margin
        
        # Crop the image
        cropped = image.crop((int(x1), int(y1), int(x2), int(y2)))
        
        logger.info(f"Simple conservative crop: {image.size} -> {cropped.size}")
        return cropped
        
    except Exception as e:
        logger.error(f"Simple crop failed: {e}")
        return image

def simple_image_enhancement(image: Image.Image) -> Image.Image:
    """Simple image enhancement without recursion"""
    try:
        # Ensure RGB
        if image.mode != 'RGB':
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert('RGB')
        
        # Light contrast enhancement
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(1.1)
        
        # Resize to consistent size
        target_size = (384, 384)
        enhanced = enhanced.resize(target_size, Image.Resampling.LANCZOS)
        
        return enhanced
        
    except Exception as e:
        logger.error(f"Simple enhancement failed: {e}")
        return image

def simple_fixed_preprocessing(image: Union[Image.Image, bytes, io.BytesIO]) -> Tuple[Image.Image, Dict]:
    """Simple fixed preprocessing without recursion"""
    # Convert to PIL Image if needed
    if isinstance(image, (bytes, io.BytesIO)):
        if isinstance(image, io.BytesIO):
            image_data = image.getvalue()
        else:
            image_data = image
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
    elif not isinstance(image, Image.Image):
        image = Image.open(image).convert('RGB')
    
    processing_info = {
        'original_size': image.size,
        'steps_applied': ['simple_conservative_crop', 'simple_enhancement'],
        'detection_result': {'method': 'conservative_crop', 'confidence': 0.8},
        'success': True
    }
    
    try:
        # Step 1: Conservative crop
        processed_image = simple_conservative_crop(image, 0.85)
        
        # Step 2: Simple enhancement
        processed_image = simple_image_enhancement(processed_image)
        
        processing_info['final_size'] = processed_image.size
        
        logger.info(f"Simple fixed preprocessing completed")
        
        return processed_image, processing_info
        
    except Exception as e:
        logger.error(f"Simple fixed preprocessing failed: {e}")
        processing_info['success'] = False
        processing_info['error'] = str(e)
        return simple_image_enhancement(image), processing_info

def process_product_image_simple_fixed(image: Union[Image.Image, bytes, io.BytesIO],
                                      product_id: Optional[str] = None,
                                      save_processed: bool = False,
                                      processed_dir: Optional[str] = None) -> Tuple[Dict, bool]:
    """Complete simple fixed product image processing pipeline"""
    try:
        # Step 1: Simple fixed preprocessing
        processed_image, preprocessing_info = simple_fixed_preprocessing(image)
        
        # Step 2: Color analysis - DIRECT IMPORT TO AVOID RECURSION
        try:
            from api.util import categorize_by_color
            color_info = categorize_by_color(processed_image)
        except Exception as e:
            logger.error(f"Color analysis failed: {e}")
            color_info = {'category': 'unknown', 'confidence': 0.0, 'colors': []}
        
        # Step 3: Visual feature extraction - SIMPLIFIED
        visual_features = None
        try:
            import torch
            import torchvision.models as models
            import torchvision.transforms as transforms
            from torchvision.models import ResNet50_Weights
            
            # Force CPU to avoid CUDA issues
            device = torch.device("cpu")
            
            # Load model directly
            resnet50 = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2).to(device)
            resnet50 = torch.nn.Sequential(*list(resnet50.children())[:-1])
            resnet50.eval()
            
            # Preprocess
            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            
            img_tensor = preprocess(processed_image).unsqueeze(0).to(device)
            
            # Extract features
            with torch.no_grad():
                features = resnet50(img_tensor)
                visual_features = features.cpu().numpy().reshape(-1)
            
            logger.info(f"Direct ResNet50 feature extraction: {len(visual_features)} dims")
            
        except Exception as e:
            logger.error(f"Visual feature extraction failed: {e}")
            visual_features = np.zeros(2048, dtype=np.float32)
        
        # Step 4: Save processed image if requested
        saved_path = None
        if save_processed and processed_dir and product_id:
            try:
                os.makedirs(processed_dir, exist_ok=True)
                filename = f"{product_id}_simple_fixed.png"
                filepath = os.path.join(processed_dir, filename)
                processed_image.save(filepath, 'PNG')
                saved_path = filepath
                logger.info(f"Saved: {filepath}")
            except Exception as e:
                logger.warning(f"Save failed: {e}")
        
        # Results
        results = {
            'preprocessing_info': preprocessing_info,
            'color_info': color_info,
            'visual_features': visual_features.tolist() if visual_features is not None else None,
            'processed_image_path': saved_path,
            'success': True
        }
        
        return results, True
        
    except Exception as e:
        logger.error(f"Simple processing failed: {e}")
        return {'error': str(e), 'success': False}, False

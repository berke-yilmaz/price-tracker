# api/util_enhanced.py - Enhanced Product Detection and Processing
import os
import io
import cv2
import numpy as np
from typing import Tuple, List, Dict, Optional, Union
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import requests
import base64
import json

# Import your existing utilities
from .util import (
    extract_visual_features_resnet,
    categorize_by_color,
    get_color_aware_text_embedding,
    COLOR_CATEGORIES
)


# Add this at the top of api/util_enhanced.py if it's missing

import logging

# Create logger for this module
logger = logging.getLogger(__name__)

# Alternative: If you want to ensure logger exists everywhere
try:
    logger
except NameError:
    logger = logging.getLogger(__name__)

# Or use this safer approach throughout the code:
def get_logger():
    """Get or create logger safely"""
    try:
        return logger
    except NameError:
        return logging.getLogger(__name__)

# Then in your code, replace logger.info() with:
# get_logger().info()

# Or simply add this one-liner at the top after other imports:
logger = logging.getLogger(__name__)
class EnhancedProductDetector:
    """
    Enhanced product detection using multiple AI services and computer vision techniques
    """
    
    def __init__(self):
        self.yolo_model = None
        self.segment_anything_available = False
        self.api_keys = {
            'roboflow': os.getenv('ROBOFLOW_API_KEY'),
            'google_vision': os.getenv('GOOGLE_VISION_API_KEY'),
            'azure_vision': os.getenv('AZURE_VISION_API_KEY')
        }
        self._load_models()
    
    def _load_models(self):
        """Load available AI models"""
        try:
            # Try to load YOLOv8 for object detection
            import ultralytics
            self.yolo_model = ultralytics.YOLO('yolov8n.pt')  # Nano version for speed
            logger.info("YOLOv8 model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load YOLOv8: {e}")
        
        try:
            # Check if Segment Anything is available
            import segment_anything
            self.segment_anything_available = True
            logger.info("Segment Anything available")
        except Exception as e:
            logger.warning(f"Segment Anything not available: {e}")
    
    def detect_product_with_yolo(self, image: Image.Image) -> Optional[Dict]:
        """
        Detect products using YOLOv8
        Returns bounding box and confidence if product detected
        """
        if not self.yolo_model:
            return None

        try:
            # Convert PIL to numpy array
            img_array = np.array(image)
            
            # Run YOLO detection
            results = self.yolo_model(img_array, verbose=False)
            
            best_detection = None
            best_confidence = 0.0
            
            for result in results:
                for box in result.boxes:
                    # Check if detected object is likely a product
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    # YOLO classes that are likely products
                    product_classes = [
                        39,  # bottle
                        40,  # wine glass
                        41,  # cup
                        42,  # fork
                        43,  # knife
                        44,  # spoon
                        45,  # bowl
                        46,  # banana
                        47,  # apple
                        48,  # sandwich
                        49,  # orange
                        50,  # broccoli
                        51,  # carrot
                        52,  # hot dog
                        53,  # pizza
                        54,  # donut
                        55,  # cake
                    ]
                    
                    if class_id in product_classes and confidence > best_confidence:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        best_detection = {
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'confidence': confidence,
                            'class_id': class_id,
                            'class_name': self.yolo_model.names[class_id]
                        }
                        best_confidence = confidence
            
            return best_detection
            
        except Exception as e:
            logger.error(f"YOLO detection failed: {e}")
            return None
    
    def detect_product_with_roboflow(self, image: Image.Image) -> Optional[Dict]:
        """
        Use Roboflow API for product detection
        """
        if not self.api_keys['roboflow']:
            return None
        
        try:
            # Convert image to base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            # Roboflow API call for general object detection
            url = f"https://detect.roboflow.com/coco/3?api_key={self.api_keys['roboflow']}"
            
            response = requests.post(url, 
                data=img_str,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                predictions = result.get('predictions', [])
                
                # Find the most confident detection
                best_detection = None
                best_confidence = 0.0
                
                for pred in predictions:
                    confidence = pred.get('confidence', 0)
                    if confidence > best_confidence:
                        # Convert Roboflow format to our format
                        x = pred['x']
                        y = pred['y']
                        width = pred['width']
                        height = pred['height']
                        
                        x1 = int(x - width/2)
                        y1 = int(y - height/2)
                        x2 = int(x + width/2)
                        y2 = int(y + height/2)
                        
                        best_detection = {
                            'bbox': [x1, y1, x2, y2],
                            'confidence': confidence,
                            'class_name': pred.get('class', 'product')
                        }
                        best_confidence = confidence
                
                return best_detection
                
        except Exception as e:
            logger.error(f"Roboflow detection failed: {e}")
            return None
    
    def detect_product_with_edge_analysis(self, image: Image.Image) -> Optional[Dict]:
        """
        Fallback method using edge detection and contour analysis
        """
        try:
            # Convert to OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Find the largest contour (likely the main product)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Calculate confidence based on contour area vs image area
            contour_area = cv2.contourArea(largest_contour)
            image_area = image.width * image.height
            area_ratio = contour_area / image_area
            
            # Confidence based on how much of the image the product occupies
            confidence = min(area_ratio * 2, 0.95)  # Cap at 95%
            
            # Only return if the detected area is reasonable
            if 0.1 <= area_ratio <= 0.8 and w > 50 and h > 50:
                return {
                    'bbox': [x, y, x + w, y + h],
                    'confidence': confidence,
                    'class_name': 'product',
                    'method': 'edge_analysis'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Edge analysis detection failed: {e}")
            return None
    
    def detect_product_smart_crop(self, image: Image.Image) -> Optional[Dict]:
        """
        Smart cropping based on content analysis
        """
        try:
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Calculate variance of Laplacian (focus measure)
            focus_map = cv2.Laplacian(gray, cv2.CV_64F)
            focus_map = np.absolute(focus_map)
            
            # Apply threshold to get high-focus areas
            _, focus_thresh = cv2.threshold(focus_map.astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(focus_thresh)
            
            # Find the largest component (excluding background)
            if num_labels > 1:
                # Get the largest component (excluding background at index 0)
                largest_idx = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
                
                x = stats[largest_idx, cv2.CC_STAT_LEFT]
                y = stats[largest_idx, cv2.CC_STAT_TOP]
                w = stats[largest_idx, cv2.CC_STAT_WIDTH]
                h = stats[largest_idx, cv2.CC_STAT_HEIGHT]
                area = stats[largest_idx, cv2.CC_STAT_AREA]
                
                # Add some padding
                padding = 20
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.width - x, w + 2 * padding)
                h = min(image.height - y, h + 2 * padding)
                
                # Calculate confidence
                total_area = image.width * image.height
                confidence = min(area / total_area * 1.5, 0.85)
                
                if w > 50 and h > 50:
                    return {
                        'bbox': [x, y, x + w, y + h],
                        'confidence': confidence,
                        'class_name': 'product',
                        'method': 'smart_crop'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Smart crop detection failed: {e}")
            return None
    
    def detect_product(self, image: Image.Image) -> Optional[Dict]:
        """
        Main product detection method - tries multiple approaches
        """
        detections = []
        
        # Try YOLO first (most accurate)
        yolo_detection = self.detect_product_with_yolo(image)
        if yolo_detection:
            detections.append(('yolo', yolo_detection))
        
        # Try Roboflow API
        roboflow_detection = self.detect_product_with_roboflow(image)
        if roboflow_detection:
            detections.append(('roboflow', roboflow_detection))
        
        # Try edge analysis
        edge_detection = self.detect_product_with_edge_analysis(image)
        if edge_detection:
            detections.append(('edge', edge_detection))
        
        # Try smart crop
        smart_detection = self.detect_product_smart_crop(image)
        if smart_detection:
            detections.append(('smart', smart_detection))
        
        if not detections:
            return None
        
        # Choose the best detection based on confidence and method priority
        best_detection = None
        best_score = 0
        
        method_weights = {
            'yolo': 1.0,
            'roboflow': 0.9,
            'edge': 0.7,
            'smart': 0.6
        }
        
        for method, detection in detections:
            score = detection['confidence'] * method_weights.get(method, 0.5)
            if score > best_score:
                best_score = score
                best_detection = detection
                best_detection['detection_method'] = method
        
        return best_detection


def intelligent_crop_product(image: Image.Image, detection_result: Optional[Dict] = None) -> Image.Image:
    """
    Intelligently crop the product based on detection results
    """
    detector = EnhancedProductDetector()
    
    # If no detection provided, try to detect
    if not detection_result:
        detection_result = detector.detect_product(image)
    
    if detection_result and 'bbox' in detection_result:
        # Use detected bounding box
        x1, y1, x2, y2 = detection_result['bbox']
        
        # Add some padding around the detected product
        padding_percent = 0.1  # 10% padding
        width = x2 - x1
        height = y2 - y1
        
        padding_x = int(width * padding_percent)
        padding_y = int(height * padding_percent)
        
        # Apply padding with bounds checking
        x1 = max(0, x1 - padding_x)
        y1 = max(0, y1 - padding_y)
        x2 = min(image.width, x2 + padding_x)
        y2 = min(image.height, y2 + padding_y)
        
        # Crop the image
        cropped = image.crop((x1, y1, x2, y2))
        
        logger.info(f"Product detected and cropped using {detection_result.get('detection_method', 'unknown')} method")
        logger.info(f"Original size: {image.size}, Cropped size: {cropped.size}, Confidence: {detection_result.get('confidence', 0):.2f}")
        
        return cropped
    else:
        # Fallback to center crop with better logic
        logger.warning("No product detected, using intelligent center crop")
        return intelligent_center_crop(image)


def intelligent_center_crop(image: Image.Image, crop_factor: float = 0.75) -> Image.Image:
    """
    Improved center cropping that analyzes image content
    """
    try:
        # Convert to numpy for analysis
        img_array = np.array(image)
        
        # Calculate image statistics to find interesting areas
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Find areas with high variance (likely to contain products)
        kernel_size = 15
        kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
        mean_img = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        
        # Calculate local variance
        sqr_img = cv2.filter2D((gray.astype(np.float32))**2, -1, kernel)
        variance_img = sqr_img - mean_img**2
        
        # Find center of mass of high-variance areas
        threshold = np.percentile(variance_img, 75)  # Top 25% variance areas
        high_var_mask = variance_img > threshold
        
        if np.any(high_var_mask):
            # Find center of mass of interesting areas
            y_coords, x_coords = np.where(high_var_mask)
            center_x = int(np.mean(x_coords))
            center_y = int(np.mean(y_coords))
        else:
            # Fallback to image center
            center_x = image.width // 2
            center_y = image.height // 2
        
        # Calculate crop dimensions
        crop_width = int(image.width * crop_factor)
        crop_height = int(image.height * crop_factor)
        
        # Calculate crop coordinates centered on the interesting area
        x1 = max(0, center_x - crop_width // 2)
        y1 = max(0, center_y - crop_height // 2)
        x2 = min(image.width, x1 + crop_width)
        y2 = min(image.height, y1 + crop_height)
        
        # Adjust if crop goes outside image bounds
        if x2 - x1 < crop_width:
            x1 = max(0, x2 - crop_width)
        if y2 - y1 < crop_height:
            y1 = max(0, y2 - crop_height)
        
        cropped = image.crop((x1, y1, x2, y2))
        
        logger.info(f"Intelligent center crop: {image.size} -> {cropped.size}, center: ({center_x}, {center_y})")
        
        return cropped
        
    except Exception as e:
        logger.error(f"Intelligent center crop failed: {e}")
        # Simple center crop as final fallback
        width, height = image.size
        crop_size = min(width, height) * crop_factor
        
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        
        return image.crop((int(left), int(top), int(right), int(bottom)))


def safe_background_removal_v2(image: Image.Image, detection_result: Optional[Dict] = None) -> Tuple[Image.Image, bool]:
    """
    Safe background removal that preserves product integrity
    """
    try:
        # First, try to detect the product
        detector = EnhancedProductDetector()
        if not detection_result:
            detection_result = detector.detect_product(image)
        
        # If we have a good detection, use selective background removal
        if detection_result and detection_result.get('confidence', 0) > 0.5:
            return selective_background_removal(image, detection_result)
        else:
            # Use conservative background removal
            return conservative_background_removal(image)
            
    except Exception as e:
        logger.error(f"Safe background removal failed: {e}")
        return image, False


def selective_background_removal(image: Image.Image, detection_result: Dict) -> Tuple[Image.Image, bool]:
    """
    Remove background only outside the detected product area
    """
    try:
        # Get product bounding box
        x1, y1, x2, y2 = detection_result['bbox']
        
        # Create a mask that protects the product area
        mask = Image.new('L', image.size, 0)  # Black mask
        draw = ImageDraw.Draw(mask)
        
        # Add some padding to the product area
        padding = 20
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(image.width, x2 + padding)
        y2 = min(image.height, y2 + padding)
        
        # White area where product is (keep this area)
        draw.rectangle([x1, y1, x2, y2], fill=255)
        
        # Apply edge-preserving background removal only outside product area
        img_array = np.array(image)
        mask_array = np.array(mask)
        
        # Simple background removal: blur the background area
        blurred = image.filter(ImageFilter.GaussianBlur(radius=5))
        blurred_array = np.array(blurred)
        
        # Combine: keep original in product area, blur outside
        result_array = np.where(mask_array[..., np.newaxis] > 128, img_array, blurred_array)
        
        # Create final image with white background
        background = Image.new('RGB', image.size, (255, 255, 255))
        result_image = Image.fromarray(result_array.astype(np.uint8))
        
        # Blend with white background using the mask
        final_image = Image.composite(result_image, background, mask)
        
        logger.info("Selective background removal completed")
        return final_image, True
        
    except Exception as e:
        logger.error(f"Selective background removal failed: {e}")
        return image, False


def conservative_background_removal(image: Image.Image) -> Tuple[Image.Image, bool]:
    """
    Conservative background removal that's less aggressive
    """
    try:
        # Use GrabCut for conservative background removal
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        height, width = img_cv.shape[:2]
        
        # Create initial mask - assume center area contains the product
        mask = np.zeros((height, width), np.uint8)
        
        # Define a rectangle in the center area (conservative)
        margin_x = width // 4
        margin_y = height // 4
        rect = (margin_x, margin_y, width - 2*margin_x, height - 2*margin_y)
        
        # Initialize GrabCut models
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Apply GrabCut with conservative settings
        cv2.grabCut(img_cv, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
        
        # Create final mask (keep probable and definite foreground)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # Apply morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel)
        mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel)
        
        # Check if the mask is reasonable (not too much removed)
        foreground_ratio = np.sum(mask2) / (height * width)
        
        if foreground_ratio < 0.1:  # Too aggressive
            logger.warning("Conservative background removal too aggressive, keeping original")
            return image, False
        
        # Create result with white background
        result = img_cv * mask2[..., np.newaxis]
        background_color = [255, 255, 255]  # White background
        result = np.where(mask2[..., np.newaxis] == 0, background_color, result)
        
        # Convert back to PIL
        result_image = Image.fromarray(cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB))
        
        logger.info(f"Conservative background removal completed, foreground ratio: {foreground_ratio:.2f}")
        return result_image, True
        
    except Exception as e:
        logger.error(f"Conservative background removal failed: {e}")
        return image, False


def enhanced_product_preprocessing(image: Union[Image.Image, bytes, io.BytesIO], 
                                 method: str = 'auto') -> Tuple[Image.Image, Dict]:
    """
    Enhanced product preprocessing pipeline
    
    Args:
        image: Input image
        method: 'auto', 'crop_only', 'bg_removal', 'full'
    
    Returns:
        Tuple of (processed_image, processing_info)
    """
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
        'steps_applied': [],
        'detection_result': None,
        'success': True
    }
    
    try:
        # Step 1: Detect product
        detector = EnhancedProductDetector()
        detection_result = detector.detect_product(image)
        processing_info['detection_result'] = detection_result
        
        if detection_result:
            processing_info['steps_applied'].append(f"product_detected_{detection_result.get('detection_method', 'unknown')}")
        
        processed_image = image
        
        if method in ['auto', 'crop_only', 'full']:
            # Step 2: Intelligent cropping
            processed_image = intelligent_crop_product(processed_image, detection_result)
            processing_info['steps_applied'].append('intelligent_crop')
            processing_info['cropped_size'] = processed_image.size
        
        if method in ['auto', 'bg_removal', 'full']:
            # Step 3: Safe background removal (only if detection confidence is high)
            if detection_result and detection_result.get('confidence', 0) > 0.6:
                bg_removed_image, bg_success = safe_background_removal_v2(processed_image, detection_result)
                if bg_success:
                    processed_image = bg_removed_image
                    processing_info['steps_applied'].append('background_removal')
                else:
                    processing_info['steps_applied'].append('background_removal_skipped')
            else:
                processing_info['steps_applied'].append('background_removal_skipped_low_confidence')
        
        # Step 4: Final enhancement
        if method == 'full':
            processed_image = enhance_product_image(processed_image)
            processing_info['steps_applied'].append('image_enhancement')
        
        processing_info['final_size'] = processed_image.size
        
        logger.info(f"Enhanced preprocessing completed: {processing_info['steps_applied']}")
        
        return processed_image, processing_info
        
    except Exception as e:
        logger.error(f"Enhanced preprocessing failed: {e}")
        processing_info['success'] = False
        processing_info['error'] = str(e)
        return image, processing_info


def enhance_product_image(image: Image.Image) -> Image.Image:
    """
    Final image enhancement for better feature extraction
    """
    try:
        # Slight contrast enhancement
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(1.1)
        
        # Slight sharpening
        enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = enhancer.enhance(1.1)
        
        # Ensure consistent size for feature extraction
        target_size = (384, 384)
        enhanced = enhanced.resize(target_size, Image.Resampling.LANCZOS)
        
        return enhanced
        
    except Exception as e:
        logger.error(f"Image enhancement failed: {e}")
        return image


def extract_visual_features_enhanced(image: Union[Image.Image, bytes, io.BytesIO],
                                   preprocessing_method: str = 'auto',
                                   use_gpu: bool = True,
                                   color_category: Optional[str] = None) -> np.ndarray:
    """
    Enhanced visual feature extraction with intelligent preprocessing
    """
    try:
        # Apply enhanced preprocessing
        processed_image, processing_info = enhanced_product_preprocessing(image, preprocessing_method)
        
        # Extract features using existing ResNet function
        features = extract_visual_features_resnet(
            processed_image,
            remove_bg=False,  # Already handled in preprocessing
            use_gpu=use_gpu,
            color_category=color_category
        )
        
        logger.info(f"Enhanced feature extraction completed with steps: {processing_info['steps_applied']}")
        
        return features
        
    except Exception as e:
        logger.error(f"Enhanced feature extraction failed: {e}")
        # Fallback to original method
        return extract_visual_features_resnet(image, remove_bg=False, use_gpu=use_gpu, color_category=color_category)


def process_product_image_enhanced(image: Union[Image.Image, bytes, io.BytesIO],
                                 product_id: Optional[str] = None,
                                 save_processed: bool = False,
                                 processed_dir: Optional[str] = None) -> Tuple[Dict, bool]:
    """
    Complete enhanced product image processing pipeline
    
    Returns:
        Tuple of (processing_results, success)
    """
    try:
        # Step 1: Enhanced preprocessing
        processed_image, preprocessing_info = enhanced_product_preprocessing(image, method='full')
        
        # Step 2: Color analysis
        color_info = categorize_by_color(processed_image)
        
        # Step 3: Visual feature extraction
        visual_features = extract_visual_features_resnet(
            processed_image,
            remove_bg=False,
            color_category=color_info['category']
        )
        
        # Step 4: Color-aware text embedding (if product name available)
        text_embedding = None
        if product_id:
            # This would need product name from database
            pass
        
        # Step 5: Save processed image if requested
        saved_path = None
        if save_processed and processed_dir and product_id:
            try:
                os.makedirs(processed_dir, exist_ok=True)
                filename = f"{product_id}_enhanced.png"
                filepath = os.path.join(processed_dir, filename)
                processed_image.save(filepath, 'PNG')
                saved_path = filepath
                logger.info(f"Saved enhanced image: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to save processed image: {e}")
        
        # Compile results
        results = {
            'preprocessing_info': preprocessing_info,
            'color_info': color_info,
            'visual_features': visual_features.tolist() if visual_features is not None else None,
            'text_embedding': text_embedding.tolist() if text_embedding is not None else None,
            'processed_image_path': saved_path,
            'success': True
        }
        
        logger.info("Enhanced product processing completed successfully")
        return results, True
        
    except Exception as e:
        logger.error(f"Enhanced product processing failed: {e}")
        return {
            'error': str(e),
            'success': False
        }, False

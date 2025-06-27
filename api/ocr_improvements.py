# api/ocr_improvements.py - Enhanced OCR for Turkish Product Labels
import re
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class TurkishProductOCREnhancer:
    """Enhanced OCR specifically tuned for Turkish product labels"""
    
    def __init__(self):
        # Known Turkish product terms and their common OCR mistakes
        self.product_terms = {
            'SUT': 'SÜT', 'SULT': 'SÜT', 'SÜI': 'SÜT',
            'YAGLI': 'YAĞLI', 'YAGHI': 'YAĞLI', 'YAoLI': 'YAĞLI',
            'CIKOLATA': 'ÇİKOLATA', 'CIKOLATALI': 'ÇİKOLATALI',
            'BROWNİ': 'BROWNIE', 'BROWNI': 'BROWNIE',
            '%I.S': '%1.5', '%IS': '%1.5', '%\s*1S': '%1.5',
            'HARNAS ST': 'HARNAS SÜT',
        }
        
        # Known Turkish brands for better, confident recognition
        self.turkish_brands = [
            'ETİ', 'ÜLKER', 'PINAR', 'SÜTAŞ', 'İÇİM', 'TORKU', 'HARNAS',
            'TAT', 'TADIM', 'KOSKA', 'ŞÖLEN', 'NESTLE'
        ]

    def enhance_image_for_ocr(self, image: Image.Image) -> List[Image.Image]:
        """Creates multiple enhanced versions of an image to improve OCR accuracy."""
        enhanced_versions = []
        try:
            # 1. Base high-contrast, sharpened version
            contrast = ImageEnhance.Contrast(image).enhance(2.0)
            sharpened = ImageEnhance.Sharpness(contrast).enhance(2.0)
            enhanced_versions.append(sharpened)

            # 2. Inverted version for light text on dark backgrounds (like the Browni package)
            # This is often the most effective for this type of packaging
            if image.mode == 'RGB':
                inverted_image = ImageOps.invert(image)
                inverted_contrast = ImageEnhance.Contrast(inverted_image).enhance(2.5)
                enhanced_versions.append(inverted_contrast)

            return enhanced_versions
        except Exception as e:
            logger.error(f"Failed to enhance image for OCR: {e}")
            return [image] # Return original on failure

    def correct_and_parse_text(self, raw_text: str) -> Dict:
        """
        Takes raw OCR text, applies corrections, and extracts structured data.
        """
        if not raw_text:
            return {'brand': '', 'name': '', 'full_text': ''}

        # Apply term corrections
        corrected_text = raw_text.upper()
        for wrong, correct in self.product_terms.items():
            corrected_text = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, corrected_text)

        lines = [line.strip() for line in corrected_text.split('\n') if line.strip()]
        
        # --- Brand Extraction ---
        found_brand = ''
        for line in lines:
            for brand in self.turkish_brands:
                if brand in line:
                    found_brand = brand
                    break
            if found_brand:
                break
        
        # --- Name Extraction ---
        # Combine all non-brand lines to form the product name
        product_name_parts = []
        for line in lines:
            # A line is part of the name if it's not the brand and not just junk
            if found_brand and found_brand in line:
                # If the brand is on a line with other text, take the other text
                other_text = line.replace(found_brand, '').strip()
                if len(other_text) > 2:
                    product_name_parts.append(other_text)
            elif len(line) > 2: # Avoid single characters or noise
                 product_name_parts.append(line)
        
        # Join the parts and clean up
        full_name = ' '.join(product_name_parts)
        # Remove the brand from the full name if it's still there
        if found_brand:
            full_name = full_name.replace(found_brand, '').strip()
        
        # Title case for readability
        full_name = full_name.title()

        return {
            'brand': found_brand.title(),
            'name': full_name,
            'full_text': corrected_text
        }

# Instantiate the enhancer for easy import
ocr_enhancer = TurkishProductOCREnhancer()
# api/tasks.py - UPDATED TO PASS IDs FOR DEBUGGING
import logging
import json
from celery import shared_task
from django.utils import timezone
from django.db import transaction

# --- Local Imports ---
from .models import Product, VisualSearchJob
from .util import (
    categorize_by_color,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    extract_text_from_product_image,
    get_vector_index,
    calculate_cosine_similarity,
)
from .serializers import ProductSerializer
from .json_encoder import CustomJSONEncoder
from .ocr_improvements import ocr_enhancer


logger = logging.getLogger(__name__)

@shared_task
def process_product_image(product_id: int):
    try:
        product = Product.objects.get(id=product_id)
        if not product.image:
            return f"Skipped: No image for product {product_id}"

        product.processing_status = 'processing'
        product.save(update_fields=['processing_status'])
        
        with product.image.open('rb') as f:
            image_bytes = f.read()

        # <<< FIX: Create a unique ID string and pass it to the util functions >>>
        debug_id = f"product_{product_id}"
        
        color_info = categorize_by_color(image_bytes, product_id=debug_id)
        visual_features = extract_visual_features_resnet(image_bytes, product_id=debug_id)
        text_embedding = get_color_aware_text_embedding(product.name, color_info.get('category', 'unknown'))

        product.color_category = color_info.get('category', 'unknown')
        product.color_confidence = color_info.get('confidence', 0.0)
        product.dominant_colors = color_info.get('colors', [])
        product.visual_embedding = visual_features.tolist()
        product.color_aware_text_embedding = text_embedding.tolist()
        product.processing_status = 'completed'
        product.processed_at = timezone.now()
        product.save()

        logger.info(f"Task completed: Processed product {product_id}")
        return f"Successfully processed product {product_id}"

    except Product.DoesNotExist:
        # ... (error handling is unchanged)
        return f"Error: Product {product_id} not found"
    except Exception as e:
        logger.error(f"Task failed for product {product_id}: {e}", exc_info=True)
        product.processing_status = 'failed'
        product.processing_error = str(e)
        product.save()
        return f"Error processing product {product_id}: {e}"

@shared_task(bind=True)
def perform_visual_search(self, job_id: str):
    logger.info(f"Task perform_visual_search started for job_id: {job_id}")
    try:
        job = VisualSearchJob.objects.get(id=job_id)
        job.status = 'PROCESSING'
        job.task_id = self.request.id
        job.save()

        with job.temp_image.open('rb') as f:
            image_bytes = f.read()
        
        # --- STAGE 1: VISUAL ANALYSIS (This is now solid) ---
        debug_id = f"search_{job_id}"
        color_info = categorize_by_color(image_bytes, product_id=debug_id)
        visual_features = extract_visual_features_resnet(image_bytes, product_id=debug_id)

        # --- STAGE 2: ENHANCED TEXT ANALYSIS ---
        # Get raw OCR text from the original image
        ocr_result = extract_text_from_product_image(image_bytes)
        
        # <<< USE THE NEW ENHANCER to parse the raw text >>>
        parsed_text_info = ocr_enhancer.correct_and_parse_text(ocr_result.get('text', ''))
        
        # Use the structured name for text embedding
        input_text_for_embedding = f"{parsed_text_info['brand']} {parsed_text_info['name']}".strip()
        input_text_vector = get_color_aware_text_embedding(input_text_for_embedding, color_info.get('category'))
        
        # Store all analysis results for the final response
        image_analysis_results = {
            **color_info,
            'ocr_raw': ocr_result.get('text', ''),
            'parsed_info': parsed_text_info
        }

        # --- STAGE 3 & 4 (Candidate Retrieval and Re-ranking) ---
        # This logic remains the same but will now benefit from much better text vectors.
        final_results = []
        if visual_features is not None:
            vector_index = get_vector_index()
            search_colors = list(set(c for c in [color_info.get('category'), color_info.get('secondary_category')] if c and c != 'unknown'))
            search_colors.append('unknown')
            visual_candidates = vector_index.search(visual_features, search_categories=search_colors, k=20)
            
            if visual_candidates:
                candidate_ids = [c['product_id'] for c in visual_candidates]
                product_queryset = Product.objects.filter(id__in=candidate_ids)
                
                for cand in visual_candidates:
                    product_obj = next((p for p in product_queryset if p.id == cand['product_id']), None)
                    if not product_obj: continue
                    visual_score = max(0.0, 1.0 - (cand.get('distance', 999) / 150.0))
                    textual_score = calculate_cosine_similarity(input_text_vector, product_obj.color_aware_text_embedding)
                    hybrid_score = (visual_score * 0.65) + (textual_score * 0.35)
                    product_data = ProductSerializer(product_obj).data
                    product_data['scores'] = {'visual_similarity': round(visual_score*100,1), 'text_similarity': round(textual_score*100,1), 'hybrid_score': round(hybrid_score*100,1)}
                    final_results.append(product_data)
        
        sorted_results = sorted(final_results, key=lambda x: x['scores']['hybrid_score'], reverse=True)
        
        job.status = 'SUCCESS'
        job.results = json.dumps({'candidates': sorted_results[:5], 'image_analysis': image_analysis_results}, cls=CustomJSONEncoder)
        job.completed_at = timezone.now()
        job.save()
        job.temp_image.delete(save=False)
        logger.info(f"Task perform_visual_search completed for job_id: {job_id}")

    except Exception as e:
        logger.error(f"CRITICAL failure in visual search task for job {job_id}: {e}", exc_info=True)
        try:
            job_to_fail = VisualSearchJob.objects.get(id=job_id)
            job_to_fail.status = 'FAILURE'
            job_to_fail.error_message = str(e)
            job_to_fail.completed_at = timezone.now()
            job_to_fail.save()
        except Exception as inner_e:
            logger.error(f"Could not even fail the job {job_id}: {inner_e}")
# api/tasks.py - FINAL, ACCURACY-ENHANCED VERSION
import logging
import json
from celery import shared_task
from django.utils import timezone
import numpy as np

# --- Local Imports ---
from .models import Product, VisualSearchJob
from .util import (
    categorize_by_color,
    extract_visual_features_resnet,
    get_color_aware_text_embedding,
    extract_text_from_product_image,
    get_vector_index,
    calculate_cosine_similarity
)
from .serializers import ProductSerializer
from .json_encoder import CustomJSONEncoder

logger = logging.getLogger(__name__)


@shared_task
def process_product_image(product_id: int):
    """
    Asynchronous task to process a product's image for AI features.
    This task is initiated when a new product is created.
    """
    try:
        product = Product.objects.get(id=product_id)
        if not product.image:
            logger.warning(f"Task skipped: Product {product_id} has no image.")
            return f"Skipped: No image for product {product_id}"

        # Mark as processing
        product.processing_status = 'processing'
        product.save(update_fields=['processing_status'])
        
        # Read image bytes from storage once
        with product.image.open('rb') as f:
            image_bytes = f.read()

        # The util functions will now use the enhanced pre-processing automatically
        color_info = categorize_by_color(image_bytes)
        visual_features = extract_visual_features_resnet(image_bytes)
        text_embedding = get_color_aware_text_embedding(product.name, color_info.get('category', 'unknown'))

        # Update product with all extracted AI features
        product.color_category = color_info.get('category', 'unknown')
        product.color_confidence = color_info.get('confidence', 0.0)
        product.dominant_colors = color_info.get('colors', [])
        product.visual_embedding = visual_features.tolist()
        product.color_aware_text_embedding = text_embedding.tolist()
        product.processing_status = 'completed'
        product.processing_error = None
        product.processed_at = timezone.now()
        product.save()

        logger.info(f"Task completed: Successfully processed product {product_id}")
        return f"Successfully processed product {product_id}"

    except Product.DoesNotExist:
        logger.error(f"Task failed: Product with ID {product_id} not found.")
        return f"Error: Product {product_id} not found"
    except Exception as e:
        logger.error(f"Task failed for product {product_id}: {e}", exc_info=True)
        try:
            # If an error occurs, mark the product as failed
            product.processing_status = 'failed'
            product.processing_error = str(e)
            product.save(update_fields=['processing_status', 'processing_error'])
        except Exception: 
            pass # Failsafe if product object is lost
        return f"Error processing product {product_id}: {e}"


@shared_task
def perform_visual_search(job_id: str):
    """
    Asynchronous task for a HYBRID visual and textual search, designed for robustness.
    This task is initiated when a user performs a visual search.
    """
    try:
        job = VisualSearchJob.objects.get(id=job_id)
        job.status = 'PROCESSING'
        job.save(update_fields=['status'])

        with job.temp_image.open('rb') as f:
            image_bytes = f.read()

        # --- STAGE 1: ANALYSIS OF USER'S INPUT IMAGE ---
        # The util functions automatically use the enhanced standardization pipeline
        color_info = categorize_by_color(image_bytes)
        visual_features = extract_visual_features_resnet(image_bytes)
        ocr_result = extract_text_from_product_image(image_bytes)
        
        # Generate SBERT vector for the input image's OCR text
        input_text = ocr_result.get('text', '')
        input_text_vector = get_color_aware_text_embedding(
            input_text, 
            color_info.get('category', 'unknown')
        )
        
        # --- STAGE 2: FAST VISUAL CANDIDATE RETRIEVAL (FAISS) ---
        primary_color = color_info.get('category', 'unknown')
        secondary_color = color_info.get('secondary_category', 'unknown')
        search_colors = list(set(c for c in [primary_color, secondary_color] if c and c != 'unknown'))
        search_colors.append('unknown') # Always include 'unknown' as a fallback
        
        vector_index = get_vector_index()
        # Retrieve more initial candidates (e.g., 20) to ensure the correct item is likely in the pool
        visual_candidates = vector_index.search(visual_features, search_categories=search_colors, k=20)

        # --- STAGE 3: DYNAMIC HYBRID RE-RANKING (VISUAL + SBERT) ---
        final_results = []
        if visual_candidates:
            candidate_ids = [c['product_id'] for c in visual_candidates]
            
            # Fetch all candidate products and their data in one efficient query
            product_queryset = Product.objects.filter(id__in=candidate_ids).prefetch_related('prices__store')
            
            # Estimate confidence in the OCR text from the input image.
            # Good OCR (more words, has numbers) gives more confidence in the text comparison.
            input_text_confidence = 0.5 + (0.3 if len(input_text.split()) > 3 else 0) + (0.2 if any(char.isdigit() for char in input_text) else 0)

            for cand in visual_candidates:
                product_obj = next((p for p in product_queryset if p.id == cand['product_id']), None)
                if not product_obj:
                    continue

                # a) Calculate Visual Score (normalized from L2 distance)
                # Lower distance is better. We convert it to a 0-1 similarity score.
                visual_score = max(0.0, 1.0 - (cand['distance'] / 150.0))

                # b) Calculate Textual Score (SBERT Cosine Similarity)
                textual_score = calculate_cosine_similarity(
                    input_text_vector,
                    product_obj.color_aware_text_embedding
                )

                # c) Calculate Dynamic Hybrid Score (the core of the robust solution)
                base_visual_weight = 0.6
                base_text_weight = 0.4
                
                # Boost text weight if OCR is reliable, otherwise it has less impact
                adjusted_text_weight = base_text_weight * input_text_confidence
                
                # If visual match is very strong, trust it more
                adjusted_visual_weight = base_visual_weight + (0.15 if visual_score > 0.9 else 0)
                
                # Normalize weights to ensure they sum to 1
                total_weight = adjusted_visual_weight + adjusted_text_weight
                hybrid_score = ((visual_score * adjusted_visual_weight) + (textual_score * adjusted_text_weight)) / total_weight if total_weight > 0 else 0

                # Serialize the product data and add all calculated scores
                product_data = ProductSerializer(product_obj).data
                product_data['scores'] = {
                    'visual_similarity': round(visual_score * 100, 2),
                    'text_similarity': round(textual_score * 100, 2),
                    'hybrid_score': round(hybrid_score * 100, 2)
                }
                final_results.append(product_data)
        
        # Re-rank all candidates based on the final hybrid score
        sorted_results = sorted(final_results, key=lambda x: x['scores']['hybrid_score'], reverse=True)

        # --- STAGE 4: SAVE FINAL JOB RESULTS ---
        job.status = 'SUCCESS'
        results_dict = {
            'candidates': sorted_results[:5], # Return the top 5 re-ranked results
            'image_analysis': {**color_info, 'ocr_text': input_text}
        }
        job.results = json.dumps(results_dict, cls=CustomJSONEncoder)
        job.completed_at = timezone.now()
        job.save()

        # Clean up the temporary image file
        job.temp_image.delete(save=False)
        return f"Search job {job_id} completed successfully with hybrid ranking."

    except Exception as e:
        logger.error(f"Visual search task failed for job {job_id}: {e}", exc_info=True)
        try:
            job = VisualSearchJob.objects.get(id=job_id)
            job.status = 'FAILURE'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
        except VisualSearchJob.DoesNotExist:
            pass
        raise e
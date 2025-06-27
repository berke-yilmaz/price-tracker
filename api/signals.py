# api/signals.py - CORRECTED
from django.db.models.signals import post_save, post_delete # <-- FIX IS HERE
from django.dispatch import receiver
from .models import Product
from .util import get_vector_index, build_vector_index
import numpy as np
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Product)
def update_product_in_index(sender, instance, created, update_fields=None, **kwargs):
    """
    Surgically adds or updates a product in the live FAISS index
    if it has just been processed.
    """
    if instance.processing_status == 'completed' and instance.visual_embedding:
        is_newly_processed = update_fields is None or 'processing_status' in update_fields or 'visual_embedding' in update_fields
        
        if created or is_newly_processed:
            try:
                logger.info(f"Signal Triggered: Product '{instance.name}' (ID: {instance.id}) is processed. Updating vector index.")
                vector_index = get_vector_index()
                vector_index.add_product(
                    product_id=instance.id,
                    feature_vector=np.array(instance.visual_embedding, dtype=np.float32),
                    color_category=instance.color_category
                )
                logger.info(f"✅ Signal Success: Added product {instance.id} to the live FAISS index for color '{instance.color_category}'.")
            except Exception as e:
                logger.error(f"Signal Error: Failed to add product {instance.id} to live index: {e}", exc_info=True)


@receiver(post_delete, sender=Product)
def remove_product_from_index(sender, instance, **kwargs):
    """
    Handles removing a product from the index by triggering a full rebuild.
    """
    try:
        if instance.visual_embedding:
            logger.info(f"Signal: Product {instance.id} deleted. Triggering index rebuild on next access.")
            build_vector_index()
    except Exception as e:
        logger.error(f"Signal Error: Failed to trigger index rebuild after deleting product {instance.id}: {e}", exc_info=True)
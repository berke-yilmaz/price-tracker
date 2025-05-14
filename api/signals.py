from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product
from .util import build_vector_index

@receiver([post_save, post_delete], sender=Product)
def update_vector_index(sender, **kwargs):
    """
    Ürün eklendiğinde, güncellendiğinde veya silindiğinde vektör indeksini yeniden oluştur
    """
    build_vector_index()
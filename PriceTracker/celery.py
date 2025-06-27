# PriceTracker/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PriceTracker.settings')

app = Celery('PriceTracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
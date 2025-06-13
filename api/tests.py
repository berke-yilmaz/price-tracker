from django.test import TestCase

# Create your tests here.

# api/tests.py
from django.test import TestCase
from .models import Store

class SimpleTestCase(TestCase):
    def test_store_creation(self):
        store = Store.objects.create(name='Test Store')
        self.assertEqual(store.name, 'Test Store')
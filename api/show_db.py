import os
import django
import sys

# Django projesinin kök dizinini Python path'ine ekleyin
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PriceTracker.settings')
django.setup()

from models import Product, Price
from django.contrib.auth.models import User

def show_database_contents():
    print("\n=== Users ===")
    for user in User.objects.all():
        print(f"Username: {user.username}, Email: {user.email}")

    print("\n=== Products ===")
    for product in Product.objects.all():
        print(f"\nID: {product.id}")
        print(f"Name: {product.name}")
        print(f"Barcode: {product.barcode}")
        print(f"Brand: {product.brand}")
        
        prices = Price.objects.filter(product=product)
        if prices.exists():
            print("Prices:")
            for price in prices:
                print(f"  - Store: {price.store}")
                print(f"    Price: {price.price}")
                print(f"    Date: {price.date}")

if __name__ == "__main__":
    show_database_contents()
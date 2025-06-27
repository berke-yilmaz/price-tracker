#!/bin/bash
# setup_test_data.sh - Complete test data setup script

echo "🏪 Setting up Price Tracker test data for Gebze, Turkey"
echo "================================================="

# Navigate to Django project directory
cd "$(dirname "$0")"

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this script from your Django project root."
    exit 1
fi

echo "📍 Current directory: $(pwd)"

# 1. First, let's see what we have
echo ""
echo "🔍 Step 1: Checking current database status..."
python manage.py shell << 'EOF'
from api.models import Product, Store, Price
from django.db.models import Count
print(f"📊 Current database status:")
print(f"   Products: {Product.objects.count()}")
print(f"   Stores: {Store.objects.count()}")
print(f"   Prices: {Price.objects.count()}")
EOF

# 2. Dry run to see what would be created
echo ""
echo "🔍 Step 2: Dry run - showing what will be created..."
echo "   (Note: Each product will now have a random number of prices from 2 to 5 stores)"
python manage.py populate_test_data --products=200 --dry-run

# 3. Ask for confirmation
echo ""
read -p "🤔 Do you want to proceed with creating/updating the test data? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled by user"
    exit 0
fi

# 4. Create the test data
echo ""
echo "🚀 Step 3: Creating test data (this may take a moment)..."
python manage.py populate_test_data --products=200 --reset

# 5. Verify the results
echo ""
echo "✅ Step 4: Verifying results..."
python manage.py shell << 'EOF'
from api.models import Product, Store, Price
from django.db.models import Count, Min, Max, Avg

print(f"📊 Final database status:")
print(f"   Products: {Product.objects.count()}")
print(f"   Stores: {Store.objects.count()}")
print(f"   Prices: {Price.objects.count()}")

print(f"\n🏪 Price distribution per store:")
for store in Store.objects.all():
    price_count = Price.objects.filter(store=store).count()
    print(f"   - {store.name}: {price_count} prices recorded")

print(f"\n🎯 Sample product price distribution:")
products_with_prices = Product.objects.annotate(
    price_count=Count('prices')
).filter(price_count__gt=0).order_by('-price_count')

if products_with_prices.exists():
    # Show a few products with the most and least prices
    print("\n   --- Products with most prices ---")
    for product in products_with_prices[:3]:
        print(f"   📦 {product.name}: {product.price_count} prices")

    print("\n   --- Products with fewest prices ---")
    for product in products_with_prices.reverse()[:3]:
        print(f"   📦 {product.name}: {product.price_count} prices")
else:
    print("No products with prices found to analyze.")
EOF

# 6. Show next steps
echo ""
echo "🎉 Test data setup complete!"
echo ""
echo "🔧 Useful commands:"
echo "   python manage.py shell         # Access Django shell"
echo "   python manage.py runserver     # Start development server"
echo ""
echo "🏪 Test stores created in Gebze:"
echo "   - Migros Gebze AVM"
echo "   - BİM Gebze Merkez"
echo "   - A101 Gebze Şubesi"
echo "   - ŞOK Market Gebze"
echo "   - CarrefourSA Gebze"
echo ""
echo "✅ Your Price Tracker system is now ready for more realistic testing!"
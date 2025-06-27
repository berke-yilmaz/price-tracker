import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
  TextInput,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../contexts/AuthContext';
import config from '../config';
import theme from '../constants/theme';
import { getImageUrl } from '../utils/imageUtils';
import StoreSelector from '../components/StoreSelector'; // Uses the new optimized component
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

// A simple, non-editable row to display existing prices
const PriceDisplayRow = ({ priceItem }) => (
  <View style={styles.priceRow}>
    <Ionicons name="storefront-outline" size={20} color={theme.colors.text.secondary} />
    <Text style={styles.storeName}>{priceItem.store_name}</Text>
    <Text style={styles.priceText}>₺{parseFloat(priceItem.price).toFixed(2)}</Text>
  </View>
);

export default function UpdatePriceScreen() {
  const router = useRouter();
  const { productId } = useLocalSearchParams();
  const { token } = useAuth();

  const [product, setProduct] = useState(null);
  const [prices, setPrices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for the unified "Update or Add" section
  const [selectedStore, setSelectedStore] = useState(null);
  const [priceValue, setPriceValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // This will hold the ID of the price if we are updating, or null if we are adding
  const [existingPriceId, setExistingPriceId] = useState(null);

  const fetchData = useCallback(async () => {
    // ... (fetchData function remains the same as your previous correct version)
    if (!productId) {
      setError('Product ID is missing.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [productRes, pricesRes] = await Promise.all([
        fetch(`${config.API_URL}/products/${productId}/`, { headers: { 'Authorization': `Token ${token}` } }),
        fetch(`${config.API_URL}/products/${productId}/prices/`, { headers: { 'Authorization': `Token ${token}` } }),
      ]);

      if (!productRes.ok || !pricesRes.ok) throw new Error('Failed to fetch product data.');
      
      const productData = await productRes.json();
      const pricesData = await pricesRes.json();

      setProduct(productData);
      setPrices(pricesData);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [productId, token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // This effect intelligently checks if a price exists when a store is selected
  useEffect(() => {
    if (selectedStore) {
      const existing = prices.find(p => p.store === selectedStore.id);
      if (existing) {
        setPriceValue(parseFloat(existing.price).toFixed(2));
        setExistingPriceId(existing.id);
      } else {
        setPriceValue('');
        setExistingPriceId(null);
      }
    } else {
        setPriceValue('');
        setExistingPriceId(null);
    }
  }, [selectedStore, prices]);

  const handleSubmitPrice = async () => {
    if (!selectedStore || !priceValue) {
      Alert.alert('Missing Info', 'Please select a store and enter a price.');
      return;
    }
    const numericPrice = parseFloat(priceValue.replace(',', '.'));
    if (isNaN(numericPrice) || numericPrice <= 0) {
      Alert.alert('Invalid Price', 'Please enter a valid positive number.');
      return;
    }

    setIsSubmitting(true);
    try {
        const isUpdate = !!existingPriceId;
        const url = isUpdate ? `${config.API_URL}/prices/${existingPriceId}/` : `${config.API_URL}/prices/`;
        const method = isUpdate ? 'PATCH' : 'POST';
        
        const body = isUpdate 
          ? { price: numericPrice.toFixed(2) }
          : { product: productId, store: selectedStore.id, price: numericPrice.toFixed(2) };

        const response = await fetch(url, {
            method: method,
            headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Failed to submit price.');
        
        Alert.alert('Success', `Price ${isUpdate ? 'updated' : 'added'} successfully!`);
        await fetchData(); // Refresh data
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.centerContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary[500]} />
      </SafeAreaView>
    );
  }
  if (error) {
    return (
      <SafeAreaView style={styles.centerContainer}>
        <Ionicons name="cloud-offline-outline" size={48} color={theme.colors.error[500]} />
        <Text style={styles.errorText}>{error}</Text>
        <Button title="Go Back" onPress={() => router.back()} />
      </SafeAreaView>
    );
  }
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={theme.colors.text.primary} />
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={1}>Manage Prices</Text>
        <View style={{width: 24}}/>
      </View>
      <ScrollView contentContainerStyle={styles.scrollContent}>

        {product && (
          <Card style={styles.productHeaderCard}>
            <Image source={{ uri: getImageUrl(product) }} style={styles.productImage} />
            <View style={styles.productInfo}>
              <Text style={styles.productName}>{product.name}</Text>
              <Text style={styles.productBrand}>{product.brand}</Text>
            </View>
          </Card>
        )}

        {/* SECTION 1: Display existing prices */}
        <Card style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Current Prices</Text>
          {prices.length > 0 ? (
            prices.map(p => <PriceDisplayRow key={p.id} priceItem={p} />)
          ) : (
            <Text style={styles.noPricesText}>No prices recorded yet.</Text>
          )}
        </Card>

        {/* SECTION 2: Unified Add/Update section */}
        <Card style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Update or Add Price</Text>
          <Text style={styles.sectionSubtitle}>Select a store to begin.</Text>
          <StoreSelector
            selectedStore={selectedStore}
            onStoreSelect={setSelectedStore}
          />
          {selectedStore && (
            <View style={styles.editContainer}>
                <Text style={styles.label}>{existingPriceId ? `Update price for ${selectedStore.name}` : `Add price for ${selectedStore.name}`}</Text>
                <View style={styles.priceInputContainer}>
                    <TextInput
                        style={styles.priceInput}
                        value={priceValue}
                        onChangeText={setPriceValue}
                        keyboardType="decimal-pad"
                        placeholder="0.00"
                    />
                    <Text style={styles.currencySymbol}>₺</Text>
                </View>
                <Button
                    title={existingPriceId ? "Update Price" : "Save New Price"}
                    onPress={handleSubmitPrice}
                    loading={isSubmitting}
                    disabled={isSubmitting}
                    style={{ marginTop: 16 }}
                />
            </View>
          )}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}


const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  scrollContent: { paddingBottom: 40 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
  backButton: { padding: 4 },
  title: { fontSize: 20, fontWeight: '600', flex: 1, textAlign: 'center' },
  productHeaderCard: { flexDirection: 'row', alignItems: 'center', margin: 16, padding: 16 },
  productImage: { width: 70, height: 70, borderRadius: theme.borderRadius.lg, marginRight: 16 },
  productInfo: { flex: 1 },
  productName: { fontSize: 18, fontWeight: 'bold', color: theme.colors.text.primary },
  productBrand: { fontSize: 14, color: theme.colors.text.secondary, marginTop: 4 },
  sectionCard: { marginHorizontal: 16, marginTop: 8, marginBottom: 8 },
  sectionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 4 },
  sectionSubtitle: { fontSize: 14, color: theme.colors.text.secondary, marginBottom: 16 },
  noPricesText: { color: theme.colors.text.secondary, fontStyle: 'italic', textAlign: 'center', paddingVertical: 16 },
  priceRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[100] },
  storeName: { flex: 1, fontSize: 16, color: theme.colors.text.primary, marginLeft: 12 },
  priceText: { fontSize: 16, fontWeight: 'bold', color: theme.colors.success[600] },
  editContainer: { marginTop: 16, paddingTop: 16, borderTopWidth: 1, borderTopColor: theme.colors.gray[200] },
  label: { fontSize: 16, fontWeight: '500', marginBottom: 8 },
  priceInputContainer: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: theme.colors.gray[300], borderRadius: theme.borderRadius.lg },
  priceInput: { flex: 1, padding: 16, fontSize: 18, fontWeight: '500' },
  currencySymbol: { fontSize: 18, paddingRight: 16, color: theme.colors.text.secondary },
});
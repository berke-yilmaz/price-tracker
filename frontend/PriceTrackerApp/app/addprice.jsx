// app/addprice.jsx - CORRECTED
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  TextInput,
  Alert,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import StoreSelector from '../components/StoreSelector';
import theme from '../constants/theme';
import config from '../config';
import { Ionicons } from '@expo/vector-icons';

export default function AddPriceScreen() {
  const router = useRouter();
  const { productId, barcode, productName: initialProductName } = useLocalSearchParams();
  const { token } = useAuth();
  
  const [productName, setProductName] = useState(initialProductName || '');
  const [selectedStore, setSelectedStore] = useState(null); // This will now hold the full store object
  const [price, setPrice] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    // ⭐ FIX: We now check selectedStore, which is an object.
    if (!selectedStore || !price) {
      Alert.alert('Error', 'Please select a store and enter a price.');
      return;
    }

    const numericPrice = parseFloat(price.replace(',', '.'));
    if (isNaN(numericPrice) || numericPrice <= 0) {
      Alert.alert('Error', 'Please enter a valid price.');
      return;
    }

    if (!productId) {
      Alert.alert('Error', 'Product information is missing. Please go back and select a product first.');
      return;
    }

    setLoading(true);

    try {
      const priceData = {
        product: productId,
        store: selectedStore.id, // Use the store ID from the selected object
        price: numericPrice.toFixed(2),
      };

      const response = await fetch(`${config.API_URL}/prices/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(priceData),
      });

      if (response.ok) {
        Alert.alert(
          'Success',
          'Price added successfully!',
          [{ text: 'OK', onPress: () => router.push('/(tabs)/history') }]
        );
      } else {
        const errorData = await response.json();
        console.error('API Error:', errorData);
        
        if (errorData.non_field_errors && errorData.non_field_errors[0].includes('unique_daily_price')) {
          Alert.alert('Info', 'You have already added a price for this product at this store today.');
        } else {
          const errorMessage = errorData.detail || Object.values(errorData).flat().join('\n') || 'Failed to add price.';
          Alert.alert('Error', errorMessage);
        }
      }
    } catch (error) {
      console.error('Add price error:', error);
      Alert.alert('Error', 'An unexpected error occurred while adding the price.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollContainer}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color={theme.colors.text.primary} />
          </TouchableOpacity>
          <Text style={styles.title}>Add Price</Text>
          <View style={{ width: 24 }} />
        </View>

        <View style={styles.form}>
          <View style={styles.productInfoCard}>
             <Text style={styles.productInfoLabel}>Product</Text>
             <Text style={styles.productInfoName}>{productName}</Text>
             {barcode && <Text style={styles.productInfoBarcode}>Barcode: {barcode}</Text>}
          </View>

          <Text style={styles.label}>Store *</Text>
          {/* ⭐ FIX: The component is now self-contained. We just pass the selectedStore object and the callback. */}
          <StoreSelector
            selectedStore={selectedStore}
            onStoreSelect={setSelectedStore}
          />

          <Text style={styles.label}>Price *</Text>
          <View style={styles.priceInputContainer}>
            <TextInput
              style={styles.priceInput}
              value={price}
              onChangeText={setPrice}
              placeholder="0.00"
              keyboardType="decimal-pad"
              placeholderTextColor={theme.colors.gray[400]}
            />
            <Text style={styles.currency}>₺</Text>
          </View>

          <TouchableOpacity 
            style={[styles.saveButton, loading && styles.disabledButton]}
            onPress={handleSave}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={theme.colors.text.inverse} />
            ) : (
              <Text style={styles.saveButtonText}>Save Price</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// Styles remain the same
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollContainer: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
  },
  title: {
    fontSize: theme.typography.fontSize.lg,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
  },
  form: {
    padding: theme.spacing.lg,
  },
  productInfoCard: {
    backgroundColor: theme.colors.primary[50],
    padding: theme.spacing.lg,
    borderRadius: theme.borderRadius.lg,
    marginBottom: theme.spacing.xl,
    borderLeftWidth: 4,
    borderLeftColor: theme.colors.primary[500],
  },
  productInfoLabel: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.xs,
  },
  productInfoName: {
    fontSize: theme.typography.fontSize.xl,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  productInfoBarcode: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    fontFamily: 'monospace',
  },
  label: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  priceInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    borderWidth: 1,
    borderColor: theme.colors.gray[300],
  },
  priceInput: {
    flex: 1,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.primary,
  },
  currency: {
    fontSize: theme.typography.fontSize.lg,
    color: theme.colors.text.secondary,
    paddingRight: theme.spacing.md,
    fontWeight: theme.typography.fontWeight.medium,
  },
  saveButton: {
    backgroundColor: theme.colors.success[500],
    paddingVertical: theme.spacing.lg,
    borderRadius: theme.borderRadius.xl,
    marginTop: theme.spacing.xl,
    alignItems: 'center',
  },
  disabledButton: {
    opacity: 0.6,
  },
  saveButtonText: {
    color: theme.colors.text.inverse,
    fontSize: theme.typography.fontSize.lg,
    fontWeight: theme.typography.fontWeight.bold,
  },
});
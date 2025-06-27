// app/addproduct.jsx - FINAL ENHANCED VERSION
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
  Image,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import theme from '../constants/theme';
import config from '../config';
import { Ionicons } from '@expo/vector-icons';

// Re-using the OCR parser from EnhancedProductCreation
const parseOcrText = (text) => {
    if (!text || typeof text !== 'string') return { name: '', brand: '', weight: '' };
    const lines = text.split(/\||\n/).map(line => line.trim()).filter(Boolean);
    const knownBrands = ['ÜLKER', 'ETİ', 'PINAR', 'SÜTAŞ', 'NESTLE', 'DANONE', 'COCA-COLA', 'PEPSI'];
    const weightRegex = /(\d+(?:\.\d+)?)\s*(kg|g|gr|ml|l|lt|%)/i;
    let name = lines[0] || '';
    let brand = '';
    let weight = '';
    lines.forEach(line => {
        const upperLine = line.toUpperCase();
        for (const b of knownBrands) {
            if (upperLine.includes(b)) brand = line;
        }
        const weightMatch = line.match(weightRegex);
        if (weightMatch) weight = weightMatch[0];
    });
    if (brand && name.toUpperCase().includes(brand.toUpperCase())) {
       name = name.replace(new RegExp(brand, 'i'), '').trim();
    }
    return { name, brand, weight };
};

export default function AddProductScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const { barcode, imageUri, analysisResult } = useLocalSearchParams(); 
  
  const [productData, setProductData] = useState({
    name: '', barcode: barcode || '', brand: '', category: '', weight: '', ingredients: '',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // ⭐ NEW: We parse the JSON string back into an object
    if (analysisResult) {
      try {
        const parsedAnalysis = JSON.parse(analysisResult);
        // We now have access to ocr_text, dominant_colors, etc.
        if (parsedAnalysis && parsedAnalysis.ocr_text) {
          const parsedOcr = parseOcrText(parsedAnalysis.ocr_text);
          setProductData(prev => ({
            ...prev,
            name: parsedOcr.name,
            brand: parsedOcr.brand,
            weight: parsedOcr.weight,
          }));
        }
      } catch (e) {
        console.error("Failed to parse analysis result:", e);
      }
    }
  }, [analysisResult]); // Dependency is now analysisResult

  const handleInputChange = (field, value) => {
    setProductData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!productData.name) {
      Alert.alert('Error', 'Product name is required');
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      Object.keys(productData).forEach(key => {
        if (productData[key]) formData.append(key, productData[key]);
      });
      
      if (imageUri) {
        formData.append('image', { uri: imageUri, type: 'image/jpeg', name: 'product.jpg' });
      }

      // We use the same unified endpoint for all creation paths
      const response = await fetch(`${config.API_URL}/products/create-from-image/`, {
        method: 'POST',
        headers: { 'Authorization': `Token ${token}` },
        body: formData,
      });

      const result = await response.json();
      
      if (response.ok && result.success) {
        Alert.alert(
          'Success',
          'Product added successfully!',
          [
            { text: 'Add Price', onPress: () => router.push({ pathname: '/addprice', params: { productId: result.product.id, productName: result.product.name, barcode: result.product.barcode } }) },
            { text: 'Done', onPress: () => router.replace('/(tabs)/') }
          ]
        );
      } else {
        throw new Error(result.error || result.detail || 'Failed to add product');
      }
    } catch (error) {
      console.error('Add product error:', error);
      Alert.alert('Error', error.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color={theme.colors.text.primary} />
          </TouchableOpacity>
          <Text style={styles.title}>Add New Product</Text>
          <View style={{ width: 24 }} />
        </View>

        <View style={styles.form}>
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.selectedImage} />
          ) : (
            barcode && (
              <View style={styles.barcodeInfo}>
                <Ionicons name="barcode" size={24} color={theme.colors.primary[600]} />
                <Text style={styles.barcodeText}>Barcode: {barcode}</Text>
              </View>
            )
          )}
          
          <Text style={styles.label}>Product Name*</Text>
          <TextInput style={styles.input} value={productData.name} onChangeText={(text) => handleInputChange('name', text)} placeholder="e.g., Ülker Albeni" />

          <Text style={styles.label}>Brand</Text>
          <TextInput style={styles.input} value={productData.brand} onChangeText={(text) => handleInputChange('brand', text)} placeholder="e.g., Ülker" />

          <Text style={styles.label}>Barcode</Text>
          <TextInput style={styles.input} value={productData.barcode} onChangeText={(text) => handleInputChange('barcode', text)} placeholder="Scan or enter barcode" keyboardType="number-pad" editable={!barcode} />

          <Text style={styles.label}>Category</Text>
          <TextInput style={styles.input} value={productData.category} onChangeText={(text) => handleInputChange('category', text)} placeholder="e.g., Snack, Chocolate" />

          <Text style={styles.label}>Weight / Volume</Text>
          <TextInput style={styles.input} value={productData.weight} onChangeText={(text) => handleInputChange('weight', text)} placeholder="e.g., 40g, 1L" />

          <Text style={styles.label}>Ingredients (Optional)</Text>
          <TextInput style={[styles.input, styles.multilineInput]} value={productData.ingredients} onChangeText={(text) => handleInputChange('ingredients', text)} placeholder="Enter ingredients" multiline />

          <TouchableOpacity 
            style={[styles.submitButton, loading && styles.disabledButton]}
            onPress={handleSubmit}
            disabled={loading}
          >
            {loading ? <ActivityIndicator color="white" /> : <Text style={styles.submitButtonText}>Save Product</Text>}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  scrollContent: { flexGrow: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: theme.spacing.lg, backgroundColor: theme.colors.surface, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
  title: { fontSize: theme.typography.fontSize.lg, fontWeight: theme.typography.fontWeight.bold, color: theme.colors.text.primary },
  form: { padding: theme.spacing.lg },
  selectedImage: { width: '100%', height: 200, borderRadius: theme.borderRadius.lg, marginBottom: theme.spacing.lg, alignSelf: 'center', backgroundColor: theme.colors.gray[100] },
  barcodeInfo: { flexDirection: 'row', alignItems: 'center', backgroundColor: theme.colors.primary[50], padding: theme.spacing.md, borderRadius: theme.borderRadius.lg, marginBottom: theme.spacing.lg },
  barcodeText: { fontSize: theme.typography.fontSize.base, color: theme.colors.primary[700], marginLeft: theme.spacing.sm, fontFamily: 'monospace' },
  label: { fontSize: theme.typography.fontSize.base, fontWeight: theme.typography.fontWeight.semibold, color: theme.colors.text.primary, marginBottom: theme.spacing.sm, marginTop: theme.spacing.md },
  input: { backgroundColor: theme.colors.surface, paddingVertical: theme.spacing.md, paddingHorizontal: theme.spacing.md, borderRadius: theme.borderRadius.lg, fontSize: theme.typography.fontSize.base, borderWidth: 1, borderColor: theme.colors.gray[300] },
  multilineInput: { height: 100, textAlignVertical: 'top' },
  submitButton: { backgroundColor: theme.colors.primary[500], paddingVertical: theme.spacing.lg, borderRadius: theme.borderRadius.xl, marginTop: theme.spacing.xl, marginBottom: theme.spacing.lg, alignItems: 'center' },
  disabledButton: { opacity: 0.7 },
  submitButtonText: { color: 'white', fontSize: theme.typography.fontSize.base, fontWeight: theme.typography.fontWeight.bold },
});
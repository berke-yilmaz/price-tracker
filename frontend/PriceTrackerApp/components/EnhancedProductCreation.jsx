// components/EnhancedProductCreation.jsx - FINAL OCR FIX
import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, Alert, ActivityIndicator, Image, ScrollView, Modal, SafeAreaView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../contexts/AuthContext';
import theme from '../constants/theme';
import config from '../config';
import StoreSelector from './StoreSelector';

const parseOcrText = (text) => {
    if (!text || typeof text !== 'string') return { name: '', brand: '', weight: '' };
    const lines = text.split(/\||\n/).map(line => line.trim()).filter(Boolean);
    const knownBrands = ['VIVIDENT', 'STORMING', 'ÜLKER', 'ETİ', 'PINAR', 'SÜTAŞ', 'NESTLE', 'DANONE', 'COCA-COLA', 'PEPSI', 'TORKU', 'İÇİM', 'HARNAS'];
    const weightRegex = /(\d[\d.,]*\s*(?:kg|g|gr|ml|l|lt|litre|cl|cc)\b)/i;
    const junkWords = ['içindekiler', 'ingredients', 'üretici', 'tarihi', 'enerji ve besin'];
    let brand = '', weight = '', name = '';
    lines.forEach(line => {
      for (const b of knownBrands) if (line.toUpperCase().includes(b)) brand = b.charAt(0) + b.slice(1).toLowerCase();
      const weightMatch = line.match(weightRegex);
      if (weightMatch && !weight) weight = weightMatch[0];
    });
    let potentialNames = lines.filter(line => !knownBrands.some(b => line.toUpperCase().includes(b)) && !weightRegex.test(line.toLowerCase()) && !junkWords.some(j => line.toLowerCase().includes(j)) && line.length > 2);
    name = potentialNames.sort((a, b) => b.length - a.length)[0] || '';
    if (name && brand) name = name.replace(new RegExp(brand, 'i'), '').trim();
    if (brand && !name && lines.length > 0) name = lines.sort((a, b) => b.length - a.length)[0] || name;
    return { name, brand, weight };
};

export default function EnhancedProductCreation({
  visible, onClose, imageUri, ocrResult, onProductCreated
}) {
  const { token } = useAuth();
  const [productData, setProductData] = useState({ name: '', brand: '', category: '', weight: '', ingredients: '' });
  const [selectedStore, setSelectedStore] = useState(null);
  const [price, setPrice] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);

  // ⭐ FINAL FIX: Extract OCR data from your specific backend format ⭐
  const extractOcrDataFromBackend = () => {
    console.log('🔍 Processing OCR result:', ocrResult);
    
    if (!ocrResult) return { hasOcr: false, success: false, data: null };

    let data = ocrResult;
    
    // Parse JSON string if needed
    if (typeof ocrResult === 'string') {
      try {
        data = JSON.parse(ocrResult);
      } catch (e) {
        console.log('❌ JSON parse failed:', e);
        return { hasOcr: true, success: false, data: null };
      }
    }

    // ⭐ NEW: Check for your backend's specific format ⭐
    const possibleTexts = [
      // Your backend format (from the logs)
      data.ocr_raw,
      data.parsed_info?.full_text,
      data.parsed_info?.name,
      
      // Also check the original paths as fallback
      data.ocr_text,
      data.text,
      data.extracted_text,
      data.analysis?.ocr_text,
      data.image_analysis?.ocr_text,
      data.results?.image_analysis?.ocr_text,
    ];

    // Find the first valid text
    for (let i = 0; i < possibleTexts.length; i++) {
      const textValue = possibleTexts[i];
      if (textValue && typeof textValue === 'string' && textValue.trim().length > 0) {
        console.log(`✅ Found OCR text at path ${i}:`, textValue);
        
        // ⭐ NEW: Use backend parsed info if available ⭐
        let extractedData = null;
        if (data.parsed_info) {
          console.log('🎯 Using backend parsed info:', data.parsed_info);
          extractedData = {
            name: data.parsed_info.name || '',
            brand: data.parsed_info.brand || '',
            weight: '', // Add weight parsing later if needed
          };
        }
        
        return { 
          hasOcr: true, 
          success: true, 
          text: textValue,
          extractedData: extractedData,
          backendParsed: !!data.parsed_info
        };
      }
    }

    console.log('❌ No valid OCR text found');
    console.log('Available keys:', Object.keys(data));
    return { hasOcr: true, success: false, data: null };
  };
  
  useEffect(() => {
    if (visible) {
      setStep(1);
      
      const ocrData = extractOcrDataFromBackend();
      
      if (ocrData.success) {
        console.log('🚀 Processing OCR data...');
        
        let finalData = {};
        
        // ⭐ NEW: Use backend extracted data if available, otherwise parse manually ⭐
        if (ocrData.backendParsed && ocrData.extractedData) {
          console.log('✅ Using backend parsed data:', ocrData.extractedData);
          finalData = ocrData.extractedData;
        } else if (ocrData.text) {
          console.log('🔧 Parsing OCR text manually:', ocrData.text);
          finalData = parseOcrText(ocrData.text);
        }
        
        console.log('🎉 Final extracted data:', finalData);
        setProductData(prev => ({ ...prev, ...finalData }));
      } else {
        console.log('❌ OCR processing failed');
      }
    } else {
      // Reset form when modal closes
      setProductData({ name: '', brand: '', category: '', weight: '', ingredients: '' });
      setSelectedStore(null);
      setPrice('');
      setLoading(false);
    }
  }, [visible, ocrResult]);

  const handleCreateProduct = async () => {
    if (!productData.name.trim()) {
      Alert.alert('Validation Error', 'Product name is required');
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      Object.keys(productData).forEach(key => { 
        if (productData[key]) formData.append(key, productData[key]); 
      });
      if (imageUri) formData.append('image', { uri: imageUri, type: 'image/jpeg', name: 'product.jpg' });

      const productResponse = await fetch(`${config.API_URL}/products/create-from-image/`, {
        method: 'POST', 
        headers: { 'Authorization': `Token ${token}` }, 
        body: formData,
      });

      const productResult = await productResponse.json();
      if (!productResponse.ok || !productResult.success) {
        throw new Error(productResult.error || 'Failed to create product.');
      }
      
      const createdProduct = productResult.product;
      let priceMessage = '';
      
      if (price && selectedStore) {
        const numericPrice = parseFloat(price.replace(',', '.'));
        if (numericPrice > 0) {
          const priceData = { 
            product: createdProduct.id, 
            store: selectedStore.id, 
            price: numericPrice.toFixed(2) 
          };
          const priceResponse = await fetch(`${config.API_URL}/prices/`, {
            method: 'POST', 
            headers: { 
              'Authorization': `Token ${token}`, 
              'Content-Type': 'application/json' 
            }, 
            body: JSON.stringify(priceData),
          });
          priceMessage = priceResponse.ok ? ' Price added successfully.' : ' Product created, but failed to add price.';
        }
      }
      
      Alert.alert(
        'Success!', 
        `Product "${createdProduct.name}" created.${priceMessage}`, 
        [{ 
          text: 'OK', 
          onPress: () => { 
            if (onProductCreated) onProductCreated(createdProduct); 
            onClose(); 
          }
        }]
      );
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const renderStepIndicator = () => (
    <View style={styles.stepIndicator}>
      <View style={[styles.step, step >= 1 && styles.stepActive]}>
        <Text style={[styles.stepNumber, step >= 1 && styles.stepNumberActive]}>1</Text>
      </View>
      <View style={[styles.stepLine, step >= 2 && styles.stepLineActive]} />
      <View style={[styles.step, step >= 2 && styles.stepActive]}>
        <Text style={[styles.stepNumber, step >= 2 && styles.stepNumberActive]}>2</Text>
      </View>
    </View>
  );

  // ⭐ FINAL: Correct status detection for your format ⭐
  const ocrData = extractOcrDataFromBackend();

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={24} color={theme.colors.text.primary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Add New Product</Text>
          {renderStepIndicator()}
        </View>

        {step === 1 ? (
          <ScrollView style={styles.content}>
            <Text style={styles.stepTitle}>Edit Product Information</Text>
            
            {/* ⭐ FINAL: Correct status messages ⭐ */}
            {ocrData.hasOcr && !ocrData.success && (
              <View style={styles.ocrInfoError}>
                <Text style={styles.ocrInfoText}>
                  AI Analysis Failed: Could not process image text
                </Text>
                <Text style={styles.ocrInfoSubtext}>
                  You can still manually enter the product information below
                </Text>
              </View>
            )}
            
            {ocrData.hasOcr && ocrData.success && (
              <View style={styles.ocrInfoSuccess}>
                <Text style={styles.ocrInfoSuccessText}>
                  ✅ AI extracted product information from image
                  {ocrData.backendParsed && ' (using backend parsing)'}
                </Text>
              </View>
            )}
            
            {imageUri && <Image source={{ uri: imageUri }} style={styles.image} />}
            
            <Text style={styles.label}>Product Name *</Text>
            <TextInput 
              style={styles.input} 
              value={productData.name} 
              onChangeText={v => setProductData(p => ({...p, name: v}))} 
              placeholder="e.g., Ülker Coco Star"
            />
            
            <Text style={styles.label}>Brand</Text>
            <TextInput 
              style={styles.input} 
              value={productData.brand} 
              onChangeText={v => setProductData(p => ({...p, brand: v}))} 
              placeholder="e.g., Ülker"
            />
            
            <Text style={styles.label}>Weight / Volume</Text>
            <TextInput 
              style={styles.input} 
              value={productData.weight} 
              onChangeText={v => setProductData(p => ({...p, weight: v}))} 
              placeholder="e.g., 40g, 1L"
            />
            
            <Text style={styles.label}>Category</Text>
            <TextInput 
              style={styles.input} 
              value={productData.category} 
              onChangeText={v => setProductData(p => ({...p, category: v}))} 
              placeholder="e.g., Snack, Chocolate"
            />
            
            <Text style={styles.label}>Ingredients (Optional)</Text>
            <TextInput 
              style={[styles.input, styles.multiline]} 
              value={productData.ingredients} 
              onChangeText={v => setProductData(p => ({...p, ingredients: v}))} 
              placeholder="List main ingredients..." 
              multiline
            />
          </ScrollView>
        ) : (
          <ScrollView style={styles.content}>
            <Text style={styles.stepTitle}>Add Store & Price (Optional)</Text>
            <Text style={styles.label}>Store</Text>
            <StoreSelector 
              selectedStore={selectedStore} 
              onStoreSelect={setSelectedStore} 
            />
            <Text style={styles.label}>Price *</Text>
            <View style={styles.priceContainer}>
              <TextInput 
                style={styles.priceInput} 
                value={price} 
                onChangeText={setPrice} 
                placeholder="0.00" 
                keyboardType="decimal-pad" 
              />
              <Text style={styles.currency}>₺</Text>
            </View>
            <Text style={styles.note}>You can skip this and add prices later.</Text>
          </ScrollView>
        )}

        <View style={styles.buttonContainer}>
          {step === 1 ? (
            <>
              <TouchableOpacity style={[styles.button, styles.cancelButton]} onPress={onClose}>
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={[styles.button, styles.nextButton]} 
                onPress={() => setStep(2)} 
                disabled={!productData.name.trim()}
              >
                <Text style={styles.nextButtonText}>Next</Text>
                <Ionicons name="arrow-forward" size={16} color="white"/>
              </TouchableOpacity>
            </>
          ) : (
            <>
              <TouchableOpacity style={[styles.button, styles.backButton]} onPress={() => setStep(1)}>
                <Ionicons name="arrow-back" size={16} color={theme.colors.primary[500]} />
                <Text style={styles.backButtonText}>Back</Text>
              </TouchableOpacity>
              <TouchableOpacity 
                style={[styles.button, styles.createButton, loading && styles.disabled]} 
                onPress={handleCreateProduct} 
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="white"/> 
                ) : (
                  <Text style={styles.createButtonText}>Save</Text>
                )}
              </TouchableOpacity>
            </>
          )}
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  header: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between', 
    paddingHorizontal: 16, 
    paddingVertical: 12, 
    borderBottomWidth: 1, 
    borderBottomColor: theme.colors.gray[200] 
  },
  closeButton: { padding: 8 },
  headerTitle: { flex: 1, textAlign: 'center', fontSize: 18, fontWeight: '600' },
  stepIndicator: { flexDirection: 'row', alignItems: 'center' },
  step: { 
    width: 32, 
    height: 32, 
    borderRadius: 16, 
    backgroundColor: theme.colors.gray[300], 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  stepActive: { backgroundColor: theme.colors.primary[500] },
  stepNumber: { color: theme.colors.text.primary, fontWeight: '600' },
  stepNumberActive: { color: 'white' },
  stepLine: { width: 20, height: 2, backgroundColor: theme.colors.gray[300] },
  stepLineActive: { backgroundColor: theme.colors.primary[500] },
  content: { flex: 1, padding: 16 },
  stepTitle: { fontSize: 22, fontWeight: '700', marginBottom: 16 },
  ocrInfoError: { 
    backgroundColor: theme.colors.error[50], 
    padding: 12, 
    borderRadius: 8, 
    marginBottom: 12, 
    borderWidth: 1, 
    borderColor: theme.colors.error[200] 
  },
  ocrInfoText: { color: theme.colors.error[700], fontWeight: '500' },
  ocrInfoSubtext: { color: theme.colors.error[600], fontSize: 12, marginTop: 4 },
  ocrInfoSuccess: { 
    backgroundColor: theme.colors.success[50], 
    padding: 12, 
    borderRadius: 8, 
    marginBottom: 12, 
    borderWidth: 1, 
    borderColor: theme.colors.success[200] 
  },
  ocrInfoSuccessText: { color: theme.colors.success[700], fontWeight: '500' },
  image: { 
    width: '100%', 
    height: 200, 
    borderRadius: 12, 
    marginBottom: 16, 
    alignSelf: 'center', 
    backgroundColor: '#f0f0f0' 
  },
  label: { fontSize: 16, fontWeight: '500', marginBottom: 8, marginTop: 12 },
  input: { borderWidth: 1, borderColor: '#ccc', padding: 12, borderRadius: 8, fontSize: 16 },
  multiline: { height: 100, textAlignVertical: 'top' },
  priceContainer: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    borderWidth: 1, 
    borderColor: '#ccc', 
    borderRadius: 8 
  },
  priceInput: { flex: 1, padding: 12, fontSize: 16 },
  currency: { paddingRight: 16, fontSize: 16, color: '#666' },
  note: { marginTop: 8, color: '#666', fontSize: 12, fontStyle: 'italic' },
  buttonContainer: { 
    flexDirection: 'row', 
    padding: 16, 
    borderTopWidth: 1, 
    borderColor: '#eee', 
    gap: 12 
  },
  button: { 
    flex: 1, 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'center', 
    paddingVertical: 14, 
    borderRadius: 12, 
    gap: 8 
  },
  cancelButton: { backgroundColor: theme.colors.gray[200] },
  cancelButtonText: { color: theme.colors.text.primary, fontWeight: '600' },
  nextButton: { backgroundColor: theme.colors.primary[500] },
  nextButtonText: { color: 'white', fontWeight: '600' },
  backButton: { 
    backgroundColor: 'transparent', 
    borderWidth: 1, 
    borderColor: theme.colors.primary[300] 
  },
  backButtonText: { color: theme.colors.primary[500], fontWeight: '600' },
  createButton: { backgroundColor: theme.colors.success[500] },
  createButtonText: { color: 'white', fontWeight: '600' },
  disabled: { opacity: 0.6 }
});
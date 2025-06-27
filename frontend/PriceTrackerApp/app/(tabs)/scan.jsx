// app/(tabs)/scan.jsx - FIXED
import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Alert, ActivityIndicator, SafeAreaView } from 'react-native';
// ⭐ --- START OF FIX --- ⭐
// Import useIsFocused from @react-navigation/native, NOT from expo-router
import { useIsFocused } from '@react-navigation/native'; 
import { useRouter } from 'expo-router';
// ⭐ --- END OF FIX --- ⭐
import { useAuth } from '../../contexts/AuthContext';
import config from '../../config';
import EnhancedScanner from '../../components/scanner/EnhancedScanner';
import SimilarityResultsModal from '../../components/SimilarityResultsModal';
import BarcodeDisambiguationModal from '../../components/scanner/BarcodeDisambiguationModal';

export default function ScanScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const isFocused = useIsFocused();
  const pollIntervalRef = useRef(null);

  const [statusText, setStatusText] = useState('');
  const [modalType, setModalType] = useState(null);
  
  const [similarityData, setSimilarityData] = useState({ candidates: [], imageUri: null, analysis: null });
  const [barcodeData, setBarcodeData] = useState({ products: [], barcode: null });

  // Cleanup polling when the screen is left
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const resetState = () => {
    setStatusText('');
    setModalType(null);
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  useEffect(() => {
    if (!isFocused) {
      resetState();
    }
  }, [isFocused]);

  const pollForResult = (jobId) => {
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${config.API_URL}/products/visual-search-result/?job_id=${jobId}`, {
          headers: { 'Authorization': `Token ${token}` },
        });

        if (!response.ok) {
            throw new Error("Failed to get job status.");
        }

        const result = await response.json();
        setStatusText(`Status: ${result.status}...`);

        if (result.status === 'SUCCESS') {
          clearInterval(pollIntervalRef.current);
          setStatusText('Search complete!');
          const finalResult = result.results;
          setSimilarityData({
              candidates: finalResult.candidates,
              imageUri: similarityData.imageUri,
              analysis: finalResult.image_analysis,
          });
          setModalType('similarity');
        } else if (result.status === 'FAILURE') {
          clearInterval(pollIntervalRef.current);
          Alert.alert('Error', result.error || 'Visual search failed during processing.');
          resetState();
        }
      } catch (error) {
        clearInterval(pollIntervalRef.current);
        Alert.alert('Connection Error', 'Could not poll for results.');
        resetState();
      }
    }, 2500);
  };

  const handlePhotoAction = async (photo) => {
    if (!photo?.uri) return;
    setStatusText('Uploading image...');
    setSimilarityData({ candidates: [], imageUri: photo.uri, analysis: null });
    
    try {
      const formData = new FormData();
      formData.append('image', { uri: photo.uri, type: 'image/jpeg', name: 'scan.jpg' });

      const response = await fetch(`${config.API_URL}/products/start-visual-search/`, {
        method: 'POST',
        headers: { 'Authorization': `Token ${token}` },
        body: formData,
      });

      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(result.error || 'Failed to start search job.');
      }
      
      setStatusText('Analyzing image in background...');
      pollForResult(result.job_id);

    } catch (error) {
      Alert.alert('Error', `Could not start visual search: ${error.message}`);
      resetState();
    }
  };
  
  const handleBarcodeScanned = async ({ data: barcode }) => {
    if (statusText) return;
    setStatusText('Checking barcode...');
    try {
      const response = await fetch(`${config.API_URL}/products/?barcode=${barcode}`);
      const result = await response.json();
      const products = result.results || [];
      if (products.length === 0) {
        router.push({ pathname: '/addproduct', params: { barcode } });
      } else if (products.length === 1) {
        const product = products[0];
        router.push({ pathname: '/addprice', params: { productId: product.id, productName: product.name, barcode: product.barcode } });
      } else {
        setBarcodeData({ products, barcode });
        setModalType('barcode');
      }
    } catch (error) {
      Alert.alert('Error', 'Could not process barcode.');
    } finally {
      setTimeout(() => setStatusText(''), 2000); 
    }
  };

  const handleSimilaritySelect = (product) => { 
    resetState(); 
    router.push({ 
        pathname: '/addprice', 
        params: { 
            productId: product.id, 
            productName: product.name, 
            barcode: product.barcode 
        } 
    }); 
  };
  
  const handleSimilarityNotFound = () => {
    const analysisString = JSON.stringify(similarityData.analysis);

    resetState();
    
    router.push({
      pathname: '/addproduct',
      params: { 
        imageUri: similarityData.imageUri,
        analysisResult: analysisString, 
      }
    });
  };

  const handleBarcodeSelect = (product) => { resetState(); router.push({ pathname: '/addprice', params: { productId: product.id, productName: product.name, barcode: product.barcode } }); };
  const handleBarcodeNotFound = () => { resetState(); router.push({ pathname: '/addproduct', params: { barcode: barcodeData.barcode } }); };
  
  if (!isFocused) return <SafeAreaView style={styles.container} />;

  return (
    <SafeAreaView style={styles.container}>
      <EnhancedScanner
        onBarcodeScanned={handleBarcodeScanned}
        onPhotoTaken={handlePhotoAction}
        onGalleryPhoto={handlePhotoAction}
        mode="both"
      />
      
      {!!statusText && (
        <View style={styles.processingOverlay}>
          <ActivityIndicator size="large" color="#FFF" />
          <Text style={styles.processingText}>{statusText}</Text>
        </View>
      )}

      <SimilarityResultsModal
        visible={modalType === 'similarity'}
        onClose={resetState}
        candidates={similarityData.candidates}
        originalImageUri={similarityData.imageUri}
        onSelectProduct={handleSimilaritySelect}
        onProductNotFound={handleSimilarityNotFound}
      />

      <BarcodeDisambiguationModal
        visible={modalType === 'barcode'}
        onClose={resetState}
        products={barcodeData.products}
        barcode={barcodeData.barcode}
        onSelectProduct={handleBarcodeSelect}
        onCreateNew={handleBarcodeNotFound}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'black',
  },
  processingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  processingText: {
    color: 'white',
    marginTop: 20,
    fontSize: 18,
    fontWeight: '600',
    paddingHorizontal: 20,
    textAlign: 'center',
  },
});
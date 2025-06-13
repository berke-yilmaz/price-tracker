// app/(tabs)/scan.jsx
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
  Image,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Camera, CameraType } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from '../../contexts/AuthContext';
import config from '../../config';

const ScanScreen = () => {
  const router = useRouter();
  const { token } = useAuth();
  const [type, setType] = useState(CameraType.back);
  const [hasPermission, setHasPermission] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [recognizedProducts, setRecognizedProducts] = useState([]);
  
  const cameraRef = useRef(null);

  useEffect(() => {
    const getCameraPermissions = async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    };

    getCameraPermissions();
  }, []);

  const takePicture = async () => {
    if (cameraRef.current && cameraReady) {
      setProcessing(true);
      try {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          base64: false,
          skipProcessing: false,
        });

        setCapturedImage(photo.uri);
        
        // Backend'e fotoğrafı gönder ve ürünü tanı
        const result = await identifyProduct(photo);
        
        if (result.found && result.product) {
          setRecognizedProducts([result.product]);
          showProductFound(result.product);
        } else {
          showProductNotFound();
        }
      } catch (error) {
        console.error('Fotoğraf çekme hatası:', error);
        Alert.alert('Hata', 'Fotoğraf çekilirken bir hata oluştu');
      } finally {
        setProcessing(false);
      }
    }
  };

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        setCapturedImage(asset.uri);
        setProcessing(true);
        
        const identifyResult = await identifyProduct(asset);
        
        if (identifyResult.found && identifyResult.product) {
          setRecognizedProducts([identifyResult.product]);
          showProductFound(identifyResult.product);
        } else {
          showProductNotFound();
        }
        setProcessing(false);
      }
    } catch (error) {
      console.error('Galeri açma hatası:', error);
      Alert.alert('Hata', 'Galeri açılırken bir hata oluştu');
    }
  };

  const identifyProduct = async (photo) => {
    try {
      const formData = new FormData();
      formData.append('image', {
        uri: photo.uri,
        type: 'image/jpeg',
        name: 'product.jpg',
      });

      const response = await fetch(`${config.API_URL}/products/identify/`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Token ${token}` : '',
          'Content-Type': 'multipart/form-data',
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Ürün tanıma hatası');
      }

      return await response.json();
    } catch (error) {
      console.error('Ürün tanıma hatası:', error);
      return { found: false };
    }
  };

  const showProductFound = (product) => {
    Alert.alert(
      'Ürün Bulundu!',
      `${product.name}\n${product.brand || ''}\n${product.lowest_price ? `Son fiyat: ₺${product.lowest_price.price} (${product.lowest_price.store})` : ''}`,
      [
        { text: 'Yeniden Dene', onPress: () => setCapturedImage(null) },
        { 
          text: 'Fiyat Ekle', 
          onPress: () => router.push(`/addprice?barcode=${product.barcode}&productId=${product.id}&productName=${encodeURIComponent(product.name)}`) 
        },
      ]
    );
  };

  const showProductNotFound = () => {
    Alert.alert(
      'Ürün Bulunamadı',
      'Bu ürün veritabanımızda bulunamadı. Yeni ürün olarak eklemek ister misiniz?',
      [
        { text: 'Yeniden Dene', onPress: () => setCapturedImage(null) },
        { text: 'Yeni Ürün Ekle', onPress: () => router.push('/addproduct') },
      ]
    );
  };

  if (hasPermission === null) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Kamera izni isteniyor...</Text>
      </View>
    );
  }

  if (hasPermission === false) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>Kamera erişimi reddedildi</Text>
        <TouchableOpacity 
          style={styles.button}
          onPress={() => Camera.requestCameraPermissionsAsync()}
        >
          <Text style={styles.buttonText}>İzin Ver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (capturedImage && !processing) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setCapturedImage(null)}>
            <Text style={styles.backButton}>← Geri</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Sonuç</Text>
        </View>
        
        <ScrollView style={styles.previewContainer}>
          <Image source={{ uri: capturedImage }} style={styles.previewImage} />
          
          {recognizedProducts.length > 0 && (
            <View style={styles.productList}>
              {recognizedProducts.map((product, index) => (
                <View key={index} style={styles.productCard}>
                  <Text style={styles.productName}>{product.name}</Text>
                  <Text style={styles.productBrand}>{product.brand}</Text>
                  {product.lowest_price && (
                    <Text style={styles.productPrice}>
                      Son fiyat: ₺{product.lowest_price.price} ({product.lowest_price.store})
                    </Text>
                  )}
                  <TouchableOpacity 
                    style={styles.addPriceButton}
                    onPress={() => router.push(`/addprice?barcode=${product.barcode}&productId=${product.id}&productName=${encodeURIComponent(product.name)}`)}
                  >
                    <Text style={styles.addPriceButtonText}>Fiyat Ekle</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.cameraContainer}>
        <Camera
          ref={cameraRef}
          style={styles.camera}
          type={type}
          onCameraReady={() => setCameraReady(true)}
        >
          <View style={styles.cameraOverlay}>
            <Text style={styles.cameraInfo}>
              Ürün fotoğrafı çekmek için butona basın
            </Text>
          </View>
        </Camera>
      </View>

      <View style={styles.controls}>
        <View style={styles.actionButtons}>
          <TouchableOpacity 
            style={styles.galleryButton}
            onPress={pickImage}
          >
            <Text style={styles.galleryButtonText}>Galeri</Text>
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.captureButton, processing && styles.disabledButton]}
            onPress={takePicture}
            disabled={processing}
          >
            {processing ? (
              <ActivityIndicator color="white" />
            ) : (
              <View style={styles.captureButtonInner} />
            )}
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.flipButton}
            onPress={() => setType(current => current === CameraType.back ? CameraType.front : CameraType.back)}
          >
            <Text style={styles.flipButtonText}>🔄</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#000',
  },
  backButton: {
    color: '#fff',
    fontSize: 16,
  },
  title: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  cameraContainer: {
    flex: 1,
    overflow: 'hidden',
  },
  camera: {
    flex: 1,
  },
  cameraOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cameraInfo: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    margin: 20,
  },
  controls: {
    paddingBottom: 30,
    paddingTop: 20,
    backgroundColor: '#000',
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  galleryButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingVertical: 8,
    paddingHorizontal: 15,
    borderRadius: 20,
  },
  galleryButtonText: {
    color: 'white',
    fontSize: 14,
  },
  captureButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledButton: {
    opacity: 0.5,
  },
  captureButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#fff',
  },
  flipButton: {
    width: 50,
    height: 50,
    justifyContent: 'center',
    alignItems: 'center',
  },
  flipButtonText: {
    fontSize: 24,
    color: 'white',
  },
  button: {
    backgroundColor: '#007AFF',
    paddingVertical: 15,
    paddingHorizontal: 30,
    borderRadius: 10,
    marginTop: 20,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  previewContainer: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  previewImage: {
    width: '100%',
    height: 300,
    resizeMode: 'contain',
  },
  productList: {
    padding: 20,
  },
  productCard: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  productName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  productBrand: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  productPrice: {
    fontSize: 14,
    color: '#4CAF50',
    marginTop: 5,
  },
  addPriceButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 8,
    paddingHorizontal: 15,
    borderRadius: 8,
    marginTop: 10,
    alignSelf: 'flex-start',
  },
  addPriceButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  loadingText: {
    color: 'white',
    fontSize: 16,
    marginTop: 10,
  },
  errorText: {
    color: 'white',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
});

export default ScanScreen;
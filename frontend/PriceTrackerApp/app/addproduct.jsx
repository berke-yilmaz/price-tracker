// app/addproduct.jsx
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
import * as ImagePicker from 'expo-image-picker';
import { useAuth } from '../contexts/AuthContext';

const API_URL = 'http://YOUR_BACKEND_URL/api'; // Backend URL'nizi buraya yazın

export default function AddProductScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const { barcode: initialBarcode } = useLocalSearchParams();
  
  const [productData, setProductData] = useState({
    name: '',
    barcode: initialBarcode || '',
    brand: '',
    category: '',
    weight: '',
    ingredients: '',
  });
  
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInputChange = (field, value) => {
    setProductData({
      ...productData,
      [field]: value,
    });
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
        setImage(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Galeri hatası:', error);
      Alert.alert('Hata', 'Görüntü seçilirken bir hata oluştu');
    }
  };

  const handleSubmit = async () => {
    // Temel validasyon
    if (!productData.name) {
      Alert.alert('Hata', 'Ürün adı gereklidir');
      return;
    }

    setLoading(true);

    try {
      // FormData oluştur
      const formData = new FormData();
      
      // Ürün verilerini ekle
      Object.keys(productData).forEach(key => {
        if (productData[key]) {
          formData.append(key, productData[key]);
        }
      });
      
      // İmaj varsa ekle
      if (image) {
        formData.append('image', {
          uri: image,
          type: 'image/jpeg',
          name: 'product.jpg',
        });
      }

      // API'ye gönder
      const response = await fetch(`${API_URL}/products/add_from_barcode/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'multipart/form-data',
        },
        body: formData,
      });

      const result = await response.json();
      
      if (response.ok) {
        Alert.alert(
          'Başarılı',
          'Ürün başarıyla eklendi!',
          [
            { 
              text: 'Fiyat Ekle', 
              onPress: () => router.push(`/addprice?barcode=${result.product.barcode}&productId=${result.product.id}&productName=${encodeURIComponent(result.product.name)}`) 
            },
            { text: 'Ana Sayfaya Dön', onPress: () => router.push('/') }
          ]
        );
      } else {
        throw new Error(result.detail || 'Ürün eklenemedi');
      }
    } catch (error) {
      console.error('Ürün ekleme hatası:', error);
      Alert.alert('Hata', error.message || 'Ürün eklenirken bir hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.backButton}>← Geri</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Yeni Ürün</Text>
          <View style={{ width: 44 }} />
        </View>

        {initialBarcode && (
          <View style={styles.barcodeInfo}>
            <Text style={styles.barcodeText}>Barkod: {initialBarcode}</Text>
          </View>
        )}

        <View style={styles.form}>
          <Text style={styles.label}>Ürün Adı*</Text>
          <TextInput
            style={styles.input}
            value={productData.name}
            onChangeText={(text) => handleInputChange('name', text)}
            placeholder="Ürün adını girin (zorunlu)"
          />

          <Text style={styles.label}>Barkod</Text>
          <TextInput
            style={styles.input}
            value={productData.barcode}
            onChangeText={(text) => handleInputChange('barcode', text)}
            placeholder="Barkodu girin"
            keyboardType="number-pad"
            editable={!initialBarcode}
          />

          <Text style={styles.label}>Marka</Text>
          <TextInput
            style={styles.input}
            value={productData.brand}
            onChangeText={(text) => handleInputChange('brand', text)}
            placeholder="Markayı girin"
          />

          <Text style={styles.label}>Kategori</Text>
          <TextInput
            style={styles.input}
            value={productData.category}
            onChangeText={(text) => handleInputChange('category', text)}
            placeholder="Kategoriyi girin"
          />

          <Text style={styles.label}>Ağırlık/Hacim</Text>
          <TextInput
            style={styles.input}
            value={productData.weight}
            onChangeText={(text) => handleInputChange('weight', text)}
            placeholder="Ör: 1kg, 500ml"
          />

          <Text style={styles.label}>İçindekiler</Text>
          <TextInput
            style={[styles.input, styles.multilineInput]}
            value={productData.ingredients}
            onChangeText={(text) => handleInputChange('ingredients', text)}
            placeholder="İçindekiler bilgisini girin"
            multiline
            numberOfLines={4}
          />

          <Text style={styles.label}>Ürün Görseli</Text>
          <TouchableOpacity 
            style={styles.imagePickerButton}
            onPress={pickImage}
          >
            <Text style={styles.imagePickerText}>Görsel Seç</Text>
          </TouchableOpacity>

          {image && (
            <Image source={{ uri: image }} style={styles.selectedImage} />
          )}

          <TouchableOpacity 
            style={[styles.submitButton, loading && styles.disabledButton]}
            onPress={handleSubmit}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.submitButtonText}>Ürünü Ekle</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    flexGrow: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#ddd',
  },
  backButton: {
    color: '#007AFF',
    fontSize: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  barcodeInfo: {
    backgroundColor: '#e8f5ff',
    padding: 15,
    margin: 20,
    borderRadius: 8,
  },
  barcodeText: {
    fontSize: 16,
    color: '#007AFF',
    textAlign: 'center',
  },
  form: {
    padding: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
    marginTop: 16,
  },
  input: {
    backgroundColor: 'white',
    paddingVertical: 12,
    paddingHorizontal: 15,
    borderRadius: 8,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  multilineInput: {
    height: 100,
    textAlignVertical: 'top',
  },
  imagePickerButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 15,
    borderRadius: 8,
    marginTop: 8,
    alignItems: 'center',
  },
  imagePickerText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  selectedImage: {
    width: '100%',
    height: 200,
    marginTop: 16,
    borderRadius: 8,
    resizeMode: 'contain',
  },
  submitButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 15,
    borderRadius: 10,
    marginTop: 30,
    marginBottom: 20,
  },
  disabledButton: {
    opacity: 0.7,
  },
  submitButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
});
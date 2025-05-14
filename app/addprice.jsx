// app/addprice.jsx - JavaScript versiyonu
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
import { useAuth } from '../contexts/AuthContext'; // AuthContext kullanarak token alacağız

const API_URL = 'http://YOUR_BACKEND_URL/api'; // Backend URL'inizi buraya ekleyin

export default function AddPriceScreen() {
  const router = useRouter();
  const { barcode, productName: initialProductName } = useLocalSearchParams();
  const { token } = useAuth(); // AuthContext'ten token alıyoruz
  
  const [productName, setProductName] = useState(initialProductName || '');
  const [selectedStore, setSelectedStore] = useState('');
  const [price, setPrice] = useState('');
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingStores, setLoadingStores] = useState(true);

  useEffect(() => {
    fetchStores();
  }, []);

  const fetchStores = async () => {
    try {
      // AuthContext ile token aldığımız için AsyncStorage'dan almaya gerek yok
      const response = await fetch(`${API_URL}/stores/`, {
        headers: {
          'Authorization': token ? `Token ${token}` : '',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setStores(data.results || data);
      } else {
        console.error('Mağazalar alınamadı');
      }
    } catch (error) {
      console.error('Mağaza alım hatası:', error);
      
      // Fallback store listesi
      setStores([
        { id: '1', name: 'BİM' },
        { id: '2', name: 'Migros' },
        { id: '3', name: 'A101' },
        { id: '4', name: 'Şok' },
      ]);
    } finally {
      setLoadingStores(false);
    }
  };

  const handleSave = async () => {
    if (!productName || !selectedStore || !price) {
      Alert.alert('Hata', 'Lütfen tüm alanları doldurun');
      return;
    }

    const numericPrice = parseFloat(price.replace(',', '.'));
    if (isNaN(numericPrice) || numericPrice <= 0) {
      Alert.alert('Hata', 'Lütfen geçerli bir fiyat girin');
      return;
    }

    setLoading(true);

    try {
      // Önce ürünü bul veya oluştur
      let productId = await findOrCreateProduct(productName, barcode);
      
      if (!productId) {
        throw new Error('Ürün oluşturulamadı');
      }

      // Fiyatı ekle
      const priceData = {
        product: productId,
        store: selectedStore,
        price: numericPrice.toFixed(2),
      };

      const response = await fetch(`${API_URL}/prices/`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Token ${token}` : '',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(priceData),
      });

      if (response.ok) {
        Alert.alert(
          'Başarılı',
          'Fiyat başarıyla eklendi!',
          [
            { text: 'Tamam', onPress: () => router.push('/(tabs)/history') }
          ]
        );
      } else {
        const errorData = await response.json();
        console.error('API Hatası:', errorData);
        
        // Kullanıcı için anlamlı hata mesajı
        if (errorData.non_field_errors && errorData.non_field_errors.includes('unique_price_per_day')) {
          Alert.alert('Bilgi', 'Bu ürün için bugün zaten fiyat eklemişsiniz.');
        } else {
          Alert.alert('Hata', 'Fiyat eklenirken bir hata oluştu');
        }
      }
    } catch (error) {
      console.error('Fiyat ekleme hatası:', error);
      Alert.alert('Hata', 'Fiyat eklenirken bir hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const findOrCreateProduct = async (name, barcode) => {
    try {
      // Önce mevcut ürünü ara
      let searchUrl = `${API_URL}/products/search/?q=${encodeURIComponent(name)}`;
      if (barcode) {
        searchUrl = `${API_URL}/products/by_barcode/?barcode=${barcode}`;
      }

      const searchResponse = await fetch(searchUrl, {
        headers: {
          'Authorization': token ? `Token ${token}` : '',
        },
      });

      if (searchResponse.ok) {
        const data = await searchResponse.json();
        const products = data.results || data;
        
        if (products.length > 0 || (data.found && data.product)) {
          // API yanıt formatına bağlı olarak ürün ID'si alınır
          return products.length > 0 ? products[0].id : data.product.id;
        }
      }

      // Ürün bulunamadıysa yeni oluştur
      const createResponse = await fetch(`${API_URL}/products/`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Token ${token}` : '',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name,
          barcode: barcode || '',
          brand: '',
          category: '',
        }),
      });

      if (createResponse.ok) {
        const newProduct = await createResponse.json();
        return newProduct.id;
      }

    } catch (error) {
      console.error('Ürün arama/oluşturma hatası:', error);
    }

    return null;
  };

  if (loadingStores) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Mağazalar yükleniyor...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollContainer}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.backButton}>← Geri</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Fiyat Ekle</Text>
          <View style={{ width: 50 }} />
        </View>

        {barcode && (
          <View style={styles.barcodeInfo}>
            <Text style={styles.barcodeText}>Barkod: {barcode}</Text>
          </View>
        )}

        <View style={styles.form}>
          <Text style={styles.label}>Ürün Adı</Text>
          <TextInput
            style={styles.input}
            value={productName}
            onChangeText={setProductName}
            placeholder="Ürün adını girin"
            editable={!initialProductName}
          />

          <Text style={styles.label}>Mağaza</Text>
          <ScrollView 
            horizontal 
            showsHorizontalScrollIndicator={false}
            style={styles.storeScrollView}
          >
            <View style={styles.storeContainer}>
              {stores.map(store => (
                <TouchableOpacity
                  key={store.id}
                  style={[
                    styles.storeButton,
                    selectedStore === store.id && styles.selectedStore
                  ]}
                  onPress={() => setSelectedStore(store.id)}
                >
                  <Text
                    style={[
                      styles.storeText,
                      selectedStore === store.id && styles.selectedStoreText
                    ]}
                  >
                    {store.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>

          <Text style={styles.label}>Fiyat</Text>
          <View style={styles.priceInputContainer}>
            <TextInput
              style={styles.priceInput}
              value={price}
              onChangeText={setPrice}
              placeholder="0.00"
              keyboardType="decimal-pad"
            />
            <Text style={styles.currency}>₺</Text>
          </View>

          <TouchableOpacity 
            style={[styles.saveButton, loading && styles.disabledButton]}
            onPress={handleSave}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.saveButtonText}>Kaydet</Text>
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
  scrollContainer: {
    flex: 1,
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
  storeScrollView: {
    marginVertical: 8,
  },
  storeContainer: {
    flexDirection: 'row',
  },
  storeButton: {
    backgroundColor: 'white',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 8,
    margin: 4,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  selectedStore: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  storeText: {
    fontSize: 14,
    color: '#333',
  },
  selectedStoreText: {
    color: 'white',
  },
  priceInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  priceInput: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 15,
    fontSize: 16,
  },
  currency: {
    fontSize: 16,
    color: '#666',
    paddingRight: 15,
  },
  saveButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 15,
    borderRadius: 10,
    marginTop: 30,
  },
  disabledButton: {
    opacity: 0.5,
  },
  saveButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
    fontSize: 16,
  },
});
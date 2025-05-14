// app/(tabs)/history.jsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  FlatList,
  TextInput,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';

const API_URL = 'http://YOUR_BACKEND_URL/api'; // Backend URL'nizi buraya yazın

export default function HistoryScreen() {
  const router = useRouter();
  const { token } = useAuth();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [prices, setPrices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchPrices();
  }, []);

  const fetchPrices = async () => {
    try {
      setLoading(true);
      
      const response = await fetch(`${API_URL}/prices/`, {
        headers: {
          'Authorization': `Token ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setPrices(data.results || data);
      } else {
        console.error('Fiyatlar alınamadı');
      }
    } catch (error) {
      console.error('Fiyat alım hatası:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchPrices();
  };

  const filteredPrices = prices.filter(price =>
    price.product_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    price.store_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR');
  };

  const renderItem = ({ item }) => (
    <View style={styles.priceItem}>
      <View style={styles.priceInfo}>
        <Text style={styles.productName}>{item.product_name}</Text>
        <Text style={styles.storeAndDate}>{item.store_name} • {formatDate(item.created_at)}</Text>
      </View>
      <Text style={styles.price}>₺{parseFloat(item.price).toFixed(2)}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <TextInput
        style={styles.searchInput}
        placeholder="Ürün veya mağaza ara..."
        value={searchQuery}
        onChangeText={setSearchQuery}
      />
      
      {loading && !refreshing ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Fiyatlar yükleniyor...</Text>
        </View>
      ) : (
        <>
          {filteredPrices.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>Fiyat kaydı bulunamadı</Text>
              <TouchableOpacity 
                style={styles.addButton}
                onPress={() => router.push('/scan')}
              >
                <Text style={styles.addButtonText}>Ürün Tarayarak Fiyat Ekleyin</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <FlatList
              data={filteredPrices}
              renderItem={renderItem}
              keyExtractor={item => item.id.toString()}
              contentContainerStyle={styles.listContainer}
              showsVerticalScrollIndicator={false}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={onRefresh}
                  colors={['#007AFF']}
                />
              }
            />
          )}
        </>
      )}
      
      <TouchableOpacity 
        style={styles.floatingButton}
        onPress={() => router.push('/addprice')}
      >
        <Text style={styles.floatingButtonText}>+</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  searchInput: {
    backgroundColor: 'white',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 8,
    fontSize: 16,
    margin: 20,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  listContainer: {
    padding: 20,
    paddingTop: 0,
  },
  priceItem: {
    backgroundColor: 'white',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    marginBottom: 10,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
    elevation: 3,
  },
  priceInfo: {
    flex: 1,
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  storeAndDate: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  price: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
    marginBottom: 20,
  },
  addButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  addButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  floatingButton: {
    position: 'absolute',
    bottom: 20,
    right: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  floatingButtonText: {
    color: 'white',
    fontSize: 24,
    fontWeight: 'bold',
  },
});
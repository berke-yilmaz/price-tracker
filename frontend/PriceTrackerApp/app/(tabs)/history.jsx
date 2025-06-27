// app/(tabs)/history.jsx - FINAL, CORRECTED - SHOWS USER'S PRICES
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  SectionList,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Image,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useFocusEffect } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import theme from '../../constants/theme';
import config from '../../config';
import { getImageUrl } from '../../utils/imageUtils';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

// Group prices by date for a better UI
const groupPricesByDate = (prices) => {
  if (!prices || prices.length === 0) return [];
  const grouped = prices.reduce((acc, price) => {
    const date = new Date(price.created_at).toDateString();
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(price);
    return acc;
  }, {});
  return Object.entries(grouped).map(([title, data]) => ({ title, data }));
};

const PriceCard = ({ item }) => {
  const router = useRouter();
  
  // ⭐ FIX: Access the nested product object for image and name
  const imageUrl = getImageUrl(item?.product);
  const productName = item?.product?.name || 'Unknown Product';
  const storeName = item?.store_name || 'Unknown Store';

  const handlePress = () => {
    if (item.product?.id) {
      Alert.alert(
        productName,
        `Price: ₺${parseFloat(item.price).toFixed(2)}\nStore: ${storeName}`,
        [
          { text: 'OK' },
          { text: 'Find Product', onPress: () => router.push({ pathname: '/(tabs)/search', params: { query: productName } }) }
        ]
      );
    }
  };

  return (
    <TouchableOpacity onPress={handlePress} style={styles.priceCard}>
        {imageUrl ? (
            <Image source={{ uri: imageUrl }} style={styles.productImage} />
        ) : (
            <View style={styles.placeholderImage}>
                <Ionicons name="image-outline" size={24} color={theme.colors.gray[400]} />
            </View>
        )}
        <View style={styles.priceInfo}>
            <Text style={styles.productName} numberOfLines={1}>{productName}</Text>
            <View style={styles.storeContainer}>
                <Ionicons name="storefront-outline" size={14} color={theme.colors.text.secondary} />
                <Text style={styles.storeName} numberOfLines={1}>{storeName}</Text>
            </View>
        </View>
        <Text style={styles.price}>₺{parseFloat(item.price).toFixed(2)}</Text>
    </TouchableOpacity>
  );
};

export default function HistoryScreen() {
  const router = useRouter();
  const { token } = useAuth();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [prices, setPrices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      fetchPrices();
    }, [token])
  );

  const fetchPrices = async () => {
    if (!token) {
        setPrices([]);
        setLoading(false);
        return;
    }
    if (!refreshing) setLoading(true);
    try {
      // The backend fix in PriceViewSet ensures this fetch is efficient
      const response = await fetch(`${config.API_URL}/prices/`, {
        headers: { 'Authorization': `Token ${token}` },
      });
      if (!response.ok) throw new Error('Failed to fetch prices');
      const data = await response.json();
      setPrices(data.results || data || []);
    } catch (error) {
      console.error('Fetch prices error:', error);
      Alert.alert('Error', 'Could not fetch your price history.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchPrices();
  }, [token]);

  const filteredPrices = useMemo(() => {
    if (!searchQuery) return prices;
    return prices.filter(price => {
      const productName = price?.product?.name || '';
      const storeName = price.store_name || '';
      return productName.toLowerCase().includes(searchQuery.toLowerCase()) ||
             storeName.toLowerCase().includes(searchQuery.toLowerCase());
    });
  }, [prices, searchQuery]);

  const groupedData = useMemo(() => groupPricesByDate(filteredPrices), [filteredPrices]);

  const formatDateHeader = (dateString) => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const date = new Date(dateString);
    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
    return date.toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  };
  
  const renderEmptyComponent = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="receipt-outline" size={64} color={theme.colors.gray[300]} />
      <Text style={styles.emptyTitle}>{searchQuery ? 'No Results Found' : 'No Price History'}</Text>
      <Text style={styles.emptyText}>{searchQuery ? 'Try a different search term.' : 'Prices you add will appear here.'}</Text>
      {prices.length === 0 && !searchQuery && (
        <Button
          title="Add Your First Price"
          onPress={() => router.push('/(tabs)/scan')}
          icon={<Ionicons name="add" size={20} color={theme.colors.text.inverse} style={{marginRight: 8}}/>}
        />
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}><Text style={styles.title}>Price History</Text></View>
      <View style={styles.searchSection}>
        <Input 
          placeholder="Search product or store..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          leftIcon="search-outline"
          rightIcon={searchQuery ? 'close-circle' : null}
          onRightIconPress={() => setSearchQuery('')}
        />
      </View>
      
      {loading && !refreshing ? (
        <View style={styles.loadingContainer}><ActivityIndicator size="large" color={theme.colors.primary[500]} /></View>
      ) : (
        <SectionList
          sections={groupedData}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => <PriceCard item={item} />}
          renderSectionHeader={({ section: { title } }) => (<Text style={styles.sectionHeader}>{formatDateHeader(title)}</Text>)}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary[500]}/>}
          ListEmptyComponent={renderEmptyComponent}
          contentContainerStyle={groupedData.length === 0 ? { flex: 1 } : { paddingBottom: 80 }}
          showsVerticalScrollIndicator={false}
          stickySectionHeadersEnabled={false}
        />
      )}

      <TouchableOpacity style={styles.floatingButton} onPress={() => router.push('/(tabs)/scan')}>
        <Ionicons name="add" size={32} color={theme.colors.text.inverse} />
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  header: { backgroundColor: theme.colors.surface, paddingTop: theme.spacing.xl, paddingBottom: theme.spacing.md, paddingHorizontal: theme.spacing.lg, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
  title: { fontSize: theme.typography.fontSize['3xl'], fontWeight: theme.typography.fontWeight.bold, color: theme.colors.text.primary },
  searchSection: { paddingHorizontal: theme.spacing.lg, paddingVertical: theme.spacing.md, backgroundColor: theme.colors.surface, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
  sectionHeader: { fontSize: theme.typography.fontSize.base, fontWeight: theme.typography.fontWeight.semibold, color: theme.colors.text.secondary, paddingHorizontal: theme.spacing.lg, paddingTop: theme.spacing.lg, paddingBottom: theme.spacing.sm, backgroundColor: theme.colors.background },
  priceCard: { backgroundColor: theme.colors.surface, padding: theme.spacing.md, flexDirection: 'row', alignItems: 'center', marginHorizontal: theme.spacing.lg, marginBottom: theme.spacing.sm, borderRadius: theme.borderRadius.lg, ...theme.shadows.sm },
  productImage: { width: 60, height: 60, borderRadius: theme.borderRadius.lg, backgroundColor: theme.colors.gray[100], marginRight: theme.spacing.md },
  placeholderImage: { width: 60, height: 60, borderRadius: theme.borderRadius.lg, backgroundColor: theme.colors.gray[100], justifyContent: 'center', alignItems: 'center', marginRight: theme.spacing.md },
  priceInfo: { flex: 1, justifyContent: 'center' },
  productName: { fontSize: theme.typography.fontSize.base, fontWeight: theme.typography.fontWeight.semibold, color: theme.colors.text.primary, marginBottom: 2 },
  storeContainer: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  storeName: { fontSize: theme.typography.fontSize.sm, color: theme.colors.text.secondary, marginLeft: theme.spacing.xs },
  price: { fontSize: theme.typography.fontSize.lg, fontWeight: theme.typography.fontWeight.bold, color: theme.colors.success[600], marginLeft: theme.spacing.md },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: theme.spacing.xl },
  emptyTitle: { fontSize: theme.typography.fontSize.xl, fontWeight: theme.typography.fontWeight.bold, color: theme.colors.text.primary, marginTop: theme.spacing.lg },
  emptyText: { fontSize: theme.typography.fontSize.base, color: theme.colors.text.secondary, marginTop: theme.spacing.sm, marginBottom: theme.spacing.xl, textAlign: 'center' },
  floatingButton: { position: 'absolute', bottom: theme.spacing.lg, right: theme.spacing.lg, width: 60, height: 60, borderRadius: 30, backgroundColor: theme.colors.primary[500], justifyContent: 'center', alignItems: 'center', ...theme.shadows.lg },
});
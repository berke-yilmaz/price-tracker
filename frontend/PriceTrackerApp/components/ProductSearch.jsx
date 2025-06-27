// components/ProductSearch.jsx - FINAL CORRECTED VERSION
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Image,
  Modal,
  ScrollView,
  Animated,
  Vibration,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../contexts/AuthContext';
import theme from '../constants/theme';
import config from '../config';
import LocationService from '../services/LocationService';
import { getImageUrl } from '../utils/imageUtils';

export default function ProductSearch({ onProductSelect, showDeleteOption = false }) {
  const { token, user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [filters, setFilters] = useState({
    color: '',
    brand: '',
    hasImages: false,
    sortBy: 'newest'
  });
  const [showFilters, setShowFilters] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletingProduct, setDeletingProduct] = useState(false);
  
  const [longPressProduct, setLongPressProduct] = useState(null);
  const longPressTimer = useRef(null);
  const longPressAnimation = useRef(new Animated.Value(0)).current;

  // --- No changes needed in this section ---
  const colorOptions = [
    { value: '', label: 'All' }, { value: 'red', label: 'Red' }, { value: 'green', label: 'Green' }, 
    { value: 'blue', label: 'Blue' }, { value: 'yellow', label: 'Yellow' }, { value: 'black', label: 'Black' },
    { value: 'white', label: 'White' }
  ];
  const sortOptions = [
    { value: 'newest', label: 'Newest' }, { value: '-lowest_price_val', label: 'Price Low-High' },
    { value: 'name', label: 'Name A-Z' }, { value: 'brand', label: 'Brand A-Z' }
  ];
  useEffect(() => {
    const init = async () => {
        const location = await LocationService.getLocationSafely();
        setUserLocation(location);
        searchProducts(true, location);
    }
    init();
  }, []);
  useEffect(() => {
    const handler = setTimeout(() => {
      searchProducts(false, userLocation);
    }, 500);
    return () => clearTimeout(handler);
  }, [searchQuery, filters]);
  useEffect(() => {
    return () => {
      if (longPressTimer.current) clearTimeout(longPressTimer.current);
    };
  }, []);
  const searchProducts = async (isInitial = false, location = userLocation) => {
    if (loading && !isInitial) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('search', searchQuery.trim());
      if (filters.color) params.append('color', filters.color);
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.hasImages) params.append('has_image', 'true');
      if (location) {
          params.append('lat', location.latitude);
          params.append('lng', location.longitude);
      }
      const orderMap = {
        'newest': '-created_at', 'oldest': 'created_at', 'name': 'name', 
        'brand': 'brand', 'confidence': '-color_confidence', '-lowest_price_val': 'lowest_price_val'
      };
      params.append('ordering', orderMap[filters.sortBy] || '-created_at');
      const response = await fetch(`${config.API_URL}/products/?${params.toString()}`);
      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      setProducts(data.results || data || []);
    } catch (error) {
      console.error('Search error:', error);
      setProducts([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  const onRefresh = useCallback(() => {
    setRefreshing(true);
    searchProducts(true, userLocation);
  }, [userLocation]);
  // --- End of no-change section ---


  // --- START OF FIX ---
  const handlePressIn = (product) => {
    if (!showDeleteOption || !user) return;
    setLongPressProduct(product);
    Animated.timing(longPressAnimation, {
      toValue: 1,
      duration: 3000,
      useNativeDriver: false,
    }).start();
    longPressTimer.current = setTimeout(() => {
      Vibration.vibrate(100);
      // ⭐ FIX: Use the correct method name: stopAnimation()
      longPressAnimation.stopAnimation(); 
      longPressAnimation.setValue(0);
      setLongPressProduct(null);
      setSelectedProduct(product);
      setShowDeleteModal(true);
    }, 3000);
  };

  const handlePressOut = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current);
      longPressTimer.current = null;
    }
    // ⭐ FIX: Use the correct method name: stopAnimation()
    longPressAnimation.stopAnimation();
    Animated.timing(longPressAnimation, {
      toValue: 0,
      duration: 200,
      useNativeDriver: false,
    }).start();
    setLongPressProduct(null);
  };
  // --- END OF FIX ---


  // --- No changes needed in this section ---
  const handleProductPress = (product) => {
    handlePressOut();
    if (onProductSelect) {
      onProductSelect(product);
    }
  };
  const handleDeleteProduct = async () => {
    if (!selectedProduct || !token) return;
    setDeletingProduct(true);
    try {
      const response = await fetch(`${config.API_URL}/products/${selectedProduct.id}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Token ${token}` },
      });
      if (response.ok) {
        setProducts(prev => prev.filter(p => p.id !== selectedProduct.id));
        Alert.alert('Success', 'Product deleted successfully');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete product');
      }
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setDeletingProduct(false);
      setShowDeleteModal(false);
    }
  };
  const getColorIndicator = (colorCategory) => {
    const colorMap = {
      'red': theme.colors.error[500], 'orange': '#FF9800', 'yellow': theme.colors.warning[500],
      'green': theme.colors.success[500], 'blue': theme.colors.primary[500], 'purple': '#9C27B0',
      'pink': '#E91E63', 'brown': '#8D6E63', 'black': theme.colors.gray[800],
      'white': theme.colors.gray[100], 'unknown': theme.colors.gray[400],
    };
    return colorMap[colorCategory] || theme.colors.gray[400];
  };
  const renderProduct = ({ item }) => {
    const imageUrl = getImageUrl(item);
    const colorIndicator = getColorIndicator(item.color_category);
    const isLongPressing = longPressProduct?.id === item.id;
    return (
      <TouchableOpacity
        style={[styles.productCard, isLongPressing && styles.productCardLongPress]}
        onPress={() => handleProductPress(item)}
        onPressIn={() => handlePressIn(item)}
        onPressOut={handlePressOut}
        activeOpacity={0.7}
      >
        <View style={styles.productImageContainer}>
          {imageUrl ? (
            <Image source={{ uri: imageUrl }} style={styles.productImage} />
          ) : (
            <View style={styles.placeholderImage}><Ionicons name="image-outline" size={32} color={theme.colors.gray[400]} /></View>
          )}
          {item.color_category && item.color_category !== 'unknown' && (
            <View style={[styles.colorBadge, { backgroundColor: colorIndicator }]} />
          )}
          {isLongPressing && showDeleteOption && (
            <View style={styles.longPressOverlay}>
              <Animated.View style={[styles.longPressProgress, { width: longPressAnimation.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] }) }]}/>
              <View style={styles.longPressText}><Ionicons name="trash" size={20} color="white" /><Text style={styles.longPressLabel}>Hold to delete</Text></View>
            </View>
          )}
        </View>

        <View style={styles.productInfo}>
          <Text style={styles.productName} numberOfLines={2}>{item.name}</Text>
          <Text style={styles.productBrand} numberOfLines={1}>{item.brand || 'No brand'}</Text>
          
          {item.nearest_price_info ? (
            <View style={styles.priceInfo}>
              <Text style={styles.priceText}>₺{parseFloat(item.nearest_price_info.price).toFixed(2)}</Text>
              {item.nearest_price_info.distanceText && (
                <Text style={styles.distanceText}>{item.nearest_price_info.distanceText}</Text>
              )}
            </View>
          ) : item.lowest_price ? (
            <View style={styles.priceInfo}>
              <Text style={styles.priceText}>from ₺{parseFloat(item.lowest_price.price).toFixed(2)}</Text>
            </View>
          ) : null}
        </View>
      </TouchableOpacity>
    );
  };
  // --- End of no-change section ---


  // The entire JSX return block is unchanged.
  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <View style={styles.searchInputContainer}>
          <Ionicons name="search" size={20} color={theme.colors.gray[500]} style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search products, brands..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholderTextColor={theme.colors.gray[500]}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={20} color={theme.colors.gray[500]} />
            </TouchableOpacity>
          )}
        </View>
        <TouchableOpacity style={styles.filterButton} onPress={() => setShowFilters(!showFilters)}>
          <Ionicons name={showFilters ? "options" : "options-outline"} size={20} color={theme.colors.primary[500]} />
        </TouchableOpacity>
      </View>
      {showFilters && (
        <View style={styles.filtersContainer}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.filterGroup}>
              <Text style={styles.filterLabel}>Color:</Text>
              <View style={styles.filterOptions}>
                {colorOptions.map((option) => (
                  <TouchableOpacity
                    key={option.value}
                    style={[styles.filterOption, filters.color === option.value && styles.filterOptionActive]}
                    onPress={() => setFilters(prev => ({ ...prev, color: option.value }))}
                  >
                    <Text style={[styles.filterOptionText, filters.color === option.value && styles.filterOptionTextActive]}>{option.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
            <View style={styles.filterGroup}>
              <Text style={styles.filterLabel}>Sort:</Text>
              <View style={styles.filterOptions}>
                {sortOptions.map((option) => (
                  <TouchableOpacity
                    key={option.value}
                    style={[styles.filterOption, filters.sortBy === option.value && styles.filterOptionActive]}
                    onPress={() => setFilters(prev => ({ ...prev, sortBy: option.value }))}
                  >
                    <Text style={[styles.filterOptionText, filters.sortBy === option.value && styles.filterOptionTextActive]}>{option.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          </ScrollView>
          <TouchableOpacity style={styles.clearFiltersButton} onPress={() => setFilters({ color: '', brand: '', hasImages: false, sortBy: 'newest' })}>
            <Text style={styles.clearFiltersText}>Clear</Text>
          </TouchableOpacity>
        </View>
      )}
      <FlatList
        data={products}
        renderItem={renderProduct}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.colors.primary[500]]} />}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            {loading ? (
              <><ActivityIndicator size="large" color={theme.colors.primary[500]} /><Text style={styles.emptyText}>Searching...</Text></>
            ) : (
              <><Ionicons name="search-outline" size={48} color={theme.colors.gray[400]} /><Text style={styles.emptyText}>{searchQuery ? 'No products found' : 'Start typing to search'}</Text></>
            )}
          </View>
        }
        contentContainerStyle={products.length === 0 ? { flex: 1 } : {}}
        numColumns={2}
        columnWrapperStyle={styles.row}
      />
      <Modal visible={showDeleteModal} animationType="fade" transparent={true} onRequestClose={() => setShowDeleteModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Ionicons name="warning" size={32} color={theme.colors.error[500]} />
              <Text style={styles.modalTitle}>Delete Product</Text>
            </View>
            <Text style={styles.modalMessage}>Are you sure you want to delete "{selectedProduct?.name}"?</Text>
            <Text style={styles.modalWarning}>This will permanently remove the product and all its price records. This action cannot be undone.</Text>
            <View style={styles.modalButtons}>
              <TouchableOpacity style={[styles.modalButton, styles.cancelButton]} onPress={() => setShowDeleteModal(false)} disabled={deletingProduct}>
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.modalButton, styles.deleteButtonModal]} onPress={handleDeleteProduct} disabled={deletingProduct}>
                {deletingProduct ? (
                  <ActivityIndicator size="small" color="white" />
                ) : (
                  <><Ionicons name="trash" size={16} color="white" /><Text style={styles.deleteButtonText}>Delete</Text></>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  searchContainer: {
    flexDirection: 'row',
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
  },
  searchInputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.gray[100],
    borderRadius: theme.borderRadius.lg,
    paddingHorizontal: theme.spacing.md,
    marginRight: theme.spacing.md,
  },
  searchIcon: {
    marginRight: theme.spacing.sm,
  },
  searchInput: {
    flex: 1,
    paddingVertical: theme.spacing.sm,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
  },
  filterButton: {
    paddingHorizontal: theme.spacing.sm,
    backgroundColor: theme.colors.primary[50],
    borderRadius: theme.borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  filtersContainer: {
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
    paddingTop: theme.spacing.sm,
    paddingBottom: theme.spacing.md,
  },
  filterGroup: {
    marginHorizontal: theme.spacing.lg,
  },
  filterLabel: {
    fontSize: theme.typography.fontSize.xs,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.xs,
    paddingLeft: theme.spacing.xs,
  },
  filterOptions: {
    flexDirection: 'row',
  },
  filterOption: {
    backgroundColor: theme.colors.gray[100],
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.full,
    marginRight: theme.spacing.sm,
  },
  filterOptionActive: {
    backgroundColor: theme.colors.primary[500],
  },
  filterOptionText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
  },
  filterOptionTextActive: {
    color: theme.colors.text.inverse,
    fontWeight: theme.typography.fontWeight.semibold,
  },
  clearFiltersButton: {
    position: 'absolute',
    right: theme.spacing.lg,
    top: 0,
  },
  clearFiltersText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.primary[500],
    fontWeight: theme.typography.fontWeight.semibold,
  },
  row: {
    justifyContent: 'space-between',
    paddingHorizontal: theme.spacing.md,
  },
  productCard: {
    width: '48%',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.xl,
    marginBottom: theme.spacing.md,
    ...theme.shadows.sm,
    overflow: 'hidden',
  },
  productCardLongPress: {
    transform: [{ scale: 0.98 }],
    borderWidth: 2,
    borderColor: theme.colors.error[300],
  },
  productImageContainer: {
    position: 'relative',
    height: 140,
  },
  productImage: {
    width: '100%',
    height: '100%',
    backgroundColor: theme.colors.gray[50],
  },
  placeholderImage: {
    width: '100%',
    height: '100%',
    backgroundColor: theme.colors.gray[100],
    justifyContent: 'center',
    alignItems: 'center',
  },
  colorBadge: {
    position: 'absolute',
    top: theme.spacing.sm,
    right: theme.spacing.sm,
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: theme.colors.surface,
  },
  longPressOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(239, 68, 68, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: theme.borderRadius.lg,
  },
  longPressProgress: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    height: 4,
    backgroundColor: 'white',
    borderRadius: theme.borderRadius.lg,
  },
  longPressText: {
    alignItems: 'center',
  },
  longPressLabel: {
    color: 'white',
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.semibold,
    marginTop: theme.spacing.xs,
  },
  productInfo: {
    padding: theme.spacing.md,
  },
  productName: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
    height: theme.typography.fontSize.sm * theme.typography.lineHeight.tight * 2,
    lineHeight: theme.typography.fontSize.sm * theme.typography.lineHeight.tight,
  },
  productBrand: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.sm,
  },
  priceInfo: {
    marginTop: 'auto',
    paddingTop: theme.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: theme.colors.gray[100],
  },
  priceText: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.success[500],
  },
  distanceText: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
    marginTop: 2,
  },
  emptyList: {
    flex: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.xl,
  },
  emptyText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    marginTop: theme.spacing.md,
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.xl,
    margin: theme.spacing.lg,
    width: '90%',
  },
  modalHeader: {
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
  },
  modalTitle: {
    fontSize: theme.typography.fontSize.lg,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
    marginTop: theme.spacing.sm,
    textAlign: 'center',
  },
  modalMessage: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.md,
    textAlign: 'center',
    fontWeight: theme.typography.fontWeight.medium,
  },
  modalWarning: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.xl,
    textAlign: 'center',
    backgroundColor: theme.colors.error[50],
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.md,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: theme.spacing.md,
  },
  modalButton: {
    flex: 1,
    paddingVertical: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  cancelButton: {
    backgroundColor: theme.colors.gray[200],
  },
  deleteButtonModal: {
    backgroundColor: theme.colors.error[500],
  },
  cancelButtonText: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.secondary,
  },
  deleteButtonText: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.inverse,
    marginLeft: theme.spacing.xs,
  },
});
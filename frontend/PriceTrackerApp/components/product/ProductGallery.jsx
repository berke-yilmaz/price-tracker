
// components/product/ProductGallery.jsx
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import theme from '../../constants/theme';
import ProductCard from './ProductCard';
import Button from '../ui/Button';

const { width } = Dimensions.get('window');

const ProductGallery = ({
  products = [],
  loading = false,
  onRefresh,
  onLoadMore,
  onProductPress,
  onAddPrice,
  variant = 'grid', // 'grid', 'list'
  showFilters = true,
}) => {
  const [viewMode, setViewMode] = useState(variant);
  const [sortBy, setSortBy] = useState('newest');

  const numColumns = viewMode === 'grid' ? 2 : 1;

  const renderProduct = ({ item, index }) => (
    <ProductCard
      product={item}
      variant={viewMode === 'grid' ? 'default' : 'search'}
      onPress={() => onProductPress?.(item)}
      onAddPrice={onAddPrice}
      style={viewMode === 'grid' && index % 2 === 1 ? { marginLeft: theme.spacing.md } : {}}
    />
  );

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.headerTop}>
        <Text style={styles.resultsCount}>
          {products.length} ürün bulundu
        </Text>
        
        <View style={styles.viewControls}>
          <TouchableOpacity
            style={[styles.viewButton, viewMode === 'grid' && styles.viewButtonActive]}
            onPress={() => setViewMode('grid')}
          >
            <Ionicons 
              name="grid-outline" 
              size={20} 
              color={viewMode === 'grid' ? theme.colors.primary[500] : theme.colors.gray[500]} 
            />
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.viewButton, viewMode === 'list' && styles.viewButtonActive]}
            onPress={() => setViewMode('list')}
          >
            <Ionicons 
              name="list-outline" 
              size={20} 
              color={viewMode === 'list' ? theme.colors.primary[500] : theme.colors.gray[500]} 
            />
          </TouchableOpacity>
        </View>
      </View>

      {showFilters && (
        <View style={styles.filterRow}>
          <TouchableOpacity style={styles.filterButton}>
            <Ionicons name="options-outline" size={16} color={theme.colors.gray[600]} />
            <Text style={styles.filterText}>Filtrele</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.sortButton}>
            <Text style={styles.sortText}>Yeniden Eskiye</Text>
            <Ionicons name="chevron-down" size={16} color={theme.colors.gray[600]} />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="basket-outline" size={64} color={theme.colors.gray[300]} />
      <Text style={styles.emptyTitle}>Ürün bulunamadı</Text>
      <Text style={styles.emptyText}>
        Aradığınız kriterlere uygun ürün bulunamadı.
      </Text>
      <Button
        title="Yeni Ürün Ekle"
        variant="outline"
        onPress={() => {/* Navigate to add product */}}
        style={styles.emptyButton}
      />
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={products}
        renderItem={renderProduct}
        keyExtractor={(item) => item.id.toString()}
        numColumns={numColumns}
        key={`${viewMode}-${numColumns}`}
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={!loading ? renderEmpty : null}
        onRefresh={onRefresh}
        refreshing={loading}
        onEndReached={onLoadMore}
        onEndReachedThreshold={0.1}
        contentContainerStyle={styles.contentContainer}
        columnWrapperStyle={viewMode === 'grid' ? styles.row : null}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  contentContainer: {
    padding: theme.spacing.md,
  },
  header: {
    marginBottom: theme.spacing.lg,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  resultsCount: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
  },
  viewControls: {
    flexDirection: 'row',
    backgroundColor: theme.colors.gray[100],
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.xs,
  },
  viewButton: {
    padding: theme.spacing.sm,
    borderRadius: theme.borderRadius.sm,
  },
  viewButtonActive: {
    backgroundColor: theme.colors.surface,
  },
  filterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    borderRadius: theme.borderRadius.md,
    ...theme.shadows.sm,
  },
  filterText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    marginLeft: theme.spacing.xs,
  },
  sortButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sortText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    marginRight: theme.spacing.xs,
  },
  row: {
    justifyContent: 'space-between',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: theme.spacing['3xl'],
  },
  emptyTitle: {
    fontSize: theme.typography.fontSize.lg,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.primary,
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.sm,
  },
  emptyText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    marginBottom: theme.spacing.xl,
    paddingHorizontal: theme.spacing.lg,
  },
  emptyButton: {
    marginTop: theme.spacing.md,
  },
});

export default ProductGallery;
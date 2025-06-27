// components/product/ProductCard.jsx
import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import theme from '../../constants/theme';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Button from '../ui/Button';

const { width } = Dimensions.get('window');
const cardWidth = (width - theme.spacing.lg * 3) / 2;

const ProductCard = ({
  product,
  onPress,
  onAddPrice,
  variant = 'default', // 'default', 'search', 'compact'
  showPrices = true,
  showActions = true,
}) => {
  const formatPrice = (price) => `₺${parseFloat(price).toFixed(2)}`;

  const getColorBadgeVariant = (colorCategory) => {
    const colorMap = {
      red: 'error',
      green: 'success',
      blue: 'primary',
      yellow: 'warning',
      orange: 'warning',
      purple: 'primary',
      pink: 'error',
      brown: 'gray',
      black: 'gray',
      white: 'gray',
      unknown: 'gray',
    };
    return colorMap[colorCategory] || 'gray';
  };

  if (variant === 'compact') {
    return (
      <TouchableOpacity onPress={onPress} style={styles.compactCard}>
        <View style={styles.compactContent}>
          {product.image_display_url && (
            <Image source={{ uri: product.image_display_url }} style={styles.compactImage} />
          )}
          
          <View style={styles.compactInfo}>
            <Text style={styles.compactName} numberOfLines={2}>
              {product.name}
            </Text>
            <Text style={styles.compactBrand}>{product.brand}</Text>
            
            {product.color_info && (
              <Badge 
                variant={getColorBadgeVariant(product.color_info.category)}
                size="small"
                style={styles.colorBadge}
              >
                {product.color_info.display_name}
              </Badge>
            )}
          </View>

          {product.lowest_price && (
            <View style={styles.priceContainer}>
              <Text style={styles.price}>
                {formatPrice(product.lowest_price.price)}
              </Text>
              <Text style={styles.store} numberOfLines={1}>
                {product.lowest_price.store}
              </Text>
            </View>
          )}
        </View>
      </TouchableOpacity>
    );
  }

  if (variant === 'search') {
    return (
      <Card style={styles.searchCard} shadow="sm">
        <TouchableOpacity onPress={onPress}>
          <View style={styles.searchContent}>
            {product.image_display_url && (
              <View style={styles.searchImageContainer}>
                <Image 
                  source={{ uri: product.image_display_url }} 
                  style={styles.searchImage} 
                />
                {product.color_info && (
                  <Badge 
                    variant={getColorBadgeVariant(product.color_info.category)}
                    size="small"
                    style={styles.searchColorBadge}
                  >
                    {product.color_info.display_name}
                  </Badge>
                )}
              </View>
            )}
            
            <View style={styles.searchInfo}>
              <Text style={styles.searchName} numberOfLines={2}>
                {product.name}
              </Text>
              <Text style={styles.searchBrand}>{product.brand}</Text>
              
              {showPrices && product.nearestPrice && (
                <View style={styles.nearestPriceContainer}>
                  <Text style={styles.nearestPriceLabel}>En yakın:</Text>
                  <Text style={styles.nearestPrice}>
                    {formatPrice(product.nearestPrice.price)}
                  </Text>
                  <Text style={styles.nearestStore}>
                    {product.nearestPrice.store_name}
                    {product.nearestPrice.distanceText && ` • ${product.nearestPrice.distanceText}`}
                  </Text>
                </View>
              )}

              {product.totalLocations > 1 && (
                <Text style={styles.moreLocations}>
                  +{product.totalLocations - 1} daha fazla konum
                </Text>
              )}
            </View>
          </View>

          {showActions && (
            <View style={styles.searchActions}>
              <Button
                title="Fiyat Ekle"
                size="small"
                onPress={() => onAddPrice?.(product)}
                style={styles.addPriceButton}
              />
            </View>
          )}
        </TouchableOpacity>
      </Card>
    );
  }

  // Default card variant
  return (
    <Card style={[styles.defaultCard, { width: cardWidth }]} shadow="md">
      <TouchableOpacity onPress={onPress}>
        <View style={styles.imageContainer}>
          {product.image_display_url ? (
            <Image 
              source={{ uri: product.image_display_url }} 
              style={styles.productImage} 
            />
          ) : (
            <View style={styles.placeholderImage}>
              <Ionicons 
                name="image-outline" 
                size={40} 
                color={theme.colors.gray[400]} 
              />
            </View>
          )}
          
          {product.color_info && (
            <Badge 
              variant={getColorBadgeVariant(product.color_info.category)}
              size="small"
              style={styles.overlayBadge}
            >
              {product.color_info.display_name}
            </Badge>
          )}

          {product.is_processed && (
            <View style={styles.aiProcessedIndicator}>
              <Ionicons name="sparkles" size={12} color="white" />
            </View>
          )}
        </View>

        <View style={styles.content}>
          <Text style={styles.productName} numberOfLines={2}>
            {product.name}
          </Text>
          
          <Text style={styles.brandName}>{product.brand}</Text>

          {showPrices && product.lowest_price && (
            <View style={styles.priceSection}>
              <LinearGradient
                colors={theme.colors.gradients.success}
                style={styles.priceGradient}
              >
                <Text style={styles.priceText}>
                  {formatPrice(product.lowest_price.price)}
                </Text>
              </LinearGradient>
              <Text style={styles.storeText} numberOfLines={1}>
                {product.lowest_price.store}
              </Text>
            </View>
          )}

          {showActions && (
            <Button
              title="Fiyat Ekle"
              size="small"
              variant="outline"
              onPress={() => onAddPrice?.(product)}
              style={styles.actionButton}
            />
          )}
        </View>
      </TouchableOpacity>
    </Card>
  );
};

const styles = StyleSheet.create({
  // Default Card Styles
  defaultCard: {
    marginBottom: theme.spacing.md,
    padding: 0,
    overflow: 'hidden',
  },
  imageContainer: {
    position: 'relative',
    height: 120,
    backgroundColor: theme.colors.gray[50],
  },
  productImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  placeholderImage: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.gray[100],
  },
  overlayBadge: {
    position: 'absolute',
    top: theme.spacing.xs,
    left: theme.spacing.xs,
  },
  aiProcessedIndicator: {
    position: 'absolute',
    top: theme.spacing.xs,
    right: theme.spacing.xs,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: theme.colors.primary[500],
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    padding: theme.spacing.md,
  },
  productName: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
    lineHeight: theme.typography.lineHeight.tight * theme.typography.fontSize.sm,
  },
  brandName: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.sm,
  },
  priceSection: {
    marginBottom: theme.spacing.sm,
  },
  priceGradient: {
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.md,
    marginBottom: theme.spacing.xs,
  },
  priceText: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.bold,
    color: 'white',
    textAlign: 'center',
  },
  storeText: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
    textAlign: 'center',
  },
  actionButton: {
    marginTop: theme.spacing.xs,
  },

  // Compact Card Styles
  compactCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    marginBottom: theme.spacing.sm,
    ...theme.shadows.sm,
  },
  compactContent: {
    flexDirection: 'row',
    padding: theme.spacing.md,
    alignItems: 'center',
  },
  compactImage: {
    width: 50,
    height: 50,
    borderRadius: theme.borderRadius.md,
    marginRight: theme.spacing.md,
  },
  compactInfo: {
    flex: 1,
  },
  compactName: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.medium,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  compactBrand: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.xs,
  },
  colorBadge: {
    alignSelf: 'flex-start',
  },
  priceContainer: {
    alignItems: 'flex-end',
  },
  price: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.success[600],
  },
  store: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.text.secondary,
    marginTop: theme.spacing.xs,
  },

  // Search Card Styles
  searchCard: {
    marginBottom: theme.spacing.md,
    padding: theme.spacing.md,
  },
  searchContent: {
    flexDirection: 'row',
    marginBottom: theme.spacing.md,
  },
  searchImageContainer: {
    position: 'relative',
    marginRight: theme.spacing.md,
  },
  searchImage: {
    width: 80,
    height: 80,
    borderRadius: theme.borderRadius.lg,
  },
  searchColorBadge: {
    position: 'absolute',
    bottom: -theme.spacing.xs,
    left: 0,
    right: 0,
    alignSelf: 'center',
  },
  searchInfo: {
    flex: 1,
  },
  searchName: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  searchBrand: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.sm,
  },
  nearestPriceContainer: {
    backgroundColor: theme.colors.success[50],
    padding: theme.spacing.sm,
    borderRadius: theme.borderRadius.md,
    marginBottom: theme.spacing.xs,
  },
  nearestPriceLabel: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.success[700],
    marginBottom: theme.spacing.xs,
  },
  nearestPrice: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.success[700],
  },
  nearestStore: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.success[600],
    marginTop: theme.spacing.xs,
  },
  moreLocations: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.primary[600],
    fontWeight: theme.typography.fontWeight.medium,
  },
  searchActions: {
    alignItems: 'flex-end',
  },
  addPriceButton: {
    minWidth: 100,
  },
});

export default ProductCard;

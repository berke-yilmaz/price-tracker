import config from '../config';
import theme from '../constants/theme';

export const getImageUrl = (product) => {
  try {
    if (!product) return null;

    if (product.image_display_url) {
      return product.image_display_url.startsWith('http')
        ? product.image_display_url
        : `${config.BASE_URL}${product.image_display_url}`;
    }

    if (product.image) {
      return product.image.startsWith('http')
        ? product.image
        : `${config.BASE_URL}${product.image}`;
    }

    return product.image_url || product.image_front_url || null;
  } catch (error) {
    console.error('Error getting image URL for product:', product?.name, error);
    return null;
  }
};

export const getColorForCategory = (colorCategory) => {
  const colorMap = {
    'red': theme.colors.error[500], 'orange': '#FF9800', 'yellow': theme.colors.warning[500],
    'green': theme.colors.success[500], 'blue': theme.colors.primary[500], 'purple': '#9C27B0',
    'pink': '#E91E63', 'brown': '#8D6E63', 'black': theme.colors.gray[800],
    'white': theme.colors.gray[100], 'unknown': theme.colors.gray[400],
  };
  return colorMap[colorCategory] || theme.colors.gray[400];
};

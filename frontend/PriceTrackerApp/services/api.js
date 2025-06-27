// services/api.js - Enhanced with delete functionality
import config from '../config';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const API_URL = config.API_URL;

// Get token for authenticated requests
const getToken = async () => {
  try {
    if (Platform.OS === 'web') {
      return localStorage.getItem('userToken');
    }
    return await AsyncStorage.getItem('userToken');
  } catch (error) {
    console.error('Error getting token:', error);
    return null;
  }
};

// Create fetch with auth headers
const apiFetch = async (url, options = {}) => {
  try {
    const token = await getToken();
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Token ${token}` }),
    };

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    const response = await fetch(`${API_URL}${url}`, config);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  } catch (error) {
    console.error(`API request failed for ${url}:`, error);
    throw error;
  }
};

// Auth API
export const authApi = {
  register: async (userData) => {
    const response = await apiFetch('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    return { data: await response.json() };
  },

  login: async (credentials) => {
    const response = await apiFetch('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    return { data: await response.json() };
  },

  logout: async () => {
    const response = await apiFetch('/auth/logout/', {
      method: 'POST',
    });
    return { data: await response.json() };
  },

  getProfile: async () => {
    const response = await apiFetch('/auth/me/');
    return { data: await response.json() };
  },

  updateProfile: async (userData) => {
    const response = await apiFetch('/auth/me/', {
      method: 'PATCH',
      body: JSON.stringify(userData),
    });
    return { data: await response.json() };
  },

  changePassword: async (passwordData) => {
    const response = await apiFetch('/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify(passwordData),
    });
    return { data: await response.json() };
  },
};

// Enhanced Product API with delete functionality
export const productApi = {
  getProducts: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `/products/${queryString ? `?${queryString}` : ''}`;
    const response = await apiFetch(url);
    return { data: await response.json() };
  },

  getProduct: async (id) => {
    const response = await apiFetch(`/products/${id}/`);
    return { data: await response.json() };
  },

  createProduct: async (productData) => {
    const response = await apiFetch('/products/', {
      method: 'POST',
      body: JSON.stringify(productData),
    });
    return { data: await response.json() };
  },

  updateProduct: async (id, productData) => {
    const response = await apiFetch(`/products/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(productData),
    });
    return { data: await response.json() };
  },

  deleteProduct: async (id) => {
    const response = await apiFetch(`/products/${id}/`, {
      method: 'DELETE',
    });
    
    // For DELETE requests, response might be empty
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return { data: await response.json() };
    }
    return { data: { detail: 'Product deleted successfully' } };
  },

  forceDeleteProduct: async (id) => {
    const response = await apiFetch(`/products/${id}/force_delete/`, {
      method: 'DELETE',
    });
    return { data: await response.json() };
  },

  getDeletionStats: async () => {
    const response = await apiFetch('/products/deletion_stats/');
    return { data: await response.json() };
  },

  searchProducts: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `/products/search/${queryString ? `?${queryString}` : ''}`;
    const response = await apiFetch(url);
    return { data: await response.json() };
  },

  getProductByBarcode: async (barcode) => {
    const response = await apiFetch(`/products/by_barcode/?barcode=${barcode}`);
    return { data: await response.json() };
  },

  addFromBarcode: async (formData) => {
    const token = await getToken();
    const response = await fetch(`${API_URL}/products/add_from_barcode/`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Token ${token}` }),
        // Don't set Content-Type for FormData, let browser set it
      },
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return { data: await response.json() };
  },

  createFromImage: async (formData) => {
    const token = await getToken();
    const response = await fetch(`${API_URL}/products/create-from-image/`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Token ${token}` }),
      },
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return { data: await response.json() };
  },

  identify: async (formData) => {
    const token = await getToken();
    const response = await fetch(`${API_URL}/products/identify/`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Token ${token}` }),
      },
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return { data: await response.json() };
  },

  getGallery: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `/products/gallery/${queryString ? `?${queryString}` : ''}`;
    const response = await apiFetch(url);
    return { data: await response.json() };
  },

  getSimilar: async (id, params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `/products/${id}/similar/${queryString ? `?${queryString}` : ''}`;
    const response = await apiFetch(url);
    return { data: await response.json() };
  },

  getColorStats: async () => {
    const response = await apiFetch('/products/color_stats/');
    return { data: await response.json() };
  },

  quickColorTest: async (formData) => {
    const token = await getToken();
    const response = await fetch(`${API_URL}/quick-color-test/`, {
      method: 'POST',
      headers: {
        ...(token && { 'Authorization': `Token ${token}` }),
      },
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return { data: await response.json() };
  },
};

// Enhanced Price API
export const priceApi = {
  getPrices: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `/prices/${queryString ? `?${queryString}` : ''}`;
    const response = await apiFetch(url);
    return { data: await response.json() };
  },

  getProductPrices: async (productId) => {
    const response = await apiFetch(`/prices/?product=${productId}`);
    return { data: await response.json() };
  },

  addPrice: async (priceData) => {
    const response = await apiFetch('/prices/add_price/', {
      method: 'POST',
      body: JSON.stringify(priceData),
    });
    return { data: await response.json() };
  },

  createPrice: async (priceData) => {
    const response = await apiFetch('/prices/', {
      method: 'POST',
      body: JSON.stringify(priceData),
    });
    return { data: await response.json() };
  },

  getPrice: async (id) => {
    const response = await apiFetch(`/prices/${id}/`);
    return { data: await response.json() };
  },

  updatePrice: async (id, priceData) => {
    const response = await apiFetch(`/prices/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(priceData),
    });
    return { data: await response.json() };
  },

  deletePrice: async (id) => {
    const response = await apiFetch(`/prices/${id}/`, {
      method: 'DELETE',
    });
    
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return { data: await response.json() };
    }
    return { data: { detail: 'Price deleted successfully' } };
  },
};

// Store API
export const storeApi = {
  getStores: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `/stores/${queryString ? `?${queryString}` : ''}`;
    const response = await apiFetch(url);
    return { data: await response.json() };
  },

  getStore: async (id) => {
    const response = await apiFetch(`/stores/${id}/`);
    return { data: await response.json() };
  },

  createStore: async (storeData) => {
    const response = await apiFetch('/stores/', {
      method: 'POST',
      body: JSON.stringify(storeData),
    });
    return { data: await response.json() };
  },

  updateStore: async (id, storeData) => {
    const response = await apiFetch(`/stores/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(storeData),
    });
    return { data: await response.json() };
  },

  deleteStore: async (id) => {
    const response = await apiFetch(`/stores/${id}/`, {
      method: 'DELETE',
    });
    
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return { data: await response.json() };
    }
    return { data: { detail: 'Store deleted successfully' } };
  },

  getColorDistribution: async (id) => {
    const response = await apiFetch(`/stores/${id}/color_distribution/`);
    return { data: await response.json() };
  },
};

// Analytics API
export const analyticsApi = {
  getProcessingStats: async () => {
    const response = await apiFetch('/processing-stats/');
    return { data: await response.json() };
  },

  testVisualIndex: async () => {
    const response = await apiFetch('/test-visual-index/');
    return { data: await response.json() };
  },

  rebuildIndex: async () => {
    const response = await apiFetch('/rebuild-index/', {
      method: 'POST',
    });
    return { data: await response.json() };
  },
};

// Enhanced Utility functions
export const apiUtils = {
  handleError: (error) => {
    if (error.message.includes('HTTP')) {
      const statusMatch = error.message.match(/HTTP (\d+):/);
      const status = statusMatch ? parseInt(statusMatch[1]) : 500;
      
      let message = 'An error occurred';
      if (status === 404) {
        message = 'Resource not found - check your API configuration';
      } else if (status === 401) {
        message = 'Authentication required - please login';
      } else if (status === 403) {
        message = 'Permission denied - insufficient privileges';
      } else if (status === 409) {
        message = 'Conflict - resource already exists or in use';
      } else if (status >= 500) {
        message = 'Server error - please try again later';
      }
      
      return { error: true, message, status };
    } else if (error.message.includes('Network request failed')) {
      return { error: true, message: 'Network error - please check your connection' };
    } else {
      return { error: true, message: error.message || 'Unknown error occurred' };
    }
  },

  createFormData: (data, imageKey = 'image') => {
    const formData = new FormData();
    
    Object.keys(data).forEach(key => {
      if (key === imageKey && data[key]) {
        if (Platform.OS === 'web') {
          formData.append(key, data[key]);
        } else {
          formData.append(key, {
            uri: data[key],
            type: 'image/jpeg',
            name: 'image.jpg',
          });
        }
      } else if (data[key] !== null && data[key] !== undefined) {
        formData.append(key, data[key]);
      }
    });
    
    return formData;
  },

  formatPrice: (price) => {
    if (!price) return '₺0.00';
    return `₺${parseFloat(price).toFixed(2)}`;
  },

  formatDate: (dateString) => {
    if (!dateString) return 'No date';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  },

  // Helper for batch operations
  batchDelete: async (type, ids) => {
    const results = { success: [], failed: [] };
    
    for (const id of ids) {
      try {
        switch (type) {
          case 'products':
            await productApi.deleteProduct(id);
            break;
          case 'prices':
            await priceApi.deletePrice(id);
            break;
          case 'stores':
            await storeApi.deleteStore(id);
            break;
          default:
            throw new Error(`Unknown type: ${type}`);
        }
        results.success.push(id);
      } catch (error) {
        results.failed.push({ id, error: error.message });
      }
    }
    
    return results;
  },

  // Validate required fields for different operations
  validateProduct: (productData) => {
    const required = ['name'];
    const missing = required.filter(field => !productData[field]);
    
    if (missing.length > 0) {
      return { valid: false, message: `Missing required fields: ${missing.join(', ')}` };
    }
    
    return { valid: true };
  },

  validatePrice: (priceData) => {
    const required = ['product', 'store', 'price'];
    const missing = required.filter(field => !priceData[field]);
    
    if (missing.length > 0) {
      return { valid: false, message: `Missing required fields: ${missing.join(', ')}` };
    }
    
    if (isNaN(parseFloat(priceData.price)) || parseFloat(priceData.price) < 0) {
      return { valid: false, message: 'Price must be a valid positive number' };
    }
    
    return { valid: true };
  },

  validateStore: (storeData) => {
    const required = ['name'];
    const missing = required.filter(field => !storeData[field]);
    
    if (missing.length > 0) {
      return { valid: false, message: `Missing required fields: ${missing.join(', ')}` };
    }
    
    return { valid: true };
  },
};

export default {
  authApi,
  productApi,
  priceApi,
  storeApi,
  analyticsApi,
  apiUtils,
};
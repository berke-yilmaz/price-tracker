// services/api.ts
import axios from 'axios';
import config from '../config';

const API_URL = config.API_URL;

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const priceApi = {
  // Tüm fiyatları getir
  getPrices: () => api.get('prices/'),
  
  // Belirli bir ürünün fiyatlarını getir
  getProductPrices: (productId: string) => api.get(`prices/?product=${productId}`),
  
  // Yeni fiyat ekle
  addPrice: (priceData: {
    product: string;
    store: string;
    price: number;
  }) => api.post('prices/', priceData),
  
  // Barkod ile ürün ara
  getProductByBarcode: (barcode: string) => api.get(`products/?barcode=${barcode}`),
  
  // Yeni ürün ekle
  addProduct: (productData: {
    name: string;
    barcode: string;
  }) => api.post('products/', productData),
  
  // Tüm mağazaları getir
  getStores: () => api.get('stores/'),
};

export default api;
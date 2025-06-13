// contexts/AuthContext.jsx
import React, { createContext, useState, useEffect, useContext } from 'react';
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';
import config from '../config';

const API_URL = config.API_URL;

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Uygulama başlatıldığında token kontrolü
  useEffect(() => {
    const loadToken = async () => {
      try {
        const savedToken = await AsyncStorage.getItem('userToken');
        console.log('Saved token found:', !!savedToken);
        if (savedToken) {
          setToken(savedToken);
          await loadUserData(savedToken);
        }
      } catch (err) {
        console.error("Token yükleme hatası:", err);
        Alert.alert('Hata', 'Oturum bilgileri yüklenirken bir hata oluştu');
      } finally {
        setLoading(false);
      }
    };

    loadToken();
  }, []);

  const loadUserData = async (currentToken) => {
    try {
      console.log('Loading user data with token:', currentToken);
      const response = await fetch(`${API_URL}/auth/me/`, {
        headers: {
          'Authorization': `Token ${currentToken}`,
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        }
      });

      console.log('User data response status:', response.status);
      if (!response.ok) {
        throw new Error(`Profil yüklenemedi: ${response.status}`);
      }

      const userData = await response.json();
      console.log('User data loaded successfully');
      setUser(userData);
      return userData;
    } catch (err) {
      console.error("Kullanıcı bilgileri yükleme hatası:", err);
      Alert.alert('Hata', 'Kullanıcı bilgileri yüklenemedi. Lütfen tekrar giriş yapın.');
      logout();
      return null;
    }
  };

  const login = async (credentials) => {
    try {
      setError(null);
      setLoading(true);
      console.log('Attempting login with credentials:', { ...credentials, password: '***' });
      
      const response = await fetch(`${API_URL}/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(credentials),
      });
      
      console.log('Login response status:', response.status);
      const data = await response.json();
      console.log('Login response data:', { ...data, token: data.token ? '***' : null });
      
      if (!response.ok) {
        throw new Error(data.non_field_errors?.[0] || data.detail || 'Giriş başarısız');
      }
      
      // Token'ı kaydet
      const { token } = data;
      await AsyncStorage.setItem('userToken', token);
      console.log('Token saved successfully');
      
      // State güncelle
      setToken(token);
      
      // Kullanıcı bilgilerini yükle
      await loadUserData(token);
      
      setLoading(false);
      return true;
    } catch (err) {
      console.error('Login error:', err);
      setLoading(false);
      
      const message = err.message || 'Giriş yapılamadı';
      setError(message);
      Alert.alert('Hata', message);
      return false;
    }
  };

  const register = async (userData) => {
    try {
      setError(null);
      setLoading(true);
      console.log('Attempting registration with data:', { ...userData, password: '***' });
      
      // API endpoint'i kontrol
      console.log('Register API URL:', `${API_URL}/auth/register/`);
      
      const response = await fetch(`${API_URL}/auth/register/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(userData),
      });
      
      console.log('Register response status:', response.status);
      
      // Response body'yi text olarak al ve log'la
      const responseText = await response.text();
      console.log('Register raw response:', responseText);
      
      // Sonra JSON'a dönüştürmeyi dene
      let data;
      try {
        data = JSON.parse(responseText);
        console.log('Register response data:', { ...data, token: data.token ? '***' : null });
      } catch (jsonErr) {
        console.error('JSON parsing error:', jsonErr);
        throw new Error('Sunucu yanıtı geçerli bir JSON formatında değil.');
      }
      
      if (!response.ok) {
        // Hata mesajlarını derle
        const errors = [];
        Object.keys(data).forEach(key => {
          if (Array.isArray(data[key])) {
            errors.push(`${key}: ${data[key].join(', ')}`);
          } else {
            errors.push(`${key}: ${data[key]}`);
          }
        });
        
        throw new Error(errors.join('\n'));
      }
      
      // Token'ı kaydet
      const { token } = data;
      
      if (!token) {
        throw new Error('Sunucu geçerli bir token döndürmedi');
      }
      
      await AsyncStorage.setItem('userToken', token);
      console.log('Registration token saved successfully');
      
      // State güncelle
      setToken(token);
      setUser(data.user);
      
      setLoading(false);
      return true;
    } catch (err) {
      console.error('Registration error:', err);
      setLoading(false);
      
      const message = err.message || 'Kayıt başarısız';
      setError(message);
      Alert.alert('Hata', message);
      return false;
    }
  };
  const logout = async () => {
    try {
      console.log('Attempting logout');
      // Backend'e logout isteği gönder
      if (token) {
        const response = await fetch(`${API_URL}/auth/logout/`, {
          method: 'POST',
          headers: {
            'Authorization': `Token ${token}`,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
        });
        console.log('Logout response status:', response.status);
      }
    } catch (err) {
      console.error("Çıkış hatası:", err);
    } finally {
      // Local storage temizle
      await AsyncStorage.removeItem('userToken');
      console.log('Token removed from storage');
      setToken(null);
      setUser(null);
    }
  };

  const updateProfile = async (updatedData) => {
    try {
      setLoading(true);
      
      const response = await fetch(`${API_URL}/auth/me/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedData),
      });
      
      if (!response.ok) {
        throw new Error('Profil güncellenemedi');
      }
      
      const updatedUser = await response.json();
      setUser(updatedUser);
      
      setLoading(false);
      return true;
    } catch (err) {
      setLoading(false);
      setError(err.message || 'Profil güncellenemedi');
      return false;
    }
  };

  const changePassword = async (passwordData) => {
    try {
      setLoading(true);
      
      const response = await fetch(`${API_URL}/auth/change-password/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(passwordData),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Şifre değiştirilemedi');
      }
      
      // Yeni token varsa güncelle
      if (data.token) {
        await AsyncStorage.setItem('userToken', data.token);
        setToken(data.token);
      }
      
      setLoading(false);
      return true;
    } catch (err) {
      setLoading(false);
      setError(err.message || 'Şifre değiştirilemedi');
      return false;
    }
  };

  const value = {
    user,
    token,
    loading,
    error,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    isAuthenticated: !!token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
// app/_layout.jsx
import React, { useEffect, useState } from 'react';
import { Stack } from 'expo-router';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import { ActivityIndicator, View, Text } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// AuthContext'i bir bileşen olarak sarmalayan özel bir yönlendirici
function AuthWrapper() {
  const { isAuthenticated, loading } = useAuth();
  const [initialRoute, setInitialRoute] = useState('login');
  const [appReady, setAppReady] = useState(false);

  useEffect(() => {
    async function checkAuth() {
      try {
        const token = await AsyncStorage.getItem('userToken');
        if (token) {
          setInitialRoute('(tabs)');  // Parantezleri koruyun ama "/" işaretini kaldırın
        } else {
          setInitialRoute('login');
        }
      } catch (error) {
        setInitialRoute('login');
      } finally {
        setAppReady(true);
      }
    }

    checkAuth();
  }, [isAuthenticated]); // isAuthenticated değişince yeniden kontrol et

  if (!appReady || loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={{ marginTop: 10, color: '#666' }}>Yükleniyor...</Text>
      </View>
    );
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
      }}
      initialRouteName={initialRoute}
    >
      {/* Kimlik doğrulama ekranları */}
      <Stack.Screen name="login" options={{ gestureEnabled: false }} />
      <Stack.Screen name="register" />
      
      {/* Ana ekranlar */}
      <Stack.Screen 
        name="(tabs)" 
        options={{ 
          gestureEnabled: false,
          headerShown: false,
        }} 
      />
      
      {/* Diğer ekranlar */}
      <Stack.Screen name="addproduct" />
      <Stack.Screen name="addprice" />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <AuthWrapper />
    </AuthProvider>
  );
}
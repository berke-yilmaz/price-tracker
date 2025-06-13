// app/(tabs)/_layout.jsx
import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'index') {
            iconName = focused ? 'home' : 'home-outline';
          } else if (route.name === 'scan') {
            iconName = focused ? 'barcode' : 'barcode-outline';
          } else if (route.name === 'history') {
            iconName = focused ? 'time' : 'time-outline';
          } else if (route.name === 'profile') {
            iconName = focused ? 'person' : 'person-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007AFF',
        tabBarInactiveTintColor: 'gray',
      })}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Anasayfa',
          headerTitle: 'Price Tracker',
        }}
      />
      <Tabs.Screen
        name="scan"
        options={{
          title: 'Tarat',
          headerTitle: 'Ürün Tarat',
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: 'Geçmiş',
          headerTitle: 'Fiyat Geçmişi',
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profil',
          headerTitle: 'Profil',
        }}
      />
    </Tabs>
  );
}
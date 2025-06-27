// components/StoreSelector.jsx - FINAL, LAZY-MOUNTED AND OPTIMIZED VERSION
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../contexts/AuthContext';
import config from '../config';
import theme from '../constants/theme';
import LocationService from '../services/LocationService';
import GoogleMapsStoreView from './GoogleMapsStoreView';
import Button from './ui/Button';
import Input from './ui/Input';

const StoreSelector = ({ onStoreSelect, selectedStore, showCreateNew = true }) => {
  const { token } = useAuth();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  
  // ⭐ LAZY MOUNT STRATEGY ⭐
  // 'list' is the default and only view rendered initially.
  // 'map' will only be set AFTER the user clicks the map button.
  const [viewMode, setViewMode] = useState('list');

  const [isCreateModalVisible, setCreateModalVisible] = useState(false);
  const [newStoreName, setNewStoreName] = useState('');
  const [newStoreAddress, setNewStoreAddress] = useState('');
  const [creatingStore, setCreatingStore] = useState(false);

  useEffect(() => {
    if (isModalOpen) {
      // When modal opens, immediately fetch data but stay in list view.
      initialize();
    } else {
      // When modal closes, ALWAYS reset to list view for the next open.
      setViewMode('list'); 
    }
  }, [isModalOpen]);

  const initialize = async () => {
    setLoading(true);
    const location = await LocationService.getLocationSafely();
    setUserLocation(location);
    await fetchStores(location);
    setLoading(false);
  };

  const fetchStores = async (location) => {
    try {
      let url = `${config.API_URL}/stores/`;
      if (location) {
        url += `?lat=${location.latitude}&lng=${location.longitude}`;
      }
      const response = await fetch(url, { headers: { 'Authorization': `Token ${token}` } });
      if (!response.ok) throw new Error('Failed to fetch stores');
      const data = await response.json();
      setStores(data.results || data || []);
    } catch (error) {
      console.error("Store fetch error:", error);
      Alert.alert("Network Error", "Could not get store list from server.");
    }
  };

  const handleStoreSelection = (store) => {
    onStoreSelect(store);
    setIsModalOpen(false);
  };
  
  const handleCreateStore = async () => {
    if (!newStoreName.trim()) {
      Alert.alert("Validation", "Please enter a store name.");
      return;
    }
    setCreatingStore(true);
    try {
      const storeData = { name: newStoreName.trim(), address: newStoreAddress.trim(), ...(userLocation && { latitude: userLocation.latitude, longitude: userLocation.longitude }) };
      const response = await fetch(`${config.API_URL}/stores/`, { method: 'POST', headers: { 'Authorization': `Token ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(storeData) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || result.detail || 'Failed to create store.');
      const newStore = result.store || result;
      setStores(prev => [newStore, ...prev]);
      setCreateModalVisible(false); setNewStoreName(''); setNewStoreAddress('');
      Alert.alert("Success", `Store "${newStore.name}" created.`);
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setCreatingStore(false);
    }
  };

  const renderStoreItem = (store) => (
    <TouchableOpacity
      key={store.id}
      style={[styles.storeItem, selectedStore?.id === store.id && styles.selectedStoreItem]}
      onPress={() => handleStoreSelection(store)}
    >
      <View style={styles.storeInfo}>
        <Text style={styles.storeName}>{store.name}</Text>
        {store.address ? <Text style={styles.storeAddress}>{store.address}</Text> : null}
        {store.distanceText ? (
            <View style={styles.distanceContainer}>
                <Ionicons name="location" size={14} color={theme.colors.primary[500]} />
                <Text style={styles.distanceText}>{store.distanceText}</Text>
            </View>
        ) : null}
      </View>
      <Ionicons name={selectedStore?.id === store.id ? "radio-button-on" : "radio-button-off"} size={24} color={theme.colors.primary[500]} />
    </TouchableOpacity>
  );

  const renderModalContent = () => {
    if (loading) {
      return <ActivityIndicator style={{ flex: 1 }} size="large" color={theme.colors.primary[500]} />;
    }
    
    // Only ever render ONE of these views.
    if (viewMode === 'map') {
      return (
        <GoogleMapsStoreView 
          stores={stores} 
          userLocation={userLocation} 
          onStoreSelect={(storeId) => {
              const store = stores.find(s => s.id.toString() === storeId.toString());
              if (store) handleStoreSelection(store);
          }}
          embedded={true}
        />
      );
    }

    // Default to list view
    return (
      <ScrollView contentContainerStyle={styles.listContent}>
        {stores.map(renderStoreItem)}
        {showCreateNew && (
          <Button
            title="Add New Store"
            variant="outline"
            onPress={() => setCreateModalVisible(true)}
            icon={<Ionicons name="add-circle-outline" size={20} color={theme.colors.primary[500]} style={{marginRight: 8}}/>}
            style={{marginTop: 16}}
          />
        )}
      </ScrollView>
    );
  };

  return (
    <>
      <TouchableOpacity style={styles.selectorButton} onPress={() => setIsModalOpen(true)}>
        <Text style={selectedStore ? styles.selectorText : styles.placeholderText}>
          {selectedStore?.name || 'Select a store'}
        </Text>
        <Ionicons name="chevron-down" size={20} color={theme.colors.text.secondary} />
      </TouchableOpacity>

      <Modal visible={isModalOpen} animationType="slide" onRequestClose={() => setIsModalOpen(false)}>
        <SafeAreaView style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Select Store</Text>
            <TouchableOpacity style={styles.closeButton} onPress={() => setIsModalOpen(false)}>
              <Ionicons name="close" size={24} color={theme.colors.text.primary} />
            </TouchableOpacity>
          </View>
          
          <View style={styles.viewToggle}>
              <TouchableOpacity style={[styles.toggleButton, viewMode === 'list' && styles.toggleButtonActive]} onPress={() => setViewMode('list')}>
                  <Ionicons name="list" size={20} color={viewMode === 'list' ? theme.colors.primary[500] : theme.colors.text.secondary} />
                  <Text style={[styles.toggleButtonText, viewMode === 'list' && styles.toggleButtonTextActive]}>List</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.toggleButton, viewMode === 'map' && styles.toggleButtonActive]} onPress={() => setViewMode('map')}>
                  <Ionicons name="map" size={20} color={viewMode === 'map' ? theme.colors.primary[500] : theme.colors.text.secondary} />
                  <Text style={[styles.toggleButtonText, viewMode === 'map' && styles.toggleButtonTextActive]}>Map</Text>
              </TouchableOpacity>
          </View>
          
          {/* This now calls the function that guarantees only one view is rendered */}
          {renderModalContent()}

        </SafeAreaView>
      </Modal>

      {/* "Create New Store" modal remains the same */}
      <Modal visible={isCreateModalVisible} animationType="fade" transparent={true} onRequestClose={() => setCreateModalVisible(false)}>
        <View style={styles.createModalOverlay}>
          <View style={styles.createModalContent}>
            <Text style={styles.createModalTitle}>Create New Store</Text>
            <Input label="Store Name" value={newStoreName} onChangeText={setNewStoreName} placeholder="e.g., Migros Jet"/>
            <Input label="Address (Optional)" value={newStoreAddress} onChangeText={setNewStoreAddress} placeholder="e.g., Main Street 123"/>
            {userLocation && (<View style={styles.locationInfo}><Ionicons name="location-sharp" size={14} color={theme.colors.success[600]}/><Text style={styles.locationInfoText}>Your current location will be saved</Text></View>)}
            <View style={styles.createModalButtons}>
              <Button title="Cancel" variant="ghost" onPress={() => setCreateModalVisible(false)} style={{flex: 1}}/>
              <Button title="Create" onPress={handleCreateStore} loading={creatingStore} disabled={creatingStore} style={{flex: 1}}/>
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
};


// Styles are unchanged.
const styles = StyleSheet.create({
    selectorButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: theme.colors.surface, padding: 12, borderRadius: theme.borderRadius.lg, borderWidth: 1, borderColor: theme.colors.gray[300] },
    selectorText: { fontSize: 16, color: theme.colors.text.primary },
    placeholderText: { fontSize: 16, color: theme.colors.gray[500] },
    modalContainer: { flex: 1, backgroundColor: theme.colors.background },
    modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
    modalTitle: { fontSize: 20, fontWeight: '600' },
    closeButton: { padding: 8 },
    viewToggle: { flexDirection: 'row', margin: 16, backgroundColor: theme.colors.gray[100], borderRadius: theme.borderRadius.md, padding: 4 },
    toggleButton: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 8, borderRadius: 6, gap: 6 },
    toggleButtonActive: { backgroundColor: 'white', ...theme.shadows.sm },
    toggleButtonText: { fontSize: 14, fontWeight: '500', color: theme.colors.text.secondary },
    toggleButtonTextActive: { color: theme.colors.primary[500] },
    listContent: { paddingHorizontal: 16, paddingBottom: 24 },
    storeItem: { flexDirection: 'row', padding: 16, marginVertical: 4, backgroundColor: theme.colors.surface, borderRadius: theme.borderRadius.lg, borderWidth: 1, borderColor: theme.colors.gray[200], alignItems: 'center' },
    selectedStoreItem: { borderColor: theme.colors.primary[500], backgroundColor: theme.colors.primary[50] },
    storeInfo: { flex: 1 },
    storeName: { fontSize: 16, fontWeight: '600' },
    storeAddress: { fontSize: 14, color: theme.colors.text.secondary, marginTop: 4 },
    distanceContainer: { flexDirection: 'row', alignItems: 'center', marginTop: 6, backgroundColor: theme.colors.primary[50], paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, alignSelf: 'flex-start' },
    distanceText: { color: theme.colors.primary[600], fontSize: 12, marginLeft: 4 },
    createModalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center', padding: 24 },
    createModalContent: { width: '100%', backgroundColor: 'white', borderRadius: theme.borderRadius.xl, padding: 24 },
    createModalTitle: { fontSize: 22, fontWeight: '700', marginBottom: 24, textAlign: 'center' },
    locationInfo: { flexDirection: 'row', alignItems: 'center', backgroundColor: theme.colors.success[50], padding: 12, borderRadius: 8, marginTop: 8 },
    locationInfoText: { color: theme.colors.success[700], marginLeft: 8 },
    createModalButtons: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 24, gap: 12 },
});

export default StoreSelector;
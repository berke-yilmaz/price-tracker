// components/InlineStoreSelectorWithMaps.jsx - FIXED
/*import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Alert,
  ScrollView,
  ActivityIndicator,
  Modal,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { WebView } from 'react-native-webview';
import { useAuth } from '../contexts/AuthContext';
import LocationService from '../services/LocationService';
import config from '../config';
import theme from '../constants/theme';

const InlineStoreSelectorWithMaps = ({
  selectedStore,
  onStoreSelect,
  stores = [],
  showCreateNew = true,
  userLocation = null
}) => {
  const { token } = useAuth();
  const [storeList, setStoreList] = useState(stores);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newStoreName, setNewStoreName] = useState('');
  const [newStoreAddress, setNewStoreAddress] = useState('');
  const [creatingStore, setCreatingStore] = useState(false);
  const [showStoreModal, setShowStoreModal] = useState(false);
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'map'
  const [mapLoading, setMapLoading] = useState(true);

  // Initialize stores on mount
  useEffect(() => {
    if (stores.length > 0) {
      setStoreList(stores);
    } else {
      fetchStores();
    }
  }, [stores]);

  const fetchStores = async () => {
    setLoading(true);

    try {
      let url = `${config.API_URL}/stores/`;
      if (userLocation) {
        url += `?lat=${userLocation.latitude}&lng=${userLocation.longitude}`;
      }

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Token ${token}` }),
        },
      });

      if (response.ok) {
        const data = await response.json();
        let fetchedStores = data.results || data || [];

        // Add demo stores if we have very few real stores
        if (fetchedStores.length < 2) {
          const demoStores = getDemoStores();
          fetchedStores = [...fetchedStores, ...demoStores];
        }

        setStoreList(fetchedStores);
      } else {
        // Use demo stores on error
        setStoreList(getDemoStores());
      }
    } catch (error) {
      console.error('Store fetch error:', error);
      setStoreList(getDemoStores());
    } finally {
      setLoading(false);
    }
  };

  const getDemoStores = () => {
    const baseLocation = userLocation || { latitude: 41.0082, longitude: 28.9784 }; // Istanbul

    return [
      {
        id: 'bim',
        name: 'BİM',
        address: 'Popular discount store chain',
        latitude: baseLocation.latitude + 0.001,
        longitude: baseLocation.longitude + 0.001,
        isFallback: true
      },
      {
        id: 'migros',
        name: 'Migros',
        address: 'Major supermarket chain',
        latitude: baseLocation.latitude + 0.002,
        longitude: baseLocation.longitude + 0.002,
        isFallback: true
      },
      {
        id: 'a101',
        name: 'A101',
        address: 'Local convenience store',
        latitude: baseLocation.latitude - 0.001,
        longitude: baseLocation.longitude - 0.001,
        isFallback: true
      },
      {
        id: 'sok',
        name: 'Şok',
        address: 'Discount grocery chain',
        latitude: baseLocation.latitude - 0.002,
        longitude: baseLocation.longitude - 0.002,
        isFallback: true
      },
    ];
  };

  const getSelectedStoreName = () => {
    const store = storeList.find(s => s.id === selectedStore);
    return store ? store.name : 'Select Store';
  };

  const handleStoreSelect = (storeId) => {
    onStoreSelect(storeId);
    setShowStoreModal(false);
  };

  const generateMapHTML = () => {
    const apiKey = config.GOOGLE_MAPS_API_KEY;

    if (!apiKey || apiKey === 'YOUR_API_KEY_HERE') {
      return null;
    }

    // Get stores with coordinates
    const mapStores = storeList.filter(store => store.latitude && store.longitude);
    if (mapStores.length === 0) return null;

    const centerLat = userLocation?.latitude || 41.0082;
    const centerLng = userLocation?.longitude || 28.9784;

    // Build markers
    const markersJS = mapStores.map((store, index) => {
      const safeName = store.name.replace(/'/g, "\\'");
      const safeAddress = (store.address || '').replace(/'/g, "\\'");

      return `
        const marker${index} = new google.maps.Marker({
          position: { lat: ${store.latitude}, lng: ${store.longitude} },
          map: map,
          title: '${safeName}',
          icon: {
            url: 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32"><circle cx="12" cy="12" r="10" fill="#e74c3c" stroke="white" stroke-width="2"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-weight="bold">${index + 1}</text></svg>'),
            scaledSize: new google.maps.Size(32, 32),
          }
        });

        const infoWindow${index} = new google.maps.InfoWindow({
          content: '<div style="max-width: 200px;"><div style="font-weight: bold; margin-bottom: 4px;">${safeName}</div><div style="font-size: 12px; color: #666; margin-bottom: 8px;">${safeAddress}</div><button onclick="selectStore(\\'${store.id}\\')" style="background: #1a73e8; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer;">Select This Store</button></div>'
        });

        marker${index}.addListener('click', () => {
          ${mapStores.map((_, i) => `infoWindow${i}.close();`).join(' ')}
          infoWindow${index}.open(map, marker${index});
        });
      `;
    }).join('');

    return `
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { margin: 0; padding: 0; }
        #map { height: 100vh; width: 100%; }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-family: Arial, sans-serif;
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div id="loading" class="loading">Loading map...</div>
    <div id="map"></div>

    <script>
        function initMap() {
            try {
                document.getElementById('loading').style.display = 'none';

                const map = new google.maps.Map(document.getElementById('map'), {
                    zoom: 13,
                    center: { lat: ${centerLat}, lng: ${centerLng} },
                    mapTypeControl: true,
                    streetViewControl: false,
                    zoomControl: true
                });

                ${markersJS}

                ${userLocation ? `
                const userMarker = new google.maps.Marker({
                  position: { lat: ${userLocation.latitude}, lng: ${userLocation.longitude} },
                  map: map,
                  title: 'Your Location',
                  icon: {
                    url: 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28"><circle cx="12" cy="12" r="8" fill="#34d399" stroke="white" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="white"/></svg>'),
                    scaledSize: new google.maps.Size(28, 28),
                  }
                });
                ` : ''}

                const bounds = new google.maps.LatLngBounds();
                ${mapStores.map((_, i) => `bounds.extend(marker${i}.getPosition());`).join(' ')}
                ${userLocation ? `bounds.extend({ lat: ${userLocation.latitude}, lng: ${userLocation.longitude} });` : ''}
                map.fitBounds(bounds);

                if (window.ReactNativeWebView) {
                  window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'MAP_LOADED' }));
                }

            } catch (error) {
                console.error('Map error:', error);
                document.getElementById('loading').innerHTML = 'Map failed to load';
            }
        }

        function selectStore(storeId) {
            if (window.ReactNativeWebView) {
                window.ReactNativeWebView.postMessage(JSON.stringify({
                    type: 'STORE_SELECT',
                    storeId: storeId
                }));
            }
        }

        window.initMap = initMap;
        window.gm_authFailure = function() {
            document.getElementById('loading').innerHTML = 'Authentication failed';
        };
    </script>

    <script async defer
        src="https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap">
    </script>
</body>
</html>`;
  };

  const handleWebViewMessage = (event) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);

      if (data.type === 'MAP_LOADED') {
        setMapLoading(false);
      } else if (data.type === 'STORE_SELECT') {
        handleStoreSelect(data.storeId);
      }
    } catch (error) {
      console.error('WebView message error:', error);
    }
  };

  const renderStoreItem = (store) => {
    const isSelected = store.id === selectedStore;
    const hasLocation = store.latitude && store.longitude;

    return (
      <TouchableOpacity
        key={store.id}
        style={[styles.storeItem, isSelected && styles.selectedStoreItem]}
        onPress={() => handleStoreSelect(store.id)}
      >
        <View style={styles.storeInfo}>
          <View style={styles.storeHeader}>
            <Text style={styles.storeName}>{store.name}</Text>
            {store.isFallback && (
              <View style={styles.fallbackBadge}>
                <Text style={styles.fallbackBadgeText}>Demo</Text>
              </View>
            )}
          </View>

          {store.address && (
            <Text style={styles.storeAddress}>{store.address}</Text>
          )}
        </View>

        <View style={styles.storeActions}>
          {hasLocation && (
            <Ionicons name="map-outline" size={16} color={theme.colors.primary[500]} />
          )}
          <Ionicons
            name={isSelected ? "radio-button-on" : "radio-button-off"}
            size={24}
            color={theme.colors.primary[500]}
          />
        </View>
      </TouchableOpacity>
    );
  };

  const renderMapView = () => {
    const mapStores = storeList.filter(store => store.latitude && store.longitude);

    if (mapStores.length === 0) {
      return (
        <View style={styles.mapUnavailable}>
          <Ionicons name="map-outline" size={48} color={theme.colors.gray[400]} />
          <Text style={styles.mapUnavailableTitle}>No Map Data</Text>
          <Text style={styles.mapUnavailableText}>
            No stores have location data for map view
          </Text>
        </View>
      );
    }

    const mapHTML = generateMapHTML();
    if (!mapHTML) {
      return (
        <View style={styles.mapUnavailable}>
          <Ionicons name="warning-outline" size={48} color={theme.colors.error[500]} />
          <Text style={styles.mapUnavailableTitle}>Maps Not Available</Text>
          <Text style={styles.mapUnavailableText}>
            Google Maps API key not configured
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.mapContainer}>
        {mapLoading && (
          <View style={styles.mapLoadingOverlay}>
            <ActivityIndicator size="large" color={theme.colors.primary[500]} />
            <Text style={styles.mapLoadingText}>Loading map...</Text>
          </View>
        )}

        <WebView
          source={{ html: mapHTML }}
          style={styles.mapWebView}
          onMessage={handleWebViewMessage}
          onLoadStart={() => setMapLoading(true)}
          javaScriptEnabled={true}
          domStorageEnabled={true}
        />
      </View>
    );
  };

  const renderViewToggle = () => (
    <View style={styles.viewToggle}>
      <TouchableOpacity
        style={[styles.toggleButton, viewMode === 'list' && styles.toggleButtonActive]}
        onPress={() => setViewMode('list')}
      >
        <Ionicons
          name="list"
          size={20}
          color={viewMode === 'list' ? theme.colors.primary[500] : theme.colors.text.secondary}
        />
        <Text style={[
          styles.toggleButtonText,
          viewMode === 'list' && styles.toggleButtonTextActive
        ]}>
          List
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.toggleButton, viewMode === 'map' && styles.toggleButtonActive]}
        onPress={() => setViewMode('map')}
      >
        <Ionicons
          name="map"
          size={20}
          color={viewMode === 'map' ? theme.colors.primary[500] : theme.colors.text.secondary}
        />
        <Text style={[
          styles.toggleButtonText,
          viewMode === 'map' && styles.toggleButtonTextActive
        ]}>
          Map
        </Text>
      </TouchableOpacity>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="small" color={theme.colors.primary[500]} />
        <Text style={styles.loadingText}>Loading stores...</Text>
      </View>
    );
  }

  return (
    <>
      <TouchableOpacity
        style={styles.selectorButton}
        onPress={() => setShowStoreModal(true)}
      >
        <Text style={styles.selectorLabel}>Store</Text>
        <View style={styles.selectorValueContainer}>
          <Text style={[
            styles.selectorValue,
            !selectedStore && styles.placeholderText
          ]}>
            {getSelectedStoreName()}
          </Text>
          <Ionicons name="chevron-down" size={20} color={theme.colors.text.secondary} />
        </View>
      </TouchableOpacity>

      <Modal
        visible={showStoreModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowStoreModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Store</Text>
              <TouchableOpacity
                style={styles.closeButton}
                onPress={() => setShowStoreModal(false)}
              >
                <Ionicons name="close" size={24} color={theme.colors.text.primary} />
              </TouchableOpacity>
            </View>

            {renderViewToggle()}

            {viewMode === 'list' ? (
              <ScrollView style={styles.storeList} showsVerticalScrollIndicator={false}>
                {storeList.map(renderStoreItem)}

                {showCreateNew && (
                  <TouchableOpacity
                    style={styles.createNewButton}
                    onPress={() => setShowCreateModal(true)}
                  >
                    <Ionicons name="add-circle-outline" size={20} color={theme.colors.primary[500]} />
                    <Text style={styles.createNewText}>Add New Store</Text>
                  </TouchableOpacity>
                )}

                {storeList.length === 0 && (
                  <View style={styles.emptyState}>
                    <Ionicons name="storefront-outline" size={48} color={theme.colors.gray[400]} />
                    <Text style={styles.emptyStateText}>No stores available</Text>
                  </View>
                )}
              </ScrollView>
            ) : (
              renderMapView()
            )}
          </View>
        </View>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: theme.colors.gray[50],
    borderRadius: 8,
  },
  loadingText: {
    marginLeft: 12,
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  selectorButton: {
    backgroundColor: 'white',
    borderWidth: 1,
    borderColor: theme.colors.gray[300],
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
  },
  selectorLabel: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    marginBottom: 4,
  },
  selectorValueContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  selectorValue: {
    fontSize: 16,
    color: theme.colors.text.primary,
    flex: 1,
  },
  placeholderText: {
    color: theme.colors.text.secondary,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: 'white',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '85%',
    minHeight: '70%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: theme.colors.text.primary,
  },
  closeButton: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: theme.colors.gray[100],
  },
  viewToggle: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginVertical: 10,
    backgroundColor: theme.colors.gray[100],
    borderRadius: 8,
    padding: 4,
  },
  toggleButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    borderRadius: 6,
    gap: 6,
  },
  toggleButtonActive: {
    backgroundColor: 'white',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  toggleButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: theme.colors.text.secondary,
  },
  toggleButtonTextActive: {
    color: theme.colors.primary[500],
  },
  storeList: {
    flex: 1,
    paddingHorizontal: 20,
  },
  storeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
    marginVertical: 4,
    backgroundColor: 'white',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: theme.colors.gray[200],
  },
  selectedStoreItem: {
    borderColor: theme.colors.primary[300],
    backgroundColor: theme.colors.primary[50],
  },
  storeInfo: {
    flex: 1,
  },
  storeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  storeName: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text.primary,
    flex: 1,
  },
  fallbackBadge: {
    // ⭐ FIX: Use bracket notation and provide a fallback
    backgroundColor: theme.colors.info?.[100] ?? theme.colors.gray[200],
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginLeft: 8,
  },
  fallbackBadgeText: {
    fontSize: 12,
    // ⭐ FIX: Use bracket notation and provide a fallback
    color: theme.colors.info?.[700] ?? theme.colors.gray[600],
    fontWeight: '500',
  },
  // --- END OF FIX ---
  storeAddress: {
    fontSize: 14,
    color: theme.colors.text.secondary,
  },
  storeActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  mapContainer: {
    flex: 1,
    marginHorizontal: 20,
    marginBottom: 20,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: theme.colors.gray[100],
    position: 'relative',
  },
  mapWebView: {
    flex: 1,
  },
  mapLoadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1,
  },
  mapLoadingText: {
    marginTop: 12,
    fontSize: 16,
    color: theme.colors.text.secondary,
  },
  mapUnavailable: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 40,
  },
  mapUnavailableTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text.primary,
    marginTop: 16,
    marginBottom: 8,
  },
  mapUnavailableText: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  createNewButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
    marginVertical: 8,
    backgroundColor: theme.colors.primary[50],
    borderRadius: 12,
    borderWidth: 1,
    borderColor: theme.colors.primary[200],
    borderStyle: 'dashed',
  },
  createNewText: {
    fontSize: 16,
    color: theme.colors.primary[600],
    fontWeight: '500',
    marginLeft: 8,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
  },
  emptyStateText: {
    fontSize: 16,
    color: theme.colors.text.secondary,
    marginTop: 12,
  },
});

export default InlineStoreSelectorWithMaps;*/
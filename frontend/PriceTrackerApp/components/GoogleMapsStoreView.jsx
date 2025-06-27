// components/GoogleMapsStoreView.jsx - FINAL ROBUST VERSION
import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
  Alert,
  Linking,
  Platform,
  SafeAreaView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { WebView } from 'react-native-webview';
import theme from '../constants/theme';
import config from '../config';

const GoogleMapsStoreView = ({ 
  visible, 
  onClose, 
  store = null, 
  stores = [], 
  userLocation,
  onStoreSelect = null, 
  embedded = false 
}) => {
  const [loading, setLoading] = useState(true);
  const webViewRef = useRef(null);

  const generateMapHTML = () => {
    const apiKey = config.GOOGLE_MAPS_API_KEY;
    if (!apiKey || apiKey === 'YOUR_API_KEY_HERE' || apiKey.length < 10) {
      return null;
    }

    let mapStores = store ? [store] : stores.filter(s => s.latitude && s.longitude);
    if (mapStores.length === 0) return null;

    const centerLat = store?.latitude || userLocation?.latitude || mapStores[0].latitude;
    const centerLng = store?.longitude || userLocation?.longitude || mapStores[0].longitude;

    const markersData = mapStores.map(s => ({
      id: s.id,
      name: s.name,
      address: s.address || '',
      lat: s.latitude,
      lng: s.longitude
    }));

    const mapConfig = {
      apiKey,
      center: { lat: centerLat, lng: centerLng },
      zoom: store ? 15 : 12,
      markers: markersData,
      userLocation: userLocation,
      onStoreSelect: !!onStoreSelect // Pass a boolean to know if the button should be rendered
    };

    return `
      <!DOCTYPE html>
      <html>
      <head>
          <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
          <style>
              body, html, #map { margin: 0; padding: 0; height: 100%; width: 100%; font-family: -apple-system, sans-serif; }
              #loader { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); z-index: 10; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
              .info-window { padding: 5px; max-width: 220px; }
              .info-window .name { font-weight: 600; margin-bottom: 4px; }
              .info-window .address { font-size: 13px; color: #555; }
              .info-window .button { background: #007AFF; color: white; border: none; padding: 8px 12px; border-radius: 6px; margin-top: 10px; font-size: 13px; width: 100%; cursor: pointer; }
          </style>
      </head>
      <body>
          <div id="map"></div>
          <div id="loader">Loading Map...</div>

          <script>
              const postMessage = (payload) => window.ReactNativeWebView.postMessage(JSON.stringify(payload));
              
              function initMap() {
                  try {
                      document.getElementById('loader').style.display = 'none';
                      const config = ${JSON.stringify(mapConfig)};
                      
                      const map = new google.maps.Map(document.getElementById('map'), {
                          center: config.center,
                          zoom: config.zoom,
                          mapTypeControl: false,
                          streetViewControl: false,
                          fullscreenControl: false,
                      });

                      const bounds = new google.maps.LatLngBounds();
                      let openInfoWindow = null;

                      config.markers.forEach(markerData => {
                          const position = { lat: markerData.lat, lng: markerData.lng };
                          const marker = new google.maps.Marker({ position, map, title: markerData.name });
                          bounds.extend(position);
                          
                          let infoContent = '<div class="info-window"><div class="name">' + markerData.name + '</div>';
                          if (markerData.address) {
                            infoContent += '<div class="address">' + markerData.address + '</div>';
                          }
                          if(config.onStoreSelect) {
                            infoContent += '<button class="button" onclick="postMessage({type: \\'STORE_SELECT\\', storeId: \\'' + markerData.id + '\\'})">Select This Store</button>';
                          }
                          infoContent += '</div>';

                          const infowindow = new google.maps.InfoWindow({ content: infoContent });

                          marker.addListener('click', () => {
                              if(openInfoWindow) openInfoWindow.close();
                              infowindow.open(map, marker);
                              openInfoWindow = infowindow;
                          });
                      });

                      if(config.userLocation) {
                        bounds.extend({ lat: config.userLocation.latitude, lng: config.userLocation.longitude });
                        new google.maps.Marker({ position: { lat: config.userLocation.latitude, lng: config.userLocation.longitude }, map, title: 'Your Location', icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'});
                      }

                      if (config.markers.length > 1 || config.userLocation) {
                        map.fitBounds(bounds);
                      }
                      
                      postMessage({ type: 'MAP_LOADED' });
                  } catch(e) {
                      postMessage({ type: 'ERROR', message: 'Map init failed: ' + e.message });
                  }
              }

              window.gm_authFailure = () => postMessage({ type: 'ERROR', message: 'Google Maps Authentication Failed. Check API Key.' });
          </script>
          <script async defer src="https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap"></script>
      </body>
      </html>
    `;
  };

  const handleWebViewMessage = (event) => {
    try {
      const { type, storeId, message } = JSON.parse(event.nativeEvent.data);
      if (type === 'MAP_LOADED') {
        setLoading(false);
      } else if (type === 'STORE_SELECT' && onStoreSelect) {
        onStoreSelect(storeId);
      } else if (type === 'ERROR') {
        setLoading(false);
        Alert.alert('Map Error', message);
      }
    } catch (e) {
      console.error("WebView message parse error", e);
    }
  };

  const mapHTML = generateMapHTML();

  if (embedded) {
    if (!mapHTML) return <View style={styles.mapError}><Text>Maps API key not configured.</Text></View>;
    return (
      <View style={styles.container}>
        {loading && <View style={styles.loadingOverlay}><ActivityIndicator size="large" color={theme.colors.primary[500]} /></View>}
        <WebView
          ref={webViewRef}
          source={{ html: mapHTML }}
          style={styles.webview}
          onMessage={handleWebViewMessage}
          onError={(e) => Alert.alert('WebView Error', e.nativeEvent.description)}
        />
      </View>
    );
  }

  // Standalone Modal version
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
            <Text style={styles.title}>{store ? store.name : 'Nearby Stores'}</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <Ionicons name="close" size={24} color={theme.colors.text.primary}/>
            </TouchableOpacity>
        </View>
        {!mapHTML ? <View style={styles.mapError}><Text>Maps API key not configured.</Text></View> : (
            <WebView
              ref={webViewRef}
              source={{ html: mapHTML }}
              style={styles.webview}
              onMessage={handleWebViewMessage}
              onError={(e) => Alert.alert('WebView Error', e.nativeEvent.description)}
            />
        )}
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'white' },
  webview: { flex: 1 },
  loadingOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(255,255,255,0.8)', justifyContent: 'center', alignItems: 'center' },
  mapError: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
  title: { fontSize: 18, fontWeight: '600' },
  closeButton: { padding: 4 }
});

export default GoogleMapsStoreView;
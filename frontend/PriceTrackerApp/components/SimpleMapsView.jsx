// SimpleMapsView.jsx - Simplified version that should work with your API
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { WebView } from 'react-native-webview';
import theme from '../constants/theme';
import config from '../config';

const SimpleMapsView = ({ 
  visible, 
  onClose, 
  stores = [], 
  userLocation = null 
}) => {
  const [loading, setLoading] = useState(true);

  const generateSimpleMapHTML = () => {
    const apiKey = config.GOOGLE_MAPS_API_KEY;
    
    if (!apiKey || apiKey === 'YOUR_API_KEY_HERE') {
      return null;
    }

    // Use a simple center point - Istanbul
    const centerLat = userLocation?.latitude || 41.0082;
    const centerLng = userLocation?.longitude || 28.9784;

    return `<!DOCTYPE html>
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
        console.log('Starting map initialization...');
        
        function initMap() {
            console.log('initMap called');
            try {
                document.getElementById('loading').style.display = 'none';
                
                const map = new google.maps.Map(document.getElementById('map'), {
                    zoom: 12,
                    center: { lat: ${centerLat}, lng: ${centerLng} },
                    mapTypeControl: true,
                    streetViewControl: true,
                    zoomControl: true
                });
                
                console.log('Map created successfully');
                
                // Add a test marker
                const marker = new google.maps.Marker({
                    position: { lat: ${centerLat}, lng: ${centerLng} },
                    map: map,
                    title: 'Test Location'
                });
                
                console.log('Marker added');
                
                // Notify React Native that map loaded
                if (window.ReactNativeWebView) {
                    window.ReactNativeWebView.postMessage(JSON.stringify({
                        type: 'MAP_LOADED',
                        success: true
                    }));
                }
                
            } catch (error) {
                console.error('Map initialization error:', error);
                document.getElementById('loading').innerHTML = 'Map failed to load: ' + error.message;
                
                if (window.ReactNativeWebView) {
                    window.ReactNativeWebView.postMessage(JSON.stringify({
                        type: 'MAP_ERROR',
                        error: error.message
                    }));
                }
            }
        }
        
        // Set up error handler
        window.gm_authFailure = function() {
            console.error('Google Maps authentication failed');
            document.getElementById('loading').innerHTML = 'Authentication failed';
        };
        
        // Initialize when ready
        window.initMap = initMap;
        
        // Fallback timeout
        setTimeout(() => {
            if (!window.google || !window.google.maps) {
                console.error('Google Maps API failed to load after 10 seconds');
                document.getElementById('loading').innerHTML = 'Map loading timeout';
            }
        }, 10000);
        
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
      console.log('📱 WebView message:', data);
      
      if (data.type === 'MAP_LOADED') {
        setLoading(false);
        console.log('🗺️ Map loaded successfully!');
      } else if (data.type === 'MAP_ERROR') {
        setLoading(false);
        console.error('🗺️ Map error:', data.error);
      }
    } catch (error) {
      console.error('Error parsing WebView message:', error);
    }
  };

  const mapHTML = generateSimpleMapHTML();

  if (!visible) return null;

  if (!mapHTML) {
    return (
      <Modal visible={visible} onRequestClose={onClose}>
        <View style={styles.container}>
          <View style={styles.header}>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={24} />
            </TouchableOpacity>
            <Text style={styles.title}>Map Error</Text>
          </View>
          <View style={styles.center}>
            <Text>Google Maps API key not configured</Text>
          </View>
        </View>
      </Modal>
    );
  }

  return (
    <Modal visible={visible} onRequestClose={onClose}>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color={theme.colors.text.primary} />
          </TouchableOpacity>
          <Text style={styles.title}>Google Maps Test</Text>
          <View style={styles.placeholder} />
        </View>
        
        <View style={styles.mapContainer}>
          <WebView
            source={{ html: mapHTML }}
            style={styles.webview}
            onMessage={handleWebViewMessage}
            onLoadStart={() => {
              console.log('🔄 WebView loading started');
              setLoading(true);
            }}
            onLoadEnd={() => {
              console.log('🔄 WebView loading ended');
            }}
            onError={(syntheticEvent) => {
              const { nativeEvent } = syntheticEvent;
              console.error('🔄 WebView error:', nativeEvent);
              setLoading(false);
            }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            startInLoadingState={false}
            mixedContentMode="compatibility"
          />
          
          {loading && (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color={theme.colors.primary[500]} />
              <Text style={styles.loadingText}>Initializing map...</Text>
            </View>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'white',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 50,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
  },
  closeButton: {
    padding: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text.primary,
  },
  placeholder: {
    width: 40,
  },
  mapContainer: {
    flex: 1,
    position: 'relative',
  },
  webview: {
    flex: 1,
  },
  loadingOverlay: {
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
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: theme.colors.text.secondary,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default SimpleMapsView;
// MapsDebugFix.jsx - Debug and fix maps loading issues
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { WebView } from 'react-native-webview';
import config from '../config';
import theme from '../constants/theme';

const MapsDebugFix = ({ visible, onClose }) => {
  const [testApiKey, setTestApiKey] = useState(config.GOOGLE_MAPS_API_KEY || '');
  const [showTestMap, setShowTestMap] = useState(false);
  const [testResults, setTestResults] = useState(null);

  const runApiKeyTest = async () => {
    if (!testApiKey || testApiKey.length < 30) {
      Alert.alert('Invalid Key', 'API key must be at least 30 characters long');
      return;
    }

    setTestResults({ testing: true });

    // Test the API key with a simple request
    const testUrl = `https://maps.googleapis.com/maps/api/js?key=${testApiKey}&libraries=geometry&callback=testCallback`;
    
    try {
      // Create test HTML
      const testHTML = generateTestHTML(testApiKey);
      setShowTestMap(true);
      
      console.log('🧪 Testing API key:', testApiKey.substring(0, 10) + '...');
      console.log('🧪 Test URL:', testUrl);
      
    } catch (error) {
      setTestResults({ 
        success: false, 
        error: error.message 
      });
    }
  };

  const generateTestHTML = (apiKey) => {
    return `
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f5f5f5;
        }
        #map { 
            height: 300px; 
            width: 100%; 
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            background: white;
        }
        .status { 
            padding: 16px; 
            margin: 16px 0; 
            border-radius: 8px; 
            text-align: center;
            font-weight: 500;
        }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .loading { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        pre { 
            background: #f8f9fa; 
            padding: 12px; 
            border-radius: 4px; 
            font-size: 12px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <h2>🗺️ Google Maps API Test</h2>
    <div id="status" class="status loading">Testing API key...</div>
    <div id="map"></div>
    
    <div id="details">
        <h3>Test Details:</h3>
        <pre id="apiKeyInfo">API Key: ${apiKey.substring(0, 10)}...${apiKey.substring(apiKey.length - 4)}
Length: ${apiKey.length} characters
Format: ${apiKey.startsWith('AIza') ? 'Valid (AIza...)' : 'Invalid (should start with AIza)'}
Test Time: ${new Date().toISOString()}</pre>
    </div>

    <script>
        let testStartTime = Date.now();
        
        function updateStatus(message, className = 'info') {
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.className = 'status ' + className;
        }

        function testCallback() {
            try {
                updateStatus('✅ API key is valid! Initializing map...', 'success');
                initMap();
            } catch (error) {
                updateStatus('❌ Map initialization failed: ' + error.message, 'error');
                sendMessage('MAP_INIT_ERROR', error.message);
            }
        }

        function initMap() {
            try {
                const map = new google.maps.Map(document.getElementById('map'), {
                    zoom: 10,
                    center: { lat: 41.0082, lng: 28.9784 }, // Istanbul
                    mapTypeControl: true,
                    streetViewControl: true,
                    fullscreenControl: false,
                });

                // Add a test marker
                const marker = new google.maps.Marker({
                    position: { lat: 41.0082, lng: 28.9784 },
                    map: map,
                    title: 'Test Marker - Istanbul',
                    icon: {
                        url: 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32"><circle cx="12" cy="12" r="10" fill="#1a73e8" stroke="white" stroke-width="2"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-weight="bold">✓</text></svg>'),
                        scaledSize: new google.maps.Size(32, 32),
                    }
                });

                const loadTime = Date.now() - testStartTime;
                updateStatus(\`🎉 Success! Map loaded in \${loadTime}ms\`, 'success');
                
                sendMessage('MAP_SUCCESS', {
                    loadTime: loadTime,
                    apiKey: '${apiKey.substring(0, 10)}...',
                    mapCenter: { lat: 41.0082, lng: 28.9784 }
                });

            } catch (error) {
                updateStatus('❌ Map creation failed: ' + error.message, 'error');
                sendMessage('MAP_ERROR', error.message);
            }
        }

        function sendMessage(type, data) {
            if (window.ReactNativeWebView) {
                window.ReactNativeWebView.postMessage(JSON.stringify({
                    type: type,
                    data: data,
                    timestamp: Date.now()
                }));
            }
        }

        // Handle API load errors
        function handleApiError() {
            updateStatus('❌ Failed to load Google Maps API. Check your API key and network.', 'error');
            sendMessage('API_LOAD_ERROR', 'Google Maps API failed to load');
        }

        // Set up error handlers
        window.gm_authFailure = function() {
            updateStatus('❌ API Key Authentication Failed! Check your key and billing.', 'error');
            sendMessage('AUTH_FAILURE', 'API key authentication failed');
        };

        // Timeout check
        setTimeout(() => {
            if (!window.google) {
                handleApiError();
            }
        }, 10000); // 10 second timeout
    </script>
    
    <script async defer 
        src="https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=testCallback&libraries=geometry"
        onerror="handleApiError()">
    </script>
</body>
</html>`;
  };

  const handleWebViewMessage = (event) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      console.log('🧪 Test result:', data);
      
      switch (data.type) {
        case 'MAP_SUCCESS':
          setTestResults({
            success: true,
            loadTime: data.data.loadTime,
            message: `Map loaded successfully in ${data.data.loadTime}ms`
          });
          Alert.alert(
            'Success! 🎉',
            'Your Google Maps API key is working correctly. The issue might be in your app configuration.',
            [
              { text: 'OK' },
              { text: 'Copy Working Key', onPress: () => copyApiKey() }
            ]
          );
          break;
          
        case 'AUTH_FAILURE':
          setTestResults({
            success: false,
            error: 'API key authentication failed. Check your key and billing settings.'
          });
          Alert.alert(
            'Authentication Failed ❌',
            'Your API key is invalid or billing is not enabled in Google Cloud Console.',
            [
              { text: 'OK' },
              { text: 'Open Google Cloud', onPress: () => openGoogleCloud() }
            ]
          );
          break;
          
        case 'API_LOAD_ERROR':
          setTestResults({
            success: false,
            error: 'Google Maps API failed to load. Check your internet connection.'
          });
          break;
          
        case 'MAP_ERROR':
        case 'MAP_INIT_ERROR':
          setTestResults({
            success: false,
            error: data.data
          });
          break;
      }
    } catch (error) {
      console.error('Error parsing test result:', error);
    }
  };

  const copyApiKey = () => {
    // You could implement clipboard copying here
    Alert.alert('API Key', testApiKey);
  };

  const openGoogleCloud = () => {
    Linking.openURL('https://console.cloud.google.com/apis/credentials');
  };

  const fixCommonIssues = () => {
    Alert.alert(
      'Common Fixes',
      '1. Enable Maps JavaScript API in Google Cloud\n2. Enable billing\n3. Check API key restrictions\n4. Restart app after .env changes',
      [
        { text: 'OK' },
        { text: 'Open Google Cloud', onPress: openGoogleCloud }
      ]
    );
  };

  if (!visible) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🗺️ Maps Debug & Fix</Text>
        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
          <Ionicons name="close" size={24} color={theme.colors.text.primary} />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {/* Current Status */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Current Configuration</Text>
          <View style={styles.statusItem}>
            <Text style={styles.label}>Environment API Key:</Text>
            <Text style={styles.value}>
              {process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY ? 
                process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY.substring(0, 10) + '...' : 
                'NOT SET'}
            </Text>
          </View>
          <View style={styles.statusItem}>
            <Text style={styles.label}>Config API Key:</Text>
            <Text style={styles.value}>
              {config.GOOGLE_MAPS_API_KEY ? 
                config.GOOGLE_MAPS_API_KEY.substring(0, 10) + '...' : 
                'NOT SET'}
            </Text>
          </View>
          <View style={styles.statusItem}>
            <Text style={styles.label}>Maps Enabled:</Text>
            <Text style={styles.value}>
              {process.env.EXPO_PUBLIC_ENABLE_MAPS === 'true' ? 'Yes' : 'No'}
            </Text>
          </View>
        </View>

        {/* Test API Key */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Test API Key</Text>
          <TextInput
            style={styles.input}
            value={testApiKey}
            onChangeText={setTestApiKey}
            placeholder="Paste your Google Maps API key here"
            multiline
          />
          <TouchableOpacity style={styles.testButton} onPress={runApiKeyTest}>
            <Ionicons name="flask" size={20} color="white" />
            <Text style={styles.testButtonText}>Test This API Key</Text>
          </TouchableOpacity>
        </View>

        {/* Test Results */}
        {testResults && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Test Results</Text>
            <View style={[
              styles.result, 
              testResults.success ? styles.resultSuccess : styles.resultError
            ]}>
              <Ionicons 
                name={testResults.success ? "checkmark-circle" : "close-circle"} 
                size={24} 
                color={testResults.success ? theme.colors.success[500] : theme.colors.error[500]} 
              />
              <Text style={styles.resultText}>
                {testResults.success ? testResults.message : testResults.error}
              </Text>
            </View>
          </View>
        )}

        {/* Live Test Map */}
        {showTestMap && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Live API Test</Text>
            <View style={styles.mapContainer}>
              <WebView
                source={{ html: generateTestHTML(testApiKey) }}
                style={styles.webview}
                onMessage={handleWebViewMessage}
                javaScriptEnabled={true}
                domStorageEnabled={true}
              />
            </View>
          </View>
        )}

        {/* Quick Fixes */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Fixes</Text>
          <TouchableOpacity style={styles.fixButton} onPress={fixCommonIssues}>
            <Ionicons name="construct" size={20} color={theme.colors.primary[500]} />
            <Text style={styles.fixButtonText}>Common Issues & Solutions</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.fixButton} onPress={openGoogleCloud}>
            <Ionicons name="cloud" size={20} color={theme.colors.primary[500]} />
            <Text style={styles.fixButtonText}>Open Google Cloud Console</Text>
          </TouchableOpacity>
        </View>

        {/* Step by Step Guide */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Fix Steps</Text>
          <Text style={styles.stepText}>1. Get API key from Google Cloud Console</Text>
          <Text style={styles.stepText}>2. Enable Maps JavaScript API</Text>
          <Text style={styles.stepText}>3. Enable billing (required for Maps)</Text>
          <Text style={styles.stepText}>4. Add to .env: EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=your_key</Text>
          <Text style={styles.stepText}>5. Restart app: npx expo start --clear</Text>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'white',
    zIndex: 1000,
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
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: theme.colors.text.primary,
  },
  closeButton: {
    padding: 8,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  section: {
    marginBottom: 24,
    padding: 16,
    backgroundColor: theme.colors.gray[50],
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text.primary,
    marginBottom: 12,
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  label: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    width: 120,
  },
  value: {
    fontSize: 14,
    color: theme.colors.text.primary,
    fontFamily: 'monospace',
    flex: 1,
  },
  input: {
    borderWidth: 1,
    borderColor: theme.colors.gray[300],
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 14,
    fontFamily: 'monospace',
    backgroundColor: 'white',
    marginBottom: 16,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  testButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.primary[500],
    paddingVertical: 12,
    borderRadius: 8,
  },
  testButtonText: {
    color: 'white',
    fontWeight: '600',
    marginLeft: 8,
  },
  result: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
  },
  resultSuccess: {
    backgroundColor: theme.colors.success[50],
  },
  resultError: {
    backgroundColor: theme.colors.error[50],
  },
  resultText: {
    marginLeft: 12,
    flex: 1,
    fontSize: 14,
  },
  mapContainer: {
    height: 300,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: theme.colors.gray[100],
  },
  webview: {
    flex: 1,
  },
  fixButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: 'white',
    borderRadius: 8,
    marginBottom: 8,
  },
  fixButtonText: {
    marginLeft: 12,
    fontSize: 14,
    color: theme.colors.primary[500],
    fontWeight: '500',
  },
  stepText: {
    fontSize: 14,
    color: theme.colors.text.primary,
    marginBottom: 8,
    paddingLeft: 16,
  },
});

export default MapsDebugFix;
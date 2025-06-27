// components/StoreMapsDebugger.jsx - Diagnostic component for store selection and maps issues
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import config from '../config';
import { useAuth } from '../contexts/AuthContext';
import LocationService from '../services/LocationService';
import theme from '../constants/theme';

const StoreMapsDebugger = ({ visible, onClose }) => {
  const { token } = useAuth();
  const [diagnostics, setDiagnostics] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      runDiagnostics();
    }
  }, [visible]);

  const runDiagnostics = async () => {
    setLoading(true);
    const results = {
      timestamp: new Date().toISOString(),
      config: {},
      api: {},
      location: {},
      maps: {},
      recommendations: []
    };

    // 1. Check Configuration
    console.log('🔍 Running diagnostics...');
    
    try {
      results.config = {
        baseUrl: config.BASE_URL,
        apiUrl: config.API_URL,
        googleMapsApiKey: config.GOOGLE_MAPS_API_KEY ? 
          config.GOOGLE_MAPS_API_KEY.substring(0, 10) + '...' : 'NOT_SET',
        googleMapsKeyStatus: getApiKeyStatus(config.GOOGLE_MAPS_API_KEY),
        envVar: process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY ? 
          process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY.substring(0, 10) + '...' : 'NOT_SET',
        mapsEnabled: process.env.EXPO_PUBLIC_ENABLE_MAPS === 'true',
        configMode: 'ngrok', // from your config
      };
    } catch (error) {
      results.config.error = error.message;
    }

    // 2. Test API Endpoints
    try {
      // Test base connection
      const baseResponse = await fetch(config.BASE_URL, {
        method: 'GET',
        timeout: 5000
      });
      results.api.baseConnection = {
        success: baseResponse.ok,
        status: baseResponse.status,
        url: config.BASE_URL
      };

      // Test stores endpoint
      const storesResponse = await fetch(`${config.API_URL}/stores/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Token ${token}` }),
        },
        timeout: 10000
      });
      
      results.api.storesEndpoint = {
        success: storesResponse.ok,
        status: storesResponse.status,
        statusText: storesResponse.statusText,
        url: `${config.API_URL}/stores/`
      };

      if (storesResponse.ok) {
        const storesData = await storesResponse.json();
        results.api.storesData = {
          count: Array.isArray(storesData) ? storesData.length : (storesData.results?.length || 0),
          hasResults: !!(storesData.results || Array.isArray(storesData)),
          sampleStore: storesData.results?.[0] || storesData[0]
        };
      }

    } catch (error) {
      results.api.error = error.message;
      results.api.networkIssue = true;
    }

    // 3. Test Location Services
    try {
      const location = await LocationService.getLocationSafely();
      results.location = {
        available: !!location,
        latitude: location?.latitude,
        longitude: location?.longitude,
        accuracy: location?.accuracy
      };
    } catch (error) {
      results.location = {
        available: false,
        error: error.message
      };
    }

    // 4. Test Google Maps API
    results.maps = {
      apiKeyConfigured: !!config.GOOGLE_MAPS_API_KEY && 
                       config.GOOGLE_MAPS_API_KEY !== 'YOUR_API_KEY_HERE' && 
                       config.GOOGLE_MAPS_API_KEY !== 'MY_KEY',
      apiKeyLength: config.GOOGLE_MAPS_API_KEY?.length || 0,
      envVarSet: !!process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY,
      mapsEnabled: process.env.EXPO_PUBLIC_ENABLE_MAPS === 'true'
    };

    // 5. Generate Recommendations
    results.recommendations = generateRecommendations(results);

    setDiagnostics(results);
    setLoading(false);
  };

  const getApiKeyStatus = (apiKey) => {
    if (!apiKey) return 'MISSING';
    if (apiKey === 'YOUR_API_KEY_HERE' || apiKey === 'MY_KEY') return 'PLACEHOLDER';
    if (apiKey.length < 30) return 'INVALID_LENGTH';
    if (apiKey.startsWith('AIza')) return 'VALID_FORMAT';
    return 'UNKNOWN_FORMAT';
  };

  const generateRecommendations = (results) => {
    const recommendations = [];

    // API Issues
    if (!results.api.baseConnection?.success) {
      recommendations.push({
        type: 'error',
        title: 'Backend Server Not Reachable',
        description: 'Cannot connect to Django backend',
        solutions: [
          'Check if Django server is running: python manage.py runserver 0.0.0.0:8000',
          'Verify ngrok is running: ngrok http 8000',
          'Update NGROK_URL in config/index.js with the new ngrok URL'
        ]
      });
    }

    if (!results.api.storesEndpoint?.success) {
      recommendations.push({
        type: 'error',
        title: 'Stores API Not Working',
        description: 'This is causing the "Store selection error"',
        solutions: [
          'Check Django URL patterns in api/urls.py',
          'Verify StoreViewSet is properly configured',
          'Check Django logs for API errors',
          'Test the endpoint directly: ' + `${config.API_URL}/stores/`
        ]
      });
    }

    // Maps Issues
    if (!results.maps.apiKeyConfigured) {
      recommendations.push({
        type: 'error',
        title: 'Google Maps API Key Not Configured',
        description: 'Maps will not work without a valid API key',
        solutions: [
          'Get a Google Maps API key from Google Cloud Console',
          'Add it to your .env file: EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=your_key_here',
          'Enable Maps JavaScript API in Google Cloud Console',
          'Make sure billing is enabled for your Google Cloud project'
        ]
      });
    }

    if (results.maps.apiKeyConfigured && results.maps.apiKeyLength < 39) {
      recommendations.push({
        type: 'warning',
        title: 'Google Maps API Key May Be Invalid',
        description: 'API key seems too short',
        solutions: [
          'Verify the complete API key was copied',
          'Check for any trailing spaces or characters',
          'Test the key directly in Google Maps API'
        ]
      });
    }

    // Location Issues
    if (!results.location.available) {
      recommendations.push({
        type: 'warning',
        title: 'Location Services Not Available',
        description: 'Store distance sorting will not work',
        solutions: [
          'Enable location permissions for the app',
          'Check device location settings',
          'Test on a physical device (simulator may not have location)'
        ]
      });
    }

    // Success cases
    if (results.api.storesEndpoint?.success && results.maps.apiKeyConfigured) {
      recommendations.push({
        type: 'success',
        title: 'Core Systems Working',
        description: 'Both store API and Maps should be functional',
        solutions: ['All main systems appear to be working correctly!']
      });
    }

    return recommendations;
  };

  const getStatusIcon = (success) => {
    return success ? 
      <Ionicons name="checkmark-circle" size={20} color={theme.colors.success[500]} /> :
      <Ionicons name="close-circle" size={20} color={theme.colors.error[500]} />;
  };

  const getRecommendationIcon = (type) => {
    switch (type) {
      case 'error': return <Ionicons name="alert-circle" size={24} color={theme.colors.error[500]} />;
      case 'warning': return <Ionicons name="warning" size={24} color={theme.colors.warning[500]} />;
      case 'success': return <Ionicons name="checkmark-circle" size={24} color={theme.colors.success[500]} />;
      default: return <Ionicons name="information-circle" size={24} color={theme.colors.info[500]} />;
    }
  };

  if (!visible) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>System Diagnostics</Text>
        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
          <Ionicons name="close" size={24} color={theme.colors.text.primary} />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.colors.primary[500]} />
            <Text style={styles.loadingText}>Running diagnostics...</Text>
          </View>
        ) : diagnostics ? (
          <>
            {/* Configuration Section */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Configuration</Text>
              <View style={styles.checkItem}>
                <Text style={styles.checkLabel}>Base URL:</Text>
                <Text style={styles.checkValue}>{diagnostics.config.baseUrl}</Text>
              </View>
              <View style={styles.checkItem}>
                <Text style={styles.checkLabel}>API URL:</Text>
                <Text style={styles.checkValue}>{diagnostics.config.apiUrl}</Text>
              </View>
              <View style={styles.checkItem}>
                <Text style={styles.checkLabel}>Maps API Key:</Text>
                <Text style={styles.checkValue}>{diagnostics.config.googleMapsApiKey}</Text>
                {getStatusIcon(diagnostics.maps.apiKeyConfigured)}
              </View>
              <View style={styles.checkItem}>
                <Text style={styles.checkLabel}>Maps Enabled:</Text>
                <Text style={styles.checkValue}>{diagnostics.config.mapsEnabled ? 'Yes' : 'No'}</Text>
                {getStatusIcon(diagnostics.config.mapsEnabled)}
              </View>
            </View>

            {/* API Section */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>API Connectivity</Text>
              <View style={styles.checkItem}>
                <Text style={styles.checkLabel}>Backend Connection:</Text>
                <Text style={styles.checkValue}>
                  {diagnostics.api.baseConnection?.success ? 'Connected' : 'Failed'}
                </Text>
                {getStatusIcon(diagnostics.api.baseConnection?.success)}
              </View>
              <View style={styles.checkItem}>
                <Text style={styles.checkLabel}>Stores Endpoint:</Text>
                <Text style={styles.checkValue}>
                  {diagnostics.api.storesEndpoint?.success ? 'Working' : 'Failed'}
                </Text>
                {getStatusIcon(diagnostics.api.storesEndpoint?.success)}
              </View>
              {diagnostics.api.storesData && (
                <View style={styles.checkItem}>
                  <Text style={styles.checkLabel}>Stores Available:</Text>
                  <Text style={styles.checkValue}>{diagnostics.api.storesData.count} stores</Text>
                  {getStatusIcon(diagnostics.api.storesData.count > 0)}
                </View>
              )}
            </View>

            {/* Location Section */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Location Services</Text>
              <View style={styles.checkItem}>
                <Text style={styles.checkLabel}>Location Available:</Text>
                <Text style={styles.checkValue}>
                  {diagnostics.location.available ? 'Yes' : 'No'}
                </Text>
                {getStatusIcon(diagnostics.location.available)}
              </View>
              {diagnostics.location.available && (
                <>
                  <View style={styles.checkItem}>
                    <Text style={styles.checkLabel}>Coordinates:</Text>
                    <Text style={styles.checkValue}>
                      {diagnostics.location.latitude?.toFixed(4)}, {diagnostics.location.longitude?.toFixed(4)}
                    </Text>
                  </View>
                  <View style={styles.checkItem}>
                    <Text style={styles.checkLabel}>Accuracy:</Text>
                    <Text style={styles.checkValue}>{diagnostics.location.accuracy?.toFixed(0)}m</Text>
                  </View>
                </>
              )}
            </View>

            {/* Recommendations */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Recommendations</Text>
              {diagnostics.recommendations.map((rec, index) => (
                <View key={index} style={[styles.recommendation, styles[`recommendation${rec.type.charAt(0).toUpperCase() + rec.type.slice(1)}`]]}>
                  <View style={styles.recommendationHeader}>
                    {getRecommendationIcon(rec.type)}
                    <Text style={styles.recommendationTitle}>{rec.title}</Text>
                  </View>
                  <Text style={styles.recommendationDescription}>{rec.description}</Text>
                  {rec.solutions.map((solution, sIndex) => (
                    <Text key={sIndex} style={styles.solution}>• {solution}</Text>
                  ))}
                </View>
              ))}
            </View>

            {/* Refresh Button */}
            <TouchableOpacity style={styles.refreshButton} onPress={runDiagnostics}>
              <Ionicons name="refresh" size={20} color="white" />
              <Text style={styles.refreshButtonText}>Run Again</Text>
            </TouchableOpacity>
          </>
        ) : null}
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: theme.colors.text.secondary,
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
  checkItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    paddingVertical: 4,
  },
  checkLabel: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    width: 120,
  },
  checkValue: {
    fontSize: 14,
    color: theme.colors.text.primary,
    flex: 1,
    fontFamily: 'monospace',
  },
  recommendation: {
    marginBottom: 16,
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 4,
  },
  recommendationError: {
    backgroundColor: theme.colors.error[50],
    borderLeftColor: theme.colors.error[500],
  },
  recommendationWarning: {
    backgroundColor: theme.colors.warning[50],
    borderLeftColor: theme.colors.warning[500],
  },
  recommendationSuccess: {
    backgroundColor: theme.colors.success[50],
    borderLeftColor: theme.colors.success[500],
  },
  recommendationHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  recommendationTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text.primary,
    marginLeft: 8,
  },
  recommendationDescription: {
    fontSize: 14,
    color: theme.colors.text.secondary,
    marginBottom: 8,
  },
  solution: {
    fontSize: 13,
    color: theme.colors.text.primary,
    marginBottom: 4,
    paddingLeft: 8,
  },
  refreshButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.primary[500],
    paddingVertical: 16,
    borderRadius: 8,
    marginTop: 16,
    marginBottom: 32,
  },
  refreshButtonText: {
    color: 'white',
    fontWeight: '600',
    marginLeft: 8,
  },
});

export default StoreMapsDebugger;
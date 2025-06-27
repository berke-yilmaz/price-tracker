// config/index.js - FINAL version using Metro config and a stable path
import { Platform } from 'react-native';

// ======================================================================
// ⚠️ SINGLE SOURCE OF TRUTH ⚠️
// This file reads from `shared_config.json` in the Django project root.
// The `metro.config.js` file has been configured to allow this.
//
// YOU ONLY NEED TO EDIT `shared_config.json`.
// ======================================================================

// This path is now valid because of the metro.config.js `watchFolders` setting.
import sharedConfig from '../../../shared_config.json'; 

const { NGROK_URL, LOCAL_IP, CONFIG_MODE = 'ngrok' } = sharedConfig;

const getBaseUrl = () => {
  if (CONFIG_MODE === 'ngrok') {
    if (!NGROK_URL || NGROK_URL.includes("your-new-ngrok-url")) {
      console.error("CONFIG FATAL ERROR: NGROK_URL is not set correctly in your main shared_config.json!");
      return 'http://error.config.not.set';
    }
    return NGROK_URL;
  }
  // Keep other modes for flexibility
  if (CONFIG_MODE === 'local') {
    return `http://${LOCAL_IP}:8000`;
  }
  if (CONFIG_MODE === 'production') {
    return 'https://your.production.domain.com';
  }
  return NGROK_URL; // Fallback
};

const BASE_URL = getBaseUrl();

const config = {
  // Core URLs
  BASE_URL: BASE_URL,
  API_URL: `${BASE_URL}/api`,
  
  // App settings
  TIMEOUT: 15000,
  
  // Google Maps API Key from environment variables
  GOOGLE_MAPS_API_KEY: process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY || null,
};

// Debug logging to confirm the config is loaded correctly
if (__DEV__) {
  console.log('🔧 Config loaded from SINGLE SOURCE OF TRUTH:');
  console.log(`   - MODE: ${CONFIG_MODE}`);
  console.log(`   - BASE_URL: ${config.BASE_URL}`);
  console.log(`   - API_URL: ${config.API_URL}`);
  console.log(`   - Maps Key Loaded: ${!!config.GOOGLE_MAPS_API_KEY}`);
}

export default config;
// services/LocationService.js - Fixed with better error handling
import * as Location from 'expo-location';

class LocationService {
  static async getCurrentLocation() {
    try {
      // Check if location services are enabled
      const isEnabled = await Location.hasServicesEnabledAsync();
      if (!isEnabled) {
        throw new Error('Location services are disabled. Please enable location in your device settings.');
      }

      // Request permission
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        throw new Error('Location permission denied. Please grant location access in app settings.');
      }

      // Get current position with fallback options
      try {
        // Try high accuracy first
        const location = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
          timeout: 10000,
          maximumAge: 60000, // Accept cached location up to 1 minute old
        });

        return {
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          accuracy: location.coords.accuracy,
        };
      } catch (highAccuracyError) {
        console.warn('High accuracy location failed, trying balanced:', highAccuracyError);
        
        // Fallback to balanced accuracy
        const location = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
          timeout: 15000,
          maximumAge: 300000, // Accept cached location up to 5 minutes old
        });

        return {
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          accuracy: location.coords.accuracy,
        };
      }
    } catch (error) {
      console.error('Location service error:', error);
      
      // Provide user-friendly error messages
      if (error.message.includes('Location request failed')) {
        throw new Error('Unable to get location. Please check your device GPS settings and try again.');
      } else if (error.message.includes('permission')) {
        throw new Error('Location permission required. Please enable location access in your device settings.');
      } else {
        throw new Error('Location service unavailable. Using app without location features.');
      }
    }
  }

  static async reverseGeocode(latitude, longitude) {
    try {
      const result = await Location.reverseGeocodeAsync({
        latitude,
        longitude,
      });

      if (result.length > 0) {
        const address = result[0];
        return {
          street: address.street,
          city: address.city,
          district: address.district,
          region: address.region,
          country: address.country,
          postalCode: address.postalCode,
          formattedAddress: this.formatAddress(address),
        };
      }
      return null;
    } catch (error) {
      console.error('Reverse geocoding error:', error);
      return null;
    }
  }

  static formatAddress(address) {
    const parts = [
      address.street,
      address.district,
      address.city,
      address.region,
    ].filter(Boolean);
    
    return parts.join(', ');
  }

  static calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Earth's radius in kilometers
    const dLat = this.toRadians(lat2 - lat1);
    const dLon = this.toRadians(lon2 - lon1);
    
    const a = 
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRadians(lat1)) * 
      Math.cos(this.toRadians(lat2)) * 
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;
    
    return distance; // Returns distance in kilometers
  }

  static toRadians(degrees) {
    return degrees * (Math.PI / 180);
  }

  static async findNearbyStores(userLocation, stores, maxDistance = 10) {
    const nearbyStores = stores
      .map(store => {
        if (!store.latitude || !store.longitude) {
          return null;
        }

        const distance = this.calculateDistance(
          userLocation.latitude,
          userLocation.longitude,
          store.latitude,
          store.longitude
        );

        return {
          ...store,
          distance: distance,
          distanceText: distance < 1 
            ? `${Math.round(distance * 1000)}m`
            : `${distance.toFixed(1)}km`
        };
      })
      .filter(store => store && store.distance <= maxDistance)
      .sort((a, b) => a.distance - b.distance);

    return nearbyStores;
  }

  // Get location with graceful fallback
  static async getLocationSafely() {
    try {
      return await this.getCurrentLocation();
    } catch (error) {
      console.warn('Location access failed:', error.message);
      // Return null instead of throwing, let the app continue without location
      return null;
    }
  }

  // Check if location is available without requesting
  static async isLocationAvailable() {
    try {
      const isEnabled = await Location.hasServicesEnabledAsync();
      if (!isEnabled) return false;

      const { status } = await Location.getForegroundPermissionsAsync();
      return status === 'granted';
    } catch (error) {
      console.warn('Location availability check failed:', error);
      return false;
    }
  }
}

export default LocationService;
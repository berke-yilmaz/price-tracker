import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform, Alert } from 'react-native';
import config from '../config';

const AuthContext = createContext();

// Web storage polyfill
const storage = {
  getItem: async (key) => {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    return AsyncStorage.getItem(key);
  },
  setItem: async (key, value) => {
    if (Platform.OS === 'web') {
      localStorage.setItem(key, value);
    } else {
      await AsyncStorage.setItem(key, value);
    }
  },
  removeItem: async (key) => {
    if (Platform.OS === 'web') {
      localStorage.removeItem(key);
    } else {
      await AsyncStorage.removeItem(key);
    }
  },
  clear: async () => {
    if (Platform.OS === 'web') {
      localStorage.clear();
    } else {
      await AsyncStorage.clear();
    }
  }
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      console.log('🔍 [checkAuthState] Starting auth state check...');
      const storedToken = await storage.getItem('userToken');
      const storedUser = await storage.getItem('userData');

      console.log('🔍 [checkAuthState] Stored token:', !!storedToken);
      console.log('🔍 [checkAuthState] Stored user:', !!storedUser);

      if (!storedToken || !storedUser) {
        console.log('❌ [checkAuthState] Missing token or user data, clearing auth...');
        await clearAuth();
        return;
      }

      let userData;
      try {
        userData = JSON.parse(storedUser);
        console.log('✅ [checkAuthState] Parsed user data:', userData.username);
      } catch (parseError) {
        console.error('❌ [checkAuthState] Failed to parse user data:', parseError);
        await clearAuth();
        return;
      }

      // Verify token with server
      const isValid = await fetchUserProfile(storedToken);
      if (isValid) {
        console.log('✅ [checkAuthState] Token valid, setting auth state...');
        setToken(storedToken);
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        console.log('❌ [checkAuthState] Token invalid, clearing auth...');
        await clearAuth();
      }
    } catch (error) {
      console.error('❌ [checkAuthState] Error:', error.message);
      await clearAuth();
    } finally {
      console.log('🔍 [checkAuthState] Completed, setting loading to false');
      setLoading(false);
    }
  };

  const fetchUserProfile = async (authToken = null) => {
    try {
      const tokenToUse = authToken || token;
      if (!tokenToUse) {
        console.log('❌ [fetchUserProfile] No token available');
        return false;
      }

      console.log('📡 [fetchUserProfile] Fetching user profile with token...');
      const response = await fetch(`${config.API_URL}/auth/me/`, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${tokenToUse}`,
          'Content-Type': 'application/json',
        },
        timeout: 10000,
      });

      console.log('🔍 [fetchUserProfile] Response status:', response.status);

      if (response.ok) {
        const userData = await response.json();
        console.log('✅ [fetchUserProfile] Success:', userData.username);
        setUser(userData);
        await storage.setItem('userData', JSON.stringify(userData));
        return true;
      } else {
        console.error('❌ [fetchUserProfile] Failed:', response.status);
        return false;
      }
    } catch (error) {
      console.error('❌ [fetchUserProfile] Error:', error.message);
      return false;
    }
  };

  const login = async (credentials) => {
    try {
      setLoading(true);
      console.log('📡 [login] Attempting login with credentials:', credentials.username);

      // Clear any existing auth state before login attempt
      await clearAuth();

      const response = await fetch(`${config.API_URL}/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      console.log('🔍 [login] Response status:', response.status);

      let responseData;
      try {
        responseData = await response.json();
        console.log('📄 [login] Response data:', responseData);
      } catch (parseError) {
        console.error('❌ [login] JSON parse error:', parseError);
        return { success: false, error: 'Invalid server response' };
      }

      if (response.ok && responseData.token && responseData.username) {
        console.log('✅ [login] Success, processing login...');
        return await handleLoginSuccess(responseData);
      } else {
        console.log('❌ [login] Failed, clearing auth...');
        await clearAuth();
        let errorMessage = 'Login failed';

        if (responseData.non_field_errors) {
          errorMessage = responseData.non_field_errors[0];
        } else if (responseData.detail) {
          errorMessage = responseData.detail;
        } else if (responseData.error) {
          errorMessage = responseData.error;
        }

        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error('❌ [login] Network error:', error.message);
      await clearAuth();
      return { success: false, error: 'Network error. Please check your connection.' };
    } finally {
      console.log('🔍 [login] Completed, setting loading to false');
      setLoading(false);
    }
  };

  const handleLoginSuccess = async (data) => {
    try {
      console.log('✅ [handleLoginSuccess] Processing:', data);
      const { token: authToken, ...userData } = data;

      // CRITICAL: Wait for storage operations to complete
      await storage.setItem('userToken', authToken);
      await storage.setItem('userData', JSON.stringify(userData));

      // Update state after successful storage - use setTimeout to ensure state updates are processed
      setTimeout(() => {
        setToken(authToken);
        setUser(userData);
        setIsAuthenticated(true);
        
        console.log('✅ [handleLoginSuccess] Auth state updated:', {
          username: userData.username,
          token: authToken.slice(0, 10) + '...',
          isAuthenticated: true
        });
      }, 100);

      return { success: true };
    } catch (error) {
      console.error('❌ [handleLoginSuccess] Error:', error.message);
      await clearAuth();
      return { success: false, error: 'Login process could not be completed' };
    }
  };

  const register = async (userData) => {
    try {
      setLoading(true);
      console.log('📡 [register] Attempting registration...');

      const response = await fetch(`${config.API_URL}/auth/register/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      console.log('🔍 [register] Response status:', response.status);

      let responseData;
      try {
        responseData = await response.json();
        console.log('📄 [register] Response data:', responseData);
      } catch (parseError) {
        console.error('❌ [register] JSON parse error:', parseError);
        return { success: false, error: 'Invalid server response' };
      }

      if (response.ok && responseData.token && responseData.user) {
        console.log('✅ [register] Success, processing...');
        const { token: authToken, user: newUser } = responseData;

        // CRITICAL: Wait for storage operations to complete
        await storage.setItem('userToken', authToken);
        await storage.setItem('userData', JSON.stringify(newUser));

        // Update state after successful storage
        setToken(authToken);
        setUser(newUser);
        setIsAuthenticated(true);

        console.log('✅ [register] Auth state updated:', {
          username: newUser.username,
          token: authToken.slice(0, 10) + '...',
          isAuthenticated: true
        });
        return { success: true };
      } else {
        console.log('❌ [register] Failed, clearing auth...');
        await clearAuth();
        let errorMessage = 'Registration failed';

        if (responseData.username) {
          errorMessage = `Username: ${responseData.username[0]}`;
        } else if (responseData.email) {
          errorMessage = `Email: ${responseData.email[0]}`;
        } else if (responseData.password) {
          errorMessage = `Password: ${responseData.password[0]}`;
        } else if (responseData.non_field_errors) {
          errorMessage = responseData.non_field_errors[0];
        } else if (responseData.detail) {
          errorMessage = responseData.detail;
        }

        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error('❌ [register] Network error:', error.message);
      await clearAuth();
      return { success: false, error: 'Network error. Please check your connection.' };
    } finally {
      console.log('🔍 [register] Completed, setting loading to false');
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      console.log('📡 [logout] Logging out...');

      if (token) {
        try {
          await fetch(`${config.API_URL}/auth/logout/`, {
            method: 'POST',
            headers: {
              'Authorization': `Token ${token}`,
              'Content-Type': 'application/json',
            },
          });
        } catch (error) {
          console.warn('⚠️ [logout] API call failed:', error.message);
        }
      }

      await clearAuth();
      console.log('✅ [logout] Success');
      return { success: true };
    } catch (error) {
      console.error('❌ [logout] Error:', error.message);
      await clearAuth();
      return { success: true };
    } finally {
      console.log('🔍 [logout] Completed, setting loading to false');
      setLoading(false);
    }
  };

  const clearAuth = async () => {
    try {
      console.log('🧹 [clearAuth] Clearing auth state...');
      await storage.clear();
      setToken(null);
      setUser(null);
      setIsAuthenticated(false);
      console.log('✅ [clearAuth] Auth state cleared');
    } catch (error) {
      console.error('❌ [clearAuth] Error:', error.message);
      // Force state reset even if storage fails
      setToken(null);
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const updateProfile = async (profileData) => {
    try {
      console.log('📡 [updateProfile] Updating profile...');

      const response = await fetch(`${config.API_URL}/auth/me/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData),
      });

      console.log('🔍 [updateProfile] Response status:', response.status);

      if (response.ok) {
        const updatedUser = await response.json();
        console.log('✅ [updateProfile] Success:', updatedUser.username);

        setUser(updatedUser);
        await storage.setItem('userData', JSON.stringify(updatedUser));
        return { success: true };
      } else {
        const errorData = await response.json();
        console.error('❌ [updateProfile] Failed:', errorData);
        return { success: false, error: errorData.detail || 'Profile could not be updated' };
      }
    } catch (error) {
      console.error('❌ [updateProfile] Error:', error.message);
      return { success: false, error: 'Network error. Please check your connection.' };
    }
  };

  const changePassword = async (passwordData) => {
    try {
      console.log('📡 [changePassword] Changing password...');

      const response = await fetch(`${config.API_URL}/auth/change-password/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(passwordData),
      });

      console.log('🔍 [changePassword] Response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('✅ [changePassword] Success');

        if (data.token) {
          await storage.setItem('userToken', data.token);
          setToken(data.token);
        }

        return { success: true, message: data.detail || 'Password changed successfully' };
      } else {
        const errorData = await response.json();
        console.error('❌ [changePassword] Failed:', errorData);
        return { 
          success: false, 
          error: errorData.detail || errorData.old_password?.[0] || 'Password change failed' 
        };
      }
    } catch (error) {
      console.error('❌ [changePassword] Error:', error.message);
      return { success: false, error: 'Network error. Please check your connection.' };
    }
  };

  const refreshAuth = async () => {
    if (token) {
      console.log('🔄 [refreshAuth] Refreshing auth...');
      return await fetchUserProfile();
    }
    console.log('❌ [refreshAuth] No token available');
    return false;
  };

  const createMockUser = () => {
    console.log('🔧 [createMockUser] Creating mock user...');
    const mockUser = {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
    };
    setUser(mockUser);
    setIsAuthenticated(true);
    setLoading(false);
  };

  const contextValue = React.useMemo(() => ({
    user,
    token,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    refreshAuth,
    clearAuth,
    createMockUser,
  }), [user, token, loading, isAuthenticated]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
// app/login.jsx - Clean English version
/*import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  Keyboard,
  TouchableWithoutFeedback,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';

export default function LoginScreen() {
  const router = useRouter();
  const { login, loading, isAuthenticated } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const passwordInputRef = useRef(null);

  // Navigate when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/(tabs)/');
    }
  }, [isAuthenticated, router]);

  const parseError = (error) => {
    if (typeof error === 'string') return error;
    if (error?.non_field_errors) return error.non_field_errors[0];
    if (error?.username) return `Username: ${error.username[0]}`;
    if (error?.password) return `Password: ${error.password[0]}`;
    
    // Convert Turkish error messages to English
    if (error === 'Geçersiz kullanıcı adı veya şifre') {
      return 'Invalid username or password';
    }
    
    return 'Login failed';
  };

  const handleLogin = async () => {
    setErrorMessage('');
    const trimmedUsername = username.trim();
    const trimmedPassword = password.trim();

    if (!trimmedUsername || !trimmedPassword) {
      setErrorMessage('Please enter username and password');
      return;
    }

    try {
      const result = await login({ username: trimmedUsername, password: trimmedPassword });
      
      if (result.success) {
        setUsername('');
        setPassword('');
        
        // Force navigation after successful login
        setTimeout(() => {
          router.replace('/(tabs)/');
        }, 500);
        
      } else {
        const errorMsg = parseError(result.error);
        setErrorMessage(errorMsg);
      }
    } catch (error) {
      setErrorMessage('An unexpected error occurred');
    }
  };

  const dismissKeyboard = () => {
    Keyboard.dismiss();
  };

  return (
    <TouchableWithoutFeedback onPress={dismissKeyboard}>
      <SafeAreaView style={styles.container}>
        <View style={styles.form}>
          <Text style={styles.title}>Price Tracker</Text>
          <Text style={styles.subtitle}>Sign in to your account</Text>

          {errorMessage ? (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{errorMessage}</Text>
            </View>
          ) : null}

          <TextInput
            style={styles.input}
            placeholder="Username"
            value={username}
            onChangeText={(text) => {
              setUsername(text);
              setErrorMessage('');
            }}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="next"
            onSubmitEditing={() => passwordInputRef.current?.focus()}
            blurOnSubmit={false}
          />

          <TextInput
            ref={passwordInputRef}
            style={styles.input}
            placeholder="Password"
            secureTextEntry
            value={password}
            onChangeText={(text) => {
              setPassword(text);
              setErrorMessage('');
            }}
            returnKeyType="done"
            onSubmitEditing={handleLogin}
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.disabledButton]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.buttonText}>Sign In</Text>
            )}
          </TouchableOpacity>

          <View style={styles.registerContainer}>
            <Text style={styles.registerText}>Don't have an account?</Text>
            <TouchableOpacity onPress={() => router.push('/register')}>
              <Text style={styles.registerLink}>Sign Up</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  form: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
    color: '#333',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 30,
    color: '#666',
  },
  errorContainer: {
    backgroundColor: '#ffebee',
    borderRadius: 8,
    padding: 12,
    marginBottom: 15,
    borderLeftWidth: 4,
    borderLeftColor: '#f44336',
  },
  errorText: {
    color: '#c62828',
    fontSize: 14,
    textAlign: 'center',
  },
  input: {
    backgroundColor: 'white',
    paddingVertical: 12,
    paddingHorizontal: 15,
    borderRadius: 8,
    fontSize: 16,
    marginBottom: 15,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  button: {
    backgroundColor: '#007AFF',
    paddingVertical: 15,
    borderRadius: 10,
    marginTop: 10,
  },
  disabledButton: {
    opacity: 0.7,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  registerContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
  },
  registerText: {
    color: '#666',
    marginRight: 5,
  },
  registerLink: {
    color: '#007AFF',
    fontWeight: '600',
  },
});*/

// app/login.jsx - Clean English version
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  Keyboard,
  TouchableWithoutFeedback,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import theme from '../constants/theme';

export default function LoginScreen() {
  const router = useRouter();
  const { login, loading, isAuthenticated } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const passwordInputRef = useRef(null);

  // Navigate when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/(tabs)/');
    }
  }, [isAuthenticated, router]);

  const parseError = (error) => {
    if (typeof error === 'string') return error;
    if (error?.non_field_errors) return error.non_field_errors[0];
    if (error?.username) return `Username: ${error.username[0]}`;
    if (error?.password) return `Password: ${error.password[0]}`;
    
    // Convert Turkish error messages to English
    if (error === 'Geçersiz kullanıcı adı veya şifre') {
      return 'Invalid username or password';
    }
    
    return 'Login failed. Please check your credentials.';
  };

  const handleLogin = async () => {
    setErrorMessage('');
    const trimmedUsername = username.trim();
    const trimmedPassword = password.trim();

    if (!trimmedUsername || !trimmedPassword) {
      setErrorMessage('Please enter both username and password');
      return;
    }

    try {
      const result = await login({ username: trimmedUsername, password: trimmedPassword });
      
      if (result.success) {
        setUsername('');
        setPassword('');
        router.replace('/(tabs)/');
      } else {
        const errorMsg = parseError(result.error);
        setErrorMessage(errorMsg);
      }
    } catch (error) {
      setErrorMessage('An unexpected error occurred. Please try again.');
    }
  };

  const dismissKeyboard = () => {
    Keyboard.dismiss();
  };

  return (
    <TouchableWithoutFeedback onPress={dismissKeyboard} style={{flex: 1}}>
      <SafeAreaView style={styles.container}>
        <View style={styles.form}>
          <Text style={styles.title}>Price Tracker</Text>
          <Text style={styles.subtitle}>Sign in to your account</Text>

          {errorMessage ? (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{errorMessage}</Text>
            </View>
          ) : null}

          <TextInput
            style={styles.input}
            placeholder="Username"
            placeholderTextColor={theme.colors.gray[400]}
            value={username}
            onChangeText={(text) => {
              setUsername(text);
              setErrorMessage('');
            }}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="next"
            onSubmitEditing={() => passwordInputRef.current?.focus()}
            blurOnSubmit={false}
          />

          <TextInput
            ref={passwordInputRef}
            style={styles.input}
            placeholder="Password"
            placeholderTextColor={theme.colors.gray[400]}
            secureTextEntry
            value={password}
            onChangeText={(text) => {
              setPassword(text);
              setErrorMessage('');
            }}
            returnKeyType="done"
            onSubmitEditing={handleLogin}
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.disabledButton]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={theme.colors.text.inverse} />
            ) : (
              <Text style={styles.buttonText}>Sign In</Text>
            )}
          </TouchableOpacity>

          <View style={styles.registerContainer}>
            <Text style={styles.registerText}>Don't have an account?</Text>
            <TouchableOpacity onPress={() => router.push('/register')}>
              <Text style={styles.registerLink}>Sign Up</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  form: {
    flex: 1,
    padding: theme.spacing.lg,
    justifyContent: 'center',
  },
  title: {
    fontSize: theme.typography.fontSize['3xl'],
    fontWeight: theme.typography.fontWeight.bold,
    textAlign: 'center',
    marginBottom: theme.spacing.sm,
    color: theme.colors.text.primary,
  },
  subtitle: {
    fontSize: theme.typography.fontSize.base,
    textAlign: 'center',
    marginBottom: theme.spacing.xl,
    color: theme.colors.text.secondary,
  },
  errorContainer: {
    backgroundColor: theme.colors.error[50],
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    borderLeftWidth: 4,
    borderLeftColor: theme.colors.error[500],
  },
  errorText: {
    color: theme.colors.error[700],
    fontSize: theme.typography.fontSize.sm,
    textAlign: 'center',
  },
  input: {
    backgroundColor: theme.colors.surface,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    fontSize: theme.typography.fontSize.base,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.gray[300],
    color: theme.colors.text.primary,
  },
  button: {
    backgroundColor: theme.colors.primary[500],
    paddingVertical: theme.spacing.lg,
    borderRadius: theme.borderRadius.lg,
    marginTop: theme.spacing.sm,
    alignItems: 'center',
  },
  disabledButton: {
    opacity: 0.7,
  },
  buttonText: {
    color: theme.colors.text.inverse,
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
  },
  registerContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: theme.spacing.xl,
  },
  registerText: {
    color: theme.colors.text.secondary,
    marginRight: theme.spacing.xs,
  },
  registerLink: {
    color: theme.colors.primary[500],
    fontWeight: theme.typography.fontWeight.semibold,
  },
});
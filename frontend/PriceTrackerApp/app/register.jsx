// app/register.jsx - Clean English version
/*import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  ScrollView,
  Keyboard,
  TouchableWithoutFeedback,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';

export default function RegisterScreen() {
  const router = useRouter();
  const { register, loading, isAuthenticated } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const emailInputRef = useRef(null);
  const firstNameInputRef = useRef(null);
  const lastNameInputRef = useRef(null);
  const passwordInputRef = useRef(null);
  const passwordConfirmInputRef = useRef(null);

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
    if (error?.email) return `Email: ${error.email[0]}`;
    if (error?.password) return `Password: ${error.password[0]}`;
    if (error?.password_confirm) return `Password Confirmation: ${error.password_confirm[0]}`;
    
    // Convert any Turkish messages to English
    if (error === 'Kayıt başarısız') {
      return 'Registration failed';
    }
    
    return 'Registration failed';
  };

  const handleRegister = async () => {
    setErrorMessage('');
    const trimmedUsername = username.trim();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    const trimmedPasswordConfirm = passwordConfirm.trim();
    const trimmedFirstName = firstName.trim();
    const trimmedLastName = lastName.trim();

    if (!trimmedUsername || !trimmedEmail || !trimmedPassword || !trimmedPasswordConfirm) {
      setErrorMessage('Please fill in all required fields');
      return;
    }

    if (trimmedPassword !== trimmedPasswordConfirm) {
      setErrorMessage('Passwords do not match');
      return;
    }

    if (trimmedPassword.length < 8) {
      setErrorMessage('Password must be at least 8 characters');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setErrorMessage('Please enter a valid email address');
      return;
    }

    try {
      const result = await register({
        username: trimmedUsername,
        email: trimmedEmail,
        password: trimmedPassword,
        password_confirm: trimmedPasswordConfirm,
        first_name: trimmedFirstName,
        last_name: trimmedLastName,
      });

      if (result.success) {
        setUsername('');
        setEmail('');
        setPassword('');
        setPasswordConfirm('');
        setFirstName('');
        setLastName('');
        
        // Force navigation after successful registration
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
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.form}>
            <Text style={styles.title}>Create Account</Text>
            <Text style={styles.subtitle}>Sign up to get started</Text>

            {errorMessage ? (
              <View style={styles.errorContainer}>
                <Text style={styles.errorText}>{errorMessage}</Text>
              </View>
            ) : null}

            <TextInput
              style={styles.input}
              placeholder="Username*"
              value={username}
              onChangeText={(text) => {
                setUsername(text);
                setErrorMessage('');
              }}
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
              onSubmitEditing={() => emailInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={emailInputRef}
              style={styles.input}
              placeholder="Email*"
              value={email}
              onChangeText={(text) => {
                setEmail(text);
                setErrorMessage('');
              }}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
              onSubmitEditing={() => firstNameInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={firstNameInputRef}
              style={styles.input}
              placeholder="First Name (optional)"
              value={firstName}
              onChangeText={setFirstName}
              returnKeyType="next"
              onSubmitEditing={() => lastNameInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={lastNameInputRef}
              style={styles.input}
              placeholder="Last Name (optional)"
              value={lastName}
              onChangeText={setLastName}
              returnKeyType="next"
              onSubmitEditing={() => passwordInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={passwordInputRef}
              style={styles.input}
              placeholder="Password (At least 8 characters)*"
              secureTextEntry
              value={password}
              onChangeText={(text) => {
                setPassword(text);
                setErrorMessage('');
              }}
              returnKeyType="next"
              onSubmitEditing={() => passwordConfirmInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={passwordConfirmInputRef}
              style={styles.input}
              placeholder="Confirm Password*"
              secureTextEntry
              value={passwordConfirm}
              onChangeText={(text) => {
                setPasswordConfirm(text);
                setErrorMessage('');
              }}
              returnKeyType="done"
              onSubmitEditing={handleRegister}
            />

            <TouchableOpacity
              style={[styles.button, loading && styles.disabledButton]}
              onPress={handleRegister}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.buttonText}>Sign Up</Text>
              )}
            </TouchableOpacity>

            <View style={styles.loginContainer}>
              <Text style={styles.loginText}>Already have an account?</Text>
              <TouchableOpacity onPress={() => router.push('/login')}>
                <Text style={styles.loginLink}>Sign In</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  form: {
    padding: 20,
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
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 20,
    marginBottom: 20,
  },
  loginText: {
    color: '#666',
    marginRight: 5,
  },
  loginLink: {
    color: '#007AFF',
    fontWeight: '600',
  },
});*/

// app/register.jsx - Clean English version
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  ActivityIndicator,
  ScrollView,
  Keyboard,
  TouchableWithoutFeedback,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import theme from '../constants/theme';

export default function RegisterScreen() {
  const router = useRouter();
  const { register, loading, isAuthenticated } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const emailInputRef = useRef(null);
  const firstNameInputRef = useRef(null);
  const lastNameInputRef = useRef(null);
  const passwordInputRef = useRef(null);
  const passwordConfirmInputRef = useRef(null);

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
    if (error?.email) return `Email: ${error.email[0]}`;
    if (error?.password) return `Password: ${error.password[0]}`;
    if (error?.password_confirm) return `Password Confirmation: ${error.password_confirm[0]}`;
    
    // Convert any Turkish messages to English
    if (error === 'Kayıt başarısız') {
      return 'Registration failed';
    }
    
    return 'Registration failed';
  };

  const handleRegister = async () => {
    setErrorMessage('');
    const trimmedUsername = username.trim();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    const trimmedPasswordConfirm = passwordConfirm.trim();
    const trimmedFirstName = firstName.trim();
    const trimmedLastName = lastName.trim();

    if (!trimmedUsername || !trimmedEmail || !trimmedPassword || !trimmedPasswordConfirm) {
      setErrorMessage('Please fill in all required fields');
      return;
    }

    if (trimmedPassword !== trimmedPasswordConfirm) {
      setErrorMessage('Passwords do not match');
      return;
    }

    if (trimmedPassword.length < 8) {
      setErrorMessage('Password must be at least 8 characters');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setErrorMessage('Please enter a valid email address');
      return;
    }

    try {
      const result = await register({
        username: trimmedUsername,
        email: trimmedEmail,
        password: trimmedPassword,
        password_confirm: trimmedPasswordConfirm,
        first_name: trimmedFirstName,
        last_name: trimmedLastName,
      });

      if (result.success) {
        router.replace('/(tabs)/');
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
    <TouchableWithoutFeedback onPress={dismissKeyboard} style={{flex: 1}}>
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.form}>
            <Text style={styles.title}>Create Account</Text>
            <Text style={styles.subtitle}>Sign up to get started</Text>

            {errorMessage ? (
              <View style={styles.errorContainer}>
                <Text style={styles.errorText}>{errorMessage}</Text>
              </View>
            ) : null}

            <TextInput
              style={styles.input}
              placeholder="Username*"
              placeholderTextColor={theme.colors.gray[400]}
              value={username}
              onChangeText={(text) => {
                setUsername(text);
                setErrorMessage('');
              }}
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
              onSubmitEditing={() => emailInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={emailInputRef}
              style={styles.input}
              placeholder="Email*"
              placeholderTextColor={theme.colors.gray[400]}
              value={email}
              onChangeText={(text) => {
                setEmail(text);
                setErrorMessage('');
              }}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
              onSubmitEditing={() => firstNameInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={firstNameInputRef}
              style={styles.input}
              placeholder="First Name (optional)"
              placeholderTextColor={theme.colors.gray[400]}
              value={firstName}
              onChangeText={setFirstName}
              returnKeyType="next"
              onSubmitEditing={() => lastNameInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={lastNameInputRef}
              style={styles.input}
              placeholder="Last Name (optional)"
              placeholderTextColor={theme.colors.gray[400]}
              value={lastName}
              onChangeText={setLastName}
              returnKeyType="next"
              onSubmitEditing={() => passwordInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={passwordInputRef}
              style={styles.input}
              placeholder="Password (At least 8 characters)*"
              placeholderTextColor={theme.colors.gray[400]}
              secureTextEntry
              value={password}
              onChangeText={(text) => {
                setPassword(text);
                setErrorMessage('');
              }}
              returnKeyType="next"
              onSubmitEditing={() => passwordConfirmInputRef.current?.focus()}
              blurOnSubmit={false}
            />

            <TextInput
              ref={passwordConfirmInputRef}
              style={styles.input}
              placeholder="Confirm Password*"
              placeholderTextColor={theme.colors.gray[400]}
              secureTextEntry
              value={passwordConfirm}
              onChangeText={(text) => {
                setPasswordConfirm(text);
                setErrorMessage('');
              }}
              returnKeyType="done"
              onSubmitEditing={handleRegister}
            />

            <TouchableOpacity
              style={[styles.button, loading && styles.disabledButton]}
              onPress={handleRegister}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color={theme.colors.text.inverse} />
              ) : (
                <Text style={styles.buttonText}>Sign Up</Text>
              )}
            </TouchableOpacity>

            <View style={styles.loginContainer}>
              <Text style={styles.loginText}>Already have an account?</Text>
              <TouchableOpacity onPress={() => router.push('/login')}>
                <Text style={styles.loginLink}>Sign In</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  form: {
    padding: theme.spacing.lg,
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
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: theme.spacing.xl,
    marginBottom: theme.spacing.lg,
  },
  loginText: {
    color: theme.colors.text.secondary,
    marginRight: theme.spacing.xs,
  },
  loginLink: {
    color: theme.colors.primary[500],
    fontWeight: theme.typography.fontWeight.semibold,
  },
});
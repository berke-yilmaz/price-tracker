// app/(tabs)/profile.jsx - Enhanced Profile Screen with consistent theme, top spacing, and adjusted padding for Account Actions
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import theme from '../../constants/theme'; // Import the theme

export default function ProfileScreen() {
  const { user, logout, updateProfile, changePassword, loading } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  
  // Profile form state
  const [profileForm, setProfileForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    username: '',
  });

  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    old_password: '',
    new_password: '',
    confirm_new_password: '',
  });

  // Loading states
  const [updating, setUpdating] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setProfileForm({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        username: user.username || '',
      });
    }
  }, [user]);

  const handleUpdateProfile = async () => {
    setUpdating(true);
    try {
      const result = await updateProfile({
        first_name: profileForm.first_name,
        last_name: profileForm.last_name,
        email: profileForm.email,
      });

      if (result.success) {
        setIsEditing(false);
        Alert.alert('Success', 'Your profile has been updated');
      } else {
        Alert.alert('Error', result.error || 'Profile could not be updated');
      }
    } catch (error) {
      Alert.alert('Error', 'An unexpected error occurred');
    } finally {
      setUpdating(false);
    }
  };

  const handleChangePassword = async () => {
    if (passwordForm.new_password !== passwordForm.confirm_new_password) {
      Alert.alert('Error', 'New passwords do not match');
      return;
    }

    if (passwordForm.new_password.length < 8) {
      Alert.alert('Error', 'New password must be at least 8 characters');
      return;
    }

    setChangingPassword(true);
    try {
      const result = await changePassword({
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password,
        confirm_new_password: passwordForm.confirm_new_password,
      });

      if (result.success) {
        setIsChangingPassword(false);
        setPasswordForm({
          old_password: '',
          new_password: '',
          confirm_new_password: '',
        });
        Alert.alert('Success', result.message || 'Your password has been changed successfully');
      } else {
        Alert.alert('Error', result.error || 'Password change failed');
      }
    } catch (error) {
      Alert.alert('Error', 'An unexpected error occurred');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Logout', 
          style: 'destructive',
          onPress: async () => {
            const result = await logout();
            if (!result.success) {
              Alert.alert('Error', 'An error occurred while logging out');
            }
          }
        },
      ]
    );
  };

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContainer}>
          <Ionicons name="person-circle-outline" size={theme.typography.fontSize['4xl']} color={theme.colors.gray[400]} />
          <Text style={styles.noUserTitle}>No User Information</Text>
          <Text style={styles.noUserText}>
            User information could not be loaded. Please try logging in again.
          </Text>
          
          {__DEV__ && ( // Keep debug info, but clean up
            <View style={styles.debugContainer}>
              <Text style={styles.debugTitle}>Debug Info:</Text>
              <Text style={styles.debugText}>User: {JSON.stringify(user)}</Text>
              <Text style={styles.debugText}>Auth Loading: {loading?.toString()}</Text>
              <Text style={styles.debugText}>Has Update Profile Func: {typeof updateProfile}</Text>
              <Text style={styles.debugText}>Has Change Password Func: {typeof changePassword}</Text>
            </View>
          )}
          
          <TouchableOpacity style={styles.retryButton} onPress={handleLogout}>
            <Text style={styles.retryButtonText}>Login Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.avatarContainer}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {user.first_name && user.last_name 
                  ? `${user.first_name[0]}${user.last_name[0]}` 
                  : user.username?.[0]?.toUpperCase() || 'U'}
              </Text>
            </View>
          </View>
          
          <Text style={styles.userName}>
            {user.first_name && user.last_name 
              ? `${user.first_name} ${user.last_name}`
              : user.username}
          </Text>
          <Text style={styles.userEmail}>{user.email}</Text>
        </View>

        {/* Profile Information */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Profile Information</Text>
            <TouchableOpacity
              onPress={() => setIsEditing(!isEditing)}
              style={styles.editButton}
            >
              <Ionicons 
                name={isEditing ? "close" : "pencil"} 
                size={theme.typography.fontSize.xl} // Adjust size
                color={theme.colors.primary[500]} // Use primary color
              />
            </TouchableOpacity>
          </View>

          {isEditing ? (
            <View style={styles.form}>
              <Text style={styles.label}>First Name</Text>
              <TextInput
                style={styles.input}
                value={profileForm.first_name}
                onChangeText={(text) => setProfileForm({...profileForm, first_name: text})}
                placeholder="Enter your first name"
                placeholderTextColor={theme.colors.gray[500]} // Themed placeholder
              />

              <Text style={styles.label}>Last Name</Text>
              <TextInput
                style={styles.input}
                value={profileForm.last_name}
                onChangeText={(text) => setProfileForm({...profileForm, last_name: text})}
                placeholder="Enter your last name"
                placeholderTextColor={theme.colors.gray[500]}
              />

              <Text style={styles.label}>Email</Text>
              <TextInput
                style={styles.input}
                value={profileForm.email}
                onChangeText={(text) => setProfileForm({...profileForm, email: text})}
                placeholder="Enter your email"
                keyboardType="email-address"
                autoCapitalize="none"
                placeholderTextColor={theme.colors.gray[500]}
              />

              <View style={styles.buttonRow}>
                <TouchableOpacity
                  style={[styles.button, styles.cancelButton]}
                  onPress={() => {
                    setIsEditing(false);
                    setProfileForm({
                      first_name: user.first_name || '',
                      last_name: user.last_name || '',
                      email: user.email || '',
                      username: user.username || '',
                    });
                  }}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.button, styles.saveButton, updating && styles.disabledButton]}
                  onPress={handleUpdateProfile}
                  disabled={updating}
                >
                  {updating ? (
                    <ActivityIndicator color={theme.colors.text.inverse} size="small" />
                  ) : (
                    <Text style={styles.saveButtonText}>Save</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <View style={styles.infoContainer}>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Username:</Text>
                <Text style={styles.infoValue}>{user.username}</Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>First Name:</Text>
                <Text style={styles.infoValue}>{user.first_name || 'Not specified'}</Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Last Name:</Text>
                <Text style={styles.infoValue}>{user.last_name || 'Not specified'}</Text>
              </View>

              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Email:</Text>
                <Text style={styles.infoValue}>{user.email}</Text>
              </View>
            </View>
          )}
        </View>

        {/* Password Change Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Change Password</Text>
            <TouchableOpacity
              onPress={() => setIsChangingPassword(!isChangingPassword)}
              style={styles.editButton}
            >
              <Ionicons 
                name={isChangingPassword ? "close" : "key"} 
                size={theme.typography.fontSize.xl} 
                color={theme.colors.primary[500]} 
              />
            </TouchableOpacity>
          </View>

          {isChangingPassword && (
            <View style={styles.form}>
              <Text style={styles.label}>Current Password</Text>
              <TextInput
                style={styles.input}
                value={passwordForm.old_password}
                onChangeText={(text) => setPasswordForm({...passwordForm, old_password: text})}
                placeholder="Enter your current password"
                secureTextEntry
                placeholderTextColor={theme.colors.gray[500]}
              />

              <Text style={styles.label}>New Password</Text>
              <TextInput
                style={styles.input}
                value={passwordForm.new_password}
                onChangeText={(text) => setPasswordForm({...passwordForm, new_password: text})}
                placeholder="Enter new password (at least 8 characters)"
                secureTextEntry
                placeholderTextColor={theme.colors.gray[500]}
              />

              <Text style={styles.label}>Confirm New Password</Text>
              <TextInput
                style={styles.input}
                value={passwordForm.confirm_new_password}
                onChangeText={(text) => setPasswordForm({...passwordForm, confirm_new_password: text})}
                placeholder="Confirm your new password"
                secureTextEntry
                placeholderTextColor={theme.colors.gray[500]}
              />

              <View style={styles.buttonRow}>
                <TouchableOpacity
                  style={[styles.button, styles.cancelButton]}
                  onPress={() => {
                    setIsChangingPassword(false);
                    setPasswordForm({
                      old_password: '',
                      new_password: '',
                      confirm_new_password: '',
                    });
                  }}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.button, styles.saveButton, changingPassword && styles.disabledButton]}
                  onPress={handleChangePassword}
                  disabled={changingPassword}
                >
                  {changingPassword ? (
                    <ActivityIndicator color={theme.colors.text.inverse} size="small" />
                  ) : (
                    <Text style={styles.saveButtonText}>Change</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          )}
        </View>

        {/* Account Actions */}
        <View style={styles.sectionAccountActions}>
          <Text style={styles.sectionTitle}>Account</Text>
          
          <TouchableOpacity style={styles.actionButton} onPress={handleLogout}>
            <Ionicons name="log-out-outline" size={theme.typography.fontSize.xl} color={theme.colors.error[500]} />
            <Text style={styles.logoutText}>Logout</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: theme.spacing['2xl'],
    backgroundColor: theme.colors.primary[50],
  },
  scrollView: {
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: theme.spacing.md,
    backgroundColor: theme.colors.primary[50],
  },
  header: {
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    paddingVertical: theme.spacing['2xl'],
    paddingHorizontal: theme.spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
    ...theme.shadows.sm,
  },
  avatarContainer: {
    marginBottom: theme.spacing.md,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: theme.borderRadius.full,
    backgroundColor: theme.colors.primary[500],
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: theme.typography.fontSize['3xl'],
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.inverse,
  },
  userName: {
    fontSize: theme.typography.fontSize['xl'],
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  userEmail: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
  },
  section: {
    backgroundColor: theme.colors.surface,
    marginTop: theme.spacing.md,
    marginHorizontal: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md, // Default padding for most sections
    ...theme.shadows.sm,
  },
  // New style for the Account Actions section with increased padding
  sectionAccountActions: {
    backgroundColor: theme.colors.surface,
    marginTop: theme.spacing.md,
    marginHorizontal: theme.spacing.md,
    borderRadius: theme.borderRadius.lg,
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.lg, // Increased vertical padding here (equivalent to 16px if theme.spacing.md is 8)
    marginBottom: theme.spacing.md, // Added margin to the bottom for separation
    ...theme.shadows.sm,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  sectionTitle: {
    fontSize: theme.typography.fontSize.lg,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
  },
  editButton: {
    padding: theme.spacing.xs,
  },
  form: {
    marginTop: theme.spacing.sm,
  },
  label: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
    marginTop: theme.spacing.sm,
  },
  input: {
    backgroundColor: theme.colors.gray[100],
    borderWidth: 1,
    borderColor: theme.colors.gray[300],
    borderRadius: theme.borderRadius.md,
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
  },
  buttonRow: {
    flexDirection: 'row',
    marginTop: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  button: {
    flex: 1,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.borderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
    ...theme.shadows.sm,
  },
  cancelButton: {
    backgroundColor: theme.colors.gray[200],
  },
  saveButton: {
    backgroundColor: theme.colors.primary[500],
  },
  disabledButton: {
    opacity: 0.6,
  },
  cancelButtonText: {
    color: theme.colors.text.secondary,
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
  },
  saveButtonText: {
    color: theme.colors.text.inverse,
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
  },
  infoContainer: {
    marginTop: theme.spacing.sm,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: theme.spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[100],
  },
  infoLabel: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    fontWeight: theme.typography.fontWeight.medium,
  },
  infoValue: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
    fontWeight: theme.typography.fontWeight.normal,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: theme.spacing.md,
    borderTopWidth: 1,
    borderTopColor: theme.colors.gray[100],
    marginTop: theme.spacing.md,
  },
  logoutText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.error[500],
    marginLeft: theme.spacing.md,
    fontWeight: theme.typography.fontWeight.medium,
  },
  noUserTitle: {
    fontSize: theme.typography.fontSize.xl,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.sm,
    textAlign: 'center',
  },
  noUserText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    marginBottom: theme.spacing.lg,
    paddingHorizontal: theme.spacing.md,
  },
  retryButton: {
    backgroundColor: theme.colors.primary[500],
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.lg,
    borderRadius: theme.borderRadius.md,
    marginTop: theme.spacing.md,
    ...theme.shadows.sm,
  },
  retryButtonText: {
    color: theme.colors.text.inverse,
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
  },
  debugContainer: {
    backgroundColor: theme.colors.gray[100],
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.md,
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.lg,
    borderWidth: 1,
    borderColor: theme.colors.gray[200],
    marginHorizontal: theme.spacing.md,
  },
  debugTitle: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.gray[700],
    marginBottom: theme.spacing.xs,
  },
  debugText: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.gray[600],
    marginBottom: theme.spacing.xs,
    fontFamily: 'monospace',
  },
});
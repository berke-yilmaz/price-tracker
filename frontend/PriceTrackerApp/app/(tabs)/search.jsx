// app/(tabs)/search.jsx - Updated with long press delete functionality
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  Alert,
  TouchableOpacity,
  Modal,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import ProductSearch from '../../components/ProductSearch';
import theme from '../../constants/theme';
import LocationService from '../../services/LocationService';
import config from '../../config';


export default function SearchScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [hasLocationAccess, setHasLocationAccess] = useState(true);
  const [showDeleteInfo, setShowDeleteInfo] = useState(false);
  const [deletionStats, setDeletionStats] = useState(null);

  useEffect(() => {
    checkAndWarnLocation();
    if (user) {
      fetchDeletionStats();
    }
  }, [user]);

  const checkAndWarnLocation = async () => {
    const isAvailable = await LocationService.isLocationAvailable();
    setHasLocationAccess(isAvailable);

    if (!isAvailable) {
      Alert.alert(
        "Location Services Off",
        "To find the nearest prices and stores, please enable location services for this app in your device settings.",
        [
          { text: "OK", onPress: () => console.log("User acknowledged location prompt") }
        ]
      );
    }
  };

  const fetchDeletionStats = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${config.API_URL}/products/deletion_stats/`, {
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const stats = await response.json();
        setDeletionStats(stats);
      }
    } catch (error) {
      console.error('Failed to fetch deletion stats:', error);
    }
  };

  const handleProductSelect = (product) => {
    // Navigate to the new price management screen, passing the product ID
    router.push({
      pathname: '/updatePrice', // We will create this new screen next
      params: { productId: product.id },
    });
  };

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.titleContainer}>
        <Text style={styles.title}>Search Products</Text>
        <Text style={styles.subtitle}>
          Find the best prices at nearby stores
          {user && <Text style={styles.deleteHint}> • Hold products to delete</Text>}
        </Text>
      </View>

      {user && (
        <TouchableOpacity
          style={styles.infoButton}
          onPress={() => setShowDeleteInfo(true)}
        >
          <Ionicons name="information-circle-outline" size={24} color={theme.colors.primary[500]} />
        </TouchableOpacity>
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {renderHeader()}

      {!hasLocationAccess && (
        <View style={styles.locationWarning}>
          <Text style={styles.locationWarningText}>
            📍 Location services are off. Enable them to see prices sorted by distance and find stores near you.
          </Text>
        </View>
      )}

      <ProductSearch 
        onProductSelect={handleProductSelect} 
        showDeleteOption={!!user} // Enable delete option if user is logged in
      />

      {/* Info Modal */}
      <Modal
        visible={showDeleteInfo}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setShowDeleteInfo(false)}
      >

        
        <SafeAreaView style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Product Management</Text>
            <TouchableOpacity
              style={styles.modalCloseButton}
              onPress={() => setShowDeleteInfo(false)}
            >
              <Ionicons name="close" size={24} color={theme.colors.text.primary} />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalContent}>
            <View style={styles.infoSection}>
              <Text style={styles.infoSectionTitle}>📊 Database Statistics</Text>
              {deletionStats ? (
                <View style={styles.statsContainer}>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Total Products:</Text>
                    <Text style={styles.statValue}>{deletionStats.total_products}</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Products with Prices:</Text>
                    <Text style={styles.statValue}>{deletionStats.products_with_prices}</Text>
                  </View>
                  <View style={styles.statItem}>
                    <Text style={styles.statLabel}>Products without Prices:</Text>
                    <Text style={styles.statValue}>{deletionStats.products_without_prices}</Text>
                  </View>
                </View>
              ) : (
                <Text style={styles.infoText}>Loading statistics...</Text>
              )}
            </View>

            <View style={styles.infoSection}>
              <Text style={styles.infoSectionTitle}>🗑️ Long Press to Delete</Text>
              <Text style={styles.infoText}>
                You can delete products by holding them for 3 seconds. This will permanently remove:
              </Text>
              <View style={styles.bulletList}>
                <Text style={styles.bulletItem}>• The product itself</Text>
                <Text style={styles.bulletItem}>• All price records for that product</Text>
                <Text style={styles.bulletItem}>• All visual and text embeddings</Text>
              </View>
              
              <View style={styles.howToContainer}>
                <Text style={styles.howToTitle}>How to delete:</Text>
                <View style={styles.stepContainer}>
                  <View style={styles.stepNumber}>
                    <Text style={styles.stepNumberText}>1</Text>
                  </View>
                  <Text style={styles.stepText}>Find the product you want to delete</Text>
                </View>
                <View style={styles.stepContainer}>
                  <View style={styles.stepNumber}>
                    <Text style={styles.stepNumberText}>2</Text>
                  </View>
                  <Text style={styles.stepText}>Press and hold for 3 seconds</Text>
                </View>
                <View style={styles.stepContainer}>
                  <View style={styles.stepNumber}>
                    <Text style={styles.stepNumberText}>3</Text>
                  </View>
                  <Text style={styles.stepText}>You'll feel a vibration and see a delete overlay</Text>
                </View>
                <View style={styles.stepContainer}>
                  <View style={styles.stepNumber}>
                    <Text style={styles.stepNumberText}>4</Text>
                  </View>
                  <Text style={styles.stepText}>Confirm deletion in the popup</Text>
                </View>
              </View>

              <Text style={styles.warningText}>
                ⚠️ This action cannot be undone. Use with caution.
              </Text>
            </View>

            <View style={styles.infoSection}>
              <Text style={styles.infoSectionTitle}>🔒 Permissions</Text>
              {deletionStats?.deletion_permissions && (
                <View style={styles.permissionsContainer}>
                  <View style={styles.permissionItem}>
                    <Ionicons 
                      name={deletionStats.deletion_permissions.can_delete_own ? "checkmark-circle" : "close-circle"} 
                      size={20} 
                      color={deletionStats.deletion_permissions.can_delete_own ? theme.colors.success[500] : theme.colors.error[500]}
                    />
                    <Text style={styles.permissionText}>Delete any product</Text>
                  </View>
                  <View style={styles.permissionItem}>
                    <Ionicons 
                      name={deletionStats.deletion_permissions.can_force_delete ? "checkmark-circle" : "close-circle"} 
                      size={20} 
                      color={deletionStats.deletion_permissions.can_force_delete ? theme.colors.success[500] : theme.colors.error[500]}
                    />
                    <Text style={styles.permissionText}>Force delete (admin only)</Text>
                  </View>
                </View>
              )}
            </View>

            <View style={styles.infoSection}>
              <Text style={styles.infoSectionTitle}>💡 Tips</Text>
              <View style={styles.bulletList}>
                <Text style={styles.bulletItem}>• Use filters to find specific products to manage</Text>
                <Text style={styles.bulletItem}>• Consider removing products without prices first</Text>
                <Text style={styles.bulletItem}>• Check location permissions for better search results</Text>
                <Text style={styles.bulletItem}>• Regular cleanup helps maintain app performance</Text>
                <Text style={styles.bulletItem}>• If you accidentally start a long press, just lift your finger</Text>
              </View>
            </View>
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: theme.spacing['2xl'],
    backgroundColor: theme.colors.primary[50],
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
  },
  titleContainer: {
    flex: 1,
  },
  title: {
    fontSize: theme.typography.fontSize['2xl'],
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  subtitle: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
  },
  deleteHint: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.primary[600],
    fontWeight: theme.typography.fontWeight.medium,
  },
  infoButton: {
    padding: theme.spacing.sm,
    backgroundColor: theme.colors.primary[50],
    borderRadius: theme.borderRadius.full,
  },
  locationWarning: {
    backgroundColor: theme.colors.warning[50],
    padding: theme.spacing.md,
    marginHorizontal: theme.spacing.lg,
    marginTop: theme.spacing.md,
    borderRadius: theme.borderRadius.md,
    borderLeftWidth: 4,
    borderLeftColor: theme.colors.warning[500],
  },
  locationWarningText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.warning[800],
    fontWeight: theme.typography.fontWeight.medium,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: theme.spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[200],
    backgroundColor: theme.colors.surface,
  },
  modalTitle: {
    fontSize: theme.typography.fontSize.xl,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
  },
  modalCloseButton: {
    padding: theme.spacing.sm,
  },
  modalContent: {
    flex: 1,
    padding: theme.spacing.lg,
  },
  infoSection: {
    marginBottom: theme.spacing.xl,
  },
  infoSectionTitle: {
    fontSize: theme.typography.fontSize.lg,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.md,
  },
  infoText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    lineHeight: theme.typography.lineHeight.relaxed * theme.typography.fontSize.base,
    marginBottom: theme.spacing.md,
  },
  statsContainer: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
  },
  statItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.gray[100],
  },
  statLabel: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
  },
  statValue: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.primary,
  },
  bulletList: {
    marginLeft: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  bulletItem: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.xs,
    lineHeight: theme.typography.lineHeight.relaxed * theme.typography.fontSize.base,
  },
  howToContainer: {
    backgroundColor: theme.colors.primary[50],
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
  },
  howToTitle: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: theme.typography.fontWeight.semibold,
    color: theme.colors.primary[700],
    marginBottom: theme.spacing.md,
  },
  stepContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  stepNumber: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: theme.colors.primary[500],
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  stepNumberText: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.bold,
    color: theme.colors.text.inverse,
  },
  stepText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.primary[700],
    flex: 1,
    lineHeight: theme.typography.lineHeight.relaxed * theme.typography.fontSize.base,
  },
  warningText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.error[600],
    fontWeight: theme.typography.fontWeight.medium,
    backgroundColor: theme.colors.error[50],
    padding: theme.spacing.sm,
    borderRadius: theme.borderRadius.md,
  },
  permissionsContainer: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
  },
  permissionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  permissionText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.secondary,
    marginLeft: theme.spacing.sm,
  },
});
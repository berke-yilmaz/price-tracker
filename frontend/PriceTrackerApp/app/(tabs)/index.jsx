import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
  ActivityIndicator,
  RefreshControl,
  Image,
  Dimensions,
  ScrollView,
  StatusBar,
  ImageBackground,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import * as ImagePicker from 'expo-image-picker';
import theme from '../../constants/theme';
import config from '../../config';
import EnhancedProductCreation from '../../components/EnhancedProductCreation';
import SimilarityResultsModal from '../../components/SimilarityResultsModal';
import { getImageUrl } from '../../utils/imageUtils';

const { width } = Dimensions.get('window');

const features = [
  {
    icon: 'camera-outline',
    title: 'Visual Product Search',
    description: 'Scan any product to instantly find it in the database.',
    gradient: ['#6366f1', '#818cf8'],
  },
  {
    icon: 'scan-outline',
    title: 'Advanced OCR',
    description: 'Automatically extract names and details from packaging.',
    gradient: ['#8b5cf6', '#a78bfa'],
  },
  {
    icon: 'color-palette-outline',
    title: 'Smart Color Analysis',
    description: 'Organize your products by their dominant color.',
    gradient: ['#10b981', '#34d399'],
  },
];

export default function HomeScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [recentProducts, setRecentProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // State for the modals and flow
  const [showSimilarityResults, setShowSimilarityResults] = useState(false);
  const [similarityCandidates, setSimilarityCandidates] = useState([]);
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [showProductCreation, setShowProductCreation] = useState(false);
  
  // State for the async job
  const [jobId, setJobId] = useState(null);
  const [isPolling, setIsPolling] = useState(false);
  const [processingImage, setProcessingImage] = useState(false);
  const [selectedImageUri, setSelectedImageUri] = useState(null);

  useEffect(() => { loadRecentProducts(); }, []);

  // Asynchronous Visual Search Polling
  useEffect(() => {
    if (!isPolling || !jobId) return;

    const interval = setInterval(async () => {
      try {
        const pollResponse = await fetch(`${config.API_URL}/products/visual-search-result/?job_id=${jobId}`, {
          headers: { 'Authorization': `Token ${token}` },
        });
        const pollResult = await pollResponse.json();

        if (pollResponse.status >= 400) { // Catch any client or server errors
          throw new Error(pollResult.error || 'Failed to get search result.');
        }

        if (pollResult.status === 'SUCCESS') {
          console.log("🎉 Home Screen: Job complete!", pollResult.results);
          clearInterval(interval);
          setIsPolling(false);
          setProcessingImage(false);
          
          setSimilarityCandidates(pollResult.results.candidates || []);
          setImageAnalysis(pollResult.results.image_analysis || null); // Ensure it can be null
          setShowSimilarityResults(true);

        } else if (pollResult.status === 'FAILURE') {
          throw new Error(pollResult.error || 'Processing failed.');
        }

      } catch (error) {
        console.error('❌ Home Screen: Polling error:', error);
        Alert.alert('Search Failed', error.message);
        clearInterval(interval);
        setIsPolling(false);
        setProcessingImage(false);
      }
    }, 2500); // Poll every 2.5 seconds

    return () => clearInterval(interval);
  }, [isPolling, jobId, token]);

  const loadRecentProducts = async () => {
    try {
      if (!refreshing) setLoading(true);
      await fetchRecentProducts();
    } catch (error) {
      console.error('Dashboard loading error:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchRecentProducts = async () => {
    try {
      const response = await fetch(`${config.API_URL}/products/?ordering=-created_at&page_size=10`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const data = await response.json();
        setRecentProducts(data.results || data || []);
      } else {
        throw new Error(`Server error: ${response.status}`);
      }
    } catch (error) {
      console.error('❌ Products fetch error:', error);
      setRecentProducts([]);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadRecentProducts();
  };

  const handleImageProductCreation = () => {
    Alert.alert(
      '✨ AI Visual Search',
      'Scan a product to find it or create a new one.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: '📷 Camera', onPress: () => takeProductPhoto() },
        { text: '🖼️ Gallery', onPress: () => pickProductImage() },
      ]
    );
  };
  
  const takeProductPhoto = async () => {
    const cameraPermission = await ImagePicker.requestCameraPermissionsAsync();
    if (cameraPermission.status !== 'granted') {
      Alert.alert("Permission Required", "Camera access is needed to take photos.");
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ allowsEditing: true, aspect: [4, 3], quality: 0.8 });
    if (!result.canceled && result.assets?.[0]) await handleImageSelected(result.assets[0].uri);
  };
  
  const pickProductImage = async () => {
    const libraryPermission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (libraryPermission.status !== 'granted') {
      Alert.alert("Permission Required", "Photo library access is needed to select images.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsEditing: true, aspect: [4, 3], quality: 0.8 });
    if (!result.canceled && result.assets?.[0]) await handleImageSelected(result.assets[0].uri);
  };

  const handleImageSelected = async (imageUri) => {
    if (!token) {
      Alert.alert("Authentication Required", "Please log in to use this feature.");
      return;
    }
    setProcessingImage(true);
    setSelectedImageUri(imageUri);
    try {
      const formData = new FormData();
      formData.append('image', { uri: imageUri, type: 'image/jpeg', name: 'product.jpg' });
      const response = await fetch(`${config.API_URL}/products/start-visual-search/`, {
        method: 'POST',
        headers: { 'Authorization': `Token ${token}` },
        body: formData,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Failed to start job.');
      
      console.log(`✅ Home Screen: Job started with ID: ${result.job_id}`);
      setJobId(result.job_id);
      setIsPolling(true);
    } catch (error) {
      console.error('❌ Visual search start error:', error);
      Alert.alert('Search Failed', error.message);
      setProcessingImage(false);
    }
  };
  
  const handleSimilaritySelect = (product) => {
    setShowSimilarityResults(false);
    // After selecting a known product, user goes to add a price for it.
    router.push({
      pathname: '/addprice',
      params: { 
        productId: product.id,
        productName: product.name,
        barcode: product.barcode || ''
      }
    });
  };

  const handleSimilarityNotFound = () => {
    // ⭐ THIS IS THE CORRECT, GLITCH-FREE WAY TO TRANSITION MODALS ⭐
    // Hide the similarity modal first.
    setShowSimilarityResults(false);
    
    // Immediately show the creation modal. React batches these state changes
    // for a smooth visual transition without navigating away.
    setShowProductCreation(true);
  };

  const handleProductCreated = (product) => {
    loadRecentProducts();
    Alert.alert(
      '🎉 Product Created!',
      `"${product.name}" has been added successfully.`,
      [
        { text: 'OK' },
        // Offer to add a price to the newly created product.
        { text: 'Add Price', onPress: () => router.push({ pathname: '/addprice', params: { productId: product.id, productName: product.name }}) },
      ]
    );
  };

  const closeProductCreation = () => {
    setShowProductCreation(false);
    setSelectedImageUri(null);
    setImageAnalysis(null);
  };
  
  const handleProductPress = (product) => {
    Alert.alert(
      product.name,
      `${product.brand || 'Brand not specified'}\n\nTo add a new price, please find this product via the Search or Scan tabs.`,
      [{ text: 'OK', style: 'cancel' }]
    );
  };
  
  const renderProductCard = (product) => {
    const imageUrl = getImageUrl(product);
    return (
      <View style={styles.productCard} key={product.id}>
        <TouchableOpacity onPress={() => handleProductPress(product)}>
          {imageUrl ? (
            <ImageBackground source={{ uri: imageUrl }} style={styles.productImage} imageStyle={{ borderRadius: theme.borderRadius.lg }}>
              <LinearGradient colors={['transparent', 'rgba(0,0,0,0.6)']} style={styles.productImageOverlay}>
                {product.brand && <Text style={styles.productCardBrand}>{product.brand}</Text>}
              </LinearGradient>
            </ImageBackground>
          ) : (
            <View style={[styles.productImage, styles.placeholderImage]}>
              <Ionicons name="image-outline" size={32} color={theme.colors.gray[400]} />
            </View>
          )}
        </TouchableOpacity>
        <Text style={styles.productName} numberOfLines={2}>{product.name}</Text>
      </View>
    );
  };
  
  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary[500]} />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary[500]} />}
      >
        <LinearGradient colors={theme.colors.gradients.primary} style={styles.header}>
            <View style={styles.headerContent}>
                <View>
                    <Text style={styles.greeting}>Ready to track prices?</Text>
                    <Text style={styles.userName}>Welcome back{user?.first_name ? `, ${user.first_name}` : ''}!</Text>
                </View>
                <TouchableOpacity onPress={() => router.push('/(tabs)/profile')}>
                    <View style={styles.avatarContainer}>
                        <Text style={styles.avatarText}>{(user?.first_name?.[0] || 'U').toUpperCase()}</Text>
                    </View>
                </TouchableOpacity>
            </View>
        </LinearGradient>

        <View style={styles.mainContent}>
            <TouchableOpacity style={styles.aiActionCard} onPress={handleImageProductCreation} disabled={processingImage || isPolling}>
                {(processingImage || isPolling) ? (
                  <>
                    <ActivityIndicator size="small" color={theme.colors.primary[600]} />
                    <Text style={styles.aiActionProcessingText}>Analyzing Image...</Text>
                  </>
                ) : (
                    <>
                        <View style={styles.aiActionIcon}><Ionicons name="sparkles" size={28} color={theme.colors.primary[500]} /></View>
                        <View style={styles.aiActionTextContainer}>
                            <Text style={styles.aiActionTitle}>AI Visual Search</Text>
                            <Text style={styles.aiActionSubtitle}>Scan a product to find or add it</Text>
                        </View>
                        <Ionicons name="chevron-forward" size={24} color={theme.colors.gray[400]} />
                    </>
                )}
            </TouchableOpacity>

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Recently Added</Text>
              {recentProducts.length > 0 ? (
                <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.productsContainer}>
                  {recentProducts.map(renderProductCard)}
                </ScrollView>
              ) : (
                <View style={styles.emptyState}>
                  <Ionicons name="albums-outline" size={48} color={theme.colors.gray[300]} />
                  <Text style={styles.emptyStateText}>Your recent products will appear here.</Text>
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Key Features</Text>
              <View style={styles.featuresContainer}>
                {features.map((feature) => (
                  <View key={feature.title} style={styles.featureItem}>
                      <LinearGradient colors={feature.gradient} style={styles.featureIconContainer}>
                          <Ionicons name={feature.icon} size={24} color="white" />
                      </LinearGradient>
                      <View style={styles.featureTextContainer}>
                          <Text style={styles.featureTitle}>{feature.title}</Text>
                          <Text style={styles.featureDescription}>{feature.description}</Text>
                      </View>
                  </View>
                ))}
              </View>
            </View>
        </View>
      </ScrollView>

      {showSimilarityResults && (
        <SimilarityResultsModal
          visible={showSimilarityResults}
          onClose={() => setShowSimilarityResults(false)}
          candidates={similarityCandidates}
          originalImageUri={selectedImageUri}
          onSelectProduct={handleSimilaritySelect}
          onProductNotFound={handleSimilarityNotFound}
        />
      )}

      {showProductCreation && (
        <EnhancedProductCreation
          visible={showProductCreation}
          onClose={closeProductCreation}
          imageUri={selectedImageUri}
          ocrResult={imageAnalysis}
          onProductCreated={handleProductCreated}
        />
      )}
    </SafeAreaView>
  );
}

// Styles remain unchanged.
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { paddingTop: 60, paddingBottom: 40, paddingHorizontal: theme.spacing.lg },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  greeting: { fontSize: theme.typography.fontSize['2xl'], fontWeight: theme.typography.fontWeight.bold, color: theme.colors.text.inverse },
  userName: { fontSize: theme.typography.fontSize.base, color: theme.colors.primary[200], opacity: 0.9, marginTop: theme.spacing.xs },
  avatarContainer: { width: 52, height: 52, borderRadius: 26, backgroundColor: 'rgba(255,255,255,0.2)', justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: 'white' },
  avatarText: { fontSize: theme.typography.fontSize.xl, fontWeight: theme.typography.fontWeight.bold, color: theme.colors.text.inverse },
  mainContent: { marginTop: -theme.spacing.xl, borderTopLeftRadius: theme.borderRadius['2xl'], borderTopRightRadius: theme.borderRadius['2xl'], backgroundColor: theme.colors.background, paddingTop: theme.spacing.lg, paddingBottom: theme.spacing['3xl'] },
  aiActionCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: theme.colors.surface, marginHorizontal: theme.spacing.lg, padding: theme.spacing.md, borderRadius: theme.borderRadius.xl, ...theme.shadows.md },
  aiActionIcon: { width: 50, height: 50, borderRadius: theme.borderRadius.lg, backgroundColor: theme.colors.primary[50], justifyContent: 'center', alignItems: 'center', marginRight: theme.spacing.md },
  aiActionTextContainer: { flex: 1 },
  aiActionTitle: { fontSize: theme.typography.fontSize.lg, fontWeight: theme.typography.fontWeight.semibold, color: theme.colors.text.primary },
  aiActionSubtitle: { fontSize: theme.typography.fontSize.sm, color: theme.colors.text.secondary, marginTop: 2 },
  aiActionProcessingText: { marginLeft: 12, fontSize: 16, fontWeight: '500', color: theme.colors.primary[600] },
  section: { marginTop: theme.spacing.xl, marginBottom: theme.spacing.sm },
  sectionTitle: { fontSize: theme.typography.fontSize.xl, fontWeight: theme.typography.fontWeight.semibold, color: theme.colors.text.primary, paddingHorizontal: theme.spacing.lg, marginBottom: theme.spacing.md },
  productsContainer: { paddingHorizontal: theme.spacing.lg, gap: theme.spacing.md },
  productCard: { width: 150 },
  productImage: { width: '100%', height: 180, borderRadius: theme.borderRadius.lg, justifyContent: 'flex-end', backgroundColor: theme.colors.gray[200] },
  placeholderImage: { alignItems: 'center', justifyContent: 'center' },
  productImageOverlay: { padding: theme.spacing.sm, borderRadius: theme.borderRadius.lg },
  productCardBrand: { color: 'white', fontWeight: '600', fontSize: 12, textShadowColor: 'rgba(0, 0, 0, 0.5)', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 2 },
  productName: { fontSize: theme.typography.fontSize.sm, color: theme.colors.text.primary, fontWeight: '500', marginTop: theme.spacing.sm, lineHeight: 18 },
  emptyState: { alignItems: 'center', justifyContent: 'center', padding: theme.spacing.xl, marginHorizontal: theme.spacing.lg, backgroundColor: theme.colors.gray[100], borderRadius: theme.borderRadius.lg, height: 150, borderWidth: 1, borderColor: theme.colors.gray[200] },
  emptyStateText: { marginTop: theme.spacing.sm, fontSize: 14, color: theme.colors.text.secondary, textAlign: 'center' },
  featuresContainer: { paddingHorizontal: theme.spacing.lg, gap: theme.spacing.md },
  featureItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'white', padding: theme.spacing.md, borderRadius: theme.borderRadius.lg, ...theme.shadows.sm },
  featureIconContainer: { width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center', marginRight: theme.spacing.md },
  featureTextContainer: { flex: 1 },
  featureTitle: { fontSize: 16, fontWeight: '600', color: theme.colors.text.primary },
  featureDescription: { fontSize: 13, color: theme.colors.text.secondary, marginTop: 2, lineHeight: 18 },
});
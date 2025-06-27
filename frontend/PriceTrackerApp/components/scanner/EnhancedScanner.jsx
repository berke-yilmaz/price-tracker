// components/scanner/EnhancedScanner.jsx - FINAL CORRECTED VERSION
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  Platform,
  Alert,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera'; 
import * as ImagePicker from 'expo-image-picker';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import theme from '../../constants/theme';
import Button from '../ui/Button';
import Card from '../ui/Card';

const { width } = Dimensions.get('window');

const EnhancedScanner = ({
  onBarcodeScanned,
  onPhotoTaken,
  onGalleryPhoto,
  mode = 'both',
  showGallery = true,
  showFlash = true,
}) => {
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraType, setCameraType] = useState('back');
  const [flashMode, setFlashMode] = useState('off');
  const [processing, setProcessing] = useState(false);
  const [scannerActive, setScannerActive] = useState(true);
  
  const cameraRef = useRef(null);
  const scanLineAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (mode === 'barcode' || mode === 'both') {
      startScanLineAnimation();
    }
  }, [mode]);

  const startScanLineAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(scanLineAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
        Animated.timing(scanLineAnim, { toValue: 0, duration: 2000, useNativeDriver: true }),
      ])
    ).start();
  };
  
  const handleBarcodeScanned = ({ type, data }) => {
    if (!scannerActive) return;
    setScannerActive(false);
    onBarcodeScanned?.({ type, data });
    setTimeout(() => setScannerActive(true), 2000);
  };

  const takePicture = async () => {
    if (!cameraRef.current || processing) return;
    setProcessing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.8 });
      onPhotoTaken?.(photo);
    } catch (error) {
      Alert.alert('Error', 'Failed to take photo');
    } finally {
      setProcessing(false);
    }
  };

  const pickFromGallery = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsEditing: true, aspect: [4, 3], quality: 0.8,
      });
      if (!result.canceled && result.assets[0]) {
        onGalleryPhoto?.(result.assets[0]);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to open gallery');
    }
  };

  const toggleFlash = () => setFlashMode(current => (current === 'off' ? 'torch' : 'off'));
  const flipCamera = () => setCameraType(current => (current === 'back' ? 'front' : 'back'));
  
  if (!permission) {
    return (
      <View style={styles.centerContainer}>
        <Card style={styles.permissionCard}>
          <Ionicons name="camera-outline" size={48} color={theme.colors.gray[400]} />
          <Text style={styles.permissionText}>Requesting permissions...</Text>
        </Card>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
        <Card style={styles.permissionCard}>
          <Ionicons name="camera-off-outline" size={48} color={theme.colors.error[500]} />
          <Text style={styles.permissionTitle}>Camera Access Required</Text>
          <Text style={styles.permissionText}>We need your permission to use the camera for scanning and taking photos.</Text>
          <Button title="Grant Permission" onPress={requestPermission} style={styles.permissionButton} />
        </Card>
      </View>
    );
  }

  const scanAreaSize = width * 0.7;
  const scanLineY = scanLineAnim.interpolate({
    inputRange: [0, 1], outputRange: [0, scanAreaSize - 4],
  });

  // ⭐ START OF FIX ⭐
  return (
    <View style={styles.container}>
      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing={cameraType}
        enableTorch={flashMode === 'torch'}
        onBarcodeScanned={(mode === 'barcode' || mode === 'both') && scannerActive ? handleBarcodeScanned : undefined}
        barcodeScannerSettings={{ barcodeTypes: ["ean13", "ean8", "qr"] }}
      />
      {/* The overlay is now a sibling to CameraView, not a child */}
      <View style={styles.overlay}>
        <View style={styles.topControls}>
          <TouchableOpacity style={styles.controlButton} onPress={flipCamera}>
            <Ionicons name="camera-reverse" size={24} color="white" />
          </TouchableOpacity>
          {showFlash && (
            <TouchableOpacity style={styles.controlButton} onPress={toggleFlash}>
              <Ionicons name={flashMode === 'off' ? "flash-off" : "flash"} size={24} color="white" />
            </TouchableOpacity>
          )}
        </View>
        {(mode === 'barcode' || mode === 'both') && (
          <View style={styles.scannerContainer}>
            <Text style={styles.instructionText}>Position barcode within the frame</Text>
            <View style={styles.scannerFrame}>
              <View style={[styles.corner, styles.topLeft]} />
              <View style={[styles.corner, styles.topRight]} />
              <View style={[styles.corner, styles.bottomLeft]} />
              <View style={[styles.corner, styles.bottomRight]} />
              <Animated.View style={[styles.scanLine, { transform: [{ translateY: scanLineY }] }]} />
            </View>
          </View>
        )}
        <View style={styles.bottomControls}>
          {showGallery && (
            <TouchableOpacity style={styles.galleryButton} onPress={pickFromGallery}>
              <Ionicons name="images-outline" size={24} color="white" />
              <Text style={styles.galleryText}>Gallery</Text>
            </TouchableOpacity>
          )}
          {(mode === 'photo' || mode === 'both') && (
            <TouchableOpacity style={[styles.captureButton, processing && styles.captureButtonDisabled]} onPress={takePicture} disabled={processing}>
                <Ionicons name="camera" size={40} color="white" />
            </TouchableOpacity>
          )}
          <View style={{ width: 60 }} />
        </View>
      </View>
    </View>
  );
  // ⭐ END OF FIX ⭐
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'black', // Ensure background is black
  },
  camera: {
    ...StyleSheet.absoluteFillObject, // Make camera fill the container
  },
  overlay: {
    ...StyleSheet.absoluteFillObject, // Make overlay fill the container on top of camera
    backgroundColor: 'transparent',
    justifyContent: 'space-between',
  },
  // --- The rest of the styles are unchanged ---
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.colors.background, padding: theme.spacing.lg },
  permissionCard: { alignItems: 'center', padding: theme.spacing.xl },
  permissionTitle: { fontSize: theme.typography.fontSize.lg, fontWeight: theme.typography.fontWeight.bold, color: theme.colors.text.primary, marginTop: theme.spacing.md, marginBottom: theme.spacing.sm, textAlign: 'center' },
  permissionText: { fontSize: theme.typography.fontSize.base, color: theme.colors.text.secondary, textAlign: 'center', marginBottom: theme.spacing.lg },
  permissionButton: { marginTop: theme.spacing.md },
  topControls: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: theme.spacing.lg, paddingTop: Platform.OS === 'ios' ? 60 : theme.spacing.lg, },
  controlButton: { width: 48, height: 48, borderRadius: 24, backgroundColor: 'rgba(0, 0, 0, 0.4)', justifyContent: 'center', alignItems: 'center' },
  scannerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingBottom: 100 },
  instructionText: { color: 'white', fontSize: theme.typography.fontSize.base, textAlign: 'center', marginBottom: theme.spacing.xl, paddingHorizontal: theme.spacing.lg, textShadowColor: 'rgba(0, 0, 0, 0.7)', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 2 },
  scannerFrame: { width: width * 0.7, height: width * 0.7, position: 'relative' },
  corner: { position: 'absolute', width: 30, height: 30, borderColor: theme.colors.primary[400], borderWidth: 4 },
  topLeft: { top: -2, left: -2, borderRightWidth: 0, borderBottomWidth: 0 },
  topRight: { top: -2, right: -2, borderLeftWidth: 0, borderBottomWidth: 0 },
  bottomLeft: { bottom: -2, left: -2, borderRightWidth: 0, borderTopWidth: 0 },
  bottomRight: { bottom: -2, right: -2, borderLeftWidth: 0, borderTopWidth: 0 },
  scanLine: { position: 'absolute', left: 0, right: 0, height: 2, backgroundColor: theme.colors.primary[400], shadowColor: theme.colors.primary[400], shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.8, shadowRadius: 4 },
  bottomControls: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: theme.spacing.xl, paddingBottom: Platform.OS === 'ios' ? 40 : theme.spacing.lg },
  galleryButton: { alignItems: 'center', justifyContent: 'center', width: 60, height: 60 },
  galleryText: { color: 'white', fontSize: theme.typography.fontSize.xs, marginTop: theme.spacing.xs },
  captureButton: { width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(255, 255, 255, 0.3)', justifyContent: 'center', alignItems: 'center', borderWidth: 4, borderColor: 'white' },
  captureButtonDisabled: { opacity: 0.5 },
});

export default EnhancedScanner;
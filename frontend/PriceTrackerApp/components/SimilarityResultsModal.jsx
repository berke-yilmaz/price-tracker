// components/SimilarityResultsModal.jsx - FINAL CORRECTED VERSION
import React from 'react';
import {
  Modal, View, Text, StyleSheet, TouchableOpacity, Image, FlatList, SafeAreaView
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import theme from '../constants/theme';
import { LinearGradient } from 'expo-linear-gradient';
import { getImageUrl } from '../utils/imageUtils'; 

const ProductCandidateCard = ({ item, onSelect }) => {
  const imageUrl = getImageUrl(item); 

  return (
    <TouchableOpacity style={styles.candidateCard} onPress={() => onSelect(item)}>
      {imageUrl ? (
        <Image source={{ uri: imageUrl }} style={styles.candidateImage} />
      ) : (
        <View style={[styles.candidateImage, styles.placeholderImage]}>
          <Ionicons name="image-outline" size={32} color={theme.colors.gray[400]} />
        </View>
      )}
      <View style={styles.candidateInfo}>
        <Text style={styles.candidateName} numberOfLines={2}>{item.name}</Text>
        <Text style={styles.candidateBrand}>{item.brand || 'No Brand'}</Text>
        
        {/* ⭐ --- THE FIX IS HERE --- ⭐ */}
        {/* We now access item.scores.hybrid_score and provide a fallback of 0 */}
        <View style={styles.similarityBadge}>
          <Ionicons name="flash-outline" size={14} color={theme.colors.primary[600]} />
          <Text style={styles.similarityText}>
        {/* ⭐ FIX: Use optional chaining to prevent crash if 'scores' is missing */}
        ~{item.scores?.hybrid_score?.toFixed(0) || 0}% similar
      </Text>
        </View>
        {/* ⭐ --- END OF FIX --- ⭐ */}

      </View>
      <Ionicons name="chevron-forward" size={24} color={theme.colors.gray[400]} />
    </TouchableOpacity>
  );
};


const SimilarityResultsModal = ({
  visible,
  onClose,
  candidates = [],
  originalImageUri,
  onSelectProduct,
  onProductNotFound,
}) => {
  // The rest of this component is unchanged and correct.
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Is this your product?</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={28} color={theme.colors.text.primary} />
          </TouchableOpacity>
        </View>
        <View style={styles.sourceContainer}>
          {originalImageUri ? (
             <Image source={{ uri: originalImageUri }} style={styles.sourceImage} />
          ) : (
            <View style={[styles.sourceImage, styles.placeholderImage]}>
              <Ionicons name="camera-outline" size={40} color={theme.colors.gray[400]} />
            </View>
          )}
          <Text style={styles.sourceCaption}>Your Scanned Image</Text>
        </View>
        <Text style={styles.listHeader}>We found these similar products:</Text>
        <FlatList
          data={candidates}
          renderItem={({ item }) => <ProductCandidateCard item={item} onSelect={onSelectProduct} />}
          keyExtractor={(item, index) => item?.id?.toString() || index.toString()}
          contentContainerStyle={styles.listContainer}
          ListEmptyComponent={() => (
            <View style={styles.emptyContainer}>
                <Ionicons name="search-circle-outline" size={60} color={theme.colors.gray[400]} />
                <Text style={styles.emptyText}>No similar products found in the database.</Text>
                <Text style={styles.emptySubText}>You can create it as a new product.</Text>
            </View>
          )}
        />
        <View style={styles.footer}>
          <TouchableOpacity style={styles.notFoundButton} onPress={onProductNotFound}>
            <LinearGradient
                colors={theme.colors.gradients.primary}
                style={styles.gradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
            >
                <Ionicons name="add" size={24} color="white" />
                <Text style={styles.notFoundButtonText}>None of these, Create New</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </Modal>
  );
};


// --- STYLES (NO CHANGES NEEDED, INCLUDED FOR COMPLETENESS) ---
const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.colors.background },
    header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
    headerTitle: { fontSize: 20, fontWeight: '600', color: theme.colors.text.primary, },
    closeButton: { padding: 4 },
    sourceContainer: { alignItems: 'center', padding: 16, backgroundColor: theme.colors.gray[100], borderBottomWidth: 1, borderBottomColor: theme.colors.gray[200] },
    sourceImage: { width: 120, height: 120, borderRadius: 12, borderWidth: 3, borderColor: theme.colors.primary[500], backgroundColor: theme.colors.gray[200], },
    placeholderImage: { alignItems: 'center', justifyContent: 'center' },
    sourceCaption: { marginTop: 8, color: theme.colors.text.secondary, fontSize: 14 },
    listHeader: { fontSize: 16, fontWeight: '500', paddingHorizontal: 16, paddingTop: 20, paddingBottom: 10, color: theme.colors.text.primary, },
    listContainer: { paddingHorizontal: 16, paddingBottom: 20 },
    candidateCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'white', padding: 12, borderRadius: 12, marginBottom: 12, borderWidth: 1, borderColor: theme.colors.gray[200], ...theme.shadows.sm, },
    candidateImage: { width: 70, height: 70, borderRadius: 8, marginRight: 12, backgroundColor: theme.colors.gray[100], },
    candidateInfo: { flex: 1 },
    candidateName: { fontSize: 16, fontWeight: '600', marginBottom: 4, color: theme.colors.text.primary, },
    candidateBrand: { fontSize: 14, color: theme.colors.text.secondary, marginBottom: 8 },
    similarityBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: theme.colors.primary[50], paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6, alignSelf: 'flex-start' },
    similarityText: { marginLeft: 6, color: theme.colors.primary[600], fontWeight: '500', fontSize: 12 },
    footer: { padding: 16, borderTopWidth: 1, borderTopColor: theme.colors.gray[200], backgroundColor: 'rgba(255,255,255,0.8)', },
    notFoundButton: { borderRadius: 12, overflow: 'hidden', ...theme.shadows.md, },
    gradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 16, gap: 10 },
    notFoundButtonText: { color: 'white', fontSize: 16, fontWeight: '600' },
    emptyContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 50 },
    emptyText: { marginTop: 16, fontSize: 16, color: theme.colors.text.secondary, textAlign: 'center', fontWeight: '500', },
    emptySubText: { marginTop: 8, fontSize: 14, color: theme.colors.text.secondary, textAlign: 'center', }
});

export default SimilarityResultsModal;
// components/scanner/BarcodeDisambiguationModal.jsx - CORRECTED
import React from 'react';
import { 
    Modal, 
    View, 
    Text, 
    StyleSheet, 
    TouchableOpacity, 
    FlatList, 
    SafeAreaView, 
    Image // ⭐ FIX: Import the Image component
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import theme from '../../constants/theme';
import { getImageUrl } from '../../utils/imageUtils';
import Button from '../ui/Button';
import Card from '../ui/Card';

const BarcodeDisambiguationModal = ({
  visible,
  onClose,
  products = [],
  barcode,
  onSelectProduct,
  onCreateNew,
}) => {

  const renderProductItem = ({ item }) => {
    const imageUrl = getImageUrl(item);
    return (
      <TouchableOpacity onPress={() => onSelectProduct(item)}>
        <Card style={styles.productCard}>
          {/* ⭐ FIX: Add a placeholder for consistency */}
          {imageUrl ? (
            <Image source={{ uri: imageUrl }} style={styles.productImage} />
          ) : (
            <View style={[styles.productImage, styles.placeholderImage]}>
              <Ionicons name="image-outline" size={32} color={theme.colors.gray[400]} />
            </View>
          )}
          <View style={styles.productInfo}>
            <Text style={styles.productName} numberOfLines={2}>{item.name}</Text>
            <Text style={styles.productBrand}>{item.brand || 'No Brand'}</Text>
          </View>
          <Ionicons name="chevron-forward" size={24} color={theme.colors.gray[400]} />
        </Card>
      </TouchableOpacity>
    );
  };
  
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Multiple Products Found</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={28} color={theme.colors.text.primary} />
          </TouchableOpacity>
        </View>

        <View style={styles.infoContainer}>
            <Ionicons name="alert-circle-outline" size={32} color={theme.colors.primary[500]}/>
            <View style={styles.infoTextContainer}>
                <Text style={styles.infoText}>This barcode is used for multiple products. Please select the correct one.</Text>
                <Text style={styles.barcodeText}>Barcode: {barcode}</Text>
            </View>
        </View>

        <FlatList
          data={products}
          renderItem={renderProductItem}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContainer}
        />
        
        <View style={styles.footer}>
            <Button
                title="It's a different product"
                onPress={onCreateNew}
                variant="outline"
                icon={<Ionicons name="add" size={20} color={theme.colors.primary[500]} style={{marginRight: 8}}/>}
            />
        </View>
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
    container: { 
        flex: 1, 
        backgroundColor: theme.colors.background 
    },
    header: { 
        flexDirection: 'row', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: 16, 
        borderBottomWidth: 1, 
        borderBottomColor: theme.colors.gray[200] 
    },
    headerTitle: { 
        fontSize: 20, 
        fontWeight: '600',
        color: theme.colors.text.primary,
    },
    closeButton: { 
        padding: 4 
    },
    infoContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        backgroundColor: theme.colors.primary[50],
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.gray[200],
    },
    infoTextContainer: {
        marginLeft: 12,
        flex: 1,
    },
    infoText: {
        fontSize: 14,
        color: theme.colors.text.secondary,
        lineHeight: 20,
    },
    barcodeText: {
        fontSize: 12,
        color: theme.colors.text.secondary,
        fontFamily: 'monospace',
        marginTop: 4,
    },
    listContainer: { 
        paddingHorizontal: 16, 
        paddingTop: 16,
        paddingBottom: 20 
    },
    productCard: { 
        flexDirection: 'row', 
        alignItems: 'center', 
        padding: 12, 
        marginBottom: 12,
    },
    productImage: { 
        width: 60, 
        height: 60, 
        borderRadius: 8, 
        marginRight: 12,
        backgroundColor: theme.colors.gray[100],
    },
    // ⭐ FIX: Add placeholder style
    placeholderImage: {
      justifyContent: 'center',
      alignItems: 'center',
    },
    productInfo: { 
        flex: 1 
    },
    productName: { 
        fontSize: 16, 
        fontWeight: '600', 
        marginBottom: 4,
        color: theme.colors.text.primary,
    },
    productBrand: { 
        fontSize: 14, 
        color: theme.colors.text.secondary, 
    },
    footer: { 
        padding: 16, 
        borderTopWidth: 1, 
        borderTopColor: theme.colors.gray[200], 
    },
});

export default BarcodeDisambiguationModal;
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Image,
  StyleSheet,
  SafeAreaView,
  RefreshControl,
  Alert,
  Modal,
  TextInput,
} from 'react-native';
import { launchImageLibrary, ImagePickerResponse } from 'react-native-image-picker';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList, WardrobeItem } from '../types';
import { colors } from '../constants/colors';
import { commonStyles } from '../constants/styles';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';

type WardrobeScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'Wardrobe'
>;

interface Props {
  navigation: WardrobeScreenNavigationProp;
}

const CATEGORIES = [
  'Tops', 'Bottoms', 'Dresses', 'Outerwear', 'Shoes', 
  'Accessories', 'Underwear', 'Activewear', 'Other'
];

const SEASONS = [
  { key: 'all', label: 'All Seasons' },
  { key: 'spring', label: 'Spring' },
  { key: 'summer', label: 'Summer' },
  { key: 'fall', label: 'Fall' },
  { key: 'winter', label: 'Winter' },
];

export const WardrobeScreen: React.FC<Props> = ({ navigation }) => {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [filterCategory, setFilterCategory] = useState('');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);

  // Add item form state
  const [newItem, setNewItem] = useState({
    name: '',
    category: 'Tops',
    color: '',
    season: 'all',
    image: null as any,
  });

  const loadWardrobe = async () => {
    try {
      const userData = await StorageService.getUserData();
      if (userData?.id) {
        const wardrobeData = await ApiService.getWardrobeItems(userData.id);
        setItems(wardrobeData);
      }
    } catch (error) {
      console.error('Error loading wardrobe:', error);
      Alert.alert('Error', 'Failed to load wardrobe items');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadWardrobe();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadWardrobe();
  };

  const filteredItems = items.filter(item => {
    if (filterCategory && item.category !== filterCategory) return false;
    if (showFavoritesOnly && !item.is_favorite) return false;
    return true;
  });

  const toggleFavorite = async (itemId: string) => {
    try {
      await ApiService.toggleFavorite(itemId);
      setItems(prev => prev.map(item => 
        item.id === itemId 
          ? { ...item, is_favorite: !item.is_favorite }
          : item
      ));
    } catch (error) {
      Alert.alert('Error', 'Failed to update favorite status');
    }
  };

  const deleteItem = async (itemId: string) => {
    Alert.alert(
      'Delete Item',
      'Are you sure you want to delete this item?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await ApiService.deleteWardrobeItem(itemId);
              setItems(prev => prev.filter(item => item.id !== itemId));
            } catch (error) {
              Alert.alert('Error', 'Failed to delete item');
            }
          },
        },
      ]
    );
  };

  const selectImage = () => {
    launchImageLibrary(
      {
        mediaType: 'photo',
        quality: 0.8,
        maxWidth: 800,
        maxHeight: 800,
      },
      (response: ImagePickerResponse) => {
        if (response.assets && response.assets[0]) {
          setNewItem(prev => ({ ...prev, image: response.assets![0] }));
        }
      }
    );
  };

  const addItem = async () => {
    if (!newItem.name.trim()) {
      Alert.alert('Error', 'Please enter an item name');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('name', newItem.name);
      formData.append('category', newItem.category);
      formData.append('color', newItem.color);
      formData.append('season', newItem.season);

      if (newItem.image) {
        formData.append('image', {
          uri: newItem.image.uri,
          type: newItem.image.type,
          name: newItem.image.fileName || 'image.jpg',
        } as any);
      }

      await ApiService.addWardrobeItem(formData);
      
      setShowAddModal(false);
      setNewItem({
        name: '',
        category: 'Tops',
        color: '',
        season: 'all',
        image: null,
      });
      
      loadWardrobe(); // Refresh the list
      Alert.alert('Success', 'Item added to wardrobe!');
    } catch (error) {
      Alert.alert('Error', 'Failed to add item. Please try again.');
    }
  };

  const renderItem = (item: WardrobeItem) => (
    <View key={item.id} style={styles.itemCard}>
      <View style={styles.itemHeader}>
        <View style={styles.itemInfo}>
          <Text style={styles.itemName}>{item.name}</Text>
          <Text style={styles.itemDetails}>
            {item.category} {item.color ? `• ${item.color}` : ''}
          </Text>
          <Text style={styles.itemSeason}>
            {SEASONS.find(s => s.key === item.season)?.label || item.season}
          </Text>
        </View>
        
        <View style={styles.itemActions}>
          <TouchableOpacity
            onPress={() => toggleFavorite(item.id)}
            style={styles.actionButton}
          >
            <Text style={styles.favoriteIcon}>
              {item.is_favorite ? '⭐' : '☆'}
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            onPress={() => deleteItem(item.id)}
            style={styles.actionButton}
          >
            <Text style={styles.deleteIcon}>🗑️</Text>
          </TouchableOpacity>
        </View>
      </View>

      {item.image && (
        <Image source={{ uri: item.image }} style={styles.itemImage} />
      )}
    </View>
  );

  if (loading) {
    return (
      <SafeAreaView style={commonStyles.centerContent}>
        <Text>Loading wardrobe...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={commonStyles.safeArea}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={commonStyles.header}>My Wardrobe</Text>
          <TouchableOpacity
            onPress={() => setShowAddModal(true)}
            style={styles.addButton}
          >
            <Text style={styles.addButtonText}>+ Add Item</Text>
          </TouchableOpacity>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filters}>
          <TouchableOpacity
            style={[styles.filterButton, !filterCategory && styles.activeFilter]}
            onPress={() => setFilterCategory('')}
          >
            <Text style={[styles.filterText, !filterCategory && styles.activeFilterText]}>
              All
            </Text>
          </TouchableOpacity>
          
          {CATEGORIES.map(category => (
            <TouchableOpacity
              key={category}
              style={[styles.filterButton, filterCategory === category && styles.activeFilter]}
              onPress={() => setFilterCategory(category)}
            >
              <Text style={[styles.filterText, filterCategory === category && styles.activeFilterText]}>
                {category}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <TouchableOpacity
          style={styles.favoritesToggle}
          onPress={() => setShowFavoritesOnly(!showFavoritesOnly)}
        >
          <Text style={styles.favoritesToggleText}>
            {showFavoritesOnly ? '⭐ Showing Favorites' : '☆ Show Favorites Only'}
          </Text>
        </TouchableOpacity>

        <ScrollView
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        >
          {filteredItems.length > 0 ? (
            filteredItems.map(renderItem)
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>
                {showFavoritesOnly 
                  ? 'No favorite items found' 
                  : 'No wardrobe items yet'
                }
              </Text>
              <TouchableOpacity
                onPress={() => setShowAddModal(true)}
                style={commonStyles.button}
              >
                <Text style={commonStyles.buttonText}>Add Your First Item</Text>
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>
      </View>

      {/* Add Item Modal */}
      <Modal visible={showAddModal} animationType="slide" presentationStyle="pageSheet">
        <SafeAreaView style={commonStyles.safeArea}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setShowAddModal(false)}>
              <Text style={styles.modalClose}>Cancel</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>Add New Item</Text>
            <TouchableOpacity onPress={addItem}>
              <Text style={styles.modalSave}>Save</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalContent}>
            <View style={styles.formGroup}>
              <Text style={styles.label}>Item Name *</Text>
              <TextInput
                style={commonStyles.input}
                value={newItem.name}
                onChangeText={(text) => setNewItem(prev => ({ ...prev, name: text }))}
                placeholder="e.g., Blue Cotton T-Shirt"
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                <View style={styles.categoryOptions}>
                  {CATEGORIES.map(category => (
                    <TouchableOpacity
                      key={category}
                      style={[
                        styles.categoryOption,
                        newItem.category === category && styles.selectedCategory
                      ]}
                      onPress={() => setNewItem(prev => ({ ...prev, category }))}
                    >
                      <Text style={[
                        styles.categoryText,
                        newItem.category === category && styles.selectedCategoryText
                      ]}>
                        {category}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </ScrollView>
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Color</Text>
              <TextInput
                style={commonStyles.input}
                value={newItem.color}
                onChangeText={(text) => setNewItem(prev => ({ ...prev, color: text }))}
                placeholder="e.g., Navy Blue, Red, etc."
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Season</Text>
              <View style={styles.seasonOptions}>
                {SEASONS.map(season => (
                  <TouchableOpacity
                    key={season.key}
                    style={[
                      styles.seasonOption,
                      newItem.season === season.key && styles.selectedSeason
                    ]}
                    onPress={() => setNewItem(prev => ({ ...prev, season: season.key }))}
                  >
                    <Text style={[
                      styles.seasonText,
                      newItem.season === season.key && styles.selectedSeasonText
                    ]}>
                      {season.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.label}>Photo</Text>
              <TouchableOpacity onPress={selectImage} style={styles.imageSelector}>
                {newItem.image ? (
                  <Image source={{ uri: newItem.image.uri }} style={styles.selectedImage} />
                ) : (
                  <View style={styles.imagePlaceholder}>
                    <Text style={styles.imagePlaceholderText}>📷 Add Photo</Text>
                  </View>
                )}
              </TouchableOpacity>
            </View>
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  addButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  addButtonText: {
    color: colors.surface,
    fontSize: 14,
    fontWeight: '600',
  },
  filters: {
    marginBottom: 16,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  activeFilter: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  filterText: {
    color: colors.text,
    fontSize: 14,
  },
  activeFilterText: {
    color: colors.surface,
    fontWeight: '500',
  },
  favoritesToggle: {
    marginBottom: 16,
    alignSelf: 'flex-start',
  },
  favoritesToggleText: {
    color: colors.primary,
    fontSize: 16,
  },
  itemCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  itemDetails: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  itemSeason: {
    fontSize: 12,
    color: colors.textSecondary,
  },
  itemActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    padding: 8,
  },
  favoriteIcon: {
    fontSize: 20,
  },
  deleteIcon: {
    fontSize: 16,
  },
  itemImage: {
    width: '100%',
    height: 200,
    borderRadius: 8,
    marginTop: 12,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    color: colors.textSecondary,
    marginBottom: 20,
    textAlign: 'center',
  },
  // Modal Styles
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  modalClose: {
    color: colors.textSecondary,
    fontSize: 16,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
  },
  modalSave: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  modalContent: {
    flex: 1,
    padding: 16,
  },
  formGroup: {
    marginBottom: 24,
  },
  label: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
    marginBottom: 8,
  },
  categoryOptions: {
    flexDirection: 'row',
    gap: 8,
  },
  categoryOption: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  selectedCategory: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  categoryText: {
    fontSize: 14,
    color: colors.text,
  },
  selectedCategoryText: {
    color: colors.surface,
    fontWeight: '500',
  },
  seasonOptions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  seasonOption: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  selectedSeason: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  seasonText: {
    fontSize: 14,
    color: colors.text,
  },
  selectedSeasonText: {
    color: colors.surface,
    fontWeight: '500',
  },
  imageSelector: {
    borderRadius: 8,
    overflow: 'hidden',
  },
  selectedImage: {
    width: '100%',
    height: 200,
  },
  imagePlaceholder: {
    height: 120,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: colors.border,
    borderStyle: 'dashed',
  },
  imagePlaceholderText: {
    color: colors.textSecondary,
    fontSize: 16,
  },
});
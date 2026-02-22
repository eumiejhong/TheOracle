import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  SafeAreaView,
  Alert,
  Modal,
  Image,
} from 'react-native';
import { launchImageLibrary, ImagePickerResponse } from 'react-native-image-picker';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList, WardrobeItem } from '../types';
import { colors } from '../constants/colors';
import { commonStyles } from '../constants/styles';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';

type DailyInputScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'DailyInput'
>;

interface Props {
  navigation: DailyInputScreenNavigationProp;
}

const MOOD_OPTIONS = [
  '😊 Happy', '💪 Confident', '😌 Relaxed', '🔥 Powerful', 
  '✨ Creative', '🎯 Focused', '💕 Romantic', '😎 Cool'
];

const WEATHER_OPTIONS = [
  '☀️ Sunny', '⛅ Partly Cloudy', '☁️ Overcast', '🌧️ Rainy',
  '❄️ Cold', '🌬️ Windy', '🌡️ Hot', '💨 Humid'
];

const OCCASION_OPTIONS = [
  'Work', 'Casual Day', 'Date', 'Party', 'Meeting', 
  'Travel', 'Exercise', 'Shopping', 'Special Event'
];

export const DailyInputScreen: React.FC<Props> = ({ navigation }) => {
  const [input, setInput] = useState({
    mood_today: '',
    occasion: '',
    weather: '',
    item_focus: '',
    custom_notes: '',
  });
  const [selectedImage, setSelectedImage] = useState<any>(null);
  const [wardrobeItems, setWardrobeItems] = useState<WardrobeItem[]>([]);
  const [selectedWardrobeItem, setSelectedWardrobeItem] = useState<string>('');
  const [showWardrobeModal, setShowWardrobeModal] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadWardrobeItems();
  }, []);

  const loadWardrobeItems = async () => {
    try {
      const userData = await StorageService.getUserData();
      if (userData?.id) {
        const items = await ApiService.getWardrobeItems(userData.id);
        setWardrobeItems(items);
      }
    } catch (error) {
      console.error('Error loading wardrobe items:', error);
    }
  };

  const selectImage = () => {
    launchImageLibrary(
      {
        mediaType: 'photo',
        quality: 0.8,
        maxWidth: 1000,
        maxHeight: 1000,
      },
      (response: ImagePickerResponse) => {
        if (response.assets && response.assets[0]) {
          setSelectedImage(response.assets[0]);
        }
      }
    );
  };

  const selectWardrobeItem = (itemId: string) => {
    setSelectedWardrobeItem(itemId);
    const item = wardrobeItems.find(i => i.id === itemId);
    if (item) {
      setInput(prev => ({ ...prev, item_focus: item.name }));
    }
    setShowWardrobeModal(false);
  };

  const submitDailyInput = async () => {
    if (!input.mood_today || !input.occasion || !input.weather) {
      Alert.alert('Missing Information', 'Please fill in mood, occasion, and weather');
      return;
    }

    setLoading(true);
    try {
      const userData = await StorageService.getUserData();
      
      const requestData = {
        ...input,
        user_id: userData?.id,
        image: selectedImage,
        wardrobe_item_id: selectedWardrobeItem,
      };

      const suggestion = await ApiService.submitDailyInput(requestData);
      
      navigation.navigate('StyleSuggestion', { 
        suggestion: {
          id: suggestion.id,
          user_id: userData?.id,
          content: suggestion.content,
          mood: input.mood_today,
          occasion: input.occasion,
          weather: input.weather,
          created_at: new Date().toISOString(),
        }
      });
    } catch (error) {
      Alert.alert('Error', 'Failed to generate style suggestion. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderOptionButtons = (
    options: string[], 
    selectedValue: string, 
    onSelect: (value: string) => void
  ) => (
    <View style={styles.optionsGrid}>
      {options.map((option) => (
        <TouchableOpacity
          key={option}
          style={[
            styles.optionButton,
            selectedValue === option && styles.selectedOption
          ]}
          onPress={() => onSelect(option)}
        >
          <Text style={[
            styles.optionText,
            selectedValue === option && styles.selectedOptionText
          ]}>
            {option}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );

  return (
    <SafeAreaView style={commonStyles.safeArea}>
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={commonStyles.header}>Daily Style Input</Text>
          <Text style={styles.subtitle}>
            Tell us about your day and we'll create the perfect outfit suggestion!
          </Text>
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>How are you feeling today? 💭</Text>
          {renderOptionButtons(
            MOOD_OPTIONS,
            input.mood_today,
            (mood) => setInput(prev => ({ ...prev, mood_today: mood }))
          )}
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>What's the occasion? 🎯</Text>
          {renderOptionButtons(
            OCCASION_OPTIONS,
            input.occasion,
            (occasion) => setInput(prev => ({ ...prev, occasion }))
          )}
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>What's the weather like? 🌤️</Text>
          {renderOptionButtons(
            WEATHER_OPTIONS,
            input.weather,
            (weather) => setInput(prev => ({ ...prev, weather }))
          )}
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>Focus Item (Optional) 👕</Text>
          <Text style={styles.sectionDescription}>
            Want to style around a specific piece? Choose from your wardrobe or upload a photo.
          </Text>

          <TouchableOpacity
            style={styles.focusItemButton}
            onPress={() => setShowWardrobeModal(true)}
          >
            <Text style={styles.focusItemButtonText}>
              {selectedWardrobeItem ? 
                wardrobeItems.find(i => i.id === selectedWardrobeItem)?.name || 'Select from Wardrobe'
                : 'Select from Wardrobe'
              }
            </Text>
          </TouchableOpacity>

          <Text style={styles.orText}>OR</Text>

          <TouchableOpacity onPress={selectImage} style={styles.imageUploadButton}>
            {selectedImage ? (
              <View style={styles.selectedImageContainer}>
                <Image source={{ uri: selectedImage.uri }} style={styles.selectedImage} />
                <Text style={styles.selectedImageText}>Tap to change photo</Text>
              </View>
            ) : (
              <View style={styles.imageUploadPlaceholder}>
                <Text style={styles.imageUploadText}>📷 Upload Photo of Item</Text>
              </View>
            )}
          </TouchableOpacity>

          {(selectedImage || selectedWardrobeItem) && (
            <TextInput
              style={[commonStyles.input, { marginTop: 12 }]}
              placeholder="Give this item a name (optional)"
              value={input.item_focus}
              onChangeText={(text) => setInput(prev => ({ ...prev, item_focus: text }))}
            />
          )}
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>Additional Notes (Optional) 📝</Text>
          <TextInput
            style={[commonStyles.input, styles.notesInput]}
            placeholder="Any specific requests, constraints, or details..."
            value={input.custom_notes}
            onChangeText={(text) => setInput(prev => ({ ...prev, custom_notes: text }))}
            multiline
            numberOfLines={3}
          />
        </View>

        <TouchableOpacity
          style={[commonStyles.button, styles.submitButton]}
          onPress={submitDailyInput}
          disabled={loading}
        >
          <Text style={commonStyles.buttonText}>
            {loading ? 'Creating Your Look...' : '✨ Get My Style Suggestion'}
          </Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Wardrobe Item Selection Modal */}
      <Modal 
        visible={showWardrobeModal} 
        animationType="slide" 
        presentationStyle="pageSheet"
      >
        <SafeAreaView style={commonStyles.safeArea}>
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={() => setShowWardrobeModal(false)}>
              <Text style={styles.modalClose}>Cancel</Text>
            </TouchableOpacity>
            <Text style={styles.modalTitle}>Choose Wardrobe Item</Text>
            <View style={{ width: 60 }} />
          </View>

          <ScrollView style={styles.wardrobeList}>
            {wardrobeItems.length > 0 ? (
              wardrobeItems.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={[
                    styles.wardrobeItem,
                    selectedWardrobeItem === item.id && styles.selectedWardrobeItem
                  ]}
                  onPress={() => selectWardrobeItem(item.id)}
                >
                  <View style={styles.wardrobeItemInfo}>
                    <Text style={styles.wardrobeItemName}>{item.name}</Text>
                    <Text style={styles.wardrobeItemDetails}>
                      {item.category} {item.color ? `• ${item.color}` : ''}
                    </Text>
                  </View>
                  {item.is_favorite && <Text>⭐</Text>}
                </TouchableOpacity>
              ))
            ) : (
              <View style={styles.emptyWardrobe}>
                <Text style={styles.emptyText}>No wardrobe items found</Text>
                <TouchableOpacity
                  onPress={() => {
                    setShowWardrobeModal(false);
                    navigation.navigate('Wardrobe');
                  }}
                  style={commonStyles.button}
                >
                  <Text style={commonStyles.buttonText}>Add Items to Wardrobe</Text>
                </TouchableOpacity>
              </View>
            )}
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
    marginBottom: 24,
  },
  subtitle: {
    fontSize: 16,
    color: colors.textSecondary,
    lineHeight: 24,
    marginTop: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  sectionDescription: {
    fontSize: 14,
    color: colors.textSecondary,
    marginBottom: 16,
    lineHeight: 20,
  },
  optionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  optionButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 4,
  },
  selectedOption: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  optionText: {
    fontSize: 14,
    color: colors.text,
  },
  selectedOptionText: {
    color: colors.surface,
    fontWeight: '500',
  },
  focusItemButton: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 12,
  },
  focusItemButtonText: {
    fontSize: 16,
    color: colors.text,
  },
  orText: {
    textAlign: 'center',
    fontSize: 14,
    color: colors.textSecondary,
    marginVertical: 8,
  },
  imageUploadButton: {
    borderRadius: 8,
    overflow: 'hidden',
  },
  imageUploadPlaceholder: {
    height: 120,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: colors.border,
    borderStyle: 'dashed',
  },
  imageUploadText: {
    color: colors.textSecondary,
    fontSize: 16,
  },
  selectedImageContainer: {
    alignItems: 'center',
  },
  selectedImage: {
    width: '100%',
    height: 200,
  },
  selectedImageText: {
    marginTop: 8,
    fontSize: 14,
    color: colors.textSecondary,
  },
  notesInput: {
    height: 80,
    textAlignVertical: 'top',
  },
  submitButton: {
    marginVertical: 24,
    paddingVertical: 16,
  },
  // Modal styles
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
  wardrobeList: {
    flex: 1,
    padding: 16,
  },
  wardrobeItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: colors.surface,
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  selectedWardrobeItem: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  wardrobeItemInfo: {
    flex: 1,
  },
  wardrobeItemName: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
  },
  wardrobeItemDetails: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 2,
  },
  emptyWardrobe: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    color: colors.textSecondary,
    marginBottom: 20,
  },
});
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
} from 'react-native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList, UserStyleProfile } from '../types';
import { colors } from '../constants/colors';
import { commonStyles } from '../constants/styles';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';

type ProfileScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'Profile'
>;

interface Props {
  navigation: ProfileScreenNavigationProp;
}

const SKIN_TONE_OPTIONS = ['Fair', 'Light', 'Medium', 'Tan', 'Deep'];
const UNDERTONE_OPTIONS = ['Cool', 'Warm', 'Neutral'];
const CONTRAST_OPTIONS = ['Low', 'Medium', 'High'];
const FORMALITY_OPTIONS = ['Casual', 'Business Casual', 'Professional', 'Formal'];

export const ProfileScreen: React.FC<Props> = ({ navigation }) => {
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<Partial<UserStyleProfile>>({
    appearance: {
      skin_tone: '',
      undertone: '',
      contrast_level: '',
    },
    style_identity: {
      face_detail_preference: '',
      texture_notes: '',
      color_pref: '',
      style_constraints: '',
      archetypes: [],
      aspirational_style: '',
    },
    lifestyle: {
      mobility: '',
      climate: '',
      life_event: '',
      dress_formality: '',
      wardrobe_phase: '',
      shopping_behavior: '',
      budget_preference: '',
    },
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const userData = await StorageService.getUserData();
      if (userData?.id) {
        const existingProfile = await ApiService.getUserProfile(userData.id);
        if (existingProfile) {
          setProfile(existingProfile);
        }
      }
    } catch (error) {
      console.log('No existing profile found');
    }
  };

  const updateProfile = (section: string, field: string, value: string) => {
    setProfile(prev => ({
      ...prev,
      [section]: {
        ...prev[section as keyof UserStyleProfile],
        [field]: value,
      },
    }));
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const userData = await StorageService.getUserData();
      const profileData = {
        ...profile,
        user_id: userData?.id || userData?.email,
      };

      if (profile.user_id) {
        await ApiService.updateUserProfile(profileData.user_id, profileData);
      } else {
        await ApiService.createUserProfile(profileData);
      }

      Alert.alert('Success', 'Profile saved successfully!', [
        { text: 'OK', onPress: () => navigation.navigate('Dashboard') }
      ]);
    } catch (error) {
      Alert.alert('Error', 'Failed to save profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderPicker = (
    title: string,
    options: string[],
    section: string,
    field: string,
    value: string
  ) => (
    <View style={styles.pickerContainer}>
      <Text style={styles.label}>{title}</Text>
      <View style={styles.optionsContainer}>
        {options.map((option) => (
          <TouchableOpacity
            key={option}
            style={[
              styles.option,
              value === option && styles.selectedOption
            ]}
            onPress={() => updateProfile(section, field, option)}
          >
            <Text style={[
              styles.optionText,
              value === option && styles.selectedOptionText
            ]}>
              {option}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={commonStyles.safeArea}>
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={commonStyles.header}>Style Profile</Text>
          <Text style={styles.subtitle}>
            Help us understand your style preferences to give you personalized suggestions
          </Text>
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>Appearance</Text>
          
          {renderPicker(
            'Skin Tone',
            SKIN_TONE_OPTIONS,
            'appearance',
            'skin_tone',
            profile.appearance?.skin_tone || ''
          )}

          {renderPicker(
            'Undertone',
            UNDERTONE_OPTIONS,
            'appearance',
            'undertone',
            profile.appearance?.undertone || ''
          )}

          {renderPicker(
            'Contrast Level',
            CONTRAST_OPTIONS,
            'appearance',
            'contrast_level',
            profile.appearance?.contrast_level || ''
          )}
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>Style Preferences</Text>
          
          <View style={styles.inputContainer}>
            <Text style={styles.label}>Color Preferences</Text>
            <TextInput
              style={commonStyles.input}
              placeholder="e.g., Blues, earth tones, jewel colors..."
              value={profile.style_identity?.color_pref || ''}
              onChangeText={(text) => updateProfile('style_identity', 'color_pref', text)}
              multiline
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>Aspirational Style</Text>
            <TextInput
              style={commonStyles.input}
              placeholder="How would you like to be perceived? What's your style goal?"
              value={profile.style_identity?.aspirational_style || ''}
              onChangeText={(text) => updateProfile('style_identity', 'aspirational_style', text)}
              multiline
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>Style Constraints</Text>
            <TextInput
              style={commonStyles.input}
              placeholder="Any limitations or things to avoid..."
              value={profile.style_identity?.style_constraints || ''}
              onChangeText={(text) => updateProfile('style_identity', 'style_constraints', text)}
              multiline
            />
          </View>
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>Lifestyle</Text>
          
          {renderPicker(
            'Dress Formality',
            FORMALITY_OPTIONS,
            'lifestyle',
            'dress_formality',
            profile.lifestyle?.dress_formality || ''
          )}

          <View style={styles.inputContainer}>
            <Text style={styles.label}>Climate</Text>
            <TextInput
              style={commonStyles.input}
              placeholder="Describe your typical weather/climate..."
              value={profile.lifestyle?.climate || ''}
              onChangeText={(text) => updateProfile('lifestyle', 'climate', text)}
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>Mobility & Activity Level</Text>
            <TextInput
              style={commonStyles.input}
              placeholder="How active are you? Any mobility considerations?"
              value={profile.lifestyle?.mobility || ''}
              onChangeText={(text) => updateProfile('lifestyle', 'mobility', text)}
              multiline
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.label}>Budget Preference</Text>
            <TextInput
              style={commonStyles.input}
              placeholder="Your approach to clothing budget..."
              value={profile.lifestyle?.budget_preference || ''}
              onChangeText={(text) => updateProfile('lifestyle', 'budget_preference', text)}
            />
          </View>
        </View>

        <TouchableOpacity
          style={[commonStyles.button, styles.saveButton]}
          onPress={handleSave}
          disabled={loading}
        >
          <Text style={commonStyles.buttonText}>
            {loading ? 'Saving...' : 'Save Profile'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
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
    marginBottom: 16,
  },
  pickerContainer: {
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
    marginBottom: 8,
  },
  optionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  option: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
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
  inputContainer: {
    marginBottom: 16,
  },
  saveButton: {
    marginVertical: 24,
  },
});
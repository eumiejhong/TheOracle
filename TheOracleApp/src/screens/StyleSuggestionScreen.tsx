import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  Share,
  TextInput,
} from 'react-native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../types';
import { colors } from '../constants/colors';
import { commonStyles } from '../constants/styles';
import { ApiService } from '../services/api';

type StyleSuggestionScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'StyleSuggestion'
>;

type StyleSuggestionScreenRouteProp = RouteProp<
  RootStackParamList,
  'StyleSuggestion'
>;

interface Props {
  navigation: StyleSuggestionScreenNavigationProp;
  route: StyleSuggestionScreenRouteProp;
}

const FEEDBACK_OPTIONS = [
  { key: 'loved', label: '❤️ Loved it!', description: 'This is perfect for me' },
  { key: 'meh', label: '🤷‍♀️ Meh', description: 'It\'s okay, but not quite right' },
  { key: 'dislike', label: '👎 Not my vibe', description: 'This doesn\'t suit me at all' },
];

export const StyleSuggestionScreen: React.FC<Props> = ({ navigation, route }) => {
  const { suggestion } = route.params;
  const [selectedFeedback, setSelectedFeedback] = useState('');
  const [feedbackComment, setFeedbackComment] = useState('');
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const handleShare = async () => {
    try {
      await Share.share({
        message: `Check out my style suggestion from The Oracle:\n\n${suggestion.content}`,
        title: 'My Style Suggestion',
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const submitFeedback = async () => {
    if (!selectedFeedback) {
      Alert.alert('Feedback Required', 'Please select how you feel about this suggestion');
      return;
    }

    try {
      await ApiService.submitFeedback(suggestion.id, {
        rating: selectedFeedback,
        comment: feedbackComment.trim(),
      });

      setFeedbackSubmitted(true);
      setShowFeedbackForm(false);
      
      Alert.alert(
        'Thank You!',
        'Your feedback helps us improve our suggestions for you.',
        [{ text: 'OK' }]
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to submit feedback. Please try again.');
    }
  };

  const getContextInfo = () => {
    const info = [];
    if (suggestion.mood) info.push(`Mood: ${suggestion.mood}`);
    if (suggestion.occasion) info.push(`Occasion: ${suggestion.occasion}`);
    if (suggestion.weather) info.push(`Weather: ${suggestion.weather}`);
    return info;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <SafeAreaView style={commonStyles.safeArea}>
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Your Style Suggestion ✨</Text>
          <Text style={styles.date}>
            Generated on {formatDate(suggestion.created_at)}
          </Text>
        </View>

        {/* Context Information */}
        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>Context</Text>
          <View style={styles.contextContainer}>
            {getContextInfo().map((info, index) => (
              <View key={index} style={styles.contextItem}>
                <Text style={styles.contextText}>{info}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Main Suggestion */}
        <View style={[commonStyles.card, styles.suggestionCard]}>
          <Text style={styles.sectionTitle}>Your Personalized Look</Text>
          <Text style={styles.suggestionContent}>{suggestion.content}</Text>
        </View>

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.actionButton, styles.shareButton]}
            onPress={handleShare}
          >
            <Text style={styles.shareButtonText}>📤 Share</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionButton, styles.feedbackButton]}
            onPress={() => setShowFeedbackForm(true)}
            disabled={feedbackSubmitted}
          >
            <Text style={styles.feedbackButtonText}>
              {feedbackSubmitted ? '✓ Feedback Sent' : '💭 Give Feedback'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Quick Actions */}
        <View style={commonStyles.card}>
          <Text style={styles.sectionTitle}>What's Next?</Text>
          
          <TouchableOpacity
            style={styles.quickAction}
            onPress={() => navigation.navigate('DailyInput')}
          >
            <View style={styles.quickActionContent}>
              <Text style={styles.quickActionIcon}>🎯</Text>
              <View style={styles.quickActionText}>
                <Text style={styles.quickActionTitle}>Get Another Suggestion</Text>
                <Text style={styles.quickActionDescription}>
                  Try different mood, occasion, or weather
                </Text>
              </View>
            </View>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.quickAction}
            onPress={() => navigation.navigate('Wardrobe')}
          >
            <View style={styles.quickActionContent}>
              <Text style={styles.quickActionIcon}>👕</Text>
              <View style={styles.quickActionText}>
                <Text style={styles.quickActionTitle}>Browse Wardrobe</Text>
                <Text style={styles.quickActionDescription}>
                  Add new items or manage existing ones
                </Text>
              </View>
            </View>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.quickAction}
            onPress={() => navigation.navigate('Dashboard')}
          >
            <View style={styles.quickActionContent}>
              <Text style={styles.quickActionIcon}>🏠</Text>
              <View style={styles.quickActionText}>
                <Text style={styles.quickActionTitle}>Back to Dashboard</Text>
                <Text style={styles.quickActionDescription}>
                  See your recent activity and suggestions
                </Text>
              </View>
            </View>
          </TouchableOpacity>
        </View>

        {/* Feedback Form Modal-like Section */}
        {showFeedbackForm && (
          <View style={[commonStyles.card, styles.feedbackForm]}>
            <Text style={styles.sectionTitle}>How do you feel about this suggestion?</Text>
            
            <View style={styles.feedbackOptions}>
              {FEEDBACK_OPTIONS.map((option) => (
                <TouchableOpacity
                  key={option.key}
                  style={[
                    styles.feedbackOption,
                    selectedFeedback === option.key && styles.selectedFeedbackOption
                  ]}
                  onPress={() => setSelectedFeedback(option.key)}
                >
                  <Text style={[
                    styles.feedbackOptionLabel,
                    selectedFeedback === option.key && styles.selectedFeedbackText
                  ]}>
                    {option.label}
                  </Text>
                  <Text style={[
                    styles.feedbackOptionDescription,
                    selectedFeedback === option.key && styles.selectedFeedbackText
                  ]}>
                    {option.description}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.commentSection}>
              <Text style={styles.commentLabel}>Additional comments (optional):</Text>
              <TextInput
                style={[commonStyles.input, styles.commentInput]}
                placeholder="Tell us more about what you liked or didn't like..."
                value={feedbackComment}
                onChangeText={setFeedbackComment}
                multiline
                numberOfLines={3}
              />
            </View>

            <View style={styles.feedbackActions}>
              <TouchableOpacity
                style={[styles.feedbackActionButton, styles.cancelButton]}
                onPress={() => {
                  setShowFeedbackForm(false);
                  setSelectedFeedback('');
                  setFeedbackComment('');
                }}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.feedbackActionButton, styles.submitButton]}
                onPress={submitFeedback}
              >
                <Text style={styles.submitButtonText}>Submit Feedback</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
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
    alignItems: 'center',
    marginBottom: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    textAlign: 'center',
  },
  date: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 4,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  contextContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  contextItem: {
    backgroundColor: colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  contextText: {
    color: colors.surface,
    fontSize: 14,
    fontWeight: '500',
  },
  suggestionCard: {
    backgroundColor: colors.background,
    borderWidth: 2,
    borderColor: colors.primary,
  },
  suggestionContent: {
    fontSize: 16,
    lineHeight: 26,
    color: colors.text,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
    marginVertical: 16,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  shareButton: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  shareButtonText: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  feedbackButton: {
    backgroundColor: colors.primary,
  },
  feedbackButtonText: {
    color: colors.surface,
    fontSize: 16,
    fontWeight: '600',
  },
  quickAction: {
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  quickActionContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  quickActionIcon: {
    fontSize: 24,
    marginRight: 16,
  },
  quickActionText: {
    flex: 1,
  },
  quickActionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  quickActionDescription: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  // Feedback Form Styles
  feedbackForm: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primary,
    marginTop: 16,
  },
  feedbackOptions: {
    marginBottom: 16,
  },
  feedbackOption: {
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: 8,
  },
  selectedFeedbackOption: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  feedbackOptionLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 4,
  },
  feedbackOptionDescription: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  selectedFeedbackText: {
    color: colors.surface,
  },
  commentSection: {
    marginBottom: 16,
  },
  commentLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
    marginBottom: 8,
  },
  commentInput: {
    height: 80,
    textAlignVertical: 'top',
  },
  feedbackActions: {
    flexDirection: 'row',
    gap: 12,
  },
  feedbackActionButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cancelButtonText: {
    color: colors.textSecondary,
    fontSize: 16,
  },
  submitButton: {
    backgroundColor: colors.primary,
  },
  submitButtonText: {
    color: colors.surface,
    fontSize: 16,
    fontWeight: '600',
  },
});
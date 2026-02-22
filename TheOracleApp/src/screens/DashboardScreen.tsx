import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  RefreshControl,
  Alert,
} from 'react-native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList, WardrobeItem, StylingSuggestion } from '../types';
import { colors } from '../constants/colors';
import { commonStyles } from '../constants/styles';
import { ApiService } from '../services/api';
import { StorageService } from '../services/storage';

type DashboardScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'Dashboard'
>;

interface Props {
  navigation: DashboardScreenNavigationProp;
}

export const DashboardScreen: React.FC<Props> = ({ navigation }) => {
  const [user, setUser] = useState<any>(null);
  const [recentItems, setRecentItems] = useState<WardrobeItem[]>([]);
  const [todaySuggestion, setTodaySuggestion] = useState<StylingSuggestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboardData = async () => {
    try {
      const userData = await StorageService.getUserData();
      setUser(userData);

      if (userData?.id) {
        const [wardrobeData, suggestionsData] = await Promise.all([
          ApiService.getWardrobeItems(userData.id),
          ApiService.getStylingSuggestions(userData.id)
        ]);

        setRecentItems(wardrobeData.slice(0, 5)); // Show 5 most recent items
        setTodaySuggestion(suggestionsData[0] || null); // Most recent suggestion
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

  const handleLogout = async () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await StorageService.clear();
            ApiService.clearToken();
            navigation.navigate('Login');
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={commonStyles.centerContent}>
        <Text>Loading...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={commonStyles.safeArea}>
      <ScrollView 
        style={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Hello, {user?.email?.split('@')[0] || 'there'}! 👋</Text>
            <Text style={styles.subGreeting}>Ready to look amazing today?</Text>
          </View>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
            <Text style={styles.logoutText}>Logout</Text>
          </TouchableOpacity>
        </View>

        {todaySuggestion && (
          <View style={[commonStyles.card, styles.suggestionCard]}>
            <Text style={styles.cardTitle}>Today's Style Suggestion ✨</Text>
            <Text style={styles.suggestionText} numberOfLines={3}>
              {todaySuggestion.content}
            </Text>
            <TouchableOpacity 
              style={styles.viewMoreButton}
              onPress={() => navigation.navigate('StyleSuggestion', { suggestion: todaySuggestion })}
            >
              <Text style={styles.viewMoreText}>View Details</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.actionButton, styles.primaryAction]}
            onPress={() => navigation.navigate('DailyInput')}
          >
            <Text style={styles.actionButtonText}>Get Style Advice</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionButton, styles.secondaryAction]}
            onPress={() => navigation.navigate('Wardrobe')}
          >
            <Text style={[styles.actionButtonText, styles.secondaryText]}>Manage Wardrobe</Text>
          </TouchableOpacity>
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.cardTitle}>Recent Wardrobe Items</Text>
          {recentItems.length > 0 ? (
            recentItems.map((item, index) => (
              <View key={item.id} style={styles.wardrobeItem}>
                <View style={styles.itemInfo}>
                  <Text style={styles.itemName}>{item.name}</Text>
                  <Text style={styles.itemCategory}>{item.category}</Text>
                </View>
                {item.is_favorite && <Text style={styles.favoriteIcon}>⭐</Text>}
              </View>
            ))
          ) : (
            <Text style={styles.emptyText}>No wardrobe items yet. Add some to get started!</Text>
          )}
          
          <TouchableOpacity
            style={styles.viewAllButton}
            onPress={() => navigation.navigate('Wardrobe')}
          >
            <Text style={styles.viewAllText}>View All Items →</Text>
          </TouchableOpacity>
        </View>

        <View style={commonStyles.card}>
          <Text style={styles.cardTitle}>Quick Actions</Text>
          <TouchableOpacity
            style={styles.quickAction}
            onPress={() => navigation.navigate('Profile')}
          >
            <Text style={styles.quickActionText}>Update Style Profile</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.quickAction}
            onPress={() => navigation.navigate('DailyInput')}
          >
            <Text style={styles.quickActionText}>What should I wear today?</Text>
          </TouchableOpacity>
        </View>
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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 24,
  },
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 4,
  },
  subGreeting: {
    fontSize: 16,
    color: colors.textSecondary,
  },
  logoutButton: {
    padding: 8,
  },
  logoutText: {
    color: colors.error,
    fontSize: 16,
  },
  suggestionCard: {
    backgroundColor: colors.primary,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  suggestionText: {
    fontSize: 16,
    color: colors.surface,
    lineHeight: 24,
    marginBottom: 12,
  },
  viewMoreButton: {
    alignSelf: 'flex-start',
  },
  viewMoreText: {
    color: colors.surface,
    fontSize: 16,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  actionButtons: {
    flexDirection: 'row',
    marginBottom: 24,
    gap: 12,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderRadius: 12,
    alignItems: 'center',
  },
  primaryAction: {
    backgroundColor: colors.primary,
  },
  secondaryAction: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.primary,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.surface,
  },
  secondaryText: {
    color: colors.primary,
  },
  wardrobeItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
  },
  itemCategory: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  favoriteIcon: {
    fontSize: 16,
  },
  emptyText: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
    paddingVertical: 20,
  },
  viewAllButton: {
    alignSelf: 'flex-end',
    marginTop: 12,
  },
  viewAllText: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  quickAction: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  quickActionText: {
    fontSize: 16,
    color: colors.text,
  },
});
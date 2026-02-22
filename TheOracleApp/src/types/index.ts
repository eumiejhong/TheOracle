export interface UserStyleProfile {
  user_id: string;
  appearance: {
    skin_tone: string;
    contrast_level: string;
    undertone: string;
  };
  style_identity: {
    face_detail_preference: string;
    texture_notes: string;
    color_pref: string;
    style_constraints: string;
    archetypes: string[];
    aspirational_style: string;
  };
  lifestyle: {
    mobility: string;
    climate: string;
    life_event: string;
    dress_formality: string;
    wardrobe_phase: string;
    shopping_behavior: string;
    budget_preference: string;
  };
  style_archetype?: string;
  created_at: string;
}

export interface WardrobeItem {
  id: string;
  user_id: string;
  name: string;
  category: string;
  color?: string;
  style_tags?: string[];
  image?: string;
  added_at: string;
  last_used?: string;
  season: 'spring' | 'summer' | 'fall' | 'winter' | 'all';
  is_favorite: boolean;
}

export interface DailyStyleInput {
  id: string;
  user_profile_id: string;
  mood_today: string;
  occasion: string;
  weather: string;
  item_focus: string;
  outfit_suggestion?: string;
  image_description?: string;
  created_at: string;
}

export interface StylingSuggestion {
  id: string;
  user_id: string;
  content: string;
  mood?: string;
  occasion?: string;
  weather?: string;
  created_at: string;
}

export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  Dashboard: undefined;
  Profile: undefined;
  Wardrobe: undefined;
  DailyInput: undefined;
  StyleSuggestion: { suggestion: StylingSuggestion };
};
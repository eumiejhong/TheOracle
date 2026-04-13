import React, { useState, useCallback } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import * as SecureStore from "expo-secure-store";
import { colors, fonts, spacing } from "../theme";
import { getProfile, saveProfile } from "../api";

const SECTIONS = [
  {
    title: "Appearance",
    fields: [
      {
        key: "skin_tone", label: "How would you describe your skin tone?",
        type: "radio",
        options: ["Fair or light", "Medium or olive", "Deep or dark", "I'm not sure"],
      },
      {
        key: "contrast_level", label: "How would you describe the contrast between your features?",
        type: "radio",
        options: [
          "Low contrast — light hair + fair skin",
          "Medium contrast — some difference, not sharp",
          "High contrast — dark hair + pale skin",
          "I'm not sure",
        ],
      },
      {
        key: "undertone", label: "Do you lean warmer or cooler in tone?",
        type: "radio",
        options: ["Warm — golden, peachy", "Cool — pink, bluish", "Neutral — a bit of both", "I'm not sure"],
      },
    ],
  },
  {
    title: "Style Identity",
    fields: [
      {
        key: "face_detail_preference", label: "Do you prefer softer or more structured details near your face?",
        type: "radio",
        options: [
          "Soft, round, or organic shapes",
          "Structured, angular, or graphic lines",
          "A mix — I go by outfit",
          "I'm not sure",
        ],
      },
      {
        key: "archetypes", label: "Which style archetypes feel most like you?",
        type: "radio",
        options: [
          "Quiet Minimalism", "Romantic Tailored", "Soft Sculptural",
          "90s Sharpness", "Boyish Luxe", "Earthy Artisanal",
          "Sleek + Functional", "I'm not sure",
        ],
      },
      {
        key: "texture_notes", label: "What silhouettes or fabrics make you feel most like yourself?",
        type: "text", placeholder: "e.g., Structured shoulders but soft drape, knits that skim but don't cling...",
      },
      {
        key: "color_pref", label: "What are your favorite colors to wear?",
        type: "text", placeholder: "e.g., Jewel tones, muted blue, baby pink...",
      },
      {
        key: "style_constraints", label: "Anything you never wear?",
        type: "text", placeholder: "e.g., Bodycon, loud prints, synthetics...",
      },
      {
        key: "aspirational_style", label: "Describe your style vision in your own words",
        type: "text", placeholder: "e.g., A mix of sharp tailoring and soft romance...",
      },
    ],
  },
  {
    title: "Lifestyle",
    fields: [
      {
        key: "life_event", label: "Are you in a life transition?",
        type: "text", placeholder: "e.g., Just moved, started a new role, navigating a breakup...",
      },
      {
        key: "mobility", label: "How do you usually move through your day?",
        type: "radio",
        options: [
          "I bike often", "I walk a lot", "I drive or use rideshare",
          "I mostly stay home or work remotely",
          "I use mobility aids or need accessible styles",
          "My energy levels vary a lot day to day",
        ],
      },
      {
        key: "climate_wear", label: "What's the climate you usually dress for?",
        type: "radio",
        options: ["Warm year-round", "Mostly cold", "Transitional / layered seasons", "I travel between climates often"],
      },
      {
        key: "dress_formality", label: "How formal is your day-to-day style?",
        type: "radio",
        options: ["Very casual", "Elevated casual", "Creative professional", "Tailored / business"],
      },
      {
        key: "wardrobe_phase", label: "How would you describe your wardrobe right now?",
        type: "radio",
        options: [
          "Overflowing — I need to refine",
          "Small but scattered — I need direction",
          "Building a new look from scratch",
          "Minimal — I love owning less",
        ],
      },
      {
        key: "shopping_behavior", label: "How do you usually shop?",
        type: "radio",
        options: [
          "Mostly secondhand or vintage",
          "A few investment pieces each year",
          "I refresh seasonally",
          "Not buying — just want styling support",
        ],
      },
      {
        key: "budget_preference", label: "What's your comfort zone for spending on a single item?",
        type: "radio",
        options: [
          "Under $50 — thrift or affordable",
          "$50–$150 — mid-range and secondhand",
          "$150–$500 — quality staples",
          "$500+ — designer or archival",
          "Not buying right now",
        ],
      },
    ],
  },
];

function flattenProfile(profile) {
  if (!profile) return {};
  const a = profile.appearance || {};
  const s = profile.style_identity || {};
  const l = profile.lifestyle || {};
  return {
    skin_tone: a.skin_tone || "",
    contrast_level: a.contrast_level || "",
    undertone: a.undertone || "",
    face_detail_preference: s.face_detail_preference || "",
    archetypes: s.archetypes || "",
    texture_notes: s.texture_notes || "",
    color_pref: s.color_pref || "",
    style_constraints: s.style_constraints || "",
    aspirational_style: s.aspirational_style || "",
    life_event: l.life_event || "",
    mobility: l.mobility || "",
    climate_wear: l.climate_wear || "",
    dress_formality: l.dress_formality || "",
    wardrobe_phase: l.wardrobe_phase || "",
    shopping_behavior: l.shopping_behavior || "",
    budget_preference: l.budget_preference || "",
  };
}

export default function ProfileScreen({ navigation }) {
  const [profile, setProfile] = useState(null);
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useFocusEffect(
    useCallback(() => {
      getProfile()
        .then((d) => {
          setProfile(d.profile);
          setValues(flattenProfile(d.profile));
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }, [])
  );

  function set(key, val) {
    setValues((prev) => ({ ...prev, [key]: val }));
  }

  async function handleSave() {
    setSaving(true);
    try {
      await saveProfile({
        appearance: {
          skin_tone: values.skin_tone, undertone: values.undertone,
          contrast_level: values.contrast_level,
        },
        style_identity: {
          archetypes: values.archetypes, texture_notes: values.texture_notes,
          color_pref: values.color_pref, style_constraints: values.style_constraints,
          face_detail_preference: values.face_detail_preference,
          aspirational_style: values.aspirational_style,
        },
        lifestyle: {
          life_event: values.life_event, mobility: values.mobility,
          climate: values.climate_wear, climate_wear: values.climate_wear,
          dress_formality: values.dress_formality,
          wardrobe_phase: values.wardrobe_phase,
          shopping_behavior: values.shopping_behavior,
          budget_preference: values.budget_preference,
        },
      });
      Alert.alert("Saved", "Your style profile has been updated.");
    } catch {
      Alert.alert("Error", "Could not save profile.");
    } finally {
      setSaving(false);
    }
  }

  async function handleLogout() {
    await SecureStore.deleteItemAsync("access_token");
    await SecureStore.deleteItemAsync("refresh_token");
    navigation.reset({ index: 0, routes: [{ name: "Tabs" }] });
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Tell me about yourself.</Text>
      <Text style={styles.subheading}>
        The Oracle reads between the lines. Be honest about your contradictions.
      </Text>

      {profile?.style_archetype && (
        <View style={styles.archetypeCard}>
          <Text style={styles.archetypeLabel}>Your Style Archetype</Text>
          <Text style={styles.archetypeText}>{profile.style_archetype}</Text>
        </View>
      )}

      {SECTIONS.map((section) => (
        <View key={section.title} style={styles.section}>
          <Text style={styles.sectionTitle}>{section.title}</Text>
          {section.fields.map((field) => (
            <View key={field.key} style={styles.fieldGroup}>
              <Text style={styles.question}>{field.label}</Text>
              {field.type === "radio" ? (
                <View style={styles.radioGroup}>
                  {field.options.map((opt) => (
                    <TouchableOpacity
                      key={opt}
                      style={[styles.radioOption, values[field.key] === opt && styles.radioSelected]}
                      onPress={() => set(field.key, opt)}
                    >
                      <View style={[styles.radioDot, values[field.key] === opt && styles.radioDotActive]} />
                      <Text style={[styles.radioLabel, values[field.key] === opt && styles.radioLabelActive]}>
                        {opt}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              ) : (
                <TextInput
                  style={styles.textArea}
                  placeholder={field.placeholder}
                  placeholderTextColor={colors.textMuted}
                  value={values[field.key] || ""}
                  onChangeText={(t) => set(field.key, t)}
                  multiline
                  numberOfLines={3}
                />
              )}
            </View>
          ))}
        </View>
      ))}

      <TouchableOpacity style={styles.saveBtn} onPress={handleSave} disabled={saving}>
        {saving ? (
          <ActivityIndicator color={colors.white} />
        ) : (
          <Text style={styles.saveBtnText}>Save Profile</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>

      <View style={{ height: 50 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  content: { padding: spacing.lg, paddingTop: spacing.xxl + 20 },
  center: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: colors.bgPrimary },
  heading: { fontFamily: fonts.display, fontSize: 28, color: colors.textPrimary, marginBottom: spacing.xs },
  subheading: { fontFamily: fonts.body, fontSize: 14, color: colors.textMuted, marginBottom: spacing.lg, lineHeight: 20 },
  archetypeCard: { backgroundColor: colors.bgSecondary, borderRadius: 8, padding: spacing.md, marginBottom: spacing.lg },
  archetypeLabel: { fontFamily: fonts.display, fontSize: 14, color: colors.textMuted, marginBottom: spacing.xs },
  archetypeText: { fontFamily: fonts.body, fontSize: 13, color: colors.textSecondary, lineHeight: 20 },
  section: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing.lg, marginTop: spacing.lg },
  sectionTitle: { fontFamily: fonts.display, fontSize: 22, color: colors.textPrimary, marginBottom: spacing.md },
  fieldGroup: { marginBottom: spacing.lg },
  question: { fontFamily: fonts.body, fontSize: 15, color: colors.textPrimary, marginBottom: spacing.sm },
  radioGroup: { gap: spacing.xs },
  radioOption: {
    flexDirection: "row", alignItems: "center", gap: 12,
    paddingVertical: 12, paddingHorizontal: spacing.md,
    backgroundColor: colors.bgSecondary, marginBottom: 4,
  },
  radioSelected: { backgroundColor: colors.accent },
  radioDot: { width: 18, height: 18, borderRadius: 9, borderWidth: 2, borderColor: colors.textMuted },
  radioDotActive: { borderColor: colors.white, backgroundColor: colors.white },
  radioLabel: { fontFamily: fonts.body, fontSize: 14, color: colors.textPrimary, flex: 1 },
  radioLabelActive: { color: colors.white },
  textArea: {
    backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border,
    padding: spacing.md, fontFamily: fonts.body, fontSize: 15, color: colors.textPrimary,
    minHeight: 80, textAlignVertical: "top",
  },
  saveBtn: {
    backgroundColor: colors.accent, paddingVertical: 16, alignItems: "center",
    marginTop: spacing.xl,
  },
  saveBtnText: { color: colors.white, fontSize: 16, fontFamily: fonts.body, fontWeight: "600" },
  logoutBtn: { alignItems: "center", marginTop: spacing.lg, paddingVertical: spacing.md },
  logoutText: { fontFamily: fonts.body, fontSize: 14, color: colors.verdictSkip },
});

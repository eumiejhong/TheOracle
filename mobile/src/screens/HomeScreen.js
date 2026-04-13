import React, { useState, useCallback } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, KeyboardAvoidingView, Platform,
  Image, Alert,
} from "react-native";
import { useFocusEffect, useNavigation } from "@react-navigation/native";
import * as ImagePicker from "expo-image-picker";
import { colors, fonts, spacing } from "../theme";
import { getProfile, getWardrobe, submitDailyInput } from "../api";

const OCCASIONS = [
  "Work day", "Date or social event", "Creative time",
  "Errands or casual day", "Travel", "Relaxing / staying in", "Other",
];
const WEATHER = [
  "Cold and damp", "Cold and dry", "Warm and sunny",
  "Hot and humid", "Transitional / layered", "Unpredictable", "Not sure",
];

export default function HomeScreen() {
  const nav = useNavigation();
  const [profile, setProfile] = useState(null);
  const [wardrobeItems, setWardrobeItems] = useState([]);
  const [mood, setMood] = useState("");
  const [occasion, setOccasion] = useState("");
  const [weather, setWeather] = useState("");
  const [addNewItem, setAddNewItem] = useState(false);
  const [itemFocus, setItemFocus] = useState("");
  const [itemImage, setItemImage] = useState(null);
  const [selectedWardrobe, setSelectedWardrobe] = useState(null);
  const [loading, setLoading] = useState(false);

  useFocusEffect(
    useCallback(() => {
      getProfile().then((d) => setProfile(d.profile)).catch(() => {});
      getWardrobe().then((d) => setWardrobeItems(d.items || [])).catch(() => {});
    }, [])
  );

  async function pickImage() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7,
    });
    if (!result.canceled) setItemImage(result.assets[0]);
  }

  async function handleSubmit() {
    if (!occasion || !weather) return;
    setLoading(true);
    try {
      let body;
      if (itemImage && addNewItem) {
        const formData = new FormData();
        formData.append("mood_today", mood || "");
        formData.append("occasion", occasion);
        formData.append("weather", weather);
        formData.append("item_focus", itemFocus || "");
        formData.append("image_name_hint", itemFocus || "Uploaded Item");
        if (selectedWardrobe) formData.append("wardrobe_item_id", String(selectedWardrobe));
        formData.append("image", {
          uri: itemImage.uri,
          type: "image/jpeg",
          name: "focus_item.jpg",
        });
        body = formData;
      } else {
        body = JSON.stringify({
          mood_today: mood || "",
          occasion,
          weather,
          item_focus: itemFocus || "",
          ...(selectedWardrobe ? { wardrobe_item_id: selectedWardrobe } : {}),
        });
      }
      const result = await submitDailyInput(body);
      if (result.error) {
        Alert.alert("Error", result.error);
      } else {
        nav.navigate("OutfitResult", { suggestion: result.outfit_suggestion });
      }
    } catch (e) {
      Alert.alert("Error", "Could not generate outfit suggestion.");
    } finally {
      setLoading(false);
    }
  }

  if (!profile) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>Welcome to The Oracle</Text>
        <Text style={styles.emptyText}>Create your style profile first.</Text>
        <TouchableOpacity style={styles.primaryBtn} onPress={() => nav.navigate("Me")}>
          <Text style={styles.primaryBtnText}>Create Profile</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <Text style={styles.eyebrow}>Daily Session</Text>
        <Text style={styles.title}>What does today ask of you?</Text>

        <Text style={styles.label}>Mood</Text>
        <Text style={styles.hint}>How do you want to feel today?</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g., Confident but effortless, soft and protected..."
          placeholderTextColor={colors.textMuted}
          value={mood}
          onChangeText={setMood}
        />

        <Text style={styles.label}>Occasion</Text>
        <Text style={styles.hint}>What's the context?</Text>
        {OCCASIONS.map((o) => (
          <TouchableOpacity
            key={o}
            style={[styles.radioOption, occasion === o && styles.radioSelected]}
            onPress={() => setOccasion(o)}
          >
            <View style={[styles.radioDot, occasion === o && styles.radioDotActive]} />
            <Text style={[styles.radioLabel, occasion === o && styles.radioLabelActive]}>{o}</Text>
          </TouchableOpacity>
        ))}

        <Text style={[styles.label, { marginTop: spacing.lg }]}>Weather</Text>
        {WEATHER.map((w) => (
          <TouchableOpacity
            key={w}
            style={[styles.radioOption, weather === w && styles.radioSelected]}
            onPress={() => setWeather(w)}
          >
            <View style={[styles.radioDot, weather === w && styles.radioDotActive]} />
            <Text style={[styles.radioLabel, weather === w && styles.radioLabelActive]}>{w}</Text>
          </TouchableOpacity>
        ))}

        <View style={styles.separator} />

        <Text style={styles.label}>Style a New Piece?</Text>
        <View style={styles.toggleRow}>
          <TouchableOpacity
            style={[styles.toggleBtn, !addNewItem && styles.toggleActive]}
            onPress={() => setAddNewItem(false)}
          >
            <Text style={[styles.toggleText, !addNewItem && styles.toggleTextActive]}>No</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.toggleBtn, addNewItem && styles.toggleActive]}
            onPress={() => setAddNewItem(true)}
          >
            <Text style={[styles.toggleText, addNewItem && styles.toggleTextActive]}>Yes</Text>
          </TouchableOpacity>
        </View>

        {addNewItem && (
          <>
            <Text style={styles.label}>Item Description</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g., My chocolate Lemaire trench..."
              placeholderTextColor={colors.textMuted}
              value={itemFocus}
              onChangeText={setItemFocus}
            />
            <Text style={styles.label}>Photo</Text>
            <TouchableOpacity style={styles.uploadBtn} onPress={pickImage}>
              <Text style={styles.uploadBtnText}>{itemImage ? "Change Photo" : "Upload Photo"}</Text>
            </TouchableOpacity>
            {itemImage && (
              <Image source={{ uri: itemImage.uri }} style={styles.previewImg} />
            )}
          </>
        )}

        {wardrobeItems.length > 0 && (
          <>
            <Text style={styles.label}>Or Select from Wardrobe</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.wardrobeScroll}>
              {wardrobeItems.map((item) => (
                <TouchableOpacity
                  key={item.id}
                  style={[styles.wardrobeChip, selectedWardrobe === item.id && styles.wardrobeChipActive]}
                  onPress={() => setSelectedWardrobe(selectedWardrobe === item.id ? null : item.id)}
                >
                  <Text style={[styles.wardrobeChipText, selectedWardrobe === item.id && { color: colors.white }]}>
                    {item.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </>
        )}

        <TouchableOpacity
          style={[styles.primaryBtn, (!occasion || !weather) && styles.disabled]}
          onPress={handleSubmit}
          disabled={!occasion || !weather || loading}
        >
          {loading ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.primaryBtnText}>Receive Guidance</Text>
          )}
        </TouchableOpacity>

        <View style={{ height: 40 }} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  content: { padding: spacing.lg, paddingTop: spacing.xxl + 20 },
  eyebrow: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted, textTransform: "uppercase", letterSpacing: 1 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.textPrimary, marginTop: spacing.xs, marginBottom: spacing.lg },
  label: { fontFamily: fonts.body, fontSize: 15, fontWeight: "600", color: colors.textPrimary, marginBottom: spacing.xs, marginTop: spacing.md },
  hint: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted, marginBottom: spacing.sm },
  input: {
    backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border,
    paddingHorizontal: spacing.md, paddingVertical: 14, fontSize: 15,
    fontFamily: fonts.body, color: colors.textPrimary,
  },
  radioOption: {
    flexDirection: "row", alignItems: "center", gap: 12,
    paddingVertical: 12, paddingHorizontal: spacing.md,
    backgroundColor: colors.bgSecondary, marginBottom: 4,
  },
  radioSelected: { backgroundColor: colors.accent },
  radioDot: { width: 16, height: 16, borderRadius: 8, borderWidth: 2, borderColor: colors.textMuted },
  radioDotActive: { borderColor: colors.white, backgroundColor: colors.white },
  radioLabel: { fontFamily: fonts.body, fontSize: 14, color: colors.textPrimary },
  radioLabelActive: { color: colors.white },
  separator: { borderTopWidth: 1, borderTopColor: colors.border, marginTop: spacing.xl, paddingTop: spacing.lg },
  toggleRow: { flexDirection: "row", gap: spacing.md, marginTop: spacing.xs },
  toggleBtn: { paddingVertical: 10, paddingHorizontal: 24, borderWidth: 1, borderColor: colors.border },
  toggleActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  toggleText: { fontFamily: fonts.body, fontSize: 14, color: colors.textSecondary },
  toggleTextActive: { color: colors.white },
  uploadBtn: { borderWidth: 1, borderColor: colors.border, padding: spacing.md, alignItems: "center" },
  uploadBtnText: { fontFamily: fonts.body, fontSize: 14, color: colors.textSecondary },
  previewImg: { width: "100%", height: 200, resizeMode: "contain", marginTop: spacing.sm, borderWidth: 1, borderColor: colors.border },
  wardrobeScroll: { marginTop: spacing.sm },
  wardrobeChip: { paddingHorizontal: 14, paddingVertical: 8, borderWidth: 1, borderColor: colors.border, marginRight: spacing.sm, backgroundColor: colors.white },
  wardrobeChipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  wardrobeChipText: { fontFamily: fonts.body, fontSize: 13, color: colors.textSecondary },
  primaryBtn: { backgroundColor: colors.accent, paddingVertical: 16, alignItems: "center", marginTop: spacing.xl },
  primaryBtnText: { color: colors.white, fontSize: 16, fontFamily: fonts.body, fontWeight: "600" },
  disabled: { opacity: 0.5 },
  empty: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: colors.bgPrimary, padding: spacing.xl },
  emptyTitle: { fontFamily: fonts.display, fontSize: 24, color: colors.textPrimary, marginBottom: spacing.md },
  emptyText: { fontFamily: fonts.body, fontSize: 15, color: colors.textMuted, textAlign: "center", marginBottom: spacing.lg },
});

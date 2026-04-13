import React, { useState, useCallback } from "react";
import {
  View, Text, TextInput, Pressable, TouchableOpacity, StyleSheet,
  ScrollView, Image, ActivityIndicator, Alert,
} from "react-native";
import { useFocusEffect, useNavigation } from "@react-navigation/native";
import * as ImagePicker from "expo-image-picker";
import { colors, fonts, spacing } from "../theme";
import { startShoppingBuddy, getShoppingHistory } from "../api";

const OCCASIONS = [
  { value: "", label: "—" },
  { value: "everyday", label: "Everyday" },
  { value: "work", label: "Work" },
  { value: "date night", label: "Date Night" },
  { value: "formal event", label: "Formal Event" },
  { value: "weekend casual", label: "Weekend Casual" },
  { value: "travel", label: "Travel" },
  { value: "special occasion", label: "Special Occasion" },
];

export default function BuyOrSkipScreen() {
  const nav = useNavigation();
  const [imageUri, setImageUri] = useState(null);
  const [productUrl, setProductUrl] = useState("");
  const [price, setPrice] = useState("");
  const [occasion, setOccasion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pastEvals, setPastEvals] = useState([]);

  useFocusEffect(
    useCallback(() => {
      getShoppingHistory()
        .then((d) => setPastEvals(d.evaluations || []))
        .catch(() => {});
    }, [])
  );

  async function pickImage() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7,
      exif: false,
    });
    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
      setProductUrl("");
    }
  }

  async function takePhoto() {
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.7,
      exif: false,
    });
    if (!result.canceled) {
      setImageUri(result.assets[0].uri);
      setProductUrl("");
    }
  }

  async function handleSubmit() {
    if (!imageUri && !productUrl.trim()) {
      Alert.alert("Missing", "Please upload a photo or paste a product URL.");
      return;
    }
    setSubmitting(true);
    const formData = new FormData();
    if (imageUri) {
      formData.append("image", { uri: imageUri, type: "image/jpeg", name: "item.jpg" });
    }
    if (productUrl.trim()) formData.append("product_url", productUrl.trim());
    if (price.trim()) formData.append("price", price.trim());
    if (occasion) formData.append("occasion", occasion);

    try {
      const data = await startShoppingBuddy(formData);
      if (data.evaluation) {
        nav.navigate("ShoppingChat", { evaluation: data.evaluation });
      } else {
        Alert.alert("Error", data.error || "Something went wrong.");
      }
    } catch {
      Alert.alert("Error", "Connection error.");
    } finally {
      setSubmitting(false);
    }
  }

  function verdictColor(verdict) {
    if (verdict === "strong_buy") return colors.verdictBuy;
    if (verdict === "skip") return colors.verdictSkip;
    if (verdict === "redundant") return colors.textMuted;
    return colors.textSecondary;
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" nestedScrollEnabled={true}>
      <Text style={styles.eyebrow}>Shopping Buddy</Text>
      <Text style={styles.title}>Should I buy this?</Text>
      <Text style={styles.description}>
        Snap a photo of something you're considering. The Oracle will tell you if it fits your style, fills a gap in your wardrobe, or if you should walk away.
      </Text>

      <View style={styles.linkRow}>
        <TouchableOpacity onPress={() => nav.navigate("Wishlist")}>
          <Text style={styles.link}>Saved Items</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => nav.navigate("Insights")}>
          <Text style={styles.link}>Purchase Insights</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.label}>Upload a photo</Text>
      <Text style={styles.hint}>A product photo, screenshot, or snap from the store — anything works.</Text>
      <View style={styles.photoRow}>
        <TouchableOpacity style={styles.uploadBtn} onPress={pickImage}>
          <Text style={styles.uploadBtnText}>Choose Photo</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.uploadBtn} onPress={takePhoto}>
          <Text style={styles.uploadBtnText}>Take Photo</Text>
        </TouchableOpacity>
      </View>

      {imageUri && (
        <Image source={{ uri: imageUri }} style={styles.previewImg} />
      )}

      <Text style={[styles.label, { marginTop: spacing.lg }]}>Or paste a product URL</Text>
      <TextInput
        style={styles.input}
        placeholder="https://..."
        placeholderTextColor={colors.textMuted}
        value={productUrl}
        onChangeText={(t) => { setProductUrl(t); if (t.trim()) setImageUri(null); }}
        autoCapitalize="none"
        keyboardType="url"
      />

      <View style={styles.twoCol}>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>Price (optional)</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g. 250"
            placeholderTextColor={colors.textMuted}
            value={price}
            onChangeText={setPrice}
            keyboardType="numeric"
          />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>Occasion (optional)</Text>
          <View style={styles.occasionWrap}>
            {OCCASIONS.filter(o => o.value).map((o) => (
              <TouchableOpacity
                key={o.value}
                style={[styles.occasionChip, occasion === o.value && styles.occasionChipActive]}
                onPress={() => setOccasion(occasion === o.value ? "" : o.value)}
              >
                <Text style={[styles.occasionChipText, occasion === o.value && { color: colors.white }]}>
                  {o.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </View>

      <TouchableOpacity style={styles.primaryBtn} onPress={handleSubmit} disabled={submitting}>
        {submitting ? (
          <ActivityIndicator color={colors.white} />
        ) : (
          <Text style={styles.primaryBtnText}>Get The Oracle's Take</Text>
        )}
      </TouchableOpacity>

      {pastEvals.length > 0 && (
        <View style={styles.pastSection}>
          <Text style={styles.pastTitle}>Recent Evaluations</Text>
          {pastEvals.map((ev) => (
            <Pressable
              key={ev.id}
              style={({ pressed }) => [
                styles.pastRow,
                pressed && { opacity: 0.6 },
              ]}
              onPress={() => {
                nav.navigate("ShoppingChat", { evaluation: ev });
              }}
            >
              {ev.thumb_b64 ? (
                <Image
                  source={{ uri: `data:image/jpeg;base64,${ev.thumb_b64}` }}
                  style={styles.pastThumb}
                />
              ) : (
                <View style={[styles.pastThumb, { backgroundColor: colors.border, justifyContent: "center", alignItems: "center" }]}>
                  <Text style={{ fontSize: 20 }}>◆</Text>
                </View>
              )}
              <View style={styles.pastRowInfo}>
                <Text style={[styles.pastVerdict, { color: verdictColor(ev.verdict) }]}>
                  {ev.verdict_display}
                </Text>
                <Text style={styles.pastDate}>
                  {new Date(ev.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </Text>
              </View>
              <Text style={styles.pastArrow}>›</Text>
            </Pressable>
          ))}
        </View>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  content: { padding: spacing.lg, paddingTop: spacing.xxl + 20 },
  eyebrow: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted, textTransform: "uppercase", letterSpacing: 1 },
  title: { fontFamily: fonts.display, fontSize: 28, color: colors.textPrimary, marginTop: spacing.xs },
  description: { fontFamily: fonts.body, fontSize: 14, color: colors.textMuted, marginTop: spacing.sm, lineHeight: 20 },
  linkRow: { flexDirection: "row", gap: spacing.lg, marginTop: spacing.md, marginBottom: spacing.md },
  link: { fontFamily: fonts.body, fontSize: 14, color: colors.textSecondary, textDecorationLine: "underline" },
  label: { fontFamily: fonts.body, fontSize: 15, fontWeight: "600", color: colors.textPrimary, marginBottom: spacing.xs, marginTop: spacing.md },
  hint: { fontFamily: fonts.body, fontSize: 13, color: colors.textMuted, marginBottom: spacing.sm },
  photoRow: { flexDirection: "row", gap: spacing.md },
  uploadBtn: { flex: 1, borderWidth: 1, borderColor: colors.border, padding: spacing.md, alignItems: "center", backgroundColor: colors.white },
  uploadBtnText: { fontFamily: fonts.body, fontSize: 14, color: colors.textSecondary },
  previewImg: { width: "100%", height: 300, resizeMode: "contain", marginTop: spacing.md, borderWidth: 1, borderColor: colors.border },
  input: {
    backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border,
    paddingHorizontal: spacing.md, paddingVertical: 14, fontSize: 15,
    fontFamily: fonts.body, color: colors.textPrimary,
  },
  twoCol: { flexDirection: "row", gap: spacing.md, marginTop: spacing.sm },
  occasionWrap: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: spacing.xs },
  occasionChip: { paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.white },
  occasionChipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  occasionChipText: { fontFamily: fonts.body, fontSize: 11, color: colors.textSecondary },
  primaryBtn: { backgroundColor: colors.accent, paddingVertical: 16, alignItems: "center", marginTop: spacing.xl },
  primaryBtnText: { color: colors.white, fontSize: 16, fontFamily: fonts.body, fontWeight: "600" },
  pastSection: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing.lg, marginTop: spacing.xl },
  pastTitle: { fontFamily: fonts.display, fontSize: 18, color: colors.textPrimary, marginBottom: spacing.md },
  pastRow: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: colors.white, borderWidth: 1, borderColor: colors.border,
    marginBottom: spacing.sm, padding: spacing.sm, gap: spacing.md,
  },
  pastThumb: { width: 50, height: 65, resizeMode: "cover" },
  pastRowInfo: { flex: 1 },
  pastVerdict: { fontFamily: fonts.body, fontSize: 12, textTransform: "uppercase", letterSpacing: 1 },
  pastDate: { fontFamily: fonts.body, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  pastArrow: { fontSize: 22, color: colors.textMuted, paddingRight: spacing.sm },
});

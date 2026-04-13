import React, { useState, useRef } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet, Image,
  TextInput, ActivityIndicator, ScrollView,
  KeyboardAvoidingView, Platform,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useNavigation } from "@react-navigation/native";
import * as ImagePicker from "expo-image-picker";
import { colors, fonts, spacing } from "../theme";
import { startShoppingBuddy } from "../api";

export default function CameraScreen() {
  const nav = useNavigation();
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef(null);

  const [phase, setPhase] = useState("camera"); // camera | preview | loading
  const [photoUri, setPhotoUri] = useState(null);
  const [price, setPrice] = useState("");
  const [occasion, setOccasion] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function snap() {
    if (!cameraRef.current) return;
    const photo = await cameraRef.current.takePictureAsync({ quality: 0.7 });
    setPhotoUri(photo.uri);
    setPhase("preview");
  }

  async function pickFromLibrary() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
      exif: false,
    });
    if (!result.canceled) {
      setPhotoUri(result.assets[0].uri);
      setPhase("preview");
    }
  }

  function retake() {
    setPhotoUri(null);
    setPhase("camera");
  }

  async function submit() {
    if (!photoUri) return;
    setSubmitting(true);
    setPhase("loading");

    const formData = new FormData();
    formData.append("image", {
      uri: photoUri,
      type: "image/jpeg",
      name: "snap.jpg",
    });
    if (price) formData.append("price", price);
    if (occasion) formData.append("occasion", occasion);

    try {
      const data = await startShoppingBuddy(formData);
      if (data.evaluation) {
        nav.navigate("ShoppingChat", { evaluation: data.evaluation });
      } else {
        alert(data.error || "Something went wrong.");
      }
    } catch {
      alert("Connection error.");
    } finally {
      setSubmitting(false);
      setPhase("camera");
      setPhotoUri(null);
      setPrice("");
      setOccasion("");
    }
  }

  // Permission not yet determined
  if (!permission) return <View style={styles.container} />;

  if (!permission.granted) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permTitle}>Camera Access</Text>
        <Text style={styles.permText}>
          The Oracle needs your camera to evaluate items while you shop.
        </Text>
        <TouchableOpacity style={styles.permBtn} onPress={requestPermission}>
          <Text style={styles.permBtnText}>Enable Camera</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Loading state
  if (phase === "loading") {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.loadingText}>The Oracle is analyzing...</Text>
      </View>
    );
  }

  // Preview with optional price/occasion
  if (phase === "preview" && photoUri) {
    return (
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.previewScroll}>
          <Image source={{ uri: photoUri }} style={styles.previewImage} />

          <View style={styles.previewFields}>
            <Text style={styles.fieldLabel}>Price (optional)</Text>
            <TextInput
              style={styles.fieldInput}
              placeholder="e.g. 250"
              placeholderTextColor={colors.textMuted}
              value={price}
              onChangeText={setPrice}
              keyboardType="numeric"
            />

            <Text style={styles.fieldLabel}>Occasion (optional)</Text>
            <TextInput
              style={styles.fieldInput}
              placeholder="e.g. work, weekend, special event"
              placeholderTextColor={colors.textMuted}
              value={occasion}
              onChangeText={setOccasion}
            />
          </View>

          <View style={styles.previewActions}>
            <TouchableOpacity style={styles.retakeBtn} onPress={retake}>
              <Text style={styles.retakeBtnText}>Retake</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.askBtn}
              onPress={submit}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color={colors.white} />
              ) : (
                <Text style={styles.askBtnText}>Ask The Oracle</Text>
              )}
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  // Camera view
  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={styles.camera} facing="back" />
      <View style={styles.cameraOverlay}>
        <Text style={styles.cameraHint}>Snap the item you're considering</Text>
      </View>
      <View style={styles.cameraControls}>
        <TouchableOpacity style={styles.galleryBtn} onPress={pickFromLibrary}>
          <Text style={styles.galleryBtnText}>Gallery</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.shutterBtn} onPress={snap}>
          <View style={styles.shutterInner} />
        </TouchableOpacity>

        <View style={{ width: 60 }} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  camera: { ...StyleSheet.absoluteFillObject },
  cameraOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    alignItems: "center",
    paddingTop: spacing.xxl + 20,
  },
  cameraHint: {
    fontFamily: fonts.body,
    fontSize: 15,
    color: "rgba(255,255,255,0.8)",
    backgroundColor: "rgba(0,0,0,0.4)",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    overflow: "hidden",
  },
  cameraControls: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    paddingBottom: 40,
    paddingHorizontal: spacing.lg,
  },
  shutterBtn: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    borderColor: "#fff",
    justifyContent: "center",
    alignItems: "center",
  },
  shutterInner: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: "#fff",
  },
  galleryBtn: {
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  galleryBtnText: {
    color: "#fff",
    fontFamily: fonts.body,
    fontSize: 14,
  },
  // Preview phase
  previewScroll: {
    backgroundColor: colors.bgPrimary,
    padding: spacing.lg,
    paddingTop: spacing.xxl + 10,
    alignItems: "center",
  },
  previewImage: {
    width: 280,
    height: 380,
    borderRadius: 12,
    resizeMode: "cover",
  },
  previewFields: {
    width: "100%",
    marginTop: spacing.lg,
  },
  fieldLabel: {
    fontFamily: fonts.body,
    fontSize: 14,
    fontWeight: "600",
    color: colors.textSecondary,
    marginBottom: spacing.xs,
    marginTop: spacing.md,
  },
  fieldInput: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 15,
    fontFamily: fonts.body,
    color: colors.textPrimary,
  },
  previewActions: {
    flexDirection: "row",
    gap: spacing.md,
    marginTop: spacing.xl,
    marginBottom: spacing.xxl,
  },
  retakeBtn: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 24,
  },
  retakeBtnText: {
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.textSecondary,
  },
  askBtn: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 24,
    flex: 1,
    alignItems: "center",
  },
  askBtnText: {
    color: colors.white,
    fontFamily: fonts.body,
    fontSize: 15,
    fontWeight: "600",
  },
  // Permission
  permissionContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.bgPrimary,
    padding: spacing.xl,
  },
  permTitle: {
    fontFamily: fonts.display,
    fontSize: 24,
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  permText: {
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.textMuted,
    textAlign: "center",
    marginBottom: spacing.lg,
    lineHeight: 22,
  },
  permBtn: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 14,
    paddingHorizontal: 32,
  },
  permBtnText: {
    color: colors.white,
    fontFamily: fonts.body,
    fontSize: 16,
    fontWeight: "600",
  },
  // Loading
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.bgPrimary,
  },
  loadingText: {
    fontFamily: fonts.display,
    fontSize: 18,
    color: colors.textMuted,
    marginTop: spacing.lg,
  },
});

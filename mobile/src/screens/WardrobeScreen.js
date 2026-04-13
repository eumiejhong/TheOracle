import React, { useState, useCallback } from "react";
import {
  View, Text, FlatList, Image, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import * as ImagePicker from "expo-image-picker";
import { colors, fonts, spacing } from "../theme";
import { getWardrobe, addWardrobeItem, deleteWardrobeItem, toggleFavorite } from "../api";

export default function WardrobeScreen() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    getWardrobe()
      .then((d) => setItems(d.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  async function handleAdd() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    });
    if (result.canceled) return;

    setAdding(true);
    const asset = result.assets[0];
    const formData = new FormData();
    formData.append("image", {
      uri: asset.uri,
      type: "image/jpeg",
      name: "wardrobe.jpg",
    });
    formData.append("name", "New Item");
    formData.append("category", "Other");

    try {
      await addWardrobeItem(formData);
      load();
    } catch {
      Alert.alert("Error", "Failed to add item.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id) {
    Alert.alert("Remove Item", "Delete this item from your wardrobe?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          await deleteWardrobeItem(id);
          load();
        },
      },
    ]);
  }

  async function handleFavorite(id, current) {
    await toggleFavorite(id, !current);
    load();
  }

  function renderItem({ item }) {
    const imageUri = item.image_b64
      ? `data:image/jpeg;base64,${item.image_b64}`
      : null;

    return (
      <TouchableOpacity
        style={styles.card}
        onLongPress={() => handleDelete(item.id)}
      >
        {imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.image} />
        ) : (
          <View style={[styles.image, styles.placeholder]}>
            <Text style={styles.placeholderText}>No Photo</Text>
          </View>
        )}
        <View style={styles.cardInfo}>
          <Text style={styles.itemName} numberOfLines={1}>
            {item.name}
          </Text>
          <Text style={styles.itemCategory}>{item.category}</Text>
        </View>
        <TouchableOpacity
          style={styles.favBtn}
          onPress={() => handleFavorite(item.id, item.is_favorite)}
        >
          <Text style={styles.favIcon}>
            {item.is_favorite ? "★" : "☆"}
          </Text>
        </TouchableOpacity>
      </TouchableOpacity>
    );
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Wardrobe</Text>
        <TouchableOpacity style={styles.addBtn} onPress={handleAdd} disabled={adding}>
          {adding ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.addBtnText}>+ Add</Text>
          )}
        </TouchableOpacity>
      </View>
      <FlatList
        data={items}
        keyExtractor={(i) => String(i.id)}
        renderItem={renderItem}
        numColumns={2}
        contentContainerStyle={styles.grid}
        columnWrapperStyle={styles.row}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.bgPrimary,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xxl + 20,
    paddingBottom: spacing.md,
  },
  title: {
    fontFamily: fonts.display,
    fontSize: 28,
    color: colors.textPrimary,
  },
  addBtn: {
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  addBtnText: {
    color: colors.white,
    fontFamily: fonts.body,
    fontSize: 14,
    fontWeight: "600",
  },
  grid: { padding: spacing.md },
  row: { gap: spacing.md },
  card: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
    marginBottom: spacing.md,
  },
  image: { width: "100%", height: 160, resizeMode: "cover" },
  placeholder: {
    backgroundColor: colors.bgSecondary,
    justifyContent: "center",
    alignItems: "center",
  },
  placeholderText: {
    color: colors.textMuted,
    fontFamily: fonts.body,
    fontSize: 12,
  },
  cardInfo: { padding: spacing.sm },
  itemName: {
    fontFamily: fonts.body,
    fontSize: 13,
    fontWeight: "600",
    color: colors.textPrimary,
  },
  itemCategory: {
    fontFamily: fonts.body,
    fontSize: 11,
    color: colors.textMuted,
    marginTop: 2,
  },
  favBtn: { position: "absolute", top: 8, right: 8 },
  favIcon: { fontSize: 22, color: colors.accent },
});

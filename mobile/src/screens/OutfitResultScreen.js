import React from "react";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import { colors, fonts, spacing } from "../theme";

export default function OutfitResultScreen({ route }) {
  const { suggestion } = route.params || {};

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
    >
      <Text style={styles.heading}>The Oracle Suggests</Text>
      <View style={styles.card}>
        <Text style={styles.body}>{suggestion || "No suggestion available."}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  content: { padding: spacing.lg },
  heading: {
    fontFamily: fonts.display,
    fontSize: 22,
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  body: {
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.textPrimary,
    lineHeight: 24,
  },
});

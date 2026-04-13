import React from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { colors, fonts, spacing } from "../theme";

export default function LoadingOverlay({ message = "The Oracle is thinking..." }) {
  return (
    <View style={styles.overlay}>
      <ActivityIndicator size="large" color={colors.accent} />
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(252, 247, 240, 0.92)",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 999,
  },
  text: {
    fontFamily: fonts.display,
    fontSize: 18,
    color: colors.textMuted,
    marginTop: spacing.lg,
  },
});

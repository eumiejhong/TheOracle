import { Platform } from "react-native";

export const colors = {
  bgPrimary: "#FCF7F0",
  bgSecondary: "#F5EDE3",
  textPrimary: "#1a1a1a",
  textSecondary: "#4a4a4a",
  textMuted: "#8a8a8a",
  border: "#e0d8ce",
  accent: "#1a1a1a",
  white: "#ffffff",
  verdictBuy: "#2d6a4f",
  verdictBuyBg: "#e8f5e9",
  verdictSkip: "#cc4444",
  verdictSkipBg: "#fff5f5",
};

export const fonts = {
  display: Platform.select({
    ios: "Georgia",
    android: "serif",
  }),
  body: Platform.select({
    ios: "System",
    android: "sans-serif",
  }),
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

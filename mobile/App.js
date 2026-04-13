import React, { useState, useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import { Platform } from "react-native";
import { StatusBar } from "expo-status-bar";
import * as SecureStore from "expo-secure-store";

import AppNavigator from "./src/navigation/AppNavigator";
import AuthScreen from "./src/screens/AuthScreen";
import { colors } from "./src/theme";

const systemFont = Platform.select({ ios: "System", android: "sans-serif" });

const oracleTheme = {
  dark: false,
  colors: {
    primary: colors.accent,
    background: colors.bgPrimary,
    card: colors.bgPrimary,
    text: colors.textPrimary,
    border: colors.border,
    notification: colors.accent,
  },
  fonts: Platform.select({
    ios: {
      regular: { fontFamily: systemFont, fontWeight: "400" },
      medium: { fontFamily: systemFont, fontWeight: "500" },
      bold: { fontFamily: systemFont, fontWeight: "700" },
      heavy: { fontFamily: systemFont, fontWeight: "900" },
    },
    android: {
      regular: { fontFamily: "sans-serif", fontWeight: "normal" },
      medium: { fontFamily: "sans-serif-medium", fontWeight: "normal" },
      bold: { fontFamily: "sans-serif", fontWeight: "bold" },
      heavy: { fontFamily: "sans-serif", fontWeight: "bold" },
    },
  }),
};

export default function App() {
  const [isAuthed, setIsAuthed] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await SecureStore.getItemAsync("access_token");
      setIsAuthed(!!token);
      setChecking(false);
    })();
  }, []);

  if (checking) return null;

  if (!isAuthed) {
    return (
      <>
        <StatusBar style="dark" />
        <AuthScreen onAuth={() => setIsAuthed(true)} />
      </>
    );
  }

  return (
    <NavigationContainer theme={oracleTheme}>
      <StatusBar style="dark" />
      <AppNavigator />
    </NavigationContainer>
  );
}

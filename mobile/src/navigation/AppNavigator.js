import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Text } from "react-native";
import { colors, fonts } from "../theme";

import HomeScreen from "../screens/HomeScreen";
import WardrobeScreen from "../screens/WardrobeScreen";
import ProfileScreen from "../screens/ProfileScreen";
import BuyOrSkipScreen from "../screens/BuyOrSkipScreen";
import ShoppingChatScreen from "../screens/ShoppingChatScreen";
import OutfitResultScreen from "../screens/OutfitResultScreen";

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

function HomeTabs() {
  const tabIcons = { Wardrobe: "▤", Today: "◇", "Buy or Skip": "◆", Me: "○" };

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 10, marginTop: -2 },
        tabBarStyle: {
          backgroundColor: colors.bgPrimary,
          borderTopColor: colors.border,
          height: 85,
          paddingBottom: 28,
          paddingTop: 8,
        },
        tabBarIcon: ({ focused, color }) => (
          <Text style={{ fontSize: 18, color }}>{tabIcons[route.name]}</Text>
        ),
      })}
    >
      <Tab.Screen name="Wardrobe" component={WardrobeScreen} />
      <Tab.Screen name="Today" component={HomeScreen} />
      <Tab.Screen name="Buy or Skip" component={BuyOrSkipScreen} />
      <Tab.Screen name="Me" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bgPrimary },
        headerTintColor: colors.textPrimary,
        headerTitleStyle: { fontFamily: fonts.display, fontSize: 18 },
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen
        name="Tabs"
        component={HomeTabs}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="ShoppingChat"
        component={ShoppingChatScreen}
        options={{ title: "The Oracle" }}
      />
      <Stack.Screen
        name="OutfitResult"
        component={OutfitResultScreen}
        options={{ title: "Today's Outfit" }}
      />
    </Stack.Navigator>
  );
}

import React, { useState, useRef, useEffect } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, Image, KeyboardAvoidingView, Platform,
  ActivityIndicator,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { colors, fonts, spacing } from "../theme";
import { sendShoppingReply, toggleSaveForLater, getShareLink } from "../api";

export default function ShoppingChatScreen({ route }) {
  const { evaluation: initialEval } = route.params || {};
  const [messages, setMessages] = useState(initialEval?.conversation || []);
  const [evalId] = useState(initialEval?.id);
  const [isComplete, setIsComplete] = useState(initialEval?.is_complete || false);
  const [verdict, setVerdict] = useState(initialEval?.verdict || "");
  const [input, setInput] = useState("");
  const [pendingImage, setPendingImage] = useState(null);
  const [sending, setSending] = useState(false);
  const [saved, setSaved] = useState(initialEval?.saved_for_later || false);
  const scrollRef = useRef();

  useEffect(() => {
    scrollRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  async function pickPhoto() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    });
    if (!result.canceled) {
      setPendingImage(result.assets[0]);
    }
  }

  async function takePhoto() {
    const result = await ImagePicker.launchCameraAsync({
      quality: 0.7,
    });
    if (!result.canceled) {
      setPendingImage(result.assets[0]);
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text && !pendingImage) return;
    if (isComplete || !evalId) return;

    setSending(true);
    const userMsg = { role: "user", text: text || "(photo)" };
    if (pendingImage) userMsg.hasImage = true;
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    const formData = new FormData();
    if (text) formData.append("message", text);
    if (pendingImage) {
      formData.append("image", {
        uri: pendingImage.uri,
        type: "image/jpeg",
        name: "reply.jpg",
      });
    }
    setPendingImage(null);

    try {
      const data = await sendShoppingReply(evalId, formData);
      if (data.reply) {
        setMessages((prev) => [...prev, { role: "oracle", text: data.reply }]);
      }
      if (data.is_complete) {
        setIsComplete(true);
        setVerdict(data.verdict || "");
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "oracle", text: "Something went wrong. Try sending that again." },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function handleSave() {
    try {
      const res = await toggleSaveForLater(evalId);
      setSaved(res.saved);
    } catch {}
  }

  async function handleShare() {
    try {
      const res = await getShareLink(evalId);
      if (res.share_url) {
        // In a real app, use Share API
        alert(`Share link: ${res.share_url}`);
      }
    } catch {}
  }

  function verdictColor() {
    if (verdict?.includes("Buy") || verdict?.includes("Strong")) return colors.verdictBuy;
    if (verdict?.includes("Skip")) return colors.verdictSkip;
    return colors.textSecondary;
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={90}
    >
      <ScrollView
        ref={scrollRef}
        style={styles.chatArea}
        contentContainerStyle={styles.chatContent}
      >
        {initialEval?.image_b64 && (
          <View style={styles.itemPreview}>
            <Image
              source={{ uri: `data:image/jpeg;base64,${initialEval.image_b64}` }}
              style={styles.itemImage}
            />
          </View>
        )}

        {messages.map((msg, i) => (
          <View
            key={i}
            style={[
              styles.bubble,
              msg.role === "user" ? styles.userBubble : styles.oracleBubble,
            ]}
          >
            {msg.role === "oracle" && (
              <Text style={styles.bubbleLabel}>The Oracle</Text>
            )}
            <Text
              style={[
                styles.bubbleText,
                msg.role === "user" && styles.userBubbleText,
              ]}
            >
              {msg.text}
            </Text>
          </View>
        ))}

        {sending && (
          <View style={[styles.bubble, styles.oracleBubble]}>
            <ActivityIndicator size="small" color={colors.textMuted} />
          </View>
        )}

        {isComplete && (
          <View style={styles.verdictArea}>
            <Text style={[styles.verdictText, { color: verdictColor() }]}>
              {verdict}
            </Text>
            <View style={styles.verdictActions}>
              <TouchableOpacity style={styles.actionBtn} onPress={handleSave}>
                <Text style={styles.actionBtnText}>
                  {saved ? "★ Saved" : "☆ Save for Later"}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionBtn} onPress={handleShare}>
                <Text style={styles.actionBtnText}>Share</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </ScrollView>

      {!isComplete && (
        <View style={styles.inputBar}>
          {pendingImage && (
            <View style={styles.previewRow}>
              <Image source={{ uri: pendingImage.uri }} style={styles.previewThumb} />
              <TouchableOpacity onPress={() => setPendingImage(null)}>
                <Text style={styles.removePreview}>✕</Text>
              </TouchableOpacity>
            </View>
          )}
          <View style={styles.inputRow}>
            <TouchableOpacity style={styles.photoBtn} onPress={takePhoto}>
              <Text style={styles.photoBtnText}>📷</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.photoBtn} onPress={pickPhoto}>
              <Text style={styles.photoBtnText}>📎</Text>
            </TouchableOpacity>
            <TextInput
              style={styles.chatInput}
              placeholder="Reply to The Oracle..."
              placeholderTextColor={colors.textMuted}
              value={input}
              onChangeText={setInput}
              multiline
            />
            <TouchableOpacity
              style={[styles.sendBtn, sending && styles.disabled]}
              onPress={handleSend}
              disabled={sending}
            >
              <Text style={styles.sendBtnText}>↑</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary },
  chatArea: { flex: 1 },
  chatContent: { padding: spacing.md, paddingBottom: spacing.xl },
  itemPreview: { alignItems: "center", marginBottom: spacing.md },
  itemImage: {
    width: 200,
    height: 260,
    borderRadius: 12,
    resizeMode: "cover",
  },
  bubble: {
    maxWidth: "85%",
    borderRadius: 16,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  userBubble: {
    backgroundColor: colors.accent,
    alignSelf: "flex-end",
    borderBottomRightRadius: 4,
  },
  oracleBubble: {
    backgroundColor: colors.white,
    alignSelf: "flex-start",
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  bubbleLabel: {
    fontFamily: fonts.display,
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: 4,
  },
  bubbleText: {
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.textPrimary,
    lineHeight: 22,
  },
  userBubbleText: { color: colors.white },
  verdictArea: {
    alignItems: "center",
    marginTop: spacing.lg,
    padding: spacing.md,
  },
  verdictText: {
    fontFamily: fonts.display,
    fontSize: 20,
    marginBottom: spacing.md,
  },
  verdictActions: { flexDirection: "row", gap: spacing.md },
  actionBtn: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  actionBtnText: {
    fontFamily: fonts.body,
    fontSize: 13,
    color: colors.textSecondary,
  },
  inputBar: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.bgPrimary,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    paddingBottom: spacing.lg,
  },
  previewRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  previewThumb: {
    width: 50,
    height: 50,
    borderRadius: 8,
    marginRight: spacing.sm,
  },
  removePreview: { fontSize: 18, color: colors.textMuted },
  inputRow: { flexDirection: "row", alignItems: "flex-end", gap: spacing.xs },
  photoBtn: { paddingVertical: 8, paddingHorizontal: 4 },
  photoBtnText: { fontSize: 22 },
  chatInput: {
    flex: 1,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxHeight: 100,
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.textPrimary,
  },
  sendBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.accent,
    justifyContent: "center",
    alignItems: "center",
  },
  sendBtnText: { color: colors.white, fontSize: 18, fontWeight: "700" },
  disabled: { opacity: 0.5 },
});

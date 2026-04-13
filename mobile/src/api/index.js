import { apiFetch } from "./client";

export async function getProfile() {
  const res = await apiFetch("/profile/");
  return res.json();
}

export async function saveProfile(data) {
  const res = await apiFetch("/profile/", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function getWardrobe() {
  const res = await apiFetch("/wardrobe/");
  return res.json();
}

export async function addWardrobeItem(formData) {
  const res = await apiFetch("/wardrobe/", {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function deleteWardrobeItem(id) {
  const res = await apiFetch(`/wardrobe/${id}/`, { method: "DELETE" });
  return res.json();
}

export async function toggleFavorite(id, isFavorite) {
  const res = await apiFetch(`/wardrobe/${id}/`, {
    method: "PATCH",
    body: JSON.stringify({ is_favorite: isFavorite }),
  });
  return res.json();
}

export async function submitDailyInput(body) {
  const res = await apiFetch("/daily-input/", {
    method: "POST",
    body,
  });
  return res.json();
}

export async function startShoppingBuddy(formData) {
  const res = await apiFetch("/shopping-buddy/", {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function sendShoppingReply(evalId, formData) {
  const res = await apiFetch(`/shopping-buddy/${evalId}/reply/`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function toggleSaveForLater(evalId) {
  const res = await apiFetch(`/shopping-buddy/${evalId}/save/`, {
    method: "POST",
  });
  return res.json();
}

export async function getWishlist() {
  const res = await apiFetch("/shopping-buddy/wishlist/");
  return res.json();
}

export async function getInsights() {
  const res = await apiFetch("/shopping-buddy/insights/");
  return res.json();
}

export async function getShoppingHistory() {
  const res = await apiFetch("/shopping-buddy/history/");
  return res.json();
}

export async function getShareLink(evalId) {
  const res = await apiFetch(`/shopping-buddy/${evalId}/share/`);
  return res.json();
}

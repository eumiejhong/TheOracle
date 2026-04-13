import * as SecureStore from "expo-secure-store";

const BASE_URL = __DEV__
  ? "http://192.168.1.186:8000/api/v1"
  : "https://theoracle.up.railway.app/api/v1";

async function getToken() {
  return SecureStore.getItemAsync("access_token");
}

async function getRefreshToken() {
  return SecureStore.getItemAsync("refresh_token");
}

async function setTokens(access, refresh) {
  await SecureStore.setItemAsync("access_token", access);
  if (refresh) await SecureStore.setItemAsync("refresh_token", refresh);
}

async function clearTokens() {
  await SecureStore.deleteItemAsync("access_token");
  await SecureStore.deleteItemAsync("refresh_token");
}

async function refreshAccessToken() {
  const refresh = await getRefreshToken();
  if (!refresh) return null;

  try {
    const res = await fetch(`${BASE_URL}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    await setTokens(data.access, null);
    return data.access;
  } catch {
    return null;
  }
}

async function apiFetch(path, options = {}) {
  let token = await getToken();

  const headers = { ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  let res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401 && token) {
    token = await refreshAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
      res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
    }
  }

  return res;
}

export { apiFetch, setTokens, clearTokens, getToken, BASE_URL };

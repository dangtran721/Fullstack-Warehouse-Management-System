import { API_BASE_URL } from "./config.js";

const TOKEN_STORAGE_KEY = "wms.auth.tokens";

export class ApiError extends Error {
  constructor(message, status = 0, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function responseMessage(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join(" ") || fallback;
  }
  return fallback;
}

export class AuthClient {
  constructor({ apiBaseUrl = API_BASE_URL, storage = globalThis.localStorage, fetchImpl = globalThis.fetch } = {}) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
    this.storage = storage;
    this.fetchImpl = fetchImpl;
  }

  get tokens() {
    try {
      const tokens = JSON.parse(this.storage.getItem(TOKEN_STORAGE_KEY));
      return tokens?.access_token && tokens?.refresh_token ? tokens : null;
    } catch {
      this.clearSession();
      return null;
    }
  }

  hasSession() {
    return this.tokens !== null;
  }

  saveTokens(tokens) {
    if (!tokens?.access_token || !tokens?.refresh_token) {
      throw new ApiError("The server returned an invalid authentication response.");
    }
    this.storage.setItem(
      TOKEN_STORAGE_KEY,
      JSON.stringify({ access_token: tokens.access_token, refresh_token: tokens.refresh_token }),
    );
  }

  clearSession() {
    this.storage.removeItem(TOKEN_STORAGE_KEY);
  }

  async register(payload) {
    return this.request("/auth/register", { method: "POST", body: payload, auth: false });
  }

  async login(identifier, password) {
    const tokens = await this.request("/auth/login", {
      method: "POST",
      body: { identifier, password },
      auth: false,
    });
    this.saveTokens(tokens);
    return tokens;
  }

  async refresh() {
    const refreshToken = this.tokens?.refresh_token;
    if (!refreshToken) throw new ApiError("Your session has expired.", 401);

    const tokens = await this.request("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      auth: false,
    });
    this.saveTokens(tokens);
    return tokens;
  }

  async logout() {
    const refreshToken = this.tokens?.refresh_token;
    try {
      if (refreshToken) {
        await this.request("/auth/logout", {
          method: "POST",
          body: { refresh_token: refreshToken },
          auth: false,
        });
      }
    } finally {
      this.clearSession();
    }
  }

  async getCurrentUser() {
    return this.request("/auth/me");
  }

  async request(path, { method = "GET", body, auth = true, retryAfterRefresh = true } = {}) {
    const headers = { Accept: "application/json" };
    const accessToken = this.tokens?.access_token;
    if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";

    let response;
    try {
      response = await this.fetchImpl.call(globalThis, `${this.apiBaseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (error) {
      throw new ApiError("Unable to reach the API. Check that the backend is running.", 0, error);
    }

    const text = await response.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = null;
    }

    if (response.status === 401 && auth && retryAfterRefresh && this.tokens?.refresh_token) {
      try {
        await this.refresh();
      } catch {
        this.clearSession();
        throw new ApiError("Your session has expired. Please sign in again.", 401);
      }
      return this.request(path, { method, body, auth, retryAfterRefresh: false });
    }

    if (!response.ok) {
      throw new ApiError(responseMessage(payload, `Request failed with status ${response.status}.`), response.status, payload);
    }
    return payload;
  }
}

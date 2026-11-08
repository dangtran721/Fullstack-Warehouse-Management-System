import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, AuthClient } from "../assets/js/auth.js";

class MemoryStorage {
  values = new Map();
  getItem(key) { return this.values.get(key) ?? null; }
  setItem(key, value) { this.values.set(key, value); }
  removeItem(key) { this.values.delete(key); }
}

function jsonResponse(status, payload = null) {
  return { ok: status >= 200 && status < 300, status, text: async () => (payload === null ? "" : JSON.stringify(payload)) };
}

test("login persists the token pair", async () => {
  const storage = new MemoryStorage();
  const client = new AuthClient({
    apiBaseUrl: "https://api.test/api/v1",
    storage,
    fetchImpl: async (url, options) => {
      assert.equal(url, "https://api.test/api/v1/auth/login");
      assert.deepEqual(JSON.parse(options.body), { identifier: "staff", password: "secret123" });
      return jsonResponse(200, { access_token: "access", refresh_token: "refresh" });
    },
  });

  await client.login("staff", "secret123");
  assert.deepEqual(client.tokens, { access_token: "access", refresh_token: "refresh" });
});

test("requests bind fetch to the global runtime", async () => {
  const client = new AuthClient({
    apiBaseUrl: "https://api.test/api/v1",
    storage: new MemoryStorage(),
    fetchImpl: function fetchImpl() {
      assert.equal(this, globalThis);
      return jsonResponse(200, { access_token: "access", refresh_token: "refresh" });
    },
  });

  await client.login("staff", "secret123");
});

test("registration sends the approved request body and returns the user", async () => {
  const client = new AuthClient({
    apiBaseUrl: "https://api.test/api/v1",
    storage: new MemoryStorage(),
    fetchImpl: async (url, options) => {
      assert.equal(url, "https://api.test/api/v1/auth/register");
      assert.deepEqual(JSON.parse(options.body), {
        username: "staff",
        email: "staff@example.com",
        password: "Password1",
        full_name: null,
      });
      return jsonResponse(201, { id: "user-id", username: "staff", role: "STAFF" });
    },
  });

  assert.equal((await client.register({
    username: "staff", email: "staff@example.com", password: "Password1", full_name: null,
  })).role, "STAFF");
});

test("an unauthorized API request refreshes once and retries with the rotated token", async () => {
  const storage = new MemoryStorage();
  const calls = [];
  const responses = [
    jsonResponse(401, { detail: "Expired" }),
    jsonResponse(200, { access_token: "new-access", refresh_token: "new-refresh" }),
    jsonResponse(200, { username: "staff" }),
  ];
  const client = new AuthClient({
    apiBaseUrl: "https://api.test/api/v1",
    storage,
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return responses.shift();
    },
  });
  client.saveTokens({ access_token: "old-access", refresh_token: "old-refresh" });

  assert.deepEqual(await client.getCurrentUser(), { username: "staff" });
  assert.equal(calls.length, 3);
  assert.equal(calls[0].options.headers.Authorization, "Bearer old-access");
  assert.deepEqual(JSON.parse(calls[1].options.body), { refresh_token: "old-refresh" });
  assert.equal(calls[2].options.headers.Authorization, "Bearer new-access");
  assert.deepEqual(client.tokens, { access_token: "new-access", refresh_token: "new-refresh" });
});

test("a failed refresh clears the persistent session", async () => {
  const storage = new MemoryStorage();
  const client = new AuthClient({
    apiBaseUrl: "https://api.test/api/v1",
    storage,
    fetchImpl: async () => jsonResponse(401, { detail: "Invalid refresh token." }),
  });
  client.saveTokens({ access_token: "expired", refresh_token: "revoked" });

  await assert.rejects(client.getCurrentUser(), (error) => error instanceof ApiError && error.status === 401);
  assert.equal(client.hasSession(), false);
});

test("logout sends the refresh token and clears the local session", async () => {
  const storage = new MemoryStorage();
  const client = new AuthClient({
    apiBaseUrl: "https://api.test/api/v1",
    storage,
    fetchImpl: async (url, options) => {
      assert.equal(url, "https://api.test/api/v1/auth/logout");
      assert.deepEqual(JSON.parse(options.body), { refresh_token: "refresh" });
      return jsonResponse(204);
    },
  });
  client.saveTokens({ access_token: "access", refresh_token: "refresh" });

  await client.logout();
  assert.equal(client.hasSession(), false);
});

test("validation responses preserve the API error message", async () => {
  const client = new AuthClient({
    apiBaseUrl: "https://api.test/api/v1",
    storage: new MemoryStorage(),
    fetchImpl: async () => jsonResponse(422, { detail: [{ msg: "Field required" }] }),
  });

  await assert.rejects(client.register({}), (error) => error.message === "Field required" && error.status === 422);
});

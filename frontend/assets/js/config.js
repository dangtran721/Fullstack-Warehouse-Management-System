const configuredApiBaseUrl = globalThis.WMS_API_BASE_URL;
const defaultApiBaseUrl =
  typeof window === "undefined"
    ? "http://localhost:8000/api/v1"
    : `${window.location.protocol}//${window.location.hostname || "localhost"}:8000/api/v1`;

export const API_BASE_URL = (configuredApiBaseUrl || defaultApiBaseUrl).replace(/\/$/, "");

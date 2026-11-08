import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const source = resolve(import.meta.dirname);
const output = resolve(source, "dist");
const apiBaseUrl = (process.env.API_BASE_URL || "").replace(/\/$/, "");

if (!apiBaseUrl) {
  throw new Error("API_BASE_URL is required for a production frontend build.");
}

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await Promise.all(
  ["index.html", "assets", "pages"].map((entry) =>
    cp(resolve(source, entry), resolve(output, entry), { recursive: true }),
  ),
);
await writeFile(
  resolve(output, "assets/js/runtime-config.js"),
  `window.WMS_API_BASE_URL = ${JSON.stringify(apiBaseUrl)};\n`,
);

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});

import path from "path";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const target = "http://localhost:8081"; // mitmweb instance URL (for development only)

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      web: path.resolve(__dirname, "../web/dist/js"),
    },
  },
  server: {
    proxy: {
      // Proxy Python Tornado endpoints.
      "/filter-help": {
        target,
      },
      "/updates": {
        target: target.replace("http", "ws"),
        ws: true,
      },
      "/commands": {
        target,
      },
      "/events": {
        target,
      },
      "/flows": {
        target,
      },
      "/clear": {
        target,
      },
      "/options": {
        target,
      },
      "/state": {
        target,
      },
      "/processes": {
        target,
      },
      "/executable-icon": {
        target,
      },
    },
  },
});

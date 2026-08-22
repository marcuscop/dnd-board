import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/uploads": "http://127.0.0.1:8000",
      "/boards": "http://127.0.0.1:8000",
      "/npcs": "http://127.0.0.1:8000",
      "/monsters": "http://127.0.0.1:8000"
    }
  }
});

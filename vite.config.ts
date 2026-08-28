import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendUrl = process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const devServerPort = Number(process.env.VITE_PORT ?? 5173);

export default defineConfig({
  plugins: [react()],
  server: {
    port: devServerPort,
    proxy: {
      "/api": backendUrl,
      "/uploads": backendUrl,
      "/boards": backendUrl,
      "/npcs": backendUrl,
      "/monsters": backendUrl
    }
  }
});

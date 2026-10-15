import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// `npm run dev`:
// so the browser always talks to a single origin (no CORS needed).
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    port: 5173,
    proxy: {
      // `npm run dev` talks to the dockerised stack (nginx on :8080), so cookies stay same-origin-like
      "/api": { target: "http://34.171.152.81:8080", changeOrigin: true },
      "/media": { target: "http://34.171.152.81:8080", changeOrigin: true },
    },
  },
});

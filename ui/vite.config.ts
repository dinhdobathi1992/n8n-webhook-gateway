import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/admin/",
  plugins: [tailwindcss(), react()],
  server: {
    port: 5173,
    proxy: {
      "/admin/api": "http://localhost:3000",
      "/health": "http://localhost:3000",
    },
  },
});

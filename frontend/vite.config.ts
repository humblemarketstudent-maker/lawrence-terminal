import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxy = process.env.API_PROXY || "http://127.0.0.1:8741";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 4317,
    strictPort: true,
    allowedHosts: true,
    proxy: { "/api": apiProxy },
  },
  preview: {
    host: "0.0.0.0",
    port: 4317,
    strictPort: true,
    allowedHosts: true,
    proxy: { "/api": apiProxy },
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    strictPort: true, // fail fast if 5173 is already occupied
    open: true,       // auto-open browser on `npm run dev`
  },

  preview: {
    port: 5173,
  },
});
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  root: path.join(__dirname, "renderer"),
  // Use relative asset paths so the renderer works when loaded via file:// in production
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});

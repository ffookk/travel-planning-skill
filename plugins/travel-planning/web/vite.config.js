import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const outputDirectory = fileURLToPath(
  new URL("../skills/travel-planning/assets/frontend", import.meta.url),
);

export default defineConfig({
  plugins: [vue()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    target: "es2015",
    outDir: outputDirectory,
    emptyOutDir: true,
    sourcemap: false,
    minify: "oxc",
    cssCodeSplit: false,
    lib: {
      entry: fileURLToPath(new URL("./src/main.js", import.meta.url)),
      name: "TravelItineraryPage",
      formats: ["iife"],
      fileName: () => "itinerary-app.js",
      cssFileName: "itinerary-app",
    },
  },
});

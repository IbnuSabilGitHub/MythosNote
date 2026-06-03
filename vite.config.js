import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    outDir: resolve(process.cwd(), "static/dist"),
    emptyOutDir: false,
    rollupOptions: {
      input: {
        workspace: resolve(process.cwd(), "static/js/entries/workspace.js"),
        project: resolve(process.cwd(), "static/js/entries/project.js"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});


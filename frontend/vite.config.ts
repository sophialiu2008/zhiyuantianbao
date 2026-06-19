import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { realpathSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = realpathSync(dirname(fileURLToPath(import.meta.url)));

export default defineConfig({
  root: projectRoot,
  plugins: [react()],
  preview: {
    allowedHosts: ["zhiyuantianbao.zeabur.app"],
  },
  build: {
    sourcemap: true,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      input: "index.html",
    },
  },
});

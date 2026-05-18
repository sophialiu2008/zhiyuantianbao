import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  preview: {
    allowedHosts: ["zhiyuantianbao.zeabur.app"],
  },
  build: {
    sourcemap: true,
    chunkSizeWarningLimit: 900,
  },
});

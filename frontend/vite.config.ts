import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
    "process.env": "{}",
    process: '{"env":{}}',
  },
  build: {
    target: "es2022",
    outDir: resolve(__dirname, "../custom_components/oikovis_pulse/frontend"),
    emptyOutDir: false,
    sourcemap: mode === "development",
    minify: "esbuild",
    cssCodeSplit: false,
    lib: {
      entry: resolve(__dirname, "src/main.tsx"),
      formats: ["es"],
      fileName: () => "pulse.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        assetFileNames: "pulse.[ext]",
      },
    },
  },
  server: {
    port: 5173,
    open: "/?demo=1",
  },
}));

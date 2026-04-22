import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// kbgen UI — builds into ../src/static/dist so FastAPI can StaticFiles-mount it.
// Dev server proxies /api → :8004 so the same code works in dev and prod.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, '../src/static/dist'),
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8004',
    },
  },
});

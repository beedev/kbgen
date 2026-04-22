import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// kbgen UI — builds into ../src/static/dist so FastAPI can StaticFiles-mount it.
// Dev server proxies /api → :8004 so the same code works in dev and prod.
//
// Base path (for reverse-proxy deploys like `https://host/kbgen/`) comes from
// the VITE_BASE_PATH env var at build time. Default empty = mounted at root.
// Vite then rewrites all asset URLs to start with that prefix, and
// `import.meta.env.BASE_URL` is exposed to app code (see lib/api.ts and App.tsx).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const rawBase = (env.VITE_BASE_PATH || '').trim();
  // Normalise: "" → "/", "/kbgen" → "/kbgen/", "/kbgen/" stays.
  const base = rawBase ? `/${rawBase.replace(/^\/+|\/+$/g, '')}/` : '/';

  return {
    base,
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
  };
});

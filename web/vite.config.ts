import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { paraglideVitePlugin } from '@inlang/paraglide-js'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Every user-facing text lives in messages/{locale}/*.json and compiles to typed functions.
    paraglideVitePlugin({
      project: './project.inlang',
      outdir: './src/paraglide',
      strategy: ['baseLocale'],
      emitTsDeclarations: true,
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/pesquisa/run': {
        target: 'http://localhost:8004',
        changeOrigin: true,
      },
    },
  },
  // @ts-expect-error Vitest configuration
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
  },
})

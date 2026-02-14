import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const basePath = process.env.VITE_BASE_PATH || '/'

export default defineConfig({
  base: basePath,
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: true,
    hmr: {
      port: 3000,
    },
    proxy: {
      [`${basePath}api`]: {
        target: process.env.VITE_BACKEND_URL || 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(new RegExp(`^${basePath}`), '/'),
      }
    }
  }
})

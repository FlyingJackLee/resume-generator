import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND_URL = 'http://127.0.0.1:8010'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': BACKEND_URL,
      '/preview': BACKEND_URL,
    },
  },
})

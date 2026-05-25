import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/fonts': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/presets': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

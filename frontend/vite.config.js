import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'openchemlib': path.resolve(__dirname, 'node_modules/openchemlib/dist/openchemlib.debug.js')
    }
  },
  optimizeDeps: {
    include: ['openchemlib']
  },
  server: {
    proxy: {
      // Когда ты на локалке делаешь запрос к /api
      '/api': {
        target: 'http://localhost:8000', // Vite перекинет его на твой FastAPI
        changeOrigin: true,
        // Если твой FastAPI не ждет префикс /api (например, корень бэкенда это /),
        // можно его отрезать:
        // rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },

  build: {
    // Увеличим лимит для ассетов, чтобы WASM файл не превратился в base64
    assetsInlineLimit: 0
  }
})
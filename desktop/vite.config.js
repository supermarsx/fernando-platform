import { defineConfig } from 'vite'
import electron from 'electron-vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    electron({
      main: {
        entry: 'src/main/main.js',
        onstart(options) {
          options.startup()
        }
      },
      preload: {
        input: {
          preload: 'src/preload/preload.js'
        }
      },
      renderer: {
        resolve: {
          alias: {
            '@': resolve(__dirname, 'src/renderer')
          }
        }
      }
    }),
    vue()
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer')
    }
  },
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/renderer/index.html')
      }
    }
  },
  server: {
    port: 3000,
    strictPort: true
  },
  optimizeDeps: {
    include: ['electron', 'electron-store', 'axios']
  },
  define: {
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false
  }
})
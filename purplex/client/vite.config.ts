import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // Bundle analysis plugin (generates dist-stats.html after build)
    visualizer({
      open: false,
      filename: 'dist-stats.html',
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    // Optimize chunk size
    chunkSizeWarningLimit: 300, // Reduced from default 500kb

    // Code splitting configuration
    rollupOptions: {
      output: {
        // Manual chunks for better caching
        manualChunks: {
          // Vendor chunks - rarely change, good for caching
          'vendor-vue': ['vue', 'vue-router', 'vuex'],
          'vendor-utils': ['axios', 'js-cookie'],
          'vendor-firebase': ['firebase/app', 'firebase/auth'],

          // Editor chunk - only loaded when needed
          'editor': ['ace-builds', 'vue3-ace-editor'],

          // Admin components - lazy loaded for admin users only
          'admin': [
            './src/components/AdminProblems.vue',
            './src/components/admin/AdminProblemEditorShell.vue',
            './src/components/AdminSubmissions.vue',
            './src/components/AdminCourses.vue',
            './src/components/AdminUsers.vue',
            './src/components/AdminProblemSets.vue'
          ],
        },

        // Better chunk naming for debugging
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId ? chunkInfo.facadeModuleId.split('/').pop() : 'chunk'
          return `js/[name]-${facadeModuleId}-[hash].js`
        },

        // Asset file naming
        assetFileNames: (assetInfo) => {
          const extType = assetInfo.name.split('.').pop()
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
            return `img/[name]-[hash][extname]`
          }
          if (/woff|woff2|eot|ttf|otf/i.test(extType)) {
            return `fonts/[name]-[hash][extname]`
          }
          return `[ext]/[name]-[hash][extname]`
        },
      },
    },

    // Remove console statements in production builds
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info'],
        passes: 2, // Run compression twice for better optimization
      },
      format: {
        comments: false, // Remove all comments
      },
    },

    // Enable minification in production
    minify: 'terser',

    // Source maps only in development
    sourcemap: process.env.NODE_ENV === 'development',

    // Inline small assets to reduce requests
    assetsInlineLimit: 4096, // 4kb

    // Enable CSS code splitting
    cssCodeSplit: true,

    // Target modern browsers for smaller bundles
    target: 'es2018',
  },
  // Environment-based configuration
  define: {
    __VUE_PROD_DEVTOOLS__: false,
  },
  server: {
    proxy: {
      '/api': {
        // Use Docker service name when running in container, localhost otherwise
        target: process.env.DOCKER_CONTAINER ? 'http://purplex_web_dev:8000' : 'http://localhost:8000',
        changeOrigin: true,
        // Rewrite the Host header to use localhost (Django allows this)
        headers: {
          'Host': 'localhost:8000'
        }
      },
    },
  },
})

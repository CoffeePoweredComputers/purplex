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
      // Two entries: the main SPA and the chromeless embed shell (F1, #143).
      input: {
        main: path.resolve(__dirname, 'index.html'),
        embed: path.resolve(__dirname, 'embed.html'),
      },
      output: {
        // Manual chunks for better caching.
        //
        // Function form (not the plain-object form) is required now that the
        // build has two entries (main + embed, #143). Only vendor packages
        // are explicitly bucketed here; app code (including the old
        // 'admin'/'content' buckets) is left to Rollup's automatic per-entry
        // chunking. Those components are already behind dynamic import() in
        // router.ts, so they still code-split on their own — explicitly
        // grouping them by static file path was what caused shared modules
        // like vue-i18n to get merged into the 'admin' chunk (since it was
        // forced to contain AdminUsers.vue regardless of the real import
        // graph), which then dragged 'admin' — and its own Firebase usage —
        // into every entry that happened to share those modules, including
        // the embed bundle.
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined
          }
          // Vendor chunks - rarely change, good for caching
          if (/[/\\](vue|vue-router|vuex)[/\\]/.test(id)) {return 'vendor-vue'}
          if (/[/\\](axios|js-cookie)[/\\]/.test(id)) {return 'vendor-utils'}
          if (/[/\\]firebase[/\\]/.test(id)) {return 'vendor-firebase'}
          // Editor chunk - only loaded when needed
          if (/[/\\](ace-builds|vue3-ace-editor)[/\\]/.test(id)) {return 'editor'}
          return undefined
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

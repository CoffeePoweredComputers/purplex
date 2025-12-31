import type { KnipConfig } from 'knip';
import { parse } from 'vue/compiler-sfc';

/**
 * Knip configuration for Vue 3 + TypeScript dead code detection.
 *
 * This configuration:
 * 1. Uses vue/compiler-sfc to extract script blocks from .vue files
 * 2. Defines entry points for the application
 * 3. Ignores test files from production analysis
 *
 * Run: npx knip
 * Auto-fix: npx knip --fix
 */
const config: KnipConfig = {
  entry: [
    'src/main.ts',
    'src/router.ts',
  ],
  project: ['src/**/*.{ts,vue}'],

  // Vue SFC compiler to extract script content for analysis
  compilers: {
    vue: (text: string, filename: string) => {
      const { descriptor } = parse(text, { filename, sourceMap: false });
      const scripts: string[] = [];

      // Extract regular <script> block
      if (descriptor.script?.content) {
        scripts.push(descriptor.script.content);
      }

      // Extract <script setup> block
      if (descriptor.scriptSetup?.content) {
        scripts.push(descriptor.scriptSetup.content);
      }

      return scripts.join('\n');
    },
  },

  // Ignore patterns
  ignore: [
    '**/node_modules/**',
    '**/*.test.ts',
    '**/*.spec.ts',
    '**/tests/**',
    '**/__tests__/**',
  ],

  // Ignore specific dependencies that are used dynamically
  ignoreDependencies: [
    'concurrently', // Used in npm scripts only
  ],

  // Ignore exports that are intentionally kept (barrel files, future use, i18n)
  ignoreExportsUsedInFile: true,
};

export default config;

/**
 * Architectural tests to prevent common anti-patterns.
 *
 * Bug Prevention:
 * - Bug 4: NotificationToast was duplicated in multiple components,
 *   causing window.$notify to be deleted when one instance unmounts,
 *   breaking toasts for the entire app.
 *
 * Singleton Pattern:
 * - Components that set global state (window.$notify, window.$modal, etc.)
 *   should only be mounted ONCE, typically in App.vue
 * - Mounting them in other components causes race conditions and
 *   unmount conflicts
 *
 * These tests scan the codebase to prevent singleton component duplication.
 */

import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const SRC_DIR = path.resolve(__dirname, '..');

/**
 * Recursively find all Vue files in a directory.
 */
function findVueFiles(dir: string): string[] {
  const files: string[] = [];

  function scan(currentDir: string): void {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);

      // Skip node_modules and test directories
      if (entry.name === 'node_modules' || entry.name === '__tests__') {
        continue;
      }

      if (entry.isDirectory()) {
        scan(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.vue')) {
        files.push(fullPath);
      }
    }
  }

  scan(dir);
  return files;
}

/**
 * Check if a Vue file imports a specific component.
 */
function fileImportsComponent(filePath: string, componentName: string): boolean {
  const content = fs.readFileSync(filePath, 'utf-8');

  // Check for various import patterns:
  // import NotificationToast from '...'
  // import { NotificationToast } from '...'
  const importPattern = new RegExp(
    `import\\s+(?:\\{[^}]*)?${componentName}[^}]*\\}?\\s+from`,
    'i'
  );

  // Check for component usage in template
  // <NotificationToast> or <NotificationToast />
  // <notification-toast> or <notification-toast />
  const kebabCase = componentName.replace(/([A-Z])/g, '-$1').toLowerCase().substring(1);
  const templatePattern = new RegExp(`<${componentName}[\\s/>]|<${kebabCase}[\\s/>]`, 'i');

  return importPattern.test(content) || templatePattern.test(content);
}

/**
 * Check if a Vue file sets window.$ properties (singleton pattern).
 */
function usesWindowGlobal(filePath: string): { file: string; matches: string[] } | null {
  const content = fs.readFileSync(filePath, 'utf-8');

  // Match window.$something = or delete window.$something
  const globalPattern = /window\.\$\w+\s*=/g;
  const matches = content.match(globalPattern);

  if (matches && matches.length > 0) {
    return {
      file: path.relative(SRC_DIR, filePath),
      matches: [...new Set(matches)], // Unique matches
    };
  }

  return null;
}

describe('Singleton Component Architecture', () => {
  /**
   * SINGLETON COMPONENTS:
   *
   * These components set global state (window.$notify, etc.) and should
   * only be used in App.vue. Adding them elsewhere causes the bug where
   * the global is deleted when one instance unmounts.
   */
  const SINGLETON_COMPONENTS: Record<string, string> = {
    NotificationToast: 'Sets window.$notify on mount, deletes on unmount',
    // Add other singleton components here as they are identified
  };

  const ALLOWED_FILES = ['App.vue'];

  for (const [componentName, reason] of Object.entries(SINGLETON_COMPONENTS)) {
    describe(`${componentName} singleton`, () => {
      it(`should only be used in allowed files (${ALLOWED_FILES.join(', ')})`, () => {
        const vueFiles = findVueFiles(SRC_DIR);

        const usages: string[] = [];

        for (const file of vueFiles) {
          const fileName = path.basename(file);

          // Skip the component's own file
          if (fileName === `${componentName}.vue`) {
            continue;
          }

          if (fileImportsComponent(file, componentName)) {
            usages.push(path.relative(SRC_DIR, file));
          }
        }

        // Filter to only non-allowed files
        const invalidUsages = usages.filter((f) => !ALLOWED_FILES.includes(path.basename(f)));

        if (invalidUsages.length > 0) {
          const errorMessage = [
            `Singleton component "${componentName}" found in ${invalidUsages.length} file(s) outside App.vue:`,
            '',
            ...invalidUsages.map((f) => `  - ${f}`),
            '',
            `Reason: ${reason}`,
            '',
            'Singleton components should only be mounted in App.vue.',
            'Mounting them elsewhere causes global state conflicts.',
          ].join('\n');

          throw new Error(errorMessage);
        }

        expect(invalidUsages).toHaveLength(0);
      });
    });
  }

  describe('window.$ global detection', () => {
    it('should identify all components that use window.$ globals', () => {
      /**
       * This test helps identify NEW singleton patterns.
       * Components that set window.$ should be reviewed and potentially
       * added to SINGLETON_COMPONENTS.
       */
      const vueFiles = findVueFiles(SRC_DIR);
      const globalSetters: { file: string; matches: string[] }[] = [];

      for (const file of vueFiles) {
        const result = usesWindowGlobal(file);
        if (result) {
          globalSetters.push(result);
        }
      }

      // Known singleton files
      const knownSingletons = ['components/NotificationToast.vue'];

      // Filter to find unexpected global setters
      const unknownGlobalSetters = globalSetters.filter(
        (g) => !knownSingletons.some((known) => g.file.includes(known))
      );

      if (unknownGlobalSetters.length > 0) {
        // This is a warning, not a failure - helps identify new singletons
        console.warn('\nFound components using window.$ pattern that are not registered as singletons:');
        for (const setter of unknownGlobalSetters) {
          console.warn(`  ${setter.file}: ${setter.matches.join(', ')}`);
        }
        console.warn('\nConsider adding these to SINGLETON_COMPONENTS if they should be singletons.\n');
      }

      // Log all global setters for visibility
      console.log('\nAll components using window.$ globals:');
      for (const setter of globalSetters) {
        console.log(`  ${setter.file}: ${setter.matches.join(', ')}`);
      }

      // The test passes - this is informational
      expect(true).toBe(true);
    });
  });
});

describe('Component import patterns', () => {
  it('should verify NotificationToast is only imported in App.vue', () => {
    /**
     * Direct check for the specific bug that occurred.
     */
    const vueFiles = findVueFiles(SRC_DIR);

    const importingFiles: string[] = [];

    for (const file of vueFiles) {
      if (fileImportsComponent(file, 'NotificationToast')) {
        const relativePath = path.relative(SRC_DIR, file);
        // Exclude the component itself
        if (!relativePath.endsWith('NotificationToast.vue')) {
          importingFiles.push(relativePath);
        }
      }
    }

    // Only App.vue should import NotificationToast
    const expectedImports = ['App.vue'];
    const unexpectedImports = importingFiles.filter((f) => !expectedImports.includes(f));

    if (unexpectedImports.length > 0) {
      throw new Error(
        `NotificationToast should only be imported in App.vue, but was found in:\n` +
          unexpectedImports.map((f) => `  - ${f}`).join('\n') +
          `\n\nThis was Bug 4: Duplicate NotificationToast causes window.$notify to be deleted.`
      );
    }

    expect(unexpectedImports).toHaveLength(0);
    expect(importingFiles).toContain('App.vue');
  });
});

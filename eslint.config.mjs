import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: [
      '**/node_modules/**',
      '**/.next/**',
      '**/dist/**',
      '**/src/generated/**',
      '**/coverage/**',
      '**/.turbo/**',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['scripts/**/*.mjs', '*.mjs'],
    languageOptions: { globals: globals.nodeBuiltin },
    rules: { 'no-undef': 'error' },
  },
  {
    files: ['apps/worker/**/*.ts', 'packages/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: [
                '@smart-catering/api',
                '@smart-catering/api/**',
                '**/apps/api/**',
                '**/api/app/**',
                '**/api/lib/**',
                '**/api/modules/**',
                '**/api/integrations/**',
                '**/api/dist/**',
              ],
              message: 'Worker and shared packages must not depend on apps/api internals.',
            },
          ],
        },
      ],
    },
  },
);

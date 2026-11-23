import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';

const eslintConfig = tseslint.config(
  {
    ignores: ['**/node_modules/**', '**/dist/**', '**/coverage/**'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: { globals: globals.nodeBuiltin },
  },
  {
    files: ['src/**/*.ts', 'modules/**/*.ts', 'integrations/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: [
                '@smart-catering/web',
                '@smart-catering/web/**',
                '@smart-catering/worker',
                '@smart-catering/worker/**',
                '@smart-catering/ai-service',
                '@smart-catering/ai-service/**',
                '**/apps/web/**',
                '**/apps/worker/**',
                '**/apps/ai-service/**',
                '**/web/app/**',
                '**/worker/src/**',
              ],
              message:
                'API (@smart-catering/api) must not import code from apps/web, apps/worker, or apps/ai-service.',
            },
          ],
        },
      ],
    },
  },
);

export default eslintConfig;

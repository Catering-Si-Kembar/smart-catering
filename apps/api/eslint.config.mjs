import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';

const eslintConfig = [
  {
    ignores: ['**/node_modules/**', '**/.next/**', '**/dist/**', '**/coverage/**', 'next-env.d.ts'],
  },
  ...nextVitals,
  ...nextTs,
  {
    files: [
      'app/**/*.ts',
      'app/**/*.tsx',
      'lib/**/*.ts',
      'lib/**/*.tsx',
      'modules/**/*.ts',
      'modules/**/*.tsx',
      'integrations/**/*.ts',
      'integrations/**/*.tsx',
    ],
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
];

export default eslintConfig;

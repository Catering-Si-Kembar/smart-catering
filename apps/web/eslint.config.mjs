import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';

const eslintConfig = [
  {
    ignores: ['**/node_modules/**', '**/.next/**', '**/dist/**', '**/coverage/**', 'next-env.d.ts'],
  },
  ...nextVitals,
  ...nextTs,
  {
    files: ['app/**/*.ts', 'app/**/*.tsx'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: [
                '@smart-catering/db',
                '@smart-catering/db/**',
                '@smart-catering/api',
                '@smart-catering/api/**',
                '@smart-catering/worker',
                '@smart-catering/worker/**',
                '**/packages/db/**',
                '**/apps/api/**',
                '**/apps/worker/**',
                '**/api/app/**',
                '**/api/modules/**',
                '**/api/integrations/**',
                '**/worker/src/**',
                '@prisma/*',
                'prisma',
                'pg',
              ],
              message:
                'Frontend (@smart-catering/web) must not import database packages, server drivers, or other app internals.',
            },
          ],
        },
      ],
    },
  },
];

export default eslintConfig;

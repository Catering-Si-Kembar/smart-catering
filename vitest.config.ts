import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['apps/api/**/*.test.ts', 'apps/worker/src/**/*.test.ts', 'scripts/**/*.test.mjs'],
    coverage: {
      provider: 'v8',
      include: [
        'apps/api/lib/**/*.ts',
        'apps/api/app/**/route.ts',
        'apps/worker/src/environment.ts',
        'scripts/service-environment.mjs',
      ],
      reporter: ['text', 'lcov', 'html'],
      thresholds: { statements: 80, branches: 80, functions: 80, lines: 80 },
    },
  },
});

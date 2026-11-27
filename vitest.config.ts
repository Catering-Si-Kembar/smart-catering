import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: [
      'apps/api/src/**/*.test.ts',
      'apps/worker/src/**/*.test.ts',
      'apps/web/lib/**/*.test.ts',
      'scripts/**/*.test.mjs',
    ],
    coverage: {
      provider: 'v8',
      include: [
        'apps/api/src/**/*.ts',
        'apps/worker/src/environment.ts',
        'apps/web/lib/**/*.ts',
        'scripts/service-environment.mjs',
        'scripts/check-vps-compose.mjs',
      ],
      exclude: ['apps/api/src/**/*.test.ts', 'apps/web/lib/**/*.test.ts'],
      reporter: ['text', 'lcov', 'html'],
      thresholds: { statements: 80, branches: 80, functions: 80, lines: 80 },
    },
  },
});

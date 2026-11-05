import { readFileSync } from 'node:fs';
import { parseEnv } from 'node:util';
import { defineConfig } from 'prisma/config';

function readDatabaseUrl(): string | undefined {
  if (process.env.DATABASE_URL !== undefined) return process.env.DATABASE_URL.trim();
  try {
    const root = parseEnv(readFileSync(new URL('../../.env', import.meta.url), 'utf8'));
    return root.DATABASE_URL?.trim();
  } catch (error) {
    if (error instanceof Error && 'code' in error && error.code === 'ENOENT') return undefined;
    throw new Error('Cannot read the root backend .env for Prisma tooling.', { cause: error });
  }
}

const BUILD_SYNTAX_FALLBACK_DATABASE_URL =
  'postgresql://build:build@127.0.0.1:5432/smart_catering_build?schema=public';

const command = process.argv[2];
const isOfflineCommand = command === 'generate' || command === 'validate';
const databaseUrl =
  readDatabaseUrl() || (isOfflineCommand ? BUILD_SYNTAX_FALLBACK_DATABASE_URL : undefined);

if (!databaseUrl) {
  throw new Error('DATABASE_URL is required for Prisma commands other than generate and validate.');
}

export default defineConfig({
  schema: 'prisma/schema.prisma',
  migrations: {
    path: 'prisma/migrations',
  },
  datasource: {
    url: databaseUrl,
  },
});

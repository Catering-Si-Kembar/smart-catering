import { PrismaPg } from '@prisma/adapter-pg';
import { PrismaClient } from './generated/prisma/client.js';

const PLACEHOLDER_PASSWORD_TOKEN = 'CHANGE_ME_LOCAL_DB_PASSWORD';
const SUPPORTED_PROTOCOLS: Readonly<Record<string, true>> = {
  'postgres:': true,
  'postgresql:': true,
};

type GlobalPrismaStore = {
  __smartCateringPrismaClient?: PrismaClient;
};

const globalForPrisma = globalThis as unknown as GlobalPrismaStore;

export function resolveDatabaseUrl(rawUrl: string | undefined = process.env.DATABASE_URL): string {
  const trimmed = rawUrl?.trim();
  if (!trimmed) {
    throw new Error(
      'DATABASE_URL is required before calling getDb(). Set a valid PostgreSQL connection string in the process environment.',
    );
  }

  if (trimmed.includes(PLACEHOLDER_PASSWORD_TOKEN)) {
    throw new Error(
      `DATABASE_URL still contains placeholder "${PLACEHOLDER_PASSWORD_TOKEN}". Replace it with your actual PostgreSQL password.`,
    );
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new Error('DATABASE_URL must be a syntactically valid PostgreSQL connection URL.');
  }

  if (!SUPPORTED_PROTOCOLS[parsed.protocol]) {
    throw new Error(
      `DATABASE_URL protocol must be "postgresql:" or "postgres:", received "${parsed.protocol}".`,
    );
  }

  if (!parsed.hostname || !parsed.pathname || parsed.pathname === '/') {
    throw new Error('DATABASE_URL must include a target PostgreSQL host and database name.');
  }

  return trimmed;
}

function createPrismaClient(connectionString: string): PrismaClient {
  const adapter = new PrismaPg({ connectionString });
  return new PrismaClient({ adapter });
}

export function getDb(): PrismaClient {
  if (globalForPrisma.__smartCateringPrismaClient) {
    return globalForPrisma.__smartCateringPrismaClient;
  }

  const connectionString = resolveDatabaseUrl(process.env.DATABASE_URL);
  const client = createPrismaClient(connectionString);
  globalForPrisma.__smartCateringPrismaClient = client;
  return client;
}

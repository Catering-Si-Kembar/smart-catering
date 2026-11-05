import { readFileSync } from 'node:fs';
import { parseEnv } from 'node:util';
import { fileURLToPath } from 'node:url';

const ROOT_ENV_PATH = fileURLToPath(new URL('../.env', import.meta.url));
const DOCS_KEYS = ['DOCS_ENABLED', 'DOCS_USERNAME', 'DOCS_PASSWORD'];
const SERVICE_KEYS = {
  web: ['API_BASE_URL', 'NEXT_PUBLIC_APP_NAME'],
  api: [
    'API_HOST',
    'API_PORT',
    'DATABASE_URL',
    'AI_SERVICE_URL',
    'WAHA_BASE_URL',
    'WAHA_API_KEY',
    ...DOCS_KEYS,
  ],
  ai: ['AI_HOST', 'AI_PORT', 'CHROMA_URL', ...DOCS_KEYS],
  worker: ['WORKER_HOST', 'WORKER_PORT'],
};
const MODES = new Set(['dev', 'build', 'start']);
const SYSTEM_KEYS = new Set([
  'PATH',
  'PATHEXT',
  'SYSTEMROOT',
  'WINDIR',
  'COMSPEC',
  'TEMP',
  'TMP',
  'TMPDIR',
  'HOME',
  'USERPROFILE',
  'HOMEDRIVE',
  'HOMEPATH',
  'APPDATA',
  'LOCALAPPDATA',
  'PROGRAMFILES',
  'PROGRAMFILES(X86)',
  'PROGRAMDATA',
  'LANG',
  'TERM',
  'COLORTERM',
  'FORCE_COLOR',
  'NO_COLOR',
  'CI',
  'NODE_OPTIONS',
  'NODE_EXTRA_CA_CERTS',
  'SSL_CERT_FILE',
  'SSL_CERT_DIR',
  'HTTP_PROXY',
  'HTTPS_PROXY',
  'ALL_PROXY',
  'NO_PROXY',
]);
const LISTENERS = {
  api: { prefix: 'API', port: 3001 },
  ai: { prefix: 'AI', port: 8001 },
  worker: { prefix: 'WORKER', port: 3002 },
};

export function readBackendEnvironment(file = ROOT_ENV_PATH) {
  try {
    return parseEnv(readFileSync(file, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return {};
    throw new Error('Cannot read the root backend .env file.', { cause: error });
  }
}

export function createServiceEnvironment(service, mode, fileValues = {}, inherited = process.env) {
  if (!Object.hasOwn(SERVICE_KEYS, service) || !MODES.has(mode)) {
    throw new Error('Unsupported service or launch mode.');
  }
  const system = Object.fromEntries(
    Object.entries(inherited).filter(([key, value]) => {
      const name = key.toUpperCase();
      return (
        typeof value === 'string' &&
        (SYSTEM_KEYS.has(name) ||
          name.startsWith('LC_') ||
          (service === 'ai' && name.startsWith('UV_')) ||
          (service === 'web' && name.startsWith('NEXT_PUBLIC_')))
      );
    }),
  );
  const scoped = Object.fromEntries(
    SERVICE_KEYS[service].flatMap((key) => {
      const value = inherited[key] ?? (service === 'web' ? undefined : fileValues[key]);
      return typeof value === 'string' ? [[key, value]] : [];
    }),
  );
  const production = mode !== 'dev';
  return {
    ...system,
    ...scoped,
    NODE_ENV: production ? 'production' : 'development',
    ...(service === 'ai' ? { APP_ENV: production ? 'production' : 'development' } : {}),
    ...(service === 'api' || service === 'web' ? { NEXT_TELEMETRY_DISABLED: '1' } : {}),
  };
}

export function readServiceListener(service, environment) {
  const listener = LISTENERS[service];
  if (!listener) throw new Error('Unsupported listener service.');
  const hostKey = `${listener.prefix}_HOST`;
  const portKey = `${listener.prefix}_PORT`;
  const host = (environment[hostKey] ?? '127.0.0.1').trim();
  const rawPort = (environment[portKey] ?? String(listener.port)).trim();
  const port = Number(rawPort);
  if (!host) throw new Error(`${hostKey} must not be blank.`);
  if (!/^[0-9]+$/.test(rawPort) || !Number.isSafeInteger(port) || port < 1 || port > 65535) {
    throw new Error(`${portKey} must be an integer from 1 to 65535.`);
  }
  return { host, port };
}

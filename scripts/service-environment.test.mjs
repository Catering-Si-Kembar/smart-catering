import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, test } from 'vitest';
import {
  createServiceEnvironment,
  readBackendEnvironment,
  readServiceListener,
} from './service-environment.mjs';

const backendValues = Object.freeze({
  DATABASE_URL: 'postgresql://private-db',
  DOCS_PASSWORD: 'private-docs-password',
  DOCS_USERNAME: 'private-docs-user',
  DOCS_ENABLED: 'true',
  WAHA_API_KEY: 'private-whatsapp-key',
  CHROMA_URL: 'http://private-chroma:8000',
  AI_SERVICE_URL: 'http://private-ai:8001',
  API_BASE_URL: 'http://must-not-reach-web',
  NEXT_PUBLIC_APP_NAME: 'must-not-reach-web',
  UNKNOWN_SECRET: 'private-unknown-value',
  API_PORT: '3101',
  AI_PORT: '8101',
  WORKER_PORT: '3102',
});

const inherited = Object.freeze({
  PATH: '/runtime/bin',
  SystemRoot: 'C:\\Windows',
  HOSTNAME: 'shell-machine-name',
  PORT: '9999',
  DATABASE_URL: 'postgresql://injected-db',
  DOCS_PASSWORD: 'injected-docs-password',
  WAHA_API_KEY: 'injected-whatsapp-key',
  UNRELATED_SECRET: 'injected-unrelated-secret',
  API_BASE_URL: 'http://frontend-api:3101',
  NEXT_PUBLIC_APP_NAME: 'Frontend name',
  UV_CACHE_DIR: '/uv-cache',
});

describe('service environment ownership', () => {
  test('frontend cannot receive backend file values or inherited backend secrets', () => {
    const environment = createServiceEnvironment('web', 'dev', backendValues, inherited);
    expect(environment.API_BASE_URL).toBe('http://frontend-api:3101');
    expect(environment.NEXT_PUBLIC_APP_NAME).toBe('Frontend name');
    for (const key of [
      'DATABASE_URL',
      'DOCS_PASSWORD',
      'WAHA_API_KEY',
      'CHROMA_URL',
      'UNKNOWN_SECRET',
      'UNRELATED_SECRET',
      'UV_CACHE_DIR',
      'PORT',
      'HOSTNAME',
    ]) {
      expect(environment).not.toHaveProperty(key);
    }
    const rootOnly = createServiceEnvironment('web', 'dev', backendValues, {});
    expect(rootOnly).not.toHaveProperty('API_BASE_URL');
    expect(rootOnly).not.toHaveProperty('NEXT_PUBLIC_APP_NAME');
  });

  test('worker receives listener configuration but no service credentials', () => {
    const environment = createServiceEnvironment('worker', 'start', backendValues, inherited);
    expect(environment.WORKER_PORT).toBe('3102');
    expect(environment.NODE_ENV).toBe('production');
    for (const key of [
      'DATABASE_URL',
      'DOCS_PASSWORD',
      'DOCS_USERNAME',
      'DOCS_ENABLED',
      'WAHA_API_KEY',
      'AI_SERVICE_URL',
      'CHROMA_URL',
      'API_BASE_URL',
      'UNKNOWN_SECRET',
      'UNRELATED_SECRET',
      'UV_CACHE_DIR',
    ]) {
      expect(environment).not.toHaveProperty(key);
    }
  });

  test('API uses process overrides without receiving AI-only or arbitrary secrets', () => {
    const environment = createServiceEnvironment('api', 'dev', backendValues, inherited);
    expect(environment.DATABASE_URL).toBe('postgresql://injected-db');
    expect(environment.DOCS_PASSWORD).toBe('injected-docs-password');
    expect(environment.WAHA_API_KEY).toBe('injected-whatsapp-key');
    expect(environment.API_PORT).toBe('3101');
    expect(environment.NODE_ENV).toBe('development');
    for (const key of [
      'CHROMA_URL',
      'WORKER_PORT',
      'UNKNOWN_SECRET',
      'UNRELATED_SECRET',
      'UV_CACHE_DIR',
      'PORT',
      'HOSTNAME',
    ]) {
      expect(environment).not.toHaveProperty(key);
    }
  });

  test('AI receives Chroma and uv settings without Node API secrets', () => {
    const environment = createServiceEnvironment('ai', 'start', backendValues, inherited);
    expect(environment.CHROMA_URL).toBe('http://private-chroma:8000');
    expect(environment.DOCS_PASSWORD).toBe('injected-docs-password');
    expect(environment.APP_ENV).toBe('production');
    expect(environment.AI_PORT).toBe('8101');
    expect(environment.UV_CACHE_DIR).toBe('/uv-cache');
    for (const key of [
      'DATABASE_URL',
      'WAHA_API_KEY',
      'AI_SERVICE_URL',
      'UNKNOWN_SECRET',
      'UNRELATED_SECRET',
      'API_BASE_URL',
    ]) {
      expect(environment).not.toHaveProperty(key);
    }
  });

  test('preserves required OS variables without mutating its input objects', () => {
    const environment = createServiceEnvironment('api', 'build', backendValues, inherited);
    expect(environment.PATH).toBe('/runtime/bin');
    expect(environment.SystemRoot).toBe('C:\\Windows');
    expect(environment.NODE_ENV).toBe('production');
    expect(backendValues.DOCS_PASSWORD).toBe('private-docs-password');
    expect(inherited.DOCS_PASSWORD).toBe('injected-docs-password');
    expect(inherited.HOSTNAME).toBe('shell-machine-name');
  });

  test('allows an explicitly empty injected setting to override the file', () => {
    expect(
      createServiceEnvironment('api', 'dev', backendValues, { DOCS_ENABLED: '' }).DOCS_ENABLED,
    ).toBe('');
  });

  test.each([
    ['unknown', 'dev'],
    ['api', 'unknown'],
  ])('rejects unsupported service or mode %s/%s', (service, mode) => {
    expect(() => createServiceEnvironment(service, mode, {}, {})).toThrow();
  });
});

describe('backend dotenv reading', () => {
  test('reads quoted secrets literally without expanding another variable', () => {
    const directory = mkdtempSync(join(tmpdir(), 'smart-catering-env-'));
    try {
      const file = join(directory, '.env');
      writeFileSync(
        file,
        'DATABASE_URL="private-value"\nDOCS_PASSWORD="${DATABASE_URL}"\nDOCS_ENABLED=\n',
      );
      const environment = readBackendEnvironment(file);
      expect(environment.DOCS_PASSWORD).toBe('${DATABASE_URL}');
      expect(environment.DOCS_ENABLED).toBe('');
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  test('missing root dotenv does not block injected container configuration', () => {
    const directory = mkdtempSync(join(tmpdir(), 'smart-catering-env-'));
    try {
      const environment = createServiceEnvironment(
        'api',
        'start',
        readBackendEnvironment(join(directory, '.env')),
        { DATABASE_URL: 'postgresql://container-db' },
      );
      expect(environment.DATABASE_URL).toBe('postgresql://container-db');
      expect(environment.NODE_ENV).toBe('production');
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });

  test('does not silently ignore an unreadable non-file source', () => {
    const directory = mkdtempSync(join(tmpdir(), 'smart-catering-env-'));
    try {
      const invalidSource = join(directory, '.env');
      mkdirSync(invalidSource);
      expect(() => readBackendEnvironment(invalidSource)).toThrow();
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });
});

describe('service listener configuration', () => {
  test.each([
    ['api', 3001],
    ['ai', 8001],
    ['worker', 3002],
  ])('uses an independent default listener for %s', (service, port) => {
    expect(readServiceListener(service, {})).toEqual({ host: '127.0.0.1', port });
  });

  test('reads distinct API/AI ports and never uses inherited generic PORT/HOSTNAME', () => {
    expect(
      readServiceListener('api', {
        API_HOST: ' localhost ',
        API_PORT: '3101',
        PORT: '9999',
        HOSTNAME: 'wrong-host',
      }),
    ).toEqual({ host: 'localhost', port: 3101 });
    expect(readServiceListener('ai', { AI_HOST: '127.0.0.2', AI_PORT: '8101' })).toEqual({
      host: '127.0.0.2',
      port: 8101,
    });
  });

  test.each(['0', '65536', '1.5', '1e3', '0x100', '', 'not-a-port'])(
    'rejects invalid port %s without echoing configuration',
    (port) => {
      expect(() => readServiceListener('api', { API_PORT: port })).toThrow(/API_PORT/);
    },
  );

  test('accepts TCP boundary ports', () => {
    expect(readServiceListener('worker', { WORKER_PORT: '1' }).port).toBe(1);
    expect(readServiceListener('ai', { AI_PORT: '65535' }).port).toBe(65535);
  });

  test('rejects an explicitly blank host', () => {
    expect(() => readServiceListener('worker', { WORKER_HOST: '  ' })).toThrow(/WORKER_HOST/);
  });
});

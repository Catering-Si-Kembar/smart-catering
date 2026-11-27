import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, test } from 'vitest';
import {
  REQUIRED_GITIGNORE_ENTRIES,
  findForbiddenTrackedPaths,
  runSecretsHygieneCheck,
  scanTextForSecrets,
  validateEnvTemplateEmptySecrets,
  validateGitignoreContent,
} from './check-secrets-hygiene.mjs';

describe('secrets hygiene guard (OPS-01)', () => {
  test('validates required .gitignore protection entries', () => {
    const valid = REQUIRED_GITIGNORE_ENTRIES.join('\n');
    expect(validateGitignoreContent(valid)).toEqual([]);

    const missing = validateGitignoreContent('.env\n# comment\n');
    expect(missing.length).toBeGreaterThanOrEqual(4);
    expect(missing.every((item) => item.rule === 'gitignore-missing-entry')).toBe(true);
  });

  test('flags forbidden tracked files while allowing .env.example and data/raw/README.md', () => {
    const cleanPaths = [
      '.env.example',
      'apps/web/.env.example',
      'data/raw/README.md',
      'apps/ai-service/app/main.py',
    ];
    expect(findForbiddenTrackedPaths(cleanPaths)).toEqual([]);

    const badPaths = [
      '.env',
      'apps/web/.env',
      '.env.production',
      'data/raw/umkm_orders_2026.csv',
      'infra/tls/server.pem',
      'certs/private.key',
      'apps/ai-service/app/ml/relevance/artifacts/relevance_model.joblib',
      'models/backup.pkl',
    ];
    const findings = findForbiddenTrackedPaths(badPaths);
    expect(findings).toHaveLength(badPaths.length);
    const rules = new Set(findings.map((item) => item.rule));
    expect(rules.has('tracked-env-file')).toBe(true);
    expect(rules.has('tracked-raw-umkm-data')).toBe(true);
    expect(rules.has('tracked-private-key-file')).toBe(true);
    expect(rules.has('tracked-binary-ml-artifact')).toBe(true);
  });

  test('ensures sensitive values in .env.example templates stay empty', () => {
    const safeTemplate = 'DATABASE_URL=\nLLM_API_KEY=\nMODAL_API_KEY=\nAI_PORT=8001\n';
    expect(validateEnvTemplateEmptySecrets('.env.example', safeTemplate)).toEqual([]);

    const leakedTemplate = 'DATABASE_URL=postgresql://user:pass@host:5432/db\nLLM_API_KEY=abc\n';
    const findings = validateEnvTemplateEmptySecrets('.env.example', leakedTemplate);
    expect(findings).toHaveLength(2);
    expect(findings.map((item) => item.rule)).toEqual([
      'non-empty-env-template-secret',
      'non-empty-env-template-secret',
    ]);
  });

  test('detects high-confidence secret patterns without echoing secret values', () => {
    const fakeGithub = `ghp_${'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8'}`;
    const fakeGoogle = `AIza${'0123456789abcdefABCDEF_-0123456789a'}`;
    const fakeKeyHeader = ['-----BEGIN', 'RSA PRIVATE KEY-----'].join(' ');
    const fakeOpenAi = `sk-proj-${'abcdefghijklmnopqrstuvwxyz123456'}`;
    const sample = [
      'const safe = "hello";',
      `const a = "${fakeGithub}";`,
      `const b = "${fakeGoogle}";`,
      fakeKeyHeader,
      `const c = "${fakeOpenAi}";`,
    ].join('\n');

    const findings = scanTextForSecrets('src/example.ts', sample);
    expect(findings).toHaveLength(4);
    expect(findings.map((item) => item.line)).toEqual([2, 3, 4, 5]);
    const serialized = JSON.stringify(findings);
    expect(serialized).not.toContain(fakeGithub);
    expect(serialized).not.toContain(fakeGoogle);
    expect(serialized).not.toContain(fakeOpenAi);
  });

  test('runs end-to-end check on temporary clean and dirty repositories', () => {
    const tempDir = mkdtempSync(join(tmpdir(), 'smart-catering-hygiene-'));
    try {
      mkdirSync(join(tempDir, 'data', 'raw'), { recursive: true });
      writeFileSync(join(tempDir, '.gitignore'), `${REQUIRED_GITIGNORE_ENTRIES.join('\n')}\n`);
      writeFileSync(join(tempDir, '.env.example'), 'DATABASE_URL=\nMODAL_API_KEY=\n');
      writeFileSync(join(tempDir, 'data', 'raw', 'README.md'), '# Raw data placeholder\n');
      writeFileSync(join(tempDir, 'logo.png'), Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x00]));

      const clean = runSecretsHygieneCheck(tempDir, [
        '.gitignore',
        '.env.example',
        'data/raw/README.md',
        'logo.png',
        'package-lock.json',
      ]);
      expect(clean.ok).toBe(true);
      expect(clean.findings).toEqual([]);

      writeFileSync(join(tempDir, '.env.example'), 'MODAL_API_KEY=hardcoded-secret\n');
      const dirty = runSecretsHygieneCheck(tempDir, ['.gitignore', '.env.example', '.env']);
      expect(dirty.ok).toBe(false);
      expect(dirty.findings.some((f) => f.rule === 'tracked-env-file')).toBe(true);
      expect(dirty.findings.some((f) => f.rule === 'non-empty-env-template-secret')).toBe(true);
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test('current repository passes secrets hygiene check with zero findings', () => {
    const result = runSecretsHygieneCheck();
    expect(result.scannedFiles).toBeGreaterThan(20);
    expect(result.findings).toEqual([]);
    expect(result.ok).toBe(true);
  });
});

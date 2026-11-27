import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseEnv } from 'node:util';

const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url));

export const REQUIRED_GITIGNORE_ENTRIES = Object.freeze([
  '.env',
  '.env.*',
  '!.env.example',
  'data/raw/*',
  '!data/raw/README.md',
  '*.pkl',
  '*.joblib',
]);

export const ENV_TEMPLATE_SENSITIVE_KEYS = Object.freeze([
  'DATABASE_URL',
  'VPS_DATABASE_URL',
  'POSTGRES_PASSWORD',
  'WAHA_API_KEY',
  'INTERNAL_SERVICE_SECRET',
  'LLM_API_KEY',
  'MODAL_API_KEY',
  'SMTP_PASS',
  'DOCS_PASSWORD',
]);

const FORBIDDEN_TRACKED_PATH_RULES = Object.freeze([
  {
    id: 'tracked-env-file',
    pattern: /(?:^|\/)\.env(?:\.(?!example$)[^/]+)?$/i,
    message: 'Real .env file must never be tracked in Git (use .env.example templates only).',
  },
  {
    id: 'tracked-raw-umkm-data',
    pattern: /^data\/raw\/(?!README\.md$).+/i,
    message: 'Raw UMKM data files under data/raw/ must never be committed to Git.',
  },
  {
    id: 'tracked-private-key-file',
    pattern: /(?:^|\/)(?:id_rsa|id_ed25519|.*\.(?:pem|key|p12|pfx))$/i,
    message: 'Private key or certificate file must never be committed to Git.',
  },
  {
    id: 'tracked-binary-ml-artifact',
    pattern: /\.(?:joblib|pkl)$/i,
    message: 'Binary serialized ML artifact (*.joblib / *.pkl) must remain git-ignored.',
  },
]);

const SECRET_CONTENT_RULES = Object.freeze([
  {
    id: 'private-key-block',
    pattern: /-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----/,
    message: 'Embedded private key header detected.',
  },
  {
    id: 'github-classic-token',
    pattern: /\bgh[pousr]_[A-Za-z0-9]{36}\b/,
    message: 'GitHub personal/OAuth access token pattern detected.',
  },
  {
    id: 'github-fine-grained-pat',
    pattern: /\bgithub_pat_[A-Za-z0-9_]{22,}\b/,
    message: 'GitHub fine-grained personal access token pattern detected.',
  },
  {
    id: 'google-api-key',
    pattern: /\bAIza[0-9A-Za-z_-]{35}\b/,
    message: 'Google / Gemini API key pattern detected.',
  },
  {
    id: 'aws-access-key-id',
    pattern: /\bAKIA[0-9A-Z]{16}\b/,
    message: 'AWS access key ID pattern detected.',
  },
  {
    id: 'openai-project-or-anthropic-key',
    pattern: /\bsk-(?:proj|ant|live)-[A-Za-z0-9_-]{20,}\b/,
    message: 'Provider secret API key pattern (OpenAI/Anthropic/Stripe) detected.',
  },
  {
    id: 'modal-token-secret',
    pattern: /\b(?:ak|as)-[A-Za-z0-9]{20,}\b/,
    message: 'Modal API token credential pattern detected.',
  },
]);

const TEXT_SCAN_SKIP_EXTENSIONS = new Set([
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.ico',
  '.pdf',
  '.woff',
  '.woff2',
  '.ttf',
  '.zip',
  '.tar',
  '.gz',
  '.whl',
]);

export function validateGitignoreContent(content) {
  const lines = new Set(
    content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0 && !line.startsWith('#')),
  );
  const missing = REQUIRED_GITIGNORE_ENTRIES.filter((entry) => !lines.has(entry));
  return missing.map((entry) => ({
    rule: 'gitignore-missing-entry',
    file: '.gitignore',
    line: 0,
    message: `Missing required .gitignore protection entry: ${entry}`,
  }));
}

export function findForbiddenTrackedPaths(trackedPaths) {
  const findings = [];
  for (const rawPath of trackedPaths) {
    const normalized = rawPath.replaceAll('\\', '/').trim();
    if (!normalized) continue;
    for (const rule of FORBIDDEN_TRACKED_PATH_RULES) {
      if (rule.pattern.test(normalized)) {
        findings.push({
          rule: rule.id,
          file: normalized,
          line: 0,
          message: rule.message,
        });
      }
    }
  }
  return findings;
}

export function validateEnvTemplateEmptySecrets(filePath, content) {
  const parsed = parseEnv(content);
  const findings = [];
  for (const key of ENV_TEMPLATE_SENSITIVE_KEYS) {
    const value = parsed[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      findings.push({
        rule: 'non-empty-env-template-secret',
        file: filePath,
        line: 0,
        message: `Sensitive variable ${key} must be empty in committed template ${filePath}.`,
      });
    }
  }
  return findings;
}

export function scanTextForSecrets(filePath, content) {
  const findings = [];
  const lines = content.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const lineText = lines[index];
    for (const rule of SECRET_CONTENT_RULES) {
      if (rule.pattern.test(lineText)) {
        findings.push({
          rule: rule.id,
          file: filePath,
          line: index + 1,
          message: rule.message,
        });
      }
    }
  }
  return findings;
}

function shouldScanFileContent(filePath) {
  const lower = filePath.toLowerCase();
  if (lower.endsWith('package-lock.json') || lower.endsWith('uv.lock')) {
    return false;
  }
  const dotIdx = lower.lastIndexOf('.');
  if (dotIdx !== -1 && TEXT_SCAN_SKIP_EXTENSIONS.has(lower.slice(dotIdx))) {
    return false;
  }
  return true;
}

function listTrackedFiles(rootDir) {
  const output = execFileSync('git', ['ls-files', '-z'], {
    cwd: rootDir,
    encoding: 'utf8',
    maxBuffer: 10 * 1024 * 1024,
  });
  return output.split('\0').filter((entry) => entry.length > 0);
}

export function runSecretsHygieneCheck(rootDir = REPO_ROOT, trackedFilesOverride = null) {
  const trackedFiles = trackedFilesOverride ?? listTrackedFiles(rootDir);
  const findings = [];

  const gitignorePath = resolve(rootDir, '.gitignore');
  const gitignoreContent = readFileSync(gitignorePath, 'utf8');
  findings.push(...validateGitignoreContent(gitignoreContent));
  findings.push(...findForbiddenTrackedPaths(trackedFiles));

  for (const relPath of trackedFiles) {
    const normalized = relPath.replaceAll('\\', '/');
    if (!shouldScanFileContent(normalized)) continue;
    const fullPath = resolve(rootDir, normalized);
    let content;
    try {
      content = readFileSync(fullPath, 'utf8');
    } catch {
      continue;
    }
    if (content.includes('\0')) continue;

    if (normalized === '.env.example' || normalized.endsWith('/.env.example')) {
      findings.push(...validateEnvTemplateEmptySecrets(normalized, content));
    }
    findings.push(...scanTextForSecrets(normalized, content));
  }

  return {
    scannedFiles: trackedFiles.length,
    findings,
    ok: findings.length === 0,
  };
}

function main() {
  const report = runSecretsHygieneCheck();
  if (!report.ok) {
    console.error(`Secrets hygiene check FAILED with ${report.findings.length} finding(s):`);
    for (const item of report.findings) {
      const location = item.line > 0 ? `${item.file}:${item.line}` : item.file;
      console.error(`  - [${item.rule}] ${location} — ${item.message}`);
    }
    process.exitCode = 1;
    return;
  }
  console.log(
    `Secrets hygiene check PASSED (${report.scannedFiles} tracked files verified, 0 findings).`,
  );
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));

const REQUIRED_SERVICES = ['caddy', 'postgres', 'chroma', 'waha', 'api', 'ai-service', 'worker'];

const INTERNAL_ONLY_SERVICES = ['postgres', 'chroma', 'ai-service', 'worker', 'waha'];
const DATA_ONLY_SERVICES = ['postgres', 'chroma'];
const REQUIRED_VOLUMES = [
  'smart_catering_vps_caddy_data',
  'smart_catering_vps_caddy_config',
  'smart_catering_vps_postgres_data',
  'smart_catering_vps_chroma_data',
  'smart_catering_vps_waha_sessions',
  'smart_catering_vps_waha_files',
];

const DIGEST_REGEX = /@sha256:[0-9a-f]{64}$/;
const ALLOWED_CADDY_PORTS = new Set(['80:80', '443:443', '443:443/udp']);
const REQUIRED_ENV_KEYS = {
  api: ['DATABASE_URL', 'AI_SERVICE_URL', 'INTERNAL_SERVICE_SECRET'],
  'ai-service': [
    'BACKEND_API_URL',
    'CHROMA_URL',
    'INTERNAL_SERVICE_SECRET',
    'LLM_API_KEY',
    'MODAL_SLM_BASE_URL',
    'MODAL_API_KEY',
  ],
  worker: ['API_BASE_URL', 'INTERNAL_SERVICE_SECRET'],
};

function stripQuotes(value) {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith("'") && trimmed.endsWith("'")) ||
    (trimmed.startsWith('"') && trimmed.endsWith('"'))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

export function parseTopLevelSections(yamlText) {
  const lines = yamlText.replace(/\r\n/g, '\n').split('\n');
  const sections = {};
  let currentSection = null;
  let currentItem = null;

  for (const rawLine of lines) {
    if (!rawLine.trim() || rawLine.trim().startsWith('#')) {
      continue;
    }

    const indent = rawLine.length - rawLine.trimStart().length;
    const trimmed = rawLine.trim();

    if (indent === 0) {
      const match = /^([A-Za-z0-9_-]+):/.exec(trimmed);
      currentSection = match ? match[1] : null;
      currentItem = null;
      if (currentSection && !sections[currentSection]) {
        sections[currentSection] = {};
      }
      continue;
    }

    if (!currentSection) {
      continue;
    }

    if (indent === 2) {
      const match = /^([A-Za-z0-9_-]+):/.exec(trimmed);
      if (match) {
        currentItem = match[1];
        sections[currentSection][currentItem] = [];
      }
      continue;
    }

    if (currentItem) {
      sections[currentSection][currentItem].push(rawLine);
    }
  }

  return sections;
}

function extractListItems(serviceLines, key) {
  const items = [];
  let active = false;
  let keyIndent = -1;

  for (const line of serviceLines) {
    const indent = line.length - line.trimStart().length;
    const trimmed = line.trim();

    if (!active) {
      if (trimmed === `${key}:`) {
        active = true;
        keyIndent = indent;
      }
      continue;
    }

    if (indent <= keyIndent) {
      break;
    }

    if (trimmed.startsWith('- ')) {
      items.push(stripQuotes(trimmed.slice(2)));
    }
  }

  return items;
}

function extractMapKeys(serviceLines, key) {
  const keys = new Set();
  let active = false;
  let keyIndent = -1;

  for (const line of serviceLines) {
    const indent = line.length - line.trimStart().length;
    const trimmed = line.trim();

    if (!active) {
      if (trimmed === `${key}:`) {
        active = true;
        keyIndent = indent;
      }
      continue;
    }

    if (indent <= keyIndent) {
      break;
    }

    const match = /^([A-Za-z0-9_]+):/.exec(trimmed);
    if (match) {
      keys.add(match[1]);
    }
  }

  return keys;
}

function findScalar(serviceLines, key) {
  for (const line of serviceLines) {
    const trimmed = line.trim();
    if (trimmed.startsWith(`${key}:`)) {
      return stripQuotes(trimmed.slice(key.length + 1));
    }
  }
  return null;
}

export function validateComposeVps(yamlText) {
  const findings = [];
  const sections = parseTopLevelSections(yamlText);
  const services = sections.services ?? {};
  const networks = sections.networks ?? {};
  const volumes = sections.volumes ?? {};

  const dataNetLines = networks.smart_catering_vps_data;
  if (!dataNetLines) {
    findings.push('compose.vps.yaml missing isolated network "smart_catering_vps_data".');
  } else if (findScalar(dataNetLines, 'internal') !== 'true') {
    findings.push('Network "smart_catering_vps_data" must set "internal: true".');
  }

  for (const volumeName of REQUIRED_VOLUMES) {
    if (!Object.hasOwn(volumes, volumeName)) {
      findings.push(`compose.vps.yaml missing persistent named volume "${volumeName}".`);
    }
  }

  for (const serviceName of REQUIRED_SERVICES) {
    const lines = services[serviceName];
    if (!lines) {
      findings.push(`compose.vps.yaml missing required service "${serviceName}".`);
      continue;
    }

    if (findScalar(lines, 'restart') !== 'unless-stopped') {
      findings.push(`Service "${serviceName}" must set "restart: unless-stopped".`);
    }

    if (!lines.some((line) => line.trim() === 'healthcheck:')) {
      findings.push(`Service "${serviceName}" must define a healthcheck.`);
    }

    const securityOpt = extractListItems(lines, 'security_opt');
    if (!securityOpt.includes('no-new-privileges:true')) {
      findings.push(`Service "${serviceName}" must enable "no-new-privileges:true".`);
    }

    if (!findScalar(lines, 'mem_limit')) {
      findings.push(`Service "${serviceName}" must define a mem_limit for VPS stability.`);
    }

    if (!lines.some((line) => line.trim().startsWith('logging:'))) {
      findings.push(`Service "${serviceName}" must configure log rotation via logging.`);
    }

    const image = findScalar(lines, 'image');
    if (image && !DIGEST_REGEX.test(image)) {
      findings.push(`Service "${serviceName}" image must be pinned with an @sha256 digest.`);
    }

    const ports = extractListItems(lines, 'ports');
    if (INTERNAL_ONLY_SERVICES.includes(serviceName) && ports.length > 0) {
      findings.push(
        `Internal service "${serviceName}" must not publish host ports (found: ${ports.join(', ')}).`,
      );
    }

    if (serviceName === 'api') {
      for (const portSpec of ports) {
        if (!portSpec.startsWith('127.0.0.1:')) {
          findings.push(`Service "api" port binding must stay loopback-only: ${portSpec}`);
        }
      }
    }

    if (serviceName === 'caddy') {
      const profiles = extractListItems(lines, 'profiles');
      if (!profiles.includes('proxy')) {
        findings.push('Service "caddy" must declare opt-in profile "proxy".');
      }
      if (ports.length === 0) {
        findings.push('Service "caddy" must publish HTTP/HTTPS ports 80 and 443.');
      }
      for (const portSpec of ports) {
        if (!ALLOWED_CADDY_PORTS.has(portSpec)) {
          findings.push(`Service "caddy" published unexpected port binding: ${portSpec}`);
        }
      }
    }

    const attachedNetworks = extractListItems(lines, 'networks');
    if (DATA_ONLY_SERVICES.includes(serviceName)) {
      if (attachedNetworks.length !== 1 || attachedNetworks[0] !== 'smart_catering_vps_data') {
        findings.push(
          `Data service "${serviceName}" must attach exclusively to "smart_catering_vps_data".`,
        );
      }
    }

    const requiredEnv = REQUIRED_ENV_KEYS[serviceName];
    if (requiredEnv) {
      const envKeys = extractMapKeys(lines, 'environment');
      for (const envKey of requiredEnv) {
        if (!envKeys.has(envKey)) {
          findings.push(`Service "${serviceName}" missing required environment key "${envKey}".`);
        }
      }
    }
  }

  return findings;
}

export function validateCaddyfile(caddyfileText) {
  const findings = [];
  const requiredSnippets = [
    ['admin off', 'Caddyfile must disable the admin API ("admin off").'],
    ['{$API_DOMAIN}', 'Caddyfile must bind site block using {$API_DOMAIN}.'],
    ['reverse_proxy api:3001', 'Caddyfile must proxy allowed public routes to api:3001.'],
    [
      'not method GET HEAD POST PUT PATCH DELETE OPTIONS',
      'Caddyfile must restrict allowed HTTP methods before proxying.',
    ],
    ['Strict-Transport-Security', 'Caddyfile must set Strict-Transport-Security header.'],
    ['X-Content-Type-Options', 'Caddyfile must set X-Content-Type-Options header.'],
    ['request>headers>Authorization delete', 'Caddyfile must redact Authorization header in logs.'],
    ['request>headers>Cookie delete', 'Caddyfile must redact Cookie header in logs.'],
    [
      'request>headers>X-Internal-Token delete',
      'Caddyfile must redact X-Internal-Token header in logs.',
    ],
    ['respond "Not Found" 404', 'Caddyfile must return 404 for non-allowlisted paths.'],
  ];

  for (const [snippet, message] of requiredSnippets) {
    if (!caddyfileText.includes(snippet)) {
      findings.push(message);
    }
  }

  const forbiddenProxies = ['ai-service', 'postgres', 'chroma', 'worker', 'waha'];
  for (const target of forbiddenProxies) {
    if (new RegExp(`reverse_proxy\\s+.*\\b${target}\\b`).test(caddyfileText)) {
      findings.push(`Caddyfile must never proxy public traffic to internal service "${target}".`);
    }
  }

  return findings;
}

export function validateAiDockerfile(dockerfileText) {
  const findings = [];
  for (const extra of ['--extra ml', '--extra rag', '--extra insight']) {
    if (!dockerfileText.includes(extra)) {
      findings.push(`ai-service.Dockerfile must include "${extra}" in default extras.`);
    }
  }
  if (!/^USER\s+(?!root\b)\S+/m.test(dockerfileText)) {
    findings.push('ai-service.Dockerfile must run as a non-root USER.');
  }
  if (!/^HEALTHCHECK\s+/m.test(dockerfileText)) {
    findings.push('ai-service.Dockerfile must define a HEALTHCHECK instruction.');
  }
  return findings;
}

export function runVpsComposeCheck(rootDir = REPO_ROOT) {
  const composeText = readFileSync(resolve(rootDir, 'infra/docker/compose.vps.yaml'), 'utf8');
  const caddyfileText = readFileSync(resolve(rootDir, 'infra/docker/Caddyfile'), 'utf8');
  const aiDockerfileText = readFileSync(
    resolve(rootDir, 'infra/docker/ai-service.Dockerfile'),
    'utf8',
  );

  return [
    ...validateComposeVps(composeText),
    ...validateCaddyfile(caddyfileText),
    ...validateAiDockerfile(aiDockerfileText),
  ];
}

const isDirectRun =
  process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url));

if (isDirectRun) {
  const findings = runVpsComposeCheck();
  if (findings.length > 0) {
    console.error(`VPS compose preflight FAILED with ${findings.length} finding(s):`);
    for (const finding of findings) {
      console.error(`  - ${finding}`);
    }
    process.exit(1);
  }
  console.log('VPS compose & HTTPS proxy preflight PASSED (0 findings).');
}

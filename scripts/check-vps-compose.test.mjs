import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  runVpsComposeCheck,
  validateAiDockerfile,
  validateCaddyfile,
  validateComposeVps,
} from './check-vps-compose.mjs';

const REPO_ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));

describe('VPS Docker Compose & Caddy HTTPS proxy preflight (OPS-02)', () => {
  it('passes cleanly on the repository production Compose, Caddyfile, and AI Dockerfile', () => {
    expect(runVpsComposeCheck(REPO_ROOT)).toEqual([]);
  });

  it('flags exposed internal ports, missing internal data network, and unpinned images', () => {
    const validYaml = readFileSync(resolve(REPO_ROOT, 'infra/docker/compose.vps.yaml'), 'utf8');
    const brokenYaml = validYaml
      .replace(
        '    networks:\n      - smart_catering_vps_data',
        '    ports:\n      - "5432:5432"\n    networks:\n      - smart_catering_vps_app',
      )
      .replace('internal: true', 'internal: false')
      .replace("      - '127.0.0.1:${API_PORT:-3001}:3001'", "      - '0.0.0.0:3001:3001'")
      .replace(/@sha256:[0-9a-f]{64}/, '');

    const findings = validateComposeVps(brokenYaml);
    expect(findings.some((f) => f.includes('Internal service "postgres" must not publish'))).toBe(
      true,
    );
    expect(findings.some((f) => f.includes('exclusively to "smart_catering_vps_data"'))).toBe(true);
    expect(findings.some((f) => f.includes('must set "internal: true"'))).toBe(true);
    expect(findings.some((f) => f.includes('must stay loopback-only'))).toBe(true);
    expect(findings.some((f) => f.includes('pinned with an @sha256 digest'))).toBe(true);
  });

  it('flags missing required services, volumes, healthchecks, and hardening directives', () => {
    const minimalYaml = `
name: broken
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - '8080:8080'
networks:
  smart_catering_vps_app:
    driver: bridge
volumes: {}
`;
    const findings = validateComposeVps(minimalYaml);
    expect(findings.some((f) => f.includes('missing isolated network'))).toBe(true);
    expect(findings.some((f) => f.includes('missing required service "postgres"'))).toBe(true);
    expect(findings.some((f) => f.includes('missing persistent named volume'))).toBe(true);
    expect(findings.some((f) => f.includes('must declare opt-in profile "proxy"'))).toBe(true);
    expect(findings.some((f) => f.includes('unexpected port binding: 8080:8080'))).toBe(true);
    expect(findings.some((f) => f.includes('must set "restart: unless-stopped"'))).toBe(true);
    expect(findings.some((f) => f.includes('must define a healthcheck'))).toBe(true);
    expect(findings.some((f) => f.includes('no-new-privileges:true'))).toBe(true);
  });

  it('flags missing required environment passthrough keys on api, ai-service, and worker', () => {
    const validYaml = readFileSync(resolve(REPO_ROOT, 'infra/docker/compose.vps.yaml'), 'utf8');
    const missingEnvYaml = validYaml.replaceAll('INTERNAL_SERVICE_SECRET:', 'UNUSED_KEY:');

    const findings = validateComposeVps(missingEnvYaml);
    expect(findings.some((f) => f.includes('"api" missing required environment key'))).toBe(true);
    expect(findings.some((f) => f.includes('"ai-service" missing required environment key'))).toBe(
      true,
    );
    expect(findings.some((f) => f.includes('"worker" missing required environment key'))).toBe(
      true,
    );
  });

  it('flags insecure Caddyfile rules and forbidden upstream targets', () => {
    const insecureCaddy = `
{$API_DOMAIN} {
  reverse_proxy ai-service:8001
}
`;
    const findings = validateCaddyfile(insecureCaddy);
    expect(findings.some((f) => f.includes('admin off'))).toBe(true);
    expect(findings.some((f) => f.includes('Strict-Transport-Security'))).toBe(true);
    expect(findings.some((f) => f.includes('Authorization'))).toBe(true);
    expect(findings.some((f) => f.includes('never proxy public traffic to internal service'))).toBe(
      true,
    );
  });

  it('flags ai-service.Dockerfile missing Python extras, non-root user, or healthcheck', () => {
    const findings = validateAiDockerfile('FROM python:3.12-slim\nRUN uv sync --frozen --no-dev\n');
    expect(findings.some((f) => f.includes('--extra ml'))).toBe(true);
    expect(findings.some((f) => f.includes('--extra rag'))).toBe(true);
    expect(findings.some((f) => f.includes('--extra insight'))).toBe(true);
    expect(findings.some((f) => f.includes('non-root USER'))).toBe(true);
    expect(findings.some((f) => f.includes('HEALTHCHECK'))).toBe(true);
  });
});

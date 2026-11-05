import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { access } from 'node:fs/promises';
import { createServer } from 'node:net';
import { dirname, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const HOST = '127.0.0.1';
const STARTUP_TIMEOUT_MS = 45_000;
const SHUTDOWN_TIMEOUT_MS = 5_000;
const REQUEST_ID = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const aiPython = resolve(
  ROOT,
  'apps/ai-service/.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
);
const targets = [
  {
    name: 'web',
    port: 3000,
    path: '/',
    command: process.execPath,
    args: ['scripts/run-service.mjs', 'web', 'start'],
    cwd: ROOT,
    env: {},
  },
  {
    name: 'api',
    port: 3001,
    path: '/health',
    schemaPath: '/api/openapi',
    command: process.execPath,
    args: ['scripts/run-service.mjs', 'api', 'start'],
    cwd: ROOT,
    env: { API_PORT: '3001', API_HOST: HOST },
  },
  {
    name: 'worker',
    port: 3002,
    path: '/health',
    command: process.execPath,
    args: ['scripts/run-service.mjs', 'worker', 'start'],
    cwd: ROOT,
    env: { WORKER_HOST: HOST, WORKER_PORT: '3002' },
  },
  {
    name: 'ai-service',
    port: 8001,
    path: '/health',
    schemaPath: '/openapi.json',
    command: process.execPath,
    args: ['scripts/run-service.mjs', 'ai', 'start'],
    cwd: ROOT,
    env: { AI_HOST: HOST, AI_PORT: '8001' },
  },
];

async function assertPortAvailable(port) {
  const server = createServer();
  server.listen({ host: HOST, port, exclusive: true });
  await once(server, 'listening');
  await new Promise((resolveClose, reject) => {
    server.close((error) => (error ? reject(error) : resolveClose()));
  });
}

async function waitForReady({ target, child }) {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  let lastError;
  while (Date.now() < deadline) {
    assert(
      child.exitCode === null && child.signalCode === null,
      `${target.name} exited at startup`,
    );
    try {
      const response = await request(target, target.path);
      if (response.ok) return response;
      lastError = new Error(`HTTP ${response.status}`);
      await response.body?.cancel();
    } catch (error) {
      lastError = error;
    }
    await delay(200);
  }
  throw new Error(`${target.name} did not become ready`, { cause: lastError });
}

function request(target, path, options = {}) {
  return fetch(`http://${HOST}:${target.port}${path}`, {
    ...options,
    signal: AbortSignal.timeout(3_000),
  });
}

async function stop(child) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  const exited = once(child, 'exit');
  const timer = setTimeout(() => child.kill('SIGKILL'), SHUTDOWN_TIMEOUT_MS);
  timer.unref();
  try {
    if (process.platform === 'win32') {
      const terminator = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
        stdio: 'ignore',
        windowsHide: true,
      });
      await once(terminator, 'exit');
    } else {
      child.kill('SIGTERM');
    }
    await exited;
  } finally {
    clearTimeout(timer);
  }
}

async function runPhase(phaseTargets, docsEnvironment, verify) {
  await Promise.all(phaseTargets.map(({ port }) => assertPortAvailable(port)));
  const processes = phaseTargets.map((target) => {
    const child = spawn(target.command, target.args, {
      cwd: target.cwd,
      env: {
        ...process.env,
        ...target.env,
        NODE_ENV: 'production',
        NEXT_TELEMETRY_DISABLED: '1',
        ...docsEnvironment,
      },
      stdio: ['ignore', 'inherit', 'inherit'],
    });
    const started = once(child, 'spawn');
    child.on('error', (error) => {
      console.error(`${target.name}: ${error.message}`);
    });
    return { target, child, started };
  });
  const shutdown = () => {
    void Promise.all(processes.map(({ child }) => stop(child))).catch((error) => {
      console.error(error);
      process.exitCode = 1;
    });
  };
  process.once('SIGINT', shutdown);
  process.once('SIGTERM', shutdown);
  try {
    await Promise.all(processes.map(({ started }) => started));
    for (const processRecord of processes) {
      const readyResponse = await waitForReady(processRecord);
      await readyResponse.body?.cancel();
      await verify(processRecord.target);
    }
  } finally {
    await Promise.all(processes.map(({ child }) => stop(child)));
    process.removeListener('SIGINT', shutdown);
    process.removeListener('SIGTERM', shutdown);
  }
}

async function assertProblem(response, status, instance, expectedId) {
  assert.equal(response.status, status);
  assert.match(response.headers.get('content-type') ?? '', /application\/problem\+json/);
  const body = await response.json();
  assert.equal(body.type, 'about:blank');
  assert.equal(body.status, status);
  assert.equal(body.instance, instance);
  assert.equal(typeof body.title, 'string');
  assert.equal(typeof body.detail, 'string');
  assert.match(body.requestId, UUID);
  assert.equal(body.requestId, response.headers.get('x-request-id'));
  if (expectedId) assert.equal(body.requestId, expectedId);
  return body;
}

async function verifyHealth(target) {
  const response = await request(target, '/health', {
    headers: { 'X-Request-Id': REQUEST_ID.toUpperCase() },
  });
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type') ?? '', /application\/json/);
  assert.match(response.headers.get('cache-control') ?? '', /no-store/);
  assert.deepEqual(await response.json(), {
    data: { status: 'ok', service: target.name },
    meta: { requestId: REQUEST_ID },
  });
  assert.equal(response.headers.get('x-request-id'), REQUEST_ID);
  const regenerated = await request(target, '/health', {
    headers: { 'X-Request-Id': 'not-a-uuid' },
  });
  const regeneratedBody = await regenerated.json();
  assert.match(regeneratedBody.meta.requestId, UUID);
  assert.equal(regenerated.headers.get('x-request-id'), regeneratedBody.meta.requestId);
  const head = await request(target, '/health', { method: 'HEAD' });
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
  assert.match(head.headers.get('x-request-id') ?? '', UUID);
  const missing = await assertProblem(
    await request(target, '/not-a-route?token=never-echo-this-value', {
      headers: { 'X-Request-Id': REQUEST_ID },
    }),
    404,
    '/not-a-route',
    REQUEST_ID,
  );
  assert(!JSON.stringify(missing).includes('never-echo-this-value'));
  const wrongMethod = await request(target, '/health', { method: 'POST' });
  assert.match(wrongMethod.headers.get('allow') ?? '', /GET/);
  await assertProblem(wrongMethod, 405, '/health');
  console.log(`PASS ${target.name}: envelope, requestId, HEAD, RFC9457 404/405, query redaction`);
}

await access(aiPython);
await runPhase(
  targets,
  { DOCS_ENABLED: 'false', DOCS_USERNAME: '', DOCS_PASSWORD: '' },
  async (target) => {
    if (target.name === 'web') {
      const response = await request(target, '/');
      assert.equal(response.status, 200);
      assert.match(await response.text(), /Smart Catering/);
      console.log('PASS web: production HTTP 200');
    } else if (target.name === 'worker') {
      const response = await request(target, '/health');
      assert.equal(response.status, 200);
      assert.deepEqual(await response.json(), { status: 'ok', service: 'worker' });
      const missing = await request(target, '/not-a-job');
      assert.equal(missing.status, 404);
      await missing.body?.cancel();
      const wrongMethod = await request(target, '/health', { method: 'POST' });
      assert.equal(wrongMethod.status, 405);
      assert.equal(wrongMethod.headers.get('allow'), 'GET');
      await wrongMethod.body?.cancel();
      console.log('PASS worker: independent liveness, 404, 405');
    } else {
      await verifyHealth(target);
      for (const path of ['/docs', target.schemaPath]) {
        await assertProblem(await request(target, path), 404, path);
      }
      console.log(`PASS ${target.name}: production docs and schema disabled`);
    }
  },
);

const username = 'smart-catering-smoke';
const password = randomUUID().replaceAll('-', '') + randomUUID().replaceAll('-', '');
const authorization = `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`;
await runPhase(
  targets.filter((target) => target.schemaPath),
  { DOCS_ENABLED: 'true', DOCS_USERNAME: username, DOCS_PASSWORD: password },
  async (target) => {
    for (const path of ['/docs', target.schemaPath]) {
      const unauthorized = await request(target, path);
      assert.match(unauthorized.headers.get('www-authenticate') ?? '', /^Basic /);
      await assertProblem(unauthorized, 401, path);
      const wrong = await request(target, path, {
        headers: { Authorization: `Basic ${Buffer.from(`${username}:wrong`).toString('base64')}` },
      });
      await assertProblem(wrong, 401, path);
      const authorized = await request(target, path, { headers: { Authorization: authorization } });
      assert.equal(authorized.status, 200);
      assert.match(authorized.headers.get('cache-control') ?? '', /private.*no-store/);
      assert.match(authorized.headers.get('vary') ?? '', /authorization/i);
      assert.match(authorized.headers.get('x-request-id') ?? '', UUID);
      if (path === '/docs') {
        assert.match(authorized.headers.get('content-type') ?? '', /text\/html/);
        const html = await authorized.text();
        assert(!html.includes(password), 'Docs must not expose server credentials');
        assert(!html.includes(authorization), 'Docs must not embed an Authorization header');
      } else {
        const schema = await authorized.json();
        assert.equal(schema.openapi, '3.1.0');
        assert.equal(
          schema.data,
          undefined,
          'OpenAPI is raw protocol JSON, not an API success envelope',
        );
        assert(schema.paths['/health'].get.responses['200'].content['application/json'].schema);
        assert(
          Object.values(schema.components.securitySchemes).some(
            (scheme) => scheme.type === 'http' && scheme.scheme === 'basic',
          ),
        );
      }
    }
    console.log(
      `PASS ${target.name}: production Basic auth protects HTML and valid raw OpenAPI 3.1`,
    );
  },
);
console.log('PASS smoke: owned processes stopped; no PostgreSQL/Chroma/WAHA connection required');

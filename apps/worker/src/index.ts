import { createServer } from 'node:http';
import type { HealthData } from '@smart-catering/types';
import { readWorkerEnvironment } from './environment.js';

const { host, port } = readWorkerEnvironment();
const health: HealthData = { status: 'ok', service: 'worker' };
const healthJson = JSON.stringify(health);
const jsonHeaders = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
};
const methodHeaders = { ...jsonHeaders, Allow: 'GET' };

const server = createServer((request, response) => {
  const url = request.url ?? '/';
  const queryIndex = url.indexOf('?');
  const path = queryIndex < 0 ? url : url.slice(0, queryIndex);
  if (path !== '/health') {
    response.writeHead(404, jsonHeaders).end('{"error":"Not found"}');
    return;
  }
  if (request.method !== 'GET') {
    response.writeHead(405, methodHeaders).end('{"error":"Method not allowed"}');
    return;
  }
  response.writeHead(200, jsonHeaders).end(healthJson);
});

server.on('error', (error: Error) => {
  console.error('Smart Catering worker listener failed:', error.message);
  process.exitCode = 1;
});

function shutdown(signal: string): void {
  if (!server.listening) return;
  console.info('Smart Catering worker stopping:', signal);
  server.close((error) => {
    if (error) {
      console.error('Smart Catering worker shutdown failed:', error.message);
      process.exitCode = 1;
    }
  });
}

process.once('SIGINT', () => shutdown('SIGINT'));
process.once('SIGTERM', () => shutdown('SIGTERM'));

server.listen(port, host, () => {
  console.info(
    `Smart Catering worker listening at http://${host}:${port}/health; no jobs scheduled.`,
  );
});

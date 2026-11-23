import type { Server } from 'node:http';
import { createApiApp } from './app.js';

export function shutdown(server: Server, signal: string): void {
  if (!server.listening) return;
  console.info('Smart Catering API stopping:', signal);
  server.close((error) => {
    if (error) {
      console.error('Smart Catering API shutdown failed:', error.message);
      process.exitCode = 1;
    }
  });
}

export function startServer(): Server {
  const rawHost = process.env['API_HOST'] ?? process.env['HOSTNAME'] ?? '127.0.0.1';
  const rawPort = process.env['API_PORT'] ?? process.env['PORT'] ?? '3001';
  const port = parseInt(rawPort, 10);

  if (!Number.isSafeInteger(port) || port < 1 || port > 65535) {
    console.error(`Smart Catering API invalid port: ${rawPort}`);
    process.exit(1);
  }

  const app = createApiApp();
  const server: Server = app.listen(port, rawHost, () => {
    console.info(`Smart Catering API listening at http://${rawHost}:${port}/health`);
  });

  server.on('error', (error: Error) => {
    console.error('Smart Catering API listener failed:', error.message);
    process.exitCode = 1;
  });

  process.once('SIGINT', () => shutdown(server, 'SIGINT'));
  process.once('SIGTERM', () => shutdown(server, 'SIGTERM'));

  return server;
}

if (process.env['NODE_ENV'] !== 'test') {
  startServer();
}

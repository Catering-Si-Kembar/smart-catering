type Environment = Readonly<Record<string, string | undefined>>;

export type WorkerEnvironment = Readonly<{ host: string; port: number }>;

const MIN_PORT = 1;
const MAX_PORT = 65_535;

export function readWorkerEnvironment(source: Environment = process.env): WorkerEnvironment {
  const host = (source.WORKER_HOST ?? '127.0.0.1').trim();
  const rawPort = source.WORKER_PORT ?? '3002';
  if (!host) {
    throw new Error('WORKER_HOST must not be blank.');
  }
  if (!/^\d+$/.test(rawPort)) {
    throw new Error('WORKER_PORT must be a decimal integer from 1 to 65535.');
  }
  const port = Number(rawPort);
  if (port < MIN_PORT || port > MAX_PORT) {
    throw new Error('WORKER_PORT must be a decimal integer from 1 to 65535.');
  }
  return { host, port };
}

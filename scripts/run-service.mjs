import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createServiceEnvironment,
  readBackendEnvironment,
  readServiceListener,
} from './service-environment.mjs';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const [service, mode, ...extraArguments] = process.argv.slice(2);

function createLaunchSpec(environment) {
  const directory = resolve(ROOT, 'apps', service === 'ai' ? 'ai-service' : service);
  const listener =
    mode === 'build' || service === 'web' ? undefined : readServiceListener(service, environment);
  if (service === 'ai') {
    if (mode === 'build') return { directory, command: 'uv', args: ['build'], environment };
    return {
      directory,
      command: 'uv',
      args: [
        'run',
        '--frozen',
        'uvicorn',
        'app.main:app',
        '--host',
        listener.host,
        '--port',
        String(listener.port),
        '--no-access-log',
        ...(mode === 'dev' ? ['--reload'] : []),
        ...extraArguments,
      ],
      environment,
    };
  }
  if (service === 'worker') {
    const args =
      mode === 'dev' ? ['--import', 'tsx', '--watch', 'src/index.ts'] : ['dist/index.js'];
    return {
      directory,
      command: process.execPath,
      args: [...args, ...extraArguments],
      environment,
    };
  }
  if (service === 'api' && mode === 'start') {
    return {
      directory,
      command: process.execPath,
      args: ['.next/standalone/apps/api/server.js', ...extraArguments],
      environment: { ...environment, PORT: String(listener.port), HOSTNAME: listener.host },
    };
  }
  const workspaceRequire = createRequire(resolve(directory, 'package.json'));
  const args = [workspaceRequire.resolve('next/dist/bin/next'), mode];
  const listenerArgs =
    mode === 'build'
      ? []
      : service === 'web'
        ? ['--port', '3000']
        : ['--hostname', listener.host, '--port', String(listener.port)];
  return {
    directory,
    command: process.execPath,
    args: [...args, ...listenerArgs, ...extraArguments],
    environment,
  };
}

function stopChild(child, signal) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  if (process.platform !== 'win32') {
    child.kill(signal);
    return;
  }
  const terminator = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
    stdio: 'ignore',
    windowsHide: true,
  });
  terminator.once('error', () => {
    console.error('Unable to stop the service process tree. Stop the service from Task Manager.');
    process.exitCode = 1;
  });
}

async function main() {
  const fileValues = service === 'web' ? {} : readBackendEnvironment();
  const environment = createServiceEnvironment(service, mode, fileValues);
  const spec = createLaunchSpec(environment);
  const child = spawn(spec.command, spec.args, {
    cwd: spec.directory,
    env: spec.environment,
    stdio: 'inherit',
    windowsHide: true,
  });
  const onInterrupt = () => stopChild(child, 'SIGINT');
  const onTerminate = () => stopChild(child, 'SIGTERM');
  process.once('SIGINT', onInterrupt);
  process.once('SIGTERM', onTerminate);
  try {
    const result = await new Promise((resolveExit, reject) => {
      child.once('error', () =>
        reject(new Error('Cannot start service. Check installed Node/uv dependencies.')),
      );
      child.once('exit', (code, signal) => resolveExit({ code, signal }));
    });
    process.exitCode = result.code ?? (result.signal === 'SIGINT' ? 130 : result.signal ? 1 : 0);
  } finally {
    process.removeListener('SIGINT', onInterrupt);
    process.removeListener('SIGTERM', onTerminate);
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});

import type { Server } from 'node:http';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { shutdown, startServer } from './index.js';

let activeServer: Server | undefined;

afterEach(async () => {
  vi.restoreAllMocks();
  delete process.env['API_PORT'];
  delete process.env['PORT'];
  delete process.env['API_HOST'];
  delete process.env['HOSTNAME'];
  if (activeServer) {
    await new Promise<void>((resolveClose) => activeServer!.close(() => resolveClose()));
    activeServer = undefined;
  }
});

describe('startServer listener and shutdown', () => {
  it('starts server on specified port and handles graceful shutdown', async () => {
    process.env['API_PORT'] = '39123';
    process.env['API_HOST'] = '127.0.0.1';

    activeServer = startServer();
    await new Promise<void>((resolve) => activeServer!.once('listening', () => resolve()));
    expect(activeServer.listening).toBe(true);

    const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {});
    shutdown(activeServer, 'SIGINT');
    expect(infoSpy).toHaveBeenCalled();
  });

  it('exits process when port is invalid or out of range', () => {
    const exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('PROCESS_EXIT');
    }) as never);
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    process.env['API_PORT'] = 'not-a-port';
    expect(() => startServer()).toThrow('PROCESS_EXIT');
    expect(exitSpy).toHaveBeenCalledWith(1);
    expect(consoleError).toHaveBeenCalled();

    exitSpy.mockClear();
    consoleError.mockClear();

    process.env['API_PORT'] = '99999';
    expect(() => startServer()).toThrow('PROCESS_EXIT');
    expect(exitSpy).toHaveBeenCalledWith(1);
  });

  it('handles server error events', async () => {
    process.env['API_PORT'] = '39124';
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    activeServer = startServer();
    activeServer.emit('error', new Error('test-error'));
    expect(consoleError).toHaveBeenCalled();
  });
});

import { describe, expect, it } from 'vitest';
import { readWorkerEnvironment } from './environment.js';

describe('worker listener configuration', () => {
  it.each(['0', '-1', '65536', '3.5', '3002oops', '', 'NaN', 'Infinity'])(
    'rejects invalid WORKER_PORT %j instead of binding an unexpected port',
    (port) => {
      expect(() => readWorkerEnvironment({ WORKER_PORT: port })).toThrow('WORKER_PORT');
    },
  );

  it.each(['1', '3002', '65535'])(
    'accepts valid TCP port %s without changing the requested address',
    (port) => {
      const result = readWorkerEnvironment({ WORKER_PORT: port, WORKER_HOST: '127.0.0.1' });
      expect(result).toEqual({ host: '127.0.0.1', port: Number(port) });
    },
  );

  it('rejects a blank host rather than exposing the listener unintentionally', () => {
    expect(() => readWorkerEnvironment({ WORKER_HOST: '  ' })).toThrow('WORKER_HOST');
  });

  it('preserves the explicit container bind address', () => {
    expect(readWorkerEnvironment({ WORKER_HOST: '0.0.0.0', WORKER_PORT: '3002' })).toEqual({
      host: '0.0.0.0',
      port: 3002,
    });
  });
});

import { describe, expect, it } from 'vitest';
import { cn } from './utils';

describe('cn utility', () => {
  it('combines multiple class names', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2');
  });

  it('handles conditional and falsy class values', () => {
    expect(cn('base', false && 'hidden', null, undefined, 0, 'visible')).toBe('base visible');
  });

  it('merges tailwind utility conflicts correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
  });
});

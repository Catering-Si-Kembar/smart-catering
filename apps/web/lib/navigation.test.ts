import { describe, expect, it } from 'vitest';
import {
  canAccessRoute,
  getMobileBarItemsForRole,
  getNavItemsForRole,
  getPageMeta,
} from './navigation';

describe('navigation helpers', () => {
  it('returns full navigation list including finance and analytics for ADMIN', () => {
    const adminItems = getNavItemsForRole('ADMIN');
    const hrefs = adminItems.map((item) => item.href);

    expect(hrefs).toContain('/');
    expect(hrefs).toContain('/pesanan');
    expect(hrefs).toContain('/menu');
    expect(hrefs).toContain('/tagihan');
    expect(hrefs).toContain('/analitik');
    expect(hrefs).toContain('/chat');
    expect(hrefs).toContain('/notifikasi');
  });

  it('hides finance (/tagihan) and analytics (/analitik) navigation items for STAFF', () => {
    const staffItems = getNavItemsForRole('STAFF');
    const hrefs = staffItems.map((item) => item.href);

    expect(hrefs).toContain('/');
    expect(hrefs).toContain('/pesanan');
    expect(hrefs).toContain('/menu');
    expect(hrefs).toContain('/chat');
    expect(hrefs).toContain('/notifikasi');
    expect(hrefs).not.toContain('/tagihan');
    expect(hrefs).not.toContain('/analitik');
  });

  it('returns four concise mobile bar items per role with role-appropriate fourth slot', () => {
    const adminBar = getMobileBarItemsForRole('ADMIN');
    const staffBar = getMobileBarItemsForRole('STAFF');

    expect(adminBar).toHaveLength(4);
    expect(adminBar.map((item) => item.href)).toEqual(['/', '/pesanan', '/menu', '/tagihan']);

    expect(staffBar).toHaveLength(4);
    expect(staffBar.map((item) => item.href)).toEqual(['/', '/pesanan', '/menu', '/chat']);
  });

  it('enforces route access checks for ADMIN vs STAFF and allows non-restricted routes', () => {
    expect(canAccessRoute('ADMIN', '/tagihan')).toBe(true);
    expect(canAccessRoute('ADMIN', '/analitik')).toBe(true);
    expect(canAccessRoute('STAFF', '/tagihan')).toBe(false);
    expect(canAccessRoute('STAFF', '/tagihan/inv-01')).toBe(false);
    expect(canAccessRoute('STAFF', '/analitik')).toBe(false);
    expect(canAccessRoute('STAFF', '/')).toBe(true);
    expect(canAccessRoute('STAFF', '/pesanan')).toBe(true);
    expect(canAccessRoute('STAFF', '/login')).toBe(true);
  });

  it('resolves Indonesian page titles and fallback metadata for unknown routes', () => {
    expect(getPageMeta('/').title).toBe('Jadwal Hari Ini');
    expect(getPageMeta('/menu').title).toBe('Menu & Bahan');
    expect(getPageMeta('/pesanan/baru').title).toBe('Pesanan');
    expect(getPageMeta('/rute-tidak-dikenal').title).toBe('Smart Catering');
  });
});

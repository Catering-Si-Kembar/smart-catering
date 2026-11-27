export type UserRole = 'ADMIN' | 'STAFF';

export type NavIconKey =
  'calendar' | 'clipboard' | 'utensils' | 'receipt' | 'bot' | 'chart' | 'bell';

export interface NavItem {
  readonly href: string;
  readonly label: string;
  readonly shortLabel: string;
  readonly description: string;
  readonly icon: NavIconKey;
  readonly roles: readonly UserRole[];
  readonly section: 'utama' | 'tambahan';
  readonly showInMobileBar: boolean;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    href: '/',
    label: 'Jadwal Hari Ini',
    shortLabel: 'Jadwal',
    description: 'Ringkasan jadwal produksi harian dan aksi cepat dapur.',
    icon: 'calendar',
    roles: ['ADMIN', 'STAFF'],
    section: 'utama',
    showInMobileBar: true,
  },
  {
    href: '/pesanan',
    label: 'Pesanan',
    shortLabel: 'Pesanan',
    description: 'Catat pesanan baru dan pantau status persiapan dapur.',
    icon: 'clipboard',
    roles: ['ADMIN', 'STAFF'],
    section: 'utama',
    showInMobileBar: true,
  },
  {
    href: '/menu',
    label: 'Menu & Bahan',
    shortLabel: 'Menu',
    description: 'Katalog paket katering, resep standar, dan hitung bahan otomatis.',
    icon: 'utensils',
    roles: ['ADMIN', 'STAFF'],
    section: 'utama',
    showInMobileBar: true,
  },
  {
    href: '/tagihan',
    label: 'Tagihan',
    shortLabel: 'Tagihan',
    description: 'Invoice digital, pencatatan DP 60%, dan pelunasan pesanan.',
    icon: 'receipt',
    roles: ['ADMIN'],
    section: 'utama',
    showInMobileBar: true,
  },
  {
    href: '/chat',
    label: 'Asisten AI',
    shortLabel: 'Asisten',
    description: 'Tanya cepat SOP katering, menu, dan status jadwal pesanan.',
    icon: 'bot',
    roles: ['ADMIN', 'STAFF'],
    section: 'tambahan',
    showInMobileBar: false,
  },
  {
    href: '/analitik',
    label: 'Analitik',
    shortLabel: 'Analitik',
    description: 'KPI penjualan, estimasi permintaan menu, dan laporan PDF.',
    icon: 'chart',
    roles: ['ADMIN'],
    section: 'tambahan',
    showInMobileBar: false,
  },
  {
    href: '/notifikasi',
    label: 'Pengingat',
    shortLabel: 'Pengingat',
    description: 'Notifikasi pesanan H-1 acara dan pengingat jatuh tempo.',
    icon: 'bell',
    roles: ['ADMIN', 'STAFF'],
    section: 'tambahan',
    showInMobileBar: false,
  },
] as const;

export function getNavItemsForRole(role: UserRole): readonly NavItem[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

export function getMobileBarItemsForRole(role: UserRole): readonly NavItem[] {
  const roleItems = getNavItemsForRole(role);
  const pinned = roleItems.filter((item) => item.showInMobileBar);
  if (role === 'STAFF') {
    const assistant = roleItems.find((item) => item.href === '/chat');
    return assistant ? [...pinned, assistant] : pinned;
  }
  return pinned;
}

export function canAccessRoute(role: UserRole, pathname: string): boolean {
  const matched = NAV_ITEMS.find((item) =>
    item.href === '/'
      ? pathname === '/'
      : pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
  if (!matched) {
    return true;
  }
  return matched.roles.includes(role);
}

export function getPageMeta(pathname: string): { title: string; description: string } {
  const matched = NAV_ITEMS.find((item) =>
    item.href === '/'
      ? pathname === '/'
      : pathname === item.href || pathname.startsWith(`${item.href}/`),
  );
  if (matched) {
    return { title: matched.label, description: matched.description };
  }
  return {
    title: 'Smart Catering',
    description: 'Sistem operasional katering Catering Si Kembar.',
  };
}

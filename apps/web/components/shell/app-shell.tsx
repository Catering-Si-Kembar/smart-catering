'use client';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import AssignmentOutlinedIcon from '@mui/icons-material/AssignmentOutlined';
import BarChartRoundedIcon from '@mui/icons-material/BarChartRounded';
import CalendarTodayRoundedIcon from '@mui/icons-material/CalendarTodayRounded';
import ChevronRightRoundedIcon from '@mui/icons-material/ChevronRightRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import KeyboardArrowDownRoundedIcon from '@mui/icons-material/KeyboardArrowDownRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import NotificationsNoneRoundedIcon from '@mui/icons-material/NotificationsNoneRounded';
import ReceiptLongRoundedIcon from '@mui/icons-material/ReceiptLongRounded';
import RestaurantMenuRoundedIcon from '@mui/icons-material/RestaurantMenuRounded';
import SupportAgentRoundedIcon from '@mui/icons-material/SupportAgentRounded';
import WifiOffRoundedIcon from '@mui/icons-material/WifiOffRounded';
import type { SvgIconProps } from '@mui/material/SvgIcon';
import { getMobileBarItemsForRole, getNavItemsForRole, type NavIconKey } from '@/lib/navigation';
import { useAppRole } from '@/components/shell/role-context';
import { cn } from '@/lib/utils';

const ICON_MAP: Record<NavIconKey, React.ComponentType<SvgIconProps>> = {
  calendar: CalendarTodayRoundedIcon,
  clipboard: AssignmentOutlinedIcon,
  utensils: RestaurantMenuRoundedIcon,
  receipt: ReceiptLongRoundedIcon,
  bot: SupportAgentRoundedIcon,
  chart: BarChartRoundedIcon,
  bell: NotificationsNoneRoundedIcon,
};

export interface AppShellProps {
  readonly appName: string;
  readonly children: React.ReactNode;
}

export function AppShell({ appName, children }: AppShellProps) {
  const pathname = usePathname();
  const { role, setRole, isOnline } = useAppRole();
  const [mobileDrawerOpen, setMobileDrawerOpen] = React.useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = React.useState(false);
  const profileMenuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setProfileMenuOpen(false);
      }
    }
    if (profileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [profileMenuOpen]);

  const roleNavItems = React.useMemo(() => getNavItemsForRole(role), [role]);
  const mobileBarItems = React.useMemo(() => getMobileBarItemsForRole(role), [role]);

  const primaryItems = roleNavItems.filter((item) => item.section === 'utama');
  const secondaryItems = roleNavItems.filter((item) => item.section === 'tambahan');

  return (
    <div className="flex min-h-screen flex-col bg-[#f9f9f8] text-[#21201c]">
      {/* Offline Alert Banner */}
      {!isOnline && (
        <div
          role="status"
          aria-live="polite"
          className="flex items-center justify-center gap-2 bg-[#b91c1c] px-4 py-2 text-center text-sm font-bold text-white shadow-sm"
        >
          <WifiOffRoundedIcon sx={{ fontSize: 18 }} className="shrink-0" aria-hidden={true} />
          <span>Koneksi internet terputus. Sistem tetap berjalan dalam mode offline lokal.</span>
        </div>
      )}

      {/* Top Header */}
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[#dad9d6] bg-white px-4 lg:px-8">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex min-h-[44px] items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#fbcc04]"
          >
            <Image
              src="/logo-katering-si-kembar.png"
              alt="Logo Catering Si Kembar"
              width={42}
              height={42}
              className="h-10 w-10 rounded-full border border-[#dad9d6] object-cover"
              priority
            />
            <div className="flex flex-col">
              <span className="text-base font-bold leading-tight text-[#21201c] sm:text-lg">
                Catering Si Kembar
              </span>
              <span className="text-xs font-semibold text-[#9e1b32]">{appName}</span>
            </div>
          </Link>
        </div>

        {/* Top Header Right Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* User Profile & Role Switcher Dropdown */}
          <div className="relative" ref={profileMenuRef}>
            <button
              type="button"
              onClick={() => setProfileMenuOpen((prev) => !prev)}
              aria-expanded={profileMenuOpen}
              aria-haspopup="true"
              aria-label="Menu akun dan peran pengguna"
              className={cn(
                'inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-[#dad9d6] bg-white px-2.5 py-1.5 text-xs font-bold text-[#21201c] shadow-xs transition hover:bg-[#f1f0ef] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#fbcc04]',
                profileMenuOpen && 'ring-2 ring-[#fbcc04] bg-[#f9f9f8]',
              )}
            >
              <div
                className={cn(
                  'flex h-6 w-6 items-center justify-center rounded-full text-white text-[10px] font-extrabold',
                  role === 'ADMIN' ? 'bg-[#9e1b32]' : 'bg-[#5c3271]',
                )}
              >
                {role === 'ADMIN' ? 'A' : 'S'}
              </div>
              <span className="hidden sm:inline font-bold">
                {role === 'ADMIN' ? 'Pengelola (ADMIN)' : 'Staf Dapur'}
              </span>
              <KeyboardArrowDownRoundedIcon
                sx={{ fontSize: 18 }}
                className={cn(
                  'text-[#82827c] transition-transform duration-150',
                  profileMenuOpen && 'rotate-180',
                )}
                aria-hidden={true}
              />
            </button>

            {/* Profile & Role Dropdown Menu */}
            {profileMenuOpen && (
              <div
                role="menu"
                aria-orientation="vertical"
                className="absolute right-0 mt-1.5 w-60 rounded-xl border border-[#dad9d6] bg-white p-2 shadow-lg z-50 animate-in fade-in zoom-in-95 duration-100"
              >
                <div className="px-2.5 py-2 border-b border-[#dad9d6] mb-1.5">
                  <p className="text-xs font-bold text-[#21201c]">Akun Masuk</p>
                  <p className="text-[11px] text-[#63635e]">
                    {role === 'ADMIN' ? 'admin@cateringsikembar.id' : 'dapur@cateringsikembar.id'}
                  </p>
                </div>

                <div className="space-y-1">
                  <p className="px-2.5 pt-1 text-[10px] font-bold uppercase tracking-wider text-[#82827c]">
                    Beralih Peran Akun:
                  </p>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setRole('ADMIN');
                      setProfileMenuOpen(false);
                    }}
                    className={cn(
                      'flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-xs font-semibold transition',
                      role === 'ADMIN'
                        ? 'bg-[#fdf2f4] text-[#8e182d] font-bold'
                        : 'text-[#21201c] hover:bg-[#f1f0ef]',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-[#9e1b32]" />
                      <span>Pengelola (ADMIN)</span>
                    </div>
                    {role === 'ADMIN' && (
                      <span className="text-[10px] font-bold text-[#8e182d]">Aktif</span>
                    )}
                  </button>

                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setRole('STAFF');
                      setProfileMenuOpen(false);
                    }}
                    className={cn(
                      'flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-xs font-semibold transition',
                      role === 'STAFF'
                        ? 'bg-[#f5eff8] text-[#5c3271] font-bold'
                        : 'text-[#21201c] hover:bg-[#f1f0ef]',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-[#5c3271]" />
                      <span>Staf Dapur (STAFF)</span>
                    </div>
                    {role === 'STAFF' && (
                      <span className="text-[10px] font-bold text-[#5c3271]">Aktif</span>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Mobile Drawer Toggle */}
          <button
            type="button"
            onClick={() => setMobileDrawerOpen((prev) => !prev)}
            aria-expanded={mobileDrawerOpen}
            aria-label={mobileDrawerOpen ? 'Tutup navigasi' : 'Buka semua menu navigasi'}
            className="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-lg border border-[#dad9d6] bg-white text-[#21201c] hover:bg-[#f1f0ef] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#fbcc04] lg:hidden"
          >
            {mobileDrawerOpen ? (
              <CloseRoundedIcon sx={{ fontSize: 22 }} aria-hidden={true} />
            ) : (
              <MenuRoundedIcon sx={{ fontSize: 22 }} aria-hidden={true} />
            )}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex flex-1">
        {/* Desktop Sidebar Navigation */}
        <aside
          aria-label="Navigasi Desktop"
          className="hidden w-64 shrink-0 border-r border-[#dad9d6] bg-[#f9f9f8] lg:flex lg:flex-col lg:justify-between"
        >
          <div className="space-y-6 p-4">
            {/* Primary Section */}
            <div>
              <p className="px-3 text-xs font-bold uppercase tracking-wider text-[#82827c]">
                Menu Operasional
              </p>
              <nav className="mt-2 space-y-1">
                {primaryItems.map((item) => {
                  const Icon = ICON_MAP[item.icon];
                  const isActive =
                    item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        'flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#fbcc04]',
                        isActive
                          ? 'bg-[#fdf2f4] text-[#8e182d] font-bold shadow-[0_0_0_1px_rgba(142,24,45,0.16)]'
                          : 'text-[#63635e] hover:bg-[#f1f0ef] hover:text-[#21201c]',
                      )}
                    >
                      <Icon sx={{ fontSize: 20 }} className="shrink-0" aria-hidden={true} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Secondary Section */}
            {secondaryItems.length > 0 && (
              <div>
                <p className="px-3 text-xs font-bold uppercase tracking-wider text-[#82827c]">
                  Fitur Tambahan
                </p>
                <nav className="mt-2 space-y-1">
                  {secondaryItems.map((item) => {
                    const Icon = ICON_MAP[item.icon];
                    const isActive = pathname.startsWith(item.href);
                    const isAi = item.href === '/chat';
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          'flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#fbcc04]',
                          isActive
                            ? isAi
                              ? 'bg-[#f5eff8] text-[#5c3271] font-bold shadow-[0_0_0_1px_rgba(92,50,113,0.18)]'
                              : 'bg-[#fdf2f4] text-[#8e182d] font-bold shadow-[0_0_0_1px_rgba(142,24,45,0.16)]'
                            : isAi
                              ? 'text-[#5c3271] hover:bg-[#f5eff8]'
                              : 'text-[#63635e] hover:bg-[#f1f0ef] hover:text-[#21201c]',
                        )}
                      >
                        <Icon sx={{ fontSize: 20 }} className="shrink-0" aria-hidden={true} />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </nav>
              </div>
            )}
          </div>

          {/* Sidebar Footer info & Keluar Akun */}
          {/* Bottom Desktop Sidebar: Clean Logout Action */}
          <div className="border-t border-[#dad9d6] p-3">
            <Link
              href="/login"
              className="flex min-h-[40px] w-full items-center gap-2.5 rounded-lg border border-[#dad9d6] bg-white px-3 py-2 text-xs font-bold text-[#b91c1c] transition hover:bg-[#fdf2f4] hover:border-[#b91c1c]/30 shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b91c1c]"
            >
              <LogoutRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
              <span>Keluar Akun</span>
            </Link>
          </div>
        </aside>

        {/* Mobile Slide-down / Drawer Navigation */}
        {mobileDrawerOpen && (
          <div
            id="mobile-nav-panel"
            className="fixed inset-0 top-16 z-40 flex flex-col bg-slate-900/40 backdrop-blur-xs lg:hidden"
            onClick={() => setMobileDrawerOpen(false)}
          >
            <div
              className="max-h-[85vh] w-full overflow-y-auto bg-white p-4 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <span className="text-base font-bold text-slate-950">Daftar Menu Navigasi</span>
                <button
                  type="button"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-slate-600 hover:bg-slate-100"
                  aria-label="Tutup panel navigasi"
                >
                  <CloseRoundedIcon sx={{ fontSize: 24 }} aria-hidden={true} />
                </button>
              </div>

              <div className="mt-4 space-y-4">
                <div>
                  <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                    Menu Utama
                  </p>
                  <nav className="space-y-1">
                    {primaryItems.map((item) => {
                      const Icon = ICON_MAP[item.icon];
                      const isActive =
                        item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => setMobileDrawerOpen(false)}
                          className={cn(
                            'flex min-h-[44px] items-center justify-between rounded-lg px-3 py-2 text-base font-semibold transition',
                            isActive
                              ? 'bg-[#fdf2f4] text-[#8e182d] font-bold shadow-[0_0_0_1px_rgba(142,24,45,0.16)]'
                              : 'text-[#21201c] hover:bg-[#f1f0ef]',
                          )}
                        >
                          <div className="flex items-center gap-3">
                            <Icon sx={{ fontSize: 20 }} className="shrink-0" aria-hidden={true} />
                            <span>{item.label}</span>
                          </div>
                          <ChevronRightRoundedIcon
                            sx={{ fontSize: 20 }}
                            className="opacity-70"
                            aria-hidden={true}
                          />
                        </Link>
                      );
                    })}
                  </nav>
                </div>

                {secondaryItems.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-bold uppercase tracking-wider text-[#82827c]">
                      Fitur Tambahan
                    </p>
                    <nav className="space-y-1">
                      {secondaryItems.map((item) => {
                        const Icon = ICON_MAP[item.icon];
                        const isActive = pathname.startsWith(item.href);
                        const isAi = item.href === '/chat';
                        return (
                          <Link
                            key={item.href}
                            href={item.href}
                            onClick={() => setMobileDrawerOpen(false)}
                            className={cn(
                              'flex min-h-[44px] items-center justify-between rounded-lg px-3 py-2 text-base font-semibold transition',
                              isActive
                                ? isAi
                                  ? 'bg-[#f5eff8] text-[#5c3271] font-bold shadow-[0_0_0_1px_rgba(92,50,113,0.18)]'
                                  : 'bg-[#fdf2f4] text-[#8e182d] font-bold shadow-[0_0_0_1px_rgba(142,24,45,0.16)]'
                                : isAi
                                  ? 'text-[#5c3271] hover:bg-[#f5eff8]'
                                  : 'text-[#21201c] hover:bg-[#f1f0ef]',
                            )}
                          >
                            <div className="flex items-center gap-3">
                              <Icon sx={{ fontSize: 20 }} className="shrink-0" aria-hidden={true} />
                              <span>{item.label}</span>
                            </div>
                            <ChevronRightRoundedIcon
                              sx={{ fontSize: 20 }}
                              className="opacity-70"
                              aria-hidden={true}
                            />
                          </Link>
                        );
                      })}
                    </nav>
                  </div>
                )}

                <div className="border-t border-[#dad9d6] pt-2">
                  <Link
                    href="/login"
                    onClick={() => setMobileDrawerOpen(false)}
                    className="flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-base font-semibold text-[#b91c1c] hover:bg-[#fdf2f4]"
                  >
                    <LogoutRoundedIcon
                      sx={{ fontSize: 20 }}
                      className="shrink-0"
                      aria-hidden={true}
                    />
                    <span>Keluar Akun</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Content Area */}
        <main
          id="konten-utama"
          tabIndex={-1}
          className="flex-1 overflow-x-hidden px-4 py-6 pb-24 sm:px-6 lg:px-8 lg:pb-8"
        >
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>

      {/* Sticky Mobile Bottom Navigation */}
      <nav
        aria-label="Navigasi Bawah Ponsel"
        className="fixed bottom-0 left-0 right-0 z-30 flex h-16 border-t border-[#dad9d6] bg-white shadow-lg lg:hidden"
      >
        <div className="grid h-full w-full auto-cols-fr grid-flow-col">
          {mobileBarItems.map((item) => {
            const Icon = ICON_MAP[item.icon];
            const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex min-h-[44px] flex-col items-center justify-center gap-1 text-center transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#fbcc04]',
                  isActive
                    ? 'font-bold text-[#9e1b32]'
                    : 'font-medium text-[#63635e] hover:text-[#21201c]',
                )}
              >
                <Icon sx={{ fontSize: 22 }} className="shrink-0" aria-hidden={true} />
                <span className="text-[11px] leading-none">{item.shortLabel}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

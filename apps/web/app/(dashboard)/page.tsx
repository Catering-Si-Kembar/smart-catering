'use client';

import * as React from 'react';
import Link from 'next/link';
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import CalendarTodayRoundedIcon from '@mui/icons-material/CalendarTodayRounded';
import LocationOnOutlinedIcon from '@mui/icons-material/LocationOnOutlined';
import RestaurantMenuRoundedIcon from '@mui/icons-material/RestaurantMenuRounded';
import {
  MOCK_ORDERS,
  ORDER_STATUS_META,
  formatRupiah,
  formatTanggalIndonesia,
  type MockOrder,
} from '@/lib/mock-data';
import { Button, buttonVariants } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { StatusBanner } from '@/components/ui/status-banner';
import { cn } from '@/lib/utils';

type UiPreviewState = 'normal' | 'loading' | 'empty' | 'error';

export default function DashboardPage() {
  const [uiState, setUiState] = React.useState<UiPreviewState>('normal');
  const [orderList] = React.useState<readonly MockOrder[]>(MOCK_ORDERS);

  const totalPortions = React.useMemo(
    () => orderList.reduce((acc, curr) => acc + curr.portions, 0),
    [orderList],
  );

  const activeOrdersCount = React.useMemo(
    () =>
      orderList.filter(
        (o) => o.status === 'IN_PREPARATION' || o.status === 'READY' || o.status === 'CONFIRMED',
      ).length,
    [orderList],
  );

  const pendingDpCount = React.useMemo(
    () => orderList.filter((o) => o.status === 'DRAFT').length,
    [orderList],
  );

  return (
    <div className="space-y-6">
      {/* Top Welcome & Quick Actions */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-0.5">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#21201c] sm:text-2xl">
              Jadwal Produksi Hari Ini
            </h1>
          </div>
          <p className="text-xs text-[#63635e] sm:text-sm">
            Rabu, 25 November 2026 · Pantauan dapur utama dan aksi cepat operasional Catering Si
            Kembar.
          </p>
        </div>

        {/* Primary Action Buttons (Calibrated tactile scale, 40px desktop) */}
        <div className="flex shrink-0 flex-row items-center gap-2 sm:gap-2.5">
          <Link
            href="/pesanan"
            className={cn(
              buttonVariants({ variant: 'default' }),
              'h-10 px-4 text-xs sm:text-sm font-bold shadow-xs whitespace-nowrap',
            )}
          >
            <AddRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
            <span>Catat Pesanan Baru</span>
          </Link>
          <Link
            href="/menu"
            className={cn(
              buttonVariants({ variant: 'secondary' }),
              'h-10 px-4 text-xs sm:text-sm font-bold text-[#21201c] border border-[#dad9d6] shadow-xs whitespace-nowrap',
            )}
          >
            <RestaurantMenuRoundedIcon
              sx={{ fontSize: 18 }}
              className="text-[#9e1b32]"
              aria-hidden={true}
            />
            <span>Hitung Bahan Dapur</span>
          </Link>
        </div>
      </div>

      {/* State: ERROR */}
      {uiState === 'error' && (
        <StatusBanner
          tone="error"
          title="Gagal mengambil jadwal dapur terkini"
          detail="Terjadi kendala saat menyinkronkan data pesanan. Silakan periksa koneksi atau coba muat ulang."
          actionLabel="Muat Ulang Data"
          onAction={() => setUiState('normal')}
        />
      )}

      {/* State: LOADING */}
      {uiState === 'loading' && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            {[1, 2, 3].map((idx) => (
              <div
                key={idx}
                className="h-28 animate-pulse rounded-lg border border-slate-200 bg-slate-100 p-4"
              />
            ))}
          </div>
          <div className="h-64 animate-pulse rounded-lg border border-slate-200 bg-slate-100 p-4" />
        </div>
      )}

      {/* State: EMPTY */}
      {uiState === 'empty' && (
        <Card className="border-slate-300 py-12 text-center">
          <CardContent className="space-y-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-500">
              <CalendarTodayRoundedIcon sx={{ fontSize: 28 }} aria-hidden={true} />
            </div>
            <div className="space-y-1">
              <h2 className="text-xl font-bold text-slate-900">Belum Ada Jadwal Masak Hari Ini</h2>
              <p className="mx-auto max-w-md text-sm text-slate-600">
                Semua pesanan untuk hari ini sudah selesai diantar atau belum ada pesanan baru yang
                dikonfirmasi.
              </p>
            </div>
            <Button type="button" className="min-h-[44px]" onClick={() => setUiState('normal')}>
              Muat Ulang Pesanan
            </Button>
          </CardContent>
        </Card>
      )}

      {/* State: NORMAL */}
      {uiState === 'normal' && (
        <>
          {/* Operational Metric Cards (High Contrast, Tactile Icon Badges) */}
          <div className="grid gap-3 sm:grid-cols-3">
            {/* Card 1: Portions */}
            <Card className="border-[#dad9d6] bg-white shadow-xs">
              <CardContent className="p-4 sm:p-5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#82827c]">
                    Porsi Masak Hari Ini
                  </span>
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#fbcc04]/20 text-[#21201c]">
                    <RestaurantMenuRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                  </div>
                </div>
                <div className="mt-2 flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold tabular-nums tracking-tight text-[#21201c]">
                    {totalPortions}
                  </span>
                  <span className="text-xs font-semibold text-[#63635e]">Porsi Box</span>
                </div>
                <p className="mt-1.5 text-xs text-[#82827c]">2 menu paket dalam antrean aktif</p>
              </CardContent>
            </Card>

            {/* Card 2: Active Orders */}
            <Card className="border-[#dad9d6] bg-white shadow-xs">
              <CardContent className="p-4 sm:p-5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#82827c]">
                    Pesanan Aktif Dapur
                  </span>
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#ecfdf5] text-[#166534]">
                    <AccessTimeRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                  </div>
                </div>
                <div className="mt-2 flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold tabular-nums tracking-tight text-[#166534]">
                    {activeOrdersCount}
                  </span>
                  <span className="text-xs font-semibold text-[#63635e]">Pesanan</span>
                </div>
                <p className="mt-1.5 text-xs text-[#82827c]">1 dimasak · 1 siap antar</p>
              </CardContent>
            </Card>

            {/* Card 3: Pending Confirmation */}
            <Card className="border-[#dad9d6] bg-white shadow-xs">
              <CardContent className="p-4 sm:p-5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#82827c]">
                    Perlu Konfirmasi DP
                  </span>
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#fef7d6] text-[#7a5600]">
                    <CalendarTodayRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                  </div>
                </div>
                <div className="mt-2 flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold tabular-nums tracking-tight text-[#7a5600]">
                    {pendingDpCount}
                  </span>
                  <span className="text-xs font-semibold text-[#63635e]">Pesanan</span>
                </div>
                <p className="mt-1.5 text-xs text-[#82827c]">Min. 60% DP sebelum belanja bahan</p>
              </CardContent>
            </Card>
          </div>

          {/* Cooking Queue Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-[#21201c] sm:text-lg">
                  Antrean Produksi Dapur
                </h2>
                <p className="text-xs text-[#63635e]">Prioritas jadwal kirim hari ini</p>
              </div>
              <Link
                href="/pesanan"
                className="inline-flex items-center gap-1 text-xs font-bold text-[#9e1b32] hover:underline"
              >
                <span>Semua Pesanan</span>
                <ArrowForwardRoundedIcon sx={{ fontSize: 16 }} aria-hidden={true} />
              </Link>
            </div>

            <div className="grid gap-3">
              {orderList.map((order) => {
                const statusInfo = ORDER_STATUS_META[order.status];
                return (
                  <Card
                    key={order.id}
                    className="border-[#dad9d6] bg-white transition hover:border-[#cfceca] shadow-xs"
                  >
                    <CardContent className="p-4 sm:p-5">
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                        {/* Kolom Kiri: Detail Pesanan Horizontal */}
                        <div className="space-y-2 min-w-0 flex-1">
                          {/* Baris 1: Kode Pesanan + Clean Status Dot */}
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-mono font-medium text-[#82827c]">
                              {order.orderNumber}
                            </span>
                            <span className="text-[#dad9d6]">·</span>
                            <div className="inline-flex items-center gap-1.5">
                              <span
                                className={cn(
                                  'h-2 w-2 rounded-full shrink-0',
                                  order.status === 'READY' && 'bg-[#166534] ring-2 ring-[#ecfdf5]',
                                  order.status === 'IN_PREPARATION' &&
                                    'bg-[#e6b400] ring-2 ring-[#fef7d6] animate-pulse',
                                  order.status === 'DRAFT' && 'bg-[#82827c] ring-2 ring-[#f1f0ef]',
                                )}
                                aria-hidden="true"
                              />
                              <span
                                className={cn(
                                  'font-semibold text-xs',
                                  order.status === 'READY' && 'text-[#166534]',
                                  order.status === 'IN_PREPARATION' && 'text-[#7a5600]',
                                  order.status === 'DRAFT' && 'text-[#63635e]',
                                )}
                              >
                                {statusInfo.label}
                              </span>
                            </div>
                          </div>

                          {/* Baris 2: Nama Menu & Porsi */}
                          <div>
                            <h3 className="text-base sm:text-lg font-bold text-[#21201c]">
                              {order.menuName}{' '}
                              <span className="text-[#9e1b32] font-mono font-bold">
                                · {order.portions} Box
                              </span>
                            </h3>
                            <p className="mt-0.5 text-xs text-[#63635e]">
                              <span className="text-[#82827c]">Pemesan:</span>{' '}
                              <span className="font-semibold text-[#21201c]">
                                {order.customerAlias}
                              </span>
                            </p>
                          </div>

                          {/* Baris 3: Jam Kirim & Lokasi */}
                          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#63635e]">
                            <div className="flex items-center gap-1.5">
                              <AccessTimeRoundedIcon
                                sx={{ fontSize: 15 }}
                                className="shrink-0 text-[#82827c]"
                                aria-hidden={true}
                              />
                              <span>
                                <span className="text-[#82827c]">Jadwal Kirim:</span>{' '}
                                <span className="font-semibold text-[#21201c]">
                                  {formatTanggalIndonesia(order.eventDate)}
                                </span>{' '}
                                · Pukul{' '}
                                <span className="font-mono font-semibold text-[#21201c]">
                                  {order.eventTime}
                                </span>
                              </span>
                            </div>
                            <span className="text-[#dad9d6]">·</span>
                            <div className="flex items-center gap-1.5">
                              <LocationOnOutlinedIcon
                                sx={{ fontSize: 15 }}
                                className="shrink-0 text-[#82827c]"
                                aria-hidden={true}
                              />
                              <span>
                                <span className="text-[#82827c]">Alamat Kirim:</span>{' '}
                                <span className="font-medium text-[#21201c]">
                                  {order.deliveryArea}
                                </span>
                              </span>
                            </div>
                          </div>

                          {/* Baris 4: Catatan Khusus Pelanggan */}
                          {order.notes && (
                            <div className="pt-0.5">
                              <div className="rounded-md border-l-2 border-[#e6b400] bg-[#fef7d6]/60 pl-2.5 py-1 pr-3 text-xs text-[#7a5600]">
                                <span className="font-bold text-[#5c4000]">Catatan Khusus:</span>{' '}
                                <span>{order.notes}</span>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Kolom Kanan: Total Nilai & Tombol Aksi */}
                        <div className="flex flex-row items-center justify-between gap-3 border-t border-[#dad9d6]/60 pt-3 sm:flex-col sm:items-end sm:justify-between sm:border-t-0 sm:pt-0 shrink-0 self-stretch sm:self-auto">
                          <div className="text-left sm:text-right">
                            <span className="text-[11px] font-medium text-[#82827c] block">
                              Total Tagihan
                            </span>
                            <span className="text-base sm:text-lg font-bold font-mono text-[#21201c]">
                              {formatRupiah(order.totalAmount)}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <Link
                              href={`/menu?menuId=${order.menuId}&portions=${order.portions}`}
                              className={cn(
                                buttonVariants({ variant: 'secondary', size: 'sm' }),
                                'h-9 px-3 text-xs font-bold text-[#21201c] gap-1.5 border border-[#dad9d6] bg-white shadow-xs hover:bg-[#f9f9f8]',
                              )}
                            >
                              <RestaurantMenuRoundedIcon
                                sx={{ fontSize: 16 }}
                                className="text-[#9e1b32]"
                                aria-hidden={true}
                              />
                              <span>Hitung Bahan Dapur</span>
                            </Link>
                            <Link
                              href="/pesanan"
                              className={cn(
                                buttonVariants({ variant: 'secondary', size: 'sm' }),
                                'h-9 px-3 text-xs font-bold text-[#21201c] gap-1 border border-[#dad9d6] bg-white shadow-xs hover:bg-[#f9f9f8]',
                              )}
                            >
                              <span>Detail</span>
                              <ArrowForwardRoundedIcon sx={{ fontSize: 14 }} aria-hidden={true} />
                            </Link>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

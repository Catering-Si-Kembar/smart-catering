'use client';

import * as React from 'react';
import Link from 'next/link';
import AccessTimeRoundedIcon from '@mui/icons-material/AccessTimeRounded';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import LocationOnOutlinedIcon from '@mui/icons-material/LocationOnOutlined';
import RestaurantMenuRoundedIcon from '@mui/icons-material/RestaurantMenuRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import {
  MOCK_ORDERS,
  ORDER_STATUS_META,
  PAYMENT_STATUS_META,
  formatRupiah,
  formatTanggalIndonesia,
  type MockOrder,
  type OrderStatus,
} from '@/lib/mock-data';
import { Button, buttonVariants } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { StatusBanner } from '@/components/ui/status-banner';
import { cn } from '@/lib/utils';

export default function OrdersPage() {
  const [orders, setOrders] = React.useState<readonly MockOrder[]>(MOCK_ORDERS);
  const [filterStatus, setFilterStatus] = React.useState<string>('ALL');
  const [searchQuery, setSearchQuery] = React.useState('');
  const [feedbackMessage, setFeedbackMessage] = React.useState<string | null>(null);

  const filteredOrders = React.useMemo(() => {
    return orders.filter((order) => {
      const matchStatus =
        filterStatus === 'ALL' ? true : order.status === filterStatus;
      const matchSearch =
        searchQuery === ''
          ? true
          : order.orderNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
            order.customerAlias.toLowerCase().includes(searchQuery.toLowerCase()) ||
            order.menuName.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStatus && matchSearch;
    });
  }, [orders, filterStatus, searchQuery]);

  const updateOrderStatus = (orderId: string, nextStatus: OrderStatus) => {
    setOrders((prev) =>
      prev.map((o) => (o.id === orderId ? { ...o, status: nextStatus } : o)),
    );
    const target = orders.find((o) => o.id === orderId);
    setFeedbackMessage(
      `Status pesanan ${target?.orderNumber ?? orderId} berhasil diperbarui menjadi "${ORDER_STATUS_META[nextStatus].label}".`,
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[#21201c] sm:text-2xl">
            Pesanan & Jadwal Produksi
          </h1>
          <p className="mt-0.5 text-xs text-[#63635e] sm:text-sm">
            Daftar pesanan katering aktif, status pembayaran DP, dan kesiapan pengantaran dapur.
          </p>
        </div>
      </div>

      {feedbackMessage && (
        <StatusBanner
          tone="success"
          title="Status Pesanan Diperbarui"
          detail={feedbackMessage}
          actionLabel="Tutup"
          onAction={() => setFeedbackMessage(null)}
        />
      )}

      {/* Filter Tabs & Search Bar (Refero SaaS Style) */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200/90 bg-white p-3.5 sm:p-4 shadow-2xs">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1">
            <SearchRoundedIcon
              sx={{ fontSize: 18 }}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              aria-hidden={true}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari nomor pesanan, pemesan, atau menu..."
              className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#fbcc04] focus:outline-none focus:ring-1 focus:ring-[#fbcc04]"
            />
          </div>

          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs font-medium" role="group" aria-label="Filter status pesanan">
            {[
              { key: 'ALL', label: 'Semua Pesanan' },
              { key: 'IN_PREPARATION', label: 'Sedang Masak' },
              { key: 'READY', label: 'Siap Kirim' },
              { key: 'DRAFT', label: 'Menunggu DP' },
            ].map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setFilterStatus(tab.key)}
                className={cn(
                  'rounded-md px-2.5 py-1 text-xs transition font-medium',
                  filterStatus === tab.key
                    ? 'bg-white text-slate-900 font-semibold shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900',
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Orders List */}
      <div className="space-y-3">
        {filteredOrders.length === 0 ? (
          <Card className="border-slate-200 py-10 text-center rounded-xl bg-white shadow-2xs">
            <CardContent>
              <p className="text-sm font-semibold text-slate-800">
                Tidak ada pesanan yang sesuai dengan filter atau kata kunci pencarian.
              </p>
              <Button
                type="button"
                variant="outline"
                className="mt-3 text-xs font-semibold"
                onClick={() => {
                  setFilterStatus('ALL');
                  setSearchQuery('');
                }}
              >
                Reset Pencarian
              </Button>
            </CardContent>
          </Card>
        ) : (
          filteredOrders.map((order) => {
            const statusInfo = ORDER_STATUS_META[order.status];
            const paymentInfo = PAYMENT_STATUS_META[order.paymentStatus];
            const remainingPayment = Math.max(0, order.totalAmount - order.paidAmount);

            return (
              <div
                key={order.id}
                className="rounded-xl border border-slate-200/80 bg-white p-4 sm:p-5 transition hover:border-slate-300 shadow-2xs"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2.5 min-w-0 flex-1">
                    {/* Baris 1: Nomor Pesanan + Clean Status Dot */}
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono font-medium text-slate-500">
                        {order.orderNumber}
                      </span>
                      <span className="text-slate-300">·</span>
                      <div className="inline-flex items-center gap-1.5">
                        <span
                          className={cn(
                            'h-2 w-2 rounded-full shrink-0',
                            order.status === 'READY' && 'bg-emerald-500 ring-2 ring-emerald-100',
                            order.status === 'IN_PREPARATION' && 'bg-amber-500 ring-2 ring-amber-100 animate-pulse',
                            order.status === 'DRAFT' && 'bg-slate-400 ring-2 ring-slate-100',
                          )}
                          aria-hidden="true"
                        />
                        <span
                          className={cn(
                            'font-semibold text-xs',
                            order.status === 'READY' && 'text-emerald-700',
                            order.status === 'IN_PREPARATION' && 'text-amber-800',
                            order.status === 'DRAFT' && 'text-slate-600',
                          )}
                        >
                          {statusInfo.label}
                        </span>
                      </div>
                    </div>

                    <div>
                      <h2 className="text-base sm:text-lg font-bold text-slate-900">
                        {order.menuName}{' '}
                        <span className="text-[#9e1b32] font-bold font-mono">
                          · {order.portions} Box
                        </span>
                      </h2>
                      <p className="mt-0.5 text-xs text-slate-600 font-normal">
                        <span className="text-slate-400">Pemesan:</span>{' '}
                        <span className="font-semibold text-slate-800">{order.customerAlias}</span>
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-y-1.5 gap-x-4 text-xs text-slate-600 font-normal">
                      <div className="flex items-center gap-1.5">
                        <AccessTimeRoundedIcon
                          sx={{ fontSize: 15 }}
                          className="shrink-0 text-slate-400"
                          aria-hidden={true}
                        />
                        <span>
                          <span className="text-slate-400">Jadwal Kirim:</span>{' '}
                          <span className="font-semibold text-slate-800">
                            {formatTanggalIndonesia(order.eventDate)}
                          </span>{' '}
                          · Pukul <span className="font-mono font-semibold text-slate-800">{order.eventTime}</span>
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <LocationOnOutlinedIcon
                          sx={{ fontSize: 15 }}
                          className="shrink-0 text-slate-400"
                          aria-hidden={true}
                        />
                        <span>
                          <span className="text-slate-400">Alamat Kirim:</span>{' '}
                          <span className="font-medium text-slate-800">{order.deliveryArea}</span>
                        </span>
                      </div>
                    </div>

                    {order.notes && (
                      <div className="rounded-md border-l-2 border-amber-500 bg-amber-50/60 pl-2.5 py-1 pr-3 text-xs text-amber-950">
                        <span className="font-bold text-amber-900">Catatan Khusus:</span>{' '}
                        <span className="text-amber-800">{order.notes}</span>
                      </div>
                    )}
                  </div>

                  {/* Operational Quick Actions & Financials */}
                  <div className="flex flex-col gap-2.5 sm:items-end shrink-0 pt-1 lg:pt-0">
                    <div className="text-left sm:text-right">
                      <span className="text-[11px] font-medium text-slate-400">Total Tagihan</span>
                      <p className="text-lg sm:text-xl font-bold font-mono text-slate-900">
                        {formatRupiah(order.totalAmount)}
                      </p>
                      <div className="mt-0.5 flex items-center sm:justify-end gap-1.5 text-[11px] font-medium">
                        {order.paymentStatus === 'PARTIALLY_PAID' && (
                          <>
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" aria-hidden="true" />
                            <span className="text-slate-600">
                              DP Masuk <strong className="text-amber-800 font-semibold">{formatRupiah(order.paidAmount)}</strong> (Sisa: {formatRupiah(remainingPayment)})
                            </span>
                          </>
                        )}
                        {order.paymentStatus === 'PAID' && (
                          <>
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" aria-hidden="true" />
                            <span className="text-emerald-700 font-semibold">Lunas 100%</span>
                          </>
                        )}
                        {order.paymentStatus === 'UNPAID' && (
                          <>
                            <span className="h-1.5 w-1.5 rounded-full bg-rose-500 shrink-0" aria-hidden="true" />
                            <span className="text-rose-600 font-medium">Belum Bayar DP (Min. {formatRupiah(order.totalAmount * 0.6)})</span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <Link
                        href={`/menu?menuId=${order.menuId}&portions=${order.portions}`}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition"
                      >
                        <RestaurantMenuRoundedIcon
                          sx={{ fontSize: 15 }}
                          className="text-[#9e1b32]"
                          aria-hidden={true}
                        />
                        <span>Hitung Bahan Dapur</span>
                      </Link>

                      {order.status === 'IN_PREPARATION' && (
                        <button
                          type="button"
                          onClick={() => updateOrderStatus(order.id, 'READY')}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-emerald-800 transition"
                        >
                          <CheckRoundedIcon sx={{ fontSize: 15 }} aria-hidden={true} />
                          <span>Tandai Siap Diantar</span>
                        </button>
                      )}

                      {order.status === 'READY' && (
                        <button
                          type="button"
                          onClick={() => updateOrderStatus(order.id, 'DELIVERED')}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white shadow-2xs hover:bg-slate-850 transition"
                        >
                          <CheckCircleOutlineRoundedIcon sx={{ fontSize: 15 }} aria-hidden={true} />
                          <span>Tandai Sudah Terkirim</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

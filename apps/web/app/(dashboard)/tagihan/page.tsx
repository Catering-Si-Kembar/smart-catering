'use client';

import { useState } from 'react';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import PaymentsOutlinedIcon from '@mui/icons-material/PaymentsOutlined';
import PrintOutlinedIcon from '@mui/icons-material/PrintOutlined';
import {
  MOCK_ORDERS,
  PAYMENT_STATUS_META,
  calculateMinimumDp,
  formatRupiah,
  type MockOrder,
} from '@/lib/mock-data';
import { useAppRole } from '@/components/shell/role-context';
import { RestrictedNotice } from '@/components/shell/restricted-notice';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBanner } from '@/components/ui/status-banner';

export default function BillingPage() {
  const { role } = useAppRole();
  const [invoices, setInvoices] = useState<readonly MockOrder[]>(MOCK_ORDERS);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(MOCK_ORDERS[0].id);
  const [banner, setBanner] = useState<{ title: string; detail: string } | null>(null);

  if (role !== 'ADMIN') {
    return <RestrictedNotice featureName="Tagihan & Invoice Keuangan" />;
  }

  const selectedInvoice =
    invoices.find((item) => item.id === selectedInvoiceId) ?? invoices[0] ?? MOCK_ORDERS[0];

  const handleRecordDp = (orderId: string) => {
    setInvoices((prev) =>
      prev.map((item) => {
        if (item.id !== orderId) return item;
        const minDp = calculateMinimumDp(item.totalAmount);
        return {
          ...item,
          paidAmount: Math.max(item.paidAmount, minDp),
          paymentStatus: 'PARTIALLY_PAID',
          status: item.status === 'DRAFT' ? 'CONFIRMED' : item.status,
        };
      }),
    );
    setBanner({
      title: 'Pembayaran DP 60% dicatat (Simulasi)',
      detail: 'Status tagihan berubah menjadi DP Masuk dan pesanan otomatis terkonfirmasi.',
    });
  };

  const handleRecordFullPayment = (orderId: string) => {
    setInvoices((prev) =>
      prev.map((item) =>
        item.id === orderId
          ? { ...item, paidAmount: item.totalAmount, paymentStatus: 'PAID' }
          : item,
      ),
    );
    setBanner({
      title: 'Pelunasan dicatat (Simulasi)',
      detail: 'Sisa tagihan sekarang Rp 0 dan status berubah menjadi Lunas.',
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">
          Tagihan, DP 60% & Invoice Digital
        </h1>
        <p className="text-base text-slate-700">
          Khusus Pengelola (ADMIN). Catat uang muka minimal 60%, pelunasan, dan pratinjau cetak
          invoice pesanan.
        </p>
      </div>

      {banner ? (
        <StatusBanner
          tone="success"
          title={banner.title}
          detail={banner.detail}
          actionLabel="Tutup"
          onAction={() => setBanner(null)}
        />
      ) : null}

      <div className="grid gap-5 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-3">
          {invoices.map((invoice) => {
            const minDp = calculateMinimumDp(invoice.totalAmount);
            const remaining = Math.max(0, invoice.totalAmount - invoice.paidAmount);
            const paymentMeta = PAYMENT_STATUS_META[invoice.paymentStatus];

            return (
              <Card
                key={invoice.id}
                className={
                  selectedInvoice.id === invoice.id
                    ? 'border-[#fbcc04] ring-1 ring-[#fbcc04]'
                    : 'border-[#dad9d6]'
                }
              >
                <CardContent className="space-y-3 p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-bold text-slate-700">
                        INV-{invoice.orderNumber.replace('ORD-', '')}
                      </p>
                      <h2 className="text-lg font-bold text-slate-950">{invoice.customerAlias}</h2>
                    </div>
                    <Badge
                      variant="outline"
                      className="border-[#dad9d6] bg-white text-sm font-bold text-slate-950"
                    >
                      {paymentMeta.label}
                    </Badge>
                  </div>

                  <p className="text-sm text-slate-700">
                    {invoice.menuName} · {invoice.portions} porsi · Acara {invoice.eventDate}
                  </p>

                  <div className="grid grid-cols-1 gap-2.5 rounded-xl bg-[#f9f9f8] border border-[#dad9d6] p-3 text-sm tabular-nums sm:grid-cols-3">
                    <div>
                      <p className="text-xs font-semibold text-slate-700">Total</p>
                      <p className="font-bold text-slate-950">
                        {formatRupiah(invoice.totalAmount)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-700">DP Min. 60%</p>
                      <p className="font-bold text-slate-950">{formatRupiah(minDp)}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-700">Sisa Bayar</p>
                      <p className="font-bold text-[#9e1b32]">{formatRupiah(remaining)}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setSelectedInvoiceId(invoice.id)}
                    >
                      <PrintOutlinedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                      Pratinjau Invoice
                    </Button>
                    {invoice.paymentStatus === 'UNPAID' ? (
                      <Button type="button" onClick={() => handleRecordDp(invoice.id)}>
                        <PaymentsOutlinedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                        Catat DP 60%
                      </Button>
                    ) : null}
                    {invoice.paymentStatus !== 'PAID' ? (
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => handleRecordFullPayment(invoice.id)}
                      >
                        <CheckCircleOutlineRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                        Catat Pelunasan
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Pratinjau Lembar Invoice */}
        <Card className="h-fit border-[#dad9d6] lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-xl">Pratinjau Invoice Digital</CardTitle>
            <CardDescription className="text-sm text-slate-700">
              Format ringkas siap cetak PDF (modul penuh di FS-06).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2 rounded-xl border border-[#dad9d6] bg-[#f9f9f8] p-4 text-sm">
              <p className="font-bold text-slate-950">Catering Si Kembar</p>
              <p className="text-slate-700">
                Nomor: INV-{selectedInvoice.orderNumber.replace('ORD-', '')}
              </p>
              <p className="text-slate-700">Pemesan: {selectedInvoice.customerAlias}</p>
              <p className="text-slate-700">
                Item: {selectedInvoice.menuName} ({selectedInvoice.portions} box)
              </p>
              <div className="border-t border-slate-300 pt-2 tabular-nums">
                <p className="flex justify-between">
                  <span>Total Tagihan</span>
                  <strong>{formatRupiah(selectedInvoice.totalAmount)}</strong>
                </p>
                <p className="flex justify-between">
                  <span>Sudah Dibayar</span>
                  <strong>{formatRupiah(selectedInvoice.paidAmount)}</strong>
                </p>
                <p className="flex justify-between text-base font-bold text-slate-950">
                  <span>Sisa Tagihan</span>
                  <span>
                    {formatRupiah(
                      Math.max(0, selectedInvoice.totalAmount - selectedInvoice.paidAmount),
                    )}
                  </span>
                </p>
              </div>
            </div>
            <Button
              type="button"
              size="lg"
              className="w-full"
              onClick={() =>
                setBanner({
                  title: 'Pratinjau cetak invoice siap (Simulasi FS-01)',
                  detail: `Dokumen PDF INV-${selectedInvoice.orderNumber.replace('ORD-', '')} akan diunduh melalui backend Express pada FS-06.`,
                })
              }
            >
              <PrintOutlinedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
              Cetak Invoice
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

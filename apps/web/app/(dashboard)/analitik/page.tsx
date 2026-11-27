'use client';

import { useState } from 'react';
import BarChartRoundedIcon from '@mui/icons-material/BarChartRounded';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import RestaurantMenuRoundedIcon from '@mui/icons-material/RestaurantMenuRounded';
import TrendingUpRoundedIcon from '@mui/icons-material/TrendingUpRounded';
import { formatRupiah } from '@/lib/mock-data';
import { useAppRole } from '@/components/shell/role-context';
import { RestrictedNotice } from '@/components/shell/restricted-notice';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBanner } from '@/components/ui/status-banner';

type PeriodKey = '7d' | '30d';

const PERIOD_DATA: Record<
  PeriodKey,
  {
    readonly label: string;
    readonly revenue: number;
    readonly portions: number;
    readonly positiveSentimentPct: number;
    readonly forecastNextWeek: number;
  }
> = {
  '7d': {
    label: '7 Hari Terakhir',
    revenue: 8_750_000,
    portions: 320,
    positiveSentimentPct: 86,
    forecastNextWeek: 350,
  },
  '30d': {
    label: '30 Hari Terakhir',
    revenue: 34_200_000,
    portions: 1_240,
    positiveSentimentPct: 84,
    forecastNextWeek: 380,
  },
};

export default function AnalyticsPage() {
  const { role } = useAppRole();
  const [period, setPeriod] = useState<PeriodKey>('7d');
  const [downloadNotice, setDownloadNotice] = useState(false);

  if (role !== 'ADMIN') {
    return <RestrictedNotice featureName="Dasbor Analitik Bisnis" />;
  }

  const metrics = PERIOD_DATA[period];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">
            Dasbor Analitik & Prediksi Permintaan
          </h1>
          <p className="text-base text-slate-700">
            Khusus Pengelola (ADMIN). Pratinjau tata letak KPI, forecasting per menu, dan ringkasan
            sentimen (integrasi penuh DS-05 & FS-08).
          </p>
        </div>
        <Button type="button" size="lg" onClick={() => setDownloadNotice(true)}>
          <DownloadRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
          Unduh Laporan PDF
        </Button>
      </div>

      {downloadNotice ? (
        <StatusBanner
          tone="success"
          title="Pratinjau unduh laporan analitik (Simulasi FS-01)"
          detail={`Ringkasan PDF periode ${metrics.label} akan dihasilkan bersama AI Business Insight pada modul FS-08 & AI-06.`}
          actionLabel="Tutup"
          onAction={() => setDownloadNotice(false)}
        />
      ) : null}

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter periode">
        <Button
          type="button"
          variant={period === '7d' ? 'default' : 'outline'}
          onClick={() => setPeriod('7d')}
        >
          7 Hari Terakhir
        </Button>
        <Button
          type="button"
          variant={period === '30d' ? 'default' : 'outline'}
          onClick={() => setPeriod('30d')}
        >
          30 Hari Terakhir
        </Button>
        <Badge
          variant="outline"
          className="border-amber-400 bg-amber-50 text-xs font-bold text-amber-950"
        >
          Data Simulasi (isSynthetic = true)
        </Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-[#dad9d6] bg-white shadow-xs">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#82827c]">
                Estimasi Omzet
              </span>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#fbcc04]/20 text-[#21201c]">
                <BarChartRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl font-extrabold tabular-nums tracking-tight text-[#21201c]">
                {formatRupiah(metrics.revenue)}
              </span>
            </div>
            <p className="mt-2 text-xs text-[#82827c]">{metrics.label}</p>
          </CardContent>
        </Card>

        <Card className="border-[#dad9d6] bg-white shadow-xs">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#82827c]">
                Porsi Terjual
              </span>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#ecfdf5] text-[#166534]">
                <RestaurantMenuRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-1.5">
              <span className="text-2xl font-extrabold tabular-nums tracking-tight text-[#21201c]">
                {metrics.portions.toLocaleString('id-ID')}
              </span>
              <span className="text-sm font-semibold text-[#63635e]">Box</span>
            </div>
            <p className="mt-2 text-xs text-[#82827c]">Dominan Ayam Lengkuas</p>
          </CardContent>
        </Card>

        <Card className="border-[#dad9d6] bg-white shadow-xs">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#82827c]">
                Prediksi Depan
              </span>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#fdf2f4] text-[#9e1b32]">
                <TrendingUpRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-1.5">
              <span className="text-2xl font-extrabold tabular-nums tracking-tight text-[#9e1b32]">
                {metrics.forecastNextWeek}
              </span>
              <span className="text-sm font-semibold text-[#63635e]">Box</span>
            </div>
            <p className="mt-2 text-xs text-[#82827c]">Model Random Forest DS-05</p>
          </CardContent>
        </Card>

        <Card className="border-[#dad9d6] bg-white shadow-xs">
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#82827c]">
                Sentimen Positif
              </span>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#f5eff8] text-[#5c3271]">
                <BarChartRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
              </div>
            </div>
            <div className="mt-3">
              <span className="text-2xl font-extrabold tabular-nums tracking-tight text-[#21201c]">
                {metrics.positiveSentimentPct}%
              </span>
            </div>
            <p className="mt-2 text-xs text-[#82827c]">Ulasan Sintetis AI-03</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-[#dad9d6]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg text-slate-950">
            <BarChartRoundedIcon sx={{ fontSize: 22 }} className="text-[#5c3271]" aria-hidden={true} />
            Ringkasan AI Business Insight (Pratinjau Layout)
          </CardTitle>
          <CardDescription className="text-sm text-slate-700">
            Slot narasi ringkas dalam bahasa Indonesia lugas agar pengelola langsung paham rencana
            belanja minggu depan.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-base leading-relaxed text-slate-800">
          <p>
            • Permintaan tertinggi diproyeksikan pada hari Jumat - Sabtu untuk paket Nasi Box Ayam
            Goreng Lengkuas (estimasi 220 box).
          </p>
          <p>
            • Saran persiapan bahan utama minggu depan (simulasi): Beras Putih ±52,5 kg dan Ayam
            Potong ±27,5 kg.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

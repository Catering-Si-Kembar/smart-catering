import type { HealthResponse } from '@smart-catering/types';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const EXPECTED_API_HEALTH: HealthResponse = {
  data: { status: 'ok', service: 'api' },
  meta: { requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
};

const WORKSPACE_ITEMS = [
  {
    name: '@smart-catering/web',
    detail: 'Frontend Next.js App Router pada port lokal 3000 (target deploy Vercel).',
  },
  {
    name: '@smart-catering/api',
    detail:
      'Backend Express.js REST (/api/v1) dengan validasi Joi pada port lokal 3001 (target deploy VPS).',
  },
  {
    name: '@smart-catering/ai-service',
    detail:
      'Backend Python + FastAPI dengan uv pada port lokal 8001; RAG, Chroma, dan ML belum diaktifkan (target deploy VPS).',
  },
  {
    name: '@smart-catering/worker',
    detail:
      'Layanan worker Node.js dengan endpoint liveness internal pada 127.0.0.1:3002 (target deploy VPS).',
  },
  {
    name: '@smart-catering/db',
    detail:
      'Paket akses database Prisma 7 + PostgreSQL dengan inisialisasi lazy getDb() tanpa tabel bisnis.',
  },
  {
    name: '@smart-catering/types',
    detail: 'Paket kontrak tipe TypeScript ESM bersama untuk komunikasi antar-workspace.',
  },
] as const;

const PHASE_ZERO_BOUNDARIES = [
  'Belum menyertakan autentikasi pengguna, sesi login, atau manajemen akun.',
  'Belum menyertakan CRUD pesanan, menu/resep standar, pembayaran/invoice, maupun model database bisnis.',
  'Belum menjalankan pipeline RAG/Chroma aktif, training/inference ML, atau pengiriman pesan WhatsApp (WAHA).',
  'Halaman ini tidak melakukan pemanggilan jaringan langsung ke API pada Fase 0; variabel API_BASE_URL disiapkan khusus di sisi server untuk integrasi SSR berikutnya.',
] as const;

export default function HomePage() {
  const appName = process.env.NEXT_PUBLIC_APP_NAME?.trim() || 'Smart Catering';

  return (
    <div className="mx-auto max-w-5xl px-5 py-10 sm:py-16">
      <header className="mb-7 rounded-xl border border-slate-300 bg-white p-8 shadow-sm">
        <Badge variant="outline" className="border-emerald-300 bg-emerald-50 text-emerald-800">
          Fase 0: Fondasi Monorepo Hybrid Minimal
        </Badge>
        <h1 className="mt-3.5 mb-2 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          {appName}
        </h1>
        <p className="max-w-3xl text-base leading-relaxed text-slate-700">
          Fondasi awal monorepo telah aktif. Antarmuka ini menampilkan status kesiapan struktur
          workspace Fase 0 secara jujur tanpa dasbor atau data bisnis tiruan.
        </p>
      </header>

      <main id="konten-utama" tabIndex={-1} className="outline-none">
        <div className="mb-6 grid grid-cols-1 gap-5 md:grid-cols-2">
          <Card aria-labelledby="judul-workspace">
            <CardHeader>
              <CardTitle id="judul-workspace" className="text-xl font-semibold text-slate-900">
                Arsitektur 6 Workspace
              </CardTitle>
              <CardDescription className="text-sm text-slate-600">
                Seluruh paket internal terhubung melalui npm Workspaces dengan versi terkunci{' '}
                <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  0.0.0
                </code>
                :
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-slate-700">
                {WORKSPACE_ITEMS.map((item) => (
                  <li key={item.name}>
                    <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                      {item.name}
                    </code>
                    : {item.detail}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card aria-labelledby="judul-kontrak-health">
            <CardHeader>
              <CardTitle id="judul-kontrak-health" className="text-xl font-semibold text-slate-900">
                Kontrak Liveness API
              </CardTitle>
              <CardDescription className="text-sm leading-relaxed text-slate-600">
                Endpoint{' '}
                <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  GET /health
                </code>{' '}
                dan{' '}
                <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  GET /api/v1/health
                </code>{' '}
                pada{' '}
                <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  @smart-catering/api
                </code>{' '}
                (port lokal{' '}
                <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  3001
                </code>
                ) menggunakan tipe{' '}
                <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  HealthResponse
                </code>{' '}
                dari{' '}
                <code className="rounded border border-slate-300 bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  @smart-catering/types
                </code>{' '}
                tanpa ketergantungan koneksi database saat eksekusi. Berikut contoh respons;
                requestId aktual dibuat per permintaan:
              </CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 font-mono text-xs text-slate-100 whitespace-pre-wrap break-all sm:text-sm">
                <code>{JSON.stringify(EXPECTED_API_HEALTH, null, 2)}</code>
              </pre>
            </CardContent>
          </Card>
        </div>

        <Card aria-labelledby="judul-batasan-fase0">
          <CardHeader>
            <CardTitle id="judul-batasan-fase0" className="text-xl font-semibold text-slate-900">
              Batasan Ruang Lingkup Fase 0
            </CardTitle>
            <CardDescription className="text-sm text-slate-600">
              Sesuai kontrak arsitektur Fase 0, fitur-fitur berikut sengaja belum diaktifkan:
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700">
              {PHASE_ZERO_BOUNDARIES.map((boundary) => (
                <li key={boundary}>{boundary}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </main>

      <footer className="mt-8 border-t border-slate-300 pt-5 text-sm text-slate-600">
        <p>
          <strong>{appName}</strong>: Setup Monorepo Fase 0. Konfigurasi frontend disiapkan untuk
          Vercel, sedangkan layanan API, AI service, worker, PostgreSQL, Chroma, dan WAHA disiapkan
          untuk lingkungan VPS.
        </p>
      </footer>
    </div>
  );
}

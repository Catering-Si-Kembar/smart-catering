import type { HealthResponse } from '@smart-catering/types';

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
    detail: 'Backend Next.js Route Handlers standalone pada port lokal 3001 (target deploy VPS).',
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
  'Belum menyertakan CRUD pesanan, inventaris dapur, pembayaran, maupun model database bisnis.',
  'Belum menjalankan pipeline RAG/Chroma aktif, training/inference ML, atau pengiriman pesan WhatsApp (WAHA).',
  'Halaman ini tidak melakukan pemanggilan jaringan langsung ke API pada Fase 0; variabel API_BASE_URL disiapkan khusus di sisi server untuk integrasi SSR berikutnya.',
] as const;

export default function HomePage() {
  const appName = process.env.NEXT_PUBLIC_APP_NAME?.trim() || 'Smart Catering';

  return (
    <div className="page-shell">
      <header className="hero-header">
        <span className="status-badge">Fase 0 — Fondasi Monorepo Hybrid Minimal</span>
        <h1 className="hero-title">{appName}</h1>
        <p className="hero-subtitle">
          Fondasi awal monorepo telah aktif. Antarmuka ini menampilkan status kesiapan struktur
          workspace Fase 0 secara jujur tanpa dasbor atau data bisnis tiruan.
        </p>
      </header>

      <main id="konten-utama" tabIndex={-1}>
        <div className="section-grid">
          <section className="card" aria-labelledby="judul-workspace">
            <h2 id="judul-workspace" className="card-title">
              Arsitektur 6 Workspace
            </h2>
            <p className="card-description">
              Seluruh paket internal terhubung melalui npm Workspaces dengan versi terkunci{' '}
              <code className="code-inline">0.0.0</code>:
            </p>
            <ul className="workspace-list">
              {WORKSPACE_ITEMS.map((item) => (
                <li key={item.name}>
                  <code className="code-inline">{item.name}</code> — {item.detail}
                </li>
              ))}
            </ul>
          </section>

          <section className="card" aria-labelledby="judul-kontrak-health">
            <h2 id="judul-kontrak-health" className="card-title">
              Kontrak Liveness API
            </h2>
            <p className="card-description">
              Endpoint <code className="code-inline">GET /health</code> pada{' '}
              <code className="code-inline">@smart-catering/api</code> (port lokal{' '}
              <code className="code-inline">3001</code>) menggunakan tipe{' '}
              <code className="code-inline">HealthResponse</code> dari{' '}
              <code className="code-inline">@smart-catering/types</code> tanpa ketergantungan
              koneksi database saat eksekusi. Berikut contoh respons; requestId aktual dibuat per
              permintaan:
            </p>
            <pre className="code-block">
              <code>{JSON.stringify(EXPECTED_API_HEALTH, null, 2)}</code>
            </pre>
          </section>
        </div>

        <section className="card" aria-labelledby="judul-batasan-fase0">
          <h2 id="judul-batasan-fase0" className="card-title">
            Batasan Ruang Lingkup Fase 0
          </h2>
          <p className="card-description">
            Sesuai kontrak arsitektur Fase 0, fitur-fitur berikut sengaja belum diaktifkan:
          </p>
          <ul className="boundary-list">
            {PHASE_ZERO_BOUNDARIES.map((boundary) => (
              <li key={boundary}>{boundary}</li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="page-footer">
        <p>
          <strong>{appName}</strong> — Setup Monorepo Fase 0. Konfigurasi frontend disiapkan untuk
          Vercel, sedangkan layanan API, AI service, worker, PostgreSQL, Chroma, dan WAHA disiapkan
          untuk lingkungan VPS.
        </p>
      </footer>
    </div>
  );
}

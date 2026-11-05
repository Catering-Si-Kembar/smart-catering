import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Smart Catering',
    template: '%s | Smart Catering',
  },
  description:
    'Halaman status setup Fase 0 monorepo Smart Catering (Next.js App Router, API terpisah, worker liveness, Prisma PostgreSQL).',
};

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="id">
      <body>
        <a className="skip-link" href="#konten-utama">
          Lewati ke konten utama
        </a>
        {children}
      </body>
    </html>
  );
}

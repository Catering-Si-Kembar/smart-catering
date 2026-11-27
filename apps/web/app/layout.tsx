import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { RoleProvider } from '@/components/shell/role-context';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-sans',
  weight: ['400', '500', '600', '700', '800'],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
  weight: ['400', '500', '600', '700'],
});

export const metadata: Metadata = {
  title: {
    default: 'Smart Catering',
    template: '%s | Smart Catering',
  },
  description:
    'Sistem operasional katering Catering Si Kembar (Next.js App Router, Tailwind CSS, API terpisah, Prisma PostgreSQL).',
};

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="id" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="font-sans antialiased selection:bg-[#fbcc04]/30 selection:text-[#21201c]">
        <a className="skip-link" href="#konten-utama">
          Lewati ke konten utama
        </a>
        <RoleProvider>{children}</RoleProvider>
      </body>
    </html>
  );
}

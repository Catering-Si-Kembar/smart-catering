import type { ReactNode } from 'react';
import { AppShell } from '@/components/shell/app-shell';

export default function DashboardLayout({ children }: { readonly children: ReactNode }) {
  const appName = process.env.NEXT_PUBLIC_APP_NAME?.trim() || 'Smart Catering';

  return <AppShell appName={appName}>{children}</AppShell>;
}

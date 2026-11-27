'use client';

import Link from 'next/link';
import AdminPanelSettingsRoundedIcon from '@mui/icons-material/AdminPanelSettingsRounded';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import { useAppRole } from '@/components/shell/role-context';
import { Button, buttonVariants } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export interface RestrictedNoticeProps {
  readonly featureName: string;
}

export function RestrictedNotice({ featureName }: RestrictedNoticeProps) {
  const { setRole } = useAppRole();

  return (
    <div className="mx-auto max-w-xl py-10">
      <Card className="border-amber-300 bg-amber-50/50">
        <CardHeader className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-800">
            <LockOutlinedIcon sx={{ fontSize: 28 }} aria-hidden={true} />
          </div>
          <CardTitle className="mt-4 text-2xl font-bold text-slate-950">
            Akses Terbatas: Khusus Pengelola (ADMIN)
          </CardTitle>
          <CardDescription className="text-base text-slate-700">
            Halaman <span className="font-semibold text-slate-900">{featureName}</span> dikhususkan untuk
            pemilik dan pengelola katering. Akun Anda saat ini berada dalam mode staf dapur (STAFF).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border border-amber-300 bg-white p-4 text-sm text-slate-800">
            <p className="font-semibold text-slate-900">Perlu menguji halaman ini?</p>
            <p className="mt-1 leading-relaxed text-slate-700">
              Gunakan simulasi switcher peran di bawah atau di pojok atas untuk berganti ke peran ADMIN
              (simulasi FS-01).
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              type="button"
              className="flex-1 min-h-[44px]"
              onClick={() => setRole('ADMIN')}
            >
              <AdminPanelSettingsRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
              Beralih ke Mode ADMIN
            </Button>
            <Link
              href="/"
              className={cn(buttonVariants({ variant: 'outline' }), 'flex-1 min-h-[44px] text-center')}
            >
              <ArrowBackRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
              Kembali ke Jadwal
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

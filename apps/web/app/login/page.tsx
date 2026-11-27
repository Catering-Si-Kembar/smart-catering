'use client';

import { useState, type FormEvent } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import LoginRoundedIcon from '@mui/icons-material/LoginRounded';
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import { useAppRole } from '@/components/shell/role-context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBanner } from '@/components/ui/status-banner';

export default function LoginPage() {
  const router = useRouter();
  const { setRole } = useAppRole();
  const [username, setUsername] = useState('admin_catering');
  const [password, setPassword] = useState('demo-simulasi-fs01');
  const [showPassword, setShowPassword] = useState(false);
  const [selectedRole, setSelectedRole] = useState<'ADMIN' | 'STAFF'>('ADMIN');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage('Nama pengguna dan kata sandi wajib diisi sebelum masuk.');
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);
    setRole(selectedRole);

    window.setTimeout(() => {
      setIsSubmitting(false);
      router.push('/');
    }, 350);
  };

  return (
    <main
      id="konten-utama"
      tabIndex={-1}
      className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-8"
    >
      <div className="w-full max-w-md space-y-5">
        <div className="flex flex-col items-center text-center">
          <Image
            src="/logo-katering-si-kembar.png"
            alt="Logo Catering Si Kembar"
            width={72}
            height={72}
            className="h-18 w-18 rounded-full border border-[#dad9d6] bg-white object-cover shadow-sm"
            priority
          />
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-950">Smart Catering</h1>
          <p className="mt-1 text-base text-slate-700">
            Masuk ke Sistem Operasional Catering Si Kembar
          </p>
        </div>

        <Card className="border-[#dad9d6] shadow-sm">
          <CardHeader>
            <CardTitle className="text-xl">Masuk Akun Staf</CardTitle>
            <CardDescription className="text-sm text-slate-700">
              Mode mockup FS-01: pilih peran simulasi di bawah untuk mencoba tampilan Pengelola atau
              Staf Dapur.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {errorMessage ? (
              <StatusBanner tone="error" title="Data masuk belum lengkap" detail={errorMessage} />
            ) : null}

            <div className="grid grid-cols-2 gap-2.5" role="group" aria-label="Pilih akun simulasi">
              <Button
                type="button"
                variant={selectedRole === 'ADMIN' ? 'default' : 'outline'}
                onClick={() => {
                  setSelectedRole('ADMIN');
                  setUsername('admin_catering');
                }}
              >
                Pengelola (ADMIN)
              </Button>
              <Button
                type="button"
                variant={selectedRole === 'STAFF' ? 'default' : 'outline'}
                onClick={() => {
                  setSelectedRole('STAFF');
                  setUsername('staf_dapur_01');
                }}
              >
                Staf Dapur (STAFF)
              </Button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="space-y-1.5">
                <label htmlFor="username" className="block text-sm font-bold text-slate-900">
                  Nama Pengguna
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="min-h-12 w-full rounded-lg border border-slate-400 bg-white px-3.5 text-base text-slate-950 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Contoh: admin_catering"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="password" className="block text-sm font-bold text-slate-900">
                  Kata Sandi
                </label>
                <div className="flex gap-2">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="min-h-12 w-full rounded-lg border border-slate-400 bg-white px-3.5 text-base text-slate-950 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
                    placeholder="Masukkan kata sandi"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? 'Sembunyikan kata sandi' : 'Tampilkan kata sandi'}
                    className="h-12 w-12 shrink-0 border-slate-400"
                  >
                    {showPassword ? (
                      <VisibilityOffOutlinedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
                    ) : (
                      <VisibilityOutlinedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
                    )}
                  </Button>
                </div>
              </div>

              <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
                <LoginRoundedIcon sx={{ fontSize: 20 }} aria-hidden={true} />
                {isSubmitting ? 'Sedang Masuk...' : 'Masuk ke Aplikasi'}
              </Button>
            </form>

            <div className="border-t border-slate-200 pt-3">
              <Link
                href="/"
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg text-sm font-semibold text-slate-800 hover:bg-slate-100"
              >
                <ArrowBackRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                Kembali ke Jadwal Hari Ini
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

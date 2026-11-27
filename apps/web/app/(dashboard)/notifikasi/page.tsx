'use client';

import { useState } from 'react';
import DoneAllRoundedIcon from '@mui/icons-material/DoneAllRounded';
import NotificationsNoneRoundedIcon from '@mui/icons-material/NotificationsNoneRounded';
import { MOCK_NOTIFICATIONS, type MockNotification } from '@/lib/mock-data';
import { useAppRole } from '@/components/shell/role-context';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { StatusBanner } from '@/components/ui/status-banner';

export default function NotificationsPage() {
  const { role } = useAppRole();
  const [items, setItems] = useState<readonly MockNotification[]>(MOCK_NOTIFICATIONS);

  const visibleItems = items.filter((item) => role === 'ADMIN' || !item.adminOnly);
  const unreadCount = visibleItems.filter((item) => !item.isRead).length;

  const markAsRead = (id: string) => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, isRead: true } : item)));
  };

  const markAllRead = () => {
    setItems((prev) =>
      prev.map((item) => (role === 'ADMIN' || !item.adminOnly ? { ...item, isRead: true } : item)),
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950">
            Pengingat Operasional
          </h1>
          <p className="text-base text-slate-700">
            Notifikasi otomatis jadwal H-1, saran belanja bahan, dan pengingat tagihan sesuai peran.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={markAllRead} disabled={unreadCount === 0}>
          <DoneAllRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
          Tandai Semua Dibaca
        </Button>
      </div>

      {unreadCount === 0 ? (
        <StatusBanner
          tone="success"
          title="Semua pengingat sudah dibaca"
          detail="Tidak ada pengingat baru yang menunggu perhatian Anda saat ini."
        />
      ) : null}

      <div className="space-y-3">
        {visibleItems.map((item) => (
          <Card
            key={item.id}
            className={
              item.isRead ? 'border-[#dad9d6] bg-[#f9f9f8]' : 'border-[#fbcc04] bg-white shadow-xs'
            }
          >
            <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <NotificationsNoneRoundedIcon
                    sx={{ fontSize: 18 }}
                    className="text-primary"
                    aria-hidden={true}
                  />
                  <Badge variant="secondary" className="text-xs font-bold text-slate-900">
                    {item.category}
                  </Badge>
                  <span className="text-xs font-medium text-slate-700">{item.timeLabel}</span>
                  {!item.isRead ? (
                    <Badge className="bg-primary text-xs text-primary-foreground">Baru</Badge>
                  ) : null}
                </div>
                <h2 className="text-base font-bold text-slate-950">{item.title}</h2>
                <p className="text-sm leading-relaxed text-slate-700">{item.message}</p>
              </div>
              {!item.isRead ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => markAsRead(item.id)}
                  className="shrink-0"
                >
                  Tandai Sudah Dibaca
                </Button>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

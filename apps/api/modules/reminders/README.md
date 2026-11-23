# Modul `reminders`

Batas modul untuk pengelolaan jadwal pengingat pesanan terdekat, pembayaran, ringkasan keuangan mingguan, serta pencatatan status pengiriman idempotent untuk mencegah duplikasi antar kanal (`in-app`, WhatsApp via WAHA, dan email opsional).

**Boundary:** Skeleton struktural. Penjadwalan cron dijalankan terpisah oleh `apps/worker`.

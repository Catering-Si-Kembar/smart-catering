# Integrasi `email` (`apps/api/integrations/email`)

Batas adapter pengiriman email opsional (SendGrid/SMTP) untuk notifikasi dan pengingat operasional.

**Boundary:** Kredensial SMTP/API hanya dibaca dari environment server (`process.env`), tidak pernah diekspos ke browser atau disimpan di kode sumber.

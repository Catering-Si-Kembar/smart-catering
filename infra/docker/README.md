# Infrastruktur Docker Smart Catering (`infra/docker`)

Direktori ini berisi konfigurasi container untuk **pengembangan lokal** dan **produksi VPS (`OPS-02` / Issue #24)**.

## Daftar Berkas

| Berkas                                           | Fungsi                                                                                                                              |
| :----------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| [`compose.dev.yaml`](compose.dev.yaml)           | Infrastruktur lokal (`postgres`, `chroma`, opt-in `waha`) dengan port loopback `127.0.0.1`                                          |
| [`compose.vps.yaml`](compose.vps.yaml)           | Stack produksi VPS terisolasi (`postgres`, `chroma`, `api`, `ai-service`, `worker`, opt-in `proxy` Caddy HTTPS, opt-in `waha`)      |
| [`Caddyfile`](Caddyfile)                         | Reverse proxy HTTPS otomatis (Caddy 2) yang hanya mengekspos `/api/v1/*` & `/health` dengan TLS, batas metode HTTP, dan redaksi log |
| [`api.Dockerfile`](api.Dockerfile)               | Image produksi Express API (`node:24.15.0-alpine3.23`, non-root)                                                                    |
| [`ai-service.Dockerfile`](ai-service.Dockerfile) | Image produksi FastAPI + extras `--extra ml --extra rag --extra insight` (`python:3.12.16-slim-bookworm`, non-root)                 |
| [`worker.Dockerfile`](worker.Dockerfile)         | Image produksi Worker Node.js independen (`node:24.15.0-alpine3.23`, non-root)                                                      |
| [`verify-vps.sh`](verify-vps.sh)                 | Skrip verifikasi live di VPS (`healthy`, isolasi port publik, HTTPS TLS, dan uji persistensi restart)                               |

## Preflight Lokal & Panduan Lengkap

Jalankan dari root repository sebelum membuka Pull Request:

```sh
npm run infra:vps:check
```

Lihat panduan provisioning VPS, firewall UFW, konfigurasi `.env`, backup, dan rollback pada [`docs/deployment-vps.md`](../../docs/deployment-vps.md).

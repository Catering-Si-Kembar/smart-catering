# Spesifikasi Teknis: Full-Stack (`01-fullstack.md`)

Berkas ini memuat spesifikasi teknis lengkap untuk 9 issue area Full-Stack (`FS-01` s.d. `FS-09`) mencakup frontend Next.js App Router, backend Express `/api/v1`, skema database Prisma PostgreSQL, dan integrasi modul katering.

---

## [FS-01] App Mockup, Desain Responsif & App Shell Staf Senior

- **Labels:** `area:fullstack`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Milestone:** `M1 (21–27 Nov 2026)`
- **Target Path:** `apps/web`

### Context

Operasional katering Catering Si Kembar melibatkan staf dapur dan staf operasional senior yang kurang terbiasa dengan antarmuka digital yang rumit. Sistem memerlukan rancangan mockup dan fondasi layout (App Shell) yang responsif untuk perangkat mobile dan desktop, memiliki kontras tinggi, navigasi intuitif dengan terminologi familiar (Pesanan, Dapur/Resep, Tagihan, Jadwal), serta tombol aksi berukuran minimal 44x44 px agar nyaman disentuh di perangkat ponsel saat berada di area dapur.

### Scope

**In-Scope:**

- Pembuatan rancangan mockup desain aplikasi web (alur pesanan, kalkulator bahan, invoice, dasbor jadwal).
- Pembuatan layout dasar (App Shell): Header, Sidebar/Bottom Navigation responsif, status bar jaringan, dan penampung konten utama (`main`).
- Penerapan tema visual dengan kontras ramah mata, tipografi jelas, dan komponen UI berbasis Tailwind CSS dan shadcn/ui.
- Pengaturan breakpoint responsif teruji pada resolusi mobile (`390x844`) dan desktop (`1440x900`).

**Out-of-Scope:**

- Integrasi data API dinamis (masih menggunakan representasi wireframe/komponen antarmuka).
- Fitur tema gelap (_dark mode_) kustom berlebih di luar kebutuhan kontras operasional dapur.

### Business Rules

- Navigasi utama harus dapat diakses maksimal dalam 2 ketukan/klik dari layar mana pun.
- Teks label tombol aksi penting harus menggunakan kata kerja bahasa Indonesia yang lugas (misal: "Simpan Pesanan", "Cetak Invoice", "Lihat Bahan").
- Seluruh elemen interaktif wajib memiliki area sentuh minimal 44x44 px untuk kenyamanan operasional layar sentuh.

### API Contract

Tidak berlaku (tugas non-API). Modul ini membangun fondasi UI shell, layouting responsif, dan aset mockup frontend di `apps/web`.

### Acceptance Criteria

- [ ] Tersedia dokumen visual mockup atau halaman prototipe statis di `apps/web/app/(dashboard)` yang mencakup seluruh alur layar utama.
- [ ] Navigasi responsif beralih mulus: sidebar vertikal pada desktop (`>= 1024px`) dan bottom bar / hamburger drawer pada mobile (`< 768px`).
- [ ] Tidak ada pergeseran tata letak horizontal (_horizontal scroll/overflow_) pada tampilan ponsel `390px`.
- [ ] Kontras warna teks memenuhi standar aksesibilitas WCAG AA (minimal rasio 4.5:1).

### Technical Notes

- Desain tombol dan navigasi disesuaikan untuk kenyamanan staf operasional senior `[Perlu Konfirmasi Tim]`.
- Keputusan desain layout, rasio font, dan hierarki navigasi didokumentasikan pada panduan antarmuka.

### DoD

- [ ] Mockup visual disetujui tim dan diimplementasikan ke dalam App Shell Next.js.
- [ ] Halaman dashboard shell lolos uji render responsif di browser desktop dan simulasi mobile tanpa layout error.
- [ ] Prettier dan linter ESLint pada `apps/web` lulus tanpa peringatan.

### Dependencies

- Prasyarat: Konfigurasi Tailwind CSS dan shadcn/ui pada monorepo.
- Terkait: Menjadi kerangka layout untuk `FS-04`, `FS-05`, `FS-06`, `FS-07`, dan `FS-08`.

---

## [FS-02] Skema Database Prisma, Migrasi & Seed Data Uji

- **Labels:** `area:fullstack`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Milestone:** `M1 (21–27 Nov 2026)`
- **Target Path:** `packages/db`

### Context

Kebutuhan transaksi katering mencakup manajemen pesanan, katalog menu, formulasi resep, kalkulasi bahan baku, invoice pembayaran (DP dan pelunasan), serta pencatatan riwayat inferensi chat AI. Seluruh entitas ini memerlukan skema database relasional PostgreSQL yang konsisten, berintegritas tinggi dengan _foreign keys_ yang tepat, serta dilengkapi script migrasi dan seed data awal.

### Scope

**In-Scope:**

- Perancangan file skema Prisma (`packages/db/prisma/schema.prisma`).
- Entitas utama: `User` (`role`: `ADMIN`, `STAFF`), `Customer`, `Menu`, `Ingredient`, `RecipeItem`, `Order` (`status`: `OrderStatus`), `OrderItem`, `Invoice` (`paymentStatus`: `PaymentStatus`), `Payment` (`type`: `DOWN_PAYMENT`, `FINAL_PAYMENT`), `ChatLog`, `NotificationLog`.
- Script seed data awal (`packages/db/prisma/seed.ts`) yang memuat akun staf uji, menu standar nasi box, resep bahan baku, dan riwayat pesanan simulasi.
- Mekanisme migrasi skema dan validasi relasi data.

**Out-of-Scope:**

- Tabel inventaris stok gudang real-time atau pencatatan transaksi mutasi keluar-masuk stok harian (fokus MVP pada resep standar dan kalkulasi agregasi bahan baku otomatis).
- Integrasi payment gateway eksternal (status pembayaran dicatat secara manual oleh staf).

### Business Rules

- Setiap `Order` wajib memiliki minimal 1 `OrderItem`.
- Setiap `Invoice` berelasi satu-ke-satu (`1:1`) dengan `Order`.
- Pembayaran dicatat dalam entitas `Payment` bertipe `DOWN_PAYMENT` (DP) atau `FINAL_PAYMENT` (Pelunasan).
- Data benih uji wajib menandai data simulasi dengan flag atau kategori jelas agar tidak tercampur dengan data operasional riil.

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan Prisma Client yang dikompilasi ke package internal `@smart-catering/db`.

### Acceptance Criteria

- [ ] Skema Prisma berhasil divalidasi via `npm run db:validate`.
- [ ] Prisma Client berhasil digenerate via `npm run db:generate`.
- [ ] Script seeding mengeksekusi insert data pengguna, menu, resep, dan pesanan uji ke PostgreSQL tanpa relasi foreign key yang putus.
- [ ] Seluruh enum status didefinisikan ketat: `OrderStatus (DRAFT, CONFIRMED, IN_PREPARATION, READY, DELIVERED, CANCELLED)` dan `PaymentStatus (UNPAID, PARTIALLY_PAID, PAID)`.
- [ ] Role pengguna dibakukan menjadi `ADMIN` dan `STAFF`.

### Technical Notes

- Besaran default persentase uang muka minimum adalah 60% `[Menunggu Konfirmasi PIC]`.
- Nama bahan baku dan satuan baku (gram, butir, lembar, kg) dikonsolidasikan dengan tim Data Science `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Berkas `packages/db/prisma/schema.prisma` dan migrasi tersimpan rapi.
- [ ] Test integrasi database pada suite Vitest lulus saat mengakses data hasil migrasi.
- [ ] Tidak ada penulisan kredensial database langsung di dalam file skema (menggunakan `DATABASE_URL`).

### Dependencies

- Prasyarat: Konfigurasi container PostgreSQL di `infra/docker/compose.vps.yaml` atau koneksi PostgreSQL lokal.
- Terkait: Menjadi pondasi wajib bagi `FS-03`, `FS-04`, `FS-05`, `FS-06`, `FS-07`.

---

## [FS-03] Autentikasi, RBAC & Standar Validasi Express `/api/v1` (Joi)

- **Labels:** `area:fullstack`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Milestone:** `M1 (21–27 Nov 2026)`
- **Target Path:** `apps/api/modules/auth`, `apps/api/src/routes`

### Context

Aplikasi katering digunakan oleh beberapa tingkatan peran pengguna: Pemilik/Pengelola (Owner/Admin) yang berhak melihat laporan keuangan dan analitik, serta Staf Operasional Dapur yang hanya berhak melihat daftar pesanan dan resep kebutuhan bahan. Diperlukan sistem autentikasi berbasis session/JWT aman, middleware RBAC (_Role-Based Access Control_), dan pipeline validasi request Joi yang mematuhi standar wire contract monorepo.

### Scope

**In-Scope:**

- Endpoint login, logout, profil sesi aktif, dan manajemen akun staf internal (`/api/v1/auth/*`).
- Middleware autentikasi verifikasi token/session dan otorisasi RBAC peran (`ADMIN`, `STAFF`).
- Middleware validasi request body, query, dan params menggunakan Joi dengan standard error RFC 9457 `422 Unprocessable Content`.
- Middleware penanganan error global (RFC 9457 `application/problem+json`), korelasi `X-Request-Id`, dan envelope seragam `{ data, meta }`.
- Integrasi dokumentasi OpenAPI 3.1.0 di `/api/openapi` dan Scalar di `/docs` (fail-closed produksi `DOCS_ENABLED`).

**Out-of-Scope:**

- Registrasi mandiri publik untuk pelanggan umum (akun staf dibuat secara internal oleh Admin).
- Fitur single sign-on (SSO) OAuth pihak ketiga (Google/Facebook Login).

### Business Rules

- Pengguna dengan peran `STAFF` dilarang mengakses modul keuangan sensitif (`/api/v1/finance/*`), analitik eksekutif, dan pembuatan user.
- Password pengguna wajib di-hash menggunakan algoritma aman (`bcrypt` atau `argon2`) dengan _salt rounds_ memadai sebelum disimpan di DB.
- Token autentikasi yang kedaluwarsa atau tidak valid harus menghasilkan HTTP `401 Unauthorized` dengan format RFC 9457.
- Akses oleh pengguna tanpa role yang mencukupi menghasilkan HTTP `403 Forbidden` RFC 9457.

### API Contract

#### Daftar Endpoint

| Method | Path                  | Fungsi                                                    | Autentikasi / Role            |
| :----- | :-------------------- | :-------------------------------------------------------- | :---------------------------- |
| `POST` | `/api/v1/auth/login`  | Autentikasi kredensial pengguna dan penerbitan sesi/token | Publik                        |
| `POST` | `/api/v1/auth/logout` | Invalidasi sesi / token pengguna aktif                    | Autentikasi: `ADMIN`, `STAFF` |
| `GET`  | `/api/v1/auth/me`     | Ambil profil pengguna dan hak akses aktif saat ini        | Autentikasi: `ADMIN`, `STAFF` |
| `POST` | `/api/v1/auth/users`  | Buat akun staf operasional internal baru                  | Autentikasi: `ADMIN`          |
| `GET`  | `/api/v1/auth/users`  | Daftar akun pengguna internal terdaftar (dengan paginasi) | Autentikasi: `ADMIN`          |

#### Format Wire Contract Sukses

- `POST /api/v1/auth/login`
  - Request:
    ```json
    {
      "username": "admin_catering",
      "password": "securepassword123"
    }
    ```
  - Response `200 OK`:
    ```json
    {
      "data": {
        "token": "token_auth_sample_placeholder",
        "user": {
          "id": "usr_01",
          "username": "admin_catering",
          "name": "Pengelola Katering",
          "role": "ADMIN"
        }
      },
      "meta": {
        "requestId": "0192f0c8-7b3a-7000-8000-000000000001"
      }
    }
    ```

- `GET /api/v1/auth/users?page=1&limit=10`
  - Response `200 OK`:
    ```json
    {
      "data": [
        {
          "id": "usr_02",
          "username": "staf_dapur_01",
          "name": "Staf Dapur Utama",
          "role": "STAFF",
          "createdAt": "2026-11-23T10:00:00.000Z"
        }
      ],
      "meta": {
        "requestId": "0192f0c8-7b3a-7000-8000-000000000002",
        "pagination": {
          "page": 1,
          "limit": 10,
          "total": 1,
          "totalPages": 1
        }
      }
    }
    ```

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Autentikasi berhasil atau pengambilan data profil sukses.
- `201 Created`: Pembuatan user baru berhasil.
- `400 Bad Request`: Payload JSON salah bentuk.
- `401 Unauthorized`: Kredensial tidak valid atau token kedaluwarsa.
- `403 Forbidden`: Role tidak memiliki hak akses (misal: `STAFF` memanggil rute admin).
- `404 Not Found`: Pengguna tidak ditemukan.
- `409 Conflict`: Username staf sudah terdaftar sebelumnya.
- `422 Unprocessable Content`: Validasi skema Joi gagal.
- `500 Internal Server Error`: Kesalahan server internal.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Validasi payload request gagal.",
  "instance": "/api/v1/auth/login",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000001",
  "errors": [
    {
      "path": "password",
      "code": "any.required",
      "message": "Password wajib diisi"
    }
  ]
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam spesifikasi OpenAPI 3.1.0 di `GET /api/openapi` dan disajikan via Scalar UI di `GET /docs` (fail-closed pada lingkungan produksi lewat konfigurasi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 5 endpoint (`/api/v1/auth/login`, `/logout`, `/me`, `POST /users`, `GET /users`) terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Endpoint `/api/v1/auth/login` sukses menerbitkan token untuk kredensial valid dan menolak kredensial salah dengan HTTP 401 RFC 9457.
- [ ] Middleware RBAC menolak peran `STAFF` saat memanggil resource admin dengan HTTP `403 Forbidden`.
- [ ] Validasi skema Joi menolak payload tidak lengkap atau salah tipe dengan HTTP `422` RFC 9457 tanpa membocorkan nilai input rahasia.
- [ ] Header response selalu menyertakan `X-Request-Id` dan `Content-Type: application/json` atau `application/problem+json`.
- [ ] Dokumentasi OpenAPI 3.1.0 teruji dapat dibuka pada Scalar UI `/docs`.

### Technical Notes

- Durasi masa aktif session token disepakati bersama `[Perlu Konfirmasi Tim]`.
- Mekanisme transport sesi (`HttpOnly cookie` lewat BFF vs `Authorization: Bearer`): `[Perlu Konfirmasi Tim]`.
- Standar penanganan error dan sanitasi log tidak membocorkan informasi kredensial di console server.

### DoD

- [ ] Seluruh unit test dan route test autentikasi di `apps/api` lulus di Vitest dengan coverage >= 80%.
- [ ] Scalar API Reference pada `/docs` menampilkan dokumentasi endpoint `/api/v1/auth` sesuai spesifikasi OpenAPI 3.1.0.
- [ ] Prettier dan ESLint lolos tanpa kesalahan.

### Dependencies

- Prasyarat: `FS-02` (Skema Prisma User).
- Terkait: Memproteksi seluruh endpoint di `FS-04`, `FS-05`, `FS-06`, `FS-07`, `FS-08`.

---

## [FS-04] Modul Katalog Menu, Resep & Kalkulator Bahan Otomatis

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`
- **Priority:** `P1-mvp`
- **Milestone:** `M2 (28 Nov–4 Des 2026)`
- **Target Path:** `apps/api/src/modules/menus`, `apps/web`

### Context

Masalah operasional terbesar Catering Si Kembar adalah lamanya waktu menghitung kebutuhan total bahan mentah secara manual saat menerima pesanan dalam jumlah besar (misal: 100 nasi box). Staf harus menghitung satu per satu kebutuhan beras, ayam, telur, minyak goreng, dan bumbu dapur. Modul ini menyediakan katalog menu baku, formulasi resep standar per porsi, dan kalkulator agregasi bahan baku otomatis yang langsung menghitung kebutuhan belanja ketika porsi diinput.

### Scope

**In-Scope:**

- Manajemen CRUD katalog menu dan daftar harga (`/api/v1/menus/*`).
- Manajemen formulasi resep per menu: daftar bahan dan takaran per 1 porsi piring/box.
- Fitur kalkulator bahan otomatis: menerima input array menu dan jumlah porsi, lalu mengembalikan daftar total agregat bahan baku per satuan (gram, kg, butir, liter).
- Antarmuka web di `apps/web` untuk katalog menu, detail resep, dan simulasi kalkulasi belanja bahan.
- Integrasi dokumentasi OpenAPI 3.1.0 dan Scalar di `/docs`.

**Out-of-Scope:**

- Sistem inventaris stok gudang real-time atau pencatatan mutasi keluar-masuk stok harian (fokus MVP adalah kalkulator agregasi bahan baku otomatis berdasarkan resep standar).
- Rekomendasi vendor supplier belanja pasar (hanya menyajikan kalkulasi kuantitas).

### Business Rules

- Menu yang belum memiliki data resep tidak dapat dihitung bahannya dan sistem harus memberikan pesan error terstruktur `Menu belum memiliki formulasi resep`.
- Agregasi bahan dengan nama dan satuan yang sama harus dijumlahkan secara otomatis pada level pesanan multi-menu.
- Perhitungan kuantitas bahan selalu dibulatkan ke atas (_ceiling_) pada satuan terkecil belanja yang wajar.

### API Contract

#### Daftar Endpoint

| Method  | Path                                  | Fungsi                                                                       | Autentikasi / Role            |
| :------ | :------------------------------------ | :--------------------------------------------------------------------------- | :---------------------------- |
| `GET`   | `/api/v1/menus`                       | Ambil daftar katalog menu (filter pencarian & paginasi)                      | Autentikasi: `ADMIN`, `STAFF` |
| `GET`   | `/api/v1/menus/:id`                   | Ambil rincian detail menu beserta daftar resep bahan                         | Autentikasi: `ADMIN`, `STAFF` |
| `POST`  | `/api/v1/menus`                       | Tambah menu baru ke katalog katering                                         | Autentikasi: `ADMIN`          |
| `PATCH` | `/api/v1/menus/:id`                   | Perbarui informasi nama, harga, atau status aktif menu                       | Autentikasi: `ADMIN`          |
| `PUT`   | `/api/v1/menus/:id/recipe`            | Tetapkan / perbarui formula resep dan takaran per 1 porsi                    | Autentikasi: `ADMIN`          |
| `POST`  | `/api/v1/menus/calculate-ingredients` | Hitung agregasi kebutuhan total belanja bahan baku untuk 1..N menu dan porsi | Autentikasi: `ADMIN`, `STAFF` |

#### Format Wire Contract Sukses

- `POST /api/v1/menus/calculate-ingredients`
  - Request:
    ```json
    {
      "items": [
        { "menuId": "menu_01", "portion": 100 },
        { "menuId": "menu_02", "portion": 50 }
      ]
    }
    ```
  - Response `200 OK`:
    ```json
    {
      "data": {
        "ingredients": [
          { "ingredientId": "ing_01", "name": "Beras Putih", "totalAmount": 15000, "unit": "gram" },
          { "ingredientId": "ing_02", "name": "Daging Ayam", "totalAmount": 12.5, "unit": "kg" }
        ],
        "summary": { "totalPortions": 150, "uniqueIngredientsCount": 2 }
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000002" }
    }
    ```

- `GET /api/v1/menus?page=1&limit=10&search=ayam`
  - Response `200 OK`:
    ```json
    {
      "data": [
        {
          "id": "menu_01",
          "name": "Nasi Box Ayam Lengkuas",
          "price": 25000,
          "category": "NASI_BOX",
          "isActive": true
        }
      ],
      "meta": {
        "requestId": "0192f0c8-7b3a-7000-8000-000000000003",
        "pagination": {
          "page": 1,
          "limit": 10,
          "total": 1,
          "totalPages": 1
        }
      }
    }
    ```

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Pengambilan data atau kalkulasi sukses.
- `201 Created`: Menu baru berhasil dibuat.
- `400 Bad Request`: Format JSON tidak valid.
- `401 Unauthorized`: Kredensial tidak valid atau tidak disertakan.
- `403 Forbidden`: Staf operasional mencoba menambah atau mengubah resep menu.
- `404 Not Found`: Menu atau bahan baku tidak ditemukan.
- `422 Unprocessable Content`: Validasi skema Joi gagal (porsi <= 0, menuId kosong).
- `500 Internal Server Error`: Kesalahan server internal.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Validasi porsi gagal.",
  "instance": "/api/v1/menus/calculate-ingredients",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000002",
  "errors": [
    {
      "path": "items.0.portion",
      "code": "number.min",
      "message": "Porsi minimal adalah 1"
    }
  ]
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam skema OpenAPI 3.1.0 di `/api/openapi` dan disajikan via Scalar UI di `/docs` (fail-closed produksi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 6 endpoint menu terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Pengujian kalkulasi bahan untuk skenario 10, 50, dan 100 porsi menghasilkan angka yang identik dengan formula resep standar.
- [ ] Input porsi bernilai 0, negatif, atau desimal tidak valid ditolak oleh validasi Joi dengan HTTP 422 RFC 9457.
- [ ] Akses modifikasi menu oleh peran `STAFF` ditolak dengan HTTP 403 Forbidden.
- [ ] Layar kalkulator di web menampilkan daftar belanja bahan yang mudah dibaca staf dapur di ponsel tanpa overflow.
- [ ] Waktu respon kalkulasi bahan pada backend Express tercatat di bawah 100ms untuk 10 menu kombinasi.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tampil di Scalar `/docs`.

### Technical Notes

- Standar gramatur bumbu dapur dan bahan baku utama nasi box `[Menunggu Konfirmasi PIC]`.
- Nama dan satuan baku bahan pangan disinkronkan dengan kamus data Data Science `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Endpoint `/api/v1/menus/*` dan `/calculate-ingredients` terimplementasi dan lolos test suite Vitest.
- [ ] Halaman kalkulator di `apps/web` terhubung ke endpoint melalui Axios BFF.
- [ ] Dokumentasi endpoint tersedia di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- Prasyarat: `FS-02` (Skema Prisma Menu/Recipe), `FS-03` (Auth/Joi).
- Terkait: Dipanggil oleh modul pesanan `FS-05` dan simulasi demonstrasi 100 porsi `FS-09`.

---

## [FS-05] Modul Pesanan & Dasbor Jadwal Produksi

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`
- **Priority:** `P1-mvp`
- **Milestone:** `M2 (28 Nov–4 Des 2026)`
- **Target Path:** `apps/api/src/modules/orders`, `apps/web`

### Context

Saat ini jadwal pesanan Catering Si Kembar dicatat di Google Spreadsheet terpisah, sehingga staf dapur seringkali tidak mengetahui perubahan jadwal acara, menu yang harus dimasak, atau pesanan yang harus disiapkan untuk hari esok. Modul ini menyediakan alur input pesanan terstruktur, pelacakan status pesanan, serta antarmuka Dasbor Jadwal Produksi yang bersih dan mudah dibaca oleh staf operasional senior di desktop maupun layar ponsel.

### Scope

**In-Scope:**

- Endpoint CRUD pesanan katering (`/api/v1/orders/*`): nama pemesan, nomor kontak, tanggal & jam acara, alamat pengiriman, daftar menu & porsi, catatan khusus.
- Kalkulasi total tagihan otomatis berdasarkan harga menu yang berlaku.
- Pengaturan status alur hidup pesanan: `DRAFT` -> `CONFIRMED` -> `IN_PREPARATION` -> `READY` -> `DELIVERED` (atau `CANCELLED`).
- Antarmuka Dasbor Jadwal Produksi berbasis kalender dan daftar urutan waktu (harian, mingguan) di `apps/web`.
- Integrasi dokumentasi OpenAPI 3.1.0 dan Scalar di `/docs`.

**Out-of-Scope:**

- Pelacakan armada kurir pengiriman berbasis GPS real-time.
- Pemesanan mandiri oleh pelanggan publik via website (_customer self-service portal_).

### Business Rules

- Tanggal acara pesanan tidak boleh berada di masa lalu (_past date_).
- Pesanan hanya dapat berpindah ke status `CONFIRMED` apabila status pembayaran uang muka (DP) sudah tercatat valid atau disetujui staf berwenang.
- Nomor telepon pemesan divalidasi dengan format nomor Indonesia yang valid (diawali `08` atau `+62`).
- Status pesanan yang sudah `DELIVERED` atau `CANCELLED` tidak dapat diubah kembali.

### API Contract

#### Daftar Endpoint

| Method  | Path                        | Fungsi                                                                                   | Autentikasi / Role            |
| :------ | :-------------------------- | :--------------------------------------------------------------------------------------- | :---------------------------- |
| `GET`   | `/api/v1/orders`            | Ambil daftar pesanan katering (filter tanggal acara, status, nama pemesan, dan paginasi) | Autentikasi: `ADMIN`, `STAFF` |
| `GET`   | `/api/v1/orders/schedule`   | Tampilan jadwal produksi harian dan mingguan terurut tanggal acara terdekat              | Autentikasi: `ADMIN`, `STAFF` |
| `GET`   | `/api/v1/orders/:id`        | Rincian lengkap pesanan beserta ringkasan kebutuhan bahan dan status tagihan             | Autentikasi: `ADMIN`, `STAFF` |
| `POST`  | `/api/v1/orders`            | Buat pesanan baru (otomatis kalkulasi total harga dan penerbitan invoice)                | Autentikasi: `ADMIN`, `STAFF` |
| `PATCH` | `/api/v1/orders/:id`        | Ubah rincian pesanan selama belum berstatus DELIVERED atau CANCELLED                     | Autentikasi: `ADMIN`, `STAFF` |
| `PATCH` | `/api/v1/orders/:id/status` | Transisi status alur hidup pesanan sesuai aturan bisnis                                  | Autentikasi: `ADMIN`, `STAFF` |

#### Format Wire Contract Sukses

- `POST /api/v1/orders`
  - Request:
    ```json
    {
      "customerName": "Ibu Rahmawati",
      "customerPhone": "081234567890",
      "eventDate": "2026-12-15T10:00:00.000Z",
      "deliveryAddress": "Jl. Melati No. 12, Jakarta",
      "notes": "Nasi box jangan pedas",
      "items": [{ "menuId": "menu_01", "portion": 100, "unitPrice": 25000 }]
    }
    ```
  - Response `201 Created`:
    ```json
    {
      "data": {
        "id": "ord_01",
        "orderNumber": "ORD-202612-0001",
        "totalAmount": 2500000,
        "status": "DRAFT",
        "eventDate": "2026-12-15T10:00:00.000Z"
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000003" }
    }
    ```

- `GET /api/v1/orders?page=1&limit=10&status=CONFIRMED`
  - Response `200 OK`:
    ```json
    {
      "data": [
        {
          "id": "ord_01",
          "orderNumber": "ORD-202612-0001",
          "customerName": "Ibu Rahmawati",
          "totalAmount": 2500000,
          "status": "CONFIRMED",
          "eventDate": "2026-12-15T10:00:00.000Z"
        }
      ],
      "meta": {
        "requestId": "0192f0c8-7b3a-7000-8000-000000000004",
        "pagination": {
          "page": 1,
          "limit": 10,
          "total": 1,
          "totalPages": 1
        }
      }
    }
    ```

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Pengambilan data pesanan berhasil.
- `201 Created`: Pesanan baru berhasil dibuat.
- `400 Bad Request`: Format JSON tidak valid.
- `401 Unauthorized`: Kredensial tidak valid.
- `403 Forbidden`: Hak akses tidak mencukupi.
- `404 Not Found`: Pesanan tidak ditemukan.
- `409 Conflict`: Transisi status tidak sah (misal: pesanan `DELIVERED` diubah kembali).
- `422 Unprocessable Content`: Validasi skema Joi gagal (tanggal lampau, nomor HP tidak valid).
- `500 Internal Server Error`: Kesalahan server internal.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Conflict",
  "status": 409,
  "detail": "Pesanan yang sudah berstatus DELIVERED tidak dapat diubah.",
  "instance": "/api/v1/orders/ord_01/status",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000003"
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam skema OpenAPI 3.1.0 di `/api/openapi` dan disajikan via Scalar UI di `/docs` (fail-closed produksi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 6 endpoint pesanan terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Pengujian simpan pesanan 100 nasi box berhasil dan mengembalikan detail pesanan dengan total kalkulasi harga akurat.
- [ ] Input data pesanan tanpa nama pemesan, porsi 0, atau tanggal kosong ditolak oleh middleware Joi dengan HTTP 422 RFC 9457.
- [ ] Percobaan transisi status tidak sah ditolak dengan HTTP 409 Conflict RFC 9457.
- [ ] Dasbor jadwal di antarmuka web menampilkan pesanan yang diurutkan berdasarkan tanggal acara terdekat.
- [ ] Tampilan dasbor jadwal terbaca jelas di layar mobile (`390px`) tanpa elemen yang terpotong.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tampil di Scalar `/docs`.

### Technical Notes

- Format penomoran pesanan unik (misal: `ORD-YYYYMM-XXXX`) `[Perlu Konfirmasi Tim]`.
- Batas maksimal porsi pesanan harian katering `[Menunggu Konfirmasi PIC]`.

### DoD

- [ ] Seluruh endpoint pesanan di `apps/api/src/modules/orders` memiliki test acceptance di Vitest.
- [ ] Tampilan dasbor jadwal pada `apps/web` memiliki filter tanggal dan status yang berjalan tanpa error console.
- [ ] Prettier dan ESLint lolos 100%.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tersedia di Scalar `/docs`.

### Dependencies

- Prasyarat: `FS-02` (Skema Order), `FS-03` (Auth/RBAC), `FS-04` (Katalog Menu).
- Terkait: Menjadi dasar bagi `FS-06` (Invoice Keuangan) dan `FS-09` (Pengingat Pesanan).

---

## [FS-06] Modul Keuangan: Invoice Digital, DP 60%, Pelunasan & Export PDF

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`
- **Priority:** `P1-mvp`
- **Milestone:** `M3 (5–11 Des 2026)`
- **Target Path:** `apps/api/src/modules/finance`, `apps/web`

### Context

Sebelumnya pembuatan invoice di Catering Si Kembar memakan waktu beberapa jam hingga keesokan harinya karena pengelola harus menghitung rincian dan menulis nota di buku secara manual. Masalah ini menyebabkan kepastian pesanan terlambat. Modul keuangan ini secara instan menerbitkan invoice digital setelah pesanan dibuat, memvalidasi pencatatan uang muka (DP minimal 60%), mengelola pelunasan sisa tagihan, serta menyediakan fitur unduh/cetak invoice dalam format PDF profesional.

### Scope

**In-Scope:**

- Endpoint penerbitan invoice digital otomatis untuk setiap pesanan (`/api/v1/finance/invoices/*`).
- Pencatatan pembayaran: Down Payment (DP minimal 60% `[Menunggu Konfirmasi PIC]`) dan Pelunasan sisa tagihan (`/api/v1/finance/payments`).
- Logika pembaruan status invoice: `UNPAID` -> `PARTIALLY_PAID` -> `PAID`.
- Endpoint & fitur pembuatan berkas PDF invoice resmi untuk dicetak atau dibagikan via WhatsApp.
- Antarmuka web di `apps/web` untuk daftar tagihan, form pencatatan pembayaran tunai/transfer, dan tombol unduh PDF.
- Integrasi dokumentasi OpenAPI 3.1.0 dan Scalar di `/docs`.

**Out-of-Scope:**

- Payment gateway otomatis (seperti Midtrans/Xendit) dengan auto-debit atau virtual account otomatis.
- Rekonsiliasi mutasi rekening bank secara otomatis (_bank scraping_).

### Business Rules

- Uang Muka (DP) yang dicatat divalidasi minimal sebesar 60% dari total tagihan pesanan `[Menunggu Konfirmasi PIC]`. Jika nominal DP di bawah batas minimum, sistem meminta konfirmasi khusus atau menolak sesuai kebijakan.
- Nominal pelunasan tidak boleh melebihi sisa tagihan (_remaining balance_).
- Invoice yang sudah berstatus `PAID` dikunci dan tidak dapat menerima penambahan pembayaran baru.
- Modul keuangan hanya boleh diakses oleh pengguna dengan role `ADMIN`.

### API Contract

#### Daftar Endpoint

| Method | Path                               | Fungsi                                                                                  | Autentikasi / Role   |
| :----- | :--------------------------------- | :-------------------------------------------------------------------------------------- | :------------------- |
| `GET`  | `/api/v1/finance/invoices`         | Ambil daftar seluruh invoice (filter PaymentStatus, rentang tanggal, dan paginasi)      | Autentikasi: `ADMIN` |
| `GET`  | `/api/v1/finance/invoices/:id`     | Rincian invoice, riwayat catatan pembayaran, total DP, dan sisa tagihan                 | Autentikasi: `ADMIN` |
| `POST` | `/api/v1/finance/invoices`         | Terbitkan invoice digital untuk pesanan terdaftar (idempoten 1:1 per order)             | Autentikasi: `ADMIN` |
| `POST` | `/api/v1/finance/payments`         | Catat transaksi pembayaran: DP (minimal 60% `[Menunggu Konfirmasi PIC]`) atau pelunasan | Autentikasi: `ADMIN` |
| `GET`  | `/api/v1/finance/invoices/:id/pdf` | Unduh / cetak invoice resmi katering dalam format biner stream application/pdf          | Autentikasi: `ADMIN` |

#### Format Wire Contract Sukses

- `POST /api/v1/finance/payments`
  - Request:
    ```json
    {
      "invoiceId": "inv_01",
      "amount": 1500000,
      "paymentType": "DOWN_PAYMENT",
      "paymentMethod": "BANK_TRANSFER",
      "paidAt": "2026-11-25T08:30:00.000Z",
      "referenceNote": "Transfer via BCA an Rahmawati"
    }
    ```
  - Response `201 Created`:
    ```json
    {
      "data": {
        "paymentId": "pay_01",
        "invoiceId": "inv_01",
        "amountPaid": 1500000,
        "remainingBalance": 1000000,
        "invoiceStatus": "PARTIALLY_PAID"
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000004" }
    }
    ```

- `GET /api/v1/finance/invoices?page=1&limit=10&status=UNPAID`
  - Response `200 OK`:
    ```json
    {
      "data": [
        {
          "id": "inv_01",
          "orderId": "ord_01",
          "invoiceNumber": "INV-202612-0001",
          "totalAmount": 2500000,
          "paidAmount": 0,
          "status": "UNPAID"
        }
      ],
      "meta": {
        "requestId": "0192f0c8-7b3a-7000-8000-000000000005",
        "pagination": {
          "page": 1,
          "limit": 10,
          "total": 1,
          "totalPages": 1
        }
      }
    }
    ```

- `GET /api/v1/finance/invoices/:id/pdf`
  - Header Request: `Accept: application/pdf`
  - Response `200 OK`: Binary Stream PDF dengan header `Content-Type: application/pdf` dan `Content-Disposition: inline; filename="invoice-INV-202612-0001.pdf"`.

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Data invoice berhasil diambil.
- `201 Created`: Pembayaran berhasil dicatat.
- `400 Bad Request`: Payload JSON salah bentuk.
- `401 Unauthorized`: Kredensial tidak valid.
- `403 Forbidden`: Staf non-admin memanggil endpoint keuangan.
- `404 Not Found`: Invoice atau pesanan tidak ditemukan.
- `409 Conflict`: Pembayaran dilakukan pada invoice yang sudah berstatus `PAID`.
- `422 Unprocessable Content`: Nominal pembayaran melampaui sisa tagihan atau DP di bawah 60%.
- `500 Internal Server Error`: Kesalahan server internal saat pembuatan PDF atau database.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Nominal pembayaran uang muka (DP) minimal 60% dari total tagihan.",
  "instance": "/api/v1/finance/payments",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000004",
  "errors": [
    {
      "path": "amount",
      "code": "finance.dp_insufficient",
      "message": "Nominal DP Rp 1.000.000 kurang dari batas minimal 60% (Rp 1.500.000)"
    }
  ]
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam skema OpenAPI 3.1.0 di `/api/openapi` dan disajikan via Scalar UI di `/docs` (fail-closed produksi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 5 endpoint keuangan terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Penerbitan invoice terjadi otomatis dalam waktu kurang dari 1 detik setelah pesanan disimpan.
- [ ] Pencatatan DP 60% berhasil mengubah status invoice menjadi `PARTIALLY_PAID` dan menghitung sisa tagihan dengan presisi tanpa kesalahan pembulatan desimal.
- [ ] Pencatatan pelunasan dengan sisa tagihan tepat mengubah status invoice menjadi `PAID`.
- [ ] Pengujian unduh file PDF menghasilkan dokumen rapi yang memuat logo katering, rincian menu, porsi, nominal DP, sisa tagihan, dan rekening pembayaran.
- [ ] Akses modul keuangan oleh pengguna peran `STAFF` ditolak dengan HTTP 403 Forbidden RFC 9457.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tampil di Scalar `/docs`.

### Technical Notes

- Aturan toleransi DP di bawah 60% untuk pelanggan tetap `[Menunggu Konfirmasi PIC]`.
- Pustaka generator PDF di server menggunakan engine ringan non-headless browser (`pdfkit` atau generator HTML template ringan) agar hemat resource VPS `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Modul `apps/api/src/modules/finance` teruji penuh di Vitest untuk berbagai variasi pembayaran.
- [ ] Layar invoice di `apps/web` dapat diakses, menampilkan status akurat, dan tombol cetak/unduh PDF berfungsi tanpa crash.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar documentation `/docs`.

### Dependencies

- Prasyarat: `FS-03` (RBAC Keuangan), `FS-05` (Pesanan Terkonfirmasi).
- Terkait: Menjadi dasar bagi reminder pembayaran di `FS-09`.

---

## [FS-07] Modul Chat AI: Proxy Backend, Riwayat Inferensi DB & UI Chat

- **Labels:** `area:fullstack`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest`
- **Milestone:** `M3 (5–11 Des 2026)`
- **Target Path:** `apps/api/src/modules/chat`, `apps/web`

### Context

Untuk membantu staf dan pengelola menanyakan informasi katering secara cepat (seperti rincian menu, takaran resep, atau status pesanan tertentu), dibangun asisten AI chatbot. Sesuai guardrail arsitektur, frontend web tidak boleh memanggil `apps/ai-service` atau LLM secara langsung. Backend Express bertindak sebagai proxy aman yang memvalidasi hak akses pengguna, meneruskan pertanyaan ke FastAPI `POST /api/v1/rag/chat`, mencatat riwayat tanya-jawab (_inference history_) ke database PostgreSQL untuk audit, serta menyajikan UI chat interaktif di browser.

### Scope

**In-Scope:**

- Endpoint Express `/api/v1/chat/messages` (menerima pesan pengguna, meneruskan ke FastAPI `:8001/api/v1/rag/chat` membawa `user_role` sesi server, dan mengembalikan respons).
- Endpoint riwayat sesi chat `/api/v1/chat/sessions` dan pesan `/api/v1/chat/sessions/:sessionId/messages`.
- Penyimpanan riwayat inferensi chat di tabel `ChatLog` (id pengguna, pesan masuk, respons AI, sumber sitasi referensi, waktu latensi inferensi).
- Antarmuka chat widget di `apps/web`: jendela obrolan mengambang atau halaman penuh dengan _bubble chat_, indikator _typing_, dan tampilan sumber sitasi.
- Penanganan graceful saat layanan AI timeout atau kuota habis dengan pesan ramah pengguna.
- Integrasi dokumentasi OpenAPI 3.1.0 dan Scalar di `/docs`.

**Out-of-Scope:**

- Voice chat atau pengenalan suara (_speech-to-text_).
- Pemanggilan LLM komersial langsung dari browser tanpa melalui proxy backend.

### Business Rules

- Pertanyaan staf hanya dijawab menggunakan dokumen dan data katering yang sah (grounded).
- Informasi rahasia keuangan (seperti total omzet tahunan atau gaji karyawan) tidak boleh dijawab kepada staf dapur biasa.
- Jika layanan AI service tidak merespon dalam batas waktu (timeout 10 detik `[Perlu Konfirmasi Tim]`), backend mengembalikan pesan fallback yang jelas dengan HTTP 503 RFC 9457 tanpa menjatuhkan aplikasi web.

### API Contract

#### Daftar Endpoint

| Method | Path                                        | Fungsi                                                                                                                  | Autentikasi / Role            |
| :----- | :------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------- | :---------------------------- |
| `POST` | `/api/v1/chat/messages`                     | Kirim pertanyaan pengguna, proxy ke FastAPI POST /api/v1/rag/chat, simpan riwayat di ChatLog, kembalikan reply & sitasi | Autentikasi: `ADMIN`, `STAFF` |
| `GET`  | `/api/v1/chat/sessions`                     | Ambil daftar riwayat sesi percakapan milik pengguna login (dengan paginasi)                                             | Autentikasi: `ADMIN`, `STAFF` |
| `GET`  | `/api/v1/chat/sessions/:sessionId/messages` | Ambil riwayat pesan dan sitasi sumber dalam sesi tertentu                                                               | Autentikasi: `ADMIN`, `STAFF` |

#### Format Wire Contract Sukses

- `POST /api/v1/chat/messages`
  - Request:
    ```json
    {
      "sessionId": "ses_01",
      "message": "Berapa porsi minimal pemesanan nasi box ayam lengkuas?"
    }
    ```
  - Response `200 OK`:
    ```json
    {
      "data": {
        "sessionId": "ses_01",
        "reply": "Pemesanan minimal nasi box ayam lengkuas adalah 20 porsi dengan konfirmasi H-2 acara.",
        "citations": [{ "source": "SOP_Pemesanan_2026.pdf", "section": "Ketentuan Minimal Order" }],
        "latencyMs": 1420
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000005" }
    }
    ```

- `GET /api/v1/chat/sessions?page=1&limit=10`
  - Response `200 OK`:
    ```json
    {
      "data": [
        {
          "sessionId": "ses_01",
          "title": "Pemesanan Nasi Box Ayam Lengkuas",
          "lastMessageAt": "2026-11-23T14:20:00.000Z"
        }
      ],
      "meta": {
        "requestId": "0192f0c8-7b3a-7000-8000-000000000006",
        "pagination": {
          "page": 1,
          "limit": 10,
          "total": 1,
          "totalPages": 1
        }
      }
    }
    ```

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Respon percakapan berhasil diterima.
- `201 Created`: Sesi percakapan baru berhasil dibuat.
- `400 Bad Request`: Payload JSON tidak valid.
- `401 Unauthorized`: Kredensial tidak valid.
- `403 Forbidden`: Hak akses tidak mencukupi.
- `404 Not Found`: Sesi percakapan tidak ditemukan.
- `422 Unprocessable Content`: Validasi pesan kosong atau format salah.
- `500 Internal Server Error`: Kesalahan server internal backend.
- `503 Service Unavailable`: Layanan FastAPI atau LLM tidak merespon / timeout.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Service Unavailable",
  "status": 503,
  "detail": "Layanan asisten cerdas sedang tidak tersedia atau mengalami batas waktu respon.",
  "instance": "/api/v1/chat/messages",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000005"
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam skema OpenAPI 3.1.0 di `/api/openapi` dan disajikan via Scalar UI di `/docs` (fail-closed produksi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 3 endpoint chat proxy terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Pengiriman pesan melalui UI web berhasil diteruskan oleh Express ke FastAPI `POST /api/v1/rag/chat` dan menampilkan balasan asisten beserta sitasi sumbernya.
- [ ] Setiap percakapan tersimpan dengan benar di tabel PostgreSQL `ChatLog`.
- [ ] Simulasi kegagalan AI service (FastAPI dimatikan/timeout) ditangani dengan respons error 503 bersahabat RFC 9457.
- [ ] UI chat responsif dan nyaman digunakan di ponsel tanpa menghalangi navigasi dasar.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tampil di Scalar `/docs`.

### Technical Notes

- Format payload sitasi dokumen disepakati bersama tim AI Engineering `[Perlu Konfirmasi Tim]`.
- Mekanisme batas laju (_rate limiting_) obrolan per pengguna untuk mencegah kehabisan kuota API LLM `[Perlu Konfirmasi Tim]`.
- SLA batas waktu respon timeout default 10 detik `[Perlu Konfirmasi Tim]`.

### DoD

- [ ] Endpoint `/api/v1/chat/messages` memiliki unit test dan mock test inter-service di Vitest.
- [ ] Komponen UI Chat di `apps/web` dapat digunakan secara interaktif tanpa console warning.
- [ ] Linter dan format Prettier lulus 100%.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- Prasyarat: `FS-03` (Autentikasi Pengguna), `AI-01` (FastAPI Serving), `AI-05` (Pipeline Agentic RAG).
- Terkait: Menjadi bagian dari demonstrasi interaktif MVP.

---

## [FS-08] Modul Dasbor Analitik DS: KPI, Filter, Upload Data & Tampilan Prediksi/Insight

- **Labels:** `area:fullstack`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest`
- **Milestone:** `M3 (5–11 Des 2026)`
- **Target Path:** `apps/api/src/modules/analytics`, `apps/web`

### Context

Pengelola katering memerlukan gambaran performa bisnis yang mudah dipahami, meliputi tren penjualan menu terlaris, pola hari sibuk, estimasi kebutuhan belanja masa depan dari model peramalan (_forecasting_), serta ringkasan evaluasi umpan balik pelanggan dari model analisis sentimen. Modul ini menyajikan Dasbor Analitik interaktif di antarmuka web yang terhubung dengan modul analitik Express dan model data hasil kerja tim Data Science.

### Scope

**In-Scope:**

- Endpoint agregasi KPI bisnis (`/api/v1/analytics/overview`): total pesanan, total porsi terjual, menu terfavorit, rasio pelunasan tagihan.
- Endpoint unggah berkas pembaruan data (`/api/v1/analytics/upload`) untuk menerima file CSV/Excel terstruktur dengan validasi skema dan penandaan `isSynthetic`.
- Endpoint pemicu narasi AI Business Insight via FastAPI `POST /api/v1/insight/generate` (`/api/v1/analytics/insights`).
- Endpoint unduh laporan analitik dalam format PDF (`/api/v1/analytics/report/pdf`).
- Halaman antarmuka Dasbor Analitik di `apps/web` dengan visualisasi grafik (grafik garis tren pesanan, grafik batang menu terlaris, donut chart sentimen pelanggan) serta tombol unggah data.
- Integrasi dokumentasi OpenAPI 3.1.0 dan Scalar di `/docs`.

**Out-of-Scope:**

- Sistem Business Intelligence enterprise yang kompleks (seperti Tableau/PowerBI embed).
- Modifikasi langsung skema analitik oleh pengguna non-admin.

### Business Rules

- Dasbor analitik hanya dapat diakses oleh pengguna dengan peran `ADMIN` / Pengelola.
- Grafik harus menampilkan label yang jelas mengenai rentang tanggal dan indikator jika data yang ditampilkan merupakan hasil simulasi/prediksi atau berasal dari data `isSynthetic = true`.
- Berkas unggahan pembaruan data wajib divalidasi ekstensi (`.csv`/`.xlsx`), ukuran maksimum, dan kolom wajibnya; berkas berformat salah ditolak dengan HTTP `422` RFC 9457 tanpa merusak data eksisting.
- Data yang ditampilkan selalu mencerminkan status transaksi terkini dari database PostgreSQL.

### API Contract

#### Daftar Endpoint

| Method | Path                           | Fungsi                                                                                        | Autentikasi / Role   |
| :----- | :----------------------------- | :-------------------------------------------------------------------------------------------- | :------------------- |
| `GET`  | `/api/v1/analytics/overview`   | Ambil ringkasan KPI, tren periode, menu terlaris, sentimen (AI-03), dan forecasting (DS-05)   | Autentikasi: `ADMIN` |
| `POST` | `/api/v1/analytics/upload`     | Unggah berkas CSV/XLSX pembaruan data (multipart/form-data, validasi skema, flag isSynthetic) | Autentikasi: `ADMIN` |
| `POST` | `/api/v1/analytics/insights`   | Picu atau ambil narasi AI Business Insight via FastAPI POST /api/v1/insight/generate          | Autentikasi: `ADMIN` |
| `GET`  | `/api/v1/analytics/report/pdf` | Unduh laporan analitik dan insight bisnis resmi dalam format application/pdf                  | Autentikasi: `ADMIN` |

#### Format Wire Contract Sukses

- `GET /api/v1/analytics/overview?startDate=2026-11-01&endDate=2026-11-30`
  - Response `200 OK`:
    ```json
    {
      "data": {
        "kpis": {
          "totalOrders": 42,
          "totalPortions": 3850,
          "revenue": 96250000,
          "topMenu": "Nasi Box Ayam Lengkuas"
        },
        "trends": [
          { "date": "2026-11-01", "portions": 120 },
          { "date": "2026-11-02", "portions": 80 }
        ],
        "sentimentDistribution": { "positive": 88, "negative": 12 },
        "demandForecastNextWeek": [{ "date": "2026-12-01", "predictedPortions": 250 }]
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000006" }
    }
    ```

- `POST /api/v1/analytics/upload`
  - Request (`multipart/form-data`): field `file` (`.csv` atau `.xlsx`), opsional `isSynthetic` (`boolean`).
  - Response `200 OK`:
    ```json
    {
      "data": {
        "importedRows": 120,
        "skippedRows": 0,
        "isSynthetic": false
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000007" }
    }
    ```

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Data analitik berhasil diambil atau berkas berhasil diunggah.
- `201 Created`: Pembuatan laporan analitik sukses.
- `400 Bad Request`: Parameter query tanggal tidak valid.
- `401 Unauthorized`: Kredensial tidak valid.
- `403 Forbidden`: Staf operasional mencoba membuka modul analitik.
- `404 Not Found`: Data tidak ditemukan.
- `422 Unprocessable Content`: Format berkas tidak didukung atau kolom wajib hilang.
- `500 Internal Server Error`: Kesalahan server internal.
- `503 Service Unavailable`: Layanan AI Insight atau forecasting tidak merespon.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Forbidden",
  "status": 403,
  "detail": "Modul analitik hanya dapat diakses oleh peran ADMIN.",
  "instance": "/api/v1/analytics/overview",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000006"
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam skema OpenAPI 3.1.0 di `/api/openapi` dan disajikan via Scalar UI di `/docs` (fail-closed produksi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 4 endpoint analitik terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Pengelola berhasil melihat indikator KPI utama dan mengubah filter periode tanggal/status dengan grafik yang terbarui secara dinamis.
- [ ] Unggah berkas CSV/Excel valid berhasil memperbarui data analitik, sedangkan berkas berformat salah ditolak dengan pesan error jelas (HTTP 422 RFC 9457).
- [ ] Hasil inferensi peramalan dari Data Science (`DS-05`), ringkasan sentimen (`AI-03`), dan narasi AI Business Insight tampil secara terpadu di tab analitik.
- [ ] Tombol unduh laporan PDF memicu pengunduhan berkas ringkasan analitik resmi katering.
- [ ] Akses oleh pengguna dengan peran `STAFF` ditolak dengan HTTP 403 Forbidden RFC 9457.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tampil di Scalar `/docs`.

### Technical Notes

- Pustaka visualisasi grafik di web menggunakan library charting kompatibel React (misal: Recharts) `[Perlu Konfirmasi Tim]`.
- Penentuan metrik default kartu ringkasan KPI `[Menunggu Konfirmasi PIC]`.

### DoD

- [ ] Endpoint `/api/v1/analytics/*` lulus pengujian rute dan otorisasi di Vitest.
- [ ] Komponen dasbor di `apps/web` bebas dari kesalahan render dan responsif di desktop dan tablet.
- [ ] Scalar documentation pada `/docs` memuat kontrak analitik OpenAPI 3.1.0.

### Dependencies

- Prasyarat: `FS-05` (Data Pesanan), `FS-06` (Data Keuangan), `DS-05` (Forecasting Service), `AI-03` (Model Sentimen).
- Terkait: Memenuhi checklist Side Quest Full-Stack dan Data Science.

---

## [FS-09] Modul Pengingat (In-App + Email Worker), Panduan Pengguna, Ukur Waktu Proses & Uji E2E

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp`
- **Milestone:** `M4 (12–20 Des 2026)`
- **Target Path:** `apps/api/src/modules/reminders`, `apps/worker`, `apps/web`

### Context

Pada tahap akhir sebelum demonstrasi produk kepada pengelola katering, sistem memerlukan modul pengingat otomatis (pengingat pesanan H-1 acara, pengingat jatuh tempo pelunasan) yang dieksekusi secara periodik oleh worker. Selain itu, diperlukan panduan pengguna ringkas (_user manual_), pelaksanaan pengujian end-to-end menyeluruh (alur pesanan, perhitungan bahan, invoice, pembayaran), serta pencatatan pengukuran waktu proses sistem untuk dibandingkan dengan baseline manual mitra.

### Scope

**In-Scope:**

- Endpoint internal pengelolaan jadwal pengingat (`/api/v1/reminders/*`) dan pencatatan riwayat pengiriman notifikasi di `NotificationLog` untuk mencegah duplikasi pengiriman (_idempotency_).
- Integrasi notifikasi in-app pada antarmuka web (lonceng notifikasi dan daftar pengingat operasional).
- Penyiapan task worker Node.js di `apps/worker` untuk memeriksa jadwal pengingat dan memicu pengiriman email atau notifikasi sistem.
- Penyusunan dokumen Panduan Pengguna (_User Manual_) praktis untuk pengelola dan staf dapur katering.
- Pengujian menyeluruh alur utama end-to-end (simulasi skenario 100 nasi box) serta pencatatan stopwatch waktu proses (hitung bahan dan cetak invoice).
- Integrasi dokumentasi OpenAPI 3.1.0 dan Scalar di `/docs`.

**Out-of-Scope:**

- Integrasi SMS gateway berbayar.
- Penjadwalan pesan pemasaran massal (_blast broadcast marketing_).

### Business Rules

- Pengingat pesanan hanya dikirimkan satu kali per event (_idempotent_) dengan status tercatat `SENT`.
- Pengingat pembayaran hanya dikirimkan untuk pesanan yang belum lunas (_status invoice bukan PAID_).
- Pencatatan waktu proses sistem harus diukur berdasarkan durasi eksekusi nyata sejak tombol ditekan hingga hasil tampil di layar, tanpa klaim spekulatif.

### API Contract

#### Daftar Endpoint

| Method  | Path                            | Fungsi                                                                                                  | Autentikasi / Role                                        |
| :------ | :------------------------------ | :------------------------------------------------------------------------------------------------------ | :-------------------------------------------------------- |
| `GET`   | `/api/v1/reminders`             | Ambil daftar notifikasi pengingat in-app sesuai role (ringkasan keuangan khusus ADMIN, dengan paginasi) | Autentikasi: `ADMIN`, `STAFF`                             |
| `PATCH` | `/api/v1/reminders/:id/read`    | Tandai entri notifikasi pengingat in-app telah dibaca pengguna                                          | Autentikasi: `ADMIN`, `STAFF`                             |
| `POST`  | `/api/v1/reminders/process-due` | Jalankan proses pemindaian dan pengiriman pengingat jatuh tempo (idempoten)                             | Autentikasi: Internal `X-Internal-Token` dari worker/cron |

#### Format Wire Contract Sukses

- `POST /api/v1/reminders/process-due` (Internal Cron / Worker Call)
  - Headers: `X-Internal-Token: <INTERNAL_SERVICE_SECRET>`
  - Response `200 OK`:
    ```json
    {
      "data": {
        "processedCount": 3,
        "sentNotifications": [
          {
            "orderId": "ord_01",
            "type": "H_MINUS_1_EVENT",
            "channel": "IN_APP",
            "status": "DELIVERED"
          }
        ]
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000008" }
    }
    ```

- `GET /api/v1/reminders?page=1&limit=10`
  - Response `200 OK`:
    ```json
    {
      "data": [
        {
          "id": "notif_01",
          "title": "Pengingat Pesanan Besok",
          "message": "Pesanan ORD-202612-0001 (100 box) dijadwalkan besok pukul 10:00",
          "isRead": false,
          "createdAt": "2026-12-14T08:00:00.000Z"
        }
      ],
      "meta": {
        "requestId": "0192f0c8-7b3a-7000-8000-000000000009",
        "pagination": {
          "page": 1,
          "limit": 10,
          "total": 1,
          "totalPages": 1
        }
      }
    }
    ```

- `PATCH /api/v1/reminders/:id/read`
  - Response `204 No Content` (tanpa body response).

#### Standar Error RFC 9457 & Kode Status HTTP

Layanan mengembalikan kode status HTTP standar:

- `200 OK`: Pemrosesan pengingat selesai atau daftar notifikasi berhasil diambil.
- `204 No Content`: Notifikasi berhasil ditandai telah dibaca.
- `400 Bad Request`: Format JSON tidak valid.
- `401 Unauthorized`: Kredensial tidak valid atau `X-Internal-Token` salah.
- `403 Forbidden`: Staf mencoba mengakses ringkasan pengingat keuangan admin.
- `404 Not Found`: Notifikasi tidak ditemukan.
- `422 Unprocessable Content`: Validasi payload gagal.
- `500 Internal Server Error`: Kesalahan server internal saat mengirim notifikasi/email.

Contoh payload error RFC 9457 (`Content-Type: application/problem+json`):

```json
{
  "type": "https://datatracker.ietf.org/doc/html/rfc9457",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Kredensial token internal tidak valid.",
  "instance": "/api/v1/reminders/process-due",
  "requestId": "0192f0c8-7b3a-7000-8000-000000000008"
}
```

#### Dokumentasi OpenAPI 3.1.0 & Scalar

Seluruh endpoint terdaftar dalam skema OpenAPI 3.1.0 di `/api/openapi` dan disajikan via Scalar UI di `/docs` (fail-closed produksi `DOCS_ENABLED`).

### Acceptance Criteria

- [ ] Seluruh 3 endpoint pengingat terdaftar pada tabel kontrak API dan terimplementasi.
- [ ] Worker berhasil memproses pengingat pesanan H-1 dan pesanan jatuh tempo tanpa terjadinya duplikasi pengiriman ke pelanggan/staf.
- [ ] Pengujian skenario demonstrasi 100 nasi box berjalan mulus end-to-end: input pesanan -> hitung bahan -> terbit invoice -> catat DP -> jadwal tampil di dasbor.
- [ ] Waktu hitung bahan dan penerbitan invoice pada sistem tercatat bersama tanggal dan sumber pengukuran sebagai hasil teramati demonstrasi (potensi < 5 menit, tanpa klaim dampak bisnis komersial).
- [ ] Dokumen panduan pengguna (_user manual_) selesai disusun dengan bahasa sederhana dan instruksi bergambar.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tampil di Scalar `/docs`.

### Technical Notes

- Kredensial akun email SMTP pengirim pengingat `[Perlu Konfirmasi Tim]`.
- Pencatatan baseline waktu manual bersama mitra katering pada pesanan nyata `[Menunggu Konfirmasi PIC]`.

### DoD

- [ ] Pengujian E2E alur utama berhasil 100% tanpa kendala fungsional.
- [ ] Panduan pengguna tersedia di dokumentasi web atau direktori `docs/`.
- [ ] Hasil pengukuran waktu proses tercatat rapi dan siap didemonstrasikan.
- [ ] Dokumentasi endpoint OpenAPI 3.1.0 tersedia di Scalar `/docs`.

### Dependencies

- Prasyarat: `FS-05` (Pesanan), `FS-06` (Invoice Keuangan), `OPS-02` (VPS Runtime).
- Terkait: Dieksekusi secara terjadwal oleh cron VPS dan diuji ketahanan failover-nya pada `OPS-05`.

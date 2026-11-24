# Spesifikasi Teknis: Full-Stack Development (`01-fullstack.md`)

Berkas ini memuat spesifikasi teknis lengkap untuk 9 issue area Full-Stack (`FS-01` s.d. `FS-09`) yang telah diselaraskan penuh dengan Asah 2026 Project Plan – A26-CS105, mencakup rancangan mockup ramah staf senior, skema Prisma PostgreSQL 17, autentikasi RBAC & validasi Joi `/api/v1`, katalog menu/resep & konversi satuan bahan baku, alur pesanan → invoice → DP 60% → konfirmasi pesanan, PDF invoice vs PDF laporan analitik, proxy chatbot + backend read-only tools DB tanpa SQL bebas, dasbor analitik, serta pengingat otomatis, pengukuran waktu proses, dan uji E2E.

---

## [FS-01] App Mockup, Desain Responsif & App Shell Staf Senior

- **Labels:** `area:fullstack`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Klasifikasi Project Plan:** Wajib (Fondasi Antarmuka) & Tambahan (Mockup, Arsitektur UI Next.js + Tailwind + shadcn/ui)
- **Milestone:** `M1: Rancangan Disepakati (21–27 Nov 2026)`
- **Penanggung Jawab (Project Plan):** Haidar Habibi Al Farisi
- **Target Path:** `apps/web`, `docs/`

### Context

Operasional Catering Si Kembar melibatkan pengelola (`ADMIN`) serta staf operasional dan karyawan senior (`STAFF`) yang sebagian kurang terbiasa dengan antarmuka digital rumit. Sesuai Project Plan A26-CS105, mockup UI harus disepakati sebelum implementasi pada M1, antarmuka wajib sederhana, responsif, terbaca jelas di desktop maupun ponsel, serta setiap keputusan desain responsif (tata letak, ukuran teks, dan navigasi ramah staf senior) beserta alasannya wajib dicatat di README atau user manual.

### Scope

**Requirement Wajib (Project Plan):**

- Penyusunan rancangan mockup UI seluruh alur utama (login, input pesanan, menu & kalkulator bahan, invoice & pembayaran, dasbor jadwal) dan fitur tambahan (chatbot, dasbor analitik, notifikasi) sebelum implementasi kode.
- Pembangunan kerangka layout (_App Shell_) berbasis Next.js App Router, Tailwind CSS, dan shadcn/ui yang responsif untuk desktop dan ponsel.
- Penyajian navigasi sederhana dengan istilah familiar bagi staf senior (Pesanan, Menu & Bahan, Tagihan, Jadwal) dan penyesuaian tampilan menu berdasarkan peran (`ADMIN` vs `STAFF`).
- Pencatatan keputusan desain responsif (layout, teks, navigasi staf senior) dan alasannya pada README atau user manual.

**Rekomendasi Teknis / Implementasi:**

- Area sentuh tombol aksi utama minimal `44x44 px` dengan kontras teks memenuhi WCAG AA (rasio minimal `4.5:1`).
- Breakpoint responsif teruji pada resolusi mobile (`390x844`) dan desktop (`1440x900`) tanpa _horizontal overflow_.
- Indikator status jelas untuk kondisi berhasil, gagal, dan sedang diproses (_loading/error states_).

**Out-of-Scope:**

- Integrasi data API dinamis penuh (dikerjakan pada `FS-04` s.d. `FS-09`).
- Aplikasi mobile native Android/iOS (cakupan MVP adalah web responsif).
- Tema gelap (_dark mode_) kustom berlebih yang mengurangi keterbacaan di area dapur.

### Business Rules

- Navigasi utama dapat dijangkau maksimal dalam 2 ketukan/klik dari layar mana pun.
- Label tombol aksi menggunakan kata kerja bahasa Indonesia yang lugas (misal: "Simpan Pesanan", "Hitung Bahan", "Cetak Invoice").
- Menu sensitif seperti Keuangan (`FS-06`) dan Dasbor Analitik (`FS-08`) tidak ditampilkan pada navigasi peran `STAFF` (otorisasi tetap ditegakkan di backend `FS-03`).

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan aset/dokumen mockup dan kerangka UI _App Shell_ di `apps/web`.

### Acceptance Criteria

- [ ] Tersedia mockup UI seluruh alur utama yang disepakati tim sebelum implementasi M2.
- [ ] _App Shell_ Next.js terimplementasi dengan navigasi responsif: sidebar vertikal pada desktop (`>= 1024px`) dan bottom bar / drawer pada mobile (`< 768px`).
- [ ] Tidak terdapat pergeseran tata letak horizontal (_horizontal overflow_) pada tampilan ponsel `390x844` maupun desktop `1440x900`.
- [ ] Kontras warna teks memenuhi standar aksesibilitas WCAG AA (minimal 4.5:1) dan tombol aksi penting memiliki area sentuh memadai (`>= 44x44 px`).
- [ ] Keputusan desain responsif untuk staf senior dan alasannya tercatat di README atau user manual.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Validasi istilah menu navigasi dan contoh tampilan dasbor jadwal agar mudah dipahami karyawan senior Catering Si Kembar.
- `[Perlu Konfirmasi Tim]` Kesepakatan akhir desain mockup UI dan pembagian rute halaman `apps/web/app/`.

### DoD

- [ ] Mockup UI disepakati tim dan diimplementasikan ke dalam App Shell Next.js.
- [ ] Uji render responsif desktop (`1440x900`) dan ponsel (`390x844`) lulus tanpa error console.
- [ ] `npm run format:check`, `npm run lint`, dan `npm run typecheck` pada `apps/web` lulus tanpa peringatan.

### Dependencies

- **Prasyarat:** Konfigurasi Tailwind CSS, shadcn/ui, dan Axios pada monorepo `apps/web`.
- **Terkait:** Menjadi kerangka layout untuk `FS-04`, `FS-05`, `FS-06`, `FS-07`, `FS-08`, `FS-09`, dan deployment `OPS-03`.

---

## [FS-02] Skema Database Prisma, Migrasi & Seed Data Uji

- **Labels:** `area:fullstack`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Klasifikasi Project Plan:** Wajib (Fondasi Aplikasi: PostgreSQL dengan Prisma)
- **Milestone:** `M1: Rancangan Disepakati (21–27 Nov 2026)`
- **Penanggung Jawab (Project Plan):** Haidar Habibi Al Farisi, Zaki Eka Saputra
- **Target Path:** `packages/db`

### Context

Seluruh alur bisnis Smart Catering—mulai dari autentikasi RBAC, katalog menu dan resep standar dengan satuan bahan baku, alur pesanan → invoice → DP → pelunasan, pencatatan riwayat chatbot (web & WhatsApp), hingga penjadwalan reminder idempoten—membutuhkan skema relasional PostgreSQL yang konsisten melalui Prisma (`packages/db`). Skema juga wajib memisahkan data operasional dari data simulasi/sintetis melalui penanda `isSynthetic` sesuai guardrail Project Plan.

### Scope

**Requirement Wajib (Project Plan):**

- Perancangan skema database PostgreSQL pada `packages/db/prisma/schema.prisma` beserta migrasi dan script seed uji (`packages/db/prisma/seed.ts`).
- Entitas inti yang disepakati pada M1:
  - `User` (`role`: `ADMIN` | `STAFF`, `whatsappNumber` opsional untuk whitelist WAHA, password hash).
  - `Customer` (data pelanggan teranonimisasi untuk uji/simulasi, tanpa menyimpan PII riil di repositori).
  - `Menu` (nama, kategori, harga resmi satuan dari DB, status aktif).
  - `Ingredient` & `RecipeItem` (mendukung **satuan dasar** resep seperti `gram`/`ml`/`butir`/`lembar` serta **satuan konversi/belanja** seperti `kg`/`liter`/`pack` dan `conversionFactor` untuk perhitungan bahan baku akurat).
  - `Order` (`status`: `DRAFT`, `CONFIRMED`, `IN_PREPARATION`, `READY`, `DELIVERED`, `CANCELLED`, penanda `isSynthetic`), `OrderItem` (snapshot `unitPrice` dari `Menu` DB + `portion`).
  - `Invoice` (relasi `1:1` dengan `Order`, `invoiceNumber`, `totalAmount`, `minDpPercentage` terkonfigurasi default `0.60`, `paymentStatus`: `UNPAID`, `PARTIALLY_PAID`, `PAID`).
  - `Payment` (`type`: `DOWN_PAYMENT` | `FINAL_PAYMENT`, nominal, metode, waktu bayar, catatan).
  - `ChatSession` & `ChatLog` (riwayat percakapan web & WAHA: `userId`, `channel`, `message`, `reply`, `isRelevant`, `toolsCalled`, `sourcesJson`, `latencyMs`, `isFallback`).
  - `NotificationLog` (riwayat reminder & pencegah duplikasi: `idempotencyKey @unique`, `type`, `channel`, `recipient`, `status`, `retryCount`, `lastError`).
  - `Feedback` (opsional/pendukung analitik sentimen dengan flag wajib `isSynthetic`).
- Data tetap persisten setelah layanan/container dimulai ulang.

**Rekomendasi Teknis / Implementasi:**

- Gunakan tipe `Decimal` atau integer rupiah (`Int`/`BigInt`) untuk seluruh kolom moneter (`price`, `unitPrice`, `totalAmount`, `amount`) agar bebas galat pembulatan floating-point.
- Gunakan indeks pada `Order.eventDate`, `Order.status`, `Invoice.paymentStatus`, `ChatLog.sessionId`, dan `NotificationLog.idempotencyKey`.

**Out-of-Scope:**

- Tabel inventaris stok gudang real-time dan pencatatan mutasi keluar-masuk stok harian (ditegaskan keluar dari cakupan MVP Project Plan).
- Tabel data gaji karyawan atau integrasi payment gateway otomatis.

### Business Rules

- Setiap `Order` wajib memiliki minimal 1 `OrderItem`, dengan `unitPrice` disalin (_snapshot_) dari tabel `Menu` di backend saat transaksi dibuat.
- Setiap `Order` berelasi `1:1` dengan `Invoice`; perubahan pembayaran pada `Payment` selalu disinkronkan secara transaksional dengan `Invoice.paymentStatus`.
- Seluruh data simulasi/seed atau data sintetis wajib memiliki flag `isSynthetic = true` agar tidak pernah tercampur dengan data operasional nyata.
- `NotificationLog.idempotencyKey` bersifat unik untuk menjamin reminder worker/cron tidak pernah mengirim notifikasi ganda.

### API Contract

Tidak berlaku (tugas non-API). Menghasilkan Prisma Client pada package internal `@smart-catering/db`.

### Acceptance Criteria

- [ ] `npm run db:validate` dan `npm run db:generate` berhasil tanpa error.
- [ ] Migrasi berjalan mulus pada PostgreSQL dan data tetap bertahan setelah container/layanan dimulai ulang.
- [ ] Skema `Ingredient` & `RecipeItem` menyimpan satuan dasar, satuan konversi/tampilan, dan faktor konversi yang selaras dengan kamus data `DS-03`.
- [ ] Seluruh enum didefinisikan ketat: `Role (ADMIN, STAFF)`, `OrderStatus (DRAFT, CONFIRMED, IN_PREPARATION, READY, DELIVERED, CANCELLED)`, `PaymentStatus (UNPAID, PARTIALLY_PAID, PAID)`, `PaymentType (DOWN_PAYMENT, FINAL_PAYMENT)`.
- [ ] Entitas `Order` dan data simulasi/seed memiliki penanda `isSynthetic = true`; `NotificationLog` memiliki constraint unik `idempotencyKey`.
- [ ] Script seed (`packages/db/prisma/seed.ts`) berhasil mengisi akun uji (`ADMIN`, `STAFF`), menu standar nasi box, resep bahan baku, dan pesanan simulasi tanpa error foreign key atau PII nyata.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Besaran default persentase DP minimal `60%` (`minDpPercentage`) serta aturan apakah nominal DP di bawah batas ditolak keras atau diizinkan dengan catatan khusus.
- `[Menunggu Konfirmasi PIC]` Daftar final menu standar, takaran resep, harga resmi, dan satuan bahan baku UMKM Catering Si Kembar.
- `[Perlu Konfirmasi Tim]` Kesepakatan daftar satuan baku & faktor konversi antara Full-Stack (`FS-02`/`FS-04`) dan Data Science (`DS-03`).

### DoD

- [ ] `packages/db/prisma/schema.prisma`, migrasi, dan `seed.ts` terverifikasi berjalan bersih.
- [ ] Tidak ada kredensial database yang ditulis langsung dalam kode/skema (hanya membaca `DATABASE_URL`).
- [ ] Test integrasi/validasi skema di Vitest lulus.

### Dependencies

- **Prasyarat:** Konfigurasi PostgreSQL lokal atau Docker Compose (`infra/docker/compose.dev.yaml` / `compose.vps.yaml`).
- **Terkait:** Fondasi wajib bagi `FS-03`, `FS-04`, `FS-05`, `FS-06`, `FS-07`, `FS-08`, `FS-09`, dan `OPS-02`.

---

## [FS-03] Autentikasi, RBAC & Standar Validasi Express `/api/v1` (Joi)

- **Labels:** `area:fullstack`, `priority:P0-blocker`, `quest:main`, `quest:side`
- **Priority:** `P0-blocker`
- **Klasifikasi Project Plan:** Wajib (Fondasi Aplikasi: Autentikasi, RBAC, Validasi Joi, Penanganan Error) & Tambahan (Express REST `/api/v1`, Kontrak API OpenAPI)
- **Milestone:** `M1: Rancangan Disepakati (21–27 Nov 2026)`
- **Penanggung Jawab (Project Plan):** Haidar Habibi Al Farisi
- **Target Path:** `apps/api/src/modules/auth`, `apps/api/src/routes`

### Context

Sistem digunakan oleh dua tingkat peran utama: Pengelola/Pemilik (`ADMIN`) yang berhak mengakses keuangan, analitik, dan manajemen akun, serta Staf Operasional (`STAFF`) yang fokus pada pesanan, resep, dan jadwal produksi. Sesuai Project Plan A26-CS105, hak akses wajib diperiksa dan ditegakkan di backend Express (`apps/api`)—bukan hanya di UI atau prompt chatbot—disertai validasi request Joi, kontrak API `/api/v1` yang terdokumentasi di Swagger/OpenAPI sebelum implementasi fitur, serta penanganan error yang jelas.

### Scope

**Requirement Wajib (Project Plan):**

- Endpoint autentikasi & manajemen akun internal (`/api/v1/auth/login`, `/logout`, `/me`, `POST/GET /users`).
- Middleware autentikasi sesi/token dan otorisasi RBAC (`ADMIN` vs `STAFF`) yang ditegakkan pada seluruh endpoint bisnis dan endpoint internal tools chatbot.
- Middleware validasi payload (body, query, params) menggunakan **Joi** yang menolak input kosong/tidak valid dengan pesan yang menyebut kolom bermasalah.
- Penanganan error terpusat dengan kode status HTTP konsisten dan pesan ramah pengguna (termasuk saat koneksi DB bermasalah, tanpa crash).

**Rekomendasi Teknis / Implementasi:**

- Wire contract monorepo seragam: envelope sukses `{ data, meta: { requestId } }`, error RFC 9457 `application/problem+json` (`422` untuk gagal validasi Joi), header korelasi `X-Request-Id`.
- Middleware proteksi internal service-to-service menggunakan `X-Internal-Token` (`hmac.compare_digest` terhadap `INTERNAL_SERVICE_SECRET`) untuk komunikasi Express ↔ FastAPI (`AI-05`) dan Express ↔ Worker (`FS-09`).
- Dokumentasi otomatis OpenAPI 3.1.0 di `GET /api/openapi` dan Scalar UI di `GET /docs` (fail-closed di produksi lewat `DOCS_ENABLED`).

**Out-of-Scope:**

- Registrasi publik mandiri untuk pelanggan umum (portal pemesanan pelanggan berada di luar cakupan MVP).
- Integrasi SSO pihak ketiga (OAuth Google/Facebook).

### Business Rules

- Peran `STAFF` dilarang mengakses modul keuangan sensitif (`/api/v1/finance/*`), analitik eksekutif (`/api/v1/analytics/*`), ringkasan keuangan mingguan, maupun manajemen user (`/api/v1/auth/users`).
- RBAC wajib diverifikasi di sisi backend Express; backend tidak boleh memercayai klaim role mentah yang dikirim dari browser maupun hasil keluaran LLM.
- Password wajib di-hash dengan algoritma aman (`bcrypt` atau `argon2`) sebelum disimpan di PostgreSQL.
- Kredensial salah menghasilkan `401 Unauthorized`; peran tanpa izin menghasilkan `403 Forbidden` (RFC 9457); tidak ada secret/password yang dicetak di log.

### API Contract

#### Daftar Endpoint

| Method | Path                  | Fungsi                                                            | Autentikasi / Role |
| :----- | :-------------------- | :---------------------------------------------------------------- | :----------------- |
| `POST` | `/api/v1/auth/login`  | Autentikasi kredensial & penerbitan sesi/token                    | Publik             |
| `POST` | `/api/v1/auth/logout` | Invalidasi sesi/token aktif                                       | `ADMIN`, `STAFF`   |
| `GET`  | `/api/v1/auth/me`     | Profil dan hak akses pengguna aktif                               | `ADMIN`, `STAFF`   |
| `POST` | `/api/v1/auth/users`  | Buat akun staf internal baru (termasuk `whatsappNumber` opsional) | `ADMIN`            |
| `GET`  | `/api/v1/auth/users`  | Daftar akun pengguna internal (paginasi)                          | `ADMIN`            |

#### Contoh Wire Contract Sukses

- `POST /api/v1/auth/login` (`200 OK`):
  ```json
  {
    "data": {
      "token": "<jwt_or_session_token>",
      "user": { "id": "usr_01", "username": "admin_catering", "name": "Pengelola", "role": "ADMIN" }
    },
    "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000001" }
  }
  ```

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized` (kredensial salah / token kedaluwarsa), `403 Forbidden` (role tidak berwenang), `409 Conflict` (username duplikat), `422 Unprocessable Content` (validasi Joi gagal dengan array `errors` menyebut `path` kolom bermasalah), `500 Internal Server Error`.

### Acceptance Criteria

- [ ] Seluruh 5 endpoint `/api/v1/auth/*` terimplementasi dan terdokumentasi di OpenAPI 3.1.0 (`/api/openapi` & Scalar `/docs`).
- [ ] Login dengan kredensial salah ditolak dengan HTTP `401` dan pesan jelas; login valid mengembalikan profil dan peran yang benar.
- [ ] Percobaan peran `STAFF` mengakses endpoint khusus `ADMIN` (misal keuangan/analitik/users) ditolak dengan HTTP `403 Forbidden` RFC 9457.
- [ ] Validasi Joi menolak payload kosong atau tipe data salah dengan HTTP `422` RFC 9457 yang menyebut nama kolom bermasalah.
- [ ] Middleware `X-Internal-Token` tersedia dan teruji untuk mengamankan pemanggilan internal dari FastAPI (`AI-05`) dan worker (`FS-09`).
- [ ] Tidak ada password, token, atau secret yang bocor pada respons HTTP maupun log server.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Perlu Konfirmasi Tim]` Pilihan mekanisme transport sesi antara frontend Next.js BFF dan Express (`HttpOnly cookie` vs `Authorization: Bearer`) serta masa berlaku token.
- `[Menunggu Konfirmasi PIC]` Daftar akun awal (Admin & Staf) yang diperlukan untuk pengujian dan demonstrasi minggu ke-4.

### DoD

- [ ] Unit test dan route test autentikasi/RBAC/Joi di `apps/api` lulus Vitest dengan coverage >= 80%.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs` sesuai kontrak tim.
- [ ] `npm run format:check`, `npm run lint`, dan `npm run typecheck` lulus 100%.

### Dependencies

- **Prasyarat:** `FS-02` (Skema Prisma `User`).
- **Terkait:** Memproteksi seluruh modul `FS-04`, `FS-05`, `FS-06`, `FS-07`, `FS-08`, `FS-09`, serta integrasi internal `AI-05` dan `AI-07`.

---

## [FS-04] Modul Katalog Menu, Resep & Kalkulator Bahan Otomatis

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`
- **Priority:** `P1-mvp`
- **Klasifikasi Project Plan:** Wajib (Main Quest Full-Stack: Menu, Resep Standar, dan Perhitungan Bahan Baku)
- **Milestone:** `M2: Fitur Inti Tersedia (28 Nov–4 Des 2026)`
- **Penanggung Jawab (Project Plan):** Zaki Eka Saputra, Rio Andika Andriansyah
- **Target Path:** `apps/api/src/modules/menus`, `apps/web`

### Context

Catering Si Kembar saat ini menghitung kebutuhan bahan baku secara manual untuk setiap pesanan (misalnya 100 nasi box), yang memakan waktu lama dan rawan selisih takaran. Sesuai Project Plan A26-CS105, modul ini mengelola katalog menu beserta harga resmi, formulasi resep standar per porsi, serta kalkulasi otomatis kebutuhan bahan baku dengan **konversi satuan baku** yang hasilnya cocok 100% dengan hitungan manual UMKM untuk berbagai jumlah porsi (10, 50, 100 porsi) dan dapat digunakan ulang untuk estimasi bahan baku dari hasil forecasting (`DS-05` / `FS-08`).

### Scope

**Requirement Wajib (Project Plan):**

- Manajemen CRUD katalog menu dan harga resmi (`/api/v1/menus/*`) yang menjadi sumber kebenaran harga tunggal (_single source of truth_) bagi modul pesanan (`FS-05`).
- Manajemen formulasi resep standar per 1 porsi untuk tiap menu beserta satuan dasar bahan baku (misal `gram`, `ml`, `butir`, `lembar`, `ikat`).
- Kalkulator agregasi bahan baku otomatis (`POST /api/v1/menus/calculate-ingredients`) dengan **aturan konversi satuan konsisten** (misal otomatis mengonversi `gram -> kg` dan `ml -> liter` saat >= 1000, sambil mempertahankan nilai presisi satuan dasar).
- Peringatan jelas apabila menu yang dipilih **belum memiliki formulasi resep** (sesuai Rencana Pengujian Project Plan).
- Antarmuka web di `apps/web` untuk katalog menu, detail resep, dan kalkulator kebutuhan bahan yang mudah dibaca staf dapur di desktop maupun ponsel.

**Rekomendasi Teknis / Implementasi:**

- Pisahkan logika inti kalkulasi & konversi satuan ke fungsi/service murni (_reusable domain service_) di `apps/api/src/modules/menus/` agar dapat dipanggil langsung oleh `FS-05` (kebutuhan bahan per pesanan) dan `FS-08` (estimasi kebutuhan bahan baku dari hasil forecasting per menu `DS-05`).
- Sertakan penanda status resep (`isConfirmedByPic`) agar resep yang masih simulasi/menunggu konfirmasi PIC tampil jelas.
- Dokumentasi OpenAPI 3.1.0 & Scalar `/docs`.

**Out-of-Scope:**

- Sistem inventaris dan pengelolaan stok bahan baku secara real-time.
- Perhitungan pembelian bersih berdasarkan stok aktual gudang (karena data stok tidak tersedia — ditegaskan Out-of-Scope di Project Plan).
- Rekomendasi vendor/supplier belanja pasar.

### Business Rules

- **Presisi Perhitungan & Konversi Satuan:** Total kebutuhan bahan dihitung eksak (`takaran_per_porsi × jumlah_porsi`) lalu diagregasikan pada bahan yang sama dalam satuan dasar sebelum dikonversi ke satuan tampilan/belanja (contoh: `150 gram × 100 porsi = 15000 gram = 15 kg`; `125 gram × 100 porsi = 12500 gram = 12.5 kg`). Dilarang melakukan pembulatan ke atas secara sepihak yang membuat hasil menyimpang dari hitungan manual UMKM (pembulatan ke kemasan belanja hanya opsional jika dikonfirmasi PIC).
- **Menu Tanpa Resep:** Jika satu atau lebih menu belum memiliki resep, sistem wajib mengembalikan peringatan eksplisit yang menyebut nama menu bermasalah (tidak diam-diam mengembalikan nilai 0).
- **RBAC:** `ADMIN` dapat mengelola menu, harga, dan resep; `STAFF` hanya memiliki akses baca katalog, resep, dan menjalankan kalkulator bahan.

### API Contract

#### Daftar Endpoint

| Method  | Path                                  | Fungsi                                                               | Autentikasi / Role |
| :------ | :------------------------------------ | :------------------------------------------------------------------- | :----------------- |
| `GET`   | `/api/v1/menus`                       | Daftar katalog menu (filter pencarian, status resep, paginasi)       | `ADMIN`, `STAFF`   |
| `GET`   | `/api/v1/menus/:id`                   | Detail menu beserta daftar bahan & takaran resep per 1 porsi         | `ADMIN`, `STAFF`   |
| `POST`  | `/api/v1/menus`                       | Tambah menu baru dan harga resmi ke katalog                          | `ADMIN`            |
| `PATCH` | `/api/v1/menus/:id`                   | Perbarui nama, harga resmi, kategori, atau status aktif menu         | `ADMIN`            |
| `PUT`   | `/api/v1/menus/:id/recipe`            | Tetapkan / perbarui formula resep standar per 1 porsi                | `ADMIN`            |
| `POST`  | `/api/v1/menus/calculate-ingredients` | Hitung agregasi bahan baku + konversi satuan untuk 1..N menu & porsi | `ADMIN`, `STAFF`   |

#### Contoh Wire Contract Sukses

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
          {
            "ingredientId": "ing_01",
            "name": "Beras Putih",
            "baseAmount": 15000,
            "baseUnit": "gram",
            "displayAmount": 15,
            "displayUnit": "kg"
          },
          {
            "ingredientId": "ing_02",
            "name": "Daging Ayam",
            "baseAmount": 12500,
            "baseUnit": "gram",
            "displayAmount": 12.5,
            "displayUnit": "kg"
          }
        ],
        "warnings": [],
        "summary": { "totalPortions": 150, "uniqueIngredientsCount": 2 }
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000002" }
    }
    ```

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized`, `403 Forbidden` (`STAFF` mengubah menu/resep), `404 Not Found` (`menuId` tidak ditemukan), `422 Unprocessable Content` (porsi `<= 0`, bukan bilangan bulat, atau item kosong).

### Acceptance Criteria

- [ ] Seluruh 6 endpoint menu & kalkulator terimplementasi sesuai kontrak OpenAPI 3.1.0 di Scalar `/docs`.
- [ ] Perbandingan hasil kalkulasi sistem dengan hitungan manual dari resep terkonfirmasi untuk **10, 50, dan 100 porsi** menghasilkan angka yang **identik** (termasuk konversi satuan `gram ↔ kg` dan `ml ↔ liter`).
- [ ] Pengujian menu tanpa resep memunculkan peringatan eksplisit yang menyebut nama menu bermasalah (tidak gagal diam-diam atau bernilai 0).
- [ ] Input porsi `0`, negatif, huruf, atau desimal ditolak oleh Joi dengan HTTP `422` RFC 9457 yang menyebut kolom bermasalah.
- [ ] Percobaan modifikasi menu/resep oleh peran `STAFF` ditolak dengan HTTP `403 Forbidden`.
- [ ] Tampilan kalkulator bahan di web terbaca jelas di ponsel (`390x844`) tanpa _overflow_.
- [ ] Service agregasi bahan baku dapat dipanggil ulang secara internal oleh modul pesanan (`FS-05`) dan modul analitik estimasi bahan baku forecasting (`FS-08`).

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Konfirmasi resep standar, takaran gramatur bumbu/bahan utama, dan harga resmi menu nasi box Catering Si Kembar (bila belum lengkap di M1, gunakan data simulasi berlabel yang disetujui PIC).
- `[Menunggu Konfirmasi PIC]` Apakah tampilan daftar belanja cukup menampilkan hasil presisi konversi (`12.5 kg`) atau juga memerlukan kolom tambahan saran pembulatan ke satuan kemasan pasar.
- `[Perlu Konfirmasi Tim]` Penyelarasan nama bahan baku dan tabel konversi satuan dengan kamus data Data Science (`DS-03`).

### DoD

- [ ] Unit test & route test kalkulator (termasuk kasus 10/50/100 porsi, multi-menu, konversi satuan, dan menu tanpa resep) lulus di Vitest.
- [ ] Antarmuka katalog menu, resep, dan kalkulator di `apps/web` terhubung ke Express melalui Axios.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- **Prasyarat:** `FS-02` (Skema Menu, Ingredient, RecipeItem), `FS-03` (Auth/RBAC/Joi), `DS-03` (keselarasan kamus satuan bahan).
- **Terkait:** Dipanggil oleh `FS-05` (Pesanan), `FS-08` (Estimasi Bahan Baku dari Forecasting `DS-05`), dan `FS-09` (Demonstrasi 100 nasi box & pengukuran waktu proses).

---

## [FS-05] Modul Pesanan & Dasbor Jadwal Produksi

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`
- **Priority:** `P1-mvp`
- **Klasifikasi Project Plan:** Wajib (Main Quest Full-Stack: Input & Manajemen Pesanan + Dasbor Jadwal Produksi)
- **Milestone:** `M2: Fitur Inti Tersedia (28 Nov–4 Des 2026)` _(penyempurnaan dasbor jadwal & integrasi status pembayaran penuh selesai paling lambat akhir M3 sebelum feature freeze)_
- **Penanggung Jawab (Project Plan):** Haidar Habibi Al Farisi, Adnan Mufti Maulana
- **Target Path:** `apps/api/src/modules/orders`, `apps/web`

### Context

Catering Si Kembar saat ini memantau jadwal pesanan di Google Spreadsheet terpisah sehingga staf dapur dan karyawan senior kerap harus bertanya berulang kepada pengelola. Sesuai Project Plan A26-CS105, alur utama sistem adalah: **input pesanan (pemesan, menu, jumlah porsi, tanggal acara, alamat, catatan) → kalkulasi bahan baku dari resep standar & validasi total harga dari database backend → penerbitan invoice digital otomatis → pencatatan DP & pelunasan (`FS-06`) → konfirmasi pesanan → tampil di dasbor jadwal secara responsif dan mudah dipahami staf senior**.

### Scope

**Requirement Wajib (Project Plan):**

- Endpoint CRUD pesanan (`/api/v1/orders/*`) dengan validasi Joi lengkap (pemesan, menu, porsi > 0, tanggal acara valid, alamat, catatan).
- **Validasi harga dari database backend:** Backend wajib mengambil harga resmi langsung dari tabel `Menu` di PostgreSQL untuk menghitung subtotal & total harga (menyimpan snapshot `unitPrice` ke `OrderItem`); client **tidak boleh** menentukan atau memanipulasi `unitPrice`/`totalAmount`.
- **Integrasi alur Pesanan → Invoice → DP → Konfirmasi:**
  1. Saat `POST /api/v1/orders` sukses, backend secara atomik menghitung kebutuhan bahan baku (atau peringatan resep kosong), menghitung total harga dari DB, membuat `Order` berstatus `DRAFT`, dan otomatis menerbitkan `Invoice` digital (`1:1`, status `UNPAID`).
  2. Status pesanan berpindah menjadi `CONFIRMED` setelah pencatatan DP memenuhi aturan pada `FS-06` (atau disetujui Admin sesuai kebijakan PIC).
  3. Siklus operasional berlanjut: `CONFIRMED` → `IN_PREPARATION` → `READY` → `DELIVERED` (atau `CANCELLED`).
- Dasbor Jadwal Produksi yang sederhana, responsif di desktop & ponsel (`390x844`), menampilkan daftar/kalender pesanan terurut tanggal terdekat, rincian porsi/menu/bahan, dan status pembayaran sesuai hak akses pengguna.

**Rekomendasi Teknis / Implementasi:**

- Bungkus pembuatan `Order`, `OrderItem`, dan penerbitan `Invoice` awal di dalam satu transaksi database (`prisma.$transaction`) agar data tidak pernah parsial.
- Sediakan filter berdasarkan rentang tanggal acara, status pesanan, dan pencarian nama pemesan/kode pesanan.
- Dokumentasi OpenAPI 3.1.0 & Scalar `/docs`.

**Out-of-Scope:**

- Portal pemesanan mandiri oleh pelanggan publik via web.
- Pelacakan kurir pengiriman berbasis GPS real-time.
- Integrasi marketplace eksternal (Shopee, dll.).

### Business Rules

- **Sumber Harga Tunggal:** Request `POST /api/v1/orders` hanya menerima `{ menuId, portion }`. Harga satuan (`unitPrice`) dan `totalAmount` 100% dihitung dari record `Menu` aktif di PostgreSQL; menu nonaktif/tidak ada ditolak.
- **Alur Konfirmasi Pesanan:** Pesanan baru otomatis berstatus `DRAFT` bersama `Invoice` (`UNPAID`). Transisi ke `CONFIRMED` mensyaratkan DP sah pada `FS-06` (atau otorisasi khusus `ADMIN` sesuai aturan PIC).
- **Validasi Input:** Menu kosong, porsi `0`/negatif/huruf, tanggal acara kosong atau masa lalu (_past date_), dan format nomor telepon tidak valid ditolak dengan HTTP `422` RFC 9457 yang menyebut kolom bermasalah.
- **Kunci Status Final:** Pesanan berstatus `DELIVERED` atau `CANCELLED` tidak dapat diubah lagi (`409 Conflict`).
- **Visibilitas RBAC:** Staf (`STAFF`) melihat detail jadwal produksi, menu, porsi, alamat, catatan, dan daftar bahan tanpa mengekspos rekap keuangan/omzet khusus `ADMIN`.

### API Contract

#### Daftar Endpoint

| Method  | Path                        | Fungsi                                                                        | Autentikasi / Role |
| :------ | :-------------------------- | :---------------------------------------------------------------------------- | :----------------- |
| `GET`   | `/api/v1/orders`            | Daftar pesanan (filter tanggal acara, status, pencarian, paginasi)            | `ADMIN`, `STAFF`   |
| `GET`   | `/api/v1/orders/schedule`   | Jadwal produksi harian/mingguan terurut tanggal acara terdekat                | `ADMIN`, `STAFF`   |
| `GET`   | `/api/v1/orders/:id`        | Rincian pesanan, ringkasan kebutuhan bahan baku, dan referensi invoice        | `ADMIN`, `STAFF`   |
| `POST`  | `/api/v1/orders`            | Buat pesanan baru (validasi harga dari DB + otomatis terbit invoice `UNPAID`) | `ADMIN`, `STAFF`   |
| `PATCH` | `/api/v1/orders/:id`        | Ubah detail pesanan selama status masih `DRAFT` / belum final                 | `ADMIN`, `STAFF`   |
| `PATCH` | `/api/v1/orders/:id/status` | Transisi status operasional sesuai state machine bisnis                       | `ADMIN`, `STAFF`   |

#### Contoh Wire Contract Sukses

- `POST /api/v1/orders`
  - Request (perhatikan: **tidak ada `unitPrice` dari client**):
    ```json
    {
      "customerName": "Ibu Rahmawati",
      "customerPhone": "081234567890",
      "eventDate": "2026-12-15T10:00:00.000Z",
      "deliveryAddress": "Jl. Melati No. 12, Jakarta",
      "notes": "Nasi box jangan pedas",
      "items": [{ "menuId": "menu_01", "portion": 100 }]
    }
    ```
  - Response `201 Created`:
    ```json
    {
      "data": {
        "id": "ord_01",
        "orderNumber": "ORD-202612-0001",
        "status": "DRAFT",
        "totalAmount": 2500000,
        "eventDate": "2026-12-15T10:00:00.000Z",
        "invoice": {
          "id": "inv_01",
          "invoiceNumber": "INV-202612-0001",
          "paymentStatus": "UNPAID"
        },
        "recipeWarnings": []
      },
      "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000003" }
    }
    ```

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict` (transisi status tidak sah / order sudah final), `422 Unprocessable Content` (validasi Joi gagal, menu kosong, porsi <= 0 / huruf, tanggal kosong/masa lalu).

### Acceptance Criteria

- [ ] Seluruh 6 endpoint pesanan terimplementasi sesuai kontrak OpenAPI 3.1.0 di Scalar `/docs`.
- [ ] Simpan pesanan **100 nasi box** berhasil menghitung total harga secara otomatis dari tabel `Menu` DB (mengabaikan/menolak manipulasi harga dari client), menyimpan snapshot `unitPrice`, dan langsung menerbitkan invoice digital berstatus `UNPAID`.
- [ ] Input menu kosong, porsi `0`, negatif, huruf, atau tanggal kosong ditolak Joi dengan HTTP `422` RFC 9457 yang menyebut nama kolom bermasalah.
- [ ] Transisi status tidak sah (misal mengubah order `DELIVERED` atau loncat ke `CONFIRMED` tanpa DP/izin valid) ditolak dengan HTTP `409 Conflict` RFC 9457.
- [ ] Dasbor jadwal menampilkan pesanan di beberapa tanggal dan status secara akurat, terbaca jelas di ponsel (`390x844`) tanpa terpotong.
- [ ] Uji keterpahaman pengguna: staf dan karyawan senior dapat menemukan dan menjelaskan ulang detail pesanan di dasbor tanpa bertanya ke pengelola.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Apakah peran `STAFF` diperbolehkan melihat label ringkas status pembayaran (`UNPAID`/`PARTIALLY_PAID`/`PAID`) pada dasbor jadwal tanpa melihat nominal rupiah/rekap keuangan.
- `[Menunggu Konfirmasi PIC]` Batas maksimal kapasitas porsi harian katering dan aturan perubahan pesanan setelah DP dibayar.
- `[Perlu Konfirmasi Tim]` Format baku penomoran pesanan (`ORD-YYYYMM-XXXX`).

### DoD

- [ ] Unit test dan route test `apps/api/src/modules/orders` (termasuk pengujian anti-manipulasi harga & state machine) lulus di Vitest.
- [ ] Halaman form pesanan & dasbor jadwal di `apps/web` terhubung melalui Axios dan lulus uji tampilan mobile.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- **Prasyarat:** `FS-01` (App Shell), `FS-02` (Skema Order/Invoice), `FS-03` (Auth/RBAC/Joi), `FS-04` (Katalog Menu & Kalkulator Bahan).
- **Terkait:** Berpasangan langsung dengan `FS-06` (DP, pelunasan, konfirmasi pesanan, PDF Invoice), `FS-07` (backend read-only tools jadwal/pesanan untuk Agentic RAG), dan `FS-09` (Reminder & uji E2E 100 nasi box).

---

## [FS-06] Modul Keuangan: Invoice Digital, DP 60%, Pelunasan & PDF Invoice

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`
- **Priority:** `P1-mvp`
- **Klasifikasi Project Plan:** Wajib (Main Quest Full-Stack: Invoice Digital, Pencatatan DP minimal 60%, Pelunasan, Status Bayar)
- **Milestone:** `M3: Alur Utama Selesai & Feature Freeze (5–11 Des 2026)` _(penerbitan invoice digital dasar mulai diuji di M2 bersama `FS-05`; pencatatan DP, pelunasan, dan PDF invoice tuntas pada M3 sebelum feature freeze)_
- **Penanggung Jawab (Project Plan):** Haidar Habibi Al Farisi, Zaki Eka Saputra _(Pengujian: Zaki Eka Saputra, Chaviela Nazwa Syaqiba)_
- **Target Path:** `apps/api/src/modules/finance`, `apps/web`

### Context

Pembuatan invoice manual di Catering Si Kembar memakan waktu beberapa jam hingga keesokan harinya sehingga kepastian pesanan tertunda. Sesuai Project Plan A26-CS105, modul ini melengkapi alur **Pesanan (`DRAFT`) → Invoice Digital (`UNPAID`) → Pencatatan DP minimal 60% (`[Menunggu Konfirmasi PIC]`) → Konfirmasi Pesanan (`CONFIRMED`) → Pelunasan (`PAID`)**, sekaligus menyediakan **pembuatan PDF Invoice per Pesanan** di backend Express.

### Scope

**Requirement Wajib (Project Plan):**

- Pengelolaan invoice digital yang diterbitkan otomatis (`1:1`) saat pesanan dibuat di `FS-05` (beserta endpoint idempoten `POST /api/v1/finance/invoices` bila diperlukan).
- Pencatatan pembayaran manual (`POST /api/v1/finance/payments`):
  - **Uang Muka (DP):** Validasi batas minimal default **60%** (`[Menunggu Konfirmasi PIC]`) dari `totalAmount` invoice; nominal di bawah batas ditolak atau memunculkan peringatan/konfirmasi khusus sesuai aturan PIC.
  - **Pelunasan:** Validasi nominal tidak kosong, > 0, dan tidak melebihi sisa tagihan (_remaining balance_).
- Pembaruan status otomatis secara transaksional:
  - Invoice: `UNPAID` → `PARTIALLY_PAID` (DP tercatat) → `PAID` (lunas).
  - Sinkronisasi ke `Order` (`FS-05`): pencatatan DP yang sah otomatis mengubah (atau membuka) status `Order` dari `DRAFT` menjadi `CONFIRMED`.
- **Pembagian Tanggung Jawab PDF:** Modul `FS-06` bertanggung jawab khusus atas **pembuatan & unduh/cetak PDF Invoice Digital per Pesanan** (`GET /api/v1/finance/invoices/:id/pdf`) di backend Express. _(Catatan: Pembuatan PDF Laporan Analitik & AI Business Insight menjadi tanggung jawab terpisah pada modul analitik `FS-08`, bukan `FS-06`.)_
- Antarmuka web di `apps/web` untuk daftar tagihan, pencatatan pembayaran tunai/transfer, rincian sisa tagihan, dan tombol cetak/unduh PDF Invoice.

**Rekomendasi Teknis / Implementasi:**

- Simpan persentase batas DP minimum sebagai parameter konfigurasi (default `0.60`), bukan angka keras tak dapat diubah, agar mudah disesuaikan setelah konfirmasi PIC.
- Gunakan generator PDF server-side ringan di Express (misal `pdfkit`) untuk menghemat RAM VPS dibandingkan headless browser.
- Dokumentasi OpenAPI 3.1.0 & Scalar `/docs`.

**Out-of-Scope:**

- Integrasi payment gateway (Midtrans/Xendit) dan verifikasi pembayaran otomatis.
- Rekonsiliasi mutasi bank otomatis.
- Pembuatan PDF Laporan Analitik / AI Business Insight (ditangani oleh `FS-08`).

### Business Rules

- Total tagihan invoice selalu bersumber dari kalkulasi harga resmi DB pada `Order` (`FS-05`).
- Nominal pembayaran `<= 0`, kosong, atau melebihi `remainingBalance` wajib ditolak dengan HTTP `422` RFC 9457.
- Aturan DP minimal **60%** masih berstatus `[Menunggu Konfirmasi PIC]`; perilaku untuk DP di bawah 60% harus mendukung penolakan atau peringatan/override khusus `ADMIN` yang tercatat alasannya sesuai keputusan PIC.
- Invoice berstatus `PAID` dikunci dan menolak pembayaran baru (`409 Conflict`).
- Seluruh endpoint modul keuangan (`/api/v1/finance/*`) dan halaman keuangan di web hanya boleh diakses peran **`ADMIN`** (`STAFF` ditolak dengan HTTP `403 Forbidden`).

### API Contract

#### Daftar Endpoint

| Method | Path                               | Fungsi                                                                                                                    | Autentikasi / Role |
| :----- | :--------------------------------- | :------------------------------------------------------------------------------------------------------------------------ | :----------------- |
| `GET`  | `/api/v1/finance/invoices`         | Daftar invoice (filter `paymentStatus`, rentang tanggal, paginasi)                                                        | `ADMIN`            |
| `GET`  | `/api/v1/finance/invoices/:id`     | Rincian invoice, riwayat pembayaran, total DP, dan sisa tagihan                                                           | `ADMIN`            |
| `POST` | `/api/v1/finance/invoices`         | Terbitkan invoice untuk order `DRAFT` (idempoten 1:1 per order)                                                           | `ADMIN`            |
| `POST` | `/api/v1/finance/payments`         | Catat pembayaran DP (default min 60% `[Menunggu Konfirmasi PIC]`) atau pelunasan; sinkronisasi status `Invoice` & `Order` | `ADMIN`            |
| `GET`  | `/api/v1/finance/invoices/:id/pdf` | Unduh / cetak **PDF Invoice Pesanan** (`application/pdf`)                                                                 | `ADMIN`            |

#### Contoh Wire Contract Sukses

- `POST /api/v1/finance/payments` (`201 Created`):
  ```json
  {
    "data": {
      "paymentId": "pay_01",
      "invoiceId": "inv_01",
      "orderId": "ord_01",
      "orderStatus": "CONFIRMED",
      "amountPaid": 1500000,
      "totalPaid": 1500000,
      "remainingBalance": 1000000,
      "invoiceStatus": "PARTIALLY_PAID"
    },
    "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000004" }
  }
  ```
- `GET /api/v1/finance/invoices/:id/pdf`: Response `200 OK`, `Content-Type: application/pdf`, `Content-Disposition: inline; filename="invoice-INV-202612-0001.pdf"`.

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized`, `403 Forbidden` (non-`ADMIN`), `404 Not Found`, `409 Conflict` (invoice sudah `PAID`), `422 Unprocessable Content` (nominal kosong/negatif/melebihi sisa tagihan/DP di bawah ketentuan PIC), `500 Internal Server Error`.

### Acceptance Criteria

- [ ] Seluruh 5 endpoint keuangan terimplementasi sesuai kontrak OpenAPI 3.1.0 di Scalar `/docs`.
- [ ] Alur **Pesanan (`DRAFT`) → Invoice (`UNPAID`) → Catat DP 60% → Invoice (`PARTIALLY_PAID`) & Pesanan (`CONFIRMED`) → Catat Pelunasan → Invoice (`PAID`)** berjalan akurat dan dapat diperiksa ulang.
- [ ] Pengujian DP di bawah 60%, nominal kosong, `<= 0`, atau melebihi sisa tagihan ditolak atau memunculkan peringatan sesuai aturan PIC yang terkonfigurasi (`422` RFC 9457).
- [ ] Total tagihan, total terbayar, dan sisa tagihan akurat tanpa galat pembulatan desimal.
- [ ] Pengunduhan `GET /api/v1/finance/invoices/:id/pdf` menghasilkan berkas PDF Invoice pesanan yang rapi, dapat dicetak/disimpan, memuat identitas katering, rincian menu & porsi, total, DP, sisa tagihan, dan informasi pembayaran.
- [ ] Akses modul keuangan oleh peran `STAFF` ditolak dengan HTTP `403 Forbidden` RFC 9457.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Kepastian angka persentase minimum DP (apakah tetap 60% atau nominal lain) serta kebijakan toleransi/override untuk DP di bawah batas minimum (ditolak mutlak vs diizinkan dengan peringatan/catatan Admin).
- `[Menunggu Konfirmasi PIC]` Format dan konten resmi PDF Invoice Catering Si Kembar (logo, nama/nomor rekening tujuan transfer, syarat & ketentuan pembayaran).
- `[Perlu Konfirmasi Tim]` Pemilihan pustaka generator PDF server-side di Express (`pdfkit` atau setara) agar berbagi utilitas yang bersih dengan PDF laporan analitik `FS-08`.

### DoD

- [ ] Unit test & route test `apps/api/src/modules/finance` (skenario DP 60%, DP < 60%, pelunasan, overpayment, double-pay pada `PAID`, RBAC `STAFF`, dan stream PDF) lulus di Vitest.
- [ ] Antarmuka daftar invoice, form pembayaran, dan tombol unduh/cetak PDF di `apps/web` berfungsi tanpa error.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- **Prasyarat:** `FS-02` (Skema Invoice/Payment), `FS-03` (Auth/RBAC `ADMIN`), `FS-05` (Pembuatan Pesanan `DRAFT` yang memicu penerbitan invoice awal).
- **Terkait:** Menjadi sumber data status DP & pelunasan bagi backend read-only tools Agentic RAG (`FS-07`/`AI-05`), analitik keuangan (`FS-08`), dan pengingat jatuh tempo pembayaran (`FS-09`).

---

## [FS-07] Modul Chat AI: Proxy Backend, Read-Only Tools DB, Riwayat Chat & UI Web

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp` _(komponen proxy chatbot web + riwayat chat mendukung fitur Wajib Chatbot Generatif; backend read-only tools operasional mendukung fitur Tambahan Agentic RAG — tidak boleh menunda penyelesaian alur utama `FS-04`..`FS-06`)_
- **Klasifikasi Project Plan:** Wajib (Chatbot Generatif melalui backend, riwayat chat tersimpan, kanal web) & Tambahan (Backend Read-Only Tools untuk Agentic RAG)
- **Milestone:** `M3: Alur Utama Selesai & Feature Freeze (5–11 Des 2026)`
- **Penanggung Jawab (Project Plan):** Haidar Habibi Al Farisi, Adnan Mufti Maulana, Mohamad Dwi Rezky Desyafa
- **Target Path:** `apps/api/src/modules/chat`, `apps/web`

### Context

Sesuai arsitektur Project Plan A26-CS105, frontend Next.js **tidak boleh** memanggil FastAPI (`apps/ai-service`), ChromaDB, maupun API LLM secara langsung. Backend Express (`apps/api`) memiliki dua peran krusial dalam ekosistem chatbot:

1. **Proxy & Penyimpan Riwayat Chat:** Memverifikasi autentikasi & peran pengguna (`ADMIN`/`STAFF`), meneruskan pertanyaan ke FastAPI `POST /api/v1/rag/chat` (bersama konteks peran terverifikasi), menyimpan riwayat percakapan (`ChatLog`) ke PostgreSQL, serta menyajikan UI chatbot web yang responsif dan ramah staf.
2. **Penyedia Backend Tools Baca-Saja (_Read-Only Tools_) ke PostgreSQL untuk Agentic RAG (`AI-05`):** Menyediakan endpoint internal baca-saja berparameter ketat agar agen LLM dapat mengambil data operasional aktual (**pesanan, invoice, status DP, pelunasan, dan jadwal produksi**) sesuai hak akses peran yang diverifikasi oleh backend Express—**tanpa pernah memberi akses SQL bebas kepada LLM**.

### Scope

**Requirement Wajib (Project Plan):**

- Endpoint proxy chat web:
  - `POST /api/v1/chat/messages`: verifikasi sesi pengguna → teruskan pertanyaan, `sessionId`, dan konteks `userId`/`userRole` terverifikasi ke FastAPI `:8001/api/v1/rag/chat` → simpan riwayat lengkap ke PostgreSQL `ChatLog` → kembalikan balasan beserta metadata sumber.
  - `GET /api/v1/chat/sessions` & `GET /api/v1/chat/sessions/:sessionId/messages`: ambil riwayat percakapan milik pengguna login.
- **Backend Tools Baca-Saja (_Read-Only_) untuk Agentic RAG (`AI-05`)** pada namespace `/api/v1/internal/agent-tools/*` (khusus operasi `GET`, validasi Joi, Prisma terparameterisasi, diproteksi `X-Internal-Token`):
  1. `GET /api/v1/internal/agent-tools/orders`: pencarian/detail pesanan aktual berdasarkan kode pesanan, nama pemesan, atau rentang tanggal.
  2. `GET /api/v1/internal/agent-tools/schedule`: jadwal produksi aktual berdasarkan rentang tanggal & status.
  3. `GET /api/v1/internal/agent-tools/invoices`: rincian invoice, total tagihan, status DP, nominal terbayar, sisa tagihan, dan status pelunasan (**wajib penegakan RBAC `ADMIN` di backend Express; ditolak `403` untuk `STAFF`**, kecuali status ringkas bila disetujui PIC).
- Antarmuka UI Chatbot di `apps/web`: menampilkan gelembung percakapan, indikator _loading/typing_, tampilan **metadata sumber tervalidasi** (nama sumber, tanggal, versi, status validasi) atau referensi kode pesanan/invoice, serta pesan error yang jelas saat layanan AI tidak tersedia/timeout/kuota habis.
- Kegagalan layanan AI (FastAPI mati, timeout, kuota habis) ditangani _graceful_ dan **tidak boleh mengganggu alur fitur inti aplikasi web**.

**Rekomendasi Teknis / Implementasi:**

- Batasi jumlah pesan konteks riwayat yang dikirim ke FastAPI (misal 6–10 pesan terakhir per sesi) untuk efisiensi token.
- Terapkan _rate limiting_ ringan per pengguna pada `/api/v1/chat/messages` untuk menjaga kuota API LLM.
- Dokumentasi OpenAPI 3.1.0 & Scalar `/docs`.

**Out-of-Scope:**

- Memberikan akses query SQL bebas (`text-to-SQL`) atau koneksi langsung PostgreSQL kepada LLM/FastAPI.
- Tools mutasi data (membuat pesanan, mengubah harga, atau mencatat pembayaran lewat chatbot).
- Voice chat / _speech-to-text_.

### Business Rules

- **Penegakan RBAC di Backend (Bukan di Prompt):** Express menentukan `userRole` secara eksklusif dari sesi/JWT terverifikasi, lalu menegakkan izin yang sama saat FastAPI memanggil `/api/v1/internal/agent-tools/*`. Jika peran `STAFF` meminta data keuangan sensitif/invoice terlarang (termasuk melalui upaya _prompt injection_), endpoint internal tool wajib menolak dengan `403 Forbidden` RFC 9457 dan mencatat kejadian di log audit keamanan.
- **Tanpa SQL Bebas:** Seluruh akses data operasional hanya melalui query Prisma terparameterisasi pada endpoint read-only yang telah ditetapkan.
- **Kejelasan Kegagalan:** Jika FastAPI tidak merespons (timeout / mati / kuota habis), Express mengembalikan respons error/fallback yang jelas (HTTP `503`/`504` RFC 9457 atau fallback terstruktur yang disepakati) tanpa membuat aplikasi web crash.
- **API Key Server-Only:** Seluruh kredensial/API key hanya berada di environment server, tidak pernah terekspos ke browser.

### API Contract

#### Daftar Endpoint

| Method | Path                                        | Fungsi                                                                       | Autentikasi / Role                                                          |
| :----- | :------------------------------------------ | :--------------------------------------------------------------------------- | :-------------------------------------------------------------------------- |
| `POST` | `/api/v1/chat/messages`                     | Kirim pertanyaan web, proxy ke FastAPI `/api/v1/rag/chat`, simpan `ChatLog`  | `ADMIN`, `STAFF`                                                            |
| `GET`  | `/api/v1/chat/sessions`                     | Daftar sesi percakapan milik pengguna login (paginasi)                       | `ADMIN`, `STAFF`                                                            |
| `GET`  | `/api/v1/chat/sessions/:sessionId/messages` | Riwayat pesan & metadata sumber dalam satu sesi                              | `ADMIN`, `STAFF`                                                            |
| `GET`  | `/api/v1/internal/agent-tools/orders`       | _(Internal Read-Only Tool)_ Ambil data pesanan aktual dari PostgreSQL        | `X-Internal-Token` + konteks `X-Actor-Role` (`ADMIN`, `STAFF`)              |
| `GET`  | `/api/v1/internal/agent-tools/schedule`     | _(Internal Read-Only Tool)_ Ambil jadwal produksi aktual                     | `X-Internal-Token` + konteks `X-Actor-Role` (`ADMIN`, `STAFF`)              |
| `GET`  | `/api/v1/internal/agent-tools/invoices`     | _(Internal Read-Only Tool)_ Ambil data invoice, status DP & pelunasan aktual | `X-Internal-Token` + konteks `X-Actor-Role` (`ADMIN` saja; `STAFF` → `403`) |

#### Contoh Wire Contract Sukses

- `POST /api/v1/chat/messages` (`200 OK`):
  ```json
  {
    "data": {
      "sessionId": "ses_01",
      "reply": "Pemesanan minimal nasi box ayam lengkuas adalah 20 porsi dengan konfirmasi H-2.",
      "isRelevant": true,
      "toolsCalled": ["search_catering_knowledge"],
      "sources": [
        {
          "source": "faq.md",
          "category": "faq",
          "version": "1.0",
          "validatedAt": "2026-11-24",
          "validationStatus": "verified",
          "chunkId": "faq_order_01_c1"
        }
      ],
      "isFallback": false,
      "latencyMs": 1420
    },
    "meta": { "requestId": "0192f0c8-7b3a-7000-8000-000000000005" }
  }
  ```

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized`, `403 Forbidden` (akses tool/data di luar hak akses role atau `X-Internal-Token` tidak sah), `404 Not Found` (sesi atau data pesanan/invoice tidak ditemukan), `422 Unprocessable Content`, `503 Service Unavailable` / `504 Gateway Timeout` (layanan FastAPI/LLM tidak tersedia/timeout).

### Acceptance Criteria

- [ ] Seluruh 3 endpoint chat proxy web dan 3 endpoint internal read-only tools terimplementasi sesuai kontrak OpenAPI 3.1.0 di Scalar `/docs`.
- [ ] Frontend Next.js hanya berkomunikasi ke Express via Axios (0 panggilan langsung ke FastAPI/LLM dari browser).
- [ ] Setiap percakapan (pertanyaan, jawaban, `isRelevant`, `toolsCalled`, metadata sumber, latensi, status fallback) tersimpan di tabel PostgreSQL `ChatLog` dan dapat dibaca ulang lewat riwayat sesi.
- [ ] Endpoint `/api/v1/internal/agent-tools/*` hanya melayani operasi baca-saja (`GET`), tervalidasi Joi, tanpa menerima query SQL mentah, dan menolak akses `STAFF` ke data invoice/keuangan terlarang dengan HTTP `403` + catatan log keamanan.
- [ ] Simulasi mematikan FastAPI (`apps/ai-service`) atau timeout menampilkan pesan error jelas pada UI chat sementara alur pesanan, kalkulator, invoice, dan dasbor tetap berjalan normal.
- [ ] UI chat menampilkan metadata sumber dokumen tervalidasi (sumber, tanggal, versi, status validasi) dan responsif di layar ponsel (`390x844`).

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Apakah `STAFF` diizinkan menanyakan status bayar ringkas (`UNPAID`/`PARTIALLY_PAID`/`PAID`) sebuah pesanan tertentu lewat chatbot tanpa menampilkan nominal uang, atau seluruh query invoice khusus `ADMIN`.
- `[Perlu Konfirmasi Tim]` Penyelarasan final skema JSON antara `POST /api/v1/chat/messages` (Express), `POST /api/v1/rag/chat` (FastAPI `AI-05`), dan `/api/v1/internal/agent-tools/*` (termasuk batas timeout default, misal 15 detik, dan batas rate limit).

### DoD

- [ ] Unit test & mock inter-service test Express–FastAPI dan pengujian keamanan RBAC pada internal agent tools lulus di Vitest.
- [ ] Komponen UI chat di `apps/web` berfungsi interaktif pada desktop & ponsel tanpa error console.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- **Prasyarat:** `FS-02` (Skema `ChatLog`), `FS-03` (Auth/RBAC & `X-Internal-Token`), `FS-05` & `FS-06` (Data Pesanan/Jadwal/Invoice), `AI-01` (FastAPI), `AI-05` (Pipeline Agentic RAG).
- **Terkait:** Berbagi pipeline RAG dan pencatatan `ChatLog` bersama integrasi kanal WhatsApp `AI-07`.

---

## [FS-08] Modul Dasbor Analitik DS: KPI, Filter, Upload Data, Estimasi Bahan Forecasting & PDF Laporan

- **Labels:** `area:fullstack`, `priority:P2-side-quest`, `quest:side`
- **Priority:** `P2-side-quest` _(fitur tambahan — tidak boleh menunda alur utama `FS-04`..`FS-06` sebelum feature freeze akhir M3)_
- **Klasifikasi Project Plan:** Tambahan (Side Quest DS: Dasbor Analitik Interaktif + Integrasi Forecasting, Sentimen, AI Business Insight & Unduhan PDF Laporan)
- **Milestone:** `M3: Alur Utama Selesai & Feature Freeze (5–11 Des 2026)`
- **Penanggung Jawab (Project Plan):** Chaviela Nazwa Syaqiba, Haidar Habibi Al Farisi
- **Target Path:** `apps/api/src/modules/analytics`, `apps/web`

### Context

Sesuai Project Plan A26-CS105, pengelola Catering Si Kembar (`ADMIN`) memerlukan dasbor analitik interaktif yang menyajikan indikator KPI yang **definisinya telah dikunci terlebih dahulu oleh tim DS pada `DS-02` (M2)**, filter periode & status, pembaruan data melalui database maupun unggahan file valid, tampilan hasil **forecasting permintaan per menu (`DS-05`) yang digabungkan dengan resep standar (`FS-04`) menjadi estimasi kebutuhan bahan baku**, ringkasan **analisis sentimen (`AI-03`)**, narasi **AI Business Insight (`AI-06`)**, serta **unduhan PDF Laporan Analitik** yang di-render oleh backend Express.

### Scope

**Requirement Wajib (Project Plan untuk Fitur Dasbor Analitik):**

- Endpoint agregasi KPI bisnis (`/api/v1/analytics/overview`) yang mengimplementasikan formula KPI resmi terkunci dari `DS-02` (M2): total pesanan, total porsi, omzet/revenue, menu terfavorit (frekuensi & volume porsi), rasio status pembayaran, tren periode, serta filter periode tanggal dan status pesanan/bayar.
- **Integrasi Forecasting Per Menu → Estimasi Kebutuhan Bahan Baku:** Backend Express memanggil layanan forecasting (`DS-05`, `POST /api/v1/ml/forecast/demand`) untuk proyeksi porsi per menu, lalu menggabungkannya dengan resep standar terkonfirmasi (`FS-04`) untuk menyajikan tabel estimasi kebutuhan bahan baku beserta pernyataan batas data/simulasi.
- Integrasi tampilan ringkasan analisis sentimen (`AI-03`) dengan label jelas apabila berasal dari data sintetis (`is_synthetic = true`).
- Endpoint unggah berkas pembaruan data (`/api/v1/analytics/upload`, `.csv`/`.xlsx`) dengan validasi skema ketat dan penanda `isSynthetic`; berkas berformat salah ditolak dengan pesan jelas (`422` RFC 9457) tanpa merusak data eksisting.
- Endpoint pemicu narasi AI Business Insight (`/api/v1/analytics/insights`) yang memanggil FastAPI `POST /api/v1/insight/generate` (`AI-06`) membawa metrik agregat aktual.
- **Pembagian Tanggung Jawab PDF:** Modul `FS-08` bertanggung jawab tunggal atas **pembuatan & unduhan PDF Laporan Analitik + AI Business Insight** (`GET /api/v1/analytics/report/pdf`) di backend Express. _(Berbeda dari PDF Invoice Pesanan yang menjadi tanggung jawab `FS-06`.)_
- Halaman Dasbor Analitik interaktif di `apps/web` dengan filter periode/status, visualisasi grafik, unggah file, panel insight AI, dan tombol unduh PDF Laporan.

**Rekomendasi Teknis / Implementasi:**

- Gunakan pustaka grafik kompatibel React/Next.js (misal Recharts) dengan label sumbu, satuan, dan disclaimer data sintetis/prediksi yang jelas.
- Sediakan endpoint terpisah atau bagian dalam overview untuk `GET /api/v1/analytics/forecast-ingredients` agar pemanggilan forecasting tidak memblokir muatan kartu KPI utama bila `apps/ai-service` lambat.
- Dokumentasi OpenAPI 3.1.0 & Scalar `/docs`.

**Out-of-Scope:**

- Platform BI enterprise eksternal (Tableau/PowerBI embed).
- Pembuatan PDF Invoice per Pesanan (dikerjakan di `FS-06`).
- Pelatihan ulang model ML dari browser.

### Business Rules

- Seluruh endpoint `/api/v1/analytics/*` (termasuk unduhan PDF Laporan) dan halaman dasbor analitik hanya boleh diakses oleh peran **`ADMIN`** (`STAFF` ditolak dengan HTTP `403 Forbidden`).
- Formula seluruh angka KPI wajib 100% identik dengan spesifikasi KPI yang dikunci di `DS-02` (dan diaudit akhir di `DS-06`).
- Setiap data sintetis (`isSynthetic = true`) atau hasil prediksi forecasting wajib menampilkan badge/catatan batas data secara eksplisit (tidak diklaim sebagai data riil atau jaminan akurasi operasional).
- Jika layanan AI Insight (`AI-06`) atau forecasting (`DS-05`) tidak tersedia/timeout, kartu KPI dan filter dasbor tetap berjalan normal dengan pesan status jelas pada panel terkait.

### API Contract

#### Daftar Endpoint

| Method | Path                                     | Fungsi                                                                                                              | Autentikasi / Role |
| :----- | :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------ | :----------------- |
| `GET`  | `/api/v1/analytics/overview`             | Ringkasan KPI (`DS-02`), tren periode, filter status/tanggal, sentimen (`AI-03`), & prediksi (`DS-05`)              | `ADMIN`            |
| `GET`  | `/api/v1/analytics/forecast-ingredients` | Ambil proyeksi permintaan per menu (`DS-05`) dan gabungkan dengan resep standar (`FS-04`) untuk estimasi bahan baku | `ADMIN`            |
| `POST` | `/api/v1/analytics/upload`               | Unggah berkas `.csv`/`.xlsx` pembaruan data (`multipart/form-data`, validasi skema, flag `isSynthetic`)             | `ADMIN`            |
| `POST` | `/api/v1/analytics/insights`             | Picu narasi AI Business Insight via FastAPI `POST /api/v1/insight/generate` (`AI-06`)                               | `ADMIN`            |
| `GET`  | `/api/v1/analytics/report/pdf`           | Unduh **PDF Laporan Analitik & AI Business Insight** (`application/pdf`)                                            | `ADMIN`            |

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized`, `403 Forbidden` (`STAFF` mengakses dasbor atau unduh PDF), `422 Unprocessable Content` (filter tanggal terbalik, format file unggahan salah/kolom wajib hilang), `503 Service Unavailable` (layanan forecasting/insight sementara tidak tersedia).

### Acceptance Criteria

- [ ] Seluruh 5 endpoint analitik terimplementasi sesuai kontrak OpenAPI 3.1.0 di Scalar `/docs` dan mengadopsi formula KPI terkunci dari `DS-02`.
- [ ] Filter periode tanggal dan status pesanan/pembayaran memperbarui indikator KPI dan grafik secara dinamis dan akurat.
- [ ] Unggah file valid (`.csv`/`.xlsx`) berhasil memperbarui data dengan penandaan `isSynthetic` yang sesuai; unggah file berformat salah ditolak dengan HTTP `422` RFC 9457 dan pesan jelas.
- [ ] Prediksi permintaan per menu (`DS-05`) berhasil digabungkan dengan resep terkonfirmasi (`FS-04`) menjadi estimasi kebutuhan bahan baku beserta catatan batas data/simulasi.
- [ ] Ringkasan sentimen (`AI-03`) dan narasi AI Business Insight (`AI-06`) tampil terpadu di dasbor; data sintetis ditandai jelas.
- [ ] Unduhan `GET /api/v1/analytics/report/pdf` menghasilkan PDF Laporan Analitik yang angkanya konsisten dengan dasbor dan narasi `AI-06`, serta menolak akses non-`ADMIN` dengan HTTP `403`.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Konfirmasi daftar kartu KPI default dan struktur ringkasan laporan PDF analitik yang paling berguna bagi pengelola Catering Si Kembar.
- `[Perlu Konfirmasi Tim]` Kesepakatan pustaka visualisasi grafik React (misal Recharts) dan struktur kolom template file CSV/XLSX unggahan antara `FS-08` dan `DS-02`/`DS-03`.

### DoD

- [ ] Unit test dan route test `/api/v1/analytics/*` (termasuk validasi upload file salah, RBAC `STAFF`, agregasi estimasi bahan, dan PDF stream) lulus di Vitest.
- [ ] Halaman Dasbor Analitik di `apps/web` responsif dan bebas error console.
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- **Prasyarat:** `DS-02` (**Definisi KPI Terkunci di M2**), `FS-04` (Resep & Service Kalkulator Bahan), `FS-05` & `FS-06` (Data Pesanan & Keuangan), `DS-05` (Forecasting per Menu), `AI-03` (Sentimen), `AI-06` (AI Business Insight).
- **Terkait:** Angka KPI dan laporan diverifikasi pada audit akurasi akhir `DS-06` (M4).

---

## [FS-09] Modul Pengingat Otomatis (In-App, WAHA, Email), User Manual, Ukur Waktu Proses & Uji E2E

- **Labels:** `area:fullstack`, `priority:P1-mvp`, `quest:main`, `quest:side`
- **Priority:** `P1-mvp` _(Pengukuran waktu proses, User Manual, dan Uji E2E 100 nasi box adalah **Wajib**; Modul Reminder Otomatis adalah **Tambahan** dan tidak boleh menunda alur utama)_
- **Klasifikasi Project Plan:** Wajib (Pengukuran Waktu Proses, Pengujian E2E & User Manual) & Tambahan (Reminder Otomatis In-App, WAHA, Email Opsional)
- **Milestone:** `M4: Validasi & Finalisasi (12–20 Des 2026)` — **PENTING (Kepatuhan Feature Freeze):** Seluruh kode fitur _Reminder Otomatis_ wajib selesai paling lambat **akhir M3 (11 Des 2026)**; fase **M4 (12–20 Des 2026)** difokuskan khusus pada pengujian E2E, perbaikan bug, pengukuran waktu proses vs baseline manual, demonstrasi PIC 100 nasi box, dan finalisasi dokumentasi/user manual.
- **Penanggung Jawab (Project Plan):** Haidar Habibi Al Farisi (Reminder & E2E), Zaki Eka Saputra (Koordinator Dokumentasi & Pengukuran Waktu Proses)
- **Target Path:** `apps/api/src/modules/reminders`, `apps/worker`, `apps/web`, `docs/`

### Context

Sesuai Project Plan A26-CS105, terdapat dua pilar kerja penutup dari sisi Full-Stack:

1. **Modul Pengingat Otomatis (kode selesai ≤ akhir M3 / Feature Freeze):** Menangani 4 jenis pengingat—**pesanan terdekat (H-1), pembayaran belum lunas, ringkasan keuangan mingguan (khusus `ADMIN`), dan saran bahan baku**—melalui kanal **in-app, WhatsApp via WAHA (khusus nomor staf terdaftar), dan email opsional (SendGrid/SMTP)**, dipicu oleh worker Node.js dan cron sistem VPS (tanpa Redis/BullMQ) dengan jaminan **tanpa duplikasi** dan pencatatan kegagalan untuk dicoba ulang.
2. **Validasi, Pengukuran Waktu Proses & Dokumentasi Akhir (M4):** Menjalankan pengujian end-to-end skenario **100 nasi box** bersama PIC, mencatat waktu hitung bahan dan waktu penerbitan invoice pada sistem dibandingkan dengan **baseline manual** yang dicatat pada M1 sebagai **hasil teramati (bukan klaim dampak bisnis)**, serta menyusun User Manual dan README lengkap.

### Scope

**Requirement Wajib (Project Plan — M4 Validasi & Dokumentasi):**

- Pengujian menyeluruh end-to-end alur utama (**skenario 100 nasi box**: input pesanan → hitung bahan → terbit invoice → catat DP & pelunasan → dasbor jadwal) pada uji internal dan demonstrasi PIC.
- Pengukuran dan pencatatan waktu proses sistem (waktu hitung bahan & waktu penerbitan invoice) dibandingkan dengan baseline waktu manual mitra (dicatat tanggal dan sumber pengukuran; target < 5 menit hanya disebut sebagai **potensi**, bukan klaim dampak bisnis).
- Penyusunan **User Manual** sederhana berbahasa Indonesia yang ramah staf senior (termasuk alasan keputusan desain responsif) dan pembaruan bagian dokumentasi uji pada README + Spreadsheet pengujian bersama.

**Requirement Fitur Tambahan (Project Plan — Kode Reminder selesai ≤ akhir M3 / Feature Freeze):**

- Endpoint pengelolaan & pemrosesan pengingat di Express (`/api/v1/reminders`, `PATCH /api/v1/reminders/:id/read`, `POST /api/v1/reminders/process-due`).
- Cakupan **4 jenis pengingat**:
  1. Pesanan terdekat (misal H-1 acara).
  2. Pembayaran belum lunas (`UNPAID` / `PARTIALLY_PAID` mendekati acara).
  3. **Ringkasan keuangan mingguan** (hanya dikirim/ditampilkan kepada peran berwenang **`ADMIN`**).
  4. **Saran kebutuhan bahan baku** untuk pesanan terjadwal terdekat (memanfaatkan kalkulasi resep `FS-04`).
- Cakupan **3 kanal pengiriman**:
  1. In-app notification di `apps/web` (lonceng & daftar pengingat sesuai role).
  2. WhatsApp via WAHA (`AI-07`) — **hanya ke nomor staf terdaftar** dengan volume rendah.
  3. Email opsional (SendGrid atau SMTP) — dengan fallback ke in-app jika belum dikonfigurasi/gagal.
- Task worker Node.js di `apps/worker` yang memanggil `POST /api/v1/reminders/process-due` (dipicu cron sistem VPS tanpa Redis/BullMQ, dan mendukung pemicuan manual lewat backend bila cron gagal).
- Mekanisme **anti-duplikasi (_idempotency_)** menggunakan `idempotencyKey` unik pada `NotificationLog` serta pencatatan status gagal (`FAILED`) dan **mekanisme percobaan ulang (_retry_)** tanpa mengulang pengiriman yang sudah berhasil.

**Out-of-Scope:**

- SMS gateway berbayar atau pesan broadcast promosi massal ke pelanggan.
- Penggunaan Redis/BullMQ pada fase MVP.
- Klaim dampak bisnis komersial telah tercapai dari hasil prototype.

### Business Rules

- **Idempotensi Ketat:** Menjalankan cron/worker dua kali pada jadwal reminder yang sama **tidak boleh** mengirim notifikasi ganda (`idempotencyKey` unik per jenis/entitas/periode/kanal/penerima).
- **Retry Tanpa Duplikasi:** Jika satu kanal gagal (misal WAHA putus atau SMTP error), kegagalan dicatat di `NotificationLog` dan dicoba ulang hanya untuk item yang berstatus `FAILED` tanpa mengganggu pengiriman kanal lain yang sudah `DELIVERED`.
- **RBAC Pengingat Keuangan:** Ringkasan keuangan mingguan dan nominal tagihan sensitif hanya boleh dikirim dan ditampilkan ke peran **`ADMIN`** (`STAFF` ditolak `403` atau tersaring ketat).
- **Whitelist WhatsApp:** Pengiriman WAHA hanya ditujukan ke `whatsappNumber` staf terdaftar di database.
- **Pelaporan Objektif Waktu Proses:** Waktu sistem dan baseline manual dicatat beserta tanggal dan sumbernya sebagai hasil teramati demonstrasi.

### API Contract

#### Daftar Endpoint

| Method  | Path                            | Fungsi                                                                                                | Autentikasi / Role                                              |
| :------ | :------------------------------ | :---------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------- |
| `GET`   | `/api/v1/reminders`             | Daftar notifikasi in-app sesuai role (ringkasan keuangan khusus `ADMIN`, paginasi)                    | `ADMIN`, `STAFF`                                                |
| `PATCH` | `/api/v1/reminders/:id/read`    | Tandai notifikasi in-app telah dibaca                                                                 | `ADMIN`, `STAFF`                                                |
| `POST`  | `/api/v1/reminders/process-due` | Pindai jadwal jatuh tempo, kirim reminder lintas kanal (in-app/WAHA/email), catat idempotensi & retry | `X-Internal-Token` (Worker/Cron) atau `ADMIN` (manual fallback) |

#### Standar Error RFC 9457 (`Content-Type: application/problem+json`)

- `401 Unauthorized` (`X-Internal-Token` atau sesi tidak valid), `403 Forbidden`, `404 Not Found`, `422 Unprocessable Content`, `500 Internal Server Error`.

### Acceptance Criteria

- [ ] Seluruh 3 endpoint reminder terimplementasi (kode selesai ≤ akhir M3) dan terdokumentasi di OpenAPI 3.1.0 Scalar `/docs`.
- [ ] Pengujian membuat pesanan H-1 & pembayaran belum lunas, lalu menjalankan cron/worker **dua kali berturut-turut** pada jadwal yang sama membuktikan reminder terkirim **tepat sekali tanpa duplikasi**.
- [ ] Pengujian mematikan salah satu kanal (misal WAHA atau email) membuktikan kegagalan tercatat di `NotificationLog`, kanal lain tetap berjalan, dan item gagal dapat dicoba ulang tanpa menduplikasi yang berhasil.
- [ ] Pesan WhatsApp hanya terkirim ke nomor staf terdaftar; ringkasan keuangan mingguan hanya dapat diakses/diterima peran `ADMIN`.
- [ ] Pengujian E2E skenario **100 nasi box** (input pesanan → hitung bahan → terbit invoice → catat DP & pelunasan → dasbor jadwal) lulus penuh pada uji internal dan demonstrasi PIC, dengan feedback PIC tercatat.
- [ ] Waktu proses manual (baseline M1) dan waktu sistem (demonstrasi M4) tercatat lengkap dengan tanggal dan sumbernya sebagai hasil teramati tanpa klaim dampak bisnis.
- [ ] User Manual berbahasa sederhana (memuat panduan staf senior & catatan keputusan desain responsif) dan catatan hasil uji di Spreadsheet bersama & README selesai disusun.

### Keputusan yang Membutuhkan Konfirmasi (PIC / Tim)

- `[Menunggu Konfirmasi PIC]` Jadwal pencatatan baseline waktu manual hitung bahan & penerbitan invoice bersama mitra (M1) serta jadwal demonstrasi 100 nasi box dan final survey (M4).
- `[Menunggu Konfirmasi PIC]` Waktu pengiriman ideal reminder harian (misal H-1 jam 08.00 WIB) dan hari pengiriman ringkasan keuangan mingguan.
- `[Perlu Konfirmasi Tim]` Pemilihan kanal email opsional (SendGrid vs SMTP gratis) atau cukup in-app + WAHA bila batas kuota email tidak memadai.

### DoD

- [ ] Kode fitur reminder & worker selesai dan lolos test idempotensi/retry/RBAC sebelum feature freeze akhir M3 (11 Des 2026).
- [ ] Uji E2E 100 nasi box, laporan waktu proses teramati, feedback PIC, dan User Manual selesai di M4 (20 Des 2026).
- [ ] Endpoint terdaftar di OpenAPI 3.1.0 Scalar `/docs`.

### Dependencies

- **Prasyarat:** `FS-02` (`NotificationLog`), `FS-04` (Kalkulator Saran Bahan), `FS-05` (Pesanan/Jadwal), `FS-06` (Invoice/DP/Pelunasan), `AI-07` (Kanal WAHA), `OPS-02` (VPS Runtime).
- **Terkait:** Penjadwalan cron & uji failover pra-demo terkoordinasi erat dengan `OPS-05`.

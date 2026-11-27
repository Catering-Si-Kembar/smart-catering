# Mockup UI, Peta Rute & Keputusan Desain Responsif Staf Senior (`FS-01`)

**Issue Terkait:** `#1` (`[FS-01] App Mockup, Desain Responsif & App Shell Staf Senior`) · **Milestone:** `M1 (21–27 Nov 2026)`  
**Pemilik Workspace:** `@smart-catering/web` (`apps/web`) · **Mitra:** Catering Si Kembar

---

## 1. Tujuan & Profil Pengguna Sasaran

Antarmuka **Smart Catering** dirancang untuk dua profil pengguna operasional:

1. **Pengelola (`ADMIN`):** Mengelola pesanan, katalog menu/resep, tagihan & invoice DP 60%, analitik penjualan/forecasting, dan pengingat keuangan.
2. **Staf Operasional & Staf Senior (`STAFF`):** Memantau jadwal produksi harian, mencatat pesanan, menghitung bahan belanja dapur, melihat pengingat H-1, dan bertanya ke Asisten AI tanpa mengakses data keuangan sensitif.

Seluruh prototipe pada `FS-01` memakai **data simulasi teranonimisasi (`isSynthetic = true`)** tanpa data pribadi pelanggan nyata dan belum terhubung ke endpoint backend dinamis (`FS-04` s.d. `FS-09`).

---

## 2. Peta Rute Resmi `apps/web/app/`

Peta rute ini menjadi kontrak tata letak bersama untuk implementasi `FS-03` hingga `FS-09`:

| Rute          | File Next.js App Router                        | Label Menu      | Akses Peran      | Modul Target     |
| ------------- | ---------------------------------------------- | --------------- | ---------------- | ---------------- |
| `/`           | `apps/web/app/(dashboard)/page.tsx`            | Jadwal Hari Ini | `ADMIN`, `STAFF` | `FS-01`, `FS-05` |
| `/login`      | `apps/web/app/login/page.tsx`                  | Masuk Akun      | Publik           | `FS-03`          |
| `/pesanan`    | `apps/web/app/(dashboard)/pesanan/page.tsx`    | Pesanan         | `ADMIN`, `STAFF` | `FS-05`          |
| `/menu`       | `apps/web/app/(dashboard)/menu/page.tsx`       | Menu & Bahan    | `ADMIN`, `STAFF` | `FS-04`          |
| `/tagihan`    | `apps/web/app/(dashboard)/tagihan/page.tsx`    | Tagihan         | `ADMIN` saja     | `FS-06`          |
| `/chat`       | `apps/web/app/(dashboard)/chat/page.tsx`       | Asisten AI      | `ADMIN`, `STAFF` | `FS-07`          |
| `/analitik`   | `apps/web/app/(dashboard)/analitik/page.tsx`   | Analitik        | `ADMIN` saja     | `FS-08`          |
| `/notifikasi` | `apps/web/app/(dashboard)/notifikasi/page.tsx` | Pengingat       | `ADMIN`, `STAFF` | `FS-09`          |

- Menu **`Tagihan`** dan **`Analitik`** disembunyikan dari sidebar, laci mobile, dan bottom bar saat peran `STAFF` aktif; akses langsung URL pada mode pratinjau menampilkan kartu pemberitahuan akses khusus `ADMIN` (otorisasi resmi tetap ditegakkan di backend Express `FS-03`).

---

## 3. Wireframe Mockup Seluruh Alur (Desktop `1440×900` & Mobile `390×844`)

### 3.1 App Shell & Jadwal Hari Ini (`/`)

```text
DESKTOP (1440x900)                                        MOBILE (390x844)
+--------------------+---------------------------------+  +-----------------------------+
| [Logo] Smart       | Jadwal Hari Ini    [Terhubung]  |  | [≡] Jadwal Hari Ini [●][🔔] |
|        Catering    | [🔔]                            |  +-----------------------------+
|--------------------|---------------------------------|  | [Badge Peran]               |
| OPERASIONAL UTAMA  | Jadwal Produksi Smart Catering  |  | Jadwal Produksi             |
| > Jadwal Hari Ini  | [Catat Pesanan Baru]            |  | [   Catat Pesanan Baru    ] |
|   Pesanan          | [Hitung Bahan]                  |  | [      Hitung Bahan       ] |
|   Menu & Bahan     |                                 |  |-----------------------------|
|   Tagihan (ADMIN)  | [150 Box] [3 Pesanan] [2 Tagih] |  | Total Porsi Besok: 150 Box  |
|                    |                                 |  |-----------------------------|
| PENDUKUNG & PINTAR | Jadwal Produksi Terdekat:       |  | 2026-11-25 · 09:30 WIB      |
|   Asisten AI       | +-----------------------------+ |  | Ayam Goreng Lengkuas (100)  |
|   Analitik (ADMIN) | | 09:30 WIB · 100 Box Ayam    | |  | [Lihat Bahan] [Buka Invoice]|
|   Pengingat        | | [Lihat Bahan] [Buka Invoice]| |  |-----------------------------|
|--------------------| +-----------------------------+ |  |                             |
| [Pratinjau Peran]  |                                 |  +-----------------------------+
| [Pengelola|Staf]   | [Uji Memuat|Berhasil|Gagal]     |  |Jadwal|Pesan|Menu|Tagih|Lain |
+--------------------+---------------------------------+  +-----------------------------+
```

### 3.2 Alur Inti & Fitur Tambahan

- **Masuk Akun (`/login`):** Kartu terpusat satu kolom, logo Catering Si Kembar, input besar (`min-h-12`), tombol tampil/sembunyikan kata sandi `48×48 px`, tombol pratinjau peran (`Pengelola` / `Staf Dapur`), dan banner validasi merah kontras tinggi bila kolom kosong.
- **Pesanan & Jadwal (`/pesanan`):** Tombol aksi utama `Buat Pesanan` membuka formulir input dengan validasi langsung, diikuti tab filter (`Semua`, `Menunggu DP`, `Sedang Dimasak`, `Siap Dikirim`), tombol cepat `Lihat Bahan`, serta tombol transisi status dapur (`Mulai Masak`, `Tandai Siap Kirim`, `Tandai Terkirim`).
- **Menu & Kalkulator Bahan (`/menu`):** Dropdown pilihan menu, input porsi dengan tombol preset cepat **`10 Box`**, **`50 Box`**, **`100 Box`**, kartu hasil konversi otomatis (`gram → kg`, `ml → liter`), serta banner peringatan kontras tinggi bila menu belum memiliki resep standar.
- **Tagihan & Invoice (`/tagihan` — khusus `ADMIN`):** Daftar invoice dengan ringkasan `Total`, `DP Min. 60%`, dan `Sisa Bayar` (`tabular-nums`), tombol `Catat DP 60%` / `Catat Pelunasan`, serta panel pratinjau lembar invoice dan tombol `Cetak Invoice`.
- **Asisten AI (`/chat`):** Tombol pertanyaan cepat sekali ketuk (mengurangi kebutuhan mengetik bagi staf senior), gelembung percakapan teks `16px`, label sumber informasi (`Resep Standar`, `Data Pesanan`, `Knowledge Base SOP`), dan contoh respons penolakan luar domain.
- **Dasbor Analitik (`/analitik` — khusus `ADMIN`):** Filter periode (`7 Hari` / `30 Hari`), 4 kartu KPI, prediksi porsi minggu depan, persentase sentimen sintetis, ringkasan narasi AI Business Insight, dan tombol `Unduh Laporan PDF`.
- **Pengingat (`/notifikasi`):** Daftar pengingat H-1, saran bahan baku, dan tagihan belum lunas (disaring sesuai peran) dengan tombol `Tandai Sudah Dibaca`.

---

## 4. Keputusan Desain Responsif untuk Staf Senior & Alasannya

| Aspek Desain          | Keputusan Implementasi                                                                                                                                                                                                                                                                                                                                                                                                      | Alasan Operasional (Staf Senior & Dapur)                                                                                                            |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tata Letak & Nav**  | Desktop `>= 1024px` memakai sidebar vertikal tetap (`288px`); mobile `< 768px` memakai bottom bar 5 slot (4 menu inti + `Lainnya` drawer); tablet memakai drawer.                                                                                                                                                                                                                                                           | Semua halaman utama terjangkau **maksimal 2 ketukan** tanpa harus menghafal submenu bertingkat.                                                     |
| **Area Sentuh**       | Seluruh tombol (`Button`), tautan menu, tab filter, dan input form memakai tinggi minimum **`44–48 px`** (`min-h-11` / `min-h-12`).                                                                                                                                                                                                                                                                                         | Mencegah salah tekan di layar ponsel `390×844` oleh staf senior saat bergerak cepat di area dapur.                                                  |
| **Tipografi & Angka** | System UI font offline-safe, teks isi `16px` (`text-base`), label kontrol minimal `14px`, angka porsi/rupiah/berat memakai `tabular-nums`.                                                                                                                                                                                                                                                                                  | Mudah dibaca tanpa memperbesar layar, angka nominal sejajar rapi, dan build CI aman tanpa remote font.                                              |
| **Kontras & Warna**   | Latar terang Warm Sand `#F9F9F8` + kartu `#FFFFFF` + border `#DAD9D6`. Teks utama Dark Ink `#21201C` (16,2:1), teks sekunder `#4B4943` (9,5:1). Aksi utama (CTA Button) Kuning Celemek Logo `#FBCC04` dengan teks `#21201C` (kontras 9,4:1 AAA, ramah dan tidak rancu dengan tombol bahaya/hapus). Aksen Operasional & Admin Merah Hijab Logo `#9E1B32` (7,8:1). Aksen Asisten AI & Staf Ungu Hijab Logo `#5C3271` (7,5:1). | Seluruh pasangan warna jauh melampaui batas **WCAG AAA** (min 7:1) dan selaras 100% dengan logo Catering Si Kembar tanpa memperkenalkan warna baru. |
| **Interaksi Tactile** | Umpan balik fisik saat ditekan (`active:scale-[0.97]`), bayangan kartu bertingkat 1px halus, sudut membulat `rounded-xl`, dan transisi cepat `duration-150`.                                                                                                                                                                                                                                                                | Memberikan kepastian sentuhan fisik bagi staf senior saat menekan tombol di layar sentuh dapur.                                                     |
| **Bahasa & Label**    | Istilah operasional familiar (_Jadwal Hari Ini_, _Pesanan_, _Menu & Bahan_, _Tagihan_) dan kata kerja aktif (_Simpan Pesanan_, _Hitung Bahan_, _Cetak Invoice_).                                                                                                                                                                                                                                                            | Menghindari jargon teknis bahasa Inggris sehingga staf senior dapat memahami fungsi tombol sekali lihat.                                            |
| **Umpan Balik State** | Komponen `StatusBanner` (`role="status"` / `role="alert"`) seragam untuk kondisi _memuat_, _berhasil_, dan _gagal_ + indikator koneksi `Terhubung`/`Offline` di header.                                                                                                                                                                                                                                                     | Mengurangi kebingungan apakah data sudah tersimpan atau gagal karena sinyal dapur kurang stabil.                                                    |
| **Keamanan Overflow** | Pembatasan lebar fleksibel (`min-w-0`, grid responsif, `overflow-x: clip`) dan ruang bawah `pb-24` pada mobile.                                                                                                                                                                                                                                                                                                             | Mencegah halaman bergeser ke samping pada `390×844` dan memastikan konten terbawah tidak tertutup bottom bar.                                       |

## 5. Prinsip Desain Anti-Slop & Standar UI Operasional Nyata (Acuan Modul Berikutnya)

Berdasarkan evaluasi operasional bersama mitra dan tim, seluruh modul lanjutan (`FS-03` hingga `FS-09` serta modul AI) **wajib mematuhi 5 standar anti-slop** berikut agar antarmuka tidak terkesan seperti purwarupa/demo AI:

1. **Bebas Jargon Developer & Kode Isu:**
   - Dilarang menampilkan kode isu internal (`FS-01`, `FS-04`, `DS-05`, `AI-06`, dll.) pada elemen UI publik (judul, tombol, pesan banner, maupun pratinjau invoice).
   - Dilarang menampilkan nama algoritma internal (misal: `Model Random Forest`, `isSynthetic = true`). Gunakan terminologi operasional yang lugas (contoh: _"Proyeksi pesanan minggu depan"_, _"Berdasarkan survei pelanggan"_).

2. **Eliminasi Frasa "Simulasi" / "Mockup" di Antarmuka Pengguna:**
   - Tidak menyematkan kata `(Simulasi)` atau `Mockup` pada nama pelanggan, judul katalog, riwayat pesan asisten, atau notifikasi sukses transaksi. UI harus terasa 100% sebagai software operasional siap pakai.

3. **Bebas Clutter Promosi di Antrean Operasional:**
   - Tidak menempatkan banner promosi atau ajakan fitur lain (misal: kartu promosi chatbot AI) di dalam alur kerja memasak staf dapur. Fitur pendukung tetap berada pada navigasi yang semestinya.

4. **Desain Badging Editorial (Anti-Badge Slop):**
   - Hindari menumpuk beberapa badge pill tebal dengan ikon 13px di header kartu.
   - Gunakan indikator dot status yang bersih: `ORD-202611-0001 · 🟡 Sedang Dimasak di Dapur`.
   - Posisikan status pembayaran di kolom finansial samping nominal tagihan, bukan di samping nomor order.
   - Tampilkan "Catatan Khusus" menggunakan aksen garis batas kiri tipis (`border-l-2 border-amber-500 bg-amber-50/60`), bukan kotak peringatan kuning tebal yang memicu kebingungan visual staf.

5. **Tata Letak Sidebar & Aksi Pengguna yang Efisien:**
   - Tombol **Keluar Akun** ditempatkan langsung di pojok kiri bawah navigasi desktop secara bersih tanpa kartu widget peran redundan.
   - Pilihan profil dan peralihan peran akun terpusat di menu avatar pojok kanan atas.

---

## 6. Item Konfirmasi Terbuka

- `[Menunggu Konfirmasi PIC]` Validasi akhir istilah navigasi (_Jadwal Hari Ini_, _Menu & Bahan_, _Tagihan_) dan format kartu jadwal bersama karyawan senior Catering Si Kembar.
- `[Perlu Konfirmasi Tim]` Kesepakatan akhir peta rute `/`, `/login`, `/pesanan`, `/menu`, `/tagihan`, `/chat`, `/analitik`, `/notifikasi` untuk integrasi modul `FS-03` s.d. `FS-09`.

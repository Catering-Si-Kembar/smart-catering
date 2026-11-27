# Knowledge Base RAG (`data/knowledge`)

Tempat menyimpan dokumen pengetahuan untuk pipeline RAG (daftar menu, FAQ, SOP operasional, dan kebijakan pembayaran DP/pelunasan) yang telah divalidasi PIC UMKM Catering Si Kembar.

## Domain Pengetahuan Terkurasi

1. `menus.md` (`category: menu`): Katalog hidangan paket nasi box, nasi liwet tampah, tumpeng kuning, snack box, dan prasmanan silver/gold.
2. `faq.md` (`category: faq`): Pertanyaan umum terkait minimal order pemesanan, lead time waktu pesan, area layanan Bandung Raya, dan menu halal/alergi.
3. `sop.md` (`category: sop`): Standar operasional prosedur pencatatan order, persiapan bahan dapur H-1, standar kebersihan food safety, dan pengantaran tepat waktu.
4. `payment_policy.md` (`category: payment`): Ketentuan uang muka DP minimal 60%, batas pelunasan tagihan H-1, kebijakan pembatalan/reschedule, dan invoice digital.

## Format Frontmatter Wajib PIC

Setiap dokumen markdown menyertakan metadata frontmatter YAML:

- `doc_id`: Pengenal unik dokumen (contoh: kb_menus_01)
- `source`: Nama file dokumen (mis. `menus.md`)
- `category`: Domain pengetahuan (`menu` | `faq` | `sop` | `payment`)
- `version`: Nomor versi rilis dokumen kurasi (mis. `"1.0"`)
- `validated_at`: Tanggal validasi PIC UMKM (mis. `"2026-11-27"`)
- `validation_status`: Status verifikasi kurasi (`verified` | `draft`)
- `is_verified`: Boolean verifikasi validasi (`true` | `false`)

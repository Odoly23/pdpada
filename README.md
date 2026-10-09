# Lafex

Tutor bahasa AI berbasis suara untuk masyarakat Timor-Leste: siswa **bicara langsung**, tutor menjawab dengan suara, mengoreksi, dan menyesuaikan level (A1-C2).

Bahasa: Inggris, Portugis, Spanyol, Korea, Jepang, dan Tetun (beta). Penjelasan bisa dalam Tetun, Indonesia, Portugis, atau Inggris.

## Menjalankan

```bash
npm install
export ANTHROPIC_API_KEY=...        # tanpa ini, jalan dalam mode offline (skrip sederhana, tanpa AI)
npm start                           # http://localhost:3000
npm test
```

Buka lewat **Chrome/Edge di Android atau desktop** (pengenalan suara terbaik di sana). Safari/Firefox mungkin hanya mendukung suara keluar; mengetik selalu tersedia.

## Akses dan voucher

Pembayaran tanpa kartu: siswa membeli **kode voucher** (kios/agen) lalu memasukkannya; kode sekali pakai dan menambah masa aktif.

```bash
npm run vouchers -- 7d 10           # buat 10 voucher 7 hari
# atau lewat HTTP: POST /api/admin/vouchers  (header x-admin-token = ADMIN_TOKEN)
```

Harga/paket ada di `lib/config.js`. Nilai awal: 24 jam $1, 3 hari $2, 7 hari $3, 1 bulan $8, 1 tahun $60 (paket bulanan/tahunan sengaja diturunkan dari usulan awal agar lebih murah per hari daripada paket mingguan). Tanpa voucher: 5 giliran gratis per hari. Dengan voucher: batas wajar 150 giliran per hari (`TURNS_PER_DAY_PAID`).

Hanya nomor seluler Timor-Leste (`+670 7xxxxxxx`) yang bisa masuk.

## Cara kerja

- `public/` — antarmuka (suara masuk/keluar lewat Web Speech API di browser, gratis). Mode tanpa tangan: tutor bicara, lalu otomatis mendengarkan. Spasi = tombol bicara.
- `lib/tutor.js` — memanggil Claude dengan keluaran terstruktur (`reply`, `correction`, `explanation`, `level`). Model default `claude-opus-5-5`; ganti lewat `TUTOR_MODEL` (mis. `claude-haiku-5-5` untuk menekan biaya per menit).
- `lib/offline.js` — tutor skrip tanpa AI untuk demo.
- `lib/db.js` — penyimpanan JSON (`data/db.json`): pengguna, voucher, jatah harian.

## Belum siap produksi (jujur)

1. **Verifikasi nomor** memakai PIN saja; perlu OTP SMS agar satu orang = satu akun.
2. **Tetun**: belum ada pengenalan suara/suara Tetun di browser (dibacakan dengan suara Portugis; input mengetik). Teks antarmuka Tetun perlu ditinjau penutur asli. Kualitas Tetun dari AI perlu diuji.
3. **Penyimpanan** JSON berkas cocok untuk uji coba; ganti database sungguhan sebelum banyak pengguna.
4. **Suara Korea/Jepang/Portugis** bergantung pada suara yang ada di HP siswa; di HP murah bisa tidak ada.
5. **Izin**: cek aturan Banco Central de Timor-Leste soal nilai tersimpan/voucher, dan periksa nama "Lafex" agar tidak bentrok merek.
6. Belum diuji dengan kunci API sungguhan di lingkungan ini; jalur AI diuji dengan server palsu (`test/ai.test.js`).

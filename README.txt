APLIKASI KAJIAN TEMA & SUBTEMA AL-QUR'AN - DENGAN ADMIN

FITUR PUBLIK
- Dashboard tema utama dan statistik ayat.
- Detail tema dan subtema.
- Pencarian kata/frasa pada teks Arab dan terjemahan.
- Ekspor pemetaan ke Excel.

FITUR ADMIN
- Login admin.
- Tambah, edit, dan hapus tema utama.
- Tambah, edit, dan hapus subtema.
- Atur kata kunci subtema; saat disimpan, kandidat pemetaan otomatis untuk subtema tersebut dihitung ulang.
- Cari ayat berdasarkan kata/frasa, nama surah, atau nomor referensi (mis. 2:255).
- Tambah pemetaan manual dan hapus pemetaan yang tidak sesuai.
- Data admin disimpan di tema_alquran.sqlite3 dan tetap ada setelah aplikasi direstart.

INSTALASI WINDOWS / LARAGON
1. Ekstrak folder tema_alquran_app ke D:\laragon\www\tema_alquran_app.
2. Pastikan alquran_terjemahan.xlsx berada di folder yang sama dengan app.py.
3. Buka terminal/CMD:
   cd /d D:\laragon\www\tema_alquran_app
   py -m venv venv
   venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
4. Sebelum menjalankan, atur password admin dan secret key di terminal yang sama:
   set ADMIN_USERNAME=admin
   set ADMIN_PASSWORD=GANTI_DENGAN_PASSWORD_KUAT
   set FLASK_SECRET_KEY=GANTI_DENGAN_SECRET_RANDOM_PANJANG
5. Jalankan:
   python app.py
6. Buka http://127.0.0.1:5000

LOGIN ADMIN
- Buka http://127.0.0.1:5000/admin/login
- Username default: admin (dapat diubah melalui ADMIN_USERNAME).
- Password default jika ADMIN_PASSWORD belum diatur: admin123. WAJIB ganti sebelum dipakai di jaringan bersama atau internet.
- Password dan secret key dari perintah set hanya berlaku pada jendela CMD tersebut. Ulangi jika membuka terminal baru.

AKSES DARI HP DI JARINGAN WIFI/LAN
- Jalankan aplikasi pada komputer.
- Cari IPv4 komputer dengan perintah ipconfig.
- Buka http://IP-KOMPUTER:5000 dari HP yang berada di Wi-Fi yang sama.
- Izinkan Python pada Windows Firewall jika diminta. Jangan publikasikan aplikasi ke internet tanpa HTTPS dan pengamanan tambahan.

DATABASE DAN BACKUP
- tema_alquran.sqlite3 dibuat otomatis saat aplikasi pertama dijalankan.
- Backup file tersebut untuk menyimpan perubahan tema, subtema, kata kunci, dan pemetaan manual.
- Workbook sumber tidak dimodifikasi.

CATATAN METODOLOGI
Pemetaan otomatis berbasis kata/frasa hanya kandidat awal. Pencocokan kata tidak selalu memahami konteks, sinonim, negasi, atau maksud ayat. Hasil perlu ditinjau; aplikasi bukan pengganti tafsir atau kajian ilmiah. Satu ayat dapat dipetakan ke beberapa subtema.

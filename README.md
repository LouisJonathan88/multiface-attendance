# Multi Face Recognition Based Attendance System On An Edge Computing Platform

Sistem presensi yang mengenali **beberapa wajah sekaligus** dalam satu frame kamera dan berjalan di perangkat edge (**Raspberry Pi 5**). Proyek ini dibuat sebagai tugas akhir (skripsi).

## Cara Kerja

### Registrasi

1. Pengguna memasukkan nomor identitas.
2. Kamera merekam citra wajah (210 citra).
3. **MTCNN** mendeteksi wajah dan titik landmark.
4. Pra-pemrosesan: potong (crop), sejajarkan (alignment), dan ubah ukuran menjadi 160x160.
5. **FaceNet** mengekstrak embedding 512 dimensi untuk setiap citra.
6. Embedding dirata-rata menjadi satu embedding referensi per pengguna.
7. Data dikirim lewat REST API ke server Flask dan disimpan di MySQL.

### Presensi

1. Sesi presensi diaktifkan dan kamera menangkap gambar secara real-time.
2. MTCNN mendeteksi **beberapa wajah** dalam satu frame.
3. Setiap wajah diproses dengan pra-pemrosesan yang sama, lalu FaceNet mengekstrak embedding.
4. **Cosine similarity** membandingkan embedding dengan seluruh embedding referensi.
5. Jika nilainya melewati ambang batas (threshold), wajah dikenali, lalu menyimpan presensi.
6. Jika tidak melewati ambang batas, wajah ditandai **UNKNOWN**.

## Arsitektur

Sistem terdiri dari tiga lapisan:

- **Edge layer:** Raspberry Pi 5 dan webcam yang menjalankan deteksi, pra-pemrosesan, ekstraksi fitur, dan pencocokan identitas.
- **Server layer:** backend Flask dengan REST API dan basis data MySQL.
- **Application layer:** antarmuka untuk registrasi dan presensi.

## Teknologi

- **Bahasa:** Python
- **Deteksi wajah:** MTCNN
- **Ekstraksi fitur:** FaceNet (InceptionResnetV1, pra-latih VGGFace2) dengan PyTorch
- **Pencocokan:** Cosine similarity
- **Pengolahan citra:** OpenCV
- **Backend:** Flask, MySQL, REST API
- **Perangkat keras:** Raspberry Pi 5, webcam

## Struktur Repositori

- `backend/`: server Flask (REST API dan akses basis data)
- `registrasi-absensi/`: aplikasi sisi edge untuk registrasi dan presensi

## Cara Menjalankan

1. Clone repositori:

   ```bash
   git clone https://github.com/LouisJonathan88/multiface-attendance.git
   cd multiface-attendance
   Salin `.env.example` menjadi `.env`, lalu isi `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, dan `DB_NAME` sesuai MySQL Anda, dan isi `SERVER_URL`.
   ```

2. **Siapkan database.** Buat database kosong bernama `presensi_wajah` (charset `utf8mb4`), lalu impor struktur tabelnya:

   ```bash
   mysql -u root -p presensi_wajah < backend/schema.sql
   ```

   Atau gunakan menu **Import** di phpMyAdmin. Skema berisi tiga tabel: `user` (data pengguna), `embedding` (embedding wajah referensi), dan `presensi` (catatan kehadiran).

3. **Jalankan backend:**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

   ```bash
   python app.py
   ```

4. **Jalankan program edge** (di terminal terpisah):
   ```bash
   cd registrasi-absensi
   ```
   ```bash
   python main.py
   ```

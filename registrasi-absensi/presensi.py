import os
os.environ["QT_QPA_PLATFORM"] = "xcb"

import cv2
import numpy as np
import torch
import threading
import time
from datetime import datetime
from math import atan2, degrees
from facenet_pytorch import InceptionResnetV1, MTCNN
from api_client import ApiClient
import os

class Presensi:
    """Class untuk presensi realtime dengan pengukuran waktu untuk BAB 4."""

    img_size  = 160
    threshold = 0.55
    log_file  = "log_waktu_presensi.txt"

    def __init__(self):
        self.device        = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_facenet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        self.mtcnn         = MTCNN(keep_all=True, device=self.device)
        self.api           = ApiClient()
        self.cache_nama    = {}
        self.data_waktu    = {}  # key: jumlah_wajah, value: list waktu total (ms)
        print(f"Device: {self.device}")

    # ════════════════════════════════
    #  FORMAT VEKTOR
    # ════════════════════════════════

    def format_vektor(self, vector: np.ndarray, n_awal: int = 5) -> str:
        awal  = ", ".join(f"{v:.5f}" for v in vector[:n_awal])
        akhir = f"{vector[-1]:.5f}"
        return f"[ {awal}, ..., {akhir} ]"
    
    # ════════════════════════════════
    #  CATAT LOG (FORMAT SKRIPSI)
    # ════════════════════════════════
    def catat_log_waktu(self, jumlah_wajah: int, waktu_detik: float, hasil_wajah: list) -> None:
        """Format tabel presensi khusus untuk lampiran Bab 4."""
        file_exists = os.path.exists(self.log_file)
        percobaan = 1
        
        # Baca file untuk menentukan ini percobaan ke berapa
        if file_exists:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Menghitung baris data yang ada angka percobaannya
                    if "|" in line and "Percobaan" not in line and "-" not in line:
                        percobaan += 1

        with open(self.log_file, 'a', encoding='utf-8') as f:
            # Tulis header tabel HANYA pada percobaan ke-1
            if percobaan == 1:
                f.write(f"{'Percobaan':<10} | {'Wajah Terdeteksi':<17} | {'Waktu (detik)':<14} | {'Similarity':<10} | {'Status'}\n")
                f.write("-" * 80 + "\n")
            
            # Jika ada multi-wajah dalam 1 frame, gabungkan datanya (misal: "0.76, 0.81")
            sims = ", ".join([f"{h['similarity']:.4f}" for h in hasil_wajah])
            statuses = ", ".join([h['keputusan'] for h in hasil_wajah])
            
            f.write(f"{percobaan:<10} | {jumlah_wajah:<17} | {waktu_detik:<14.2f} | {sims:<10} | {statuses}\n")

    # ════════════════════════════════
    #  SIMPAN RINGKASAN AKHIR
    # ════════════════════════════════

    def simpan_ringkasan(self) -> None:
        """Simpan ringkasan rata-rata waktu per jumlah wajah ke log file."""
        if not self.data_waktu:
            return

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write("=" * 65 + "\n")
            f.write("RINGKASAN PENGUJIAN — SIAP UNTUK TABEL BAB 4\n")
            f.write("=" * 65 + "\n")
            f.write(f"{'Jumlah Wajah':<15} {'Sample':<10} "
                    f"{'Rata-rata (ms)':<17} {'Min (ms)':<12} {'Maks (ms)'}\n")
            f.write("-" * 65 + "\n")

            for jml in sorted(self.data_waktu.keys()):
                data     = self.data_waktu[jml]
                rata     = np.mean(data)
                minimum  = np.min(data)
                maksimum = np.max(data)
                f.write(f"{jml:<15} {len(data):<10} "
                        f"{rata:<17.1f} {minimum:<12.1f} {maksimum:.1f}\n")

            f.write("=" * 65 + "\n")

        print("\n" + "=" * 65)
        print("RINGKASAN PENGUJIAN — SIAP UNTUK TABEL BAB 4")
        print("=" * 65)
        print(f"{'Jumlah Wajah':<15} {'Sample':<10} "
              f"{'Rata-rata (ms)':<17} {'Min (ms)':<12} {'Maks (ms)'}")
        print("-" * 65)
        for jml in sorted(self.data_waktu.keys()):
            data     = self.data_waktu[jml]
            rata     = np.mean(data)
            minimum  = np.min(data)
            maksimum = np.max(data)
            print(f"{jml:<15} {len(data):<10} "
                  f"{rata:<17.1f} {minimum:<12.1f} {maksimum:.1f}")
        print("=" * 65)
        print(f"\nLog lengkap tersimpan di: {self.log_file}")

    # ════════════════════════════════
    #  SIMPAN PRESENSI ASYNC
    # ════════════════════════════════

    def simpan_presensi_async(self, nomor_identitas: str) -> None:
        threading.Thread(
            target=self.api.simpan_presensi,
            args=(nomor_identitas,),
            daemon=True
        ).start()

    # ════════════════════════════════
    #  SEJAJARKAN WAJAH
    # ════════════════════════════════

    def sejajarkan_wajah(self, gambar, keypoints) -> np.ndarray:
        mata_kiri  = (int(keypoints['left_eye'][0]),  int(keypoints['left_eye'][1]))
        mata_kanan = (int(keypoints['right_eye'][0]), int(keypoints['right_eye'][1]))

        sudut = degrees(atan2(mata_kanan[1] - mata_kiri[1], mata_kanan[0] - mata_kiri[0]))

        if sudut == 0:
            return gambar

        pusat_mata = ((mata_kiri[0] + mata_kanan[0]) // 2, (mata_kiri[1] + mata_kanan[1]) // 2)
        matriks    = cv2.getRotationMatrix2D(pusat_mata, sudut, 1)

        return cv2.warpAffine(gambar, matriks,
                              (gambar.shape[1], gambar.shape[0]),
                              flags=cv2.INTER_CUBIC)

    # ════════════════════════════════
    #  HITUNG COSINE SIMILARITY
    # ════════════════════════════════

    def hitung_jarak_cosine(self, embedding_a, embedding_b) -> float:
        embedding_a = embedding_a / np.linalg.norm(embedding_a)
        embedding_b = embedding_b / np.linalg.norm(embedding_b)
        return float(np.dot(embedding_a, embedding_b))

    # ════════════════════════════════
    #  AMBIL EMBEDDING
    # ════════════════════════════════

    def ambil_embedding(self, gambar_wajah) -> np.ndarray:
        img_norm   = (gambar_wajah / 255.0 - 0.5) * 2.0
        img_tensor = torch.tensor(
            img_norm.transpose(2, 0, 1),
            dtype=torch.float32
        ).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.model_facenet(img_tensor)

        return embedding.cpu().numpy().flatten()

    # ════════════════════════════════
    #  KENALI WAJAH
    # ════════════════════════════════

    def kenali_wajah(self, embedding, kamus_embedding) -> tuple:
        kemiripan_maks      = -1.0
        cocok               = "UNKNOWN"
        embedding_ref_cocok = None

        for nomor_identitas, emb_db in kamus_embedding.items():
            kemiripan = self.hitung_jarak_cosine(embedding, emb_db)

            if kemiripan > kemiripan_maks:
                kemiripan_maks      = kemiripan
                embedding_ref_cocok = emb_db
                cocok               = nomor_identitas if kemiripan >= self.threshold else "UNKNOWN"

        return cocok, kemiripan_maks, embedding_ref_cocok

    # ════════════════════════════════
    #  KENALI SATU WAJAH (MURNI PROSES AI)
    # ════════════════════════════════
    def kenali_satu_wajah(self, frame, box, mark, kamus_embedding) -> dict:
        """Deteksi, ekstraksi, dan pencocokan satu wajah — murni proses AI tanpa I/O jaringan."""
        x1 = max(0, int(box[0]))
        y1 = max(0, int(box[1]))
        x2 = min(frame.shape[1], int(box[2]))
        y2 = min(frame.shape[0], int(box[3]))

        potongan = frame[y1:y2, x1:x2]
        if potongan.size == 0:
            return None

        keypoints = {
            'left_eye':  tuple(mark[0]),
            'right_eye': tuple(mark[1]),
        }

        wajah_sejajar = self.sejajarkan_wajah(potongan, keypoints)
        wajah_resize  = cv2.resize(wajah_sejajar, (self.img_size, self.img_size))
        embedding     = self.ambil_embedding(wajah_resize)
        nomor_identitas, similarity, emb_ref = self.kenali_wajah(embedding, kamus_embedding)

        return {
            "box"             : (x1, y1, x2, y2),
            "nomor_identitas" : nomor_identitas,
            "similarity"      : similarity,
            "keputusan"       : "DIKENALI" if nomor_identitas != "UNKNOWN" else "UNKNOWN",
        }

    # ════════════════════════════════
    #  PASCA-PENGENALAN (DI LUAR CAKUPAN WAKTU)
    # ════════════════════════════════
    def proses_pasca_pengenalan(self, hasil: dict, presensi_sesi_ini) -> dict:
        """Ambil nama, simpan presensi, dan tandai log — tidak termasuk pengukuran waktu AI."""
        nomor_identitas = hasil["nomor_identitas"]
        baru_absen      = False

        if nomor_identitas != "UNKNOWN":
            if nomor_identitas not in self.cache_nama:
                self.cache_nama[nomor_identitas] = self.api.ambil_nama(nomor_identitas)

            if nomor_identitas not in presensi_sesi_ini:
                self.simpan_presensi_async(nomor_identitas)
                presensi_sesi_ini.add(nomor_identitas)

            if nomor_identitas not in self.wajah_tercatat_log:
                self.wajah_tercatat_log.add(nomor_identitas)
                baru_absen = True

        hasil["nama"]       = self.cache_nama.get(nomor_identitas, "")
        hasil["baru_absen"] = baru_absen
        return hasil

    # ════════════════════════════════
    #  TAMPILKAN OVERLAY
    # ════════════════════════════════
    def tampilkan_overlay(self, frame, hasil_wajah: list, fps: float) -> None:
        """Tampilkan bounding box, identitas, dan FPS di frame (waktu disembunyikan)."""
        cv2.putText(frame, f"FPS: {fps:.1f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"Wajah: {len(hasil_wajah)}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
        for hasil in hasil_wajah:
            x1, y1, x2, y2 = hasil["box"]
            warna = (0, 255, 0) if hasil["keputusan"] == "DIKENALI" else (0, 0, 255)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), warna, 2)
            cv2.putText(frame, f"No. Identitas: {hasil['nomor_identitas']}",
                        (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, warna, 2)
            
            if hasil["keputusan"] == "DIKENALI":
                cv2.putText(frame, f"Nama: {hasil['nama']}",
                            (x1, y2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, warna, 2)
                cv2.putText(frame, f"Similarity: {hasil['similarity']:.4f}",
                            (x1, y2 + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, warna, 2)
                # Teks waktu yang sebelumnya ada di sini sudah dihapus
            else:
                cv2.putText(frame, "UNKNOWN",
                            (x1, y2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, warna, 2)


    # ════════════════════════════════
    #  MULAI PRESENSI
    # ════════════════════════════════
    def mulai_presensi(self) -> None:
        print("\n" + "=" * 40)
        print("        PRESENSI REALTIME")
        print("=" * 40)
        
        self.wajah_tercatat_log = set() 
        window_name = "PRESENSI REALTIME" # Inisialisasi nama window agar seragam
        
        kamus_embedding = self.api.muat_semua_embedding()
        if not kamus_embedding:
            print("Tidak ada embedding di database.")
            return
            
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Kamera tidak tersedia.")
            return
            
        # =========================
        # RESOLUSI KAMERA
        # =========================
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # =========================
        # FULLSCREEN WINDOW
        # =========================
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        print("Kamera aktif — tekan 'q' untuk keluar\n")
        
        presensi_sesi_ini = self.api.ambil_nomor_identitas_presensi_hari_ini()
        prev_frame_time = time.perf_counter()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret: continue
                
                now = time.perf_counter()
                fps = 1.0 / (now - prev_frame_time) if (now - prev_frame_time) > 0 else 0
                prev_frame_time = now
                
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # ==========================================
                # START TIMER: Deteksi (MTCNN) + Pengenalan (FaceNet)
                # ==========================================
                t_deteksi_pengenalan_mulai = time.perf_counter()
                
                boxes, _, marks = self.mtcnn.detect(rgb, landmarks=True)
                hasil_wajah = []
                
                if boxes is not None:
                    for box, mark in zip(boxes, marks):
                        try:
                            hasil = self.kenali_satu_wajah(
                                frame, box, mark, kamus_embedding
                            )
                            if hasil:
                                hasil_wajah.append(hasil)
                        except Exception as error:
                            print(f"Error: {error}")

                    waktu_total_detik = time.perf_counter() - t_deteksi_pengenalan_mulai

                    for hasil in hasil_wajah:
                        self.proses_pasca_pengenalan(hasil, presensi_sesi_ini)

                    ada_presensi_baru = any(h.get("baru_absen", False) for h in hasil_wajah)
                    
                    if hasil_wajah and ada_presensi_baru:
                        self.catat_log_waktu(
                            jumlah_wajah = len(hasil_wajah),
                            waktu_detik  = waktu_total_detik,
                            hasil_wajah  = hasil_wajah
                        )
                        print(f"\n[SUKSES] Pengujian ke log. Waktu: {waktu_total_detik:.2f} detik")
                        
                # Panggil overlay
                self.tampilkan_overlay(frame, hasil_wajah, fps)
                
                # Gunakan variabel window_name yang konsisten
                cv2.imshow(window_name, frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        finally:
            cap.release()
            cv2.destroyAllWindows()
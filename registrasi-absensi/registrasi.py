import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
import time
import shutil
import cv2
from api_client import ApiClient


class Registrasi:
    """Class untuk menangani proses registrasi pengguna."""

    dir_registrasi     = "registrasi"
    jarak_list         = ["1m", "2m"]
    ekspresi           = ["Tanpa Senyum", "Senyum", "Senyum Gigi"]
    total_per_ekspresi = 35
    fps_rekam          = 5
    countdown_jarak    = 15
    countdown_ekspresi = 3

    def __init__(self):
        self.nomor_identitas = None
        self.nama            = None
        self.dibatalkan      = False
        self.api             = ApiClient()
        
        # Inisialisasi nama window yang seragam
        self.window_name     = "REGISTRASI WAJAH"

    # ════════════════════════════════
    #  INPUT DATA
    # ════════════════════════════════

    def masukkan_data(self) -> tuple:
        """Input dan validasi nomor identitas dan nama pengguna."""
        while True:
            nomor_identitas = input("Nomor Identitas : ").strip()
            if not nomor_identitas:
                print("Nomor identitas tidak boleh kosong")
                continue
            if self.api.cek_nomor_identitas_terdaftar(nomor_identitas):
                print(f"Nomor identitas {nomor_identitas} sudah terdaftar. Registrasi dibatalkan.")
                return None, None
            break

        while True:
            nama = input("Nama            : ").strip()
            if nama:
                break
            print("Nama tidak boleh kosong")

        self.nomor_identitas = nomor_identitas
        self.nama            = nama
        return nomor_identitas, nama

    # ════════════════════════════════
    #  OVERLAY TEKS
    # ════════════════════════════════

    def tampilkan_teks(self, frame, baris: list) -> None:
        """Tampilkan teks overlay di frame kamera beserta header judul."""
        # Menampilkan Judul Statis di bagian atas frame
        cv2.putText(frame, "REGISTRASI WAJAH", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
        
        # Menampilkan Garis Pembatas Horizontal di bawah judul
        cv2.line(frame, (0, 55), (frame.shape[1], 55), (0, 0, 0), 1)

        # Koordinat Y dimulai dari 90 agar teks informasi di bawahnya tidak menabrak header
        y = 90
        for teks, warna, skala in baris:
            cv2.putText(frame, teks, (30, y),
                        cv2.FONT_HERSHEY_SIMPLEX, skala, warna, 2)
            y += int(skala * 55)

    # ════════════════════════════════
    #  COUNTDOWN
    # ════════════════════════════════

    def hitung_mundur_jarak(self, cap, jarak: str, detik: int) -> bool:
        """Tampilkan countdown jarak di frame kamera."""
        for i in range(detik, 0, -1):
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            self.tampilkan_teks(frame, [
                (f"Berdiri pada jarak {jarak}", (0, 0, 255), 1.0),
                (f"Mulai dalam {i} detik...",   (0, 0, 255), 1.0),
                ("Tekan 'q' untuk batal",        (255, 255, 0), 0.6),
            ])
            cv2.imshow(self.window_name, frame)
            if cv2.waitKey(1000) & 0xFF == ord('q'):
                return False
        return True

    def hitung_mundur_ekspresi(self, cap, label: str, detik: int) -> bool:
        """Tampilkan countdown ekspresi di frame kamera."""
        for i in range(detik, 0, -1):
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            self.tampilkan_teks(frame, [
                (f"Ekspresi: {label}",        (0, 255, 0),   1.0),
                (f"Mulai dalam {i} detik...", (0, 0, 255),   1.0),
                ("Tekan 'q' untuk batal",      (255, 255, 0), 0.6),
            ])
            cv2.imshow(self.window_name, frame)
            if cv2.waitKey(1000) & 0xFF == ord('q'):
                return False
        return True

    # ════════════════════════════════
    #  OVERLAY CAPTURE
    # ════════════════════════════════

    def tampilkan_progres(self, frame, label: str, count: int, target: int, jarak: str) -> None:
        """Tampilkan progress pengambilan foto di frame kamera."""
        self.tampilkan_teks(frame, [
            (f"Ekspresi : {label}",          (0, 255, 0),   0.9),
            (f"Captured : {count}/{target}", (0, 255, 0),   0.9),
            (f"Jarak    : {jarak}",          (0, 255, 0),   0.9),
            ("Tekan 'q' untuk batal",         (255, 255, 0), 0.6),
        ])

    # ════════════════════════════════
    #  REKAM WAJAH
    # ════════════════════════════════

    def rekam_wajah(self, nomor_identitas: str, nama: str) -> bool:
        base_folder = os.path.join(
            self.dir_registrasi, f"{nomor_identitas}_{nama.replace(' ', '')}"
        )
        os.makedirs(base_folder, exist_ok=True)

        interval        = 1 / self.fps_rekam
        self.dibatalkan = False

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Kamera tidak tersedia")
            shutil.rmtree(base_folder, ignore_errors=True)
            return False

        # =========================
        # RESOLUSI KAMERA
        # =========================
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        try:
            for jarak in self.jarak_list:
                jarak_folder = os.path.join(base_folder, jarak)
                os.makedirs(jarak_folder, exist_ok=True)

                lanjut = self.hitung_mundur_jarak(cap, jarak, self.countdown_jarak)
                if not lanjut:
                    self.dibatalkan = True
                    break

                count = 0

                for label in self.ekspresi:
                    lanjut = self.hitung_mundur_ekspresi(cap, label, self.countdown_ekspresi)
                    if not lanjut:
                        self.dibatalkan = True
                        break

                    ekspresi_count = 0
                    last_time      = time.time()

                    while ekspresi_count < self.total_per_ekspresi:
                        ret, frame = cap.read()
                        if not ret:
                            time.sleep(0.01)
                            continue

                        now = time.time()
                        if now - last_time >= interval:
                            count          += 1
                            ekspresi_count += 1
                            cv2.imwrite(
                                os.path.join(jarak_folder, f"img_{count:03d}.jpg"),
                                frame
                            )
                            last_time = now

                        self.tampilkan_progres(frame, label, ekspresi_count, self.total_per_ekspresi, jarak)
                        cv2.imshow(self.window_name, frame)

                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.dibatalkan = True
                            break

                    print(f"{label} selesai ({ekspresi_count} foto)")

                    ret, frame = cap.read()
                    if ret:
                        self.tampilkan_progres(frame, label, ekspresi_count, self.total_per_ekspresi, jarak)
                        cv2.imshow(self.window_name, frame)
                        cv2.waitKey(700)

                    if self.dibatalkan:
                        break

                if self.dibatalkan:
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        if self.dibatalkan:
            shutil.rmtree(base_folder, ignore_errors=True)
            print("\nRegistrasi dibatalkan, folder dihapus")
            return False

        print("\nSemua foto berhasil diambil")
        return True


if __name__ == "__main__":
    registrasi = Registrasi()
    nomor_identitas, nama = registrasi.masukkan_data()
    if nomor_identitas is None:
        exit()
    registrasi.rekam_wajah(nomor_identitas, nama)
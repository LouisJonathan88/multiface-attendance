import os
import sys
from registrasi import Registrasi
from preprocessing import Preprocessing
from ekstraksi_fitur import EkstraksiWajah
from presensi import Presensi
from api_client import ApiClient


class MainApp:
    """Class utama untuk mengatur seluruh alur sistem presensi wajah."""

    def __init__(self):
        self.api            = ApiClient()
        self.registrasi     = Registrasi()
        self.preprocessing  = Preprocessing()
        self.ekstraksi      = EkstraksiWajah()
        self.presensi       = Presensi()

    # ════════════════════════════════
    #  HELPER
    # ════════════════════════════════

    def bersihkan_layar(self) -> None:
        """Bersihkan layar terminal."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def tampilkan_header(self, judul: str) -> None:
        """Tampilkan header dengan judul."""
        print("\n" + "=" * 40)
        print(f"  {judul}")
        print("=" * 40)

    # ════════════════════════════════
    #  ALUR REGISTRASI
    # ════════════════════════════════

    def alur_registrasi(self) -> None:
        """Jalankan alur proses registrasi pengguna."""
        self.tampilkan_header("REGISTRASI PENGGUNA")

        # Step 1 — Input data
        nomor_identitas, nama = self.registrasi.masukkan_data()
        if nomor_identitas is None:
            return

        # Step 2 — Konfirmasi data
        print(f"\nData yang akan didaftarkan:")
        print(f"   Nomor Identitas : {nomor_identitas}")
        print(f"   Nama            : {nama}")
        print()
        print("  [1] Rekam wajah")
        print("  [2] Edit data")
        print("  [3] Batal")

        while True:
            pilihan = input("\nPilihan: ").strip()
            if pilihan == "1":
                break
            elif pilihan == "2":
                self.alur_registrasi()
                return
            elif pilihan == "3":
                print("Registrasi dibatalkan")
                return
            else:
                print("Pilihan tidak valid")

        # Step 3 — Rekam wajah
        selesai = self.registrasi.rekam_wajah(nomor_identitas, nama)
        if not selesai:
            return

        folder_name = f"{nomor_identitas}_{nama.replace(' ', '')}"

        # Step 4 — Preprocessing
        print("Memproses wajah...")
        self.preprocessing.proses_pengguna(folder_name)

        # Step 5 — Simpan pengguna
        self.api.simpan_pengguna(nomor_identitas, nama)

        # Step 6 — Ekstraksi embedding
        sukses = self.ekstraksi.ekstrak_dan_simpan(folder_name)

        # Step 7 — Hasil
        if sukses:
            print(f"Registrasi {nama} ({nomor_identitas}) berhasil")
        else:
            print(f"Registrasi {nama} ({nomor_identitas}) selesai, tapi embedding gagal dibuat")

    # ════════════════════════════════
    #  MENU UTAMA
    # ════════════════════════════════

    def tampilkan_menu(self) -> None:
        """Tampilkan dan jalankan menu utama."""
        while True:
            self.bersihkan_layar()
            self.tampilkan_header("SISTEM PRESENSI WAJAH")
            print("  [1] Registrasi Pengguna")
            print("  [2] Mulai Presensi")
            print("  [3] Keluar")

            pilihan = input("\nPilihan: ").strip()

            if pilihan == "1":
                self.alur_registrasi()
                input("\nTekan Enter untuk kembali ke menu...")

            elif pilihan == "2":
                self.presensi.mulai_presensi()
                input("\nTekan Enter untuk kembali ke menu...")

            elif pilihan == "3":
                self.bersihkan_layar()
                print("Sampai jumpa!")
                sys.exit(0)

            else:
                print("Pilihan tidak valid")
                input("Tekan Enter untuk mencoba lagi...")


if __name__ == "__main__":
    app = MainApp()
    app.tampilkan_menu()
import os
import numpy as np
import requests
from flask.cli import load_dotenv


class ApiClient:
    """Class untuk komunikasi API ke server/backend."""

    def __init__(self):
        load_dotenv()
        self.server_url = os.getenv("SERVER_URL", "http://localhost:5000")

    # ════════════════════════════════
    #  HELPER
    # ════════════════════════════════

    def _post(self, endpoint: str, data: dict) -> dict:
        """Helper untuk POST request ke server."""
        try:
            response = requests.post(
                f"{self.server_url}{endpoint}",
                json=data,
                timeout=10
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"Tidak dapat terhubung ke server: {self.server_url}")
            return {"error": "Connection error"}
        except requests.exceptions.Timeout:
            print(f"Request timeout ke server: {self.server_url}")
            return {"error": "Timeout"}
        except Exception as error:
            print(f"Error: {error}")
            return {"error": str(error)}

    def _get(self, endpoint: str) -> dict:
        """Helper untuk GET request ke server."""
        try:
            response = requests.get(
                f"{self.server_url}{endpoint}",
                timeout=10
            )
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"Tidak dapat terhubung ke server: {self.server_url}")
            return {"error": "Connection error"}
        except requests.exceptions.Timeout:
            print(f"Request timeout ke server: {self.server_url}")
            return {"error": "Timeout"}
        except Exception as error:
            print(f"Error: {error}")
            return {"error": str(error)}

    # ════════════════════════════════
    #  PENGGUNA
    # ════════════════════════════════

    def cek_nomor_identitas_terdaftar(self, nomor_identitas: str) -> bool:
        """Cek apakah nomor identitas sudah terdaftar di server."""
        result = self._get(f"/api/pengguna/{nomor_identitas}")
        if "error" in result:
            return False
        return result.get("terdaftar", False)

    def simpan_pengguna(self, nomor_identitas: str, nama: str) -> None:
        """Simpan data pengguna ke server."""
        result = self._post("/api/pengguna", {"nomor_identitas": nomor_identitas, "nama": nama})
        if "error" in result:
            print(f"Gagal simpan pengguna: {result['error']}")
        else:
            print(f"\nData pengguna tersimpan — Nomor Identitas: {nomor_identitas} | Nama: {nama}")

    def ambil_nama(self, nomor_identitas: str) -> str:
        """Ambil nama pengguna berdasarkan nomor identitas."""
        result = self._get(f"/api/pengguna/{nomor_identitas}")
        if "error" in result:
            return "UNKNOWN"
        return result.get("nama", "UNKNOWN")

    # ════════════════════════════════
    #  EMBEDDING
    # ════════════════════════════════

    def simpan_embedding(self, nomor_identitas: str, vector: np.ndarray) -> None:
        """Simpan embedding wajah ke server."""
        vector_hex = vector.astype(np.float32).tobytes().hex()
        result     = self._post("/api/embedding", {"nomor_identitas": nomor_identitas, "vector": vector_hex})
        if "error" in result:
            print(f"Gagal simpan embedding: {result['error']}")
        else:
            print(f"Embedding tersimpan — Nomor Identitas: {nomor_identitas}")

    def muat_semua_embedding(self) -> dict:
        """Ambil semua embedding dari server."""
        result = self._get("/api/embeddings")
        if "error" in result:
            print(f"Gagal muat embedding: {result['error']}")
            return {}
        embeddings = {}
        for nomor_identitas, vector_hex in result.items():
            vector = np.frombuffer(bytes.fromhex(vector_hex), dtype=np.float32)
            embeddings[str(nomor_identitas)] = vector
        return embeddings

    # ════════════════════════════════
    #  PRESENSI
    # ════════════════════════════════

    def simpan_presensi(self, nomor_identitas: str) -> None:
        """Simpan data presensi ke server."""
        result = self._post("/api/presensi", {"nomor_identitas": nomor_identitas})
        if "error" in result:
            print(f"Gagal simpan presensi: {result['error']}")
        else:
            print(f"Presensi tercatat — Nomor Identitas: {nomor_identitas}")

    def ambil_nomor_identitas_presensi_hari_ini(self) -> set:
        """Ambil nomor identitas yang sudah presensi hari ini."""
        result = self._get("/api/presensi/hari-ini")
        if "error" in result:
            print(f"Gagal muat presensi hari ini: {result['error']}")
            return set()
        return set(result.get("daftar_nomor_identitas", []))
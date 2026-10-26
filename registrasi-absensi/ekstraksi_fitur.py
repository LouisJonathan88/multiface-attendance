import os
import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1
from api_client import ApiClient


class EkstraksiWajah:
    """Class untuk ekstraksi embedding wajah menggunakan FaceNet."""

    dir_aligned = "faces_aligned"
    img_size    = 160

    def __init__(self):
        self.device         = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_facenet  = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        self.api             = ApiClient()

    # ════════════════════════════════
    #  AMBIL EMBEDDING
    # ════════════════════════════════

    def ambil_embedding(self, jalur_gambar: str) -> np.ndarray:
        """Ekstrak embedding dari satu gambar."""
        img = cv2.imread(jalur_gambar)
        if img is None:
            return None

        img      = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img      = cv2.resize(img, (self.img_size, self.img_size))
        img_norm = (img / 255.0 - 0.5) * 2.0

        img_tensor = torch.tensor(
            img_norm.transpose(2, 0, 1),
            dtype=torch.float32
        ).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.model_facenet(img_tensor)

        return embedding.cpu().numpy().flatten()

    # ════════════════════════════════
    #  PROSES EMBEDDING PENGGUNA
    # ════════════════════════════════

    def proses_embedding_pengguna(self, folder_pengguna: str) -> tuple:
        """Ekstrak semua embedding untuk satu pengguna."""
        nomor_identitas = folder_pengguna.split("_", 1)[0] if "_" in folder_pengguna else folder_pengguna
        jalur           = os.path.join(self.dir_aligned, folder_pengguna)

        semua_embedding = []

        for jarak in os.listdir(jalur):
            jalur_jarak = os.path.join(jalur, jarak)
            if not os.path.isdir(jalur_jarak):
                continue

            for nama_gambar in sorted(os.listdir(jalur_jarak)):
                if not nama_gambar.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                embedding = self.ambil_embedding(os.path.join(jalur_jarak, nama_gambar))
                if embedding is not None:
                    semua_embedding.append(embedding)

        if not semua_embedding:
            print(f"Tidak ada embedding valid untuk {folder_pengguna}")
            return nomor_identitas, None

        rata_embedding = np.mean(np.stack(semua_embedding), axis=0)

         # Tambahan sementara untuk keperluan dokumentasi BAB 4 — hapus setelah screenshot diambil
        awal  = ", ".join(f"{v:.5f}" for v in rata_embedding[:5])
        akhir = f"{rata_embedding[-1]:.5f}"
        print(f"Embedding rata-rata: [ {awal}, ..., {akhir} ]")
        # sampai ini
        
        return nomor_identitas, rata_embedding

    # ════════════════════════════════
    #  EKSTRAK DAN SIMPAN
    # ════════════════════════════════

    def ekstrak_dan_simpan(self, folder_pengguna: str) -> bool:
        """Ekstrak embedding lalu simpan ke server."""
        nomor_identitas, rata_embedding = self.proses_embedding_pengguna(folder_pengguna)
        if rata_embedding is None:
            return False
        self.api.simpan_embedding(nomor_identitas, rata_embedding)
        return True


if __name__ == "__main__":
    ekstraksi = EkstraksiWajah()
    ekstraksi.ekstrak_dan_simpan("10122362_Louis")
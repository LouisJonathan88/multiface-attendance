import os
import cv2
import numpy as np
import torch
from math import atan2, degrees
from facenet_pytorch import MTCNN


class Preprocessing:
    """Class untuk preprocessing wajah: deteksi, crop, alignment, dan resize."""

    dir_registrasi = "registrasi"
    dir_deteksi    = "deteksi"
    dir_crop       = "face_crop"
    dir_aligned    = "faces_aligned"
    dir_resized    = "faces_resized"  
    img_size       = 160

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.mtcnn  = MTCNN(keep_all=True, device=self.device)

    # ════════════════════════════════
    #  GAMBAR HASIL DETEKSI (BBOX + 5 LANDMARK)
    # ════════════════════════════════

    def gambar_deteksi(self, img: np.ndarray, box: np.ndarray, landmark: np.ndarray) -> np.ndarray:
        """Gambar bounding box dan 5 titik landmark di atas gambar asli (untuk visualisasi)."""
        hasil = img.copy()

        x1, y1, x2, y2 = box.astype(int)
        cv2.rectangle(hasil, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Urutan landmark MTCNN: mata kiri, mata kanan, hidung, mulut kiri, mulut kanan
        warna_titik = (0, 0, 255)
        for (px, py) in landmark:
            cv2.circle(hasil, (int(px), int(py)), 3, warna_titik, -1)

        return hasil

    # ════════════════════════════════
    #  SEJAJARKAN WAJAH
    # ════════════════════════════════

    def sejajarkan_wajah(self, image: np.ndarray, keypoints: dict) -> np.ndarray:
        """Rotasi wajah agar posisi mata sejajar horizontal."""
        left_eye  = (int(keypoints['left_eye'][0]),  int(keypoints['left_eye'][1]))
        right_eye = (int(keypoints['right_eye'][0]), int(keypoints['right_eye'][1]))

        angle = degrees(atan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0]))

        if angle == 0:
            return image

        eyes_center = ((left_eye[0] + right_eye[0]) // 2, (left_eye[1] + right_eye[1]) // 2)

        rotation_matrix = cv2.getRotationMatrix2D(eyes_center, angle, 1)
        return cv2.warpAffine(image, rotation_matrix,
                              (image.shape[1], image.shape[0]),
                              flags=cv2.INTER_CUBIC)

    # ════════════════════════════════
    #  DETEKSI WAJAH
    # ════════════════════════════════

    def deteksi_wajah(self, img: np.ndarray, nama_gambar: str) -> tuple:
        """Deteksi wajah (bbox + 5 landmark) dari gambar, tanpa crop."""
        rgb                 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        boxes, _, landmarks = self.mtcnn.detect(rgb, landmarks=True)

        if boxes is None:
            print(f"Tidak ada wajah terdeteksi: {nama_gambar}")
            return None, None

        return boxes[0], landmarks[0]

    # ════════════════════════════════
    #  POTONG WAJAH
    # ════════════════════════════════

    def potong_wajah(self, img: np.ndarray, box: np.ndarray, landmark: np.ndarray) -> tuple:
        """Crop wajah dari gambar berdasarkan bbox & landmark hasil deteksi."""
        x1 = max(0, int(box[0]))
        y1 = max(0, int(box[1]))
        x2 = min(img.shape[1], int(box[2]))
        y2 = min(img.shape[0], int(box[3]))

        face_crop = img[y1:y2, x1:x2]

        if face_crop.size == 0:
            return None, None
        keypoints = {
            'left_eye':  (landmark[0][0] - x1, landmark[0][1] - y1),
            'right_eye': (landmark[1][0] - x1, landmark[1][1] - y1),
        }
        return face_crop, keypoints

    # ════════════════════════════════
    #  PROSES ALIGNMENT
    # ════════════════════════════════

    def proses_wajah(self, face_crop: np.ndarray, keypoints: dict, nama_gambar: str) -> np.ndarray:
        """Alignment wajah dan resize ke img_size."""
        aligned     = self.sejajarkan_wajah(face_crop, keypoints)
        rgb_aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)

        boxes_aligned, _, _ = self.mtcnn.detect(rgb_aligned, landmarks=True)

        if boxes_aligned is not None:
            box  = boxes_aligned[0].astype(int)
            x1   = max(0, box[0])
            y1   = max(0, box[1])
            x2   = min(aligned.shape[1], box[2])
            y2   = min(aligned.shape[0], box[3])
            face_aligned = aligned[y1:y2, x1:x2]

            if face_aligned.size == 0:
                print(f"Alignment crop kosong: {nama_gambar}")
                return None
        else:
            face_aligned = aligned
        return face_aligned

    def resize_wajah(self, face_aligned: np.ndarray) -> np.ndarray:
        """Resize citra wajah yang sudah disejajarkan dan di-crop ulang ke img_size."""
        return cv2.resize(face_aligned, (self.img_size, self.img_size))

    # ════════════════════════════════
    #  PROSES SATU PENGGUNA
    # ════════════════════════════════

    def proses_pengguna(self, folder_pengguna: str) -> None:
        """Deteksi + crop + alignment + resize untuk satu pengguna."""
        jalur_pengguna = os.path.join(self.dir_registrasi, folder_pengguna)
        sukses = 0
        gagal  = 0

        for jarak in os.listdir(jalur_pengguna):
            jalur_jarak = os.path.join(jalur_pengguna, jarak)
            if not os.path.isdir(jalur_jarak):
                continue

            folder_deteksi = os.path.join(self.dir_deteksi, folder_pengguna, jarak)
            folder_crop    = os.path.join(self.dir_crop,    folder_pengguna, jarak)
            folder_aligned = os.path.join(self.dir_aligned, folder_pengguna, jarak)
            folder_resized = os.path.join(self.dir_resized, folder_pengguna, jarak)
            os.makedirs(folder_deteksi, exist_ok=True)
            os.makedirs(folder_crop,    exist_ok=True)
            os.makedirs(folder_aligned, exist_ok=True)
            os.makedirs(folder_resized, exist_ok=True)

            for nama_gambar in sorted(os.listdir(jalur_jarak)):
                if not nama_gambar.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                img = cv2.imread(os.path.join(jalur_jarak, nama_gambar))
                if img is None:
                    print(f"Gagal membaca: {nama_gambar}")
                    gagal += 1
                    continue

                # Step 1 — Deteksi wajah (bbox + 5 landmark)
                box, landmark = self.deteksi_wajah(img, nama_gambar)
                if box is None:
                    gagal += 1
                    continue

                # Step 2 — Simpan visualisasi hasil deteksi
                img_deteksi = self.gambar_deteksi(img, box, landmark)
                cv2.imwrite(
                    os.path.join(folder_deteksi, nama_gambar.replace("img", "deteksi")),
                    img_deteksi
                )

                # Step 3 — Crop wajah
                face_crop, keypoints = self.potong_wajah(img, box, landmark)
                if face_crop is None:
                    print(f"Crop kosong: {nama_gambar}")
                    gagal += 1
                    continue

                cv2.imwrite(os.path.join(folder_crop, nama_gambar.replace("img", "crop")), face_crop)

                # Step 4 — Alignment + crop ulang
                face_aligned = self.proses_wajah(face_crop, keypoints, nama_gambar)
                if face_aligned is None:
                    gagal += 1
                    continue

                cv2.imwrite(os.path.join(folder_aligned, nama_gambar.replace("img", "aligned")), face_aligned)

                # Step 5 — Resize final
                face_final = self.resize_wajah(face_aligned)
                cv2.imwrite(os.path.join(folder_resized, nama_gambar.replace("img", "resized")), face_final)
                sukses += 1

        print(f"Selesai — sukses: {sukses} | gagal: {gagal}")


if __name__ == "__main__":
    preprocessing = Preprocessing()
    preprocessing.proses_pengguna("")
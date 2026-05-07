# ## semoga fix

# from datetime import datetime
# import os
# import numpy as np
# from flask.cli import load_dotenv
# import mysql.connector
# from mysql.connector import pooling

# load_dotenv()

# DB_CONFIG = {
#     "host":     os.getenv("DB_HOST", "localhost"),
#     "port":     int(os.getenv("DB_PORT", 3306)),
#     "user":     os.getenv("DB_USER", "root"),
#     "password": os.getenv("DB_PASS", ""),
#     "database": os.getenv("DB_NAME", "absensi_fix_4"),
# }

# # ✅ CONNECTION POOL
# connection_pool = pooling.MySQLConnectionPool(
#     pool_name="mypool",
#     pool_size=5,
#     **DB_CONFIG
# )


# def get_conn():
#     conn = connection_pool.get_connection()
#     cursor = conn.cursor()
#     cursor.execute("SET time_zone = '+07:00';")
#     cursor.close()
#     return conn


# # ════════════════════════════════
# #  MAHASISWA
# # ════════════════════════════════

# def nim_sudah_terdaftar(nim: str) -> bool:
#     conn   = get_conn()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT 1 FROM mahasiswa WHERE nim = %s LIMIT 1", (int(nim),))
#         return cursor.fetchone() is not None
#     finally:
#         cursor.close()
#         conn.close()


# def simpan_mahasiswa(nim: str, nama: str) -> None:
#     conn   = get_conn()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("DELETE FROM mahasiswa WHERE nim = %s", (int(nim),))
#         cursor.execute(
#             "INSERT INTO mahasiswa (nim, nama) VALUES (%s, %s)",
#             (int(nim), nama)
#         )
#         conn.commit()
#         print(f"✅ Data mahasiswa tersimpan — NIM: {nim} | Nama: {nama}")
#     except mysql.connector.Error as e:
#         conn.rollback()
#         print(f"❌ Gagal simpan mahasiswa: {e}")
#     finally:
#         cursor.close()
#         conn.close()


# def get_nama(nim: str) -> str:
#     conn   = get_conn()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT nama FROM mahasiswa WHERE nim = %s LIMIT 1", (int(nim),))
#         result = cursor.fetchone()
#         return result[0] if result else "UNKNOWN"
#     finally:
#         cursor.close()
#         conn.close()


# # ════════════════════════════════
# #  EMBEDDING
# # ════════════════════════════════

# def simpan_embedding(nim: str, vector: np.ndarray) -> None:
#     """
#     Simpan atau update avg embedding mahasiswa ke tabel embedding.
#     Jika NIM sudah ada, embedding lama akan diganti (UPDATE).
#     """
#     conn   = get_conn()
#     cursor = conn.cursor()
#     try:
#         # Konversi numpy array → bytes untuk disimpan sebagai BLOB
#         vector_bytes = vector.astype(np.float32).tobytes()

#         # Gunakan REPLACE INTO agar otomatis update jika NIM sudah ada
#         cursor.execute(
#             "DELETE FROM embedding WHERE nim = %s",
#             (int(nim),)
#         )
#         cursor.execute(
#             "INSERT INTO embedding (nim, vector) VALUES (%s, %s)",
#             (int(nim), vector_bytes)
#         )
#         conn.commit()
#         print(f"✅ Embedding tersimpan — NIM: {nim}")
#     except mysql.connector.Error as e:
#         conn.rollback()
#         print(f"❌ Gagal simpan embedding: {e}")
#     finally:
#         cursor.close()
#         conn.close()


# def load_semua_embedding() -> dict:
#     """
#     Load semua embedding dari DB.
#     Return dict {nim_str: np.ndarray} siap dipakai untuk pencocokan wajah.
#     """
#     conn   = get_conn()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT nim, vector FROM embedding")
#         rows = cursor.fetchall()
#     finally:
#         cursor.close()
#         conn.close()

#     embeddings = {}
#     for nim, vector_bytes in rows:
#         # Konversi bytes → numpy array float32 dengan 512 dimensi
#         vector = np.frombuffer(vector_bytes, dtype=np.float32)
#         embeddings[str(nim)] = vector

#     print(f"📂 Loaded {len(embeddings)} embedding dari database")
#     return embeddings


# # ════════════════════════════════
# #  ABSENSI
# # ════════════════════════════════

# def sudah_absen_hari_ini(nim: str) -> bool:
#     conn   = get_conn()
#     cursor = conn.cursor()
#     try:
#         today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
#         today_end   = datetime.now().strftime("%Y-%m-%d 23:59:59")

#         cursor.execute(
#             """
#             SELECT 1 FROM absensi 
#             WHERE nim = %s 
#             AND waktu_absen BETWEEN %s AND %s
#             LIMIT 1
#             """,
#             (int(nim), today_start, today_end)
#         )
#         return cursor.fetchone() is not None
#     finally:
#         cursor.close()
#         conn.close()


# def simpan_absensi(nim: str) -> None:
#     if sudah_absen_hari_ini(nim):
#         return

#     now    = datetime.now()
#     conn   = get_conn()
#     cursor = conn.cursor()
#     try:
#         cursor.execute(
#             "INSERT INTO absensi (nim, waktu_absen, status) VALUES (%s, %s, 'Hadir')",
#             (int(nim), now)
#         )
#         conn.commit()

#         nama = get_nama(nim)
#         print(f"[ABSENSI] {now.strftime('%H:%M:%S')} | NIM: {nim} | {nama} | Hadir")

#     except mysql.connector.Error as e:
#         conn.rollback()
#         print(f"❌ Gagal simpan absensi: {e}")
#     finally:
#         cursor.close()
#         conn.close()


# # ════════════════════════════════
# #  KEHADIRAN
# # ════════════════════════════════

# def get_kehadiran(keyword: str = "", tanggal: str = "") -> list:
#     conn   = get_conn()
#     cursor = conn.cursor(dictionary=True)

#     try:
#         query = """
#             SELECT a.id, a.nim, m.nama, a.waktu_absen, a.status
#             FROM absensi a
#             JOIN mahasiswa m ON a.nim = m.nim
#             WHERE 1=1
#         """
#         params = []

#         if keyword:
#             query += " AND (a.nim LIKE %s OR m.nama LIKE %s)"
#             like = f"%{keyword}%"
#             params.extend([like, like])

#         if tanggal:
#             start = f"{tanggal} 00:00:00"
#             end   = f"{tanggal} 23:59:59"
#             query += " AND a.waktu_absen BETWEEN %s AND %s"
#             params.extend([start, end])

#         query += " ORDER BY a.waktu_absen DESC LIMIT 100"

#         cursor.execute(query, params)
#         rows = cursor.fetchall()

#     finally:
#         cursor.close()
#         conn.close()

#     for row in rows:
#         if isinstance(row["waktu_absen"], datetime):
#             row["waktu_absen"] = row["waktu_absen"].strftime("%Y-%m-%d %H:%M:%S")

#     return rows


from datetime import datetime
import os
import numpy as np
from flask.cli import load_dotenv
import mysql.connector
from mysql.connector import pooling

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "absensi_fix_4"),
}

# ✅ CONNECTION POOL
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    **DB_CONFIG
)


def get_conn():
    conn = connection_pool.get_connection()
    cursor = conn.cursor()
    cursor.execute("SET time_zone = '+07:00';")
    cursor.close()
    return conn


# ════════════════════════════════
#  MAHASISWA
# ════════════════════════════════

def nim_sudah_terdaftar(nim: str) -> bool:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM mahasiswa WHERE nim = %s LIMIT 1", (int(nim),))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def simpan_mahasiswa(nim: str, nama: str) -> None:
    """
    INSERT mahasiswa baru, atau UPDATE nama saja kalau NIM sudah ada.
    Tidak DELETE — absensi lama tetap aman.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        # cursor.execute(
        #     """
        #     INSERT INTO mahasiswa (nim, nama)
        #     VALUES (%s, %s)
        #     ON DUPLICATE KEY UPDATE nama = VALUES(nama)
        #     """,
        #     (int(nim), nama)
        # )

        cursor.execute("""
                INSERT INTO mahasiswa (nim, nama, waktu_registrasi)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    nama = VALUES(nama),
                    waktu_registrasi = NOW()
            """, (nim, nama))
        conn.commit()
        print(f"✅ Data mahasiswa tersimpan — NIM: {nim} | Nama: {nama}")
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ Gagal simpan mahasiswa: {e}")
    finally:
        cursor.close()
        conn.close()


def get_nama(nim: str) -> str:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT nama FROM mahasiswa WHERE nim = %s LIMIT 1", (int(nim),))
        result = cursor.fetchone()
        return result[0] if result else "UNKNOWN"
    finally:
        cursor.close()
        conn.close()


# ════════════════════════════════
#  EMBEDDING
# ════════════════════════════════

def simpan_embedding(nim: str, vector: np.ndarray) -> None:
    """
    INSERT embedding baru, atau UPDATE vector kalau NIM sudah ada.
    Otomatis mengganti embedding lama saat re-registrasi.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        vector_bytes = vector.astype(np.float32).tobytes()
        cursor.execute(
            """
            INSERT INTO embedding (nim, vector)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE vector = VALUES(vector)
            """,
            (int(nim), vector_bytes)
        )
        conn.commit()
        print(f"✅ Embedding tersimpan — NIM: {nim}")
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ Gagal simpan embedding: {e}")
    finally:
        cursor.close()
        conn.close()


def load_semua_embedding() -> dict:
    """
    Load semua embedding dari DB.
    Return dict {nim_str: np.ndarray} siap dipakai untuk pencocokan wajah.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT nim, vector FROM embedding")
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    embeddings = {}
    for nim, vector_bytes in rows:
        vector = np.frombuffer(vector_bytes, dtype=np.float32)
        embeddings[str(nim)] = vector

    print(f"📂 Loaded {len(embeddings)} embedding dari database")
    return embeddings


# ════════════════════════════════
#  ABSENSI
# ════════════════════════════════

def sudah_absen_hari_ini(nim: str) -> bool:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT 1 FROM absensi
            WHERE nim = %s
            AND DATE(waktu_absen) = CURDATE()
            LIMIT 1
            """,
            (int(nim),)
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def simpan_absensi(nim: str) -> None:
    if sudah_absen_hari_ini(nim):
        return

    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO absensi (nim, waktu_absen) VALUES (%s, NOW())",
            (int(nim),)
        )
        conn.commit()

        now  = datetime.now()
        nama = get_nama(nim)
        print(f"[ABSENSI] {now.strftime('%H:%M:%S')} | NIM: {nim} | {nama} | Hadir")

    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ Gagal simpan absensi: {e}")
    finally:
        cursor.close()
        conn.close()


# ════════════════════════════════
#  KEHADIRAN
# ════════════════════════════════

def get_kehadiran(keyword: str = "", tanggal: str = "") -> list:
    conn   = get_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            SELECT a.id, a.nim, m.nama, a.waktu_absen, a.status
            FROM absensi a
            JOIN mahasiswa m ON a.nim = m.nim
            WHERE 1=1
        """
        params = []

        if keyword:
            query += " AND (a.nim LIKE %s OR m.nama LIKE %s)"
            like = f"%{keyword}%"
            params.extend([like, like])

        if tanggal:
            query += " AND DATE(a.waktu_absen) = %s"
            params.append(tanggal)

        query += " ORDER BY a.waktu_absen DESC LIMIT 100"

        cursor.execute(query, params)
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    for row in rows:
        if isinstance(row["waktu_absen"], datetime):
            row["waktu_absen"] = row["waktu_absen"].strftime("%Y-%m-%d %H:%M:%S")

    return rows
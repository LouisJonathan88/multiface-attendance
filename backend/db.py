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
    "user":     os.getenv("DB_USER", "lj"),
    "password": os.getenv("DB_PASS", "LJ123"),
    "database": os.getenv("DB_NAME", "presensi_wajah"),
}

# CONNECTION POOL
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
#  PENGGUNA
# ════════════════════════════════

def nomor_identitas_sudah_terdaftar(nomor_identitas: str) -> bool:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM user WHERE nomor_identitas = %s LIMIT 1", (nomor_identitas,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def simpan_pengguna(nomor_identitas: str, nama: str) -> None:
    """
    INSERT pengguna baru, atau UPDATE nama saja kalau nomor identitas sudah ada.
    Tidak DELETE — presensi lama tetap aman.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
                INSERT INTO user (nomor_identitas, nama, waktu_registrasi)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    nama = VALUES(nama),
                    waktu_registrasi = NOW()
            """, (nomor_identitas, nama))
        conn.commit()
        print(f"Data pengguna tersimpan — Nomor Identitas: {nomor_identitas} | Nama: {nama}")
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"Gagal simpan pengguna: {e}")
    finally:
        cursor.close()
        conn.close()


def get_nama(nomor_identitas: str) -> str:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT nama FROM user WHERE nomor_identitas = %s LIMIT 1", (nomor_identitas,))
        result = cursor.fetchone()
        return result[0] if result else "UNKNOWN"
    finally:
        cursor.close()
        conn.close()


# ════════════════════════════════
#  EMBEDDING
# ════════════════════════════════

def simpan_embedding(nomor_identitas: str, vector: np.ndarray) -> None:
    """
    INSERT embedding baru, atau UPDATE vector kalau nomor identitas sudah ada.
    Otomatis mengganti embedding lama saat re-registrasi.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        vector_bytes = vector.astype(np.float32).tobytes()
        cursor.execute(
            """
            INSERT INTO embedding (nomor_identitas, face_embedding)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE face_embedding = VALUES(face_embedding)
            """,
            (nomor_identitas, vector_bytes)
        )
        conn.commit()
        print(f"Embedding tersimpan — Nomor Identitas: {nomor_identitas}")
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"Gagal simpan embedding: {e}")
    finally:
        cursor.close()
        conn.close()


def load_semua_embedding() -> dict:
    """
    Load semua embedding dari DB.
    Return dict {nomor_identitas_str: np.ndarray} siap dipakai untuk pencocokan wajah.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT nomor_identitas, face_embedding FROM embedding")
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    embeddings = {}
    for nomor_identitas, vector_bytes in rows:
        vector = np.frombuffer(vector_bytes, dtype=np.float32)
        embeddings[str(nomor_identitas)] = vector

    print(f"Loaded {len(embeddings)} embedding dari database")
    return embeddings


# ════════════════════════════════
#  PRESENSI
# ════════════════════════════════

def sudah_presensi_hari_ini(nomor_identitas: str) -> bool:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT 1 FROM presensi
            WHERE nomor_identitas = %s
            AND DATE(waktu_presensi) = CURDATE()
            LIMIT 1
            """,
            (nomor_identitas,)
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def simpan_presensi(nomor_identitas: str) -> None:
    if sudah_presensi_hari_ini(nomor_identitas):
        return

    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO presensi (nomor_identitas, waktu_presensi) VALUES (%s, NOW())",
            (nomor_identitas,)
        )
        conn.commit()

        now  = datetime.now()
        nama = get_nama(nomor_identitas)
        print(f"[PRESENSI] {now.strftime('%H:%M:%S')} | Nomor Identitas: {nomor_identitas} | {nama} | Hadir")

    except mysql.connector.Error as e:
        conn.rollback()
        print(f"Gagal simpan presensi: {e}")
    finally:
        cursor.close()
        conn.close()


def get_nomor_identitas_presensi_hari_ini() -> set:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT nomor_identitas FROM presensi
            WHERE DATE(waktu_presensi) = CURDATE()
            """
        )
        rows = cursor.fetchall()
        return {str(row[0]) for row in rows}
    finally:
        cursor.close()
        conn.close()


# ════════════════════════════════
#  KEHADIRAN
# ════════════════════════════════

def get_kehadiran(keyword: str = "", tanggal_dari: str = "", tanggal_sampai: str = "") -> list:
    conn   = get_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            SELECT a.nomor_identitas, m.nama, a.waktu_presensi, a.status
            FROM presensi a
            JOIN user m ON a.nomor_identitas = m.nomor_identitas
            WHERE 1=1
        """
        params = []

        if keyword:
            query += " AND (a.nomor_identitas LIKE %s OR m.nama LIKE %s)"
            like = f"%{keyword}%"
            params.extend([like, like])

        if tanggal_dari:
            query += " AND a.waktu_presensi >= %s"
            params.append(f"{tanggal_dari} 00:00:00")

        if tanggal_sampai:
            query += " AND a.waktu_presensi <= %s"
            params.append(f"{tanggal_sampai} 23:59:59")

        query += " ORDER BY a.waktu_presensi DESC"  # LIMIT dihapus agar bisa ditarik semua

        cursor.execute(query, params)
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    for row in rows:
        if isinstance(row["waktu_presensi"], datetime):
            row["waktu_presensi"] = row["waktu_presensi"].strftime("%Y-%m-%d %H:%M:%S")

    return rows
# # db.py — semua operasi MySQL
# from datetime import datetime
# import os
# from flask.cli import load_dotenv
# import mysql.connector

# load_dotenv()

# DB_CONFIG = {
#     "host":     os.getenv("DB_HOST", "localhost"),
#     "port":     int(os.getenv("DB_PORT", 3306)),  # ← tambahkan ini
#     "user":     os.getenv("DB_USER", "root"),
#     "password": os.getenv("DB_PASS", ""),
#     "database": os.getenv("DB_NAME", "absensi_fix_4"),
# }


# # ════════════════════════════════
# #  MAHASISWA
# # ════════════════════════════════

# def nim_sudah_terdaftar(nim: str) -> bool:
#     """Cek apakah NIM sudah ada di tabel mahasiswa."""
#     conn   = mysql.connector.connect(**DB_CONFIG)
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT COUNT(*) FROM mahasiswa WHERE nim = %s", (int(nim),))
#         return cursor.fetchone()[0] > 0
#     finally:
#         cursor.close()
#         conn.close()


# def simpan_mahasiswa(nim: str, nama: str) -> None:
#     conn   = mysql.connector.connect(**DB_CONFIG)
#     cursor = conn.cursor()
#     try:
#         # Hapus data lama dulu (absensi ikut terhapus karena ON DELETE CASCADE)
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
#     """Ambil nama mahasiswa berdasarkan NIM. Return 'UNKNOWN' jika tidak ada."""
#     conn   = mysql.connector.connect(**DB_CONFIG)
#     cursor = conn.cursor()
#     try:
#         cursor.execute("SELECT nama FROM mahasiswa WHERE nim = %s", (int(nim),))
#         result = cursor.fetchone()
#         return result[0] if result else "UNKNOWN"
#     finally:
#         cursor.close()
#         conn.close()


# # ════════════════════════════════
# #  ABSENSI
# # ════════════════════════════════

# def sudah_absen_hari_ini(nim: str) -> bool:
#     """Cek apakah mahasiswa sudah absen hari ini."""
#     today  = datetime.now().strftime("%Y-%m-%d")
#     conn   = mysql.connector.connect(**DB_CONFIG)
#     cursor = conn.cursor()
#     try:
#         cursor.execute(
#             "SELECT COUNT(*) FROM absensi WHERE nim = %s AND DATE(waktu_absen) = %s",
#             (int(nim), today)
#         )
#         return cursor.fetchone()[0] > 0
#     finally:
#         cursor.close()
#         conn.close()


# def simpan_absensi(nim: str) -> None:
#     """
#     Simpan absensi mahasiswa dengan status Hadir.
#     Diabaikan jika mahasiswa sudah absen hari ini.
#     """
#     if sudah_absen_hari_ini(nim):
#         return

#     now    = datetime.now()
#     conn   = mysql.connector.connect(**DB_CONFIG)
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


# def get_kehadiran(keyword: str = "", tanggal: str = "") -> list:
#     """
#     Ambil data kehadiran, opsional filter by keyword (NIM/Nama) dan tanggal.
#     Dipakai oleh Flask /kehadiran/data.
#     """
#     conn   = mysql.connector.connect(**DB_CONFIG)
#     cursor = conn.cursor(dictionary=True)
#     try:
#         query  = """
#             SELECT a.id, a.nim, m.nama, a.waktu_absen, a.status
#             FROM absensi a
#             JOIN mahasiswa m ON a.nim = m.nim
#             WHERE 1=1
#         """
#         params = []

#         if keyword:
#             like = f"%{keyword}%"
#             query += " AND (CAST(a.nim AS CHAR) LIKE %s OR m.nama LIKE %s)"
#             params.extend([like, like])

#         if tanggal:
#             query += " AND DATE(a.waktu_absen) = %s"
#             params.append(tanggal)

#         query += " ORDER BY a.waktu_absen DESC"
#         cursor.execute(query, params)
#         rows = cursor.fetchall()
#     finally:
#         cursor.close()
#         conn.close()

#     for row in rows:
#         if isinstance(row["waktu_absen"], datetime):
#             row["waktu_absen"] = row["waktu_absen"].strftime("%Y-%m-%d %H:%M:%S")
#     return rows

# db.py — versi optimized (FAST)
from datetime import datetime, timedelta
import os
from flask.cli import load_dotenv
import mysql.connector
from mysql.connector import pooling

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "lj"),
    "password": os.getenv("DB_PASS", "LJ123"),
    "database": os.getenv("DB_NAME", "absensi_db"),
}

# ✅ CONNECTION POOL (PENTING)
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
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM mahasiswa WHERE nim = %s", (int(nim),))
        cursor.execute(
            "INSERT INTO mahasiswa (nim, nama) VALUES (%s, %s)",
            (int(nim), nama)
        )
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
#  ABSENSI
# ════════════════════════════════

def sudah_absen_hari_ini(nim: str) -> bool:
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
        today_end   = datetime.now().strftime("%Y-%m-%d 23:59:59")

        cursor.execute(
            """
            SELECT 1 FROM absensi 
            WHERE nim = %s 
            AND waktu_absen BETWEEN %s AND %s
            LIMIT 1
            """,
            (int(nim), today_start, today_end)
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def simpan_absensi(nim: str) -> None:
    if sudah_absen_hari_ini(nim):
        return

    now    = datetime.now()
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO absensi (nim, waktu_absen, status) VALUES (%s, %s, 'Hadir')",
            (int(nim), now)
        )
        conn.commit()

        nama = get_nama(nim)
        print(f"[ABSENSI] {now.strftime('%H:%M:%S')} | NIM: {nim} | {nama} | Hadir")

    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ Gagal simpan absensi: {e}")
    finally:
        cursor.close()
        conn.close()


# ════════════════════════════════
#  KEHADIRAN (OPTIMIZED QUERY)
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

        # ✅ FILTER KEYWORD (OPTIMIZED)
        if keyword:
            query += " AND (a.nim LIKE %s OR m.nama LIKE %s)"
            like = f"%{keyword}%"
            params.extend([like, like])

        # ✅ FILTER TANGGAL TANPA DATE()
        if tanggal:
            start = f"{tanggal} 00:00:00"
            end   = f"{tanggal} 23:59:59"
            query += " AND a.waktu_absen BETWEEN %s AND %s"
            params.extend([start, end])

        query += " ORDER BY a.waktu_absen DESC LIMIT 100"

        cursor.execute(query, params)
        rows = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    # format datetime
    for row in rows:
        if isinstance(row["waktu_absen"], datetime):
            row["waktu_absen"] = row["waktu_absen"].strftime("%Y-%m-%d %H:%M:%S")

    return rows
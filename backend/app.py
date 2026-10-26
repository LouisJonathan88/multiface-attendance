from flask import Flask, render_template, request, jsonify, send_file
import numpy as np
import pandas as pd
from io import BytesIO

from db import (
    get_kehadiran, 
    simpan_pengguna, 
    simpan_embedding, 
    simpan_presensi, 
    load_semua_embedding,
    get_nama,
    nomor_identitas_sudah_terdaftar,
    get_nomor_identitas_presensi_hari_ini
)

app = Flask(__name__)


#  HALAMAN
@app.route('/')
@app.route('/kehadiran')
def kehadiran():
    return render_template('data_kehadiran.html')


#  API DATA WEB
@app.route('/kehadiran/data')
def kehadiran_data():
    keyword = request.args.get('keyword', '').strip()
    tanggal_dari = request.args.get('tanggal_dari', '').strip()
    tanggal_sampai = request.args.get('tanggal_sampai', '').strip()
    try:
        data = get_kehadiran(keyword, tanggal_dari, tanggal_sampai)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/kehadiran/export')
def kehadiran_export():
    keyword = request.args.get('keyword', '').strip()
    tanggal_dari = request.args.get('tanggal_dari', '').strip()
    tanggal_sampai = request.args.get('tanggal_sampai', '').strip()

    if tanggal_dari and tanggal_sampai and tanggal_dari > tanggal_sampai:
        return "Rentang tanggal tidak valid", 400

    data = get_kehadiran(keyword, tanggal_dari, tanggal_sampai)

    if not data:
        df = pd.DataFrame(columns=["Nomor Identitas", "Nama Pengguna", "Waktu Presensi", "Status"])
    else:
        df = pd.DataFrame(data)
        df.rename(columns={
            "nomor_identitas": "Nomor Identitas",
            "nama": "Nama Pengguna",
            "waktu_presensi": "Waktu Presensi",
            "status": "Status"
        }, inplace=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data Presensi')

        worksheet = writer.sheets['Data Presensi']
        worksheet.set_column('B:B', 18)  
        worksheet.set_column('C:C', 30)  
        worksheet.set_column('D:D', 20)  

    output.seek(0)

    if tanggal_dari or tanggal_sampai:
        filename = f"Presensi_{tanggal_dari}_sd_{tanggal_sampai}.xlsx"
    else:
        filename = "Presensi_Semua_Data.xlsx"

    return send_file(output, download_name=filename, as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

#  API ENDPOINT UNTUK EDGE (RPi)

@app.route('/api/pengguna', methods=['POST'])
def api_simpan_pengguna():
    try:
        data = request.get_json()
        nomor_identitas = data.get('nomor_identitas')
        nama = data.get('nama')

        if not nomor_identitas or not nama:
            return jsonify({"error": "Nomor identitas dan nama wajib diisi"}), 400

        simpan_pengguna(nomor_identitas, nama)
        return jsonify({"message": f"Pengguna {nama} ({nomor_identitas}) berhasil disimpan"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/embedding', methods=['POST'])
def api_simpan_embedding():
    try:
        data = request.get_json()
        nomor_identitas = data.get('nomor_identitas')
        vector_hex = data.get('vector')

        if not nomor_identitas or not vector_hex:
            return jsonify({"error": "Nomor identitas dan vector wajib diisi"}), 400

        vector = np.frombuffer(bytes.fromhex(vector_hex), dtype=np.float32)
        simpan_embedding(nomor_identitas, vector)
        return jsonify({"message": f"Embedding nomor identitas {nomor_identitas} berhasil disimpan"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/presensi', methods=['POST'])
def api_simpan_presensi():
    try:
        data = request.get_json()
        nomor_identitas = data.get('nomor_identitas')

        if not nomor_identitas:
            return jsonify({"error": "Nomor identitas wajib diisi"}), 400

        simpan_presensi(nomor_identitas)
        return jsonify({"message": f"Presensi nomor identitas {nomor_identitas} berhasil dicatat"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/embeddings', methods=['GET'])
def api_get_embeddings():
    try:
        embeddings = load_semua_embedding()
        result = {}

        for nomor_identitas, vector in embeddings.items():
            result[nomor_identitas] = vector.tobytes().hex()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/pengguna/<nomor_identitas>', methods=['GET'])
def api_get_pengguna(nomor_identitas):
    try:
        terdaftar = nomor_identitas_sudah_terdaftar(nomor_identitas)
        if terdaftar:
            nama = get_nama(nomor_identitas)
            return jsonify({"terdaftar": True, "nama": nama}), 200
        return jsonify({"terdaftar": False}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/presensi/hari-ini', methods=['GET'])
def api_get_presensi_hari_ini():
    try:
        daftar_nomor_identitas = get_nomor_identitas_presensi_hari_ini()
        return jsonify({"daftar_nomor_identitas": list(daftar_nomor_identitas)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



#  MAIN
if __name__ == '__main__':
    app.run(debug=True, threaded=True, use_reloader=False)
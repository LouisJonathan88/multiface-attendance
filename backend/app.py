# app.py
from flask import Flask, render_template, request, jsonify, redirect, Response
from db import get_kehadiran
import json
import time

app = Flask(__name__)

# ════════════════════════════════
#  HALAMAN
# ════════════════════════════════

@app.route('/')
def index():
    return redirect('/kehadiran')

@app.route('/mahasiswa')
def mahasiswa():
    return render_template('data_mahasiswa.html')

@app.route('/kehadiran')
def kehadiran():
    return render_template('data_kehadiran.html')


# ════════════════════════════════
#  API DATA
# ════════════════════════════════

@app.route('/kehadiran/data')
def kehadiran_data():
    keyword = request.args.get('keyword', '').strip()
    tanggal = request.args.get('tanggal', '').strip()
    try:
        data = get_kehadiran(keyword, tanggal)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════
#  SSE STREAM (REALTIME)
# ════════════════════════════════

@app.route('/kehadiran/stream')
def kehadiran_stream():
    keyword = request.args.get('keyword', '').strip()
    tanggal = request.args.get('tanggal', '').strip()

    # def event_stream():
    #     last_data = None

    #     while True:
    #         try:
    #             data = get_kehadiran(keyword, tanggal)

    #             # kirim hanya jika berubah
    #             if data != last_data:
    #                 yield f"data: {json.dumps(data)}\n\n"
    #                 last_data = data

    #             time.sleep(2)

    #         except Exception as e:
    #             yield f"data: {json.dumps({'error': str(e)})}\n\n"
    #             time.sleep(3)
    def event_stream():
        last_data = None

        while True:
            data = get_kehadiran(keyword, tanggal)

            if data != last_data:
                yield f"data: {json.dumps(data)}\n\n"
                last_data = data

            time.sleep(5)

    return Response(event_stream(), mimetype="text/event-stream")


# ════════════════════════════════
#  MAIN
# ════════════════════════════════

if __name__ == '__main__':
    # app.run(debug=True, use_reloader=False)
    app.run(debug=True, threaded=True, use_reloader=False)
# app.py
from flask import Flask, render_template, request, jsonify, Response
from db import get_kehadiran
import json
import time

app = Flask(__name__)


# ════════════════════════════════
#  HALAMAN
# ════════════════════════════════

@app.route('/')
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
    app.run(debug=True, threaded=True, use_reloader=False)
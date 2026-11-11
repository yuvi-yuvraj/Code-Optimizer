from flask import Flask, render_template, request, jsonify, send_file
from optimizer import optimize_cpp
import io

app = Flask(__name__)

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/optimize")
def optimize():
    payload = request.get_json(silent=True) or {}
    source = payload.get("code", "")
    if not isinstance(source, str) or not source.strip():
        return jsonify({"error": "Please enter some C++ code."}), 400
    try:
        result = optimize_cpp(source)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Optimization failed: {exc}"}), 500

@app.post("/api/validate")
def validate():
    payload = request.get_json(silent=True) or {}
    source = payload.get("code", "")
    import shutil, subprocess, tempfile, os
    compiler = shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        return jsonify({
            "available": False,
            "message": "No C++ compiler found. Install g++ (MinGW-w64 on Windows) to enable validation."
        })
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "check.cpp")
        out = os.path.join(tmp, "check.out")
        with open(src, "w", encoding="utf-8") as f:
            f.write(source)
        proc = subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-fsyntax-only", src],
                              capture_output=True, text=True, timeout=15)
        return jsonify({
            "available": True,
            "valid": proc.returncode == 0,
            "message": proc.stderr.strip() or ("C++ syntax check passed." if proc.returncode == 0 else "Compilation failed.")
        })

@app.post("/api/download")
def download():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code", "")
    return send_file(io.BytesIO(code.encode("utf-8")), mimetype="text/plain",
                     as_attachment=True, download_name="optimized.cpp")

if __name__ == "__main__":
    app.run(debug=True, port=5000)

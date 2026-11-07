import io
import os

from flask import Flask, jsonify, request, send_file, send_from_directory

import stego

DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

app = Flask(__name__, static_folder=DIST, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def _image():
    f = request.files.get("image")
    if not f:
        raise stego.StegoError("Choose an image first.")
    return f.read()


@app.get("/")
def index():
    return send_from_directory(DIST, "index.html")


@app.post("/api/capacity")
def capacity():
    return jsonify(bytes=stego.capacity_bytes(_image()))


@app.post("/api/seal")
def seal():
    png = stego.encode(_image(), request.form.get("message", ""), request.form.get("key", ""))
    return send_file(io.BytesIO(png), mimetype="image/png", download_name="sealed.png")


@app.post("/api/reveal")
def reveal():
    return jsonify(message=stego.decode(_image(), request.form.get("key", "")))


@app.errorhandler(stego.StegoError)
def on_error(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(413)
def too_big(e):
    return jsonify(error="That file is too large. The limit is 10 MB."), 413


@app.after_request
def no_store(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


if __name__ == "__main__":
    app.run(port=5000, debug=True)

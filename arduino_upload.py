from flask import Flask, request, jsonify
import os
import sys
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BINARY_FILENAME = "binary.hex"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

arduino_port = "/dev/ttyUSB0"

@app.route("/")
def home():
    return "Binary upload server is running at /upload"

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    file_path = os.path.join(UPLOAD_FOLDER, BINARY_FILENAME)
    
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))
    
    file.save(file_path)
    upload()
    return jsonify({
        "message": "File uploaded"
    })

def upload():
    command = f"avrdude -v -patmega2560 -cwiring -P {arduino_port} -b115200 -D -U flash:w:{UPLOAD_FOLDER}/{BINARY_FILENAME}:i"
    os.system(command)

def start() -> None:
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    start()
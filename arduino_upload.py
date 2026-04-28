from flask import Flask, request, jsonify
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BINARY_FILENAME = "binary.hex"

app.config("UPLOAD_FOLDER") = UPLOAD_FOLDER

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
    return jsonify({
        "message": "File uploaded"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
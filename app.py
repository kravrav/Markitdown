import os
import glob
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from markitdown import MarkItDown

app = Flask(__name__, static_folder="static")
MAX_FILE_MB = 10

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls",
    "html", "htm", "csv", "json", "xml", "txt", "md", "jpg", "jpeg", "png"
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_temp_files():
    """Delete any leftover temp files from the system temp directory."""
    tmp_dir = tempfile.gettempdir()
    deleted = 0
    for ext in ALLOWED_EXTENSIONS:
        for f in glob.glob(os.path.join(tmp_dir, f"*.{ext}")):
            try:
                os.unlink(f)
                deleted += 1
            except Exception:
                pass
    return deleted


# Clean up any leftover files from a previous crash on startup
cleanup_temp_files()


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"}), 400

    if request.content_length and request.content_length > MAX_FILE_MB * 1024 * 1024:
        return jsonify({"error": f"File too large. Maximum size is {MAX_FILE_MB} MB."}), 413

    suffix = "." + file.filename.rsplit(".", 1)[1].lower()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        md = MarkItDown()
        result = md.convert(tmp_path)
        markdown_text = result.text_content
        del md
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return jsonify({"markdown": markdown_text, "filename": file.filename})


@app.route("/cleanup", methods=["POST"])
def cleanup():
    deleted = cleanup_temp_files()
    return jsonify({"deleted": deleted})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

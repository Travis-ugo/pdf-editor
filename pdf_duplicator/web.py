import os
import io
import uuid
import json
import base64
import tempfile
from flask import Flask, render_template, request, send_file, jsonify
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

import fitz  # PyMuPDF for rendering page preview images

from pdf_duplicator.core import duplicate_pdf, duplicate_pages, add_signature_to_pdf, merge_pdfs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)

# Allow up to 100 MB request payloads (for large PDFs and high-res signature payloads)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['MAX_FORM_MEMORY_SIZE'] = 100 * 1024 * 1024

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "The uploaded file or signature data is too large (max 100 MB)."}), 413


# Temporary session storage directory for PDF preview processing
UPLOAD_TEMP_DIR = tempfile.mkdtemp(prefix="pdf_duplicator_web_")

import shutil

# Project Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
USER_DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

def save_to_user_downloads(src_path, filename):
    """Returns the generated output path. File download is handled directly by browser."""
    return src_path

def sanitize_output_filename(default_name, custom_name=None):
    """
    Sanitizes user custom output filename, enforcing valid characters and .pdf extension.
    """
    if not custom_name or not str(custom_name).strip():
        return default_name

    import re
    clean_name = os.path.basename(str(custom_name).strip())
    clean_name = re.sub(r'[^\w\s\.\-]', '_', clean_name).strip()
    if not clean_name:
        return default_name

    if not clean_name.lower().endswith(".pdf"):
        clean_name += ".pdf"

    return clean_name



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/output/<filename>")
def download_output_file(filename):
    """
    Serves generated PDF files directly from the output directory.
    """
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        file_path = os.path.join(UPLOAD_TEMP_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found."}), 404
    return send_file(file_path, as_attachment=True, download_name=filename, mimetype="application/pdf")

@app.route("/api/inspect-pdf", methods=["POST"])
def inspect_pdf():
    """
    Receives an uploaded PDF file, saves to temp storage, extracts page info,
    and renders page previews as PNG base64 strings for visual editing.
    """
    if "file" not in request.files:
        return jsonify({"error": "No PDF file provided."}), 400

    file = request.files["file"]
    password = request.form.get("password") or None

    file_id = str(uuid.uuid4())
    temp_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
    file.save(temp_path)

    try:
        reader = PdfReader(temp_path)
        is_encrypted = reader.is_encrypted
        if is_encrypted:
            if not password:
                return jsonify({"error": "PDF is encrypted.", "is_encrypted": True}), 401
            decrypted = reader.decrypt(password)
            if decrypted == 0:
                return jsonify({"error": "Incorrect password for encrypted PDF.", "is_encrypted": True}), 401

        total_pages = len(reader.pages)
        page_previews = []
        page_dimensions = []

        # Use PyMuPDF to render page previews
        doc = fitz.open(temp_path)
        if doc.is_encrypted and password:
            doc.authenticate(password)

        for pno in range(min(total_pages, 20)):  # preview up to first 20 pages
            page = doc.load_page(pno)
            rect = page.rect  # width, height
            page_dimensions.append({"width": float(rect.width), "height": float(rect.height)})
            
            # Render page to image (zoom factor 1.5 for crisp clarity)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img_bytes = pix.tobytes("png")
            b64_img = "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")
            page_previews.append(b64_img)

        doc.close()

        return jsonify({
            "file_id": file_id,
            "filename": file.filename,
            "total_pages": total_pages,
            "is_encrypted": is_encrypted,
            "page_dimensions": page_dimensions,
            "page_previews": page_previews
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/preview-pdf", methods=["POST"])
def preview_pdf():
    """
    Renders a full signed document preview by applying current signatures onto a temporary PDF 
    and returning rendered base64 PNG images for all pages.
    """
    file_id = request.form.get("file_id")
    password = request.form.get("password") or None
    signatures_json = request.form.get("signatures_json")
    
    signatures_list = None
    if signatures_json:
        try:
            signatures_list = json.loads(signatures_json)
        except Exception:
            pass

    input_path = None
    if file_id:
        input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
        if not os.path.exists(input_path):
            input_path = None

    if not input_path:
        if "file" in request.files:
            file = request.files["file"]
            file_id = str(uuid.uuid4())
            input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
            file.save(input_path)
        else:
            return jsonify({"error": "Missing input PDF file."}), 400

    preview_output_filename = f"prev_{uuid.uuid4().hex[:8]}.pdf"
    preview_output_path = os.path.join(UPLOAD_TEMP_DIR, preview_output_filename)

    try:
        if signatures_list:
            add_signature_to_pdf(
                input_path,
                preview_output_path,
                password=password,
                signatures=signatures_list
            )
        else:
            shutil.copyfile(input_path, preview_output_path)

        doc = fitz.open(preview_output_path)
        if doc.is_encrypted and password:
            doc.authenticate(password)

        page_previews = []
        for pno in range(len(doc)):
            page = doc.load_page(pno)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img_bytes = pix.tobytes("png")
            b64_img = "data:image/png;base64," + base64.b64encode(img_bytes).decode("utf-8")
            page_previews.append(b64_img)

        doc.close()
        if os.path.exists(preview_output_path):
            os.remove(preview_output_path)

        return jsonify({
            "total_pages": len(page_previews),
            "page_previews": page_previews
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sign", methods=["POST"])
def sign_pdf_endpoint():
    """
    Adds signature overlay to PDF and returns downloadable PDF.
    """
    file_id = request.form.get("file_id")
    password = request.form.get("password") or None
    pages_spec = request.form.get("pages_spec") or None
    
    try:
        x = float(request.form.get("x", 50))
        y = float(request.form.get("y", 50))
        width = float(request.form.get("width", 150))
        height = float(request.form.get("height", 50))
        y_from_top = request.form.get("y_from_top", "true").lower() == "true"
    except ValueError:
        return jsonify({"error": "Invalid numeric coordinates or dimensions."}), 400

    input_path = None
    original_filename = "document.pdf"
    if file_id:
        input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
        if not os.path.exists(input_path):
            input_path = None

    if not input_path:
        if "file" in request.files:
            file = request.files["file"]
            file_id = str(uuid.uuid4())
            original_filename = file.filename
            input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
            file.save(input_path)
        else:
            return jsonify({"error": "Missing input PDF file."}), 400

    import json
    signatures_json = request.form.get("signatures_json")
    signatures_list = None
    if signatures_json:
        try:
            signatures_list = json.loads(signatures_json)
        except Exception as e:
            print(f"Error parsing signatures_json: {e}")

    signature_data = request.form.get("signature_data")
    signature_file = request.files.get("signature_file")

    if not signatures_list:
        if signature_data:
            sig_input = signature_data
        elif signature_file:
            sig_input = signature_file.read()
        else:
            return jsonify({"error": "Missing signature image or drawing."}), 400
    else:
        sig_input = None

    default_output_name = f"signed_{file_id[:6]}.pdf"
    custom_name = request.form.get("custom_filename") or request.form.get("output_filename")
    output_filename = sanitize_output_filename(default_output_name, custom_name)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        add_signature_to_pdf(
            input_path,
            output_path,
            signature_img=sig_input,
            pages_spec=pages_spec,
            x=x,
            y=y,
            width=width,
            height=height,
            password=password,
            y_from_top=y_from_top,
            signatures=signatures_list
        )


        saved_user_path = save_to_user_downloads(output_path, output_filename)
        download_url = f"/output/{output_filename}"

        if request.headers.get("Accept") == "application/json":
            return jsonify({
                "success": True,
                "message": "Signature applied successfully!",
                "download_url": download_url,
                "filename": output_filename,
                "save_location": saved_user_path
            })

        response = send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype="application/pdf"
        )
        response.headers["X-Download-Url"] = download_url
        response.headers["X-File-Path"] = saved_user_path
        response.headers["Access-Control-Expose-Headers"] = "X-Download-Url, X-File-Path"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/duplicate", methods=["POST"])
def duplicate_pdf_endpoint():
    """
    Executes page duplication and returns downloadable PDF.
    """
    file_id = request.form.get("file_id")
    password = request.form.get("password") or None
    pages_spec = request.form.get("pages_spec") or None
    count = int(request.form.get("count", 2))
    repeat_sequence = request.form.get("repeat_sequence", "false").lower() == "true"

    input_path = None
    if file_id:
        input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
        if not os.path.exists(input_path):
            input_path = None

    if not input_path:
        if "file" in request.files:
            file = request.files["file"]
            file_id = str(uuid.uuid4())
            input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
            file.save(input_path)
        else:
            return jsonify({"error": "Missing input PDF file."}), 400

    default_output_name = f"duplicated_{file_id[:6]}.pdf"
    custom_name = request.form.get("custom_filename") or request.form.get("output_filename")
    output_filename = sanitize_output_filename(default_output_name, custom_name)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        duplicate_pages(
            input_path,
            output_path,
            pages_spec=pages_spec,
            count=count,
            password=password,
            repeat_sequence=repeat_sequence
        )

        saved_user_path = save_to_user_downloads(output_path, output_filename)
        download_url = f"/output/{output_filename}"

        if request.headers.get("Accept") == "application/json":
            return jsonify({
                "success": True,
                "message": "Pages duplicated successfully!",
                "download_url": download_url,
                "filename": output_filename,
                "save_location": saved_user_path
            })

        response = send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype="application/pdf"
        )
        response.headers["X-Download-Url"] = download_url
        response.headers["X-File-Path"] = saved_user_path
        response.headers["Access-Control-Expose-Headers"] = "X-Download-Url, X-File-Path"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/clone", methods=["POST"])
def clone_pdf_endpoint():
    """
    Executes PDF cloning and decryption, returning downloadable PDF.
    """
    file_id = request.form.get("file_id")
    password = request.form.get("password") or None

    input_path = None
    if file_id:
        input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
        if not os.path.exists(input_path):
            input_path = None

    if not input_path:
        if "file" in request.files:
            file = request.files["file"]
            file_id = str(uuid.uuid4())
            input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
            file.save(input_path)
        else:
            return jsonify({"error": "Missing input PDF file."}), 400

    default_output_name = f"cloned_{file_id[:6]}.pdf"
    custom_name = request.form.get("custom_filename") or request.form.get("output_filename")
    output_filename = sanitize_output_filename(default_output_name, custom_name)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        duplicate_pdf(
            input_path,
            output_path,
            password=password
        )

        saved_user_path = save_to_user_downloads(output_path, output_filename)
        download_url = f"/output/{output_filename}"

        if request.headers.get("Accept") == "application/json":
            return jsonify({
                "success": True,
                "message": "PDF cloned & decrypted successfully!",
                "download_url": download_url,
                "filename": output_filename,
                "save_location": saved_user_path
            })

        response = send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype="application/pdf"
        )
        response.headers["X-Download-Url"] = download_url
        response.headers["X-File-Path"] = saved_user_path
        response.headers["Access-Control-Expose-Headers"] = "X-Download-Url, X-File-Path"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/merge", methods=["POST"])
def merge_pdf_endpoint():
    """
    Merges multiple PDF files into a single document.
    Accepts files via items_json referencing file_ids, or uploaded files.
    Supports custom_filename parameter.
    """
    items_json = request.form.get("items_json")
    custom_name = request.form.get("custom_filename") or request.form.get("output_filename")

    pdf_inputs = []

    if items_json:
        try:
            items = json.loads(items_json)
            for item in items:
                file_id = item.get("file_id")
                pwd = item.get("password") or None
                spec = item.get("pages_spec") or None
                if file_id:
                    input_path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
                    if os.path.exists(input_path):
                        pdf_inputs.append({
                            "path": input_path,
                            "password": pwd,
                            "pages_spec": spec
                        })
        except Exception as e:
            return jsonify({"error": f"Invalid items_json payload: {e}"}), 400

    uploaded_files = request.files.getlist("files") or request.files.getlist("files[]")
    if uploaded_files:
        for ufile in uploaded_files:
            if ufile and ufile.filename:
                fid = str(uuid.uuid4())
                tpath = os.path.join(UPLOAD_TEMP_DIR, f"{fid}.pdf")
                ufile.save(tpath)
                pdf_inputs.append({
                    "path": tpath,
                    "password": None,
                    "pages_spec": None
                })

    if not pdf_inputs:
        return jsonify({"error": "No PDF files provided to merge."}), 400

    default_output_name = f"merged_{uuid.uuid4().hex[:6]}.pdf"
    output_filename = sanitize_output_filename(default_output_name, custom_name)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        merge_pdfs(pdf_inputs, output_path)

        saved_user_path = save_to_user_downloads(output_path, output_filename)
        download_url = f"/output/{output_filename}"

        if request.headers.get("Accept") == "application/json" or request.is_json or True:
            return jsonify({
                "success": True,
                "message": "PDFs merged successfully!",
                "download_url": download_url,
                "filename": output_filename,
                "save_location": saved_user_path
            })

        response = send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype="application/pdf"
        )
        response.headers["X-Download-Url"] = download_url
        response.headers["X-File-Path"] = saved_user_path
        response.headers["Access-Control-Expose-Headers"] = "X-Download-Url, X-File-Path"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_server(host="127.0.0.1", port=5000, debug=False):
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_server(debug=True)


import os
import io
import uuid
import json
import base64
import tempfile
from flask import Flask, render_template, request, send_file, jsonify
from pypdf import PdfReader

import fitz  # PyMuPDF for rendering page preview images

from pdf_duplicator.convert import convert_to_pdf, SUPPORTED_EXTENSIONS
from pdf_duplicator.core import duplicate_pdf, duplicate_pages, add_signature_to_pdf, merge_pdfs, all_text_font_coverage, text_font_catalog

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



def unique_output_path(filename):
    """
    (filename, path) in OUTPUT_DIR that doesn't overwrite an existing file: 'contract.pdf' becomes
    'contract (1).pdf', 'contract (2).pdf', ... the way browsers name repeated downloads.
    """
    stem, ext = os.path.splitext(filename)
    candidate, n = filename, 0
    while os.path.exists(os.path.join(OUTPUT_DIR, candidate)):
        n += 1
        candidate = f"{stem} ({n}){ext}"
    return candidate, os.path.join(OUTPUT_DIR, candidate)


def render_page_preview(page, zoom, max_side):
    """
    Renders a page to a base64 PNG data URL at `zoom`, scaled down if needed so the longest side
    is at most `max_side` pixels. Oversized pages (e.g. scans saved at 1pt per pixel, ~27x38in)
    would otherwise produce 20+ megapixel images that take seconds each to PNG-encode and
    hundreds of MB to send to the browser. Previews only -- the output PDF is never rasterized.
    Pages without text (scans/photos) are sent as high-quality JPEG, which encodes ~3x faster and
    ~5x smaller than PNG for photographic content; text pages stay PNG so lettering stays crisp.
    """
    rect = page.rect
    zoom = min(zoom, max_side / max(rect.width, rect.height, 1))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    if page.get_text().strip():
        return "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode("utf-8")
    return "data:image/jpeg;base64," + base64.b64encode(pix.tobytes("jpeg", jpg_quality=92)).decode("utf-8")


INITIAL_PREVIEW_PAGES = 20


def render_editor_preview(page):
    # This is the background the editor draws signatures/text onto, so it needs to stay sharp on
    # HiDPI (Retina) screens: zoom 2.0 renders at "@2x" density, matching typical Retina DPR.
    return render_page_preview(page, 2.0, 2400)


@app.route("/")
def index():
    return render_template("index.html", font_catalog=text_font_catalog(), font_coverage=all_text_font_coverage(),
                           document_extensions=sorted(SUPPORTED_EXTENSIONS))

def _upload_path(file_id):
    """
    Path of an uploaded PDF, or None. file_id comes from the client, so only accept the UUIDs that
    /api/inspect-pdf hands out; anything else (e.g. '../../x') could reach PDFs outside the upload dir.
    """
    try:
        file_id = str(uuid.UUID(str(file_id)))
    except (ValueError, TypeError, AttributeError):
        return None
    path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
    return path if os.path.exists(path) else None


def save_upload(file):
    """
    Saves an uploaded document as <file_id>.pdf in the upload folder, converting it first if it
    isn't a PDF (Word, images, text, ...). Returns (file_id, path, kind). Raises ValueError
    (convert.UnsupportedDocument) for files that can't be opened.
    """
    file_id = str(uuid.uuid4())
    path = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.pdf")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext in ("", ".pdf"):
        file.save(path)
        return file_id, path, "pdf"
    original = os.path.join(UPLOAD_TEMP_DIR, f"{file_id}.source{ext}")
    file.save(original)
    try:
        kind = convert_to_pdf(original, path, filename=file.filename)
    finally:
        os.remove(original)
    return file_id, path, kind


def _save_fallback_upload():
    """(file_id, path, error_response) for an endpoint's re-sent 'file' when its file_id is gone."""
    if "file" not in request.files:
        return None, None, (jsonify({"error": "Missing input PDF file."}), 400)
    try:
        file_id, path, _ = save_upload(request.files["file"])
    except ValueError as e:
        return None, None, (jsonify({"error": str(e)}), 400)
    return file_id, path, None


def _safe_join(directory, filename):
    """
    Resolves filename under directory and returns the path only if it's actually a file that
    stays within directory (guards against '..' or other traversal in a user-supplied filename).
    """
    candidate = os.path.realpath(os.path.join(directory, filename))
    directory = os.path.realpath(directory)
    if os.path.commonpath([candidate, directory]) != directory:
        return None
    return candidate if os.path.isfile(candidate) else None


@app.route("/output/<filename>")
def download_output_file(filename):
    """
    Serves generated PDF files directly from the output directory.
    """
    file_path = _safe_join(OUTPUT_DIR, filename) or _safe_join(UPLOAD_TEMP_DIR, filename)
    if not file_path:
        return jsonify({"error": "File not found."}), 404
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(filename), mimetype="application/pdf")

@app.route("/api/inspect-pdf", methods=["POST"])
def inspect_pdf():
    """
    Receives an uploaded document (a PDF, or any format convert.py can turn into one), saves it to
    temp storage as a PDF, extracts page info, and renders page previews for visual editing.
    """
    if "file" not in request.files:
        return jsonify({"error": "No document provided."}), 400

    file = request.files["file"]
    password = request.form.get("password") or None

    try:
        file_id, temp_path, source_kind = save_upload(file)
    except ValueError as e:
        return jsonify({"error": str(e), "unsupported": True}), 415

    try:
        reader = PdfReader(temp_path)
        is_encrypted = reader.is_encrypted
        if is_encrypted:
            # The file is already saved under file_id regardless of encryption, so callers that
            # can supply a password later (e.g. per-file passwords in Merge mode, which never
            # re-calls this endpoint) still need file_id now to reference it at merge/sign time.
            if not password:
                return jsonify({"error": "PDF is encrypted.", "is_encrypted": True, "file_id": file_id}), 401
            decrypted = reader.decrypt(password)
            if decrypted == 0:
                return jsonify({"error": "Incorrect password for encrypted PDF.", "is_encrypted": True, "file_id": file_id}), 401

        total_pages = len(reader.pages)
        page_previews = []
        page_dimensions = []

        # Use PyMuPDF to render page previews
        doc = fitz.open(temp_path)
        if doc.is_encrypted and password:
            doc.authenticate(password)

        for pno in range(total_pages):
            page = doc.load_page(pno)
            rect = page.rect  # displayed width, height (crop box, after /Rotate)
            page_dimensions.append({"width": float(rect.width), "height": float(rect.height)})

            # Only the first pages are rendered up front; the rest come from /api/page-preview
            # when the editor shows them.
            if pno < INITIAL_PREVIEW_PAGES:
                page_previews.append(render_editor_preview(page))

        doc.close()

        return jsonify({
            "file_id": file_id,
            "filename": file.filename,
            "total_pages": total_pages,
            "is_encrypted": is_encrypted,
            "source_kind": source_kind,  # "pdf", or what it was converted from ("office", "image", ...)
            "page_dimensions": page_dimensions,
            "page_previews": page_previews
        })

    except ValueError as e:  # bad input: page range, password, count, overlay fields...
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/page-preview", methods=["POST"])
def page_preview():
    """Renders one page of an uploaded PDF for the editor (pages past the first few load lazily)."""
    input_path = _upload_path(request.form.get("file_id"))
    if not input_path:
        return jsonify({"error": "Unknown file. Open the PDF again."}), 404
    password = request.form.get("password") or None
    try:
        page_num = int(request.form.get("page", ""))
    except ValueError:
        return jsonify({"error": "Invalid page number."}), 400

    doc = fitz.open(input_path)
    try:
        if doc.is_encrypted and not doc.authenticate(password or ""):
            return jsonify({"error": "Incorrect password for encrypted PDF.", "is_encrypted": True}), 401
        if not 1 <= page_num <= len(doc):
            return jsonify({"error": f"Page {page_num} is out of range (1-{len(doc)})."}), 400
        return jsonify({"page": page_num, "preview": render_editor_preview(doc.load_page(page_num - 1))})
    finally:
        doc.close()


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

    input_path = _upload_path(file_id) if file_id else None

    if not input_path:
        file_id, input_path, error = _save_fallback_upload()
        if error:
            return error

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
            # This is the "what you'll actually download" preview, rendered once on demand, so it's
            # worth the extra render time to render it at higher density ("@3x") than the live editor.
            page_previews.append(render_page_preview(page, 3.0, 3200))

        doc.close()
        if os.path.exists(preview_output_path):
            os.remove(preview_output_path)

        return jsonify({
            "total_pages": len(page_previews),
            "page_previews": page_previews
        })
    except ValueError as e:  # bad input: page range, password, count, overlay fields...
        return jsonify({"error": str(e)}), 400
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

    input_path = _upload_path(file_id) if file_id else None

    if not input_path:
        file_id, input_path, error = _save_fallback_upload()
        if error:
            return error

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
    output_filename, output_path = unique_output_path(output_filename)

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
    except ValueError as e:  # bad input: page range, password, count, overlay fields...
        return jsonify({"error": str(e)}), 400
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
    try:
        count = int(request.form.get("count") or 2)
    except ValueError:
        return jsonify({"error": "Invalid duplication count."}), 400
    repeat_sequence = request.form.get("repeat_sequence", "false").lower() == "true"

    input_path = _upload_path(file_id) if file_id else None

    if not input_path:
        file_id, input_path, error = _save_fallback_upload()
        if error:
            return error

    default_output_name = f"duplicated_{file_id[:6]}.pdf"
    custom_name = request.form.get("custom_filename") or request.form.get("output_filename")
    output_filename = sanitize_output_filename(default_output_name, custom_name)
    output_filename, output_path = unique_output_path(output_filename)

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
    except ValueError as e:  # bad input: page range, password, count, overlay fields...
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/clone", methods=["POST"])
def clone_pdf_endpoint():
    """
    Executes PDF cloning and decryption, returning downloadable PDF.
    """
    file_id = request.form.get("file_id")
    password = request.form.get("password") or None

    input_path = _upload_path(file_id) if file_id else None

    if not input_path:
        file_id, input_path, error = _save_fallback_upload()
        if error:
            return error

    default_output_name = f"cloned_{file_id[:6]}.pdf"
    custom_name = request.form.get("custom_filename") or request.form.get("output_filename")
    output_filename = sanitize_output_filename(default_output_name, custom_name)
    output_filename, output_path = unique_output_path(output_filename)

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
    except ValueError as e:  # bad input: page range, password, count, overlay fields...
        return jsonify({"error": str(e)}), 400
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
                input_path = _upload_path(file_id) if file_id else None
                if input_path:
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
                try:
                    _, tpath, _ = save_upload(ufile)
                except ValueError as e:
                    return jsonify({"error": f"{ufile.filename}: {e}"}), 400
                pdf_inputs.append({
                    "path": tpath,
                    "password": None,
                    "pages_spec": None
                })

    if not pdf_inputs:
        return jsonify({"error": "No PDF files provided to merge."}), 400

    default_output_name = f"merged_{uuid.uuid4().hex[:6]}.pdf"
    output_filename = sanitize_output_filename(default_output_name, custom_name)
    output_filename, output_path = unique_output_path(output_filename)

    try:
        merge_pdfs(pdf_inputs, output_path)

        saved_user_path = save_to_user_downloads(output_path, output_filename)
        download_url = f"/output/{output_filename}"

        if request.headers.get("Accept") == "application/json":
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
    except ValueError as e:  # bad input: page range, password, count, overlay fields...
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_server(host="127.0.0.1", port=5000, debug=False):
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_server(debug=True)


"""
Turns any supported document into a PDF, so the editor (sign, text, pen, merge, ...) can work on it.

- PDF: used as is.
- Images, SVG, XPS, EPUB, FB2, MOBI, CBZ: rendered by PyMuPDF.
- Plain text, Markdown, HTML: laid out on Letter pages by PyMuPDF's Story (with Noto fallback
  fonts, so non-Latin scripts render).
- Word, PowerPoint, Excel, OpenDocument, RTF: converted by LibreOffice running headless. That's
  optional: without it these formats fail with a clear message instead.
"""
import html
import io
import os
import shutil
import subprocess
import tempfile

import fitz

PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".jxr", ".pnm", ".pbm", ".pgm", ".ppm"}
FITZ_EXTENSIONS = {".svg", ".xps", ".oxps", ".epub", ".fb2", ".mobi", ".cbz"}
TEXT_EXTENSIONS = {".txt", ".text", ".log", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".ini", ".cfg"}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
HTML_EXTENSIONS = {".html", ".htm"}
OFFICE_EXTENSIONS = {
    ".doc", ".docx", ".docm", ".dot", ".dotx", ".odt", ".ott", ".rtf", ".wpd", ".pages",
    ".ppt", ".pptx", ".pps", ".ppsx", ".odp",
    ".xls", ".xlsx", ".xlsm", ".ods",
}

SUPPORTED_EXTENSIONS = (PDF_EXTENSIONS | IMAGE_EXTENSIONS | FITZ_EXTENSIONS | TEXT_EXTENSIONS
                        | MARKDOWN_EXTENSIONS | HTML_EXTENSIONS | OFFICE_EXTENSIONS)

PAGE = fitz.paper_rect("letter")
MARGIN = 72  # 1 inch
OFFICE_TIMEOUT_S = 120

TEXT_CSS = """
body { font-family: sans-serif; font-size: 11pt; line-height: 1.45; color: #1a1a1a; }
pre { font-family: monospace; font-size: 9.5pt; white-space: pre-wrap; }
h1 { font-size: 22pt; } h2 { font-size: 17pt; } h3 { font-size: 13.5pt; }
code { font-family: monospace; font-size: 9.5pt; }
table { border-collapse: collapse; } th, td { border: 1px solid #999; padding: 3pt 6pt; }
blockquote { color: #555; margin-left: 12pt; }
"""


class UnsupportedDocument(ValueError):
    """The file type can't be opened (or needs a converter that isn't installed)."""


def document_kind(filename):
    """'pdf', 'image', 'text', 'office', ... for a file name, or None if unsupported."""
    ext = os.path.splitext(str(filename or ""))[1].lower()
    for kind, exts in (("pdf", PDF_EXTENSIONS), ("image", IMAGE_EXTENSIONS), ("ebook", FITZ_EXTENSIONS),
                       ("text", TEXT_EXTENSIONS), ("markdown", MARKDOWN_EXTENSIONS),
                       ("html", HTML_EXTENSIONS), ("office", OFFICE_EXTENSIONS)):
        if ext in exts:
            return kind
    return None


def find_soffice():
    """Path of LibreOffice's command-line binary, or None."""
    for candidate in (os.environ.get("SOFFICE_PATH"), shutil.which("soffice"), shutil.which("libreoffice"),
                      "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def convert_to_pdf(input_path, output_path, filename=None):
    """
    Writes a PDF version of input_path to output_path and returns the document kind. `filename`
    (the name the user uploaded) decides the format; it defaults to input_path's name.
    Raises UnsupportedDocument for formats that can't be opened.
    """
    name = filename or input_path
    kind = document_kind(name)
    ext = os.path.splitext(name)[1].lower() or "(no extension)"
    if kind is None:
        raise UnsupportedDocument(f"Can't open {ext} files. Supported: PDF, Word, PowerPoint, Excel, "
                                  "OpenDocument, RTF, text, Markdown, HTML, images, SVG and e-books.")
    if kind == "pdf":
        if os.path.abspath(input_path) != os.path.abspath(output_path):
            shutil.copyfile(input_path, output_path)
    elif kind in ("image", "ebook"):
        _fitz_to_pdf(input_path, output_path, ext)
    elif kind in ("text", "markdown", "html"):
        with open(input_path, "rb") as f:
            text = _decode(f.read())
        if kind == "text":
            body = f"<pre>{html.escape(text)}</pre>"
        elif kind == "markdown":
            import markdown
            body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
        else:
            body = text
        _html_to_pdf(body, output_path)
    else:
        _office_to_pdf(input_path, output_path, ext)
    return kind


def _decode(data):
    """Text file bytes -> str: UTF-16 (with BOM), else UTF-8, else Windows-1252 (old Windows files)."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _fitz_to_pdf(input_path, output_path, ext):
    try:
        _save_as_pdf(fitz.open(input_path, filetype=ext.lstrip(".")), output_path)
    except Exception:
        # MuPDF opens lazily, so a bad file can fail at open or at conversion. Images get a second
        # chance through Pillow (which reads some formats MuPDF can't); anything else is unreadable.
        if ext not in IMAGE_EXTENSIONS:
            raise UnsupportedDocument(f"This {ext} file couldn't be read.")
        _save_as_pdf(_pillow_image_as_png(input_path), output_path)


def _save_as_pdf(src, output_path):
    try:
        if src.is_reflowable:
            src.layout(PAGE)
        pdf = fitz.open("pdf", src.convert_to_pdf())
        pdf.save(output_path, garbage=3, deflate=True)
        pdf.close()
    finally:
        src.close()


def _pillow_image_as_png(input_path):
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(input_path) as img:
            img.load()
            buf = io.BytesIO()
            (img if img.mode in ("RGB", "RGBA", "L", "LA") else img.convert("RGBA")).save(buf, format="PNG")
    except (UnidentifiedImageError, OSError):
        raise UnsupportedDocument("This image couldn't be read.")
    return fitz.open("png", buf.getvalue())


def _html_to_pdf(body, output_path):
    story = fitz.Story(html=body, user_css=TEXT_CSS)
    writer = fitz.DocumentWriter(output_path)
    content = PAGE + (MARGIN, MARGIN, -MARGIN, -MARGIN)
    more = True
    while more:
        device = writer.begin_page(PAGE)
        more, _ = story.place(content)
        story.draw(device)
        writer.end_page()
    writer.close()


def _office_to_pdf(input_path, output_path, ext):
    soffice = find_soffice()
    if not soffice:
        raise UnsupportedDocument(
            f"Opening {ext} files needs LibreOffice (free). Install it from libreoffice.org "
            "or with `brew install --cask libreoffice`, then try again.")
    with tempfile.TemporaryDirectory(prefix="pdfstudio_office_") as work:
        # LibreOffice names its output after the input, so give it a known name with the right extension
        src = os.path.join(work, "document" + ext)
        shutil.copyfile(input_path, src)
        # A private profile lets conversions run while the user has LibreOffice open
        profile = "file://" + os.path.join(work, "profile")
        cmd = [soffice, f"-env:UserInstallation={profile}", "--headless", "--norestore",
               "--convert-to", "pdf", "--outdir", work, src]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=OFFICE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise UnsupportedDocument(f"Converting the {ext} file took too long.")
        produced = os.path.join(work, "document.pdf")
        if result.returncode != 0 or not os.path.exists(produced):
            detail = (result.stderr or result.stdout or b"").decode(errors="replace").strip()[:300]
            raise UnsupportedDocument(f"LibreOffice couldn't convert this {ext} file. {detail}".strip())
        shutil.move(produced, output_path)

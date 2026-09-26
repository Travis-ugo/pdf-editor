import functools
import os

from pypdf import PdfReader, PdfWriter


def parse_page_range(pages_spec, total_pages):
    """
    Parses a string representing pages/ranges and returns a list of 0-based indices.
    Example specs: '1', '1-3', '1,2,5', '1-3,5'
    """
    if pages_spec is None or pages_spec == "":
        return list(range(total_pages))
    
    pages_spec_str = str(pages_spec).strip()
    if not pages_spec_str:
        return list(range(total_pages))
    
    indices = []
    parts = pages_spec_str.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start, end = part.split('-')
                start_idx = int(start.strip()) - 1
                end_idx = int(end.strip()) - 1
                
                # Validation
                if start_idx < 0 or end_idx >= total_pages or start_idx > end_idx:
                    raise ValueError(f"Invalid page range: {part}. Total pages in file: {total_pages}")
                
                indices.extend(range(start_idx, end_idx + 1))
            except ValueError as e:
                raise ValueError(f"Invalid range format: {part}. Error: {e}")
        else:
            try:
                idx = int(part) - 1
                if idx < 0 or idx >= total_pages:
                    raise ValueError(f"Page number {part} out of bounds. Total pages in file: {total_pages}")
                indices.append(idx)
            except ValueError as e:
                raise ValueError(f"Invalid page number: {part}. Error: {e}")
    return indices


def duplicate_pdf(input_path, output_path, password=None):
    """
    Clones/duplicates a PDF document. Removes password encryption if decrypted.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    reader = PdfReader(input_path)
    
    if reader.is_encrypted:
        if not password:
            raise ValueError("The PDF is encrypted. Please provide a password.")
        decrypted = reader.decrypt(password)
        # pypdf decrypt returns a DecryptionResult or 0/1/2
        # In modern pypdf, decrypt returns 0 for failure, or a non-zero integer status code / PasswordType
        if decrypted == 0:
            raise ValueError("Incorrect password for the PDF file.")
            
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
        
    with open(output_path, "wb") as f:
        writer.write(f)

def duplicate_pages(input_path, output_path, pages_spec=None, count=1, password=None, repeat_sequence=False):
    """
    Duplicates pages of a PDF a specified number of times.
    If repeat_sequence is True, repeats the entire selection sequence: (p1, p2, p1, p2)
    If False, duplicates each page individually: (p1, p1, p2, p2)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    if count < 1:
        raise ValueError("Count must be at least 1.")
        
    reader = PdfReader(input_path)
    
    if reader.is_encrypted:
        if not password:
            raise ValueError("The PDF is encrypted. Please provide a password.")
        decrypted = reader.decrypt(password)
        if decrypted == 0:
            raise ValueError("Incorrect password for the PDF file.")
            
    total_pages = len(reader.pages)
    indices = parse_page_range(pages_spec, total_pages)
    
    writer = PdfWriter()
    
    if repeat_sequence:
        # Repeat the sequence of pages `count` times
        for _ in range(count):
            for idx in indices:
                writer.add_page(reader.pages[idx])
    else:
        # Duplicate each page `count` times individually
        for idx in indices:
            for _ in range(count):
                writer.add_page(reader.pages[idx])
                
    with open(output_path, "wb") as f:
        writer.write(f)

def merge_pdfs(pdf_inputs, output_path):
    """
    Merges multiple PDF documents into a single PDF.
    
    :param pdf_inputs: List of PDF file paths (str) or dict objects:
                       [{ 'path': '...', 'password': '...', 'pages_spec': '...' }]
    :param output_path: Path to output PDF file
    """
    if not pdf_inputs or len(pdf_inputs) == 0:
        raise ValueError("At least one PDF file must be provided for merging.")

    writer = PdfWriter()

    for item in pdf_inputs:
        if isinstance(item, str):
            input_path = item
            password = None
            pages_spec = None
        elif isinstance(item, dict):
            input_path = item.get("path")
            password = item.get("password")
            pages_spec = item.get("pages_spec")
        else:
            raise ValueError(f"Invalid PDF input format: {item}")

        if not input_path or not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        reader = PdfReader(input_path)

        if reader.is_encrypted:
            if not password:
                raise ValueError(f"The PDF '{os.path.basename(input_path)}' is encrypted. Please provide a password.")
            decrypted = reader.decrypt(password)
            if decrypted == 0:
                raise ValueError(f"Incorrect password for '{os.path.basename(input_path)}'.")

        total_pages = len(reader.pages)
        indices = parse_page_range(pages_spec, total_pages)

        for idx in indices:
            writer.add_page(reader.pages[idx])

    with open(output_path, "wb") as f:
        writer.write(f)


def _process_image_input(sig_input):
    import io
    import base64
    from PIL import Image
    if isinstance(sig_input, str):
        if sig_input.startswith("data:image"):
            if "," in sig_input:
                header, encoded = sig_input.split(",", 1)
            else:
                encoded = sig_input
            encoded = encoded.strip()
            missing_padding = len(encoded) % 4
            if missing_padding:
                encoded += "=" * (4 - missing_padding)
            img_bytes = base64.b64decode(encoded)
            img = Image.open(io.BytesIO(img_bytes))
            img.load()
            return img
        elif os.path.exists(sig_input):
            img = Image.open(sig_input)
            img.load()
            return img
        else:
            raise ValueError(f"Signature image file not found: {sig_input}")
    elif isinstance(sig_input, bytes):
        img = Image.open(io.BytesIO(sig_input))
        img.load()
        return img
    elif hasattr(sig_input, "read"):
        img = Image.open(sig_input)
        img.load()
        return img
    elif isinstance(sig_input, Image.Image):
        return sig_input
    else:
        raise ValueError("Invalid signature image format.")

# --- Text overlay support ---------------------------------------------------
# Text boxes are laid out on a fixed grid so the browser preview and the PDF agree:
# every line is TEXT_LINE_HEIGHT * font_size tall and the first baseline sits
# TEXT_BASELINE * font_size below the top of the box. Keep these in sync with
# TEXT_LINE_HEIGHT / TEXT_BASELINE in static/js/app.js.
TEXT_LINE_HEIGHT = 1.2
TEXT_BASELINE = 0.9
TEXT_MIN_FONT_SIZE = 4
TEXT_MAX_FONT_SIZE = 400

# (family, bold, italic) -> built-in PDF font. These need no embedding.
TEXT_FONTS = {
    ("helvetica", False, False): "Helvetica",
    ("helvetica", True, False): "Helvetica-Bold",
    ("helvetica", False, True): "Helvetica-Oblique",
    ("helvetica", True, True): "Helvetica-BoldOblique",
    ("times", False, False): "Times-Roman",
    ("times", True, False): "Times-Bold",
    ("times", False, True): "Times-Italic",
    ("times", True, True): "Times-BoldItalic",
    ("courier", False, False): "Courier",
    ("courier", True, False): "Courier-Bold",
    ("courier", False, True): "Courier-Oblique",
    ("courier", True, True): "Courier-BoldOblique",
}

# Fonts that ship with the app (static/fonts, all SIL Open Font License -- see static/fonts/licenses)
# and are embedded (subset) into the PDF. They cover far more characters than the built-in fonts.
# The web UI loads the same files for the stage, so the preview and the export match.
# "files" maps (bold, italic) -> TTF basename; a family may lack some cuts (e.g. script fonts).
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts")
EMBEDDED_FONTS = {
    "dmsans": {"label": "DM Sans", "category": "sans", "files": {(False, False): "DMSans-Regular", (True, False): "DMSans-Bold", (False, True): "DMSans-Italic", (True, True): "DMSans-BoldItalic"}},
    "didactgothic": {"label": "Didact Gothic", "category": "sans", "files": {(False, False): "DidactGothic-Regular"}},
    "josefinsans": {"label": "Josefin Sans", "category": "sans", "files": {(False, False): "JosefinSans-Regular", (True, False): "JosefinSans-Bold", (False, True): "JosefinSans-Italic", (True, True): "JosefinSans-BoldItalic"}},
    "jost": {"label": "Jost", "category": "sans", "files": {(False, False): "Jost-Regular", (True, False): "Jost-Bold", (False, True): "Jost-Italic", (True, True): "Jost-BoldItalic"}},
    "lato": {"label": "Lato", "category": "sans", "files": {(False, False): "Lato-Regular", (True, False): "Lato-Bold", (False, True): "Lato-Italic", (True, True): "Lato-BoldItalic"}},
    "montserrat": {"label": "Montserrat", "category": "sans", "files": {(False, False): "Montserrat-Regular", (True, False): "Montserrat-Bold", (False, True): "Montserrat-Italic", (True, True): "Montserrat-BoldItalic"}},
    "nunito": {"label": "Nunito", "category": "sans", "files": {(False, False): "Nunito-Regular", (True, False): "Nunito-Bold", (False, True): "Nunito-Italic", (True, True): "Nunito-BoldItalic"}},
    "opensans": {"label": "Open Sans", "category": "sans", "files": {(False, False): "OpenSans-Regular", (True, False): "OpenSans-Bold", (False, True): "OpenSans-Italic", (True, True): "OpenSans-BoldItalic"}},
    "poppins": {"label": "Poppins", "category": "sans", "files": {(False, False): "Poppins-Regular", (True, False): "Poppins-Bold", (False, True): "Poppins-Italic", (True, True): "Poppins-BoldItalic"}},
    "raleway": {"label": "Raleway", "category": "sans", "files": {(False, False): "Raleway-Regular", (True, False): "Raleway-Bold", (False, True): "Raleway-Italic", (True, True): "Raleway-BoldItalic"}},
    "roboto": {"label": "Roboto", "category": "sans", "files": {(False, False): "Roboto-Regular", (True, False): "Roboto-Bold", (False, True): "Roboto-Italic", (True, True): "Roboto-BoldItalic"}},
    "cormorantgaramond": {"label": "Cormorant Garamond", "category": "serif", "files": {(False, False): "CormorantGaramond-Regular", (True, False): "CormorantGaramond-Bold", (False, True): "CormorantGaramond-Italic", (True, True): "CormorantGaramond-BoldItalic"}},
    "ebgaramond": {"label": "EB Garamond", "category": "serif", "files": {(False, False): "EBGaramond-Regular", (True, False): "EBGaramond-Bold", (False, True): "EBGaramond-Italic", (True, True): "EBGaramond-BoldItalic"}},
    "lora": {"label": "Lora", "category": "serif", "files": {(False, False): "Lora-Regular", (True, False): "Lora-Bold", (False, True): "Lora-Italic", (True, True): "Lora-BoldItalic"}},
    "merriweather": {"label": "Merriweather", "category": "serif", "files": {(False, False): "Merriweather-Regular", (True, False): "Merriweather-Bold", (False, True): "Merriweather-Italic", (True, True): "Merriweather-BoldItalic"}},
    "playfairdisplay": {"label": "Playfair Display", "category": "serif", "files": {(False, False): "PlayfairDisplay-Regular", (True, False): "PlayfairDisplay-Bold", (False, True): "PlayfairDisplay-Italic", (True, True): "PlayfairDisplay-BoldItalic"}},
    "caveat": {"label": "Caveat", "category": "script", "files": {(False, False): "Caveat-Regular", (True, False): "Caveat-Bold"}},
    "dancingscript": {"label": "Dancing Script", "category": "script", "files": {(False, False): "DancingScript-Regular", (True, False): "DancingScript-Bold"}},
    "greatvibes": {"label": "Great Vibes", "category": "script", "files": {(False, False): "GreatVibes-Regular"}},
    "pacifico": {"label": "Pacifico", "category": "script", "files": {(False, False): "Pacifico-Regular"}},
}

# Built-in PDF fonts, shown first in the font list.
STANDARD_FONT_LABELS = {"helvetica": "Helvetica", "times": "Times", "courier": "Courier"}


def _embedded_font(family, bold, italic):
    """
    Registers (once) and returns the reportlab font name for an embedded family's cut. A missing
    cut falls back to the nearest one the family has, the same way the web UI draws it.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    files = EMBEDDED_FONTS[family]["files"]
    key = (bool(bold), bool(italic))
    for candidate in (key, (key[0], False), (False, key[1]), (False, False)):
        if candidate in files:
            name = files[candidate]
            break
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS_DIR, name + ".ttf")))
    return name


def text_font_catalog():
    """Font list for the web UI: [{key, label, category, bold, italic, files}], in display order."""
    catalog = [{"key": k, "label": v, "category": "standard", "bold": True, "italic": True, "files": None}
               for k, v in STANDARD_FONT_LABELS.items()]
    for key, info in EMBEDDED_FONTS.items():
        files = info["files"]
        catalog.append({
            "key": key,
            "label": info["label"],
            "category": info["category"],
            "bold": (True, False) in files,
            "italic": (False, True) in files,
            "files": {("bold" if b else "normal") + "-" + ("italic" if i else "normal"): name
                      for (b, i), name in files.items()},
        })
    return catalog


def _supported_codepoints(font_name):
    """Set of code points a registered TrueType font can draw (None = built-in Windows-1252 font)."""
    from reportlab.pdfbase import pdfmetrics

    face = getattr(pdfmetrics.getFont(font_name), "face", None)
    charmap = getattr(face, "charToGlyph", None)
    return set(charmap) if charmap else None


@functools.lru_cache(maxsize=None)
def _coverage_ranges(font_name):
    codepoints = sorted(c for c in _supported_codepoints(font_name) if c >= 0x20)
    ranges = []
    for cp in codepoints:
        if ranges and cp == ranges[-1][1] + 1:
            ranges[-1][1] = cp
        else:
            ranges.append([cp, cp])
    return ranges


def text_font_coverage(family="montserrat"):
    """
    Code point ranges an embedded family can draw, as [[lo, hi], ...]. The web UI uses this to warn
    about characters that would be replaced with '?' when the PDF is written.
    """
    return [list(r) for r in _coverage_ranges(_embedded_font(family, False, False))]


def all_text_font_coverage():
    """{family: ranges} for every embedded family (the built-in fonts are Windows-1252)."""
    return {family: text_font_coverage(family) for family in EMBEDDED_FONTS}


def _process_text_item(item):
    """
    Validates a text overlay dict and returns its normalized drawing parameters,
    or None when the text is blank (nothing to draw).
    """
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics

    text = str(item.get("text") or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return None

    family = str(item.get("font_family") or "helvetica").lower()
    bold = bool(item.get("bold"))
    italic = bool(item.get("italic"))
    if family in EMBEDDED_FONTS:
        font_name = _embedded_font(family, bold, italic)
    else:
        font_name = TEXT_FONTS.get((family, bold, italic))
    if font_name is None:
        raise ValueError(f"Unsupported font family: {family}")

    # Swap anything the font can't draw for '?' instead of emitting missing-glyph boxes.
    # The built-in PDF fonts only cover Windows-1252; embedded fonts have their own character maps.
    supported = _supported_codepoints(font_name)
    if supported is None:
        text = text.encode("cp1252", errors="replace").decode("cp1252")
    else:
        text = "".join(ch if (ch == "\n" or ord(ch) in supported) else "?" for ch in text)
    lines = text.split("\n")

    try:
        font_size = float(item.get("font_size") or 16)
    except (TypeError, ValueError):
        raise ValueError("Invalid font size for text overlay.")
    font_size = max(TEXT_MIN_FONT_SIZE, min(TEXT_MAX_FONT_SIZE, font_size))

    try:
        color = HexColor(str(item.get("color") or "#000000"))
    except (ValueError, TypeError):
        raise ValueError(f"Invalid text color: {item.get('color')}")

    natural_width = max(pdfmetrics.stringWidth(line, font_name, font_size) for line in lines)
    natural_height = len(lines) * TEXT_LINE_HEIGHT * font_size

    return {
        "lines": lines,
        "font_name": font_name,
        "font_size": font_size,
        "color": color,
        # The client measures the box it shows; fall back to our own metrics.
        "width": float(item.get("width") or natural_width),
        "height": float(item.get("height") or natural_height),
    }


def _draw_text_item(can, sig):
    """Draws a processed text overlay with its top-left corner at (sig['x'], top edge)."""
    top = sig["pdf_y"] + sig["height"]
    can.setFillColor(sig["color"])
    can.setFont(sig["font_name"], sig["font_size"])
    for i, line in enumerate(sig["lines"]):
        baseline = top - (TEXT_BASELINE + i * TEXT_LINE_HEIGHT) * sig["font_size"]
        can.drawString(sig["x"], baseline, line)


def add_signature_to_pdf(
    input_path,
    output_path,
    signature_img=None,
    pages_spec=None,
    x=50,
    y=50,
    width=150,
    height=50,
    password=None,
    y_from_top=False,
    signatures=None,
    rotation=0
):
    """
    Adds single or multiple signature image and text overlays to specified pages of a PDF document.
    
    :param input_path: Path to input PDF file
    :param output_path: Path to output PDF file
    :param signature_img: Single signature image path / base64 / bytes
    :param pages_spec: Target pages spec
    :param x: X position in PDF points
    :param y: Y position in PDF points
    :param width: Signature width in PDF points
    :param height: Signature height in PDF points
    :param password: Password if PDF is encrypted
    :param y_from_top: Measure Y coordinate from top of page if True
    :param signatures: Optional list of signature dict items for multi-signature placement:
                       [{ 'signature_img': ..., 'pages_spec': ..., 'x': ..., 'y': ..., 'width': ..., 'height': ..., 'rotation': ..., 'y_from_top': ... }]
                       An item with 'type': 'text' draws text instead of an image and takes
                       'text', 'font_family' (helvetica | times | courier | a key of EMBEDDED_FONTS), 'font_size' (points),
                       'bold', 'italic' and 'color' (hex) in place of 'signature_img'.
    :param rotation: Rotation angle in degrees clockwise (0 to 360)
    """
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    reader = PdfReader(input_path)

    if reader.is_encrypted:
        if not password:
            raise ValueError("The PDF is encrypted. Please provide a password.")
        decrypted = reader.decrypt(password)
        if decrypted == 0:
            raise ValueError("Incorrect password for the PDF file.")

    total_pages = len(reader.pages)

    if not signatures:
        if not signature_img:
            raise ValueError("No signature image or signatures list provided.")
        signatures = [{
            "signature_img": signature_img,
            "pages_spec": pages_spec,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "rotation": rotation,
            "y_from_top": y_from_top
        }]

    # Process all signature items
    processed_sigs = []
    for sig_item in signatures:
        is_text = sig_item.get("type") == "text"
        if is_text:
            text_props = _process_text_item(sig_item)
            if text_props is None:
                continue
            img_obj = None
        else:
            text_props = None
            img_obj = _process_image_input(sig_item.get("signature_img") or signature_img)
        spec = sig_item.get("pages_spec")
        if spec is None or spec == "":
            spec = sig_item.get("page")
        if spec is None or spec == "":
            spec = pages_spec
        target_idxs = set(parse_page_range(spec, total_pages))
        rot_val = float(sig_item.get("rotation", 0) or rotation or 0)
        opacity_val = float(sig_item.get("opacity", 1.0) if sig_item.get("opacity") is not None else 1.0)
        z_index_val = int(sig_item.get("z_index", 1) or sig_item.get("zIndex", 1) or 1)

        processed_sigs.append({
            "img_obj": img_obj,
            "text": text_props,
            "target_indices": target_idxs,
            "x": float(sig_item.get("x", 50)),
            "y": float(sig_item.get("y", 50)),
            "width": text_props["width"] if is_text else float(sig_item.get("width", 150)),
            "height": text_props["height"] if is_text else float(sig_item.get("height", 50)),
            "rotation": rot_val,
            "opacity": opacity_val,
            "z_index": z_index_val,
            "y_from_top": sig_item.get("y_from_top", True)
        })

    writer = PdfWriter()

    for idx, page in enumerate(reader.pages):
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        matching_sigs = [s for s in processed_sigs if idx in s["target_indices"]]
        matching_sigs.sort(key=lambda s: s["z_index"])

        if matching_sigs:
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            for sig in matching_sigs:
                pdf_y = page_height - sig["y"] - sig["height"] if sig["y_from_top"] else sig["y"]
                rot = float(sig.get("rotation", 0) or 0) % 360
                opacity = float(sig.get("opacity", 1.0))

                can.saveState()
                if opacity < 1.0:
                    try:
                        can.setFillAlpha(opacity)
                        can.setStrokeAlpha(opacity)
                    except AttributeError:
                        pass

                if rot != 0:
                    center_x = sig["x"] + sig["width"] / 2.0
                    center_y = pdf_y + sig["height"] / 2.0
                    can.translate(center_x, center_y)
                    can.rotate(-rot)
                    can.translate(-center_x, -center_y)

                if sig["text"]:
                    _draw_text_item(can, {**sig["text"], "x": sig["x"], "pdf_y": pdf_y,
                                          "width": sig["width"], "height": sig["height"]})
                else:
                    can.drawImage(
                        ImageReader(sig["img_obj"]),
                        sig["x"],
                        pdf_y,
                        width=sig["width"],
                        height=sig["height"],
                        mask='auto',
                        preserveAspectRatio=True,
                        anchor='c'
                    )

                can.restoreState()

            can.save()
            packet.seek(0)

            overlay_pdf = PdfReader(packet)
            overlay_page = overlay_pdf.pages[0]
            new_page = writer.add_page(page)
            new_page.merge_page(overlay_page)
        else:
            writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)




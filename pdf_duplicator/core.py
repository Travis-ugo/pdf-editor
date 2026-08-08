import os

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    from PyPDF2 import PdfReader, PdfWriter


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
    signatures=None
):
    """
    Adds single or multiple signature image overlays to specified pages of a PDF document.
    
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
                       [{ 'signature_img': ..., 'pages_spec': ..., 'x': ..., 'y': ..., 'width': ..., 'height': ..., 'y_from_top': ... }]
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
            "y_from_top": y_from_top
        }]

    # Process all signature items
    processed_sigs = []
    for sig_item in signatures:
        s_img = sig_item.get("signature_img") or signature_img
        img_obj = _process_image_input(s_img)
        spec = sig_item.get("pages_spec")
        if spec is None or spec == "":
            spec = sig_item.get("page")
        if spec is None or spec == "":
            spec = pages_spec
        target_idxs = set(parse_page_range(spec, total_pages))
        processed_sigs.append({
            "img_obj": img_obj,
            "target_indices": target_idxs,
            "x": float(sig_item.get("x", 50)),
            "y": float(sig_item.get("y", 50)),
            "width": float(sig_item.get("width", 150)),
            "height": float(sig_item.get("height", 50)),
            "y_from_top": sig_item.get("y_from_top", True)
        })

    writer = PdfWriter()

    for idx, page in enumerate(reader.pages):
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        matching_sigs = [s for s in processed_sigs if idx in s["target_indices"]]

        if matching_sigs:
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            for sig in matching_sigs:
                pdf_y = page_height - sig["y"] - sig["height"] if sig["y_from_top"] else sig["y"]
                can.drawImage(ImageReader(sig["img_obj"]), sig["x"], pdf_y, width=sig["width"], height=sig["height"], mask='auto')
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




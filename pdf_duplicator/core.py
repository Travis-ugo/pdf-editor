import os
from pypdf import PdfReader, PdfWriter

def parse_page_range(pages_spec, total_pages):
    """
    Parses a string representing pages/ranges and returns a list of 0-based indices.
    Example specs: '1', '1-3', '1,2,5', '1-3,5'
    """
    if not pages_spec:
        return list(range(total_pages))
    
    indices = []
    parts = pages_spec.split(',')
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

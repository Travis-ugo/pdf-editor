import click
import sys
from pdf_duplicator.core import duplicate_pdf, duplicate_pages, add_signature_to_pdf, merge_pdfs

@click.group()
def cli():
    """PDF Duplicator - A tool to duplicate PDFs, duplicate pages, and sign PDFs."""
    pass

@cli.command()
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('output_file', type=click.Path(writable=True, dir_okay=False))
@click.option('--password', '-p', default=None, help='Password for encrypted PDF files.')
def clone(input_file, output_file, password):
    """
    Clone a PDF file. If the file is encrypted, it decrypts and clones a decrypted version.
    """
    click.echo(f"Cloning {input_file} to {output_file}...")
    
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    try:
        reader = PdfReader(input_file)
        is_encrypted = reader.is_encrypted
    except Exception as e:
        click.secho(f"Error reading file: {e}", fg="red", err=True)
        sys.exit(1)
        
    if is_encrypted and not password:
        password = click.prompt("PDF is encrypted. Enter password", hide_input=True)
        
    try:
        duplicate_pdf(input_file, output_file, password)
        click.secho("Success! PDF cloned successfully.", fg="green")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

@cli.command(name="duplicate-pages")
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('output_file', type=click.Path(writable=True, dir_okay=False))
@click.option('--pages', '-g', default=None, help='Pages to duplicate (e.g. "1", "1-3", "1,2,5"). Defaults to all pages.')
@click.option('--count', '-c', default=2, type=int, help='Number of times to duplicate each page/sequence.')
@click.option('--password', '-p', default=None, help='Password for encrypted PDF files.')
@click.option('--repeat-sequence', '-r', is_flag=True, help='Repeat the sequence of pages instead of duplicating individual pages.')
def duplicate_pgs(input_file, output_file, pages, count, password, repeat_sequence):
    """
    Duplicate pages within a PDF file a specified number of times.
    """
    click.echo(f"Duplicating pages of {input_file} to {output_file} (count={count})...")
    
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    try:
        reader = PdfReader(input_file)
        is_encrypted = reader.is_encrypted
    except Exception as e:
        click.secho(f"Error reading file: {e}", fg="red", err=True)
        sys.exit(1)
        
    if is_encrypted and not password:
        password = click.prompt("PDF is encrypted. Enter password", hide_input=True)
        
    try:
        duplicate_pages(input_file, output_file, pages_spec=pages, count=count, password=password, repeat_sequence=repeat_sequence)
        click.secho("Success! PDF pages duplicated successfully.", fg="green")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

@cli.command(name="add-signature")
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('output_file', type=click.Path(writable=True, dir_okay=False))
@click.option('--signature', '-s', required=True, type=click.Path(exists=True, dir_okay=False), help='Signature image file path.')
@click.option('--pages', '-g', default=None, help='Target pages (e.g. "1", "1-3", "1,3,5"). Defaults to all pages.')
@click.option('--x', default=50.0, type=float, help='X coordinate on PDF page.')
@click.option('--y', default=50.0, type=float, help='Y coordinate on PDF page.')
@click.option('--width', default=150.0, type=float, help='Width of signature.')
@click.option('--height', default=50.0, type=float, help='Height of signature.')
@click.option('--password', '-p', default=None, help='Password for encrypted PDF files.')
@click.option('--y-from-top', is_flag=True, help='Measure Y coordinate from top of page instead of bottom.')
@click.option('--rotation', '-r', default=0.0, type=float, help='Rotation angle in degrees clockwise (0-360).')
def add_sig(input_file, output_file, signature, pages, x, y, width, height, password, y_from_top, rotation):
    """
    Add a signature image overlay to a PDF file.
    """
    click.echo(f"Adding signature {signature} to {input_file} -> {output_file}...")
    
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    try:
        reader = PdfReader(input_file)
        is_encrypted = reader.is_encrypted
    except Exception as e:
        click.secho(f"Error reading file: {e}", fg="red", err=True)
        sys.exit(1)
        
    if is_encrypted and not password:
        password = click.prompt("PDF is encrypted. Enter password", hide_input=True)
        
    try:
        add_signature_to_pdf(
            input_file,
            output_file,
            signature_img=signature,
            pages_spec=pages,
            x=x,
            y=y,
            width=width,
            height=height,
            password=password,
            y_from_top=y_from_top,
            rotation=rotation
        )
        click.secho("Success! Signature added to PDF successfully.", fg="green")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)

@cli.command(name="merge")
@click.argument('input_files', nargs=-1, type=click.Path(exists=False, dir_okay=False), required=True)
@click.option('--output', '-o', default=None, type=click.Path(writable=True, dir_okay=False), help='Output PDF path. If omitted, the last argument is treated as the output file.')
@click.option('--password', '-p', multiple=True, help='Password(s) for encrypted input PDFs.')
def merge_cmd(input_files, output, password):
    """
    Merge multiple PDF files into a single output PDF.
    """
    import os
    files = list(input_files)
    if output:
        output_file = output
    else:
        if len(files) < 2:
            click.secho("Error: Please specify at least one input file and an output file path.", fg="red", err=True)
            sys.exit(1)
        output_file = files.pop()

    for f in files:
        if not os.path.exists(f):
            click.secho(f"Error: Input file '{f}' does not exist.", fg="red", err=True)
            sys.exit(1)

    passwords = list(password)
    pdf_inputs = []
    for idx, fpath in enumerate(files):
        pwd = passwords[idx] if idx < len(passwords) else (passwords[0] if len(passwords) == 1 else None)
        pdf_inputs.append({"path": fpath, "password": pwd})

    click.echo(f"Merging {len(files)} files into {output_file}...")
    try:
        merge_pdfs(pdf_inputs, output_file)
        click.secho("Success! PDFs merged successfully.", fg="green")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command(name="web")
@click.option('--host', default='127.0.0.1', help='Host address to bind to.')
@click.option('--port', default=5000, type=int, help='Port to listen on.')
@click.option('--debug', is_flag=True, help='Enable debug mode.')
def launch_web(host, port, debug):
    """
    Launch the Apple-standard Web UI application.
    """
    from pdf_duplicator.web import run_server
    click.secho(f"Starting Apple HIG PDF Duplicator Web UI on http://{host}:{port} ...", fg="cyan")
    run_server(host=host, port=port, debug=debug)


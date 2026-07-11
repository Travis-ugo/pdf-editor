import click
import sys
from pdf_duplicator.core import duplicate_pdf, duplicate_pages

@click.group()
def cli():
    """PDF Duplicator - A command line tool to duplicate PDFs and duplicate PDF pages."""
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
    
    from pypdf import PdfReader
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
    
    from pypdf import PdfReader
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

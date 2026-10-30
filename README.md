# PDF Duplicator

A lightweight, robust Python command-line interface (CLI) tool and library designed to duplicate PDF files, remove encryption passwords, and replicate/duplicate individual pages or sequences of pages within a PDF.

## Features

- **Clone / Decrypt PDFs**: Make a direct duplicate of any PDF file. If the file is password-encrypted, you can provide the password to output a fully decrypted PDF copy.
- **Duplicate Pages**: Replicate specific pages (using list/range syntax like `1-3,5`) or the entire document a specified number of times.
- **Flexible Ordering**: Replicate pages sequentially (e.g. page 1 twice, page 2 twice: `p1, p1, p2, p2`) or repeat the entire selected page sequence (e.g., `p1, p2, p1, p2`).
- **Interactive Prompts**: Securely prompts for passwords in the console if an encrypted file is detected.

### Opening other documents (web app)

The web editor opens more than PDFs: each file is converted to PDF on upload, then signed, annotated,
merged or duplicated like any PDF (saves are always PDF). See `pdf_duplicator/convert.py`.

- Built in: images (PNG, JPEG, GIF, BMP, TIFF incl. multi-page, WebP), SVG, plain text, Markdown,
  HTML, EPUB/XPS and other e-book formats.
- Word, PowerPoint, Excel, OpenDocument and RTF need [LibreOffice](https://www.libreoffice.org)
  (`brew install --cask libreoffice`). It's found on `PATH`, in `/Applications`, or via
  `SOFFICE_PATH`. Without it those files show a message saying so.

## Directory Structure

```text
pdf-duplicator/
├── pdf_duplicator/
│   ├── __init__.py      # Package entry point
│   ├── core.py          # Core logic (PDF operations & page parser)
│   └── cli.py           # Command-line interface definitions (Click commands)
├── tests/
│   └── test_core.py     # Unit test suite
├── .venv/               # Virtual environment directory
├── requirements.txt     # Dependencies (pypdf, click)
├── setup.py             # Packaging setup configuration
├── run.py               # Main CLI wrapper/execution entry point
└── README.md            # This documentation
```

## Setup & Installation

### Prerequisite

- Python 3.9 or higher

### Installation

1. Navigate to the project directory:
   ```bash
   cd /Users/travis/Software/pdf-duplicator
   ```

2. Create a virtual environment (if not already done):
   ```bash
   python3 -m venv .venv
   ```

3. Activate the virtual environment:
   - **macOS / Linux**:
     ```bash
     source .venv/bin/activate
     ```
   - **Windows**:
     ```cmd
     .venv\Scripts\activate
     ```

4. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage Guide

The tool provides two main subcommands: `clone` and `duplicate-pages`. You can run these commands via `run.py`.

### 1. Cloning a PDF (and Decrypting)

To make a direct copy of a PDF:
```bash
python run.py clone input.pdf output.pdf
```

If the PDF is encrypted, you can pass the password with `-p` or `--password`:
```bash
python run.py clone input.pdf output.pdf --password "my_secret_password"
```

If you don't supply a password for an encrypted PDF, you will be prompted to enter it securely. The resulting copy will be saved **without password protection** (decrypted).

### 2. Duplicating Pages Within a PDF

Use the `duplicate-pages` subcommand to replicate pages. By default, it duplicates **all pages twice**.

#### Replicate each page individually (Default)
This duplicates each page one after another:
```bash
# Results in: Page 1, Page 1, Page 2, Page 2, Page 3, Page 3
python run.py duplicate-pages input.pdf output.pdf --count 2
```

#### Repeat the entire sequence
To repeat the entire sequence of pages:
```bash
# Results in: Page 1, Page 2, Page 3, Page 1, Page 2, Page 3
python run.py duplicate-pages input.pdf output.pdf --count 2 --repeat-sequence
```

#### Replicate specific pages
You can specify which pages to process using `-g` or `--pages` with lists and ranges (1-indexed):
```bash
# Replicate pages 1, 2, 3, and 5 three times each
# Results in: Page 1, Page 1, Page 1, Page 2, Page 2, Page 2, ...
python run.py duplicate-pages input.pdf output.pdf --pages "1-3,5" --count 3
```

---

## Running Tests

Install the test tools once, then run everything from the project root:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests            # everything (~1 min)
.venv/bin/python -m pytest tests --ignore=tests/e2e   # skip the browser tests (~5 s)
```

- `tests/test_*.py`: the PDF engine (`core.py`) and the HTTP API (`test_web.py`). They use
  throwaway folders, never the real `output/`.
- `tests/e2e/`: drives the web app in Google Chrome with Playwright (open, type, draw, sign,
  save, then checks the PDF written to disk). Set `PDF_E2E_BROWSER=chromium` to use Playwright's
  own Chromium instead (`.venv/bin/playwright install chromium`). Skipped if Playwright is missing.

The unit tests also still run with plain `unittest`:
`.venv/bin/python -m unittest discover -s tests`.

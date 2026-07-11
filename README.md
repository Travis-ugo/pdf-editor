# PDF Duplicator

A lightweight, robust Python command-line interface (CLI) tool and library designed to duplicate PDF files, remove encryption passwords, and replicate/duplicate individual pages or sequences of pages within a PDF.

## Features

- **Clone / Decrypt PDFs**: Make a direct duplicate of any PDF file. If the file is password-encrypted, you can provide the password to output a fully decrypted PDF copy.
- **Duplicate Pages**: Replicate specific pages (using list/range syntax like `1-3,5`) or the entire document a specified number of times.
- **Flexible Ordering**: Replicate pages sequentially (e.g. page 1 twice, page 2 twice: `p1, p1, p2, p2`) or repeat the entire selected page sequence (e.g., `p1, p2, p1, p2`).
- **Interactive Prompts**: Securely prompts for passwords in the console if an encrypted file is detected.

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

To run the automated unit tests, make sure you are in the root directory of the project and execute:

```bash
PYTHONPATH=. .venv/bin/python3 -m unittest discover -s tests
```
# pdf-duplicator

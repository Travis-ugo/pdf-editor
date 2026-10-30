import io
import os
import stat
import tempfile
import unittest
import zipfile
from unittest import mock

import fitz
from PIL import Image

from pdf_duplicator import convert
from pdf_duplicator.convert import UnsupportedDocument, convert_to_pdf, document_kind


def minimal_docx(path, text):
    """A bare-bones .docx (just enough parts for Word/LibreOffice to open) with one paragraph."""
    parts = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>',
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return path


class ConvertTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = self.path("out.pdf")

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def write(self, name, data):
        path = self.path(name)
        with open(path, "wb" if isinstance(data, bytes) else "w", **({} if isinstance(data, bytes) else {"encoding": "utf-8"})) as f:
            f.write(data)
        return path

    def output(self):
        doc = fitz.open(self.out)
        self.addCleanup(doc.close)
        return doc

    def text(self):
        return "".join(page.get_text() for page in self.output())


class TestDocumentKind(ConvertTestCase):
    def test_kinds(self):
        for name, kind in (("a.PDF", "pdf"), ("photo.JPG", "image"), ("scan.tiff", "image"), ("x.svg", "ebook"),
                           ("notes.txt", "text"), ("data.csv", "text"), ("README.md", "markdown"),
                           ("page.html", "html"), ("letter.docx", "office"), ("deck.pptx", "office"),
                           ("sheet.xlsx", "office"), ("old.doc", "office"), ("memo.rtf", "office"),
                           ("app.exe", None), ("noext", None), ("", None), (None, None)):
            with self.subTest(name=name):
                self.assertEqual(document_kind(name), kind)


class TestConvertNative(ConvertTestCase):
    def test_pdf_is_copied_unchanged(self):
        src = fitz.open()
        src.new_page().insert_text((72, 72), "Original")
        path = self.path("in.pdf")
        src.save(path)
        self.assertEqual(convert_to_pdf(path, self.out), "pdf")
        self.assertIn("Original", self.text())

    def test_png_becomes_one_page_of_the_same_aspect(self):
        path = self.path("photo.png")
        Image.new("RGB", (400, 200), (200, 30, 30)).save(path)
        self.assertEqual(convert_to_pdf(path, self.out), "image")
        doc = self.output()
        self.assertEqual(len(doc), 1)
        self.assertAlmostEqual(doc[0].rect.width / doc[0].rect.height, 2.0, places=2)
        self.assertEqual(len(doc[0].get_images()), 1)

    def test_jpeg_and_transparent_png(self):
        for name, mode, fmt in (("p.jpg", "RGB", "JPEG"), ("t.png", "RGBA", "PNG"), ("g.gif", "P", "GIF"), ("b.bmp", "RGB", "BMP")):
            with self.subTest(name=name):
                path = self.path(name)
                Image.new(mode, (50, 80)).save(path, format=fmt)
                convert_to_pdf(path, self.out)
                self.assertEqual(len(self.output()), 1)

    def test_webp(self):
        path = self.path("w.webp")
        Image.new("RGB", (60, 30), (0, 128, 0)).save(path, format="WEBP")
        convert_to_pdf(path, self.out)
        self.assertEqual(len(self.output()), 1)

    def test_multipage_tiff_keeps_every_page(self):
        path = self.path("scan.tiff")
        frames = [Image.new("RGB", (100, 140), c) for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
        frames[0].save(path, save_all=True, append_images=frames[1:])
        convert_to_pdf(path, self.out)
        self.assertEqual(len(self.output()), 3)

    def test_corrupt_image_is_a_clear_error(self):
        path = self.write("broken.png", b"not really a png")
        with self.assertRaises(UnsupportedDocument):
            convert_to_pdf(path, self.out)

    def test_svg(self):
        path = self.write("logo.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
                                      '<rect width="200" height="100" fill="red"/><text x="10" y="50">Logo</text></svg>')
        convert_to_pdf(path, self.out)
        doc = self.output()
        self.assertEqual((doc[0].rect.width, doc[0].rect.height), (200, 100))

    def test_plain_text_wraps_and_paginates(self):
        lines = [f"Line {i}: " + "word " * 30 for i in range(1, 201)]
        path = self.write("notes.txt", "\n".join(lines))
        self.assertEqual(convert_to_pdf(path, self.out), "text")
        doc = self.output()
        self.assertGreater(len(doc), 3)
        self.assertEqual((doc[0].rect.width, doc[0].rect.height), (612, 792))
        text = self.text()
        self.assertIn("Line 1:", text)
        self.assertIn("Line 200:", text)
        # Nothing runs off the right edge: wrapped text stays within the 1-inch margins
        for page in doc:
            for block in page.get_text("blocks"):
                self.assertLessEqual(block[2], 612 - 72 + 1)

    def test_text_is_not_interpreted_as_html(self):
        path = self.write("code.txt", "<b>not bold</b> & <script>x</script>")
        convert_to_pdf(path, self.out)
        self.assertIn("<b>not bold</b> & <script>x</script>", self.text())

    def test_text_encodings(self):
        sample = "naïve café — Ελληνικά Кириллица 中文"
        for name, data in (("utf8.txt", sample.encode("utf-8")), ("bom.txt", b"\xef\xbb\xbf" + sample.encode("utf-8")),
                           ("utf16.txt", sample.encode("utf-16"))):
            with self.subTest(name=name):
                convert_to_pdf(self.write(name, data), self.out)
                self.assertIn(sample, self.text().replace("\n", " "))
        # Old Windows files that aren't valid UTF-8 still open (as Windows-1252)
        convert_to_pdf(self.write("win.txt", "café".encode("cp1252")), self.out)
        self.assertIn("café", self.text())

    def test_empty_text_file_gives_one_blank_page(self):
        convert_to_pdf(self.write("empty.txt", ""), self.out)
        self.assertEqual(len(self.output()), 1)

    def test_markdown_is_rendered(self):
        md = "# Title\n\nSome **bold** text.\n\n- one\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```\ncode()\n```\n"
        self.assertEqual(convert_to_pdf(self.write("README.md", md), self.out), "markdown")
        text = self.text()
        for expected in ("Title", "bold", "one", "two", "code()"):
            self.assertIn(expected, text)
        self.assertNotIn("**", text)
        self.assertNotIn("# Title", text)
        spans = [s for b in self.output()[0].get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]]
        title = next(s for s in spans if s["text"] == "Title")
        body = next(s for s in spans if "Some" in s["text"])
        self.assertGreater(title["size"], body["size"])

    def test_html(self):
        convert_to_pdf(self.write("page.html", "<h1>Hello</h1><p>World</p>"), self.out)
        self.assertIn("Hello", self.text())
        self.assertIn("World", self.text())

    def test_unsupported_type(self):
        path = self.write("app.exe", b"MZ")
        with self.assertRaises(UnsupportedDocument) as ctx:
            convert_to_pdf(path, self.out)
        self.assertIn(".exe", str(ctx.exception))

    def test_filename_decides_the_format(self):
        # Uploads are stored under a temp name; the user's file name says what it is
        path = self.write("upload.bin", "plain words")
        self.assertEqual(convert_to_pdf(path, self.out, filename="notes.txt"), "text")
        self.assertIn("plain words", self.text())


class TestConvertOffice(ConvertTestCase):
    """The LibreOffice path, driven by a fake `soffice` so it runs without LibreOffice installed."""

    def fake_soffice(self, body):
        path = self.path("soffice")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n" + body)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        return path

    def test_without_libreoffice_explains_how_to_get_it(self):
        with mock.patch.object(convert, "find_soffice", return_value=None):
            with self.assertRaises(UnsupportedDocument) as ctx:
                convert_to_pdf(minimal_docx(self.path("a.docx"), "x"), self.out)
        self.assertIn("LibreOffice", str(ctx.exception))
        self.assertIn(".docx", str(ctx.exception))

    def test_runs_headless_with_a_private_profile_and_picks_up_the_pdf(self):
        made = fitz.open()
        made.new_page().insert_text((72, 72), "From LibreOffice")
        made.save(self.path("made.pdf"))
        log = self.path("args.log")
        soffice = self.fake_soffice(
            f'echo "$@" > "{log}"\n'
            'while [ $# -gt 0 ]; do [ "$1" = "--outdir" ] && out="$2"; last="$1"; shift; done\n'
            f'cp "{self.path("made.pdf")}" "$out/document.pdf"\n')
        with mock.patch.dict(os.environ, {"SOFFICE_PATH": soffice}):
            kind = convert_to_pdf(minimal_docx(self.path("letter.docx"), "x"), self.out)
        self.assertEqual(kind, "office")
        self.assertIn("From LibreOffice", self.text())
        with open(log) as f:
            args = f.read()
        for flag in ("--headless", "--convert-to pdf", "-env:UserInstallation=file://"):
            self.assertIn(flag, args)
        self.assertTrue(args.strip().endswith("document.docx"))

    def test_libreoffice_failure_is_reported(self):
        soffice = self.fake_soffice('echo "Error: source file could not be loaded" >&2\nexit 1\n')
        with mock.patch.dict(os.environ, {"SOFFICE_PATH": soffice}):
            with self.assertRaises(UnsupportedDocument) as ctx:
                convert_to_pdf(self.write("bad.docx", b"garbage"), self.out)
        self.assertIn("could not be loaded", str(ctx.exception))
        self.assertFalse(os.path.exists(self.out))

    def test_libreoffice_timeout(self):
        soffice = self.fake_soffice("sleep 5\n")
        with mock.patch.dict(os.environ, {"SOFFICE_PATH": soffice}), mock.patch.object(convert, "OFFICE_TIMEOUT_S", 0.5):
            with self.assertRaises(UnsupportedDocument) as ctx:
                convert_to_pdf(self.write("slow.docx", b"x"), self.out)
        self.assertIn("too long", str(ctx.exception))

    @unittest.skipUnless(convert.find_soffice(), "LibreOffice isn't installed")
    def test_real_libreoffice_converts_a_docx(self):
        convert_to_pdf(minimal_docx(self.path("real.docx"), "Signed agreement text"), self.out)
        self.assertIn("Signed agreement text", self.text())


if __name__ == "__main__":
    unittest.main()

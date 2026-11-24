"""Redaction: content under a redact box must be gone from the saved file, not just covered."""
import io
import os
import tempfile
import unittest
import zlib

import fitz
from PIL import Image
from reportlab.pdfgen import canvas

from pdf_duplicator.core import add_signature_to_pdf, apply_redactions


def displayed_word_rect(page, word):
    """Where `word` appears on the page as displayed (crop box, after /Rotate), origin top-left:
    the space the editor places items in."""
    for w in page.get_text("words"):
        if w[4] == word:
            return fitz.Rect(w[:4]) * page.rotation_matrix
    raise AssertionError(f"{word!r} not on page")


def redact_item(rect, page=1, color="#000000", pad=1.0, **extra):
    return {"type": "redact", "x": rect.x0 - pad, "y": rect.y0 - pad, "width": rect.width + 2 * pad,
            "height": rect.height + 2 * pad, "page": page, "color": color, "y_from_top": True, **extra}


def all_stream_bytes(path):
    """Every stream in the file, decompressed, so a test can tell if removed text is still hiding."""
    doc = fitz.open(path)
    try:
        out = b""
        for xref in range(1, doc.xref_length()):
            try:
                if doc.xref_is_stream(xref):
                    out += doc.xref_stream(xref) or b""
            except Exception:
                pass
        return out
    finally:
        doc.close()


class RedactTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.dir, name)

    def make_pdf(self, name="in.pdf", background=None, image=False, rotation=0, cropbox=None, password=None):
        buf = io.BytesIO()
        can = canvas.Canvas(buf, pagesize=(612, 792))
        if background:
            can.setFillColorRGB(*background)
            can.rect(0, 0, 612, 792, stroke=0, fill=1)
        if image:
            img = io.BytesIO()
            Image.new("RGB", (100, 100), (255, 0, 0)).save(img, format="PNG")
            img.seek(0)
            from reportlab.lib.utils import ImageReader
            can.drawImage(ImageReader(img), 300, 300, width=200, height=200)
        can.setFillColorRGB(0, 0, 0)
        can.setFont("Helvetica", 20)
        can.drawString(72, 700, "Account SECRET1234 belongs to Ada")
        can.drawString(72, 650, "Keep this line")
        can.save()
        doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        for page in doc:
            if cropbox:
                page.set_cropbox(fitz.Rect(*cropbox))
            page.set_rotation(rotation)
        path = self.path(name)
        if password:
            doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
        else:
            doc.save(path)
        doc.close()
        return path

    def word_rect(self, path, word):
        doc = fitz.open(path)
        try:
            return displayed_word_rect(doc[0], word)
        finally:
            doc.close()

    def text(self, path):
        doc = fitz.open(path)
        try:
            return doc[0].get_text()
        finally:
            doc.close()

    def pixel(self, path, x, y):
        """RGB at displayed point (x, y) of page 1."""
        doc = fitz.open(path)
        try:
            pix = doc[0].get_pixmap(clip=fitz.Rect(x, y, x + 1, y + 1))
            return tuple(pix.samples[:3])
        finally:
            doc.close()

    # --- tests ----------------------------------------------------------------------------------

    def test_text_under_box_is_removed_from_the_file(self):
        src = self.make_pdf()
        out = self.path("out.pdf")
        rect = self.word_rect(src, "SECRET1234")
        add_signature_to_pdf(src, out, signatures=[redact_item(rect)])

        text = self.text(out)
        self.assertNotIn("SECRET1234", text)
        self.assertIn("Account", text)          # neighbours on the same line survive
        self.assertIn("Keep this line", text)
        # Not merely hidden: the characters are gone from every stream in the file.
        self.assertNotIn(b"SECRET1234", all_stream_bytes(out))
        self.assertNotIn(b"SECRET1234", zlib.compress(b"") + open(out, "rb").read())
        # The box is painted with the fill color
        self.assertEqual(self.pixel(out, rect.x0 + rect.width / 2, rect.y0 + rect.height / 2), (0, 0, 0))

    def test_fill_color_and_page_background_survive(self):
        cream = (1, 240 / 255, 200 / 255)
        src = self.make_pdf(background=cream)
        out = self.path("out.pdf")
        rect = self.word_rect(src, "SECRET1234")
        add_signature_to_pdf(src, out, signatures=[redact_item(rect, color="#fff0c8")])
        self.assertNotIn("SECRET1234", self.text(out))
        inside = self.pixel(out, rect.x0 + rect.width / 2, rect.y0 + rect.height / 2)
        outside = self.pixel(out, 400, 400)
        close = lambda a, b: all(abs(x - y) <= 2 for x, y in zip(a, b))
        self.assertTrue(close(inside, (255, 240, 200)), inside)
        # The full-page background rectangle isn't inside the box, so it's kept
        self.assertTrue(close(outside, (255, 240, 200)), outside)
        self.assertIn("Keep this line", self.text(out))

    def test_image_pixels_under_box_are_blanked(self):
        src = self.make_pdf(image=True)
        out = self.path("out.pdf")
        # The red image covers displayed (300..500, 292..492); redact its left half
        box = {"type": "redact", "x": 300, "y": 292, "width": 100, "height": 200, "page": 1,
               "color": "#ffffff", "y_from_top": True}
        add_signature_to_pdf(src, out, signatures=[box])
        self.assertEqual(self.pixel(out, 350, 390), (255, 255, 255))
        self.assertEqual(self.pixel(out, 450, 390), (255, 0, 0))
        # The pixels themselves changed, not just a white box drawn on top
        doc = fitz.open(out)
        try:
            imgs = doc[0].get_images()
            self.assertEqual(len(imgs), 1)
            data = fitz.Pixmap(doc, imgs[0][0])
            self.assertEqual(tuple(data.pixel(10, 50)[:3]), (255, 255, 255))
            self.assertEqual(tuple(data.pixel(90, 50)[:3]), (255, 0, 0))
            self.assertEqual(len(doc[0].get_drawings()), 1)  # only the fill box
        finally:
            doc.close()

    def test_rotated_page_uses_displayed_coordinates(self):
        for rotation in (90, 180, 270):
            with self.subTest(rotation=rotation):
                src = self.make_pdf(name=f"r{rotation}.pdf", rotation=rotation)
                out = self.path(f"r{rotation}-out.pdf")
                rect = self.word_rect(src, "SECRET1234")
                add_signature_to_pdf(src, out, signatures=[redact_item(rect)])
                text = self.text(out)
                self.assertNotIn("SECRET1234", text)
                self.assertIn("Account", text)
                self.assertIn("Keep this line", text)

    def test_cropped_page_uses_displayed_coordinates(self):
        src = self.make_pdf(cropbox=(50, 50, 562, 742))
        out = self.path("out.pdf")
        rect = self.word_rect(src, "SECRET1234")
        add_signature_to_pdf(src, out, signatures=[redact_item(rect)])
        text = self.text(out)
        self.assertNotIn("SECRET1234", text)
        self.assertIn("Account", text)

    def test_other_items_are_drawn_on_top_of_the_redacted_page(self):
        src = self.make_pdf()
        out = self.path("out.pdf")
        rect = self.word_rect(src, "SECRET1234")
        add_signature_to_pdf(src, out, signatures=[
            redact_item(rect),
            {"type": "text", "text": "REDACTED BY ADA", "font_family": "helvetica", "font_size": 12,
             "x": 72, "y": 400, "page": 1, "y_from_top": True},
        ])
        text = self.text(out)
        self.assertNotIn("SECRET1234", text)
        self.assertIn("REDACTED BY ADA", text)

    def test_encrypted_input(self):
        src = self.make_pdf(password="pw")
        out = self.path("out.pdf")
        add_signature_to_pdf(src, out, password="pw",
                             signatures=[redact_item(fitz.Rect(140, 80, 280, 100))])
        doc = fitz.open(out)
        try:
            self.assertFalse(doc.needs_pass)
        finally:
            doc.close()
        with self.assertRaises(ValueError):
            add_signature_to_pdf(src, self.path("bad.pdf"), password="wrong",
                                 signatures=[redact_item(fitz.Rect(140, 80, 280, 100))])

    def test_rotated_box_redacts_its_bounding_box(self):
        src = self.make_pdf()
        out = self.path("out.pdf")
        rect = self.word_rect(src, "SECRET1234")
        add_signature_to_pdf(src, out, signatures=[redact_item(rect, rotation=3)])
        self.assertNotIn("SECRET1234", self.text(out))

    def test_box_outside_page_or_empty_is_ignored(self):
        src = self.make_pdf()
        out = self.path("out.pdf")
        n = apply_redactions(src, out, [
            {"x": 900, "y": 900, "width": 50, "height": 50, "page": 1},
            {"x": 10, "y": 10, "width": 0, "height": 50, "page": 1},
        ])
        self.assertEqual(n, 0)
        self.assertIn("SECRET1234", self.text(out))

    def test_all_pages_spec(self):
        buf = io.BytesIO()
        can = canvas.Canvas(buf, pagesize=(612, 792))
        for _ in range(3):
            can.setFont("Helvetica", 20)
            can.drawString(72, 700, "CONFIDENTIAL header")
            can.showPage()
        can.save()
        src = self.path("multi.pdf")
        open(src, "wb").write(buf.getvalue())
        out = self.path("out.pdf")
        r = self.word_rect(src, "CONFIDENTIAL")
        box = {**redact_item(r), "pages_spec": "", "page": None}
        add_signature_to_pdf(src, out, signatures=[box])
        doc = fitz.open(out)
        try:
            self.assertTrue(all("CONFIDENTIAL" not in p.get_text() for p in doc))
            self.assertTrue(all("header" in p.get_text() for p in doc))
        finally:
            doc.close()


if __name__ == "__main__":
    unittest.main()

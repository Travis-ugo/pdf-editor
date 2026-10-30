import base64
import io
import os
import tempfile
import unittest

import fitz
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, NumberObject, RectangleObject

from pdf_duplicator.core import add_signature_to_pdf


def _png_data_url(width=100, height=40):
    """A solid black, fully opaque PNG: its bounding box on the rendered page is easy to find."""
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), (0, 0, 0, 255)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _ink_bbox(pdf_path, page_index=0):
    """Bounding box (x0, y0, x1, y1) of the dark pixels on a page rendered as a viewer shows it (1px = 1pt)."""
    doc = fitz.open(pdf_path)
    try:
        pix = doc[page_index].get_pixmap()
        size = (pix.width, pix.height)
        img = Image.frombytes("RGB", size, pix.samples).convert("L").point(lambda v: 255 if v < 128 else 0)
        return size, img.getbbox()
    finally:
        doc.close()


class TestOverlayPlacementOnUnusualPages(unittest.TestCase):
    """
    The web UI places items on the page as displayed (crop box, after /Rotate) -- the space
    PyMuPDF's page.rect reports. Whatever the page's internal geometry, an item placed at
    (50, 50) from the top-left must appear there in the output.
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _path(self, name):
        return os.path.join(self.tmpdir.name, name)

    def _make_pdf(self, rotation=0, mediabox=None, cropbox=None, inherited_rotation=False):
        path = self._path(f"in_{rotation}_{mediabox}_{cropbox}_{inherited_rotation}.pdf")
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        if mediabox:
            page.mediabox = RectangleObject(mediabox)
        if cropbox:
            page.cropbox = RectangleObject(cropbox)
        if rotation and not inherited_rotation:
            page.rotation = rotation
        if rotation and inherited_rotation:
            # /Rotate on the /Pages node, inherited by the page
            writer._root_object["/Pages"][NameObject("/Rotate")] = NumberObject(rotation)
        with open(path, "wb") as f:
            writer.write(f)
        return path

    def _items(self):
        box = {"x": 50, "y": 50, "width": 100, "height": 40, "page": 1, "y_from_top": True}
        return {
            "image": {**box, "signature_img": _png_data_url()},
            "ink": {**box, "type": "ink", "line_width": 2, "base_width": 100, "base_height": 40,
                    "strokes": [[[0, 0], [100, 0], [100, 40], [0, 40], [0, 0]]]},
        }

    def _assert_placed(self, input_path, kind):
        out = self._path(f"out_{kind}.pdf")
        add_signature_to_pdf(input_path, out, signatures=[self._items()[kind]])
        _, bbox = _ink_bbox(out)
        self.assertIsNotNone(bbox, "nothing was drawn")
        # The ink stroke is centred on the box edge, so allow a couple of points either way
        for got, want in zip(bbox, (50, 50, 150, 90)):
            self.assertAlmostEqual(got, want, delta=2, msg=f"{kind}: bbox {bbox}")

    def test_plain_page(self):
        path = self._make_pdf()
        for kind in ("image", "ink"):
            self._assert_placed(path, kind)

    def test_every_rotation(self):
        for rotation in (90, 180, 270):
            path = self._make_pdf(rotation=rotation)
            with self.subTest(rotation=rotation):
                for kind in ("image", "ink"):
                    self._assert_placed(path, kind)

    def test_negative_rotation_is_normalized(self):
        path = self._make_pdf(rotation=-90)
        self.assertEqual(PdfReader(path).pages[0].rotation % 360, 270)
        self._assert_placed(path, "ink")

    def test_rotation_inherited_from_page_tree(self):
        path = self._make_pdf(rotation=90, inherited_rotation=True)
        self.assertEqual(fitz.open(path)[0].rotation, 90)
        self._assert_placed(path, "ink")

    def test_mediabox_with_offset_origin(self):
        path = self._make_pdf(mediabox=[100, 100, 712, 892])
        for kind in ("image", "ink"):
            self._assert_placed(path, kind)

    def test_cropbox_smaller_than_mediabox(self):
        path = self._make_pdf(cropbox=[50, 60, 450, 700])
        self._assert_placed(path, "ink")

    def test_cropbox_and_rotation_together(self):
        path = self._make_pdf(rotation=90, cropbox=[50, 60, 450, 700])
        for kind in ("image", "ink"):
            self._assert_placed(path, kind)

    def test_image_stays_upright_on_rotated_page(self):
        # A wide image (100x40) must still look wide on a page displayed in landscape
        path = self._make_pdf(rotation=90)
        out = self._path("upright.pdf")
        add_signature_to_pdf(path, out, signatures=[self._items()["image"]])
        _, (x0, y0, x1, y1) = _ink_bbox(out)
        self.assertGreater(x1 - x0, y1 - y0)

    def test_text_on_rotated_page_reads_horizontally(self):
        path = self._make_pdf(rotation=90)
        out = self._path("text.pdf")
        add_signature_to_pdf(path, out, signatures=[{
            "type": "text", "text": "Approved", "font_family": "helvetica", "font_size": 20,
            "x": 50, "y": 50, "page": 1, "y_from_top": True}])
        doc = fitz.open(out)
        try:
            page = doc[0]
            words = page.get_text("words")
            self.assertEqual([w[4] for w in words], ["Approved"])
            # Word box in displayed coordinates: starts near (50, 50) and is wider than tall
            x0, y0, x1, y1 = fitz.Rect(words[0][:4]) * page.rotation_matrix
            self.assertAlmostEqual(min(x0, x1), 50, delta=3)
            self.assertAlmostEqual(min(y0, y1), 50, delta=6)
            self.assertGreater(abs(x1 - x0), abs(y1 - y0))
        finally:
            doc.close()

    def test_y_from_bottom_uses_displayed_height(self):
        # y measured from the bottom on a landscape-displayed page: bottom edge at 792 wide x 612 tall
        path = self._make_pdf(rotation=90)
        out = self._path("bottom.pdf")
        item = {**self._items()["ink"], "y": 50, "y_from_top": False}
        add_signature_to_pdf(path, out, signatures=[item])
        (w, h), bbox = _ink_bbox(out)
        self.assertEqual((w, h), (792, 612))
        self.assertAlmostEqual(bbox[3], h - 50, delta=2)


if __name__ == "__main__":
    unittest.main()

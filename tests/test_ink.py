import os
import unittest
import tempfile

import fitz
from pypdf import PdfWriter
from pdf_duplicator.core import add_signature_to_pdf


class TestInkOverlay(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.input_pdf = os.path.join(self.tmpdir.name, "sample.pdf")
        self.output_pdf = os.path.join(self.tmpdir.name, "out.pdf")

        writer = PdfWriter()
        writer.add_blank_page(width=500, height=700)
        writer.add_blank_page(width=500, height=700)
        with open(self.input_pdf, "wb") as f:
            writer.write(f)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _add(self, items):
        add_signature_to_pdf(self.input_pdf, self.output_pdf, signatures=items)

    def _drawings(self, page_index=0):
        doc = fitz.open(self.output_pdf)
        try:
            return doc[page_index].get_drawings(), doc[page_index].get_images()
        finally:
            doc.close()

    def _ink(self, **overrides):
        item = {"type": "ink", "strokes": [[[0, 0], [100, 50]]], "base_width": 100, "base_height": 50,
                "line_width": 2, "color": "#cc0000", "x": 50, "y": 100, "width": 100, "height": 50,
                "pages_spec": "1", "y_from_top": True}
        item.update(overrides)
        return item

    def test_ink_is_vector_not_image(self):
        self._add([self._ink()])
        drawings, images = self._drawings(0)
        self.assertEqual(images, [])
        self.assertEqual(len(drawings), 1)
        d = drawings[0]
        self.assertAlmostEqual(d["width"], 2, delta=0.01)
        r, g, b = d["color"]
        self.assertAlmostEqual(r, 0.8, delta=0.01)
        self.assertAlmostEqual(g, 0, delta=0.01)
        self.assertEqual(d["lineCap"][0], 1)

    def test_ink_position_uses_top_left_box(self):
        self._add([self._ink()])
        drawings, _ = self._drawings(0)
        rect = drawings[0]["rect"]  # fitz coords: y measured from the top, like the web UI
        self.assertAlmostEqual(rect.x0, 50, delta=0.5)
        self.assertAlmostEqual(rect.y0, 100, delta=0.5)
        self.assertAlmostEqual(rect.x1, 150, delta=0.5)
        self.assertAlmostEqual(rect.y1, 150, delta=0.5)
        # The first point is the top-left corner (base y is down, like the stage SVG).
        start = drawings[0]["items"][0][1]
        self.assertAlmostEqual(start.x, 50, delta=0.5)
        self.assertAlmostEqual(start.y, 100, delta=0.5)

    def test_resized_ink_scales_strokes_and_width(self):
        self._add([self._ink(width=200, height=100)])
        drawings, _ = self._drawings(0)
        rect = drawings[0]["rect"]
        self.assertAlmostEqual(rect.x1 - rect.x0, 200, delta=0.5)
        self.assertAlmostEqual(rect.y1 - rect.y0, 100, delta=0.5)
        self.assertAlmostEqual(drawings[0]["width"], 4, delta=0.01)

    def test_ink_only_on_target_pages(self):
        self._add([self._ink(pages_spec="2")])
        self.assertEqual(self._drawings(0)[0], [])
        self.assertEqual(len(self._drawings(1)[0]), 1)

    def test_check_mark_and_dot(self):
        check = self._ink(strokes=[[[1.7, 7.7], [5.6, 11.5], [12.6, 2.5]]], base_width=14, base_height=14,
                          width=14, height=14, line_width=1.8)
        dot = self._ink(strokes=[[[5, 5]]], base_width=10, base_height=10, width=10, height=10, x=300)
        self._add([check, dot])
        drawings, _ = self._drawings(0)
        self.assertEqual(len(drawings), 2)
        self.assertEqual(len(drawings[0]["items"]), 2)  # two line segments

    def test_empty_ink_is_skipped(self):
        self._add([self._ink(strokes=[[]])])
        self.assertEqual(self._drawings(0)[0], [])

    def test_invalid_ink_raises(self):
        with self.assertRaises(ValueError):
            self._add([self._ink(strokes="nope")])
        with self.assertRaises(ValueError):
            self._add([self._ink(strokes=[[["a", 1]]])])
        with self.assertRaises(ValueError):
            self._add([self._ink(color="not-a-color")])


if __name__ == "__main__":
    unittest.main()

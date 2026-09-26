import os
import unittest
import tempfile

import fitz
from pypdf import PdfReader, PdfWriter
from pdf_duplicator.core import (add_signature_to_pdf, text_font_coverage, text_font_catalog,
                                 EMBEDDED_FONTS, FONTS_DIR, TEXT_BASELINE)


class TestTextOverlay(unittest.TestCase):

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

    def _page_text(self, page_index):
        return PdfReader(self.output_pdf).pages[page_index].extract_text()

    def test_text_is_real_extractable_text(self):
        self._add([{"type": "text", "text": "Hello World", "x": 50, "y": 60,
                    "font_size": 20, "pages_spec": "1"}])
        self.assertIn("Hello World", self._page_text(0))
        self.assertNotIn("Hello World", self._page_text(1))

    def test_text_position_matches_layout_grid(self):
        self._add([{"type": "text", "text": "Hi", "x": 50, "y": 100,
                    "font_size": 20, "pages_spec": "1", "y_from_top": True}])
        doc = fitz.open(self.output_pdf)
        try:
            words = doc[0].get_text("words")
        finally:
            doc.close()
        x0, _, _, _, word = words[0][:5]
        self.assertEqual(word, "Hi")
        self.assertAlmostEqual(x0, 50, delta=1.5)
        # Baseline is TEXT_BASELINE * font_size below the box top (y=100 from top).
        doc = fitz.open(self.output_pdf)
        try:
            origin_y = doc[0].get_text("dict")["blocks"][0]["lines"][0]["spans"][0]["origin"][1]
        finally:
            doc.close()
        self.assertAlmostEqual(origin_y, 100 + TEXT_BASELINE * 20, delta=0.5)

    def test_multiline_text(self):
        self._add([{"type": "text", "text": "first\nsecond", "x": 40, "y": 40,
                    "font_size": 14, "pages_spec": "1"}])
        text = self._page_text(0)
        self.assertIn("first", text)
        self.assertIn("second", text)

    def test_font_style_and_color(self):
        self._add([{"type": "text", "text": "Styled", "x": 40, "y": 40, "font_size": 18,
                    "font_family": "times", "bold": True, "italic": True,
                    "color": "#ff0000", "pages_spec": "1"}])
        doc = fitz.open(self.output_pdf)
        try:
            span = doc[0].get_text("dict")["blocks"][0]["lines"][0]["spans"][0]
        finally:
            doc.close()
        self.assertIn("Times", span["font"])
        self.assertIn("Bold", span["font"])
        self.assertEqual(span["color"], 0xFF0000)

    def test_text_mixed_with_rotation_and_opacity(self):
        self._add([{"type": "text", "text": "Rotated", "x": 100, "y": 100, "font_size": 24,
                    "rotation": 45, "opacity": 0.5, "pages_spec": "2"}])
        self.assertEqual(len(PdfReader(self.output_pdf).pages), 2)
        self.assertIn("Rotated", self._page_text(1))

    def test_unsupported_characters_are_replaced(self):
        self._add([{"type": "text", "text": "café 中", "x": 40, "y": 40,
                    "font_size": 14, "pages_spec": "1"}])
        text = self._page_text(0)
        self.assertIn("café", text)
        self.assertIn("?", text)

    def _first_span(self):
        doc = fitz.open(self.output_pdf)
        try:
            return doc[0].get_text("dict")["blocks"][0]["lines"][0]["spans"][0]
        finally:
            doc.close()

    def test_montserrat_is_embedded(self):
        self._add([{"type": "text", "text": "Montserrat sample", "x": 40, "y": 40, "font_size": 20,
                    "font_family": "montserrat", "pages_spec": "1"}])
        self.assertIn("Montserrat-Regular", self._first_span()["font"])
        self.assertIn("Montserrat sample", self._page_text(0))
        doc = fitz.open(self.output_pdf)
        try:
            fonts = doc[0].get_fonts(full=True)  # (xref, ext, type, basefont, ...)
        finally:
            doc.close()
        # 'ttf' means the font program is embedded, so it renders without Montserrat installed
        self.assertTrue(any("Montserrat" in f[3] and f[1] == "ttf" for f in fonts))

    def test_montserrat_variants(self):
        for bold, italic, expected in [(True, False, "Montserrat-Bold"), (False, True, "Montserrat-Italic"),
                                       (True, True, "Montserrat-BoldItalic")]:
            self._add([{"type": "text", "text": "Variant", "x": 40, "y": 40, "font_size": 20,
                        "font_family": "montserrat", "bold": bold, "italic": italic, "pages_spec": "1"}])
            self.assertIn(expected, self._first_span()["font"])

    def test_montserrat_draws_more_than_windows_1252(self):
        # Cyrillic is outside Windows-1252 but inside Montserrat; CJK is in neither.
        self._add([{"type": "text", "text": "\u041f\u0440\u0438\u0432\u0435\u0442 \u0141\u00f3d\u017a \u4e2d", "x": 40, "y": 40,
                    "font_size": 20, "font_family": "montserrat", "pages_spec": "1"}])
        text = self._page_text(0)
        self.assertIn("\u041f\u0440\u0438\u0432\u0435\u0442", text)
        self.assertIn("\u0141\u00f3d\u017a", text)
        self.assertIn("?", text)
        self.assertNotIn("\u4e2d", text)

    def test_font_coverage_ranges(self):
        ranges = text_font_coverage()
        covered = lambda cp: any(lo <= cp <= hi for lo, hi in ranges)
        self.assertTrue(covered(ord("A")) and covered(ord("\u00e9")) and covered(ord("\u0416")) and covered(ord("\u20ac")))
        self.assertFalse(covered(0x4e2d))
        self.assertTrue(all(lo <= hi for lo, hi in ranges))

    def test_every_catalog_font_embeds_and_draws(self):
        catalog = text_font_catalog()
        self.assertGreaterEqual(len(catalog), 20)
        for font in catalog:
            with self.subTest(font=font["key"]):
                self._add([{"type": "text", "text": "Sample 123", "x": 40, "y": 40, "font_size": 18,
                            "font_family": font["key"], "pages_spec": "1"}])
                self.assertIn("Sample 123", self._page_text(0))

    def test_poppins_is_embedded(self):
        self._add([{"type": "text", "text": "Poppins", "x": 40, "y": 40, "font_size": 20,
                    "font_family": "poppins", "bold": True, "pages_spec": "1"}])
        fonts = fitz.open(self.output_pdf)[0].get_fonts()
        self.assertTrue(any("Poppins-Bold" in f[3] and f[1] == "ttf" for f in fonts))

    def test_missing_cut_falls_back_to_nearest(self):
        # Great Vibes has no bold/italic cut: it draws with the regular one instead of failing.
        self.assertNotIn((True, True), EMBEDDED_FONTS["greatvibes"]["files"])
        self._add([{"type": "text", "text": "Script", "x": 40, "y": 40, "font_size": 20,
                    "font_family": "greatvibes", "bold": True, "italic": True, "pages_spec": "1"}])
        fonts = fitz.open(self.output_pdf)[0].get_fonts()
        self.assertTrue(any("GreatVibes-Regular" in f[3] for f in fonts))

    def test_catalog_files_exist_and_flags_match(self):
        for font in text_font_catalog():
            if font["files"] is None:
                continue
            with self.subTest(font=font["key"]):
                for name in font["files"].values():
                    self.assertTrue(os.path.isfile(os.path.join(FONTS_DIR, name + ".ttf")), name)
                self.assertEqual(font["bold"], "bold-normal" in font["files"])
                self.assertEqual(font["italic"], "normal-italic" in font["files"])

    def test_blank_text_draws_nothing(self):
        self._add([{"type": "text", "text": "   ", "x": 40, "y": 40, "pages_spec": "1"}])
        self.assertEqual(len(PdfReader(self.output_pdf).pages), 2)
        self.assertEqual(self._page_text(0).strip(), "")

    def test_bad_color_and_font_rejected(self):
        with self.assertRaises(ValueError):
            self._add([{"type": "text", "text": "x", "color": "not-a-color", "pages_spec": "1"}])
        with self.assertRaises(ValueError):
            self._add([{"type": "text", "text": "x", "font_family": "comic-sans", "pages_spec": "1"}])


if __name__ == "__main__":
    unittest.main()

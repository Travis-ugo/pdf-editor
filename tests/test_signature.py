import os
import unittest
import tempfile
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from pdf_duplicator.core import add_signature_to_pdf

class TestSignatureFeature(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.input_pdf = os.path.join(self.tmpdir.name, "sample.pdf")
        self.output_pdf = os.path.join(self.tmpdir.name, "signed.pdf")
        self.sig_image = os.path.join(self.tmpdir.name, "sig.png")

        # Create a sample PDF with 2 pages
        writer = PdfWriter()
        writer.add_blank_page(width=500, height=700)
        writer.add_blank_page(width=500, height=700)
        with open(self.input_pdf, "wb") as f:
            writer.write(f)

        # Create a sample signature image (PNG with transparency)
        img = Image.new("RGBA", (200, 100), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 190, 90], outline="blue", width=3)
        draw.text((30, 40), "John Doe", fill="darkblue")
        img.save(self.sig_image, "PNG")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_signature_all_pages(self):
        add_signature_to_pdf(
            self.input_pdf,
            self.output_pdf,
            signature_img=self.sig_image,
            pages_spec=None,
            x=100,
            y=100,
            width=150,
            height=50
        )
        self.assertTrue(os.path.exists(self.output_pdf))
        reader = PdfReader(self.output_pdf)
        self.assertEqual(len(reader.pages), 2)

    def test_add_signature_single_page(self):
        add_signature_to_pdf(
            self.input_pdf,
            self.output_pdf,
            signature_img=self.sig_image,
            pages_spec="1",
            x=50,
            y=50,
            width=120,
            height=40,
            y_from_top=True
        )
        self.assertTrue(os.path.exists(self.output_pdf))
        reader = PdfReader(self.output_pdf)
        self.assertEqual(len(reader.pages), 2)

    def test_add_signature_base64(self):
        import base64
        with open(self.sig_image, "rb") as f:
            b64_str = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

        add_signature_to_pdf(
            self.input_pdf,
            self.output_pdf,
            signature_img=b64_str,
            pages_spec="2",
            x=200,
            y=200,
            width=100,
            height=50
        )
    def test_add_multiple_signatures(self):
        sigs = [
            {"signature_img": self.sig_image, "pages_spec": "1", "x": 50, "y": 50, "width": 120, "height": 40},
            {"signature_img": self.sig_image, "pages_spec": "1", "x": 250, "y": 300, "width": 100, "height": 50}
        ]
        add_signature_to_pdf(
            self.input_pdf,
            self.output_pdf,
            signatures=sigs
        )
        self.assertTrue(os.path.exists(self.output_pdf))
        reader = PdfReader(self.output_pdf)
        self.assertEqual(len(reader.pages), 2)

if __name__ == "__main__":
    unittest.main()


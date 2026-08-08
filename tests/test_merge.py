import os
import unittest
import tempfile
from pypdf import PdfReader, PdfWriter
from pdf_duplicator.core import merge_pdfs
from pdf_duplicator.web import sanitize_output_filename

class TestPDFMerge(unittest.TestCase):

    def test_merge_multiple_pdfs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf1_path = os.path.join(tmpdir, "doc1.pdf")
            pdf2_path = os.path.join(tmpdir, "doc2.pdf")
            output_path = os.path.join(tmpdir, "merged.pdf")

            # Create doc1 with 2 pages (width 100)
            writer1 = PdfWriter()
            writer1.add_blank_page(width=100, height=100)
            writer1.add_blank_page(width=100, height=100)
            with open(pdf1_path, "wb") as f:
                writer1.write(f)

            # Create doc2 with 3 pages (width 200)
            writer2 = PdfWriter()
            writer2.add_blank_page(width=200, height=200)
            writer2.add_blank_page(width=200, height=200)
            writer2.add_blank_page(width=200, height=200)
            with open(pdf2_path, "wb") as f:
                writer2.write(f)

            # Merge pdf1 and pdf2
            merge_pdfs([pdf1_path, pdf2_path], output_path)

            self.assertTrue(os.path.exists(output_path))
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 5)
            self.assertEqual(reader.pages[0].mediabox.width, 100)
            self.assertEqual(reader.pages[1].mediabox.width, 100)
            self.assertEqual(reader.pages[2].mediabox.width, 200)
            self.assertEqual(reader.pages[4].mediabox.width, 200)

    def test_merge_with_page_specs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf1_path = os.path.join(tmpdir, "doc1.pdf")
            pdf2_path = os.path.join(tmpdir, "doc2.pdf")
            output_path = os.path.join(tmpdir, "merged_specs.pdf")

            writer1 = PdfWriter()
            writer1.add_blank_page(width=100, height=100) # page 1
            writer1.add_blank_page(width=150, height=150) # page 2
            with open(pdf1_path, "wb") as f:
                writer1.write(f)

            writer2 = PdfWriter()
            writer2.add_blank_page(width=200, height=200) # page 1
            writer2.add_blank_page(width=250, height=250) # page 2
            with open(pdf2_path, "wb") as f:
                writer2.write(f)

            # Merge only page 2 of doc1 and page 1 of doc2
            inputs = [
                {"path": pdf1_path, "pages_spec": "2"},
                {"path": pdf2_path, "pages_spec": "1"}
            ]
            merge_pdfs(inputs, output_path)

            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 2)
            self.assertEqual(reader.pages[0].mediabox.width, 150)
            self.assertEqual(reader.pages[1].mediabox.width, 200)

    def test_merge_empty_inputs(self):
        with self.assertRaises(ValueError):
            merge_pdfs([], "out.pdf")

    def test_merge_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            merge_pdfs(["non_existent_file.pdf"], "out.pdf")

    def test_sanitize_output_filename(self):
        self.assertEqual(sanitize_output_filename("default.pdf", ""), "default.pdf")
        self.assertEqual(sanitize_output_filename("default.pdf", "  my_report  "), "my_report.pdf")
        self.assertEqual(sanitize_output_filename("default.pdf", "my_doc.PDF"), "my_doc.PDF")
        self.assertEqual(sanitize_output_filename("default.pdf", "../../secret_file.pdf"), "secret_file.pdf")

if __name__ == "__main__":
    unittest.main()

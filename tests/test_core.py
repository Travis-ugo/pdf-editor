import os
import unittest
import tempfile
from pypdf import PdfReader, PdfWriter
from pdf_duplicator.core import parse_page_range, duplicate_pdf, duplicate_pages

class TestPDFDuplicatorCore(unittest.TestCase):

    def test_parse_page_range_none(self):
        self.assertEqual(parse_page_range(None, 5), [0, 1, 2, 3, 4])
        self.assertEqual(parse_page_range("", 5), [0, 1, 2, 3, 4])

    def test_parse_page_range_single(self):
        self.assertEqual(parse_page_range("1", 5), [0])
        self.assertEqual(parse_page_range("5", 5), [4])

    def test_parse_page_range_simple_list(self):
        self.assertEqual(parse_page_range("1,3,5", 5), [0, 2, 4])
        self.assertEqual(parse_page_range("2, 4 ", 5), [1, 3])

    def test_parse_page_range_intervals(self):
        self.assertEqual(parse_page_range("1-3", 5), [0, 1, 2])
        self.assertEqual(parse_page_range("2-4", 5), [1, 2, 3])

    def test_parse_page_range_mixed(self):
        self.assertEqual(parse_page_range("1-2,4,5", 5), [0, 1, 3, 4])
        self.assertEqual(parse_page_range("1, 3-5", 5), [0, 2, 3, 4])

    def test_parse_page_range_errors(self):
        with self.assertRaises(ValueError):
            parse_page_range("0", 5)  # 1-indexed, so 0 is invalid
        with self.assertRaises(ValueError):
            parse_page_range("6", 5)  # Out of bounds
        with self.assertRaises(ValueError):
            parse_page_range("4-3", 5)  # Start > End
        with self.assertRaises(ValueError):
            parse_page_range("1-6", 5)  # End out of bounds
        with self.assertRaises(ValueError):
            parse_page_range("abc", 5)  # Invalid format

    def test_duplicate_pdf(self):
        # Create a dummy PDF with 3 pages
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.pdf")
            
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            writer.add_blank_page(width=100, height=100)
            writer.add_blank_page(width=100, height=100)
            with open(input_path, "wb") as f:
                writer.write(f)
                
            # Run duplicate
            duplicate_pdf(input_path, output_path)
            
            # Verify the output PDF
            self.assertTrue(os.path.exists(output_path))
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 3)

    def test_duplicate_pages_default(self):
        # Create a dummy PDF with 2 pages
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.pdf")
            
            writer = PdfWriter()
            # Add page 1 and page 2 with distinct sizes so we can identify them
            writer.add_blank_page(width=100, height=100) # page 1
            writer.add_blank_page(width=200, height=200) # page 2
            with open(input_path, "wb") as f:
                writer.write(f)
                
            # Duplicate all pages twice (default repeat = False -> 1,1,2,2)
            duplicate_pages(input_path, output_path, pages_spec=None, count=2, repeat_sequence=False)
            
            # Verify
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 4)
            # Check sizes to confirm order: 100, 100, 200, 200
            self.assertEqual(reader.pages[0].mediabox.width, 100)
            self.assertEqual(reader.pages[1].mediabox.width, 100)
            self.assertEqual(reader.pages[2].mediabox.width, 200)
            self.assertEqual(reader.pages[3].mediabox.width, 200)

    def test_duplicate_pages_repeat_sequence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.pdf")
            
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100) # page 1
            writer.add_blank_page(width=200, height=200) # page 2
            with open(input_path, "wb") as f:
                writer.write(f)
                
            # Duplicate all pages twice with repeat_sequence = True -> 1,2,1,2
            duplicate_pages(input_path, output_path, pages_spec=None, count=2, repeat_sequence=True)
            
            # Verify
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 4)
            # Check sizes to confirm order: 100, 200, 100, 200
            self.assertEqual(reader.pages[0].mediabox.width, 100)
            self.assertEqual(reader.pages[1].mediabox.width, 200)
            self.assertEqual(reader.pages[2].mediabox.width, 100)
            self.assertEqual(reader.pages[3].mediabox.width, 200)

    def test_duplicate_specific_pages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.pdf")
            output_path = os.path.join(tmpdir, "output.pdf")
            
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100) # page 1
            writer.add_blank_page(width=200, height=200) # page 2
            writer.add_blank_page(width=300, height=300) # page 3
            with open(input_path, "wb") as f:
                writer.write(f)
                
            # Duplicate page 1 and page 3, count=2 -> 1,1,3,3
            duplicate_pages(input_path, output_path, pages_spec="1,3", count=2, repeat_sequence=False)
            
            # Verify
            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 4)
            # Check sizes: 100, 100, 300, 300
            self.assertEqual(reader.pages[0].mediabox.width, 100)
            self.assertEqual(reader.pages[1].mediabox.width, 100)
            self.assertEqual(reader.pages[2].mediabox.width, 300)
            self.assertEqual(reader.pages[3].mediabox.width, 300)

if __name__ == "__main__":
    unittest.main()

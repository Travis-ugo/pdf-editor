import base64
import io
import json
import os
import tempfile
import unittest
import uuid

import fitz
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from pdf_duplicator import web


def make_pdf(pages=3, password=None, label="Page"):
    """A small PDF whose page N says '<label> N', so tests can tell pages apart by their text."""
    buf = io.BytesIO()
    can = canvas.Canvas(buf, pagesize=(612, 792))
    for n in range(1, pages + 1):
        can.setFont("Helvetica", 24)
        can.drawString(72, 700, f"{label} {n}")
        can.showPage()
    can.save()
    if not password:
        return buf.getvalue()
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(buf.getvalue())))
    writer.encrypt(password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def page_texts(pdf_bytes_or_path):
    doc = fitz.open(stream=pdf_bytes_or_path, filetype="pdf") if isinstance(pdf_bytes_or_path, bytes) else fitz.open(pdf_bytes_or_path)
    try:
        return [p.get_text().strip() for p in doc]
    finally:
        doc.close()


def png_data_url():
    buf = io.BytesIO()
    Image.new("RGBA", (60, 20), (0, 0, 120, 255)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class WebTestCase(unittest.TestCase):
    """Runs the Flask app against throwaway upload and output folders (never the real output/)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.upload_dir = os.path.join(self.tmp.name, "uploads")
        self.output_dir = os.path.join(self.tmp.name, "output")
        os.makedirs(self.upload_dir)
        os.makedirs(self.output_dir)
        self._saved = (web.UPLOAD_TEMP_DIR, web.OUTPUT_DIR)
        web.UPLOAD_TEMP_DIR, web.OUTPUT_DIR = self.upload_dir, self.output_dir
        web.app.config["TESTING"] = True
        self.client = web.app.test_client()

    def tearDown(self):
        web.UPLOAD_TEMP_DIR, web.OUTPUT_DIR = self._saved
        self.tmp.cleanup()

    def upload(self, pdf_bytes=None, password=None, name="doc.pdf"):
        data = {"file": (io.BytesIO(pdf_bytes if pdf_bytes is not None else make_pdf()), name)}
        if password:
            data["password"] = password
        return self.client.post("/api/inspect-pdf", data=data, content_type="multipart/form-data")

    def file_id(self, pdf_bytes=None, password=None):
        res = self.upload(pdf_bytes, password)
        self.assertEqual(res.status_code, 200, res.get_json())
        return res.get_json()["file_id"]

    def post_json(self, url, data):
        return self.client.post(url, data=data, headers={"Accept": "application/json"})

    def output_file(self, filename):
        path = os.path.join(self.output_dir, filename)
        self.assertTrue(os.path.isfile(path), f"{filename} not in output dir: {os.listdir(self.output_dir)}")
        return path


class TestIndex(WebTestCase):
    def test_index_renders_with_font_catalog(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("window.FONT_CATALOG", html)
        self.assertIn('id="pdfFileInput"', html)

    def test_static_assets_served(self):
        for path in ("/static/js/app.js", "/static/js/store.js", "/static/css/apple_style.css", "/static/manifest.json"):
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(res.status_code, 200)
                res.close()


class TestInspect(WebTestCase):
    def test_inspect_returns_dimensions_and_previews(self):
        data = self.upload(make_pdf(3)).get_json()
        self.assertEqual(data["total_pages"], 3)
        self.assertFalse(data["is_encrypted"])
        self.assertEqual(len(data["page_dimensions"]), 3)
        self.assertEqual(data["page_dimensions"][0], {"width": 612.0, "height": 792.0})
        self.assertEqual(len(data["page_previews"]), 3)
        self.assertTrue(data["page_previews"][0].startswith("data:image/png;base64,"))
        uuid.UUID(data["file_id"])

    def test_long_document_has_every_dimension_but_lazy_previews(self):
        data = self.upload(make_pdf(25)).get_json()
        self.assertEqual(data["total_pages"], 25)
        self.assertEqual(len(data["page_dimensions"]), 25)
        self.assertEqual(len(data["page_previews"]), web.INITIAL_PREVIEW_PAGES)

    def test_rotated_page_reports_displayed_size(self):
        doc = fitz.open()
        doc.new_page(width=612, height=792).set_rotation(90)
        data = self.upload(doc.tobytes()).get_json()
        self.assertEqual(data["page_dimensions"][0], {"width": 792.0, "height": 612.0})

    def test_encrypted_without_password_asks_for_one(self):
        res = self.upload(make_pdf(1, password="s3cret"))
        self.assertEqual(res.status_code, 401)
        body = res.get_json()
        self.assertTrue(body["is_encrypted"])
        self.assertIn("file_id", body)

    def test_encrypted_with_wrong_password(self):
        res = self.upload(make_pdf(1, password="s3cret"), password="nope")
        self.assertEqual(res.status_code, 401)
        self.assertIn("Incorrect password", res.get_json()["error"])

    def test_encrypted_with_right_password(self):
        res = self.upload(make_pdf(2, password="s3cret"), password="s3cret")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["is_encrypted"])
        self.assertEqual(len(data["page_previews"]), 2)

    def test_aes_encrypted_pdfs_open(self):
        # AES is what Acrobat, Word and Preview use; pypdf needs the `cryptography` package for it
        for algorithm in (fitz.PDF_ENCRYPT_AES_128, fitz.PDF_ENCRYPT_AES_256):
            with self.subTest(algorithm=algorithm):
                doc = fitz.open(stream=make_pdf(2), filetype="pdf")
                pdf = doc.tobytes(encryption=algorithm, user_pw="pw", owner_pw="owner")
                self.assertEqual(self.upload(pdf).status_code, 401)
                res = self.upload(pdf, password="pw")
                self.assertEqual(res.status_code, 200, res.get_json())
                fid = res.get_json()["file_id"]
                res = self.post_json("/api/clone", {"file_id": fid, "password": "pw"})
                self.assertEqual(page_texts(self.output_file(res.get_json()["filename"])), ["Page 1", "Page 2"])

    def test_missing_file(self):
        res = self.client.post("/api/inspect-pdf", data={})
        self.assertEqual(res.status_code, 400)

    def test_not_a_pdf_is_an_error_not_a_crash(self):
        res = self.upload(b"this is not a pdf", name="notes.pdf")
        self.assertGreaterEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())


class TestOpenAnyDocument(WebTestCase):
    """Non-PDF uploads are converted to PDF, then work like any PDF."""

    def png_bytes(self):
        buf = io.BytesIO()
        Image.new("RGB", (300, 150), (255, 255, 255)).save(buf, format="PNG")
        return buf.getvalue()

    def test_text_file_opens_and_can_be_signed(self):
        res = self.upload(b"Terms and conditions\nSign below.", name="terms.txt")
        self.assertEqual(res.status_code, 200, res.get_json())
        data = res.get_json()
        self.assertEqual(data["source_kind"], "text")
        self.assertEqual(data["filename"], "terms.txt")
        self.assertEqual(data["page_dimensions"][0], {"width": 612.0, "height": 792.0})
        items = [{"type": "text", "text": "Agreed", "x": 72, "y": 600, "page": 1}]
        res = self.post_json("/api/sign", {"file_id": data["file_id"], "signatures_json": json.dumps(items)})
        text = page_texts(self.output_file(res.get_json()["filename"]))[0]
        self.assertIn("Terms and conditions", text)
        self.assertIn("Agreed", text)

    def test_image_opens_as_a_page_of_its_shape(self):
        data = self.upload(self.png_bytes(), name="photo.png").get_json()
        self.assertEqual(data["source_kind"], "image")
        dims = data["page_dimensions"][0]
        self.assertAlmostEqual(dims["width"] / dims["height"], 2.0, places=2)

    def test_pdf_reports_pdf(self):
        self.assertEqual(self.upload(make_pdf(1)).get_json()["source_kind"], "pdf")

    def test_unsupported_type_is_415_with_a_message(self):
        res = self.upload(b"MZ...", name="setup.exe")
        self.assertEqual(res.status_code, 415)
        self.assertIn(".exe", res.get_json()["error"])
        self.assertEqual(os.listdir(self.upload_dir), [])

    def test_word_without_libreoffice_says_what_to_install(self):
        from unittest import mock
        from pdf_duplicator import convert
        with mock.patch.object(convert, "find_soffice", return_value=None):
            res = self.upload(b"PK\x03\x04", name="contract.docx")
        self.assertEqual(res.status_code, 415)
        self.assertIn("LibreOffice", res.get_json()["error"])
        # Neither the original nor a half-written PDF is left behind
        self.assertEqual(os.listdir(self.upload_dir), [])

    def test_merge_mixed_formats_in_order(self):
        pdf = self.file_id(make_pdf(1, label="PDF"))
        txt = self.upload(b"From a text file", name="notes.txt").get_json()["file_id"]
        img = self.upload(self.png_bytes(), name="scan.png").get_json()["file_id"]
        res = self.post_json("/api/merge", {"items_json": json.dumps([{"file_id": txt}, {"file_id": img}, {"file_id": pdf}])})
        texts = page_texts(self.output_file(res.get_json()["filename"]))
        self.assertEqual(len(texts), 3)
        self.assertIn("From a text file", texts[0])
        self.assertEqual(texts[2], "PDF 1")

    def test_merge_direct_upload_converts_too(self):
        res = self.client.post("/api/merge", headers={"Accept": "application/json"}, content_type="multipart/form-data", data={
            "files": [(io.BytesIO(b"text page"), "a.txt"), (io.BytesIO(make_pdf(1, label="P")), "b.pdf")]})
        self.assertEqual(res.status_code, 200, res.get_json())
        texts = page_texts(self.output_file(res.get_json()["filename"]))
        self.assertIn("text page", texts[0])
        self.assertEqual(texts[1], "P 1")

    def test_fallback_reupload_of_a_non_pdf_is_converted(self):
        # When the server lost the upload (e.g. restart), the client re-sends the original file
        res = self.client.post("/api/clone", headers={"Accept": "application/json"}, content_type="multipart/form-data",
                               data={"file_id": str(uuid.uuid4()), "file": (io.BytesIO(b"resent text"), "notes.txt")})
        self.assertEqual(res.status_code, 200, res.get_json())
        self.assertIn("resent text", page_texts(self.output_file(res.get_json()["filename"]))[0])

    def test_index_advertises_supported_extensions(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("window.DOCUMENT_EXTENSIONS", html)
        self.assertIn(".docx", html)


class TestPagePreview(WebTestCase):
    def test_renders_a_page_past_the_initial_batch(self):
        fid = self.file_id(make_pdf(25))
        res = self.client.post("/api/page-preview", data={"file_id": fid, "page": "25"})
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["page"], 25)
        self.assertTrue(body["preview"].startswith("data:image/"))

    def test_out_of_range_and_bad_numbers(self):
        fid = self.file_id(make_pdf(2))
        for page in ("0", "3", "-1", "abc", ""):
            with self.subTest(page=page):
                res = self.client.post("/api/page-preview", data={"file_id": fid, "page": page})
                self.assertEqual(res.status_code, 400)

    def test_unknown_file(self):
        res = self.client.post("/api/page-preview", data={"file_id": str(uuid.uuid4()), "page": "1"})
        self.assertEqual(res.status_code, 404)

    def test_encrypted_needs_the_password(self):
        pdf = make_pdf(2, password="pw")
        fid = self.file_id(pdf, password="pw")
        self.assertEqual(self.client.post("/api/page-preview", data={"file_id": fid, "page": "2"}).status_code, 401)
        res = self.client.post("/api/page-preview", data={"file_id": fid, "page": "2", "password": "pw"})
        self.assertEqual(res.status_code, 200)


class TestFileIdIsolation(WebTestCase):
    """file_id comes from the client and must never reach a file outside the upload folder."""

    def setUp(self):
        super().setUp()
        # A PDF outside the upload folder that a traversing file_id would point at
        self.secret = os.path.join(self.tmp.name, "secret.pdf")
        with open(self.secret, "wb") as f:
            f.write(make_pdf(1, label="Secret"))
        self.evil_ids = ["../secret", "..%2Fsecret", os.path.join(self.tmp.name, "secret"), "", "not-a-uuid"]

    def test_clone_rejects_traversal(self):
        for fid in self.evil_ids:
            with self.subTest(file_id=fid):
                res = self.post_json("/api/clone", {"file_id": fid})
                self.assertEqual(res.status_code, 400)
        self.assertEqual(os.listdir(self.output_dir), [])

    def test_page_preview_rejects_traversal(self):
        for fid in self.evil_ids:
            with self.subTest(file_id=fid):
                res = self.client.post("/api/page-preview", data={"file_id": fid, "page": "1"})
                self.assertEqual(res.status_code, 404)

    def test_merge_skips_traversal_ids(self):
        res = self.post_json("/api/merge", {"items_json": json.dumps([{"file_id": "../secret"}])})
        self.assertEqual(res.status_code, 400)

    def test_sign_rejects_traversal(self):
        res = self.post_json("/api/sign", {"file_id": "../secret", "signature_data": png_data_url()})
        self.assertEqual(res.status_code, 400)

    def test_output_download_rejects_traversal(self):
        for name in ("../secret.pdf", "..%2Fsecret.pdf"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(f"/output/{name}").status_code, 404)


class TestSign(WebTestCase):
    def test_sign_with_text_ink_and_image(self):
        fid = self.file_id(make_pdf(2))
        items = [
            {"type": "text", "text": "Signed by Ada", "font_family": "helvetica", "font_size": 14,
             "x": 72, "y": 600, "page": 1, "y_from_top": True},
            {"type": "ink", "strokes": [[[0, 0], [10, 10]]], "base_width": 10, "base_height": 10,
             "x": 72, "y": 650, "width": 20, "height": 20, "page": 2, "y_from_top": True},
            {"signature_img": png_data_url(), "x": 300, "y": 600, "width": 120, "height": 40,
             "page": 1, "y_from_top": True},
        ]
        res = self.post_json("/api/sign", {"file_id": fid, "signatures_json": json.dumps(items),
                                            "custom_filename": "contract-signed"})
        self.assertEqual(res.status_code, 200, res.get_json())
        body = res.get_json()
        self.assertEqual(body["filename"], "contract-signed.pdf")
        self.assertEqual(body["download_url"], "/output/contract-signed.pdf")

        doc = fitz.open(self.output_file("contract-signed.pdf"))
        try:
            self.assertEqual(len(doc), 2)
            self.assertIn("Signed by Ada", doc[0].get_text())
            self.assertEqual(len(doc[0].get_images()), 1)
            self.assertEqual(len(doc[1].get_drawings()), 1)
            self.assertNotIn("Signed by Ada", doc[1].get_text())
        finally:
            doc.close()

        dl = self.client.get(body["download_url"])
        self.assertEqual(dl.status_code, 200)
        self.assertEqual(dl.mimetype, "application/pdf")
        self.assertTrue(dl.data.startswith(b"%PDF"))
        dl.close()

    def test_sign_without_json_accept_streams_the_pdf(self):
        fid = self.file_id()
        res = self.client.post("/api/sign", data={"file_id": fid, "signature_data": png_data_url()})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data.startswith(b"%PDF"))
        self.assertTrue(res.headers["X-Download-Url"].startswith("/output/signed_"))
        res.close()

    def test_sign_encrypted_output_is_readable_without_password(self):
        fid = self.file_id(make_pdf(1, password="pw"), password="pw")
        items = [{"type": "text", "text": "OK", "x": 10, "y": 10, "page": 1}]
        res = self.post_json("/api/sign", {"file_id": fid, "password": "pw", "signatures_json": json.dumps(items)})
        self.assertEqual(res.status_code, 200, res.get_json())
        self.assertFalse(PdfReader(self.output_file(res.get_json()["filename"])).is_encrypted)

    def test_sign_bad_coordinates(self):
        fid = self.file_id()
        res = self.post_json("/api/sign", {"file_id": fid, "x": "left", "signature_data": png_data_url()})
        self.assertEqual(res.status_code, 400)

    def test_sign_without_signature(self):
        res = self.post_json("/api/sign", {"file_id": self.file_id()})
        self.assertEqual(res.status_code, 400)

    def test_sign_bad_page_range_reports_error(self):
        fid = self.file_id(make_pdf(2))
        items = [{"type": "text", "text": "x", "x": 1, "y": 1, "pages_spec": "5"}]
        res = self.post_json("/api/sign", {"file_id": fid, "signatures_json": json.dumps(items)})
        self.assertEqual(res.status_code, 400)
        self.assertIn("out of bounds", res.get_json()["error"])


class TestOutputNaming(WebTestCase):
    def test_repeated_saves_never_overwrite(self):
        fid = self.file_id()
        names = []
        for _ in range(3):
            res = self.post_json("/api/clone", {"file_id": fid, "custom_filename": "My Contract"})
            self.assertEqual(res.status_code, 200)
            names.append(res.get_json()["filename"])
        self.assertEqual(names, ["My Contract.pdf", "My Contract (1).pdf", "My Contract (2).pdf"])
        for name in names:
            self.output_file(name)
            dl = self.client.get(f"/output/{name}")
            self.assertEqual(dl.status_code, 200)
            dl.close()

    def test_existing_user_file_is_left_alone(self):
        existing = os.path.join(self.output_dir, "keep.pdf")
        with open(existing, "wb") as f:
            f.write(b"%PDF-user-file")
        res = self.post_json("/api/clone", {"file_id": self.file_id(), "custom_filename": "keep.pdf"})
        self.assertEqual(res.get_json()["filename"], "keep (1).pdf")
        with open(existing, "rb") as f:
            self.assertEqual(f.read(), b"%PDF-user-file")

    def test_filename_sanitized(self):
        for given, expected in (("../../etc/passwd", "passwd.pdf"), ("a<b>c", "a_b_c.pdf"),
                                ("report.PDF", "report.PDF"), ("   ", None)):
            with self.subTest(given=given):
                res = self.post_json("/api/clone", {"file_id": self.file_id(), "custom_filename": given})
                name = res.get_json()["filename"]
                if expected:
                    self.assertEqual(name, expected)
                else:
                    self.assertTrue(name.startswith("cloned_"))
                self.assertEqual(os.path.dirname(name), "")


class TestDuplicateCloneMerge(WebTestCase):
    def test_duplicate_each_page(self):
        fid = self.file_id(make_pdf(2))
        res = self.post_json("/api/duplicate", {"file_id": fid, "count": "2", "repeat_sequence": "false"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(page_texts(self.output_file(res.get_json()["filename"])), ["Page 1", "Page 1", "Page 2", "Page 2"])

    def test_duplicate_sequence_with_range(self):
        fid = self.file_id(make_pdf(3))
        res = self.post_json("/api/duplicate", {"file_id": fid, "count": "2", "repeat_sequence": "true", "pages_spec": "2-3"})
        self.assertEqual(page_texts(self.output_file(res.get_json()["filename"])), ["Page 2", "Page 3", "Page 2", "Page 3"])

    def test_duplicate_bad_count(self):
        fid = self.file_id()
        self.assertEqual(self.post_json("/api/duplicate", {"file_id": fid, "count": "two"}).status_code, 400)
        self.assertEqual(self.post_json("/api/duplicate", {"file_id": fid, "count": "0"}).status_code, 400)

    def test_clone_decrypts(self):
        fid = self.file_id(make_pdf(2, password="pw"), password="pw")
        res = self.post_json("/api/clone", {"file_id": fid, "password": "pw"})
        path = self.output_file(res.get_json()["filename"])
        self.assertFalse(PdfReader(path).is_encrypted)
        self.assertEqual(page_texts(path), ["Page 1", "Page 2"])

    def test_clone_encrypted_without_password_fails_cleanly(self):
        fid = self.upload(make_pdf(1, password="pw")).get_json()["file_id"]
        res = self.post_json("/api/clone", {"file_id": fid})
        self.assertEqual(res.status_code, 400)
        self.assertIn("encrypted", res.get_json()["error"])

    def test_merge_in_order_with_page_ranges_and_passwords(self):
        a = self.file_id(make_pdf(3, label="A"))
        b = self.file_id(make_pdf(2, label="B", password="pw"), password="pw")
        items = [{"file_id": b, "password": "pw", "pages_spec": "2"}, {"file_id": a, "pages_spec": "1,3"}]
        res = self.post_json("/api/merge", {"items_json": json.dumps(items), "custom_filename": "bundle"})
        self.assertEqual(res.status_code, 200, res.get_json())
        self.assertEqual(page_texts(self.output_file("bundle.pdf")), ["B 2", "A 1", "A 3"])

    def test_merge_uploaded_files(self):
        res = self.client.post("/api/merge", headers={"Accept": "application/json"}, content_type="multipart/form-data", data={
            "files": [(io.BytesIO(make_pdf(1, label="X")), "x.pdf"), (io.BytesIO(make_pdf(1, label="Y")), "y.pdf")]})
        self.assertEqual(page_texts(self.output_file(res.get_json()["filename"])), ["X 1", "Y 1"])

    def test_merge_nothing(self):
        self.assertEqual(self.post_json("/api/merge", {}).status_code, 400)
        self.assertEqual(self.post_json("/api/merge", {"items_json": "not json"}).status_code, 400)


class TestPreview(WebTestCase):
    def test_preview_renders_every_page_with_overlays(self):
        fid = self.file_id(make_pdf(25))
        items = [{"type": "text", "text": "Hi", "x": 10, "y": 10, "page": 25}]
        res = self.client.post("/api/preview-pdf", data={"file_id": fid, "signatures_json": json.dumps(items)})
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["total_pages"], 25)
        self.assertEqual(len(body["page_previews"]), 25)
        # The preview's temporary PDF is cleaned up
        self.assertFalse([f for f in os.listdir(self.upload_dir) if f.startswith("prev_")])

    def test_preview_without_overlays(self):
        res = self.client.post("/api/preview-pdf", data={"file_id": self.file_id(make_pdf(2))})
        self.assertEqual(res.get_json()["total_pages"], 2)

    def test_preview_missing_input(self):
        self.assertEqual(self.client.post("/api/preview-pdf", data={}).status_code, 400)


if __name__ == "__main__":
    unittest.main()

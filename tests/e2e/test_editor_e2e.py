"""
End-to-end tests: the real web app in a real browser, checked against the PDF files it writes.

Runs against throwaway upload/output folders (never the project's output/). Uses the installed
Google Chrome by default; set PDF_E2E_BROWSER=chromium to use Playwright's own Chromium
(`playwright install chromium`). Skipped when Playwright or a browser isn't available.

    .venv/bin/python -m pytest tests/e2e -q
"""
import io
import os
import tempfile
import threading
import unittest

import fitz
from reportlab.pdfgen import canvas as rl_canvas

from pdf_duplicator import web

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def make_pdf(path, pages=3, label="Page", rotation=0, password=None):
    buf = io.BytesIO()
    can = rl_canvas.Canvas(buf, pagesize=(612, 792))
    for n in range(1, pages + 1):
        can.setFont("Helvetica", 24)
        can.drawString(72, 700, f"{label} {n}")
        can.showPage()
    can.save()
    doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
    for page in doc:
        page.set_rotation(rotation)
    if password:
        doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
    else:
        doc.save(path)
    doc.close()
    return path


class EditorE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sync_playwright is None:
            raise unittest.SkipTest("playwright is not installed (pip install -r requirements-dev.txt)")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.upload_dir = os.path.join(cls.tmp.name, "uploads")
        cls.output_dir = os.path.join(cls.tmp.name, "output")
        cls.fixtures = os.path.join(cls.tmp.name, "fixtures")
        for d in (cls.upload_dir, cls.output_dir, cls.fixtures):
            os.makedirs(d)
        cls._saved = (web.UPLOAD_TEMP_DIR, web.OUTPUT_DIR)
        web.UPLOAD_TEMP_DIR, web.OUTPUT_DIR = cls.upload_dir, cls.output_dir

        from werkzeug.serving import make_server
        cls.server = make_server("127.0.0.1", 0, web.app, threaded=True)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

        cls.pw = sync_playwright().start()
        browser = os.environ.get("PDF_E2E_BROWSER", "chrome")
        try:
            if browser == "chrome":
                cls.browser = cls.pw.chromium.launch(channel="chrome")
            else:
                cls.browser = cls.pw.chromium.launch()
        except Exception as e:  # pragma: no cover
            cls._teardown_server()
            raise unittest.SkipTest(f"no browser for e2e tests ({browser}): {e}")

        cls.sample = make_pdf(os.path.join(cls.fixtures, "sample.pdf"), pages=3)

    @classmethod
    def _teardown_server(cls):
        cls.server.shutdown()
        web.UPLOAD_TEMP_DIR, web.OUTPUT_DIR = cls._saved
        cls.pw.stop()
        cls.tmp.cleanup()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._teardown_server()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.on("console", lambda m: m.type == "error" and self.errors.append(m.text))
        self.page.goto(self.base_url)
        self.page.wait_for_function("window.appStore !== undefined")

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], "browser reported errors")

    # --- helpers -----------------------------------------------------------------------------

    def open_pdf(self, path, password=None):
        self.page.set_input_files("#pdfFileInput", path)
        if password:
            self.page.wait_for_selector("#passwordSection:not(.hidden)")
            self.page.fill("#pdfPasswordInput", password)
            self.page.press("#pdfPasswordInput", "Enter")
            self.page.dispatch_event("#pdfPasswordInput", "change")
        self.page.wait_for_function("window.appStore.state.document.fileId && document.getElementById('pdfPageImg').complete && document.getElementById('pdfPageImg').naturalWidth > 0")
        self.page.wait_for_selector("#pdfCanvasContainer:not(.hidden)")

    def items(self):
        return self.page.evaluate("window.appStore.state.signature.activeSignaturesOnDoc.map(s => ({...s, dataUrl: undefined}))")

    def page_point(self, x, y):
        """Screen position of a point given in PDF points from the page's top-left."""
        box = self.page.locator("#pdfPageImg").bounding_box()
        dims = self.page.evaluate("(() => { const d = window.appStore.state.document; return d.pageDimensions[d.currentPage - 1]; })()")
        scale = box["width"] / dims["width"]
        return box["x"] + x * scale, box["y"] + y * scale

    def save(self, filename):
        before = set(os.listdir(self.output_dir))
        self.page.fill("#customOutputFilenameInput", filename)
        with self.page.expect_download():
            self.page.click("#processActionBtn")
        self.page.wait_for_selector("#statusAlert:not(.hidden)")
        new = set(os.listdir(self.output_dir)) - before
        self.assertEqual(len(new), 1, f"expected one new output file, got {new}")
        return os.path.join(self.output_dir, new.pop())

    def add_text(self, text):
        self.page.click("#addTextBtn")
        self.page.keyboard.press("Meta+A")
        self.page.keyboard.type(text)

    # --- tests -------------------------------------------------------------------------------

    def test_app_loads_with_empty_state(self):
        self.assertTrue(self.page.is_visible("#emptyStageNotice"))
        self.assertTrue(self.page.is_disabled("#processActionBtn"))

    def test_open_pdf_lists_pages_and_navigates(self):
        self.open_pdf(self.sample)
        self.assertEqual(self.page.inner_text("#docName"), "sample.pdf")
        self.assertEqual(self.page.locator(".thumb-card").count(), 3)
        self.page.click("#nextPageBtn")
        self.assertEqual(self.page.inner_text("#currentPageNum"), "2")
        self.page.locator(".thumb-card").nth(2).click()
        self.assertEqual(self.page.inner_text("#currentPageNum"), "3")
        self.assertTrue(self.page.is_disabled("#nextPageBtn"))

    def test_text_box_typed_and_saved_into_the_pdf(self):
        self.open_pdf(self.sample)
        self.add_text("Hello world")
        self.assertEqual(self.page.eval_on_selector(".text-overlay-svg", "e => e.textContent"), "Hello world")
        out = self.save("e2e-text")
        doc = fitz.open(out)
        self.assertIn("Hello world", doc[0].get_text())
        self.assertNotIn("Hello world", doc[1].get_text())
        doc.close()

    def test_clicking_empty_canvas_closes_text_editor(self):
        # Regression: the editor used to stay open and focused after deselecting, silently
        # swallowing whatever was typed next.
        self.open_pdf(self.sample)
        self.add_text("Keep")
        self.page.mouse.click(*self.page_point(500, 760))
        self.assertTrue(self.page.locator("#textEditor").is_hidden())
        self.assertNotEqual(self.page.evaluate("document.activeElement.id"), "textContentInput")
        self.page.keyboard.type("XYZ")
        self.assertEqual([i["text"] for i in self.items()], ["Keep"])

    def test_text_style_controls(self):
        self.open_pdf(self.sample)
        self.add_text("Styled")
        self.page.click("#textBoldBtn")
        self.page.fill("#textSizeInput", "30")
        self.page.dispatch_event("#textSizeInput", "change")
        self.page.click('.text-color-btn[data-color="#cc0000"]')
        item = self.items()[0]
        self.assertTrue(item["bold"])
        self.assertEqual(item["fontSize"], 30)
        self.assertEqual(item["color"], "#cc0000")
        out = self.save("e2e-styled")
        spans = [s for b in fitz.open(out)[0].get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"] if s["text"] == "Styled"]
        self.assertEqual(len(spans), 1)
        self.assertAlmostEqual(spans[0]["size"], 30, delta=0.5)
        self.assertIn("Bold", spans[0]["font"])
        self.assertEqual(spans[0]["color"], 0xCC0000)

    def test_pen_draws_vector_ink(self):
        self.open_pdf(self.sample)
        self.page.click("#toolPenBtn")
        x0, y0 = self.page_point(100, 300)
        x1, y1 = self.page_point(250, 340)
        self.page.mouse.move(x0, y0)
        self.page.mouse.down()
        for i in range(1, 21):
            self.page.mouse.move(x0 + (x1 - x0) * i / 20, y0 + (y1 - y0) * i / 20)
        self.page.mouse.up()
        items = self.items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["type"], "ink")
        out = self.save("e2e-pen")
        page = fitz.open(out)[0]
        drawings = page.get_drawings()
        self.assertEqual(len(drawings), 1)
        r = drawings[0]["rect"]
        self.assertAlmostEqual(r.x0, 100, delta=5)
        self.assertAlmostEqual(r.x1, 250, delta=5)
        self.assertEqual(page.get_images(), [])

    def test_check_mark_and_cross(self):
        self.open_pdf(self.sample)
        self.page.click("#toolMarkBtn")
        self.page.mouse.click(*self.page_point(78, 640))
        self.page.keyboard.press("x")
        self.page.mouse.click(*self.page_point(78, 600))
        shapes = sorted(i.get("shape") for i in self.items())
        self.assertEqual(shapes, ["check", "cross"])
        out = self.save("e2e-marks")
        self.assertEqual(len(fitz.open(out)[0].get_drawings()), 2)

    def test_draw_signature_and_place_it(self):
        self.open_pdf(self.sample)
        self.page.click("#toolNewSigBtn")
        self.page.wait_for_selector("#sigStudioModal:not(.hidden)")
        box = self.page.locator("#sigCanvas").bounding_box()
        self.page.mouse.move(box["x"] + 40, box["y"] + 150)
        self.page.mouse.down()
        for i in range(30):
            self.page.mouse.move(box["x"] + 40 + i * 12, box["y"] + 150 - (i % 5) * 15)
        self.page.mouse.up()
        self.page.click("#saveSigModalBtn")
        self.page.wait_for_selector("#sigStudioModal.hidden", state="attached")
        self.assertEqual(len(self.items()), 1)
        self.assertGreater(self.page.locator("#signatureTrayContainer img").count(), 0)
        out = self.save("e2e-signature")
        self.assertEqual(len(fitz.open(out)[0].get_images()), 1)

    def test_blank_signature_is_refused(self):
        self.open_pdf(self.sample)
        self.page.click("#toolNewSigBtn")
        self.page.click("#saveSigModalBtn")
        self.assertIn("Draw your signature", self.page.inner_text("#sigModalHint"))
        self.assertEqual(self.items(), [])

    def test_undo_redo_and_delete(self):
        self.open_pdf(self.sample)
        self.add_text("One")
        self.page.mouse.click(*self.page_point(500, 760))
        self.assertEqual([i["text"] for i in self.items()], ["One"])
        # First undo reverts the typing (one step per editing session), the second removes the box
        self.page.keyboard.press("Meta+Z")
        self.assertEqual([i["text"] for i in self.items()], ["Your text"])
        self.page.keyboard.press("Meta+Z")
        self.assertEqual(self.items(), [])
        self.page.keyboard.press("Meta+Shift+Z")
        self.page.keyboard.press("Meta+Shift+Z")
        self.assertEqual([i["text"] for i in self.items()], ["One"])
        # Select it on the stage and delete with the keyboard
        self.page.locator(".signature-overlay").first.click()
        self.page.keyboard.press("Backspace")
        self.assertEqual(len(self.items()), 0)

    def test_save_is_disabled_until_something_is_placed(self):
        self.open_pdf(self.sample)
        self.assertTrue(self.page.is_disabled("#processActionBtn"))
        self.add_text("Now")
        self.assertTrue(self.page.is_enabled("#processActionBtn"))
        self.page.keyboard.press("Escape")
        self.page.locator(".signature-overlay").first.click()
        self.page.keyboard.press("Backspace")
        self.assertTrue(self.page.is_disabled("#processActionBtn"))

    def test_long_document_loads_later_pages_on_demand(self):
        path = make_pdf(os.path.join(self.fixtures, "long.pdf"), pages=25)
        self.open_pdf(path)
        self.assertEqual(self.page.locator(".thumb-card").count(), 25)
        self.page.locator(".thumb-card").nth(24).scroll_into_view_if_needed()
        self.page.locator(".thumb-card").nth(24).click()
        self.assertEqual(self.page.inner_text("#currentPageNum"), "25")
        self.page.wait_for_function("document.getElementById('pdfPageImg').src.startsWith('data:image/')"
                                    " && window.appStore.state.document.pagePreviews[24]")
        self.page.wait_for_function("document.querySelectorAll('.thumb-card')[24].querySelector('img').src.startsWith('data:')")
        self.add_text("Last page")
        out = self.save("e2e-long")
        doc = fitz.open(out)
        self.assertEqual(len(doc), 25)
        self.assertIn("Last page", doc[24].get_text())
        self.assertNotIn("Last page", doc[0].get_text())

    def test_rotated_page_item_lands_where_it_was_placed(self):
        path = make_pdf(os.path.join(self.fixtures, "rotated.pdf"), pages=1, rotation=90)
        self.open_pdf(path)
        dims = self.page.evaluate("window.appStore.state.document.pageDimensions[0]")
        self.assertEqual((dims["width"], dims["height"]), (792, 612))
        self.add_text("Rotated")
        item = self.items()[0]
        out = self.save("e2e-rotated")
        page = fitz.open(out)[0]
        word = [w for w in page.get_text("words") if w[4] == "Rotated"][0]
        x0, y0, x1, y1 = fitz.Rect(word[:4]) * page.rotation_matrix
        self.assertAlmostEqual(min(x0, x1), item["x"], delta=3)
        self.assertGreater(abs(x1 - x0), abs(y1 - y0))

    def test_encrypted_pdf_asks_for_password(self):
        path = make_pdf(os.path.join(self.fixtures, "locked.pdf"), pages=2, password="open-sesame")
        self.page.set_input_files("#pdfFileInput", path)
        self.page.wait_for_selector("#passwordSection:not(.hidden)")
        self.page.fill("#pdfPasswordInput", "open-sesame")
        self.page.dispatch_event("#pdfPasswordInput", "change")
        self.page.wait_for_selector("#pdfCanvasContainer:not(.hidden)")
        self.assertEqual(self.page.locator(".thumb-card").count(), 2)
        self.add_text("Unlocked")
        out = self.save("e2e-locked")
        self.assertIn("Unlocked", fitz.open(out)[0].get_text())
        # The 401 for the first, password-less attempt is expected
        self.errors = [e for e in self.errors if "401" not in e]

    def test_text_file_opens_signs_and_downloads_as_pdf(self):
        path = os.path.join(self.fixtures, "terms.txt")
        with open(path, "w") as f:
            f.write("Terms of service\n\nBy signing you agree.")
        self.open_pdf(path)
        self.assertEqual(self.page.inner_text("#docName"), "terms.txt")
        self.assertIn("from TXT", self.page.inner_text("#docMeta"))
        self.add_text("Agreed")
        # No custom name: the download is named after the document, with a .pdf extension
        before = set(os.listdir(self.output_dir))
        with self.page.expect_download() as dl:
            self.page.click("#processActionBtn")
        self.assertEqual(dl.value.suggested_filename, "sign_terms.pdf")
        self.page.wait_for_selector("#statusAlert:not(.hidden)")
        new = set(os.listdir(self.output_dir)) - before
        self.assertEqual(len(new), 1)
        text = fitz.open(os.path.join(self.output_dir, new.pop()))[0].get_text()
        self.assertIn("Terms of service", text)
        self.assertIn("Agreed", text)

    def test_image_opens_as_a_page(self):
        from PIL import Image
        path = os.path.join(self.fixtures, "receipt.png")
        Image.new("RGB", (600, 900), (250, 250, 250)).save(path)
        self.open_pdf(path)
        dims = self.page.evaluate("window.appStore.state.document.pageDimensions[0]")
        self.assertAlmostEqual(dims["width"] / dims["height"], 600 / 900, places=2)
        self.assertIn("from PNG", self.page.inner_text("#docMeta"))

    def test_unsupported_file_shows_why(self):
        path = os.path.join(self.fixtures, "setup.exe")
        with open(path, "wb") as f:
            f.write(b"MZ")
        self.page.set_input_files("#pdfFileInput", path)
        self.page.wait_for_function("document.getElementById('statusAlert').textContent.includes('.exe')")
        self.assertTrue(self.page.is_visible("#emptyStageNotice"))
        self.errors = [e for e in self.errors if "415" not in e]

    def test_merge_accepts_other_formats(self):
        txt = os.path.join(self.fixtures, "cover.txt")
        with open(txt, "w") as f:
            f.write("Cover letter")
        pdf = make_pdf(os.path.join(self.fixtures, "body.pdf"), pages=1, label="Body")
        self.page.click('.rail-btn[data-mode="merge"]')
        self.page.set_input_files("#mergeFileInput", [txt, pdf])
        self.page.wait_for_function("window.appStore.state.merge.files.length === 2 && window.appStore.state.merge.files.every(f => f.fileId)")
        # Uploads finish in any order; put the cover letter first
        names = self.page.evaluate("window.appStore.state.merge.files.map(f => f.filename)")
        out = self.save("e2e-mixed-merge")
        texts = [p.get_text().strip() for p in fitz.open(out)]
        self.assertEqual(len(texts), 2)
        self.assertEqual(texts[names.index("cover.txt")], "Cover letter")
        self.assertEqual(texts[names.index("body.pdf")], "Body 1")

    def test_duplicate_mode(self):
        self.open_pdf(self.sample)
        self.page.click('.rail-btn[data-mode="duplicate"]')
        self.page.fill("#dupPagesInput", "2")
        self.page.fill("#dupCountInput", "3")
        out = self.save("e2e-dup")
        self.assertEqual([p.get_text().strip() for p in fitz.open(out)], ["Page 2"] * 3)

    def test_merge_mode(self):
        a = make_pdf(os.path.join(self.fixtures, "a.pdf"), pages=1, label="A")
        b = make_pdf(os.path.join(self.fixtures, "b.pdf"), pages=2, label="B")
        self.page.click('.rail-btn[data-mode="merge"]')
        self.page.set_input_files("#mergeFileInput", [a, b])
        self.page.wait_for_function("window.appStore.state.merge.files.length === 2 && window.appStore.state.merge.files.every(f => f.fileId)")
        out = self.save("e2e-merge")
        self.assertEqual([p.get_text().strip() for p in fitz.open(out)], ["A 1", "B 1", "B 2"])

    def test_leaving_merge_mode_restores_the_open_document(self):
        # Regression: merge mode took over the stage and other modes never gave it back, so the
        # open document vanished (empty merge queue) or signing drew over a merge file's page.
        self.open_pdf(self.sample)
        doc_src = self.page.get_attribute("#pdfPageImg", "src")
        self.page.click('.rail-btn[data-mode="merge"]')
        self.assertTrue(self.page.is_visible("#emptyStageNotice"))
        self.page.click('.rail-btn[data-mode="duplicate"]')
        self.assertTrue(self.page.is_visible("#pdfCanvasContainer"))
        self.assertTrue(self.page.is_hidden("#emptyStageNotice"))

        other = make_pdf(os.path.join(self.fixtures, "other.pdf"), pages=5, label="Other")
        self.page.click('.rail-btn[data-mode="merge"]')
        self.page.set_input_files("#mergeFileInput", other)
        self.page.wait_for_function("window.appStore.state.merge.files.length === 1")
        self.page.wait_for_function("document.getElementById('totalPagesNum').textContent === '5'")
        self.page.click('.rail-btn[data-mode="sign"]')
        self.page.wait_for_function(f"document.getElementById('pdfPageImg').src === {doc_src!r}")
        self.assertEqual(self.page.inner_text("#totalPagesNum"), "3")

    def test_clone_mode(self):
        self.open_pdf(self.sample)
        self.page.click('.rail-btn[data-mode="clone"]')
        out = self.save("e2e-clone")
        self.assertEqual(len(fitz.open(out)), 3)

    def test_theme_toggle_persists_across_reload(self):
        start = self.page.evaluate("document.body.className")
        self.page.click("#themeToggleBtn")
        toggled = self.page.evaluate("document.body.className")
        self.assertNotEqual(start, toggled)
        self.page.reload()
        self.page.wait_for_function("window.appStore !== undefined")
        self.assertEqual(self.page.evaluate("document.body.className"), toggled)

    def test_zoom_controls(self):
        self.open_pdf(self.sample)
        self.page.click("#zoomMenuBtn")
        self.page.click("#zoomInBtn")
        self.assertNotEqual(self.page.inner_text("#zoomVal"), "100%")
        self.page.click("#zoomMenuBtn")
        self.page.click("#zoomResetBtn")
        self.assertEqual(self.page.inner_text("#zoomVal"), "100%")

    def test_preview_modal_shows_every_page(self):
        self.open_pdf(self.sample)
        self.add_text("Preview me")
        self.page.click("#toolPreviewBtn")
        self.page.wait_for_selector("#previewPagesContainer:not(.hidden)")
        self.assertEqual(self.page.locator("#previewPagesContainer img").count(), 3)


if __name__ == "__main__":
    unittest.main()

# PDF Duplicator & Studio - Feature Roadmap & TODO

This document outlines the step-by-step TODO plan for adding **Firebase Integration**, **Signature Background Remover**, and the **Full-Blown PDF Creator Studio** to the **PDF Duplicator** project, followed by an exhaustive reference list of all features in Adobe Acrobat.

---

## 📋 Architecture & Feature Map

```
                               ┌────────────────────────────────────────┐
                               │        PDF Studio Web Frontend         │
                               └───────────────────┬────────────────────┘
                                                   │
         ┌─────────────────────────────────────────┼────────────────────────────────────────┐
         ▼                                         ▼                                        ▼
┌──────────────────┐                     ┌──────────────────┐                     ┌──────────────────┐
│  Firebase Sync   │                     │ Signature Remover│                     │   PDF Creator    │
│ (Auth/Firestore) │                     │ (Camera/Photo)   │                     │  (Full Authoring)│
└────────┬─────────┘                     └────────┬─────────┘                     └────────┬─────────┘
         │                                        │                                        │
         └────────────────────────────────────────┼────────────────────────────────────────┘
                                                  │
                                                  ▼
                                      ┌──────────────────────┐
                                      │    Flask Backend     │
                                      │ (PyMuPDF / ReportLab)│
                                      └──────────────────────┘
```

---

## taskList / Checklist

### Phase 1: Firebase Setup & Configuration
- [ ] **1.1 Create Firebase Project**
  - Go to [Firebase Console](https://console.firebase.google.com/) and create project `pdf-duplicator`.
  - Enable **Firebase Authentication** (Email/Password & Google Sign-In).
  - Enable **Cloud Firestore** in Production mode.
  - Enable **Cloud Storage** bucket for PDF file storage.
- [ ] **1.2 Register Web Application & Download Config**
  - Register Web App in Firebase console to get `firebaseConfig` keys (`apiKey`, `authDomain`, `projectId`, `storageBucket`, etc.).
- [ ] **1.3 Create Service Account for Backend**
  - Generate a service account key JSON from Firebase Settings -> Service Accounts.
  - Save as `firebase-service-account.json` (add to `.gitignore`).
- [ ] **1.4 Update Dependencies**
  - Add `firebase-admin` to [`requirements.txt`](file:///Users/travis/Software/pdf-duplicator/requirements.txt).

---

### Phase 2: Client-side Firebase Integration (Frontend)
- [ ] **2.1 Create Firebase Client Module**
  - Create [`pdf_duplicator/static/js/firebase-config.js`](file:///Users/travis/Software/pdf-duplicator/pdf_duplicator/static/js/firebase-config.js) initializing Firebase App, Auth, Firestore, and Storage.
- [ ] **2.2 Add User Authentication UI & State**
  - Add Sign In / Sign Up modal in [`pdf_duplicator/templates/index.html`](file:///Users/travis/Software/pdf-duplicator/pdf_duplicator/templates/index.html).
  - Update [`pdf_duplicator/static/js/store.js`](file:///Users/travis/Software/pdf-duplicator/pdf_duplicator/static/js/store.js) state to track active user (`state.user: { uid, email, displayName }`).
- [ ] **2.3 Sync Signatures to Cloud Firestore**
  - Update `addSignature()` & `deleteSignature()` in [`store.js`](file:///Users/travis/Software/pdf-duplicator/pdf_duplicator/static/js/store.js) to write/delete signatures in Firestore collection `users/{uid}/signatures`.
  - Retain IndexedDB for offline cache & instant loading.
- [ ] **2.4 Load Cloud Signatures on Login**
  - Fetch saved signatures from Firestore when `onAuthStateChanged` fires and merge with local store.

---

### Phase 3: Flask Backend Integration & Document Storage
- [ ] **3.1 Initialize Firebase Admin in Flask**
  - In [`pdf_duplicator/web.py`](file:///Users/travis/Software/pdf-duplicator/pdf_duplicator/web.py), load `firebase_admin` credentials and bucket.
- [ ] **3.2 Implement Auth Token Middleware / Helper**
  - Add a helper in [`web.py`](file:///Users/travis/Software/pdf-duplicator/pdf_duplicator/web.py) to decode and verify `Authorization: Bearer <id_token>` headers.
- [ ] **3.3 Cloud Document Vault Uploads**
  - Update `/api/add-signature` and `/api/duplicate` endpoints in [`web.py`](file:///Users/travis/Software/pdf-duplicator/pdf_duplicator/web.py) to upload generated output PDFs to Firebase Storage (`users/{uid}/documents/{docId}/signed_output.pdf`).
  - Store document metadata (filename, date, mode, placement settings, download URL) in Firestore sub-collection `users/{uid}/documents`.
- [ ] **3.4 "My Saved Documents" History Tab**
  - Add a new tab/drawer in the frontend UI to display user's past edited documents with direct download links.

---

### Phase 4: Signature Background Remover Feature 📸 ✨
- [ ] **4.1 Image Selection & Camera Capture Modal**
  - Add camera capture (`<input type="file" accept="image/*" capture="environment">`) & photo gallery upload options in signature modal.
  - Support drag-and-drop photo upload for signature extraction.
- [ ] **4.2 Background Removal Engine**
  - Implement canvas-based / Python OpenCV + PIL algorithm for automatic background removal:
    - **Grayscale Conversion & Contrast Enhancement:** Boost ink-to-paper contrast.
    - **Luminance Thresholding & Alpha Conversion:** Convert paper background (white/off-white/shadows) into transparent alpha pixels.
    - **Ink Color Preservation:** Preserve dark ink lines (black, blue, red) while removing paper texture and shadows.
    - **Auto-Bounding Box Cropping:** Trim unnecessary white margins around extracted signature.
- [ ] **4.3 Interactive Threshold Adjustment Slider**
  - Provide a live preview modal with a sensitivity/threshold slider allowing users to adjust background removal strength in real-time.
- [ ] **4.4 Export Clean PNG Signature**
  - Convert extracted signature to transparent PNG Data URL (`data:image/png;base64,...`).
  - Save directly into active document signature overlays and user's saved signature library (IndexedDB + Cloud Firestore).

---

### Phase 5: Full-Blown PDF Creator Studio 📄 ✏️
- [ ] **5.1 Document Creation Canvas UI**
  - Create a new "Create PDF" mode/tab in the studio header navigation.
  - WYSIWYG page editor canvas supporting multi-page creation.
- [ ] **5.2 Page Layout & Formatting Controls**
  - **Page Sizes:** A4, US Letter, Legal, Executive, and custom dimensions.
  - **Page Orientation:** Portrait and Landscape toggles.
  - **Margins & Padding:** Adjustable top, bottom, left, and right page margins (in mm/inches).
  - **Cover Page Templates:** One-click formal cover pages (Title, Subtitle, Author, Date, Logo).
- [ ] **5.3 Rich Text Formatting & Font Engine**
  - Multi-line text boxes with positionable text frames.
  - **Font Selector:** Inter, Roboto, Open Sans, Times New Roman, Courier, Helvetica, Georgia.
  - **Text Styling:** Font size, weight (Bold), style (Italic), line height, text color picker, text alignment (Left, Center, Right, Justified).
- [ ] **5.4 Image & Graphic Embedding**
  - Upload & place images onto creator canvas.
  - Drag-to-resize, rotation controls, and lock aspect ratio constraints.
- [ ] **5.5 Headers, Footers & Automated Page Numbering**
  - Dynamic page headers and footers editor.
  - Automated page numbering placeholders (`Page {page_num} of {total_pages}`).
  - Document title and timestamp variables in headers/footers.
- [ ] **5.6 Page Management & Navigation**
  - "Add Next Page" button.
  - Re-order pages via drag-and-drop thumbnail drawer.
  - Duplicate page & delete page controls.
- [ ] **5.7 PDF Generation Engine & Storage Export**
  - Implement backend PDF generation endpoint using ReportLab / PyMuPDF (`fitz`) to compile JSON layout schema into crisp vector PDF binaries.
  - Integrate with Firebase Storage to save created documents into user's Cloud Document Vault.

---

### Phase 6: Security Rules & Polish
- [ ] **6.1 Deploy Firestore Security Rules**
  ```javascript
  rules_version = '2';
  service cloud.firestore {
    match /databases/{database}/documents {
      match /users/{userId}/{document=**} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
  }
  ```
- [ ] **6.2 Deploy Storage Security Rules**
  ```javascript
  rules_version = '2';
  service firebase.storage {
    match /b/{bucket}/o {
      match /users/{userId}/{allPaths=**} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
  }
  ```
- [ ] **6.3 Update .gitignore & Documentation**
  - Ensure service account credentials and local tokens are excluded in `.gitignore`.
  - Update [`README.md`](file:///Users/travis/Software/pdf-duplicator/README.md) with full feature overview.

---

## 🗄️ Database & Storage Schemas

### Firestore Collections

#### `users/{uid}` (User Profile)
```json
{
  "email": "user@example.com",
  "displayName": "User Name",
  "theme": "dark-mode",
  "createdAt": "2026-08-13T10:00:00Z"
}
```

#### `users/{uid}/signatures/{signatureId}` (Saved Signatures)
```json
{
  "title": "Main Signature",
  "dataUrl": "data:image/png;base64,...",
  "source": "camera_extracted", 
  "aspectRatio": 2.5,
  "createdAt": "2026-08-13T10:05:00Z"
}
```

#### `users/{uid}/documents/{docId}` (Document Audit & History)
```json
{
  "filename": "Contract_Signed.pdf",
  "originalFilename": "Contract.pdf",
  "pageCount": 5,
  "mode": "creator", 
  "storagePath": "users/UID_123/documents/DOC_999/Contract_Signed.pdf",
  "downloadUrl": "https://firebasestorage.googleapis.com/...",
  "createdAt": "2026-08-13T10:10:00Z"
}
```

### Cloud Storage Folder Structure
```
gs://your-app-bucket.appspot.com/
  └── users/
      └── {uid}/
          └── documents/
              └── {docId}/
                  ├── original.pdf
                  └── signed_output.pdf
```

---

## 📕 Complete Reference: Exhaustive List of Adobe Acrobat PDF App Features

Below is an exhaustive reference list of all features across Adobe Acrobat (Desktop, Mobile, Web, and Acrobat Pro DC).

### 1. 👁️ Viewing, Reading & Accessibility Experience
- **Liquid Mode:** Responsive mobile reflow powered by Adobe Sensei AI for optimized reading on smaller screens.
- **Viewing Modes:** Single Page, Continuous Scroll, Two-Page Spread, Two-Page Continuous, Cover Page View.
- **Zoom & Navigation:** Zoom In/Out, Fit Width, Fit Page, Fit Visible, Actual Size (100%), Dynamic Zoom Tool, Pan & Loupe Tool.
- **Color Modes & Themes:** Dark Theme, Light Theme, System Theme, Sepia Mode, High Contrast Mode.
- **Read Out Loud (Text-to-Speech):** Built-in screen reader reading single page or entire document with customizable speed and pitch.
- **Accessibility Engine (PDF/UA):** Accessibility Checker, Reading Order Tool, Auto-Tagging, Alt-Text Editor for Images, Structure Tree Inspector.
- **Document Navigation:** Page Thumbnails Panel, Bookmarks / Outlines Tree, Attachments Pane, Layers Pane, Article Threads.
- **Presentation & Full Screen:** Full-Screen Mode with customizable slide transitions and pointer tools.

### 2. 📄 Create & Export PDF (Document Conversion)
- **Create PDF from File:** Convert Microsoft Office files (.docx, .xlsx, .pptx), Text (.txt), Rich Text (.rtf), Images (.png, .jpg, .tiff, .bmp), and PostScript (.ps).
- **Create PDF from Scanner / Camera:** Direct scanner driver integration (TWAIN/WIA) and mobile camera scan with edge detection.
- **Create PDF from Web Page:** Convert full web pages or HTML files to PDF with active hyperlinks preserved.
- **Create PDF from Clipboard:** Generate PDF directly from copied image or text data on system clipboard.
- **Export PDF to Office Formats:** Convert PDF to editable Word (.docx), Excel (.xlsx), and PowerPoint (.pptx).
- **Export PDF to Image Formats:** Export PDF pages as JPEG, PNG, TIFF, or JPEG 2000.
- **Export PDF to Text & HTML:** Export as Plain Text (.txt), Rich Text Format (.rtf), HTML 5, or XML.
- **Batch Processing:** Combine, convert, or export multiple files simultaneously in batch jobs.

### 3. ✏️ PDF Content Editing & Page Manipulation
- **Text Editing:** Edit paragraph text with automatic line-wrapping and paragraph reflow; change font family, font size, text color, bold, italic, underline, superscript, subscript, line spacing, paragraph alignment, character spacing (kerning), and horizontal scaling.
- **Image Editing:** Insert, replace, delete, resize, rotate, flip (horizontal/vertical), crop, align, arrange z-order (bring forward/send backward), and adjust opacity/transparency of images.
- **Object & Vector Editing:** Select, move, resize, group, ungroup, align, and edit vector paths/shapes.
- **Page Manipulation:**
  - **Insert Pages:** From file, scanner, clipboard, or blank page.
  - **Delete Pages:** Delete selected page ranges.
  - **Extract Pages:** Extract selected pages into a separate new PDF (with option to delete after extraction).
  - **Replace Pages:** Swap specific pages with pages from another PDF.
  - **Rotate Pages:** Clockwise 90°, Counterclockwise 90°, or 180° (selected pages or all pages).
  - **Reorder Pages:** Drag-and-drop page thumbnail arrangement.
  - **Split PDF:** Split single PDF into multiple documents by page count, file size, or top-level bookmarks.
  - **Combine / Merge PDF:** Merge multiple PDFs, images, and office documents into a unified PDF binder.
- **Headers, Footers & Page Numbers:** Add/edit dynamic headers and footers, date/time, document title, and automated page numbering.
- **Bates Numbering:** Apply legal Bates numbering (prefixes, suffixes, zero-padded numbers) across multiple documents.
- **Watermarks & Backgrounds:** Add text or image watermarks with custom rotation, opacity, scale, and page range; set document background color or background image.
- **Page Box Editing:** Adjust Crop Box, Trim Box, Bleed Box, Art Box, and Media Box dimensions.

### 4. 💬 Annotations, Comments & Markup Collaboration
- **Text Markup Tools:** Highlight text, Underline text, Strikethrough text, Replace text, Add note to text.
- **Comment Tools:** Sticky Notes, Typewriter Text Box, Callout Text Box, Floating Text Comment.
- **Freehand Drawing:** Pencil / Pen Tool with customizable color, line width, and opacity; Eraser tool.
- **Drawing Shapes:** Rectangle, Oval / Circle, Line, Arrow, Polygon, Polygon Line, Cloud Shape Callout.
- **Stamp Tool:**
  - **Standard Business Stamps:** APPROVED, REJECTED, CONFIDENTIAL, DRAFT, FINAL, FOR PUBLIC RELEASE, COMPLETED.
  - **Dynamic Stamps:** Stamps auto-populated with current user name, date, and time.
  - **Custom Stamps:** Create custom stamps from PNG/JPEG images or vector files.
- **File & Audio Attachments:** Attach raw files or record audio voice comments directly into the PDF layout.
- **Measurement Tools:** Distance Tool, Perimeter Tool, Area Tool (with scale calibration for architectural drawings).
- **Real-Time Collaborative Review:** Share PDF via link, multi-user simultaneous commenting, @mention team members, comment filter/sort/search, status tags (Accepted, Rejected, Cancelled, Completed), export/import comments (FDF/XFDF).

### 5. 📋 Fillable Forms & Data Collection
- **Automatic Form Field Recognition:** Auto-detect form fields on scanned documents using AI.
- **Form Field Authoring:** Insert Text Fields, Checkboxes, Radio Buttons, Dropdown Lists, List Boxes, Push Buttons, Digital Signature Fields, Image Upload Fields, and Date Fields.
- **Form Field Properties:** Tooltips, Required/Optional flags, Read-Only state, Default Values, Character Limits, Multi-line support, Password mask.
- **Form Validation & Formatting:** Format fields as Number, Percentage, Date, Time, Zip Code, Phone Number, Social Security Number, or Custom Regex.
- **JavaScript & Calculations:** Custom JavaScript execution on field change, focus, blur, or calculate (Sum, Product, Average, Min, Max, Custom Math formula).
- **Form Data Import & Export:** Export response data as FDF, XFDF, XML, or CSV; import pre-filled data files.
- **Distribute & Collect Forms:** Send forms to multiple recipients, track response status, and automatically compile response dataset into a summary spreadsheet.

### 6. ✍️ Signatures, E-Sign & Digital Certificates
- **Adobe Fill & Sign:**
  - Type name with stylized handwriting fonts.
  - Draw signature using mouse, stylus, or touchscreen.
  - Upload image of paper signature.
  - Capture signature via mobile camera with automatic background removal.
  - Store initials & signature in user profile for one-click placement.
- **Adobe Acrobat Sign (Enterprise E-Sign Workflows):**
  - Send for Signature: Request legally binding signatures from multiple signers.
  - Specify Signing Order: Parallel or sequential multi-party routing.
  - Assign Roles: Signer, Approver, Acceptor, Certified Recipient, Form Filler.
  - In-flight Tracking: Real-time status notifications, reminder triggers, deadline expiration.
  - Audit Trail & Certificate of Completion: Complete audit log recording IP addresses, email verification, timestamps, and tamper-evident SHA-256 digital seal.
- **Digital Certificates & PKI Signatures:**
  - Sign with Digital ID (PFX/P12 files, Windows Certificate Store, macOS Keychain, Smart Cards, Hardware Tokens).
  - Time Stamp Authority (TSA) integration for RFC 3161 compliant timestamping.
  - Long-Term Validation (LTV) enabling signature verification years into the future.
  - Certificate Revocation Check via CRL (Certificate Revocation List) and OCSP.

### 7. 🔐 Security, Encryption & Redaction
- **Password Protection:**
  - Document Open Password (require password to view content).
  - Permissions / Change Password (restrict printing, high-res printing, content copying, editing, commenting, form filling, page extraction).
- **Encryption Standards:** 128-bit AES, 256-bit AES (Acrobat 9.0+), 128-bit RC4, 40-bit RC4.
- **Certificate Encryption:** Encrypt PDF for specific recipient public key certificates.
- **Permanent Redaction:**
  - Mark for Redaction: Highlight text, images, or page areas to be permanently removed.
  - Apply Redaction: Permanently burn out underlying vector, raster, and text data (irreversible blackout).
  - Auto-Redact / Search & Redact: Automatically locate and redact SSNs, Credit Card Numbers, Email Addresses, Phone Numbers, or custom RegEx strings across multi-page documents.
- **Sanitize Document / Remove Hidden Info:** Strip hidden metadata, hidden text, unattached annotations, embedded search indexes, form fields, deleted object remnants, and file attachments.
- **Policy Protection & Security Envelopes:** Digital Rights Management (DRM) integration to revoke document access remotely.

### 8. 🔍 OCR & Scanning Tools
- **Optical Character Recognition (OCR Engine):** Recognizes text in scanned images across 40+ global languages.
- **Searchable Image Mode:** Keeps exact visual scan background while overlaying invisible, searchable text behind it.
- **Editable Text Mode:** Converts scanned image pages into fully editable PDF fonts, paragraphs, and vector layouts.
- **Scan Enhancement Cleanup:**
  - Auto-Deskew (straighten crooked scans).
  - De-speckle (remove scanner dust and spots).
  - Background Cleaning (turn gray/yellow paper white).
  - Edge Detection & Automatic Page Trimming.
  - Color & Contrast Auto-Correction.

### 9. 🖨️ PDF Standards, Preflight & Commercial Printing
- **PDF Standards Validation & Conversion:**
  - **PDF/A:** Archival standard (PDF/A-1b, PDF/A-2b, PDF/A-3b).
  - **PDF/X:** Commercial printing standard (PDF/X-1a, PDF/X-3, PDF/X-4).
  - **PDF/E:** Engineering & technical drawings standard.
  - **PDF/VT:** Variable data and transactional printing.
  - **PDF/UA:** Universal Accessibility standard.
- **Preflight Inspection:** Automated check for low-resolution images, missing/unembedded fonts, RGB colors in print workflows, thin hair lines, overprint errors, and ink coverage limits.
- **Color Management & Separation Preview:** CMYK color separation inspection, Spot Color mapping, Pantone color libraries, and Overprint preview.
- **Printer Marks Generator:** Add trim marks, bleed marks, registration marks, color bars, and page information.
- **Flattening Engine:** Flatten layers, transparency, and annotations into base page graphics.

### 10. 🤖 Advanced Tools, AI & Platform Ecosystem
- **Adobe Acrobat AI Assistant:**
  - Generative AI chat interface to ask questions about single or multiple PDFs.
  - Instant executive summaries, key takeaways, and structured outlines.
  - Interactive clickable citation links jumping directly to source pages.
  - Draft email summaries, study guides, and presentation points.
- **Compare Documents:** Compare two PDF versions side-by-side with visual pixel diff highlights, text insertion/deletion reports, and summary of changes.
- **Action Wizard (Batch Automation):** Create customizable multi-step macro routines (e.g. OCR -> Add Watermark -> Sanitize -> Apply Password -> Export to Storage).
- **Index Engine (Full-Text Search Index):** Build `.pdx` search catalogs across thousands of PDFs for instantaneous deep search.
- **3D PDF Engine:** Embed, view, rotate, pan, slice, measure, and render interactive 3D models (U3D and PRC formats).
- **Geospatial PDF Tools:** View map coordinates (latitude/longitude), measure distance, and track GPS position on geospatial PDFs.
- **Cloud Storage & Ecosystem Integrations:** Native integration with Adobe Document Cloud, Google Drive, Microsoft OneDrive, SharePoint, Dropbox, and Box.
- **Cross-Platform Availability:** Windows desktop application, macOS desktop application, Web Browser App (Acrobat Web), Chrome & Edge Extensions, iOS Mobile App, Android Mobile App.

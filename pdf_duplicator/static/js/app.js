// Apple HIG PDF Duplicator & Sign Studio - Multi-Signature Application Logic

document.addEventListener("DOMContentLoaded", () => {
    const store = window.appStore;

    // --- DOM Elements ---
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const pwaInstallBtn = document.getElementById("pwaInstallBtn");
    const segmentedButtons = document.querySelectorAll(".segmented-item");
    
    // Cards
    const documentUploadCard = document.getElementById("documentUploadCard");
    const signControlsCard = document.getElementById("signControlsCard");
    const textControlsCard = document.getElementById("textControlsCard");
    const mergeControlsCard = document.getElementById("mergeControlsCard");
    const duplicateControlsCard = document.getElementById("duplicateControlsCard");
    const cloneControlsCard = document.getElementById("cloneControlsCard");
    
    // Merge Controls
    const mergeDropzone = document.getElementById("mergeDropzone");
    const mergeFileInput = document.getElementById("mergeFileInput");
    const mergeFileList = document.getElementById("mergeFileList");
    const customOutputFilenameInput = document.getElementById("customOutputFilenameInput");
    
    // Upload & Doc
    const dropzone = document.getElementById("dropzone");
    const pdfFileInput = document.getElementById("pdfFileInput");
    const docInfoCard = document.getElementById("docInfoCard");
    const docName = document.getElementById("docName");
    const docMeta = document.getElementById("docMeta");
    const removeDocBtn = document.getElementById("removeDocBtn");
    const passwordSection = document.getElementById("passwordSection");
    const pdfPasswordInput = document.getElementById("pdfPasswordInput");

    // Action Button
    const processActionBtn = document.getElementById("processActionBtn");
    const actionBtnText = document.getElementById("actionBtnText");
    const actionSpinner = document.getElementById("actionSpinner");
    const statusAlert = document.getElementById("statusAlert");

    // --- Sidebar Resize Handle ---
    (function initSidebarResize() {
        const handle = document.getElementById("sidebarResizeHandle");
        const sidebar = document.getElementById("sidebarPanel");
        if (!handle || !sidebar) return;

        let isResizing = false;
        let startX = 0;
        let startWidth = 0;
        const MIN_WIDTH = 160;
        const MAX_WIDTH = 480;

        handle.addEventListener("mousedown", (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = sidebar.offsetWidth;
            handle.classList.add("dragging");
            document.body.style.cursor = "col-resize";
            document.body.style.userSelect = "none";
            e.preventDefault();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isResizing) return;
            const dx = e.clientX - startX;
            const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + dx));
            sidebar.style.width = newWidth + "px";
        });

        document.addEventListener("mouseup", () => {
            if (!isResizing) return;
            isResizing = false;
            handle.classList.remove("dragging");
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        });
    })();

    // Stage
    const stageViewport = document.getElementById("stageViewport") || document.querySelector(".stage-viewport");
    const emptyStageNotice = document.getElementById("emptyStageNotice");
    const pdfCanvasContainer = document.getElementById("pdfCanvasContainer");
    const pdfPageImg = document.getElementById("pdfPageImg");
    const prevPageBtn = document.getElementById("prevPageBtn");
    const nextPageBtn = document.getElementById("nextPageBtn");
    const currentPageNumEl = document.getElementById("currentPageNum");
    const totalPagesNumEl = document.getElementById("totalPagesNum");
    const thumbnailRibbon = document.getElementById("thumbnailRibbon");

    // Multi-Signature Controls
    const openSigStudioBtn = document.getElementById("openSigStudioBtn");
    const multiSigListCard = document.getElementById("multiSigListCard");
    const sigCountNum = document.getElementById("sigCountNum");
    const placedSignaturesContainer = document.getElementById("placedSignaturesContainer");
    
    const signPagesMode = document.getElementById("signPagesMode");
    const customPageRangeGroup = document.getElementById("customPageRangeGroup");
    const signPageSpecInput = document.getElementById("signPageSpecInput");
    
    const sigXInput = document.getElementById("sigXInput");
    const sigYInput = document.getElementById("sigYInput");
    const sigWInput = document.getElementById("sigWInput");
    const sigHInput = document.getElementById("sigHInput");

    const sigRotSlider = document.getElementById("sigRotSlider");
    const sigRotValue = document.getElementById("sigRotValue");
    const sigRotResetBtn = document.getElementById("sigRotResetBtn");
    const sigRot90Btn = document.getElementById("sigRot90Btn");

    const undoBtn = document.getElementById("undoBtn");
    const redoBtn = document.getElementById("redoBtn");

    // Duplication Inputs
    const dupPagesInput = document.getElementById("dupPagesInput");
    const dupCountInput = document.getElementById("dupCountInput");
    const stepperMinusBtn = document.getElementById("stepperMinusBtn");
    const stepperPlusBtn = document.getElementById("stepperPlusBtn");

    // Signature Studio Modal
    const sigStudioModal = document.getElementById("sigStudioModal");
    const closeSigStudioBtn = document.getElementById("closeSigStudioBtn");
    const cancelSigModalBtn = document.getElementById("cancelSigModalBtn");
    const saveSigModalBtn = document.getElementById("saveSigModalBtn");
    const modalTabs = document.querySelectorAll(".modal-tab");
    const tabDraw = document.getElementById("tabDraw");
    const tabUpload = document.getElementById("tabUpload");
    const tabLibrary = document.getElementById("tabLibrary");
    const sigLibraryGrid = document.getElementById("sigLibraryGrid");
    
    const sigCanvas = document.getElementById("sigCanvas");
    const canvasCtx = sigCanvas ? sigCanvas.getContext("2d") : null;
    const clearCanvasBtn = document.getElementById("clearCanvasBtn");
    const colorBtns = document.querySelectorAll(".color-btn");
    const strokeWidthInput = document.getElementById("strokeWidthInput");
    const sigImageFileInput = document.getElementById("sigImageFileInput");
    const sigUploadDropzone = document.querySelector(".sig-upload-dropzone");
    const uploadedSigPreview = document.getElementById("uploadedSigPreview");
    const uploadedSigImg = document.getElementById("uploadedSigImg");

    // Active Selection State
    let selectedSigId = null;
    let isDrawing = false;
    let activeColor = "#000000";
    let strokeWidth = 3;
    let canvasScale = 1; // backing-buffer px per CSS px for sigCanvas; keeps drawn strokes sharp on HiDPI screens

    // --- PWA Installation Event Listener ---
    let deferredInstallPrompt = null;
    window.addEventListener("beforeinstallprompt", (e) => {
        e.preventDefault();
        deferredInstallPrompt = e;
        if (pwaInstallBtn) pwaInstallBtn.classList.remove("hidden");
    });

    if (pwaInstallBtn) {
        pwaInstallBtn.addEventListener("click", () => {
            if (deferredInstallPrompt) {
                deferredInstallPrompt.prompt();
                deferredInstallPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === "accepted") {
                        console.log("[PWA] User accepted install prompt");
                    }
                    deferredInstallPrompt = null;
                    pwaInstallBtn.classList.add("hidden");
                });
            }
        });
    }

    // --- Theme Subscriptions ---
    if (store.state.theme === "light-mode") {
        document.body.classList.remove("dark-mode");
        document.body.classList.add("light-mode");
    }

    themeToggleBtn.addEventListener("click", () => {
        const nextTheme = document.body.classList.contains("dark-mode") ? "light-mode" : "dark-mode";
        store.setTheme(nextTheme);
    });

    store.subscribe("theme:changed", (theme) => {
        document.body.className = theme;
    });

    // --- Mode Switcher Subscriptions ---
    segmentedButtons.forEach(btn => {
        btn.addEventListener("click", () => store.setMode(btn.dataset.mode));
    });

    store.subscribe("mode:changed", (mode) => {
        segmentedButtons.forEach(b => b.classList.toggle("active", b.dataset.mode === mode));
        signControlsCard.classList.add("hidden");
        if (textControlsCard) textControlsCard.classList.add("hidden");
        if (mergeControlsCard) mergeControlsCard.classList.add("hidden");
        duplicateControlsCard.classList.add("hidden");
        cloneControlsCard.classList.add("hidden");

        if (documentUploadCard) documentUploadCard.classList.remove("hidden");

        if (mode === "sign") {
            signControlsCard.classList.remove("hidden");
            if (textControlsCard) textControlsCard.classList.remove("hidden");
            actionBtnText.textContent = "Save";
            renderStageSignatures();
        } else if (mode === "merge") {
            if (mergeControlsCard) mergeControlsCard.classList.remove("hidden");
            actionBtnText.textContent = "Save";
            clearStageOverlays();
            updateMergedStagePreview(store.state.merge.files);
        } else if (mode === "duplicate") {
            duplicateControlsCard.classList.remove("hidden");
            actionBtnText.textContent = "Save";
            clearStageOverlays();
        } else if (mode === "clone") {
            cloneControlsCard.classList.remove("hidden");
            actionBtnText.textContent = "Save";
            clearStageOverlays();
        }
        updateSaveBtn();
    });

    // --- File Upload & Document Subscriptions ---
    dropzone.addEventListener("click", () => pdfFileInput.click());
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    pdfFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
        }
    });

    removeDocBtn.addEventListener("click", () => store.resetDocument());

    pdfPasswordInput.addEventListener("change", () => {
        const file = store.state.document.fileObj || pendingUploadFile;
        if (file) {
            handleFileUpload(file);
        }
    });

    // Holds the raw File across an "enter password" retry. store.setDocument() (which is what
    // normally remembers the file as document.fileObj) is never called for an encrypted PDF until
    // the password succeeds, so without this the retry request had no file to resend and typing
    // the correct password silently did nothing.
    let pendingUploadFile = null;

    function handleFileUpload(file) {
        showStatus(null);
        const formData = new FormData();
        formData.append("file", file);
        if (pdfPasswordInput.value) {
            formData.append("password", pdfPasswordInput.value);
        }

        fetch("/api/inspect-pdf", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                if (data.is_encrypted) {
                    passwordSection.classList.remove("hidden");
                    pendingUploadFile = file;
                }
                showStatus(data.error, "error");
                return;
            }
            pendingUploadFile = null;

            store.setDocument({
                fileId: data.file_id,
                fileObj: file,
                filename: file.name,
                totalPages: data.total_pages,
                isEncrypted: data.is_encrypted,
                currentPage: 1,
                pagePreviews: data.page_previews,
                pageDimensions: data.page_dimensions
            });

            if (store.state.currentMode === "merge") {
                const existing = store.state.merge.files.find(f => f.fileId === data.file_id || f.filename === file.name);
                if (!existing) {
                    store.addMergeFile({
                        fileId: data.file_id || null,
                        fileObj: file,
                        filename: file.name,
                        totalPages: data.total_pages || 0,
                        isEncrypted: !!data.is_encrypted,
                        password: pdfPasswordInput.value || "",
                        pagesSpec: "",
                        pagePreviews: data.page_previews || []
                    });
                }
            }
        })
        .catch(err => {
            showStatus("Failed to inspect PDF: " + err.message, "error");
        });
    }

    // --- Save Button State Helper ---
    function updateSaveBtn() {
        const doc = store.state.document;
        const mode = store.state.currentMode;
        const hasDoc = !!(doc && (doc.filename || doc.fileId || doc.fileObj));
        let hasEdits = false;

        if (mode === "sign") {
            hasEdits = hasDoc && store.state.signature.activeSignaturesOnDoc && store.state.signature.activeSignaturesOnDoc.length > 0;
        } else if (mode === "merge") {
            hasEdits = store.state.merge.files && store.state.merge.files.length > 0;
        } else {
            // duplicate / clone just need a doc
            hasEdits = hasDoc;
        }

        processActionBtn.disabled = !hasEdits;
    }

    // --- Custom Output Filename Input Listener ---
    if (customOutputFilenameInput) {
        customOutputFilenameInput.addEventListener("input", (e) => {
            store.setCustomOutputFilename(e.target.value);
        });
    }

    // --- Merge Mode Dropzone & Queue Event Listeners ---
    if (mergeDropzone && mergeFileInput) {
        mergeDropzone.addEventListener("click", () => mergeFileInput.click());
        mergeDropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            mergeDropzone.classList.add("dragover");
        });
        mergeDropzone.addEventListener("dragleave", () => mergeDropzone.classList.remove("dragover"));
        mergeDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            mergeDropzone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleMergeFilesUpload(Array.from(e.dataTransfer.files));
            }
        });
        mergeFileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleMergeFilesUpload(Array.from(e.target.files));
                mergeFileInput.value = "";
            }
        });
    }

    function handleMergeFilesUpload(filesList) {
        filesList.forEach(file => {
            if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
                return;
            }
            const formData = new FormData();
            formData.append("file", file);
            fetch("/api/inspect-pdf", {
                method: "POST",
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.error && !data.is_encrypted) {
                    showStatus(data.error, "error");
                    return;
                }
                store.addMergeFile({
                    fileId: data.file_id || null,
                    fileObj: file,
                    filename: file.name,
                    totalPages: data.total_pages || 0,
                    isEncrypted: !!data.is_encrypted,
                    password: "",
                    pagesSpec: "",
                    pagePreviews: data.page_previews || []
                });
            })
            .catch(err => {
                showStatus(err.message, "error");
            });
        });
    }

    store.subscribe("merge:files_updated", (files) => {
        renderMergeFileList(files);
        updateSaveBtn();
        updateMergedStagePreview(files);
    });

    let draggedMergeItemIdx = null;

    function renderMergeFileList(files) {
        if (!mergeFileList) return;
        mergeFileList.innerHTML = "";
        if (!files || files.length === 0) {
            mergeFileList.innerHTML = `<p class="empty-list-notice" style="font-size: 0.72rem; color: var(--text-secondary); text-align: center; padding: 10px 0;">No PDFs added yet. Drop or select PDF files to merge.</p>`;
            return;
        }

        files.forEach((fileItem, idx) => {
            const itemEl = document.createElement("div");
            itemEl.className = "merge-file-item";
            itemEl.draggable = true;
            itemEl.dataset.id = fileItem.id;
            itemEl.dataset.index = idx;

            const thumbSrc = (fileItem.pagePreviews && fileItem.pagePreviews[0]) ? fileItem.pagePreviews[0] : "";
            const thumbHtml = thumbSrc ? `<img src="${thumbSrc}" class="merge-file-thumb" alt="thumb">` : `<div class="merge-file-icon">📄</div>`;

            itemEl.innerHTML = `
                <div class="merge-item-drag-handle" title="Drag to reorder (Pos #${idx + 1})">
                    <span class="merge-pos-badge">#${idx + 1}</span>
                    <span class="drag-dots">⋮⋮</span>
                </div>
                ${thumbHtml}
                <div class="merge-item-info">
                    <div class="merge-item-header">
                        <span class="merge-item-title" title="${fileItem.filename}">${fileItem.filename}</span>
                        <span class="merge-item-meta">${fileItem.totalPages} page${fileItem.totalPages !== 1 ? 's' : ''} ${fileItem.isEncrypted ? '🔐' : ''}</span>
                    </div>
                    ${fileItem.isEncrypted ? `
                        <input type="password" class="apple-input small margin-top-xs merge-pwd-input" placeholder="Password required..." value="${fileItem.password || ''}">
                    ` : ''}
                    <div class="margin-top-xs">
                        <input type="text" class="apple-input small merge-spec-input" placeholder="Page range e.g. 1-3 (optional)" value="${fileItem.pagesSpec || ''}">
                    </div>
                </div>
                <div class="merge-item-actions">
                    <button class="merge-btn-order move-up-btn" title="Move Up" ${idx === 0 ? 'disabled' : ''}>▲</button>
                    <button class="merge-btn-order move-down-btn" title="Move Down" ${idx === files.length - 1 ? 'disabled' : ''}>▼</button>
                    <button class="merge-btn-remove remove-merge-btn" title="Remove PDF">✕</button>
                </div>
            `;

            // HTML5 Drag and Drop Event Listeners
            itemEl.addEventListener("dragstart", (e) => {
                draggedMergeItemIdx = idx;
                itemEl.classList.add("dragging");
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", idx);
            });

            itemEl.addEventListener("dragend", () => {
                itemEl.classList.remove("dragging");
                document.querySelectorAll(".merge-file-item").forEach(el => el.classList.remove("drag-over"));
                draggedMergeItemIdx = null;
            });

            itemEl.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                itemEl.classList.add("drag-over");
            });

            itemEl.addEventListener("dragleave", () => {
                itemEl.classList.remove("drag-over");
            });

            itemEl.addEventListener("drop", (e) => {
                e.preventDefault();
                itemEl.classList.remove("drag-over");
                if (draggedMergeItemIdx !== null && draggedMergeItemIdx !== idx) {
                    store.moveMergeFile(draggedMergeItemIdx, idx);
                }
            });

            const moveUpBtn = itemEl.querySelector(".move-up-btn");
            const moveDownBtn = itemEl.querySelector(".move-down-btn");
            const removeBtn = itemEl.querySelector(".remove-merge-btn");
            const pwdInput = itemEl.querySelector(".merge-pwd-input");
            const specInput = itemEl.querySelector(".merge-spec-input");

            if (moveUpBtn) moveUpBtn.addEventListener("click", () => store.moveMergeFile(idx, idx - 1));
            if (moveDownBtn) moveDownBtn.addEventListener("click", () => store.moveMergeFile(idx, idx + 1));
            if (removeBtn) removeBtn.addEventListener("click", () => store.removeMergeFile(fileItem.id));

            if (pwdInput) {
                pwdInput.addEventListener("input", (e) => store.updateMergeFile(fileItem.id, { password: e.target.value }));
            }
            if (specInput) {
                specInput.addEventListener("input", (e) => store.updateMergeFile(fileItem.id, { pagesSpec: e.target.value }));
            }

            mergeFileList.appendChild(itemEl);
        });
    }


    function updateMergedStagePreview(files) {
        if (store.state.currentMode !== "merge") return;
        if (!files || files.length === 0) {
            emptyStageNotice.classList.remove("hidden");
            pdfCanvasContainer.classList.add("hidden");
            thumbnailRibbon.classList.add("hidden");
            return;
        }
        const firstFile = files[0];
        if (firstFile && firstFile.pagePreviews && firstFile.pagePreviews.length > 0) {
            emptyStageNotice.classList.add("hidden");
            pdfCanvasContainer.classList.remove("hidden");
            thumbnailRibbon.classList.remove("hidden");
            pdfPageImg.src = firstFile.pagePreviews[0];
            currentPageNumEl.textContent = "1";
            const totalMergedPages = files.reduce((acc, f) => acc + (f.totalPages || 0), 0);
            totalPagesNumEl.textContent = totalMergedPages;
        }
    }


    store.subscribe("document:loaded", (doc) => {
        docName.textContent = doc.filename;
        docMeta.textContent = `${doc.totalPages} page${doc.totalPages > 1 ? 's' : ''}`;
        dropzone.classList.add("hidden");
        docInfoCard.classList.remove("hidden");
        if (!doc.isEncrypted) {
            passwordSection.classList.add("hidden");
        }

        renderStagePage(1);
        renderThumbnails();
        updateSaveBtn();
    });

    store.subscribe("document:reset", () => {
        pendingUploadFile = null;
        pdfFileInput.value = "";
        pdfPasswordInput.value = "";
        docInfoCard.classList.add("hidden");
        passwordSection.classList.add("hidden");
        dropzone.classList.remove("hidden");
        pdfCanvasContainer.classList.add("hidden");
        thumbnailRibbon.classList.add("hidden");
        emptyStageNotice.classList.remove("hidden");
        clearStageOverlays();
        updateSaveBtn();
    });

    // --- Page Navigation & Stage Rendering ---
    function renderStagePage(pageNum) {
        const doc = store.state.document;
        if (pageNum < 1 || pageNum > doc.totalPages) return;
        store.setCurrentPage(pageNum);
    }

    store.subscribe("page:changed", (pageNum) => {
        const doc = store.state.document;
        currentPageNumEl.textContent = pageNum;
        totalPagesNumEl.textContent = doc.totalPages;

        document.querySelectorAll(".current-page-num").forEach(el => el.textContent = pageNum);

        prevPageBtn.disabled = pageNum <= 1;
        nextPageBtn.disabled = pageNum >= doc.totalPages;

        emptyStageNotice.classList.add("hidden");
        pdfCanvasContainer.classList.remove("hidden");
        thumbnailRibbon.classList.remove("hidden");

        pdfPageImg.src = doc.pagePreviews[pageNum - 1];
        pdfPageImg.onload = () => {
            renderStageSignatures();
        };

        document.querySelectorAll(".thumb-card").forEach((card, idx) => {
            card.classList.toggle("active", idx === pageNum - 1);
        });
    });

    prevPageBtn.addEventListener("click", () => renderStagePage(store.state.document.currentPage - 1));
    nextPageBtn.addEventListener("click", () => renderStagePage(store.state.document.currentPage + 1));

    function renderThumbnails() {
        thumbnailRibbon.innerHTML = "";
        store.state.document.pagePreviews.forEach((b64, idx) => {
            const card = document.createElement("div");
            card.className = `thumb-card ${idx === 0 ? 'active' : ''}`;
            card.innerHTML = `<img src="${b64}" alt="Page ${idx + 1}">`;
            card.addEventListener("click", () => renderStagePage(idx + 1));
            thumbnailRibbon.appendChild(card);
        });
    }

    // CSS px (pre-stage-zoom) per PDF point. Overlay elements are positioned in this space via
    // plain `left`/`top`/`width`/`height`, and the stage's zoom transform (see setStageZoom) then
    // scales that whole layer for display along with everything else in it — so this must stay
    // based on `clientWidth`, which (unlike getBoundingClientRect) ignores CSS transforms.
    // For converting a real on-screen point (a mouse event's clientX/clientY) into PDF-point
    // space, use screenToDocument() instead, which accounts for the current zoom.
    function getScaleFactor() {
        const doc = store.state.document;
        if (!doc.pageDimensions.length || !pdfPageImg.clientWidth) return 1.0;
        const pageDim = doc.pageDimensions[doc.currentPage - 1] || doc.pageDimensions[0];
        return pdfPageImg.clientWidth / pageDim.width;
    }

    // --- Permanent Multi-Signature Library Tray & Drag-and-Drop ---
    const signatureTrayContainer = document.getElementById("signatureTrayContainer");
    const stampBanner = document.getElementById("stampBanner");
    const stopStampBtn = document.getElementById("stopStampBtn");
    const signatureGhostCursor = document.getElementById("signatureGhostCursor");
    const ghostSigImg = document.getElementById("ghostSigImg");

    let isStampModeActive = false;
    let draggedSigUrl = null;

    function setStampMode(active) {
        isStampModeActive = active;
        if (stageViewport) {
            stageViewport.classList.toggle("stamp-active", active);
        }
        if (stampBanner) {
            stampBanner.classList.toggle("hidden", !active);
        }
        if (signatureGhostCursor) {
            signatureGhostCursor.classList.toggle("hidden", !active);
        }
        renderSignatureTray();
    }

    if (stopStampBtn) {
        stopStampBtn.addEventListener("click", () => setStampMode(false));
    }

    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && isStampModeActive) {
            setStampMode(false);
        }
    });

    // Follow Mouse Cursor for Figma Ghost Stamp
    window.addEventListener("mousemove", (e) => {
        if (isStampModeActive && signatureGhostCursor) {
            signatureGhostCursor.style.left = `${e.clientX}px`;
            signatureGhostCursor.style.top = `${e.clientY}px`;
        }
    });

    // Render Draggable & Clickable Signature Tray
    function renderSignatureTray() {
        if (!signatureTrayContainer) return;
        const savedSignatures = store.state.signature.savedSignatures;

        if (!savedSignatures || savedSignatures.length === 0) {
            signatureTrayContainer.innerHTML = `<div class="empty-tray-notice">No signatures yet.</div>`;
            return;
        }

        signatureTrayContainer.innerHTML = "";
        savedSignatures.forEach((item, index) => {
            const isCarrying = isStampModeActive && store.state.signature.activeDataUrl === item.dataUrl;
            const card = document.createElement("div");
            card.className = `tray-sig-card ${isCarrying ? 'active-carrying' : ''}`;
            card.draggable = true;
            card.dataset.id = item.id;

            card.innerHTML = `
                <div class="tray-sig-left">
                    <span class="tray-sig-drag-handle" title="Drag onto PDF">⋮⋮</span>
                    <div class="tray-sig-thumb">
                        <img src="${item.dataUrl}" alt="Signature ${index + 1}">
                    </div>
                </div>
                <button class="overlay-action-btn btn-remove small" title="Delete">✕</button>
            `;

            // HTML5 Drag Event Handlers (Supports PDF drop + Tray Reordering)
            card.addEventListener("dragstart", (e) => {
                draggedSigUrl = item.dataUrl;
                e.dataTransfer.setData("text/plain", item.dataUrl);
                e.dataTransfer.setData("text/tray-index", index.toString());
                e.dataTransfer.effectAllowed = "copyMove";
                card.classList.add("dragging-source");

                // Hide floating stamp ghost cursor so it doesn't double render
                if (signatureGhostCursor) signatureGhostCursor.classList.add("hidden");

                // Set clean drag image of the signature thumbnail only
                const thumbImg = card.querySelector(".tray-sig-thumb img");
                if (thumbImg && e.dataTransfer.setDragImage) {
                    e.dataTransfer.setDragImage(thumbImg, thumbImg.clientWidth / 2, thumbImg.clientHeight / 2);
                }
            });

            card.addEventListener("dragend", () => {
                draggedSigUrl = null;
                card.classList.remove("dragging-source");
                document.querySelectorAll(".tray-sig-card").forEach(c => c.classList.remove("drag-over-target"));
                if (isStampModeActive && signatureGhostCursor) {
                    signatureGhostCursor.classList.remove("hidden");
                }
            });

            card.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                card.classList.add("drag-over-target");
            });

            card.addEventListener("dragleave", () => {
                card.classList.remove("drag-over-target");
            });

            card.addEventListener("drop", (e) => {
                card.classList.remove("drag-over-target");
                const fromIdxStr = e.dataTransfer.getData("text/tray-index");
                if (fromIdxStr !== "") {
                    const fromIdx = parseInt(fromIdxStr);
                    if (!isNaN(fromIdx) && fromIdx !== index) {
                        e.stopPropagation();
                        store.reorderSignaturesInLibrary(fromIdx, index);
                    }
                }
            });

            // Click Handler for Stamp Carrying
            card.addEventListener("click", (e) => {
                if (e.target.closest(".btn-remove")) {
                    store.deleteSignatureFromLibrary(item.id);
                    return;
                }
                store.setActiveSignature(item.dataUrl);
                setStampMode(true);
            });

            signatureTrayContainer.appendChild(card);
        });
    }


    store.subscribe("signature:library_updated", () => renderSignatureTray());

    // Canvas Drop & Click Handlers for Multi-Signature Placement
    if (pdfCanvasContainer) {
        // Drag over PDF page
        pdfCanvasContainer.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
        });

        // Drop Signature onto PDF Page
        pdfCanvasContainer.addEventListener("drop", (e) => {
            e.preventDefault();
            const sigUrl = e.dataTransfer.getData("text/plain") || draggedSigUrl;
            if (!sigUrl) return;

            const dropPos = screenToDocument(e.clientX, e.clientY);
            const sigW = store.state.placement.width || 150;
            const sigH = store.state.placement.height || 60;
            const pdfX = Math.max(0, Math.round(dropPos.x - sigW / 2));
            const pdfY = Math.max(0, Math.round(dropPos.y - sigH / 2));

            store.addSignatureToDoc(sigUrl, {
                page: store.state.document.currentPage,
                x: pdfX,
                y: pdfY,
                width: sigW,
                height: sigH
            });

            store.setActiveSignature(sigUrl);
        });

        // Click Stamping
        pdfCanvasContainer.addEventListener("click", (e) => {
            if (!isStampModeActive || !store.state.signature.activeDataUrl) return;
            if (e.target.closest(".signature-overlay")) return;

            const clickPos = screenToDocument(e.clientX, e.clientY);
            const sigW = store.state.placement.width || 150;
            const sigH = store.state.placement.height || 60;
            const pdfX = Math.max(0, Math.round(clickPos.x - sigW / 2));
            const pdfY = Math.max(0, Math.round(clickPos.y - sigH / 2));

            store.addSignatureToDoc(store.state.signature.activeDataUrl, {
                page: store.state.document.currentPage,
                x: pdfX,
                y: pdfY,
                width: sigW,
                height: sigH
            });
        });
    }

    store.subscribe("signature:active", (dataUrl) => {
        if (ghostSigImg) ghostSigImg.src = dataUrl;
        renderSignatureTray();
    });


    // --- Coordinate System Transformations ---
    // Converts a viewport point (a mouse/drop event's clientX/clientY) into PDF-point space on the
    // current page. This must derive its scale from the SAME (post-zoom) rect it reads the offset
    // from: getBoundingClientRect() reflects the stage's current CSS zoom, but getScaleFactor()
    // deliberately does not (see its comment), so mixing the two here used to send drops, clicks
    // and drags to the wrong spot on the page at any zoom level other than 100%.
    function screenToDocument(clientX, clientY) {
        const doc = store.state.document;
        const pageDim = doc.pageDimensions[doc.currentPage - 1] || doc.pageDimensions[0];
        const rect = pdfPageImg.getBoundingClientRect();
        const scale = (pageDim && rect.width) ? rect.width / pageDim.width : getScaleFactor();
        return {
            x: (clientX - rect.left) / scale,
            y: (clientY - rect.top) / scale
        };
    }

    function documentToLocal(docX, docY, center, angleRad) {
        const dx = docX - center.x;
        const dy = docY - center.y;
        const cosA = Math.cos(-angleRad);
        const sinA = Math.sin(-angleRad);
        return {
            x: dx * cosA - dy * sinA,
            y: dx * sinA + dy * cosA
        };
    }

    function localToDocument(localX, localY, center, angleRad) {
        const cosA = Math.cos(angleRad);
        const sinA = Math.sin(angleRad);
        return {
            x: center.x + (localX * cosA - localY * sinA),
            y: center.y + (localX * sinA + localY * cosA)
        };
    }

    function clearStageOverlays() {
        const existingOverlays = pdfCanvasContainer.querySelectorAll(".signature-overlay");
        existingOverlays.forEach(el => el.remove());
    }

    function renderStageSignatures() {
        clearStageOverlays();
        if (store.state.currentMode !== "sign") return;

        const doc = store.state.document;
        const activeSigs = store.state.signature.activeSignaturesOnDoc;
        const scale = getScaleFactor();

        if (sigCountNum) sigCountNum.textContent = activeSigs.length;
        if (multiSigListCard) {
            multiSigListCard.classList.toggle("hidden", activeSigs.length === 0);
        }

        renderPlacedSidebarList(activeSigs);

        activeSigs.forEach((sig) => {
            if (sig.page !== doc.currentPage && signPagesMode.value !== "all") return;

            const overlay = document.createElement("div");
            const isText = sig.type === "text";
            overlay.className = `signature-overlay ${isText ? 'text-overlay' : ''} ${sig.confirmed ? 'confirmed' : ''} ${selectedSigId === sig.id ? 'active-selected' : ''}`;
            overlay.dataset.sigId = sig.id;
            overlay.style.left = `${sig.x * scale}px`;
            overlay.style.top = `${sig.y * scale}px`;
            overlay.style.width = `${sig.width * scale}px`;
            overlay.style.height = `${sig.height * scale}px`;
            overlay.style.transform = `rotate(${sig.rotation || 0}deg)`;
            overlay.style.transformOrigin = "center center";
            overlay.style.opacity = sig.opacity !== undefined ? sig.opacity : 1.0;
            overlay.style.zIndex = sig.zIndex || 1;

            overlay.innerHTML = `
                <div class="rot-live-tooltip hidden">0°</div>
                <div class="overlay-inner">
                    ${isText ? buildTextSvg(sig) : `<img src="${sig.dataUrl}" alt="Signature">`}
                </div>
                <!-- Word-style corner rotation: hovering just outside a corner handle (not on it)
                     swaps to a rotate cursor/icon; the handle itself still scales. No handle is
                     shown until hovered -- see attachOverlayDragAndResize() for the drag logic. -->
                <div class="corner-rot-zone rot-nw" data-handle="rot" title="Drag to rotate (hold Shift to snap)"></div>
                <div class="corner-rot-zone rot-ne" data-handle="rot" title="Drag to rotate (hold Shift to snap)"></div>
                <div class="corner-rot-zone rot-sw" data-handle="rot" title="Drag to rotate (hold Shift to snap)"></div>
                <div class="corner-rot-zone rot-se" data-handle="rot" title="Drag to rotate (hold Shift to snap)"></div>
                <div class="resize-handle handle-nw" data-handle="nw"></div>
                <div class="resize-handle handle-n" data-handle="n"></div>
                <div class="resize-handle handle-ne" data-handle="ne"></div>
                <div class="resize-handle handle-w" data-handle="w"></div>
                <div class="resize-handle handle-e" data-handle="e"></div>
                <div class="resize-handle handle-sw" data-handle="sw"></div>
                <div class="resize-handle handle-s" data-handle="s"></div>
                <div class="resize-handle handle-se" data-handle="se"></div>
            `;

            if (isText) {
                overlay.addEventListener("dblclick", () => focusTextEditor());
            }

            overlay.addEventListener("contextmenu", (e) => {
                e.preventDefault();
                e.stopPropagation();
                selectedSigId = sig.id;
                syncInspectorInputs(sig);
                renderStageSignatures();
                openItemContextMenu(sig.id, e.clientX, e.clientY);
            });

            attachOverlayDragAndResize(overlay, sig);

            pdfCanvasContainer.appendChild(overlay);
        });
    }

    function renderPlacedSidebarList(activeSigs) {
        if (!placedSignaturesContainer) return;
        placedSignaturesContainer.innerHTML = "";

        activeSigs.forEach((sig, index) => {
            const item = document.createElement("div");
            item.className = `sig-item-row ${selectedSigId === sig.id ? 'active' : ''}`;
            item.innerHTML = `
                <div class="sig-item-left">
                    ${sig.type === "text"
                        ? `<div class="sig-item-thumb text-thumb">T</div>`
                        : `<div class="sig-item-thumb"><img src="${sig.dataUrl}" alt="Sig ${index + 1}"></div>`}
                    <span class="sig-item-title">${sig.type === "text" ? escapeHtml(textItemLabel(sig)) : `Sig #${index + 1}`} (Pg ${sig.page})${sig.rotation ? ` · ${sig.rotation}°` : ''}</span>
                </div>
                <div class="sig-item-actions">
                    <button class="overlay-action-btn btn-confirm small" title="Confirm Placement">${sig.confirmed ? '✓' : '✓'}</button>
                    <button class="overlay-action-btn btn-remove small" title="Remove">✕</button>
                </div>
            `;

            item.addEventListener("click", () => {
                selectedSigId = sig.id;
                syncInspectorInputs(sig);
                renderStageSignatures();
            });

            item.querySelector(".btn-confirm").addEventListener("click", (e) => {
                e.stopPropagation();
                store.confirmSignatureOnDoc(sig.id);
            });

            item.querySelector(".btn-remove").addEventListener("click", (e) => {
                e.stopPropagation();
                store.removeSignatureFromDoc(sig.id);
            });

            placedSignaturesContainer.appendChild(item);
        });
    }

    // --- Right-Click Item Menu & Keyboard Actions for Placed Items ---
    const isMac = /Mac|iPhone|iPad/.test(navigator.platform);
    const modKey = isMac ? "⌘" : "Ctrl+";
    let itemContextMenu = null;

    function rotateItem90(id) {
        const sig = store.state.signature.activeSignaturesOnDoc.find(s => s.id === id);
        if (!sig) return;
        let nextRot = ((sig.rotation || 0) + 90) % 360;
        if (nextRot > 180) nextRot -= 360;
        store.updateSignatureOnDoc(id, { rotation: nextRot }, true);
        syncInspectorInputs(sig);
    }

    function deleteItem(id) {
        if (selectedSigId === id) selectedSigId = null;
        store.removeSignatureFromDoc(id);
    }

    function duplicateItem(id) {
        const copy = store.duplicateSignatureOnDoc(id);
        if (copy) {
            selectedSigId = copy.id;
            syncInspectorInputs(copy);
            renderStageSignatures();
        }
    }

    function closeItemContextMenu() {
        if (itemContextMenu) {
            itemContextMenu.remove();
            itemContextMenu = null;
        }
    }

    function openItemContextMenu(id, clientX, clientY) {
        closeItemContextMenu();
        const actions = [
            { label: "Duplicate", shortcut: `${modKey}D`, run: () => duplicateItem(id) },
            { label: "Rotate 90°", shortcut: "", run: () => rotateItem90(id) },
            { divider: true },
            { label: "Bring to Front", shortcut: `${modKey}]`, run: () => store.reorderSignatureOnDoc(id, "front") },
            { label: "Send to Back", shortcut: `${modKey}[`, run: () => store.reorderSignatureOnDoc(id, "back") },
            { divider: true },
            { label: "Delete", shortcut: isMac ? "⌫" : "Del", danger: true, run: () => deleteItem(id) }
        ];

        const menu = document.createElement("div");
        menu.className = "item-context-menu";
        menu.setAttribute("role", "menu");
        actions.forEach(a => {
            if (a.divider) {
                menu.insertAdjacentHTML("beforeend", `<div class="ctx-divider"></div>`);
                return;
            }
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = `ctx-item ${a.danger ? "danger" : ""}`;
            btn.setAttribute("role", "menuitem");
            btn.innerHTML = `<span>${a.label}</span><span class="ctx-shortcut">${a.shortcut}</span>`;
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                closeItemContextMenu();
                a.run();
            });
            menu.appendChild(btn);
        });
        // Keep clicks inside the menu from reaching the stage (pan/deselect) handlers.
        menu.addEventListener("mousedown", (e) => e.stopPropagation());
        menu.addEventListener("contextmenu", (e) => e.preventDefault());

        document.body.appendChild(menu);
        // Keep the menu fully on screen.
        const { width, height } = menu.getBoundingClientRect();
        const left = Math.min(clientX, window.innerWidth - width - 8);
        const top = Math.min(clientY, window.innerHeight - height - 8);
        menu.style.left = `${Math.max(8, left)}px`;
        menu.style.top = `${Math.max(8, top)}px`;
        itemContextMenu = menu;
    }

    window.addEventListener("mousedown", (e) => {
        if (itemContextMenu && !itemContextMenu.contains(e.target)) closeItemContextMenu();
    });
    window.addEventListener("blur", closeItemContextMenu);
    window.addEventListener("resize", closeItemContextMenu);

    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && itemContextMenu) {
            closeItemContextMenu();
            return;
        }
        const el = document.activeElement;
        if (el && (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable)) return;
        if (!selectedSigId || store.state.currentMode !== "sign") return;
        if (!store.state.signature.activeSignaturesOnDoc.some(s => s.id === selectedSigId)) return;

        const mod = e.metaKey || e.ctrlKey;
        if (e.key === "Delete" || e.key === "Backspace") {
            e.preventDefault();
            closeItemContextMenu();
            deleteItem(selectedSigId);
        } else if (mod && e.key.toLowerCase() === "d") {
            e.preventDefault();
            duplicateItem(selectedSigId);
        } else if (mod && e.key === "]") {
            e.preventDefault();
            store.reorderSignatureOnDoc(selectedSigId, "front");
        } else if (mod && e.key === "[") {
            e.preventDefault();
            store.reorderSignatureOnDoc(selectedSigId, "back");
        }
    });

    store.subscribe("signatures:doc_updated", () => {
        renderStageSignatures();
        syncTextEditor();
        updateSaveBtn();
    });

    // Attach Microsoft Word-Style Drag, Resize & Rotate to an Overlay Box
    function attachOverlayDragAndResize(overlay, sig) {
        let isDragging = false;
        let isResizing = false;
        let isRotating = false;
        let resizeHandle = null;

        let initX = 0, initY = 0, initW = 0, initH = 0;
        let initRot = 0, startAngle = 0;
        let initFontSize = 0;
        let initCenter = { x: 0, y: 0 };
        let centerScreen = { x: 0, y: 0 };
        let startPointerDoc = { x: 0, y: 0 };

        const liveTooltip = overlay.querySelector(".rot-live-tooltip");

        overlay.addEventListener("mousedown", (e) => {
            selectedSigId = sig.id;
            syncInspectorInputs(sig);

            // Only a primary-button press moves/resizes/rotates; right-click opens the item menu
            // and middle-click falls through to the stage's pan handler.
            if (e.button !== 0) return;

            startPointerDoc = screenToDocument(e.clientX, e.clientY);

            initX = sig.x;
            initY = sig.y;
            initW = sig.width;
            initH = sig.height;
            initRot = sig.rotation || 0;
            initFontSize = sig.fontSize || 0;
            initCenter = { x: initX + initW / 2, y: initY + initH / 2 };

            if (e.target.closest(".corner-rot-zone") || e.target.dataset.handle === "rot") {
                isRotating = true;
                const rect = overlay.getBoundingClientRect();
                centerScreen = {
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2
                };
                startAngle = Math.atan2(e.clientY - centerScreen.y, e.clientX - centerScreen.x) * (180 / Math.PI);
                if (liveTooltip) {
                    liveTooltip.textContent = `${initRot}°`;
                    liveTooltip.classList.remove("hidden");
                }
                e.preventDefault();
                e.stopPropagation();
                return;
            } else if (e.target.classList.contains("resize-handle")) {
                isResizing = true;
                resizeHandle = e.target.dataset.handle;
            } else {
                isDragging = true;
            }

            e.preventDefault();
        });

        const onMouseMove = (e) => {
            if (!isDragging && !isResizing && !isRotating) return;
            const scale = getScaleFactor();
            const currPointerDoc = screenToDocument(e.clientX, e.clientY);

            if (isRotating) {
                const currentAngle = Math.atan2(e.clientY - centerScreen.y, e.clientX - centerScreen.x) * (180 / Math.PI);
                const delta = currentAngle - startAngle;
                let deg = initRot + delta;

                if (e.shiftKey) {
                    deg = Math.round(deg / 15) * 15;
                } else {
                    deg = Math.round(deg);
                }

                deg = ((deg % 360) + 360) % 360;
                if (deg > 180) deg -= 360;

                sig.rotation = deg;
                overlay.style.transform = `rotate(${deg}deg)`;
                syncRotationInputs(deg);
                if (liveTooltip) {
                    liveTooltip.textContent = `${deg}°`;
                    liveTooltip.classList.remove("hidden");
                }
            } else if (isDragging) {
                const deltaX = currPointerDoc.x - startPointerDoc.x;
                const deltaY = currPointerDoc.y - startPointerDoc.y;
                let newX = Math.round(Math.max(0, initX + deltaX));
                let newY = Math.round(Math.max(0, initY + deltaY));

                overlay.style.left = `${newX * scale}px`;
                overlay.style.top = `${newY * scale}px`;

                sig.x = newX;
                sig.y = newY;
                if (sigXInput) sigXInput.value = newX;
                if (sigYInput) sigYInput.value = newY;
            } else if (isResizing) {
                const rotRad = (initRot * Math.PI) / 180;
                const localPointer = documentToLocal(currPointerDoc.x, currPointerDoc.y, initCenter, rotRad);
                const ratio = sig.aspectRatio || ((initW > 0 && initH > 0) ? (initW / initH) : 2.5);
                // Small text boxes are legitimately narrower than a signature would ever be
                const minW = sig.type === "text" ? 6 : 20;
                const minH = sig.type === "text" ? 4 : 10;

                const L = -initW / 2;
                const R = initW / 2;
                const T = -initH / 2;
                const B = initH / 2;

                let newL = L, newR = R, newT = T, newB = B;

                if (resizeHandle === "se") {
                    newR = localPointer.x;
                    newB = localPointer.y;
                    let newW = Math.max(minW, newR - L);
                    let newH = Math.max(minH, Math.round(newW / ratio));
                    newR = L + newW;
                    newB = T + newH;
                } else if (resizeHandle === "nw") {
                    newL = localPointer.x;
                    newT = localPointer.y;
                    let newW = Math.max(minW, R - newL);
                    let newH = Math.max(minH, Math.round(newW / ratio));
                    newL = R - newW;
                    newT = B - newH;
                } else if (resizeHandle === "ne") {
                    newR = localPointer.x;
                    newT = localPointer.y;
                    let newW = Math.max(minW, newR - L);
                    let newH = Math.max(minH, Math.round(newW / ratio));
                    newR = L + newW;
                    newT = B - newH;
                } else if (resizeHandle === "sw") {
                    newL = localPointer.x;
                    newB = localPointer.y;
                    let newW = Math.max(minW, R - newL);
                    let newH = Math.max(minH, Math.round(newW / ratio));
                    newL = R - newW;
                    newT = B - newH;
                } else if (resizeHandle === "n") {
                    newT = Math.min(B - 10, localPointer.y);
                } else if (resizeHandle === "s") {
                    newB = Math.max(T + 10, localPointer.y);
                } else if (resizeHandle === "w") {
                    newL = Math.min(R - 20, localPointer.x);
                } else if (resizeHandle === "e") {
                    newR = Math.max(L + 20, localPointer.x);
                }

                const finalW = Math.round(newR - newL);
                const finalH = Math.round(newB - newT);
                const localCenterNew = { x: (newL + newR) / 2, y: (newT + newB) / 2 };

                const docCenterNew = localToDocument(localCenterNew.x, localCenterNew.y, initCenter, rotRad);
                const finalX = Math.round(docCenterNew.x - finalW / 2);
                const finalY = Math.round(docCenterNew.y - finalH / 2);

                overlay.style.left = `${finalX * scale}px`;
                overlay.style.top = `${finalY * scale}px`;
                overlay.style.width = `${finalW * scale}px`;
                overlay.style.height = `${finalH * scale}px`;

                sig.x = finalX;
                sig.y = finalY;
                sig.width = finalW;
                sig.height = finalH;

                if (sig.type === "text" && initW > 0) {
                    // The SVG scales with the box for a live preview; the font size is committed on mouseup
                    sig.fontSize = initFontSize * finalW / initW;
                }

                if (sigXInput) sigXInput.value = finalX;
                if (sigYInput) sigYInput.value = finalY;
                if (sigWInput) sigWInput.value = finalW;
                if (sigHInput) sigHInput.value = finalH;
            }
        };

        const onMouseUp = () => {
            if (isRotating || isDragging || isResizing) {
                if (sig.type === "text" && isResizing) {
                    // Snap to a clean font size and re-fit the box to the text
                    const fontSize = normalizeFontSize(sig.fontSize);
                    store.updateSignatureOnDoc(sig.id, {
                        x: sig.x,
                        y: sig.y,
                        rotation: sig.rotation || 0,
                        fontSize,
                        ...measureTextBox({ ...sig, fontSize })
                    }, true);
                } else {
                    store.updateSignatureOnDoc(sig.id, {
                        x: sig.x,
                        y: sig.y,
                        width: sig.width,
                        height: sig.height,
                        rotation: sig.rotation || 0
                    }, true);
                }
                if (liveTooltip) liveTooltip.classList.add("hidden");
            }
            isDragging = false;
            isResizing = false;
            isRotating = false;
            resizeHandle = null;
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
        };

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
    }

    // --- Inspector Inputs & Handlers ---
    const sigOpacitySlider = document.getElementById("sigOpacitySlider");
    const sigOpacityValue = document.getElementById("sigOpacityValue");
    const sigZUpBtn = document.getElementById("sigZUpBtn");
    const sigZDownBtn = document.getElementById("sigZDownBtn");

    function syncInspectorInputs(sig) {
        if (!sig) return;
        if (sigXInput) sigXInput.value = Math.round(sig.x);
        if (sigYInput) sigYInput.value = Math.round(sig.y);
        if (sigWInput) sigWInput.value = Math.round(sig.width);
        if (sigHInput) sigHInput.value = Math.round(sig.height);
        syncRotationInputs(sig.rotation || 0);
        if (sigOpacitySlider) sigOpacitySlider.value = Math.round((sig.opacity !== undefined ? sig.opacity : 1.0) * 100);
        if (sigOpacityValue) sigOpacityValue.textContent = `${Math.round((sig.opacity !== undefined ? sig.opacity : 1.0) * 100)}%`;
        syncTextEditor();
    }

    function syncRotationInputs(deg) {
        deg = Math.round(deg || 0);
        if (sigRotSlider) sigRotSlider.value = deg;
        if (sigRotValue) sigRotValue.textContent = `${deg}°`;
    }

    if (sigRotSlider) {
        sigRotSlider.addEventListener("input", () => {
            const val = parseInt(sigRotSlider.value) || 0;
            if (sigRotValue) sigRotValue.textContent = `${val}°`;
            if (selectedSigId) {
                store.updateSignatureOnDoc(selectedSigId, { rotation: val });
                const ov = pdfCanvasContainer.querySelector(`.signature-overlay[data-sig-id="${selectedSigId}"]`);
                if (ov) ov.style.transform = `rotate(${val}deg)`;
            }
        });
    }

    if (sigRotResetBtn) {
        sigRotResetBtn.addEventListener("click", () => {
            if (selectedSigId) {
                store.updateSignatureOnDoc(selectedSigId, { rotation: 0 }, true);
                syncRotationInputs(0);
                const ov = pdfCanvasContainer.querySelector(`.signature-overlay[data-sig-id="${selectedSigId}"]`);
                if (ov) ov.style.transform = "rotate(0deg)";
            }
        });
    }

    if (sigRot90Btn) {
        sigRot90Btn.addEventListener("click", () => {
            if (selectedSigId) {
                const sig = store.state.signature.activeSignaturesOnDoc.find(s => s.id === selectedSigId);
                let nextRot = ((sig && sig.rotation ? sig.rotation : 0) + 90) % 360;
                if (nextRot > 180) nextRot -= 360;
                store.updateSignatureOnDoc(selectedSigId, { rotation: nextRot }, true);
                syncRotationInputs(nextRot);
                const ov = pdfCanvasContainer.querySelector(`.signature-overlay[data-sig-id="${selectedSigId}"]`);
                if (ov) ov.style.transform = `rotate(${nextRot}deg)`;
            }
        });
    }

    if (sigOpacitySlider) {
        sigOpacitySlider.addEventListener("input", () => {
            const opacityVal = (parseInt(sigOpacitySlider.value) || 100) / 100;
            if (sigOpacityValue) sigOpacityValue.textContent = `${Math.round(opacityVal * 100)}%`;
            if (selectedSigId) {
                store.updateSignatureOnDoc(selectedSigId, { opacity: opacityVal });
                const ov = pdfCanvasContainer.querySelector(`.signature-overlay[data-sig-id="${selectedSigId}"]`);
                if (ov) ov.style.opacity = opacityVal;
            }
        });
    }

    if (sigZUpBtn) {
        sigZUpBtn.addEventListener("click", () => {
            if (selectedSigId) {
                const sig = store.state.signature.activeSignaturesOnDoc.find(s => s.id === selectedSigId);
                if (sig) {
                    store.updateSignatureOnDoc(selectedSigId, { zIndex: (sig.zIndex || 1) + 1 }, true);
                }
            }
        });
    }

    if (sigZDownBtn) {
        sigZDownBtn.addEventListener("click", () => {
            if (selectedSigId) {
                const sig = store.state.signature.activeSignaturesOnDoc.find(s => s.id === selectedSigId);
                if (sig) {
                    store.updateSignatureOnDoc(selectedSigId, { zIndex: Math.max(1, (sig.zIndex || 1) - 1) }, true);
                }
            }
        });
    }

    sigWInput.addEventListener("change", () => {
        if (selectedSigId) {
            const sig = store.state.signature.activeSignaturesOnDoc.find(s => s.id === selectedSigId);
            if (sig && sig.type === "text") {
                scaleTextItem(sig, (parseFloat(sigWInput.value) || sig.width) / sig.width);
                return;
            }
            const ratio = (sig && sig.aspectRatio) || (sig && sig.width && sig.height ? sig.width / sig.height : 2.5);
            const newW = Math.max(20, parseFloat(sigWInput.value) || 150);
            const newH = Math.max(10, Math.round(newW / ratio));
            sigHInput.value = newH;
            store.updateSignatureOnDoc(selectedSigId, {
                width: newW,
                height: newH
            }, true);
        }
    });

    sigHInput.addEventListener("change", () => {
        if (selectedSigId) {
            const sig = store.state.signature.activeSignaturesOnDoc.find(s => s.id === selectedSigId);
            if (sig && sig.type === "text") {
                scaleTextItem(sig, (parseFloat(sigHInput.value) || sig.height) / sig.height);
                return;
            }
            const ratio = (sig && sig.aspectRatio) || (sig && sig.width && sig.height ? sig.width / sig.height : 2.5);
            const newH = Math.max(10, parseFloat(sigHInput.value) || 60);
            const newW = Math.max(20, Math.round(newH * ratio));
            sigWInput.value = newW;
            store.updateSignatureOnDoc(selectedSigId, {
                width: newW,
                height: newH
            }, true);
        }
    });

    sigXInput.addEventListener("change", () => {
        if (selectedSigId) {
            store.updateSignatureOnDoc(selectedSigId, {
                x: parseFloat(sigXInput.value) || 50
            }, true);
        }
    });

    sigYInput.addEventListener("change", () => {
        if (selectedSigId) {
            store.updateSignatureOnDoc(selectedSigId, {
                y: parseFloat(sigYInput.value) || 50
            }, true);
        }
    });

    undoBtn.addEventListener("click", () => store.undoPlacement());
    redoBtn.addEventListener("click", () => store.redoPlacement());

    // The buttons start disabled in the HTML and nothing was ever re-enabling them, so Undo/Redo
    // were unreachable from the UI even though the underlying history stack worked correctly.
    store.subscribe("placement:updated", ({ canUndo, canRedo }) => {
        undoBtn.disabled = !canUndo;
        redoBtn.disabled = !canRedo;
    });

    // Keyboard shortcuts to match what the buttons' titles already advertise (⌘Z / ⌘⇧Z on Mac,
    // Ctrl+Z / Ctrl+Shift+Z elsewhere), which previously didn't exist.
    window.addEventListener("keydown", (e) => {
        if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "z") return;
        if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
        e.preventDefault();
        if (e.shiftKey) {
            if (!redoBtn.disabled) store.redoPlacement();
        } else if (!undoBtn.disabled) {
            store.undoPlacement();
        }
    });

    // Steppers
    stepperMinusBtn.addEventListener("click", () => {
        const val = parseInt(dupCountInput.value) || 2;
        if (val > 1) dupCountInput.value = val - 1;
    });
    stepperPlusBtn.addEventListener("click", () => {
        const val = parseInt(dupCountInput.value) || 1;
        dupCountInput.value = val + 1;
    });

    signPagesMode.addEventListener("change", () => {
        if (signPagesMode.value === "custom") {
            customPageRangeGroup.classList.remove("hidden");
        } else {
            customPageRangeGroup.classList.add("hidden");
        }
        renderStageSignatures();
    });

    // --- Signature Studio Modal ---
    if (openSigStudioBtn) {
        openSigStudioBtn.addEventListener("click", () => {
            if (sigStudioModal) sigStudioModal.classList.remove("hidden");
            initCanvas();
        });
    }

    if (closeSigStudioBtn) closeSigStudioBtn.addEventListener("click", () => sigStudioModal && sigStudioModal.classList.add("hidden"));
    if (cancelSigModalBtn) cancelSigModalBtn.addEventListener("click", () => sigStudioModal && sigStudioModal.classList.add("hidden"));


    modalTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            modalTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            tabDraw.classList.add("hidden");
            tabUpload.classList.add("hidden");
            tabLibrary.classList.add("hidden");

            if (tab.dataset.tab === "draw") {
                tabDraw.classList.remove("hidden");
            } else if (tab.dataset.tab === "upload") {
                tabUpload.classList.remove("hidden");
            } else if (tab.dataset.tab === "library") {
                tabLibrary.classList.remove("hidden");
                renderSavedLibrary(store.state.signature.savedSignatures);
            }
        });
    });

    const addSelectedLibSigsBtn = document.getElementById("addSelectedLibSigsBtn");
    const addAndKeepSigBtn = document.getElementById("addAndKeepSigBtn");
    let selectedLibSigIds = new Set();

    function renderSavedLibrary(savedList) {
        if (!sigLibraryGrid) return;
        selectedLibSigIds.clear();
        updateAddSelectedLibBtn();

        if (!savedList || savedList.length === 0) {
            sigLibraryGrid.innerHTML = `<p class="empty-library-text">No saved signatures yet. Draw or upload a signature to save it to your library!</p>`;
            return;
        }

        sigLibraryGrid.innerHTML = "";
        savedList.forEach(item => {
            const card = document.createElement("div");
            card.className = "sig-library-card";
            card.dataset.id = item.id;
            card.innerHTML = `
                <input type="checkbox" class="sig-card-checkbox">
                <div class="sig-lib-img">
                    <img src="${item.dataUrl}" alt="${item.title}">
                </div>
                <div class="sig-lib-info">
                    <span class="sig-lib-title">${item.title}</span>
                    <span class="sig-lib-date">${new Date(item.createdAt).toLocaleDateString()}</span>
                </div>
            `;

            const checkbox = card.querySelector(".sig-card-checkbox");

            card.addEventListener("click", (e) => {
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                }
                if (checkbox.checked) {
                    selectedLibSigIds.add(item.id);
                    card.classList.add("selected-card");
                } else {
                    selectedLibSigIds.delete(item.id);
                    card.classList.remove("selected-card");
                }
                updateAddSelectedLibBtn();
            });

            sigLibraryGrid.appendChild(card);
        });
    }

    function updateAddSelectedLibBtn() {
        if (!addSelectedLibSigsBtn) return;
        const count = selectedLibSigIds.size;
        addSelectedLibSigsBtn.textContent = `Add Selected Signatures (${count})`;
        addSelectedLibSigsBtn.disabled = count === 0;
    }

    if (addSelectedLibSigsBtn) {
        addSelectedLibSigsBtn.addEventListener("click", () => {
            const savedList = store.state.signature.savedSignatures;
            selectedLibSigIds.forEach(id => {
                const item = savedList.find(s => s.id === id);
                if (item) {
                    store.addSignatureToDoc(item.dataUrl);
                }
            });
            sigStudioModal.classList.add("hidden");
        });
    }

    function trimCanvas(canvas) {
        if (!canvas) return null;
        const ctx = canvas.getContext("2d");
        const w = canvas.width;
        const h = canvas.height;
        const imgData = ctx.getImageData(0, 0, w, h);
        const data = imgData.data;

        let minX = w, minY = h, maxX = -1, maxY = -1;
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const alpha = data[(y * w + x) * 4 + 3];
                if (alpha > 10) {
                    if (x < minX) minX = x;
                    if (x > maxX) maxX = x;
                    if (y < minY) minY = y;
                    if (y > maxY) maxY = y;
                }
            }
        }

        if (maxX === -1) return null;

        const pad = 8;
        minX = Math.max(0, minX - pad);
        minY = Math.max(0, minY - pad);
        maxX = Math.min(w, maxX + pad);
        maxY = Math.min(h, maxY + pad);

        const cropW = maxX - minX;
        const cropH = maxY - minY;

        const trimmedCanvas = document.createElement("canvas");
        trimmedCanvas.width = cropW;
        trimmedCanvas.height = cropH;
        const trimmedCtx = trimmedCanvas.getContext("2d");
        trimmedCtx.drawImage(canvas, minX, minY, cropW, cropH, 0, 0, cropW, cropH);

        return trimmedCanvas.toDataURL("image/png");
    }

    function trimImagePadding(img) {
        try {
            if (!img || !img.naturalWidth || !img.naturalHeight) return img ? img.src : null;
            const tempCanvas = document.createElement("canvas");
            tempCanvas.width = img.naturalWidth;
            tempCanvas.height = img.naturalHeight;
            const ctx = tempCanvas.getContext("2d");
            ctx.drawImage(img, 0, 0);
            const trimmed = trimCanvas(tempCanvas);
            return trimmed || img.src;
        } catch (e) {
            return img.src;
        }
    }

    function initCanvas() {
        if (!canvasCtx) return;

        // The canvas element is sized in CSS (width: 100%, height: 220px), but its backing pixel
        // buffer defaults to the fixed 560x220 from its HTML attributes. On a HiDPI/Retina screen,
        // or whenever the modal renders wider than 560px, that buffer gets upscaled to fill the
        // element and the drawn signature comes out soft/pixelated. Resizing the buffer to match
        // the actual on-screen size * devicePixelRatio fixes that at the source, so what's captured
        // (and later embedded in the PDF) is as sharp as the screen it was drawn on.
        // Resizing the buffer clears it, so only do it when the size actually changed.
        const dpr = window.devicePixelRatio || 1;
        const rect = sigCanvas.getBoundingClientRect();
        const targetW = Math.max(1, Math.round((rect.width || sigCanvas.clientWidth || 560) * dpr));
        const targetH = Math.max(1, Math.round((rect.height || 220) * dpr));
        if (sigCanvas.width !== targetW || sigCanvas.height !== targetH) {
            sigCanvas.width = targetW;
            sigCanvas.height = targetH;
        }
        canvasScale = sigCanvas.width / (rect.width || sigCanvas.clientWidth || 560);

        canvasCtx.lineCap = "round";
        canvasCtx.lineJoin = "round";
        canvasCtx.strokeStyle = activeColor;
        canvasCtx.lineWidth = strokeWidth * canvasScale;
    }

    if (sigCanvas) {
        const getCanvasPos = (e) => {
            const rect = sigCanvas.getBoundingClientRect();
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;
            return {
                x: (clientX - rect.left) * (sigCanvas.width / rect.width),
                y: (clientY - rect.top) * (sigCanvas.height / rect.height)
            };
        };

        const startDraw = (e) => {
            isDrawing = true;
            const pos = getCanvasPos(e);
            canvasCtx.beginPath();
            canvasCtx.moveTo(pos.x, pos.y);
            e.preventDefault();
        };

        const drawMove = (e) => {
            if (!isDrawing) return;
            const pos = getCanvasPos(e);
            canvasCtx.lineTo(pos.x, pos.y);
            canvasCtx.stroke();
            e.preventDefault();
        };

        const stopDraw = () => { isDrawing = false; };

        sigCanvas.addEventListener("mousedown", startDraw);
        sigCanvas.addEventListener("mousemove", drawMove);
        window.addEventListener("mouseup", stopDraw);

        sigCanvas.addEventListener("touchstart", startDraw);
        sigCanvas.addEventListener("touchmove", drawMove);
        window.addEventListener("touchend", stopDraw);
    }

    clearCanvasBtn.addEventListener("click", () => {
        if (canvasCtx) canvasCtx.clearRect(0, 0, sigCanvas.width, sigCanvas.height);
    });

    colorBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            colorBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activeColor = btn.dataset.color;
            if (canvasCtx) canvasCtx.strokeStyle = activeColor;
        });
    });

    strokeWidthInput.addEventListener("input", () => {
        strokeWidth = parseInt(strokeWidthInput.value);
        if (canvasCtx) canvasCtx.lineWidth = strokeWidth * canvasScale;
    });

    sigUploadDropzone.addEventListener("click", () => sigImageFileInput.click());
    sigImageFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            const reader = new FileReader();
            reader.onload = (evt) => {
                const img = new Image();
                img.onload = () => {
                    const trimmedDataUrl = trimImagePadding(img);
                    uploadedSigImg.src = trimmedDataUrl;
                    uploadedSigPreview.classList.remove("hidden");
                    store.setActiveSignature(trimmedDataUrl);
                };
                img.src = evt.target.result;
            };
            reader.readAsDataURL(e.target.files[0]);
        }
    });

    if (addAndKeepSigBtn) {
        addAndKeepSigBtn.addEventListener("click", async () => {
            const activeTab = document.querySelector(".modal-tab.active").dataset.tab;
            let sigData = store.state.signature.activeDataUrl;

            if (activeTab === "draw" && canvasCtx) {
                // trimCanvas() returns null for a blank canvas -- don't fall back to capturing the
                // whole (blank) canvas anyway, or "draw nothing, click this" saves an invisible
                // signature to the library.
                sigData = trimCanvas(sigCanvas);
                if (!sigData) {
                    alert("Please draw a signature first.");
                    return;
                }
                await store.saveSignatureToLibrary(sigData, "Handwritten Signature");
                canvasCtx.clearRect(0, 0, sigCanvas.width, sigCanvas.height);
            } else if (activeTab === "upload" && sigData) {
                await store.saveSignatureToLibrary(sigData, "Uploaded Signature");
            } else if (activeTab === "library" && selectedLibSigIds.size > 0) {
                const savedList = store.state.signature.savedSignatures;
                selectedLibSigIds.forEach(id => {
                    const item = savedList.find(s => s.id === id);
                    if (item) store.addSignatureToDoc(item.dataUrl);
                });
            }
            // Draw/upload tabs only save to the library here — "Add & Draw Another" means stay open
            // and build up the library, not also drop an unrequested copy onto the document at a
            // default corner. Placing onto the page is what "Use This Signature" and the library
            // tray/tab's own placement actions are for.
        });
    }

    saveSigModalBtn.addEventListener("click", async () => {
        const activeTab = document.querySelector(".modal-tab.active").dataset.tab;
        let sigData = store.state.signature.activeDataUrl;

        if (activeTab === "draw" && canvasCtx) {
            // trimCanvas() returns null for a blank canvas -- don't fall back to capturing the
            // whole (blank) canvas anyway, or "click Use This Signature" with nothing drawn places
            // an invisible signature on the document.
            sigData = trimCanvas(sigCanvas);
            if (!sigData) {
                alert("Please draw a signature first.");
                return;
            }
            await store.saveSignatureToLibrary(sigData, "Handwritten Signature");
        } else if (activeTab === "upload" && sigData) {
            await store.saveSignatureToLibrary(sigData, "Uploaded Signature");
        } else if (activeTab === "library" && selectedLibSigIds.size > 0) {
            const savedList = store.state.signature.savedSignatures;
            selectedLibSigIds.forEach(id => {
                const item = savedList.find(s => s.id === id);
                if (item) store.addSignatureToDoc(item.dataUrl);
            });
            sigStudioModal.classList.add("hidden");
            return;
        } else if (activeTab === "upload" && !sigData) {
            alert("Please upload a signature image first.");
            return;
        } else if (activeTab === "library") {
            alert("Please select at least one saved signature first.");
            return;
        }

        if (sigData) {
            store.addSignatureToDoc(sigData);
        }

        sigStudioModal.classList.add("hidden");
    });


    // --- Overlay payload (signature images + text boxes) sent to /api/sign and /api/preview-pdf ---
    function buildOverlaysPayload(items) {
        const pagesModeVal = signPagesMode ? signPagesMode.value : "current";
        const pageSpecVal = (signPageSpecInput && signPageSpecInput.value) ? signPageSpecInput.value : "";
        const num = (v, fallback) => (v !== undefined && v !== null && Number.isFinite(Number(v))) ? Number(v) : fallback;

        return items.map(s => {
            const common = {
                pages_spec: pagesModeVal === "current" ? ((s.page != null) ? s.page.toString() : "1") : (pagesModeVal === "custom" ? pageSpecVal : ""),
                x: num(s.x, 50),
                y: num(s.y, 50),
                width: num(s.width, 150),
                height: num(s.height, 60),
                rotation: num(s.rotation, 0),
                scale_x: num(s.scaleX, 1.0),
                scale_y: num(s.scaleY, 1.0),
                opacity: num(s.opacity, 1.0),
                z_index: num(s.zIndex, 1) || 1,
                locked: !!s.locked,
                y_from_top: true
            };
            if (s.type === "text") {
                return {
                    ...common,
                    type: "text",
                    text: s.text || "",
                    font_family: s.fontFamily || "helvetica",
                    font_size: num(s.fontSize, 16),
                    bold: !!s.bold,
                    italic: !!s.italic,
                    color: s.color || "#000000"
                };
            }
            return { ...common, signature_img: s.dataUrl || "" };
        });
    }

    // --- Text Boxes ---
    // Text is laid out on a fixed grid so the stage matches the exported PDF exactly:
    // each line is TEXT_LINE_HEIGHT * fontSize tall and the first baseline sits
    // TEXT_BASELINE * fontSize below the box top. Keep in sync with core.py.
    const TEXT_LINE_HEIGHT = 1.2;
    const TEXT_BASELINE = 0.9;
    const TEXT_MIN_FONT_SIZE = 4;
    const TEXT_MAX_FONT_SIZE = 400;
    const TEXT_FONT_STACKS = {
        helvetica: "Helvetica, Arial, sans-serif",
        times: "'Times New Roman', Times, serif",
        courier: "'Courier New', Courier, monospace",
        montserrat: "'Montserrat Text', sans-serif"
    };
    // Characters the PDF standard fonts can draw (Windows-1252)
    const CP1252_EXTRAS = "€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ";

    const addTextBtn = document.getElementById("addTextBtn");
    const textEditor = document.getElementById("textEditor");
    const textEditorHint = document.getElementById("textEditorHint");
    const textContentInput = document.getElementById("textContentInput");
    const textCharWarning = document.getElementById("textCharWarning");
    const textFontSelect = document.getElementById("textFontSelect");
    const textSizeInput = document.getElementById("textSizeInput");
    const textBoldBtn = document.getElementById("textBoldBtn");
    const textItalicBtn = document.getElementById("textItalicBtn");
    const textColorInput = document.getElementById("textColorInput");
    const textColorBtns = document.querySelectorAll(".text-color-btn");

    const measureCtx = document.createElement("canvas").getContext("2d");
    // The PDF places glyphs by plain advance widths (no kerning pairs, no ligatures), so the stage
    // must too, or Montserrat text would come out ~1% wider in the export than it looks here.
    measureCtx.fontKerning = "none";
    // Style used for the next box added, so a run of labels can share a look
    let lastTextStyle = { fontFamily: "helvetica", fontSize: 16, bold: false, italic: false, color: "#000000" };

    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }

    function textItemLabel(sig) {
        const flat = (sig.text || "").replace(/\s+/g, " ").trim();
        if (!flat) return "Text (empty)";
        return `Text "${flat.length > 14 ? flat.slice(0, 14) + "…" : flat}"`;
    }

    function normalizeFontSize(size) {
        const rounded = Math.round((Number(size) || 16) * 2) / 2;
        return Math.max(TEXT_MIN_FONT_SIZE, Math.min(TEXT_MAX_FONT_SIZE, rounded));
    }

    // Would this text lose characters ("?") when drawn in the given font? Mirrors core.py.
    function hasUnsupportedChars(text, fontFamily) {
        const ranges = fontFamily === "montserrat" ? (window.MONTSERRAT_COVERAGE || []) : null;
        for (const ch of text) {
            const c = ch.codePointAt(0);
            if (c === 10 || c === 13) continue;
            const ok = ranges
                ? ranges.some(([lo, hi]) => c >= lo && c <= hi)
                : ((c >= 0x20 && c <= 0x7e) || (c >= 0xa0 && c <= 0xff) || CP1252_EXTRAS.includes(ch));
            if (!ok) return true;
        }
        return false;
    }

    // Size of the box that hugs the text (in PDF points)
    function measureTextBox(t) {
        const fontSize = t.fontSize || 16;
        measureCtx.font = `${t.italic ? "italic " : ""}${t.bold ? "bold " : ""}${fontSize}px ${TEXT_FONT_STACKS[t.fontFamily] || TEXT_FONT_STACKS.helvetica}`;
        const lines = String(t.text || "").split("\n");
        const widest = Math.max(...lines.map(line => measureCtx.measureText(line).width));
        const width = Math.max(fontSize * 0.6, Math.round(widest * 100) / 100);
        const height = Math.round(lines.length * TEXT_LINE_HEIGHT * fontSize * 100) / 100;
        return { width, height, aspectRatio: width / height };
    }

    // The SVG viewBox is the box in PDF points, so the stage draws exactly what the PDF will contain
    function buildTextSvg(sig) {
        const fontSize = sig.fontSize || 16;
        const lines = String(sig.text || "").split("\n");
        const rows = lines.map((line, i) =>
            `<text x="0" y="${(TEXT_BASELINE + i * TEXT_LINE_HEIGHT) * fontSize}" xml:space="preserve" style="white-space:pre">${escapeHtml(line)}</text>`
        ).join("");
        return `<svg class="text-overlay-svg" viewBox="0 0 ${sig.width} ${sig.height}" preserveAspectRatio="none"
                    font-family="${TEXT_FONT_STACKS[sig.fontFamily] || TEXT_FONT_STACKS.helvetica}"
                    font-size="${fontSize}" font-weight="${sig.bold ? "bold" : "normal"}"
                    font-style="${sig.italic ? "italic" : "normal"}" fill="${escapeHtml(sig.color || "#000000")}"
                    style="font-kerning:none;font-variant-ligatures:none;font-feature-settings:'kern' 0,'liga' 0,'clig' 0">${rows}</svg>`;
    }

    function getSelectedTextItem() {
        const sig = store.state.signature.activeSignaturesOnDoc.find(s => s.id === selectedSigId);
        return sig && sig.type === "text" ? sig : null;
    }

    // Applies a text/style change, re-fitting the box to the new text
    function applyTextChange(sig, changes, recordHistory = false) {
        const next = { ...sig, ...changes };
        if (changes.fontSize !== undefined) next.fontSize = normalizeFontSize(next.fontSize);
        store.updateSignatureOnDoc(sig.id, {
            ...changes,
            fontSize: next.fontSize,
            ...measureTextBox(next)
        }, recordHistory);
        syncInspectorInputs(sig);
    }

    // Used by the W/H inspector inputs: resizing a text box scales its font
    function scaleTextItem(sig, factor) {
        if (!Number.isFinite(factor) || factor <= 0) return;
        applyTextChange(sig, { fontSize: sig.fontSize * factor }, true);
    }

    function focusTextEditor() {
        if (!textContentInput || !getSelectedTextItem()) return;
        textContentInput.focus();
        textContentInput.select();
    }

    function syncTextEditor() {
        if (!textEditor) return;
        const sig = getSelectedTextItem();
        textEditor.classList.toggle("hidden", !sig);
        if (textEditorHint) textEditorHint.classList.toggle("hidden", !!sig);
        if (!sig) return;

        // Don't fight the caret while the user is typing
        if (document.activeElement !== textContentInput) textContentInput.value = sig.text;
        if (document.activeElement !== textSizeInput) textSizeInput.value = sig.fontSize;
        textFontSelect.value = sig.fontFamily;
        textBoldBtn.classList.toggle("active", !!sig.bold);
        textItalicBtn.classList.toggle("active", !!sig.italic);
        textColorInput.value = sig.color;
        textColorBtns.forEach(b => b.classList.toggle("active", b.dataset.color === sig.color));
        textCharWarning.classList.toggle("hidden", !hasUnsupportedChars(sig.text || "", sig.fontFamily));
    }

    function rememberTextStyle(sig) {
        lastTextStyle = { fontFamily: sig.fontFamily, fontSize: sig.fontSize, bold: sig.bold, italic: sig.italic, color: sig.color };
    }

    // Canvas measuring silently falls back to another font until Montserrat has loaded, so load every
    // cut up front and re-fit any Montserrat boxes that were measured too early.
    if (document.fonts && document.fonts.load) {
        Promise.all(["400", "700", "italic 400", "italic 700"].map(v => document.fonts.load(`${v} 16px "Montserrat Text"`)))
            .then(() => {
                store.state.signature.activeSignaturesOnDoc
                    .filter(s => s.type === "text" && s.fontFamily === "montserrat")
                    .forEach(s => store.updateSignatureOnDoc(s.id, measureTextBox(s)));
            })
            .catch(() => { /* offline or blocked: the stage falls back to sans-serif, the PDF is unaffected */ });
    }

    if (addTextBtn) {
        addTextBtn.addEventListener("click", () => {
            const doc = store.state.document;
            if (!doc.totalPages) {
                showStatus("Upload a PDF first, then add text to it.", "error");
                return;
            }
            showStatus(null);

            const props = { text: "Your text", ...lastTextStyle };
            const box = measureTextBox(props);
            const page = doc.pageDimensions[doc.currentPage - 1] || doc.pageDimensions[0];
            // Centered on the page, fanned out so consecutive boxes don't stack exactly
            const fan = (store.state.signature.activeSignaturesOnDoc.length % 6) * 18;
            const sig = store.addTextToDoc({
                ...props,
                ...box,
                page: doc.currentPage,
                x: Math.max(0, Math.round((page.width - box.width) / 2) + fan),
                y: Math.max(0, Math.round((page.height - box.height) / 2) + fan)
            });

            selectedSigId = sig.id;
            syncInspectorInputs(sig);
            renderStageSignatures();
            focusTextEditor();
        });
    }

    if (textContentInput) {
        let editSnapshotTaken = false;
        textContentInput.addEventListener("focus", () => { editSnapshotTaken = false; });
        textContentInput.addEventListener("input", () => {
            const sig = getSelectedTextItem();
            if (!sig) return;
            // One undo step per editing session rather than one per keystroke
            if (!editSnapshotTaken) {
                store.recordStateSnapshot();
                editSnapshotTaken = true;
            }
            applyTextChange(sig, { text: textContentInput.value });
        });
    }

    textFontSelect.addEventListener("change", () => {
        const sig = getSelectedTextItem();
        if (!sig) return;
        applyTextChange(sig, { fontFamily: textFontSelect.value }, true);
        rememberTextStyle(sig);
    });

    textSizeInput.addEventListener("change", () => {
        const sig = getSelectedTextItem();
        if (!sig) return;
        applyTextChange(sig, { fontSize: parseFloat(textSizeInput.value) || sig.fontSize }, true);
        rememberTextStyle(sig);
    });

    [[textBoldBtn, "bold"], [textItalicBtn, "italic"]].forEach(([btn, prop]) => {
        btn.addEventListener("click", () => {
            const sig = getSelectedTextItem();
            if (!sig) return;
            applyTextChange(sig, { [prop]: !sig[prop] }, true);
            rememberTextStyle(sig);
        });
    });

    textColorBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const sig = getSelectedTextItem();
            if (!sig) return;
            applyTextChange(sig, { color: btn.dataset.color }, true);
            rememberTextStyle(sig);
        });
    });

    // The native picker fires "input" continuously while dragging: one undo step per pick
    let colorSnapshotTaken = false;
    textColorInput.addEventListener("input", () => {
        const sig = getSelectedTextItem();
        if (!sig) return;
        if (!colorSnapshotTaken) {
            store.recordStateSnapshot();
            colorSnapshotTaken = true;
        }
        applyTextChange(sig, { color: textColorInput.value });
        rememberTextStyle(sig);
    });
    textColorInput.addEventListener("change", () => { colorSnapshotTaken = false; });

    // --- Action Processing ---
    processActionBtn.addEventListener("click", () => {
        const doc = store.state.document;
        // Merge mode's input is store.state.merge.files (from the dedicated "Add PDFs to Merge"
        // dropzone), not store.state.document -- that's only ever set by the single-file upload
        // card above it. Merge has its own "at least one file" check further down; this guard was
        // blocking every merge whose files came solely from the merge dropzone (the normal case).
        if (store.state.currentMode !== "merge" && !doc.fileId && !doc.fileObj) {
            showStatus("Please upload a PDF file first.", "error");
            return;
        }

        showStatus(null);
        actionSpinner.classList.remove("hidden");
        processActionBtn.disabled = true;

        const formData = new FormData();
        if (doc.fileId) formData.append("file_id", doc.fileId);
        if (doc.fileObj) formData.append("file", doc.fileObj);

        if (pdfPasswordInput.value) {
            formData.append("password", pdfPasswordInput.value);
        }

        let endpoint = "";

        if (store.state.currentMode === "sign") {
            const activeSigs = store.state.signature.activeSignaturesOnDoc;
            if (!activeSigs || activeSigs.length === 0) {
                showStatus("Please add at least one signature to the document first.", "error");
                actionSpinner.classList.add("hidden");
                processActionBtn.disabled = false;
                return;
            }

            endpoint = "/api/sign";

            formData.append("signatures_json", JSON.stringify(buildOverlaysPayload(activeSigs)));

        } else if (store.state.currentMode === "duplicate") {
            endpoint = "/api/duplicate";
            formData.append("pages_spec", dupPagesInput.value);
            formData.append("count", dupCountInput.value);
            const repeatSeq = document.querySelector('input[name="dupSequence"]:checked').value;
            formData.append("repeat_sequence", repeatSeq);
        if (customOutputFilenameInput && customOutputFilenameInput.value.trim()) {
            formData.append("custom_filename", customOutputFilenameInput.value.trim());
        }

        } else if (store.state.currentMode === "merge") {
            const mergeFiles = store.state.merge.files;
            if (!mergeFiles || mergeFiles.length === 0) {
                showStatus("Please add at least one PDF file to merge.", "error");
                actionSpinner.classList.add("hidden");
                processActionBtn.disabled = false;
                return;
            }
            endpoint = "/api/merge";
            const itemsPayload = mergeFiles.map(f => ({
                file_id: f.fileId,
                password: f.password || null,
                pages_spec: f.pagesSpec || null
            }));
            formData.append("items_json", JSON.stringify(itemsPayload));
            if (customOutputFilenameInput && customOutputFilenameInput.value.trim()) {
                formData.append("custom_filename", customOutputFilenameInput.value.trim());
            }

        } else if (store.state.currentMode === "clone") {
            endpoint = "/api/clone";
            if (customOutputFilenameInput && customOutputFilenameInput.value.trim()) {
                formData.append("custom_filename", customOutputFilenameInput.value.trim());
            }
        }

        let downloadUrl = "";
        let filePathHeader = "";

        fetch(endpoint, {
            method: "POST",
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json()
                    .then(err => { throw new Error(err.error || "Operation failed."); })
                    .catch(err => {
                        if (err.message && !err.message.includes("is not valid JSON") && !err.message.includes("Unexpected token")) {
                            throw err;
                        }
                        throw new Error(`Server Error (${response.status}): ${response.statusText}`);
                    });
            }
            downloadUrl = response.headers.get("X-Download-Url") || "";
            filePathHeader = response.headers.get("X-File-Path") || "";
            return response.blob();
        })
        .then(blob => {
            const customVal = customOutputFilenameInput ? customOutputFilenameInput.value.trim() : "";
            let fileName = customVal;
            if (fileName) {
                if (!fileName.toLowerCase().endsWith(".pdf")) fileName += ".pdf";
            } else {
                fileName = `${store.state.currentMode}_${doc.filename || 'document.pdf'}`;
            }
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();

            const directLink = downloadUrl || url;
            const successHtml = `
                <div>
                    <strong>✅ PDF Saved Successfully!</strong><br>
                    <a href="${directLink}" download="${fileName}" target="_blank" style="color: #4cd964; text-decoration: underline; font-weight: 600; display: inline-block; margin-top: 6px;">
                        📥 Downloaded ${fileName} (Click here to open or re-download)
                    </a>
                </div>
            `;
            showStatus(successHtml, "success", true);
            setTimeout(() => {
                a.remove();
            }, 1000);
        })
        .catch(err => {
            showStatus(err.message, "error");
        })
        .finally(() => {
            actionSpinner.classList.add("hidden");
            processActionBtn.disabled = false;
        });
    });

    // --- Figma-Style Infinite Canvas: Free Pan & Zoom ---
    // The page is positioned with a translate + scale transform rather than by scrolling the
    // viewport, so it can be dragged anywhere in the stage (scrolling clamps it to the edges).
    // Left-drag on anything that isn't a placed item pans; middle/right-drag, Space+drag and the
    // Hand tool pan from anywhere. Trackpad two-finger scroll pans, pinch / ⌘-scroll zooms toward
    // the cursor. screenToDocument() reads getBoundingClientRect(), so it follows the transform.
    const togglePanToolBtn = document.getElementById("togglePanToolBtn");
    const PAN_THRESHOLD_PX = 3;
    let isPanModeActive = false;
    let isPanning = false;
    let panPending = null; // { button, startX, startY, onEmpty } until the pointer moves past the threshold
    let panStartX = 0, panStartY = 0;
    let panOriginX = 0, panOriginY = 0;
    let panX = 0, panY = 0;
    let zoomLevel = 1.0;
    let suppressNextClick = false;

    function applyStageTransform() {
        if (!pdfCanvasContainer) return;
        pdfCanvasContainer.style.transformOrigin = "0 0";
        pdfCanvasContainer.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
    }

    function isTypingTarget(el) {
        return !!el && (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable);
    }

    function setPanMode(active) {
        isPanModeActive = active;
        if (togglePanToolBtn) {
            togglePanToolBtn.classList.toggle("active", active);
        }
        if (stageViewport) {
            stageViewport.classList.toggle("pan-active", active);
        }
        if (active && isStampModeActive) {
            setStampMode(false);
        }
    }

    if (togglePanToolBtn) {
        togglePanToolBtn.addEventListener("click", () => setPanMode(!isPanModeActive));
    }

    // Spacebar Key Hold for Temporary Figma Pan Mode
    window.addEventListener("keydown", (e) => {
        if (e.code === "Space" && !isTypingTarget(document.activeElement)) {
            e.preventDefault();
            if (!isPanModeActive) setPanMode(true);
        }
    });

    window.addEventListener("keyup", (e) => {
        if (e.code === "Space" && isPanModeActive) {
            setPanMode(false);
        }
    });

    function beginPan(clientX, clientY) {
        isPanning = true;
        stageViewport.classList.add("is-panning");
        panStartX = clientX;
        panStartY = clientY;
        panOriginX = panX;
        panOriginY = panY;
    }

    if (stageViewport) {
        // Capture phase so the Hand tool / middle button pan even when pressed on a placed item,
        // before that item's own drag handler sees the event.
        stageViewport.addEventListener("mousedown", (e) => {
            closeItemContextMenu();
            if (isPanModeActive || e.button === 1) {
                beginPan(e.clientX, e.clientY);
                e.preventDefault();
                e.stopPropagation();
            }
        }, true);

        stageViewport.addEventListener("mousedown", (e) => {
            if (isPanning || e.target.closest(".signature-overlay")) return;
            if (e.button !== 0 && e.button !== 2) return;
            // Don't start a pan until the pointer actually moves, so a plain click still
            // stamps (stamp mode) or deselects (everywhere else).
            panPending = { button: e.button, startX: e.clientX, startY: e.clientY };
            if (e.button === 0) e.preventDefault();
        });

        // Right-click on the page/background never shows the browser menu; placed items show
        // their own (see openItemContextMenu).
        stageViewport.addEventListener("contextmenu", (e) => e.preventDefault());

        window.addEventListener("mousemove", (e) => {
            if (panPending && !isPanning) {
                const moved = Math.hypot(e.clientX - panPending.startX, e.clientY - panPending.startY);
                if (moved < PAN_THRESHOLD_PX) return;
                beginPan(panPending.startX, panPending.startY);
            }
            if (!isPanning) return;
            panX = panOriginX + (e.clientX - panStartX);
            panY = panOriginY + (e.clientY - panStartY);
            applyStageTransform();
        });

        window.addEventListener("mouseup", (e) => {
            if (isPanning) {
                isPanning = false;
                stageViewport.classList.remove("is-panning");
                // A drag that started on the page must not also count as a stamp click.
                if (panPending && panPending.button === 0) suppressNextClick = true;
            } else if (panPending && panPending.button === 0 && !isStampModeActive && selectedSigId) {
                // Plain click on empty page/background: deselect, like Figma.
                selectedSigId = null;
                renderStageSignatures();
            }
            panPending = null;
        });

        window.addEventListener("click", (e) => {
            if (suppressNextClick) {
                suppressNextClick = false;
                e.stopPropagation();
                e.preventDefault();
            }
        }, true);

        // Two-finger scroll / mouse wheel over the stage pans the canvas.
        stageViewport.addEventListener("wheel", (e) => {
            if (e.ctrlKey || e.metaKey) return; // handled by the zoom interceptor below
            e.preventDefault();
            const unit = e.deltaMode === 1 ? 16 : (e.deltaMode === 2 ? stageViewport.clientHeight : 1);
            const dx = e.shiftKey && !e.deltaX ? e.deltaY : e.deltaX;
            const dy = e.shiftKey && !e.deltaX ? 0 : e.deltaY;
            panX -= dx * unit;
            panY -= dy * unit;
            applyStageTransform();
        }, { passive: false });
    }

    // --- Stage Canvas Zoom & Global Page Zoom Interception ---
    const zoomOutBtn = document.getElementById("zoomOutBtn");
    const zoomInBtn = document.getElementById("zoomInBtn");
    const zoomResetBtn = document.getElementById("zoomResetBtn");
    const zoomVal = document.getElementById("zoomVal");

    // Zooms so that the screen point (anchorX, anchorY) stays over the same spot on the page.
    // Defaults to the centre of the stage (toolbar buttons).
    function setStageZoom(newZoom, anchorX, anchorY) {
        const clamped = Math.max(0.3, Math.min(4.0, newZoom));
        if (pdfCanvasContainer && stageViewport) {
            if (anchorX === undefined) {
                const vp = stageViewport.getBoundingClientRect();
                anchorX = vp.left + vp.width / 2;
                anchorY = vp.top + vp.height / 2;
            }
            // With transform-origin 0 0, the untransformed layout origin is the current rect's
            // top-left minus the pan offset.
            const rect = pdfCanvasContainer.getBoundingClientRect();
            const originX = rect.left - panX;
            const originY = rect.top - panY;
            const ratio = clamped / zoomLevel;
            panX = (anchorX - originX) - (anchorX - originX - panX) * ratio;
            panY = (anchorY - originY) - (anchorY - originY - panY) * ratio;
        }
        zoomLevel = clamped;
        if (zoomVal) zoomVal.textContent = `${Math.round(zoomLevel * 100)}%`;
        applyStageTransform();
        renderStageSignatures();
    }

    function resetStageView() {
        panX = 0;
        panY = 0;
        zoomLevel = 1.0;
        if (zoomVal) zoomVal.textContent = "100%";
        applyStageTransform();
        renderStageSignatures();
    }

    if (zoomOutBtn) zoomOutBtn.addEventListener("click", () => setStageZoom(zoomLevel - 0.15));
    if (zoomInBtn) zoomInBtn.addEventListener("click", () => setStageZoom(zoomLevel + 0.15));
    if (zoomResetBtn) zoomResetBtn.addEventListener("click", resetStageView);
    store.subscribe("document:loaded", resetStageView);

    // Global interception: Prevent browser page zooming, route pinch/ctrl-wheel to stage canvas zoom (Figma style)
    window.addEventListener("wheel", (e) => {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            const factor = Math.exp(-Math.max(-50, Math.min(50, e.deltaY)) * 0.01);
            const overStage = stageViewport && stageViewport.contains(e.target);
            if (overStage) {
                setStageZoom(zoomLevel * factor, e.clientX, e.clientY);
            } else {
                setStageZoom(zoomLevel * factor);
            }
        }
    }, { passive: false });

    // Safari/Mac gesture zoom prevention for whole page
    window.addEventListener("gesturestart", (e) => e.preventDefault());
    window.addEventListener("gesturechange", (e) => e.preventDefault());
    window.addEventListener("gestureend", (e) => e.preventDefault());



    // --- Full Document Preview Screen Modal ---
    const openFullPreviewBtn = document.getElementById("openFullPreviewBtn");
    const pdfPreviewModal = document.getElementById("pdfPreviewModal");
    const closePreviewModalBtn = document.getElementById("closePreviewModalBtn");
    const closePreviewFooterBtn = document.getElementById("closePreviewFooterBtn");
    const previewSaveBtn = document.getElementById("previewSaveBtn");
    const previewSaveFooterBtn = document.getElementById("previewSaveFooterBtn");
    const previewPageCount = document.getElementById("previewPageCount");
    const previewSpinner = document.getElementById("previewSpinner");
    const previewPagesContainer = document.getElementById("previewPagesContainer");

    if (openFullPreviewBtn) {
        openFullPreviewBtn.addEventListener("click", () => {
            const doc = store.state.document;
            if (!doc.fileId && !doc.fileObj) {
                showStatus("Please upload a PDF document first.", "error");
                return;
            }

            pdfPreviewModal.classList.remove("hidden");
            previewSpinner.classList.remove("hidden");
            previewPagesContainer.classList.add("hidden");
            previewPagesContainer.innerHTML = "";

            const formData = new FormData();
            if (doc.fileId) formData.append("file_id", doc.fileId);
            if (doc.fileObj) formData.append("file", doc.fileObj);

            if (pdfPasswordInput.value) {
                formData.append("password", pdfPasswordInput.value);
            }

            const activeSigs = store.state.signature.activeSignaturesOnDoc;
            if (activeSigs && activeSigs.length > 0) {
                formData.append("signatures_json", JSON.stringify(buildOverlaysPayload(activeSigs)));
            }

            fetch("/api/preview-pdf", {
                method: "POST",
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert("Preview error: " + data.error);
                    pdfPreviewModal.classList.add("hidden");
                    return;
                }

                previewSpinner.classList.add("hidden");
                previewPagesContainer.classList.remove("hidden");
                previewPageCount.textContent = `${data.total_pages} Pages`;

                data.page_previews.forEach((b64, idx) => {
                    const card = document.createElement("div");
                    card.className = "preview-page-card";
                    card.innerHTML = `
                        <img src="${b64}" alt="Page ${idx + 1}">
                        <div class="preview-page-badge">Page ${idx + 1} of ${data.total_pages}</div>
                    `;
                    previewPagesContainer.appendChild(card);
                });
            })
            .catch(err => {
                alert("Failed to load preview: " + err.message);
                pdfPreviewModal.classList.add("hidden");
            });
        });
    }

    if (closePreviewModalBtn) closePreviewModalBtn.addEventListener("click", () => pdfPreviewModal.classList.add("hidden"));
    if (closePreviewFooterBtn) closePreviewFooterBtn.addEventListener("click", () => pdfPreviewModal.classList.add("hidden"));

    const triggerSaveFromPreview = () => {
        pdfPreviewModal.classList.add("hidden");
        processActionBtn.click();
    };

    if (previewSaveBtn) previewSaveBtn.addEventListener("click", triggerSaveFromPreview);
    if (previewSaveFooterBtn) previewSaveFooterBtn.addEventListener("click", triggerSaveFromPreview);

    function showStatus(msg, type = "error", isHtml = false) {
        if (!msg) {
            statusAlert.classList.add("hidden");
            return;
        }
        if (isHtml) {
            statusAlert.innerHTML = msg;
        } else {
            statusAlert.textContent = msg;
        }
        statusAlert.className = `status-alert ${type}`;
        statusAlert.classList.remove("hidden");
    }
});


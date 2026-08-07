// Apple HIG PDF Duplicator & Sign Studio - Multi-Signature Application Logic

document.addEventListener("DOMContentLoaded", () => {
    const store = window.appStore;

    // --- DOM Elements ---
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const pwaInstallBtn = document.getElementById("pwaInstallBtn");
    const segmentedButtons = document.querySelectorAll(".segmented-item");
    
    // Cards
    const signControlsCard = document.getElementById("signControlsCard");
    const duplicateControlsCard = document.getElementById("duplicateControlsCard");
    const cloneControlsCard = document.getElementById("cloneControlsCard");
    
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

    // Stage
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
    const addAnotherSigBtn = document.getElementById("addAnotherSigBtn");
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
        duplicateControlsCard.classList.add("hidden");
        cloneControlsCard.classList.add("hidden");

        if (mode === "sign") {
            signControlsCard.classList.remove("hidden");
            actionBtnText.textContent = "Sign & Download PDF";
            renderStageSignatures();
        } else if (mode === "duplicate") {
            duplicateControlsCard.classList.remove("hidden");
            actionBtnText.textContent = "Duplicate & Download PDF";
            clearStageOverlays();
        } else if (mode === "clone") {
            cloneControlsCard.classList.remove("hidden");
            actionBtnText.textContent = "Clone & Decrypt PDF";
            clearStageOverlays();
        }
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
        if (store.state.document.fileObj) {
            handleFileUpload(store.state.document.fileObj);
        }
    });

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
                }
                showStatus(data.error, "error");
                return;
            }

            store.setDocument({
                fileId: data.file_id,
                fileObj: file,
                filename: file.filename,
                totalPages: data.total_pages,
                isEncrypted: data.is_encrypted,
                currentPage: 1,
                pagePreviews: data.page_previews,
                pageDimensions: data.page_dimensions
            });
        })
        .catch(err => {
            showStatus("Failed to inspect PDF: " + err.message, "error");
        });
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
    });

    store.subscribe("document:reset", () => {
        pdfFileInput.value = "";
        pdfPasswordInput.value = "";
        docInfoCard.classList.add("hidden");
        passwordSection.classList.add("hidden");
        dropzone.classList.remove("hidden");
        pdfCanvasContainer.classList.add("hidden");
        thumbnailRibbon.classList.add("hidden");
        emptyStageNotice.classList.remove("hidden");
        clearStageOverlays();
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
            signatureTrayContainer.innerHTML = `
                <div class="empty-tray-notice">
                    No saved signatures in tray.<br>
                    Click <strong>+ New Signature</strong> above to draw or upload!
                </div>
            `;
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
                    <span class="tray-sig-drag-handle" title="Drag directly onto PDF">⋮⋮</span>
                    <div class="tray-sig-thumb">
                        <img src="${item.dataUrl}" alt="${item.title}">
                    </div>
                    <div class="tray-sig-details">
                        <span class="tray-sig-title">${item.title || `Sig #${index + 1}`}</span>
                        <span class="tray-sig-hint">${isCarrying ? '✋ Currently Carrying...' : 'Drag onto PDF or Click to Stamp'}</span>
                    </div>
                </div>
                <button class="overlay-action-btn btn-remove small" title="Delete Signature">✕</button>
            `;

            // HTML5 Drag Event Handlers (Supports PDF drop + Tray Reordering)
            card.addEventListener("dragstart", (e) => {
                draggedSigUrl = item.dataUrl;
                e.dataTransfer.setData("text/plain", item.dataUrl);
                e.dataTransfer.setData("text/tray-index", index.toString());
                e.dataTransfer.effectAllowed = "copyMove";
                card.classList.add("dragging-source");
                if (ghostSigImg) ghostSigImg.src = item.dataUrl;
            });

            card.addEventListener("dragend", () => {
                draggedSigUrl = null;
                card.classList.remove("dragging-source");
                document.querySelectorAll(".tray-sig-card").forEach(c => c.classList.remove("drag-over-target"));
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

            const rect = pdfPageImg.getBoundingClientRect();
            const dropX = e.clientX - rect.left;
            const dropY = e.clientY - rect.top;
            const scale = getScaleFactor();

            const sigW = store.state.placement.width || 150;
            const sigH = store.state.placement.height || 60;
            const pdfX = Math.max(0, Math.round((dropX / scale) - (sigW / 2)));
            const pdfY = Math.max(0, Math.round((dropY / scale) - (sigH / 2)));

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

            const rect = pdfPageImg.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;
            const scale = getScaleFactor();

            const sigW = store.state.placement.width || 150;
            const sigH = store.state.placement.height || 60;
            const pdfX = Math.max(0, Math.round((clickX / scale) - (sigW / 2)));
            const pdfY = Math.max(0, Math.round((clickY / scale) - (sigH / 2)));

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
            // Check if signature belongs to current page or all pages
            if (sig.page !== doc.currentPage && signPagesMode.value !== "all") return;

            const overlay = document.createElement("div");
            overlay.className = `signature-overlay ${sig.confirmed ? 'confirmed' : ''} ${selectedSigId === sig.id ? 'active-selected' : ''}`;
            overlay.dataset.sigId = sig.id;
            overlay.style.left = `${sig.x * scale}px`;
            overlay.style.top = `${sig.y * scale}px`;
            overlay.style.width = `${sig.width * scale}px`;
            overlay.style.height = `${sig.height * scale}px`;

            overlay.innerHTML = `
                <div class="overlay-action-bar">
                    <button class="overlay-action-btn btn-confirm" title="Confirm & Lock Placement">✓</button>
                    <button class="overlay-action-btn btn-remove" title="Remove Signature">✕</button>
                </div>
                <div class="overlay-inner">
                    <img src="${sig.dataUrl}" alt="Signature">
                </div>
                <div class="resize-handle handle-nw" data-handle="nw"></div>
                <div class="resize-handle handle-ne" data-handle="ne"></div>
                <div class="resize-handle handle-sw" data-handle="sw"></div>
                <div class="resize-handle handle-se" data-handle="se"></div>
            `;

            // Action Buttons
            const confirmBtn = overlay.querySelector(".btn-confirm");
            const removeBtn = overlay.querySelector(".btn-remove");

            confirmBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                store.confirmSignatureOnDoc(sig.id);
            });

            removeBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                store.removeSignatureFromDoc(sig.id);
            });

            // Drag & Resize Listeners
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
                    <div class="sig-item-thumb">
                        <img src="${sig.dataUrl}" alt="Sig ${index + 1}">
                    </div>
                    <span class="sig-item-title">Sig #${index + 1} (Pg ${sig.page})</span>
                </div>
                <div class="sig-item-actions">
                    <button class="overlay-action-btn btn-confirm small" title="Confirm Placement">${sig.confirmed ? '✓' : '✓'}</button>
                    <button class="overlay-action-btn btn-remove small" title="Remove">✕</button>
                </div>
            `;

            item.addEventListener("click", () => {
                selectedSigId = sig.id;
                sigXInput.value = Math.round(sig.x);
                sigYInput.value = Math.round(sig.y);
                sigWInput.value = Math.round(sig.width);
                sigHInput.value = Math.round(sig.height);
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

    store.subscribe("signatures:doc_updated", () => {
        renderStageSignatures();
    });

    // Attach Drag & Resize to an Overlay Box
    function attachOverlayDragAndResize(overlay, sig) {
        let isDragging = false;
        let isResizing = false;
        let resizeHandle = null;
        let startX = 0, startY = 0;
        let initL = 0, initT = 0, initW = 0, initH = 0;

        overlay.addEventListener("mousedown", (e) => {
            selectedSigId = sig.id;
            if (e.target.classList.contains("resize-handle")) {
                isResizing = true;
                resizeHandle = e.target.dataset.handle;
            } else if (!e.target.classList.contains("overlay-action-btn")) {
                isDragging = true;
            } else {
                return;
            }

            startX = e.clientX;
            startY = e.clientY;
            initL = parseFloat(overlay.style.left) || 0;
            initT = parseFloat(overlay.style.top) || 0;
            initW = overlay.offsetWidth;
            initH = overlay.offsetHeight;

            e.preventDefault();
        });

        const onMouseMove = (e) => {
            if (!isDragging && !isResizing) return;
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            const scale = getScaleFactor();

            if (isDragging) {
                let newL = Math.max(0, Math.min(initL + deltaX, pdfPageImg.clientWidth - overlay.offsetWidth));
                let newT = Math.max(0, Math.min(initT + deltaY, pdfPageImg.clientHeight - overlay.offsetHeight));
                overlay.style.left = `${newL}px`;
                overlay.style.top = `${newT}px`;

                sigXInput.value = Math.round(newL / scale);
                sigYInput.value = Math.round(newT / scale);
            } else if (isResizing) {
                let newW = initW, newH = initH, newL = initL, newT = initT;
                if (resizeHandle.includes("e")) newW = Math.max(30, initW + deltaX);
                if (resizeHandle.includes("s")) newH = Math.max(15, initH + deltaY);
                if (resizeHandle.includes("w")) {
                    const calcW = initW - deltaX;
                    if (calcW > 30) { newW = calcW; newL = initL + deltaX; }
                }
                if (resizeHandle.includes("n")) {
                    const calcH = initH - deltaY;
                    if (calcH > 15) { newH = calcH; newT = initT + deltaY; }
                }

                overlay.style.left = `${newL}px`;
                overlay.style.top = `${newT}px`;
                overlay.style.width = `${newW}px`;
                overlay.style.height = `${newH}px`;

                sigXInput.value = Math.round(newL / scale);
                sigYInput.value = Math.round(newT / scale);
                sigWInput.value = Math.round(newW / scale);
                sigHInput.value = Math.round(newH / scale);
            }
        };

        const onMouseUp = () => {
            if (isDragging || isResizing) {
                const scale = getScaleFactor();
                store.updateSignatureOnDoc(sig.id, {
                    x: Math.round((parseFloat(overlay.style.left) || 0) / scale),
                    y: Math.round((parseFloat(overlay.style.top) || 0) / scale),
                    width: Math.round(overlay.offsetWidth / scale),
                    height: Math.round(overlay.offsetHeight / scale)
                });
            }
            isDragging = false;
            isResizing = false;
            resizeHandle = null;
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
        };

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
    }

    // --- Inputs & Undo/Redo ---
    [sigXInput, sigYInput, sigWInput, sigHInput].forEach(input => {
        input.addEventListener("change", () => {
            if (selectedSigId) {
                store.updateSignatureOnDoc(selectedSigId, {
                    x: parseFloat(sigXInput.value) || 50,
                    y: parseFloat(sigYInput.value) || 50,
                    width: parseFloat(sigWInput.value) || 150,
                    height: parseFloat(sigHInput.value) || 60
                });
            }
        });
    });

    undoBtn.addEventListener("click", () => store.undoPlacement());
    redoBtn.addEventListener("click", () => store.redoPlacement());

    if (addAnotherSigBtn) {
        addAnotherSigBtn.addEventListener("click", () => {
            sigStudioModal.classList.remove("hidden");
            initCanvas();
        });
    }

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

    function initCanvas() {
        if (!canvasCtx) return;
        canvasCtx.lineCap = "round";
        canvasCtx.lineJoin = "round";
        canvasCtx.strokeStyle = activeColor;
        canvasCtx.lineWidth = strokeWidth;
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
        if (canvasCtx) canvasCtx.lineWidth = strokeWidth;
    });

    sigUploadDropzone.addEventListener("click", () => sigImageFileInput.click());
    sigImageFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            const reader = new FileReader();
            reader.onload = (evt) => {
                uploadedSigImg.src = evt.target.result;
                uploadedSigPreview.classList.remove("hidden");
                store.setActiveSignature(evt.target.result);
            };
            reader.readAsDataURL(e.target.files[0]);
        }
    });

    if (addAndKeepSigBtn) {
        addAndKeepSigBtn.addEventListener("click", async () => {
            const activeTab = document.querySelector(".modal-tab.active").dataset.tab;
            let sigData = store.state.signature.activeDataUrl;

            if (activeTab === "draw" && canvasCtx) {
                sigData = sigCanvas.toDataURL("image/png");
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
                return;
            }

            if (sigData) {
                store.addSignatureToDoc(sigData);
            }
        });
    }

    saveSigModalBtn.addEventListener("click", async () => {
        const activeTab = document.querySelector(".modal-tab.active").dataset.tab;
        let sigData = store.state.signature.activeDataUrl;

        if (activeTab === "draw" && canvasCtx) {
            sigData = sigCanvas.toDataURL("image/png");
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
        }

        if (!store.state.signature.activeDataUrl && !sigData) {
            alert("Please draw, upload, or select a signature first.");
            return;
        }

        if (sigData) {
            store.addSignatureToDoc(sigData);
        }

        sigStudioModal.classList.add("hidden");
    });


    // --- Action Processing ---
    processActionBtn.addEventListener("click", () => {
        const doc = store.state.document;
        if (!doc.fileId && !doc.fileObj) {
            showStatus("Please upload a PDF file first.", "error");
            return;
        }

        showStatus(null);
        actionSpinner.classList.remove("hidden");
        processActionBtn.disabled = true;

        const formData = new FormData();
        if (doc.fileId) formData.append("file_id", doc.fileId);
        else formData.append("file", doc.fileObj);

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

            const sigsPayload = activeSigs.map(s => ({
                signature_img: s.dataUrl,
                pages_spec: signPagesMode.value === "current" ? s.page.toString() : (signPagesMode.value === "custom" ? signPageSpecInput.value : ""),
                x: s.x,
                y: s.y,
                width: s.width,
                height: s.height,
                y_from_top: true
            }));

            formData.append("signatures_json", JSON.stringify(sigsPayload));

        } else if (store.state.currentMode === "duplicate") {
            endpoint = "/api/duplicate";
            formData.append("pages_spec", dupPagesInput.value);
            formData.append("count", dupCountInput.value);
            const repeatSeq = document.querySelector('input[name="dupSequence"]:checked').value;
            formData.append("repeat_sequence", repeatSeq);

        } else if (store.state.currentMode === "clone") {
            endpoint = "/api/clone";
        }

        let downloadUrl = "";
        let filePathHeader = "";

        fetch(endpoint, {
            method: "POST",
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Operation failed."); });
            }
            downloadUrl = response.headers.get("X-Download-Url") || "";
            filePathHeader = response.headers.get("X-File-Path") || "";
            return response.blob();
        })
        .then(blob => {
            const fileName = `${store.state.currentMode}_${doc.filename || 'document.pdf'}`;
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
                        📥 Click here to Download / Open PDF
                    </a>
                    ${filePathHeader ? `<br><small style="color: var(--text-secondary); display: inline-block; margin-top: 4px;">Saved to Downloads folder:<br><code>${filePathHeader}</code></small>` : ''}
                </div>
            `;
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

    // --- Isolated Stage Zooming & Figma Pan Tool ---
    const togglePanToolBtn = document.getElementById("togglePanToolBtn");
    let isPanModeActive = false;
    let isPanning = false;
    let panStartX = 0, panStartY = 0;
    let scrollLeftStart = 0, scrollTopStart = 0;

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
        if (e.code === "Space" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
            e.preventDefault();
            if (!isPanModeActive) setPanMode(true);
        }
    });

    window.addEventListener("keyup", (e) => {
        if (e.code === "Space" && isPanModeActive) {
            setPanMode(false);
        }
    });

    if (stageViewport) {
        stageViewport.addEventListener("mousedown", (e) => {
            if (isPanModeActive || e.button === 1 || e.button === 2) { // Left-click in Pan mode, Middle click, or Right click
                isPanning = true;
                stageViewport.classList.add("is-panning");
                panStartX = e.clientX;
                panStartY = e.clientY;
                scrollLeftStart = stageViewport.scrollLeft;
                scrollTopStart = stageViewport.scrollTop;
                e.preventDefault();
            }
        });

        stageViewport.addEventListener("contextmenu", (e) => {
            if (isPanning || isPanModeActive) {
                e.preventDefault();
            }
        });

        window.addEventListener("mousemove", (e) => {
            if (!isPanning) return;
            const dx = e.clientX - panStartX;
            const dy = e.clientY - panStartY;
            stageViewport.scrollLeft = scrollLeftStart - dx;
            stageViewport.scrollTop = scrollTopStart - dy;
        });

        window.addEventListener("mouseup", () => {
            if (isPanning) {
                isPanning = false;
                stageViewport.classList.remove("is-panning");
            }
        });
    }

    const zoomOutBtn = document.getElementById("zoomOutBtn");
    const zoomInBtn = document.getElementById("zoomInBtn");
    const zoomResetBtn = document.getElementById("zoomResetBtn");
    const zoomVal = document.getElementById("zoomVal");

    let zoomLevel = 1.0;

    function setStageZoom(newZoom) {
        zoomLevel = Math.max(0.5, Math.min(3.0, newZoom));
        if (zoomVal) zoomVal.textContent = `${Math.round(zoomLevel * 100)}%`;
        if (pdfCanvasContainer) {
            pdfCanvasContainer.style.transform = `scale(${zoomLevel})`;
            pdfCanvasContainer.style.transformOrigin = "top center";
        }
        renderStageSignatures();
    }

    if (zoomOutBtn) zoomOutBtn.addEventListener("click", () => setStageZoom(zoomLevel - 0.15));
    if (zoomInBtn) zoomInBtn.addEventListener("click", () => setStageZoom(zoomLevel + 0.15));
    if (zoomResetBtn) zoomResetBtn.addEventListener("click", () => setStageZoom(1.0));

    if (stageViewport) {
        stageViewport.addEventListener("wheel", (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 0.08 : -0.08;
                setStageZoom(zoomLevel + delta);
            } else {
                stageViewport.scrollLeft += e.deltaX;
                stageViewport.scrollTop += e.deltaY;
            }
        }, { passive: false });
    }



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
            else formData.append("file", doc.fileObj);

            if (pdfPasswordInput.value) {
                formData.append("password", pdfPasswordInput.value);
            }

            const activeSigs = store.state.signature.activeSignaturesOnDoc;
            if (activeSigs && activeSigs.length > 0) {
                const sigsPayload = activeSigs.map(s => ({
                    signature_img: s.dataUrl,
                    pages_spec: signPagesMode.value === "current" ? s.page.toString() : (signPagesMode.value === "custom" ? signPageSpecInput.value : ""),
                    x: s.x,
                    y: s.y,
                    width: s.width,
                    height: s.height,
                    y_from_top: true
                }));
                formData.append("signatures_json", JSON.stringify(sigsPayload));
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


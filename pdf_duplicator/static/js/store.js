/**
 * PDF Studio Pro - Reactive State Management Store
 * Handles application state, reactive subscriptions, IndexedDB persistent signature storage,
 * and Undo/Redo placement history.
 */

class PDFStudioStore {
    constructor() {
        this.listeners = new Map();
        
        // Initial State
        this.state = {
            currentMode: "sign", // "sign" | "duplicate" | "clone"
            theme: localStorage.getItem("pdf_studio_theme") || "dark-mode",
            
            // Document State
            document: {
                fileId: null,
                fileObj: null,
                filename: null,
                totalPages: 0,
                isEncrypted: false,
                currentPage: 1,
                pagePreviews: [],
                pageDimensions: []
            },
            
            // Signature State
            signature: {
                activeDataUrl: null,
                savedSignatures: [], // Array of { id, dataUrl, createdAt, title }
                activeSignaturesOnDoc: [] // Array of { id, dataUrl, page, x, y, width, height, confirmed }
            },

            
            // Placement State & History
            placement: {
                x: 50,
                y: 50,
                width: 150,
                height: 60,
                pagesMode: "current", // "current" | "all" | "custom"
                customPageSpec: ""
            },
            
            // Undo/Redo Stack
            history: {
                undoStack: [],
                redoStack: []
            },
            
            // Duplication Mode Settings
            duplication: {
                pagesSpec: "",
                count: 2,
                repeatSequence: false
            },

            // Custom Output Filename
            customOutputFilename: "",

            // Merge Mode State Queue
            merge: {
                files: [] // Array of { id, fileId, filename, totalPages, isEncrypted, password, pagesSpec, pagePreviews }
            }
        };

        this.initIndexedDB();
    }

    // --- Observer / Event Listener Subscription Pattern ---
    subscribe(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
        return () => {
            const callbacks = this.listeners.get(event).filter(cb => cb !== callback);
            this.listeners.set(event, callbacks);
        };
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(cb => cb(data, this.state));
        }
        if (this.listeners.has("*")) {
            this.listeners.get("*").forEach(cb => cb(event, data, this.state));
        }
    }

    // --- State Setters & Dispatchers ---
    setMode(mode) {
        if (this.state.currentMode !== mode) {
            this.state.currentMode = mode;
            this.emit("mode:changed", mode);
        }
    }

    setCustomOutputFilename(filename) {
        this.state.customOutputFilename = filename || "";
        this.emit("output_filename:changed", this.state.customOutputFilename);
    }

    setTheme(theme) {
        this.state.theme = theme;
        localStorage.setItem("pdf_studio_theme", theme);
        this.emit("theme:changed", theme);
    }

    setDocument(docData) {
        this.state.document = { ...this.state.document, ...docData };
        this.emit("document:loaded", this.state.document);
    }

    resetDocument() {
        this.state.document = {
            fileId: null,
            fileObj: null,
            filename: null,
            totalPages: 0,
            isEncrypted: false,
            currentPage: 1,
            pagePreviews: [],
            pageDimensions: []
        };
        this.emit("document:reset");
    }

    setCurrentPage(pageNum) {
        if (pageNum >= 1 && pageNum <= this.state.document.totalPages) {
            this.state.document.currentPage = pageNum;
            this.emit("page:changed", pageNum);
        }
    }

    // --- Merge Mode Queue Methods ---
    addMergeFile(fileData) {
        const item = {
            id: "merge_item_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
            fileId: fileData.fileId || null,
            fileObj: fileData.fileObj || null,
            filename: fileData.filename || "document.pdf",
            totalPages: fileData.totalPages || 0,
            isEncrypted: fileData.isEncrypted || false,
            password: fileData.password || "",
            pagesSpec: fileData.pagesSpec || "",
            pagePreviews: fileData.pagePreviews || []
        };
        this.state.merge.files.push(item);
        this.emit("merge:files_updated", this.state.merge.files);
        return item;
    }

    removeMergeFile(id) {
        this.state.merge.files = this.state.merge.files.filter(f => f.id !== id);
        this.emit("merge:files_updated", this.state.merge.files);
    }

    moveMergeFile(fromIndex, toIndex) {
        const list = this.state.merge.files;
        if (fromIndex < 0 || fromIndex >= list.length || toIndex < 0 || toIndex >= list.length || fromIndex === toIndex) return;
        const [moved] = list.splice(fromIndex, 1);
        list.splice(toIndex, 0, moved);
        this.emit("merge:files_updated", this.state.merge.files);
    }

    updateMergeFile(id, newProps) {
        const item = this.state.merge.files.find(f => f.id === id);
        if (item) {
            Object.assign(item, newProps);
            this.emit("merge:files_updated", this.state.merge.files);
        }
    }

    // --- Signature Management & Storage ---
    setActiveSignature(dataUrl) {
        this.state.signature.activeDataUrl = dataUrl;
        this.emit("signature:active", dataUrl);
    }

    addSignatureToDoc(dataUrl, customProps = {}) {
        this.recordStateSnapshot();
        const docPage = this.state.document.currentPage || 1;
        const existingCount = this.state.signature.activeSignaturesOnDoc.length;
        const offsetX = (existingCount % 6) * 35;
        const offsetY = (existingCount % 6) * 30;

        const baseX = customProps.x || this.state.placement.x || 50;
        const baseY = customProps.y || this.state.placement.y || 50;

        let initialW = customProps.width || this.state.placement.width || 150;
        let initialH = customProps.height || this.state.placement.height || 60;

        const maxZ = existingCount > 0 
            ? Math.max(...this.state.signature.activeSignaturesOnDoc.map(s => s.zIndex || 1)) + 1 
            : 1;

        const newSigItem = {
            id: "sig_doc_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
            dataUrl: dataUrl,
            page: docPage,
            x: baseX + (customProps.x ? 0 : offsetX),
            y: baseY + (customProps.y ? 0 : offsetY),
            width: initialW,
            height: initialH,
            rotation: customProps.rotation || 0,
            scaleX: customProps.scaleX || 1.0,
            scaleY: customProps.scaleY || 1.0,
            opacity: customProps.opacity !== undefined ? customProps.opacity : 1.0,
            zIndex: customProps.zIndex || maxZ,
            locked: !!customProps.locked,
            confirmed: false
        };

        // Determine proportional dimensions from image natural dimensions to prevent stretching
        const img = new Image();
        img.src = dataUrl;
        const applyProportions = () => {
            if (img.naturalWidth && img.naturalHeight) {
                const ratio = img.naturalWidth / img.naturalHeight;
                newSigItem.aspectRatio = ratio;
                newSigItem.origWidth = img.naturalWidth;
                newSigItem.origHeight = img.naturalHeight;
                if (!customProps.width || !customProps.height) {
                    let w = 160;
                    let h = Math.round(w / ratio);
                    if (h > 90) {
                        h = 90;
                        w = Math.round(h * ratio);
                    }
                    if (w > 260) {
                        w = 260;
                        h = Math.round(w / ratio);
                    }
                    newSigItem.width = w;
                    newSigItem.height = h;
                    newSigItem.scaleX = w / img.naturalWidth;
                    newSigItem.scaleY = h / img.naturalHeight;
                    this.state.placement.width = w;
                    this.state.placement.height = h;
                    this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
                }
            }
        };

        if (img.complete && img.naturalWidth) {
            applyProportions();
        } else {
            img.onload = applyProportions;
        }

        this.state.signature.activeSignaturesOnDoc.push(newSigItem);
        this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
        return newSigItem;
    }


    // Text boxes live in the same list as signature images (type: "text"), so they share
    // selection, undo/redo, z-order, page targeting and the position inspector.
    addTextToDoc(customProps = {}) {
        this.recordStateSnapshot();
        const items = this.state.signature.activeSignaturesOnDoc;
        const maxZ = items.length > 0 ? Math.max(...items.map(s => s.zIndex || 1)) + 1 : 1;

        const newTextItem = {
            id: "text_doc_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
            type: "text",
            text: "Your text",
            fontFamily: "helvetica",
            fontSize: 16,
            bold: false,
            italic: false,
            color: "#000000",
            page: this.state.document.currentPage || 1,
            x: 50,
            y: 50,
            width: 0,
            height: 0,
            rotation: 0,
            opacity: 1.0,
            zIndex: maxZ,
            locked: false,
            confirmed: false,
            ...customProps
        };

        items.push(newTextItem);
        this.emit("signatures:doc_updated", items);
        return newTextItem;
    }

    updateSignatureOnDoc(id, newProps, recordHistory = false) {
        if (recordHistory) {
            this.recordStateSnapshot();
        }
        const sig = this.state.signature.activeSignaturesOnDoc.find(s => s.id === id);
        if (sig) {
            Object.assign(sig, newProps);
            if (sig.origWidth && sig.width) sig.scaleX = sig.width / sig.origWidth;
            if (sig.origHeight && sig.height) sig.scaleY = sig.height / sig.origHeight;
            // Sync placement if active
            this.state.placement.x = sig.x;
            this.state.placement.y = sig.y;
            this.state.placement.width = sig.width;
            this.state.placement.height = sig.height;
            this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
        }
    }

    confirmSignatureOnDoc(id) {
        this.recordStateSnapshot();
        const sig = this.state.signature.activeSignaturesOnDoc.find(s => s.id === id);
        if (sig) {
            sig.confirmed = true;
            this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
            this.emit("signature:confirmed", sig);
        }
    }

    // Copies a placed item (image or text) onto the same page, nudged down-right and on top.
    duplicateSignatureOnDoc(id) {
        const items = this.state.signature.activeSignaturesOnDoc;
        const src = items.find(s => s.id === id);
        if (!src) return null;
        this.recordStateSnapshot();
        const maxZ = Math.max(...items.map(s => s.zIndex || 1)) + 1;
        const prefix = src.type === "text" ? "text_doc_" : "sig_doc_";
        const copy = {
            ...src,
            id: prefix + Date.now() + "_" + Math.floor(Math.random() * 1000),
            x: src.x + 12,
            y: src.y + 12,
            zIndex: maxZ,
            confirmed: false
        };
        items.push(copy);
        this.emit("signatures:doc_updated", items);
        return copy;
    }

    // "front" / "back": renumbers every item's zIndex 1..n so the target ends up top or bottom.
    reorderSignatureOnDoc(id, where) {
        const items = this.state.signature.activeSignaturesOnDoc;
        const target = items.find(s => s.id === id);
        if (!target) return;
        this.recordStateSnapshot();
        const others = items.filter(s => s.id !== id).sort((a, b) => (a.zIndex || 1) - (b.zIndex || 1));
        const ordered = where === "back" ? [target, ...others] : [...others, target];
        ordered.forEach((s, i) => { s.zIndex = i + 1; });
        this.emit("signatures:doc_updated", items);
    }

    removeSignatureFromDoc(id) {
        this.recordStateSnapshot();
        this.state.signature.activeSignaturesOnDoc = this.state.signature.activeSignaturesOnDoc.filter(s => s.id !== id);
        this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
    }

    async saveSignatureToLibrary(dataUrl, title = "Handwritten Signature") {
        if (!dataUrl) return null;

        // Prevent duplicate signatures if identical dataUrl already exists in library tray
        const existingSig = this.state.signature.savedSignatures.find(s => s.dataUrl === dataUrl);
        if (existingSig) {
            this.setActiveSignature(existingSig.dataUrl);
            return existingSig;
        }

        const newSig = {
            id: "sig_" + Date.now(),
            dataUrl: dataUrl,
            createdAt: new Date().toISOString(),
            title: title
        };
        
        this.state.signature.savedSignatures.unshift(newSig);
        if (this.state.signature.savedSignatures.length > 15) {
            this.state.signature.savedSignatures.pop();
        }
        
        this.emit("signature:library_updated", this.state.signature.savedSignatures);
        await this.persistSignatureToIDB(newSig);
        this.setActiveSignature(dataUrl);
        return newSig;
    }


    async deleteSignatureFromLibrary(id) {
        this.state.signature.savedSignatures = this.state.signature.savedSignatures.filter(s => s.id !== id);
        if (this.state.signature.activeDataUrl && !this.state.signature.savedSignatures.some(s => s.dataUrl === this.state.signature.activeDataUrl)) {
            this.state.signature.activeDataUrl = this.state.signature.savedSignatures[0]?.dataUrl || null;
        }
        this.emit("signature:library_updated", this.state.signature.savedSignatures);
        await this.removeSignatureFromIDB(id);
    }

    reorderSignaturesInLibrary(fromIndex, toIndex) {
        const list = this.state.signature.savedSignatures;
        if (fromIndex < 0 || fromIndex >= list.length || toIndex < 0 || toIndex >= list.length || fromIndex === toIndex) return;
        const [movedItem] = list.splice(fromIndex, 1);
        list.splice(toIndex, 0, movedItem);
        this.emit("signature:library_updated", this.state.signature.savedSignatures);
    }

    // --- History Snapshots & Placement/Transform Undo/Redo Logic ---
    recordStateSnapshot() {
        const snapshot = {
            placement: { ...this.state.placement },
            activeSignaturesOnDoc: JSON.parse(JSON.stringify(this.state.signature.activeSignaturesOnDoc))
        };
        this.state.history.undoStack.push(snapshot);
        this.state.history.redoStack = []; // clear redo on new action
        if (this.state.history.undoStack.length > 30) {
            this.state.history.undoStack.shift();
        }
        this.emit("placement:updated", {
            placement: this.state.placement,
            canUndo: this.state.history.undoStack.length > 0,
            canRedo: this.state.history.redoStack.length > 0
        });
    }

    setPlacement(newPos, recordHistory = true) {
        if (recordHistory) {
            this.recordStateSnapshot();
        }
        this.state.placement = { ...this.state.placement, ...newPos };
        this.emit("placement:updated", {
            placement: this.state.placement,
            canUndo: this.state.history.undoStack.length > 0,
            canRedo: this.state.history.redoStack.length > 0
        });
    }

    undoPlacement() {
        if (this.state.history.undoStack.length > 0) {
            const currentSnapshot = {
                placement: { ...this.state.placement },
                activeSignaturesOnDoc: JSON.parse(JSON.stringify(this.state.signature.activeSignaturesOnDoc))
            };
            const prevSnapshot = this.state.history.undoStack.pop();
            this.state.history.redoStack.push(currentSnapshot);

            this.state.placement = prevSnapshot.placement;
            this.state.signature.activeSignaturesOnDoc = prevSnapshot.activeSignaturesOnDoc;

            this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
            this.emit("placement:updated", {
                placement: this.state.placement,
                canUndo: this.state.history.undoStack.length > 0,
                canRedo: this.state.history.redoStack.length > 0
            });
        }
    }

    redoPlacement() {
        if (this.state.history.redoStack.length > 0) {
            const currentSnapshot = {
                placement: { ...this.state.placement },
                activeSignaturesOnDoc: JSON.parse(JSON.stringify(this.state.signature.activeSignaturesOnDoc))
            };
            const nextSnapshot = this.state.history.redoStack.pop();
            this.state.history.undoStack.push(currentSnapshot);

            this.state.placement = nextSnapshot.placement;
            this.state.signature.activeSignaturesOnDoc = nextSnapshot.activeSignaturesOnDoc;

            this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
            this.emit("placement:updated", {
                placement: this.state.placement,
                canUndo: this.state.history.undoStack.length > 0,
                canRedo: this.state.history.redoStack.length > 0
            });
        }
    }

    // --- IndexedDB Persistent Storage ---
    initIndexedDB() {
        if (!window.indexedDB) return;
        const request = indexedDB.open("PDFStudioDB", 1);
        
        request.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains("signatures")) {
                db.createObjectStore("signatures", { keyPath: "id" });
            }
        };

        request.onsuccess = (e) => {
            this.db = e.target.result;
            this.loadSignaturesFromIDB();
        };
    }

    async persistSignatureToIDB(sigObj) {
        if (!this.db) return;
        const tx = this.db.transaction("signatures", "readwrite");
        const store = tx.objectStore("signatures");
        store.put(sigObj);
    }

    async removeSignatureFromIDB(id) {
        if (!this.db) return;
        const tx = this.db.transaction("signatures", "readwrite");
        const store = tx.objectStore("signatures");
        store.delete(id);
    }


    async loadSignaturesFromIDB() {
        if (!this.db) return;
        const tx = this.db.transaction("signatures", "readonly");
        const store = tx.objectStore("signatures");
        const req = store.getAll();
        
        req.onsuccess = () => {
            if (req.result && req.result.length > 0) {
                const sorted = req.result.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
                this.state.signature.savedSignatures = sorted;
                if (!this.state.signature.activeDataUrl && sorted[0]) {
                    this.setActiveSignature(sorted[0].dataUrl);
                }
                this.emit("signature:library_updated", sorted);
            }
        };
    }
}

// Global Store Instance
window.appStore = new PDFStudioStore();

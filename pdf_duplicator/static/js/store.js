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

    // --- Signature Management & Storage ---
    setActiveSignature(dataUrl) {
        this.state.signature.activeDataUrl = dataUrl;
        this.emit("signature:active", dataUrl);

        // Automatically add to document stage if document is loaded
        if (this.state.document.fileId || this.state.document.fileObj) {
            this.addSignatureToDoc(dataUrl);
        }
    }

    addSignatureToDoc(dataUrl, customProps = {}) {
        const docPage = this.state.document.currentPage || 1;
        const existingCount = this.state.signature.activeSignaturesOnDoc.length;
        const offsetX = (existingCount % 6) * 35;
        const offsetY = (existingCount % 6) * 30;

        const baseX = customProps.x || this.state.placement.x || 50;
        const baseY = customProps.y || this.state.placement.y || 50;

        const newSigItem = {
            id: "sig_doc_" + Date.now() + "_" + Math.floor(Math.random() * 1000),
            dataUrl: dataUrl,
            page: docPage,
            x: baseX + (customProps.x ? 0 : offsetX),
            y: baseY + (customProps.y ? 0 : offsetY),
            width: customProps.width || this.state.placement.width || 150,
            height: customProps.height || this.state.placement.height || 60,
            confirmed: false
        };

        this.state.signature.activeSignaturesOnDoc.push(newSigItem);
        this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
        return newSigItem;
    }


    updateSignatureOnDoc(id, newProps) {
        const sig = this.state.signature.activeSignaturesOnDoc.find(s => s.id === id);
        if (sig) {
            Object.assign(sig, newProps);
            // Sync placement if active
            this.state.placement.x = sig.x;
            this.state.placement.y = sig.y;
            this.state.placement.width = sig.width;
            this.state.placement.height = sig.height;
            this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
        }
    }

    confirmSignatureOnDoc(id) {
        const sig = this.state.signature.activeSignaturesOnDoc.find(s => s.id === id);
        if (sig) {
            sig.confirmed = true;
            this.emit("signatures:doc_updated", this.state.signature.activeSignaturesOnDoc);
            this.emit("signature:confirmed", sig);
        }
    }

    removeSignatureFromDoc(id) {
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




    // --- Placement & Undo/Redo Logic ---
    setPlacement(newPos, recordHistory = true) {
        const prevPos = { ...this.state.placement };
        
        if (recordHistory) {
            this.state.history.undoStack.push(prevPos);
            this.state.history.redoStack = []; // clear redo on new action
            if (this.state.history.undoStack.length > 30) {
                this.state.history.undoStack.shift();
            }
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
            const currentPos = { ...this.state.placement };
            const prevPos = this.state.history.undoStack.pop();
            this.state.history.redoStack.push(currentPos);

            this.state.placement = prevPos;
            this.emit("placement:updated", {
                placement: this.state.placement,
                canUndo: this.state.history.undoStack.length > 0,
                canRedo: this.state.history.redoStack.length > 0
            });
        }
    }

    redoPlacement() {
        if (this.state.history.redoStack.length > 0) {
            const currentPos = { ...this.state.placement };
            const nextPos = this.state.history.redoStack.pop();
            this.state.history.undoStack.push(currentPos);

            this.state.placement = nextPos;
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

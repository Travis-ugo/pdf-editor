// Hover tooltips for every button that has a `title`.
//
// The browser's own title tooltip waits about a second, is tiny and never shows on keyboard
// focus, so customers didn't discover what the tools do. This takes over: on hover (or keyboard
// focus) it shows a styled tooltip after a short delay, built from the existing `title` text:
//
//   "Pen: draw or write on the page (P)"  ->  **Pen**  draw or write on the page  [P]
//
// The title is moved to data-tip while hovered so the native tooltip doesn't double up, and put
// back on leave, so code that reads or rewrites `title` keeps working.
(function () {
    "use strict";

    const SHOW_DELAY = 350;       // first tooltip
    const SWITCH_DELAY = 60;      // moving along a toolbar while one is already showing
    const GAP = 8;
    const SELECTOR = "button[title], label[title], .rail-btn[title], [data-tip]";

    const tip = document.createElement("div");
    tip.className = "ui-tooltip";
    tip.setAttribute("role", "tooltip");
    tip.id = "uiTooltip";
    document.addEventListener("DOMContentLoaded", () => document.body.appendChild(tip));

    let target = null;
    let showTimer = null;
    let hideTimer = null;
    let visible = false;

    function textFor(el) {
        if (el.hasAttribute("title")) {
            const t = el.getAttribute("title");
            if (!el.hasAttribute("aria-label") && !el.textContent.trim()) el.setAttribute("aria-label", t);
            el.dataset.tipFromTitle = "1";
            el.dataset.tip = t;
            el.removeAttribute("title");
        }
        return el.dataset.tip || "";
    }

    function restoreTitle(el) {
        if (el && el.dataset.tipFromTitle && !el.hasAttribute("title")) {
            el.setAttribute("title", el.dataset.tip);
        }
    }

    // "Name: what it does (Shortcut)" -> parts. A trailing "(…)" is a shortcut only when it
    // looks like one (short, or starts with a single key) so "(pt)" style notes stay as text.
    function render(text) {
        let name = text, desc = "", key = "";
        const m = text.match(/\s*\(([^()]{1,40})\)\s*$/);
        if (m && (/^(⌘|⇧|⌥|Esc|Space|[A-Z0-9])([\s,+⌘⇧⌥A-Z]|$)/.test(m[1]))) {
            key = m[1];
            name = text.slice(0, m.index);
        }
        const colon = name.indexOf(": ");
        if (colon > 0 && colon < 30) {
            desc = name.slice(colon + 2);
            name = name.slice(0, colon);
        }
        tip.replaceChildren();
        const title = document.createElement("span");
        title.className = "ui-tooltip-title";
        title.textContent = name;
        tip.appendChild(title);
        if (key) {
            const k = document.createElement("kbd");
            k.textContent = key;
            title.appendChild(k);
        }
        if (desc) {
            const d = document.createElement("span");
            d.className = "ui-tooltip-desc";
            d.textContent = desc.charAt(0).toUpperCase() + desc.slice(1);
            tip.appendChild(d);
        }
    }

    function place(el) {
        const r = el.getBoundingClientRect();
        const t = tip.getBoundingClientRect();
        const vw = document.documentElement.clientWidth;
        const vh = document.documentElement.clientHeight;
        let side;
        let x, y;
        // The left rail: to the right of the button. Everything else: above, flipping below.
        if (el.closest(".tool-rail") && r.right + GAP + t.width < vw) {
            side = "right";
            x = r.right + GAP;
            y = r.top + r.height / 2 - t.height / 2;
        } else if (r.top - GAP - t.height >= 4) {
            side = "top";
            x = r.left + r.width / 2 - t.width / 2;
            y = r.top - GAP - t.height;
        } else {
            side = "bottom";
            x = r.left + r.width / 2 - t.width / 2;
            y = r.bottom + GAP;
        }
        x = Math.max(8, Math.min(x, vw - t.width - 8));
        y = Math.max(4, Math.min(y, vh - t.height - 4));
        tip.dataset.side = side;
        tip.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
    }

    function show(el) {
        const text = textFor(el);
        if (!text || !el.isConnected) return;
        render(text);
        tip.classList.add("visible");
        visible = true;
        place(el);
        el.setAttribute("aria-describedby", tip.id);
    }

    function hide() {
        clearTimeout(showTimer);
        tip.classList.remove("visible");
        visible = false;
        if (target) {
            if (target.getAttribute("aria-describedby") === tip.id) target.removeAttribute("aria-describedby");
            restoreTitle(target);
        }
        target = null;
    }

    function enter(el) {
        if (el === target) return;
        clearTimeout(hideTimer);
        clearTimeout(showTimer);
        const wasVisible = visible;
        if (target) restoreTitle(target);
        target = el;
        textFor(el);  // take the title now so the native tooltip never starts
        showTimer = setTimeout(() => { if (target === el) show(el); }, wasVisible ? SWITCH_DELAY : SHOW_DELAY);
    }

    function leave() {
        clearTimeout(showTimer);
        // A short grace period lets the pointer move to a neighbouring tool without flicker.
        hideTimer = setTimeout(hide, 80);
    }

    document.addEventListener("pointerover", (e) => {
        if (e.pointerType === "touch") return;  // touch has no hover; a tap would leave it stuck
        const el = e.target.closest && e.target.closest(SELECTOR);
        if (el) enter(el);
        else if (target) leave();
    });
    document.addEventListener("pointerout", (e) => {
        if (!target) return;
        const to = e.relatedTarget;
        if (!to || !target.contains(to)) leave();
    });

    // Keyboard users get the same help when tabbing onto a tool.
    document.addEventListener("focusin", (e) => {
        const el = e.target.closest && e.target.closest(SELECTOR);
        if (el && el.matches(":focus-visible")) enter(el);
    });
    document.addEventListener("focusout", () => { if (target) leave(); });

    // Clicking, typing, scrolling or resizing dismisses it; the button may move or change.
    document.addEventListener("pointerdown", hide, true);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" || visible) hide(); }, true);
    window.addEventListener("scroll", hide, true);
    window.addEventListener("resize", hide);
    window.addEventListener("blur", hide);
})();

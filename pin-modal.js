// Shared masked-PIN prompt, used anywhere the app needs to collect the
// Owner PIN (or any other PIN) from someone standing at a shared device.
//
// window.prompt() cannot be masked — whatever is typed into it is shown in
// plain text on screen, which is a problem for a PIN that unlocks/locks a
// day or unlocks a closed shift in front of other staff. askPin() renders a
// small modal with a real <input type="password"> instead, so the digits
// are hidden as they're typed, same as a normal password field.
//
// Usage: const pin = await askPin("Owner PIN to lock this day:");
//        if (!pin) return; // cancelled
//
// Injects its own markup/styles into the page on first use, so a page just
// needs this script included — no extra HTML or CSS required.
function askPin(title) {
  return new Promise((resolve) => {
    let overlay = document.getElementById("pin-modal-overlay");
    if (!overlay) {
      const style = document.createElement("style");
      style.textContent = `
        #pin-modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:9999; display:flex; align-items:center; justify-content:center; padding:16px; box-sizing:border-box; }
        #pin-modal-box { background:#fff; border-radius:12px; padding:20px; width:100%; max-width:300px; box-shadow:0 10px 30px rgba(0,0,0,0.25); font-family:inherit; box-sizing:border-box; }
        #pin-modal-title { font-weight:600; margin-bottom:12px; font-size:15px; color:#222; }
        #pin-modal-input { width:100%; box-sizing:border-box; padding:10px 12px; font-size:20px; letter-spacing:6px; text-align:center; border:1px solid #ccc; border-radius:8px; }
        #pin-modal-error { color:#c0392b; font-size:12px; margin-top:8px; min-height:14px; }
        #pin-modal-actions { display:flex; gap:8px; margin-top:14px; }
        #pin-modal-actions button { flex:1; padding:10px; border-radius:8px; border:none; font-size:14px; cursor:pointer; }
        #pin-modal-ok { background:#b5542a; color:#fff; }
        #pin-modal-cancel { background:#eee; color:#333; }
      `;
      document.head.appendChild(style);

      overlay = document.createElement("div");
      overlay.id = "pin-modal-overlay";
      overlay.hidden = true;
      overlay.innerHTML = `
        <div id="pin-modal-box">
          <div id="pin-modal-title"></div>
          <input type="password" id="pin-modal-input" inputmode="numeric" autocomplete="off">
          <div id="pin-modal-error"></div>
          <div id="pin-modal-actions">
            <button type="button" id="pin-modal-cancel">Cancel</button>
            <button type="button" id="pin-modal-ok">OK</button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
    }

    const titleEl = document.getElementById("pin-modal-title");
    const input = document.getElementById("pin-modal-input");
    const errEl = document.getElementById("pin-modal-error");
    const okBtn = document.getElementById("pin-modal-ok");
    const cancelBtn = document.getElementById("pin-modal-cancel");

    titleEl.textContent = title || "Enter PIN:";
    input.value = "";
    errEl.textContent = "";
    overlay.hidden = false;
    setTimeout(() => input.focus(), 30);

    function cleanup(result) {
      overlay.hidden = true;
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
      input.removeEventListener("keydown", onKey);
      overlay.removeEventListener("click", onOverlayClick);
      resolve(result);
    }
    function onOk() {
      const v = input.value.trim();
      if (!v) { errEl.textContent = "Enter a PIN."; return; }
      cleanup(v);
    }
    function onCancel() { cleanup(null); }
    function onKey(e) {
      if (e.key === "Enter") onOk();
      if (e.key === "Escape") onCancel();
    }
    function onOverlayClick(e) { if (e.target === overlay) onCancel(); }

    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
    input.addEventListener("keydown", onKey);
    overlay.addEventListener("click", onOverlayClick);
  });
}

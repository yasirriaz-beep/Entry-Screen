// Shared per-visit login session, used by home.html (the single login +
// tabs launcher) and every entry screen.
//
// Deliberately sessionStorage, not localStorage: it survives navigating
// between pages in the same tab/visit, but clears the moment the browser (or
// tab) is closed — so a shared/unlocked device doesn't stay "logged in" as
// whoever used it last. See reference/ACCESS_CONTROL_AND_PIN_SYSTEM.md.
//
// Session shape: { managerId, userId, userName, role, pages: string[], loginAt }
// `pages` is the list of page_keys this manager is granted (from
// list_pages_for_manager). Directors get access to everything regardless of
// what's in `pages` - see hasAccess().

const FNK_SESSION_KEY = "fnk_session_v1";

const FNKSession = {
  get() {
    try {
      const raw = sessionStorage.getItem(FNK_SESSION_KEY);
      if (!raw) return null;
      const session = JSON.parse(raw);
      if (!session || !session.userId || !session.managerId) return null;
      return session;
    } catch (e) {
      return null;
    }
  },

  set(session) {
    try {
      sessionStorage.setItem(FNK_SESSION_KEY, JSON.stringify(session));
    } catch (e) {
      /* sessionStorage unavailable (private mode, etc.) - caller falls back to per-page login */
    }
  },

  clear() {
    try {
      sessionStorage.removeItem(FNK_SESSION_KEY);
    } catch (e) {
      /* no-op */
    }
  },

  // Directors see and can open every screen, same as the old role-select
  // flow; everyone else is limited to the page_keys granted to them.
  hasAccess(session, pageKey) {
    if (!session) return false;
    if (session.role === "director") return true;
    return Array.isArray(session.pages) && session.pages.includes(pageKey);
  },

  // View-only access (set per person, per page, in Manage Access): the
  // person can open and see the page, but can't save anything on it.
  // Directors are never view-only - this is for people granted access to a
  // specific screen in a look-but-don't-touch capacity (e.g. an auditor
  // reviewing Stock Count without being able to log a count).
  // `session.viewOnlyPages` is the subset of `session.pages` that's
  // view-only; built at login time from list_pages_for_manager_v2.
  isViewOnly(session, pageKey) {
    if (!session || session.role === "director") return false;
    return Array.isArray(session.viewOnlyPages) && session.viewOnlyPages.includes(pageKey);
  },

  // Locks every input/select/textarea/button on the page so nothing can be
  // saved, and shows a banner saying why. Call once, right after login
  // succeeds (both the fresh-login and the auto-login-from-session paths).
  // Deliberately blunt - it disables ALL buttons, including any date-range
  // or tab filters a page might have, not just "Save" - the alternative
  // (guessing which buttons are "safe" per page) risked leaving a real save
  // path open on some screen. A view-only person can still read everything
  // on the page; they just can't click anything on it.
  applyAccessLock(session, pageKey) {
    if (!FNKSession.isViewOnly(session, pageKey)) return;
    if (document.getElementById("fnk-view-only-banner")) return; // already applied
    const loginBox = document.getElementById("step-name") || document.getElementById("step-login") || document.getElementById("whoCard");
    document.querySelectorAll("input, select, textarea, button").forEach((el) => {
      if (loginBox && loginBox.contains(el)) return;
      el.disabled = true;
    });
    const banner = document.createElement("div");
    banner.id = "fnk-view-only-banner";
    banner.textContent = "View-only access — you can review this page, but changes can't be saved here.";
    banner.style.cssText = "background:#fdf1dd;color:#a3650a;border:1px solid #a3650a;border-radius:10px;padding:10px 12px;font-size:0.85rem;margin:0 0 14px;font-family:system-ui,sans-serif;";
    document.body.insertBefore(banner, document.body.firstChild);
  },
};

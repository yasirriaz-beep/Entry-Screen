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
};

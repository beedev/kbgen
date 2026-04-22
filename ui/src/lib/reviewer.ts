// Reviewer identity — stored in localStorage.kbgen.reviewer, prompted once
// per browser. Deliberately lightweight; real auth arrives when the service
// is fronted by Keycloak (see README § Production hardening).

const KEY = 'kbgen.reviewer';

export function getReviewer(): string | null {
  if (typeof window === 'undefined') return null;
  const v = localStorage.getItem(KEY);
  return v && v.trim() ? v.trim() : null;
}

export function setReviewer(name: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(KEY, name.trim());
}

export function clearReviewer(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(KEY);
}

/**
 * Ensure a reviewer identity is set. If none, prompt. Returns the name or
 * null if the user cancelled (in which case the caller should abort the
 * action — we never push anonymously).
 */
export function ensureReviewer(): string | null {
  const existing = getReviewer();
  if (existing) return existing;
  const entered = window.prompt(
    'Reviewer name\n\nYour name or email is attached to every draft you approve, ' +
      'reject, or push — so the audit trail shows who did what. You can change it ' +
      'later in the sidebar footer.',
    '',
  );
  if (!entered || !entered.trim()) return null;
  setReviewer(entered.trim());
  return entered.trim();
}

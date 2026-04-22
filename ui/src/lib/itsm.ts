// Helpers to produce clickable URLs into the ITSM's web UI.
//
// Right now only GLPI is wired. kbgen knows the ITSM's REST URL but not its
// web URL, so we derive by swapping /apirest.php → / and mapping port 8004 →
// 9080 for same-host demos. If that derivation is wrong for your deploy, set
// `window.__KBGEN_ITSM_WEB_URL__ = 'https://glpi.corp'` before the SPA loads.

declare global {
  interface Window {
    __KBGEN_ITSM_WEB_URL__?: string;
  }
}

function itsmWebBase(): string {
  if (typeof window === 'undefined') return '';
  if (window.__KBGEN_ITSM_WEB_URL__) return window.__KBGEN_ITSM_WEB_URL__.replace(/\/$/, '');
  // Same-host demo: kbgen at :8004, bundled GLPI at :9080.
  const host = window.location.hostname || 'localhost';
  return `http://${host}:9080`;
}

export function itsmKbUrl(kbId: string | number | null | undefined): string | null {
  if (kbId == null || kbId === '') return null;
  return `${itsmWebBase()}/front/knowbaseitem.form.php?id=${kbId}`;
}

export function itsmKbListUrl(): string {
  return `${itsmWebBase()}/front/knowbaseitem.php?reset=reset`;
}

export function itsmTicketUrl(ticketId: string | number): string {
  return `${itsmWebBase()}/front/ticket.form.php?id=${ticketId}`;
}

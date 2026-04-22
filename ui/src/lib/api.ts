// Thin fetch wrapper for calling kbgen's REST API. All kb endpoints live
// under /api/kb/*; the health check under /api/health.
//
// When kbgen is reverse-proxied at a non-root path (e.g. `/kbgen/`),
// Vite bakes `import.meta.env.BASE_URL` (e.g. `/kbgen/`) into the bundle at
// build time. We prepend that base to API calls so they hit the proxy-
// rewritten route. At root, BASE_URL === "/" and the prefix reduces to "".

const BASE = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '');

function qsPart(params: Record<string, unknown> | undefined): string {
  if (!params) return '';
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') usp.append(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : '';
}

export async function api<T>(
  path: string,
  opts: RequestInit & { params?: Record<string, unknown> } = {},
): Promise<T> {
  const { params, ...rest } = opts;
  const r = await fetch(`${BASE}/api/kb${path}${qsPart(params)}`, {
    headers: { 'Content-Type': 'application/json', ...(rest.headers ?? {}) },
    ...rest,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`${r.status} ${r.statusText}: ${text.slice(0, 200)}`);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export async function pingHealth(): Promise<unknown> {
  const r = await fetch(`${BASE}/api/health`);
  return r.ok ? r.json() : null;
}

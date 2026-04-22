"""GLPI REST adapter.

Auth:
  * Preferred: `App-Token` + `Authorization: user_token <t>` if both configured.
  * Fallback: Basic auth with `GLPI_USER` / `GLPI_PASSWORD` (or the defaults
    `glpi:glpi` on a fresh install) so local dev works out of the box.

Session lifecycle: each adapter call opens a session, runs the request, and
kills the session. GLPI also supports long-lived sessions, but the per-call
form is the safest default for a service that only polls every 60s.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from datetime import datetime

import httpx

from src.itsm.base import ITSMAdapter, ItsmKbArticle, KbSearchResult
from src.schemas.ticket import ConversationEntry, Ticket

log = logging.getLogger(__name__)


# GLPI Ticket statuses: 1=new, 2=processing(assigned), 3=processing(planned),
# 4=pending, 5=solved, 6=closed. We consider 5 & 6 "resolved".
_RESOLVED_STATUSES = {5, 6}


def _strip_html(s: str | None) -> str:
    if not s:
        return ""
    # Ultra-light HTML → text. GLPI often stores rich text; for indexing + prompt
    # input we only care about the words.
    no_tags = re.sub(r"<[^>]+>", " ", s)
    no_entities = re.sub(r"&nbsp;|&#160;", " ", no_tags)
    return re.sub(r"\s+", " ", no_entities).strip()


def _parse_dt(v) -> datetime | None:
    if not v or v in ("0000-00-00 00:00:00",):
        return None
    try:
        dt = datetime.fromisoformat(v.replace(" ", "T"))
    except (TypeError, ValueError):
        return None
    # GLPI returns naive local-time strings; treat them as UTC so downstream
    # arithmetic against `datetime.now(timezone.utc)` doesn't explode.
    from datetime import timezone as _tz  # noqa: local to keep top imports clean
    return dt if dt.tzinfo else dt.replace(tzinfo=_tz.utc)


class GLPIAdapter(ITSMAdapter):
    name = "glpi"

    def __init__(
        self,
        base_url: str,
        app_token: str | None = None,
        user_token: str | None = None,
        basic_user: str | None = None,
        basic_password: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.app_token = app_token or None
        self.user_token = user_token or None
        self.basic_user = basic_user or os.getenv("GLPI_USER") or "glpi"
        self.basic_password = basic_password or os.getenv("GLPI_PASSWORD") or "glpi"
        self._timeout = timeout
        # Name → ITILCategory id cache. Populated lazily by
        # `_ensure_category_id`; avoids re-listing /ITILCategory on every
        # seeded ticket in a burst.
        self._cat_cache: dict[str, int] = {}

    # ── auth helpers ────────────────────────────────────────────────────────
    def _auth_headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.app_token:
            h["App-Token"] = self.app_token
        if self.user_token:
            h["Authorization"] = f"user_token {self.user_token}"
        else:
            creds = base64.b64encode(f"{self.basic_user}:{self.basic_password}".encode()).decode()
            h["Authorization"] = f"Basic {creds}"
        return h

    async def _init_session(self, client: httpx.AsyncClient) -> str:
        r = await client.get(f"{self.base_url}/initSession", headers=self._auth_headers())
        r.raise_for_status()
        return r.json()["session_token"]

    async def _kill_session(self, client: httpx.AsyncClient, token: str) -> None:
        try:
            await client.get(f"{self.base_url}/killSession", headers=self._session_headers(token))
        except Exception:
            pass  # non-fatal on teardown

    def _session_headers(self, token: str) -> dict[str, str]:
        h = {"Session-Token": token, "Content-Type": "application/json"}
        if self.app_token:
            h["App-Token"] = self.app_token
        return h

    # ── ITSMAdapter surface ─────────────────────────────────────────────────
    async def test_connection(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                token = await self._init_session(client)
                await self._kill_session(client, token)
            return True, f"connected to {self.base_url}"
        except Exception as exc:
            return False, f"{exc.__class__.__name__}: {exc}"

    async def list_resolved_tickets(self, since: datetime | None = None) -> list[Ticket]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._init_session(client)
            try:
                params = {"range": "0-199", "expand_dropdowns": "true"}
                r = await client.get(
                    f"{self.base_url}/Ticket",
                    headers=self._session_headers(token),
                    params=params,
                )
                r.raise_for_status()
                rows = r.json() or []

                out: list[Ticket] = []
                for row in rows:
                    status = int(row.get("status", 0) or 0)
                    if status not in _RESOLVED_STATUSES:
                        continue
                    resolved_at = _parse_dt(row.get("solvedate")) or _parse_dt(row.get("closedate"))
                    if since and resolved_at and resolved_at < since:
                        continue
                    ticket = await self._hydrate_ticket(client, token, row)
                    out.append(ticket)
                return out
            finally:
                await self._kill_session(client, token)

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._init_session(client)
            try:
                r = await client.get(
                    f"{self.base_url}/Ticket/{ticket_id}",
                    headers=self._session_headers(token),
                    params={"expand_dropdowns": "true"},
                )
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return await self._hydrate_ticket(client, token, r.json())
            finally:
                await self._kill_session(client, token)

    async def _hydrate_ticket(self, client: httpx.AsyncClient, token: str, row: dict) -> Ticket:
        ticket_id = str(row["id"])
        # Solution (ITILSolution) + followups (ITILFollowup) are the richest
        # resolution signal. Cheap to fetch; we just take the first/latest.
        solution_text = ""
        try:
            sol = await client.get(
                f"{self.base_url}/Ticket/{ticket_id}/ITILSolution",
                headers=self._session_headers(token),
            )
            if sol.status_code == 200:
                sols = sol.json() or []
                if sols:
                    solution_text = _strip_html(sols[-1].get("content", ""))
        except Exception:
            pass

        conversation: list[ConversationEntry] = []
        try:
            fu = await client.get(
                f"{self.base_url}/Ticket/{ticket_id}/ITILFollowup",
                headers=self._session_headers(token),
            )
            if fu.status_code == 200:
                for entry in (fu.json() or [])[:20]:
                    conversation.append(
                        ConversationEntry(
                            author=str(entry.get("users_id") or "glpi"),
                            body=_strip_html(entry.get("content", "")),
                            timestamp=_parse_dt(entry.get("date")),
                        )
                    )
        except Exception:
            pass

        category = row.get("itilcategories_id")
        if isinstance(category, dict):
            category = category.get("name")

        return Ticket(
            itsm_ticket_id=ticket_id,
            itsm_provider=self.name,
            title=row.get("name", "") or "",
            description=_strip_html(row.get("content", "")),
            conversation=conversation,
            resolution=solution_text,
            topic=category if isinstance(category, str) else None,
            tags=[],
            resolved_at=_parse_dt(row.get("solvedate")) or _parse_dt(row.get("closedate")),
        )

    async def search_kb(self, query: str, limit: int = 5) -> list[KbSearchResult]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._init_session(client)
            try:
                # GLPI's native full-text search over KnowbaseItem.
                params = {
                    "criteria[0][field]": "6",  # name
                    "criteria[0][searchtype]": "contains",
                    "criteria[0][value]": query,
                    "range": f"0-{max(0, limit - 1)}",
                }
                r = await client.get(
                    f"{self.base_url}/search/KnowbaseItem",
                    headers=self._session_headers(token),
                    params=params,
                )
                if r.status_code == 400:
                    return []
                r.raise_for_status()
                payload = r.json() or {}
                rows = payload.get("data") or []
                return [
                    KbSearchResult(
                        itsm_kb_id=str(row.get("2") or row.get("id") or ""),
                        title=str(row.get("6") or row.get("name") or ""),
                        snippet=_strip_html(str(row.get("1") or ""))[:240],
                        score=None,
                    )
                    for row in rows
                    if (row.get("2") or row.get("id"))
                ]
            finally:
                await self._kill_session(client, token)

    async def list_kb_articles(self, since: datetime | None = None) -> list[ItsmKbArticle]:
        out: list[ItsmKbArticle] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._init_session(client)
            try:
                r = await client.get(
                    f"{self.base_url}/KnowbaseItem",
                    headers=self._session_headers(token),
                    params={"range": "0-499", "expand_dropdowns": "true"},
                )
                r.raise_for_status()
                for row in r.json() or []:
                    updated = _parse_dt(row.get("date_mod"))
                    if since and updated and updated < since:
                        continue
                    out.append(
                        ItsmKbArticle(
                            itsm_kb_id=str(row["id"]),
                            title=row.get("name") or "",
                            body=_strip_html(row.get("answer", "")),
                            category=(
                                row.get("knowbaseitemcategories_id")
                                if isinstance(row.get("knowbaseitemcategories_id"), str)
                                else None
                            ),
                            tags=[],
                            created_at=_parse_dt(row.get("date_creation")),
                            updated_at=updated,
                        )
                    )
            finally:
                await self._kill_session(client, token)
        return out

    async def create_kb_draft(
        self,
        *,
        title: str,
        body: str,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        answer_html = "<p>" + body.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
        payload = {
            "input": {
                "name": title,
                "answer": answer_html,
                "is_faq": 0,
            }
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._init_session(client)
            try:
                r = await client.post(
                    f"{self.base_url}/KnowbaseItem",
                    headers=self._session_headers(token),
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list):
                    data = data[0]
                kb_id = data.get("id")
                if kb_id is None:
                    raise RuntimeError(f"GLPI create_kb_draft returned no id: {data}")
                return str(kb_id)
            finally:
                await self._kill_session(client, token)

    async def _ensure_category_id(
        self, client: httpx.AsyncClient, token: str, name: str
    ) -> int | None:
        """Resolve an ITIL category name → id, creating it in GLPI if absent.

        Mirrors `scripts/seed_glpi_healthcare._ensure_categories`. Result is
        cached on the adapter instance so a burst of demo-seeded tickets
        sharing a category only triggers one list + one create.
        """
        cached = self._cat_cache.get(name)
        if cached is not None:
            return cached
        try:
            r = await client.get(
                f"{self.base_url}/ITILCategory",
                headers=self._session_headers(token),
                params={"range": "0-499"},
            )
            r.raise_for_status()
            for c in r.json() or []:
                cid = c.get("id")
                if c.get("name") == name and cid is not None:
                    self._cat_cache[name] = int(cid)
                    return int(cid)
            rc = await client.post(
                f"{self.base_url}/ITILCategory",
                headers=self._session_headers(token),
                json={
                    "input": {
                        "name": name,
                        "is_helpdeskvisible": 1,
                        "is_request": 1,
                        "is_incident": 1,
                    }
                },
            )
            if rc.status_code >= 400:
                log.warning(
                    "GLPI create ITILCategory '%s' failed: %s %s",
                    name, rc.status_code, rc.text[:160],
                )
                return None
            data = rc.json()
            if isinstance(data, list):
                data = data[0]
            cid = data.get("id")
            if cid is None:
                return None
            self._cat_cache[name] = int(cid)
            return int(cid)
        except Exception as exc:  # network / JSON / schema drift
            log.warning("GLPI _ensure_category_id(%s) failed: %s", name, exc)
            return None

    async def create_resolved_ticket(
        self,
        *,
        title: str,
        description: str,
        resolution: str,
        category: str | None = None,
    ) -> str | None:
        """Create → post solution → close, matching scripts/seed_glpi_healthcare.

        GLPI won't let you POST a ticket directly at status=6; it has to
        walk the state machine. We do: (1) POST Ticket status=1, (2) POST
        ITILSolution which auto-moves status→5, (3) PUT status=6 with
        solvedate/closedate = now.
        """
        from datetime import timezone as _tz
        now_str = datetime.now(_tz.utc).strftime("%Y-%m-%d %H:%M:%S")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._init_session(client)
            try:
                cat_id: int | None = None
                if category:
                    cat_id = await self._ensure_category_id(client, token, category)
                ticket_input: dict = {
                    "name": title,
                    "content": f"<p>{description}</p>",
                    "status": 1,
                }
                if cat_id is not None:
                    ticket_input["itilcategories_id"] = cat_id
                payload = {"input": ticket_input}
                r = await client.post(
                    f"{self.base_url}/Ticket",
                    headers=self._session_headers(token),
                    json=payload,
                )
                if r.status_code >= 400:
                    log.warning("GLPI create Ticket failed: %s %s", r.status_code, r.text[:200])
                    return None
                data = r.json()
                if isinstance(data, list):
                    data = data[0]
                tid = data.get("id")
                if not tid:
                    return None

                sol_payload = {
                    "input": {
                        "itemtype": "Ticket",
                        "items_id": tid,
                        "content": f"<p>{resolution}</p>",
                    }
                }
                sr = await client.post(
                    f"{self.base_url}/ITILSolution",
                    headers=self._session_headers(token),
                    json=sol_payload,
                )
                if sr.status_code >= 400:
                    log.warning(
                        "GLPI post ITILSolution for ticket %s failed: %s %s",
                        tid, sr.status_code, sr.text[:200],
                    )

                close_payload = {
                    "input": {
                        "id": tid,
                        "status": 6,
                        "solvedate": now_str,
                        "closedate": now_str,
                    }
                }
                cr = await client.put(
                    f"{self.base_url}/Ticket/{tid}",
                    headers=self._session_headers(token),
                    json=close_payload,
                )
                if cr.status_code >= 400:
                    log.warning(
                        "GLPI close ticket %s failed: %s %s",
                        tid, cr.status_code, cr.text[:200],
                    )
                return str(tid)
            finally:
                await self._kill_session(client, token)

    async def link_kb_to_ticket(self, *, itsm_kb_id: str, itsm_ticket_id: str) -> bool:
        """Create a glpi_knowbaseitems_items row so the ticket's KB tab shows it.

        GLPI models ticket↔KB associations as a separate KnowbaseItem_Item
        entity. Idempotent at the API level: if the same association already
        exists GLPI returns a non-201 that we swallow.
        """
        payload = {
            "input": {
                "knowbaseitems_id": int(itsm_kb_id),
                "itemtype": "Ticket",
                "items_id": int(itsm_ticket_id),
            }
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            token = await self._init_session(client)
            try:
                r = await client.post(
                    f"{self.base_url}/KnowbaseItem_Item",
                    headers=self._session_headers(token),
                    json=payload,
                )
                if r.status_code in (200, 201):
                    return True
                # Duplicate association → GLPI responds 400/409. Treat as success.
                body_text = (r.text or "").lower()
                if r.status_code in (400, 409) and "already" in body_text:
                    return True
                log.warning(
                    "GLPI link_kb_to_ticket kb=%s ticket=%s → %s %s",
                    itsm_kb_id, itsm_ticket_id, r.status_code, r.text[:200],
                )
                return False
            finally:
                await self._kill_session(client, token)

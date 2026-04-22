"""Seed GLPI with 100+ healthcare-relevant resolved tickets and a small set of
pre-existing KB articles, so kbgen's pipeline has realistic dedup material.

Default behaviour wipes ALL existing tickets + KB articles and then creates
a clean set of 135 healthcare tickets (no `[SEED]` prefix). Pass
`--keep-existing` to skip the wipe and only insert.

Usage (GLPI must be running at http://localhost:9080):
    python scripts/seed_glpi_healthcare.py               # purge all + seed 135
    python scripts/seed_glpi_healthcare.py --keep-existing
"""

from __future__ import annotations

import argparse
import asyncio
import random
from datetime import datetime, timedelta, timezone

import httpx

BASE = "http://localhost:9080/apirest.php"
BASIC_USER = "glpi"
BASIC_PASSWORD = "glpi"


# ──────────────────────────────────────────────────────────────────────────────
# Content templates — healthcare IT issues: provisioning, EHR, FHIR, HL7,
# imaging, pharmacy, lab, HIE, patient portal, compliance, devices.
# ──────────────────────────────────────────────────────────────────────────────

_TEMPLATES: list[dict] = [
    # ── Provisioning & Access ────────────────────────────────────────────────
    {
        "cat": "Provisioning",
        "title": "New physician Epic access request — onboarding day 1",
        "desc": "Dr. {name} joining Cardiology needs Epic Hyperspace access, department Cardio, role Physician, patient scope Clinic_North.",
        "sol": "Created Epic user via User Provisioning tool. Assigned Physician role, Cardiology department security class, Clinic_North patient scope. Verified login via two-factor. Enrolled in Care Everywhere.",
    },
    {
        "cat": "Provisioning",
        "title": "Terminate departing nurse Cerner access and RBAC cleanup",
        "desc": "{name} separation effective immediately. Disable Cerner PowerChart + Millennium and remove from on-call group.",
        "sol": "Disabled Cerner account via HNAM. Removed from all scheduled groups. Revoked Kerberos delegation. Archived session cache.",
    },
    {
        "cat": "Provisioning",
        "title": "Resident rotation — bulk Meditech access grant",
        "desc": "Monthly resident rotation — 14 new residents need Meditech Expanse read+write in Medicine unit.",
        "sol": "Used Meditech bulk user import CSV. Assigned Resident role, Medicine service. Tested random sample of 3 logins.",
    },
    {
        "cat": "Provisioning",
        "title": "SSO federation failure between Active Directory and Epic",
        "desc": "Users report Epic SSO sends them back to login page after AD auth.",
        "sol": "Fixed mismatched SAML attribute mapping: Epic expected 'EPCS_ID' but AD was sending 'employeeID'. Updated claim rule in ADFS, re-tested.",
    },
    {
        "cat": "Provisioning",
        "title": "MFA enrollment blocked for new phlebotomists",
        "desc": "New phlebotomy batch cannot enroll in Okta Verify — 'user not in group' error.",
        "sol": "Added users to Okta group 'healthcare_mfa_required'. Confirmed enrollment via test account. Group membership now syncs via SCIM every 5 min.",
    },
    # ── FHIR & Interoperability ─────────────────────────────────────────────
    {
        "cat": "FHIR",
        "title": "FHIR Patient resource 404 for known MRN",
        "desc": "API consumer reports GET /Patient/{mrn} returns 404 though patient exists in EHR.",
        "sol": "FHIR server requires internal patient id (UUID), not MRN. Use GET /Patient?identifier=MRN|<mrn>  to resolve. Documented in integration guide.",
    },
    {
        "cat": "FHIR",
        "title": "FHIR Observation bundle rejected with 422",
        "desc": "Posting bundle of 50 lab observations returns 422 — OperationOutcome says 'value[x] missing'.",
        "sol": "Lab interface was sending Observation.valueQuantity with unit but without value numeric. Added value population; bundle accepted.",
    },
    {
        "cat": "FHIR",
        "title": "SMART on FHIR launch fails with invalid_scope",
        "desc": "Third-party app launch from Epic with scopes 'launch patient/*.read' errors.",
        "sol": "App registration in Epic App Orchard did not include 'patient/*.read'. Re-registered app with correct scope, re-tested launch. Consumer must refresh client metadata.",
    },
    {
        "cat": "FHIR",
        "title": "FHIR subscription notifications stopped firing",
        "desc": "Subscription to Patient resource no longer posts to webhook after last night.",
        "sol": "HAPI FHIR subscription status went to 'error' after 3 consecutive webhook failures. Webhook endpoint was returning 502. Restored endpoint, reactivated subscription via PUT Subscription/{id} with status=requested.",
    },
    {
        "cat": "FHIR",
        "title": "$everything operation times out for high-utilization patients",
        "desc": "Patient/{id}/$everything times out after 60s for patients with >5000 resources.",
        "sol": "Enabled pagination via _count=100 and _getpages cursor on the HAPI FHIR server. Updated client to follow next-page links. Typical patient now completes in <20s.",
    },
    # ── HL7 v2 ──────────────────────────────────────────────────────────────
    {
        "cat": "HL7",
        "title": "HL7 ADT^A08 message rejected — invalid date format",
        "desc": "Interface engine logs 'invalid PID-7' for incoming ADT^A08 from registration.",
        "sol": "Upstream EMR was sending PID-7 as YYYYMMDD but interface expected YYYYMMDDHHMMSS. Added padding transform 'append 000000' in Rhapsody mapper.",
    },
    {
        "cat": "HL7",
        "title": "Lab ORU^R01 results missing observation status",
        "desc": "Inbound lab results trigger OBX-11 validation error and do not post to chart.",
        "sol": "LIS was omitting OBX-11. Added default value 'F' (final) in Mirth Connect channel preprocessor. Notified LIS vendor to fix upstream.",
    },
    {
        "cat": "HL7",
        "title": "Outbound ORM^O01 orders not reaching pharmacy",
        "desc": "Pharmacy complains orders placed in EHR do not appear. HL7 engine shows no errors.",
        "sol": "Pharmacy side MLLP listener had been restarted with wrong port. Reverted to port 2575 and confirmed ACK receipt. Added health check to on-call runbook.",
    },
    {
        "cat": "HL7",
        "title": "SIU^S12 appointment duplicates after refactor",
        "desc": "Scheduling sends duplicate SIU events after queue change.",
        "sol": "Deduplication by FillerAppt Number added in integration engine. Back-filled de-dup window to 7 days.",
    },
    # ── EHR / Applications ──────────────────────────────────────────────────
    {
        "cat": "EHR",
        "title": "Epic Hyperspace freezes during chart open for single patient",
        "desc": "Opening patient MRN 10023849 hangs Hyperspace for 90s before timeout.",
        "sol": "Patient had >3000 encounters; flowsheet rows triggered client slowness. Cleared client-side flowsheet cache, filed ticket to Epic for root cause on server side.",
    },
    {
        "cat": "EHR",
        "title": "Meditech Expanse PDoc missing from Physician Portal",
        "desc": "Doctor cannot access Physician Documentation tab after shift swap.",
        "sol": "Role assignment had expired overnight. Extended physician role expiry by 1 year. Added reminder rule to prevent silent expiry.",
    },
    {
        "cat": "EHR",
        "title": "Cerner PowerChart slow navigation in ED",
        "desc": "ED staff report 10s+ delays switching between patients during peak.",
        "sol": "Citrix session latency from ED VLAN to PowerChart farm. Moved ED to dedicated VDI pool, enabled NetScaler session persistence. P95 navigation now <2s.",
    },
    # ── Pharmacy / CPOE ─────────────────────────────────────────────────────
    {
        "cat": "Pharmacy",
        "title": "CPOE order set 'Sepsis Bundle' missing vancomycin",
        "desc": "Pharmacy notes Sepsis Bundle does not include vancomycin after last content update.",
        "sol": "Restored vancomycin from order-set version history. Content change had dropped it during medication formulary sync. Added QA check to content pipeline.",
    },
    {
        "cat": "Pharmacy",
        "title": "E-prescribing to pharmacy rejected — DEA number missing",
        "desc": "NewRx messages rejected by Surescripts for controlled substance.",
        "sol": "Provider profile was missing DEA number after re-credentialing. Re-entered DEA in Epic EPCS config. Tested with schedule-II test order.",
    },
    # ── Lab ─────────────────────────────────────────────────────────────────
    {
        "cat": "Lab",
        "title": "Lab result not resulting in EHR after LIS upgrade",
        "desc": "Post LIS 7.2 upgrade, results arrive at HL7 listener but do not file.",
        "sol": "LIS now sends OBR-4 with different loinc code (short vs long form). Updated mapping table; old results reprocessed from queue.",
    },
    {
        "cat": "Lab",
        "title": "Microbiology sensitivity results truncated in chart",
        "desc": "Only first 5 antibiotics show in PowerChart result view.",
        "sol": "Default result column template limited to 5 rows. Expanded to 25. Long-term: request updated Cerner template.",
    },
    # ── Imaging / PACS ─────────────────────────────────────────────────────
    {
        "cat": "Imaging",
        "title": "PACS viewer fails to open DICOM from outside network",
        "desc": "Teleradiologist cannot load studies when working from home.",
        "sol": "VPN profile did not include PACS VLAN. Updated split-tunnel config to include 10.20.30.0/24. Confirmed study load.",
    },
    {
        "cat": "Imaging",
        "title": "DICOM study duplicate accession numbers",
        "desc": "Same accession appearing twice in worklist after modality maintenance.",
        "sol": "Modality sent duplicate MPPS on reboot. Configured MWL server to dedupe on AccessionNumber + SeriesInstanceUID window.",
    },
    # ── HIE / Care Everywhere ───────────────────────────────────────────────
    {
        "cat": "HIE",
        "title": "Care Everywhere query failing for partner hospital",
        "desc": "Outside records not returning from Hospital B though agreement active.",
        "sol": "Partner's assertion endpoint certificate expired; SAML responses rejected. Coordinated with partner IT to rotate cert. Tested query.",
    },
    {
        "cat": "HIE",
        "title": "CCDA import fails on malformed narrative block",
        "desc": "Incoming CCDA rejected by document parser with XML namespace error.",
        "sol": "Partner was embedding HTML without CDATA. Updated our parser to handle mixed-content narrative per C-CDA R2.1 §3.2.",
    },
    # ── Patient Portal ──────────────────────────────────────────────────────
    {
        "cat": "Patient Portal",
        "title": "MyChart activation email not received by new patients",
        "desc": "Multiple patients report never getting MyChart activation link.",
        "sol": "SendGrid reputation dropped causing deferred delivery. Rotated IP pool and added SPF/DKIM for a warm secondary. Backfilled pending activations.",
    },
    {
        "cat": "Patient Portal",
        "title": "MyChart proxy access not working for pediatric parent",
        "desc": "Parent cannot see minor's chart despite proxy relationship entered in EHR.",
        "sol": "Proxy was set to Level 2 (no chart). Updated to Level 3 (full pediatric). Reviewed policy: minors <12 default to Level 3 unless restricted.",
    },
    # ── Devices / Monitoring ────────────────────────────────────────────────
    {
        "cat": "Devices",
        "title": "Vital signs monitors not posting to EHR in ICU bay 4",
        "desc": "Philips IntelliVue MP70 values missing in flowsheet for bed ICU-4B.",
        "sol": "Bay 4 network jack misconfigured VLAN. Re-patched to med-device VLAN 120. Confirmed values flowing within 15 min.",
    },
    {
        "cat": "Devices",
        "title": "Smart pump drug library out-of-date in PACU",
        "desc": "BD Alaris pumps in PACU not showing latest pharmacy drug library.",
        "sol": "Pumps were offline during last library push. Manually synced via Guardrails server. Scheduled automatic overnight checks.",
    },
    # ── Compliance / HIPAA ──────────────────────────────────────────────────
    {
        "cat": "Compliance",
        "title": "Audit log export for HIPAA inquiry spans 7-year window",
        "desc": "Compliance office requests full access log for MRN 10045982 from 2018 onward.",
        "sol": "Used Epic Chronicles audit extract + archived audit DB for pre-2022. Delivered CSV via SFTP to compliance drop. Documented retention policy.",
    },
    {
        "cat": "Compliance",
        "title": "Break-glass access review — unexplained emergency open",
        "desc": "Emergency access used on VIP patient chart — compliance wants justification trail.",
        "sol": "Pulled break-glass event with user, reason entered, and chart-touch log. User had valid clinical reason. Closed with note; policy reaffirmed.",
    },
    # ── Network / Infra ─────────────────────────────────────────────────────
    {
        "cat": "Infrastructure",
        "title": "VPN disconnects every 15 minutes for remote coders",
        "desc": "HIM coders report frequent VPN drops preventing chart review.",
        "sol": "Idle timeout on Cisco AnyConnect policy was 15m. Raised to 8h for coder group. Verified no HIPAA risk — full-tunnel enforced.",
    },
    {
        "cat": "Infrastructure",
        "title": "WiFi certificate expired clinical laptops lose connectivity",
        "desc": "Fleet of nursing laptops dropped off corp WiFi this morning.",
        "sol": "Intermediate CA cert expired. Pushed new cert via Intune. Manually reconnected 20 laptops; rest picked up on reboot.",
    },
    # ── Identity / Patient Matching ─────────────────────────────────────────
    {
        "cat": "Identity",
        "title": "Duplicate patient records merged incorrectly by EMPI",
        "desc": "EMPI merged two distinct patients with similar names; chart now contains mixed records.",
        "sol": "Unmerged via EMPI split workflow. Re-ran scoring with stricter DOB match. Escalated to vendor to tune threshold.",
    },
    {
        "cat": "Identity",
        "title": "Newborn 'Baby Girl' placeholder not updated after naming",
        "desc": "Nursing reports newborn still named 'Babygirl Smith' in system 2 days after parents chose name.",
        "sol": "Nameless-newborn naming workflow requires registrar action. Trained unit clerks on proper rename step. Escalation path documented.",
    },
    # ── Scheduling ──────────────────────────────────────────────────────────
    {
        "cat": "Scheduling",
        "title": "Clinic template showing wrong provider after EHR update",
        "desc": "Scheduling shows Dr. X's template instead of Dr. Y after overnight build.",
        "sol": "Build inadvertently overwrote Dr. Y's template. Restored from Epic Chronicles backup. Added change-control sign-off to build release.",
    },
    {
        "cat": "Scheduling",
        "title": "Operating Room block release automation failing",
        "desc": "OR block release for next day not triggering; blocks held 48h past policy.",
        "sol": "Scheduled job ran out of memory. Increased memory allocation on OR Manager server. Added monitoring alert for job state.",
    },
    # ── Reporting / Analytics ───────────────────────────────────────────────
    {
        "cat": "Reporting",
        "title": "Clarity ETL lag — reports stale by 2 days",
        "desc": "Quality team reports Clarity SQL data 2 days old; usually <24h.",
        "sol": "ETL server hit disk space limit. Expanded volume, relaunched job, backfilled missed windows.",
    },
    {
        "cat": "Reporting",
        "title": "Power BI dashboard auth fails for executive team",
        "desc": "Execs cannot load the hospital-wide dashboard; get sign-in loop.",
        "sol": "Conditional Access policy updated — execs were no longer in the 'PowerBI_Viewer' group. Reinstated group membership; policy exception documented.",
    },
    # ── Billing / Revenue Cycle ─────────────────────────────────────────────
    {
        "cat": "Billing",
        "title": "837 claims rejected with Loop 2300 DTP error",
        "desc": "Many claims rejected by clearinghouse for date-qualifier loop.",
        "sol": "DTP qualifier changed from 454 to 096 per latest 5010A2 companion guide. Updated Epic Resolute output mapping.",
    },
    {
        "cat": "Billing",
        "title": "Patient estimate tool showing $0 for all inpatient stays",
        "desc": "Price estimator returning $0 after rate-table sync.",
        "sol": "Rate table import had column header drift; DRG column unmapped. Restored mapping; re-ran overnight import. Values now populated.",
    },
    # ── Security / IR ───────────────────────────────────────────────────────
    {
        "cat": "Security",
        "title": "Phishing email with fake Microsoft login reached clinicians",
        "desc": "Phishing email targeting MD users delivered despite filter.",
        "sol": "Tuned Defender for Office 365 URL defense; recalled messages; forced password reset for 7 clicked users; no lateral movement observed.",
    },
    {
        "cat": "Security",
        "title": "Unusual download volume from EHR by one user over weekend",
        "desc": "SIEM fired alert on 40GB chart PDF download from single user.",
        "sol": "User was legitimate researcher with IRB approval but bulk export was not permitted under policy. Paused access, reviewed data, re-enabled with audit trail required.",
    },
]

# Extra ticket templates where the resolution notes are intentionally missing or
# near-empty. These drive "gap" topics in the dashboard because kbgen will
# SKIP drafting without enough resolution text.
_SKIP_TEMPLATES: list[dict] = [
    # Gap-only categories — nothing in _TEMPLATES touches these, so every
    # ticket in them will SKIP, producing true "gap" topics in the dashboard.
    {"cat": "Biomedical Engineering", "title": "Telemetry transmitter pairing failure on 6-East", "desc": "TX units intermittently fail to pair with receivers after reboot.", "sol": ""},
    {"cat": "Biomedical Engineering", "title": "Infusion pump battery runtime shorter than spec", "desc": "Fleet showing 40% runtime vs specified 8h.", "sol": ""},
    {"cat": "Clinical Analytics", "title": "Sepsis predictive model output drifted vs validation set", "desc": "Model calibration slope differs from baseline.", "sol": ""},
    {"cat": "Clinical Analytics", "title": "Readmission dashboard off by 3 discharges vs Clarity", "desc": "Dashboard total doesn't match source-of-truth.", "sol": ""},
    {"cat": "Research Informatics", "title": "REDCap data pull failing for IRB 2024-112", "desc": "Nightly extract errors without logs.", "sol": ""},
    {"cat": "Research Informatics", "title": "i2b2 ontology term 'CCS 172' missing after refresh", "desc": "Cohort query missing diagnosis rollup.", "sol": ""},
    {"cat": "Telehealth", "title": "Zoom for Healthcare session dropping for 1% of visits", "desc": "Sporadic drops impacting clinicians with no pattern.", "sol": ""},
    {"cat": "Telehealth", "title": "E-visit queue not surfacing new requests in MyChart", "desc": "Patient-initiated e-visits sometimes invisible to staff.", "sol": ""},
    # Existing-category skips — help the dashboard show "covered" vs "draft-pending"
    # nuance where some tickets are gaps within otherwise-covered topics.
    {"cat": "Devices", "title": "Glucometer readings not appearing in EHR for bed 12B", "desc": "Vitals missing for bed 12B since 07:00.", "sol": ""},
    {"cat": "HIE", "title": "Sporadic Care Everywhere timeouts for clinic D", "desc": "Clinic D reports intermittent outside-record timeouts; no pattern.", "sol": ""},
    {"cat": "Compliance", "title": "Audit trail gap for workstation 22 on 2026-03-15", "desc": "SIEM shows no events from WS-22 for a 3-hour window.", "sol": ""},
    {"cat": "Reporting", "title": "Clarity slicer dice mismatch for readmissions", "desc": "Two reports using same slicer show different readmission counts.", "sol": ""},
    {"cat": "Billing", "title": "Denial spike on modifier 59 — need investigation", "desc": "Modifier-59 denial rate rose 8× last week.", "sol": ""},
    {"cat": "Scheduling", "title": "Dermatology overbooking after last template change", "desc": "Derm template shows 2 patients per slot where it used to be 1.", "sol": ""},
    {"cat": "Security", "title": "Unusual geo-login for on-call MD — flagged but unverified", "desc": "Login from unfamiliar country; user on vacation.", "sol": ""},
]

FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Riley", "Casey", "Drew", "Sam", "Robin", "Avery", "Priya", "Hiroshi", "Mei", "Kenji", "Lucia", "Noah"]
LAST_NAMES = ["Patel", "Nguyen", "Garcia", "Johnson", "Kim", "Williams", "Brown", "Rodriguez", "Davis", "Miller", "Anderson", "Singh", "Tanaka", "Cohen", "Rossi"]


def _fake_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _safe_format(s: str, **kw) -> str:
    """str.format that tolerates missing keys — returns the original placeholder."""
    class _Default(dict):
        def __missing__(self, k: str) -> str:  # noqa: D401
            return "{" + k + "}"
    return s.format_map(_Default(**kw))


def build_tickets(n: int) -> list[dict]:
    random.seed(20260422)
    out: list[dict] = []
    now = datetime.now(timezone.utc)
    for i in range(n):
        tpl = _TEMPLATES[i % len(_TEMPLATES)]
        variant = (i // len(_TEMPLATES)) + 1
        name = _fake_name()
        suffix = f" (case #{variant:02d})" if variant > 1 else ""
        resolved_at = (now - timedelta(days=random.randint(0, 120), hours=random.randint(0, 23))).replace(microsecond=0)
        out.append(
            {
                "title": f"{tpl['title']}{suffix}",
                "desc": _safe_format(tpl["desc"], name=name),
                "sol": tpl["sol"],
                "cat": tpl["cat"],
                "solvedate": resolved_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    # Append the "gap" (no-resolution) tickets.
    for i, tpl in enumerate(_SKIP_TEMPLATES):
        resolved_at = (now - timedelta(days=random.randint(0, 60))).replace(microsecond=0)
        out.append(
            {
                "title": tpl["title"],
                "desc": _safe_format(tpl["desc"]),
                "sol": tpl["sol"],
                "cat": tpl["cat"],
                "solvedate": resolved_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return out


# Small set of pre-existing KB articles — seeds the dedup path so some tickets
# will be marked COVERED.
_KB_ARTICLES = [
    {
        "title": "How to request SSO access to Epic for new physicians",
        "answer": (
            "<p>Submit a provisioning ticket with the physician's NPI, department, and "
            "role. Once approved by the department head, Identity Services enables Epic "
            "Hyperspace access in the User Provisioning tool and enrolls the user in "
            "Care Everywhere.</p>"
        ),
    },
    {
        "title": "FHIR: resolving Patient resource by MRN via identifier search",
        "answer": (
            "<p>The FHIR server requires its internal UUID, not the MRN. To look up a "
            "patient by MRN, use <code>GET /Patient?identifier=MRN|&lt;mrn&gt;</code>. "
            "See the integration guide for the full list of identifier systems.</p>"
        ),
    },
    {
        "title": "Troubleshooting VPN timeouts for remote clinical staff",
        "answer": (
            "<p>Cisco AnyConnect idle timeouts are enforced per-policy. If a user reports "
            "frequent drops, verify their assigned group and raise the idle timeout for "
            "long-running roles such as HIM coders and teleradiologists. Full-tunnel must "
            "remain enforced.</p>"
        ),
    },
    {
        "title": "Recovering a stuck HL7 interface channel in Mirth Connect",
        "answer": (
            "<p>Check the queue backlog and error log. If messages are piling with no "
            "ACK, verify MLLP port and destination server health. Restart the channel, "
            "then flush error store only after confirming upstream is healthy.</p>"
        ),
    },
]


async def _login(client: httpx.AsyncClient) -> str:
    creds = httpx.BasicAuth(BASIC_USER, BASIC_PASSWORD)
    r = await client.get(f"{BASE}/initSession", auth=creds)
    r.raise_for_status()
    return r.json()["session_token"]


def _headers(session: str) -> dict[str, str]:
    return {"Session-Token": session, "Content-Type": "application/json"}


async def _purge_all(client: httpx.AsyncClient, session: str) -> None:
    """Delete every ticket and every KB article in GLPI, paginated.

    Uses `force_purge=1` so rows are hard-deleted, not soft-deleted.
    """

    async def _purge_collection(endpoint: str, label: str) -> int:
        removed = 0
        while True:
            r = await client.get(
                f"{BASE}/{endpoint}",
                headers=_headers(session),
                params={"range": "0-199", "only_id": "true"},
            )
            if r.status_code == 206 or r.status_code == 200:
                rows = r.json() or []
            else:
                break
            if not rows:
                break
            for row in rows:
                rid = row.get("id")
                if rid is None:
                    continue
                await client.delete(
                    f"{BASE}/{endpoint}/{rid}?force_purge=1",
                    headers=_headers(session),
                )
                removed += 1
            # Small progress marker on large sets so we can see work happening.
            if removed and removed % 200 == 0:
                print(f"  {label}: purged {removed}…")
        return removed

    n_tickets = await _purge_collection("Ticket", "tickets")
    n_kb = await _purge_collection("KnowbaseItem", "kb articles")
    print(f"purged {n_tickets} tickets and {n_kb} KB articles")


async def _ensure_categories(
    client: httpx.AsyncClient, session: str, categories: set[str]
) -> dict[str, int]:
    """Return a map {category_name: id}, creating any missing categories."""
    r = await client.get(
        f"{BASE}/ITILCategory", headers=_headers(session), params={"range": "0-499"}
    )
    r.raise_for_status()
    existing = {c["name"]: c["id"] for c in (r.json() or []) if c.get("name")}
    out: dict[str, int] = {}
    for cat in sorted(categories):
        if cat in existing:
            out[cat] = existing[cat]
            continue
        rc = await client.post(
            f"{BASE}/ITILCategory",
            headers=_headers(session),
            json={"input": {"name": cat, "is_helpdeskvisible": 1, "is_request": 1, "is_incident": 1}},
        )
        if rc.status_code >= 400:
            print(f"  category '{cat}' create failed: {rc.status_code} {rc.text[:160]}")
            continue
        data = rc.json()
        if isinstance(data, list):
            data = data[0]
        out[cat] = data.get("id")
    return out


async def main(purge: bool = True) -> None:
    tickets = build_tickets(120)
    async with httpx.AsyncClient(timeout=60.0) as client:
        session = await _login(client)
        print(f"session: {session[:8]}…")

        if purge:
            print("purging ALL tickets + KB articles (this may take a moment)…")
            await _purge_all(client, session)
        else:
            print("--keep-existing: skipping purge, inserting on top of existing data")

        categories = {t["cat"] for t in tickets}
        print(f"ensuring {len(categories)} ITIL categories…")
        cat_map = await _ensure_categories(client, session, categories)
        print(f"  {len(cat_map)} category ids resolved")

        print(f"seeding {len(_KB_ARTICLES)} KB articles…")
        for kb in _KB_ARTICLES:
            payload = {
                "input": {
                    "name": kb["title"],
                    "answer": kb["answer"],
                    "is_faq": 0,
                }
            }
            r = await client.post(f"{BASE}/KnowbaseItem", headers=_headers(session), json=payload)
            r.raise_for_status()

        print(f"seeding {len(tickets)} tickets (status=closed with solution)…")
        created = 0
        for i, t in enumerate(tickets):
            # Follow GLPI's real workflow:
            #   1. create ticket in 'new' (status=1)
            #   2. add ITILSolution — GLPI transitions status to 'solved' (5)
            #   3. update to 'closed' (status=6) + backdate solvedate/closedate
            payload = {
                "input": {
                    "name": t["title"],
                    "content": f"<p>{t['desc']}</p>",
                    "status": 1,
                    "itilcategories_id": cat_map.get(t["cat"], 0),
                }
            }
            r = await client.post(f"{BASE}/Ticket", headers=_headers(session), json=payload)
            if r.status_code >= 400:
                print(f"  ticket {i} failed: {r.status_code} {r.text[:200]}")
                continue
            data = r.json()
            if isinstance(data, list):
                data = data[0]
            tid = data.get("id")
            if not tid:
                continue
            # Add the ITILSolution (if we have resolution notes). This transitions
            # the ticket to 'solved' (status=5).
            if t["sol"]:
                sol_payload = {
                    "input": {
                        "itemtype": "Ticket",
                        "items_id": tid,
                        "content": f"<p>{t['sol']}</p>",
                    }
                }
                sr = await client.post(
                    f"{BASE}/ITILSolution", headers=_headers(session), json=sol_payload
                )
                if sr.status_code >= 400:
                    print(f"  ticket {tid} ITILSolution failed: {sr.status_code} {sr.text[:160]}")

            # Close the ticket and backdate solvedate/closedate for realistic
            # "recently resolved" data across the history window.
            close_payload = {
                "input": {
                    "id": tid,
                    "status": 6,
                    "solvedate": t["solvedate"],
                    "closedate": t["solvedate"],
                }
            }
            cr = await client.put(
                f"{BASE}/Ticket/{tid}", headers=_headers(session), json=close_payload
            )
            if cr.status_code >= 400:
                print(f"  ticket {tid} close failed: {cr.status_code} {cr.text[:160]}")
            created += 1
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(tickets)}")
        print(f"created {created} tickets")

        # Spot-check.
        r = await client.get(f"{BASE}/Ticket?range=0-0", headers=_headers(session))
        total_header = r.headers.get("Content-Range", "")
        print(f"Content-Range from GLPI: {total_header}")

        await client.get(f"{BASE}/killSession", headers=_headers(session))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not purge existing tickets/KB before seeding. Default is to purge all.",
    )
    args = parser.parse_args()
    asyncio.run(main(purge=not args.keep_existing))

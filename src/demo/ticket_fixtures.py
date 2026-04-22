"""Demo fixture packs — one button click drops 10 themed resolved tickets
into the ITSM so a walkthrough can show the full kbgen story:

  * big cluster (6)  → 1 master draft + 5 covered siblings
  * small cluster (2) → 1 master draft + 1 covered sibling
  * near-duplicate of an already-live KB (1) → COVERED → KB N (no draft)
  * gap ticket (1) — no resolution, unrelated category → SKIPPED,
    exercisable via the gap-RAG "generate KB" action

Successive button clicks rotate through packs so the demo doesn't just
produce more copies of the same theme. Each pack appends a short batch
tag to titles so multi-click demos show up as visibly distinct tickets
in GLPI without fighting with semantic dedup.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class DemoTicket:
    title: str
    description: str
    resolution: str
    category: str | None = None


@dataclass
class DemoPack:
    theme: str
    narrative: str  # one-line story the demo is telling
    tickets: list[DemoTicket]


# Canonical resolution templates — siblings must share near-verbatim
# resolution wording to cluster above the 0.82 cosine threshold. The
# description varies (which clinic / which room) but the "here's what fixed
# it" paragraph stays consistent. Reality-check: in real ITSMs, technicians
# copy-paste their own prior solution into similar tickets, so this pattern
# matches what kbgen would see in production ticket histories.
_ZOOM_RES = (
    "Zoom Rooms appliance was on 5.16 with Smart Gallery audio routing enabled. "
    "Upgraded the Zoom Rooms appliance to 5.18 and toggled off Smart Gallery audio routing "
    "in the room profile. Verified audio stays stable for a full 45-minute telehealth visit. "
    "Rolling the same fix out to other Zoom Rooms on 5.16."
)
_MYCHART_RES = (
    "Overnight Active Directory sync truncated the userPrincipalName for accounts with "
    "non-ASCII characters, which broke MyChart SSO. Re-ran the AD sync using the updated "
    "PowerShell connector that preserves UTF-8 attributes, then cleared the IdP session cache. "
    "MyChart logins restored within 15 minutes."
)


# ── Pack A — Zoom / Telehealth cluster + MyChart + MFA near-dup ──────────────
_PACK_A = DemoPack(
    theme="telehealth-zoom",
    narrative="Telemedicine Zoom audio dropouts across clinics; MyChart SSO fallout; MFA enrollment near-duplicate.",
    tickets=[
        # Big cluster: Zoom audio dropouts during telemedicine visits (6) —
        # identical resolution wording so siblings cluster above 0.82.
        DemoTicket(
            category="Telehealth",
            title="Zoom audio dropping mid-visit in tumor board telehealth room A",
            description="Clinicians report one-way audio freezes every few minutes during oncology telehealth consults from room A.",
            resolution=_ZOOM_RES,
        ),
        DemoTicket(
            category="Telehealth",
            title="Telemedicine visit audio cuts out in cardiology Zoom Room B",
            description="Cardiologists on Zoom telehealth visits from room B report audio drops to silence every 3–4 minutes.",
            resolution=_ZOOM_RES,
        ),
        DemoTicket(
            category="Telehealth",
            title="Zoom telehealth room C — patient cannot hear provider after first 2 minutes",
            description="Patient joins a telehealth visit hosted from room C and loses provider audio roughly 2 minutes in; provider still hears patient.",
            resolution=_ZOOM_RES,
        ),
        DemoTicket(
            category="Telehealth",
            title="Intermittent Zoom audio dropout in pediatrics telehealth visits",
            description="Pediatrics providers report audio freezes during telehealth visits from their clinic's Zoom Room.",
            resolution=_ZOOM_RES,
        ),
        DemoTicket(
            category="Telehealth",
            title="Psychiatry telehealth visit — Zoom audio freeze on provider side",
            description="Psychiatry group reports provider-side audio freezes mid-visit on Zoom.",
            resolution=_ZOOM_RES,
        ),
        DemoTicket(
            category="Telehealth",
            title="Endocrinology Zoom telehealth — audio skips for patient every few minutes",
            description="Patient in an endocrinology telehealth visit reports the provider's audio skips every 3–5 minutes.",
            resolution=_ZOOM_RES,
        ),
        # Small cluster: MyChart login failure after AD sync (2) — shared resolution.
        DemoTicket(
            category="Patient Portal",
            title="MyChart login failing after overnight AD sync — access denied banner",
            description="Patients reporting 'Access denied' on MyChart login this morning; affects users who changed password in last 24h.",
            resolution=_MYCHART_RES,
        ),
        DemoTicket(
            category="Patient Portal",
            title="MyChart access-denied for patients who reset password overnight",
            description="Patients who reset their MyChart password last night get 'Access denied' on login today.",
            resolution=_MYCHART_RES,
        ),
        # Near-dup of live KB — MFA enrollment for new phlebotomists (1)
        DemoTicket(
            category="Provisioning",
            title="MFA enrollment blocked for new phlebotomists starting this week (case #04)",
            description="New phlebotomy hires cannot enroll in Okta Verify — they hit a 'user not in group' error.",
            resolution="Added the new phlebotomists to the Okta group 'healthcare_mfa_required'. Confirmed enrollment through a test account. Group membership syncs via SCIM every 5 minutes.",
        ),
        # Gap ticket (1) — no resolution, unrelated category → SKIPPED.
        # Kept intentionally off-theme from the Zoom/MyChart siblings so it
        # won't accidentally get pulled into their clusters.
        DemoTicket(
            category="Biomedical Engineering",
            title="Telemetry transmitter pairing failure on 6-East",
            description="TX units on 6-East intermittently fail to pair with receivers after reboot. No fix yet; nurses rotating to spare units.",
            resolution="",
        ),
    ],
)


_HL7_RES = (
    "The interface engine filter had the legacy 240-character PID segment length cap "
    "still in place. Set maxSegmentLength on the inbound filter to 0 (unlimited) and "
    "re-routed the backlog from the replay queue. Message flow restored; validated with "
    "a replay of the most recent 50 ADT messages, no truncation events logged since."
)
_PYXIS_RES = (
    "Pyxis MedStation firmware 1.16.4 silently reset the override session window to 0 "
    "seconds. Applied the site policy template 'Pharmacy-Ops' which restores the 5-minute "
    "override window, then pushed the policy to all 14 MedStations. Overrides working normally."
)


# ── Pack B — HL7 / Pharmacy + WiFi cert near-dup ─────────────────────────────
_PACK_B = DemoPack(
    theme="hl7-pharmacy",
    narrative="HL7 ADT truncation across lab interfaces; pharmacy override failures; WiFi cert near-duplicate.",
    tickets=[
        # Big cluster: HL7 ADT segment truncation (6) — shared resolution.
        DemoTicket(
            category="HL7",
            title="HL7 ADT^A01 rejected — PID segment truncated (Quest lab interface)",
            description="Quest lab interface rejecting inbound ADT^A01 messages — ops sees 'segment truncated' in Rhapsody logs.",
            resolution=_HL7_RES,
        ),
        DemoTicket(
            category="HL7",
            title="ADT A08 messages dropping from LabCorp feed — truncation error",
            description="LabCorp feed drops ADT^A08 updates with PID segment truncation errors in the interface engine.",
            resolution=_HL7_RES,
        ),
        DemoTicket(
            category="HL7",
            title="Rhapsody interface — ADT A04 truncated on patient registration",
            description="Patient registrations from admitting system fail downstream because ADT^A04 PID segments come through truncated.",
            resolution=_HL7_RES,
        ),
        DemoTicket(
            category="HL7",
            title="Lab interface outbound ADT A11 truncation — cancellations not propagating",
            description="ADT^A11 cancellation messages to external lab are being truncated at the PID segment; external system complains.",
            resolution=_HL7_RES,
        ),
        DemoTicket(
            category="HL7",
            title="Reference lab ADT A02 transfers — PID truncation blocks billing",
            description="Transfer ADTs to the reference lab are being truncated; billing cycle flags mismatched patient identifiers.",
            resolution=_HL7_RES,
        ),
        DemoTicket(
            category="HL7",
            title="Corepoint engine truncating ADT A08 — downstream EMPI errors",
            description="EMPI errors correlate with truncated ADT^A08 from Corepoint over the past 24 hours.",
            resolution=_HL7_RES,
        ),
        # Small cluster: Pharmacy Pyxis override failures (2) — shared resolution.
        DemoTicket(
            category="Pharmacy",
            title="Pyxis MedStation override requires re-login every time — pharmacy tech blocked",
            description="Pharmacy technicians forced to re-authenticate on every Pyxis MedStation override after last week's firmware push.",
            resolution=_PYXIS_RES,
        ),
        DemoTicket(
            category="Pharmacy",
            title="Pyxis cabinet override failures in oncology pharmacy after firmware update",
            description="Oncology pharmacy cabinet denies override authentications after the 1.16.4 firmware.",
            resolution=_PYXIS_RES,
        ),
        # Near-dup of live KB — WiFi cert expiry on clinical laptops (1)
        DemoTicket(
            category="Infrastructure",
            title="WiFi certificate expired on clinical laptops — floor 5 reports no network (case #04)",
            description="Clinical laptops on floor 5 lost WiFi this morning. The 802.1x cert chain expired.",
            resolution="Issued fresh device certs from the internal PKI, pushed via Intune to the affected laptop group. Rebooted one as a sanity check — connected on first try. Full fleet remediation completed in 90 minutes.",
        ),
        # Gap ticket (1) — no resolution, unrelated category → SKIPPED.
        DemoTicket(
            category="Research Informatics",
            title="REDCap data pull failing for IRB 2024-112",
            description="Nightly extract for IRB 2024-112 errors out with no log output. Research team blocked on cohort refresh.",
            resolution="",
        ),
    ],
)


_PACS_RES = (
    "The morning network change renumbered the PACS VLAN, but Epic Radiant's Bridges "
    "HL7-to-DICOM relay was still pinned to the old IP. Updated the relay destination in "
    "the Bridges config and bounced the relay service. Radiant renders studies again; "
    "confirmed with a cross-modality sanity check (CT, MRI, US)."
)
_FHIR_SUB_RES = (
    "The webhook ingress TLS cert had expired overnight so the front door was returning "
    "502, which tripped HAPI's subscription-to-error rule after 3 consecutive failures. "
    "Renewed the cert, redeployed the ingress, then PUT Subscription/{id} with status=requested "
    "to reactivate. Events flowing again."
)


# ── Pack C — PACS / FHIR subs + MFA near-dup variant ─────────────────────────
_PACK_C = DemoPack(
    theme="imaging-fhir",
    narrative="PACS study not rendering in Epic Radiant; FHIR Subscription webhook loops; MFA near-duplicate.",
    tickets=[
        # Big cluster: PACS study not rendering in Epic Radiant (6) — shared resolution.
        DemoTicket(
            category="Imaging",
            title="Radiology PACS — MRI study not launching in Epic Radiant after router swap",
            description="MRI studies scheduled after 07:00 today fail to launch in Epic Radiant; Radiant shows 'Image unavailable'.",
            resolution=_PACS_RES,
        ),
        DemoTicket(
            category="Imaging",
            title="CT studies fail to open in Epic Radiant — 'image unavailable'",
            description="CT studies from this morning fail to open in Radiant with 'Image unavailable'.",
            resolution=_PACS_RES,
        ),
        DemoTicket(
            category="Imaging",
            title="Ultrasound studies not rendering — PACS returns error to Radiant",
            description="Ultrasound studies requested in Radiant error out during image fetch.",
            resolution=_PACS_RES,
        ),
        DemoTicket(
            category="Imaging",
            title="Radiant shows 'Image unavailable' for all new imaging orders this morning",
            description="All net-new imaging orders in Radiant return 'Image unavailable' for the last 3 hours.",
            resolution=_PACS_RES,
        ),
        DemoTicket(
            category="Imaging",
            title="PACS image display broken in Radiant — VLAN change suspected",
            description="After the morning change window PACS images are not displaying in Radiant.",
            resolution=_PACS_RES,
        ),
        DemoTicket(
            category="Imaging",
            title="Nuc-med study unavailable in Radiant — relay suspected stale",
            description="Nuclear medicine study orders in Radiant fail with 'Image unavailable' after today's network change.",
            resolution=_PACS_RES,
        ),
        # Small cluster: FHIR Subscription webhook 502 loops (2) — shared resolution.
        DemoTicket(
            category="FHIR",
            title="FHIR Subscription to Patient resource stuck in error after webhook 502s",
            description="Our Patient-resource Subscription stopped firing — HAPI marked it in error after 3 consecutive 502s from the webhook.",
            resolution=_FHIR_SUB_RES,
        ),
        DemoTicket(
            category="FHIR",
            title="HAPI FHIR Subscription disabled — repeated webhook 502 errors",
            description="Subscription we use for real-time Patient updates disabled itself after 3 webhook 502s overnight.",
            resolution=_FHIR_SUB_RES,
        ),
        # Near-dup of live KB — MFA variant (1)
        DemoTicket(
            category="Provisioning",
            title="MFA enrollment blocked for new phlebotomy hires — 'user not in group' (case #05)",
            description="Another phlebotomy cohort blocked at Okta Verify with 'user not in group'.",
            resolution="Added the hires to Okta group 'healthcare_mfa_required'. SCIM sync completed within 5 min. Enrollment succeeded after that.",
        ),
        # Gap ticket (1) — no resolution, unrelated category → SKIPPED.
        DemoTicket(
            category="Devices",
            title="Glucometer readings not appearing in EHR for bed 12B",
            description="Vitals missing for bed 12B since 07:00. Device shows readings locally but they never reach the EHR.",
            resolution="",
        ),
    ],
)


_PACKS: list[DemoPack] = [_PACK_A, _PACK_B, _PACK_C]

# Module-level counter so successive /admin/seed-demo calls walk through the
# packs instead of always returning the same theme.
_call_count = 0


def next_pack() -> DemoPack:
    """Return the next fixture pack in the rotation.

    Appends a short timestamp tag to every title so the tickets created in
    this batch are visually distinguishable from earlier demo seeds in the
    GLPI UI. The resolution text is untouched, which is what the dedup
    embedding cares about — so scenario-B tickets still cluster against the
    live KB.
    """
    global _call_count
    pack = _PACKS[_call_count % len(_PACKS)]
    _call_count += 1

    batch_tag = datetime.now(timezone.utc).strftime("%H%M")
    tagged = DemoPack(
        theme=pack.theme,
        narrative=pack.narrative,
        tickets=[
            DemoTicket(
                title=f"{t.title} [{batch_tag}]",
                description=t.description,
                resolution=t.resolution,
                category=t.category,
            )
            for t in pack.tickets
        ],
    )
    return tagged

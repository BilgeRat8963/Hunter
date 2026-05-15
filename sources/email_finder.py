"""
Email enrichment module — discovers a contact email for each Lead and writes it back
onto the Lead object in place.

The strategy is deliberately conservative: fetch the lead's own website (homepage
and /contact if the homepage yields nothing), extract emails from mailto: links first
(highest confidence), then fall back to plain-text regex. Candidates are scored by
prefix quality (hello@, contact@, support@ score higher than generic info@) and by
domain match (an email at the same domain as the product website scores higher than
a third-party address). Obvious noise — noreply@, abuse@, postmaster@, example@ —
is discarded before scoring. robots.txt is respected, responses are capped at 500 KB
to avoid downloading huge asset bundles, and a 2-second sleep is inserted between
requests to avoid hammering small indie sites.
"""

import re
import time
import urllib.robotparser
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from sources.base import Lead

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
TIMEOUT = 10
MAX_BYTES = 500_000
DELAY = 2

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

SKIP_PREFIXES = {"noreply", "no-reply", "donotreply", "bounce", "abuse",
                 "postmaster", "mailer-daemon", "example", "test", "user",
                 "email", "admin", "root", "info", "webmaster"}

GOOD_PREFIXES = ["hello", "contact", "support", "hi", "team", "founder",
                 "hey", "mail", "reach", "get"]

_robots_cache: dict = {}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def _get_robots(base_url: str, session: requests.Session) -> urllib.robotparser.RobotFileParser:
    origin = urlparse(base_url).scheme + "://" + urlparse(base_url).netloc
    if origin in _robots_cache:
        return _robots_cache[origin]
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(origin + "/robots.txt")
    try:
        rp.read()
    except Exception:
        pass  # treat unreadable robots.txt as permissive
    _robots_cache[origin] = rp
    return rp


def _allowed(url: str, session: requests.Session) -> bool:
    try:
        rp = _get_robots(url, session)
        return rp.can_fetch(UA, url)
    except Exception:
        return True


def _fetch(url: str, session: requests.Session) -> Optional[str]:
    try:
        resp = session.get(url, timeout=TIMEOUT, stream=True)
        resp.raise_for_status()
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) >= MAX_BYTES:
                break
        return content.decode("utf-8", errors="replace")
    except Exception:
        return None


def _score_email(email: str, domain: str) -> int:
    """Higher = better candidate."""
    prefix = email.split("@")[0].lower()
    edomain = email.split("@")[1].lower() if "@" in email else ""

    # Hard skip
    if any(prefix == s or prefix.startswith(s + ".") for s in SKIP_PREFIXES):
        return -1

    score = 0
    if edomain and domain and (edomain == domain or edomain.endswith("." + domain)):
        score += 10
    for i, good in enumerate(GOOD_PREFIXES):
        if prefix == good or prefix.startswith(good):
            score += (len(GOOD_PREFIXES) - i)
            break
    return score


def _extract_emails(html: str, site_domain: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")

    candidates: dict[str, int] = {}  # email -> best score

    # mailto links (highest confidence)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            email = href[7:].split("?")[0].strip().lower()
            if EMAIL_RE.fullmatch(email):
                s = _score_email(email, site_domain)
                if s >= 0:
                    candidates[email] = max(candidates.get(email, 0), s + 5)

    # Plain text regex scan
    for email in EMAIL_RE.findall(soup.get_text(" ")):
        email = email.lower().rstrip(".")
        if EMAIL_RE.fullmatch(email):
            s = _score_email(email, site_domain)
            if s >= 0:
                candidates[email] = max(candidates.get(email, 0), s)

    if not candidates:
        return []
    return sorted(candidates, key=lambda e: candidates[e], reverse=True)


def _find_email_for_lead(lead: Lead, session: requests.Session) -> Optional[str]:
    url = lead.website_url
    if not url or not url.startswith("http"):
        return None

    domain = urlparse(url).netloc.lstrip("www.")

    pages_to_try = [url]
    # Also probe /contact
    contact_url = urljoin(url.rstrip("/") + "/", "contact")
    pages_to_try.append(contact_url)

    for page_url in pages_to_try:
        if not _allowed(page_url, session):
            continue
        html = _fetch(page_url, session)
        if not html:
            continue
        emails = _extract_emails(html, domain)
        if emails:
            return emails[0]
        time.sleep(DELAY)

    return None


def enrich_with_emails(leads: List[Lead], max_leads: int = None) -> List[Lead]:
    targets = leads if max_leads is None else leads[:max_leads]
    session = _session()

    for i, lead in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] Enriching {lead.name}...")
        if lead.email:
            print(f"  already has email: {lead.email}")
            continue
        if not lead.website_url:
            print(f"  no website_url, skipping")
            continue

        email = _find_email_for_lead(lead, session)
        if email:
            lead.email = email
            print(f"  found: {email}")
        else:
            print(f"  no email found")
        time.sleep(DELAY)

    return leads

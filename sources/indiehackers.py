"""
Indie Hackers source — fetches recently approved products from the IH product index.

Indie Hackers is a client-side Ember.js app with no public REST API, but their
frontend embeds a read-only Algolia search key that we can query directly against
the products index. Each hit includes the product name, tagline, reported MRR,
Twitter handle, and external website URL — everything needed to populate a Lead
without any HTML scraping. Pagination is handled automatically so callers can
request up to 200 results across multiple Algolia pages. The `must_have_handle`
flag filters out products with no Twitter/X presence before they hit the caller,
keeping the lead list actionable.
"""

import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List

from sources.base import BaseSource, Lead

ALGOLIA_APP_ID = "N86T1R3OWZ"
ALGOLIA_KEY = "5140dac5e87f47346abbda1a34ee70c3"  # public search-only key embedded in IH frontend
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/products/query"

IH_PRODUCT_URL = "https://www.indiehackers.com/product/{slug}"


def _extract_category(tags: list) -> str:
    """Pull the first vertical-* tag and strip the prefix."""
    for tag in tags:
        if tag.startswith("vertical-"):
            return tag[len("vertical-"):]
    return ""


class IndieHackersSource(BaseSource):
    name = "indiehackers"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Hunter/1.0 (https://github.com/BilgeRat8963/Hunter)",
            "X-Algolia-Application-Id": ALGOLIA_APP_ID,
            "X-Algolia-API-Key": ALGOLIA_KEY,
        })

    def fetch(
        self,
        days: int = 21,
        limit: int = 100,
        must_have_handle: bool = False,
    ) -> List[Lead]:
        """
        Fetch recently-approved products from Indie Hackers.

        Args:
            days: How many days back to look (filters by approvedTimestamp)
            limit: Max products to return
            must_have_handle: When True, only return leads with a non-empty handle

        Returns:
            List of Lead objects.
        """
        cutoff_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)

        hits_per_page = min(limit, 200)
        leads = []
        page = 0

        while len(leads) < limit:
            time.sleep(2)  # polite rate limit between requests

            payload = {
                "query": "",
                "hitsPerPage": hits_per_page,
                "page": page,
                "numericFilters": [f"approvedTimestamp>{cutoff_ms}"],
                "attributesToRetrieve": [
                    "name", "tagline", "websiteUrl", "twitterHandle",
                    "revenue", "approvedTimestamp", "productId", "objectID", "_tags",
                ],
                "attributesToHighlight": [],
            }

            resp = self.session.post(ALGOLIA_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            hits = data.get("hits", [])
            if not hits:
                break

            for hit in hits:
                if len(leads) >= limit:
                    break

                twitter = (hit.get("twitterHandle") or "").strip().lstrip("@")
                if must_have_handle and not twitter:
                    continue

                revenue = hit.get("revenue")
                revenue_score = int(revenue) if revenue is not None else 0

                slug = hit.get("productId") or hit.get("objectID", "")
                source_url = IH_PRODUCT_URL.format(slug=slug) if slug else ""

                leads.append(Lead(
                    name=hit.get("name", ""),
                    handle=twitter,
                    source=self.name,
                    source_url=source_url,
                    website_url=(hit.get("websiteUrl") or "").strip(),
                    description=hit.get("tagline", ""),
                    score=revenue_score,
                    category=_extract_category(hit.get("_tags") or []),
                ))

            total_pages = data.get("nbPages", 1)
            page += 1
            if page >= total_pages:
                break

        return leads[:limit]

"""
HackerNews source — fetches recent Show HN posts via the public HN Firebase API.

Show HN posts are the closest thing HN has to a product launch feed: founders
sharing something they built, open to feedback. This source pulls the current
Show HN story list from the Firebase endpoint, fetches each story's metadata,
and filters by post date and score range. The score range filter is intentional —
very low scores are likely spam or very early, very high scores tend to be
open-source libraries or tools from established companies, not individual indie
founders. Note that HN usernames are not Twitter handles; the `handle` field on
HN leads is left empty and should be enriched separately if needed.
"""

import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List

from sources.base import BaseSource, Lead

HN_BASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsSource(BaseSource):
    name = "hackernews"

    def fetch(
        self,
        days: int = 7,
        limit: int = 50,
        min_score: int = 5,
        max_score: int = 200,
        require_handle: bool = False,
    ) -> List[Lead]:
        """
        Fetch Show HN posts from the last N days, filtered by score range.

        Args:
            days: How many days back to look
            limit: Max number of top Show HN stories to scan
            min_score: Skip stories with fewer points (filters noise)
            max_score: Skip stories with more points (filters viral/big-company posts)
            require_handle: If True, skip leads with no social handle (always empty for HN)

        Returns:
            List of Lead objects.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_ts = cutoff.timestamp()

        resp = requests.get(f"{HN_BASE}/showstories.json", timeout=30)
        resp.raise_for_status()
        story_ids = resp.json()[:limit]

        leads = []
        for story_id in story_ids:
            time.sleep(0.1)

            item_resp = requests.get(f"{HN_BASE}/item/{story_id}.json", timeout=30)
            item_resp.raise_for_status()
            story = item_resp.json()

            if not story or story.get("type") != "story":
                continue

            title = story.get("title", "")
            if not title.lower().startswith("show hn:"):
                continue

            posted_ts = story.get("time", 0)
            if posted_ts < cutoff_ts:
                continue

            score = story.get("score", 0)
            if score < min_score or score > max_score:
                continue

            author = story.get("by", "")
            if require_handle and not author:
                continue

            url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"

            # Strip "Show HN: " prefix (case-insensitive, preserve rest of casing)
            description = title[len("Show HN: "):] if title.lower().startswith("show hn: ") else title[len("Show HN:"):]

            leads.append(Lead(
                name=author,
                handle="",
                source=self.name,
                source_url=url,
                description=description,
                score=score,
                category="",
            ))

        return leads

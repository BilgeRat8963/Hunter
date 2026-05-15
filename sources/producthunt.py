"""
ProductHunt source — fetches recent product launches via the ProductHunt GraphQL API.

Requires a PRODUCTHUNT_TOKEN in your .env file (get one at producthunt.com/v2/oauth/applications).
Each API call returns up to 50 launches sorted by vote count; the `max_score` filter removes
large-company launches that wouldn't be indie founders. The source maps makers (the people
who built the product) onto the Lead schema, preferring makers who have a Twitter handle so
the lead is immediately reachable. Only the first maker per product is emitted — for the
purposes of cold outreach, reaching one person per product is enough.
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from typing import List
from dotenv import load_dotenv

from sources.base import BaseSource, Lead

load_dotenv()

PH_API_URL = "https://api.producthunt.com/v2/api/graphql"
PH_TOKEN = os.getenv("PRODUCTHUNT_TOKEN")


class ProductHuntSource(BaseSource):
    name = "producthunt"

    def __init__(self):
        if not PH_TOKEN:
            raise RuntimeError(
                "PRODUCTHUNT_TOKEN not found. Add it to your .env file."
            )
        self.headers = {
            "Authorization": f"Bearer {PH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def fetch(
        self,
        days: int = 1,
        category: str = None,
        limit: int = 50,
        max_score: int = 100,
        require_handle: bool = True,
    ) -> List[Lead]:
        """
        Fetch posts launched in the last N days, filtered for indie-scale launches.

        Args:
            days: How many days back to look (default 1 = today's launches)
            category: Topic slug to filter by (e.g. 'artificial-intelligence')
            limit: Max number of API results to scan (max 50 per API call)
            max_score: Skip launches with more votes than this (filters out funded/big launches)
            require_handle: Skip leads that don't have a Twitter handle (default True)

        Returns:
            List of Lead objects.
        """
        posted_after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = """
        query Posts($postedAfter: DateTime!, $topic: String, $first: Int!) {
            posts(postedAfter: $postedAfter, topic: $topic, first: $first, order: VOTES) {
                edges {
                    node {
                        name
                        tagline
                        url
                        votesCount
                        createdAt
                        topics {
                            edges {
                                node {
                                    slug
                                }
                            }
                        }
                        makers {
                            name
                            twitterUsername
                            username
                        }
                    }
                }
            }
        }
        """

        variables = {
            "postedAfter": posted_after,
            "topic": category,
            "first": min(limit, 50),
        }

        response = requests.post(
            PH_API_URL,
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"ProductHunt API returned {response.status_code}: {response.text}"
            )

        data = response.json()

        if "errors" in data:
            raise RuntimeError(f"ProductHunt API errors: {data['errors']}")

        leads = []
        seen_products = set()  # Track product URLs we've already processed
        posts = data.get("data", {}).get("posts", {}).get("edges", [])

        for edge in posts:
            post = edge["node"]
            votes = post.get("votesCount", 0)

            # Filter 1: skip big launches (likely funded companies, not indie)
            if votes > max_score:
                continue

            # Filter 2: dedupe — only process each product once
            product_url = post["url"]
            if product_url in seen_products:
                continue
            seen_products.add(product_url)

            topics = [t["node"]["slug"] for t in post.get("topics", {}).get("edges", [])]
            primary_category = topics[0] if topics else ""
            makers = post.get("makers", [])

            # Pick the first maker with a Twitter handle (most likely to be reachable)
            reachable_maker = None
            for maker in makers:
                if maker.get("twitterUsername"):
                    reachable_maker = maker
                    break

            # Filter 3: skip if we can't reach anyone
            if require_handle and not reachable_maker:
                continue

            if reachable_maker:
                leads.append(Lead(
                    name=reachable_maker.get("name", "") or post["name"],
                    handle=reachable_maker.get("twitterUsername", ""),
                    source=self.name,
                    source_url=product_url,
                    description=f"{post['name']} — {post.get('tagline', '')}",
                    score=votes,
                    category=primary_category,
                ))
            else:
                # No reachable maker but require_handle=False, log the product
                leads.append(Lead(
                    name=post["name"],
                    handle="",
                    source=self.name,
                    source_url=product_url,
                    description=post.get("tagline", ""),
                    score=votes,
                    category=primary_category,
                ))

        return leads
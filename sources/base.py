"""
Base class for all source modules.
Every source (ProductHunt, Indie Hackers, etc.) inherits from this and
implements the fetch() method. This ensures all sources return data in the
same shape, so hunter.py can treat them interchangeably.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Lead:
    """Common schema for a single lead, regardless of source."""
    name: str                    # Person or product name
    handle: str = ""             # X/Twitter or social handle, if available
    source: str = ""             # e.g. "producthunt", "indiehackers"
    source_url: str = ""         # Direct URL to the launch/post
    website_url: str = ""        # Product's own website
    description: str = ""        # One-line description of the product
    score: int = 0               # Votes, upvotes, or relevance score
    category: str = ""           # Category/tag from the source
    email: str = ""              # Best contact email found for this lead
    captured_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to a flat dict for CSV/JSON export."""
        return {
            "name": self.name,
            "handle": self.handle,
            "source": self.source,
            "source_url": self.source_url,
            "website_url": self.website_url,
            "description": self.description,
            "score": self.score,
            "category": self.category,
            "email": self.email,
            "captured_at": self.captured_at.isoformat(),
        }


class BaseSource:
    """
    Abstract base class. Every source module subclasses this and implements
    fetch() to return a list of Lead objects.
    """
    name: str = "base"

    def fetch(self, **filters) -> List[Lead]:
        """
        Fetch leads from this source.
        Subclasses must override this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement fetch()"
        )
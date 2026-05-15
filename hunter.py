"""Hunter — lead generation tool for indie founders."""

import sys
sys.stdout.reconfigure(encoding="utf-8")

# ProductHunt and HackerNews skipped for now (handle coverage problems)
# from sources.producthunt import ProductHuntSource
# from sources.hackernews import HackerNewsSource
from sources.indiehackers import IndieHackersSource
from sources.email_finder import enrich_with_emails

TARGET_HANDLES = [
    "joinmobius",
    "muhammad_a39750",
    "zhabibek4u",
    "DeveloperL92487",
    "inqeryai",
    "mmirman",
    "PixlCoreMedia",
    "AnmolRajSoni2",
    "cyntac_inc",
]


def main():
    print("=" * 60)
    print("SOURCE: Indie Hackers (21d, limit=100, must_have_handle)")
    print("=" * 60)

    ih = IndieHackersSource()
    leads = ih.fetch(days=21, limit=100, must_have_handle=True)
    print(f"Fetched {len(leads)} leads with handles.")

    target_set = {h.lower() for h in TARGET_HANDLES}
    targeted = [l for l in leads if l.handle.lower() in target_set]
    print(f"Matched {len(targeted)}/{len(TARGET_HANDLES)} target handles.\n")

    print("=" * 60)
    print("EMAIL ENRICHMENT (targeted leads)")
    print("=" * 60)
    enrich_with_emails(targeted)

    print()
    print("=" * 60)
    print("RESULTS: all targeted leads")
    print("=" * 60)
    for i, lead in enumerate(targeted, 1):
        mrr = f"${lead.score}/mo" if lead.score else "$0/mo"
        email_str = lead.email if lead.email else "(no email found)"
        print(f"{i}. {lead.name}  @{lead.handle}")
        print(f"   {lead.description}")
        print(f"   Email: {email_str}")
        print(f"   MRR: {mrr}  |  {lead.source_url}")
        print()

    found = sum(1 for l in targeted if l.email)
    print(f"Leads with handle+email: {found}/{len(targeted)}")
    print(f"Total emails found: {found}")


if __name__ == "__main__":
    main()
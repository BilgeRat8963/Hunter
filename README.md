# Hunter

A lightweight lead-generation tool that finds indie founders launching products right now - and surfaces their reachable contact info.

## Why

Most outreach tools are built for sales teams targeting companies. Hunter is built for a different problem: you want to reach the *founders* - people shipping solo products on Indie Hackers, launching on ProductHunt, and posting Show HN threads. They're publicly building, publicly reachable, but scattered across sources with no unified way to find them with a handle and an email. Hunter scrapes those sources, normalises everything into a common lead schema, and runs a lightweight email-discovery pass against each founder's own website so you have something to work with.

## How it works

- **Pluggable source modules** — each source in `sources/` inherits from `BaseSource` and implements `fetch()`. Adding a new source is one new file.
- **Common Lead schema** — every source returns the same `Lead` dataclass: name, handle, description, MRR, source URL, website URL, email. Downstream code never needs to know which source a lead came from.
- **Sources currently supported** — Indie Hackers (via public Algolia index embedded in their frontend), HackerNews Show HN (Firebase API), ProductHunt (GraphQL API, requires token).
- **Email enrichment** — `sources/email_finder.py` fetches each lead's own website (homepage + `/contact`), extracts emails from `mailto:` links and plain-text regex, scores candidates by prefix quality and domain match, and writes the best one back onto the Lead object.

## Sample output

```
============================================================
SOURCE: Indie Hackers (21d, limit=100, must_have_handle)
============================================================
Fetched 100 leads with handles.

[1/4] Enriching Mobius...
  found: contact@example.com
[2/4] Enriching Cloud Watchdog...
  found: hello@example.dev
[3/4] Enriching Valcr...
  no email found
[4/4] Enriching InQery...
  no email found

============================================================
RESULTS: all targeted leads
============================================================
1. Mobius  @joinmobius
   Describe a trade. Mobius builds, backtests, and trades it.
   Email: contact@example.com
   MRR: $750/mo  |  https://www.indiehackers.com/product/mobius

2. Cloud Watchdog  @zhabibek4u
   AWS cost watchdog — stop bills before they explode
   Email: hello@example.dev
   MRR: $1000/mo  |  https://www.indiehackers.com/product/cloud-watchdog

Leads with handle+email: 2/4
Total emails found: 2
```

## Install

```bash
git clone https://github.com/BilgeRat8963/Hunter.git
cd Hunter
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys (only needed for ProductHunt):

```bash
cp .env.example .env
```

## Usage

```bash
python hunter.py
```

Target specific handles by editing `TARGET_HANDLES` at the top of `hunter.py`. The IH scan window and result limit are controlled by the `fetch()` call arguments.

## Roadmap

- [ ] More sources: GitHub Trending, BetaList, Micro.blog
- [ ] Smarter email discovery: check LinkedIn bios, Twitter bios, WHOIS contact fields
- [ ] CSV export for every run saved to `output/`
- [ ] Optional Claude API integration — draft a personalised first-touch message for each lead automatically
- [ ] Deduplication across runs so you don't re-enrich leads you've already contacted

## Built by

[Ayden Cheer](https://aydencheersportfolio.vercel.app/)

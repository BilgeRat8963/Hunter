# Hunter

A lead-generation tool for finding indie founders launching products on ProductHunt and Indie Hackers.

## What it does

Scrapes recent launches and build-in-public posts, filters by category, and outputs a clean CSV of leads with name, handle, product description, and source URL.

## Setup

```bash
git clone https://github.com/BilgeRat8963/hunter.git
cd hunter
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

Then copy `.env.example` to `.env` and fill in your API keys.

## Usage

```bash
python hunter.py --source producthunt --category ai --days 3 --output leads.csv
```

## Architecture

Source modules are pluggable. Each source in `sources/` inherits from `BaseSource` and implements `fetch(filters)` returning a list of leads in a common schema. Adding a new source (HackerNews, GitHub trending, etc.) is one new file.

## Status

v1 — ProductHunt working, Indie Hackers in progress.
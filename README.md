# YouTube Political Ad Spend Analyzer

A Streamlit dashboard for tracking and analyzing political advertising spend on YouTube, powered by the [Google Political Ads Transparency Report](https://transparencyreport.google.com/political-ads/home).

## Features

- **Top Spenders** — ranked leaderboard of top 100 political advertisers with party inference
- **Daily Spend** — daily spend trend chart (max/min range)
- **By State** — geographic breakdown with per-state advertiser drill-down
- **Advertiser Insights** — per-advertiser spend trend, geographic strategy, targeting data
- **Platform Comparison** — YouTube vs CTV spend (upload AdImpact/iSpot export for real CTV data)
- **Spend Trends** — week-over-week momentum analysis, rising/falling advertisers

## Party Inference

4-tier system: Manual override → Curated dict (~150 entries) → Wikidata politician lookup → Declared scope text → Keywords → Unknown

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app auto-downloads the Google Political Ads transparency bundle (~277 MB) on first run and caches it in `.yt_cache/`.

## Data Sources

- `advertiser-weekly-spend.csv` — exact 2026 YTD spend per advertiser
- `advertiser-geo-spend.csv` — spend by state (all-time, filtered to 2026-active advertisers)
- `advertiser-declared-stats.csv` — declared scope text for party inference
- `creative-stats.csv` — individual ad creatives with targeting data (daily chart only)

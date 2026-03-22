# Political Ad Intelligence · 2026

A unified Streamlit dashboard for tracking political advertising spend across **YouTube**, **Meta (Facebook/Instagram)**, and **Snapchat** — with cross-platform candidate Match Up.

## Platforms

- **▶ YouTube** — Google Political Ads Transparency bundle (auto-downloaded, cached)
- **f Meta** — Facebook/Instagram Ad Library (programmatic API fetch or manual ZIP upload)
- **👻 Snap** — Snapchat Political Ads (Google Cloud Storage, cached)
- **⚡ Match Up** — Cross-platform candidate comparison with entity resolution

## Features

- **Top Spenders** — ranked leaderboard with party inference (Republican / Democrat / Other)
- **Daily/Weekly Spend** — trend charts with max/min range
- **By State** — geographic breakdown with per-state advertiser drill-down
- **Advertiser Insights** — per-advertiser spend trend, targeting data, creative previews
- **Cross-Platform Match Up** — unify advertiser names via alias system + fuzzy matching
- **XSS Protection** — all external advertiser names HTML-escaped before rendering

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app auto-downloads the Google Political Ads transparency bundle (~277 MB) on first run and caches it locally.

## Environment Variables

| Variable | Purpose |
|---|---|
| `META_TOKEN` | Meta Ad Library API token (optional — enables programmatic Meta fetch) |

Set via a `.env` file or Streamlit Cloud Secrets.

## Data Sources

- **YouTube**: Google Political Ads Transparency Report (auto-downloaded)
- **Meta**: Facebook Ad Library Report ZIP or Graph API (`ads_archive`)
- **Snapchat**: GCS political ads dump (`ad-manager-political-ads-dump`)

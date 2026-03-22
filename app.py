"""
YouTube Political Ad Spend — 2026
Streamlit App · Run: streamlit run youtube_spend_app.py
"""

import io, csv, datetime, zipfile, pathlib, json, re, html as _html, os
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import requests
from collections import defaultdict
import pandas as pd
import numpy as np
import plotly.express as px
from plotly.subplots import make_subplots

csv.field_size_limit(10 * 1024 * 1024)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Political Ad Intelligence · 2026",
    page_icon="▶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Config ───────────────────────────────────────────────────────────────────
BUNDLE_URL          = "https://storage.googleapis.com/political-csv/google-political-ads-transparency-bundle.zip"
CACHE_DIR           = pathlib.Path(__file__).parent / ".yt_cache"
CACHE_FILE          = CACHE_DIR / "google-political-ads.zip"
OVERRIDES_FILE      = CACHE_DIR / "party_overrides.json"
CACHE_MAX_AGE_HOURS = 24
TODAY               = datetime.date.today()
WINDOW_START        = datetime.date(2026, 1, 1)
ALIASES_FILE        = CACHE_DIR / "aliases.json"

# Meta Ad Library API (programmatic fetch — replaces manual ZIP download)
META_API_URL            = "https://graph.facebook.com/v25.0/ads_archive"
META_API_CACHE_ADV      = CACHE_DIR / "meta_api_advertisers.csv"
META_API_CACHE_LOC      = CACHE_DIR / "meta_api_locations.csv"
META_API_CACHE_META_JSON = CACHE_DIR / "meta_api_meta.json"
META_API_MAX_PAGES      = 200   # cap at 100 k ads to avoid runaway fetches

# Snapchat Political Ads
SNAP_ZIP_URL        = "https://storage.googleapis.com/ad-manager-political-ads-dump/political/2026/PoliticalAds.zip"
SNAP_CACHE_DIR      = pathlib.Path(__file__).parent / "snapwatch"
SNAP_CACHE_CSV      = SNAP_CACHE_DIR / ".snapwatch_cache.csv"
SNAP_CACHE_META     = SNAP_CACHE_DIR / ".snapwatch_cache.json"
SNAP_COLOR          = "#E5C100"

# ─── CSS — Pacewatch design language ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --bg:         #F6F5F2;
  --surface:    #FFFFFF;
  --sidebar-bg: #EFEDE8;
  --border:     #E2DDD7;
  --border2:    #CCC6BE;
  --accent:     #3374AA;
  --accent-lo:  #EBF3FA;
  --orange:     #F5902B;
  --orange-lo:  #FEF3E8;
  --text:       #1A1714;
  --dim:        #6B6560;
  --good:       #0A8A57;
  --good-bg:    #EDFAF3;
  --major:      #C63A1A;
  --major-bg:   #FFF1EE;
}

*, *::before, *::after { box-sizing: border-box; }
.stApp, .main, [data-testid="stAppViewContainer"] { background: var(--bg) !important; }
.block-container { max-width: 100% !important; padding: 2rem 2.25rem 1.75rem !important; }
body, h1, h2, h3, p, div, label, button, input, select, textarea {
  font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
  color: var(--text); -webkit-font-smoothing: antialiased;
}
/* Restore Material Symbols icon font — must beat the broad font rule above */
[data-testid="stIconMaterial"],
[data-testid="stSidebar"] [data-testid="stIconMaterial"] {
  font-family: 'Material Symbols Rounded' !important;
  font-feature-settings: normal !important;
  font-variation-settings: normal !important;
  visibility: visible !important;
  color: var(--dim) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: var(--sidebar-bg) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebarContent"] { padding-top: 1.25rem !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] div, [data-testid="stSidebar"] strong {
  color: var(--text) !important; font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color: var(--text) !important; font-size: 12px !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
  color: var(--dim) !important; font-size: 11.5px !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button {
  background: #F5902B !important; border: none !important;
  border-radius: 8px !important; width: 32px !important; height: 32px !important;
  min-width: unset !important; padding: 0 !important;
  box-shadow: 0 2px 8px rgba(245,144,43,.35) !important;
}
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px 20px !important;
  box-shadow: 0 1px 4px rgba(0,0,0,.05) !important;
}
[data-testid="stMetricLabel"] {
  font-size: 11px !important; font-weight: 700 !important;
  letter-spacing: .06em !important; text-transform: uppercase !important; color: var(--dim) !important;
}
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 700 !important; color: var(--text) !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 600 !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] { border-bottom: 2px solid var(--border) !important; gap: 0 !important; }
[data-testid="stTabs"] [role="tab"] {
  font-size: 13px !important; font-weight: 700 !important; color: var(--dim) !important;
  background: transparent !important; border: none !important;
  border-bottom: 2px solid transparent !important; border-radius: 0 !important;
  padding: 8px 18px 9px !important; margin-bottom: -2px !important; transition: color .15s !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: var(--text) !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: var(--orange) !important; border-bottom-color: var(--orange) !important; background: transparent !important;
}
[data-testid="stTabs"] [data-testid="stTabPanel"] { padding: 1rem 0 0 !important; }

/* ── Table ── */
.pw-table-wrap {
  overflow-x: auto; border-radius: 12px;
  border: 1px solid var(--border); background: var(--surface);
  box-shadow: 0 1px 6px rgba(0,0,0,.05);
}
.pw-table { width: 100%; border-collapse: collapse; font-size: 13px; font-family: 'Plus Jakarta Sans', sans-serif; }
.pw-table thead th {
  background: #FAFAF8; color: var(--dim);
  font-size: 10.5px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase;
  padding: 11px 14px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap;
}
.pw-table thead th:first-child { border-radius: 12px 0 0 0; }
.pw-table thead th:last-child  { border-radius: 0 12px 0 0; }
.pw-table tbody tr { border-bottom: 1px solid #F2EDE8; transition: background .1s; }
.pw-table tbody tr:last-child { border-bottom: none; }
.pw-table tbody tr:hover { background: #F0F6FB; }
.pw-table td { padding: 11px 14px; vertical-align: middle; color: var(--text); }
.pw-adv { font-weight: 600; font-size: 13px; color: var(--text); }
.pw-rank { font-size: 12px; font-weight: 700; color: var(--dim); }
.pw-rank-1 { font-size: 13px; font-weight: 700; color: var(--orange); }
.pw-sbar { margin-top: 5px; height: 3px; background: var(--border); border-radius: 3px; position: relative; }
.pw-sbar-fill { height: 3px; border-radius: 3px; position: absolute; top: 0; left: 0; background: var(--accent); }

/* ── Sidebar section label ── */
.sb-label {
  font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: var(--dim); margin: 0 0 8px;
}
.sb-sep {
  height: 1px; background: var(--border); margin: 18px 0;
}

/* ── Sidebar buttons — base styles ── */
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
  background: transparent !important; border: 1px solid var(--border) !important;
  border-radius: 8px !important; color: var(--dim) !important;
  font-size: 12px !important; font-weight: 500 !important;
  padding: 6px 12px !important; transition: all .15s !important;
  width: 100% !important;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--border2) !important; color: var(--text) !important;
}
/* Time-range active buttons → orange */
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
  background: var(--orange) !important; border: none !important;
  border-radius: 8px !important; color: #fff !important;
  font-size: 12px !important; font-weight: 700 !important;
  padding: 6px 12px !important; width: 100% !important;
}
/* Party button colors applied via JS (see components.html injection in main()) */

/* ── Party badges ── */
.badge {
  display: inline-flex; align-items: center;
  font-size: 10px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
  padding: 2px 8px; border-radius: 5px; font-family: 'Plus Jakarta Sans', sans-serif; white-space: nowrap;
}
.badge-d   { background: #EBF3FA; color: #1D4B7C; }
.badge-r   { background: #FFF1EE; color: #C63A1A; }
.badge-n   { background: #FEF3E8; color: #9A4A00; }
.badge-unk { background: #F0EDEA; color: var(--dim); }
.badge-ovr { outline: 2px solid var(--orange); outline-offset: 1px; cursor: default; }

/* ── Source pill ── */
.src-pill {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 500; color: var(--dim);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 3px 10px;
}
.src-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--orange); flex-shrink: 0; }

/* ── Sidebar collapse button ── */
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="collapsedControl"] button:hover {
  background: #fff !important; box-shadow: 0 2px 12px rgba(245,144,43,.4) !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="collapsedControl"] svg { color: #1A1714 !important; fill: #1A1714 !important; }
[data-testid="stSidebarCollapseButton"] svg path,
[data-testid="collapsedControl"] svg path { fill: #1A1714 !important; stroke: #1A1714 !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: 10px !important; margin-bottom: 10px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.04) !important;
}
[data-testid="stExpander"] summary { color: var(--text) !important; font-size: 13px !important; font-weight: 600 !important; }
[data-testid="stExpander"] summary svg { color: #5A5A5A !important; fill: #5A5A5A !important; stroke: #5A5A5A !important; opacity: 1 !important; }
[data-testid="stExpander"] summary svg path { fill: #5A5A5A !important; stroke: #5A5A5A !important; }
[data-testid="stExpander"] summary svg polyline,
[data-testid="stExpander"] summary svg line { fill: none !important; stroke: #5A5A5A !important; stroke-width: 2.5px !important; }

/* ── Leaderboard party popovers ── */
/* Make popover buttons look like compact badge pills */
[data-testid="stPopover"] > button {
  border-radius: 5px !important; font-size: 10px !important; font-weight: 700 !important;
  letter-spacing: .05em !important; text-transform: uppercase !important;
  padding: 2px 10px !important; min-height: unset !important; height: auto !important;
  line-height: 1.6 !important; border: none !important;
  width: auto !important; min-width: unset !important;
}
/* Per-party colors via :has() on the adjacent marker div */
[data-testid="stVerticalBlockBorderWrapper"]:has(.lb-D) + [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] > button { background: #EBF3FA !important; color: #1D4B7C !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.lb-R) + [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] > button { background: #FFF1EE !important; color: #C63A1A !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.lb-N) + [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] > button { background: #FEF3E8 !important; color: #9A4A00 !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.lb-unk) + [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] > button { background: #F0EDEA !important; color: #6B6560 !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.lb-ovr) + [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPopover"] > button { outline: 2px solid #F5902B !important; outline-offset: 1px !important; }
/* Row separators */
[data-testid="stVerticalBlockBorderWrapper"]:has(.lb-row) + [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
  border-bottom: 1px solid #F2EDE8; padding: 4px 0;
}

/* ── Inputs ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  color: var(--text) !important; border-radius: 8px !important;
  box-shadow: 0 1px 2px rgba(0,0,0,.04) !important;
}
button[kind="primary"] {
  background: var(--accent) !important; color: #fff !important;
  border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important;
}
button[kind="secondary"] {
  background: var(--orange-lo) !important; border: 1.5px solid var(--orange) !important;
  color: var(--orange) !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important;
}

hr { border-color: var(--border) !important; margin: 1.25rem 0 !important; }
.stAlert { background: var(--surface) !important; border-color: var(--border2) !important; }

/* ── File uploader — drag-and-drop zone ── */
[data-testid="stFileUploader"] {
  background: var(--surface) !important;
  border: 1.5px dashed var(--border2) !important;
  border-radius: 10px !important;
  padding: 4px !important; }
[data-testid="stFileUploader"] section { padding: 12px 16px !important; }
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
  background: var(--bg) !important; border-radius: 8px !important; }
[data-testid="stFileUploaderDropzoneInstructions"] p {
  font-size: 12px !important; color: var(--dim) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] [data-testid="stIconMaterial"] {
  color: var(--accent) !important; }
/* Uploaded file pill */
[data-testid="stFileUploaderFile"] {
  background: var(--bg) !important; border-radius: 6px !important;
  border: 1px solid var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# ─── State lookup tables ──────────────────────────────────────────────────────
US_STATE_NAMES = {
    'Alabama','Alaska','Arizona','Arkansas','California','Colorado',
    'Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho',
    'Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana',
    'Maine','Maryland','Massachusetts','Michigan','Minnesota',
    'Mississippi','Missouri','Montana','Nebraska','Nevada',
    'New Hampshire','New Jersey','New Mexico','New York',
    'North Carolina','North Dakota','Ohio','Oklahoma','Oregon',
    'Pennsylvania','Rhode Island','South Carolina','South Dakota',
    'Tennessee','Texas','Utah','Vermont','Virginia','Washington',
    'West Virginia','Wisconsin','Wyoming','District of Columbia',
}
STATE_NAMES_BY_ABBR = {
    'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas',
    'CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware',
    'FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho',
    'IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas',
    'KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland',
    'MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi',
    'MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada',
    'NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York',
    'NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma',
    'OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island',
    'SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas',
    'UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington',
    'WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'District of Columbia',
}

# ─────────────────────────────────────────────────────────────────────────────
# PARTY INFERENCE
# Tier 0 (user override) → Tier 1 (candidate name) → Tier 2 (curated) →
# Tier 2b (declared scope) → Tier 3 (keywords) → Tier 4 (unknown)
# ─────────────────────────────────────────────────────────────────────────────

# Tier 1 — known candidate last names (2026 cycle + recent high-profile races)
# Keys are lowercase last names or "firstname lastname" for disambiguation.
CANDIDATE_PARTY: dict[str, str] = {
    # ── 2026 Senate candidates ────────────────────────────────────────────────
    "ossoff": "D"                           ,  "warnock": "D",
    "fetterman": "D"                        ,  "boebert": "R",
    "gaetz": "R"                            ,  "desantis": "R",
    "whitmer": "D"                          ,  "pritzker": "D",
    "newsom": "D"                           ,  "ron johnson": "R",
    "tommy tuberville": "R"                 ,  "ted cruz": "R",
    "lindsey graham": "R"                   ,  "john cornyn": "R",
    "tom cotton": "R"                       ,  "mark kelly": "D",
    "raphael warnock": "D"                  ,  "jon ossoff": "D",
    "john fetterman": "D"                   ,  "jacky rosen": "D",
    "ruben gallego": "D"                    ,  "adam schiff": "D",
    "elissa slotkin": "D"                   ,  "lisa blunt rochester": "D",
    "andy kim": "D"                         ,  "chris murphy": "D",
    "brian schatz": "D"                     ,  "mazie hirono": "D",
    "martin heinrich": "D"                  ,  "ben ray lujan": "D",
    "jeff merkley": "D"                     ,  "ron wyden": "D",
    "maria cantwell": "D"                   ,  "patty murray": "D",
    "sherrod brown": "D"                    ,  "tammy baldwin": "D",
    "bob casey": "D"                        ,  "debbie stabenow": "D",
    "gary peters": "D"                      ,  "amy klobuchar": "D",
    "tina smith": "D"                       ,  "angus king": "D",
    "bernie sanders": "D"                   ,  "dave mccormick": "R",
    "eric schmitt": "R"                     ,  "mike braun": "R",
    "pete ricketts": "R"                    ,  "kevin cramer": "R",
    "john hoeven": "R"                      ,  "john thune": "R",
    "mike rounds": "R"                      ,  "tim scott": "R",
    "bill hagerty": "R"                     ,  "marsha blackburn": "R",
    "john barrasso": "R"                    ,  "cynthia lummis": "R",
    "steve daines": "R"                     ,  "jim risch": "R",
    "mike crapo": "R"                       ,  "mike lee": "R",
    "mitt romney": "R"                      ,  "joni ernst": "R",
    "chuck grassley": "R"                   ,  "roger marshall": "R",
    "jerry moran": "R"                      ,  "mitch mcconnell": "R",
    "rand paul": "R"                        ,  "shelley moore capito": "R",
    # ── 2026 House — Democratic members & candidates ──────────────────────────
    "hakeem jeffries": "D"                  ,  "katherine clark": "D",
    "pete aguilar": "D"                     ,  "nancy pelosi": "D",
    "steny hoyer": "D"                      ,  "jim clyburn": "D",
    "alexandria ocasio-cortez": "D"         ,  "ocasio-cortez": "D",
    "ilhan omar": "D"                       ,  "rashida tlaib": "D",
    "ayanna pressley": "D"                  ,  "pramila jayapal": "D",
    "ro khanna": "D"                        ,  "maxwell frost": "D",
    "greg casar": "D"                       ,  "summer lee": "D",
    "becca balint": "D"                     ,  "jasmine crockett": "D",
    "delia ramirez": "D"                    ,  "jamaal bowman": "D",
    "marie gluesenkamp perez": "D"          ,  "jared golden": "D",
    "don davis": "D"                        ,  "angie craig": "D",
    "sharice davids": "D"                   ,  "susan wild": "D",
    "matt cartwright": "D"                  ,  "chris deluzio": "D",
    "emilia sykes": "D"                     ,  "marcy kaptur": "D",
    "eric sorensen": "D"                    ,  "lauren underwood": "D",
    "hilary scholten": "D"                  ,  "tom suozzi": "D",
    "pat ryan": "D"                         ,  "mike levin": "D",
    "susie lee": "D"                        ,  "steven horsford": "D",
    "vicente gonzalez": "D"                 ,  "henry cuellar": "D",
    "lucy mcbath": "D"                      ,  "nikema williams": "D",
    "sanford bishop": "D"                   ,  "debbie mucarsel-powell": "D",
    "val demings": "D"                      ,  "lori chavez-deRemer": "R",
    "kaiali'i kahele": "D"                  ,  "keikilani kahele": "D",
    "yadira caraveo": "D"                   ,  "dave min": "D",
    "katie porter": "D"                     ,  "adam gray": "D",
    "rudy salas": "D"                       ,  "colin allred": "D",
    "greg landsman": "D"                    ,  "abigail spanberger": "D",
    "jennifer wexton": "D"                  ,  "elaine luria": "D",
    "jen kiggans": "R"                      ,  "maxine waters": "D",
    "eric swalwell": "D"                    ,  "ted lieu": "D",
    "linda sanchez": "D"                    ,  "norma torres": "D",
    "raul ruiz": "D"                        ,  "salud carbajal": "D",
    "julia brownley": "D"                   ,  "jimmy gomez": "D",
    "robert garcia": "D"                    ,  "sydney kamlager-dove": "D",
    "barbara lee": "D"                      ,  "mark desaulnier": "D",
    "john garamendi": "D"                   ,  "ami bera": "D",
    "doris matsui": "D"                     ,  "jerry mcnerney": "D",
    "josh harder": "D"                      ,  "anna eshoo": "D",
    "zoe lofgren": "D"                      ,  "jackie speier": "D",
    "jared huffman": "D"                    ,  "mike thompson": "D",
    "mark takano": "D"                      ,  "lou correa": "D",
    "alan lowenthal": "D"                   ,  "nanette barragan": "D",
    "jimmy panetta": "D"                    ,  "sara jacobs": "D",
    "scott peters": "D"                     ,  "brad sherman": "D",
    "tony cardenas": "D"                    ,  "judy chu": "D",
    "grace napolitano": "D"                 ,  "adam smith": "D",
    "derek kilmer": "D"                     ,  "suzan delbene": "D",
    "rick larsen": "D"                      ,  "kim schrier": "D",
    "gerry connolly": "D"                   ,  "don beyer": "D",
    "bobby scott": "D"                      ,  "morgan griffith": "R",
    "stacey plaskett": "D"                  ,  "del. plaskett": "D",
    "sheila jackson lee": "D"               ,  "al green": "D",
    "sylvester turner": "D"                 ,  "lloyd doggett": "D",
    "joaquin castro": "D"                   ,  "marc veasey": "D",
    "eddie bernice johnson": "D"            ,  "veronica escobar": "D",
    "sylvia garcia": "D"                    ,  "bennie thompson": "D",
    "bobby rush": "D"                       ,  "danny davis": "D",
    "jan schakowsky": "D"                   ,  "brad schneider": "D",
    "bill foster": "D"                      ,  "chuy garcia": "D",
    "sean casten": "D"                      ,  "bill pascrell": "D",
    "josh gottheimer": "D"                  ,  "mikie sherrill": "D",
    "frank pallone": "D"                    ,  "bonnie watson coleman": "D",
    "donald payne": "D"                     ,  "albio sires": "D",
    "brendan boyle": "D"                    ,  "dwight evans": "D",
    "madeleine dean": "D"                   ,  "mary gay scanlon": "D",
    "chrissy houlahan": "D"                 ,  "jim langevin": "D",
    "david cicilline": "D"                  ,  "seth magaziner": "D",
    "jake auchincloss": "D"                 ,  "lori trahan": "D",
    "jim mcgovern": "D"                     ,  "bill keating": "D",
    "stephen lynch": "D"                    ,  "richard neal": "D",
    "john larson": "D"                      ,  "rosa delauro": "D",
    "jahana hayes": "D"                     ,  "joe courtney": "D",
    "jim himes": "D"                        ,  "paul tonko": "D",
    "antonio delgado": "D"                  ,  "mondaire jones": "D",
    "sean patrick maloney": "D"             ,  "grace meng": "D",
    "nydia velazquez": "D"                  ,  "carolyn maloney": "D",
    "yvette clarke": "D"                    ,  "jerry nadler": "D",
    "adriano espaillat": "D"                ,  "alexandria ocasio": "D",
    "eliot engel": "D"                      ,  "nita lowey": "D",
    "jose serrano": "D"                     ,  "charles rangel": "D",
    "dina titus": "D"                       ,  "mark pocan": "D",
    "gwen moore": "D"                       ,  "ron kind": "D",
    # ── 2026 House — Republican members & candidates ──────────────────────────
    "mike johnson": "R"                     ,  "steve scalise": "R",
    "tom emmer": "R"                        ,  "elise stefanik": "R",
    "richard hudson": "R"                   ,  "guy reschenthaler": "R",
    "jim jordan": "R"                       ,  "marjorie taylor greene": "R",
    "taylor greene": "R"                    ,  "matt gaetz": "R",
    "lauren boebert": "R"                   ,  "andy biggs": "R",
    "paul gosar": "R"                       ,  "eli crane": "R",
    "chip roy": "R"                         ,  "bob good": "R",
    "warren davidson": "R"                  ,  "scott perry": "R",
    "ralph norman": "R"                     ,  "diana harshbarger": "R",
    "mary miller": "R"                      ,  "barry moore": "R",
    "andrew clyde": "R"                     ,  "madison cawthorn": "R",
    "dan bishop": "R"                       ,  "jeff duncan": "R",
    "mike lawler": "R"                      ,  "marc molinaro": "R",
    "george santos": "R"                    ,  "brandon williams": "R",
    "ryan mackenzie": "R"                   ,  "rob bresnahan": "R",
    "tom barrett": "R"                      ,  "derrick van orden": "R",
    "juan ciscomani": "R"                   ,  "david schweikert": "R",
    "john duarte": "R"                      ,  "david valadao": "R",
    "mike garcia": "R"                      ,  "michelle steel": "R",
    "young kim": "R"                        ,  "ken calvert": "R",
    "brian fitzpatrick": "R"                ,  "don bacon": "R",
    "david joyce": "R"                      ,  "anthony gonzalez": "R",
    "mike turner": "R"                      ,  "brad wenstrup": "R",
    "steve chabot": "R"                     ,  "cliff bentz": "R",
    "val hoyle": "D"                        ,  "ben cline": "R",
    "rob wittman": "R"                      ,  "kevin mccarthy": "R",
    "devin nunes": "R"                      ,  "will hurd": "R",
    "adam kinzinger": "R"                   ,  "liz cheney": "R",
    "peter meijer": "R"                     ,  "fred upton": "R",
    "tom rice": "R"                         ,  "john katko": "R",
    "jaime herrera beutler": "R"            ,  "dan newhouse": "R",
    "michael burgess": "R"                  ,  "kay granger": "R",
    "beth van duyne": "R"                   ,  "ronny jackson": "R",
    "august pfluger": "R"                   ,  "michael cloud": "R",
    "jodey arrington": "R"                  ,  "randy weber": "R",
    "troy nehls": "R"                       ,  "jake ellzey": "R",
    "pete sessions": "R"                    ,  "lance gooden": "R",
    "brian babin": "R"                      ,  "louie gohmert": "R",
    "sam graves": "R"                       ,  "jason smith": "R",
    "blaine luetkemeyer": "R"               ,  "mark green": "R",
    "tim burchett": "R"                     ,  "chuck fleischmann": "R",
    "scott desJarlais": "R"                 ,  "john rose": "R",
    "david kustoff": "R"                    ,  "mike rogers": "R",
    "mo brooks": "R"                        ,  "gary palmer": "R",
    "robert aderholt": "R"                  ,  "jerry carl": "R",
    "mike kelly": "R"                       ,  "lloyd smucker": "R",
    "dan meuser": "R"                       ,  "fred keller": "R",
    "john joyce": "R"                       ,  "gt thompson": "R",
    "greg murphy": "R"                      ,  "virginia foxx": "R",
    "patrick mchenry": "R"                  ,  "tim moore": "R",
    "jeff jackson": "D"                     ,  "kathy manning": "D",
    "alma adams": "D"                       ,  "david price": "D",
    "butterfield": "D"                      ,  "buddy carter": "R",
    "drew ferguson": "R"                    ,  "rick allen": "R",
    "austin scott": "R"                     ,  "tom graves": "R",
    "barry loudermilk": "R"                 ,  "doug collins": "R",
    "jody hice": "R"                        ,  "marjorie taylor": "R",
    "bill huizenga": "R"                    ,  "john moolenaar": "R",
    "jack bergman": "R"                     ,  "lisa mcclain": "R",
    "tim walberg": "R"                      ,  "bill posey": "R",
    "kat cammack": "R"                      ,  "neal dunn": "R",
    "john rutherford": "R"                  ,  "dan webster": "R",
    "gus bilirakis": "R"                    ,  "scott franklin": "R",
    "vern buchanan": "R"                    ,  "greg steube": "R",
    "brian mast": "R"                       ,  "mario diaz-balart": "R",
    "carlos gimenez": "R"                   ,  "maria elvira salazar": "R",
    "tom cole": "R"                         ,  "kevin hern": "R",
    "markwayne mullin": "R"                 ,  "frank lucas": "R",
    "stephanie bice": "R"                   ,  "russ fulcher": "R",
    "mike simpson": "R"                     ,  "cathy mcmorris rodgers": "R",
    "matt rosendale": "R"                   ,  "ryan zinke": "R",
    "dusty johnson": "R"                    ,  "kristi noem": "R",
    "jenniffer gonzalez": "R"               ,  "aumua amata": "R",
}
CURATED_PARTY: dict[str, str] = {
    # ── Democratic ───────────────────────────────────────────────────────────
    "dccc": "D",                                    "democratic congressional campaign": "D",
    "dscc": "D",                                    "democratic senatorial campaign": "D",
    "democratic national committee": "D",
    "senate majority pac": "D",                     "house majority pac": "D",
    "priorities usa": "D",                          "american bridge": "D",
    "emily's list": "D",                            "emilys list": "D",
    "actblue": "D",                                 "swing left": "D",
    "moveon": "D",                                  "move on": "D",
    "indivisible": "D",                             "future forward": "D",
    "planned parenthood action": "D",               "naral": "D",
    "for our future": "D",                          "america votes": "D",
    "lincoln project": "D",                         "bold pac": "D",
    "progressive turnout project": "D",             "end citizens united": "D",
    "win justice": "D",                             "new democratic pac": "D",
    "democratic governors association": "D",        "dlcc": "D",
    "democratic legislative campaign": "D",         "house democratic": "D",
    "senate democratic": "D",                       "democratic party": "D",
    "everytown": "D",                               "moms demand": "D",
    "giffords pac": "D",                            "march for our lives": "D",
    "league of conservation voters": "D",           "lcv ": "D",
    "sierra club": "D",                             "latino victory": "D",
    "color of change": "D",                         "voto latino": "D",
    "when we all vote": "D",
    "seiu ": "D",                                   "service employees international union": "D",
    "afscme": "D",                                  "national education association": "D",
    "american federation of teachers": "D",         "unite here": "D",
    "united auto workers": "D",                     "uaw ": "D",
    "communications workers of america": "D",       "ibew": "D",
    "afl-cio": "D",                                 "afl cio": "D",
    "run for something": "D",                       "way to win": "D",
    "ff pac": "D",                                  "sister district": "D",
    # ── Republican ───────────────────────────────────────────────────────────
    "nrcc": "R",                                    "national republican congressional": "R",
    "nrsc": "R",                                    "national republican senatorial": "R",
    "republican national committee": "R",
    "congressional leadership fund": "R",           "senate leadership fund": "R",
    "american crossroads": "R",                     "crossroads gps": "R",
    "club for growth": "R",                         "americans for prosperity": "R",
    "freedom partners": "R",                        "heritage action": "R",
    "heritage foundation": "R",                     "tea party patriots": "R",
    "make america great again": "R",                "america first pac": "R",
    "america first action": "R",                    "save america": "R",
    "45pac": "R",                                   "45 pac": "R",
    "never back down": "R",                         "nra ": "R",
    "national rifle association": "R",              "gun owners of america": "R",
    "susan b. anthony": "R",                        "susan b anthony": "R",
    "national right to life": "R",                  "march for life": "R",
    "concerned women for america": "R",             "family research council": "R",
    "american conservative union": "R",             "cpac": "R",
    "turning point usa": "R",                       "turning point action": "R",
    "tpusa": "R",                                   "young america's foundation": "R",
    "young americans foundation": "R",              "republican governors association": "R",
    "rga ": "R",                                    "republican state leadership": "R",
    "rslc": "R",                                    "republican party": "R",
    "winning for america": "R",                     "america pac": "R",
    "freedomworks": "R",                            "freedom works": "R",
    "one nation": "R",                              "american action network": "R",
    "american action fund": "R",                    "45committee": "R",
    "45 committee": "R",                            "job creators network": "R",
    "citizens united": "R",                         "judicial crisis network": "R",
    "judicial confirmation network": "R",           "faith and freedom coalition": "R",
    "federation for american immigration reform": "R", "fair immigration": "R",
    "susan b. anthony list": "R",                   "nrsc ": "R",
    "republican jewish coalition": "R",             "rjc ": "R",
    "american majority": "R",                       "hillpac": "R",
    "trump 47": "R",                                "trump save america": "R",
    "maga pac": "R",                                "restore the future": "R",
    "right to rise": "R",                           "jeb bush": "R",
    "karl rove": "R",                               "reagan": "R",
    "newt gingrich": "R",                           "gingrich": "R",
    "tea party express": "R",                       "liberty university": "R",
    # ── Republican governors / senators / prominent figures ───────────────────
    "greg abbott": "R",                             "abbott for governor": "R",
    "ron desantis": "R",                            "desantis": "R",
    "brian kemp": "R",                              "kemp for governor": "R",
    "glenn youngkin": "R",                          "youngkin": "R",
    "kim reynolds": "R",                            "mike dewine": "R",
    "bill lee": "R",                                "pete ricketts": "R",
    "doug burgum": "R",                             "tate reeves": "R",
    "kay ivey": "R",                                "kevin stitt": "R",
    "spencer cox": "R",                             "mark gordon": "R",
    "greg gianforte": "R",                          "brad little": "R",
    "jim justice": "R",                             "henry mcmaster": "R",
    "asa hutchinson": "R",                          "eric holcomb": "R",
    "mike parson": "R",                             "pete ricketts": "R",
    "ted cruz": "R",                                "marco rubio": "R",
    "tim scott": "R",                               "rick scott": "R",
    "josh hawley": "R",                             "tom cotton": "R",
    "john thune": "R",                              "mitch mcconnell": "R",
    "mcconnell": "R",                               "lindsey graham": "R",
    "rand paul": "R",                               "ron johnson": "R",
    "john cornyn": "R",                             "mike crapo": "R",
    "james risch": "R",                             "lisa murkowski": "R",
    "dan sullivan": "R",                            "chuck grassley": "R",
    "joni ernst": "R",                              "mike rounds": "R",
    "john hoeven": "R",                             "kevin cramer": "R",
    "cynthia lummis": "R",                          "john barrasso": "R",
    "steve daines": "R",                            "mike braun": "R",
    "todd young": "R",                              "rob portman": "R",
    "bill cassidy": "R",                            "john kennedy": "R",
    "roger wicker": "R",                            "cindy hyde-smith": "R",
    "shelby": "R",                                  "tommy tuberville": "R",
    "richard shelby": "R",                          "katie britt": "R",
    "roger marshall": "R",                          "jerry moran": "R",
    "pat toomey": "R",                              "mehmet oz": "R",
    "dr oz": "R",                                   "herschel walker": "R",
    "don bolduc": "R",                              "blake masters": "R",
    "adam laxalt": "R",                             "joe o'dea": "R",
    "ron johnson": "R",                             "eric greitens": "R",
    "eric schmitt": "R",                            "j.d. vance": "R",
    "jd vance": "R",                                "matt gaetz": "R",
    "marjorie taylor greene": "R",                  "mtg ": "R",
    "jim jordan": "R",                              "kevin mccarthy": "R",
    # ── Democratic governors / senators / prominent figures ───────────────────
    "gavin newsom": "D",                            "newsom": "D",
    "gretchen whitmer": "D",                        "whitmer": "D",
    "tony evers": "D",                              "josh shapiro": "D",
    "wes moore": "D",                               "andy beshear": "D",
    "beshear": "D",                                 "jay inslee": "D",
    "kate brown": "D",                              "tina kotek": "D",
    "kathy hochul": "D",                            "hochul": "D",
    "phil murphy": "D",                             "ned lamont": "D",
    "dan mckee": "D",                               "maura healey": "D",
    "michelle lujan grisham": "D",                  "laura kelly": "D",
    "tim walz": "D",                                "pritzker": "D",
    "jb pritzker": "D",                             "andy cuomo": "D",
    "raphael warnock": "D",                         "warnock": "D",
    "jon ossoff": "D",                              "ossoff": "D",
    "mark kelly": "D",                              "kyrsten sinema": "N",
    "sinema": "N",                                  "joe manchin": "N",
    "manchin": "N",                                 "bernie sanders": "D",
    "sanders for president": "D",                   "elizabeth warren": "D",
    "warren for senate": "D",                       "chuck schumer": "D",
    "schumer": "D",                                 "nancy pelosi": "D",
    "pelosi": "D",                                  "hakeem jeffries": "D",
    "amy klobuchar": "D",                           "klobuchar": "D",
    "cory booker": "D",                             "booker": "D",
    "sherrod brown": "D",                           "tester": "D",
    "jon tester": "D",                              "bob casey": "D",
    "tammy baldwin": "D",                           "debbie stabenow": "D",
    "gary peters": "D",                             "ben ray lujan": "D",
    "martin heinrich": "D",                         "michael bennet": "D",
    "john hickenlooper": "D",                       "maggie hassan": "D",
    "jeanne shaheen": "D",                          "chris murphy": "D",
    "richard blumenthal": "D",                      "jack reed": "D",
    "sheldon whitehouse": "D",                      "angus king": "D",
    "susan collins": "R",                           "patrick leahy": "D",
    "peter welch": "D",                             "tim kaine": "D",
    "mark warner": "D",                             "patty murray": "D",
    "maria cantwell": "D",                          "ron wyden": "D",
    "jeff merkley": "D",                            "dianne feinstein": "D",
    "alex padilla": "D",                            "laphonza butler": "D",
    "adam schiff": "D",                             "jacky rosen": "D",
    "catherine cortez masto": "D",                  "john fetterman": "D",
    "fetterman": "D",
    # ── Democratic ── additional ─────────────────────────────────────────────
    "nextgen": "D",                                 "next gen": "D",
    "tom steyer": "D",                              "michael bloomberg": "D",
    "bloomberg": "D",                               "george soros": "D",
    "open society": "D",                            "win senate": "D",
    "win the era": "D",                             "battleground texas": "D",
    "stacey abrams": "D",                           "fair fight": "D",
    "georgia democratic": "D",                      "pennsylvania democratic": "D",
    "michigan democratic": "D",                     "wisconsin democratic": "D",
    "arizona democratic": "D",                      "nevada democratic": "D",
    "north carolina democratic": "D",               "new georgia project": "D",
    "chispa": "D",                                  "sunrise movement": "D",
    "working families party": "D",                  "our revolution": "D",
    "justice democrats": "D",                       "brand new congress": "D",
    "blue wave": "D",                               "red to blue": "D",
    # ── Neutral / Bipartisan ─────────────────────────────────────────────────
    "aarp": "N",                                    "us chamber of commerce": "N",
    "chamber of commerce": "N",                     "business roundtable": "N",
    "national association of realtors": "N",        "realtors pac": "N",
    "no labels": "N",                               "issue one": "N",
    "forward party": "N",                           "bipartisan policy": "N",
    "phrma": "N",                                   "pharmaceutical research and": "N",
    "american hospital association": "N",           "american medical association": "N",
    "national association of manufacturers": "N",   "common cause": "N",
}

N_KEYWORDS = [
    'chamber of commerce', 'bipartisan', 'nonpartisan', 'no labels',
    'issue one', 'forward party', 'centrist', 'aarp ',
    'realtors pac', 'phrma', 'hospital association',
    'medical association', 'manufacturers association',
]
D_KEYWORDS = [
    'democratic', 'democrat ', 'democrats', 'dnc ', 'dccc', 'dscc',
    'actblue', 'house majority', 'senate majority', 'for progress',
    'move on', 'moveon', "emily's list", 'emilys list',
    'swing left', 'indivisible', 'progressive turnout',
    'priorities usa', 'american bridge', 'future forward',
    'planned parenthood', 'naral', 'pro-choice',
    'everytown', 'moms demand', 'giffords',
    'league of conservation voters', 'lcv ',
    'end citizens united', 'win justice', 'vote blue', 'bold pac',
]
R_KEYWORDS = [
    'republican', 'gop ', 'rnc ', 'nrcc', 'nrsc', 'maga', 'conservative',
    'freedom caucus', 'america first', 'trump', 'heritage',
    'right to life', 'pro-life', 'congressional leadership',
    'senate leadership', 'american crossroads', 'club for growth',
    'turning point', 'tpusa', 'freedom works', 'freedomworks',
    'tea party', 'gun rights', 'nra ',
    'save america', '45pac', 'never back down', 'winning for america',
]


# ─── Wikidata party lookup ────────────────────────────────────────────────────
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_CACHE    = pathlib.Path(".yt_cache/wikidata_parties.json")
WIKIDATA_TTL_DAYS = 7

# Map Wikidata party labels → internal codes
WIKIDATA_PARTY_CODES: dict[str, str] = {
    "Democratic Party": "D",
    "Democratic-Farmer-Labor Party": "D",   # Minnesota
    "Working Families Party": "D",
    "Democratic-NPL Party": "D",
    "Republican Party": "R",
    "Conservative Party of New York State": "R",
    "Independent": "N",
    "Libertarian Party": "N",
    "Green Party of the United States": "N",
    "No Labels": "N",
    "Reform Party of the United States of America": "N",
    "Constitution Party": "N",
}

# Covers: US Senators/Reps/President/VP + any position whose country is USA
# (captures state governors, AGs, Secretaries of State, state legislators, etc.)
WIKIDATA_SPARQL = """
SELECT DISTINCT ?personLabel ?partyLabel
WHERE {
  VALUES ?party { wd:Q29552 wd:Q29468 wd:Q327591 wd:Q327648 wd:Q148113
                  wd:Q637984 wd:Q1572502 }
  ?person wdt:P31 wd:Q5 ;
          wdt:P27 wd:Q30 ;
          wdt:P102 ?party ;
          wdt:P39  ?pos .
  { VALUES ?pos { wd:Q13217683 wd:Q13218630 wd:Q30461 wd:Q11696 }
  } UNION {
    ?pos wdt:P17 wd:Q30 .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
"""


def load_wikidata_parties() -> dict[str, str]:
    """
    Query Wikidata for US politicians → party code.
    Result is cached to disk for WIKIDATA_TTL_DAYS days.
    Returns {lowercase_full_name: 'D'|'R'|'N'}.
    """
    WIKIDATA_CACHE.parent.mkdir(parents=True, exist_ok=True)

    # Serve from disk cache if fresh
    if WIKIDATA_CACHE.exists():
        age_days = (datetime.datetime.now() -
                    datetime.datetime.fromtimestamp(WIKIDATA_CACHE.stat().st_mtime)).days
        if age_days < WIKIDATA_TTL_DAYS:
            try:
                with open(WIKIDATA_CACHE) as f:
                    return json.load(f)
            except Exception:
                pass

    try:
        resp = requests.get(
            WIKIDATA_ENDPOINT,
            params={"query": WIKIDATA_SPARQL, "format": "json"},
            headers={"User-Agent": "YTAdSpendApp/1.0 (political transparency tool)"},
            timeout=45,
        )
        resp.raise_for_status()
        bindings = resp.json().get("results", {}).get("bindings", [])
    except Exception as e:
        # Non-fatal: fall back to curated dict + keywords
        print(f"[wikidata] fetch failed: {e}")
        return {}

    result: dict[str, str] = {}
    for row in bindings:
        name  = row.get("personLabel", {}).get("value", "").strip()
        party = row.get("partyLabel",  {}).get("value", "").strip()
        code  = WIKIDATA_PARTY_CODES.get(party)
        if name and code and " " in name:          # require full name (2+ words)
            key = name.lower()
            # Don't overwrite if already set (first match wins — usually the current party)
            if key not in result:
                result[key] = code

    try:
        with open(WIKIDATA_CACHE, "w") as f:
            json.dump(result, f)
    except Exception:
        pass

    return result


@st.cache_data(show_spinner=False, ttl=datetime.timedelta(days=WIKIDATA_TTL_DAYS))
def get_wikidata_parties() -> dict[str, str]:
    return load_wikidata_parties()


def _text_to_party(text: str) -> str:
    """Tier 2+3 inference on any text string. Returns party code or '?'."""
    n = text.lower().strip()
    if n in CURATED_PARTY:
        return CURATED_PARTY[n]
    for key, party in CURATED_PARTY.items():
        if key in n:
            return party
    if any(k in n for k in N_KEYWORDS): return 'N'
    if any(k in n for k in D_KEYWORDS): return 'D'
    if any(k in n for k in R_KEYWORDS): return 'R'
    return '?'


_party_cache: dict = {}  # (name_lower, scope_lower, ov_id, wd_id) → (party, source)


def infer_party(
    name: str,
    declared_scope: str = "",
    overrides: dict | None = None,
    wikidata: dict | None = None,
) -> tuple[str, str]:
    """
    Returns (party_code, source_label).
    Tier 0 : manual override
    Tier 1 : curated candidate-name dict
    Tier 2 : curated committee/org dict + keywords on name
    Tier 2.5: Wikidata politician lookup (politician name as substring)
    Tier 2b : declared scope text
    Tier 4 : unknown
    Results are cached per (name, scope, overrides identity, wikidata identity)
    to avoid O(N²) substring scans on repeated calls.
    """
    cache_key = (name.strip().lower(), (declared_scope or "").strip().lower(),
                 id(overrides), id(wikidata))
    cached = _party_cache.get(cache_key)
    if cached is not None:
        return cached

    def _store(party: str, src: str) -> tuple[str, str]:
        result = (party, src)
        _party_cache[cache_key] = result
        return result

    # Tier 0
    if overrides and name in overrides:
        return _store(overrides[name], "Manual override")
    # Tier 1 — candidate name lookup
    n_lower = name.lower()
    for candidate, party in CANDIDATE_PARTY.items():
        if candidate in n_lower:
            return _store(party, "Candidate lookup")
    # Tier 2 — curated orgs + keywords
    p = _text_to_party(name)
    if p != '?':
        src = "Curated lookup" if any(k in n_lower for k in CURATED_PARTY) else "Keyword match"
        return _store(p, src)
    # Tier 2.5 — Wikidata politician names
    if wikidata:
        for politician, code in wikidata.items():
            if politician in n_lower:           # politician is already lowercase, 2+ words
                return _store(code, "Wikidata")
    # Tier 2b — declared scope text
    if declared_scope:
        p2 = _text_to_party(declared_scope)
        if p2 != '?':
            return _store(p2, "Declared scope")
    # Tier 4
    return _store('?', "No match")


# ─── Override persistence ─────────────────────────────────────────────────────
def load_overrides() -> dict:
    try:
        if OVERRIDES_FILE.exists():
            return json.loads(OVERRIDES_FILE.read_text())
    except Exception as e:
        print(f"[warn] Failed to load party overrides: {e}")
    return {}


def save_overrides(overrides: dict):
    CACHE_DIR.mkdir(exist_ok=True)
    OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2))
    _party_cache.clear()  # invalidate cached infer_party results


# ─── Download ─────────────────────────────────────────────────────────────────
def _zip_is_valid(path: pathlib.Path) -> bool:
    """Return True only if path exists and is a readable zip file."""
    try:
        if not path.exists():
            return False
        with zipfile.ZipFile(path) as zf:
            zf.namelist()          # minimal integrity check
        return True
    except Exception:
        return False

def download_bundle() -> pathlib.Path:
    CACHE_DIR.mkdir(exist_ok=True)

    # Serve from cache if fresh AND valid
    if CACHE_FILE.exists():
        age_h = (
            datetime.datetime.now()
            - datetime.datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        ).total_seconds() / 3600
        if age_h < CACHE_MAX_AGE_HOURS:
            if _zip_is_valid(CACHE_FILE):
                return CACHE_FILE
            else:
                CACHE_FILE.unlink(missing_ok=True)   # corrupt — delete and re-download

    st.info("Downloading Google Political Ads bundle (~277 MB). This only happens once per day.")
    progress = st.progress(0, text="Starting download…")
    tmp_file = CACHE_FILE.with_suffix(".tmp")
    try:
        r = requests.get(BUNDLE_URL, stream=True, timeout=300)
        r.raise_for_status()
        total      = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(tmp_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total
                    progress.progress(
                        pct,
                        text=f"Downloading… {pct*100:.0f}%  ({downloaded//1024//1024} / {total//1024//1024} MB)",
                    )
        # Validate before promoting
        if not _zip_is_valid(tmp_file):
            tmp_file.unlink(missing_ok=True)
            st.error("Download appears incomplete or corrupt. Please reload the page to retry.")
            st.stop()
        tmp_file.rename(CACHE_FILE)
        progress.progress(1.0, text="Download complete!")
    except Exception as exc:
        tmp_file.unlink(missing_ok=True)
        raise exc
    return CACHE_FILE


# ─── Fast data loaders ────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading advertiser & geographic data…")
def load_fast_data(zip_path_str: str, today_str: str) -> dict:
    """
    Scans three lightweight files (~77 MB uncompressed total):
      1. advertiser-weekly-spend     → exact 2026 YTD spend per advertiser
      2. advertiser-geo-spend        → exact spend per state (2026-active advertisers)
      3. advertiser-declared-stats   → declared scope text for enhanced party inference
    Runs in seconds; cached daily.
    """
    import csv as _csv
    _csv.field_size_limit(10 * 1024 * 1024)

    zip_path        = pathlib.Path(zip_path_str)
    adv_spend:      dict[str, float] = {}   # canon_name → total 2026 USD spend
    weekly_raw:     dict[str, dict]  = {}   # canon_name → {week_str → spend}
    adv_ids_2026:   set              = set()
    adv_id_to_name: dict[str, str]   = {}   # adv_id → canon_name
    _name_canon:    dict[str, str]   = {}   # lower_key → first-seen display name
    state_spend:     dict[str, float]        = {}
    state_adv_spend: dict[str, dict]         = {}   # state → {adv_name → spend}
    name_to_scope:   dict[str, str]          = {}

    with zipfile.ZipFile(zip_path) as zf:

        # ── 1. Weekly spend ────────────────────────────────────────────────────
        with zf.open("google-political-ads-advertiser-weekly-spend.csv") as raw:
            reader = _csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            for row in reader:
                adv_id = (row.get("Advertiser_ID") or "").strip()
                raw_name = (row.get("Advertiser_Name") or "").strip()
                if not raw_name:
                    continue
                # Canonicalise: first-seen capitalisation wins; all variants merge
                _key = raw_name.lower()
                if _key not in _name_canon:
                    _name_canon[_key] = raw_name
                name = _name_canon[_key]
                if adv_id:
                    adv_id_to_name[adv_id] = name          # track all IDs
                week = (row.get("Week_Start_Date") or "")[:10]
                if week < "2026-01-01":
                    continue
                try:
                    spend = float(row.get("Spend_USD") or 0)
                except (ValueError, TypeError):
                    spend = 0.0
                if spend > 0:
                    adv_spend[name] = adv_spend.get(name, 0.0) + spend
                    if name not in weekly_raw:
                        weekly_raw[name] = {}
                    weekly_raw[name][week] = weekly_raw[name].get(week, 0.0) + spend
                    if adv_id:
                        adv_ids_2026.add(adv_id)

        # ── 2. Geo spend (filtered to 2026-active advertisers) ─────────────────
        with zf.open("google-political-ads-advertiser-geo-spend.csv") as raw:
            reader = _csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            for row in reader:
                if (row.get("Country") or "").strip().upper() != "US":
                    continue
                adv_id = (row.get("Advertiser_ID") or "").strip()
                if adv_id not in adv_ids_2026:
                    continue
                state = (row.get("Country_Subdivision_Primary") or "").strip().upper()
                state = state.replace("US-", "")          # normalise "US-CA" → "CA"
                if len(state) != 2:
                    continue
                try:
                    spend = float(row.get("Spend_USD") or 0)
                except (ValueError, TypeError):
                    spend = 0.0
                state_spend[state] = state_spend.get(state, 0.0) + spend
                adv_name = adv_id_to_name.get(adv_id, "")
                if adv_name and spend > 0:
                    if state not in state_adv_spend:
                        state_adv_spend[state] = {}
                    state_adv_spend[state][adv_name] = (
                        state_adv_spend[state].get(adv_name, 0.0) + spend
                    )

        # ── 3. Declared stats ─────────────────────────────────────────────────
        with zf.open("google-political-ads-advertiser-declared-stats.csv") as raw:
            reader = _csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            for row in reader:
                region = (row.get("Region") or "")
                if not region.startswith("US"):
                    continue
                adv_id        = (row.get("Advertiser_ID") or "").strip()
                decl_name     = (row.get("Advertiser_Declared_Name") or "").strip()
                decl_scope    = (row.get("Advertiser_Declared_Scope") or "").strip()
                scope_text    = f"{decl_name} {decl_scope}".strip()
                canon_name    = adv_id_to_name.get(adv_id, "")
                if canon_name and scope_text:
                    name_to_scope[canon_name] = scope_text

    return {
        "adv_spend":      adv_spend,
        "weekly_raw":     weekly_raw,
        "state_spend":    state_spend,
        "state_adv_spend": {s: dict(v) for s, v in state_adv_spend.items()},
        "name_to_scope":  name_to_scope,
    }


@st.cache_data(show_spinner="Building daily chart — scanning creative stats (~1–2 min first run)…")
def load_daily_data(zip_path_str: str, today_str: str) -> dict:
    """
    Scans creative-stats.csv for daily spend data only.
    Cached daily; subsequent loads are instant.
    """
    import csv as _csv
    _csv.field_size_limit(10 * 1024 * 1024)

    zip_path     = pathlib.Path(zip_path_str)
    today        = datetime.date.fromisoformat(today_str)
    window_start = WINDOW_START
    daily        = defaultdict(lambda: {"min": 0.0, "max": 0.0})

    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("google-political-ads-creative-stats.csv") as raw:
            reader = _csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            for row in reader:
                if "US" not in (row.get("Regions") or ""):
                    continue
                if row.get("Ad_Type") != "VIDEO":
                    continue
                start_str = (row.get("Date_Range_Start") or "")[:10]
                end_str   = (row.get("Date_Range_End") or "")[:10]
                if not start_str:
                    continue
                try:
                    ad_start = datetime.date.fromisoformat(start_str)
                    ad_end   = datetime.date.fromisoformat(end_str) if end_str else ad_start
                    ad_end   = min(ad_end, today)
                    if ad_end < window_start or ad_start > today:
                        continue
                    spend_min = float(row.get("Spend_Range_Min_USD") or 0)
                    spend_max = float(row.get("Spend_Range_Max_USD") or 0)
                    overlap_start = max(ad_start, window_start)
                    overlap_end   = ad_end
                    total_days    = max((ad_end - ad_start).days + 1, 1)
                    overlap_days  = (overlap_end - overlap_start).days + 1
                    frac          = overlap_days / total_days
                    d_min = (spend_min * frac) / overlap_days
                    d_max = (spend_max * frac) / overlap_days
                    d = overlap_start
                    while d <= overlap_end:
                        key = d.isoformat()
                        daily[key]["min"] += d_min
                        daily[key]["max"] += d_max
                        d += datetime.timedelta(days=1)
                except Exception as e:
                    print(f"[warn] Skipped malformed creative row: {e}")
                    continue

    return {k: dict(v) for k, v in daily.items()}


@st.cache_data(show_spinner="Scanning ad creatives for this advertiser (one-time per advertiser, ~2 min)…")
def load_advertiser_creatives(zip_path_str: str, advertiser_name: str, today_str: str) -> dict:
    """
    Scan creative-stats.csv for a single advertiser.
    Cached per (advertiser, day) — instant on repeat visits.
    """
    import csv as _csv
    _csv.field_size_limit(10 * 1024 * 1024)

    ads: list[dict] = []
    age_counts:    dict[str, int] = {}
    gender_counts: dict[str, int] = {}

    with zipfile.ZipFile(zip_path_str) as zf:
        with zf.open("google-political-ads-creative-stats.csv") as raw:
            reader = _csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            for row in reader:
                if (row.get("Advertiser_Name") or "").strip() != advertiser_name:
                    continue
                for a in (row.get("Age_Targeting") or "").split(","):
                    a = a.strip()
                    if a:
                        age_counts[a] = age_counts.get(a, 0) + 1
                for g in (row.get("Gender_Targeting") or "").split(","):
                    g = g.strip()
                    if g:
                        gender_counts[g] = gender_counts.get(g, 0) + 1
                ads.append({
                    "url":      (row.get("Ad_URL") or "").strip(),
                    "type":     (row.get("Ad_Type") or "").strip(),
                    "start":    (row.get("Date_Range_Start") or "")[:10],
                    "end":      (row.get("Date_Range_End") or "")[:10],
                    "impr":     (row.get("Impressions") or "").strip(),
                    "spend":    (row.get("Spend_USD") or "").strip(),
                    "last_srv": (row.get("Last_Served_Timestamp") or "").strip()[:10],
                    "age":      (row.get("Age_Targeting") or "").strip(),
                    "gender":   (row.get("Gender_Targeting") or "").strip(),
                    "geo_inc":  (row.get("Geo_Targeting_Included") or "").strip(),
                })

    ads_sorted = sorted(ads, key=lambda x: x.get("last_srv", ""), reverse=True)
    return {
        "ads":           ads_sorted[:300],
        "total_ads":     len(ads),
        "age_counts":    age_counts,
        "gender_counts": gender_counts,
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────
def money(n: float) -> str:
    if n >= 1_000_000: return f"${n/1_000_000:.1f}M"
    if n >= 1_000:     return f"${n/1_000:.0f}K"
    return f"${n:.0f}"


def compute_trend(name: str, weekly_raw: dict) -> tuple:
    """
    Compare most recent two weeks of spend for an advertiser.
    Returns (last_spend, prev_spend, delta, pct_change).
    Uses last 2 weeks in the data regardless of date filter.
    """
    weeks_data = weekly_raw.get(name, {})
    if len(weeks_data) < 2:
        return (0.0, 0.0, 0.0, 0.0)
    sw = sorted(weeks_data.keys())
    last = weeks_data[sw[-1]]
    prev = weeks_data[sw[-2]]
    delta = last - prev
    pct   = (delta / prev * 100) if prev > 0 else 0.0
    return (last, prev, delta, pct)


PARTY_LABEL = {"D": "Democrat", "R": "Republican", "N": "Neutral", "?": "Unknown"}
PARTY_SHORT = {"D": "Dem",      "R": "Rep",         "N": "Neutral", "?": "Unknown"}
PARTY_CLASS = {"D": "badge-d",  "R": "badge-r",     "N": "badge-n", "?": "badge-unk"}


def badge_html(party: str, is_override: bool = False) -> str:
    ovr = " badge-ovr" if is_override else ""
    return (
        f'<span class="badge {PARTY_CLASS[party]}{ovr}" '
        f'title="{"Manual override active" if is_override else PARTY_LABEL[party]}">'
        f'{PARTY_SHORT[party]}</span>'
    )


# ─── CTV Upload Parser ─────────────────────────────────────────────────────────
CTV_CACHE_FILE = pathlib.Path(".yt_cache/ctv_upload.json")

_CTV_ADV_COLS   = ["advertiser", "advertiser_name", "advertiser name", "name",
                   "organization", "committee", "client", "buyer"]
_CTV_WEEK_COLS  = ["week", "week_start", "week_start_date", "date", "week start",
                   "week start date", "start_date", "start date", "period"]
_CTV_SPEND_COLS = ["spend", "spend_usd", "spend (usd)", "total_spend", "total spend",
                   "amount_spent", "amount spent", "cost", "total cost", "impressions cost",
                   "media_cost", "media cost", "gross_spend", "net_spend"]

def _find_col(headers: list[str], candidates: list[str]) -> str | None:
    """Case-insensitive best-match column finder."""
    h_lower = {h.lower().strip(): h for h in headers}
    for c in candidates:
        if c in h_lower:
            return h_lower[c]
    # Partial match fallback
    for c in candidates:
        for h_low, h_orig in h_lower.items():
            if c in h_low or h_low in c:
                return h_orig
    return None

def parse_ctv_upload(file_bytes: bytes, filename: str) -> tuple[dict, str]:
    """
    Parse an uploaded CTV CSV/XLSX into weekly_raw-compatible dict.
    Returns (data_dict, error_message). On success error_message is "".
    data_dict shape: {advertiser_name: {week_str (YYYY-MM-DD): spend_float}}
    """
    import io as _io
    try:
        if filename.lower().endswith((".xlsx", ".xls")):
            import openpyxl
            wb = openpyxl.load_workbook(_io.BytesIO(file_bytes), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            headers = [str(c).strip() if c is not None else "" for c in rows[0]]
            raw_rows = [dict(zip(headers, r)) for r in rows[1:]]
        else:
            import csv as _csv
            text = file_bytes.decode("utf-8-sig", errors="replace")
            reader = _csv.DictReader(_io.StringIO(text))
            raw_rows = list(reader)
            headers  = list(reader.fieldnames or [])

        adv_col   = _find_col(headers, _CTV_ADV_COLS)
        week_col  = _find_col(headers, _CTV_WEEK_COLS)
        spend_col = _find_col(headers, _CTV_SPEND_COLS)

        missing = [label for label, col in [("Advertiser", adv_col),
                                             ("Week/Date",  week_col),
                                             ("Spend",      spend_col)] if col is None]
        if missing:
            return {}, (f"Could not auto-detect columns: {', '.join(missing)}. "
                        f"Detected headers: {', '.join(headers[:12])}")

        data: dict[str, dict[str, float]] = {}
        skipped = 0
        for row in raw_rows:
            adv   = str(row.get(adv_col,   "") or "").strip()
            raw_w = str(row.get(week_col,  "") or "").strip()
            raw_s = str(row.get(spend_col, "") or "").strip().replace(",", "").replace("$", "")
            if not adv or not raw_w or not raw_s:
                skipped += 1
                continue
            # Normalise date → YYYY-MM-DD (week-start Monday)
            try:
                import re as _re
                # Handle various date formats
                raw_w = _re.sub(r"[\/\.]", "-", raw_w)
                parts = raw_w.split("-")
                if len(parts) == 3:
                    y, m, d = (int(p) for p in parts) if len(parts[0]) == 4 \
                               else (int(parts[2]), int(parts[0]), int(parts[1]))
                    dt = datetime.date(y, m, d)
                    # Snap to Monday (week start)
                    dt -= datetime.timedelta(days=dt.weekday())
                    week_str = dt.isoformat()
                else:
                    skipped += 1
                    continue
            except Exception as e:
                if skipped < 3:
                    print(f"[warn] Skipped malformed weekly-spend row: {e}")
                skipped += 1
                continue
            try:
                spend = float(raw_s)
            except ValueError:
                skipped += 1
                continue
            if spend <= 0:
                continue
            data.setdefault(adv, {})[week_str] = data.get(adv, {}).get(week_str, 0.0) + spend

        n_advs  = len(data)
        n_rows  = sum(len(v) for v in data.values())
        summary = f"Loaded {n_advs:,} advertisers · {n_rows:,} weekly data points"
        if skipped:
            summary += f" · {skipped} rows skipped"
        return data, summary

    except Exception as exc:
        return {}, f"Parse error: {exc}"

def save_ctv_upload(data: dict) -> None:
    CTV_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CTV_CACHE_FILE, "w") as f:
        json.dump(data, f)

def load_ctv_upload() -> dict:
    if CTV_CACHE_FILE.exists():
        try:
            with open(CTV_CACHE_FILE) as f:
                return json.load(f)
        except Exception as e:
            print(f"[warn] Failed to load CTV cache: {e}")
    return {}


# ─── Mock CTV Data ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_mock_ctv_data(zip_path_str: str, today_str: str) -> dict:
    """
    Deterministic mock CTV weekly spend, keyed identically to weekly_raw.
    ⚠️  PLACEHOLDER — replace with real AdImpact / CTV feed before production.
    Ratio per advertiser (CTV ÷ YouTube): 0.30 – 2.20, seeded from name hash.
    """
    import hashlib
    weekly_raw = load_fast_data(zip_path_str, today_str)["weekly_raw"]
    mock: dict = {}
    for adv_name, weeks in weekly_raw.items():
        seed  = int(hashlib.md5(adv_name.encode()).hexdigest()[:8], 16)
        ratio = 0.30 + (seed / 0xFFFFFFFF) * 1.90          # 0.30 → 2.20
        adv_mock: dict = {}
        for week, yt_spend in weeks.items():
            wk_seed = int(hashlib.md5((adv_name + week).encode()).hexdigest()[:8], 16)
            noise   = (wk_seed / 0xFFFFFFFF) * 0.70 - 0.35  # ±35%
            ctv_v   = yt_spend * ratio * (1.0 + noise)
            if ctv_v >= 500:
                adv_mock[week] = round(ctv_v, 2)
        if adv_mock:
            mock[adv_name] = adv_mock
    return mock


PLOTLY_LIGHT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#FAFAF8",
    font=dict(family="Plus Jakarta Sans, -apple-system, sans-serif", color="#6B6560", size=11),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#6B6560")),
    margin=dict(l=0, r=0, t=20, b=0),
)


# ─── Meta Ad Library helper functions ─────────────────────────────────────────

def parse_midpoint(s) -> float:
    """'lower_bound: 100, upper_bound: 199' → 149.5"""
    if not s or not isinstance(s, str):
        return 0.0
    lb = re.search(r"lower_bound:\s*(\d+)", s)
    ub = re.search(r"upper_bound:\s*(\d+)", s)
    if lb and ub:
        return (int(lb.group(1)) + int(ub.group(1))) / 2
    elif lb:
        return float(lb.group(1))
    return 0.0


def parse_json_field(s) -> list:
    """Safely parse JSON list field from Meta CSV.
    Meta exports these as bare comma-separated objects (no outer []), so we wrap them.
    """
    if not s or not isinstance(s, str) or s.strip() == "":
        return []
    try:
        result = json.loads("[" + s + "]")
        return result if isinstance(result, list) else [result]
    except Exception:
        try:
            result = json.loads(s)
            return result if isinstance(result, list) else [result]
        except Exception:
            return []


def classify_theme(text: str) -> str:
    """Classify ad creative into strategic themes."""
    if not text or not isinstance(text, str):
        return "Other"
    t = text.lower()
    if re.search(r"\$\d+|donate|chip in|contribution|deadline|end.of.quarter|winred", t):
        return "Fundraising"
    if re.search(r"socialist|radical|opponent|other side|far.left|far.right|extreme", t):
        return "Attack/Contrast"
    if re.search(r"\bvote\b|get out the vote|election day|polls open|cast your ballot|make your voice heard|register to vote|voter registration|early vote|mail.in ballot|absentee", t):
        return "Urgency/GOTV"
    if re.search(r"police|crime|safe|neighborhood|school|violent|fentanyl", t):
        return "Public Safety"
    if re.search(r"famil|father|mother|kids|children|grocer|home|afford|work", t):
        return "Economic/Family"
    if re.search(r"video|watch|explain|announcement", t):
        return "Video/Engagement"
    return "Other"


def infer_objective(link_caption, link_title) -> str:
    """Classify landing page objective."""
    combined = f"{link_caption} {link_title}".lower()
    if "winred" in combined or "actblue" in combined:
        return "Fundraising"
    if combined.strip():
        return "Website"
    return "Unknown"


def classify_ad_type(row, home_state: str) -> str:
    """Classify each ad as Fundraising or Persuasion.
    Uses geographic delivery data if home_state is set, otherwise falls back to landing page.
    """
    if home_state:
        regions = parse_json_field(row.get("delivery_by_region", ""))
        if regions:
            in_state = sum(r["percentage"] for r in regions if r.get("region") == home_state)
            return "Persuasion" if in_state >= 0.25 else "Fundraising"
    combined = f"{row.get('ad_creative_link_captions', '')} {row.get('ad_creative_link_titles', '')}".lower()
    return "Fundraising" if ("winred" in combined or "actblue" in combined) else "Persuasion"


def build_daily_ts(df: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct daily spend/impressions by spreading each ad across its run dates."""
    records = []
    for _, row in df.iterrows():
        if pd.isna(row.get("start_date")):
            continue
        d = row["start_date"]
        end = row["stop_date"] if not pd.isna(row.get("stop_date")) else datetime.date.today()
        # Clamp to date objects
        if hasattr(d, "date"):
            d = d.date()
        if hasattr(end, "date"):
            end = end.date()
        while d <= end:
            records.append({
                "date": d,
                "spend": row["daily_spend"],
                "impressions": row["daily_impressions"],
            })
            d += datetime.timedelta(days=1)
    if not records:
        return pd.DataFrame(columns=["date", "spend", "impressions"])
    ts = pd.DataFrame(records).groupby("date").sum().reset_index()
    ts["date"] = pd.to_datetime(ts["date"])
    return ts.sort_values("date")


def build_demo_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate demographic delivery across all ads, spend-weighted."""
    demo_col = next((c for c in df.columns if "demographic_distribution" in c.lower()), None)
    if demo_col is None:
        return pd.DataFrame()
    rows = []
    for _, ad in df.iterrows():
        demos = parse_json_field(ad.get(demo_col, ""))
        weight = ad["spend_mid"] if ad["spend_mid"] > 0 else 1
        for d in demos:
            if "age" in d and "gender" in d and "percentage" in d:
                rows.append({
                    "age_range": d["age"],
                    "gender": d["gender"],
                    "wpct": d["percentage"] * weight,
                })
    if not rows:
        return pd.DataFrame()
    agg = pd.DataFrame(rows).groupby(["age_range", "gender"])["wpct"].sum().reset_index()
    total = agg["wpct"].sum()
    agg["pct"] = agg["wpct"] / total * 100
    return agg


def _build_region_df_meta(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate state-level delivery, spend-weighted (Meta)."""
    region_col = next((c for c in df.columns if "delivery_by_region" in c.lower()), None)
    if region_col is None:
        return pd.DataFrame()
    rows = []
    for _, ad in df.iterrows():
        regions = parse_json_field(ad.get(region_col, ""))
        weight = ad["spend_mid"] if ad["spend_mid"] > 0 else 1
        for r in regions:
            if "region" in r and "percentage" in r:
                rows.append({"region": r["region"], "wpct": r["percentage"] * weight})
    if not rows:
        return pd.DataFrame()
    agg = pd.DataFrame(rows).groupby("region")["wpct"].sum().reset_index()
    total = agg["wpct"].sum()
    agg["pct"] = agg["wpct"] / total * 100
    return agg.sort_values("pct", ascending=False)


def detect_patterns(df: pd.DataFrame, home_state: str = "") -> list[str]:
    """Return list of strategic insight strings in 'Headline — explanation' format."""
    patterns = []
    total_spend = max(df["spend_mid"].sum(), 1)

    body_col = next((c for c in df.columns if "creative_bodies" in c.lower()), None)

    # A/B testing
    if body_col:
        df = df.copy()
        df["_prefix"] = df[body_col].str[:70].str.strip()
        ab = df[df["_prefix"].notna()].groupby("_prefix").filter(lambda x: len(x) > 1)
        n_groups = ab["_prefix"].nunique()
        if n_groups > 0:
            patterns.append(
                f"A/B Testing Detected — {n_groups} message group(s) with multiple ad variants: "
                "campaign is actively split-testing creative."
            )

    # Fundraising dominance
    fund_pct = df[df["theme"] == "Fundraising"]["spend_mid"].sum() / total_spend * 100
    if fund_pct > 60:
        patterns.append(
            f"Fundraising-Heavy — {fund_pct:.0f}% of estimated spend on fundraising messages: "
            "campaign is in money-chase mode."
        )
    elif fund_pct > 30:
        patterns.append(
            f"Mixed Objective — {fund_pct:.0f}% fundraising spend: balancing donor acquisition "
            "with persuasion/awareness."
        )

    # Low-dollar asks
    if body_col:
        low_dollar = df[body_col].str.contains(
            r"\$1\.00|\$1 |\$5|\$10|just a buck|one dollar", case=False, regex=True, na=False
        ).sum()
        if low_dollar > 0:
            patterns.append(
                f"Low-Dollar List Building — {low_dollar} ad(s) ask for $1–$10: "
                "broad donor acquisition strategy to grow the file."
            )

        # Deadline urgency
        deadline = df[body_col].str.contains(
            r"deadline|end.of.quarter|march 31|march 15|midnight|hours left", case=False, regex=True, na=False
        ).sum()
        if deadline > 2:
            patterns.append(
                f"Deadline Urgency Pattern — {deadline} ads use deadline pressure: "
                "classic urgency fundraising playbook."
            )

    # Attack spend
    attack_pct = df[df["theme"] == "Attack/Contrast"]["spend_mid"].sum() / total_spend * 100
    if attack_pct > 20:
        patterns.append(
            f"Significant Attack Spend — {attack_pct:.0f}% of spend drawing contrast with opponent: "
            "campaign is on offense."
        )

    # Geographic spread vs. concentration
    region_df = _build_region_df_meta(df)
    if not region_df.empty and home_state:
        home_pct = region_df[region_df["region"] == home_state]["pct"].sum()
        if home_pct < 15:
            patterns.append(
                f"National Donor Strategy — Only {home_pct:.1f}% of delivery in {home_state}: "
                "ads are reaching a national small-dollar donor base, not in-state voters."
            )
        elif home_pct > 40:
            patterns.append(
                f"In-State Focus — {home_pct:.1f}% of delivery in {home_state}: "
                "campaign is prioritizing in-state reach."
            )

    # 65+ skew
    demo_df = build_demo_df(df)
    if not demo_df.empty:
        senior_pct = demo_df[demo_df["age_range"].isin(["55-64", "65+"])]["pct"].sum()
        if senior_pct > 60:
            patterns.append(
                f"Senior-Skewed Delivery — {senior_pct:.0f}% of delivery to 55+: "
                "consistent with a fundraising-first campaign (older donors give at higher rates)."
            )

    # Active vs. stopped ads
    stop_col = "ad_delivery_stop_time" if "ad_delivery_stop_time" in df.columns else None
    if stop_col:
        pct_active = df[stop_col].isna().sum() / len(df) * 100
        if pct_active > 70:
            patterns.append(
                f"High Creative Retention — {pct_active:.0f}% of ads still active: "
                "campaign is keeping winners running rather than rotating frequently."
            )

    return patterns


@st.cache_data(show_spinner=False)
def load_meta_csv(file_bytes: bytes) -> pd.DataFrame:
    """Parse a Meta Ad Library CSV export."""
    import io as _io
    df = pd.read_csv(_io.BytesIO(file_bytes), low_memory=False)
    # spend_mid
    if "spend" in df.columns:
        df["spend_mid"] = df["spend"].apply(parse_midpoint)
    else:
        df["spend_mid"] = 0.0
    # impressions_mid
    if "impressions" in df.columns:
        df["impressions_mid"] = df["impressions"].apply(parse_midpoint)
    else:
        df["impressions_mid"] = 0.0
    # dates
    for col in ["ad_delivery_start_time", "ad_delivery_stop_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "ad_delivery_start_time" in df.columns:
        df["start_date"] = df["ad_delivery_start_time"].dt.date
    if "ad_delivery_stop_time" in df.columns:
        df["stop_date"] = df["ad_delivery_stop_time"].dt.date.fillna(datetime.date.today())
    else:
        df["stop_date"] = datetime.date.today()
    df["duration_days"] = (
        pd.to_datetime(df.get("stop_date", datetime.date.today())) -
        pd.to_datetime(df.get("start_date", datetime.date.today()))
    ).dt.days.clip(lower=1)
    df["daily_spend"]       = df["spend_mid"] / df["duration_days"]
    df["daily_impressions"] = df["impressions_mid"] / df["duration_days"]
    # theme + objective
    body_col = next((c for c in df.columns if "creative_bodies" in c.lower()), None)
    df["theme"] = df[body_col].fillna("").apply(classify_theme) if body_col else "Other"
    caption_col = next((c for c in df.columns if "link_caption" in c.lower()), None)
    title_col   = next((c for c in df.columns if "link_title" in c.lower()), None)
    df["objective"] = df.apply(
        lambda r: infer_objective(
            r.get(caption_col, "") if caption_col else "",
            r.get(title_col, "") if title_col else ""
        ), axis=1
    )
    return df


# ─── Meta Bulk Report Helpers ─────────────────────────────────────────────────
def parse_bulk_spend(s) -> float:
    """Parse Meta bulk report spend: '≤100' → 50.0, numeric → float."""
    if not s:
        return 0.0
    s = str(s).strip().replace(",", "").replace("$", "")
    if s.startswith("≤") or s.startswith("<="):
        return 50.0
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def get_disclaimer(row: dict) -> str:
    """Return Disclaimer if valid legal entity, else fall back to Page name."""
    d = str(row.get("Disclaimer", "") or "").strip()
    if d and d.lower() not in ("these ads ran without a disclaimer", ""):
        return d
    return str(row.get("Page name", "") or row.get("page_name", "")).strip()

@st.cache_data(show_spinner="Parsing Meta Library Report…")
def load_bulk_zip(file_bytes: bytes) -> dict:
    """
    Parse the FacebookAdLibraryReport ZIP.
    Returns dict with advertisers_df, locations_df, state_files list.
    """
    import io as _io
    import zipfile as _zf
    import csv as _csv

    with _zf.ZipFile(_io.BytesIO(file_bytes)) as zf:
        names = zf.namelist()

        adv_file = next((n for n in names if "_advertisers.csv" in n and "regions" not in n), None)
        loc_file = next((n for n in names if "_locations.csv"  in n and "regions" not in n), None)

        def _read(fname):
            with zf.open(fname) as f:
                reader = _csv.DictReader(_io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"))
                return list(reader)

        rows_adv = _read(adv_file) if adv_file else []
        rows_loc = _read(loc_file) if loc_file else []
        state_files = sorted(n for n in names if n.startswith("regions/") and n.endswith(".csv"))

    adv_df = pd.DataFrame(rows_adv) if rows_adv else pd.DataFrame(
        columns=["Page ID","Page name","Disclaimer","Amount spent (USD)","Number of ads in Library"]
    )
    if not adv_df.empty:
        adv_df["spend"]      = adv_df["Amount spent (USD)"].apply(parse_bulk_spend)
        adv_df["n_ads"]      = pd.to_numeric(
            adv_df.get("Number of ads in Library", 0), errors="coerce"
        ).fillna(0).astype(int)
        adv_df["advertiser"] = adv_df.apply(get_disclaimer, axis=1)
        adv_df = adv_df.sort_values("spend", ascending=False).reset_index(drop=True)

    loc_df = pd.DataFrame(rows_loc) if rows_loc else pd.DataFrame(
        columns=["Location name","Amount spent (USD)"]
    )
    if not loc_df.empty:
        loc_df["spend"] = loc_df["Amount spent (USD)"].apply(parse_bulk_spend)
        loc_df = loc_df.sort_values("spend", ascending=False).reset_index(drop=True)

    return {
        "advertisers_df": adv_df,
        "locations_df":   loc_df,
        "state_files":    state_files,
    }

def get_state_df(zip_bytes: bytes, state_file: str) -> pd.DataFrame:
    """Lazily load a single state CSV from the bulk ZIP."""
    import io as _io
    import zipfile as _zf
    import csv as _csv

    with _zf.ZipFile(_io.BytesIO(zip_bytes)) as zf:
        with zf.open(state_file) as f:
            reader = _csv.DictReader(_io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"))
            rows = list(reader)

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["Page ID","Page name","Disclaimer","Amount spent (USD)"]
    )
    if not df.empty:
        df["spend"]      = df["Amount spent (USD)"].apply(parse_bulk_spend)
        df["advertiser"] = df.apply(get_disclaimer, axis=1)
        df = df.sort_values("spend", ascending=False).reset_index(drop=True)
    return df

# ─── Meta App Renderer ────────────────────────────────────────────────────────

def _party_badge_html(party: str) -> str:
    COLORS = {"D": ("#EBF3FA","#2563EB"), "R": ("#FFF1EE","#DC2626"),
               "N": ("#F5F0FF","#7C3AED"), "?": ("#F0EDEA","#9CA3AF")}
    LABELS = {"D": "DEM", "R": "REP", "N": "NPN", "?": "UNK"}
    bg, fg = COLORS.get(party, ("#F0EDEA","#9CA3AF"))
    return (f'<span style="padding:2px 10px;border-radius:5px;background:{bg};color:{fg};'
            f'font-size:10px;font-weight:800;letter-spacing:.07em">{LABELS.get(party,"UNK")}</span>')


def render_bulk_view(bulk_data: dict, zip_bytes: bytes):
    """Render the Library Report overview + by-state views."""
    overrides    = st.session_state.overrides
    party_filter = [p for p in ["D","R","N","?"] if st.session_state.get(f"pf_{p}", True)]
    adv_df       = bulk_data["advertisers_df"].copy()
    loc_df       = bulk_data["locations_df"].copy()
    state_files  = bulk_data["state_files"]

    if adv_df.empty:
        st.error("Could not parse advertisers from the uploaded ZIP.")
        return

    # Infer party for every advertiser
    adv_df["party"] = adv_df["advertiser"].apply(
        lambda n: infer_party(n, "", overrides)[0]
    )
    adv_df_filtered = adv_df[adv_df["party"].isin(party_filter)]

    # ── National KPIs ─────────────────────────────────────────────────────────
    total_spend  = adv_df_filtered["spend"].sum()
    n_advertisers = len(adv_df_filtered)
    d_spend = adv_df_filtered[adv_df_filtered["party"] == "D"]["spend"].sum()
    r_spend = adv_df_filtered[adv_df_filtered["party"] == "R"]["spend"].sum()

    k1, k2, k3, k4 = st.columns(4)
    def _kpi(col, label, val, sub=""):
        col.markdown(
            f'<div style="background:#fff;border:1px solid #E2DDD7;border-radius:12px;padding:16px 18px">'
            f'<div style="font-size:11px;font-weight:700;color:#6B6560;letter-spacing:.06em;text-transform:uppercase">{label}</div>'
            f'<div style="font-size:24px;font-weight:800;color:#1A1714;margin:4px 0 2px">{val}</div>'
            f'<div style="font-size:11px;color:#6B6560">{sub}</div></div>',
            unsafe_allow_html=True,
        )
    _kpi(k1, "Total Spend",          money(total_spend),   "last 7 days · filtered")
    _kpi(k2, "Active Advertisers",   f"{n_advertisers:,}", "political advertisers")
    _kpi(k3, "Democrat Spend",
         f'<span style="color:#2563EB">{money(d_spend)}</span>', "last 7 days")
    _kpi(k4, "Republican Spend",
         f'<span style="color:#DC2626">{money(r_spend)}</span>', "last 7 days")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_ov, tab_state = st.tabs(["Overview", "By State"])

    # ── Overview tab ──────────────────────────────────────────────────────────
    with tab_ov:
        top100 = adv_df_filtered.head(100)
        top1   = top100["spend"].iloc[0] if not top100.empty else 1

        # Header row
        h0, h1, h2, h3, h4 = st.columns([1, 6, 2, 2, 2])
        for _h, _t in zip([h0,h1,h2,h3,h4], ["#","ADVERTISER","PARTY","SPEND","ADS"]):
            _h.markdown(
                f'<p style="font-size:11px;font-weight:700;color:#6B6560;margin:0">{_t}</p>',
                unsafe_allow_html=True,
            )
        st.markdown('<div style="height:1px;background:#E2DDD7;margin:4px 0 6px"></div>',
                    unsafe_allow_html=True)

        for rank, row in enumerate(top100.itertuples(), 1):
            party    = row.party
            pct      = row.spend / top1 * 100
            PCOL     = {"D":"#2563EB","R":"#DC2626","N":"#7C3AED","?":"#9CA3AF"}
            p_color  = PCOL.get(party, "#9CA3AF")
            c0,c1,c2,c3,c4 = st.columns([1,6,2,2,2])
            c0.markdown(f'<p style="font-size:12px;color:#6B6560;margin:4px 0">{rank}</p>',
                        unsafe_allow_html=True)
            c1.markdown(
                f'<div style="padding:4px 0">'
                f'<div style="font-size:13px;font-weight:600;color:#1A1714">{_html.escape(row.advertiser)}</div>'
                f'<div style="margin-top:3px;height:3px;width:{pct:.1f}%;background:{p_color};'
                f'border-radius:2px;opacity:0.5"></div></div>',
                unsafe_allow_html=True,
            )
            c2.markdown(_party_badge_html(party), unsafe_allow_html=True)
            c3.markdown(
                f'<p style="font-size:13px;font-weight:600;color:#1A1714;margin:4px 0">'
                f'{money(row.spend)}</p>', unsafe_allow_html=True,
            )
            c4.markdown(
                f'<p style="font-size:12px;color:#6B6560;margin:4px 0">{row.n_ads:,}</p>',
                unsafe_allow_html=True,
            )
            st.markdown('<div style="height:1px;background:#F0EDEA;margin:0"></div>',
                        unsafe_allow_html=True)

    # ── By State tab ──────────────────────────────────────────────────────────
    with tab_state:
        if not loc_df.empty:
            # State spend bar chart
            top_locs = loc_df[loc_df["spend"] > 0].head(52)
            fig_l = go.Figure([go.Bar(
                y=top_locs["Location name"].tolist(),
                x=top_locs["spend"].tolist(),
                orientation="h",
                marker_color="#1877F2", marker_line_width=0,
                text=[money(v) for v in top_locs["spend"]],
                textposition="outside",
                textfont=dict(size=10, color="#6B6560"),
            )])
            fig_l.update_layout(
                **PLOTLY_LIGHT,
                height=max(380, len(top_locs) * 22),
                showlegend=False,
                xaxis=dict(gridcolor="#E2DDD7", tickprefix="$", tickformat=",.0f"),
                yaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=11), autorange="reversed"),
            )
            st.plotly_chart(fig_l, use_container_width=True)

        # State drilldown
        st.markdown(
            '<h3 style="font-size:15px;font-weight:700;margin:24px 0 10px">Top Advertisers by State</h3>',
            unsafe_allow_html=True,
        )

        # Build state name → file mapping
        def _state_name_from_file(fn: str) -> str:
            base  = fn.split("/")[-1].replace(".csv", "")
            parts = base.split("_")
            # Filename: FacebookAdLibraryReport_YYYY-MM-DD_US_last_7_days_StateName
            # Anchor on "days" — everything after is the state name
            try:
                idx = next(i for i, p in enumerate(parts) if p.lower() == "days")
                return " ".join(parts[idx + 1:])
            except StopIteration:
                return base

        state_map = {_state_name_from_file(f): f for f in state_files}
        state_names = sorted(state_map.keys())

        if not state_names:
            _src = bulk_data.get("source", "zip")
            if _src == "api":
                st.info("State-level drilldown is not available for API-fetched data. "
                        "Upload a Library Report ZIP to access per-state advertiser breakdowns.")
            else:
                st.info("No state-level files found in this ZIP.")
        else:
            sel_state = st.selectbox(
                "Select state", options=state_names,
                key="bulk_state_select", label_visibility="collapsed",
            )
            state_df = get_state_df(zip_bytes, state_map[sel_state])
            state_df["party"] = state_df["advertiser"].apply(
                lambda n: infer_party(n, "", overrides)[0]
            )
            state_filtered = state_df[state_df["party"].isin(party_filter)]

            if state_filtered.empty:
                st.info(f"No advertisers match the current party filter for {sel_state}.")
            else:
                state_top1 = state_filtered["spend"].iloc[0] if not state_filtered.empty else 1
                sh0,sh1,sh2,sh3 = st.columns([1,7,2,2])
                for _h,_t in zip([sh0,sh1,sh2,sh3],["#","ADVERTISER","PARTY","SPEND"]):
                    _h.markdown(
                        f'<p style="font-size:11px;font-weight:700;color:#6B6560;margin:0">{_t}</p>',
                        unsafe_allow_html=True,
                    )
                st.markdown('<div style="height:1px;background:#E2DDD7;margin:4px 0 6px"></div>',
                            unsafe_allow_html=True)
                PCOL = {"D":"#2563EB","R":"#DC2626","N":"#7C3AED","?":"#9CA3AF"}
                for rank, row in enumerate(state_filtered.head(50).itertuples(), 1):
                    party   = row.party
                    pct     = row.spend / state_top1 * 100 if state_top1 else 0
                    p_color = PCOL.get(party, "#9CA3AF")
                    s0,s1,s2,s3 = st.columns([1,7,2,2])
                    s0.markdown(f'<p style="font-size:12px;color:#6B6560;margin:4px 0">{rank}</p>',
                                unsafe_allow_html=True)
                    s1.markdown(
                        f'<div style="padding:4px 0">'
                        f'<div style="font-size:13px;font-weight:600;color:#1A1714">{_html.escape(row.advertiser)}</div>'
                        f'<div style="margin-top:3px;height:3px;width:{pct:.1f}%;background:{p_color};'
                        f'border-radius:2px;opacity:0.5"></div></div>',
                        unsafe_allow_html=True,
                    )
                    s2.markdown(_party_badge_html(party), unsafe_allow_html=True)
                    s3.markdown(
                        f'<p style="font-size:13px;font-weight:600;color:#1A1714;margin:4px 0">'
                        f'{money(row.spend)}</p>', unsafe_allow_html=True,
                    )
                    st.markdown('<div style="height:1px;background:#F0EDEA;margin:0"></div>',
                                unsafe_allow_html=True)


def render_single_advertiser_view():
    """Render the single-advertiser Meta analysis (Spend Trends, Creative, Audience, Patterns)."""
    overrides    = st.session_state.overrides
    meta_dfs     = st.session_state.get("meta_dfs", {})
    party_filter = [p for p in ["D","R","N","?"] if st.session_state.get(f"pf_{p}", True)]

    combined  = pd.concat(list(meta_dfs.values()), ignore_index=True)
    page_col  = next((c for c in combined.columns if "page_name" in c.lower()), None)
    if page_col is None:
        st.error("Could not find 'page_name' column. Is this a Meta Ad Library export?")
        return

    adv_totals = combined.groupby(page_col)["spend_mid"].sum().sort_values(ascending=False)
    filtered_advs = [
        (name, spend) for name, spend in adv_totals.items()
        if infer_party(name, "", overrides)[0] in party_filter
    ]
    if not filtered_advs:
        st.info("No advertisers match the current party filter.")
        return

    sel_adv = st.selectbox(
        "Select advertiser", options=[n for n,_ in filtered_advs],
        key="meta_sel_adv", label_visibility="collapsed",
    )
    adv_df = combined[combined[page_col] == sel_adv].copy()

    adv_party, _ = infer_party(sel_adv, "", overrides)
    PCOL = {"D":"#2563EB","R":"#DC2626","N":"#7C3AED","?":"#9CA3AF"}
    PBG  = {"D":"#EBF3FA","R":"#FFF1EE","N":"#F5F0FF","?":"#F0EDEA"}
    p_color = PCOL.get(adv_party,"#9CA3AF")
    p_bg    = PBG.get(adv_party,"#F0EDEA")
    PLABEL  = {"D":"DEM","R":"REP","N":"NPN","?":"UNK"}

    total_spend       = adv_df["spend_mid"].sum()
    total_impressions = adv_df["impressions_mid"].sum()
    total_ads         = len(adv_df)
    active_ads        = int(adv_df["ad_delivery_stop_time"].isna().sum()) \
                        if "ad_delivery_stop_time" in adv_df.columns else 0

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;'
        f'padding-bottom:16px;border-bottom:2px solid #1877F2">'
        f'<div style="flex:1"><div style="font-size:22px;font-weight:800;color:#1A1714">{_html.escape(sel_adv)}</div>'
        f'<div style="font-size:12px;color:#6B6560;margin-top:2px">Meta · Single Advertiser Analysis</div></div>'
        f'<span style="padding:4px 14px;border-radius:6px;background:{p_bg};color:{p_color};'
        f'font-size:11px;font-weight:800;letter-spacing:.07em">{PLABEL.get(adv_party,"UNK")}</span>'
        f'</div>', unsafe_allow_html=True,
    )

    k1,k2,k3,k4 = st.columns(4)
    def _kpi(col, label, val, sub=""):
        col.markdown(
            f'<div style="background:#fff;border:1px solid #E2DDD7;border-radius:12px;padding:16px 18px">'
            f'<div style="font-size:11px;font-weight:700;color:#6B6560;letter-spacing:.06em;text-transform:uppercase">{label}</div>'
            f'<div style="font-size:24px;font-weight:800;color:#1A1714;margin:4px 0 2px">{val}</div>'
            f'<div style="font-size:11px;color:#6B6560">{sub}</div></div>',
            unsafe_allow_html=True,
        )
    _kpi(k1,"Est. Spend",       money(total_spend),           "midpoint estimate")
    _kpi(k2,"Est. Impressions", f"{total_impressions:,.0f}",  "midpoint estimate")
    _kpi(k3,"Total Ads",        f"{total_ads:,}",             "creatives in export")
    _kpi(k4,"Active Ads",       f"{active_ads:,}",            "no stop date")
    st.markdown("<br>", unsafe_allow_html=True)

    tab_trends, tab_creative, tab_audience, tab_patterns = st.tabs([
        "Spend Trends","Creative Analysis","Audience Delivery","Auto-Detected Patterns"
    ])

    with tab_trends:
        gran = st.radio("Granularity",["Daily","Weekly","Monthly"],
                        horizontal=True, key="meta_gran", label_visibility="collapsed")
        daily_ts = build_daily_ts(adv_df)
        if daily_ts.empty:
            st.info("Not enough date data to build a time series.")
        else:
            if gran == "Weekly":
                daily_ts["period"] = pd.to_datetime(daily_ts["date"]).dt.to_period("W").dt.start_time
            elif gran == "Monthly":
                daily_ts["period"] = pd.to_datetime(daily_ts["date"]).dt.to_period("M").dt.start_time
            else:
                daily_ts["period"] = pd.to_datetime(daily_ts["date"])
            agg = daily_ts.groupby("period")[["spend","impressions"]].sum().reset_index().sort_values("period")
            fmt = "%b %-d" if gran in ("Daily","Weekly") else "%b %Y"
            x_labels = agg["period"].dt.strftime(fmt).tolist()
            fig = make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Bar(name="Est. Spend", x=x_labels, y=agg["spend"].tolist(),
                                 marker_color=p_color, marker_line_width=0, opacity=0.85),
                          secondary_y=False)
            fig.add_trace(go.Scatter(name="Est. Impressions", x=x_labels,
                                     y=agg["impressions"].tolist(),
                                     line=dict(color="#F5902B",width=2.5),
                                     mode="lines+markers", marker=dict(size=4)),
                          secondary_y=True)
            fig.update_layout(
                **{k:v for k,v in PLOTLY_LIGHT.items() if k != "legend"},
                height=340, showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=11,color="#6B6560"),
                            orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
                xaxis=dict(gridcolor="#E2DDD7",tickfont=dict(size=10)),
            )
            fig.update_yaxes(tickprefix="$",tickformat=",.0f",gridcolor="#E2DDD7",secondary_y=False)
            fig.update_yaxes(gridcolor="rgba(0,0,0,0)",tickformat=",.0f",secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('<p style="font-size:11px;color:#6B6560">Spend and impressions are midpoint '
                    'estimates from Meta\'s reported ranges.</p>', unsafe_allow_html=True)

    with tab_creative:
        theme_spend = adv_df.groupby("theme")["spend_mid"].sum().sort_values(ascending=True)
        if not theme_spend.empty:
            TCOL = {"Fundraising":"#F5902B","Attack/Contrast":"#DC2626","Urgency/GOTV":"#0A8A57",
                    "Public Safety":"#7C3AED","Economic/Family":"#2563EB",
                    "Video/Engagement":"#3374AA","Other":"#9CA3AF"}
            fig_t = go.Figure([go.Bar(
                y=theme_spend.index.tolist(), x=theme_spend.values.tolist(),
                orientation="h",
                marker_color=[TCOL.get(t,"#9CA3AF") for t in theme_spend.index],
                marker_line_width=0,
                text=[money(v) for v in theme_spend.values], textposition="outside",
                textfont=dict(size=11,color="#6B6560"),
            )])
            fig_t.update_layout(**PLOTLY_LIGHT, height=max(220,len(theme_spend)*38),
                                showlegend=False,
                                xaxis=dict(gridcolor="#E2DDD7",tickprefix="$",tickformat=",.0f"),
                                yaxis=dict(tickfont=dict(size=12)))
            st.plotly_chart(fig_t, use_container_width=True)

        hs = "" if st.session_state.get("meta_home_state","(none)") == "(none)" \
             else st.session_state.meta_home_state
        adv_df["ad_type"] = adv_df.apply(lambda r: classify_ad_type(r, hs), axis=1)
        type_split = adv_df.groupby("ad_type")["spend_mid"].sum()
        fund_pct = type_split.get("Fundraising",0) / max(total_spend,1) * 100
        pers_pct = type_split.get("Persuasion",0)  / max(total_spend,1) * 100
        st.markdown(
            f'<div style="display:flex;gap:12px;margin:8px 0 20px">'
            f'<div style="flex:1;background:#FEF3E8;border:1px solid #F5902B;border-radius:10px;padding:14px 18px">'
            f'<div style="font-size:11px;font-weight:700;color:#9A4A00;letter-spacing:.06em">FUNDRAISING</div>'
            f'<div style="font-size:28px;font-weight:800;color:#F5902B;margin:4px 0">{fund_pct:.0f}%</div>'
            f'<div style="font-size:12px;color:#9A4A00">{money(type_split.get("Fundraising",0))} est.</div></div>'
            f'<div style="flex:1;background:#EBF3FA;border:1px solid #3374AA;border-radius:10px;padding:14px 18px">'
            f'<div style="font-size:11px;font-weight:700;color:#1D4B7C;letter-spacing:.06em">PERSUASION</div>'
            f'<div style="font-size:28px;font-weight:800;color:#3374AA;margin:4px 0">{pers_pct:.0f}%</div>'
            f'<div style="font-size:12px;color:#1D4B7C">{money(type_split.get("Persuasion",0))} est.</div></div>'
            f'</div>', unsafe_allow_html=True,
        )
        body_col = next((c for c in adv_df.columns if "creative_bodies" in c.lower()), None)
        if body_col:
            top_ads = adv_df.nlargest(20,"spend_mid")[[body_col,"theme","spend_mid","duration_days"]].copy()
            top_ads.columns = ["Ad Copy","Theme","Est. Spend","Days"]
            top_ads["Ad Copy"]    = top_ads["Ad Copy"].fillna("").str[:120] + "…"
            top_ads["Est. Spend"] = top_ads["Est. Spend"].apply(money)
            top_ads["Days"]       = top_ads["Days"].astype(int)
            st.markdown('<h4 style="font-size:14px;font-weight:700;margin:8px 0">Top Ads by Spend</h4>',
                        unsafe_allow_html=True)
            st.dataframe(top_ads, use_container_width=True, hide_index=True)

    with tab_audience:
        demo_df = build_demo_df(adv_df)
        if demo_df.empty:
            st.info("No demographic delivery data in this export.")
        else:
            pivot = demo_df.pivot_table(index="age_range",columns="gender",
                                        values="pct",aggfunc="sum",fill_value=0)
            age_order = ["18-24","25-34","35-44","45-54","55-64","65+","Unknown"]
            pivot = pivot.reindex([a for a in age_order if a in pivot.index])
            col_hm,col_bar = st.columns(2)
            with col_hm:
                st.markdown('<h4 style="font-size:14px;font-weight:700;margin:0 0 8px">Age × Gender Heatmap</h4>',
                            unsafe_allow_html=True)
                fig_hm = go.Figure(go.Heatmap(
                    z=pivot.values.tolist(), x=pivot.columns.tolist(), y=pivot.index.tolist(),
                    colorscale=[[0,"#F6F5F2"],[1,"#1877F2"]], showscale=True,
                    text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
                    texttemplate="%{text}", textfont=dict(size=11),
                ))
                fig_hm.update_layout(**PLOTLY_LIGHT, height=300,
                                     yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_hm, use_container_width=True)
            with col_bar:
                st.markdown('<h4 style="font-size:14px;font-weight:700;margin:0 0 8px">Age Group Breakdown</h4>',
                            unsafe_allow_html=True)
                GCOL = {"male":"#3374AA","female":"#F5902B","unknown":"#9CA3AF"}
                fig_db = go.Figure()
                for g in pivot.columns:
                    fig_db.add_trace(go.Bar(name=g.title(), x=pivot.index.tolist(),
                                            y=pivot[g].tolist(),
                                            marker_color=GCOL.get(g.lower(),"#9CA3AF"),
                                            marker_line_width=0))
                fig_db.update_layout(**PLOTLY_LIGHT, height=300, barmode="group",
                                     yaxis=dict(ticksuffix="%",gridcolor="#E2DDD7"))
                st.plotly_chart(fig_db, use_container_width=True)
            male_pct   = pivot.get("male",   pd.Series(dtype=float)).sum()
            female_pct = pivot.get("female", pd.Series(dtype=float)).sum()
            senior_pct = sum(pivot.loc[a].sum() for a in ["55-64","65+"] if a in pivot.index)
            youth_pct  = sum(pivot.loc[a].sum() for a in ["18-24","25-34"] if a in pivot.index)
            insights = []
            if male_pct > 60:   insights.append(f"Male-dominant delivery ({male_pct:.0f}% male)")
            if female_pct > 60: insights.append(f"Female-dominant delivery ({female_pct:.0f}% female)")
            if senior_pct > 50: insights.append(f"Senior-skewed (55+ = {senior_pct:.0f}%)")
            if youth_pct  > 40: insights.append(f"Youth-heavy (18–34 = {youth_pct:.0f}%)")
            for ins in insights:
                st.markdown(
                    f'<div style="padding:8px 14px;background:#F6F5F2;border-left:3px solid #1877F2;'
                    f'border-radius:0 8px 8px 0;margin-bottom:6px;font-size:13px;color:#1A1714">'
                    f'📊 {ins}</div>', unsafe_allow_html=True,
                )

    with tab_patterns:
        hs = "" if st.session_state.get("meta_home_state","(none)") == "(none)" \
             else st.session_state.meta_home_state
        patterns = detect_patterns(adv_df, hs)
        if not patterns:
            st.markdown('<div style="text-align:center;padding:40px;color:#6B6560">'
                        '✓ No notable patterns detected.</div>', unsafe_allow_html=True)
        else:
            PICONS = {"A/B":"🔬","fundrais":"💰","low-dollar":"💵","deadline":"⏰",
                      "attack":"⚔️","national":"🗺️","in-state":"📍","senior":"👴"}
            for pat in patterns:
                icon  = next((v for k,v in PICONS.items() if k.lower() in pat.lower()), "💡")
                parts = pat.split(" — ",1)
                hl    = parts[0]
                det   = parts[1] if len(parts) > 1 else ""
                _det_html = (f'<div style="font-size:13px;color:#6B6560;margin-top:3px">{det}</div>'
                             if det else "")
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #E2DDD7;border-left:4px solid #1877F2;'
                    f'border-radius:0 12px 12px 0;padding:16px 20px;margin-bottom:10px">'
                    f'<div style="display:flex;align-items:center;gap:10px">'
                    f'<span style="font-size:20px">{icon}</span>'
                    f'<div><div style="font-size:14px;font-weight:700;color:#1A1714">{hl}</div>'
                    f'{_det_html}'
                    f'</div></div></div>', unsafe_allow_html=True,
                )
        if hs:
            st.markdown(f'<p style="font-size:11px;color:#6B6560;margin-top:8px">'
                        f'Home state: <strong>{hs}</strong></p>', unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-size:11px;color:#9CA3AF;margin-top:8px">'
                        '💡 Set a home state in the sidebar for in-state vs. national analysis.</p>',
                        unsafe_allow_html=True)


# ─── Alias / Entity-Resolution Helpers ──────────────────────────────────────

def load_aliases() -> dict:
    """Load alias map {lowercase_alias: canonical_display_name} from disk."""
    if ALIASES_FILE.exists():
        try:
            return json.loads(ALIASES_FILE.read_text())
        except Exception as e:
            print(f"[warn] Failed to load aliases: {e}")
    return {}


def save_aliases(aliases: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ALIASES_FILE.write_text(json.dumps(aliases, indent=2, sort_keys=True))


def normalize_for_matching(name: str) -> str:
    """Strip committee language so 'Vivek Ramaswamy for Ohio' → 'Vivek Ramaswamy'."""
    n = name.strip()
    n = re.sub(r"\bfriends\s+of\s+", "", n, flags=re.IGNORECASE)
    n = re.sub(r"\bcitizens\s+for\s+", "", n, flags=re.IGNORECASE)
    n = re.sub(r"\s+for\s+.+$", "", n, flags=re.IGNORECASE)
    n = re.sub(
        r"\s+(pac|committee|fund|inc\.?|llc\.?|campaign|victory|action|team|america|usa)\s*$",
        "", n, flags=re.IGNORECASE,
    )
    return n.strip()


def resolve_alias(name: str, aliases: dict) -> str:
    """Return the canonical name for an alias, or the name itself if none found."""
    return aliases.get(name.lower(), name)


def find_fuzzy_matches(
    name: str,
    pool: list,
    aliases: dict,
    threshold: float = 0.4,
) -> list:
    """
    Return pool entries likely referring to the same entity as `name`.
    Uses word-token Jaccard similarity — names must share at least one
    meaningful word (≥4 chars). Avoids character-level false positives
    like 'John X' matching 'Hoan for 9'.
    Returns list of (candidate_name, score) sorted by score descending.
    """
    tokens_a = set(normalize_for_matching(name).lower().split())
    # Single short token is too ambiguous to match safely
    if len(tokens_a) < 2 and all(len(t) < 5 for t in tokens_a):
        return []

    canon_a = resolve_alias(name, aliases).lower()
    seen    = {canon_a}
    results = []

    for n in pool:
        if n == name:
            continue
        n_canon = resolve_alias(n, aliases).lower()
        if n_canon in seen:
            continue
        tokens_b = set(normalize_for_matching(n).lower().split())
        shared   = tokens_a & tokens_b
        # Require at least one shared word of meaningful length
        if not any(len(w) >= 4 for w in shared):
            continue
        score = len(shared) / len(tokens_a | tokens_b)
        if score >= threshold:
            results.append((n, score))
            seen.add(n_canon)

    return sorted(results, key=lambda x: -x[1])[:5]


# ─── Match Up: Cross-Platform Candidate Comparison ───────────────────────────

def _matchup_candidate_data(
    name: str,
    adv_spend: dict,
    weekly_raw: dict,
    name_to_scope: dict,
    aliases: dict,
) -> dict:
    """
    Aggregate all available data for one candidate across YouTube and Meta.
    Uses three-layer entity resolution:
      1. Explicit alias file  (user-confirmed mappings)
      2. Name normalization   (strips "for Ohio", "Committee", etc.)
      3. Exact match fallback
    """
    overrides = st.session_state.overrides
    wikidata  = get_wikidata_parties()
    party, _  = infer_party(name, name_to_scope.get(name, ""), overrides, wikidata)

    # Build the full set of raw names that refer to this candidate
    canonical    = resolve_alias(name, aliases)
    canon_lower  = canonical.lower()
    norm_name    = normalize_for_matching(name).lower()

    def _matches(n: str) -> bool:
        """True if advertiser name n refers to the same entity as our candidate."""
        if resolve_alias(n, aliases).lower() == canon_lower:
            return True
        if normalize_for_matching(n).lower() == norm_name and norm_name:
            return True
        return False

    # ── YouTube ───────────────────────────────────────────────────────────────
    yt_spend:  float           = 0.0
    yt_weekly: dict[str, float] = {}
    for n, sp in adv_spend.items():
        if _matches(n):
            yt_spend += sp
            for wk, wsp in weekly_raw.get(n, {}).items():
                yt_weekly[wk] = yt_weekly.get(wk, 0.0) + wsp

    # ── Meta bulk (ZIP upload preferred; fall back to API data) ──────────────
    meta_bulk_spend = 0.0
    meta_bulk_ads   = 0
    bulk_data = (st.session_state.get("meta_bulk_data")
                 or st.session_state.get("meta_api_data"))
    if bulk_data and "advertisers_df" in bulk_data:
        adf   = bulk_data["advertisers_df"]
        mask  = adf["advertiser"].apply(_matches) | adf["Page name"].apply(_matches)
        match = adf[mask]
        if not match.empty:
            meta_bulk_spend = float(match["spend"].sum())
            meta_bulk_ads   = int(match["n_ads"].sum())

    # ── Meta single CSV ───────────────────────────────────────────────────────
    meta_single_spend = 0.0
    meta_single_ts    = pd.DataFrame()
    meta_dfs = st.session_state.get("meta_dfs", {})
    if meta_dfs:
        combined = pd.concat(list(meta_dfs.values()), ignore_index=True)
        page_col = next((c for c in combined.columns if "page_name" in c.lower()), None)
        if page_col:
            match_single = combined[combined[page_col].apply(_matches)]
            if not match_single.empty:
                meta_single_spend = float(match_single["spend_mid"].sum())
                meta_single_ts    = build_daily_ts(match_single)

    meta_spend = meta_single_spend if meta_single_spend > 0 else meta_bulk_spend

    # ── Snap ──────────────────────────────────────────────────────────────────
    snap_spend = 0.0
    snap_ads   = 0
    for _so in st.session_state.get("snap_processed_orgs", []):
        if _matches(_so["org"]) or _matches(_so.get("payer", "")):
            snap_spend += _so["spend"]
            snap_ads   += _so["ad_count"]

    return {
        "name":          name,
        "party":         party,
        "yt_spend":      yt_spend,
        "meta_spend":    meta_spend,
        "meta_bulk_ads": meta_bulk_ads,
        "snap_spend":    snap_spend,
        "snap_ads":      snap_ads,
        "total":         yt_spend + meta_spend + snap_spend,
        "yt_weekly":     yt_weekly,
        "meta_ts":       meta_single_ts,
    }


def _party_color(party: str, idx: int = 0) -> str:
    """Return a brand color for a party; idx differentiates when both candidates are same party."""
    palette = {
        "D": ["#1A56DB", "#3B82F6"],
        "R": ["#C81E1E", "#EF4444"],
        "N": ["#6D28D9", "#A78BFA"],
        "?": ["#3374AA", "#F5902B"],
    }
    colors = palette.get(party, palette["?"])
    return colors[min(idx, len(colors) - 1)]


def _party_badge(party: str) -> str:
    cls = {"D": "badge-d", "R": "badge-r", "N": "badge-n"}.get(party, "badge-unk")
    return f'<span class="badge {cls}">{party}</span>'


def render_matchup():
    """Head-to-head candidate comparison across YouTube and Meta."""

    # ── Load YouTube data (cached — nearly instant after first load) ──────────
    try:
        with st.spinner("Loading data…"):
            zip_path = download_bundle()
        fast            = load_fast_data(str(zip_path), TODAY.isoformat())
        adv_spend       = fast["adv_spend"]
        weekly_raw      = fast["weekly_raw"]
        name_to_scope   = fast["name_to_scope"]
    except Exception as e:
        print(f"[warn] Match Up: Failed to load YouTube data: {e}")
        adv_spend = {}; weekly_raw = {}; name_to_scope = {}

    # ── Build merged advertiser list ──────────────────────────────────────────
    all_names: set[str] = set(adv_spend.keys())

    # Include names from ZIP bulk data OR API data
    for _bd in filter(None, [st.session_state.get("meta_bulk_data"),
                              st.session_state.get("meta_api_data")]):
        if "advertisers_df" in _bd:
            for n in _bd["advertisers_df"]["advertiser"].dropna().unique():
                if n:
                    all_names.add(str(n))

    meta_dfs = st.session_state.get("meta_dfs", {})
    if meta_dfs:
        combined = pd.concat(list(meta_dfs.values()), ignore_index=True)
        page_col = next((c for c in combined.columns if "page_name" in c.lower()), None)
        if page_col:
            for n in combined[page_col].dropna().unique():
                if n:
                    all_names.add(str(n))

    # Snap orgs
    _snap_orgs_mu = st.session_state.get("snap_processed_orgs", [])
    for _so in _snap_orgs_mu:
        all_names.add(_so["org"])

    overrides    = st.session_state.overrides
    wikidata     = get_wikidata_parties()
    party_filter = [p for p in ["D", "R", "N", "?"] if st.session_state.get(f"pf_{p}", True)]

    filtered = [
        n for n in all_names
        if infer_party(n, name_to_scope.get(n, ""), overrides, wikidata)[0] in party_filter
    ]
    sorted_names = sorted(filtered, key=lambda n: -adv_spend.get(n, 0))
    opts = ["— select candidate —"] + sorted_names

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:1.75rem;
                padding-bottom:1.25rem;border-bottom:3px solid #7C3AED">
      <div>
        <div style="font-size:28px;font-weight:700;letter-spacing:-.03em;color:#1A1714;line-height:1.1">
          Candidate Match Up
          <span style="font-size:16px;font-weight:600;color:#6B6560;margin-left:8px">
            Cross-Platform Spend Intelligence
          </span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Candidate selectors ───────────────────────────────────────────────────
    col_a, col_vs, col_b = st.columns([10, 1, 10])
    with col_a:
        st.markdown(
            '<div style="font-size:10.5px;font-weight:700;letter-spacing:.07em;'
            'text-transform:uppercase;color:#6B6560;margin-bottom:4px">Candidate A</div>',
            unsafe_allow_html=True,
        )
        cand_a = st.selectbox(
            "Candidate A", options=opts, key="matchup_a", label_visibility="collapsed"
        )
    with col_vs:
        st.markdown(
            '<div style="text-align:center;font-size:18px;font-weight:700;'
            'color:#6B6560;padding-top:26px">vs</div>',
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            '<div style="font-size:10.5px;font-weight:700;letter-spacing:.07em;'
            'text-transform:uppercase;color:#6B6560;margin-bottom:4px">Candidate B</div>',
            unsafe_allow_html=True,
        )
        cand_b = st.selectbox(
            "Candidate B", options=opts, key="matchup_b", label_visibility="collapsed"
        )

    if cand_a == "— select candidate —" or cand_b == "— select candidate —":
        st.markdown("""
        <div style="margin-top:3rem;text-align:center;padding:3.5rem 2rem;
                    background:white;border-radius:16px;border:1px solid #E2DDD7">
          <div style="font-size:42px;margin-bottom:12px">⚡</div>
          <div style="font-size:18px;font-weight:700;color:#1A1714;margin-bottom:6px">
            Select two candidates above to compare
          </div>
          <div style="font-size:13px;color:#6B6560">
            Draws from any advertiser in your loaded YouTube or Meta data
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    if cand_a == cand_b:
        st.warning("Select two different candidates.")
        return

    # ── Alias loading + auto-suggest ──────────────────────────────────────────
    if "aliases" not in st.session_state:
        st.session_state.aliases = load_aliases()
    aliases = st.session_state.aliases

    for _cand, _suffix in [(cand_a, "a"), (cand_b, "b")]:
        _suggestions = find_fuzzy_matches(_cand, sorted_names, aliases)
        if _suggestions:
            with st.expander(
                f"⚡ Possible aliases for **{_cand}** — {len(_suggestions)} similar name(s) found",
                expanded=False,
            ):
                st.markdown(
                    '<div style="font-size:12px;color:#6B6560;margin-bottom:10px">'
                    'These names may refer to the same candidate across platforms. '
                    'Confirm to merge their spend data.</div>',
                    unsafe_allow_html=True,
                )
                for _sugg, _score in _suggestions:
                    _s1, _s2, _s3 = st.columns([5, 2, 2])
                    _s1.markdown(
                        f'<div style="font-size:13px;font-weight:600;color:#1A1714">{_html.escape(_sugg)}</div>',
                        unsafe_allow_html=True,
                    )
                    _s2.markdown(
                        f'<div style="font-size:12px;color:#6B6560;padding-top:4px">'
                        f'{_score:.0%} match</div>',
                        unsafe_allow_html=True,
                    )
                    if _s3.button("Merge →", key=f"merge_{_suffix}_{hash(_sugg) % 99999}"):
                        _new_al = dict(aliases)
                        _new_al[_sugg.lower()] = _cand  # alias → canonical
                        save_aliases(_new_al)
                        st.session_state.aliases = _new_al
                        aliases = _new_al
                        st.rerun()

    # ── Aggregate data ────────────────────────────────────────────────────────
    data_a = _matchup_candidate_data(cand_a, adv_spend, weekly_raw, name_to_scope, aliases)
    data_b = _matchup_candidate_data(cand_b, adv_spend, weekly_raw, name_to_scope, aliases)

    same_party  = data_a["party"] == data_b["party"]
    color_a     = _party_color(data_a["party"], 0)
    color_b     = _party_color(data_b["party"], 1 if same_party else 0)
    badge_a     = _party_badge(data_a["party"])
    badge_b     = _party_badge(data_b["party"])

    total_combined = data_a["total"] + data_b["total"]
    pct_a   = data_a["total"] / total_combined * 100 if total_combined > 0 else 50.0
    pct_b   = 100.0 - pct_a
    leader  = cand_a if data_a["total"] >= data_b["total"] else cand_b
    gap     = abs(data_a["total"] - data_b["total"])

    def _fmt(v: float) -> str:
        return f"${v:,.0f}" if v > 0 else "—"

    # ── Spend share header card ───────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:white;border:1px solid #E2DDD7;border-radius:14px;
                padding:20px 24px;margin-bottom:20px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
        <div>
          <div style="font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
                      color:#6B6560;margin-bottom:4px">Combined Spend · All Platforms</div>
          <div style="font-size:24px;font-weight:700;color:#1A1714">{_fmt(total_combined)}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:11px;color:#6B6560;font-weight:600">Spend leader</div>
          <div style="font-size:15px;font-weight:700;color:#1A1714">{_html.escape(leader[:30])}</div>
          <div style="font-size:12px;color:#6B6560">+{_fmt(gap)} advantage</div>
        </div>
      </div>
      <div style="display:flex;border-radius:8px;overflow:hidden;height:10px;background:#F0EDE8">
        <div style="width:{pct_a:.1f}%;background:{color_a};transition:width .4s"></div>
        <div style="width:{pct_b:.1f}%;background:{color_b};transition:width .4s"></div>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:7px">
        <div style="font-size:11px;font-weight:700;color:{color_a}">
          {_html.escape(cand_a[:28])} &nbsp;{pct_a:.0f}%
        </div>
        <div style="font-size:11px;font-weight:700;color:{color_b};text-align:right">
          {pct_b:.0f}%&nbsp; {_html.escape(cand_b[:28])}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_overview, tab_velocity = st.tabs(["Overview", "Spend Velocity"])

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 1 — Overview
    # ─────────────────────────────────────────────────────────────────────────
    with tab_overview:

        def _metric_col(data: dict, color: str, badge: str) -> str:
            _t = data["total"] or 1
            yt_bar_w   = int(data["yt_spend"]   / _t * 100)
            meta_bar_w = int(data["meta_spend"]  / _t * 100)
            snap_bar_w = int(data["snap_spend"]  / _t * 100)
            return f"""
            <div style="background:white;border:1px solid #E2DDD7;border-radius:12px;
                        padding:18px 20px;border-top:4px solid {color};height:100%">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
                {badge}
                <div style="font-size:13px;font-weight:700;color:#1A1714;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                            max-width:180px">{_html.escape(data["name"])}</div>
              </div>
              <div style="margin-bottom:12px">
                <div style="font-size:10px;font-weight:700;letter-spacing:.06em;
                            text-transform:uppercase;color:#6B6560;margin-bottom:2px">
                  Total Spend
                </div>
                <div style="font-size:22px;font-weight:700;color:#1A1714">{_fmt(data["total"])}</div>
              </div>
              <div style="margin-bottom:10px">
                <div style="display:flex;justify-content:space-between;
                            font-size:12px;margin-bottom:3px">
                  <span style="font-weight:600;color:#6B6560">\u25b6 YouTube</span>
                  <span style="font-weight:700;color:#1A1714">{_fmt(data["yt_spend"])}</span>
                </div>
                <div style="height:4px;background:#F0EDE8;border-radius:4px">
                  <div style="width:{yt_bar_w}%;height:4px;background:{color};
                              border-radius:4px"></div>
                </div>
              </div>
              <div style="margin-bottom:10px">
                <div style="display:flex;justify-content:space-between;
                            font-size:12px;margin-bottom:3px">
                  <span style="font-weight:600;color:#6B6560">f&nbsp; Meta</span>
                  <span style="font-weight:700;color:#1A1714">{_fmt(data["meta_spend"])}</span>
                </div>
                <div style="height:4px;background:#F0EDE8;border-radius:4px">
                  <div style="width:{meta_bar_w}%;height:4px;background:{color};
                              opacity:0.5;border-radius:4px"></div>
                </div>
              </div>
              <div style="margin-bottom:10px">
                <div style="display:flex;justify-content:space-between;
                            font-size:12px;margin-bottom:3px">
                  <span style="font-weight:600;color:#6B6560">\U0001F47B Snap</span>
                  <span style="font-weight:700;color:#1A1714">{_fmt(data["snap_spend"])}</span>
                </div>
                <div style="height:4px;background:#F0EDE8;border-radius:4px">
                  <div style="width:{snap_bar_w}%;height:4px;background:{color};
                              opacity:0.35;border-radius:4px"></div>
                </div>
              </div>
              <div style="font-size:12px;color:#6B6560;margin-top:8px">
                <span style="font-weight:600">{data["meta_bulk_ads"]:,}</span> Meta ads
                &nbsp;\u00b7&nbsp;
                <span style="font-weight:600">{data["snap_ads"]:,}</span> Snap ads
              </div>
            </div>"""

        col_card_a, col_spacer, col_card_b = st.columns([1, 0.05, 1])
        with col_card_a:
            st.markdown(_metric_col(data_a, color_a, badge_a), unsafe_allow_html=True)
        with col_card_b:
            st.markdown(_metric_col(data_b, color_b, badge_b), unsafe_allow_html=True)

        st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

        # ── Platform allocation grouped bar ───────────────────────────────────
        if data_a["total"] > 0 or data_b["total"] > 0:
            st.markdown(
                '<h4 style="font-size:13px;font-weight:700;color:#1A1714;margin:0 0 12px">'
                'Platform Allocation</h4>',
                unsafe_allow_html=True,
            )
            fig_alloc = go.Figure()
            for data, color in [(data_a, color_a), (data_b, color_b)]:
                vals = [data["yt_spend"], data["meta_spend"], data["snap_spend"]]
                fig_alloc.add_trace(go.Bar(
                    name=data["name"],
                    x=["\u25b6 YouTube", "f  Meta", "\U0001F47B Snap"],
                    y=vals,
                    marker_color=color,
                    marker_line_width=0,
                    text=[_fmt(v) if v > 0 else "" for v in vals],
                    textposition="outside",
                    textfont=dict(size=11, color="#1A1714"),
                ))
            _cfg = {k: v for k, v in PLOTLY_LIGHT.items() if k not in ("legend", "margin")}
            fig_alloc.update_layout(
                **_cfg,
                barmode="group",
                height=240,
                margin=dict(l=0, r=0, t=30, b=0),
                yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#F0EDE8", showgrid=True),
                xaxis=dict(tickfont=dict(size=12, color="#1A1714")),
                legend=dict(
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#6B6560"),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                ),
            )
            st.plotly_chart(fig_alloc, use_container_width=True, config={"displayModeBar": False})

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 2 — Spend Velocity (YouTube weekly)
    # ─────────────────────────────────────────────────────────────────────────
    with tab_velocity:
        all_weeks = sorted(
            set(data_a["yt_weekly"].keys()) | set(data_b["yt_weekly"].keys())
        )

        if not all_weeks:
            st.info(
                "No weekly YouTube spend data found for the selected candidates. "
                "Make sure YouTube data is loaded and both advertisers have 2026 activity."
            )
        else:
            st.markdown(
                '<p style="font-size:12px;color:#6B6560;margin-bottom:16px">'
                'Weekly YouTube spend · 2026 YTD · solid = Candidate A · dashed = Candidate B</p>',
                unsafe_allow_html=True,
            )

            vals_a  = [data_a["yt_weekly"].get(w, 0.0) for w in all_weeks]
            vals_b  = [data_b["yt_weekly"].get(w, 0.0) for w in all_weeks]
            labels  = [datetime.date.fromisoformat(w).strftime("%b %-d") for w in all_weeks]

            fig_vel = go.Figure()

            # Shaded gap region between the two lines
            fig_vel.add_trace(go.Scatter(
                x=labels + labels[::-1],
                y=vals_a + vals_b[::-1],
                fill="toself",
                fillcolor="rgba(124,58,237,0.06)",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ))

            # Candidate A — solid line
            fig_vel.add_trace(go.Scatter(
                x=labels, y=vals_a,
                name=cand_a,
                mode="lines+markers",
                line=dict(color=color_a, width=2.5),
                marker=dict(size=5, color=color_a),
                hovertemplate="<b>%{x}</b><br>" + cand_a + ": $%{y:,.0f}<extra></extra>",
            ))

            # Candidate B — dashed line
            fig_vel.add_trace(go.Scatter(
                x=labels, y=vals_b,
                name=cand_b,
                mode="lines+markers",
                line=dict(color=color_b, width=2.5, dash="dash"),
                marker=dict(size=5, color=color_b),
                hovertemplate="<b>%{x}</b><br>" + cand_b + ": $%{y:,.0f}<extra></extra>",
            ))

            _cfg = {k: v for k, v in PLOTLY_LIGHT.items() if k not in ("legend", "margin")}
            fig_vel.update_layout(
                **_cfg,
                height=360,
                yaxis=dict(
                    tickprefix="$", tickformat=",.0f",
                    gridcolor="#F0EDE8", showgrid=True,
                ),
                xaxis=dict(tickangle=-30, tickfont=dict(size=10)),
                legend=dict(
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#6B6560"),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                ),
                hovermode="x unified",
            )
            st.plotly_chart(fig_vel, use_container_width=True, config={"displayModeBar": False})

            # ── Week-over-week change cards ───────────────────────────────────
            if len(all_weeks) >= 2:
                def _wow_delta(vals: list) -> tuple:
                    prev, curr = vals[-2], vals[-1]
                    if prev == 0:
                        return None, None
                    delta = curr - prev
                    return delta, delta / prev * 100

                delta_a, pct_a_wow = _wow_delta(vals_a)
                delta_b, pct_b_wow = _wow_delta(vals_b)
                last_lbl = labels[-1]

                wow_cols = st.columns(2)
                for col, data, delta, pct_wow, color in [
                    (wow_cols[0], data_a, delta_a, pct_a_wow, color_a),
                    (wow_cols[1], data_b, delta_b, pct_b_wow, color_b),
                ]:
                    with col:
                        if pct_wow is not None:
                            arrow       = "↑" if delta >= 0 else "↓"
                            trend_color = "#0A8A57" if delta >= 0 else "#C63A1A"
                            st.markdown(f"""
                            <div style="background:white;border:1px solid #E2DDD7;
                                        border-radius:10px;padding:14px 16px;
                                        border-left:4px solid {color}">
                              <div style="font-size:12px;font-weight:700;color:#1A1714;
                                          margin-bottom:2px;white-space:nowrap;overflow:hidden;
                                          text-overflow:ellipsis">{data["name"][:32]}</div>
                              <div style="font-size:11px;color:#6B6560;margin-bottom:6px">
                                Week of {last_lbl}
                              </div>
                              <div style="font-size:22px;font-weight:700;color:{trend_color}">
                                {arrow} {abs(pct_wow):.1f}%
                              </div>
                              <div style="font-size:12px;color:#6B6560">
                                ${abs(delta):,.0f} vs prior week
                              </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background:white;border:1px solid #E2DDD7;
                                        border-radius:10px;padding:14px 16px;
                                        border-left:4px solid {color}">
                              <div style="font-size:12px;font-weight:700;color:#1A1714;
                                          margin-bottom:2px">{data["name"][:32]}</div>
                              <div style="font-size:13px;color:#6B6560">
                                No prior week to compare
                              </div>
                            </div>
                            """, unsafe_allow_html=True)


# ─── Snapchat Political Ads ──────────────────────────────────────────────────

def snap_clean(v) -> str:
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "nat", "") else s


def snap_parse_dt(s):
    s = str(s).strip()
    if not s or s in ("", "nan", "NaT"):
        return None
    try:
        return datetime.datetime.strptime(s[:19], "%Y/%m/%d %H:%M:%S")
    except Exception:
        return None


def snap_fmt_usd(v) -> str:
    if not v:
        return "—"
    v = float(v)
    if v >= 1_000_000:
        return f"${v / 1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v:,.0f}"
    return f"${v:.0f}"


def snap_fmt_num(v) -> str:
    if not v:
        return "—"
    v = int(v)
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.1f}K"
    return str(v)


def fetch_snap_data() -> pd.DataFrame:
    """Download PoliticalAds.zip from Snap and return DataFrame."""
    resp = requests.get(SNAP_ZIP_URL, timeout=120)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_names:
        raise ValueError("No CSV found in Snap zip archive")
    with zf.open(csv_names[0]) as f:
        df = pd.read_csv(f, dtype=str, low_memory=False)
    SNAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(SNAP_CACHE_CSV, index=False)
    meta = {"fetched": datetime.datetime.now().isoformat(), "rows": len(df)}
    SNAP_CACHE_META.write_text(json.dumps(meta))
    return df


def load_snap_cached_data():
    """Return (df, fetched_label) from disk cache, or (None, None)."""
    if not SNAP_CACHE_CSV.exists():
        return None, None
    try:
        df = pd.read_csv(SNAP_CACHE_CSV, dtype=str, low_memory=False)
        fetched = "unknown"
        if SNAP_CACHE_META.exists():
            meta = json.loads(SNAP_CACHE_META.read_text())
            fetched = meta.get("fetched", "")[:16].replace("T", " ")
        return df, fetched
    except Exception as e:
        print(f"[warn] Failed to load Snap cache: {e}")
        return None, None


def process_snap_df(df: pd.DataFrame, recency_days: int = 30) -> list:
    """Filter US rows and build org-level rollups."""
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    cutoff = now - datetime.timedelta(days=recency_days)

    # US filter — handle both column-name variants
    cc_col = "CountryCode" if "CountryCode" in df.columns else "Country Code"
    if cc_col not in df.columns:
        cc_col = next((c for c in df.columns if "country" in c.lower()), None)
    if cc_col is None:
        return []
    us = df[df[cc_col].str.lower().isin(["united states", "us", "usa"])].copy()

    orgs: dict = {}
    for _, row in us.iterrows():
        end_dt = snap_parse_dt(row.get("EndDate", ""))
        if end_dt is None:
            status = "Live"
        elif end_dt >= cutoff:
            status = "Recently Ended"
        else:
            continue

        try:
            spend = float(str(row.get("Spend", 0)).replace(",", "") or 0)
        except Exception:
            spend = 0.0
        try:
            impr = int(str(row.get("Impressions", 0)).replace(",", "") or 0)
        except Exception:
            impr = 0

        org_name = snap_clean(row.get("OrganizationName", "")) or "Unknown"
        payer = snap_clean(row.get("PayingAdvertiserName", ""))
        committee = snap_clean(row.get("CommitteeName", ""))
        candidate = snap_clean(row.get("CandidateBallotInformation", ""))
        gender = snap_clean(row.get("Gender", "")) or "All"
        age = snap_clean(row.get("AgeBracket", "")) or "All"
        regions = snap_clean(row.get("Regions (Included)", "")) or "Nationwide"
        creative = snap_clean(row.get("CreativeUrl", ""))
        jurisdiction = snap_clean(row.get("AdvertisingJurisdiction", ""))

        cpm = round((spend / impr) * 1000, 2) if impr > 0 else 0

        ad_record = {
            "id": str(row.get("ADID", ""))[:12],
            "status": status, "spend": spend, "impressions": impr, "cpm": cpm,
            "start": snap_clean(row.get("StartDate", ""))[:10],
            "end": str(row.get("EndDate", ""))[:10] if end_dt else "Ongoing",
            "payer": payer, "committee": committee, "candidate": candidate,
            "gender": gender, "age": age, "regions": regions,
            "jurisdiction": jurisdiction, "creative_url": creative,
        }

        if org_name not in orgs:
            orgs[org_name] = {
                "org": org_name, "payer": payer or committee,
                "spend": 0.0, "impressions": 0,
                "live_count": 0, "ended_count": 0, "ads": [],
                "genders": set(), "ages": set(), "regions": set(),
            }
        o = orgs[org_name]
        o["spend"] += spend
        o["impressions"] += impr
        if status == "Live":
            o["live_count"] += 1
        else:
            o["ended_count"] += 1
        o["genders"].add(gender)
        o["ages"].add(age)
        if regions != "Nationwide":
            o["regions"].add(regions)
        o["ads"].append(ad_record)

    result = []
    for o in orgs.values():
        o["genders"] = sorted(o["genders"])
        o["ages"] = sorted(o["ages"])
        o["regions"] = sorted(o["regions"]) or ["Nationwide"]
        o["ad_count"] = o["live_count"] + o["ended_count"]
        result.append(o)
    result.sort(key=lambda x: x["spend"], reverse=True)
    return result


# ── Snap HTML renderers ──────────────────────────────────────────────────────

def render_snap_badge(o):
    if o["live_count"] > 0 and o["ended_count"] > 0:
        return (f'<div class="sw-badge both">'
                f'<span class="sw-badge live">\u25cf LIVE ({o["live_count"]})</span>'
                f'<span class="sw-badge ended">\u25d0 ENDED ({o["ended_count"]})</span></div>')
    elif o["live_count"] > 0:
        return f'<span class="sw-badge live">\u25cf LIVE ({o["live_count"]})</span>'
    return f'<span class="sw-badge ended">\u25d0 ENDED ({o["ended_count"]})</span>'


def render_snap_target(o):
    tags = []
    for g in o["genders"]:
        if g != "All":
            tags.append(f'<span class="sw-tag">{_html.escape(g)}</span>')
    for a in o["ages"]:
        tags.append(f'<span class="sw-tag">{_html.escape(a)}</span>')
    for r in o["regions"][:3]:
        tags.append(f'<span class="sw-tag">{_html.escape(r)}</span>')
    if not o["regions"] or o["regions"] == ["Nationwide"]:
        tags.append('<span class="sw-tag">Nationwide</span>')
    return '<div class="sw-target">' + "".join(tags) + "</div>"


def render_snap_ad_card(ad):
    badge_cls = "live" if ad["status"] == "Live" else "ended"
    badge_lbl = "\u25cf LIVE" if ad["status"] == "Live" else "\u25d0 ENDED"
    payer_row = f'<br><strong>Paid by:</strong> {_html.escape(ad["payer"])}' if ad["payer"] else ""
    comm_row = f'<br><strong>Committee:</strong> {_html.escape(ad["committee"])}' if ad["committee"] else ""
    cand_row = f'<br><strong>Candidate/Issue:</strong> {_html.escape(ad["candidate"])}' if ad["candidate"] else ""
    cpm_row = f'<br><strong>CPM:</strong> ${ad["cpm"]}' if ad["cpm"] else ""
    link_row = (f'<br><a class="sw-ad-link" href="{_html.escape(ad["creative_url"])}" '
                f'target="_blank">\u25b6 View Creative</a>') if ad["creative_url"] else ""
    return f"""
    <div class="sw-ad-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div class="sw-ad-spend">{snap_fmt_usd(ad['spend'])}</div>
        <span class="sw-badge {badge_cls}" style="font-size:10px">{badge_lbl}</span>
      </div>
      <div class="sw-ad-meta">
        <strong>Impressions:</strong> {snap_fmt_num(ad['impressions'])}
        {cpm_row}
        <br><strong>Start:</strong> {_html.escape(ad['start'])}
        <br><strong>End:</strong> {_html.escape(ad['end'])}
        <br><strong>Gender:</strong> {_html.escape(ad['gender'])}
        <br><strong>Age:</strong> {_html.escape(ad['age'])}
        <br><strong>Region:</strong> {_html.escape(ad['regions'])}
        {payer_row}{comm_row}{cand_row}{link_row}
      </div>
    </div>"""


def render_snap_table(orgs: list, table_id: str = "sw-main") -> str:
    if not orgs:
        return '<div class="sw-empty">\U0001F47B No advertisers match your current filters.</div>'
    rows_html = ""
    for i, o in enumerate(orgs):
        ads_html = "".join(render_snap_ad_card(a) for a in sorted(o["ads"], key=lambda x: -x["spend"]))
        rows_html += f"""
        <tr onclick="toggleExpand({i},'{table_id}')">
          <td><div class="sw-org">{_html.escape(o['org'])}</div>
              <div class="sw-payer">{_html.escape(o['payer'])}</div></td>
          <td>{render_snap_badge(o)}</td>
          <td><div class="sw-money">{snap_fmt_usd(o['spend'])}</div></td>
          <td><div class="sw-dim">{snap_fmt_num(o['impressions'])}</div></td>
          <td><div class="sw-dim" style="text-align:center">{o['ad_count']}</div></td>
          <td>{render_snap_target(o)}</td>
        </tr>
        <tr id="expand-{table_id}-{i}" style="display:none">
          <td colspan="6"><div class="sw-expand">
            <div class="sw-expand-title">Individual Ads \u2014 {o['ad_count']} total</div>
            <div class="sw-ads-grid">{ads_html}</div>
          </div></td>
        </tr>"""
    return f"""
    <style>
    :root{{--bg:#F6F5F2;--surface:#FFFFFF;--border:#E2DDD7;--border2:#CCC6BE;
          --text:#1A1714;--dim:#6B6560;--accent:#3374AA;--live:#0A8A57;--live-bg:#EDFAF3;
          --ended:#B45309;--ended-bg:#FEF9EC;--orange:#F5902B;}}
    *{{box-sizing:border-box;font-family:'Plus Jakarta Sans',-apple-system,sans-serif;}}
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    .sw-table-wrap{{overflow-x:auto;border-radius:12px;border:1px solid var(--border);
      background:var(--surface);box-shadow:0 1px 6px rgba(0,0,0,.05);}}
    .sw-table{{width:100%;border-collapse:collapse;font-size:13px;}}
    .sw-table thead th{{background:#FAFAF8;color:var(--dim);font-size:10.5px;font-weight:700;
      letter-spacing:.07em;text-transform:uppercase;padding:11px 14px;text-align:left;
      border-bottom:1px solid var(--border);white-space:nowrap;}}
    .sw-table thead th:first-child{{border-radius:12px 0 0 0;}}
    .sw-table thead th:last-child{{border-radius:0 12px 0 0;}}
    .sw-table tbody tr{{border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s;}}
    .sw-table tbody tr:last-child{{border-bottom:none;}}
    .sw-table tbody tr:hover{{background:#FAFAF8;}}
    .sw-table tbody td{{padding:13px 14px;vertical-align:top;}}
    .sw-org{{font-weight:600;font-size:13px;color:var(--text);}}
    .sw-payer{{font-size:11.5px;color:var(--dim);margin-top:2px;}}
    .sw-money{{font-weight:700;font-size:13px;color:var(--text);font-feature-settings:'tnum';}}
    .sw-dim{{font-size:12.5px;color:var(--dim);font-feature-settings:'tnum';}}
    .sw-badge{{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;
      padding:3px 9px;border-radius:20px;white-space:nowrap;letter-spacing:.02em;}}
    .sw-badge.live{{background:var(--live-bg);color:var(--live);}}
    .sw-badge.ended{{background:var(--ended-bg);color:var(--ended);}}
    .sw-badge.both{{display:flex;flex-direction:column;gap:3px;}}
    .sw-target{{font-size:11.5px;color:var(--dim);line-height:1.7;}}
    .sw-tag{{display:inline-block;background:#F0EDEA;color:var(--dim);font-size:10.5px;
      font-weight:600;padding:1px 7px;border-radius:4px;margin:1px 2px 1px 0;}}
    .sw-expand{{background:#FAFAF8;border-top:1px solid var(--border);padding:16px 18px;}}
    .sw-expand-title{{font-size:10.5px;font-weight:700;letter-spacing:.07em;
      text-transform:uppercase;color:var(--dim);margin-bottom:12px;}}
    .sw-ads-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;}}
    .sw-ad-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;
      padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.04);}}
    .sw-ad-spend{{font-size:17px;font-weight:700;color:var(--text);}}
    .sw-ad-meta{{font-size:11.5px;color:var(--dim);line-height:1.8;margin-top:8px;}}
    .sw-ad-meta strong{{color:var(--text);font-weight:600;}}
    .sw-ad-link{{font-size:11px;font-weight:600;color:var(--orange);text-decoration:none;}}
    .sw-empty{{text-align:center;padding:64px 20px;color:var(--dim);font-size:14px;}}
    </style>
    <div class="sw-table-wrap">
      <table class="sw-table">
        <thead><tr>
          <th>Advertiser</th><th>Status</th><th>Spend (USD)</th>
          <th>Impressions</th><th style="text-align:center">Ads</th><th>Targeting</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <script>
    function toggleExpand(i, tid){{
      var el = document.getElementById('expand-'+tid+'-'+i);
      if(!el) return;
      el.style.display = el.style.display==='none' ? 'table-row' : 'none';
    }}
    </script>"""


# ── Snap app view ────────────────────────────────────────────────────────────

def render_snap_app():
    """Snapchat Political Ad Intelligence view."""

    # Header
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:1.75rem;
                padding-bottom:1.25rem;border-bottom:3px solid {SNAP_COLOR}">
      <div>
        <div style="font-size:28px;font-weight:700;letter-spacing:-.03em;color:#1A1714;line-height:1.1">
          \U0001F47B Snapchat Political Ad Intelligence
          <span style="font-size:16px;font-weight:600;color:#6B6560;margin-left:8px">2026</span>
        </div>
      </div>
      <div class="src-pill" style="margin-left:auto">
        <span class="src-dot" style="background:{SNAP_COLOR}"></span>
        Snapchat Political Ads Library &nbsp;\u00b7&nbsp; US only
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.snap_df is None:
        st.info("\U0001F448 Click **Fetch Latest Data** in the sidebar to load the Snapchat Political Ads Library.")
        return

    # Read sidebar controls from session state
    recency = st.session_state.get("snap_recency", 30)
    search = st.session_state.get("snap_search", "")
    sort_by = st.session_state.get("snap_sort", "Spend")

    orgs = process_snap_df(st.session_state.snap_df, recency_days=recency)

    # Party filter
    overrides = st.session_state.get("overrides", {})
    wikidata = get_wikidata_parties()
    party_filter = [p for p in ["D", "R", "N", "?"] if st.session_state.get(f"pf_{p}", True)]
    orgs = [o for o in orgs
            if infer_party(o["org"], "", overrides, wikidata)[0] in party_filter]

    # Search filter
    if search.strip():
        q = search.strip().lower()
        orgs = [o for o in orgs if q in o["org"].lower() or q in o["payer"].lower()]

    # Sort
    if sort_by == "Impressions":
        orgs.sort(key=lambda x: x["impressions"], reverse=True)
    elif sort_by == "Ad Count":
        orgs.sort(key=lambda x: x["ad_count"], reverse=True)

    # Store for Match Up access
    st.session_state.snap_processed_orgs = orgs

    # KPIs
    total_spend = sum(o["spend"] for o in orgs)
    total_impr = sum(o["impressions"] for o in orgs)
    total_live = sum(o["live_count"] for o in orgs)
    total_ended = sum(o["ended_count"] for o in orgs)
    avg_cpm = round((total_spend / total_impr) * 1000, 2) if total_impr > 0 else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Advertisers", len(orgs))
    k2.metric("Total Spend", snap_fmt_usd(total_spend))
    k3.metric("Total Impressions", snap_fmt_num(total_impr))
    k4.metric("Live Ads", f"{total_live:,}")
    k5.metric("Avg CPM", f"${avg_cpm:.2f}")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Tabs
    tab_all, tab_live, tab_ended = st.tabs(["All Active", "\U0001f7e2 Live Now", "\U0001f7e0 Recently Ended"])

    with tab_all:
        html = render_snap_table(orgs, "all")
        components.html(html, height=max(200, 80 + len(orgs) * 95), scrolling=False)

    with tab_live:
        live_orgs = [o for o in orgs if o["live_count"] > 0]
        html = render_snap_table(live_orgs, "live")
        components.html(html, height=max(200, 80 + len(live_orgs) * 95), scrolling=False)

    with tab_ended:
        ended_orgs = [o for o in orgs if o["ended_count"] > 0]
        html = render_snap_table(ended_orgs, "ended")
        components.html(html, height=max(200, 80 + len(ended_orgs) * 95), scrolling=False)


# ─── Meta Ad Library API fetch ───────────────────────────────────────────────

def _parse_api_spend(spend_obj) -> float:
    """Convert Meta API spend object {'lower_bound': '100', 'upper_bound': '499'} → midpoint float."""
    if not spend_obj:
        return 0.0
    if isinstance(spend_obj, dict):
        try:
            lo = float(spend_obj.get("lower_bound", 0) or 0)
            hi = float(spend_obj.get("upper_bound", lo) or lo)
            return (lo + hi) / 2.0
        except (ValueError, TypeError):
            return 0.0
    # Fallback: plain string like "≤100" or "250"
    return parse_bulk_spend(str(spend_obj))


def fetch_meta_api_data(token: str, on_progress=None) -> dict:
    """
    Fetch US political ads from the Meta Ad Library API and aggregate by advertiser.
    Returns a dict matching load_bulk_zip() schema so it plugs straight into the bulk view:
      {
        'advertisers_df': pd.DataFrame(columns=[advertiser, Page name, spend, n_ads]),
        'locations_df':   pd.DataFrame(columns=[advertiser, state, spend]),
        'state_files':    [],
        'source':         'api',
        'fetched_at':     ISO string,
        'total_ads':      int,
      }
    on_progress(fetched_ads, page_num) is called after each page (optional).
    """
    from collections import defaultdict

    params = {
        "ad_type":             "POLITICAL_AND_ISSUE_ADS",
        "ad_reached_countries": "['US']",
        "fields":              "page_name,spend,impressions,delivery_by_region,"
                               "ad_delivery_start_time,ad_delivery_stop_time",
        "limit":               500,
        "access_token":        token,
    }

    adv_spend:  defaultdict = defaultdict(float)
    adv_ads:    defaultdict = defaultdict(int)
    loc_rows:   list        = []
    total_ads = 0
    url        = META_API_URL

    for page_num in range(META_API_MAX_PAGES):
        resp = requests.get(url, params=params if page_num == 0 else None, timeout=60)
        if resp.status_code == 400:
            err = resp.json().get("error", {})
            raise ValueError(f"Meta API error: {err.get('message', resp.text)}")
        resp.raise_for_status()
        data = resp.json()

        ads = data.get("data", [])
        for ad in ads:
            page = ad.get("page_name") or "Unknown"
            spend_mid = _parse_api_spend(ad.get("spend"))
            adv_spend[page] += spend_mid
            adv_ads[page]   += 1

            # Location breakdown (delivery_by_region is a list of {region, percentage})
            for reg in (ad.get("delivery_by_region") or []):
                region = reg.get("region", "")
                try:
                    pct = float(reg.get("percentage", 0) or 0) / 100.0
                except (ValueError, TypeError):
                    pct = 0.0
                if region and pct > 0:
                    loc_rows.append({
                        "advertiser": page,
                        "state":      region,
                        "spend":      round(spend_mid * pct, 2),
                    })

        total_ads += len(ads)
        if on_progress:
            on_progress(total_ads, page_num + 1)

        next_url = data.get("paging", {}).get("next")
        if not next_url or not ads:
            break
        url    = next_url
        params = None   # next URL already contains all query params

    # Build DataFrames
    adv_rows = [
        {"advertiser": name, "Page name": name,
         "spend": round(adv_spend[name], 2), "n_ads": adv_ads[name]}
        for name in adv_spend
    ]
    advertisers_df = (
        pd.DataFrame(adv_rows)
        .sort_values("spend", ascending=False)
        .reset_index(drop=True)
    ) if adv_rows else pd.DataFrame(columns=["advertiser", "Page name", "spend", "n_ads"])

    locations_df = (
        pd.DataFrame(loc_rows)
        if loc_rows
        else pd.DataFrame(columns=["advertiser", "state", "spend"])
    )

    # Persist to disk cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    advertisers_df.to_csv(META_API_CACHE_ADV, index=False)
    locations_df.to_csv(META_API_CACHE_LOC,   index=False)
    META_API_CACHE_META_JSON.write_text(json.dumps({
        "fetched":    datetime.datetime.now().isoformat(),
        "total_ads":  total_ads,
        "advertisers": len(adv_rows),
        "source":     "api",
    }, indent=2))

    return {
        "advertisers_df": advertisers_df,
        "locations_df":   locations_df,
        "state_files":    [],
        "source":         "api",
        "fetched_at":     datetime.datetime.now().isoformat(),
        "total_ads":      total_ads,
    }


def load_meta_api_cache():
    """Load persisted API fetch from disk. Returns (data_dict, fetched_label) or (None, None)."""
    if not META_API_CACHE_ADV.exists():
        return None, None
    try:
        advertisers_df = pd.read_csv(META_API_CACHE_ADV)
        locations_df   = (
            pd.read_csv(META_API_CACHE_LOC)
            if META_API_CACHE_LOC.exists()
            else pd.DataFrame(columns=["advertiser", "state", "spend"])
        )
        fetched_label = "unknown"
        total_ads     = 0
        if META_API_CACHE_META_JSON.exists():
            meta = json.loads(META_API_CACHE_META_JSON.read_text())
            fetched_label = meta.get("fetched", "")[:16].replace("T", " ")
            total_ads     = meta.get("total_ads", 0)
        return {
            "advertisers_df": advertisers_df,
            "locations_df":   locations_df,
            "state_files":    [],
            "source":         "api",
            "fetched_at":     fetched_label,
            "total_ads":      total_ads,
        }, fetched_label
    except Exception as e:
        print(f"[warn] Failed to load Meta API cache: {e}")
        return None, None


def render_meta_app():
    """Top-level Meta router: bulk view, single view, or landing.
    Bulk data may come from either a manually-uploaded ZIP or from the API fetch.
    API data takes precedence only when no ZIP is loaded.
    """
    has_zip_bulk = st.session_state.get("meta_bulk_bytes") is not None
    has_api_bulk = st.session_state.get("meta_api_data") is not None
    has_bulk     = has_zip_bulk or has_api_bulk
    has_single   = bool(st.session_state.get("meta_dfs", {}))

    # Determine which bulk data to use (ZIP preferred over API)
    if has_zip_bulk:
        _bulk_data  = st.session_state.meta_bulk_data
        _bulk_bytes = st.session_state.meta_bulk_bytes
        _bulk_src   = "zip"
    elif has_api_bulk:
        _bulk_data  = st.session_state.meta_api_data
        _bulk_bytes = None   # API data has no ZIP bytes — render_bulk_view handles None
        _bulk_src   = "api"
    else:
        _bulk_data  = None
        _bulk_bytes = None
        _bulk_src   = None

    # ── Header ────────────────────────────────────────────────────────────────
    _src_label = {
        "zip": "Library Report ZIP",
        "api": f"Meta Ad Library API · {_bulk_data['total_ads']:,} ads" if _bulk_data else "",
    }.get(_bulk_src, "")
    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;'
        'padding-bottom:1.25rem;border-bottom:3px solid #1877F2">'
        '<div style="width:32px;height:32px;background:#1877F2;border-radius:8px;'
        'display:flex;align-items:center;justify-content:center;'
        'font-size:18px;color:#fff;font-weight:900">f</div>'
        '<div><div style="font-size:20px;font-weight:800;color:#1A1714">Meta Political Ad Intelligence</div>'
        f'<div style="font-size:12px;color:#6B6560">Ad Library · 2026'
        + (f' &nbsp;·&nbsp; {_html.escape(_src_label)}' if _src_label else "")
        + '</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not has_bulk and not has_single:
        # Landing — show 3 cards now (ZIP, API, single)
        c1, c2, c3 = st.columns(3)
        for col, icon, title, desc, hint in [
            (c1, "📊", "Library Report ZIP",
             "Full political ad market — all advertisers, state-level spend breakdown.",
             "Upload the FacebookAdLibraryReport ZIP from facebook.com/ads/library/report"),
            (c2, "⚡", "Fetch via API",
             "Automatically pull fresh data using your Meta Ad Library token — no ZIP needed.",
             "Click '↻ Fetch from Meta API' in the sidebar. Requires a Meta token."),
            (c3, "🔍", "Advertiser Export",
             "Single-advertiser deep dive — spend trends, creative themes, audience demographics.",
             "Upload a meta-ad-library CSV export for one advertiser from the Ad Library"),
        ]:
            col.markdown(
                f'<div style="background:#fff;border:1px solid #E2DDD7;border-radius:14px;'
                f'padding:28px;height:100%">'
                f'<div style="font-size:32px;margin-bottom:12px">{icon}</div>'
                f'<div style="font-size:16px;font-weight:700;color:#1A1714;margin-bottom:8px">{title}</div>'
                f'<div style="font-size:13px;color:#6B6560;margin-bottom:14px">{desc}</div>'
                f'<div style="font-size:11px;color:#9CA3AF;background:#F6F5F2;border-radius:8px;'
                f'padding:8px 12px">{hint}</div></div>',
                unsafe_allow_html=True,
            )
        return

    if has_bulk and has_single:
        view_tab_bulk, view_tab_single = st.tabs(["Library Report", "Advertiser Analysis"])
        with view_tab_bulk:
            render_bulk_view(_bulk_data, _bulk_bytes)
        with view_tab_single:
            render_single_advertiser_view()
    elif has_bulk:
        render_bulk_view(_bulk_data, _bulk_bytes)
    else:
        render_single_advertiser_view()


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # ── Session state ──────────────────────────────────────────────────────────
    if "overrides" not in st.session_state:
        st.session_state.overrides = load_overrides()
    if "platform" not in st.session_state:
        st.session_state.platform = "youtube"
    if "aliases" not in st.session_state:
        st.session_state.aliases = load_aliases()
    for _sk, _sv in [("snap_df", None), ("snap_fetched_at", None),
                      ("snap_fetch_error", None), ("snap_processed_orgs", [])]:
        if _sk not in st.session_state:
            st.session_state[_sk] = _sv
    # Auto-load Snap cache from disk on first run
    if st.session_state.snap_df is None:
        _sdf, _sfetch = load_snap_cached_data()
        if _sdf is not None:
            st.session_state.snap_df = _sdf
            st.session_state.snap_fetched_at = _sfetch
    # Meta API session state
    for _sk, _sv in [("meta_api_data", None), ("meta_api_fetched_at", None),
                      ("meta_api_error", None), ("meta_api_token", ""),
                      ("show_meta_api_token", False)]:
        if _sk not in st.session_state:
            st.session_state[_sk] = _sv
    # Auto-load Meta API cache from disk on first run
    if st.session_state.meta_api_data is None:
        _mdata, _mfetch = load_meta_api_cache()
        if _mdata is not None:
            st.session_state.meta_api_data = _mdata
            st.session_state.meta_api_fetched_at = _mfetch

    wikidata_parties = get_wikidata_parties()
    _platform = st.session_state.platform

    # ── Top Navigation Bar ────────────────────────────────────────────────────
    _nc1, _nc2, _nc3, _nc4, _nc_space = st.columns([1, 1, 1, 1, 4])
    if _nc1.button("▶  YouTube",  key="plat_yt",      use_container_width=True,
                   type="primary" if _platform == "youtube"  else "secondary"):
        st.session_state.platform = "youtube";  st.rerun()
    if _nc2.button("f  Meta",     key="plat_meta",    use_container_width=True,
                   type="primary" if _platform == "meta"     else "secondary"):
        st.session_state.platform = "meta";     st.rerun()
    if _nc3.button("\U0001F47B  Snap", key="plat_snap", use_container_width=True,
                   type="primary" if _platform == "snap"     else "secondary"):
        st.session_state.platform = "snap";     st.rerun()
    if _nc4.button("\u26a1  Match Up", key="plat_matchup", use_container_width=True,
                   type="primary" if _platform == "matchup"  else "secondary"):
        st.session_state.platform = "matchup";  st.rerun()

    # JS: style top-nav buttons (scoped to main content, not sidebar)
    components.html(f"""<script>
(function(){{
  const NAV = {json.dumps({
      "YouTube":  {"bg": "#3374AA", "bd": "#3374AA"},
      "Meta":     {"bg": "#1877F2", "bd": "#1877F2"},
      "Snap":     {"bg": SNAP_COLOR, "bd": SNAP_COLOR},
      "Match Up": {"bg": "#7C3AED", "bd": "#7C3AED"},
  })};
  function styleNav(){{
    const main = window.parent.document.querySelector('[data-testid="stMain"]');
    if (!main) return;
    // Only target buttons in the first horizontal block (the nav row)
    const firstRow = main.querySelector('[data-testid="stHorizontalBlock"]');
    if (!firstRow) return;
    firstRow.querySelectorAll('button').forEach(b => {{
      const txt  = b.textContent.trim();
      const key  = Object.keys(NAV).find(k => txt.includes(k));
      if (!key) return;
      const c      = NAV[key];
      const active = b.getAttribute('data-testid') === 'stBaseButton-primary';
      b.style.setProperty('background',    active ? c.bg : 'transparent', 'important');
      b.style.setProperty('color',         active ? '#fff' : 'rgba(107,101,96,0.8)', 'important');
      b.style.setProperty('border',        '1.5px solid ' + (active ? c.bd : '#E2DDD7'), 'important');
      b.style.setProperty('border-radius', '8px', 'important');
      b.style.setProperty('font-weight',   '700', 'important');
      b.style.setProperty('font-size',     '13px', 'important');
      b.style.setProperty('box-shadow',    'none', 'important');
    }});
  }}
  styleNav();
  new MutationObserver(styleNav).observe(
    window.parent.document.body,
    {{subtree: true, childList: true, attributeFilter: ['data-testid']}}
  );
}})();
</script>""", height=0)

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    # ── Header — only shown on YouTube platform ───────────────────────────────
    if _platform == "youtube":
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:1.75rem;
                    padding-bottom:1.25rem;border-bottom:3px solid #F5902B">
          <div>
            <div style="font-size:28px;font-weight:700;letter-spacing:-.03em;color:#1A1714;line-height:1.1">
              YouTube Political Ad Spend
              <span style="font-size:16px;font-weight:600;color:#6B6560;margin-left:8px">2026 Cycle</span>
            </div>
          </div>
          <div class="src-pill" style="margin-left:auto">
            <span class="src-dot"></span>
            Google Transparency Report &nbsp;·&nbsp; VIDEO ads &nbsp;·&nbsp; US only
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        # ── Party Affiliation ──────────────────────────────────────────────────
        st.markdown('<div class="sb-label">Party Affiliation</div>', unsafe_allow_html=True)

        _PARTY_ROWS = [
            ("D", "Democrat",             "#EBF3FA", "#BFDBFE", "#1A56DB", "#93C5FD"),
            ("R", "Republican",           "#FFF1EE", "#FECACA", "#C81E1E", "#FCA5A5"),
            ("N", "Neutral / Bipartisan", "#F5F3FF", "#DDD6FE", "#6D28D9", "#C4B5FD"),
            ("?", "Unknown",              "#F3F4F6", "#D1D5DB", "#374151", "#9CA3AF"),
        ]
        party_filter = []
        for _code, _label, _abg, _abrd, _ac, _ic in _PARTY_ROWS:
            _key = f"pf_{_code}"
            if _key not in st.session_state:
                st.session_state[_key] = True
            _on = st.session_state[_key]
            if st.button(_label, key=f"_btn_{_code}",
                         use_container_width=True,
                         type="primary" if _on else "secondary"):
                st.session_state[_key] = not _on
                st.rerun()
            if st.session_state[_key]:
                party_filter.append(_code)
        if not party_filter:
            party_filter = ["D", "R", "N", "?"]

        # JS: style party buttons by text content (CSS :has() doesn't reach sidebar DOM)
        _pj = {row[1]: {"ab":row[2],"abrd":row[3],"ac":row[4],"ic":row[5]}
               for row in _PARTY_ROWS}
        components.html(f"""<script>
(function(){{
  const C={json.dumps(_pj)};
  function apply(){{
    const sb=window.parent.document.querySelector('[data-testid="stSidebar"]');
    if(!sb)return;
    sb.querySelectorAll('button').forEach(b=>{{
      const txt=b.textContent.trim();
      if(!C[txt])return;
      const c=C[txt],active=b.getAttribute('data-testid')==='stBaseButton-primary';
      b.style.setProperty('background',active?c.ab:'transparent','important');
      b.style.setProperty('border','1.5px solid '+(active?c.abrd:c.abrd),'important');
      b.style.setProperty('color',active?c.ac:c.ic,'important');
      b.style.setProperty('box-shadow','none','important');
    }});
  }}
  apply();
  new MutationObserver(apply).observe(
    window.parent.document.body,
    {{subtree:true,childList:true,attributeFilter:['data-testid']}}
  );
}})();
</script>""", height=0)

        _sb_plat = st.session_state.get("platform", "youtube")
        if _sb_plat == "youtube":
            # ── CTV Data Upload ────────────────────────────────────────────────
            st.markdown('<div class="sb-sep"></div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-label">CTV Comparison Data</div>', unsafe_allow_html=True)

            if "show_ctv_uploader" not in st.session_state:
                st.session_state.show_ctv_uploader = False
            if "ctv_data" not in st.session_state:
                st.session_state.ctv_data = load_ctv_upload()
            if "ctv_status" not in st.session_state:
                st.session_state.ctv_status = (
                    "Real data loaded from cache." if st.session_state.ctv_data else ""
                )

            has_ctv = bool(st.session_state.ctv_data)

            # Status badge
            if has_ctv:
                n_advs = len(st.session_state.ctv_data)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;'
                    f'margin-bottom:8px;padding:6px 10px;background:#F0FDF4;'
                    f'border:1px solid #86EFAC;border-radius:8px">'
                    f'<span style="color:#16A34A;font-size:14px">✓</span>'
                    f'<span style="font-size:12px;color:#15803D;font-weight:600">'
                    f'Real CTV data · {n_advs:,} advertisers</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:6px;'
                    'margin-bottom:8px;padding:6px 10px;background:#FEF3E8;'
                    'border:1px solid #F5902B;border-radius:8px">'
                    '<span style="color:#F5902B;font-size:14px">⚠️</span>'
                    '<span style="font-size:12px;color:#9A4A00;font-weight:600">'
                    'Mock data active</span></div>',
                    unsafe_allow_html=True,
                )

            if st.button("⬆  Upload CTV Data", use_container_width=True, key="ctv_upload_btn"):
                st.session_state.show_ctv_uploader = not st.session_state.show_ctv_uploader

            if st.session_state.show_ctv_uploader:
                st.markdown(
                    '<div style="font-size:11px;color:#6B6560;margin:6px 0 4px;line-height:1.5">'
                    'Upload an AdImpact, iSpot, or similar CTV export.<br>'
                    'Needs columns for: Advertiser, Week/Date, Spend.</div>',
                    unsafe_allow_html=True,
                )
                _ctv_file = st.file_uploader(
                    "CTV data",
                    type=["csv", "xlsx", "xls"],
                    accept_multiple_files=False,
                    label_visibility="collapsed",
                    key="ctv_file_input",
                )
                if _ctv_file is not None:
                    _data, _msg = parse_ctv_upload(_ctv_file.read(), _ctv_file.name)
                    if _data:
                        save_ctv_upload(_data)
                        st.session_state.ctv_data          = _data
                        st.session_state.ctv_status        = f"✓ {_msg}"
                        st.session_state.show_ctv_uploader = False
                        st.rerun()
                    else:
                        st.error(_msg)

            if st.session_state.ctv_status:
                st.markdown(
                    f'<div style="font-size:11px;color:#6B6560;margin-top:4px">'
                    f'{st.session_state.ctv_status}</div>',
                    unsafe_allow_html=True,
                )

            if has_ctv:
                if st.button("✕  Clear CTV Data", use_container_width=True, key="ctv_clear_btn"):
                    if CTV_CACHE_FILE.exists():
                        CTV_CACHE_FILE.unlink(missing_ok=True)
                    st.session_state.ctv_data   = {}
                    st.session_state.ctv_status = ""
                    st.rerun()

            # ── Time Range ─────────────────────────────────────────────────────
            st.markdown('<div class="sb-sep"></div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-label">Time Range</div>', unsafe_allow_html=True)

            if "time_preset" not in st.session_state:
                st.session_state.time_preset = "YTD 2026"

            _presets = ["YTD 2026", "Last 30 Days", "Last 7 Days", "Custom"]
            _pc1, _pc2 = st.columns(2)
            for _i, _preset in enumerate(_presets):
                _col = _pc1 if _i % 2 == 0 else _pc2
                _active = st.session_state.time_preset == _preset
                if _col.button(_preset, key=f"tr_{_preset}",
                               use_container_width=True,
                               type="primary" if _active else "secondary"):
                    st.session_state.time_preset = _preset
                    st.rerun()

            time_preset = st.session_state.time_preset
            if time_preset == "Last 7 Days":
                date_from = TODAY - datetime.timedelta(days=6)
                date_to   = TODAY
            elif time_preset == "Last 30 Days":
                date_from = TODAY - datetime.timedelta(days=29)
                date_to   = TODAY
            elif time_preset == "Custom":
                custom_range = st.date_input(
                    "Select range",
                    value=(WINDOW_START, TODAY),
                    min_value=datetime.date(2018, 1, 1),
                    max_value=TODAY,
                    label_visibility="collapsed",
                )
                if isinstance(custom_range, (list, tuple)) and len(custom_range) == 2:
                    date_from, date_to = custom_range[0], custom_range[1]
                else:
                    date_from = date_to = custom_range if custom_range else TODAY
            else:  # YTD 2026
                date_from = WINDOW_START
                date_to   = TODAY

            # ── Methodology ────────────────────────────────────────────────────
            st.markdown('<div class="sb-sep"></div>', unsafe_allow_html=True)
            with st.expander("Methodology & Data Sources"):
                st.markdown(f"""
**Leaderboard** — `advertiser-weekly-spend.csv`
Exact weekly USD totals filtered to weeks starting on or after 2026-01-01.

**Daily chart** — `creative-stats.csv`
Max/min spend ranges prorated across each ad's run dates. ~2.6 GB uncompressed; cached after first run.

**State breakdown** — `advertiser-geo-spend.csv`
Exact lifetime USD spend by advertiser × state, filtered to 2026-active advertisers. All-time, not 2026-only.

**Party inference — 4-tier system**
0 · Manual override → 2 · Curated lookup (~100 entries) → 2b · Declared scope text → 3 · Keywords → 4 · Unknown

Google data typically has a 24–48 hr reporting lag.

---
Source: Google Political Ads Transparency Report
Data cached 24 hrs · Generated {TODAY.strftime("%B %d, %Y")}
                """)

        elif _sb_plat == "meta":
            # ── Meta: Library Report upload ────────────────────────────────────
            st.markdown('<div class="sb-label">Meta Ad Data</div>', unsafe_allow_html=True)

            # ── Session state init ─────────────────────────────────────────────
            for _k, _v in [
                ("show_bulk_uploader",   False),
                ("meta_bulk_bytes",      None),
                ("meta_bulk_data",       None),
                ("show_single_uploader", False),
                ("meta_dfs",             {}),
                ("meta_home_state",      "(none)"),
            ]:
                if _k not in st.session_state:
                    st.session_state[_k] = _v

            # ── 1. Library Report (ZIP) ────────────────────────────────────────
            _has_bulk = st.session_state.meta_bulk_bytes is not None
            if _has_bulk:
                _n_adv = len(st.session_state.meta_bulk_data["advertisers_df"])
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    f'background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;margin-bottom:6px">'
                    f'<span style="color:#16A34A">✓</span>'
                    f'<span style="font-size:12px;color:#15803D;font-weight:600">'
                    f'Library Report · {_n_adv:,} advertisers</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    'background:#F5F3FF;border:1px solid #DDD6FE;border-radius:8px;margin-bottom:6px">'
                    '<span style="color:#7C3AED">○</span>'
                    '<span style="font-size:12px;color:#6D28D9;font-weight:600">'
                    'No Library Report</span></div>',
                    unsafe_allow_html=True,
                )

            if st.button("⬆  Upload Library Report", use_container_width=True, key="bulk_upload_btn"):
                st.session_state.show_bulk_uploader = not st.session_state.show_bulk_uploader

            if st.session_state.show_bulk_uploader:
                st.markdown(
                    '<div style="font-size:11px;color:#6B6560;margin:4px 0;line-height:1.5">'
                    'FacebookAdLibraryReport ZIP from facebook.com/ads/library/report'
                    '</div>', unsafe_allow_html=True,
                )
                _bulk_file = st.file_uploader(
                    "Library ZIP", type=["zip"],
                    accept_multiple_files=False,
                    label_visibility="collapsed",
                    key="bulk_file_input",
                )
                if _bulk_file is not None:
                    try:
                        _raw = _bulk_file.read()
                        _data = load_bulk_zip(_raw)
                        st.session_state.meta_bulk_bytes      = _raw
                        st.session_state.meta_bulk_data       = _data
                        st.session_state.show_bulk_uploader   = False
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Error parsing ZIP: {_e}")

            if _has_bulk:
                if st.button("✕  Clear Library Report", use_container_width=True, key="bulk_clear_btn"):
                    st.session_state.meta_bulk_bytes = None
                    st.session_state.meta_bulk_data  = None
                    st.rerun()

            # ── 1b. Fetch from Meta API ────────────────────────────────────────
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:11px;font-weight:700;letter-spacing:.07em;'
                'text-transform:uppercase;color:#6B6560;margin-bottom:6px">'
                'Or fetch via API</div>',
                unsafe_allow_html=True,
            )

            # Token: prefer META_TOKEN env var, fall back to user input
            _env_token = os.getenv("META_TOKEN", "")
            _has_api_data = st.session_state.meta_api_data is not None

            if _has_api_data:
                _n_api_adv = len(st.session_state.meta_api_data["advertisers_df"])
                _api_total = st.session_state.meta_api_data.get("total_ads", 0)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    f'background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;margin-bottom:6px">'
                    f'<span style="color:#16A34A">\u2713</span>'
                    f'<span style="font-size:12px;color:#15803D;font-weight:600">'
                    f'API data \u00b7 {_n_api_adv:,} advertisers</span></div>',
                    unsafe_allow_html=True,
                )
                if st.session_state.meta_api_fetched_at:
                    st.caption(f"Last fetched: {st.session_state.meta_api_fetched_at}")
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    'background:#EBF3FA;border:1px solid #93C5FD;border-radius:8px;margin-bottom:6px">'
                    '<span style="color:#3374AA">\u25cb</span>'
                    '<span style="font-size:12px;color:#1A56DB;font-weight:600">'
                    'No API data</span></div>',
                    unsafe_allow_html=True,
                )

            # Show token input only when no env token
            _active_token = _env_token
            if not _env_token:
                if st.button(
                    "\U0001f511  Enter API Token" if not st.session_state.show_meta_api_token
                    else "\u25b4  Hide token input",
                    use_container_width=True, key="meta_token_toggle",
                ):
                    st.session_state.show_meta_api_token = not st.session_state.show_meta_api_token

                if st.session_state.show_meta_api_token:
                    _typed = st.text_input(
                        "Meta API token",
                        value=st.session_state.meta_api_token,
                        type="password",
                        label_visibility="collapsed",
                        placeholder="Paste your Meta Ad Library token\u2026",
                        key="meta_token_input",
                    )
                    st.session_state.meta_api_token = _typed
                    _active_token = _typed
                    st.markdown(
                        '<div style="font-size:10px;color:#6B6560;margin-top:2px">'
                        'Get a token at facebook.com/ads/library/api</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div style="font-size:10px;color:#16A34A;margin-bottom:6px">'
                    '\u2713 Using META_TOKEN environment variable</div>',
                    unsafe_allow_html=True,
                )

            _can_fetch = bool(_active_token)
            if st.button(
                "\u21bb  Fetch from Meta API",
                use_container_width=True,
                key="meta_api_fetch_btn",
                disabled=not _can_fetch,
                type="primary",
            ):
                _prog_text = st.empty()
                _prog_bar  = st.progress(0)
                try:
                    def _on_progress(fetched, page_num):
                        _prog_text.markdown(
                            f'<div style="font-size:11px;color:#6B6560">'
                            f'Page {page_num} \u2014 {fetched:,} ads fetched\u2026</div>',
                            unsafe_allow_html=True,
                        )
                        _prog_bar.progress(min(page_num / META_API_MAX_PAGES, 0.99))

                    _mdata = fetch_meta_api_data(_active_token, on_progress=_on_progress)
                    st.session_state.meta_api_data      = _mdata
                    st.session_state.meta_api_fetched_at = _mdata["fetched_at"][:16].replace("T", " ")
                    st.session_state.meta_api_error     = None
                    st.session_state.show_meta_api_token = False
                    _prog_bar.progress(1.0)
                    _prog_text.empty()
                    st.rerun()
                except Exception as _e:
                    _prog_bar.empty()
                    _prog_text.empty()
                    st.session_state.meta_api_error = str(_e)

            if st.session_state.meta_api_error:
                st.error(f"Fetch failed: {st.session_state.meta_api_error}")

            if _has_api_data:
                if st.button("✕  Clear API Data", use_container_width=True, key="meta_api_clear_btn"):
                    st.session_state.meta_api_data      = None
                    st.session_state.meta_api_fetched_at = None
                    for _f in [META_API_CACHE_ADV, META_API_CACHE_LOC, META_API_CACHE_META_JSON]:
                        _f.unlink(missing_ok=True)
                    st.rerun()

            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

            # ── 2. Single Advertiser Export (CSV) ─────────────────────────────
            _has_single = bool(st.session_state.meta_dfs)
            if _has_single:
                _n_files = len(st.session_state.meta_dfs)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    f'background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;margin-bottom:6px">'
                    f'<span style="color:#16A34A">✓</span>'
                    f'<span style="font-size:12px;color:#15803D;font-weight:600">'
                    f'Advertiser Export · {_n_files} file(s)</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    'background:#FEF3E8;border:1px solid #F5902B;border-radius:8px;margin-bottom:6px">'
                    '<span style="color:#F5902B">○</span>'
                    '<span style="font-size:12px;color:#9A4A00;font-weight:600">'
                    'No Advertiser Export</span></div>',
                    unsafe_allow_html=True,
                )

            if st.button("⬆  Upload Advertiser Export", use_container_width=True, key="single_upload_btn"):
                st.session_state.show_single_uploader = not st.session_state.show_single_uploader

            if st.session_state.show_single_uploader:
                st.markdown(
                    '<div style="font-size:11px;color:#6B6560;margin:4px 0;line-height:1.5">'
                    'Meta Ad Library CSV export for a single advertiser.'
                    '</div>', unsafe_allow_html=True,
                )
                _single_files = st.file_uploader(
                    "Advertiser CSV", type=["csv"],
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                    key="single_file_input",
                )
                if _single_files:
                    _new = dict(st.session_state.meta_dfs)
                    for _sf in _single_files:
                        try:
                            _new[_sf.name] = load_meta_csv(_sf.read())
                        except Exception as _e:
                            st.error(f"Error parsing {_sf.name}: {_e}")
                    st.session_state.meta_dfs             = _new
                    st.session_state.show_single_uploader = False
                    st.rerun()

            if _has_single:
                if st.button("✕  Clear Advertiser Export", use_container_width=True, key="single_clear_btn"):
                    st.session_state.meta_dfs = {}
                    st.rerun()

            # ── Home State (for single-advertiser analysis) ────────────────────
            if _has_single:
                st.markdown('<div class="sb-sep"></div>', unsafe_allow_html=True)
                st.markdown("<div class=\"sb-label\">Candidate's Home State</div>", unsafe_allow_html=True)
                _state_opts = ["(none)"] + sorted(STATE_NAMES_BY_ABBR.values())
                _hs = st.selectbox(
                    "Home state", options=_state_opts,
                    index=_state_opts.index(st.session_state.meta_home_state),
                    label_visibility="collapsed", key="meta_hs_select",
                )
                if _hs != st.session_state.meta_home_state:
                    st.session_state.meta_home_state = _hs
                    st.rerun()

            # date_from / date_to defaults (YouTube code never runs for Meta platform)
            date_from = WINDOW_START
            date_to   = TODAY

        elif _sb_plat == "matchup":
            # ── Match Up: Alias Manager ────────────────────────────────────────
            st.markdown('<div class="sb-sep"></div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-label">Advertiser Aliases</div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:11px;color:#6B6560;margin-bottom:10px;line-height:1.5">'
                'Merge different names that refer to the same candidate across platforms.</div>',
                unsafe_allow_html=True,
            )
            if "aliases" not in st.session_state:
                st.session_state.aliases = load_aliases()
            _aliases = st.session_state.aliases
            if _aliases:
                for _al, _can in list(_aliases.items()):
                    _ac1, _ac2 = st.columns([5, 1])
                    _ac1.markdown(
                        f'<div style="font-size:11px;color:#6B6560;line-height:1.4;padding:3px 0">'
                        f'{_al}<br>'
                        f'<span style="color:#1A1714;font-weight:700">→ {_can}</span></div>',
                        unsafe_allow_html=True,
                    )
                    if _ac2.button("✕", key=f"del_al_{hash(_al) % 99999}"):
                        _new_al = dict(_aliases)
                        del _new_al[_al]
                        save_aliases(_new_al)
                        st.session_state.aliases = _new_al
                        st.rerun()
            else:
                st.markdown(
                    '<div style="font-size:12px;color:#6B6560;font-style:italic">'
                    'No aliases yet. Select candidates in Match Up to see suggestions.</div>',
                    unsafe_allow_html=True,
                )
            # date_from / date_to defaults (not used in matchup path)
            date_from = WINDOW_START
            date_to   = TODAY

        elif _sb_plat == "snap":
            # ── Snapchat Controls ──────────────────────────────────────────────
            st.markdown('<div class="sb-sep"></div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-label">Snapchat Ad Data</div>', unsafe_allow_html=True)

            _has_snap = st.session_state.snap_df is not None
            if _has_snap:
                _snap_rows = len(st.session_state.snap_df)
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    f'background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;margin-bottom:6px">'
                    f'<span style="color:#16A34A">\u2713</span>'
                    f'<span style="font-size:12px;color:#15803D;font-weight:600">'
                    f'Snap data \u00b7 {_snap_rows:,} rows</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;'
                    f'background:#FEF9EC;border:1px solid {SNAP_COLOR};border-radius:8px;margin-bottom:6px">'
                    f'<span style="color:{SNAP_COLOR}">\u25cb</span>'
                    '<span style="font-size:12px;color:#92700C;font-weight:600">'
                    'No data loaded</span></div>',
                    unsafe_allow_html=True,
                )

            if st.button("\u21bb  Fetch Latest Data", type="primary", use_container_width=True, key="snap_fetch_btn"):
                with st.spinner("Downloading from Snapchat\u2026"):
                    try:
                        _sdf = fetch_snap_data()
                        st.session_state.snap_df = _sdf
                        st.session_state.snap_fetched_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        st.session_state.snap_fetch_error = None
                        st.rerun()
                    except Exception as _e:
                        st.session_state.snap_fetch_error = str(_e)

            if st.session_state.snap_fetch_error:
                st.error(f"Fetch failed: {st.session_state.snap_fetch_error}")

            if st.session_state.snap_fetched_at:
                st.caption(f"Last updated: {st.session_state.snap_fetched_at}")

            st.markdown('<div class="sb-sep"></div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-label">Filters</div>', unsafe_allow_html=True)

            _snap_recency = st.selectbox(
                "Show ads ended within",
                [30, 60, 90],
                format_func=lambda x: f"Last {x} days",
                index=0,
                key="snap_recency_select",
            )
            st.session_state.snap_recency = _snap_recency

            _snap_search = st.text_input(
                "Search advertiser / payer",
                placeholder="e.g. Daily Wire",
                key="snap_search_input",
            )
            st.session_state.snap_search = _snap_search

            _snap_sort = st.selectbox(
                "Sort by",
                ["Spend", "Impressions", "Ad Count"],
                key="snap_sort_select",
            )
            st.session_state.snap_sort = _snap_sort

            date_from = WINDOW_START
            date_to   = TODAY

    # ── Platform conditional rendering ────────────────────────────────────────
    _platform = st.session_state.get("platform", "youtube")
    if _platform == "meta":
        render_meta_app()
        return
    if _platform == "matchup":
        render_matchup()
        return
    if _platform == "snap":
        render_snap_app()
        return

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("Checking data cache…"):
        zip_path = download_bundle()

    fast         = load_fast_data(str(zip_path), TODAY.isoformat())
    daily_spend  = load_daily_data(str(zip_path), TODAY.isoformat())
    mock_ctv     = get_mock_ctv_data(str(zip_path), TODAY.isoformat())

    adv_spend       = fast["adv_spend"]
    weekly_raw      = fast["weekly_raw"]
    state_spend     = fast["state_spend"]
    state_adv_spend = fast["state_adv_spend"]
    name_to_scope   = fast["name_to_scope"]

    if not adv_spend:
        st.error("No 2026 US YouTube ad data found.")
        return

    # ── Apply time-range filter ────────────────────────────────────────────────
    date_from_str = date_from.isoformat()
    date_to_str   = date_to.isoformat()
    is_ytd        = (date_from == WINDOW_START and date_to == TODAY)

    if is_ytd:
        adv_spend_filtered = adv_spend          # already 2026 YTD — no re-sum needed
    else:
        adv_spend_filtered = {}
        one_week = datetime.timedelta(days=6)
        for name, weeks in weekly_raw.items():
            total = 0.0
            for wk, sp in weeks.items():
                wk_end = (datetime.date.fromisoformat(wk) + one_week).isoformat()
                if wk <= date_to_str and wk_end >= date_from_str:
                    total += sp
            if total > 0:
                adv_spend_filtered[name] = total

    # Daily chart filtered to selected window
    dates_all    = sorted(daily_spend.keys())
    dates        = [d for d in dates_all if date_from_str <= d <= date_to_str]
    max_vals     = [round(daily_spend[d]["max"]) for d in dates]
    min_vals     = [round(daily_spend[d]["min"]) for d in dates]

    # ── KPI strip ─────────────────────────────────────────────────────────────
    overrides_kpi   = st.session_state.overrides
    total_spend     = sum(adv_spend_filtered.values())
    active_advs     = len(adv_spend_filtered)
    top_adv         = max(adv_spend_filtered, key=adv_spend_filtered.get) if adv_spend_filtered else "—"

    # Partisan spend totals
    dem_spend = rep_spend = 0.0
    for name, spend in adv_spend_filtered.items():
        p = infer_party(name, name_to_scope.get(name, ""), overrides_kpi, wikidata_parties)[0]
        if p == "D":
            dem_spend += spend
        elif p == "R":
            rep_spend += spend

    range_label = (
        "YTD 2026" if is_ytd else
        f"{date_from.strftime('%b %-d')} – {date_to.strftime('%b %-d, %Y')}"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Spend", money(total_spend),
              help=f"Exact USD · {range_label} · advertiser-weekly-spend.csv")
    c2.metric("Active Advertisers", f"{active_advs:,}",
              help="Unique advertisers with spend in the selected window")
    c3.markdown(f"""
        <div style="background:#EBF3FA;border:1px solid #BFDBFE;border-radius:12px;
                    padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.05)">
          <div style="font-size:11px;font-weight:700;letter-spacing:.06em;
                      text-transform:uppercase;color:#1D4B7C;margin-bottom:6px">
            Democrat Spend
          </div>
          <div style="font-size:26px;font-weight:700;color:#1A56DB;line-height:1.1">
            {money(dem_spend)}
          </div>
          <div style="font-size:11px;color:#3374AA;margin-top:4px">{range_label}</div>
        </div>""", unsafe_allow_html=True)
    c4.markdown(f"""
        <div style="background:#FFF1EE;border:1px solid #FECACA;border-radius:12px;
                    padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.05)">
          <div style="font-size:11px;font-weight:700;letter-spacing:.06em;
                      text-transform:uppercase;color:#9B1C1C;margin-bottom:6px">
            Republican Spend
          </div>
          <div style="font-size:26px;font-weight:700;color:#C81E1E;line-height:1.1">
            {money(rep_spend)}
          </div>
          <div style="font-size:11px;color:#E05A3A;margin-top:4px">{range_label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="height:3px;background:#F5902B;border-radius:2px;margin:16px 0 20px"></div>',
        unsafe_allow_html=True,
    )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_daily, tab_leaders, tab_trends, tab_states, tab_platform, tab_insights = st.tabs(
        ["Daily Spend", "Top Spenders", "Spend Trends", "By State", "Platform Comparison", "Advertiser Insights"]
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Tab 1: Daily spend chart
    # ──────────────────────────────────────────────────────────────────────────
    with tab_daily:
        st.markdown(
            '<p style="font-size:12px;color:#6B6560;margin-bottom:12px">'
            'Prorated max/min reported spend per day · source: <code>creative-stats.csv</code>'
            ' (spend ranges, not exact)</p>',
            unsafe_allow_html=True,
        )
        disp_dates = [datetime.date.fromisoformat(d).strftime("%b %-d") for d in dates]

        fig = go.Figure([
            go.Bar(
                name="Max Spend", x=disp_dates, y=max_vals,
                marker_color="#3374AA", marker_line_width=0,
            ),
            go.Bar(
                name="Min Spend", x=disp_dates, y=min_vals,
                marker_color="rgba(51,116,170,0.22)", marker_line_width=0,
            ),
        ])
        fig.update_layout(
            **PLOTLY_LIGHT, barmode="overlay", height=380,
            xaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=10), automargin=True),
            yaxis=dict(
                gridcolor="#E2DDD7", tickprefix="$", tickformat=",.0f",
                title=dict(text="Est. Daily Spend (USD)", font=dict(size=10, color="#6B6560")),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Tab 2: Top spenders leaderboard + party override editor
    # ──────────────────────────────────────────────────────────────────────────
    with tab_leaders:
        overrides = st.session_state.overrides

        # Filter by party + time range
        filtered = [
            (name, spend) for name, spend in adv_spend_filtered.items()
            if infer_party(name, name_to_scope.get(name, ""), overrides, wikidata_parties)[0] in party_filter
        ]
        top100   = sorted(filtered, key=lambda x: -x[1])[:100]
        top1    = top100[0][1] if top100 else 1

        st.markdown(
            f'<p style="font-size:12px;color:#6B6560;margin-bottom:16px">'
            f'Exact spend · <strong>{range_label}</strong> · source: <code>advertiser-weekly-spend.csv</code> · '
            f'party badges show orange outline when manually overridden</p>',
            unsafe_allow_html=True,
        )

        # ── Column header row ─────────────────────────────────────────────────
        hc = st.columns([1, 6, 2, 2, 2])
        hc[0].markdown('<div style="font-size:11px;font-weight:700;color:#6B6560;padding:4px 0">#</div>', unsafe_allow_html=True)
        hc[1].markdown('<div style="font-size:11px;font-weight:700;color:#6B6560;padding:4px 0">Advertiser</div>', unsafe_allow_html=True)
        hc[2].markdown('<div style="font-size:11px;font-weight:700;color:#6B6560;padding:4px 0">Party</div>', unsafe_allow_html=True)
        hc[3].markdown('<div style="font-size:11px;font-weight:700;color:#6B6560;padding:4px 0;text-align:right">WoW Trend</div>', unsafe_allow_html=True)
        hc[4].markdown('<div style="font-size:11px;font-weight:700;color:#6B6560;padding:4px 0;text-align:right">2026 Spend</div>', unsafe_allow_html=True)
        st.markdown('<hr style="margin:2px 0 6px;border:none;border-top:1px solid #E2DDD7">', unsafe_allow_html=True)

        # ── Leaderboard rows ──────────────────────────────────────────────────
        for i, (name, spend) in enumerate(top100):
            party, auto_src = infer_party(name, name_to_scope.get(name, ""), overrides, wikidata_parties)
            is_override     = name in overrides
            pct             = spend / top1 * 100
            party_key       = {"D": "D", "R": "R", "N": "N"}.get(party, "unk")
            if is_override:
                party_key += " lb-ovr"

            # Hidden CSS marker for :has() coloring; row separator
            st.markdown(
                f'<div class="lb-{party_key} lb-row" style="display:none"></div>',
                unsafe_allow_html=True,
            )

            rc = st.columns([1, 6, 2, 2, 2])
            _last, _prev, _delta, _pct = compute_trend(name, weekly_raw)

            # Rank
            rank_style = (
                "display:inline-flex;align-items:center;justify-content:center;"
                "width:24px;height:24px;border-radius:50%;font-size:11px;font-weight:700;"
                + ("background:#F5902B;color:#fff;" if i == 0 else "background:#E2DDD7;color:#6B6560;")
            )
            rc[0].markdown(f'<span style="{rank_style}">{i+1}</span>', unsafe_allow_html=True)

            # Advertiser name + spend bar
            rc[1].markdown(
                f'<div style="font-weight:600;font-size:13px;line-height:1.3">{_html.escape(name)}</div>'
                f'<div style="height:4px;background:#E2DDD7;border-radius:2px;margin-top:4px">'
                f'<div style="height:4px;width:{pct:.0f}%;background:#3374AA;border-radius:2px"></div></div>',
                unsafe_allow_html=True,
            )

            # Party pill as popover
            with rc[2]:
                pill_label = PARTY_SHORT.get(party, "?")
                with st.popover(pill_label, use_container_width=False):
                    inferred_label = PARTY_LABEL.get(
                        infer_party(name, name_to_scope.get(name, ""), None, wikidata_parties)[0], "?"
                    )
                    scope_note = name_to_scope.get(name, "")
                    _esc_name = _html.escape(name)
                    override_badge = ' <span style="color:#F5902B;font-size:10px;font-weight:700">OVERRIDDEN</span>' if name in overrides else ""
                    st.markdown(
                        f'<div style="font-weight:600;font-size:13px;margin-bottom:4px">{_esc_name}{override_badge}</div>'
                        f'<div style="font-size:11px;color:#6B6560;margin-bottom:2px">Inferred: {inferred_label} &nbsp;·&nbsp; {auto_src}</div>'
                        + (f'<div style="font-size:11px;color:#6B6560;margin-bottom:8px">Declared scope: {_html.escape(scope_note[:80])}{"…" if len(scope_note) > 80 else ""}</div>' if scope_note else '<div style="margin-bottom:8px"></div>'),
                        unsafe_allow_html=True,
                    )
                    inferred_party = infer_party(name, name_to_scope.get(name, ""), None, wikidata_parties)[0]
                    current_val    = overrides.get(name, inferred_party)
                    opts = ["D", "R", "N", "?"]
                    idx  = opts.index(current_val) if current_val in opts else 0
                    sel  = st.selectbox(
                        "Set party",
                        opts, index=idx,
                        key=f"ovr__{name}",
                        format_func=lambda x: PARTY_LABEL.get(x, x),
                    )
                    if sel != overrides.get(name):
                        new_overrides = dict(overrides)
                        new_overrides[name] = sel
                        save_overrides(new_overrides)
                        st.session_state.overrides = new_overrides
                        st.rerun()
                    if name in overrides:
                        if st.button("Reset to inferred", key=f"rst__{name}"):
                            new_overrides = dict(overrides)
                            new_overrides.pop(name)
                            save_overrides(new_overrides)
                            st.session_state.overrides = new_overrides
                            st.rerun()

            # WoW Trend
            if _prev == 0:
                trend_html = '<div style="text-align:right;font-size:11px;color:#9CA3AF;padding-top:2px">—</div>'
            elif abs(_pct) < 5:
                trend_html = '<div style="text-align:right;font-size:11px;color:#6B6560;padding-top:2px">→ flat</div>'
            elif _delta > 0:
                trend_html = (
                    f'<div style="text-align:right;padding-top:2px">'
                    f'<span style="font-size:12px;font-weight:700;color:#16a34a">▲ {money(abs(_delta))}</span>'
                    f'<br><span style="font-size:10px;color:#4ade80">+{_pct:.0f}% WoW</span></div>'
                )
            else:
                trend_html = (
                    f'<div style="text-align:right;padding-top:2px">'
                    f'<span style="font-size:12px;font-weight:700;color:#dc2626">▼ {money(abs(_delta))}</span>'
                    f'<br><span style="font-size:10px;color:#f87171">{_pct:.0f}% WoW</span></div>'
                )
            rc[3].markdown(trend_html, unsafe_allow_html=True)

            # Spend
            rc[4].markdown(
                f'<div style="font-weight:700;font-size:13px;font-feature-settings:\'tnum\';text-align:right;padding-top:2px">{money(spend)}</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<hr style="margin:4px 0;border:none;border-top:1px solid #F0EDEA">', unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Tab 3: Spend Trends
    # ──────────────────────────────────────────────────────────────────────────
    with tab_trends:
        overrides_tr = st.session_state.overrides

        # ── Market-wide weekly totals ──────────────────────────────────────────
        market_weekly: dict[str, float] = {}
        for _name, _weeks in weekly_raw.items():
            for _wk, _sp in _weeks.items():
                market_weekly[_wk] = market_weekly.get(_wk, 0.0) + _sp
        mw_weeks = sorted(market_weekly.keys())
        mw_vals  = [round(market_weekly[w]) for w in mw_weeks]
        mw_labels = [datetime.date.fromisoformat(w).strftime("%b %-d") for w in mw_weeks]

        st.markdown(
            '<h3 style="font-size:15px;font-weight:700;margin:0 0 4px">Market Weekly Spend</h3>'
            '<p style="font-size:12px;color:#6B6560;margin:0 0 12px">All political advertisers · exact weekly totals · 2026 YTD</p>',
            unsafe_allow_html=True,
        )
        fig_mw = go.Figure([
            go.Bar(
                x=mw_labels, y=mw_vals,
                marker_color="#3374AA", marker_line_width=0,
                text=[money(v) for v in mw_vals],
                textposition="outside",
                textfont=dict(size=10, color="#6B6560"),
            )
        ])
        fig_mw.update_layout(
            **PLOTLY_LIGHT, height=280,
            xaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=10)),
            yaxis=dict(gridcolor="#E2DDD7", tickprefix="$", tickformat=",.0f",
                       tickfont=dict(size=10)),
        )
        st.plotly_chart(fig_mw, use_container_width=True)

        # ── Compute WoW for all advertisers ───────────────────────────────────
        all_trends = []
        for _name, _sp in adv_spend.items():
            _last, _prev, _delta, _pct = compute_trend(_name, weekly_raw)
            if _prev == 0 or abs(_delta) < 1000:   # skip no-data or negligible moves
                continue
            _party = infer_party(_name, name_to_scope.get(_name, ""), overrides_tr, wikidata_parties)[0]
            if _party not in party_filter:
                continue
            all_trends.append((_name, _last, _prev, _delta, _pct, _party))

        risers  = sorted(all_trends, key=lambda x: -x[3])[:10]
        fallers = sorted(all_trends, key=lambda x:  x[3])[:10]

        # Latest two week labels for column headers
        if len(mw_weeks) >= 2:
            wk_last_lbl = datetime.date.fromisoformat(mw_weeks[-1]).strftime("Wk of %b %-d")
            wk_prev_lbl = datetime.date.fromisoformat(mw_weeks[-2]).strftime("Wk of %b %-d")
        else:
            wk_last_lbl, wk_prev_lbl = "This Week", "Prior Week"

        def _trend_table(rows: list, title: str, arrow: str, color: str) -> None:
            st.markdown(
                f'<h3 style="font-size:15px;font-weight:700;margin:24px 0 4px">'
                f'{arrow} {title}</h3>'
                f'<p style="font-size:12px;color:#6B6560;margin:0 0 10px">'
                f'Comparing <strong>{wk_last_lbl}</strong> vs <strong>{wk_prev_lbl}</strong></p>',
                unsafe_allow_html=True,
            )
            th = st.columns([5, 2, 2, 2])
            for _col, _txt in zip(th, ["Advertiser", wk_prev_lbl, wk_last_lbl, "Change"]):
                _col.markdown(
                    f'<div style="font-size:11px;font-weight:700;color:#6B6560;padding:2px 0">{_txt}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown('<hr style="margin:2px 0 6px;border:none;border-top:1px solid #E2DDD7">', unsafe_allow_html=True)

            PARTY_DOT = {"D": "#1A56DB", "R": "#C81E1E", "N": "#6D28D9", "?": "#9CA3AF"}
            for _name, _last, _prev, _delta, _pct, _party in rows:
                tc = st.columns([5, 2, 2, 2])
                _dot = PARTY_DOT.get(_party, "#9CA3AF")
                tc[0].markdown(
                    f'<div style="font-size:13px;font-weight:600;padding:3px 0">'
                    f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                    f'background:{_dot};margin-right:6px;vertical-align:middle"></span>'
                    f'{_html.escape(_name)}</div>',
                    unsafe_allow_html=True,
                )
                tc[1].markdown(
                    f'<div style="font-size:13px;color:#6B6560;text-align:right;padding:3px 0">{money(_prev)}</div>',
                    unsafe_allow_html=True,
                )
                tc[2].markdown(
                    f'<div style="font-size:13px;font-weight:600;text-align:right;padding:3px 0">{money(_last)}</div>',
                    unsafe_allow_html=True,
                )
                sign = "+" if _delta > 0 else "-"
                tc[3].markdown(
                    f'<div style="font-size:13px;font-weight:700;color:{color};text-align:right;padding:3px 0">'
                    f'{sign}{money(abs(_delta))}<br>'
                    f'<span style="font-size:10px;font-weight:400">{sign}{abs(_pct):.0f}%</span></div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<hr style="margin:2px 0;border:none;border-top:1px solid #F0EDEA">', unsafe_allow_html=True)

        col_r, col_f = st.columns(2)
        with col_r:
            _trend_table(risers,  "Rising This Week",  "▲", "#16a34a")
        with col_f:
            _trend_table(fallers, "Falling This Week", "▼", "#dc2626")

    # ──────────────────────────────────────────────────────────────────────────
    # Tab 4: State breakdown
    # ──────────────────────────────────────────────────────────────────────────
    with tab_states:
        st.markdown(
            '<p style="font-size:12px;color:#6B6560;margin-bottom:16px">'
            'Exact lifetime spend for 2026-active advertisers · '
            'source: <code>advertiser-geo-spend.csv</code> · '
            'note: geo-spend is all-time, not 2026-filtered</p>',
            unsafe_allow_html=True,
        )

        top_states   = sorted(state_spend.items(), key=lambda x: -x[1])[:50]
        state_labels = [STATE_NAMES_BY_ABBR.get(abbr, abbr) for abbr, _ in top_states]
        state_vals   = [round(v) for _, v in top_states]

        fig_s = go.Figure([
            go.Bar(
                name="Spend", y=state_labels, x=state_vals, orientation="h",
                marker_color="#3374AA", marker_line_width=0,
                text=[money(v) for v in state_vals], textposition="outside",
                textfont=dict(size=11, color="#6B6560"),
            ),
        ])
        fig_s.update_layout(
            **PLOTLY_LIGHT,
            height=max(380, len(top_states) * 28),
            showlegend=False,
            xaxis=dict(
                gridcolor="#E2DDD7", tickprefix="$", tickformat=",.0f",
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                gridcolor="#E2DDD7", tickfont=dict(size=12), autorange="reversed",
            ),
        )
        st.plotly_chart(fig_s, use_container_width=True)

        # ── Top Advertisers by State ───────────────────────────────────────────
        st.markdown(
            '<h3 style="font-size:16px;font-weight:700;margin:28px 0 12px">Top Advertisers by State</h3>',
            unsafe_allow_html=True,
        )

        # Build sorted state list for the selector (full name → abbr map)
        sorted_state_abbrs = [abbr for abbr, _ in top_states]
        sorted_state_names = [STATE_NAMES_BY_ABBR.get(a, a) for a in sorted_state_abbrs]
        state_name_to_abbr = {name: abbr for abbr, name in zip(sorted_state_abbrs, sorted_state_names)}

        sel_state_name = st.selectbox(
            "Select state",
            options=sorted_state_names,
            index=0,
            key="state_drilldown",
        )
        sel_abbr = state_name_to_abbr.get(sel_state_name, sorted_state_abbrs[0])
        adv_in_state = state_adv_spend.get(sel_abbr, {})

        if adv_in_state:
            overrides_st = st.session_state.overrides
            ranked = sorted(adv_in_state.items(), key=lambda x: -x[1])[:50]
            state_top1 = ranked[0][1] if ranked else 1

            # Header row
            h0, h1, h2, h3 = st.columns([1, 7, 2, 2])
            h0.markdown('<p style="font-size:11px;font-weight:700;color:#6B6560;margin:0">#</p>', unsafe_allow_html=True)
            h1.markdown('<p style="font-size:11px;font-weight:700;color:#6B6560;margin:0">ADVERTISER</p>', unsafe_allow_html=True)
            h2.markdown('<p style="font-size:11px;font-weight:700;color:#6B6560;margin:0">PARTY</p>', unsafe_allow_html=True)
            h3.markdown('<p style="font-size:11px;font-weight:700;color:#6B6560;margin:0;text-align:right">SPEND</p>', unsafe_allow_html=True)
            st.markdown('<div style="height:1px;background:#E2DDD7;margin:4px 0 6px"></div>', unsafe_allow_html=True)

            PARTY_COLORS_ST = {"D": "#2563EB", "R": "#DC2626", "N": "#7C3AED", "?": "#9CA3AF"}
            PARTY_BG_ST     = {"D": "#EBF3FA", "R": "#FFF1EE", "N": "#F5F0FF", "?": "#F0EDEA"}
            PARTY_LABEL_ST  = {"D": "DEM", "R": "REP", "N": "NPN", "?": "UNK"}

            for rank, (name, spend) in enumerate(ranked, 1):
                party, _src = infer_party(name, name_to_scope.get(name, ""), overrides_st, wikidata_parties)
                pct  = spend / state_top1 * 100
                p_color = PARTY_COLORS_ST.get(party, "#9CA3AF")
                p_bg    = PARTY_BG_ST.get(party, "#F0EDEA")
                p_label = PARTY_LABEL_ST.get(party, "UNK")

                c0, c1, c2, c3 = st.columns([1, 7, 2, 2])
                c0.markdown(f'<p style="font-size:13px;color:#6B6560;margin:6px 0">{rank}</p>', unsafe_allow_html=True)
                c1.markdown(
                    f'<div style="padding:6px 0">'
                    f'<div style="font-size:13px;font-weight:600;color:#1A1714">{_html.escape(name)}</div>'
                    f'<div style="margin-top:3px;height:4px;width:{pct:.1f}%;background:{p_color};'
                    f'border-radius:2px;opacity:0.5"></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                c2.markdown(
                    f'<span style="display:inline-block;margin-top:6px;padding:2px 10px;'
                    f'border-radius:5px;background:{p_bg};color:{p_color};'
                    f'font-size:10px;font-weight:700;letter-spacing:.05em">{p_label}</span>',
                    unsafe_allow_html=True,
                )
                c3.markdown(
                    f'<p style="font-size:13px;font-weight:600;color:#1A1714;'
                    f'text-align:right;margin:6px 0">{money(spend)}</p>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="height:1px;background:#F0EDEA;margin:0"></div>', unsafe_allow_html=True)
        else:
            st.info(f"No advertiser-level data available for {sel_state_name}.")

    # ──────────────────────────────────────────────────────────────────────────
    # Tab 5: Platform Comparison (YouTube vs CTV — mock data)
    # ──────────────────────────────────────────────────────────────────────────
    with tab_platform:
        # ── Select data source: real upload or mock ───────────────────────────
        _ctv_source = st.session_state.get("ctv_data", {})
        _using_real_ctv = bool(_ctv_source)
        ctv_weekly = _ctv_source if _using_real_ctv else mock_ctv

        if _using_real_ctv:
            st.markdown(
                '<div style="background:#F0FDF4;border:1.5px solid #86EFAC;border-radius:10px;'
                'padding:12px 18px;margin-bottom:20px;display:flex;align-items:center;gap:10px">'
                '<span style="font-size:18px">✓</span>'
                '<div><span style="font-weight:700;color:#15803D">Real CTV Data Active</span>'
                '<span style="color:#15803D;font-size:13px;margin-left:8px">'
                f'Uploaded · {len(_ctv_source):,} advertisers · '
                'Upload a new file in the sidebar to refresh.</span></div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#FEF3E8;border:1.5px solid #F5902B;border-radius:10px;'
                'padding:12px 18px;margin-bottom:20px;display:flex;align-items:center;gap:10px">'
                '<span style="font-size:18px">⚠️</span>'
                '<div><span style="font-weight:700;color:#9A4A00">Mock CTV Data</span>'
                '<span style="color:#9A4A00;font-size:13px;margin-left:8px">'
                'CTV figures are algorithmically generated placeholders. '
                'Upload a real AdImpact export via the sidebar to activate real data.</span>'
                '</div></div>',
                unsafe_allow_html=True,
            )

        _ctv_label = "" if _using_real_ctv else " (mock)"

        # ── Compute CTV totals for the selected time window ───────────────────
        overrides_plt = st.session_state.overrides
        ctv_filtered: dict[str, float] = {}
        for adv, weeks in ctv_weekly.items():
            total = sum(v for w, v in weeks.items() if date_from_str <= w <= date_to_str)
            if total > 0:
                ctv_filtered[adv] = total

        total_yt      = sum(adv_spend_filtered.values())
        total_ctv     = sum(ctv_filtered.values())
        total_market  = total_yt + total_ctv
        yt_share_pct  = total_yt  / total_market * 100 if total_market else 0
        ctv_share_pct = total_ctv / total_market * 100 if total_market else 0

        # Party totals per platform
        yt_party: dict[str, float]  = {"D": 0.0, "R": 0.0, "N": 0.0, "?": 0.0}
        ctv_party: dict[str, float] = {"D": 0.0, "R": 0.0, "N": 0.0, "?": 0.0}
        for adv, spend in adv_spend_filtered.items():
            p, _ = infer_party(adv, name_to_scope.get(adv, ""), overrides_plt, wikidata_parties)
            yt_party[p] = yt_party.get(p, 0.0) + spend
        for adv, spend in ctv_filtered.items():
            p, _ = infer_party(adv, name_to_scope.get(adv, ""), overrides_plt, wikidata_parties)
            ctv_party[p] = ctv_party.get(p, 0.0) + spend

        # ── KPI strip ─────────────────────────────────────────────────────────
        def _kpi_card(label, value, sub="", accent="#1A1714"):
            return (
                f'<div style="background:#fff;border:1px solid #E2DDD7;border-radius:12px;'
                f'padding:18px 20px;flex:1;min-width:0">'
                f'<div style="font-size:11px;font-weight:700;letter-spacing:.06em;'
                f'text-transform:uppercase;color:#6B6560;margin-bottom:6px">{label}</div>'
                f'<div style="font-size:26px;font-weight:700;color:{accent};line-height:1">{value}</div>'
                f'{"<div style=font-size:11px;color:#9CA3AF;margin-top:4px>" + sub + "</div>" if sub else ""}'
                f'</div>'
            )

        st.markdown(
            f'<div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap">'
            + _kpi_card("Total Market", money(total_market), f"YouTube + CTV · {range_label}")
            + _kpi_card("YouTube", money(total_yt), f"{yt_share_pct:.0f}% of market", "#3374AA")
            + _kpi_card("CTV", money(total_ctv), f"{ctv_share_pct:.0f}% of market · MOCK", "#F5902B")
            + _kpi_card("Dem (both)", money(yt_party["D"] + ctv_party["D"]), "", "#1A56DB")
            + _kpi_card("Rep (both)", money(yt_party["R"] + ctv_party["R"]), "", "#C81E1E")
            + '</div>',
            unsafe_allow_html=True,
        )

        # ── Platform share bars ────────────────────────────────────────────────
        left_col, right_col = st.columns([3, 2])

        with left_col:
            st.markdown(
                '<h3 style="font-size:15px;font-weight:700;margin:0 0 14px">Platform Spend Share</h3>',
                unsafe_allow_html=True,
            )
            fig_share = go.Figure([go.Bar(
                x=[total_yt, total_ctv],
                y=["YouTube", f"CTV{_ctv_label}"],
                orientation="h",
                marker_color=["#3374AA", "#F5902B"],
                marker_line_width=0,
                text=[f"{money(total_yt)}  {yt_share_pct:.0f}%",
                      f"{money(total_ctv)}  {ctv_share_pct:.0f}%" + (" ⚠️" if not _using_real_ctv else "")],
                textposition="outside",
                textfont=dict(size=12, color="#6B6560"),
            )])
            fig_share.update_layout(
                **PLOTLY_LIGHT,
                height=160,
                showlegend=False,
                xaxis=dict(gridcolor="#E2DDD7", tickprefix="$", tickformat=",.0f",
                           tickfont=dict(size=10)),
                yaxis=dict(tickfont=dict(size=13, color="#1A1714")),
            )
            st.plotly_chart(fig_share, use_container_width=True)

        with right_col:
            st.markdown(
                '<h3 style="font-size:15px;font-weight:700;margin:0 0 14px">Partisan Split by Platform</h3>',
                unsafe_allow_html=True,
            )
            fig_partisan = go.Figure([
                go.Bar(name="Democrat",   x=["YouTube", f"CTV{_ctv_label}"],
                       y=[yt_party["D"], ctv_party["D"]],
                       marker_color="#2563EB", marker_line_width=0),
                go.Bar(name="Republican", x=["YouTube", f"CTV{_ctv_label}"],
                       y=[yt_party["R"], ctv_party["R"]],
                       marker_color="#DC2626", marker_line_width=0),
                go.Bar(name="Neutral",    x=["YouTube", f"CTV{_ctv_label}"],
                       y=[yt_party["N"], ctv_party["N"]],
                       marker_color="#7C3AED", marker_line_width=0),
            ])
            fig_partisan.update_layout(
                **PLOTLY_LIGHT,
                barmode="stack",
                height=260,
                xaxis=dict(tickfont=dict(size=12, color="#1A1714")),
                yaxis=dict(gridcolor="#E2DDD7", tickprefix="$",
                           tickformat=",.0f", tickfont=dict(size=10)),
            )
            st.plotly_chart(fig_partisan, use_container_width=True)

        # ── Weekly trend: YouTube vs CTV ──────────────────────────────────────
        st.markdown(
            '<h3 style="font-size:15px;font-weight:700;margin:16px 0 4px">Weekly Spend Trend</h3>'
            f'<p style="font-size:12px;color:#6B6560;margin:0 0 12px">YouTube (real) vs CTV{"" if _using_real_ctv else " (mock)"} · '
            + range_label + '</p>',
            unsafe_allow_html=True,
        )

        yt_weekly_totals:  dict[str, float] = {}
        ctv_weekly_totals: dict[str, float] = {}
        for adv, weeks in weekly_raw.items():
            if adv not in adv_spend_filtered:
                continue
            for w, v in weeks.items():
                if date_from_str <= w <= date_to_str:
                    yt_weekly_totals[w]  = yt_weekly_totals.get(w, 0.0) + v
        for adv, weeks in ctv_weekly.items():
            if adv not in adv_spend_filtered:
                continue
            for w, v in weeks.items():
                if date_from_str <= w <= date_to_str:
                    ctv_weekly_totals[w] = ctv_weekly_totals.get(w, 0.0) + v

        all_weeks_plt = sorted(set(list(yt_weekly_totals.keys()) + list(ctv_weekly_totals.keys())))
        if all_weeks_plt:
            wk_disp  = [datetime.date.fromisoformat(w).strftime("%b %-d") for w in all_weeks_plt]
            yt_vals  = [round(yt_weekly_totals.get(w, 0))  for w in all_weeks_plt]
            ctv_vals = [round(ctv_weekly_totals.get(w, 0)) for w in all_weeks_plt]

            fig_trend = go.Figure([
                go.Scatter(x=wk_disp, y=yt_vals,  mode="lines+markers",
                           name="YouTube", line=dict(color="#3374AA", width=2.5),
                           marker=dict(size=4)),
                go.Scatter(x=wk_disp, y=ctv_vals, mode="lines+markers",
                           name=f"CTV{_ctv_label}", line=dict(color="#F5902B", width=2.5, dash="dot"),
                           marker=dict(size=4)),
            ])
            fig_trend.update_layout(
                **PLOTLY_LIGHT,
                height=300,
                xaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#E2DDD7", tickprefix="$",
                           tickformat=",.0f", tickfont=dict(size=10)),
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        # ── Top cross-platform spenders ───────────────────────────────────────
        st.markdown(
            '<h3 style="font-size:15px;font-weight:700;margin:16px 0 12px">Top Cross-Platform Spenders</h3>',
            unsafe_allow_html=True,
        )

        cross_rows = []
        all_advs_set = set(adv_spend_filtered.keys()) | set(ctv_filtered.keys())
        for adv in all_advs_set:
            yt_v  = adv_spend_filtered.get(adv, 0.0)
            ctv_v = ctv_filtered.get(adv, 0.0)
            cross_rows.append((adv, yt_v, ctv_v, yt_v + ctv_v))
        cross_rows.sort(key=lambda x: -x[3])

        # Header
        ch0, ch1, ch2, ch3, ch4, ch5 = st.columns([1, 6, 2, 2, 2, 2])
        for col, lbl in zip([ch0,ch1,ch2,ch3,ch4,ch5],
                            ["#","ADVERTISER","PARTY","YOUTUBE","CTV ⚠️","TOTAL"]):
            col.markdown(
                f'<p style="font-size:11px;font-weight:700;color:#6B6560;margin:0">{lbl}</p>',
                unsafe_allow_html=True,
            )
        st.markdown('<div style="height:1px;background:#E2DDD7;margin:4px 0 6px"></div>',
                    unsafe_allow_html=True)

        PARTY_COLORS_P = {"D":"#1A56DB","R":"#C81E1E","N":"#6D28D9","?":"#6B6560"}
        PARTY_BG_P     = {"D":"#EBF3FA","R":"#FFF1EE","N":"#F5F0FF","?":"#F0EDEA"}
        PARTY_LBL_P    = {"D":"DEM","R":"REP","N":"NPN","?":"UNK"}

        for rank, (adv, yt_v, ctv_v, total_v) in enumerate(cross_rows[:50], 1):
            p, _ = infer_party(adv, name_to_scope.get(adv,""), overrides_plt, wikidata_parties)
            c0,c1,c2,c3,c4,c5 = st.columns([1,6,2,2,2,2])
            c0.markdown(f'<p style="font-size:12px;color:#9CA3AF;margin:5px 0">{rank}</p>',
                        unsafe_allow_html=True)
            c1.markdown(
                f'<p style="font-size:13px;font-weight:600;color:#1A1714;margin:5px 0">{adv}</p>',
                unsafe_allow_html=True,
            )
            c2.markdown(
                f'<span style="display:inline-block;margin-top:5px;padding:2px 9px;'
                f'border-radius:5px;background:{PARTY_BG_P.get(p,"#F0EDEA")};'
                f'color:{PARTY_COLORS_P.get(p,"#6B6560")};'
                f'font-size:10px;font-weight:700;letter-spacing:.05em">'
                f'{PARTY_LBL_P.get(p,"UNK")}</span>',
                unsafe_allow_html=True,
            )
            for col, val in [(c3, yt_v), (c4, ctv_v), (c5, total_v)]:
                col.markdown(
                    f'<p style="font-size:13px;font-weight:{"700" if col is c5 else "400"};'
                    f'color:{"#1A1714" if col is c5 else "#6B6560"};text-align:right;margin:5px 0">'
                    f'{money(val) if val > 0 else "—"}</p>',
                    unsafe_allow_html=True,
                )
            st.markdown('<div style="height:1px;background:#F0EDEA;margin:0"></div>',
                        unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Tab 6: Advertiser Insights
    # ──────────────────────────────────────────────────────────────────────────
    with tab_insights:
        overrides_ins = st.session_state.overrides

        # ── Advertiser selector ───────────────────────────────────────────────
        all_advs_sorted = sorted(adv_spend.keys(), key=lambda x: -adv_spend[x])
        sel_adv = st.selectbox(
            "Search or select advertiser",
            options=[""] + all_advs_sorted,
            index=0,
            key="insights_adv",
            placeholder="Type to search…",
        )

        if not sel_adv:
            st.markdown(
                '<div style="text-align:center;padding:48px 0;color:#9CA3AF;font-size:14px">'
                'Select an advertiser above to view detailed insights.</div>',
                unsafe_allow_html=True,
            )
        else:
            # Use filtered spend to match the sidebar time range
            adv_total   = adv_spend_filtered.get(sel_adv, 0.0)
            adv_rank    = sorted(adv_spend_filtered.keys(), key=lambda x: -adv_spend_filtered[x]).index(sel_adv) + 1 \
                          if sel_adv in adv_spend_filtered else len(adv_spend_filtered)
            adv_weeks   = len(weekly_raw.get(sel_adv, {}))
            party_ins, party_src_ins = infer_party(sel_adv, name_to_scope.get(sel_adv, ""), overrides_ins, wikidata_parties)
            i_last, i_prev, i_delta, i_pct = compute_trend(sel_adv, weekly_raw)

            PARTY_COLORS_INS = {"D": "#1A56DB", "R": "#C81E1E", "N": "#6D28D9", "?": "#6B6560"}
            PARTY_BG_INS     = {"D": "#EBF3FA", "R": "#FFF1EE", "N": "#F5F3FF", "?": "#F3F4F6"}
            p_color = PARTY_COLORS_INS.get(party_ins, "#6B6560")
            p_bg    = PARTY_BG_INS.get(party_ins, "#F3F4F6")

            # ── Header ────────────────────────────────────────────────────────
            scope_note = name_to_scope.get(sel_adv, "")
            st.markdown(
                f'<div style="margin:12px 0 20px">'
                f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
                f'<h2 style="font-size:22px;font-weight:700;margin:0">{_html.escape(sel_adv)}</h2>'
                f'<span style="padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;'
                f'letter-spacing:.06em;background:{p_bg};color:{p_color}">'
                f'{PARTY_LABEL.get(party_ins,"?").upper()}</span>'
                f'<span style="font-size:11px;color:#9CA3AF">via {party_src_ins}</span>'
                f'</div>'
                + (f'<div style="font-size:12px;color:#6B6560;margin-top:4px">{_html.escape(scope_note)}</div>' if scope_note else "")
                + f'</div>',
                unsafe_allow_html=True,
            )

            # ── KPI strip ─────────────────────────────────────────────────────
            k1, k2, k3, k4 = st.columns(4)
            k1.metric(range_label, money(adv_total),
                      help=f"Exact spend · {range_label} · advertiser-weekly-spend.csv")
            k2.metric("Rank", f"#{adv_rank:,}",
                      help=f"Ranked #{adv_rank} of {len(adv_spend_filtered):,} advertisers in this period")
            k3.metric("Weeks Active", f"{adv_weeks}",
                      help="Number of weeks with at least $1 in reported spend since Jan 2026")
            if i_prev > 0:
                wow_label = f"{'▲' if i_delta >= 0 else '▼'} {money(abs(i_delta))} ({'+' if i_delta>=0 else ''}{i_pct:.0f}%)"
                k4.metric("WoW Change", wow_label,
                          help=f"Most recent week {money(i_last)} vs prior week {money(i_prev)}")
            else:
                k4.metric("WoW Change", "—", help="Insufficient weekly data")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Weekly spend chart ────────────────────────────────────────────
            adv_weeks_data = weekly_raw.get(sel_adv, {})
            # Filter weeks to match sidebar time range (week start must fall in window)
            adv_weeks_data = {
                w: v for w, v in adv_weeks_data.items()
                if date_from_str <= w <= date_to_str
            }
            if adv_weeks_data:
                wk_sorted = sorted(adv_weeks_data.keys())
                wk_labels = [datetime.date.fromisoformat(w).strftime("%b %-d") for w in wk_sorted]
                wk_vals   = [round(adv_weeks_data[w]) for w in wk_sorted]
                avg_spend = sum(wk_vals) / len(wk_vals)

                st.markdown(
                    f'<h3 style="font-size:15px;font-weight:700;margin:0 0 4px">Weekly Spend History</h3>'
                    f'<p style="font-size:12px;color:#6B6560;margin:0 0 12px">Exact weekly USD · {range_label}</p>',
                    unsafe_allow_html=True,
                )
                fig_adv = go.Figure()
                fig_adv.add_trace(go.Bar(
                    x=wk_labels, y=wk_vals,
                    marker_color=[p_color] * len(wk_vals),
                    marker_opacity=0.85,
                    marker_line_width=0,
                    name="Weekly Spend",
                ))
                fig_adv.add_trace(go.Scatter(
                    x=wk_labels, y=[avg_spend] * len(wk_labels),
                    mode="lines",
                    line=dict(color="#F5902B", width=1.5, dash="dot"),
                    name="Avg/week",
                ))
                fig_adv.update_layout(
                    **{**PLOTLY_LIGHT,
                       "legend": dict(orientation="h", yanchor="bottom", y=1.02,
                                      xanchor="right", x=1, font=dict(size=10),
                                      bgcolor="rgba(0,0,0,0)")},
                    height=260, showlegend=True,
                    xaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=10)),
                    yaxis=dict(gridcolor="#E2DDD7", tickprefix="$", tickformat=",.0f",
                               tickfont=dict(size=10)),
                )
                st.plotly_chart(fig_adv, use_container_width=True)

            # ── Platform breakdown (YouTube vs CTV) ───────────────────────────
            _ins_ctv_src   = st.session_state.get("ctv_data", {}) or mock_ctv
            _ins_using_real = bool(st.session_state.get("ctv_data", {}))
            adv_ctv_weeks = _ins_ctv_src.get(sel_adv, {})
            adv_ctv_total = sum(v for w, v in adv_ctv_weeks.items()
                                if date_from_str <= w <= date_to_str)
            cross_total   = adv_total + adv_ctv_total

            st.markdown("<br>", unsafe_allow_html=True)
            _ctv_note = "real upload" if _ins_using_real else "⚠️ mock placeholder"
            st.markdown(
                '<h3 style="font-size:15px;font-weight:700;margin:0 0 4px">Platform Breakdown</h3>'
                f'<p style="font-size:12px;color:#6B6560;margin:0 0 12px">'
                f'YouTube (real) vs CTV ({_ctv_note}) · {range_label}</p>',
                unsafe_allow_html=True,
            )

            if cross_total > 0:
                yt_pct  = adv_total   / cross_total * 100
                ctv_pct = adv_ctv_total / cross_total * 100
                pb_left, pb_right = st.columns([3, 2])

                with pb_left:
                    fig_pb = go.Figure([go.Bar(
                        x=[adv_total, adv_ctv_total],
                        y=["YouTube", f"CTV{'' if _ins_using_real else ' (mock)'}"],
                        orientation="h",
                        marker_color=[p_color, "#F5902B"],
                        marker_line_width=0,
                        text=[f"{money(adv_total)}  {yt_pct:.0f}%",
                              f"{money(adv_ctv_total)}  {ctv_pct:.0f}%"
                              + ("" if _ins_using_real else "  ⚠️")],
                        textposition="outside",
                        textfont=dict(size=11, color="#6B6560"),
                    )])
                    fig_pb.update_layout(
                        **PLOTLY_LIGHT,
                        height=150,
                        showlegend=False,
                        xaxis=dict(gridcolor="#E2DDD7", tickprefix="$",
                                   tickformat=",.0f", tickfont=dict(size=10)),
                        yaxis=dict(tickfont=dict(size=12, color="#1A1714")),
                    )
                    st.plotly_chart(fig_pb, use_container_width=True)

                with pb_right:
                    st.markdown(
                        f'<div style="background:#F6F5F2;border:1px solid #E2DDD7;'
                        f'border-radius:12px;padding:18px;text-align:center;margin-top:8px">'
                        f'<div style="font-size:11px;font-weight:700;letter-spacing:.06em;'
                        f'text-transform:uppercase;color:#6B6560;margin-bottom:6px">'
                        f'Cross-Platform Total</div>'
                        f'<div style="font-size:30px;font-weight:700;color:{p_color};line-height:1">'
                        f'{money(cross_total)}</div>'
                        f'<div style="font-size:11px;color:#9CA3AF;margin-top:4px">'
                        f'YouTube + CTV</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Side-by-side weekly comparison
                adv_ctv_filtered_weeks = {
                    w: v for w, v in adv_ctv_weeks.items()
                    if date_from_str <= w <= date_to_str
                }
                all_pw = sorted(set(list(adv_weeks_data.keys()) +
                                    list(adv_ctv_filtered_weeks.keys())))
                if all_pw:
                    pw_labels  = [datetime.date.fromisoformat(w).strftime("%b %-d") for w in all_pw]
                    pw_yt_vals = [round(adv_weeks_data.get(w, 0))       for w in all_pw]
                    pw_ctv_vals= [round(adv_ctv_filtered_weeks.get(w,0)) for w in all_pw]

                    fig_pw = go.Figure([
                        go.Bar(name="YouTube", x=pw_labels, y=pw_yt_vals,
                               marker_color=p_color, marker_opacity=0.85,
                               marker_line_width=0),
                        go.Bar(name=f"CTV{'' if _ins_using_real else ' (mock)'}", x=pw_labels, y=pw_ctv_vals,
                               marker_color="#F5902B", marker_opacity=0.75,
                               marker_line_width=0),
                    ])
                    fig_pw.update_layout(
                        **PLOTLY_LIGHT,
                        barmode="group",
                        height=220,
                        xaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=10)),
                        yaxis=dict(gridcolor="#E2DDD7", tickprefix="$",
                                   tickformat=",.0f", tickfont=dict(size=10)),
                    )
                    st.plotly_chart(fig_pw, use_container_width=True)

            # ── Geographic footprint ──────────────────────────────────────────
            adv_state_spend = {
                abbr: vals.get(sel_adv, 0.0)
                for abbr, vals in state_adv_spend.items()
                if sel_adv in vals
            }
            if adv_state_spend:
                top_adv_states = sorted(adv_state_spend.items(), key=lambda x: -x[1])[:15]
                total_geo = sum(adv_state_spend.values())
                top3_pct  = sum(v for _, v in top_adv_states[:3]) / total_geo * 100 if total_geo else 0

                geo_labels = [STATE_NAMES_BY_ABBR.get(a, a) for a, _ in top_adv_states]
                geo_vals   = [round(v) for _, v in top_adv_states]

                st.markdown("<br>", unsafe_allow_html=True)
                g_col, c_col = st.columns([3, 1])

                with g_col:
                    st.markdown(
                        '<h3 style="font-size:15px;font-weight:700;margin:0 0 4px">Geographic Footprint</h3>'
                        '<p style="font-size:12px;color:#6B6560;margin:0 0 12px">'
                        'Top 15 states · all-time spend (geo-spend.csv)</p>',
                        unsafe_allow_html=True,
                    )
                    fig_geo = go.Figure([go.Bar(
                        y=geo_labels, x=geo_vals, orientation="h",
                        marker_color=p_color, marker_opacity=0.75, marker_line_width=0,
                        text=[money(v) for v in geo_vals], textposition="outside",
                        textfont=dict(size=10, color="#6B6560"),
                    )])
                    fig_geo.update_layout(
                        **PLOTLY_LIGHT,
                        height=max(260, len(top_adv_states) * 24),
                        showlegend=False,
                        xaxis=dict(gridcolor="#E2DDD7", tickprefix="$",
                                   tickformat=",.0f", tickfont=dict(size=10)),
                        yaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=11),
                                   autorange="reversed"),
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)

                with c_col:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="background:#F6F5F2;border:1px solid #E2DDD7;border-radius:12px;'
                        f'padding:20px;text-align:center">'
                        f'<div style="font-size:11px;font-weight:700;letter-spacing:.06em;'
                        f'text-transform:uppercase;color:#6B6560;margin-bottom:8px">Geographic Focus</div>'
                        f'<div style="font-size:36px;font-weight:700;color:{p_color};line-height:1">'
                        f'{top3_pct:.0f}%</div>'
                        f'<div style="font-size:11px;color:#9CA3AF;margin-top:6px">'
                        f'of spend in top 3 states</div>'
                        f'<div style="font-size:12px;color:#6B6560;margin-top:12px;font-weight:600">'
                        f'{", ".join(STATE_NAMES_BY_ABBR.get(a,a) for a,_ in top_adv_states[:3])}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

            # ── Targeting & Creative Gallery ──────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<h3 style="font-size:15px;font-weight:700;margin:0 0 4px">'
                'Targeting Intelligence & Creative Gallery</h3>'
                '<p style="font-size:12px;color:#6B6560;margin:0 0 14px">'
                'Requires scanning creative-stats.csv (~2 min first time per advertiser · cached after)</p>',
                unsafe_allow_html=True,
            )

            load_key = f"load_creatives_{sel_adv}"
            if load_key not in st.session_state:
                st.session_state[load_key] = False

            if not st.session_state[load_key]:
                if st.button("Load Targeting & Creative Data", key=f"btn_{load_key}",
                             type="primary"):
                    st.session_state[load_key] = True
                    st.rerun()
            else:
                cdata = load_advertiser_creatives(str(zip_path), sel_adv, TODAY.isoformat())
                ads   = cdata["ads"]
                age_c = cdata["age_counts"]
                gen_c = cdata["gender_counts"]
                n_ads = cdata["total_ads"]

                if not ads:
                    st.info("No creative data found for this advertiser in creative-stats.csv.")
                else:
                    # ── Targeting charts ───────────────────────────────────────
                    t_col, g_col2 = st.columns(2)

                    AGE_ORDER = ["18-24","25-34","35-44","45-54","55-64","65+","Unknown"]
                    age_labels = [a for a in AGE_ORDER if a in age_c]
                    age_vals   = [age_c[a] for a in age_labels]
                    if not age_labels:
                        age_labels = list(age_c.keys())
                        age_vals   = list(age_c.values())

                    with t_col:
                        st.markdown(
                            '<div style="font-size:12px;font-weight:700;color:#6B6560;'
                            'letter-spacing:.05em;text-transform:uppercase;margin-bottom:8px">'
                            'Age Targeting</div>',
                            unsafe_allow_html=True,
                        )
                        if age_labels:
                            fig_age = go.Figure([go.Bar(
                                y=age_labels, x=age_vals, orientation="h",
                                marker_color=p_color, marker_opacity=0.7, marker_line_width=0,
                                text=[f"{v:,} ads" for v in age_vals], textposition="outside",
                                textfont=dict(size=10, color="#6B6560"),
                            )])
                            fig_age.update_layout(
                                **PLOTLY_LIGHT, height=220, showlegend=False,
                                xaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=10),
                                           title=dict(text="# Creatives", font=dict(size=10))),
                                yaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=11),
                                           autorange="reversed"),
                            )
                            st.plotly_chart(fig_age, use_container_width=True)

                    with g_col2:
                        st.markdown(
                            '<div style="font-size:12px;font-weight:700;color:#6B6560;'
                            'letter-spacing:.05em;text-transform:uppercase;margin-bottom:8px">'
                            'Gender Targeting</div>',
                            unsafe_allow_html=True,
                        )
                        if gen_c:
                            gen_labels = list(gen_c.keys())
                            gen_vals   = list(gen_c.values())
                            fig_gen = go.Figure([go.Bar(
                                y=gen_labels, x=gen_vals, orientation="h",
                                marker_color=p_color, marker_opacity=0.7, marker_line_width=0,
                                text=[f"{v:,} ads" for v in gen_vals], textposition="outside",
                                textfont=dict(size=10, color="#6B6560"),
                            )])
                            fig_gen.update_layout(
                                **PLOTLY_LIGHT, height=220, showlegend=False,
                                xaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=10),
                                           title=dict(text="# Creatives", font=dict(size=10))),
                                yaxis=dict(gridcolor="#E2DDD7", tickfont=dict(size=11),
                                           autorange="reversed"),
                            )
                            st.plotly_chart(fig_gen, use_container_width=True)

                    # ── Creative Gallery ───────────────────────────────────────
                    st.markdown(
                        f'<h3 style="font-size:15px;font-weight:700;margin:20px 0 4px">'
                        f'Creative Gallery</h3>'
                        f'<p style="font-size:12px;color:#6B6560;margin:0 0 12px">'
                        f'Showing {len(ads):,} of {n_ads:,} creatives · sorted by most recently served</p>',
                        unsafe_allow_html=True,
                    )

                    # Header
                    gh = st.columns([4, 2, 2, 2, 2])
                    for _c, _t in zip(gh, ["Ad", "Dates", "Impressions", "Spend", "Last Served"]):
                        _c.markdown(
                            f'<div style="font-size:11px;font-weight:700;color:#6B6560;padding:2px 0">{_t}</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown('<hr style="margin:2px 0 6px;border:none;border-top:1px solid #E2DDD7">',
                                unsafe_allow_html=True)

                    for ad in ads:
                        gc = st.columns([4, 2, 2, 2, 2])
                        # Ad link
                        if ad["url"]:
                            gc[0].markdown(
                                f'<div style="font-size:12px;padding:3px 0">'
                                f'<a href="{ad["url"]}" target="_blank" '
                                f'style="color:{p_color};text-decoration:none;font-weight:600">'
                                f'▶ Watch on YouTube</a>'
                                + (f'<span style="font-size:10px;color:#9CA3AF;margin-left:6px">{ad["type"]}</span>' if ad["type"] else "")
                                + f'</div>'
                                + (f'<div style="font-size:10px;color:#6B6560">{ad["age"] or "All ages"} · {ad["gender"] or "All genders"}</div>' if ad["age"] or ad["gender"] else ""),
                                unsafe_allow_html=True,
                            )
                        else:
                            gc[0].markdown(
                                f'<div style="font-size:12px;color:#9CA3AF;padding:3px 0">[No URL]</div>',
                                unsafe_allow_html=True,
                            )
                        gc[1].markdown(
                            f'<div style="font-size:11px;color:#6B6560;padding:3px 0">'
                            f'{ad["start"]} –<br>{ad["end"]}</div>',
                            unsafe_allow_html=True,
                        )
                        gc[2].markdown(
                            f'<div style="font-size:12px;padding:3px 0">{ad["impr"] or "—"}</div>',
                            unsafe_allow_html=True,
                        )
                        gc[3].markdown(
                            f'<div style="font-size:12px;padding:3px 0">{ad["spend"] or "—"}</div>',
                            unsafe_allow_html=True,
                        )
                        gc[4].markdown(
                            f'<div style="font-size:11px;color:#6B6560;padding:3px 0">{ad["last_srv"] or "—"}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<hr style="margin:2px 0;border:none;border-top:1px solid #F0EDEA">',
                                    unsafe_allow_html=True)


if __name__ == "__main__":
    main()

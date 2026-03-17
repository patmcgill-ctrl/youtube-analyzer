"""
YouTube Political Ad Spend — 2026
Streamlit App · Run: streamlit run youtube_spend_app.py
"""

import io, csv, datetime, zipfile, pathlib, json
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import requests
from collections import defaultdict

csv.field_size_limit(10 * 1024 * 1024)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YouTube Political Ad Spend · 2026",
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
    """
    # Tier 0
    if overrides and name in overrides:
        return overrides[name], "Manual override"
    # Tier 1 — candidate name lookup
    n_lower = name.lower()
    for candidate, party in CANDIDATE_PARTY.items():
        if candidate in n_lower:
            return party, "Candidate lookup"
    # Tier 2 — curated orgs + keywords
    p = _text_to_party(name)
    if p != '?':
        src = "Curated lookup" if any(k in n_lower for k in CURATED_PARTY) else "Keyword match"
        return p, src
    # Tier 2.5 — Wikidata politician names
    if wikidata:
        for politician, code in wikidata.items():
            if politician in n_lower:           # politician is already lowercase, 2+ words
                return code, "Wikidata"
    # Tier 2b — declared scope text
    if declared_scope:
        p2 = _text_to_party(declared_scope)
        if p2 != '?':
            return p2, "Declared scope"
    # Tier 4
    return '?', "No match"


# ─── Override persistence ─────────────────────────────────────────────────────
def load_overrides() -> dict:
    try:
        if OVERRIDES_FILE.exists():
            return json.loads(OVERRIDES_FILE.read_text())
    except Exception:
        pass
    return {}


def save_overrides(overrides: dict):
    CACHE_DIR.mkdir(exist_ok=True)
    OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2))


# ─── Download ─────────────────────────────────────────────────────────────────
def download_bundle() -> pathlib.Path:
    CACHE_DIR.mkdir(exist_ok=True)
    if CACHE_FILE.exists():
        age_h = (
            datetime.datetime.now()
            - datetime.datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        ).total_seconds() / 3600
        if age_h < CACHE_MAX_AGE_HOURS:
            return CACHE_FILE
    st.info("Downloading Google Political Ads bundle (~277 MB). This only happens once per day.")
    progress = st.progress(0, text="Starting download…")
    r = requests.get(BUNDLE_URL, stream=True, timeout=300)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    downloaded = 0
    with open(CACHE_FILE, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total
                progress.progress(
                    pct,
                    text=f"Downloading… {pct*100:.0f}%  ({downloaded//1024//1024} / {total//1024//1024} MB)",
                )
    progress.progress(1.0, text="Download complete!")
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
                except Exception:
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
            except Exception:
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
        except Exception:
            pass
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


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # ── Session state ──────────────────────────────────────────────────────────
    if "overrides" not in st.session_state:
        st.session_state.overrides = load_overrides()

    wikidata_parties = get_wikidata_parties()

    # ── Header ────────────────────────────────────────────────────────────────
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
        st.markdown(
            '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
            'color:var(--dim);padding-bottom:14px;border-bottom:1px solid var(--border);'
            'margin-bottom:18px">Filters</div>',
            unsafe_allow_html=True,
        )

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

        # ── CTV Data Upload ───────────────────────────────────────────────────
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

        # ── Time Range ────────────────────────────────────────────────────────
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

        # ── Methodology ───────────────────────────────────────────────────────
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
                f'<div style="font-weight:600;font-size:13px;line-height:1.3">{name}</div>'
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
                    override_badge = ' <span style="color:#F5902B;font-size:10px;font-weight:700">OVERRIDDEN</span>' if name in overrides else ""
                    st.markdown(
                        f'<div style="font-weight:600;font-size:13px;margin-bottom:4px">{name}{override_badge}</div>'
                        f'<div style="font-size:11px;color:#6B6560;margin-bottom:2px">Inferred: {inferred_label} &nbsp;·&nbsp; {auto_src}</div>'
                        + (f'<div style="font-size:11px;color:#6B6560;margin-bottom:8px">Declared scope: {scope_note[:80]}{"…" if len(scope_note) > 80 else ""}</div>' if scope_note else '<div style="margin-bottom:8px"></div>'),
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
                    f'{_name}</div>',
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
                    f'<div style="font-size:13px;font-weight:600;color:#1A1714">{name}</div>'
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
                          if sel_adv in adv_spend_filtered else len(adv_spend)
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
                f'<h2 style="font-size:22px;font-weight:700;margin:0">{sel_adv}</h2>'
                f'<span style="padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;'
                f'letter-spacing:.06em;background:{p_bg};color:{p_color}">'
                f'{PARTY_LABEL.get(party_ins,"?").upper()}</span>'
                f'<span style="font-size:11px;color:#9CA3AF">via {party_src_ins}</span>'
                f'</div>'
                + (f'<div style="font-size:12px;color:#6B6560;margin-top:4px">{scope_note}</div>' if scope_note else "")
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

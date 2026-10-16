"""
styles.py — Global CSS injected on every page.
Call inject_styles() at the top of each page after set_page_config.
"""

import streamlit as st

_CSS = """
<style>
/* ── FONTS ─────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── GLOBAL RESETS ──────────────────────────────────────────────────── */
#MainMenu, footer, header, [data-testid="stHeader"], [data-testid="stSidebarHeader"], [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {
    display: none !important;
    visibility: hidden !important;
    height: 0px !important;
}

/* Remove Streamlit's default top padding */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px !important;
}

/* ── SIDEBAR ────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #0D0D0D !important;
    border-right: 1px solid #1E1E1E !important;
    padding-top: 1.5rem !important;
}

section[data-testid="stSidebar"] *:not(.material-symbols-rounded):not([data-testid="stIconMaterial"]) {
    font-family: 'Inter', sans-serif !important;
}

.material-symbols-rounded, [data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded' !important;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarHeader"],
header[data-testid="stHeader"],
button[data-testid="baseButton-headerNoPadding"],
button[aria-label*="sidebar" i],
button[aria-label*="Sidebar" i] {
    display: none !important;
    visibility: hidden !important;
    width: 0px !important;
    height: 0px !important;
    overflow: hidden !important;
}

section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] p {
    color: #888888 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

section[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #111111 !important;
    border: 1px solid #222222 !important;
    border-radius: 0px !important;
    color: #F5F5F5 !important;
    font-size: 0.85rem !important;
}

/* Sidebar nav links */
section[data-testid="stSidebar"] a {
    color: #666666 !important;
    text-decoration: none !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}

section[data-testid="stSidebar"] a:hover {
    color: #F5F5F5 !important;
}

/* ── HEADINGS ───────────────────────────────────────────────────────── */
h1 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1.4rem !important;
    color: #FFFFFF !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0 !important;
}

h2 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.75rem !important;
    color: #555555 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    margin-bottom: 0.75rem !important;
    margin-top: 0 !important;
}

h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    color: #888888 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

/* ── METRICS ────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background-color: #111111 !important;
    border: 1px solid #1E1E1E !important;
    border-radius: 0px !important;
    padding: 1rem 1.25rem !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: #555555 !important;
}

[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 500 !important;
    color: #F5F5F5 !important;
    letter-spacing: -0.02em !important;
}

[data-testid="stMetricDelta"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* ── BUTTONS ────────────────────────────────────────────────────────── */
.stButton > button {
    background-color: transparent !important;
    color: #F5F5F5 !important;
    border: 1px solid #333333 !important;
    border-radius: 0px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    padding: 0.5rem 1.25rem !important;
    transition: border-color 0.15s, color 0.15s !important;
}

.stButton > button:hover {
    border-color: #E53E3E !important;
    color: #E53E3E !important;
    background-color: transparent !important;
}

.stButton > button:active {
    background-color: #E53E3E !important;
    color: #FFFFFF !important;
    border-color: #E53E3E !important;
}

/* ── DATAFRAME / TABLE ──────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #1E1E1E !important;
    border-radius: 0px !important;
}

[data-testid="stDataFrame"] th {
    background-color: #0D0D0D !important;
    color: #555555 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    border-bottom: 1px solid #222222 !important;
}

[data-testid="stDataFrame"] td {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
    color: #CCCCCC !important;
    border-bottom: 1px solid #161616 !important;
}

/* ── SELECTBOX / INPUTS ─────────────────────────────────────────────── */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background-color: #111111 !important;
    border: 1px solid #222222 !important;
    border-radius: 0px !important;
    color: #F5F5F5 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
}

/* ── SLIDER ─────────────────────────────────────────────────────────── */
/* Track fill */
.stSlider > div > div > div > div {
    background-color: #E53E3E !important;
}
/* Thumb */
[data-testid="stSlider"] [role="slider"] {
    background-color: #E53E3E !important;
    border: 2px solid #E53E3E !important;
}
/* Value label — always visible, not just on hover */
[data-testid="stSlider"] > div > div > div > div > div,
[data-testid="stSlider"] [data-testid="stThumbValue"],
[data-testid="stSlider"] output {
    opacity: 1 !important;
    visibility: visible !important;
    color: #F5F5F5 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
}
/* Slider label text */
[data-testid="stSlider"] label {
    color: #CCCCCC !important;
    font-size: 0.78rem !important;
}
/* Min / Max tick labels */
[data-testid="stTickBarMin"],
[data-testid="stTickBarMax"] {
    opacity: 1 !important;
    visibility: visible !important;
    color: #888888 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
}

/* ── ALERTS / INFO / SUCCESS / WARNING ──────────────────────────────── */
.stAlert {
    border-radius: 0px !important;
    border-left-width: 3px !important;
    background-color: #111111 !important;
}

/* ── EXPANDER ───────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #1E1E1E !important;
    border-radius: 0px !important;
    background-color: #111111 !important;
}

/* ── DIVIDER ────────────────────────────────────────────────────────── */
hr {
    border-color: #1E1E1E !important;
    margin: 1rem 0 !important;
}

/* ── SPINNER ────────────────────────────────────────────────────────── */
.stSpinner > div {
    border-top-color: #E53E3E !important;
}

/* ── PAGE LINK (sidebar nav) ────────────────────────────────────────── */
[data-testid="stPageLink"] a {
    color: #555555 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    text-decoration: none !important;
    padding: 0.4rem 0 !important;
    display: block !important;
    border-left: 2px solid transparent !important;
    padding-left: 0.75rem !important;
    transition: color 0.15s, border-color 0.15s !important;
}

[data-testid="stPageLink"] a:hover,
[data-testid="stPageLink-active"] a {
    color: #F5F5F5 !important;
    border-left-color: #E53E3E !important;
}

/* ── SCROLLBAR ──────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0A; }
::-webkit-scrollbar-thumb { background: #2A2A2A; border-radius: 0px; }
::-webkit-scrollbar-thumb:hover { background: #3A3A3A; }

/* ── UTILITY CLASSES ────────────────────────────────────────────────── */

/* Stat block — large monospace number with label */
.volt-stat {
    padding: 1.25rem 1.5rem;
    border: 1px solid #1E1E1E;
    background: #111111;
}

.volt-stat .label {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #555555;
    margin-bottom: 0.35rem;
    font-family: 'Inter', sans-serif;
}

.volt-stat .value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem;
    font-weight: 500;
    color: #FFFFFF;
    line-height: 1;
    letter-spacing: -0.03em;
}

.volt-stat .sub {
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    color: #444444;
    margin-top: 0.3rem;
}

/* Status badge */
.volt-badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid currentColor;
    line-height: 1.6;
}

.volt-badge.waste     { color: #E53E3E; border-color: #E53E3E22; background: #E53E3E0A; }
.volt-badge.inefficient { color: #E07B39; border-color: #E07B3922; background: #E07B390A; }
.volt-badge.occupied  { color: #AAAAAA; border-color: #AAAAAA22; background: transparent; }
.volt-badge.efficient { color: #555555; border-color: #33333344; background: transparent; }
.volt-badge.monitoring { color: #888888; border-color: #44444444; background: transparent; }

/* Room row in the status table */
.volt-room-row {
    display: grid;
    grid-template-columns: 2fr 1.2fr 0.8fr 0.8fr 1fr;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #161616;
    gap: 1rem;
}

.volt-room-row:last-child { border-bottom: none; }

.volt-room-row .room-name {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #CCCCCC;
    font-weight: 400;
}

.volt-room-row .room-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: #666666;
}

/* Section header with top border */
.volt-section-header {
    border-top: 1px solid #1E1E1E;
    padding-top: 1rem;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #444444;
}

/* Top bar — wordmark + live indicator */
.volt-topbar {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #1E1E1E;
    margin-bottom: 1.5rem;
}

.volt-wordmark {
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: #FFFFFF;
    letter-spacing: -0.01em;
}

.volt-wordmark span {
    color: #E53E3E;
}

.volt-live-dot {
    width: 6px;
    height: 6px;
    background: #E53E3E;
    border-radius: 50%;
    display: inline-block;
    margin-right: 0.4rem;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

.volt-live-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #555555;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.volt-timestamp {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #444444;
    letter-spacing: 0.05em;
}

/* ── SIDEBAR ICON FIX (prevents 'keyboard_double_arrow_left' text) ─── */
.material-symbols-rounded {
    font-family: 'Material Symbols Rounded' !important;
    font-size: 20px !important;
    font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 20;
}

/* ── SLIDER VALUE TOOLTIP ────────────────────────────────────────────── */
/* Undo any accidental visibility:hidden on slider thumb tooltip */
[data-testid="stSlider"] [role="slider"] {
    background-color: #E53E3E !important;
}
[data-testid="stSlider"] > div > div > div > div > div {
    color: #F5F5F5 !important;
    visibility: visible !important;
}
/* Slider track fill */
[data-testid="stSlider"] > div > div > div > div {
    background: #E53E3E !important;
}
</style>
"""

def inject_styles():
    """Call once per page, right after st.set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)

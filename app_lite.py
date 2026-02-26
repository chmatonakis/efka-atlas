#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import html as html_mod
import os
import re
import uuid
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

os.environ.setdefault("ATLAS_LITE", "1")

from app_final import (
    extract_efka_data,
    build_print_html,
    build_print_section_html,
    build_print_table_html,
    build_yearly_print_html,
    wrap_print_html,
    get_print_disclaimer_html,
    build_summary_grouped_display,
    build_count_report,
    generate_audit_report,
    build_description_map,
    get_last_update_date,
    find_gaps_in_insurance_data,
    find_zero_duration_intervals,
    build_parallel_print_df,
    build_parallel_2017_print_df,
    build_multi_employment_print_df,
    compute_complex_file_metrics,
    should_show_complex_file_warning,
)

st.set_page_config(
    page_title="ATLAS Lite",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap');

:root {
    --font-main: "Fira Sans", -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    --color-bg: #f5f6f7;
    --color-surface: #ffffff;
    --color-border: #e1e4e8;
    --color-text: #111827;
    --color-text-muted: #6c757d;
    --color-text-subtle: #4a5568;
    --color-primary: #6f42c1;
    --color-primary-dark: #5a189a;
    --color-accent: #e88e10;
    --color-success: #00b050;
    --color-info: #0666ba;
    --color-link: #0056b3;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
    --shadow-lg: 0 10px 30px rgba(0,0,0,0.08);
    --transition: all 0.2s ease;
}

#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stToolbar"] {visibility: hidden;}
div[data-testid="stDecoration"] {visibility: hidden;}
div[data-testid="stStatusWidget"] {visibility: hidden;}

.stApp { background-color: var(--color-bg); }
html, body, [data-testid="stAppViewContainer"], .block-container {
    font-family: var(--font-main) !important;
    font-size: 17px;
    color: var(--color-text);
}

div.stButton > button[kind="primary"] {
    background-color: #ee1d23 !important; color: white !important;
    border: 1px solid #ee1d23 !important; font-weight: 700 !important;
    font-size: 18px !important; padding: 0.6rem 2rem !important;
    box-shadow: var(--shadow-sm) !important; border-radius: var(--radius-sm) !important;
    width: 100%; font-family: var(--font-main) !important; transition: var(--transition);
}
div.stButton > button[kind="primary"]:hover {
    background-color: #cc181e !important; border-color: #cc181e !important;
    color: white !important; box-shadow: var(--shadow-md) !important;
    transform: translateY(-1px);
}
div.stButton > button[kind="secondary"] {
    background-color: white !important; color: #333 !important;
    border: 1px solid #ddd !important; font-weight: 600 !important;
    font-size: 18px !important; padding: 0.6rem 2rem !important;
    border-radius: var(--radius-sm) !important; width: 100%;
    font-family: var(--font-main) !important; transition: var(--transition);
}
div.stButton > button[kind="secondary"]:hover {
    background-color: #f1f1f1 !important; border-color: #ccc !important;
    color: #000 !important; transform: translateY(-1px);
}

/* Κουμπί Προβολή Ανάλυσης: μπλε (η κλάση προστίθεται με JS) */
button.btn-view-analysis,
button.btn-view-analysis:hover {
    background-color: #2563eb !important; border-color: #2563eb !important;
    color: white !important;
}
button.btn-view-analysis:hover {
    background-color: #1d4ed8 !important; border-color: #1d4ed8 !important;
}


/* All headings & markdown text */
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stCaptionContainer"],
label {
    font-family: var(--font-main) !important;
}
[data-testid="stMarkdownContainer"] h3 {
    font-weight: 700 !important;
    color: #1e293b !important;
}

/* Streamlit messages: accent left-border */
div[data-testid="stAlert"] > div {
    border-left: 4px solid currentColor !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--font-main) !important;
}

.purple-header {
    background: linear-gradient(135deg, #7b2cbf 0%, var(--color-primary-dark) 100%);
    color: white; text-align: center; padding: 2rem 1rem;
    margin: -4rem -5rem 2rem -5rem; font-size: 2rem; font-weight: 700;
    box-shadow: var(--shadow-md);
}
.upload-section {
    background-color: transparent; padding: 1.5rem 1rem;
    border-radius: var(--radius-md); border: 0;
    text-align: center; margin: 1rem 0 2rem 0;
}
[data-testid="stFileUploader"] {
    background-color: #f8fbff; padding: 3rem;
    border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
    border: 2px dashed #3b82f6; max-width: 800px; margin: 0 auto;
    transition: var(--transition);
}
.upload-prompt-text {
    font-size: 1.2rem; font-weight: 600; color: var(--color-text);
    margin-bottom: 1rem; text-align: center !important;
    width: 100%; display: block;
}
.efka-link { color: var(--color-link) !important; text-decoration: none; font-weight: 400; font-size: 1rem; }
.efka-link:hover { text-decoration: underline; color: #003d82 !important; }
.instructions-box {
    max-width: 800px; margin: 0 auto 4rem auto;
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: 12px; padding: 3rem; box-shadow: var(--shadow-md);
}
.instructions-title {
    font-size: 1.5rem; font-weight: 700; color: #2c3e50;
    margin-bottom: 2rem; text-align: center;
    border-bottom: 2px solid #f0f2f5; padding-bottom: 1rem;
}
.instructions-list {
    text-align: left; color: var(--color-text-subtle);
    font-size: 1.1rem; line-height: 1.8;
}
.main-footer {
    margin-top: 5rem; padding: 3rem 1rem;
    background-color: #f8f9fa; border-top: 1px solid var(--color-border);
    text-align: center; color: var(--color-text-muted);
    margin-left: -5rem; margin-right: -5rem; margin-bottom: -5rem;
}
.footer-disclaimer {
    font-size: 0.85rem; color: var(--color-text-muted);
    margin-bottom: 1.5rem; line-height: 1.6;
    max-width: 800px; margin-left: auto; margin-right: auto;
}
.footer-copyright { font-weight: 600; color: #2c3e50; font-size: 0.95rem; }
</style>
""",
    unsafe_allow_html=True
)

# Google Analytics (GA4)
components.html(
    """
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-PDYEH50X5W"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-PDYEH50X5W');
    </script>
    """,
    height=0
)

def get_section() -> str:
    try:
        section = st.query_params.get("section", "summary")
    except Exception:
        params = st.experimental_get_query_params()
        section = params.get("section", ["summary"])[0]
    section = (section or "summary").strip().lower()
    if section not in {"summary", "summary_grouped", "count", "all"}:
        section = "summary"
    return section

def get_query_param(name: str) -> str:
    try:
        return str(st.query_params.get(name, "") or "")
    except Exception:
        params = st.experimental_get_query_params()
        return str(params.get(name, [""])[0])

section = get_section()
client_name_param = get_query_param("client").strip()

if "lite_file_uploaded" not in st.session_state:
    st.session_state["lite_file_uploaded"] = False
if "lite_processing_done" not in st.session_state:
    st.session_state["lite_processing_done"] = False

if client_name_param and not st.session_state.get("lite_client_name"):
    st.session_state["lite_client_name"] = client_name_param

# Header
st.markdown('''
    <div class="purple-header">
        ATLAS lite
    </div>
''', unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align: center; color: #666; font-size: 0.85rem; margin-top: 0.5rem; margin-bottom: 1rem;'>{get_last_update_date()}</div>",
    unsafe_allow_html=True
)

if not st.session_state["lite_file_uploaded"]:
    st.markdown('<div class="upload-prompt-text">Ανεβάστε το αρχείο ΑΤΛΑΣ για ανάλυση</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Επιλέξτε PDF αρχείο",
        type=["pdf"],
        help="Ανεβάστε το PDF αρχείο e‑EFKA",
        label_visibility="collapsed"
    )

    if uploaded_file is not None:
        st.session_state["lite_uploaded_file"] = uploaded_file
        st.session_state["lite_filename"] = uploaded_file.name
        st.session_state["lite_file_uploaded"] = True
        st.rerun()

    st.markdown('''
        <div class="instructions-box">
            <div class="instructions-title">Γενικές Οδηγίες Χρήσης</div>
            <div class="instructions-list">
                1. Μεταβείτε στην υπηρεσία του e-ΕΦΚΑ πατώντας <a href="https://www.e-efka.gov.gr/el/elektronikes-yperesies/synoptiko-kai-analytiko-istoriko-asphalises" target="_blank" class="efka-link">εδώ</a>.<br>
                2. Συνδεθείτε με τους κωδικούς Taxisnet.<br>
                3. Επιλέξτε "Συνοπτικό και Αναλυτικό Ιστορικό Ασφάλισης".<br>
                4. Κατεβάστε το αρχείο σε μορφή PDF στον υπολογιστή σας.<br>
                5. Ανεβάστε το αρχείο που κατεβάσατε στην παραπάνω φόρμα.<br>
                <br>
                <strong>Σημείωση:</strong> Τα δεδομένα επεξεργάζονται αποκλειστικά στον browser σας (client-side) και δεν αποθηκεύονται σε κανέναν server.
            </div>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown('''
        <div class="main-footer">
            <div class="footer-disclaimer">
                <strong>ΑΠΟΠΟΙΗΣΗ ΕΥΘΥΝΗΣ:</strong> Η παρούσα εφαρμογή αποτελεί εργαλείο ιδιωτικής πρωτοβουλίας για την διευκόλυνση ανάγνωσης του ασφαλιστικού βιογραφικού. 
                Δεν συνδέεται με τον e-ΕΦΚΑ ή άλλο δημόσιο φορέα. 
                Τα αποτελέσματα παράγονται βάσει των δεδομένων του αρχείου PDF που εισάγετε και ενδέχεται να περιέχουν ανακρίβειες. 
                Για επίσημη πληροφόρηση και θέματα συνταξιοδότησης, απευθυνθείτε αποκλειστικά στον e-ΕΦΚΑ.
            </div>
            <div class="footer-copyright">
                © Syntaksi Pro - my advisor
            </div>
        </div>
    ''', unsafe_allow_html=True)
    st.stop()

if not st.session_state["lite_processing_done"]:
    st.markdown('<div class="app-container upload-section">', unsafe_allow_html=True)
    st.markdown("### Επιλεγμένο αρχείο")
    st.success(f"{st.session_state['lite_uploaded_file'].name}")
    st.info(f"Μέγεθος: {st.session_state['lite_uploaded_file'].size:,} bytes")

    if st.button("Επεξεργασία", type="primary"):
        st.session_state["lite_processing_done"] = True
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('''
        <div class="instructions-box">
            <div class="instructions-title">Οδηγίες</div>
            <div class="instructions-list">
                • Κατεβάστε το PDF του Ασφαλιστικού βιογραφικού από τον e‑EFKA<br>
                • Προτείνεται Chrome/Edge για καλύτερη συμβατότητα<br>
                • Ανεβάστε το αρχείο από τη φόρμα παραπάνω<br>
                • Πατήστε "Επεξεργασία" για ανάλυση<br>
                • Μετά την επεξεργασία θα εμφανιστούν οι σύνδεσμοι εκτύπωσης<br>
                • Τα δεδομένα επεξεργάζονται τοπικά και δεν αποθηκεύονται
            </div>
        </div>
    ''', unsafe_allow_html=True)
    st.stop()

if st.session_state.get("lite_df") is None:
    with st.spinner("Επεξεργασία αρχείου..."):
        st.session_state["lite_df"] = extract_efka_data(st.session_state["lite_uploaded_file"])
        st.rerun()

df = st.session_state.get("lite_df")
if df is None or df.empty:
    st.warning("Δεν βρέθηκαν δεδομένα. Παρακαλώ ανεβάστε ξανά το αρχείο.")
    st.stop()

# Μετά την επεξεργασία πηγαίνουμε πάντα στο section "all" για να εμφανίζονται τα 3 κουμπιά
if section != "all":
    try:
        st.query_params["section"] = "all"
        if st.session_state.get("lite_client_name"):
            st.query_params["client"] = st.session_state["lite_client_name"]
    except Exception:
        st.experimental_set_query_params(section="all", client=st.session_state.get("lite_client_name", ""))
    st.rerun()

if "lite_show_disclaimer" not in st.session_state:
    st.session_state["lite_show_disclaimer"] = False
if "lite_disclaimer_for" not in st.session_state:
    st.session_state["lite_disclaimer_for"] = "viewer"  # "viewer" | "print"
if "lite_do_open" not in st.session_state:
    st.session_state["lite_do_open"] = None  # None | "viewer" | "print"

def show_disclaimer_dialog():
    disclaimer_text = (
        "Η αναφορά βασίζεται αποκλειστικά στα δεδομένα του αρχείου ΑΤΛΑΣ/e‑ΕΦΚΑ. "
        "Ενδέχεται να υπάρχουν κενά ή σφάλματα και απαιτείται έλεγχος από τον χρήστη."
    )
    try:
        @st.dialog("Πριν την προβολή")
        def _dlg():
            st.warning(disclaimer_text)
            if st.button("Αποδοχή-Προβολή", type="primary"):
                st.session_state["lite_do_open"] = st.session_state.get("lite_disclaimer_for", "viewer")
                st.session_state["lite_show_disclaimer"] = False
                try:
                    st.query_params["section"] = "all"
                    if client_value:
                        st.query_params["client"] = client_value
                except Exception:
                    st.experimental_set_query_params(section="all", client=client_value)
                st.rerun()
        _dlg()
    except Exception:
        st.warning(disclaimer_text)
        if st.button("Αποδοχή-Προβολή", type="primary"):
            st.session_state["lite_do_open"] = st.session_state.get("lite_disclaimer_for", "viewer")
            st.session_state["lite_show_disclaimer"] = False
            try:
                st.query_params["section"] = "all"
                if client_value:
                    st.query_params["client"] = client_value
            except Exception:
                st.experimental_set_query_params(section="all", client=client_value)
            st.rerun()

# --- CENTERED INPUTS LAYOUT ---
# We use empty columns to center the content in the middle ~40-50%
col_left, col_mid, col_right = st.columns([1, 1.5, 1], gap="medium")

with col_mid:
    # 1. Full Name Input
    client_name = st.text_input("Ονοματεπώνυμο:", value=st.session_state.get("lite_client_name", ""), key="client_input")
    st.session_state["lite_client_name"] = client_name

    client_value = client_name.strip()

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # 2. Τρία κουμπιά: Προβολή Ανάλυσης (κέντρο πάνω, μπλε), Εκτύπωση & Νέο αρχείο (κάτω)
    if st.button("Προβολή Ανάλυσης", type="primary", use_container_width=True, key="view_analysis_btn"):
        st.session_state["lite_disclaimer_for"] = "viewer"
        st.session_state["lite_show_disclaimer"] = True
        st.rerun()

    st.markdown("""
    <script>
    (function() {
      function styleViewButton() {
        var btns = document.querySelectorAll('div[data-testid="stButton"] button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].textContent.trim() === 'Προβολή Ανάλυσης') {
            btns[i].classList.add('btn-view-analysis');
            return true;
          }
        }
        return false;
      }
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', styleViewButton);
      } else {
        styleViewButton();
      }
      setTimeout(styleViewButton, 500);
      setTimeout(styleViewButton, 1500);
    })();
    </script>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    b_col1, b_col2 = st.columns([1, 1], gap="small")

    with b_col1:
        if st.button("Εκτύπωση", type="primary", use_container_width=True):
            st.session_state["lite_disclaimer_for"] = "print"
            st.session_state["lite_show_disclaimer"] = True
            st.rerun()

    with b_col2:
        if st.button("Νέο αρχείο", type="secondary", use_container_width=True):
            for key in [
                "lite_file_uploaded",
                "lite_processing_done",
                "lite_uploaded_file",
                "lite_filename",
                "lite_df",
                "lite_client_name",
                "lite_show_disclaimer",
                "lite_disclaimer_for",
                "lite_do_open",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            try:
                st.query_params.clear()
            except Exception:
                st.experimental_set_query_params()
            st.rerun()

if st.session_state.get("lite_show_disclaimer"):
    show_disclaimer_dialog()

description_map = build_description_map(df)
excluded_packages = {"Α", "Λ", "Υ", "Ο", "Χ", "026", "899"}
excluded_packages_label = ", ".join(sorted(excluded_packages))
LITE_EXCLUSION_NOTE = f'<div class="lite-exclusion-note">Εξαιρούνται από την καταμέτρηση: {excluded_packages_label}</div>'
COMPLEX_FILE_WARNING_HTML = (
    '<div class="complex-file-warning" style="'
    'background:#fef2f2;border:2px solid #dc2626;border-radius:8px;padding:12px 16px;margin-bottom:16px;'
    'color:#991b1b;font-weight:700;font-size:1rem;">'
    '⚠️ Προσοχή: Περίπλοκο αρχείο — Ελέγξτε απαραίτητα το πρωτότυπο ΑΤΛΑΣ.'
    '</div>'
)
if 'Κλάδος/Πακέτο Κάλυψης' in df.columns:
    pkg_series = df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
    count_df = df[~pkg_series.isin(excluded_packages)].copy()
else:
    count_df = df.copy()

def _parse_greek_number(s):
    """Μετατροπή ελληνικού αριθμού (π.χ. 7.725 ή 29,5) σε float."""
    if pd.isna(s) or s == "" or str(s).strip() in ("-", ""):
        return 0
    s = str(s).strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0


def _build_timeline_html(source_df):
    """Χρονοδιάγραμμα ασφάλισης ανά Ταμείο - Τύπο Ασφάλισης με οπτικές μπάρες."""
    if source_df.empty or 'Από' not in source_df.columns or 'Έως' not in source_df.columns:
        return ""

    t = source_df.copy()
    t['_from'] = pd.to_datetime(t['Από'], format='%d/%m/%Y', errors='coerce')
    t['_to'] = pd.to_datetime(t['Έως'], format='%d/%m/%Y', errors='coerce')
    t = t.dropna(subset=['_from', '_to'])
    if t.empty:
        return ""

    tameio_col = 'Ταμείο' if 'Ταμείο' in t.columns else None
    ins_col = 'Τύπος Ασφάλισης' if 'Τύπος Ασφάλισης' in t.columns else None

    if tameio_col:
        t['_label'] = t[tameio_col].astype(str).str.strip()
        if ins_col:
            ins_vals = t[ins_col].astype(str).str.strip()
            mask = (ins_vals != '') & (ins_vals != 'nan')
            t.loc[mask, '_label'] = t.loc[mask, '_label'] + ' — ' + ins_vals[mask]
    else:
        t['_label'] = 'Ασφάλιση'

    global_min = t['_from'].min()
    global_max = t['_to'].max()
    total_days = (global_max - global_min).days
    if total_days <= 0:
        return ""

    gaps_df = find_gaps_in_insurance_data(source_df)

    fund_colors = [
        '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444',
        '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
    ]

    groups = t.groupby('_label', sort=False)
    label_order = list(groups.groups.keys())

    color_map = {}
    for i, lbl in enumerate(label_order):
        color_map[lbl] = fund_colors[i % len(fund_colors)]

    rows_html = []

    legend_items = "".join(
        f'<span class="tl-legend-item"><span class="tl-legend-dot" style="background:{color_map[lbl]};"></span>{html_mod.escape(lbl)}</span>'
        for lbl in label_order
    )

    for lbl in label_order:
        grp = groups.get_group(lbl)
        color = color_map[lbl]
        bars = []
        for _, r in grp.iterrows():
            left_pct = max(0, (r['_from'] - global_min).days / total_days * 100)
            width_pct = max(0.3, (r['_to'] - r['_from']).days / total_days * 100)
            tooltip = f"{r['Από']} — {r['Έως']}"
            bars.append(
                f'<div class="tl-bar" style="left:{left_pct:.2f}%;width:{width_pct:.2f}%;background:{color};" title="{html_mod.escape(tooltip)}"></div>'
            )
        rows_html.append(
            f'<div class="tl-row">'
            f'<div class="tl-label">{html_mod.escape(lbl)}</div>'
            f'<div class="tl-track">{"".join(bars)}</div>'
            f'</div>'
        )

    gap_bars = ""
    if gaps_df is not None and not gaps_df.empty:
        gap_items = []
        gaps_df2 = gaps_df.copy()
        gaps_df2['_gf'] = pd.to_datetime(gaps_df2['Από'], format='%d/%m/%Y', errors='coerce')
        gaps_df2['_gt'] = pd.to_datetime(gaps_df2['Έως'], format='%d/%m/%Y', errors='coerce')
        gaps_df2 = gaps_df2.dropna(subset=['_gf', '_gt'])
        for _, g in gaps_df2.iterrows():
            left_pct = max(0, (g['_gf'] - global_min).days / total_days * 100)
            width_pct = max(0.3, (g['_gt'] - g['_gf']).days / total_days * 100)
            tooltip = f"Κενό: {g['Από']} — {g['Έως']}"
            gap_items.append(
                f'<div class="tl-bar tl-gap" style="left:{left_pct:.2f}%;width:{width_pct:.2f}%;" title="{html_mod.escape(tooltip)}"></div>'
            )
        if gap_items:
            rows_html.append(
                f'<div class="tl-row">'
                f'<div class="tl-label tl-label-gap">Κενά</div>'
                f'<div class="tl-track">{"".join(gap_items)}</div>'
                f'</div>'
            )
            legend_items += '<span class="tl-legend-item"><span class="tl-legend-dot" style="background:repeating-linear-gradient(45deg,#fca5a5,#fca5a5 2px,#fecaca 2px,#fecaca 4px);border:1px solid #ef4444;"></span>Κενά</span>'

    year_min = global_min.year
    year_max = global_max.year
    tick_years = list(range(year_min, year_max + 1, max(1, (year_max - year_min) // 12)))
    if tick_years[-1] != year_max:
        tick_years.append(year_max)
    ticks_html = ""
    for yr in tick_years:
        yr_date = pd.Timestamp(year=yr, month=1, day=1)
        pos = max(0, min(100, (yr_date - global_min).days / total_days * 100))
        ticks_html += f'<div class="tl-tick" style="left:{pos:.2f}%;"><span>{yr}</span></div>'

    period_str = f"{global_min.strftime('%d/%m/%Y')} — {global_max.strftime('%d/%m/%Y')}"

    return f"""
    <section class="print-section">
      <h2>Χρονοδιάγραμμα Ασφάλισης</h2>
      <p class="print-description">Οπτική απεικόνιση χρονικών περιόδων ασφάλισης ανά Ταμείο. Περίοδος: {html_mod.escape(period_str)}</p>
      <div class="tl-legend">{legend_items}</div>
      <div class="tl-container">
        {"".join(rows_html)}
        <div class="tl-axis">{ticks_html}</div>
      </div>
    </section>
    """


def _build_totals_with_filters(display_summary, warning_types=None):
    """Κατασκευή της ενότητας Σύνολα με φίλτρα Πακέτο, Ταμείο, Από-Έως (default κενά, πολλαπλή επιλογή).
    warning_types: λίστα από strings όπως ['παράλληλη ασφάλιση', 'πολλαπλή απασχόληση', 'παράλληλη απασχόληση 2017+']
    """
    paketo_col = "Κλάδος/Πακέτο Κάλυψης"
    tameio_col = "Ταμείο"
    apo_col = "Από"
    eos_col = "Έως"
    hmeres_col = "Συνολικές ημέρες"

    # Μοναδικές τιμές για τα dropdowns
    paketo_vals = sorted(display_summary[paketo_col].dropna().astype(str).str.strip().unique().tolist()) if paketo_col in display_summary.columns else []
    tameio_vals = sorted(display_summary[tameio_col].dropna().astype(str).str.strip().unique().tolist()) if tameio_col in display_summary.columns else []

    # HTML για φίλτρα (checkboxes, default κενά)
    def _checkboxes(name, values, data_attr):
        if not values:
            return ""
        items = "".join(
            f'<label class="filter-cb"><input type="checkbox" name="{name}" value="{html_mod.escape(str(v))}" data-attr="{data_attr}">{html_mod.escape(str(v))}</label>'
            for v in values
        )
        return f'<div class="filter-group"><span class="filter-label">{name}:</span><div class="filter-options">{items}</div></div>'

    paketo_filters = _checkboxes("Πακέτο", paketo_vals, "paketo")
    tameio_filters = _checkboxes("Ταμείο", tameio_vals, "tameio")
    date_filters = '''
    <div class="filter-group">
      <span class="filter-label">Από (ηη/μμ/εεεε):</span>
      <input type="text" id="filter-apo" class="filter-date" placeholder="ηη/μμ/εεεε" maxlength="10">
    </div>
    <div class="filter-group">
      <span class="filter-label">Έως (ηη/μμ/εεεε):</span>
      <input type="text" id="filter-eos" class="filter-date" placeholder="ηη/μμ/εεεε" maxlength="10">
    </div>
    '''

    # Ενημερωτικό ή προειδοποιητικό μήνυμα + Σύνοψη
    warning_types = warning_types or []
    if warning_types:
        warn_text = ", ".join(warning_types)
        info_msg = f"Προσοχή: υπάρχει πιθανή {warn_text}. Το άθροισμα ημερών μπορεί να δώσει λάθος αποτελέσματα."
        info_bar_class = "totals-info-bar totals-info-bar-warning"
    else:
        info_msg = "Επιλέξτε πακέτα κάλυψης για αθροιστική προϋπηρεσία."
        info_bar_class = "totals-info-bar"
    info_banner = f'''
    <div class="{info_bar_class}">
      <div class="totals-info-msg">{html_mod.escape(info_msg)}</div>
      <div class="totals-summary">
        <div class="totals-summary-item">
          <span class="totals-summary-label">Εκτίμηση Ημερών Ασφάλισης</span>
          <span class="totals-summary-value" id="totals-sum-hmeres">—</span>
        </div>
        <div class="totals-summary-item">
          <span class="totals-summary-label">Συνολικά Έτη</span>
          <span class="totals-summary-value" id="totals-sum-eti">—</span>
        </div>
      </div>
    </div>
    '''

    filters_bar = f'''
    <div class="totals-filters">
      {paketo_filters}
      {tameio_filters}
      {date_filters}
    </div>
    '''

    # Πίνακας με data attributes σε κάθε γραμμή (συμπεριλαμβανομένου data-hmeres για άθροισμα)
    headers_html = "".join(f"<th>{html_mod.escape(str(h))}</th>" for h in display_summary.columns)
    rows_parts = []
    for _, row in display_summary.iterrows():
        paketo_val = str(row.get(paketo_col, "")).strip() if paketo_col in row.index else ""
        tameio_val = str(row.get(tameio_col, "")).strip() if tameio_col in row.index else ""
        apo_val = str(row.get(apo_col, "")).strip() if apo_col in row.index else ""
        eos_val = str(row.get(eos_col, "")).strip() if eos_col in row.index else ""
        hmeres_raw = _parse_greek_number(row.get(hmeres_col, 0)) if hmeres_col in row.index else 0
        is_total = any(str(v).strip().startswith("Σύνολο") for v in row.values)
        tr_cls = ' class="total-row"' if is_total else ""
        data_attrs = f' data-paketo="{html_mod.escape(paketo_val)}" data-tameio="{html_mod.escape(tameio_val)}" data-apo="{html_mod.escape(apo_val)}" data-eos="{html_mod.escape(eos_val)}" data-hmeres="{int(hmeres_raw)}"'
        tds = "".join(f"<td>{'' if pd.isna(v) else html_mod.escape(str(v))}</td>" for v in row.values)
        rows_parts.append(f"<tr{tr_cls}{data_attrs}>{tds}</tr>")
    table_body = "".join(rows_parts)
    custom_table = f'<table class="print-table wrap-cells" id="totals-filter-table"><thead><tr>{headers_html}</tr></thead><tbody>{table_body}</tbody></table>'

    js = """
    (function(){
      function parseDate(str) {
        if (!str || str === '') return null;
        var parts = str.match(/^(\\d{1,2})\\/(\\d{1,2})\\/(\\d{4})$/);
        if (!parts) return null;
        return new Date(parseInt(parts[3],10), parseInt(parts[2],10)-1, parseInt(parts[1],10));
      }
      function formatGreekInt(n) {
        if (n === 0) return '0';
        return n.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');
      }
      function formatGreekDec(n) {
        var parts = n.toFixed(1).split('.');
        var intPart = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');
        return intPart + ',' + parts[1];
      }
      function applyTotalsFilters() {
        var rows = document.querySelectorAll('#totals-filter-table tbody tr');
        var paketoChecked = [];
        document.querySelectorAll('.totals-filters input[name="Πακέτο"]:checked').forEach(function(cb){ paketoChecked.push(cb.value); });
        var tameioChecked = [];
        document.querySelectorAll('.totals-filters input[name="Ταμείο"]:checked').forEach(function(cb){ tameioChecked.push(cb.value); });
        var apoVal = document.getElementById('filter-apo') ? document.getElementById('filter-apo').value.trim() : '';
        var eosVal = document.getElementById('filter-eos') ? document.getElementById('filter-eos').value.trim() : '';
        var apoDate = apoVal ? parseDate(apoVal) : null;
        var eosDate = eosVal ? parseDate(eosVal) : null;

        var hasSelection = paketoChecked.length > 0;
        var totalHmeres = 0;

        rows.forEach(function(tr) {
          var paketo = (tr.getAttribute('data-paketo') || '').trim();
          var tameio = (tr.getAttribute('data-tameio') || '').trim();
          var apoStr = (tr.getAttribute('data-apo') || '').trim();
          var eosStr = (tr.getAttribute('data-eos') || '').trim();

          var paketoOk = paketoChecked.length === 0 || paketoChecked.indexOf(paketo) !== -1;
          var tameioOk = tameioChecked.length === 0 || tameioChecked.indexOf(tameio) !== -1;

          var apoRow = parseDate(apoStr);
          var eosRow = parseDate(eosStr);
          var rangeOk = true;
          if (apoDate) rangeOk = rangeOk && eosRow && eosRow >= apoDate;
          if (eosDate) rangeOk = rangeOk && apoRow && apoRow <= eosDate;

          var visible = paketoOk && tameioOk && rangeOk;
          tr.style.display = visible ? '' : 'none';
          if (visible) {
            var h = parseInt(tr.getAttribute('data-hmeres') || '0', 10);
            totalHmeres += h;
          }
        });

        var elHmeres = document.getElementById('totals-sum-hmeres');
        var elEti = document.getElementById('totals-sum-eti');
        if (elHmeres && elEti) {
          if (!hasSelection) {
            elHmeres.textContent = '—';
            elEti.textContent = '—';
          } else {
            elHmeres.textContent = totalHmeres > 0 ? formatGreekInt(totalHmeres) : '—';
            elEti.textContent = totalHmeres > 0 ? formatGreekDec(totalHmeres / 300) : '—';
          }
        }
      }

      document.querySelectorAll('.totals-filters input').forEach(function(inp) {
        inp.addEventListener('change', applyTotalsFilters);
      });
      document.querySelectorAll('.totals-filters input.filter-date').forEach(function(inp) {
        inp.addEventListener('input', applyTotalsFilters);
      });
      applyTotalsFilters();
    })();
    """

    section_html = f"""
    <section class="print-section">
      <h2>Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)</h2>
      <p class="print-description">Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης και Ταμείο.</p>
      {info_banner}
      {filters_bar}
      {custom_table}
      <script>{js}</script>
    </section>
    """
    return section_html

# --- FULL WIDTH REPORT OUTPUT ---
if section == "all":
    # Μπλε κουμπί "Προβολή Ανάλυσης" (script τρέχει στο parent document)
    components.html("""
    <script>
    (function() {
      try {
        var doc = window.parent.document;
        var btns = doc.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
          if (btns[i].textContent.trim().indexOf('Προβολή Ανάλυσης') !== -1) {
            btns[i].classList.add('btn-view-analysis');
            btns[i].style.setProperty('background-color', '#2563eb', 'important');
            btns[i].style.setProperty('border-color', '#2563eb', 'important');
            break;
          }
        }
      } catch (e) {}
    })();
    </script>
    """, height=0)

    do_open = st.session_state.get("lite_do_open")

    def _build_report_block():
        audit_df = generate_audit_report(df)
        display_summary = build_summary_grouped_display(df, df) if 'Κλάδος/Πακέτο Κάλυψης' in df.columns else pd.DataFrame()
        final_display_df, _, _, _, print_style_rows = build_count_report(
            count_df,
            description_map=description_map,
            show_count_totals_only=False
        )
        show_complex_warning = False
        try:
            n_agg, n_limits_25, n_unpaid = compute_complex_file_metrics(df)
            show_complex_warning = should_show_complex_file_warning(n_agg, n_limits_25, n_unpaid)
        except Exception:
            pass

        # --- Build tab entries: (id, label, html_content) ---
        tab_entries = []

        # Έλεγχος για παράλληλη ασφάλιση / πολλαπλή απασχόληση (προειδοποίηση στα Σύνολα)
        warning_types = []
        try:
            parallel_df = build_parallel_print_df(df, description_map)
            if parallel_df is not None and not parallel_df.empty:
                warning_types.append("παράλληλη ασφάλιση")
        except Exception:
            pass
        try:
            parallel_2017_df = build_parallel_2017_print_df(df, description_map)
            if parallel_2017_df is not None and not parallel_2017_df.empty:
                warning_types.append("παράλληλη απασχόληση 2017+")
        except Exception:
            pass
        try:
            multi_df = build_multi_employment_print_df(df, description_map)
            if multi_df is not None and not multi_df.empty:
                warning_types.append("πολλαπλή απασχόληση")
        except Exception:
            pass

        if not display_summary.empty:
            totals_html = _build_totals_with_filters(display_summary, warning_types=warning_types)
            tab_entries.append(("totals", "Σύνολα", totals_html))

        if not final_display_df.empty:
            count_table_html = build_yearly_print_html(final_display_df, year_column='ΕΤΟΣ', style_rows=print_style_rows)
            tab_entries.append(("count", "Καταμέτρηση",
                f"<section class='print-section'><h2>Πίνακας Καταμέτρησης</h2>"
                f"<p class='print-description'>Αναλυτική καταμέτρηση ημερών ασφάλισης ανά μήνα.</p>{count_table_html}</section>"
            ))

        try:
            gaps_df = find_gaps_in_insurance_data(df)
            zero_duration_df = find_zero_duration_intervals(df)
            gaps_content_parts = []
            if gaps_df is not None and not gaps_df.empty:
                gaps_content_parts.append(build_print_section_html(
                    "Κενά Διαστήματα", gaps_df,
                    description="Χρονικές περίοδοι χωρίς ασφαλιστική κάλυψη.", heading_tag="h2"
                ))
            if zero_duration_df is not None and not zero_duration_df.empty:
                gaps_content_parts.append(build_print_section_html(
                    "Διαστήματα χωρίς ημέρες ασφάλισης", zero_duration_df,
                    description="Εγγραφές που εμφανίζονται στον ΑΤΛΑΣ αλλά χωρίς τιμές σε Έτη/Μήνες/Ημέρες.",
                    heading_tag="h2"
                ))
            if gaps_content_parts:
                tab_entries.append(("gaps", "Κενά", "".join(gaps_content_parts)))
        except Exception:
            pass

        try:
            parallel_df = build_parallel_print_df(df, description_map)
            if parallel_df is not None and not parallel_df.empty:
                par_html = build_yearly_print_html(
                    parallel_df, year_column='Έτος',
                    collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης']
                )
                tab_entries.append(("parallel", "Παράλληλη",
                    f"<section class='print-section'><h2>Παράλληλη Ασφάλιση</h2>"
                    f"<p class='print-description'>ΙΚΑ & ΟΑΕΕ / ΟΑΕΕ & ΤΣΜΕΔΕ / ΟΓΑ & ΙΚΑ/ΟΑΕΕ (έως 31/12/2016).</p>{par_html}</section>"
                ))
        except Exception:
            pass

        try:
            parallel_2017_df = build_parallel_2017_print_df(df, description_map)
            if parallel_2017_df is not None and not parallel_2017_df.empty:
                par2017_html = build_yearly_print_html(
                    parallel_2017_df, year_column='Έτος',
                    collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης']
                )
                tab_entries.append(("parallel2017", "Παράλληλη 2017+",
                    f"<section class='print-section'><h2>Παράλληλη Απασχόληση 2017+</h2>"
                    f"<p class='print-description'>Από 01/2017 (ΙΚΑ & ΕΦΚΑ μη μισθωτή / ΕΦΚΑ μισθωτή & ΕΦΚΑ μη μισθωτή).</p>{par2017_html}</section>"
                ))
        except Exception:
            pass

        try:
            multi_df = build_multi_employment_print_df(df, description_map)
            if multi_df is not None and not multi_df.empty:
                multi_html = build_yearly_print_html(
                    multi_df, year_column='Έτος',
                    collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης'],
                    bold_columns=['Εργοδότης'],
                    col_width_overrides={'Εργοδότης': '90px'},
                )
                tab_entries.append(("multi", "Πολλαπλή",
                    f"<section class='print-section'><h2>Πολλαπλή Απασχόληση</h2>"
                    f"<p class='print-description'>Μήνες με πολλαπλούς εργοδότες ΙΚΑ (αποδοχές 01, 16, ή 99).</p>{multi_html}</section>"
                ))
        except Exception:
            pass

        # Αντιστοίχιση ελέγχου -> tab id (για clickable cards)
        _check_to_tab = {
            "Κενά ασφάλισης": "gaps",
            "Ασφαλιστικά ταμεία": "totals",
            "Παράλληλη ασφάλιση": "parallel",
            "Παράλληλη απασχόληση 2017+": "parallel2017",
            "Πολλαπλή απασχόληση": "multi",
            "Ενοποιημένα διαστήματα": "count",
        }
        available_tab_ids = {tid for tid, _, _ in tab_entries}

        # Custom card generation for Synopsis (με clickable cards που ανοίγουν το σχετικό tab)
        if not audit_df.empty:
            cards_html = "<div class='audit-grid'>"
            for _, row in audit_df.iterrows():
                title = str(row.get('Έλεγχος', ''))
                result = str(row.get('Εύρημα', ''))
                details = str(row.get('Λεπτομέρειες', ''))
                actions = str(row.get('Ενέργειες', ''))
                target_tab = _check_to_tab.get(title)
                is_clickable = target_tab and target_tab in available_tab_ids
                card_attrs = ''
                if is_clickable:
                    safe_tab = html_mod.escape(target_tab)
                    card_attrs = f' class="audit-card audit-card-clickable" data-tab="{safe_tab}" onclick="showTab(\'{safe_tab}\');return false;" onkeydown="if(event.key===\'Enter\'){{showTab(\'{safe_tab}\');return false;}}" role="button" tabindex="0"'
                else:
                    card_attrs = ' class="audit-card"'
                action_html = ""
                if actions and actions != '-':
                    action_html = f"<div class='audit-card-actions'>{actions}</div>"
                cards_html += f"""
                <div{card_attrs}>
                    <div class='audit-card-header'>
                        <span>{html_mod.escape(title)}</span>
                    </div>
                    <div class='audit-card-result'>{html_mod.escape(result)}</div>
                    <div class='audit-card-details'>{details}</div>
                    {action_html}
                </div>
                """
            cards_html += "</div>"
            synopsis_html = f"<section class='print-section'><h2>Σύνοψη</h2><p class='print-description'>Βασικοί έλεγχοι δεδομένων.</p>{cards_html}</section>"
        else:
            synopsis_html = "<p>Δεν βρέθηκαν στοιχεία.</p>"

        tab_entries.insert(0, ("synopsis", "Σύνοψη", synopsis_html))

        try:
            timeline_html = _build_timeline_html(df)
            if timeline_html:
                tab_entries.insert(1, ("timeline", "Χρονοδιάγραμμα", timeline_html))
        except Exception:
            pass

        if show_complex_warning:
            tab_entries = [(tid, label, COMPLEX_FILE_WARNING_HTML + content) for tid, label, content in tab_entries]

        return audit_df, display_summary, final_display_df, print_style_rows, tab_entries

    if do_open:
        with st.spinner("Φόρτωση αναφοράς..."):
            audit_df, display_summary, final_display_df, print_style_rows, tab_entries = _build_report_block()
    else:
        audit_df, display_summary, final_display_df, print_style_rows, tab_entries = _build_report_block()

    # --- Sidebar nav items ---
    nav_items = "\n".join(
        f'<a href="#" class="nav-item{" active" if i == 0 else ""}" data-tab="{tid}" onclick="showTab(\'{tid}\');return false;">{html_mod.escape(label)}</a>'
        for i, (tid, label, _) in enumerate(tab_entries)
    )

    # --- Tab panes (με σημείωση εξαίρεσης πάνω δεξιά σε κάθε tab) ---
    tab_panes = "\n".join(
        f'<div id="pane-{tid}" class="tab-pane{" active" if i == 0 else ""}">{LITE_EXCLUSION_NOTE}{content}</div>'
        for i, (tid, _, content) in enumerate(tab_entries)
    )

    # --- All sections for print (no tabs) ---
    # Στην εκτύπωση: Σύνοψη πίνακας, Σύνολα χωρίς φίλτρα, υπόλοιπα από tabs
    synopsis_print = build_print_section_html(
        "Σύνοψη", audit_df, description="Βασικοί έλεγχοι δεδομένων.", wrap_cells=True, heading_tag="h2"
    )
    totals_print = ""
    if not display_summary.empty:
        totals_print = build_print_section_html(
            "Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)", display_summary,
            description="Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης και Ταμείο.", heading_tag="h2"
        )
    rest_for_print = [LITE_EXCLUSION_NOTE + content for (tid, _, content) in tab_entries[1:] if tid != "totals"]
    all_sections_print = LITE_EXCLUSION_NOTE + synopsis_print
    if totals_print:
        all_sections_print += "\n<div class='page-break'></div>\n" + LITE_EXCLUSION_NOTE + totals_print
    if rest_for_print:
        all_sections_print += "\n<div class='page-break'></div>\n" + "\n<div class='page-break'></div>\n".join(rest_for_print)

    safe_name = html_mod.escape(client_name.strip()) if client_name.strip() else ""
    name_block = f'<div class="header-name">{safe_name}</div>' if safe_name else ""
    disclaimer = get_print_disclaimer_html()

    # --- Clean print HTML (all sections, no sidebar, compact) ---
    print_name = f"<div class='prt-name'>{safe_name}</div>" if safe_name else ""
    print_html = f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="utf-8">
<title>ATLAS Lite - Εκτύπωση</title>
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
@media print {{ @page {{ size: A4 landscape; margin: 8mm; }} }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: "Fira Sans", sans-serif; color: #222; margin: 0; padding: 12px 16px; font-size: 11px; line-height: 1.4; background: #ffffff; }}
.prt-name {{ text-align: center; font-size: 18px; font-weight: 800; margin-bottom: 2px; }}
.prt-title {{ text-align: center; font-size: 14px; font-weight: 600; color: #555; margin-bottom: 14px; }}
.page-break {{ page-break-after: always; }}
.print-section {{ margin-bottom: 16px; }}
.print-section h2 {{ font-size: 13px; font-weight: 700; color: #111; margin: 0 0 4px 0; padding-bottom: 3px; border-bottom: 1.5px solid #333; }}
.print-description {{ font-size: 10px; color: #666; font-style: italic; margin: 0 0 6px 0; }}
table.print-table {{ border-collapse: collapse; width: 100%; font-size: 10px; table-layout: fixed; }}
table.print-table thead th {{
  background: #f3f4f6; border-bottom: 1px solid #bbb; padding: 3px 3px;
  text-align: left; font-weight: 700; font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
table.print-table tbody td {{
  border-bottom: 0.5px solid #ddd; padding: 2px 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
table.print-table tbody tr:nth-child(even) td {{ background: #fafafa; }}
table.print-table tbody td:first-child {{ font-weight: 700; }}
table.print-table tbody tr.total-row td {{ background: #dbeafe !important; font-weight: 700 !important; border-top: 1px solid #93c5fd; }}
table.print-table.wrap-cells thead th, table.print-table.wrap-cells tbody td {{ white-space: normal; word-break: break-word; }}
.year-section {{ margin-bottom: 10px; }}
.year-heading {{ font-size: 12px; font-weight: 800; padding: 4px 0 2px 0; border-bottom: 1.5px solid #6f42c1; margin-bottom: 3px; }}
.print-disclaimer {{ font-size: 9px; color: #888; margin-top: 16px; padding-top: 8px; border-top: 1px solid #ddd; line-height: 1.4; }}
.print-disclaimer strong {{ color: #444; }}
.lite-exclusion-note {{ text-align: right; font-size: 9px; color: #64748b; font-style: italic; margin-bottom: 4px; }}
.tl-container {{ position: relative; padding-bottom: 28px; }}
.tl-row {{ display: flex; align-items: center; margin-bottom: 4px; min-height: 16px; }}
.tl-label {{ width: 140px; min-width: 140px; font-size: 8px; font-weight: 600; color: #334155; text-align: right; padding-right: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.tl-label-gap {{ color: #dc2626; }}
.tl-track {{ position: relative; flex: 1; height: 14px; background: #f1f5f9; border-radius: 3px; }}
.tl-bar {{ position: absolute; top: 1px; height: 12px; border-radius: 2px; opacity: 0.85; }}
.tl-bar:hover {{ opacity: 1; box-shadow: 0 0 4px rgba(0,0,0,0.3); z-index: 2; }}
.tl-gap {{ background: repeating-linear-gradient(45deg, #fca5a5, #fca5a5 2px, #fecaca 2px, #fecaca 4px) !important; border: 1px solid #ef4444; opacity: 0.7; }}
.tl-axis {{ position: relative; height: 20px; margin-left: 148px; margin-top: 2px; border-top: 1px solid #cbd5e1; }}
.tl-tick {{ position: absolute; top: 2px; font-size: 7px; color: #64748b; transform: translateX(-50%); }}
.tl-tick::before {{ content: ''; position: absolute; top: -4px; left: 50%; width: 1px; height: 4px; background: #cbd5e1; }}
.tl-legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; font-size: 8px; }}
.tl-legend-item {{ display: inline-flex; align-items: center; gap: 3px; color: #334155; }}
.tl-legend-dot {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}
</style>
</head>
<body onload="window.print();">
{print_name}
<div class="prt-title">Ασφαλιστικό Βιογραφικό ATLAS</div>
{all_sections_print}
{disclaimer}
<div style="margin-top:12px;font-size:9px;color:#888;text-align:left;">© Syntaksi Pro - my advisor</div>
</body>
</html>"""

    # Escape print HTML for embedding in JS
    print_js = json.dumps(print_html).replace("</script>", "<\\/script>")
    dl_safe = re.sub(r'[<>:"/\\|?*]', '', (client_value or "Αναφορά").strip())[:60].strip() or "Αναφορά"
    download_filename_js = json.dumps(f"ATLAS_Lite_{dl_safe}.html")

    # --- Interactive viewer HTML (sidebar + tabs) ---
    html_doc = f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ATLAS Lite - Αναφορά</title>
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: "Fira Sans", -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #1e293b; background: #ffffff; }}
.app-layout {{ display: flex; min-height: 100vh; }}
.sidebar {{
  width: 220px; min-width: 220px; background: #1e293b; color: #e2e8f0;
  display: flex; flex-direction: column; position: fixed; top: 0; left: 0; bottom: 0; z-index: 10;
}}
.sidebar-header {{ padding: 20px 16px 12px; border-bottom: 1px solid #334155; font-size: 18px; font-weight: 800; color: #fff; text-align: center; }}
.sidebar-header small {{ display: block; font-size: 11px; font-weight: 400; color: #94a3b8; margin-top: 2px; }}
.sidebar-nav {{ flex: 1; padding: 8px 0; overflow-y: auto; }}
.nav-item {{
  display: block; padding: 10px 20px; color: #cbd5e1; text-decoration: none;
  font-size: 14px; font-weight: 600; border-left: 3px solid transparent; transition: all .15s;
}}
.nav-item:hover {{ background: #334155; color: #fff; }}
.nav-item.active {{ background: #334155; color: #fff; border-left-color: #6366f1; }}
.sidebar-footer {{ padding: 12px 16px; border-top: 1px solid #334155; display: flex; flex-direction: column; gap: 8px; }}
.sidebar-footer-copyright {{ margin-top: auto; padding-top: 12px; font-size: 11px; color: #94a3b8; text-align: left; }}
.btn-action {{
  width: 100%; border: none; padding: 10px 0; border-radius: 6px;
  font-size: 14px; font-weight: 700; cursor: pointer; transition: background .15s;
}}
.btn-save {{ background: #2563eb; color: white; }}
.btn-save:hover {{ background: #1d4ed8; }}
.btn-print {{ background: #dc3545; color: white; }}
.btn-print:hover {{ background: #b91c1c; }}
.main-content {{ margin-left: 220px; flex: 1; padding: 24px 32px; min-width: 0; }}
.header-name {{ font-size: 22px; font-weight: 800; color: #111827; margin-bottom: 4px; }}
.main-title {{ font-size: 15px; color: #64748b; font-weight: 600; margin-bottom: 20px; }}
.tab-pane {{ display: none; }}
.tab-pane.active {{ display: block; position: relative; }}
.lite-exclusion-note {{ text-align: right; font-size: 11px; color: #64748b; font-style: italic; margin-bottom: 8px; }}

/* Cards CSS */
.audit-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.audit-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); display: flex; flex-direction: column; }}
.audit-card-clickable {{ cursor: pointer; transition: box-shadow 0.2s, border-color 0.2s; }}
.audit-card-clickable:hover {{ box-shadow: 0 4px 12px rgba(99,102,241,0.2); border-color: #6366f1; }}
.audit-card-clickable:focus {{ outline: 2px solid #6366f1; outline-offset: 2px; }}
.audit-card-header {{ font-size: 14px; font-weight: 700; color: #334155; margin-bottom: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }}
.audit-card-result {{ font-size: 16px; font-weight: 600; color: #0f172a; margin-bottom: 8px; }}
.audit-card-details {{ font-size: 13px; color: #64748b; line-height: 1.5; flex: 1; }}
.audit-card-actions {{ margin-top: 12px; padding-top: 8px; border-top: 1px dashed #e2e8f0; font-size: 12px; color: #ef4444; font-weight: 600; }}
.print-section {{ margin-bottom: 24px; }}
.print-section h2 {{ font-size: 18px; font-weight: 700; color: #1e293b; margin: 0 0 8px 0; padding-bottom: 6px; border-bottom: 2px solid #6366f1; }}
.print-description {{ font-size: 13px; color: #64748b; font-style: italic; margin: 0 0 12px 0; }}
table.print-table {{
  border-collapse: collapse; width: 100%; font-size: 13px; table-layout: auto; background: #fff;
  border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
table.print-table thead th {{
  background: #f8fafc; border-bottom: 2px solid #e2e8f0; padding: 10px 12px;
  text-align: left; font-weight: 700; color: #334155; font-size: 12px; white-space: nowrap;
}}
table.print-table tbody td {{ border-bottom: 1px solid #f1f5f9; padding: 8px 12px; color: #475569; }}
table.print-table tbody tr:hover td {{ background: #f8fafc; }}
table.print-table tbody td:first-child {{ font-weight: 700; color: #1e293b; }}
table.print-table tbody tr.total-row td {{ background: #dbeafe !important; color: #1e293b; font-weight: 700 !important; border-top: 1px solid #93c5fd; }}
table.print-table.wrap-cells thead th, table.print-table.wrap-cells tbody td {{ white-space: normal; word-break: break-word; }}
.year-section {{ margin-bottom: 20px; }}
.year-heading {{ font-size: 15px; font-weight: 800; color: #1e293b; padding: 8px 0 4px 0; border-bottom: 2px solid #6366f1; margin-bottom: 6px; }}
.print-disclaimer {{ font-size: 12px; color: #64748b; margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; line-height: 1.6; }}
.print-disclaimer strong {{ color: #374151; }}

/* Timeline */
.tl-container {{ position: relative; padding-bottom: 36px; }}
.tl-row {{ display: flex; align-items: center; margin-bottom: 8px; min-height: 28px; }}
.tl-label {{ width: 200px; min-width: 200px; font-size: 13px; font-weight: 600; color: #334155; text-align: right; padding-right: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.tl-label-gap {{ color: #dc2626; }}
.tl-track {{ position: relative; flex: 1; height: 24px; background: #f1f5f9; border-radius: 6px; }}
.tl-bar {{ position: absolute; top: 2px; height: 20px; border-radius: 4px; opacity: 0.85; cursor: default; transition: opacity 0.15s; }}
.tl-bar:hover {{ opacity: 1; box-shadow: 0 0 6px rgba(0,0,0,0.25); z-index: 2; }}
.tl-gap {{ background: repeating-linear-gradient(45deg, #fca5a5, #fca5a5 3px, #fecaca 3px, #fecaca 6px) !important; border: 1px solid #ef4444; opacity: 0.7; }}
.tl-axis {{ position: relative; height: 28px; margin-left: 214px; margin-top: 4px; border-top: 1px solid #cbd5e1; }}
.tl-tick {{ position: absolute; top: 4px; font-size: 11px; color: #64748b; transform: translateX(-50%); }}
.tl-tick::before {{ content: ''; position: absolute; top: -6px; left: 50%; width: 1px; height: 6px; background: #cbd5e1; }}
.tl-legend {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; font-size: 13px; }}
.tl-legend-item {{ display: inline-flex; align-items: center; gap: 6px; color: #334155; }}
.tl-legend-dot {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}

/* Totals info bar + summary */
.totals-info-bar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 24px; margin-bottom: 20px; padding: 16px 20px; background: #dbeafe; border-radius: 8px; border: 1px solid #93c5fd; }}
.totals-info-bar-warning {{ background: #fef3c7; border-color: #f59e0b; }}
.totals-info-bar-warning .totals-info-msg {{ color: #b45309; }}
.totals-info-msg {{ font-size: 16px; font-weight: 600; color: #1e40af; flex: 1; min-width: 200px; }}
.totals-summary {{ display: flex; gap: 24px; flex-wrap: wrap; }}
.totals-summary-item {{ display: flex; flex-direction: column; gap: 4px; }}
.totals-summary-label {{ font-size: 13px; font-weight: 600; color: #475569; }}
.totals-summary-value {{ font-size: 22px; font-weight: 800; color: #1e293b; }}

/* Totals filters */
.totals-filters {{ display: flex; flex-wrap: wrap; gap: 20px 28px; margin-bottom: 20px; padding: 16px 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }}
.totals-filters .filter-group {{ display: flex; flex-direction: column; gap: 10px; }}
.totals-filters .filter-label {{ font-size: 16px; font-weight: 700; color: #1e293b; }}
.totals-filters .filter-options {{ display: flex; flex-wrap: wrap; gap: 12px 16px; max-height: 160px; overflow-y: auto; }}
.totals-filters .filter-cb {{ display: flex; align-items: center; gap: 10px; font-size: 16px; color: #334155; cursor: pointer; white-space: nowrap; line-height: 1.4; }}
.totals-filters .filter-cb input[type="checkbox"] {{ width: 20px; height: 20px; min-width: 20px; min-height: 20px; cursor: pointer; accent-color: #6366f1; }}
.totals-filters .filter-date {{ padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; }}
@media print {{ .totals-filters {{ display: none !important; }} .totals-info-bar {{ display: none !important; }} .lite-exclusion-note {{ font-size: 9px; margin-bottom: 4px; }} }}

/* Copyable values */
.copy-target {{ cursor: pointer; position: relative; transition: background-color 0.15s; }}
.copy-target:hover {{ background-color: rgba(99, 102, 241, 0.15) !important; }}
.copy-target:active {{ background-color: rgba(99, 102, 241, 0.25) !important; }}

  /* Toast notification */
  #toast-container {{
    position: fixed; bottom: 20px; right: 20px; z-index: 9999;
    pointer-events: none;
  }}
  .toast {{
    background: #1e293b; color: #fff; padding: 10px 16px; border-radius: 8px;
    margin-top: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    font-size: 15px; font-weight: 600; opacity: 0; transform: translateY(10px);
    transition: opacity 0.3s, transform 0.3s;
  }}
.toast.show {{ opacity: 1; transform: translateY(0); }}
</style>
</head>
<body>
<div class="app-layout">
  <nav class="sidebar">
    <div class="sidebar-header">ATLAS lite<small>Αναφορά</small></div>
    <div class="sidebar-nav">{nav_items}</div>
    <div class="sidebar-footer">
      <button type="button" class="btn-action btn-save" onclick="downloadFullHtml();">Πλήρης Αποθήκευση</button>
      <button type="button" class="btn-action btn-print" onclick="openPrint();">Εκτύπωση</button>
      <div class="sidebar-footer-copyright">© Syntaksi Pro - my advisor</div>
    </div>
  </nav>
  <main class="main-content">
    {name_block}
    <div class="main-title">Ασφαλιστικό Βιογραφικό</div>
    {tab_panes}
    {disclaimer}
  </main>
</div>
<div id="toast-container"></div>
<script>
function showTab(tabId) {{
  document.querySelectorAll('.tab-pane').forEach(function(p) {{ p.classList.remove('active'); }});
  document.querySelectorAll('.nav-item').forEach(function(a) {{ a.classList.remove('active'); }});
  var pane = document.getElementById('pane-' + tabId);
  var link = document.querySelector('.nav-item[data-tab="' + tabId + '"]');
  if (pane) pane.classList.add('active');
  if (link) link.classList.add('active');
}}
var _printHtml = {print_js};
var _downloadFilename = {download_filename_js};
function openPrint() {{
  var blob = new Blob([_printHtml], {{ type: 'text/html;charset=utf-8' }});
  var url = URL.createObjectURL(blob);
  window.open(url, '_blank');
}}
function downloadFullHtml() {{
  var html = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
  var blob = new Blob([html], {{ type: 'text/html;charset=utf-8' }});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = _downloadFilename;
  a.click();
  URL.revokeObjectURL(a.href);
}}

// Copy to clipboard logic
function showToast(message) {{
  var container = document.getElementById('toast-container');
  var toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);
  
  // Trigger reflow
  void toast.offsetWidth;
  toast.classList.add('show');
  
  setTimeout(function() {{
    toast.classList.remove('show');
    setTimeout(function() {{
      if (container.contains(toast)) container.removeChild(toast);
    }}, 300);
  }}, 2000);
}}

document.addEventListener('click', function(e) {{
  var target = e.target.closest('.copy-target');
  if (target) {{
    var text = target.innerText.trim();
    if (text && text !== '-' && text !== '') {{
      navigator.clipboard.writeText(text).then(function() {{
        showToast('Αντιγράφηκε: ' + text);
      }}).catch(function(err) {{
        console.error('Could not copy text: ', err);
      }});
    }}
  }}
}});

// Add copy-target class to relevant elements
document.addEventListener('DOMContentLoaded', function() {{
  // 1. Στήλες πινάκων που θέλουμε να είναι clickable
  // Μπορείτε να προσθέσετε ή να αφαιρέσετε ονόματα στηλών εδώ
  var targetColumns = [
    'Συνολικές ημέρες',
    'Μικτές αποδοχές',
    'Συνολικές εισφορές',
    'ΣΥΝΟΛΟ',
    'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ',
    'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ',
    'Ημέρες Ασφ.',
    'Σύνολο',
    'Μικτές Αποδοχές',
    'Συνολικές Εισφορές'
  ];

  var tables = document.querySelectorAll('table.print-table');
  tables.forEach(function(table) {{
    var headers = table.querySelectorAll('thead th');
    var targetIndices = [];
    
    headers.forEach(function(th, index) {{
      var headerText = th.textContent.trim();
      // Έλεγχος αν το όνομα της στήλης περιέχει κάποιο από τα targetColumns
      if (targetColumns.some(function(col) {{ return headerText.indexOf(col) !== -1; }})) {{
        targetIndices.push(index);
      }}
    }});

    if (targetIndices.length > 0) {{
      var rows = table.querySelectorAll('tbody tr');
      rows.forEach(function(row) {{
        var cells = row.querySelectorAll('td');
        targetIndices.forEach(function(index) {{
          if (cells[index]) {{
            cells[index].classList.add('copy-target');
            cells[index].title = 'Κλικ για αντιγραφή';
          }}
        }});
      }});
    }}
  }});

  // 2. Στοιχεία καρτών σύνοψης (προαιρετικά - αφαιρέστε αν δεν τα θέλετε)
  var cardElements = document.querySelectorAll('.audit-card-result');
  cardElements.forEach(function(el) {{
    el.classList.add('copy-target');
    el.title = 'Κλικ για αντιγραφή';
  }});
}});
</script>
</body>
</html>"""

    # --- Ανοίγουμε viewer ή print μόνο μετά από disclaimer (lite_do_open) ---
    do_open = st.session_state.get("lite_do_open")
    if do_open == "viewer":
        js_content = json.dumps(html_doc).replace("</script>", "<\\/script>")
        open_viewer_snippet = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
(function() {{
  var htmlContent = {js_content};
  var blob = new Blob([htmlContent], {{ type: 'text/html;charset=utf-8' }});
  var url = URL.createObjectURL(blob);
  window.open(url, '_blank');
}})();
</script><p style="margin:0;font-size:14px;color:#666;">Άνοιγμα Προβολής Ανάλυσης...</p></body></html>"""
        components.html(open_viewer_snippet, height=40)
        st.session_state["lite_do_open"] = None
    elif do_open == "print":
        open_print_snippet = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
(function() {{
  var htmlContent = {print_js};
  var blob = new Blob([htmlContent], {{ type: 'text/html;charset=utf-8' }});
  var url = URL.createObjectURL(blob);
  window.open(url, '_blank');
}})();
</script><p style="margin:0;font-size:14px;color:#666;">Άνοιγμα εκτυπώσιμης μορφής...</p></body></html>"""
        components.html(open_print_snippet, height=40)
        st.session_state["lite_do_open"] = None

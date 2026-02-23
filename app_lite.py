#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
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
    build_parallel_print_df,
    build_parallel_2017_print_df,
    build_multi_employment_print_df,
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
                © 2026 Χαράλαμπος Ματωνάκης - myadvisor 
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

if "lite_show_disclaimer" not in st.session_state:
    st.session_state["lite_show_disclaimer"] = False

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
                try:
                    st.query_params["section"] = "all"
                    if client_value:
                        st.query_params["client"] = client_value
                except Exception:
                    st.experimental_set_query_params(section="all", client=client_value)
                st.session_state["lite_show_disclaimer"] = False
                st.rerun()
        _dlg()
    except Exception:
        st.warning(disclaimer_text)
        if st.button("Αποδοχή-Προβολή", type="primary"):
            try:
                st.query_params["section"] = "all"
                if client_value:
                    st.query_params["client"] = client_value
            except Exception:
                st.experimental_set_query_params(section="all", client=client_value)
            st.session_state["lite_show_disclaimer"] = False
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

    # 2. Buttons Row inside the centered column
    b_col1, b_col2 = st.columns([1.5, 1], gap="small")
    
    with b_col1:
        if st.button("Προβολή επεξεργασίας", type="primary", use_container_width=True):
             st.session_state["lite_show_disclaimer"] = True
    
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
excluded_packages = {"Α", "Λ", "Υ", "Ο", "Χ", "899"}
if 'Κλάδος/Πακέτο Κάλυψης' in df.columns:
    pkg_series = df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
    count_df = df[~pkg_series.isin(excluded_packages)].copy()
else:
    count_df = df.copy()

# --- FULL WIDTH REPORT OUTPUT ---
if section == "all":
    audit_df = generate_audit_report(df)
    display_summary = build_summary_grouped_display(df, df) if 'Κλάδος/Πακέτο Κάλυψης' in df.columns else pd.DataFrame()
    final_display_df, _, _, _, print_style_rows = build_count_report(
        count_df,
        description_map=description_map,
        show_count_totals_only=False
    )

    sections = []
    sections.append(
        build_print_section_html(
            "Σύνοψη",
            audit_df,
            description="Βασικοί έλεγχοι δεδομένων.",
            wrap_cells=True,
            heading_tag="h2"
        )
    )
    sections.append("<div class='page-break'></div>")
    if not display_summary.empty:
        sections.append(
            build_print_section_html(
                "Συνοπτική Αναφορά",
                display_summary,
                description="Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης και Ταμείο.",
                heading_tag="h2"
            )
        )
    else:
        sections.append("<section class='print-section'><h2>Συνοπτική Αναφορά</h2><p class='print-description'>Δεν βρέθηκαν δεδομένα.</p></section>")
    sections.append("<div class='page-break'></div>")
    if not final_display_df.empty:
        count_table_html = build_yearly_print_html(
            final_display_df,
            year_column='ΕΤΟΣ',
            style_rows=print_style_rows,
        )
        sections.append(
            f"<section class='print-section'>"
            f"<h2>Πίνακας Καταμέτρησης</h2>"
            f"<p class='print-description'>Αναλυτική καταμέτρηση ημερών ασφάλισης ανά μήνα.</p>"
            f"{count_table_html}"
            f"</section>"
        )
    else:
        sections.append("<section class='print-section'><h2>Πίνακας Καταμέτρησης</h2><p class='print-description'>Δεν βρέθηκαν δεδομένα.</p></section>")

    # --- Κενά Διαστήματα ---
    sections.append("<div class='page-break'></div>")
    try:
        gaps_df = find_gaps_in_insurance_data(df)
        if gaps_df is not None and not gaps_df.empty:
            sections.append(
                build_print_section_html(
                    "Κενά Διαστήματα",
                    gaps_df,
                    description="Χρονικές περίοδοι όπου δεν βρέθηκε ασφαλιστική κάλυψη μεταξύ των δηλωμένων εγγραφών.",
                    heading_tag="h2"
                )
            )
        else:
            sections.append("<section class='print-section'><h2>Κενά Διαστήματα</h2><p class='print-description'>Δεν εντοπίστηκαν κενά.</p></section>")
    except Exception:
        sections.append("<section class='print-section'><h2>Κενά Διαστήματα</h2><p class='print-description'>Δεν ήταν δυνατός ο υπολογισμός.</p></section>")

    # --- Παράλληλη Ασφάλιση ---
    sections.append("<div class='page-break'></div>")
    try:
        parallel_df = build_parallel_print_df(df, description_map)
        if parallel_df is not None and not parallel_df.empty:
            par_html = build_yearly_print_html(parallel_df, year_column='Έτος')
            sections.append(
                f"<section class='print-section'>"
                f"<h2>Παράλληλη Ασφάλιση</h2>"
                f"<p class='print-description'>Διαστήματα παράλληλης ασφάλισης (ΙΚΑ & ΟΑΕΕ / ΟΑΕΕ & ΤΣΜΕΔΕ / ΟΓΑ & ΙΚΑ/ΟΑΕΕ, έως 31/12/2016).</p>"
                f"{par_html}"
                f"</section>"
            )
        else:
            sections.append("<section class='print-section'><h2>Παράλληλη Ασφάλιση</h2><p class='print-description'>Δεν εντοπίστηκαν διαστήματα παράλληλης ασφάλισης.</p></section>")
    except Exception:
        sections.append("<section class='print-section'><h2>Παράλληλη Ασφάλιση</h2><p class='print-description'>Δεν ήταν δυνατός ο υπολογισμός.</p></section>")

    # --- Παράλληλη Απασχόληση 2017+ ---
    sections.append("<div class='page-break'></div>")
    try:
        parallel_2017_df = build_parallel_2017_print_df(df, description_map)
        if parallel_2017_df is not None and not parallel_2017_df.empty:
            par2017_html = build_yearly_print_html(parallel_2017_df, year_column='Έτος')
            sections.append(
                f"<section class='print-section'>"
                f"<h2>Παράλληλη Απασχόληση 2017+</h2>"
                f"<p class='print-description'>Διαστήματα παράλληλης απασχόλησης από 01/2017 (ΙΚΑ & ΕΦΚΑ μη μισθωτή / ΕΦΚΑ μισθωτή & ΕΦΚΑ μη μισθωτή).</p>"
                f"{par2017_html}"
                f"</section>"
            )
        else:
            sections.append("<section class='print-section'><h2>Παράλληλη Απασχόληση 2017+</h2><p class='print-description'>Δεν εντοπίστηκαν διαστήματα.</p></section>")
    except Exception:
        sections.append("<section class='print-section'><h2>Παράλληλη Απασχόληση 2017+</h2><p class='print-description'>Δεν ήταν δυνατός ο υπολογισμός.</p></section>")

    # --- Πολλαπλή Απασχόληση ---
    sections.append("<div class='page-break'></div>")
    try:
        multi_df = build_multi_employment_print_df(df, description_map)
        if multi_df is not None and not multi_df.empty:
            multi_html = build_yearly_print_html(
                multi_df, year_column='Έτος',
                extra_group_cols=['Ταμείο', 'Τύπος Ασφάλισης'],
                bold_columns=['Εργοδότης'],
                col_width_overrides={'Εργοδότης': '90px'},
            )
            sections.append(
                f"<section class='print-section'>"
                f"<h2>Πολλαπλή Απασχόληση</h2>"
                f"<p class='print-description'>Μήνες με πολλαπλούς εργοδότες ΙΚΑ (αποδοχές 01, 16, ή 99).</p>"
                f"{multi_html}"
                f"</section>"
            )
        else:
            sections.append("<section class='print-section'><h2>Πολλαπλή Απασχόληση</h2><p class='print-description'>Δεν εντοπίστηκαν μήνες πολλαπλής απασχόλησης.</p></section>")
    except Exception:
        sections.append("<section class='print-section'><h2>Πολλαπλή Απασχόληση</h2><p class='print-description'>Δεν ήταν δυνατός ο υπολογισμός.</p></section>")

    client_name_html = f"<div class='print-client-name'>{client_name.strip()}</div>" if client_name.strip() else ""
    body_html = (
        f"{client_name_html}"
        f"<h1>Συνολική Εκτύπωση</h1>"
        f"{''.join(sections)}"
        f"{get_print_disclaimer_html()}"
    )
    html_doc = wrap_print_html("Συνολική Εκτύπωση", body_html, auto_print=True)
    html_doc += f"\n<!-- nonce: {uuid.uuid4()} -->"
    with st.expander("Ενοποιημένη προβολή εκτύπωσης", expanded=False):
        components.html(html_doc, height=900, scrolling=True)

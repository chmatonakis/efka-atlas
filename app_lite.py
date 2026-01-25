#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import uuid
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

os.environ.setdefault("ATLAS_LITE", "1")

from app_final import (
    extract_efka_data,
    build_print_html,
    build_print_section_html,
    wrap_print_html,
    get_print_disclaimer_html,
    build_summary_grouped_display,
    build_count_report,
    generate_audit_report,
    build_description_map,
    get_last_update_date,
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
    .stApp {
        background-color: #f8f9fa;
    }
    
    html, body, [data-testid="stAppViewContainer"], .block-container {
        font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
        font-size: 17px;
    }

    /* Primary Action Button (Red) - Προβολή επεξεργασίας */
    div.stButton > button[kind="primary"] {
        background-color: #ee1d23 !important;
        color: white !important;
        border: 1px solid #ee1d23 !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        padding: 0.6rem 2rem !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        border-radius: 8px !important;
        width: 100%;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #cc181e !important;
        border-color: #cc181e !important;
        color: white !important;
        box-shadow: 0 6px 8px rgba(0,0,0,0.15) !important;
        transform: translateY(-1px);
    }
    
    /* Secondary Action Button (White) - Νέο αρχείο */
    div.stButton > button[kind="secondary"] {
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        padding: 0.6rem 2rem !important;
        border-radius: 8px !important;
        width: 100%;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: #f1f1f1 !important;
        border-color: #ccc !important;
        color: #000 !important;
    }
    
    /* Purple Header Full Width */
    .purple-header {
        background: linear-gradient(135deg, #7b2cbf 0%, #5a189a 100%);
        color: white;
        text-align: center;
        padding: 2rem 1rem;
        margin: -4rem -5rem 2rem -5rem; /* Negative margins to span full width in wide mode */
        font-size: 2rem;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Initial Upload Styles */
    .upload-section {
        background-color: transparent;
        padding: 1.5rem 1rem;
        border-radius: 10px;
        border: 0;
        text-align: center;
        margin: 1rem 0 2rem 0;
    }
    [data-testid="stFileUploader"] {
        background-color: #f8fbff;
        padding: 3rem;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 2px dashed #3b82f6;
        max-width: 800px;
        margin: 0 auto;
    }
    .upload-prompt-text {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1rem;
        text-align: center !important;
        width: 100%;
        display: block;
    }
    .efka-btn-wrapper {
        text-align: center;
        margin: 2rem 0;
    }
    .efka-btn {
        display: inline-block;
        background-color: transparent;
        color: #0056b3 !important;
        border: 2px solid #0056b3;
        padding: 0.6rem 1.5rem;
        border-radius: 50px;
        text-decoration: none !important;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.2s ease;
    }
    .efka-btn:hover {
        background-color: #eef6fc;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 86, 179, 0.1);
    }
    .instructions-box {
        max-width: 800px;
        margin: 0 auto 4rem auto;
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 12px;
        padding: 3rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    }
    .instructions-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 2rem;
        text-align: center;
        border-bottom: 2px solid #f0f2f5;
        padding-bottom: 1rem;
    }
    .instructions-list {
        text-align: left;
        color: #4a5568;
        font-size: 1.1rem;
        line-height: 1.8;
    }
    .main-footer {
        margin-top: 5rem;
        padding: 3rem 1rem;
        background-color: #f8f9fa;
        border-top: 1px solid #e1e4e8;
        text-align: center;
        color: #6c757d;
        margin-left: -5rem;
        margin-right: -5rem;
        margin-bottom: -5rem;
    }
    .footer-disclaimer {
        font-size: 0.85rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
        line-height: 1.6;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    .footer-copyright {
        font-weight: 600;
        color: #2c3e50;
        font-size: 0.95rem;
    }
</style>
""",
    unsafe_allow_html=True
)

CACHE_DIR = Path(__file__).parent / ".lite_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LAST_TOKEN_FILE = CACHE_DIR / "last_token.txt"

def save_cached_df(token: str, df: pd.DataFrame) -> None:
    try:
        df.to_pickle(CACHE_DIR / f"{token}.pkl")
    except Exception:
        pass

def load_cached_df(token: str) -> pd.DataFrame | None:
    try:
        cache_path = CACHE_DIR / f"{token}.pkl"
        if cache_path.exists():
            return pd.read_pickle(cache_path)
    except Exception:
        return None
    return None

def save_last_token(token: str) -> None:
    try:
        LAST_TOKEN_FILE.write_text(token, encoding="utf-8")
    except Exception:
        pass

def load_last_token() -> str:
    try:
        if LAST_TOKEN_FILE.exists():
            return LAST_TOKEN_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    return ""

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
token = get_query_param("token").strip()
client_name_param = get_query_param("client").strip()
last_token = load_last_token()

if "lite_file_uploaded" not in st.session_state:
    st.session_state["lite_file_uploaded"] = False
if "lite_processing_done" not in st.session_state:
    st.session_state["lite_processing_done"] = False

if token and st.session_state.get("lite_df") is None:
    cached_df = load_cached_df(token)
    if isinstance(cached_df, pd.DataFrame) and not cached_df.empty:
        st.session_state["lite_df"] = cached_df
        st.session_state["lite_token"] = token
        st.session_state["lite_file_uploaded"] = True
        st.session_state["lite_processing_done"] = True
        if client_name_param and not st.session_state.get("lite_client_name"):
            st.session_state["lite_client_name"] = client_name_param

if not token and st.session_state.get("lite_df") is None and last_token:
    cached_df = load_cached_df(last_token)
    if isinstance(cached_df, pd.DataFrame) and not cached_df.empty:
        try:
            st.query_params["section"] = section
            st.query_params["token"] = last_token
        except Exception:
            st.experimental_set_query_params(section=section, token=last_token)
        st.rerun()

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
    st.markdown('''
        <div class="efka-btn-wrapper">
            <a href="https://www.e-efka.gov.gr/el/elektronikes-yperesies/synoptiko-kai-analytiko-istoriko-asphalises" target="_blank" class="efka-btn">
                Κατεβάστε το αρχείο ΑΤΛΑΣ
            </a>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown('<div class="upload-prompt-text">Στη συνέχεια ανεβάστε το αρχείο εδώ για ανάλυση</div>', unsafe_allow_html=True)

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
                1. Μεταβείτε στην υπηρεσία του e-ΕΦΚΑ πατώντας το μπλε κουμπί παραπάνω.<br>
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
                © 2025 Χαράλαμπος Ματωνάκης - myadvisor 
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
        new_token = uuid.uuid4().hex
        st.session_state["lite_token"] = new_token
        save_cached_df(new_token, st.session_state["lite_df"])
        save_last_token(new_token)
        try:
            st.query_params["token"] = new_token
        except Exception:
            st.experimental_set_query_params(token=new_token)
        st.rerun()

df = st.session_state.get("lite_df")
if df is None or df.empty:
    if token:
        st.warning("Δεν βρέθηκαν αποθηκευμένα δεδομένα για το link. Παρακαλώ ανεβάστε ξανά το αρχείο.")
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
                    st.query_params["token"] = link_token
                    if client_value:
                        st.query_params["client"] = client_value
                except Exception:
                    st.experimental_set_query_params(section="all", token=link_token, client=client_value)
                st.session_state["lite_show_disclaimer"] = False
                st.rerun()
        _dlg()
    except Exception:
        st.warning(disclaimer_text)
        if st.button("Αποδοχή-Προβολή", type="primary"):
            try:
                st.query_params["section"] = "all"
                st.query_params["token"] = link_token
                if client_value:
                    st.query_params["client"] = client_value
            except Exception:
                st.experimental_set_query_params(section="all", token=link_token, client=client_value)
            st.session_state["lite_show_disclaimer"] = False
            st.rerun()

# --- CENTERED INPUTS LAYOUT ---
# We use empty columns to center the content in the middle ~40-50%
col_left, col_mid, col_right = st.columns([1, 1.5, 1], gap="medium")

with col_mid:
    # 1. Full Name Input
    client_name = st.text_input("Ονοματεπώνυμο:", value=st.session_state.get("lite_client_name", ""), key="client_input")
    st.session_state["lite_client_name"] = client_name

    link_token = st.session_state.get("lite_token", token).strip()
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
                "lite_token",
                "lite_client_name",
                "lite_show_disclaimer",
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            try:
                if link_token:
                    cached_path = CACHE_DIR / f"{link_token}.pkl"
                    if cached_path.exists():
                        cached_path.unlink()
            except Exception:
                pass
            try:
                if LAST_TOKEN_FILE.exists():
                    LAST_TOKEN_FILE.unlink()
            except Exception:
                pass
            try:
                st.query_params.clear()
            except Exception:
                st.experimental_set_query_params()
            st.rerun()

if st.session_state.get("lite_show_disclaimer"):
    show_disclaimer_dialog()

description_map = build_description_map(df)

# --- FULL WIDTH REPORT OUTPUT ---
if section == "all":
    audit_df = generate_audit_report(df)
    display_summary = build_summary_grouped_display(df, df) if 'Κλάδος/Πακέτο Κάλυψης' in df.columns else pd.DataFrame()
    final_display_df, _, _, _, print_style_rows = build_count_report(
        df,
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
        sections.append(
            build_print_section_html(
                "Πίνακας Καταμέτρησης",
                final_display_df,
                description="Αναλυτική καταμέτρηση ημερών ασφάλισης ανά μήνα.",
                style_rows=print_style_rows,
                heading_tag="h2"
            )
        )
    else:
        sections.append("<section class='print-section'><h2>Πίνακας Καταμέτρησης</h2><p class='print-description'>Δεν βρέθηκαν δεδομένα.</p></section>")

    client_name_html = f"<div class='print-client-name'>{client_name.strip()}</div>" if client_name.strip() else ""
    body_html = (
        f"{client_name_html}"
        f"<h1>Συνολική Εκτύπωση</h1>"
        f"{''.join(sections)}"
        f"{get_print_disclaimer_html()}"
    )
    html_doc = wrap_print_html("Συνολική Εκτύπωση", body_html, auto_print=True)
    html_doc += f"\n<!-- nonce: {uuid.uuid4()} -->"
    components.html(html_doc, height=900, scrolling=True)

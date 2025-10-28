#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor - Final Version
Τελική, σταθερή έκδοση με multi-page functionality
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import urllib.parse
import pandas as pd
import io
import tempfile
import os
import re
from pathlib import Path

# Προσπάθεια εισαγωγής διαφορετικών PDF readers
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Ρύθμιση σελίδας
st.set_page_config(
    page_title="Ασφαλιστικό βιογραφικό ΑΤΛΑΣ",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS για καλύτερη εμφάνιση
st.markdown("""
<style>
    /* Καθολικό φόντο και γραμματοσειρά */
    .stApp { background-color: #f5f6f7; }
    html, body, [data-testid="stAppViewContainer"], .block-container {
        font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
        font-size: 17px;
    }
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .professional-header {
        background: linear-gradient(135deg, #6f42c1 0%, #8e44ad 100%);
        color: #ffffff;
        padding: 1.5rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1200px;
        margin: 0 auto;
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .header-icon {
        font-size: 2.5rem;
        background: rgba(255,255,255,0.2);
        padding: 0.5rem;
        border-radius: 10px;
    }
    .header-text h1 {
        margin: 0;
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: 0.2px;
    }
    .header-text p {
        margin: 0.25rem 0 0 0;
        font-size: 1rem;
        opacity: 0.9;
        color: #ffffff !important;
    }
    .header-right { display: flex; gap: 1.5rem; }
    .nav-link { color: #ffffff !important; text-decoration: none; font-weight: 600; padding: 0; }
    .nav-link:hover { text-decoration: underline; color: #ffffff !important; }
    .upload-section {
        background-color: transparent;
        padding: 1.5rem 1rem;
        border-radius: 10px;
        border: 0;
        text-align: center;
        margin: 1rem 0 2rem 0;
    }
    /* Σκιές και περίγραμμα για το πλαίσιο μεταφοράς/απόθεσης */
    [data-testid="stFileUploader"] {
        background: #ffffff;
        border: 1px solid #d0d7de;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 6px 16px rgba(0,0,0,0.06);
    }
    /* Έλεγχος πλάτους του ίδιου του file uploader (χωρίς wrapper) */
    div[data-testid="stFileUploader"] {
        max-width: 45% !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    @media (max-width: 1200px) {
        div[data-testid="stFileUploader"] { max-width: 65% !important; }
    }
    @media (max-width: 768px) {
        div[data-testid="stFileUploader"] { max-width: 85% !important; }
    }
    .app-container { max-width: 680px; margin: 0 auto; }
    .main-header { margin-top: 0.5rem; }
    
    /* Μωβ Header - Full Width */
    .purple-header {
        background: linear-gradient(135deg, #7b2cbf 0%, #5a189a 100%);
        color: white;
        text-align: center;
        padding: 4rem 1.25rem;
        margin: -5rem -5rem 3rem -5rem;
        font-size: 2.6rem;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Upload Container - Κεντρικό 45% */
    .upload-container {
        max-width: 45%;
        margin: 0 auto 2rem auto;
        text-align: center;
    }
    @media (max-width: 1200px) {
        .upload-container { max-width: 65%; }
    }
    @media (max-width: 768px) {
        .upload-container { max-width: 85%; }
    }
    
    .upload-prompt {
        font-size: 1.25rem;
        font-weight: 700;
        color: #000000;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    /* Οδηγίες Box - Κεντρικό 40% */
    .instructions-box {
        max-width: 40%;
        margin: 3rem auto 2rem auto;
        background: white;
        border: 2px solid #cbd5e1;
        border-radius: 8px;
        padding: 2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    @media (max-width: 1200px) {
        .instructions-box { max-width: 60%; }
    }
    @media (max-width: 768px) {
        .instructions-box { max-width: 90%; }
    }
    .instructions-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #000000;
        margin-bottom: 1rem;
        text-align: left;
    }
    .instructions-list {
        text-align: left;
        color: #333333;
        font-size: 1.1rem;
        line-height: 1.9;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        margin: 1rem 0;
    }
    .results-section {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        margin: 2rem 0;
    }
    .stButton > button {
        width: 100%;
        font-size: 1.2rem;
        padding: 0.5rem 1rem;
    }
    
    /* Μεγαλύτερα εικονίδια για τα dataframe controls */
    [data-testid="stDataFrame"] button {
        transform: scale(1.5) !important;
        margin: 0.3rem !important;
    }
    [data-testid="stDataFrame"] button svg {
        width: 22px !important;
        height: 22px !important;
    }
    [data-testid="stDataFrame"] [data-testid="baseButton-header"] {
        transform: scale(1.5) !important;
    }
    [data-testid="stDataFrame"] .stElementContainer button {
        transform: scale(1.5) !important;
        margin: 0.4rem !important;
    }
    /* Μεγαλύτερο μέγεθος για τα toolbar buttons */
    div[data-testid="stDataFrameToolbar"] button {
        transform: scale(1.5) !important;
        transform-origin: center !important;
        margin: 0.3rem !important;
        padding: 0.3rem !important;
    }
    div[data-testid="stDataFrameToolbar"] button svg {
        width: 22px !important;
        height: 22px !important;
    }
    div[data-testid="stDataFrameToolbar"] {
        padding: 0.5rem !important;
        z-index: 1000 !important;
        position: relative !important;
    }
</style>
""", unsafe_allow_html=True)

def render_print_button(button_key: str, title: str, dataframe: pd.DataFrame) -> None:
    """Εμφανίζει κουμπί εκτύπωσης που ανοίγει νέο παράθυρο με καλαίσθητη εκτύπωση του πίνακα.

    Args:
        button_key: Μοναδικό key για το κουμπί
        title: Τίτλος που θα εμφανιστεί στην εκτύπωση
        dataframe: Τα δεδομένα προς εκτύπωση (όπως εμφανίζονται)
    """
    col_spacer, col_btn = st.columns([1, 0.12])
    with col_btn:
        if st.button("Εκτύπωση", key=button_key, use_container_width=True):
            # Μοναδικό nonce ώστε το component να επανα-τοποθετείται και να εκτελείται κάθε φορά
            nonce_key = f"_print_nonce_{button_key}"
            nonce = st.session_state.get(nonce_key, 0) + 1
            st.session_state[nonce_key] = nonce
            window_name = f"printwin_{button_key}_{nonce}"
            # Δημιουργία HTML για εκτύπωση με ειδική μορφοποίηση
            headers_html = ''.join(f"<th>{h}</th>" for h in dataframe.columns)
            rows_html = []
            for _, row in dataframe.iterrows():
                first_val = str(row.iloc[0]) if len(row) > 0 else ''
                is_total = first_val.strip().startswith('Σύνολο')
                tr_class = ' class="total-row"' if is_total else ''
                tds = ''.join(f"<td>{'' if pd.isna(v) else v}</td>" for v in row.values)
                rows_html.append(f"<tr{tr_class}>{tds}</tr>")
            table_html = f"<table class=\"print-table\"><thead><tr>{headers_html}</tr></thead><tbody>{''.join(rows_html)}</tbody></table>"

            # Δημιουργία JavaScript που θα ανοίξει νέο παράθυρο
            js_code = f"""
<script>
function openPrintWindow() {{
    const printWindow = window.open('', '{window_name}', 'width=900,height=700');
    const htmlContent = `<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    @media print {{ @page {{ size: A4 landscape; margin: 12mm; }} }}
    body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #222; }}
    h1 {{ font-size: 20px; margin: 0 0 12px 0; }}
    table.print-table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
    table.print-table thead th {{ background: #f2f4f7; border-bottom: 1px solid #d0d7de; padding: 8px; text-align: left; }}
    table.print-table tbody td {{ border-bottom: 1px solid #eee; padding: 6px 8px; }}
    table.print-table tbody td:first-child {{ font-weight: 700; }}
    table.print-table tbody tr.total-row td {{ background: #e6f2ff; color: #000; font-weight: 700; }}
  </style>
</head>
<body onload="window.print()">
  <h1>{title}</h1>
  {table_html}
</body>
</html>`;
    
    try {{
      printWindow.document.open();
      printWindow.document.write(htmlContent);
      printWindow.document.close();
      printWindow.focus();
    }} catch (e) {{
      console.error('Print window error:', e);
    }}
}}

openPrintWindow();
</script>
"""
            # Σε ορισμένες εκδόσεις Streamlit, το components.html δεν δέχεται 'key'.
            # Η χρήση nonce στο περιεχόμενο διασφαλίζει νέα εκτέλεση κάθε φορά.
            st.components.v1.html(js_code + f"\n<!-- nonce:{nonce} -->", height=0)

def render_yearly_table_html(df: pd.DataFrame) -> None:
    """Απεικόνιση του ετήσιου πίνακα ως HTML με μπλε γραμμές συνόλων, χωρίς εξάρτηση από jinja2."""
    # CSS για τον πίνακα και τις γραμμές συνόλων
    st.markdown(
        """
<style>
.table-yearly { width: 100%; border-collapse: collapse; font-size: 14px; }
.table-yearly thead th { background: #f2f4f7; border-bottom: 1px solid #d0d7de; padding: 8px; text-align: left; }
.table-yearly tbody td { border-bottom: 1px solid #eee; padding: 6px 8px; }
.table-yearly tbody tr:nth-child(even) td { background: #fafbfc; }
.table-yearly tr.year-total-row td { background: #e6f2ff !important; color: #000; font-weight: 700; }
</style>
""",
        unsafe_allow_html=True,
    )

    # Δημιουργία HTML
    headers = ''.join(f"<th>{h}</th>" for h in df.columns)
    rows_html = []
    for _, row in df.iterrows():
        is_total = str(row.iloc[0]).startswith('Σύνολο')  # πρώτη στήλη είναι 'Έτος'
        tr_class = ' class="year-total-row"' if is_total else ''
        tds = ''.join(f"<td>{'' if pd.isna(val) else val}</td>" for val in row.values)
        rows_html.append(f"<tr{tr_class}>{tds}</tr>")
    table_html = f"<table class=\"table-yearly\"><thead><tr>{headers}</tr></thead><tbody>{''.join(rows_html)}</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

def extract_header_info(page):
    """
    Εξάγει Ταμείο και Τύπος Ασφάλισης από τον πρώτο πίνακα (2x2 grid)
    """
    try:
        tables = page.extract_tables()
        
        for table in tables:
            if not table or len(table) < 2:
                continue
                
            # Ελέγχουμε αν είναι ο πρώτος πίνακας (2x2 grid)
            if (len(table) == 2 and 
                len(table[0]) >= 2 and 
                len(table[1]) >= 2 and
                "Φορέας Κοινωνικής Ασφάλισης" in str(table[0][0])):
                
                # Εξάγουμε Ταμείο και Τύπος από τη δεύτερη γραμμή
                taimeio = str(table[1][0]).strip() if table[1][0] else ""
                typos = str(table[1][1]).strip() if table[1][1] else ""
                
                return taimeio, typos
                
    except Exception as e:
        st.warning(f"Σφάλμα εξαγωγής header info: {str(e)}")
    
    return None, None

def extract_tables_adaptive(pdf_path):
    """
    Προσαρμοστική εξαγωγή πινάκων με πολλές στρατηγικές
    """
    import pdfplumber
    
    all_tables = []
    current_taimeio = ""
    current_typos = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        st.info(f"Σύνολο σελίδων: {total_pages}")
        
        # Δημιουργία progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for page_num, page in enumerate(pdf.pages):
            if page_num < 1:  # Παρακάμπτουμε την πρώτη σελίδα
                continue
                
            # Ενημέρωση progress
            progress = (page_num - 1) / (total_pages - 2) if total_pages > 2 else 0
            progress_bar.progress(progress)
            status_text.text(f"Επεξεργασία σελίδας {page_num + 1} από {total_pages - 1}...")
            
            # Εξαγωγή header info (Ταμείο & Τύπος)
            taimeio, typos = extract_header_info(page)
            if taimeio and typos:
                current_taimeio = taimeio
                current_typos = typos
                st.info(f"Σελίδα {page_num + 1}: Ταμείο='{taimeio}', Τύπος='{typos}'")
            
            # Στρατηγική 1: Κανονική εξαγωγή πινάκων
            tables = page.extract_tables()
            
            if len(tables) >= 2:
                second_table = tables[1]
                if second_table and len(second_table) > 1:
                    df = pd.DataFrame(second_table[1:], columns=second_table[0])
                    df['Σελίδα'] = page_num + 1
                    
                    # Προσθήκη Ταμείου και Τύπου ως πρώτες στήλες
                    df.insert(0, 'Ταμείο', current_taimeio)
                    df.insert(1, 'Τύπος Ασφάλισης', current_typos)
                    
                    all_tables.append(df)
                    st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
                    continue
            
            # Στρατηγική 2: Εξαγωγή με διαφορετικές παραμέτρους
            try:
                tables_alt = page.extract_tables(table_settings={
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict"
                })
                
                if len(tables_alt) >= 2:
                    second_table = tables_alt[1]
                    if second_table and len(second_table) > 1:
                        df = pd.DataFrame(second_table[1:], columns=second_table[0])
                        df['Σελίδα'] = page_num + 1
                        
                        # Προσθήκη Ταμείου και Τύπου ως πρώτες στήλες
                        df.insert(0, 'Ταμείο', current_taimeio)
                        df.insert(1, 'Τύπος Ασφάλισης', current_typos)
                        
                        all_tables.append(df)
                        st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
                        continue
            except Exception:
                pass
            
            # Στρατηγική 3: Εξαγωγή όλων των πινάκων
            try:
                all_tables_page = page.extract_tables()
                if all_tables_page:
                    largest_table = max(all_tables_page, key=len)
                    if largest_table and len(largest_table) > 1:
                        df = pd.DataFrame(largest_table[1:], columns=largest_table[0])
                        df['Σελίδα'] = page_num + 1
                        
                        # Προσθήκη Ταμείου και Τύπου ως πρώτες στήλες
                        df.insert(0, 'Ταμείο', current_taimeio)
                        df.insert(1, 'Τύπος Ασφάλισης', current_typos)
                        
                        all_tables.append(df)
                        st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
                        continue
            except Exception:
                pass
            
            # Στρατηγική 4: Text-based parsing
            try:
                text = page.extract_text()
                if text and len(text) > 100:
                    table_data = parse_text_for_tables(text, page_num + 1)
                    if table_data and len(table_data) > 1:
                        df = pd.DataFrame(table_data[1:], columns=table_data[0])
                        df['Σελίδα'] = page_num + 1
                        
                        # Προσθήκη Ταμείου και Τύπου ως πρώτες στήλες
                        df.insert(0, 'Ταμείο', current_taimeio)
                        df.insert(1, 'Τύπος Ασφάλισης', current_typos)
                        
                        all_tables.append(df)
                        st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
                        continue
            except Exception:
                pass
            
            # Στρατηγική 5: Εξαγωγή όλων των πινάκων (fallback)
            try:
                all_tables_page = page.extract_tables()
                if all_tables_page:
                    for table_idx, table in enumerate(all_tables_page):
                        if table and len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df['Σελίδα'] = page_num + 1
                            df['Πίνακας'] = table_idx + 1
                            
                            # Προσθήκη Ταμείου και Τύπου ως πρώτες στήλες
                            df.insert(0, 'Ταμείο', current_taimeio)
                            df.insert(1, 'Τύπος Ασφάλισης', current_typos)
                            
                            all_tables.append(df)
                            st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (πίνακας {table_idx + 1})")
                            break
            except Exception:
                pass
            
            # Στρατηγική 6: PyMuPDF fallback
            if PYMUPDF_AVAILABLE:
                try:
                    import fitz
                    doc = fitz.open(pdf_path)
                    page_pymupdf = doc[page_num]
                    tables_pymupdf = page_pymupdf.find_tables()
                    
                    if len(tables_pymupdf) >= 2:
                        second_table = tables_pymupdf[1]
                        table_data = second_table.extract()
                        if table_data and len(table_data) > 1:
                            df = pd.DataFrame(table_data[1:], columns=table_data[0])
                            df['Σελίδα'] = page_num + 1
                            
                            # Προσθήκη Ταμείου και Τύπου ως πρώτες στήλες
                            df.insert(0, 'Ταμείο', current_taimeio)
                            df.insert(1, 'Τύπος Ασφάλισης', current_typos)
                            
                            all_tables.append(df)
                            st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
                            doc.close()
                            continue
                    doc.close()
                except Exception:
                    pass
            
            st.warning(f"Σελίδα {page_num + 1}: Δεν βρέθηκε πίνακας")
        
        # Τελικό progress
        progress_bar.progress(1.0)
        status_text.text("Επεξεργασία ολοκληρώθηκε!")
    
    return all_tables

def parse_text_for_tables(text, page_num):
    """
    Αναλύει κείμενο για να βρει πίνακες
    """
    lines = text.split('\n')
    
    # Ψάχνουμε για γραμμές που μοιάζουν με πίνακα
    table_lines = []
    in_table = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Ψάχνουμε για patterns που υποδεικνύουν πίνακα
        if (re.search(r'\d{1,2}/\d{1,2}/\d{4}', line) or  # Ημερομηνίες
            re.search(r'[\d,]+\.\d{2}', line) or  # Ποσά
            line.count(' ') > 3 or  # Πολλά κενά
            '\t' in line):  # Tabs
            
            table_lines.append(line)
            in_table = True
        elif in_table and len(table_lines) > 0:
            # Αν είχαμε βρει πίνακα αλλά τώρα δεν βρίσκουμε δεδομένα
            if len(table_lines) > 5:  # Αν έχουμε αρκετές γραμμές
                break
            else:
                table_lines = []  # Reset αν δεν έχουμε αρκετές γραμμές
                in_table = False
    
    if len(table_lines) < 3:
        return None
    
    # Δημιουργούμε headers
    headers = ['Στήλη_1', 'Στήλη_2', 'Στήλη_3', 'Στήλη_4', 'Στήλη_5', 'Στήλη_6']
    
    # Μετατρέπουμε τις γραμμές σε δεδομένα
    data = [headers]
    for line in table_lines:
        # Χωρίζουμε τη γραμμή σε στήλες
        parts = line.split()
        if len(parts) >= 3:  # Αν έχει αρκετές στήλες
            # Συμπληρώνουμε με κενά αν χρειάζεται
            while len(parts) < len(headers):
                parts.append('')
            data.append(parts[:len(headers)])
    
    return data if len(data) > 1 else None

def detect_currency(value):
    """Ανίχνευση νομίσματος από την τιμή"""
    if pd.isna(value) or value == '' or value == '-':
        return None
    
    value_str = str(value).strip()
    if 'ΔΡΧ' in value_str:
        return 'ΔΡΧ'
    elif '€' in value_str:
        return '€'
    else:
        # Αν δεν υπάρχει νόμισμα, υποθέτουμε € (μετά το 2002)
        return '€'

def format_currency(value):
    """Μορφοποίηση νομισματικών ποσών για εμφάνιση με Ελληνικό πρότυπο
    
    Ελληνικό πρότυπο:
    - Διαχωριστικό χιλιάδων: τελεία (.)
    - Διαχωριστικό δεκαδικών: κόμμα (,)
    - Σύμβολο νομίσματος: € ή ΔΡΧ
    Παράδειγμα: 1.234,56 € ή 50.000 ΔΡΧ
    """
    try:
        if pd.isna(value) or value == '' or value == '-':
            return ''
        
        # Ανίχνευση νομίσματος πριν τον καθαρισμό
        currency_symbol = detect_currency(value)
        if currency_symbol is None:
            currency_symbol = '€'  # Default
        
        # Μετατροπή σε float αν είναι αριθμός
        if isinstance(value, (int, float)):
            numeric_value = float(value)
        else:
            numeric_value = clean_numeric_value(value)
        
        if numeric_value == 0:
            return ''
        
        # Μορφοποίηση με Αμερικανικό format πρώτα (κόμμα=χιλιάδες, τελεία=δεκαδικά)
        formatted = f"{numeric_value:,.2f}"
        
        # Αφαίρεση των .00 αν είναι ακέραιος
        if formatted.endswith('.00'):
            formatted = formatted[:-3]
        
        # Μετατροπή σε Ελληνικό format
        # Αντικατάσταση κόμματος (χιλιάδες) με placeholder
        formatted = formatted.replace(',', '|||')
        # Αντικατάσταση τελείας (δεκαδικά) με κόμμα
        formatted = formatted.replace('.', ',')
        # Αντικατάσταση placeholder με τελεία (χιλιάδες)
        formatted = formatted.replace('|||', '.')
        
        # Προσθήκη συμβόλου νομίσματος
        formatted = f"{formatted} {currency_symbol}"
        
        return formatted
    except (ValueError, TypeError):
        return str(value) if value else ''

def format_number_greek(value, decimals=None):
    """Μορφοποίηση αριθμού με ελληνικό format (τελεία για χιλιάδες, κόμμα για δεκαδικά)
    
    Args:
        value: Ο αριθμός προς μορφοποίηση
        decimals: Αριθμός δεκαδικών (None = αυτόματα, 0 = χωρίς δεκαδικά, 1+ = συγκεκριμένος αριθμός)
    
    Παράδειγμα: 
        3804 -> 3.804
        123.4 -> 123,4
        9.6 -> 9,6
    """
    try:
        if pd.isna(value) or value == '' or value == '-':
            return ''
        
        # Μετατροπή σε float
        if isinstance(value, (int, float)):
            numeric_value = float(value)
        else:
            numeric_value = float(str(value).replace(',', '.'))
        
        # Καθορισμός δεκαδικών ψηφίων
        if decimals is None:
            # Αυτόματος καθορισμός: αν είναι ακέραιος, χωρίς δεκαδικά
            if numeric_value == int(numeric_value):
                decimals = 0
            else:
                # Βρίσκουμε πόσα δεκαδικά υπάρχουν (max 2)
                decimals = min(len(str(numeric_value).split('.')[-1]), 2) if '.' in str(numeric_value) else 1
        
        # Μορφοποίηση με αμερικανικό format πρώτα (κόμμα=χιλιάδες, τελεία=δεκαδικά)
        if decimals == 0:
            formatted = f"{int(numeric_value):,}"
        else:
            formatted = f"{numeric_value:,.{decimals}f}"
        
        # Μετατροπή σε ελληνικό format
        # Αντικατάσταση κόμματος (χιλιάδες) με placeholder
        formatted = formatted.replace(',', '|||')
        # Αντικατάσταση τελείας (δεκαδικά) με κόμμα
        formatted = formatted.replace('.', ',')
        # Αντικατάσταση placeholder με τελεία (χιλιάδες)
        formatted = formatted.replace('|||', '.')
        
        return formatted
    except (ValueError, TypeError):
        return str(value) if value else ''

def clean_numeric_value(value, exclude_drx=False):
    """Καθαρισμός και μετατροπή αριθμητικών τιμών σε float
    
    Args:
        value: Η τιμή προς καθαρισμό
        exclude_drx: Αν True, επιστρέφει 0.0 για ποσά σε ΔΡΧ
    """
    try:
        if pd.isna(value) or value == '' or value == '-':
            return 0.0
        
        # Μετατροπή σε string και καθαρισμός
        clean_value = str(value).strip()
        
        # Έλεγχος για ΔΡΧ αν exclude_drx=True
        if exclude_drx and 'ΔΡΧ' in clean_value:
            return 0.0
        
        # Αφαίρεση κειμένου όπως "ΔΡΧ", "€", κλπ
        clean_value = clean_value.replace('ΔΡΧ', '').replace('€', '').replace(' ', '')
        
        # Αφαίρεση όλων των γραμμάτων
        import re
        clean_value = re.sub(r'[a-zA-Zα-ωΑ-Ω]', '', clean_value)
        
        # Αφαίρεση κενών
        clean_value = clean_value.strip()
        
        if not clean_value or clean_value == '-':
            return 0.0
        
        # Έλεγχος για ελληνικό format (κόμμα ως διαχωριστικός χιλιάδων, τελεία ως δεκαδικός)
        # π.χ. "1,234.56" ή "1234.56" ή "1,234"
        if ',' in clean_value and '.' in clean_value:
            # Format: 1,234.56 (κόμμα χιλιάδες, τελεία δεκαδικά)
            clean_value = clean_value.replace(',', '')
            return float(clean_value)
        elif ',' in clean_value:
            # Ελέγχουμε αν το κόμμα είναι διαχωριστικός χιλιάδων ή δεκαδικών
            parts = clean_value.split(',')
            if len(parts) == 2:
                # Αν το δεύτερο μέρος έχει 3 ψηφία, είναι πιθανώς χιλιάδες
                # Αν έχει 1-2 ψηφία, είναι πιθανώς δεκαδικά
                if len(parts[1]) == 3 and parts[1].isdigit():
                    # Κόμμα ως διαχωριστικός χιλιάδων: 1,234 -> 1234
                    clean_value = clean_value.replace(',', '')
                elif len(parts[1]) <= 2:
                    # Κόμμα ως δεκαδικός διαχωριστικός: 1,23 -> 1.23
                    clean_value = clean_value.replace(',', '.')
                else:
                    # Αφαίρεση κόμματος (χιλιάδες)
                    clean_value = clean_value.replace(',', '')
            else:
                # Πολλά κόμματα, αφαίρεση όλων (χιλιάδες)
                clean_value = clean_value.replace(',', '')
        
        # Μετατροπή σε float
        return float(clean_value)
    except (ValueError, TypeError):
        return 0.0

def find_gaps_in_insurance_data(df):
    """
    Εντοπίζει κενά διαστήματα στα ασφαλιστικά δεδομένα
    
    Args:
        df: DataFrame με τα ασφαλιστικά δεδομένα
        
    Returns:
        DataFrame με τα κενά διαστήματα
    """
    if 'Από' not in df.columns or 'Έως' not in df.columns:
        return pd.DataFrame()
    
    # Φιλτράρουμε μόνο τις γραμμές με έγκυρες ημερομηνίες
    gaps_df = df.copy()
    gaps_df['Από_DateTime'] = pd.to_datetime(gaps_df['Από'], format='%d/%m/%Y', errors='coerce')
    gaps_df['Έως_DateTime'] = pd.to_datetime(gaps_df['Έως'], format='%d/%m/%Y', errors='coerce')
    gaps_df = gaps_df.dropna(subset=['Από_DateTime', 'Έως_DateTime'])
    
    if gaps_df.empty:
        return pd.DataFrame()
    
    # Βρίσκουμε το παλιότερο "Από" και το νεότερο "Έως"
    min_date = gaps_df['Από_DateTime'].min()
    max_date = gaps_df['Έως_DateTime'].max()
    
    # Δημιουργούμε λίστα με όλα τα διαστήματα
    intervals = []
    for _, row in gaps_df.iterrows():
        intervals.append((row['Από_DateTime'], row['Έως_DateTime']))
    
    # Ταξινομούμε τα διαστήματα κατά ημερομηνία έναρξης
    intervals.sort(key=lambda x: x[0])
    
    # Εντοπίζουμε τα κενά
    gaps = []
    current_end = min_date
    
    for start, end in intervals:
        # Αν υπάρχει κενό μεταξύ του current_end και του start
        if start > current_end + pd.Timedelta(days=1):
            gap_start = current_end + pd.Timedelta(days=1)
            gap_end = start - pd.Timedelta(days=1)
            gaps.append({
                'Από': gap_start.strftime('%d/%m/%Y'),
                'Έως': gap_end.strftime('%d/%m/%Y'),
                'Ημερολογιακές ημέρες': (gap_end - gap_start).days + 1,
                'Μήνες': round((gap_end - gap_start).days / 30.44, 1),
                'Έτη': round((gap_end - gap_start).days / 365.25, 1)
            })
        
        # Ενημερώνουμε το current_end με το μεγαλύτερο από το τρέχον και το end
        current_end = max(current_end, end)
    
    if not gaps:
        return pd.DataFrame()
    
    # Δημιουργούμε DataFrame με τα κενά
    gaps_df_result = pd.DataFrame(gaps)
    
    # Ταξινομούμε κατά ημερομηνία έναρξης
    gaps_df_result['Από_DateTime'] = pd.to_datetime(gaps_df_result['Από'], format='%d/%m/%Y')
    gaps_df_result = gaps_df_result.sort_values('Από_DateTime')
    gaps_df_result = gaps_df_result.drop('Από_DateTime', axis=1)
    
    return gaps_df_result

def normalize_column_name(name):
    """
    Κανονικοποιεί ένα όνομα στήλης για σύγκριση
    Αφαιρεί \n, πολλαπλά κενά, και μετατρέπει σε πεζά
    """
    if pd.isna(name):
        return ""
    # Αντικατάσταση \n και tabs με κενό
    normalized = str(name).replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')
    # Αφαίρεση πολλαπλών κενών
    normalized = ' '.join(normalized.split())
    # Αφαίρεση περιττών κενών στην αρχή/τέλος
    normalized = normalized.strip()
    return normalized

def find_column_by_pattern(df, patterns):
    """
    Βρίσκει μια στήλη με βάση patterns (υποστηρίζει πολλαπλά patterns)
    Επιστρέφει το πραγματικό όνομα της στήλης ή None
    """
    if isinstance(patterns, str):
        patterns = [patterns]
    
    for col in df.columns:
        col_normalized = normalize_column_name(col).lower()
        for pattern in patterns:
            pattern_normalized = pattern.lower().strip()
            if pattern_normalized in col_normalized or col_normalized in pattern_normalized:
                return col
    return None

def normalize_column_names(df):
    """
    Κανονικοποίηση ονομάτων στηλών με mapping σε standard names
    """
    # Mapping από patterns -> standard name (με προτεραιότητα - πιο συγκεκριμένα πρώτα)
    column_mapping = {
        'Συνολικές εισφορές': ['συνολικές εισφορές', 'συνολικες εισφορες', 'συνολικ εισφορ'],
        'Μικτές αποδοχές': ['μικτές αποδοχές', 'μικτες αποδοχες', 'μικτ αποδοχ'],
        'Τύπος Αποδοχών': ['τύπος αποδοχών', 'τυπος αποδοχων', 'τυπος απο'],
        'Κλάδος/Πακέτο Κάλυψης': ['κλάδος πακέτο κάλυψης', 'κλαδος πακετο καλυψης', 'κλάδος', 'πακέτο κάλυψης'],
        'Α/Μ εργοδότη': ['α μ εργοδότη', 'α/μ εργοδ', 'εργοδότη'],
        'Ημέρες': ['ημέρες', 'ημερες', 'ημερ'],
        'Έτη': ['έτη', 'ετη'],
        'Μήνες': ['μήνες', 'μηνες'],
        'Από': ['από'],
        'Έως': ['έως', 'εως'],
    }
    
    # Δημιουργία mapping από παλιό -> νέο όνομα
    rename_dict = {}
    used_standards = set()  # Για να μην αντιστοιχίσουμε δύο στήλες στο ίδιο standard name
    
    # Πρώτα ψάχνουμε για exact matches ή πολύ κοντινά matches
    for col in df.columns:
        col_normalized = normalize_column_name(col).lower()
        
        # Ελέγχουμε για κάθε standard name (με τη σειρά προτεραιότητας)
        for standard_name, patterns in column_mapping.items():
            if standard_name in used_standards:
                continue
                
            # Έλεγχος για match
            matched = False
            for pattern in patterns:
                # Ελέγχουμε αν το pattern ταιριάζει
                if pattern == col_normalized:
                    # Exact match
                    rename_dict[col] = standard_name
                    used_standards.add(standard_name)
                    matched = True
                    break
                elif len(pattern) > 5 and pattern in col_normalized:
                    # Substring match (αλλά μόνο για μακρά patterns)
                    rename_dict[col] = standard_name
                    used_standards.add(standard_name)
                    matched = True
                    break
                elif len(col_normalized) > 5 and col_normalized in pattern:
                    # Reverse substring match
                    rename_dict[col] = standard_name
                    used_standards.add(standard_name)
                    matched = True
                    break
            
            if matched:
                break
    
    # Εφαρμογή mapping
    if rename_dict:
        df = df.rename(columns=rename_dict)
    
    return df

def extract_efka_data(uploaded_file):
    """
    Εξαγωγή δεδομένων από PDF αρχείο
    """
    
    # Δημιουργούμε ένα προσωρινό αρχείο
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Εξάγουμε πίνακες
        all_tables = extract_tables_adaptive(tmp_path)
        
        if not all_tables:
            st.error("Δεν βρέθηκαν πίνακες στο PDF αρχείο")
            return pd.DataFrame()
        
        # Κανονικοποίηση ονομάτων στηλών για όλους τους πίνακες
        for i in range(len(all_tables)):
            all_tables[i] = normalize_column_names(all_tables[i])
        
        # Συνδυάζουμε όλα τα DataFrames
        with st.spinner("Συνδυασμός δεδομένων..."):
            combined_df = pd.concat(all_tables, ignore_index=True)
        
        st.success(f"🎉 Συνολικά εξήχθησαν {len(combined_df)} γραμμές δεδομένων από {len(all_tables)} πίνακες")
        return combined_df
    
    except Exception as e:
        st.error(f"Σφάλμα κατά την εξαγωγή: {str(e)}")
        return pd.DataFrame()
    
    finally:
        # Διαγράφουμε το προσωρινό αρχείο
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def show_results_page(df, filename):
    """
    Εμφανίζει τη σελίδα αποτελεσμάτων
    """
    
    # Έλεγχος για αναμενόμενες στήλες
    expected_columns = ['Από', 'Έως', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές']
    missing_columns = []
    found_columns = []
    
    for col in expected_columns:
        if col in df.columns:
            found_columns.append(col)
        else:
            missing_columns.append(col)
    
    # Δημιουργία mapping για περιγραφές πακέτων κάλυψης (για χρήση σε φίλτρα)
    description_map = {}
    if 'Κωδικός Κλάδων / Πακέτων Κάλυψης' in df.columns and 'Περιγραφή' in df.columns:
        desc_df = df[['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']].copy()
        desc_df = desc_df.dropna(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή'])
        desc_df = desc_df[desc_df['Κωδικός Κλάδων / Πακέτων Κάλυψης'] != '']
        desc_df = desc_df[desc_df['Περιγραφή'] != '']
        desc_df = desc_df.drop_duplicates(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης'])
        # Δημιουργούμε dictionary: κωδικός -> περιγραφή
        for _, row in desc_df.iterrows():
            code = str(row['Κωδικός Κλάδων / Πακέτων Κάλυψης']).strip()
            desc = str(row['Περιγραφή']).strip()
            description_map[code] = desc
    
    # Professional Header
    st.markdown("""
    <div class="professional-header">
        <div class="header-content">
            <div class="header-left">
                <div class="header-text">
                    <h1>Ασφαλιστικό βιογραφικό ΑΤΛΑΣ</h1>
                    <p>Ανάλυση και Επεξεργασία Ασφαλιστικών Δεδομένων από το syntaksi.com</p>
                </div>
            </div>
            <div class="header-right">
                <a href="#" class="nav-link" onclick="resetToHome()">Αρχική</a>
                <a href="#" class="nav-link">Οδηγίες</a>
                <a href="#" class="nav-link">Σχετικά</a>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    
    
    # CSS για μεγαλύτερους τίτλους tabs
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem !important;
    }
    /* Λευκό φόντο για πεδία φίλτρων */
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div,
    .stTextInput input,
    .stDateInput input,
    .stNumberInput input,
    .stTextArea textarea,
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border-color: #d0d7de !important;
        box-shadow: inset 0 1px 2px rgba(16,24,40,0.04) !important;
    }
    /* Βελτίωση αντίθεσης labels φίλτρων */
    label, .stMarkdown p {
        color: #111827;
    }
    /* Βελτιωμένο z-index για popover menus χωρίς να επηρεάζουμε το μέγεθος */
    body > div[data-baseweb="popover"],
    body > div[role="dialog"] {
        z-index: 10000 !important;
    }
    /* Σταθερή θέση toolbar επάνω δεξιά του πίνακα */
    div[data-testid="stDataFrameToolbar"] {
        position: sticky !important;
        top: 8px !important;
        right: 8px !important;
        z-index: 100 !important;
    }
    /* Dataframe container χαμηλότερο z-index από τα popover */
    div[data-testid="stDataFrame"] {
        z-index: 1 !important;
        position: relative !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Μετάφραση ενδείξεων του file uploader στα Ελληνικά
    components.html(
        """
        <script>
          const translateUploader = () => {
            const root = document.querySelector('div[data-testid="stFileUploader"]');
            if (!root) return;
            // Κείμενα drag & drop
            const hints = root.querySelectorAll('span, div');
            hints.forEach((el) => {
              if (el.textContent && el.textContent.includes('Drag and drop')) {
                el.textContent = 'Σύρετε και αφήστε το αρχείο εδώ';
              }
              if (el.textContent && el.textContent.includes('Drag and drop files here')) {
                el.textContent = 'Σύρετε και αφήστε τα αρχεία εδώ';
              }
              if (el.textContent && el.textContent.includes('Limit')) {
                el.textContent = el.textContent
                  .replace('Limit', 'Όριο')
                  .replace('per file', 'ανά αρχείο');
              }
            });
            // Κουμπί Browse
            const btns = root.querySelectorAll('button, span, label');
            btns.forEach((b) => {
              if (b.textContent && b.textContent.trim() === 'Επιλογή αρχείου') {
                b.textContent = 'Επιλογή αρχείου';
              }
              if (b.textContent && b.textContent.trim() === 'Browse file') {
                b.textContent = 'Επιλογή αρχείου';
              }
            });
          };
          const obs = new MutationObserver(() => translateUploader());
          obs.observe(document.body, { childList: true, subtree: true });
          window.addEventListener('load', translateUploader);
          setTimeout(translateUploader, 800);
        </script>
        """,
        height=0
    )
    
    # Δημιουργία tabs για διαφορετικούς τύπους δεδομένων
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Κύρια Δεδομένα", "Επιπλέον Πίνακες", "Συνοπτική Αναφορά", "Ετήσια Αναφορά", "Ημέρες Ασφάλισης", "Κενά Διαστήματα"])
    
    with tab1:
        # Κύρια δεδομένα (χωρίς τις στήλες από τελευταίες σελίδες)
        main_columns = [col for col in df.columns if col not in ['Φορέας', 'Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή', 'Κωδικός Τύπου Αποδοχών']]
        main_df = df[main_columns] if main_columns else df
        
        
        # Φιλτράρουμε μόνο τις γραμμές που ξεκινάνε με ημερομηνία "Από"
        if 'Από' in main_df.columns:
            # Κρατάμε μόνο τις γραμμές που έχουν έγκυρη ημερομηνία στο "Από"
            main_df = main_df.copy()
            main_df['Από_DateTime'] = pd.to_datetime(main_df['Από'], format='%d/%m/%Y', errors='coerce')
            
            # Φιλτράρουμε μόνο τις γραμμές με έγκυρη ημερομηνία
            main_df = main_df.dropna(subset=['Από_DateTime'])
            
            # Χρονολογική ταξινόμηση
            main_df = main_df.sort_values('Από_DateTime', na_position='last')
            main_df = main_df.drop('Από_DateTime', axis=1)  # Αφαιρούμε τη βοηθητική στήλη
        
        # Σύστημα Φίλτρων (χωρίς εμφανή τίτλο)
        
        # Κουμπί για άνοιγμα popup φίλτρων
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Άνοιγμα Φίλτρων", type="secondary", use_container_width=True):
                st.session_state['show_filters'] = not st.session_state.get('show_filters', False)
        
        # Popup φίλτρων
        if st.session_state.get('show_filters', False):
            with st.expander("Φίλτρα Δεδομένων", expanded=True):
                # Όλα τα φίλτρα σε μία γραμμή
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.1, 1.1, 1.4, 1.1, 1.0, 1.0, 0.6, 0.6])

                with col1:
                    # Φίλτρο Ταμείου
                    if 'Ταμείο' in main_df.columns:
                        taimeia_options = ['Όλα'] + sorted(main_df['Ταμείο'].dropna().unique().tolist())
                        selected_taimeia = st.multiselect(
                            "Ταμείο:",
                            options=taimeia_options,
                            default=['Όλα'],
                            key="filter_taimeio"
                        )
                        if 'Όλα' not in selected_taimeia:
                            main_df = main_df[main_df['Ταμείο'].isin(selected_taimeia)]

                with col2:
                    # Φίλτρο Τύπου Ασφάλισης
                    if 'Τύπος Ασφάλισης' in main_df.columns:
                        typos_options = ['Όλα'] + sorted(main_df['Τύπος Ασφάλισης'].dropna().unique().tolist())
                        selected_typos = st.multiselect(
                            "Τύπος Ασφάλισης:",
                            options=typos_options,
                            default=['Όλα'],
                            key="filter_typos"
                        )
                        if 'Όλα' not in selected_typos:
                            main_df = main_df[main_df['Τύπος Ασφάλισης'].isin(selected_typos)]

                with col3:
                    # Φίλτρο Κλάδου/Πακέτου με περιγραφές
                    if 'Κλάδος/Πακέτο Κάλυψης' in main_df.columns:
                        # Δημιουργούμε options με περιγραφές
                        klados_codes = sorted(main_df['Κλάδος/Πακέτο Κάλυψης'].dropna().unique().tolist())
                        klados_options_with_desc = ['Όλα']
                        klados_code_map = {}  # Mapping από "Κωδικός - Περιγραφή" -> Κωδικός
                        
                        for code in klados_codes:
                            if code in description_map and description_map[code]:
                                option_label = f"{code} - {description_map[code]}"
                                klados_options_with_desc.append(option_label)
                                klados_code_map[option_label] = code
                            else:
                                klados_options_with_desc.append(code)
                                klados_code_map[code] = code
                        
                        selected_klados = st.multiselect(
                            "Κλάδος/Πακέτο:",
                            options=klados_options_with_desc,
                            default=['Όλα'],
                            key="filter_klados"
                        )
                        
                        if 'Όλα' not in selected_klados:
                            # Μετατρέπουμε τις επιλογές σε κωδικούς
                            selected_codes = [klados_code_map.get(opt, opt) for opt in selected_klados]
                            main_df = main_df[main_df['Κλάδος/Πακέτο Κάλυψης'].isin(selected_codes)]

                with col4:
                    # Φίλτρο Τύπου Αποδοχών (σταθερή και ανθεκτική ανίχνευση ονόματος)
                    earnings_col = None
                    if 'Τύπος Αποδοχών' in main_df.columns:
                        earnings_col = 'Τύπος Αποδοχών'
                    else:
                        for c in main_df.columns:
                            name = str(c).strip().lower()
                            if ('αποδοχ' in name) and ('τύπος' in name or 'τυπος' in name):
                                earnings_col = c
                                break
                    if earnings_col is not None:
                        options_raw = main_df[earnings_col].dropna().astype(str).unique().tolist()
                        typos_apodochon_options = ['Όλα'] + sorted(options_raw)
                        selected_typos_apodochon = st.multiselect(
                            "Τύπος Αποδοχών:",
                            options=typos_apodochon_options,
                            default=['Όλα'],
                            key="filter_apodochon"
                        )
                        if 'Όλα' not in selected_typos_apodochon:
                            main_df = main_df[main_df[earnings_col].isin(selected_typos_apodochon)]

                with col5:
                    # Ημερομηνία Από
                    if 'Από' in main_df.columns:
                        from_date_str = st.text_input(
                            "Από (dd/mm/yyyy):",
                            value="",
                            placeholder="01/01/1985",
                            key="filter_from_date"
                        )

                with col6:
                    # Ημερομηνία Έως
                    if 'Από' in main_df.columns:
                        to_date_str = st.text_input(
                            "Έως (dd/mm/yyyy):",
                            value="",
                            placeholder="31/12/1990",
                            key="filter_to_date"
                        )

                with col7:
                    # Κουμπί επαναφοράς
                    reset_label = "↻"
                    if st.button(reset_label, help="Επαναφορά", use_container_width=True):
                        st.session_state['show_filters'] = False
                        st.rerun()

                with col8:
                    # Κουμπί κλεισίματος φίλτρων
                    if st.button("❌", help="Κλείσιμο", use_container_width=True):
                        st.session_state['show_filters'] = False
                        st.rerun()
                
                # Εφαρμογή φίλτρων ημερομηνιών
                if 'Από' in main_df.columns and (from_date_str or to_date_str):
                    main_df['Από_DateTime'] = pd.to_datetime(main_df['Από'], format='%d/%m/%Y', errors='coerce')
                    
                    if from_date_str:
                        try:
                            from_date_pd = pd.to_datetime(from_date_str, format='%d/%m/%Y')
                            main_df = main_df[main_df['Από_DateTime'] >= from_date_pd]
                        except:
                            st.error("Μη έγκυρη μορφή ημερομηνίας 'Από'")
                    
                    if to_date_str:
                        try:
                            to_date_pd = pd.to_datetime(to_date_str, format='%d/%m/%Y')
                            main_df = main_df[main_df['Από_DateTime'] <= to_date_pd]
                        except:
                            st.error("Μη έγκυρη μορφή ημερομηνίας 'Έως'")
                    
                    main_df = main_df.drop('Από_DateTime', axis=1)
        
        # Εμφάνιση αποτελεσμάτων φίλτρων (σε πραγματικό χρόνο)
        if st.session_state.get('show_filters', False):
            st.info(f"Εμφανίζονται {len(main_df)} γραμμές")
        
        # Δημιουργούμε αντίγραφο για εμφάνιση με μορφοποίηση
        display_df = main_df.copy()
        
        # Εφαρμόζουμε μορφοποίηση νομισμάτων μόνο για εμφάνιση
        currency_columns = ['Μικτές αποδοχές', 'Συνολικές εισφορές']
        for col in currency_columns:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(format_currency)
        
        # Εφαρμόζουμε ελληνική μορφοποίηση για αριθμητικές στήλες
        numeric_columns = ['Ημερολογιακές ημέρες', 'Μήνες', 'Έτη']
        for col in numeric_columns:
            if col in display_df.columns:
                # Μήνες και Έτη με 1 δεκαδικό, ημέρες χωρίς δεκαδικά
                decimals = 1 if col in ['Μήνες', 'Έτη'] else 0
                display_df[col] = display_df[col].apply(lambda x: format_number_greek(x, decimals=decimals) if pd.notna(x) and x != '' else x)
        
        st.markdown("### Κύρια Δεδομένα e-EFKA (Με χρονολογική σειρά)")
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600
        )
        # Κουμπί εκτύπωσης για Κύρια Δεδομένα
        render_print_button("print_main", "Κύρια Δεδομένα e-EFKA", display_df)
    
    with tab2:
        # Επιπλέον πίνακες (στήλες από τελευταίες σελίδες)
        extra_columns = [col for col in df.columns if col in ['Φορέας', 'Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']]
        
        if extra_columns:
            extra_df = df[extra_columns].copy()
            
            # Φιλτράρουμε κενές γραμμές (όπου όλες οι στήλες είναι κενές ή "None")
            extra_df = extra_df.dropna(how='all')  # Αφαιρούμε γραμμές που είναι όλες κενές
            extra_df = extra_df[~((extra_df == 'None') | (extra_df == '') | (extra_df.isna())).all(axis=1)]  # Αφαιρούμε γραμμές με "None" ή κενά
            
            if not extra_df.empty:
                st.markdown("### Επιπλέον Πίνακες (Τελευταίες Σελίδες)")
                st.dataframe(
                    extra_df,
                    use_container_width=True,
                    height=600
                )
                render_print_button("print_extra", "Επιπλέον Πίνακες", extra_df)
            else:
                st.info("Δεν βρέθηκαν δεδομένα στα επιπλέον πίνακες.")
        else:
            st.info("Δεν βρέθηκαν επιπλέον πίνακες από τις τελευταίες σελίδες.")
    
    with tab3:
        # Συνοπτική Αναφορά - Ομαδοποίηση με βάση Κλάδος/Πακέτο Κάλυψης
        st.markdown("### Συνοπτική Αναφορά - Ομαδοποίηση κατά Κλάδο/Πακέτο Κάλυψης")
        st.info("Σημείωση: Στα αθροίσματα συμπεριλαμβάνονται μόνο τα ποσά σε €. Τα ποσά σε ΔΡΧ (πριν το 2002) εμφανίζονται αλλά δεν υπολογίζονται στα συνολικά.")
        
        if 'Κλάδος/Πακέτο Κάλυψης' in df.columns:
            # Προετοιμασία δεδομένων
            summary_df = df.copy()
            # Κανονικοποίηση τιμών κλάδου/πακέτου
            summary_df['Κλάδος/Πακέτο Κάλυψης'] = (
                summary_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
            )
            # Μετατροπή ημερομηνιών σε datetime για ορθή min/max
            summary_df['Από_dt'] = pd.to_datetime(summary_df.get('Από'), format='%d/%m/%Y', errors='coerce')
            summary_df['Έως_dt'] = pd.to_datetime(summary_df.get('Έως'), format='%d/%m/%Y', errors='coerce')
            # Κρατάμε γραμμές με τουλάχιστον έγκυρη μία ημερομηνία έναρξης
            summary_df = summary_df.dropna(subset=['Από_dt'])
            
            # Καθαρισμός αριθμητικών στηλών πριν την ομαδοποίηση
            # Για τα ποσά, εξαιρούμε τα ΔΡΧ από τα αθροίσματα
            numeric_columns = ['Έτη', 'Μήνες', 'Ημέρες']
            currency_columns = ['Μικτές αποδοχές', 'Συνολικές εισφορές']
            
            for col in numeric_columns:
                if col in summary_df.columns:
                    summary_df[col] = summary_df[col].apply(clean_numeric_value)
            
            # Για τα νομισματικά ποσά, εξαιρούμε τα ΔΡΧ
            for col in currency_columns:
                if col in summary_df.columns:
                    summary_df[col] = summary_df[col].apply(lambda x: clean_numeric_value(x, exclude_drx=True))
            
            # Ομαδοποίηση με βάση Κλάδος/Πακέτο και υπολογισμός min/max σε datetime
            grouped = summary_df.groupby('Κλάδος/Πακέτο Κάλυψης').agg({
                'Από_dt': 'min',
                'Έως_dt': 'max',
                'Έτη': 'sum',
                'Μήνες': 'sum',
                'Ημέρες': 'sum',
                'Μικτές αποδοχές': 'sum',
                'Συνολικές εισφορές': 'sum'
            }).reset_index()
            # Μορφοποίηση ημερομηνιών ξανά σε dd/mm/yyyy
            grouped['Από'] = grouped['Από_dt'].dt.strftime('%d/%m/%Y')
            grouped['Έως'] = grouped['Έως_dt'].dt.strftime('%d/%m/%Y')
            grouped = grouped.drop(columns=['Από_dt', 'Έως_dt'])

            # Υπολογισμός «Συνολικές ημέρες» βάσει παραμέτρων από την αναφορά ημερών
            basis_label = st.session_state.get('ins_days_basis', 'Μήνας = 25, Έτος = 300')
            if str(basis_label).startswith('Μήνας = 30'):
                month_days, year_days = 30, 360
            else:
                month_days, year_days = 25, 300
            grouped['Συνολικές ημέρες'] = (
                grouped['Ημέρες'].fillna(0) +
                grouped['Μήνες'].fillna(0) * month_days +
                grouped['Έτη'].fillna(0) * year_days
            ).round(0).astype(int)
            
            # Μετράμε τις εγγραφές για κάθε κλάδο
            record_counts = summary_df['Κλάδος/Πακέτο Κάλυψης'].value_counts().reset_index()
            record_counts.columns = ['Κλάδος/Πακέτο Κάλυψης', 'Αριθμός Εγγραφών']
            
            # Συνδυάζουμε τα δεδομένα
            summary_final = grouped.merge(record_counts, on='Κλάδος/Πακέτο Κάλυψης', how='left')
            
            # Προσθήκη περιγραφής από τα Επιπλέον Πίνακες
            if 'Κωδικός Κλάδων / Πακέτων Κάλυψης' in df.columns and 'Περιγραφή' in df.columns:
                # Δημιουργούμε mapping από Κωδικός -> Περιγραφή
                description_map = df[['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']].copy()
                description_map = description_map.dropna(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή'])
                description_map = description_map[description_map['Κωδικός Κλάδων / Πακέτων Κάλυψης'] != '']
                description_map = description_map[description_map['Περιγραφή'] != '']
                # Αφαιρούμε duplicates - κρατάμε την πρώτη περιγραφή για κάθε κωδικό
                description_map = description_map.drop_duplicates(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης'])
                description_map.columns = ['Κλάδος/Πακέτο Κάλυψης', 'Περιγραφή']
                
                # Κανονικοποίηση τιμών για matching
                description_map['Κλάδος/Πακέτο Κάλυψης'] = description_map['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
                
                # Merge με τη συνοπτική αναφορά
                summary_final = summary_final.merge(description_map, on='Κλάδος/Πακέτο Κάλυψης', how='left')
            
            # Αναδιατάσσουμε τις στήλες - Περιγραφή δεξιά από Κλάδος/Πακέτο
            columns_order = ['Κλάδος/Πακέτο Κάλυψης']
            if 'Περιγραφή' in summary_final.columns:
                columns_order.append('Περιγραφή')
            columns_order += ['Από', 'Έως', 'Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες', 
                             'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
            summary_final = summary_final[columns_order]
            
            # Δημιουργούμε αντίγραφο για εμφάνιση με μορφοποίηση
            display_summary = summary_final.copy()
            
            # Εφαρμόζουμε μορφοποίηση νομισμάτων μόνο για εμφάνιση
            display_summary['Μικτές αποδοχές'] = display_summary['Μικτές αποδοχές'].apply(format_currency)
            display_summary['Συνολικές εισφορές'] = display_summary['Συνολικές εισφορές'].apply(format_currency)
            
            # Εφαρμόζουμε ελληνική μορφοποίηση για αριθμητικές στήλες
            numeric_columns_summary = ['Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες', 'Αριθμός Εγγραφών']
            for col in numeric_columns_summary:
                if col in display_summary.columns:
                    # Έτη και Μήνες με 1 δεκαδικό, οι υπόλοιπες χωρίς δεκαδικά
                    decimals = 1 if col in ['Έτη', 'Μήνες'] else 0
                    display_summary[col] = display_summary[col].apply(lambda x: format_number_greek(x, decimals=decimals) if pd.notna(x) and x != '' else x)
            
            # Εμφάνιση του πίνακα
            st.dataframe(
                display_summary,
                use_container_width=True,
                height=600
            )
            render_print_button("print_summary", "Συνοπτική Αναφορά", display_summary)
        else:
            st.warning("Η στήλη 'Κλάδος/Πακέτο Κάλυψης' δεν βρέθηκε στα δεδομένα.")
    
    with tab4:
        # Ετήσια Αναφορά - Ομαδοποίηση με βάση έτος, ταμείο και κλάδο/πακέτο
        st.markdown("### Ετήσια Αναφορά - Ομαδοποίηση κατά Έτος, Ταμείο και Κλάδο/Πακέτο")
        st.info("Σημείωση: Στα αθροίσματα συμπεριλαμβάνονται μόνο τα ποσά σε €. Τα ποσά σε ΔΡΧ (πριν το 2002) εμφανίζονται αλλά δεν υπολογίζονται στα συνολικά.")
        
        if 'Από' in df.columns and 'Ταμείο' in df.columns:
            # Φιλτράρουμε μόνο τις γραμμές με έγκυρες ημερομηνίες
            yearly_df = df.copy()
            yearly_df['Από_DateTime'] = pd.to_datetime(yearly_df['Από'], format='%d/%m/%Y', errors='coerce')
            yearly_df = yearly_df.dropna(subset=['Από_DateTime'])
            
            # Εξαγωγή έτους από την ημερομηνία
            yearly_df['Έτος'] = yearly_df['Από_DateTime'].dt.year

            # Εντοπισμός στήλης Τύπου Αποδοχών με ανθεκτικότητα στο όνομα
            earnings_col = None
            if 'Τύπος Αποδοχών' in yearly_df.columns:
                earnings_col = 'Τύπος Αποδοχών'
            else:
                for c in yearly_df.columns:
                    name = str(c).strip().lower()
                    if ('αποδοχ' in name) and ('τύπος' in name or 'τυπος' in name):
                        earnings_col = c
                        break

            # Φίλτρα (μόνιμα εμφανή, χωρίς τίτλους/expanders)
            y1, y2, y3, y4, y5, y6, y7 = st.columns([1.2, 1.2, 1.6, 1.2, 1.0, 1.0, 0.6])

            with y1:
                if 'Ταμείο' in yearly_df.columns:
                    tameia_opts = ['Όλα'] + sorted(yearly_df['Ταμείο'].dropna().astype(str).unique().tolist())
                    sel_tameia = st.multiselect("Ταμείο:", tameia_opts, default=['Όλα'], key="y_filter_tameio")
                    if 'Όλα' not in sel_tameia:
                        yearly_df = yearly_df[yearly_df['Ταμείο'].isin(sel_tameia)]

            with y2:
                if 'Τύπος Ασφάλισης' in yearly_df.columns:
                    tyas_opts = ['Όλα'] + sorted(yearly_df['Τύπος Ασφάλισης'].dropna().astype(str).unique().tolist())
                    sel_tyas = st.multiselect("Τύπος Ασφάλισης:", tyas_opts, default=['Όλα'], key="y_filter_typos_asfal")
                    if 'Όλα' not in sel_tyas:
                        yearly_df = yearly_df[yearly_df['Τύπος Ασφάλισης'].isin(sel_tyas)]

            with y3:
                if 'Κλάδος/Πακέτο Κάλυψης' in yearly_df.columns:
                    # Δημιουργούμε options με περιγραφές
                    klados_codes = sorted(yearly_df['Κλάδος/Πακέτο Κάλυψης'].dropna().astype(str).unique().tolist())
                    klados_opts_with_desc = ['Όλα']
                    klados_code_map_y = {}
                    
                    for code in klados_codes:
                        if code in description_map and description_map[code]:
                            option_label = f"{code} - {description_map[code]}"
                            klados_opts_with_desc.append(option_label)
                            klados_code_map_y[option_label] = code
                        else:
                            klados_opts_with_desc.append(code)
                            klados_code_map_y[code] = code
                    
                    sel_klados = st.multiselect("Κλάδος/Πακέτο:", klados_opts_with_desc, default=['Όλα'], key="y_filter_klados")
                    
                    if 'Όλα' not in sel_klados:
                        selected_codes = [klados_code_map_y.get(opt, opt) for opt in sel_klados]
                        yearly_df = yearly_df[yearly_df['Κλάδος/Πακέτο Κάλυψης'].isin(selected_codes)]

            with y4:
                if earnings_col and earnings_col in yearly_df.columns:
                    apod_opts = ['Όλα'] + sorted(yearly_df[earnings_col].dropna().astype(str).unique().tolist())
                    sel_apod = st.multiselect("Τύπος Αποδοχών:", apod_opts, default=['Όλα'], key="y_filter_apodochon")
                    if 'Όλα' not in sel_apod:
                        yearly_df = yearly_df[yearly_df[earnings_col].isin(sel_apod)]

            with y5:
                from_y_str = st.text_input("Από (dd/mm/yyyy):", value="", placeholder="01/01/1980", key="y_filter_from_date")
            with y6:
                to_y_str = st.text_input("Έως (dd/mm/yyyy):", value="", placeholder="31/12/2025", key="y_filter_to_date")
            with y7:
                reset_label = "↻"
                if st.button(reset_label, help="Επαναφορά", use_container_width=True, key="y_filter_reset"):
                    for _k in [
                        'y_filter_tameio', 'y_filter_typos_asfal', 'y_filter_klados',
                        'y_filter_apodochon', 'y_filter_from_date', 'y_filter_to_date']:
                        if _k in st.session_state:
                            del st.session_state[_k]
                    st.rerun()

            # Εφαρμογή φίλτρων ημερομηνιών
            if from_y_str or to_y_str:
                try:
                    if from_y_str:
                        from_pd = pd.to_datetime(from_y_str, format='%d/%m/%Y')
                        yearly_df = yearly_df[yearly_df['Από_DateTime'] >= from_pd]
                except Exception:
                    st.warning("Μη έγκυρη ημερομηνία στο πεδίο Από")
                try:
                    if to_y_str:
                        to_pd = pd.to_datetime(to_y_str, format='%d/%m/%Y')
                        yearly_df = yearly_df[yearly_df['Από_DateTime'] <= to_pd]
                except Exception:
                    st.warning("Μη έγκυρη ημερομηνία στο πεδίο Έως")
            
            # Καθαρισμός αριθμητικών στηλών πριν την ομαδοποίηση
            # Για τα ποσά, εξαιρούμε τα ΔΡΧ από τα αθροίσματα
            numeric_columns = ['Έτη', 'Μήνες', 'Ημέρες']
            currency_columns = ['Μικτές αποδοχές', 'Συνολικές εισφορές']
            
            for col in numeric_columns:
                if col in yearly_df.columns:
                    yearly_df[col] = yearly_df[col].apply(clean_numeric_value)
            
            # Για τα νομισματικά ποσά, εξαιρούμε τα ΔΡΧ
            for col in currency_columns:
                if col in yearly_df.columns:
                    yearly_df[col] = yearly_df[col].apply(lambda x: clean_numeric_value(x, exclude_drx=True))
            
            # Ομαδοποίηση με βάση: Έτος, Ταμείο, Κλάδος/Πακέτο και Τύπος Αποδοχών (αν υπάρχει)
            group_keys = ['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης']
            if earnings_col:
                group_keys.append(earnings_col)
            yearly_grouped = yearly_df.groupby(group_keys).agg({
                'Από': 'min',
                'Έως': 'max',
                'Έτη': 'sum',
                'Μήνες': 'sum',
                'Ημέρες': 'sum',
                'Μικτές αποδοχές': 'sum',
                'Συνολικές εισφορές': 'sum'
            }).reset_index()
            
            # Μετράμε τις εγγραφές για κάθε συνδυασμό
            count_keys = ['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης']
            if earnings_col:
                count_keys.append(earnings_col)
            yearly_counts = yearly_df.groupby(count_keys).size().reset_index()
            yearly_counts.columns = count_keys + ['Αριθμός Εγγραφών']
            
            # Συνδυάζουμε τα δεδομένα
            yearly_final = yearly_grouped.merge(yearly_counts, on=count_keys, how='left')

            # Μετατρέπουμε σε ακέραιους όπου απαιτείται για καθαρή εμφάνιση
            for int_col in ['Έτη', 'Μήνες', 'Ημέρες', 'Αριθμός Εγγραφών']:
                if int_col in yearly_final.columns:
                    yearly_final[int_col] = yearly_final[int_col].fillna(0).astype(int)

            # Σύνοψη Τύπου Ασφάλισης ανά (Έτος, Ταμείο)
            if 'Τύπος Ασφάλισης' in yearly_df.columns:
                insurance_summary = (
                    yearly_df.groupby(['Έτος', 'Ταμείο'])['Τύπος Ασφάλισης']
                    .apply(lambda s: ' / '.join(sorted(pd.Series(s.dropna().astype(str).unique()))))
                    .reset_index()
                    .rename(columns={'Τύπος Ασφάλισης': 'Τύπος Ασφάλισης (Σύνοψη)'})
                )
                yearly_final = yearly_final.merge(insurance_summary, on=['Έτος', 'Ταμείο'], how='left')

            # Κανονικοποίηση ονόματος στήλης τύπου αποδοχών για εμφάνιση
            if earnings_col and earnings_col != 'Τύπος Αποδοχών' and earnings_col in yearly_final.columns:
                yearly_final = yearly_final.rename(columns={earnings_col: 'Τύπος Αποδοχών'})
            
            # Αναδιατάσσουμε τις στήλες: Έτος, Ταμείο, Τύπος Ασφάλισης, Κλάδος/Πακέτο, Από, Έως, Τύπος Αποδοχών, συνολικά
            display_order = ['Έτος', 'Ταμείο']
            if 'Τύπος Ασφάλισης (Σύνοψη)' in yearly_final.columns:
                display_order.append('Τύπος Ασφάλισης (Σύνοψη)')
            display_order += ['Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως']
            if 'Τύπος Αποδοχών' in yearly_final.columns:
                display_order.append('Τύπος Αποδοχών')
            display_order += ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
            yearly_final = yearly_final[display_order]
            
            # Ταξινομούμε πρώτα ανά έτος, μετά ανά ταμείο, μετά ανά κλάδο
            sort_keys = ['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης']
            if 'Τύπος Αποδοχών' in yearly_final.columns:
                sort_keys.append('Τύπος Αποδοχών')
            yearly_final = yearly_final.sort_values(sort_keys)
            
            # Δημιουργούμε αντίγραφο για εμφάνιση με μορφοποίηση και βελτιωμένη εμφάνιση
            display_yearly = yearly_final.copy()
            
            # Εφαρμόζουμε μορφοποίηση νομισμάτων μόνο για εμφάνιση
            display_yearly['Μικτές αποδοχές'] = display_yearly['Μικτές αποδοχές'].apply(format_currency)
            display_yearly['Συνολικές εισφορές'] = display_yearly['Συνολικές εισφορές'].apply(format_currency)
            
            # Βελτιώνουμε την εμφάνιση για καλύτερη αναγνωσιμότητα
            # Δημιουργούμε μια νέα στήλη για εμφάνιση με κενά όπου επαναλαμβάνονται τα έτη/ταμεία
            display_yearly_detailed = display_yearly.copy()
            
            # Αφαιρούμε επαναλαμβανόμενα έτη (με σωστό data type)
            display_yearly_detailed['Έτος_Display'] = display_yearly_detailed['Έτος'].astype(str)
            for i in range(1, len(display_yearly_detailed)):
                if display_yearly_detailed.iloc[i]['Έτος'] == display_yearly_detailed.iloc[i-1]['Έτος']:
                    display_yearly_detailed.iloc[i, display_yearly_detailed.columns.get_loc('Έτος_Display')] = ''
            
            # Αφαιρούμε επαναλαμβανόμενα ταμεία
            display_yearly_detailed['Ταμείο_Display'] = display_yearly_detailed['Ταμείο'].astype(str)
            for i in range(1, len(display_yearly_detailed)):
                if (display_yearly_detailed.iloc[i]['Έτος'] == display_yearly_detailed.iloc[i-1]['Έτος'] and 
                    display_yearly_detailed.iloc[i]['Ταμείο'] == display_yearly_detailed.iloc[i-1]['Ταμείο']):
                    display_yearly_detailed.iloc[i, display_yearly_detailed.columns.get_loc('Ταμείο_Display')] = ''

            # Αφαιρούμε επαναλαμβανόμενο «Τύπος Ασφάλισης (Σύνοψη)» ανά (Έτος, Ταμείο)
            if 'Τύπος Ασφάλισης (Σύνοψη)' in display_yearly_detailed.columns:
                display_yearly_detailed['Τύπος_Ασφάλισης_Display'] = display_yearly_detailed['Τύπος Ασφάλισης (Σύνοψη)'].fillna('').astype(str)
                for i in range(1, len(display_yearly_detailed)):
                    same_group = (
                        display_yearly_detailed.iloc[i]['Έτος'] == display_yearly_detailed.iloc[i-1]['Έτος'] and
                        display_yearly_detailed.iloc[i]['Ταμείο'] == display_yearly_detailed.iloc[i-1]['Ταμείο']
                    )
                    if same_group:
                        display_yearly_detailed.iloc[i, display_yearly_detailed.columns.get_loc('Τύπος_Ασφάλισης_Display')] = ''
            
            # Προσθήκη γραμμών "Σύνολο <Έτος>" με αθροίσματα ανά έτος (δυναμικά με βάση τα φίλτρα)
            totals_rows = []
            for year_value in sorted(yearly_final['Έτος'].unique()):
                # Επιλεγμένες γραμμές του συγκεκριμένου έτους από τον πίνακα εμφάνισης
                year_rows_disp = display_yearly_detailed[display_yearly_detailed['Έτος'] == year_value]
                # Προσθήκη των κανονικών γραμμών για το έτος
                totals_rows.append(year_rows_disp)
                # Υπολογισμός αθροισμάτων από τον μη-μορφοποιημένο πίνακα
                yr_mask = yearly_final['Έτος'] == year_value
                sum_years = yearly_final.loc[yr_mask, 'Έτη'].sum() if 'Έτη' in yearly_final.columns else 0
                sum_months = yearly_final.loc[yr_mask, 'Μήνες'].sum() if 'Μήνες' in yearly_final.columns else 0
                sum_days = yearly_final.loc[yr_mask, 'Ημέρες'].sum() if 'Ημέρες' in yearly_final.columns else 0
                sum_gross = yearly_final.loc[yr_mask, 'Μικτές αποδοχές'].sum() if 'Μικτές αποδοχές' in yearly_final.columns else 0
                sum_contrib = yearly_final.loc[yr_mask, 'Συνολικές εισφορές'].sum() if 'Συνολικές εισφορές' in yearly_final.columns else 0
                sum_count = yearly_final.loc[yr_mask, 'Αριθμός Εγγραφών'].sum() if 'Αριθμός Εγγραφών' in yearly_final.columns else 0

                # Δημιουργία γραμμής συνόλου σε επίπεδο εμφάνισης
                total_row = {col: '' for col in display_yearly_detailed.columns}
                # Στήλες εμφάνισης για έτος/ταμείο/τύπος ασφάλισης
                if 'Έτος_Display' in total_row:
                    total_row['Έτος_Display'] = ''
                if 'Ταμείο_Display' in total_row:
                    total_row['Ταμείο_Display'] = ''
                if 'Τύπος_Ασφάλισης_Display' in total_row:
                    total_row['Τύπος_Ασφάλισης_Display'] = ''
                # Το "Σύνολο ΧΧΧΧ" πηγαίνει στη στήλη Έως
                if 'Έως' in total_row:
                    total_row['Έως'] = f"Σύνολο {int(year_value)}"
                # Αθροιστικές στήλες
                if 'Έτη' in total_row:
                    total_row['Έτη'] = int(sum_years)
                if 'Μήνες' in total_row:
                    total_row['Μήνες'] = int(sum_months)
                if 'Ημέρες' in total_row:
                    total_row['Ημέρες'] = int(sum_days)
                if 'Μικτές αποδοχές' in total_row:
                    total_row['Μικτές αποδοχές'] = format_currency(sum_gross)
                if 'Συνολικές εισφορές' in total_row:
                    total_row['Συνολικές εισφορές'] = format_currency(sum_contrib)
                if 'Αριθμός Εγγραφών' in total_row:
                    total_row['Αριθμός Εγγραφών'] = int(sum_count)

                totals_rows.append(pd.DataFrame([total_row], columns=display_yearly_detailed.columns))

            # Ενοποίηση με τις γραμμές συνόλων ανά έτος
            if totals_rows:
                display_yearly_detailed = pd.concat(totals_rows, ignore_index=True)

            # Αναδιατάσσουμε τις στήλες για εμφάνιση
            display_columns = ['Έτος_Display', 'Ταμείο_Display']
            if 'Τύπος_Ασφάλισης_Display' in display_yearly_detailed.columns:
                display_columns.append('Τύπος_Ασφάλισης_Display')
            display_columns += ['Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως']
            if 'Τύπος Αποδοχών' in display_yearly_detailed.columns:
                display_columns.append('Τύπος Αποδοχών')
            display_columns += ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
            
            # Δημιουργούμε τον τελικό πίνακα για εμφάνιση
            display_final = display_yearly_detailed[display_columns].copy()
            
            # Μετονομάζουμε τις στήλες για εμφάνιση
            final_headers = ['Έτος', 'Ταμείο']
            if 'Τύπος_Ασφάλισης_Display' in display_yearly_detailed.columns:
                final_headers.append('Τύπος Ασφάλισης')
            final_headers += ['Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως']
            if 'Τύπος Αποδοχών' in display_yearly_detailed.columns:
                final_headers.append('Τύπος Αποδοχών')
            final_headers += ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές Αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
            display_final.columns = final_headers
            
            # Εφαρμόζουμε ελληνική μορφοποίηση για αριθμητικές στήλες
            numeric_cols_yearly = ['Έτη', 'Μήνες', 'Ημέρες', 'Αριθμός Εγγραφών']
            for col in numeric_cols_yearly:
                if col in display_final.columns:
                    # Έτη και Μήνες με 1 δεκαδικό, οι υπόλοιπες χωρίς δεκαδικά
                    decimals = 1 if col in ['Έτη', 'Μήνες'] else 0
                    display_final[col] = display_final[col].apply(lambda x: format_number_greek(x, decimals=decimals) if pd.notna(x) and x != '' and str(x).strip() != '' else x)
            
            # Στυλ για γραμμές "Σύνολο <Έτος>" και σκούρα γραμματοσειρά στη στήλη Έτος
            def _highlight_totals(row):
                value = str(row.get('Έως', ''))
                styles = []
                
                # Βρίσκουμε τη θέση της στήλης "Έως"
                eos_index = list(row.index).index('Έως') if 'Έως' in row.index else -1
                
                if value.startswith('Σύνολο'):
                    # Για κάθε στήλη
                    for i, col_name in enumerate(row.index):
                        if i >= eos_index and eos_index != -1:
                            # Από "Έως" και δεξιότερα: μπλε background
                            styles.append('background-color: #e6f2ff; color: #000000; font-weight: 700;')
                        else:
                            # Αριστερά από "Έως": χωρίς background
                            styles.append('font-weight: 700;')
                else:
                    styles = [''] * len(row)
                
                return styles
            
            def _bold_year_column(row):
                styles = [''] * len(row)
                # Η στήλη Έτος είναι η πρώτη (index 0)
                styles[0] = 'font-weight: bold; color: #000000;'
                return styles

            try:
                styled = display_final.style.apply(_highlight_totals, axis=1).apply(_bold_year_column, axis=1)
                st.dataframe(
                    styled,
                    use_container_width=True,
                    height=600
                )
            except Exception:
                # Fallback χωρίς χρωματισμό για να διατηρηθούν search/download/expand & scroll
                st.dataframe(
                    display_final,
                    use_container_width=True,
                    height=600
                )
            render_print_button("print_yearly", "Ετήσια Αναφορά", display_final)
            
            # Στατιστικά
            st.markdown("#### Στατιστικά Ετήσιας Αναφοράς")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Συνολικά Έτη", yearly_final['Έτος'].nunique())
            with col2:
                st.metric("Συνολικά Ταμεία", yearly_final['Ταμείο'].nunique())
            with col3:
                total_records = yearly_final['Αριθμός Εγγραφών'].sum()
                st.metric("Συνολικές Εγγραφές", total_records)
            with col4:
                total_years = yearly_final['Έτη'].sum()
                st.metric("Συνολικά Έτη Ασφάλισης", total_years)
                
        else:
            st.warning("Οι στήλες 'Από' ή 'Ταμείο' δεν βρέθηκαν στα δεδομένα.")
    
    with tab5:
        # Αναφορά Ημερών Ασφάλισης ανά Έτος και Διάστημα, με στήλες τα Πακέτα Κάλυψης
        st.markdown("### Αναφορά Ημερών Ασφάλισης (Έτος × Διάστημα × Πακέτα)")

        if 'Από' in df.columns and 'Έως' in df.columns:
            days_df = df.copy()
            days_df['Από_DateTime'] = pd.to_datetime(days_df['Από'], format='%d/%m/%Y', errors='coerce')
            days_df['Έως_DateTime'] = pd.to_datetime(days_df['Έως'], format='%d/%m/%Y', errors='coerce')
            days_df = days_df.dropna(subset=['Από_DateTime', 'Έως_DateTime'])
            days_df['Έτος'] = days_df['Από_DateTime'].dt.year

            # Φίλτρα και παράμετρος σε μία γραμμή: Ταμείο | Από | Έως | Επαναφορά | Συντελεστές
            f1, f2, f3, f4, f5 = st.columns([1.6, 1.0, 1.0, 0.5, 1.6])
            with f1:
                if 'Ταμείο' in days_df.columns:
                    tameia_opts = ['Όλα'] + sorted(days_df['Ταμείο'].dropna().astype(str).unique().tolist())
                    sel_tameia = st.multiselect('Ταμείο:', tameia_opts, default=['Όλα'], key='insdays_filter_tameio')
                    if 'Όλα' not in sel_tameia:
                        days_df = days_df[days_df['Ταμείο'].isin(sel_tameia)]
            with f2:
                from_str = st.text_input('Από (dd/mm/yyyy):', value='', placeholder='01/01/1980', key='insdays_filter_from')
            with f3:
                to_str = st.text_input('Έως (dd/mm/yyyy):', value='', placeholder='31/12/2025', key='insdays_filter_to')
            with f4:
                reset_label = "↻"
                if st.button(reset_label, help='Επαναφορά', use_container_width=True, key='insdays_filter_reset'):
                    # Καθαρισμός κατάστασης widgets ώστε να επανέλθουν στις προεπιλογές
                    for _k in ['insdays_filter_tameio', 'insdays_filter_from', 'insdays_filter_to', 'ins_days_basis']:
                        if _k in st.session_state:
                            del st.session_state[_k]
                    st.rerun()
            with f5:
                # Επιλογή συντελεστών υπολογισμού ημερών από μήνες/έτη
                basis = st.selectbox(
                    "Συντελεστές υπολογισμού:",
                    options=["Μήνας = 25, Έτος = 300", "Μήνας = 30, Έτος = 360"],
                    index=0,
                    help=None,
                    key="ins_days_basis"
                )

            # Εφαρμογή φίλτρων ημερομηνίας
            if from_str:
                try:
                    from_dt = pd.to_datetime(from_str, format='%d/%m/%Y')
                    days_df = days_df[days_df['Από_DateTime'] >= from_dt]
                except Exception:
                    st.warning('Μη έγκυρη ημερομηνία στο πεδίο Από')
            if to_str:
                try:
                    to_dt = pd.to_datetime(to_str, format='%d/%m/%Y')
                    days_df = days_df[days_df['Από_DateTime'] <= to_dt]
                except Exception:
                    st.warning('Μη έγκυρη ημερομηνία στο πεδίο Έως')

            # Ανάγνωση της επιλογής συντελεστών (έχει ήδη δημιουργηθεί στο ίδιο row)
            if basis.startswith("Μήνας = 30"):
                month_days, year_days = 30, 360
            else:
                month_days, year_days = 25, 300

            # Καθαρισμός αριθμητικών
            for col in ['Ημέρες', 'Μήνες', 'Έτη']:
                if col in days_df.columns:
                    days_df[col] = days_df[col].apply(clean_numeric_value)
                else:
                    days_df[col] = 0.0

            # Υπολογισμός μονάδων ανά γραμμή (πάντα άθροισμα σε ημέρες)
            days_df['Μονάδες'] = days_df['Ημέρες'] + (days_df['Μήνες'] * month_days) + (days_df['Έτη'] * year_days)

            # Ετικέτα διαστήματος
            days_df['Διάστημα'] = days_df['Από_DateTime'].dt.strftime('%d/%m/%Y') + ' - ' + days_df['Έως_DateTime'].dt.strftime('%d/%m/%Y')

            # Έλεγχος ότι υπάρχει στήλη πακέτου
            pkg_col = 'Κλάδος/Πακέτο Κάλυψης'
            if pkg_col not in days_df.columns:
                st.warning("Η στήλη 'Κλάδος/\\nΠακέτο\\nΚάλυψης' δεν βρέθηκε στα δεδομένα.")
            else:
                # Ομαδοποίηση πρώτα ανά Έτος-Διάστημα-Πακέτο
                grouped = (
                    days_df.groupby(['Έτος', 'Διάστημα', pkg_col], dropna=False)['Μονάδες']
                    .sum()
                    .reset_index()
                )

                # Pivot: γραμμές το Έτος + Διάστημα, στήλες τα Πακέτα, τιμές οι Μονάδες
                pivot = grouped.pivot_table(
                    index=['Έτος', 'Διάστημα'],
                    columns=pkg_col,
                    values='Μονάδες',
                    aggfunc='sum',
                    fill_value=0.0,
                )
                pivot = pivot.reset_index()

                # Ταξινόμηση με βάση Έτος και πραγματική ημερομηνία «Από» μέσα στο διάστημα
                # Εξαγωγή ημερομηνίας έναρξης από την ετικέτα για ακριβή ταξινόμηση
                try:
                    pivot['_start_dt'] = pd.to_datetime(pivot['Διάστημα'].str.split(' - ').str[0], format='%d/%m/%Y')
                    pivot = pivot.sort_values(['Έτος', '_start_dt']).drop(columns=['_start_dt'])
                except Exception:
                    pivot = pivot.sort_values(['Έτος', 'Διάστημα'])

                # Εισαγωγή γραμμών «Σύνολο <Έτος>» και συνολικό σύνολο όλων των ετών στην αρχή
                package_cols = [c for c in pivot.columns if c not in ['Έτος', 'Διάστημα']]
                final_blocks = []

                # Συνολικό σύνολο όλων των ετών (στην αρχή)
                grand_totals = {col: int(round(pivot[col].sum())) for col in package_cols}
                grand_row = {'Έτος': '', 'Διάστημα': 'Σύνολο Όλων των Ετών'}
                grand_row.update(grand_totals)
                # Προσθήκη συνόλου ημερών για τη γραμμή grand total
                grand_row['Σύνολο Ημερών'] = sum(grand_totals.values())
                # Προσαρμογή των στηλών για να περιλαμβάνει τη νέα στήλη
                pivot_with_total_col = list(pivot.columns) + ['Σύνολο Ημερών']
                final_blocks.append(pd.DataFrame([grand_row], columns=pivot_with_total_col))

                # Κατά έτος μπλοκ και σύνολο
                for yr in sorted(pivot['Έτος'].unique()):
                    yr_rows = pivot[pivot['Έτος'] == yr].copy()
                    # Προσθήκη στήλης Σύνολο Ημερών στις κανονικές γραμμές
                    yr_rows['Σύνολο Ημερών'] = yr_rows[package_cols].sum(axis=1)
                    final_blocks.append(yr_rows)
                    totals = {col: int(round(yr_rows[col].sum())) for col in package_cols}
                    total_row = {'Έτος': '', 'Διάστημα': f"Σύνολο {int(yr)}"}
                    total_row.update(totals)
                    # Προσθήκη συνόλου ημερών για τη γραμμή ετήσιου συνόλου
                    total_row['Σύνολο Ημερών'] = sum(totals.values())
                    final_blocks.append(pd.DataFrame([total_row], columns=pivot_with_total_col))

                display_days = pd.concat(final_blocks, ignore_index=True) if final_blocks else pivot.copy()

                # Αν δεν υπάρχει ήδη η στήλη "Σύνολο Ημερών", την προσθέτουμε
                if 'Σύνολο Ημερών' not in display_days.columns:
                    display_days['Σύνολο Ημερών'] = display_days[package_cols].sum(axis=1)

                # Μετατροπή τιμών σε ακέραιους για καθαρή εμφάνιση
                for col in package_cols + ['Σύνολο Ημερών']:
                    display_days[col] = display_days[col].fillna(0).round(0).astype(int)

                # Καλύτερη εμφάνιση επαναλαμβανόμενου έτους
                display_days['Έτος_Display'] = display_days['Έτος'].astype(str)
                for i in range(1, len(display_days)):
                    if str(display_days.iloc[i-1]['Έτος']).isdigit() and display_days.iloc[i]['Έτος'] == display_days.iloc[i-1]['Έτος']:
                        display_days.iloc[i, display_days.columns.get_loc('Έτος_Display')] = ''

                # Τελικός πίνακας εμφάνισης - η στήλη "Σύνολο Ημερών" να είναι 3η στη σειρά
                disp_cols = ['Έτος_Display', 'Διάστημα', 'Σύνολο Ημερών'] + package_cols
                display_final_days = display_days[disp_cols].copy()
                display_final_days.columns = ['Έτος', 'Διάστημα', 'Σύνολο Ημερών'] + package_cols

                # Στυλ για γραμμές «Σύνολο <Έτος>»
                def _highlight_totals_days(row):
                    value = str(row.get('Διάστημα', ''))
                    if value.startswith('Σύνολο'):
                        return ['background-color: #e6f2ff; color: #000000; font-weight: 700;'] * len(row)
                    return [''] * len(row)

                # Προβολή: κενά αντί για μηδενικές τιμές μέσω Styler.format με ελληνική μορφοποίηση
                def _blank_zero(x):
                    try:
                        if float(x) == 0:
                            return ''
                        # Χρήση ελληνικής μορφοποίησης για αριθμούς >= 1000
                        num = int(round(float(x)))
                        return format_number_greek(num, decimals=0)
                    except Exception:
                        return ''

                try:
                    # Formatter για μηδενικές τιμές και bold για στήλη Έτος
                    formatter = {col: _blank_zero for col in package_cols + ['Σύνολο Ημερών']}
                    
                    # Συνάρτηση για bold στη στήλη Έτος
                    def _bold_year_column(row):
                        styles = [''] * len(row)
                        # Η στήλη Έτος είναι η πρώτη (index 0)
                        styles[0] = 'font-weight: bold;'
                        return styles
                    
                    styled_days = (
                        display_final_days
                        .style
                        .apply(_highlight_totals_days, axis=1)
                        .apply(_bold_year_column, axis=1)
                        .format(formatter)
                    )
                    st.dataframe(styled_days, use_container_width=True, height=600)
                except Exception:
                    # Fallback χωρίς ειδική μορφοποίηση
                    st.dataframe(display_final_days, use_container_width=True, height=600)

                # Κουμπί εκτύπωσης (με κενά για μηδενικές τιμές)
                print_days = display_final_days.copy()
                # Εφαρμογή κενών για μηδενικές τιμές σε όλες τις αριθμητικές στήλες
                for col in ['Σύνολο Ημερών'] + package_cols:
                    print_days[col] = print_days[col].apply(lambda v: '' if pd.isna(v) or float(v) == 0 else int(round(float(v))))
                render_print_button("print_ins_days", "Αναφορά Ημερών Ασφάλισης", print_days)
        else:
            st.warning("Οι στήλες 'Από' και 'Έως' δεν βρέθηκαν στα δεδομένα.")
    
    with tab6:
        # Αναφορά Κενών Διαστήματων
        st.markdown("### Αναφορά Κενών Διαστήματων")
        st.info("Σκοπός: Εντοπίζει χρονικά διαστήματα που δεν καλύπτονται από κανένα ασφαλιστικό διάστημα.")
        
        if 'Από' in df.columns and 'Έως' in df.columns:
            # Εντοπισμός κενών διαστημάτων
            gaps_df = find_gaps_in_insurance_data(df)
            
            if not gaps_df.empty:
                st.markdown("#### Εντοπισμένα Κενά Διαστήματα")
                
                # Στατιστικά
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Συνολικά Κενά", len(gaps_df))
                with col2:
                    total_days = gaps_df['Ημερολογιακές ημέρες'].sum()
                    st.metric("Συνολικές Ημερολογιακές Ημέρες", format_number_greek(total_days, decimals=0))
                with col3:
                    total_months = gaps_df['Μήνες'].sum()
                    st.metric("Συνολικοί Μήνες", format_number_greek(total_months, decimals=1))
                with col4:
                    total_years = gaps_df['Έτη'].sum()
                    st.metric("Συνολικά Έτη", format_number_greek(total_years, decimals=1))
                
                # Δημιουργούμε αντίγραφο για εμφάνιση με μορφοποίηση
                display_gaps = gaps_df.copy()
                
                # Εφαρμόζουμε ελληνική μορφοποίηση για αριθμητικές στήλες
                numeric_cols_gaps = ['Ημερολογιακές ημέρες', 'Μήνες', 'Έτη']
                for col in numeric_cols_gaps:
                    if col in display_gaps.columns:
                        # Μήνες και Έτη με 1 δεκαδικό, ημέρες χωρίς δεκαδικά
                        decimals = 1 if col in ['Μήνες', 'Έτη'] else 0
                        display_gaps[col] = display_gaps[col].apply(lambda x: format_number_greek(x, decimals=decimals) if pd.notna(x) and x != '' else x)
                
                # Εμφάνιση πίνακα
                st.dataframe(
                    display_gaps,
                    use_container_width=True,
                    height=600
                )
                
                # Κουμπί εκτύπωσης
                render_print_button("print_gaps", "Κενά Διαστήματα", gaps_df)
                
                # Συμβουλές
                st.markdown("#### Συμβουλές")
                if len(gaps_df) > 0:
                    st.warning("Σημαντικό: Τα εντοπισμένα κενά διαστήματα μπορεί να επηρεάσουν τη θεμελίωση δικαιώματος για σύνταξη.")
                    
                    # Εμφάνιση του μεγαλύτερου κενού
                    max_gap = gaps_df.loc[gaps_df['Ημερολογιακές ημέρες'].idxmax()]
                    st.info(f"Μεγαλύτερο κενό: {max_gap['Από']} - {max_gap['Έως']} ({max_gap['Ημερολογιακές ημέρες']} ημερολογιακές ημέρες)")
            else:
                st.success("Καμία κενή περίοδος δεν εντοπίστηκε. Όλα τα διαστήματα είναι συνεχή.")
                st.info("Σημείωση: Αυτό σημαίνει ότι δεν υπάρχουν κενά μεταξύ των ασφαλιστικών σας περιόδων.")
        else:
            st.warning("Οι στήλες 'Από' και 'Έως' δεν βρέθηκαν στα δεδομένα.")
    
    # Download section
    st.markdown("---")
    st.markdown("### Κατέβασμα Αποτελεσμάτων")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download για κύρια δεδομένα (μόνο με ημερομηνίες, ταξινομημένα χρονολογικά)
        main_output = io.BytesIO()
        with pd.ExcelWriter(main_output, engine='openpyxl') as writer:
            main_df.to_excel(writer, sheet_name='Κύρια_Δεδομένα', index=False)
        
        main_output.seek(0)
        
        if filename.endswith('.pdf'):
            main_filename = filename[:-4] + '_κύρια_δεδομένα.xlsx'
        else:
            main_filename = 'efka_κύρια_δεδομένα.xlsx'
        
        st.download_button(
            label="Κύρια Δεδομένα (Excel)",
            data=main_output.getvalue(),
            file_name=main_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        # Download για όλα τα δεδομένα
        all_output = io.BytesIO()
        with pd.ExcelWriter(all_output, engine='openpyxl') as writer:
            # Φιλτράρουμε και ταξινομούμε όλα τα δεδομένα
            all_df_sorted = df.copy()
            if 'Από' in all_df_sorted.columns:
                all_df_sorted['Από_DateTime'] = pd.to_datetime(all_df_sorted['Από'], format='%d/%m/%Y', errors='coerce')
                # Φιλτράρουμε μόνο τις γραμμές με έγκυρη ημερομηνία
                all_df_sorted = all_df_sorted.dropna(subset=['Από_DateTime'])
                all_df_sorted = all_df_sorted.sort_values('Από_DateTime', na_position='last')
                all_df_sorted = all_df_sorted.drop('Από_DateTime', axis=1)
            
            all_df_sorted.to_excel(writer, sheet_name='Όλα_Δεδομένα', index=False)
            if extra_columns and not extra_df.empty:
                extra_df.to_excel(writer, sheet_name='Επιπλέον_Πίνακες', index=False)
            
            # Προσθήκη Συνοπτικής Αναφοράς
            if 'Κλάδος/Πακέτο Κάλυψης' in df.columns:
                summary_df = df.copy()
                if 'Από' in summary_df.columns:
                    summary_df['Από_DateTime'] = pd.to_datetime(summary_df['Από'], format='%d/%m/%Y', errors='coerce')
                    summary_df = summary_df.dropna(subset=['Από_DateTime'])
                
                grouped = summary_df.groupby('Κλάδος/Πακέτο Κάλυψης').agg({
                    'Από': 'min',
                    'Έως': 'max',
                    'Έτη': 'sum',
                    'Μήνες': 'sum',
                    'Ημέρες': 'sum',
                    'Μικτές αποδοχές': 'sum',
                    'Συνολικές εισφορές': 'sum'
                }).reset_index()
                
                record_counts = summary_df['Κλάδος/Πακέτο Κάλυψης'].value_counts().reset_index()
                record_counts.columns = ['Κλάδος/Πακέτο Κάλυψης', 'Αριθμός Εγγραφών']
                
                summary_final = grouped.merge(record_counts, on='Κλάδος/Πακέτο Κάλυψης', how='left')
                summary_final = summary_final[['Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως', 'Έτη', 'Μήνες', 'Ημέρες', 
                                             'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']]
                
                summary_final.to_excel(writer, sheet_name='Συνοπτική_Αναφορά', index=False)
                
                # Προσθήκη ετήσιας αναφοράς στο Excel (με νέα δομή: Έτος, Ταμείο, Κλάδος/Πακέτο)
                if 'Από' in df.columns and 'Ταμείο' in df.columns:
                    yearly_df = df.copy()
                    yearly_df['Από_DateTime'] = pd.to_datetime(yearly_df['Από'], format='%d/%m/%Y', errors='coerce')
                    yearly_df = yearly_df.dropna(subset=['Από_DateTime'])
                    yearly_df['Έτος'] = yearly_df['Από_DateTime'].dt.year
                    
                    # Καθαρισμός αριθμητικών στηλών
                    numeric_columns = ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές']
                    for col in numeric_columns:
                        if col in yearly_df.columns:
                            yearly_df[col] = yearly_df[col].apply(clean_numeric_value)
                    
                    # Ομαδοποίηση με βάση έτος, ταμείο και κλάδο/πακέτο κάλυψης
                    yearly_grouped = yearly_df.groupby(['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης']).agg({
                        'Από': 'min',
                        'Έως': 'max',
                        'Έτη': 'sum',
                        'Μήνες': 'sum',
                        'Ημέρες': 'sum',
                        'Μικτές αποδοχές': 'sum',
                        'Συνολικές εισφορές': 'sum'
                    }).reset_index()
                    
                    # Μετράμε τις εγγραφές για κάθε έτος, ταμείο και κλάδο
                    yearly_counts = yearly_df.groupby(['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης']).size().reset_index()
                    yearly_counts.columns = ['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης', 'Αριθμός Εγγραφών']
                    
                    # Συνδυάζουμε τα δεδομένα
                    yearly_final = yearly_grouped.merge(yearly_counts, on=['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης'], how='left')
                    
                    # Αναδιατάσσουμε τις στήλες (πρώτα Έτος, μετά Ταμείο, μετά Κλάδος/Πακέτο)
                    yearly_final = yearly_final[['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως', 'Έτη', 'Μήνες', 'Ημέρες', 
                                               'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']]
                    
                    # Ταξινομούμε πρώτα ανά έτος, μετά ανά ταμείο, μετά ανά κλάδο
                    yearly_final = yearly_final.sort_values(['Έτος', 'Ταμείο', 'Κλάδος/Πακέτο Κάλυψης'])
                    
                    yearly_final.to_excel(writer, sheet_name='Ετήσια_Αναφορά', index=False)
                
                # Προσθήκη αναφοράς κενών διαστημάτων στο Excel
                gaps_df = find_gaps_in_insurance_data(df)
                if not gaps_df.empty:
                    gaps_df.to_excel(writer, sheet_name='Κενά_Διαστήματα', index=False)
        
        all_output.seek(0)
        
        if filename.endswith('.pdf'):
            all_filename = filename[:-4] + '_όλα_δεδομένα.xlsx'
        else:
            all_filename = 'efka_όλα_δεδομένα.xlsx'
        
        st.download_button(
            label="Όλα τα Δεδομένα (Excel)",
            data=all_output.getvalue(),
            file_name=all_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # Footer
    st.markdown("---")
    st.markdown("### Πληροφορίες")
    st.info("""
    **Τι περιέχει το Excel αρχείο:**
    - Όλα τα δεδομένα από όλες τις σελίδες
    - Στήλη 'Σελίδα' που δείχνει από ποια σελίδα προέρχεται κάθε γραμμή
    - Στήλη 'Πίνακας' (αν υπάρχει) που δείχνει τον αριθμό πίνακα
    - Τα δεδομένα παραμένουν ακατέργαστα όπως εξήχθησαν από το PDF
    """)
    
    # JavaScript για τα menu links
    st.markdown("""
    <script>
    function resetToHome() {
        // Reset session state και επιστροφή στην αρχική
        window.location.reload();
    }
    
    function resetToNewFile() {
        // Reset session state και επιστροφή στην αρχική
        window.location.reload();
    }
    </script>
    """, unsafe_allow_html=True)

def main():
    """Κύρια συνάρτηση της εφαρμογής"""
    
    # Αρχική κατάσταση - ανέβασμα αρχείου
    if 'file_uploaded' not in st.session_state:
        st.session_state['file_uploaded'] = False
    if 'processing_done' not in st.session_state:
        st.session_state['processing_done'] = False
    if 'show_results' not in st.session_state:
        st.session_state['show_results'] = False
    if 'show_filters' not in st.session_state:
        st.session_state['show_filters'] = False
    if 'filters_applied' not in st.session_state:
        st.session_state['filters_applied'] = False
    if 'filter_logic' not in st.session_state:
        st.session_state['filter_logic'] = 'AND'
    
    # Εμφάνιση αποτελεσμάτων αν υπάρχουν
    if st.session_state.get('show_results', False) and 'extracted_data' in st.session_state:
        df = st.session_state['extracted_data']
        filename = st.session_state.get('filename', 'extracted_data.pdf')
        show_results_page(df, filename)
        return
    
    # Μωβ Header - Full Width
    st.markdown('''
        <div class="purple-header">
            Ασφαλιστικό βιογραφικό ΑΤΛΑΣ
        </div>
    ''', unsafe_allow_html=True)
    
    # Εμφάνιση ανεβάσματος αρχείου
    if not st.session_state['file_uploaded']:
        # Προτροπή και Upload Button - Κεντρικό 30%
        st.markdown('<div class="upload-container">', unsafe_allow_html=True)
        st.markdown('<p class="upload-prompt">Ανεβάστε το pdf αρχείο από τον ΕΦΚΑ</p>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Επιλέξτε PDF αρχείο",
            type=['pdf'],
            help="Ανεβάστε το PDF αρχείο e‑EFKA",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            st.session_state['uploaded_file'] = uploaded_file
            st.session_state['filename'] = uploaded_file.name
            st.session_state['file_uploaded'] = True
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Οδηγίες σε πλαίσιο - Κεντρικό 30%
        st.markdown('''
            <div class="instructions-box">
                <div class="instructions-title">Οδηγίες</div>
                <div class="instructions-list">
                    • Κατεβάστε το PDF του Ασφαλιστικού βιογραφικού από τον e‑EFKA<br>
                    • Προτείνεται Chrome/Edge για καλύτερη συμβατότητα<br>
                    • Ανεβάστε το αρχείο από τη φόρμα παραπάνω<br>
                    • Πατήστε το κουμπί "Επεξεργασία" για ανάλυση των δεδομένων<br>
                    • Μετά την επεξεργασία θα εμφανιστούν αναλυτικά αποτελέσματα<br>
                    • Τα δεδομένα επεξεργάζονται τοπικά και δεν αποθηκεύονται
                </div>
            </div>
        ''', unsafe_allow_html=True)
    
    # Εμφάνιση κουμπιού αναζήτησης
    elif not st.session_state['processing_done']:
        st.markdown('<div class="app-container upload-section">', unsafe_allow_html=True)
        st.markdown("### Επιλεγμένο αρχείο")
        st.success(f"{st.session_state['uploaded_file'].name}")
        st.info(f"Μέγεθος: {st.session_state['uploaded_file'].size:,} bytes")
        
        if st.button("Επεξεργασία", type="primary"):
            st.session_state['processing_done'] = True
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Οδηγίες σε πλαίσιο - Κεντρικό 30%
        st.markdown('''
            <div class="instructions-box">
                <div class="instructions-title">Οδηγίες</div>
                <div class="instructions-list">
                    • Κατεβάστε το PDF του Ασφαλιστικού βιογραφικ από τον e‑EFKA<br>
                    • Προτείνεται Chrome/Edge για καλύτερη συμβατότητα<br>
                    • Ανεβάστε το αρχείο από τη φόρμα παραπάνω<br>
                    • Πατήστε το κουμπί "αναζήτηση" για επεξεργασία<br>
                    • Μετά την επεξεργασία θα εμφανιστούν αναλυτικά αποτελέσματα<br>
                    • Τα δεδομένα επεξεργάζονται τοπικά και δεν αποθηκεύονται
                </div>
            </div>
        ''', unsafe_allow_html=True)
    
    # Επεξεργασία και εμφάνιση αποτελεσμάτων
    else:
        # Ελέγχουμε αν τα δεδομένα υπάρχουν ήδη (για να μην ξανακάνουμε επεξεργασία)
        if 'extracted_data' in st.session_state and not st.session_state['extracted_data'].empty:
            # Τα δεδομένα υπάρχουν ήδη - εμφάνιση κουμπιού απευθείας
            df = st.session_state['extracted_data']
            
            st.markdown("### Επεξεργασία Ολοκληρώθηκε")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Προβολή Αποτελεσμάτων", type="primary", use_container_width=True, key="show_results_btn"):
                    st.session_state['show_results'] = True
                    st.rerun()
            
            st.success(f"Εξήχθησαν {len(df)} γραμμές δεδομένων από {df['Σελίδα'].nunique() if 'Σελίδα' in df.columns else 0} σελίδες")
        else:
            # Πρώτη φορά - κάνουμε επεξεργασία
            # Δημιουργία placeholders για ελεγχόμενη σειρά εμφάνισης
            header_placeholder = st.empty()
            button_placeholder = st.empty()
            summary_placeholder = st.empty()
            messages_placeholder = st.empty()
            
            # Εμφάνιση header
            with header_placeholder.container():
                st.markdown("### Επεξεργασία σε εξέλιξη...")
            
            # Container για μηνύματα επεξεργασίας (θα εμφανιστούν κάτω)
            with messages_placeholder.container():
                df = extract_efka_data(st.session_state['uploaded_file'])
            
            if not df.empty:
                st.session_state['extracted_data'] = df
                
                # Ενημέρωση header
                with header_placeholder.container():
                    st.markdown("### Επεξεργασία Ολοκληρώθηκε")
                
                # Εμφάνιση κουμπιού
                with button_placeholder.container():
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        if st.button("Προβολή Αποτελεσμάτων", type="primary", use_container_width=True, key="show_results_btn"):
                            st.session_state['show_results'] = True
                            st.rerun()
                
                # Εμφάνιση summary
                with summary_placeholder.container():
                    st.success(f"Εξήχθησαν {len(df)} γραμμές δεδομένων από {df['Σελίδα'].nunique() if 'Σελίδα' in df.columns else 0} σελίδες")
            else:
                st.error("Δεν βρέθηκαν δεδομένα για εξαγωγή")
                
                # Reset button
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("Δοκιμάστε Ξανά", use_container_width=True):
                        # Reset session state
                        for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data', 'show_results', 'filename']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()

if __name__ == "__main__":
    main()

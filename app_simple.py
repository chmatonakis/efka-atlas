#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor - Simple Version
Απλοποιημένη έκδοση με καθαρή εμφάνιση
"""

import streamlit as st
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
    page_title="e-EFKA PDF Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS για καλύτερη εμφάνιση
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .upload-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed #dee2e6;
        text-align: center;
        margin: 2rem 0;
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
</style>
""", unsafe_allow_html=True)

def extract_tables_adaptive(pdf_path):
    """
    Προσαρμοστική εξαγωγή πινάκων με πολλές στρατηγικές
    """
    import pdfplumber
    
    all_tables = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        st.info(f"📄 Σύνολο σελίδων: {total_pages}")
        
        # Δημιουργία progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for page_num, page in enumerate(pdf.pages):
            if page_num < 1:  # Παρακάμπτουμε την πρώτη σελίδα
                continue
                
            # Ενημέρωση progress
            progress = (page_num - 1) / (total_pages - 2) if total_pages > 2 else 0
            progress_bar.progress(progress)
            status_text.text(f"🔍 Επεξεργασία σελίδας {page_num + 1} από {total_pages - 1}...")
            
            # Στρατηγική 1: Κανονική εξαγωγή πινάκων
            tables = page.extract_tables()
            
            if len(tables) >= 2:
                second_table = tables[1]
                if second_table and len(second_table) > 1:
                    df = pd.DataFrame(second_table[1:], columns=second_table[0])
                    df['Σελίδα'] = page_num + 1
                    all_tables.append(df)
                    st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
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
                        all_tables.append(df)
                        st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
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
                        all_tables.append(df)
                        st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
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
                        all_tables.append(df)
                        st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
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
                            all_tables.append(df)
                            st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (πίνακας {table_idx + 1})")
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
                            all_tables.append(df)
                            st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
                            doc.close()
                            continue
                    doc.close()
                except Exception:
                    pass
            
            st.warning(f"⚠️ Σελίδα {page_num + 1}: Δεν βρέθηκε πίνακας")
        
        # Τελικό progress
        progress_bar.progress(1.0)
        status_text.text("✅ Επεξεργασία ολοκληρώθηκε!")
    
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
        
        # Συνδυάζουμε όλα τα DataFrames
        with st.spinner("Συνδυασμός δεδομένων..."):
            combined_df = pd.concat(all_tables, ignore_index=True)
        
        return combined_df
    
    except Exception as e:
        st.error(f"Σφάλμα κατά την εξαγωγή: {str(e)}")
        return pd.DataFrame()
    
    finally:
        # Διαγράφουμε το προσωρινό αρχείο
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def main():
    """Κύρια συνάρτηση της εφαρμογής"""
    
    # Header
    st.markdown('<h1 class="main-header">📄 e-EFKA PDF Data Extractor</h1>', unsafe_allow_html=True)
    
    # Αρχική κατάσταση - ανέβασμα αρχείου
    if 'file_uploaded' not in st.session_state:
        st.session_state['file_uploaded'] = False
    if 'processing_done' not in st.session_state:
        st.session_state['processing_done'] = False
    
    # Εμφάνιση ανεβάσματος αρχείου
    if not st.session_state['file_uploaded']:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.markdown("### 📤 Ανέβασμα PDF Αρχείου e-EFKA")
        st.markdown("Επιλέξτε το PDF αρχείο που θέλετε να αναλύσετε")
        
        uploaded_file = st.file_uploader(
            "Επιλέξτε PDF αρχείο",
            type=['pdf'],
            help="Ανεβάστε το PDF αρχείο e-EFKA",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            st.session_state['uploaded_file'] = uploaded_file
            st.session_state['file_uploaded'] = True
            st.success(f"✅ Ανεβλήθηκε αρχείο: {uploaded_file.name}")
            st.info(f"📊 Μέγεθος αρχείου: {uploaded_file.size:,} bytes")
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Εμφάνιση κουμπιού επεξεργασίας
    elif not st.session_state['processing_done']:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.markdown("### ✅ Αρχείο Ανεβλήθηκε")
        st.success(f"📄 {st.session_state['uploaded_file'].name}")
        st.info(f"📊 Μέγεθος: {st.session_state['uploaded_file'].size:,} bytes")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚀 Επεξεργασία PDF", type="primary", use_container_width=True):
                st.session_state['processing_done'] = True
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Επεξεργασία και εμφάνιση αποτελεσμάτων
    else:
        # Επεξεργασία
        with st.spinner("Επεξεργασία PDF αρχείου..."):
            df = extract_efka_data(st.session_state['uploaded_file'])
        
        if not df.empty:
            st.session_state['extracted_data'] = df
            st.session_state['processing_done'] = True
            
            # Εμφάνιση αποτελεσμάτων
            st.markdown('<div class="results-section">', unsafe_allow_html=True)
            st.markdown("### 📊 Αποτελέσματα Εξαγωγής")
            
            # Στατιστικά
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Συνολικές Γραμμές", len(df))
            with col2:
                st.metric("Στήλες", len(df.columns))
            with col3:
                st.metric("Σελίδες", df['Σελίδα'].nunique() if 'Σελίδα' in df.columns else 0)
            with col4:
                st.metric("Μέγεθος", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
            
            # Πίνακας δεδομένων (όλα τα δεδομένα, χωρίς φίλτρα)
            st.markdown("#### 📋 Όλα τα Δεδομένα")
            st.dataframe(
                df,
                use_container_width=True,
                height=600
            )
            
            # Download button
            st.markdown("#### 💾 Κατέβασμα Αποτελεσμάτων")
            
            # Δημιουργία Excel αρχείου
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='e-EFKA_Data', index=False)
            
            output.seek(0)
            
            # Download button
            st.download_button(
                label="📥 Κατεβάστε Excel αρχείο",
                data=output.getvalue(),
                file_name=f"efka_data_{st.session_state['uploaded_file'].name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            # Reset button
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("🔄 Νέο Αρχείο", use_container_width=True):
                    # Reset session state
                    for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Δεν βρέθηκαν δεδομένα για εξαγωγή")
            
            # Reset button
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("🔄 Δοκιμάστε Ξανά", use_container_width=True):
                    # Reset session state
                    for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

if __name__ == "__main__":
    main()



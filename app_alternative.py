#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor - Alternative Version (No Ghostscript Required)
Χρησιμοποιεί PyMuPDF αντί για camelot για να αποφύγει το Ghostscript dependency
"""

import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import io
import tempfile
import os
import re
from pathlib import Path

# Ρύθμιση σελίδας
st.set_page_config(
    page_title="e-EFKA PDF Extractor (Alternative)",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS για καλύτερη εμφάνιση
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

def extract_tables_from_pdf_pymupdf(pdf_path):
    """
    Εξάγει πίνακες από PDF χρησιμοποιώντας PyMuPDF
    """
    doc = fitz.open(pdf_path)
    all_tables = []
    
    for page_num in range(len(doc)):
        if page_num < 1:  # Παρακάμπτουμε την πρώτη σελίδα
            continue
            
        page = doc[page_num]
        
        # Εξάγουμε πίνακες από τη σελίδα
        tables = page.find_tables()
        
        if len(tables) >= 2:
            # Παίρνουμε τον δεύτερο πίνακα (index 1)
            second_table = tables[1]
            table_data = second_table.extract()
            
            if table_data:
                # Μετατρέπουμε σε DataFrame
                df = pd.DataFrame(table_data[1:], columns=table_data[0])  # Πρώτη γραμμή ως headers
                df['Σελίδα'] = page_num + 1  # +1 γιατί το page_num είναι 0-based
                all_tables.append(df)
                
                st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές")
        else:
            st.warning(f"Σελίδα {page_num + 1}: Δεν βρέθηκε δεύτερος πίνακας")
    
    doc.close()
    return all_tables

def extract_efka_data_alternative(uploaded_file):
    """
    Εναλλακτική εξαγωγή δεδομένων χρησιμοποιώντας PyMuPDF
    """
    
    # Δημιουργούμε ένα προσωρινό αρχείο
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Εξάγουμε πίνακες
        with st.spinner("Ανάγνωση PDF αρχείου με PyMuPDF..."):
            all_tables = extract_tables_from_pdf_pymupdf(tmp_path)
        
        if not all_tables:
            st.error("Δεν βρέθηκαν πίνακες στο PDF αρχείο")
            return pd.DataFrame()
        
        # Συνδυάζουμε όλα τα DataFrames
        with st.spinner("Συνδυασμός δεδομένων..."):
            combined_df = pd.concat(all_tables, ignore_index=True)
        
        st.success(f"Συνολικά εξήχθησαν {len(combined_df)} γραμμές δεδομένων")
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
    st.markdown('<h1 class="main-header">📄 e-EFKA PDF Data Extractor (Alternative)</h1>', unsafe_allow_html=True)
    
    # Sidebar με οδηγίες
    with st.sidebar:
        st.markdown("## 📋 Οδηγίες")
        st.markdown("""
        1. **Ανεβάστε PDF αρχείο** e-EFKA
        2. **Πατήστε "Εξαγωγή Δεδομένων"**
        3. **Προβάλετε τα αποτελέσματα** στον πίνακα
        4. **Κατεβάστε το Excel** αρχείο
        
        **Στήλες που εξάγονται:**
        - Από
        - Έως
        - Ημέρες
        - Μικτές αποδοχές
        - Συνολικές Εισφορές
        - Α/Μ Εργοδότη
        """)
        
        st.markdown("## ⚠️ Σημαντικά")
        st.markdown("""
        - Χρησιμοποιεί **PyMuPDF** (χωρίς Ghostscript)
        - Εξάγει πίνακες από **σελίδα 2** και μετά
        - Παίρνει τον **δεύτερο πίνακα** από κάθε σελίδα
        - Τα δεδομένα παραμένουν **ακατέργαστα**
        """)
        
        st.markdown("## 🔧 Τεχνικά")
        st.markdown("""
        **Αυτή η έκδοση:**
        - Δεν χρειάζεται Ghostscript
        - Χρησιμοποιεί PyMuPDF
        - Μπορεί να είναι λιγότερο ακριβής από το camelot
        """)
    
    # Κύριο περιεχόμενο
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📤 Ανέβασμα PDF Αρχείου")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Επιλέξτε PDF αρχείο e-EFKA",
            type=['pdf'],
            help="Ανεβάστε το PDF αρχείο που θέλετε να αναλύσετε"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ Ανεβλήθηκε αρχείο: {uploaded_file.name}")
            st.info(f"📊 Μέγεθος αρχείου: {uploaded_file.size:,} bytes")
    
    with col2:
        st.markdown("### ⚙️ Ενέργειες")
        
        if uploaded_file is not None:
            if st.button("🚀 Εξαγωγή Δεδομένων", type="primary", use_container_width=True):
                # Εξαγωγή δεδομένων
                df = extract_efka_data_alternative(uploaded_file)
                
                if not df.empty:
                    # Αποθήκευση στο session state
                    st.session_state['extracted_data'] = df
                    st.session_state['filename'] = uploaded_file.name
                    st.rerun()
        else:
            st.info("Ανεβάστε πρώτα ένα PDF αρχείο")
    
    # Εμφάνιση αποτελεσμάτων
    if 'extracted_data' in st.session_state and not st.session_state['extracted_data'].empty:
        st.markdown("---")
        st.markdown("### 📊 Αποτελέσματα Εξαγωγής")
        
        df = st.session_state['extracted_data']
        
        # Στατιστικά
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Συνολικές Γραμμές", len(df))
        with col2:
            st.metric("Στήλες", len(df.columns))
        with col3:
            st.metric("Σελίδες", df['Σελίδα'].nunique() if 'Σελίδα' in df.columns else 0)
        with col4:
            st.metric("Μέγεθος DataFrame", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        
        # Προβολή δεδομένων
        st.markdown("#### 📋 Προβολή Δεδομένων")
        
        # Φίλτρα
        if 'Σελίδα' in df.columns:
            pages = sorted(df['Σελίδα'].unique())
            selected_pages = st.multiselect(
                "Επιλέξτε σελίδες για προβολή:",
                options=pages,
                default=pages[:3] if len(pages) > 3 else pages
            )
            
            if selected_pages:
                filtered_df = df[df['Σελίδα'].isin(selected_pages)]
            else:
                filtered_df = df
        else:
            filtered_df = df
        
        # Πλήθος γραμμών προς εμφάνιση
        rows_to_show = st.slider("Αριθμός γραμμών προς εμφάνιση:", 10, min(100, len(filtered_df)), 20)
        
        # Πίνακας δεδομένων
        st.dataframe(
            filtered_df.head(rows_to_show),
            use_container_width=True,
            height=400
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
            file_name=f"efka_data_{st.session_state.get('filename', 'extracted')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # Clear button
        if st.button("🗑️ Καθαρισμός Αποτελεσμάτων", use_container_width=True):
            if 'extracted_data' in st.session_state:
                del st.session_state['extracted_data']
            if 'filename' in st.session_state:
                del st.session_state['filename']
            st.rerun()

if __name__ == "__main__":
    main()



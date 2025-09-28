#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor - Streamlit Web App
Web εφαρμογή για εξαγωγή δεδομένων από PDF αρχεία e-EFKA
"""

import streamlit as st
import camelot
import pandas as pd
import io
import tempfile
import os
from pathlib import Path

# Ρύθμιση σελίδας
st.set_page_config(
    page_title="e-EFKA PDF Extractor",
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

def extract_efka_data_from_upload(uploaded_file):
    """
    Εξάγει δεδομένα από ανεβασμένο PDF αρχείο
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        pd.DataFrame: Τα εξαγόμενα δεδομένα
    """
    
    # Δημιουργούμε ένα προσωρινό αρχείο
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Λίστα για αποθήκευση όλων των DataFrames
        all_dataframes = []
        
        # Διαβάζουμε το PDF
        with st.spinner("Ανάγνωση PDF αρχείου..."):
            try:
                tables = camelot.read_pdf(tmp_path, pages='all', flavor='lattice')
            except Exception as e:
                if "Ghostscript" in str(e):
                    st.error("❌ Το Ghostscript δεν είναι εγκατεστημένο!")
                    st.info("""
                    **Για να εγκαταστήσετε το Ghostscript:**
                    
                    1. Κατεβάστε από: https://www.ghostscript.com/download/gsdnld.html
                    2. Εγκαταστήστε το Ghostscript
                    3. Προσθέστε το στο PATH του συστήματος
                    4. Επανεκκινήστε την εφαρμογή
                    
                    **Εναλλακτικά, χρησιμοποιήστε το command-line script:**
                    `python efka_pdf_extractor.py`
                    """)
                    return pd.DataFrame()
                else:
                    raise e
        
        if not tables:
            st.error("Δεν βρέθηκαν πίνακες στο PDF αρχείο")
            return pd.DataFrame()
        
        st.info(f"Βρέθηκαν {len(tables)} πίνακες συνολικά")
        
        # Ομαδοποιούμε τους πίνακες ανά σελίδα
        pages_dict = {}
        for table in tables:
            page_num = table.page
            if page_num not in pages_dict:
                pages_dict[page_num] = []
            pages_dict[page_num].append(table)
        
        # Εξάγουμε δεδομένα από κάθε σελίδα (ξεκινώντας από σελίδα 2)
        progress_bar = st.progress(0)
        total_pages = len([p for p in pages_dict.keys() if p >= 2])
        processed_pages = 0
        
        for page_num in sorted(pages_dict.keys()):
            if page_num < 2:  # Παρακάμπτουμε την πρώτη σελίδα
                continue
                
            with st.spinner(f"Επεξεργασία σελίδας {page_num}..."):
                page_tables = pages_dict[page_num]
                
                if len(page_tables) >= 2:
                    # Παίρνουμε τον δεύτερο πίνακα (index 1)
                    second_table = page_tables[1]
                    df = second_table.df
                    
                    # Προσθέτουμε μια στήλη με τον αριθμό σελίδας
                    df['Σελίδα'] = page_num
                    
                    all_dataframes.append(df)
                    st.success(f"Σελίδα {page_num}: Εξήχθηκαν {len(df)} γραμμές")
                else:
                    st.warning(f"Σελίδα {page_num}: Δεν βρέθηκε δεύτερος πίνακας")
            
            processed_pages += 1
            progress_bar.progress(processed_pages / total_pages)
        
        # Συνδυάζουμε όλα τα DataFrames
        if all_dataframes:
            with st.spinner("Συνδυασμός δεδομένων..."):
                combined_df = pd.concat(all_dataframes, ignore_index=True)
            
            st.success(f"Συνολικά εξήχθησαν {len(combined_df)} γραμμές δεδομένων")
            return combined_df
        else:
            st.error("Δεν βρέθηκαν δεδομένα για εξαγωγή")
            return pd.DataFrame()
    
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
        - Το PDF πρέπει να έχει πίνακες με grid lines
        - Εξάγεται ο **δεύτερος πίνακας** από κάθε σελίδα
        - Ξεκινάει από **σελίδα 2**
        - Τα δεδομένα παραμένουν **ακατέργαστα**
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
                df = extract_efka_data_from_upload(uploaded_file)
                
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

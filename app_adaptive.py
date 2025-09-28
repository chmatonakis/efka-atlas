#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor - Adaptive Version
Προσαρμοστική έκδοση που δοκιμάζει πολλές προσεγγίσεις
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
    page_title="e-EFKA PDF Extractor (Adaptive)",
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
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
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
        
        for page_num, page in enumerate(pdf.pages):
            if page_num < 1:  # Παρακάμπτουμε την πρώτη σελίδα
                continue
                
            st.markdown(f"### 🔍 Επεξεργασία Σελίδας {page_num + 1}")
            
            # Στρατηγική 1: Κανονική εξαγωγή πινάκων
            tables = page.extract_tables()
            st.info(f"📊 Βρέθηκαν {len(tables)} πίνακες με κανονική μέθοδο")
            
            if len(tables) >= 2:
                second_table = tables[1]
                if second_table and len(second_table) > 1:
                    df = pd.DataFrame(second_table[1:], columns=second_table[0])
                    df['Σελίδα'] = page_num + 1
                    all_tables.append(df)
                    st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (κανονική μέθοδος)")
                    continue
            
            # Στρατηγική 2: Εξαγωγή με διαφορετικές παραμέτρους
            try:
                tables_alt = page.extract_tables(table_settings={
                    "vertical_strategy": "lines_strict",
                    "horizontal_strategy": "lines_strict"
                })
                st.info(f"📊 Βρέθηκαν {len(tables_alt)} πίνακες με strict lines")
                
                if len(tables_alt) >= 2:
                    second_table = tables_alt[1]
                    if second_table and len(second_table) > 1:
                        df = pd.DataFrame(second_table[1:], columns=second_table[0])
                        df['Σελίδα'] = page_num + 1
                        all_tables.append(df)
                        st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (strict lines)")
                        continue
            except Exception as e:
                st.warning(f"⚠️ Strict lines απέτυχε: {str(e)}")
            
            # Στρατηγική 3: Εξαγωγή όλων των πινάκων
            try:
                all_tables_page = page.extract_tables()
                if all_tables_page:
                    # Παίρνουμε τον μεγαλύτερο πίνακα
                    largest_table = max(all_tables_page, key=len)
                    if largest_table and len(largest_table) > 1:
                        df = pd.DataFrame(largest_table[1:], columns=largest_table[0])
                        df['Σελίδα'] = page_num + 1
                        all_tables.append(df)
                        st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (μεγαλύτερος πίνακας)")
                        continue
            except Exception as e:
                st.warning(f"⚠️ Μεγαλύτερος πίνακας απέτυχε: {str(e)}")
            
            # Στρατηγική 4: Text-based parsing
            try:
                text = page.extract_text()
                if text and len(text) > 100:
                    st.info(f"📝 Εξήχθησαν {len(text)} χαρακτήρες κειμένου")
                    
                    # Ψάχνουμε για πίνακες στο κείμενο
                    table_data = parse_text_for_tables(text, page_num + 1)
                    if table_data and len(table_data) > 1:
                        df = pd.DataFrame(table_data[1:], columns=table_data[0])
                        df['Σελίδα'] = page_num + 1
                        all_tables.append(df)
                        st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (text parsing)")
                        continue
            except Exception as e:
                st.warning(f"⚠️ Text parsing απέτυχε: {str(e)}")
            
            # Στρατηγική 6: Εξαγωγή όλων των πινάκων (fallback)
            try:
                all_tables_page = page.extract_tables()
                if all_tables_page:
                    # Παίρνουμε όλους τους πίνακες, όχι μόνο τον δεύτερο
                    for table_idx, table in enumerate(all_tables_page):
                        if table and len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df['Σελίδα'] = page_num + 1
                            df['Πίνακας'] = table_idx + 1
                            all_tables.append(df)
                            st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (πίνακας {table_idx + 1})")
            except Exception as e:
                st.warning(f"⚠️ Fallback extraction απέτυχε: {str(e)}")
            
            # Στρατηγική 7: Εξαγωγή με διαφορετικές ρυθμίσεις
            try:
                tables_alt2 = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text"
                })
                st.info(f"📊 Βρέθηκαν {len(tables_alt2)} πίνακες με text strategy")
                
                if tables_alt2:
                    for table_idx, table in enumerate(tables_alt2):
                        if table and len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df['Σελίδα'] = page_num + 1
                            df['Πίνακας'] = table_idx + 1
                            all_tables.append(df)
                            st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (text strategy, πίνακας {table_idx + 1})")
            except Exception as e:
                st.warning(f"⚠️ Text strategy απέτυχε: {str(e)}")
            
            # Στρατηγική 5: Εξαγωγή με PyMuPDF
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
                            st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (PyMuPDF)")
                            doc.close()
                            continue
                    doc.close()
                except Exception as e:
                    st.warning(f"⚠️ PyMuPDF απέτυχε: {str(e)}")
            
            st.warning(f"⚠️ Σελίδα {page_num + 1}: Δεν βρέθηκε πίνακας με καμία στρατηγική")
    
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

def extract_efka_data_adaptive(uploaded_file):
    """
    Προσαρμοστική εξαγωγή δεδομένων
    """
    
    # Δημιουργούμε ένα προσωρινό αρχείο
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        st.markdown("### 🔍 Προσαρμοστική Ανάλυση PDF")
        
        # Εξάγουμε πίνακες με προσαρμοστική μέθοδο
        all_tables = extract_tables_adaptive(tmp_path)
        
        if not all_tables:
            st.error("Δεν βρέθηκαν πίνακες στο PDF αρχείο")
            return pd.DataFrame()
        
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

def main():
    """Κύρια συνάρτηση της εφαρμογής"""
    
    # Header
    st.markdown('<h1 class="main-header">📄 e-EFKA PDF Data Extractor (Adaptive)</h1>', unsafe_allow_html=True)
    
    # Sidebar με οδηγίες
    with st.sidebar:
        st.markdown("## 📋 Οδηγίες")
        st.markdown("""
        1. **Ανεβάστε PDF αρχείο** e-EFKA
        2. **Πατήστε "Εξαγωγή Δεδομένων"**
        3. **Προβάλετε τα αποτελέσματα** στον πίνακα
        4. **Κατεβάστε το Excel** αρχείο
        """)
        
        st.markdown("## 🔧 Προσαρμοστική Μέθοδος")
        st.markdown("""
        **Αυτή η έκδοση:**
        - **5 διαφορετικές στρατηγικές** ανά σελίδα
        - **Fallback system** - αν μια αποτύχει, δοκιμάζει την επόμενη
        - **Flexible parsing** για όλους τους τύπους πινάκων
        - **Multiple libraries** (pdfplumber, PyMuPDF)
        """)
        
        st.markdown("## ⚠️ Σημαντικά")
        st.markdown("""
        - Εξάγει από **σελίδα 2** και μετά
        - **Δοκιμάζει όλες τις στρατηγικές** για κάθε σελίδα
        - **Automatic fallback** αν μια στρατηγική αποτύχει
        - **Detailed logging** για κάθε προσπάθεια
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
                df = extract_efka_data_adaptive(uploaded_file)
                
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
            
            # Εμφανίζουμε όλες τις σελίδες που έχουν δεδομένα
            st.info(f"📊 Διαθέσιμες σελίδες με δεδομένα: {', '.join(map(str, pages))}")
            
            selected_pages = st.multiselect(
                "Επιλέξτε σελίδες για προβολή:",
                options=pages,
                default=pages  # Προεπιλογή: όλες οι σελίδες
            )
            
            if selected_pages:
                filtered_df = df[df['Σελίδα'].isin(selected_pages)]
            else:
                filtered_df = df
        else:
            filtered_df = df
        
        # Πλήθος γραμμών προς εμφάνιση
        max_rows = min(500, len(filtered_df))  # Αυξάνουμε το μέγιστο όριο
        rows_to_show = st.slider("Αριθμός γραμμών προς εμφάνιση:", 10, max_rows, min(50, max_rows))
        
        # Εμφάνιση στατιστικών για τις επιλεγμένες σελίδες
        if 'Σελίδα' in filtered_df.columns:
            page_stats = filtered_df['Σελίδα'].value_counts().sort_index()
            st.info(f"📊 Γραμμές ανά σελίδα: {dict(page_stats)}")
        
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

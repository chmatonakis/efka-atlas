#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor - Specialized Version
Εξειδικευμένη έκδοση για e-EFKA PDF αρχεία με custom parsing
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
    page_title="e-EFKA PDF Extractor (Specialized)",
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

def extract_efka_tables_specialized(pdf_path):
    """
    Εξειδικευμένη εξαγωγή πινάκων για e-EFKA PDF αρχεία
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
            
            # Εξάγουμε όλο το κείμενο από τη σελίδα
            text = page.extract_text()
            
            if not text:
                st.warning(f"⚠️ Σελίδα {page_num + 1}: Δεν βρέθηκε κείμενο")
                continue
            
            st.info(f"📝 Εξήχθησαν {len(text)} χαρακτήρες κειμένου")
            
            # Εξειδικευμένη ανάλυση για e-EFKA πίνακες
            table_data = parse_efka_table_text(text, page_num + 1)
            
            if table_data and len(table_data) > 1:
                # Δημιουργούμε DataFrame
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                df['Σελίδα'] = page_num + 1
                all_tables.append(df)
                st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές δεδομένων")
            else:
                st.warning(f"⚠️ Σελίδα {page_num + 1}: Δεν βρέθηκαν δεδομένα πίνακα")
    
    return all_tables

def parse_efka_table_text(text, page_num):
    """
    Εξειδικευμένη ανάλυση κειμένου για e-EFKA πίνακες
    """
    lines = text.split('\n')
    
    # Ψάχνουμε για το header του πίνακα
    header_line = None
    header_index = -1
    
    # Γνωστοί headers από e-EFKA
    efka_headers = [
        ['Από', 'Έως', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές Εισφορές', 'Α/Μ Εργοδότη'],
        ['ΑΠΟ', 'ΕΩΣ', 'ΗΜΕΡΕΣ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'Α/Μ ΕΡΓΟΔΟΤΗ'],
        ['Από', 'Έως', 'Ημέρες', 'Μικτές', 'Συνολικές', 'Α/Μ'],
        ['ΑΠΟ', 'ΕΩΣ', 'ΗΜΕΡΕΣ', 'ΜΙΚΤΕΣ', 'ΣΥΝΟΛΙΚΕΣ', 'Α/Μ']
    ]
    
    # Ψάχνουμε για header
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
            
        # Ελέγχουμε αν η γραμμή περιέχει headers
        for header_variant in efka_headers:
            if all(header_word in line_clean for header_word in header_variant):
                header_line = header_variant
                header_index = i
                st.info(f"  📋 Βρέθηκε header: {line_clean}")
                break
        
        if header_line:
            break
    
    if not header_line:
        st.warning(f"  ⚠️ Δεν βρέθηκε header πίνακα")
        return None
    
    # Εξάγουμε δεδομένα μετά το header
    table_data = [header_line]
    data_lines = []
    
    for i in range(header_index + 1, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        
        # Σταματάμε αν βρήκαμε νέο header ή τίτλο
        if any(word in line.upper() for word in ['ΣΕΛΙΔΑ', 'ΣΥΝΟΛΟ', 'ΣΥΝΟΛΙΚΑ', 'ΣΕΛΙΔΕΣ']):
            break
        
        # Ελέγχουμε αν η γραμμή περιέχει δεδομένα πίνακα
        if is_efka_data_line(line):
            data_lines.append(line)
            st.info(f"  📊 Γραμμή δεδομένων: {line[:50]}...")
    
    st.info(f"  📈 Βρέθηκαν {len(data_lines)} γραμμές δεδομένων")
    
    # Μετατρέπουμε τις γραμμές δεδομένων σε στήλες
    for line in data_lines:
        row_data = parse_efka_data_line(line, len(header_line))
        if row_data:
            table_data.append(row_data)
    
    return table_data if len(table_data) > 1 else None

def is_efka_data_line(line):
    """
    Ελέγχει αν μια γραμμή περιέχει δεδομένα e-EFKA πίνακα
    """
    # Patterns για e-EFKA δεδομένα
    date_pattern = r'\d{1,2}/\d{1,2}/\d{4}'  # Ημερομηνίες
    amount_pattern = r'[\d,]+\.\d{2}'  # Ποσά με δεκαδικά
    days_pattern = r'^\d+$'  # Μόνο αριθμοί (ημέρες)
    
    # Ελέγχουμε αν η γραμμή περιέχει τουλάχιστον 2 από τα παρακάτω:
    patterns_found = 0
    
    if re.search(date_pattern, line):
        patterns_found += 1
    if re.search(amount_pattern, line):
        patterns_found += 1
    if re.search(days_pattern, line.split()[-1] if line.split() else ''):
        patterns_found += 1
    
    # Επίσης ελέγχουμε αν έχει αρκετές λέξεις (πιθανά στήλες)
    words = line.split()
    if len(words) >= 4:
        patterns_found += 1
    
    return patterns_found >= 2

def parse_efka_data_line(line, expected_columns):
    """
    Μετατρέπει μια γραμμή δεδομένων σε στήλες
    """
    # Χωρίζουμε τη γραμμή σε λέξεις
    words = line.split()
    
    if len(words) < 4:
        return None
    
    # Προσπαθούμε να βρούμε τις στήλες με έξυπνο τρόπο
    row_data = []
    
    # Στήλη 1-2: Ημερομηνίες (Από, Έως)
    date_pattern = r'\d{1,2}/\d{1,2}/\d{4}'
    dates = re.findall(date_pattern, line)
    
    if len(dates) >= 2:
        row_data.extend(dates[:2])
    elif len(dates) == 1:
        row_data.extend([dates[0], ''])
    else:
        row_data.extend(['', ''])
    
    # Στήλη 3: Ημέρες (αριθμός)
    days_pattern = r'^\d+$'
    days = None
    for word in words:
        if re.match(days_pattern, word):
            days = word
            break
    
    row_data.append(days if days else '')
    
    # Στήλες 4-5: Ποσά (Μικτές αποδοχές, Συνολικές Εισφορές)
    amount_pattern = r'[\d,]+\.\d{2}'
    amounts = re.findall(amount_pattern, line)
    
    if len(amounts) >= 2:
        row_data.extend(amounts[:2])
    elif len(amounts) == 1:
        row_data.extend([amounts[0], ''])
    else:
        row_data.extend(['', ''])
    
    # Στήλη 6: Α/Μ Εργοδότη (συνήθως αριθμός)
    am_pattern = r'\d{6,}'  # Αριθμός με τουλάχιστον 6 ψηφία
    am_match = re.search(am_pattern, line)
    row_data.append(am_match.group() if am_match else '')
    
    # Συμπληρώνουμε με κενά αν χρειάζεται
    while len(row_data) < expected_columns:
        row_data.append('')
    
    return row_data[:expected_columns]

def extract_efka_data_specialized(uploaded_file):
    """
    Εξειδικευμένη εξαγωγή δεδομένων για e-EFKA PDF αρχεία
    """
    
    # Δημιουργούμε ένα προσωρινό αρχείο
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        st.markdown("### 🔍 Εξειδικευμένη Ανάλυση e-EFKA PDF")
        
        # Εξάγουμε πίνακες με εξειδικευμένη μέθοδο
        all_tables = extract_efka_tables_specialized(tmp_path)
        
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
    st.markdown('<h1 class="main-header">📄 e-EFKA PDF Data Extractor (Specialized)</h1>', unsafe_allow_html=True)
    
    # Sidebar με οδηγίες
    with st.sidebar:
        st.markdown("## 📋 Οδηγίες")
        st.markdown("""
        1. **Ανεβάστε PDF αρχείο** e-EFKA
        2. **Πατήστε "Εξαγωγή Δεδομένων"**
        3. **Προβάλετε τα αποτελέσματα** στον πίνακα
        4. **Κατεβάστε το Excel** αρχείο
        """)
        
        st.markdown("## 🔧 Εξειδικευμένη Μέθοδος")
        st.markdown("""
        **Αυτή η έκδοση:**
        - **Εξειδικευμένη** για e-EFKA PDF
        - **Custom parsing** για πίνακες
        - **Regex patterns** για δεδομένα
        - **Intelligent header detection**
        - **Smart column parsing**
        """)
        
        st.markdown("## ⚠️ Σημαντικά")
        st.markdown("""
        - Εξάγει από **σελίδα 2** και μετά
        - Ψάχνει για **γνωστούς headers** e-EFKA
        - **Custom parsing** για κάθε γραμμή
        - **Pattern matching** για δεδομένα
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
                df = extract_efka_data_specialized(uploaded_file)
                
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



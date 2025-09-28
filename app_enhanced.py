#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor - Enhanced Version
Χρησιμοποιεί πολλαπλές βιβλιοθήκες για καλύτερη ανάγνωση πινάκων
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
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Ρύθμιση σελίδας
st.set_page_config(
    page_title="e-EFKA PDF Extractor (Enhanced)",
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

def extract_tables_with_pdfplumber(pdf_path):
    """Εξάγει πίνακες χρησιμοποιώντας pdfplumber με βελτιωμένο αλγόριθμο"""
    import pdfplumber
    
    all_tables = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num < 1:  # Παρακάμπτουμε την πρώτη σελίδα
                continue
                
            st.info(f"🔍 Επεξεργασία σελίδας {page_num + 1}...")
            
            # Δοκιμάζουμε διαφορετικές στρατηγικές εξαγωγής
            tables_found = False
            
            # Στρατηγική 1: Κανονική εξαγωγή πινάκων
            tables = page.extract_tables()
            st.info(f"  - Βρέθηκαν {len(tables)} πίνακες με κανονική μέθοδο")
            
            if len(tables) >= 2:
                second_table = tables[1]
                if second_table and len(second_table) > 1:
                    df = pd.DataFrame(second_table[1:], columns=second_table[0])
                    df['Σελίδα'] = page_num + 1
                    all_tables.append(df)
                    st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (pdfplumber - κανονική)")
                    tables_found = True
            
            # Στρατηγική 2: Εξαγωγή με διαφορετικές παραμέτρους
            if not tables_found:
                try:
                    # Δοκιμάζουμε με διαφορετικές ρυθμίσεις
                    tables_alt = page.extract_tables(table_settings={
                        "vertical_strategy": "lines_strict",
                        "horizontal_strategy": "lines_strict",
                        "min_words_vertical": 1,
                        "min_words_horizontal": 1
                    })
                    st.info(f"  - Βρέθηκαν {len(tables_alt)} πίνακες με strict lines")
                    
                    if len(tables_alt) >= 2:
                        second_table = tables_alt[1]
                        if second_table and len(second_table) > 1:
                            df = pd.DataFrame(second_table[1:], columns=second_table[0])
                            df['Σελίδα'] = page_num + 1
                            all_tables.append(df)
                            st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (pdfplumber - strict)")
                            tables_found = True
                except Exception as e:
                    st.warning(f"  - Στρατηγική 2 απέτυχε: {str(e)}")
            
            # Στρατηγική 3: Εξαγωγή όλων των πινάκων και επιλογή του μεγαλύτερου
            if not tables_found:
                try:
                    all_tables_page = page.extract_tables()
                    if all_tables_page:
                        # Βρίσκουμε τον μεγαλύτερο πίνακα (εκτός από τον πρώτο)
                        if len(all_tables_page) > 1:
                            largest_table = max(all_tables_page[1:], key=len)
                        else:
                            largest_table = all_tables_page[0]
                        
                        if largest_table and len(largest_table) > 1:
                            df = pd.DataFrame(largest_table[1:], columns=largest_table[0])
                            df['Σελίδα'] = page_num + 1
                            all_tables.append(df)
                            st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (pdfplumber - μεγαλύτερος πίνακας)")
                            tables_found = True
                except Exception as e:
                    st.warning(f"  - Στρατηγική 3 απέτυχε: {str(e)}")
            
            # Στρατηγική 4: Εξαγωγή με text-based approach
            if not tables_found:
                try:
                    # Εξάγουμε όλο το κείμενο και ψάχνουμε για patterns
                    text = page.extract_text()
                    if text and len(text) > 100:  # Αν υπάρχει αρκετό κείμενο
                        # Ψάχνουμε για γραμμές που μοιάζουν με πίνακα
                        lines = text.split('\n')
                        table_lines = []
                        for line in lines:
                            # Ψάχνουμε για γραμμές με πολλά κενά ή tabs (πιθανά πίνακες)
                            if line.count(' ') > 5 or '\t' in line:
                                table_lines.append(line)
                        
                        if len(table_lines) > 10:  # Αν βρήκαμε αρκετές γραμμές
                            st.info(f"  - Βρέθηκαν {len(table_lines)} γραμμές κειμένου που μοιάζουν με πίνακα")
                            # Δημιουργούμε έναν απλό DataFrame
                            data = []
                            for line in table_lines:
                                # Χωρίζουμε τη γραμμή σε στήλες
                                columns = [col.strip() for col in line.split() if col.strip()]
                                if len(columns) > 3:  # Αν έχει αρκετές στήλες
                                    data.append(columns)
                            
                            if data and len(data) > 1:
                                # Δημιουργούμε DataFrame
                                max_cols = max(len(row) for row in data)
                                for i, row in enumerate(data):
                                    while len(row) < max_cols:
                                        row.append('')
                                
                                df = pd.DataFrame(data[1:], columns=[f'Στήλη_{i+1}' for i in range(max_cols)])
                                df['Σελίδα'] = page_num + 1
                                all_tables.append(df)
                                st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (pdfplumber - text-based)")
                                tables_found = True
                except Exception as e:
                    st.warning(f"  - Στρατηγική 4 απέτυχε: {str(e)}")
            
            # Στρατηγική 5: Regex-based pattern matching για e-EFKA πίνακες
            if not tables_found:
                try:
                    text = page.extract_text()
                    if text:
                        # Ψάχνουμε για patterns που είναι χαρακτηριστικά των e-EFKA πινάκων
                        lines = text.split('\n')
                        
                        # Regex patterns για e-EFKA δεδομένα
                        date_pattern = r'\d{1,2}/\d{1,2}/\d{4}'  # Ημερομηνίες
                        amount_pattern = r'[\d,]+\.\d{2}'  # Ποσά με δεκαδικά
                        days_pattern = r'\d+'  # Ημέρες
                        
                        table_data = []
                        in_table = False
                        header_found = False
                        
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Ψάχνουμε για header του πίνακα
                            if not header_found and ('Από' in line or 'Ημέρες' in line or 'Μικτές' in line):
                                header_found = True
                                in_table = True
                                continue
                            
                            # Αν είμαστε μέσα στον πίνακα
                            if in_table:
                                # Ψάχνουμε για γραμμές που περιέχουν ημερομηνίες ή ποσά
                                if (re.search(date_pattern, line) or 
                                    re.search(amount_pattern, line) or 
                                    line.count(' ') > 3):
                                    
                                    # Χωρίζουμε τη γραμμή σε στήλες
                                    parts = line.split()
                                    if len(parts) >= 4:  # Αν έχει αρκετές στήλες
                                        table_data.append(parts)
                                else:
                                    # Αν δεν βρήκαμε δεδομένα για 3 γραμμές συνεχόμενα, σταματάμε
                                    if len(table_data) > 0 and i > 0:
                                        # Ελέγχουμε αν οι επόμενες 3 γραμμές έχουν δεδομένα
                                        next_lines = lines[i:i+3]
                                        has_data = False
                                        for next_line in next_lines:
                                            if (re.search(date_pattern, next_line) or 
                                                re.search(amount_pattern, next_line)):
                                                has_data = True
                                                break
                                        
                                        if not has_data:
                                            break
                        
                        if table_data and len(table_data) > 1:
                            st.info(f"  - Βρέθηκαν {len(table_data)} γραμμές με regex pattern matching")
                            
                            # Δημιουργούμε DataFrame
                            max_cols = max(len(row) for row in table_data)
                            for row in table_data:
                                while len(row) < max_cols:
                                    row.append('')
                            
                            # Προσπαθούμε να βρούμε headers
                            if len(table_data) > 0:
                                # Χρησιμοποιούμε γνωστά headers από e-EFKA
                                headers = ['Από', 'Έως', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές Εισφορές', 'Α/Μ Εργοδότη']
                                if len(headers) <= max_cols:
                                    df = pd.DataFrame(table_data, columns=headers[:max_cols])
                                else:
                                    df = pd.DataFrame(table_data, columns=[f'Στήλη_{i+1}' for i in range(max_cols)])
                                
                                df['Σελίδα'] = page_num + 1
                                all_tables.append(df)
                                st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (pdfplumber - regex pattern)")
                                tables_found = True
                except Exception as e:
                    st.warning(f"  - Στρατηγική 5 απέτυχε: {str(e)}")
            
            # Στρατηγική 6: OCR-based extraction (αν είναι διαθέσιμο)
            if not tables_found:
                try:
                    # Δοκιμάζουμε να εξάγουμε πίνακες με OCR
                    import pytesseract
                    from PIL import Image
                    import io
                    
                    # Μετατρέπουμε τη σελίδα σε εικόνα
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Εξάγουμε κείμενο με OCR
                    ocr_text = pytesseract.image_to_string(img, lang='ell+eng')
                    
                    if ocr_text and len(ocr_text) > 100:
                        st.info(f"  - OCR εξήγαγε {len(ocr_text)} χαρακτήρες")
                        
                        # Ψάχνουμε για πίνακες στο OCR κείμενο
                        lines = ocr_text.split('\n')
                        table_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            if (re.search(r'\d{1,2}/\d{1,2}/\d{4}', line) or  # Ημερομηνίες
                                re.search(r'[\d,]+\.\d{2}', line) or  # Ποσά
                                line.count(' ') > 3):  # Πολλά κενά
                                table_lines.append(line)
                        
                        if len(table_lines) > 5:
                            st.info(f"  - Βρέθηκαν {len(table_lines)} γραμμές με OCR")
                            
                            # Δημιουργούμε DataFrame
                            data = []
                            for line in table_lines:
                                parts = line.split()
                                if len(parts) >= 4:
                                    data.append(parts)
                            
                            if data and len(data) > 1:
                                max_cols = max(len(row) for row in data)
                                for row in data:
                                    while len(row) < max_cols:
                                        row.append('')
                                
                                df = pd.DataFrame(data, columns=[f'Στήλη_{i+1}' for i in range(max_cols)])
                                df['Σελίδα'] = page_num + 1
                                all_tables.append(df)
                                st.success(f"✅ Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (OCR)")
                                tables_found = True
                except ImportError:
                    st.info(f"  - OCR δεν είναι διαθέσιμο (pytesseract)")
                except Exception as e:
                    st.warning(f"  - Στρατηγική 6 απέτυχε: {str(e)}")
            
            if not tables_found:
                st.warning(f"⚠️ Σελίδα {page_num + 1}: Δεν βρέθηκε πίνακας με καμία στρατηγική")
    
    return all_tables

def extract_tables_with_pymupdf(pdf_path):
    """Εξάγει πίνακες χρησιμοποιώντας PyMuPDF"""
    import fitz
    
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
            
            if table_data and len(table_data) > 1:
                # Μετατρέπουμε σε DataFrame
                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                df['Σελίδα'] = page_num + 1
                all_tables.append(df)
                
                st.success(f"Σελίδα {page_num + 1}: Εξήχθησαν {len(df)} γραμμές (PyMuPDF)")
            else:
                st.warning(f"Σελίδα {page_num + 1}: Δεύτερος πίνακας κενός (PyMuPDF)")
        else:
            st.warning(f"Σελίδα {page_num + 1}: Δεν βρέθηκε δεύτερος πίνακας (PyMuPDF)")
    
    doc.close()
    return all_tables

def extract_tables_with_camelot(pdf_path):
    """Εξάγει πίνακες χρησιμοποιώντας camelot"""
    try:
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        if not tables:
            return []
        
        # Ομαδοποιούμε τους πίνακες ανά σελίδα
        pages_dict = {}
        for table in tables:
            page_num = table.page
            if page_num not in pages_dict:
                pages_dict[page_num] = []
            pages_dict[page_num].append(table)
        
        all_tables = []
        
        # Εξάγουμε δεδομένα από κάθε σελίδα (ξεκινώντας από σελίδα 2)
        for page_num in sorted(pages_dict.keys()):
            if page_num < 2:  # Παρακάμπτουμε την πρώτη σελίδα
                continue
                
            page_tables = pages_dict[page_num]
            
            if len(page_tables) >= 2:
                # Παίρνουμε τον δεύτερο πίνακα (index 1)
                second_table = page_tables[1]
                df = second_table.df
                
                # Προσθέτουμε μια στήλη με τον αριθμό σελίδας
                df['Σελίδα'] = page_num
                
                all_tables.append(df)
                st.success(f"Σελίδα {page_num}: Εξήχθησαν {len(df)} γραμμές (camelot)")
            else:
                st.warning(f"Σελίδα {page_num}: Δεν βρέθηκε δεύτερος πίνακας (camelot)")
        
        return all_tables
        
    except Exception as e:
        st.error(f"Σφάλμα με camelot: {str(e)}")
        return []

def extract_tables_with_tabula(pdf_path):
    """Εξάγει πίνακες χρησιμοποιώντας tabula-py"""
    try:
        import tabula
        
        # Εξάγουμε πίνακες από όλες τις σελίδες (ξεκινώντας από σελίδα 2)
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        
        all_tables = []
        
        for i, table in enumerate(tables):
            if table is not None and not table.empty:
                # Προσθέτουμε στήλη σελίδας
                table['Σελίδα'] = i + 2  # +2 γιατί ξεκινάμε από σελίδα 2
                all_tables.append(table)
                st.success(f"Tabula: Εξήχθη πίνακας {i+1} με {len(table)} γραμμές")
        
        return all_tables
        
    except ImportError:
        st.warning("Tabula-py δεν είναι διαθέσιμο")
        return []
    except Exception as e:
        st.error(f"Σφάλμα με tabula: {str(e)}")
        return []

def extract_efka_data_enhanced(uploaded_file):
    """
    Ενισχυμένη εξαγωγή δεδομένων με πολλαπλές βιβλιοθήκες
    """
    
    # Δημιουργούμε ένα προσωρινό αρχείο
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        all_tables = []
        
        # Δοκιμάζουμε διαφορετικές βιβλιοθήκες με σειρά προτεραιότητας
        methods = []
        
        if CAMELOT_AVAILABLE:
            methods.append(("camelot", extract_tables_with_camelot))
        
        if PDFPLUMBER_AVAILABLE:
            methods.append(("pdfplumber", extract_tables_with_pdfplumber))
        
        # Προσθέτουμε tabula ως επιπλέον επιλογή
        try:
            import tabula
            methods.append(("tabula", extract_tables_with_tabula))
        except ImportError:
            pass
        
        if PYMUPDF_AVAILABLE:
            methods.append(("PyMuPDF", extract_tables_with_pymupdf))
        
        if not methods:
            st.error("❌ Δεν είναι διαθέσιμες βιβλιοθήκες PDF!")
            return pd.DataFrame()
        
        st.info(f"Διαθέσιμες βιβλιοθήκες: {', '.join([m[0] for m in methods])}")
        
        # Δοκιμάζουμε κάθε μέθοδο
        for method_name, method_func in methods:
            st.markdown(f"### 🔍 Δοκιμή με {method_name}")
            
            try:
                with st.spinner(f"Εξαγωγή με {method_name}..."):
                    tables = method_func(tmp_path)
                
                if tables:
                    all_tables.extend(tables)
                    st.success(f"✅ {method_name}: Εξήχθησαν {len(tables)} πίνακες")
                    break  # Αν βρήκαμε δεδομένα, σταματάμε
                else:
                    st.warning(f"⚠️ {method_name}: Δεν βρέθηκαν πίνακες")
                    
            except Exception as e:
                st.error(f"❌ {method_name}: Σφάλμα - {str(e)}")
                continue
        
        if not all_tables:
            st.error("Δεν βρέθηκαν πίνακες με καμία μέθοδο")
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
    st.markdown('<h1 class="main-header">📄 e-EFKA PDF Data Extractor (Enhanced)</h1>', unsafe_allow_html=True)
    
    # Sidebar με οδηγίες
    with st.sidebar:
        st.markdown("## 📋 Οδηγίες")
        st.markdown("""
        1. **Ανεβάστε PDF αρχείο** e-EFKA
        2. **Πατήστε "Εξαγωγή Δεδομένων"**
        3. **Προβάλετε τα αποτελέσματα** στον πίνακα
        4. **Κατεβάστε το Excel** αρχείο
        """)
        
        st.markdown("## 🔧 Διαθέσιμες Βιβλιοθήκες")
        if CAMELOT_AVAILABLE:
            st.success("✅ camelot (καλύτερο για grid tables)")
        else:
            st.error("❌ camelot (χρειάζεται Ghostscript)")
            
        if PDFPLUMBER_AVAILABLE:
            st.success("✅ pdfplumber (καλό για πίνακες)")
        else:
            st.error("❌ pdfplumber")
            
        if PYMUPDF_AVAILABLE:
            st.success("✅ PyMuPDF (γενική χρήση)")
        else:
            st.error("❌ PyMuPDF")
        
        st.markdown("## ⚠️ Σημαντικά")
        st.markdown("""
        - **camelot**: Καλύτερο για πίνακες με grid lines
        - **pdfplumber**: Καλό για πίνακες χωρίς grid
        - **PyMuPDF**: Γενική χρήση, λιγότερο ακριβές
        - Εξάγει από **σελίδα 2** και μετά
        - Παίρνει τον **δεύτερο πίνακα** από κάθε σελίδα
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
                df = extract_efka_data_enhanced(uploaded_file)
                
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

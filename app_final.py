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
import subprocess
import datetime
import html
import json

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

def get_last_update_date():
    """Παίρνει την ημερομηνία του τελευταίου git commit."""
    try:
        # The path to the repository directory
        repo_path = Path(__file__).parent.resolve()
        date_str = subprocess.check_output(
            ['git', 'log', '-1', "--format=%cd", "--date=format:'%d/%m/%Y'"],
            cwd=repo_path,
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip().replace("'", "")
        return f"Τελευταία ενημέρωση: {date_str}"
    except Exception:
        # Fallback to current date if git command fails
        return ""

# Ρύθμιση σελίδας
if not os.environ.get("ATLAS_LITE"):
    st.set_page_config(
        page_title="Ασφαλιστικό βιογραφικό ΑΤΛΑΣ",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed"
    )

# Global CSS override removed to allow individual dataframe height control
st.markdown(
    """
    <style>
    /* Custom scrollbar styling if needed */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #f1f1f1; 
    }
    ::-webkit-scrollbar-thumb {
        background: #888; 
        border-radius: 5px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555; 
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Lookup table για την περιγραφή αποδοχών
APODOXES_DESCRIPTIONS = {
    '01': 'Τακτικές αποδοχές', '02': 'Αποδοχές υπαλλήλων ΝΠΔΔ κλπ.', '03': 'Δώρο Χριστουγέννων',
    '04': 'Δώρο Πάσχα', '05': 'Επίδομα αδείας', '06': 'Επίδομα ισολογισμού',
    '07': 'Αποδοχές αδειών εποχικά απασχ/νων Ξενοδ/λων', '08': 'Αποδοχές ασθενείας',
    '09': 'Αναδρομικές αποδοχές', '10': 'Bonus', '11': 'Υπερωρίες',
    '12': 'Αμοιβή με το κομμάτι (Φασόν)', '13': 'Τεκμαρτές Αποδοχές', '14': 'Λοιπές Αποδοχές',
    '15': 'Τεκμαρτές Αποδοχές για κλάδο ΕΤΕΑΜ', '16': 'Αμοιβές κατ\' αποκοπήν/ΕΦΑΠΑΞ',
    '17': 'Εισφορές χωρίς αποδοχές', '18': 'Κανονικές αποδοχές πληρ/των Μεσογ τουρ πλοίων',
    '19': 'Αποδοχές αδείας πληρωμάτων Μεσογ τουρ πλοίων', '20': 'Αποδοχές Ασφαλιζομένων στο ΕΤΕΑΜ',
    '21': 'Τακτικές αποδοχές', '22': 'Δώρο Χριστουγέννων', '23': 'Δώρο Πάσχα', '24': 'Επίδομα Αδείας',
    '25': 'Επίδομα Ισολογισμού', '26': 'Αποδοχές Ασθενείας', '27': 'Αναδρομικές αποδοχές',
    '28': 'Bonus', '29': 'Υπερωρίες', '30': 'Λοιπές αποδοχές', '31': 'Εισφορές χωρίς αποδοχές',
    '32': 'Τακτικές Αποδοχές – Δ.Π.Υ.', '33': 'Δώρο Πάσχα – Δ.Π.Υ.', '34': 'Επίδομα Αδείας – Δ.Π.Υ.',
    '35': 'Δώρο Χριστουγέννων – Δ.Π.Υ.',
    '36': 'Τακτικές αποδοχές για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '37': 'Δώρο Πάσχα για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '38': 'Δώρο Χριστουγέννων για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '39': 'Επίδομα Αδείας για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '40': 'Επίδομα Ισολογισμού για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '41': 'Υπερωρίες για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '42': 'Αναδρομικές αποδοχές για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '43': 'Bonus για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '44': 'Τακτικές αποδοχές για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '45': 'Δώρο Χριστουγέννων για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '46': 'Δώρο Πάσχα για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '47': 'Επίδομα Αδείας για υπολογισμό συνεισπραττόμενων εισφορών και ΕΤΕΑΜ',
    '48': 'Αναδρομικές αποδοχές για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '49': 'Bonus για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '50': 'Αποδοχές αδειών εποχικών απασχολουμένων για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '51': 'Λοιπές αποδοχές για υπολογισμό εισφορών υπέρ Ειδικού Λογαριασμού Ξενοδοχοϋπαλλήλων',
    '52': 'Τακτικές αποδοχές για υπολογισμό εισφορών ασθένειας σε είδος και σε χρήμα τ. ΤΑΞΥ',
    '53': 'Δώρο Πάσχα για υπολογισμό εισφορών ασθένειας σε είδος και σε χρήμα τ. ΤΑΞΥ',
    '54': 'Δώρο Χριστουγέννων για υπολογισμό εισφορών ασθένειας σε είδος και σε χρήμα τ. ΤΑΞΥ',
    '55': 'Επίδομα Αδείας για υπολογισμό εισφορών ασθένειας σε είδος και σε χρήμα τ. ΤΑΞΥ',
    '56': 'Τακτικές αποδοχές', '57': 'Δώρο Χριστουγέννων', '58': 'Δώρο Πάσχα', '59': 'Επίδομα Αδείας',
    '60': 'Επίδομα Ισολογισμού', '61': 'Αποδοχές Ασθενείας', '62': 'Αναδρομικές αποδοχές',
    '63': 'Bonus', '64': 'Υπερωρίες', '65': 'Λοιπές αποδοχές', '66': 'Εισφορές χωρίς αποδοχές',
    '67': 'Τακτικές αποδοχές για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '68': 'Δώρο Χριστουγέννων για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '69': 'Δώρο Πάσχα για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '70': 'Επίδομα Αδείας για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '71': 'Επίδομα Ισολογισμού για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '72': 'Αποδοχές Ασθενείας για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '73': 'Αναδρομικές αποδοχές για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '74': 'Bonus για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '75': 'Υπερωρίες για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '76': 'Λοιπές αποδοχές για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '77': 'Εισφορές χωρίς αποδοχές για υπολογισμό εισφορών υπέρ ΙΚΑ – ΕΤΕΑΜ',
    '78': 'Τακτικές Αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '79': 'Δώρο Χριστουγέννων για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '80': 'Δώρο Πάσχα για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '81': 'Επίδομα αδείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '82': 'Επίδομα Ισολογισμού για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '83': 'Αποδοχές ασθενείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '84': 'Αναδρομικές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '85': 'Bonus για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '86': 'Υπερωρίες για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '87': 'Λοιπές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '88': 'Εισφορές χωρίς αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/07 – 31/7/2012',
    '89': 'Τακτικές Αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '90': 'Δώρο Χριστουγέννων για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '91': 'Δώρο Πάσχα για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '92': 'Επίδομα αδείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '93': 'Επίδομα Ισολογισμού για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '94': 'Αποδοχές ασθενείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '95': 'Αναδρομικές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '96': 'Bonus για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '97': 'Υπερωρίες για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '98': 'Λοιπές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '99': 'Εισφορές χωρίς αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/12 – 31/7/2017',
    '100': 'Τακτικές Αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '101': 'Δώρο Χριστουγέννων για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '102': 'Δώρο Πάσχα για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '103': 'Επίδομα αδείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '104': 'Επίδομα Ισολογισμού για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '105': 'Αποδοχές ασθενείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '106': 'Αναδρομικές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '107': 'Bonus για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '108': 'Υπερωρίες για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '109': 'Λοιπές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '110': 'Εισφορές χωρίς αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/17 – 31/7/2022',
    '111': 'Τακτικές Αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '112': 'Δώρο Χριστουγέννων για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '113': 'Δώρο Πάσχα για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '114': 'Επίδομα αδείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '115': 'Επίδομα Ισολογισμού για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '116': 'Αποδοχές ασθενείας για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '117': 'Αναδρομικές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '118': 'Bonus για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '119': 'Υπερωρίες για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '120': 'Λοιπές αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
    '121': 'Εισφορές χωρίς αποδοχές για υπολογισμό εισφορών κλάδου κύριας σύνταξης τ. Τ.Σ.Ε.Α.Π.Γ.Σ.Ο. από 1/8/22',
}

# Lookup tables for insurance contribution ceiling (plafond)
PLAFOND_PALIOS = {
  "2002": 1884.75, "2003": 1960.25, "2004": 2058.25, "2005": 2140.50,
  "2006": 2226.00, "2007": 2315.00, "2008": 2384.50, "2009": 2432.25,
  "2010": 2432.25, "2011": 2432.25, "2012": 2432.25, "2013": 5546.80,
  "2014": 5546.80, "2015": 5546.80, "2016": 5861.00, "2017": 5861.00,
  "2018": 5861.00, "2019": 6500.00, "2020": 6500.00, "2021": 6500.00,
  "2022": 6500.00, "2023": 7126.94, "2024": 7126.94, "2025": 7572.62
}

PLAFOND_NEOS = {
  "2002": 4693.52, "2003": 4693.52, "2004": 4693.52, "2005": 4881.26,
  "2006": 5076.51, "2007": 5279.57, "2008": 5437.96, "2009": 5543.55,
  "2010": 5543.55, "2011": 5543.55, "2012": 5546.80, "2013": 5546.80,
  "2014": 5546.80, "2015": 5546.80, "2016": 5861.00, "2017": 5861.00,
  "2018": 5861.00, "2019": 6500.00, "2020": 6500.00, "2021": 6500.00,
  "2022": 6500.00, "2023": 7126.94, "2024": 7126.94, "2025": 7572.62
}

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
        padding: 0.8rem 1.5rem;
        margin: -4rem -5rem 0.5rem -5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
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
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: 0.2px;
    }
    .header-text p {
        margin: 0.25rem 0 0 0;
        font-size: 1rem;
        opacity: 0.9;
        color: #ffffff !important;
    }
    .header-right { display: flex; gap: 1.5rem; }
    .nav-link { 
        color: #ffffff !important; 
        text-decoration: none; 
        font-weight: 600; 
        padding: 0.5rem 1.2rem; 
        border: 1px solid rgba(255,255,255,0.5);
        border-radius: 6px;
        transition: all 0.2s ease;
        display: inline-block;
    }
    .nav-link:hover { 
        background-color: rgba(255,255,255,0.15); 
        border-color: #ffffff;
        text-decoration: none !important; 
        color: #ffffff !important;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .upload-section {
        background-color: transparent;
        padding: 1.5rem 1rem;
        border-radius: 10px;
        border: 0;
        text-align: center;
        margin: 1rem 0 2rem 0;
    }
    /* Upload Container - Modern Card Style - Εφαρμογή απευθείας στο widget */
    [data-testid="stFileUploader"] {
        background-color: #f8fbff;
        padding: 3rem;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 2px dashed #3b82f6;
    }

    /* Κεντράρισμα του uploader */
    div[data-testid="stFileUploader"] {
        margin-left: auto !important;
        margin-right: auto !important;
        max-width: 600px !important;
    }

    /* Βοηθητικό class για το κείμενο προτροπής */
    .upload-prompt-text {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1rem;
        text-align: center !important;
        width: 100%;
        display: block;
    }
    .app-container { max-width: 680px; margin: 0 auto; }
    .main-header { margin-top: 0.5rem; }
    
    /* Μωβ Header - Full Width - Modern */
    .purple-header {
        background: linear-gradient(135deg, #7b2cbf 0%, #5a189a 100%);
        color: white;
        text-align: center;
        padding: 2rem 1rem;
        margin: -4rem -5rem 2rem -5rem;
        font-size: 2rem;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    
    /* EFKA Button Style - Secondary Action */
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
    
    /* Οδηγίες Box - Modern Style */
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

    /* Footer Styles */
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
    
    /* Απόκρυψη μενού Streamlit (Fork, Settings, κτλ) */
    [data-testid="stHeader"] button[kind="header"],
    [data-testid="stHeader"] [data-testid="stDeployButton"],
    [data-testid="stHeader"] button[title="Fork this app"],
    [data-testid="stHeader"] button[title="Settings"],
    [data-testid="stHeader"] button[title="Menu"],
    [data-testid="stHeader"] button[aria-label*="Settings"],
    [data-testid="stHeader"] button[aria-label*="Menu"],
    [data-testid="stHeader"] button[aria-label*="Fork"],
    button[kind="header"],
    .stDeployButton,
    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] [data-testid="stToolbar"],
    header[data-testid="stHeader"] [data-testid="stHeaderViewButton"],
    header[data-testid="stHeader"] [data-testid="stHeaderActionElements"],
    header[data-testid="stHeader"] > div:last-child,
    header[data-testid="stHeader"] > div:nth-child(2) {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Απόκρυψη ολόκληρου του header αν είναι απαραίτητο */
    /* [data-testid="stHeader"] {
        display: none !important;
    } */
</style>
""", unsafe_allow_html=True)

def build_print_table_html(
    dataframe: pd.DataFrame,
    style_rows: list[dict[str, str]] | None = None,
    wrap_cells: bool = False,
) -> str:
    colgroup_html = '<colgroup>'
    for col in dataframe.columns:
        c_name = str(col).upper().strip()
        width = 'auto'
        if c_name in ['A/A', 'Α/Α', 'AA']:
            width = '24px'
        if c_name in ['ΕΤΟΣ', 'ETOS']:
            width = '30px'
        elif c_name in ['ΤΑΜΕΙΟ', 'TAMEIO']:
            width = '45px'
        elif c_name in ['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ']:
            width = '45px'
        elif c_name in ['ΕΡΓΟΔΟΤΗΣ']:
            width = '45px'
        elif 'ΚΛΑΔΟΣ' in c_name:
            width = '30px'
        elif c_name in ['ΠΕΡΙΓΡΑΦΗ']:
            width = '90px'
        elif 'ΑΠΟΔΟΧΩΝ' in c_name and 'ΤΥΠΟΣ' in c_name:
            width = '45px'
        elif c_name in ['ΣΥΝΟΛΟ']:
            width = '30px'
        elif c_name.endswith('ος'):
            width = '46px'
        elif 'ΜΙΚΤΕΣ' in c_name:
            width = '55px'
        elif 'ΕΙΣΦΟΡΕΣ' in c_name:
            width = '55px'
        elif 'ΠΟΣΟΣΤΟ' in c_name:
            width = '35px'
        colgroup_html += f'<col style="width:{width}">'
    colgroup_html += '</colgroup>'

    headers_html = ''.join(f"<th>{h}</th>" for h in dataframe.columns)
    rows_html = []
    for ridx, row in dataframe.iterrows():
        is_total = any(str(v).strip().startswith('Σύνολο') for v in row.values)
        tr_class = ' class="total-row"' if is_total else ''
        row_styles = style_rows[ridx] if style_rows and ridx < len(style_rows) else {}
        tds_list = []
        for cidx, v in enumerate(row.values):
            col_name = dataframe.columns[cidx]
            cell_style = row_styles.get(col_name, '')
            style_attr = f' style="{cell_style}"' if cell_style else ''
            tds_list.append(f"<td{style_attr}>{'' if pd.isna(v) else v}</td>")
        tds = ''.join(tds_list)
        rows_html.append(f"<tr{tr_class}>{tds}</tr>")
    table_class = "print-table wrap-cells" if wrap_cells else "print-table"
    return f"<table class=\"{table_class}\">{colgroup_html}<thead><tr>{headers_html}</tr></thead><tbody>{''.join(rows_html)}</tbody></table>"

def build_print_filters_html(filters: list[str] | None = None) -> str:
    if not filters:
        return ''
    cleaned = [html.escape(f) for f in filters if isinstance(f, str) and f.strip()]
    if not cleaned:
        return ''
    items = ''.join(f"<li>{item}</li>" for item in cleaned)
    return (
        "<div class='print-filters'>"
        "<div class='print-filters-label'>Ενεργά φίλτρα</div>"
        f"<ul>{items}</ul>"
        "</div>"
    )

def get_print_disclaimer_html() -> str:
    return (
        "<div class='print-disclaimer'>"
        "<strong>ΣΗΜΑΝΤΙΚΉ ΣΗΜΕΙΩΣΗ:</strong> Η παρούσα αναφορά βασίζεται αποκλειστικά στα δεδομένα που εμφανίζονται στο αρχείο ΑΤΛΑΣ/e-ΕΦΚΑ και αποτελεί απλή επεξεργασία των καταγεγραμμένων εγγραφών. "
        "Η πλατφόρμα ΑΤΛΑΣ μπορεί να περιέχει κενά ή σφάλματα και η αναφορά αυτή δεν υποκαθιστά νομική ή οικονομική συμβουλή σε καμία περίπτωση. "
        "Για θέματα συνταξιοδότησης και οριστικές απαντήσεις αρμόδιος παραμένει αποκλειστικά ο e-ΕΦΚΑ."
        "</div>"
    )

def build_print_section_html(
    title: str,
    dataframe: pd.DataFrame,
    description: str | None = None,
    filters: list[str] | None = None,
    style_rows: list[dict[str, str]] | None = None,
    wrap_cells: bool = False,
    heading_tag: str = "h2",
) -> str:
    description_html = f"<p class='print-description'>{html.escape(description)}</p>" if description else ''
    filters_html = build_print_filters_html(filters)
    table_html = build_print_table_html(dataframe, style_rows, wrap_cells=wrap_cells)
    return f"<section class='print-section'><{heading_tag}>{html.escape(title)}</{heading_tag}>{description_html}{filters_html}{table_html}</section>"

def wrap_print_html(title: str, body_html: str, auto_print: bool = True, scale: float = 1.0) -> str:
    return f"""<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <style>
    @media print {{ @page {{ size: A4 landscape; margin: 5mm; }} }}
    :root {{ --print-scale: {scale}; }}
    body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #222; }}
    h1 {{ font-size: 20px; margin: 12px 0 10px 0; text-align: center; }}
    h2 {{ font-size: 16px; margin: 18px 0 8px 0; text-align: left; }}
    .print-section {{ margin-bottom: 18px; }}
    .page-break {{ page-break-after: always; }}
    .print-client-name {{ font-size: 28px; font-weight: 700; text-align: center; margin: 0; color: #111827; }}
    .print-client-amka {{ font-size: 15px; text-align: center; margin: 2px 0 10px 0; color: #4b5563; }}
    .print-description {{ font-size: 15px; text-align: center; color: #4b5563; margin: 0 0 8px 0; }}
    .print-filters {{ font-size: 12px; margin: 0 0 10px 0; color: #374151; }}
    .print-filters-label {{ font-weight: 600; margin-bottom: 2px; }}
    .print-filters ul {{ margin: 4px 0 0 18px; padding: 0; }}
    .print-disclaimer {{ font-size: 13px; color: #374151; margin-top: 35px; line-height: 1.4; }}
    .print-disclaimer strong {{ font-weight: 700; }}
    table.print-table {{ border-collapse: collapse; width: 100%; font-size: 10px; table-layout: fixed; }}
    table.print-table thead th {{ background: #f2f4f7; border-bottom: 1px solid #d0d7de; padding: 4px 2px; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    table.print-table tbody td {{ border-bottom: 1px solid #eee; padding: 4px 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    table.print-table tbody td:first-child {{ font-weight: 700; }}
    table.print-table tbody tr.total-row td {{ background: #e6f2ff !important; color: #000; font-weight: 700 !important; }}
    table.print-table.wrap-cells thead th,
    table.print-table.wrap-cells tbody td {{
        white-space: normal;
        overflow: visible;
        text-overflow: clip;
        word-break: break-word;
    }}
    #print-root {{ transform: scale(var(--print-scale)); transform-origin: top left; }}
  </style>
</head>
<body{(" onload=\"window.print()\"" if auto_print else "")}>
  <div id="print-root">
    {body_html}
  </div>
</body>
</html>"""

def build_print_html(
    title: str,
    dataframe: pd.DataFrame,
    description: str | None = None,
    filters: list[str] | None = None,
    style_rows: list[dict[str, str]] | None = None,
    client_name: str | None = None,
    client_amka: str | None = None,
    auto_print: bool = True,
    scale: float = 1.0,
    wrap_cells: bool = False,
) -> str:
    client_name = (client_name or '').strip()
    client_amka = (client_amka or '').strip()
    name_html = f"<div class='print-client-name'>{html.escape(client_name)}</div>" if client_name else ''
    amka_html = f"<div class='print-client-amka'>ΑΜΚΑ: {html.escape(client_amka)}</div>" if client_amka else ''
    description_html = f"<p class='print-description'>{html.escape(description)}</p>" if description else ''
    filters_html = build_print_filters_html(filters)
    table_html = build_print_table_html(dataframe, style_rows, wrap_cells=wrap_cells)
    disclaimer_html = get_print_disclaimer_html()

    body_html = (
        f"{name_html}"
        f"{amka_html}"
        f"<h1>{html.escape(title)}</h1>"
        f"{description_html}"
        f"{filters_html}"
        f"{table_html}"
        f"{disclaimer_html}"
    )
    return wrap_print_html(title, body_html, auto_print, scale)

def render_print_button(
    button_key: str,
    title: str,
    dataframe: pd.DataFrame,
    description: str | None = None,
    filters: list[str] | None = None,
    style_rows: list[dict[str, str]] | None = None,
    scale: float = 1.0,
) -> None:
    """Εμφανίζει κουμπί εκτύπωσης που ανοίγει νέο παράθυρο με καλαίσθητη εκτύπωση του πίνακα.

    Args:
        button_key: Μοναδικό key για το κουμπί
        title: Τίτλος που θα εμφανιστεί στην εκτύπωση
        dataframe: Τα δεδομένα προς εκτύπωση (όπως εμφανίζονται)
        description: Προαιρετική περιγραφή που θα εμφανιστεί κάτω από τον τίτλο
        filters: Προαιρετική λίστα με περιγραφές φίλτρων που εφαρμόστηκαν
    """
    col_spacer, col_btn = st.columns([1, 0.12])
    with col_btn:
        if st.button("Εκτύπωση", key=button_key, use_container_width=True):
            # Μοναδικό nonce ώστε το component να επανα-τοποθετείται και να εκτελείται κάθε φορά
            nonce_key = f"_print_nonce_{button_key}"
            nonce = st.session_state.get(nonce_key, 0) + 1
            st.session_state[nonce_key] = nonce
            window_name = f"printwin_{button_key}_{nonce}"
            client_name = st.session_state.get('print_client_name', '').strip()
            client_amka = st.session_state.get('print_client_amka', '').strip()
            html_content = build_print_html(
                title=title,
                dataframe=dataframe,
                description=description,
                filters=filters,
                style_rows=style_rows,
                client_name=client_name,
                client_amka=client_amka,
                scale=scale
            )

            # Δημιουργία JavaScript που θα ανοίξει νέο tab με auto-print
            js_code = f"""
<script>
function openPrintTab() {{
  const htmlContent = {json.dumps(html_content)};
  const blob = new Blob([htmlContent], {{ type: 'text/html' }});
  const url = URL.createObjectURL(blob);
  const printWindow = window.open(url, '{window_name}');
  if (printWindow) {{
    printWindow.focus();
  }}
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}}

openPrintTab();
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
        is_negative = False

        # Υποστήριξη unicode minus και αρνητικού σε παρένθεση/τέλος
        clean_value = clean_value.replace('\u2212', '-')
        if clean_value.startswith('(') and clean_value.endswith(')'):
            is_negative = True
            clean_value = clean_value[1:-1].strip()
        if clean_value.endswith('-'):
            is_negative = True
            clean_value = clean_value[:-1].strip()
        if clean_value.startswith('-'):
            is_negative = True
            clean_value = clean_value[1:].strip()
        
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
        result = float(clean_value)
        return -result if is_negative else result
    except (ValueError, TypeError):
        return 0.0

def get_negative_amount_sign(gross_val, contrib_val) -> int:
    """Επιστρέφει -1 όταν υπάρχουν αρνητικά ποσά (αναστροφή εγγραφής)."""
    try:
        if (gross_val is not None and gross_val < 0) or (contrib_val is not None and contrib_val < 0):
            return -1
    except Exception:
        pass
    return 1

def apply_negative_time_sign(df: pd.DataFrame,
                             gross_col: str = 'Μικτές αποδοχές',
                             contrib_col: str = 'Συνολικές εισφορές') -> pd.DataFrame:
    """Αν υπάρχουν αρνητικά ποσά, κάνει αρνητικές τις ημέρες/μήνες/έτη."""
    if not isinstance(df, pd.DataFrame):
        return df
    if gross_col not in df.columns and contrib_col not in df.columns:
        return df

    def _row_sign(r) -> int:
        gross_val = clean_numeric_value(r.get(gross_col, 0), exclude_drx=True)
        contrib_val = clean_numeric_value(r.get(contrib_col, 0), exclude_drx=True)
        return get_negative_amount_sign(gross_val, contrib_val)

    sign_series = df.apply(_row_sign, axis=1)
    for col in ['Έτη', 'Μήνες', 'Ημέρες']:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric_value)
            df[col] = df[col] * sign_series
    return df

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
        'Α-Μ εργοδότη': ['α μ εργοδότη', 'α/μ εργοδ', 'εργοδότη', 'α-μ εργοδότη'],
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

def build_description_map(df: pd.DataFrame) -> dict[str, str]:
    """Δημιουργεί mapping κωδικός -> περιγραφή για πακέτα κάλυψης."""
    description_map = {}
    if 'Κωδικός Κλάδων / Πακέτων Κάλυψης' in df.columns and 'Περιγραφή' in df.columns:
        desc_df = df[['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']].copy()
        desc_df = desc_df.dropna(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή'])
        desc_df = desc_df[desc_df['Κωδικός Κλάδων / Πακέτων Κάλυψης'] != '']
        desc_df = desc_df[desc_df['Περιγραφή'] != '']
        desc_df = desc_df.drop_duplicates(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης'])
        for _, row in desc_df.iterrows():
            code = str(row['Κωδικός Κλάδων / Πακέτων Κάλυψης']).strip()
            desc = str(row['Περιγραφή']).strip()
            description_map[code] = desc
    return description_map

def compute_parallel_months(base_df: pd.DataFrame) -> list[tuple[int, int]]:
    if base_df.empty or not all(col in base_df.columns for col in ['Από', 'Έως']):
        return []

    parallel_rows = []
    for _, row in base_df.iterrows():
        try:
            if pd.isna(row['Από']) or pd.isna(row['Έως']):
                continue

            start_dt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
            end_dt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')

            if pd.isna(start_dt) or pd.isna(end_dt):
                continue

            days_val = 0
            if 'Ημέρες' in row and pd.notna(row['Ημέρες']) and str(row['Ημέρες']).strip() != '':
                d = clean_numeric_value(row['Ημέρες'])
                if d is not None and d != 0:
                    days_val += d

            if 'Έτη' in row and pd.notna(row['Έτη']):
                y = clean_numeric_value(row['Έτη'])
                if y is not None and y != 0:
                    days_val += y * 300

            if 'Μήνες' in row and pd.notna(row['Μήνες']):
                m = clean_numeric_value(row['Μήνες'])
                if m is not None and m != 0:
                    days_val += m * 25

            curr = start_dt.replace(day=1)
            end_month_dt = end_dt.replace(day=1)
            months_list = []
            while curr <= end_month_dt:
                months_list.append(curr)
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)

            num_months = len(months_list)
            if num_months == 0:
                continue

            days_per_month = days_val / num_months

            for m_dt in months_list:
                parallel_rows.append({
                    'ΕΤΟΣ': m_dt.year,
                    'Μήνας_Num': m_dt.month,
                    'ΤΑΜΕΙΟ': str(row.get('Ταμείο', '')).strip(),
                    'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': str(row.get('Τύπος Ασφάλισης', '')).strip(),
                    'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': str(row.get('Κλάδος/Πακέτο Κάλυψης', '')).strip(),
                    'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': str(row.get('Τύπος Αποδοχών', '')).strip(),
                    'Ημέρες': days_per_month
                })
        except Exception:
            continue

    if not parallel_rows:
        return []

    p_c_df = pd.DataFrame(parallel_rows)

    def is_ika_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        et = str(row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')).strip()
        is_ika_tameio = 'IKA' in t or 'ΙΚΑ' in t
        is_misthoti = 'ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type
        is_et_ika = et in ['01', '1', '16', '99']
        return (is_ika_tameio or is_misthoti) and is_et_ika

    def is_oaee_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
        is_oaee_tameio = 'OAEE' in t or 'ΟΑΕΕ' in t or 'TEBE' in t or 'ΤΕΒΕ' in t or 'TAE' in t or 'ΤΑΕ' in t
        is_k = kl in ['K', 'Κ']
        return is_oaee_tameio and is_k

    def is_tsm_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
        is_tsm_tameio = 'ΤΣΜΕΔΕ' in t or 'TSMEDE' in t
        is_ks = kl in ['ΚΣ', 'ΠΚΣ', 'KS', 'PKS']
        return is_tsm_tameio and is_ks

    def is_oga_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
        is_oga_tameio = 'ΟΓΑ' in t or 'OGA' in t
        is_k = kl in ['K', 'Κ']
        return is_oga_tameio and is_k

    p_c_df['is_ika'] = p_c_df.apply(is_ika_match, axis=1)
    p_c_df['is_oaee'] = p_c_df.apply(is_oaee_match, axis=1)
    p_c_df['is_tsm'] = p_c_df.apply(is_tsm_match, axis=1)
    p_c_df['is_oga'] = p_c_df.apply(is_oga_match, axis=1)

    month_groups = p_c_df.groupby(['ΕΤΟΣ', 'Μήνας_Num'])
    valid_months = []
    for (year, month), group in month_groups:
        ika_days = group.loc[group['is_ika'], 'Ημέρες'].sum()
        oaee_days = group.loc[group['is_oaee'], 'Ημέρες'].sum()
        tsm_days = group.loc[group['is_tsm'], 'Ημέρες'].sum()
        oga_days = group.loc[group['is_oga'], 'Ημέρες'].sum()

        has_ika = ika_days > 0
        has_oaee = oaee_days > 0
        has_tsm = tsm_days > 0
        has_oga = oga_days > 0

        if (has_ika and has_oaee) or (has_oaee and has_tsm) or (has_oga and (has_ika or has_oaee)):
            if year <= 2016:
                valid_months.append((year, month))

    return valid_months

def generate_audit_report(data_df: pd.DataFrame, extra_data_df: pd.DataFrame | None = None) -> pd.DataFrame:
    audit_rows = []

    # Check 1: Old/New Insured
    try:
        dates = pd.to_datetime(data_df['Από'], format='%d/%m/%Y', errors='coerce')
        min_date = dates.min()
        if pd.notna(min_date):
            cutoff = pd.Timestamp('1993-01-01')
            is_palios = min_date < cutoff
            status_str = "Παλιός" if is_palios else "Νέος"
            details = f"Πρώτη εγγραφή: {min_date.strftime('%d/%m/%Y')}"
            audit_rows.append({
                'A/A': 1, 'Έλεγχος': 'Παλιός ή νέος ασφαλισμένος',
                'Εύρημα': status_str, 'Λεπτομέρειες': details, 'Ενέργειες': '-'
            })
    except Exception:
        pass

    # Check 2: Insurance Funds History (ανά Ταμείο & Τύπο Ασφάλισης: πρώτη/τελευταία ημερομηνία)
    try:
        if 'Ταμείο' in data_df.columns:
            temp_df = data_df.copy()
            temp_df['Start'] = pd.to_datetime(temp_df['Από'], format='%d/%m/%Y', errors='coerce')
            temp_df['End'] = pd.to_datetime(temp_df['Έως'], format='%d/%m/%Y', errors='coerce')
            temp_df['End'] = temp_df['End'].fillna(temp_df['Start'])
            temp_df = temp_df.dropna(subset=['Start'])

            # Ομαδοποίηση ανά Ταμείο και Τύπο Ασφάλισης (αν υπάρχει)
            group_cols = ['Ταμείο']
            if 'Τύπος Ασφάλισης' in temp_df.columns:
                group_cols.append('Τύπος Ασφάλισης')

            grouped = temp_df.groupby(group_cols).agg({
                'Start': 'min',
                'End': 'max'
            }).reset_index()
            grouped = grouped.sort_values('Start')

            rows_html = []
            for _, row2 in grouped.iterrows():
                fund = str(row2['Ταμείο']).strip()
                typ = str(row2['Τύπος Ασφάλισης']).strip() if 'Τύπος Ασφάλισης' in grouped.columns else ""
                label = fund if typ in [None, '', 'nan'] else f"{fund} - {typ}"
                s_date = row2['Start'].strftime('%d/%m/%Y')
                e_date = row2['End'].strftime('%d/%m/%Y')
                rows_html.append(
                    f"<div style='font-weight: 600; color: #2c3e50;'>{label}</div>"
                    f"<div style='color: #555;'>{s_date} - {e_date}</div>"
                )
            history_html = (
                "<div style='display: grid; grid-template-columns: 1fr auto; column-gap: 12px; row-gap: 4px;'>"
                + "".join(rows_html) +
                "</div>"
            )

            count_funds = temp_df['Ταμείο'].dropna().nunique()
            audit_rows.append({
                'A/A': 2, 'Έλεγχος': 'Ασφαλιστικά ταμεία',
                'Εύρημα': f"{count_funds} Ταμεία",
                'Λεπτομέρειες': history_html, 'Ενέργειες': '-'
            })
    except Exception:
        pass

    # Check 3: Gaps
    try:
        gaps = find_gaps_in_insurance_data(data_df)
        if not gaps.empty:
            gap_details = []
            for _, g in gaps.head(3).iterrows():
                duration = g.get('Ημερολογιακές ημέρες', '')
                gap_details.append(f"Από {g['Από']} έως {g['Έως']} ({duration} ημέρες)")
            if len(gaps) > 3:
                gap_details.append("...")

            audit_rows.append({
                'A/A': 3, 'Έλεγχος': 'Κενά ασφάλισης',
                'Εύρημα': f"{len(gaps)} Διάστημα(τα)",
                'Λεπτομέρειες': "<br>".join(gap_details),
                'Ενέργειες': 'Ελέγξτε την καρτέλα "Κενά Διαστήματα"'
            })
        else:
            audit_rows.append({
                'A/A': 3, 'Έλεγχος': 'Κενά ασφάλισης',
                'Εύρημα': 'Κανένα', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'
            })
    except Exception as e:
        audit_rows.append({
            'A/A': 3, 'Έλεγχος': 'Κενά ασφάλισης',
            'Εύρημα': 'Σφάλμα ελέγχου', 'Λεπτομέρειες': str(e), 'Ενέργειες': '-'
        })

    # Check 4: Unpaid OAEE / TSMEDE / OGA / TSAY
    try:
        if 'Κλάδος/Πακέτο Κάλυψης' in data_df.columns and 'Συνολικές εισφορές' in data_df.columns:
            def clean_money_chk(x):
                if isinstance(x, str):
                    if 'DRX' in x or 'ΔΡΧ' in x:
                        return 0.0
                    return clean_numeric_value(x, exclude_drx=True)
                return x

            t_df = data_df.copy()
            t_df['C'] = t_df['Συνολικές εισφορές'].apply(clean_money_chk)
            t_df['K'] = t_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip().str.upper()
            t_df['T'] = t_df['Ταμείο'].astype(str).str.strip().upper() if 'Ταμείο' in t_df.columns else ''

            # Ορισμός συνθηκών για κάθε ταμείο
            cond_oaee = (t_df['K'].isin(['K', 'Κ'])) & (t_df['T'].str.contains('OAEE|ΟΑΕΕ|TEBE|ΤΕΒΕ|TAE|ΤΑΕ', na=False))
            cond_tsmede = (t_df['K'].isin(['ΚΣ', 'KS'])) & (t_df['T'].str.contains('ΤΣΜΕΔΕ|TSMEDE', na=False))
            cond_oga = (t_df['K'].isin(['K', 'Κ'])) & (t_df['T'].str.contains('ΟΓΑ|OGA', na=False))
            cond_tsay = (t_df['K'].isin(['ME', 'ΜΕ'])) & (t_df['T'].str.contains('ΤΣΑΥ|TSAY', na=False))

            unpaid = t_df[(cond_oaee | cond_tsmede | cond_oga | cond_tsay) & (t_df['C'] == 0)]

            if not unpaid.empty:
                # Ομαδοποίηση ανά ταμείο για αναφορά
                fund_details = []
                
                # Helper για καταμέτρηση ανά κατηγορία
                def get_fund_unpaid(condition, label):
                    u = t_df[condition & (t_df['C'] == 0)]
                    if not u.empty:
                        return f"{len(u)} μήνες {label}"
                    return None

                f_oaee = get_fund_unpaid(cond_oaee, "ΟΑΕΕ (Κ)")
                f_tsmede = get_fund_unpaid(cond_tsmede, "ΤΣΜΕΔΕ (ΚΣ)")
                f_oga = get_fund_unpaid(cond_oga, "ΟΓΑ (Κ)")
                f_tsay = get_fund_unpaid(cond_tsay, "ΤΣΑΥ (ΜΕ)")

                all_funds = [x for x in [f_oaee, f_tsmede, f_oga, f_tsay] if x]
                details_msg = ", ".join(all_funds) + " με μηδενική εισφορά."

                # Προσθήκη ενδεικτικών μηνών
                months = []
                for _, r in unpaid.head(5).iterrows(): # Πρώτοι 5 για συντομία
                    try:
                        d = pd.to_datetime(r['Από'], format='%d/%m/%Y', errors='coerce')
                        if pd.notna(d):
                            months.append(d.strftime('%m/%Y'))
                    except:
                        pass
                
                if months:
                    details_msg += f"<br><span style='font-size: 0.85rem; color: #666;'>Ενδεικτικά: ({', '.join(months)}...)</span>"

                audit_rows.append({
                    'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές',
                    'Εύρημα': 'Εντοπίστηκαν',
                    'Λεπτομέρειες': details_msg,
                    'Ενέργειες': 'Ελέγξτε για τυχόν οφειλές στα αντίστοιχα ταμεία'
                })
            else:
                audit_rows.append({'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές', 'Εύρημα': 'Καμία', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
    except Exception:
        pass

    # Check 5: Parallel Insurance (Month-based Logic)
    try:
        valid_months = compute_parallel_months(data_df)
        p_found = bool(valid_months)

        if p_found:
            audit_rows.append({
                'A/A': 5, 'Έλεγχος': 'Παράλληλη ασφάλιση',
                'Εύρημα': 'Πιθανή',
                'Λεπτομέρειες': 'Βρέθηκαν χρονικά επικαλυπτόμενα διαστήματα ΙΚΑ (01/16/99) & ΟΑΕΕ (Κ), ΟΑΕΕ (Κ) & ΤΣΜΕΔΕ (ΚΣ/ΠΚΣ) ή ΟΓΑ (Κ) & ΙΚΑ/ΟΑΕΕ.',
                'Ενέργειες': 'Ελέγξτε την καρτέλα "Παράλληλη Ασφάλιση"'
            })
        else:
            audit_rows.append({'A/A': 5, 'Έλεγχος': 'Παράλληλη ασφάλιση', 'Εύρημα': 'Όχι', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
    except Exception:
        pass

    # Check 6: Multiple Employers (Month-based Logic)
    try:
        m_found = False

        if 'Α-Μ εργοδότη' in data_df.columns:
            m_df = data_df.copy()
            m_df['Start'] = pd.to_datetime(m_df['Από'], format='%d/%m/%Y', errors='coerce')
            m_df['End'] = pd.to_datetime(m_df['Έως'], format='%d/%m/%Y', errors='coerce')
            m_df = m_df.dropna(subset=['Start', 'End'])

            def is_ika_multi(row):
                et = str(row.get('Τύπος Αποδοχών', '')).strip()
                t = str(row.get('Ταμείο', '')).upper()
                return ('IKA' in t or 'ΙΚΑ' in t) and et in ['01', '1', '16', '99']

            m_df['is_ika'] = m_df.apply(is_ika_multi, axis=1)
            m_df = m_df[m_df['is_ika']]

            m_df['Emp'] = m_df['Α-Μ εργοδότη'].astype(str).str.strip().replace(['nan', 'None', '', 'NaN'], pd.NA)
            m_df = m_df.dropna(subset=['Emp'])

            if m_df['Emp'].nunique() > 1:
                m_df = m_df.sort_values('Start')
                seen_months = {}

                for _, row in m_df.iterrows():
                    s = row['Start']
                    e = row['End']
                    emp = row['Emp']
                    curr = s.replace(day=1)
                    end_m = e.replace(day=1)
                    while curr <= end_m:
                        k = (curr.year, curr.month)
                        if k not in seen_months:
                            seen_months[k] = set()
                        seen_months[k].add(emp)
                        if len(seen_months[k]) > 1:
                            m_found = True
                            break
                        if curr.month == 12:
                            curr = curr.replace(year=curr.year + 1, month=1)
                        else:
                            curr = curr.replace(month=curr.month + 1)
                    if m_found:
                        break

        if m_found:
            audit_rows.append({
                'A/A': 6, 'Έλεγχος': 'Πολλαπλή απασχόληση',
                'Εύρημα': 'Πιθανή',
                'Λεπτομέρειες': "Βρέθηκαν μήνες με > 1 εργοδότες για ΙΚΑ (01/16/99).",
                'Ενέργειες': 'Ελέγξτε την καρτέλα "Πολλαπλή"'
            })
        else:
            audit_rows.append({'A/A': 6, 'Έλεγχος': 'Πολλαπλή απασχόληση', 'Εύρημα': '-', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
    except Exception:
        pass

    # Check 7: Low APD
    try:
        if 'Μικτές αποδοχές' in data_df.columns and 'Συνολικές εισφορές' in data_df.columns:
            def get_val_chk(x):
                if isinstance(x, str):
                    if 'DRX' in x or 'ΔΡΧ' in x:
                        return 0.0
                    return clean_numeric_value(x, exclude_drx=True) or 0.0
                return x if pd.notna(x) else 0.0
            t_df = data_df.copy()
            t_df['G'] = t_df['Μικτές αποδοχές'].apply(get_val_chk)
            t_df['C'] = t_df['Συνολικές εισφορές'].apply(get_val_chk)
            t_df = t_df[t_df['G'] > 0]
            if not t_df.empty:
                t_df['Ratio'] = t_df['C'] / t_df['G']
                cnt = len(t_df[t_df['Ratio'] < 0.30])
                if cnt > 0:
                    audit_rows.append({
                        'A/A': 7, 'Έλεγχος': 'ΑΠΔ με χαμηλές κρατήσεις',
                        'Εύρημα': 'Εντοπίστηκαν',
                        'Λεπτομέρειες': f"{cnt} εγγραφές με εισφορές < 30% των αποδοχών.",
                        'Ενέργειες': 'Ελέγξτε για πιθανά σφάλματα ή ειδικές περιπτώσεις'
                    })
                else:
                    audit_rows.append({'A/A': 7, 'Έλεγχος': 'ΑΠΔ με χαμηλές κρατήσεις', 'Εύρημα': 'Καμία', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
            else:
                audit_rows.append({'A/A': 7, 'Έλεγχος': 'ΑΠΔ με χαμηλές κρατήσεις', 'Εύρημα': '-', 'Λεπτομέρειες': 'Δεν βρέθηκαν αποδοχές', 'Ενέργειες': '-'})
    except Exception:
        pass

    # Check 8: Plafond
    try:
        if 'Από' in data_df.columns and 'Μικτές αποδοχές' in data_df.columns and 'Μήνες' in data_df.columns:
            t_df = data_df.copy()
            t_df['Dt'] = pd.to_datetime(t_df['Από'], format='%d/%m/%Y', errors='coerce')
            t_df['Y'] = t_df['Dt'].dt.year

            def get_val_chk(x):
                if isinstance(x, str):
                    if 'DRX' in x or 'ΔΡΧ' in x:
                        return 0.0
                    return clean_numeric_value(x, exclude_drx=True) or 0.0
                return x if pd.notna(x) else 0.0

            t_df['G'] = t_df['Μικτές αποδοχές'].apply(get_val_chk)
            t_df['M'] = t_df['Μήνες'].apply(lambda x: clean_numeric_value(x) or 1)

            min_dt = t_df['Dt'].min()
            is_p = False
            if pd.notna(min_dt) and min_dt < pd.Timestamp('1993-01-01'):
                is_p = True
            curr_pl = PLAFOND_PALIOS if is_p else PLAFOND_NEOS

            exc = 0
            for _, r in t_df.iterrows():
                ys = str(int(r['Y'])) if pd.notna(r['Y']) else ""
                if ys in curr_pl:
                    pl = curr_pl.get(ys)
                    months = r.get('M') or 1
                    if months <= 0:
                        months = 1
                    if r['G'] > pl * months:
                        exc += 1

            if exc > 0:
                audit_rows.append({
                    'A/A': 8, 'Έλεγχος': 'Πλαφόν αποδοχών',
                    'Εύρημα': 'Εντοπίστηκαν',
                    'Λεπτομέρειες': f"{exc} εγγραφές υπερβαίνουν το πλαφόν αποδοχών.",
                    'Ενέργειες': 'Ελέγξτε την καρτέλα "Ανάλυση ΑΠΔ"'
                })
            else:
                audit_rows.append({'A/A': 8, 'Έλεγχος': 'Πλαφόν αποδοχών', 'Εύρημα': 'Όχι', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
    except Exception:
        pass

    # Check 9: Aggregated Intervals (Enhanced with fund/date rules)
    try:
        if 'Από' in data_df.columns and 'Έως' in data_df.columns:
            t_df = data_df.copy()
            t_df['D_From'] = pd.to_datetime(t_df['Από'], format='%d/%m/%Y', errors='coerce')
            t_df['D_To'] = pd.to_datetime(t_df['Έως'], format='%d/%m/%Y', errors='coerce')
            t_df['Duration'] = (t_df['D_To'] - t_df['D_From']).dt.days + 1

            def get_num(val):
                try:
                    return clean_numeric_value(val) or 0
                except Exception:
                    return 0

            def is_expected_oaee(r):
                tam = str(r.get('Ταμείο', '')).upper()
                if 'ΟΑΕΕ' not in tam:
                    return False
                months_val = get_num(r.get('Μήνες'))
                days_val = get_num(r.get('Ημέρες'))
                # OAEE: μέχρι 2 μήνες με 25 ημέρες/μήνα θεωρούνται τυπικά
                if months_val and months_val <= 2:
                    if days_val and abs(days_val - months_val * 25) <= 1:
                        return True
                    if not days_val and r.get('Duration', 0) <= 62:
                        return True
                return False

            def is_expected_tsm(r):
                tam = str(r.get('Ταμείο', '')).upper()
                if 'ΤΣΜΕΔΕ' not in tam:
                    return False
                months_val = get_num(r.get('Μήνες'))
                days_val = get_num(r.get('Ημέρες'))
                d_from, d_to = r.get('D_From'), r.get('D_To')
                if pd.notna(d_from) and pd.notna(d_to) and d_from.year == d_to.year:
                    sem1 = (d_from.month == 1 and d_to.month == 6)
                    sem2 = (d_from.month == 7 and d_to.month == 12)
                    if sem1 or sem2:
                        # 6 μήνες με ~25 ημέρες/μήνα είναι αναμενόμενοι
                        if months_val == 6 and (not days_val or abs(days_val - 150) <= 2):
                            return True
                        if not months_val and 150 <= r.get('Duration', 0) <= 190:
                            return True
                return False

            agg_recs = t_df[
                (t_df['Duration'] > 31) &
                (t_df['D_To'] < pd.Timestamp('2002-01-01'))
            ].copy()

            if not agg_recs.empty:
                agg_recs = agg_recs[
                    ~agg_recs.apply(lambda r: is_expected_oaee(r) or is_expected_tsm(r), axis=1)
                ]

            if not agg_recs.empty:
                count_total = len(agg_recs)
                count_year = len(agg_recs[agg_recs['Duration'] > 366])
                details_list = []
                agg_recs = agg_recs.sort_values('D_From')
                for _, r in agg_recs.iterrows():
                    tam = str(r.get('Ταμείο', '')).strip()
                    d_str = f"{r['Από']}-{r['Έως']}"
                    details_list.append(f"{tam} ({d_str})")
                details_str = "<br>".join(details_list)
                finding_msg = f"{count_total} > 1 μήνα"
                if count_year > 0:
                    finding_msg += f", {count_year} > 1 έτος"

                audit_rows.append({
                    'A/A': 9, 'Έλεγχος': 'Ενοποιημένα διαστήματα',
                    'Εύρημα': finding_msg,
                    'Λεπτομέρειες': details_str,
                    'Ενέργειες': 'Ελέγξτε το αρχείο ΑΤΛΑΣ. Οι σχετικές ημέρες ασφάλισης κατανεμήθηκαν ισομερώς στην καρτέλα Καταμέτρηση'
                })
            else:
                audit_rows.append({'A/A': 9, 'Έλεγχος': 'Ενοποιημένα διαστήματα', 'Εύρημα': 'Κανένα', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
    except Exception:
        pass

    return pd.DataFrame(audit_rows)

def build_summary_grouped_display(summary_df: pd.DataFrame, source_df: pd.DataFrame, basis_label: str | None = None) -> pd.DataFrame:
    """Επιστρέφει το μορφοποιημένο DataFrame της Συνοπτικής Αναφοράς."""
    summary_df = summary_df.copy()
    summary_df['Κλάδος/Πακέτο Κάλυψης'] = summary_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
    summary_df['Από_dt'] = pd.to_datetime(summary_df.get('Από'), format='%d/%m/%Y', errors='coerce')
    summary_df['Έως_dt'] = pd.to_datetime(summary_df.get('Έως'), format='%d/%m/%Y', errors='coerce')
    summary_df = summary_df.dropna(subset=['Από_dt'])

    numeric_columns = ['Έτη', 'Μήνες', 'Ημέρες']
    currency_columns = ['Μικτές αποδοχές', 'Συνολικές εισφορές']
    for col in numeric_columns:
        if col in summary_df.columns:
            summary_df[col] = summary_df[col].apply(clean_numeric_value)
    for col in currency_columns:
        if col in summary_df.columns:
            summary_df[col] = summary_df[col].apply(lambda x: clean_numeric_value(x, exclude_drx=True))

    summary_df = apply_negative_time_sign(summary_df)

    group_keys = ['Κλάδος/Πακέτο Κάλυψης']
    if 'Ταμείο' in summary_df.columns:
        group_keys.append('Ταμείο')

    grouped = summary_df.groupby(group_keys).agg({
        'Από_dt': 'min',
        'Έως_dt': 'max',
        'Έτη': 'sum',
        'Μήνες': 'sum',
        'Ημέρες': 'sum',
        'Μικτές αποδοχές': 'sum',
        'Συνολικές εισφορές': 'sum'
    }).reset_index()

    grouped['Από'] = grouped['Από_dt'].dt.strftime('%d/%m/%Y')
    grouped['Έως'] = grouped['Έως_dt'].dt.strftime('%d/%m/%Y')
    grouped = grouped.drop(columns=['Από_dt', 'Έως_dt'])

    if basis_label is None:
        try:
            basis_label = st.session_state.get('ins_days_basis', 'Μήνας = 25, Έτος = 300')
        except Exception:
            basis_label = 'Μήνας = 25, Έτος = 300'

    if str(basis_label).startswith('Μήνας = 30'):
        month_days, year_days = 30, 360
    else:
        month_days, year_days = 25, 300

    grouped['Συνολικές ημέρες'] = (
        grouped['Ημέρες'].fillna(0) +
        grouped['Μήνες'].fillna(0) * month_days +
        grouped['Έτη'].fillna(0) * year_days
    ).round(0).astype(int)

    record_counts = summary_df.groupby(group_keys).size().reset_index(name='Αριθμός Εγγραφών')
    summary_final = grouped.merge(record_counts, on=group_keys, how='left')

    if 'Κωδικός Κλάδων / Πακέτων Κάλυψης' in source_df.columns and 'Περιγραφή' in source_df.columns:
        desc_df_merge = source_df[['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']].copy()
        desc_df_merge = desc_df_merge.dropna(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή'])
        desc_df_merge = desc_df_merge[desc_df_merge['Κωδικός Κλάδων / Πακέτων Κάλυψης'] != '']
        desc_df_merge = desc_df_merge[desc_df_merge['Περιγραφή'] != '']
        desc_df_merge = desc_df_merge.drop_duplicates(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης'])
        desc_df_merge.columns = ['Κλάδος/Πακέτο Κάλυψης', 'Περιγραφή']
        desc_df_merge['Κλάδος/Πακέτο Κάλυψης'] = desc_df_merge['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
        summary_final = summary_final.merge(desc_df_merge, on='Κλάδος/Πακέτο Κάλυψης', how='left')

    columns_order = ['Κλάδος/Πακέτο Κάλυψης']
    if 'Ταμείο' in summary_final.columns:
        columns_order.append('Ταμείο')
    if 'Περιγραφή' in summary_final.columns:
        columns_order.append('Περιγραφή')
    columns_order += ['Από', 'Έως', 'Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες',
                      'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
    summary_final = summary_final[columns_order]

    display_summary = summary_final.copy()
    display_summary['Μικτές αποδοχές'] = display_summary['Μικτές αποδοχές'].apply(format_currency)
    display_summary['Συνολικές εισφορές'] = display_summary['Συνολικές εισφορές'].apply(format_currency)

    numeric_columns_summary = ['Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες', 'Αριθμός Εγγραφών']
    for col in numeric_columns_summary:
        if col in display_summary.columns:
            decimals = 1 if col in ['Έτη', 'Μήνες'] else 0
            display_summary[col] = display_summary[col].apply(
                lambda x: format_number_greek(x, decimals=decimals) if pd.notna(x) and x != '' else x
            )

    return display_summary

def build_count_report(count_df: pd.DataFrame, description_map: dict[str, str] | None = None, show_count_totals_only: bool = False):
    required_cols = ['Από', 'Έως', 'Ημέρες']
    if not all(col in count_df.columns for col in required_cols):
        return pd.DataFrame(), [], None, [], []

    counting_rows = []

    def _get_num(val):
        try:
            return clean_numeric_value(val) or 0
        except Exception:
            return 0

    def _is_expected_oaee(r, duration_days):
        tam = str(r.get('Ταμείο', '')).upper()
        if 'ΟΑΕΕ' not in tam:
            return False
        months_val = _get_num(r.get('Μήνες'))
        days_val = _get_num(r.get('Ημέρες'))
        if months_val and months_val <= 2:
            if days_val and abs(days_val - months_val * 25) <= 1:
                return True
            if not days_val and duration_days <= 62:
                return True
        return False

    def _is_expected_tsm(r, duration_days, start_dt, end_dt):
        tam = str(r.get('Ταμείο', '')).upper()
        if 'ΤΣΜΕΔΕ' not in tam:
            return False
        months_val = _get_num(r.get('Μήνες'))
        days_val = _get_num(r.get('Ημέρες'))
        if pd.notna(start_dt) and pd.notna(end_dt) and start_dt.year == end_dt.year:
            sem1 = (start_dt.month == 1 and end_dt.month == 6)
            sem2 = (start_dt.month == 7 and end_dt.month == 12)
            if sem1 or sem2:
                if months_val == 6 and (not days_val or abs(days_val - 150) <= 2):
                    return True
                if not months_val and 150 <= duration_days <= 190:
                    return True
        return False

    for _, row in count_df.iterrows():
        try:
            if pd.isna(row['Από']) or pd.isna(row['Έως']):
                continue

            start_dt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
            end_dt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')

            if pd.isna(start_dt) or pd.isna(end_dt):
                continue

            duration_days = (end_dt - start_dt).days + 1
            is_pre2002 = end_dt < pd.Timestamp('2002-01-01')
            expected_agg_pattern = _is_expected_oaee(row, duration_days) or _is_expected_tsm(row, duration_days, start_dt, end_dt)

            days_val = 0
            if 'Ημέρες' in row and pd.notna(row['Ημέρες']) and str(row['Ημέρες']).strip() != '':
                d = clean_numeric_value(row['Ημέρες'])
                if d is not None and d != 0:
                    days_val += d

            if 'Έτη' in row and pd.notna(row['Έτη']):
                y = clean_numeric_value(row['Έτη'])
                if y is not None and y != 0:
                    days_val += y * 300

            if 'Μήνες' in row and pd.notna(row['Μήνες']):
                m = clean_numeric_value(row['Μήνες'])
                if m is not None and m != 0:
                    days_val += m * 25

            raw_gross = str(row.get('Μικτές αποδοχές', ''))
            if 'ΔΡΧ' in raw_gross.upper() or 'DRX' in raw_gross.upper():
                gross_val = 0.0
            else:
                gross_val = clean_numeric_value(raw_gross, exclude_drx=True)
            if gross_val is None:
                gross_val = 0.0

            raw_contrib = str(row.get('Συνολικές εισφορές', ''))
            if 'ΔΡΧ' in raw_contrib.upper() or 'DRX' in raw_contrib.upper():
                contrib_val = 0.0
            else:
                contrib_val = clean_numeric_value(raw_contrib, exclude_drx=True)
            if contrib_val is None:
                contrib_val = 0.0

            sign = get_negative_amount_sign(gross_val, contrib_val)
            if sign == -1:
                days_val = -abs(days_val)

            tameio = str(row.get('Ταμείο', '')).strip()
            insurance_type = str(row.get('Τύπος Ασφάλισης', '')).strip()
            employer = str(row.get('Α-Μ εργοδότη', '')).strip()
            klados = str(row.get('Κλάδος/Πακέτο Κάλυψης', '')).strip()
            klados_desc = description_map.get(klados, '') if isinstance(description_map, dict) else ''
            earnings_type = str(row.get('Τύπος Αποδοχών', '')).strip()

            curr = start_dt.replace(day=1)
            end_month_dt = end_dt.replace(day=1)

            months_list = []
            while curr <= end_month_dt:
                months_list.append(curr)
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)

            num_months = len(months_list)
            if num_months == 0:
                continue

            days_per_month = days_val / num_months
            gross_per_month = gross_val / num_months
            contrib_per_month = contrib_val / num_months
            is_aggregate = (num_months > 1) and is_pre2002 and (duration_days > 31) and not expected_agg_pattern

            for m_dt in months_list:
                counting_rows.append({
                    'ΕΤΟΣ': m_dt.year,
                    'ΤΑΜΕΙΟ': tameio,
                    'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': insurance_type,
                    'ΕΡΓΟΔΟΤΗΣ': employer,
                    'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': klados,
                    'ΠΕΡΙΓΡΑΦΗ': klados_desc,
                    'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': earnings_type,
                    'Μήνας_Num': m_dt.month,
                    'Ημέρες': days_per_month,
                    'Μικτές_Part': gross_per_month,
                    'Εισφορές_Part': contrib_per_month,
                    'Is_Aggregate': is_aggregate
                })
        except Exception:
            continue

    if not counting_rows:
        return pd.DataFrame(), [], None, [], []

    c_df = pd.DataFrame(counting_rows)

    annual_totals = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'])[['Ημέρες', 'Μικτές_Part', 'Εισφορές_Part']].sum().reset_index()
    annual_totals.rename(columns={
        'Ημέρες': 'ΣΥΝΟΛΟ',
        'Μικτές_Part': 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ',
        'Εισφορές_Part': 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'
    }, inplace=True)

    pivot_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Ημέρες'].sum().reset_index()
    agg_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Is_Aggregate'].max().reset_index()
    contrib_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Εισφορές_Part'].sum().reset_index()

    final_val = pivot_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Ημέρες').fillna(0)
    final_agg = agg_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Is_Aggregate').fillna(False)
    final_contrib = contrib_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Εισφορές_Part').fillna(0)

    final_val = final_val.reset_index()
    final_val = final_val.merge(annual_totals, on=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], how='left')
    final_val.set_index(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], inplace=True)
    final_contrib = final_contrib.reindex(final_val.index)

    for m in range(1, 13):
        if m not in final_val.columns:
            final_val[m] = 0
        if m not in final_agg.columns:
            final_agg[m] = False
        if m not in final_contrib.columns:
            final_contrib[m] = 0

    month_cols_int = sorted([c for c in final_val.columns if isinstance(c, int)])
    final_val = final_val[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ']]

    if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in final_val.columns and 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in final_val.columns:
        final_val['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = pd.NA
        gross_series = final_val['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
        valid_mask = gross_series.notna() & (gross_series != 0)
        ratios = (
            final_val.loc[valid_mask, 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] /
            final_val.loc[valid_mask, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
        ) * 100
        final_val.loc[valid_mask, 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ratios
        final_val = final_val[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']]

    month_map = {m: f"{m}ος" for m in range(1, 13)}
    final_val = final_val.rename(columns=month_map)
    final_agg = final_agg.rename(columns=month_map)
    final_contrib = final_contrib.rename(columns=month_map)
    month_cols = list(month_map.values())

    final_val = final_val.sort_values('ΕΤΟΣ', ascending=True)
    final_agg = final_agg.reindex(final_val.index)
    final_contrib = final_contrib.reindex(final_val.index)

    display_cnt_df = final_val.reset_index()
    mask_cnt_df = final_agg.reset_index()
    contrib_cnt_df = final_contrib.reset_index()

    if not display_cnt_df.empty:
        try:
            min_year = int(display_cnt_df['ΕΤΟΣ'].min())
            max_year = int(display_cnt_df['ΕΤΟΣ'].max())
            existing_years = set(display_cnt_df['ΕΤΟΣ'].dropna().astype(int).tolist())
            missing_years = [y for y in range(min_year, max_year + 1) if y not in existing_years]
        except Exception:
            missing_years = []
        if missing_years:
            filler_rows = []
            filler_masks = []
            block_rows_list = []
            for missing_year in missing_years:
                row_template = {col: '' for col in display_cnt_df.columns}
                row_template['ΕΤΟΣ'] = missing_year
                row_template['ΤΑΜΕΙΟ'] = "ΚΕΝΟ ΔΙΑΣΤΗΜΑ"
                for c in month_cols:
                    if c in row_template:
                        row_template[c] = 0
                if 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ' in row_template:
                    row_template['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = ''
                for c in ['ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']:
                    if c in row_template:
                        row_template[c] = 0
                filler_rows.append(row_template)

                mask_template = {}
                for col in mask_cnt_df.columns:
                    if col == 'ΕΤΟΣ':
                        mask_template[col] = missing_year
                    elif col == 'ΤΑΜΕΙΟ':
                        mask_template[col] = "ΚΕΝΟ ΔΙΑΣΤΗΜΑ"
                    elif col == 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ':
                        mask_template[col] = ''
                    elif col in ['ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']:
                        mask_template[col] = ''
                    else:
                        mask_template[col] = False
                filler_masks.append(mask_template)

                contrib_template = {}
                for col in contrib_cnt_df.columns:
                    if col == 'ΕΤΟΣ':
                        contrib_template[col] = missing_year
                    elif col == 'ΤΑΜΕΙΟ':
                        contrib_template[col] = "ΚΕΝΟ ΔΙΑΣΤΗΜΑ"
                    elif col == 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ':
                        contrib_template[col] = ''
                    elif col in ['ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']:
                        contrib_template[col] = ''
                    else:
                        contrib_template[col] = 0
                block_rows_list.append(contrib_template)

            display_cnt_df = pd.concat([display_cnt_df, pd.DataFrame(filler_rows)], ignore_index=True)
            mask_cnt_df = pd.concat([mask_cnt_df, pd.DataFrame(filler_masks)], ignore_index=True)
            contrib_cnt_df = pd.concat([contrib_cnt_df, pd.DataFrame(block_rows_list)], ignore_index=True)

        sort_keys = ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']
        display_cnt_df = display_cnt_df.sort_values(sort_keys, na_position='first').reset_index(drop=True)
        mask_cnt_df = mask_cnt_df.sort_values(sort_keys, na_position='first').reset_index(drop=True)
        contrib_cnt_df = contrib_cnt_df.sort_values(sort_keys, na_position='first').reset_index(drop=True)

    year_totals = {}
    if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in display_cnt_df.columns or 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in display_cnt_df.columns:
        sum_cols = [col for col in ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] if col in display_cnt_df.columns]
        if sum_cols:
            year_totals = (
                display_cnt_df.groupby('ΕΤΟΣ')[sum_cols]
                .sum()
                .to_dict('index')
            )

    def format_cell_days(val):
        if val == 0:
            return ""
        if abs(val - round(val)) < 0.01:
            return str(int(round(val)))
        return format_number_greek(val, decimals=1)

    def format_amount_cell(val):
        if val == 0 or pd.isna(val):
            return ""
        return format_currency(val)

    def format_pct_cell(val):
        if pd.isna(val) or val == 0:
            return ""
        return f"{format_number_greek(val, decimals=2)} %"

    processed_rows = []
    processed_mask_rows = []
    last_month_col = month_cols[-1] if month_cols else None

    prev_year = None
    prev_tameio = None
    prev_insurance_type = None
    prev_employer = None

    def make_mask_row(is_total=False):
        base = {m: False for m in month_cols}
        base['__is_total__'] = is_total
        return base

    contrib_lookup = {}
    for _, row in contrib_cnt_df.iterrows():
        k = (
            row.get('ΕΤΟΣ'), row.get('ΤΑΜΕΙΟ'), row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'),
            row.get('ΕΡΓΟΔΟΤΗΣ'), row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ'), row.get('ΠΕΡΙΓΡΑΦΗ'), row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ')
        )
        contrib_lookup[k] = row.to_dict()

    def _matches_target(code_val):
        code_upper = str(code_val).upper()
        tokens = re.split(r'[^A-ZΑ-Ω0-9]+', code_upper)
        target_set = {'ΚΣ', 'Κ', 'ΜΕ', 'ΠΚΣ', 'ΕΙΠΡ', 'ΕΦΑΠ', 'ΕΠΙΚ', 'Ε'}
        return any(tok in target_set for tok in tokens if tok)

    for _, row in display_cnt_df.iterrows():
        try:
            curr_year = row.get('ΕΤΟΣ')
            curr_tameio = row.get('ΤΑΜΕΙΟ')
            curr_insurance_type = row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ')
            curr_employer = row.get('ΕΡΓΟΔΟΤΗΣ')

            if prev_year is not None and curr_year != prev_year:
                total_row = {c: '' for c in display_cnt_df.columns}
                total_row['ΕΤΟΣ'] = ''
                if last_month_col:
                    total_row[last_month_col] = f"ΣΥΝΟΛΟ {prev_year}"
                totals_vals = year_totals.get(prev_year, {})
                if totals_vals:
                    gross_total = totals_vals.get('ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 0)
                    contrib_total = totals_vals.get('ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 0)
                    if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in total_row:
                        total_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = format_amount_cell(gross_total)
                    if 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in total_row:
                        total_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = format_amount_cell(contrib_total)
                    if 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ' in total_row:
                        total_row['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ''
                processed_rows.append(total_row)
                processed_mask_rows.append(make_mask_row(is_total=True))

                processed_rows.append({c: '' for c in display_cnt_df.columns})
                processed_mask_rows.append(make_mask_row())

            curr_row = row.to_dict()

            for m_col in month_cols:
                curr_row[m_col] = format_cell_days(curr_row.get(m_col, 0))
            curr_row['ΣΥΝΟΛΟ'] = format_cell_days(curr_row.get('ΣΥΝΟΛΟ', 0))
            if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in curr_row:
                curr_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = format_amount_cell(curr_row.get('ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 0))
            if 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in curr_row:
                curr_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = format_amount_cell(curr_row.get('ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 0))
            if 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ' in curr_row:
                curr_row['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = format_pct_cell(curr_row.get('ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'))

            if curr_year == prev_year:
                curr_row['ΕΤΟΣ'] = ''
                if curr_tameio == prev_tameio:
                    curr_row['ΤΑΜΕΙΟ'] = ''
                    if curr_insurance_type == prev_insurance_type:
                        curr_row['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = ''
                        if curr_employer == prev_employer:
                            curr_row['ΕΡΓΟΔΟΤΗΣ'] = ''

            processed_rows.append(curr_row)

            mask_row = {m: False for m in month_cols}
            for m_col in month_cols:
                if mask_cnt_df.get(m_col) is not None:
                    try:
                        if bool(mask_cnt_df.loc[row.name, m_col]):
                            mask_row[m_col] = True
                    except Exception:
                        pass
            mask_row['__is_total__'] = False
            processed_mask_rows.append(mask_row)

            curr_key = (
                row.get('ΕΤΟΣ'), row.get('ΤΑΜΕΙΟ'), row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'),
                row.get('ΕΡΓΟΔΟΤΗΣ'), row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ'), row.get('ΠΕΡΙΓΡΑΦΗ'), row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ')
            )
            if _matches_target(curr_row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')):
                c_row = contrib_lookup.get(curr_key, {})
                has_amount = False
                contrib_display = {col: '' for col in display_cnt_df.columns}
                for m_col in month_cols:
                    if m_col in c_row and c_row[m_col]:
                        contrib_display[m_col] = format_currency(c_row[m_col])
                        has_amount = True
                if has_amount:
                    contrib_display.update({
                        'ΕΤΟΣ': '',
                        'ΤΑΜΕΙΟ': '',
                        'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': '',
                        'ΕΡΓΟΔΟΤΗΣ': curr_row.get('ΕΡΓΟΔΟΤΗΣ', ''),
                        'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': curr_row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', ''),
                        'ΠΕΡΙΓΡΑΦΗ': 'Εισφορές μήνα',
                        'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': curr_row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', ''),
                        'ΣΥΝΟΛΟ': '',
                        'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ': '',
                        'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ': '',
                        'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ': ''
                    })
                    processed_rows.append(contrib_display)
                    empty_mask = {m: False for m in month_cols}
                    empty_mask['__is_total__'] = False
                    processed_mask_rows.append(empty_mask)

            prev_year = curr_year
            prev_tameio = curr_tameio
            prev_insurance_type = curr_insurance_type
            prev_employer = curr_employer
        except Exception:
            pass

    if prev_year is not None:
        total_row = {c: '' for c in display_cnt_df.columns}
        total_row['ΕΤΟΣ'] = ''
        if last_month_col:
            total_row[last_month_col] = f"ΣΥΝΟΛΟ {prev_year}"
        totals_vals = year_totals.get(prev_year, {})
        if totals_vals:
            gross_total = totals_vals.get('ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 0)
            contrib_total = totals_vals.get('ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 0)
            if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in total_row:
                total_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = format_amount_cell(gross_total)
            if 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in total_row:
                total_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = format_amount_cell(contrib_total)
            if 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ' in total_row:
                total_row['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ''
        processed_rows.append(total_row)
        processed_mask_rows.append(make_mask_row(is_total=True))

        processed_rows.append({c: '' for c in display_cnt_df.columns})
        processed_mask_rows.append(make_mask_row())

    final_display_df = pd.DataFrame(processed_rows, columns=display_cnt_df.columns)
    masks_df = pd.DataFrame(processed_mask_rows)
    if not masks_df.empty:
        masks_df = masks_df.reset_index(drop=True)
    else:
        masks_df = pd.DataFrame({'__is_total__': []})

    if show_count_totals_only:
        try:
            total_mask = masks_df['__is_total__'].fillna(False)
            final_display_df = final_display_df[total_mask].reset_index(drop=True)
            masks_df = masks_df[total_mask].reset_index(drop=True)
        except Exception:
            pass
    else:
        final_display_df = final_display_df.reset_index(drop=True)
        masks_df = masks_df.reset_index(drop=True)

    active_mask_rows = masks_df.to_dict('records') if not masks_df.empty else []

    total_highlight_cols = [col for col in [last_month_col, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] if col]
    print_style_rows = []
    for ridx, _ in final_display_df.iterrows():
        mask_row = active_mask_rows[ridx] if ridx < len(active_mask_rows) else {}
        is_total = mask_row.get('__is_total__', False)
        row_styles = {}
        for col in final_display_df.columns:
            style = ''
            if col in ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']:
                style += 'font-weight:700;'
            if is_total and col in total_highlight_cols:
                style += 'background-color:#cfe2f3;color:#000;'
            elif col in month_cols and mask_row.get(col, False):
                style += 'background-color:#fff9c4;color:#000;'
            if col == 'ΠΕΡΙΓΡΑΦΗ':
                style += 'white-space:nowrap;'
            row_styles[col] = style
        print_style_rows.append(row_styles)

    return final_display_df, active_mask_rows, last_month_col, month_cols, print_style_rows

def show_results_page(df, filename):
    """
    Εμφανίζει τη σελίδα αποτελεσμάτων
    """

    # Συλλογή προβολών για εξαγωγή μεμονωμένων πινάκων
    view_exports = {}

    def register_view(label: str, data: pd.DataFrame):
        """Αποθηκεύει το τρέχον DataFrame για χρήση στο κουμπί 'Εξαγωγή πίνακα'."""
        if data is None:
            return
        if isinstance(data, pd.DataFrame):
            try:
                view_exports[label] = data.copy()
            except Exception:
                # Σε σπάνιες περιπτώσεις (π.χ. styler με pandas>=2) fallback χωρίς copy
                view_exports[label] = pd.DataFrame(data)

    # --- Step 1: Determine insurance type (Παλιός/Νέος) ---
    # This check is done once on the original unfiltered dataframe
    is_palios = False
    if 'Από' in df.columns:
        try:
            from_dates = pd.to_datetime(df['Από'], format='%d/%m/%Y', errors='coerce')
            cutoff_date = pd.Timestamp('1993-01-01')
            if not from_dates.isnull().all() and from_dates.min() < cutoff_date:
                is_palios = True
        except Exception:
            pass # Default to False if any error occurs

    plafond_map = PLAFOND_PALIOS if is_palios else PLAFOND_NEOS
    insurance_status_message = "Παλιός Ασφαλισμένος (εγγραφή πριν από 1/1/1993)" if is_palios else "Νέος Ασφαλισμένος (χωρίς εγγραφή πριν από 1/1/1993)"
    
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
    
    # Professional Header (Compact)
    st.markdown("""
    <div class="professional-header">
        <div class="header-content">
            <div class="header-left">
                <div class="header-text">
                    <h1>Ασφαλιστικό βιογραφικό ΑΤΛΑΣ</h1>
                </div>
            </div>
            <div class="header-right">
                <a href="." target="_self" class="nav-link">Αρχική</a>
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
    /* Απόκρυψη badges/κουμπιών Streamlit Cloud (Manage app) */
    div[class*="viewerBadge"],
    a[class*="viewerBadge"],
    button[class*="viewerBadge"],
    div[data-testid="stToolbarActionButton"] {
        display: none !important;
        visibility: hidden !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Μετάφραση ενδείξεων του file uploader στα Ελληνικά
    components.html(
        """
        <script>
          const translateUploader = () => {
            const root = document.querySelector('div[data-testid="stFileUploader"]');
            if (root) {
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
            const btns = root.querySelectorAll('button, span, label');
            btns.forEach((b) => {
              if (b.textContent && b.textContent.trim() === 'Browse file') {
                b.textContent = 'Επιλογή αρχείου';
              }
            });
            }
          };

          const hideManageButton = () => {
            const selectors = [
              'button[title*="Manage"]',
              'button[aria-label*="Manage"]',
              'a[title*="Manage"]',
              'a[aria-label*="Manage"]',
              'div[class*="viewerBadge"]',
              'button[class*="viewerBadge"]',
              'a[class*="viewerBadge"]'
            ];
            selectors.forEach((selector) => {
              document.querySelectorAll(selector).forEach((el) => {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                if (el.parentElement) {
                  el.parentElement.style.display = 'none';
                }
              });
            });
            const textCandidates = document.querySelectorAll('button, a, div');
            textCandidates.forEach((el) => {
              if (el.textContent && el.textContent.trim().includes('Manage app')) {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                if (el.parentElement) {
                  el.parentElement.style.display = 'none';
                }
              }
            });
          };

          const applyUiTweaks = () => {
            translateUploader();
            hideManageButton();
          };

          const obs = new MutationObserver(() => applyUiTweaks());
          obs.observe(document.body, { childList: true, subtree: true });
          window.addEventListener('load', applyUiTweaks);
          setTimeout(applyUiTweaks, 800);
        </script>
        """,
        height=0
    )
    
    # Προ-υπολογισμός ειδοποιήσεων για Tabs
    tab_titles = {
        "summary": "Σύνοψη",
        "count": "Καταμέτρηση",
        "gaps": "Κενά",
        "apd": "Ανάλυση ΑΠΔ",
        "parallel": "Παράλληλη",
        "multi": "Πολλαπλή",
        "yearly": "Ετήσια Αναφορά",
        "days": "Ημέρες Ασφάλισης",
        "main": "Κύρια Δεδομένα",
        "annex": "Παράρτημα"
    }

    if not df.empty and 'Από' in df.columns:
        # 1. Κενά
        try:
            gaps_found = find_gaps_in_insurance_data(df)
            if not gaps_found.empty:
                tab_titles["gaps"] = "❗ Κενά"
        except: pass

        # 2. Πολλαπλή (ίδιος έλεγχος με τη Σύνοψη: ΙΚΑ 01/16/99 & >1 εργοδότες ανά μήνα)
        try:
            if all(col in df.columns for col in ['Από', 'Έως', 'Α-Μ εργοδότη']):
                t_df = df.copy()
                t_df['Start'] = pd.to_datetime(t_df['Από'], format='%d/%m/%Y', errors='coerce')
                t_df['End'] = pd.to_datetime(t_df['Έως'], format='%d/%m/%Y', errors='coerce')
                t_df = t_df.dropna(subset=['Start', 'End'])

                def is_ika_multi_title(row):
                    et = str(row.get('Τύπος Αποδοχών', '')).strip()
                    t = str(row.get('Ταμείο', '')).upper()
                    return ('IKA' in t or 'ΙΚΑ' in t) and et in ['01', '1', '16', '99']

                t_df = t_df[t_df.apply(is_ika_multi_title, axis=1)]
                t_df['Emp'] = t_df['Α-Μ εργοδότη'].astype(str).str.strip().replace(['nan', 'None', '', 'NaN'], pd.NA)
                t_df = t_df.dropna(subset=['Emp'])

                seen_months = {}
                found_multi = False
                for _, row in t_df.iterrows():
                    s = row['Start']
                    e = row['End']
                    emp = row['Emp']
                    curr = s.replace(day=1)
                    end_m = e.replace(day=1)
                    while curr <= end_m:
                        k = (curr.year, curr.month)
                        if k not in seen_months:
                            seen_months[k] = set()
                        seen_months[k].add(emp)
                        if len(seen_months[k]) > 1:
                            found_multi = True
                            break
                        if curr.month == 12:
                            curr = curr.replace(year=curr.year + 1, month=1)
                        else:
                            curr = curr.replace(month=curr.month + 1)
                    if found_multi:
                        break

                if found_multi:
                    tab_titles["multi"] = "❗ Πολλαπλή"
        except:
            pass

        # 3. Παράλληλη (ίδια λογική με την καρτέλα: μήνες με ημέρες και στα δύο ταμεία)
        try:
            valid_months = compute_parallel_months(df)
            if valid_months:
                tab_titles["parallel"] = "❗ Παράλληλη"
        except: pass

    # Δημιουργία tabs
    tab_summary, tab_count, tab_gaps, tab_apd, tab_parallel, tab_multi, tab_yearly, tab_days, tab_main, tab_annex = st.tabs(list(tab_titles.values()))
    
    with tab_main:
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
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1.1, 1.1, 1.4, 1.1, 1.0, 1.0, 1.2])

                with col1:
                    # Φίλτρο Ταμείου
                    if 'Ταμείο' in main_df.columns:
                        taimeia_options = sorted(main_df['Ταμείο'].dropna().unique().tolist())
                        selected_taimeia = st.multiselect(
                            "Ταμείο:",
                            options=taimeia_options,
                            default=[],
                            key="filter_taimeio"
                        )
                        if selected_taimeia:
                            main_df = main_df[main_df['Ταμείο'].isin(selected_taimeia)]

                with col2:
                    # Φίλτρο Τύπου Ασφάλισης
                    if 'Τύπος Ασφάλισης' in main_df.columns:
                        typos_options = sorted(main_df['Τύπος Ασφάλισης'].dropna().unique().tolist())
                        selected_typos = st.multiselect(
                            "Τύπος Ασφάλισης:",
                            options=typos_options,
                            default=[],
                            key="filter_typos"
                        )
                        if selected_typos:
                            main_df = main_df[main_df['Τύπος Ασφάλισης'].isin(selected_typos)]

                with col3:
                    # Φίλτρο Κλάδου/Πακέτου με περιγραφές
                    if 'Κλάδος/Πακέτο Κάλυψης' in main_df.columns:
                        # Δημιουργούμε options με περιγραφές
                        klados_codes = sorted(main_df['Κλάδος/Πακέτο Κάλυψης'].dropna().unique().tolist())
                        klados_options_with_desc = []
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
                            default=[],
                            key="filter_klados"
                        )
                        
                        if selected_klados:
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
                        typos_apodochon_options = sorted(options_raw)
                        selected_typos_apodochon = st.multiselect(
                            "Τύπος Αποδοχών:",
                            options=typos_apodochon_options,
                            default=[],
                            key="filter_apodochon"
                        )
                        if selected_typos_apodochon:
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
                    # Φίλτρο Α-Μ Εργοδότη
                    if 'Α-Μ εργοδότη' in main_df.columns:
                        ame_options = ['Όλα'] + sorted(main_df['Α-Μ εργοδότη'].dropna().astype(str).unique().tolist())
                        selected_ame = st.multiselect(
                            "Α-Μ Εργοδότη:",
                            options=ame_options,
                            default=['Όλα'],
                            key="filter_ame"
                        )
                        if 'Όλα' not in selected_ame:
                            main_df = main_df[main_df['Α-Μ εργοδότη'].astype(str).isin(selected_ame)]
                
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
            use_container_width=True
        )
        register_view("Κύρια Δεδομένα", display_df)
        # Κουμπί εκτύπωσης για Κύρια Δεδομένα
        render_print_button(
            "print_main",
            "Κύρια Δεδομένα e-EFKA",
            display_df,
            description="Αναλυτική χρονολογική κατάσταση ασφαλιστικών εγγραφών όπως εξήχθησαν από τον e-ΕΦΚΑ και το ασφ. βιογραφικό ΑΤΛΑΣ."
        )
    
    with tab_annex:
        # Επιπλέον πίνακες (στήλες από τελευταίες σελίδες)
        extra_columns = [col for col in df.columns if col in ['Φορέας', 'Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']]
        
        if extra_columns:
            extra_df = df[extra_columns].copy()
            
            # Φιλτράρουμε κενές γραμμές (όπου όλες οι στήλες είναι κενές ή "None")
            extra_df = extra_df.dropna(how='all')  # Αφαιρούμε γραμμές που είναι όλες κενές
            extra_df = extra_df[~((extra_df == 'None') | (extra_df == '') | (extra_df.isna())).all(axis=1)]  # Αφαιρούμε γραμμές με "None" ή κενά
            
            if not extra_df.empty:
                st.markdown("### Παράρτημα (Τελευταίες Σελίδες)")
                st.dataframe(
                    extra_df,
                    use_container_width=True
                )
                register_view("Παράρτημα", extra_df)
                render_print_button(
                    "print_extra",
                    "Παράρτημα",
                    extra_df,
                    description="Επεξηγηματικοί πίνακες καλύψεων και αποδοχών."
                )
            else:
                st.info("Δεν βρέθηκαν δεδομένα στα επιπλέον πίνακες.")
        else:
            st.info("Δεν βρέθηκαν επιπλέον πίνακες από τις τελευταίες σελίδες.")
    
    with tab_summary:
        
        # --- Audit Report Integration ---
        if not df.empty and 'Από' in df.columns:
            def generate_audit_report(data_df, extra_data_df=None):
                audit_rows = []
                
                # Check 1: Old/New Insured
                try:
                    dates = pd.to_datetime(data_df['Από'], format='%d/%m/%Y', errors='coerce')
                    min_date = dates.min()
                    if pd.notna(min_date):
                        cutoff = pd.Timestamp('1993-01-01')
                        is_palios = min_date < cutoff
                        status_str = "Παλιός" if is_palios else "Νέος"
                        details = f"Πρώτη εγγραφή: {min_date.strftime('%d/%m/%Y')}"
                        audit_rows.append({
                            'A/A': 1, 'Έλεγχος': 'Παλιός ή νέος ασφαλισμένος', 
                            'Εύρημα': status_str, 'Λεπτομέρειες': details, 'Ενέργειες': '-'
                        })
                except Exception: pass

                # Check 2: Insurance Funds History (ανά Ταμείο & Τύπο Ασφάλισης: πρώτη/τελευταία ημερομηνία)
                try:
                    if 'Ταμείο' in data_df.columns:
                        temp_df = data_df.copy()
                        temp_df['Start'] = pd.to_datetime(temp_df['Από'], format='%d/%m/%Y', errors='coerce')
                        temp_df['End'] = pd.to_datetime(temp_df['Έως'], format='%d/%m/%Y', errors='coerce')
                        temp_df['End'] = temp_df['End'].fillna(temp_df['Start'])
                        temp_df = temp_df.dropna(subset=['Start'])
                        
                        # Ομαδοποίηση ανά Ταμείο και Τύπο Ασφάλισης (αν υπάρχει)
                        group_cols = ['Ταμείο']
                        if 'Τύπος Ασφάλισης' in temp_df.columns:
                            group_cols.append('Τύπος Ασφάλισης')
                        
                        grouped = temp_df.groupby(group_cols).agg({
                            'Start': 'min',
                            'End': 'max'
                        }).reset_index()
                        grouped = grouped.sort_values('Start')
                        
                        rows_html = []
                        for _, row2 in grouped.iterrows():
                            fund = str(row2['Ταμείο']).strip()
                            typ = str(row2['Τύπος Ασφάλισης']).strip() if 'Τύπος Ασφάλισης' in grouped.columns else ""
                            label = fund if typ in [None, '', 'nan'] else f"{fund} - {typ}"
                            s_date = row2['Start'].strftime('%d/%m/%Y')
                            e_date = row2['End'].strftime('%d/%m/%Y')
                            rows_html.append(
                                f"<div style='font-weight: 600; color: #2c3e50;'>{label}</div>"
                                f"<div style='color: #555;'>{s_date} - {e_date}</div>"
                            )
                        history_html = (
                            "<div style='display: grid; grid-template-columns: 1fr auto; column-gap: 12px; row-gap: 4px;'>"
                            + "".join(rows_html) +
                            "</div>"
                        )
                        
                        count_funds = temp_df['Ταμείο'].dropna().nunique()
                        audit_rows.append({
                            'A/A': 2, 'Έλεγχος': 'Ασφαλιστικά ταμεία', 
                            'Εύρημα': f"{count_funds} Ταμεία", 
                            'Λεπτομέρειες': history_html, 'Ενέργειες': '-'
                        })
                except Exception: pass

                # Check 3: Gaps
                try:
                    gaps = find_gaps_in_insurance_data(data_df)
                    if not gaps.empty:
                        # Format first few gaps
                        gap_details = []
                        for _, g in gaps.head(3).iterrows():
                            # Fix column name access
                            duration = g.get('Ημερολογιακές ημέρες', '')
                            gap_details.append(f"Από {g['Από']} έως {g['Έως']} ({duration} ημέρες)")
                        if len(gaps) > 3:
                            gap_details.append("...")
                        
                        audit_rows.append({
                            'A/A': 3, 'Έλεγχος': 'Κενά ασφάλισης', 
                            'Εύρημα': f"{len(gaps)} Διάστημα(τα)", 
                            'Λεπτομέρειες': "<br>".join(gap_details),
                            'Ενέργειες': 'Ελέγξτε την καρτέλα "Κενά Διαστήματα"'
                        })
                    else:
                        audit_rows.append({
                            'A/A': 3, 'Έλεγχος': 'Κενά ασφάλισης', 
                            'Εύρημα': 'Κανένα', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'
                        })
                except Exception as e:
                     audit_rows.append({
                        'A/A': 3, 'Έλεγχος': 'Κενά ασφάλισης', 
                        'Εύρημα': 'Σφάλμα ελέγχου', 'Λεπτομέρειες': str(e), 'Ενέργειες': '-'
                    })

                # Check 4: Unpaid OAEE
                try:
                    if 'Κλάδος/Πακέτο Κάλυψης' in data_df.columns and 'Συνολικές εισφορές' in data_df.columns:
                        def clean_money_chk(x):
                            if isinstance(x, str):
                                if 'DRX' in x or 'ΔΡΧ' in x: return 0.0
                                return clean_numeric_value(x, exclude_drx=True)
                            return x
                        
                        t_df = data_df.copy()
                        t_df['C'] = t_df['Συνολικές εισφορές'].apply(clean_money_chk)
                        t_df['K'] = t_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip().str.upper()
                        unpaid = t_df[(t_df['K'].isin(['K', 'Κ'])) & (t_df['C'] == 0)]
                        
                        if not unpaid.empty:
                            months = []
                            for _, r in unpaid.iterrows():
                                try:
                                    d = pd.to_datetime(r['Από'], format='%d/%m/%Y', errors='coerce')
                                    if pd.notna(d):
                                        months.append(d.strftime('%m/%Y'))
                                except: pass
                            
                            months_str = ", ".join(months) if months else ""
                            details_msg = f"{len(unpaid)} μήνες ΟΑΕΕ (Κ) με μηδενική εισφορά."
                            if months_str:
                                details_msg += f"<br><span style='font-size: 0.85rem; color: #666;'>({months_str})</span>"

                            audit_rows.append({
                                'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές', 
                                'Εύρημα': 'Εντοπίστηκαν', 
                                'Λεπτομέρειες': details_msg,
                                'Ενέργειες': 'Ελέγξτε για τυχόν οφειλές στον ΟΑΕΕ'
                            })
                        else:
                            audit_rows.append({'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές', 'Εύρημα': 'Καμία', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                except Exception: pass

                # Check 5: Parallel Insurance (Month-based Logic)
                try:
                    valid_months = compute_parallel_months(data_df)
                    p_found = bool(valid_months)
                    
                    if p_found:
                         audit_rows.append({
                            'A/A': 5, 'Έλεγχος': 'Παράλληλη ασφάλιση', 
                            'Εύρημα': 'Πιθανή', 
                            'Λεπτομέρειες': 'Βρέθηκαν χρονικά επικαλυπτόμενα διαστήματα ΙΚΑ (01/16/99) & ΟΑΕΕ (Κ), ΟΑΕΕ (Κ) & ΤΣΜΕΔΕ (ΚΣ/ΠΚΣ) ή ΟΓΑ (Κ) & ΙΚΑ/ΟΑΕΕ.',
                            'Ενέργειες': 'Ελέγξτε την καρτέλα "Παράλληλη Ασφάλιση"'
                        })
                    else:
                        audit_rows.append({'A/A': 5, 'Έλεγχος': 'Παράλληλη ασφάλιση', 'Εύρημα': 'Όχι', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                except Exception: pass

                # Check 6: Multiple Employers (Month-based Logic)
                try:
                    m_found = False
                    
                    if 'Α-Μ εργοδότη' in data_df.columns:
                        m_df = data_df.copy()
                        m_df['Start'] = pd.to_datetime(m_df['Από'], format='%d/%m/%Y', errors='coerce')
                        m_df['End'] = pd.to_datetime(m_df['Έως'], format='%d/%m/%Y', errors='coerce')
                        m_df = m_df.dropna(subset=['Start', 'End'])
                        
                        def is_ika_multi(row):
                            et = str(row.get('Τύπος Αποδοχών', '')).strip()
                            t = str(row.get('Ταμείο', '')).upper()
                            return ('IKA' in t or 'ΙΚΑ' in t) and et in ['01', '1', '16', '99']
                        
                        m_df['is_ika'] = m_df.apply(is_ika_multi, axis=1)
                        m_df = m_df[m_df['is_ika']]
                        
                        m_df['Emp'] = m_df['Α-Μ εργοδότη'].astype(str).str.strip().replace(['nan', 'None', '', 'NaN'], pd.NA)
                        m_df = m_df.dropna(subset=['Emp'])
                        
                        if m_df['Emp'].nunique() > 1:
                            m_df = m_df.sort_values('Start')
                            seen_months = {}
                            
                            for _, row in m_df.iterrows():
                                s = row['Start']
                                e = row['End']
                                emp = row['Emp']
                                curr = s.replace(day=1)
                                end_m = e.replace(day=1)
                                while curr <= end_m:
                                    k = (curr.year, curr.month)
                                    if k not in seen_months: seen_months[k] = set()
                                    seen_months[k].add(emp)
                                    if len(seen_months[k]) > 1:
                                        m_found = True
                                        break
                                    if curr.month == 12: curr = curr.replace(year=curr.year+1, month=1)
                                    else: curr = curr.replace(month=curr.month+1)
                                if m_found: break

                    if m_found:
                        audit_rows.append({
                            'A/A': 6, 'Έλεγχος': 'Πολλαπλή απασχόληση', 
                            'Εύρημα': 'Πιθανή', 
                            'Λεπτομέρειες': f"Βρέθηκαν μήνες με > 1 εργοδότες για ΙΚΑ (01/16/99).",
                            'Ενέργειες': 'Ελέγξτε την καρτέλα "Πολλαπλή"'
                        })
                    else:
                        audit_rows.append({'A/A': 6, 'Έλεγχος': 'Πολλαπλή απασχόληση', 'Εύρημα': '-', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                except Exception: pass

                # Check 7: Low APD
                try:
                    if 'Μικτές αποδοχές' in data_df.columns and 'Συνολικές εισφορές' in data_df.columns:
                        def get_val_chk(x):
                            if isinstance(x, str):
                                if 'DRX' in x or 'ΔΡΧ' in x: return 0.0
                                return clean_numeric_value(x, exclude_drx=True) or 0.0
                            return x if pd.notna(x) else 0.0
                        t_df = data_df.copy()
                        t_df['G'] = t_df['Μικτές αποδοχές'].apply(get_val_chk)
                        t_df['C'] = t_df['Συνολικές εισφορές'].apply(get_val_chk)
                        t_df = t_df[t_df['G'] > 0]
                        if not t_df.empty:
                            t_df['Ratio'] = t_df['C'] / t_df['G']
                            # Check < 0.30 (30%)
                            cnt = len(t_df[t_df['Ratio'] < 0.30])
                            if cnt > 0:
                                audit_rows.append({
                                    'A/A': 7, 'Έλεγχος': 'ΑΠΔ με χαμηλές κρατήσεις', 
                                    'Εύρημα': 'Εντοπίστηκαν', 
                                    'Λεπτομέρειες': f"{cnt} εγγραφές με εισφορές < 30% των αποδοχών.",
                                    'Ενέργειες': 'Ελέγξτε για πιθανά σφάλματα ή ειδικές περιπτώσεις'
                                })
                            else:
                                audit_rows.append({'A/A': 7, 'Έλεγχος': 'ΑΠΔ με χαμηλές κρατήσεις', 'Εύρημα': 'Καμία', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                        else:
                            audit_rows.append({'A/A': 7, 'Έλεγχος': 'ΑΠΔ με χαμηλές κρατήσεις', 'Εύρημα': '-', 'Λεπτομέρειες': 'Δεν βρέθηκαν αποδοχές', 'Ενέργειες': '-'})
                except Exception: pass

                # Check 8: Plafond
                try:
                    if 'Από' in data_df.columns and 'Μικτές αποδοχές' in data_df.columns and 'Μήνες' in data_df.columns:
                        t_df = data_df.copy()
                        t_df['Dt'] = pd.to_datetime(t_df['Από'], format='%d/%m/%Y', errors='coerce')
                        t_df['Y'] = t_df['Dt'].dt.year
                        
                        def get_val_chk(x):
                            if isinstance(x, str):
                                if 'DRX' in x or 'ΔΡΧ' in x: return 0.0
                                return clean_numeric_value(x, exclude_drx=True) or 0.0
                            return x if pd.notna(x) else 0.0
                        
                        t_df['G'] = t_df['Μικτές αποδοχές'].apply(get_val_chk)
                        t_df['M'] = t_df['Μήνες'].apply(lambda x: clean_numeric_value(x) or 1)
                        
                        min_dt = t_df['Dt'].min()
                        is_p = False
                        if pd.notna(min_dt) and min_dt < pd.Timestamp('1993-01-01'): is_p = True
                        curr_pl = PLAFOND_PALIOS if is_p else PLAFOND_NEOS
                        
                        exc = 0
                        for _, r in t_df.iterrows():
                            ys = str(int(r['Y'])) if pd.notna(r['Y']) else ""
                            if ys in curr_pl:
                                m_g = r['G'] / r['M'] if r['M'] > 0 else 0
                                if m_g > curr_pl[ys]: exc += 1
                        
                        if exc > 0:
                            audit_rows.append({
                                'A/A': 8, 'Έλεγχος': 'Ανώτατο εισφορίσιμο πλαφόν', 
                                'Εύρημα': 'Υπέρβαση', 
                                'Λεπτομέρειες': f"{exc} εγγραφές ξεπερνούν το μηνιαίο πλαφόν.",
                                'Ενέργειες': 'Ελέγξτε τα ποσά'
                            })
                        else:
                            audit_rows.append({'A/A': 8, 'Έλεγχος': 'Ανώτατο εισφορίσιμο πλαφόν', 'Εύρημα': 'Εντός ορίων', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                except Exception: pass

                # Check 9: Aggregated Intervals (Enhanced with fund/date rules)
                try:
                    if 'Από' in data_df.columns and 'Έως' in data_df.columns:
                        t_df = data_df.copy()
                        t_df['D_From'] = pd.to_datetime(t_df['Από'], format='%d/%m/%Y', errors='coerce')
                        t_df['D_To'] = pd.to_datetime(t_df['Έως'], format='%d/%m/%Y', errors='coerce')
                        t_df['Duration'] = (t_df['D_To'] - t_df['D_From']).dt.days + 1

                        def get_num(val):
                            try:
                                return clean_numeric_value(val) or 0
                            except Exception:
                                return 0

                        def is_expected_oaee(r):
                            tam = str(r.get('Ταμείο', '')).upper()
                            if 'ΟΑΕΕ' not in tam:
                                return False
                            months_val = get_num(r.get('Μήνες'))
                            days_val = get_num(r.get('Ημέρες'))
                            # OAEE: μέχρι 2 μήνες με 25 ημέρες/μήνα θεωρούνται τυπικά
                            if months_val and months_val <= 2:
                                if days_val and abs(days_val - months_val * 25) <= 1:
                                    return True
                                # εναλλακτικά, μικρή διάρκεια ημερών
                                if not days_val and r.get('Duration', 0) <= 62:
                                    return True
                            return False

                        def is_expected_tsm(r):
                            tam = str(r.get('Ταμείο', '')).upper()
                            if 'ΤΣΜΕΔΕ' not in tam:
                                return False
                            months_val = get_num(r.get('Μήνες'))
                            days_val = get_num(r.get('Ημέρες'))
                            d_from, d_to = r.get('D_From'), r.get('D_To')
                            if pd.notna(d_from) and pd.notna(d_to) and d_from.year == d_to.year:
                                sem1 = (d_from.month == 1 and d_to.month == 6)
                                sem2 = (d_from.month == 7 and d_to.month == 12)
                                if sem1 or sem2:
                                    # 6 μήνες με ~25 ημέρες/μήνα είναι αναμενόμενοι
                                    if months_val == 6 and (not days_val or abs(days_val - 150) <= 2):
                                        return True
                                    if not months_val and 150 <= r.get('Duration', 0) <= 190:
                                        return True
                            return False

                        # Βασικό φίλτρο: διαστήματα > 1 μήνα πριν το 2002
                        agg_recs = t_df[
                            (t_df['Duration'] > 31) &
                            (t_df['D_To'] < pd.Timestamp('2002-01-01'))
                        ].copy()

                        if not agg_recs.empty:
                            # Αποκλεισμός αναμενόμενων μοτίβων για ΟΑΕΕ και ΤΣΜΕΔΕ
                            agg_recs = agg_recs[
                                ~agg_recs.apply(lambda r: is_expected_oaee(r) or is_expected_tsm(r), axis=1)
                            ]

                        if not agg_recs.empty:
                            count_total = len(agg_recs)
                            count_year = len(agg_recs[agg_recs['Duration'] > 366])
                            details_list = []
                            agg_recs = agg_recs.sort_values('D_From')
                            for _, r in agg_recs.iterrows():
                                tam = str(r.get('Ταμείο', '')).strip()
                                d_str = f"{r['Από']}-{r['Έως']}"
                                details_list.append(f"{tam} ({d_str})")
                            details_str = "<br>".join(details_list)
                            finding_msg = f"{count_total} > 1 μήνα"
                            if count_year > 0: finding_msg += f", {count_year} > 1 έτος"
                            
                            audit_rows.append({
                                'A/A': 9, 'Έλεγχος': 'Ενοποιημένα διαστήματα', 
                                'Εύρημα': finding_msg, 
                                'Λεπτομέρειες': details_str,
                                'Ενέργειες': '-'
                            })
                        else:
                            audit_rows.append({'A/A': 9, 'Έλεγχος': 'Ενοποιημένα διαστήματα', 'Εύρημα': 'Κανένα', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                except Exception: pass

                return pd.DataFrame(audit_rows)

            st.markdown("### Βασικοί έλεγχοι δεδομένων")
            audit_df = generate_audit_report(df, extra_df)
            
            # Custom 3-Column Layout
            ac1, ac2, ac3 = st.columns(3)
            
            # Helper to render a specific check by A/A
            def render_check(row):
                actions_html = ""
                if row['Ενέργειες'] != '-' and row['Ενέργειες']:
                    actions_html = f"""
                    <div style="margin-top: 4px; font-weight: bold; color: #d9534f; font-size: 0.9rem;">
                        Ενέργειες: <span style="font-weight: normal; color: #333;">{row['Ενέργειες']}</span>
                    </div>
                    """
                
                details_val = row['Λεπτομέρειες'] if row['Λεπτομέρειες'] != '-' else ""
                if details_val:
                    if row['A/A'] == 9:
                        details_html = f'<div style="margin-top: 4px; color: #555; font-size: 0.95rem; columns: 2; -webkit-columns: 2; column-gap: 16px;">{details_val}</div>'
                    else:
                        details_html = f'<div style="margin-top: 4px; color: #555; font-size: 0.95rem;">{details_val}</div>'
                else:
                    details_html = ""

                # Εικονίδιο προσοχής για προβληματικά ευρήματα
                finding_text = str(row['Εύρημα'])
                aa = row['A/A']
                icon_html = ""
                is_safe = False
                
                safe_keywords = ["Κανένα", "Κανένας", "Καμία", "Όχι", "Εντός ορίων", "Δεν εντοπίστηκαν", "0 ημέρες", "-"]
                
                if aa in [1, 2]: # Πληροφοριακά
                    is_safe = True
                else:
                    for safe in safe_keywords:
                        if safe in finding_text:
                            is_safe = True
                            break
                
                if not is_safe:
                    icon_html = "⚠️ "
                    finding_text = f"<span style='color: #d9534f;'>{finding_text}</span>"

                st.markdown(
                    f"""
                    <div style="margin-bottom: 20px; padding: 12px; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                        <div style="font-size: 1.3rem; color: #111; margin-bottom: 6px;">
                            <span style="font-weight: 700; color: #2c3e50;">{row['Έλεγχος']}</span>
                            <br>
                            <span style="font-weight: 600; color: #2980b9;">{icon_html}{finding_text}</span>
                        </div>
                        {details_html}
                        {actions_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Column 1: 1, 2, 5, 6
            with ac1:
                for aa in [1, 2, 5, 6]:
                    r = audit_df[audit_df['A/A'] == aa]
                    if not r.empty: render_check(r.iloc[0])

            # Column 2: 3, 4, 7, 8 (Gaps first)
            with ac2:
                for aa in [3, 4, 7, 8]:
                    r = audit_df[audit_df['A/A'] == aa]
                    if not r.empty: render_check(r.iloc[0])

            # Column 3: 9
            with ac3:
                for aa in [9]:
                    r = audit_df[audit_df['A/A'] == aa]
                    if not r.empty: render_check(r.iloc[0])
            
            register_view("Διαγνωστικός_Έλεγχος", audit_df)
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        
        if 'Κλάδος/Πακέτο Κάλυψης' in df.columns:
            st.markdown("### Συνοπτική Αναφορά - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)")
            st.info("Σημείωση: Στα αθροίσματα συμπεριλαμβάνονται μόνο τα ποσά σε €. Τα ποσά σε ΔΡΧ (πριν το 2002) εμφανίζονται αλλά δεν υπολογίζονται στα συνολικά.")
            # Προετοιμασία δεδομένων
            summary_df = df.copy()
            # Κανονικοποίηση τιμών κλάδου/πακέτου
            summary_df['Κλάδος/Πακέτο Κάλυψης'] = (
                summary_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
            )
            # Μετατροπή ημερομηνιών σε datetime για φίλτρα και ομαδοποίηση
            summary_df['Από_dt'] = pd.to_datetime(summary_df.get('Από'), format='%d/%m/%Y', errors='coerce')
            summary_df['Έως_dt'] = pd.to_datetime(summary_df.get('Έως'), format='%d/%m/%Y', errors='coerce')

            # Φίλτρα: Ταμείο και ημερομηνίες (όπως στην αναφορά Ημερών)
            filter_cols = st.columns([1.4, 0.9, 0.9, 0.4])
            selected_tameia = ['Όλα']
            from_summary_str = ''
            to_summary_str = ''

            with filter_cols[0]:
                if 'Ταμείο' in summary_df.columns:
                    tameia_options = sorted(summary_df['Ταμείο'].dropna().astype(str).unique().tolist())
                    selected_tameia = st.multiselect(
                        "Ταμείο:",
                        options=tameia_options,
                        default=[],
                        key="summary_filter_tameio"
                    )
                else:
                    st.write("")
                    selected_tameia = []

            with filter_cols[1]:
                from_summary_str = st.text_input(
                    "Από (dd/mm/yyyy):",
                    value="",
                    placeholder="01/01/1980",
                    key="summary_filter_from"
                )

            with filter_cols[2]:
                to_summary_str = st.text_input(
                    "Έως (dd/mm/yyyy):",
                    value="",
                    placeholder="31/12/2025",
                    key="summary_filter_to"
                )

            with filter_cols[3]:
                st.write("")

            # Εφαρμογή φίλτρων Ταμείου
            if 'Ταμείο' in summary_df.columns and selected_tameia:
                summary_df = summary_df[summary_df['Ταμείο'].isin(selected_tameia)]

            # Εφαρμογή φίλτρων ημερομηνιών
            if from_summary_str:
                try:
                    from_dt = pd.to_datetime(from_summary_str, format='%d/%m/%Y')
                    summary_df = summary_df[summary_df['Από_dt'] >= from_dt]
                except Exception:
                    st.warning("Μη έγκυρη ημερομηνία στο πεδίο Από για τη Συνοπτική Αναφορά.")
            if to_summary_str:
                try:
                    to_dt = pd.to_datetime(to_summary_str, format='%d/%m/%Y')
                    summary_df = summary_df[summary_df['Από_dt'] <= to_dt]
                except Exception:
                    st.warning("Μη έγκυρη ημερομηνία στο πεδίο Έως για τη Συνοπτική Αναφορά.")

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

            summary_df = apply_negative_time_sign(summary_df)
            
            # Ομαδοποίηση με βάση Κλάδος/Πακέτο και (αν υπάρχει) Ταμείο
            group_keys = ['Κλάδος/Πακέτο Κάλυψης']
            if 'Ταμείο' in summary_df.columns:
                group_keys.append('Ταμείο')

            grouped = summary_df.groupby(group_keys).agg({
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
            
            # Μετράμε τις εγγραφές για κάθε συνδυασμό (Κλάδος, Ταμείο)
            record_counts = summary_df.groupby(group_keys).size().reset_index(name='Αριθμός Εγγραφών')
            
            # Συνδυάζουμε τα δεδομένα
            summary_final = grouped.merge(record_counts, on=group_keys, how='left')
            
            # Προσθήκη περιγραφής από το Παράρτημα
            if 'Κωδικός Κλάδων / Πακέτων Κάλυψης' in df.columns and 'Περιγραφή' in df.columns:
                # Δημιουργούμε DataFrame για merge (διαφορετικό από το dictionary description_map)
                desc_df_merge = df[['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']].copy()
                desc_df_merge = desc_df_merge.dropna(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή'])
                desc_df_merge = desc_df_merge[desc_df_merge['Κωδικός Κλάδων / Πακέτων Κάλυψης'] != '']
                desc_df_merge = desc_df_merge[desc_df_merge['Περιγραφή'] != '']
                # Αφαιρούμε duplicates - κρατάμε την πρώτη περιγραφή για κάθε κωδικό
                desc_df_merge = desc_df_merge.drop_duplicates(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης'])
                desc_df_merge.columns = ['Κλάδος/Πακέτο Κάλυψης', 'Περιγραφή']
                
                # Κανονικοποίηση τιμών για matching
                desc_df_merge['Κλάδος/Πακέτο Κάλυψης'] = desc_df_merge['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
                
                # Merge με τη συνοπτική αναφορά
                summary_final = summary_final.merge(desc_df_merge, on='Κλάδος/Πακέτο Κάλυψης', how='left')
            
            # Αναδιατάσσουμε τις στήλες - Περιγραφή δεξιά από Κλάδος/Πακέτο
            columns_order = ['Κλάδος/Πακέτο Κάλυψης']
            if 'Ταμείο' in summary_final.columns:
                columns_order.append('Ταμείο')
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
                use_container_width=True
            )
            register_view("Συνοπτική Αναφορά", display_summary)
            render_print_button(
                "print_summary",
                "Συνοπτική Αναφορά",
                display_summary,
                description="Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης για τις περιόδους που εμφανίζονται, καθώς και άθροισμα αποδοχών και εισφορών (μόνο των εγγραφών σε €)."
            )
        else:
            st.warning("Η στήλη 'Κλάδος/Πακέτο Κάλυψης' δεν βρέθηκε στα δεδομένα.")
    
    with tab_yearly:
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
            with st.container():
                y1, y2, y3, y4, y5, y6, y7 = st.columns([1.1, 1.1, 1.4, 1.1, 1.0, 1.0, 1.2])

                with y1:
                    if 'Ταμείο' in yearly_df.columns:
                        tameia_opts = sorted(yearly_df['Ταμείο'].dropna().astype(str).unique().tolist())
                        sel_tameia = st.multiselect("Ταμείο:", tameia_opts, default=[], key="y_filter_tameio")
                        if sel_tameia:
                            yearly_df = yearly_df[yearly_df['Ταμείο'].isin(sel_tameia)]

                with y2:
                    if 'Τύπος Ασφάλισης' in yearly_df.columns:
                        tyas_opts = sorted(yearly_df['Τύπος Ασφάλισης'].dropna().astype(str).unique().tolist())
                        sel_tyas = st.multiselect("Τύπος Ασφάλισης:", tyas_opts, default=[], key="y_filter_typos_asfal")
                        if sel_tyas:
                            yearly_df = yearly_df[yearly_df['Τύπος Ασφάλισης'].isin(sel_tyas)]

                with y3:
                    if 'Κλάδος/Πακέτο Κάλυψης' in yearly_df.columns:
                        # Δημιουργούμε options με περιγραφές
                        klados_codes = sorted(yearly_df['Κλάδος/Πακέτο Κάλυψης'].dropna().astype(str).unique().tolist())
                        klados_opts_with_desc = []
                        klados_code_map_y = {}
                        
                        for code in klados_codes:
                            if code in description_map and description_map[code]:
                                option_label = f"{code} - {description_map[code]}"
                                klados_opts_with_desc.append(option_label)
                                klados_code_map_y[option_label] = code
                            else:
                                klados_opts_with_desc.append(code)
                                klados_code_map_y[code] = code
                        
                        sel_klados = st.multiselect("Κλάδος/Πακέτο:", klados_opts_with_desc, default=[], key="y_filter_klados")
                        
                        if sel_klados:
                            selected_codes = [klados_code_map_y.get(opt, opt) for opt in sel_klados]
                            yearly_df = yearly_df[yearly_df['Κλάδος/Πακέτο Κάλυψης'].isin(selected_codes)]

                with y4:
                    if earnings_col and earnings_col in yearly_df.columns:
                        apod_opts = sorted(yearly_df[earnings_col].dropna().astype(str).unique().tolist())
                        sel_apod = st.multiselect("Τύπος Αποδοχών:", apod_opts, default=[], key="y_filter_apodochon")
                        if sel_apod:
                            yearly_df = yearly_df[yearly_df[earnings_col].isin(sel_apod)]

            with y5:
                from_y_str = st.text_input("Από (dd/mm/yyyy):", value="", placeholder="01/01/1980", key="y_filter_from_date")
            with y6:
                to_y_str = st.text_input("Έως (dd/mm/yyyy):", value="", placeholder="31/12/2025", key="y_filter_to_date")
            with y7:
                st.write("")

            # Διακόπτης εμφάνισης μόνο ετήσιων γραμμών συνόλου (default: πλήρης εικόνα)
            show_yearly_totals_only = st.toggle("Μόνο ετήσιες γραμμές συνόλου", value=False, key="yearly_totals_only")

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

            yearly_df = apply_negative_time_sign(yearly_df)
            
            # Ομαδοποίηση με βάση: Έτος, Ταμείο, Τύπο Ασφάλισης, Κλάδο/Πακέτο και Τύπο Αποδοχών (αν υπάρχει)
            group_keys = ['Έτος', 'Ταμείο']
            if 'Τύπος Ασφάλισης' in yearly_df.columns:
                group_keys.append('Τύπος Ασφάλισης')
            group_keys.append('Κλάδος/Πακέτο Κάλυψης')
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
            count_keys = ['Έτος', 'Ταμείο']
            if 'Τύπος Ασφάλισης' in yearly_df.columns:
                count_keys.append('Τύπος Ασφάλισης')
            count_keys.append('Κλάδος/Πακέτο Κάλυψης')
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

            # Κανονικοποίηση ονόματος στήλης τύπου αποδοχών για εμφάνιση
            if earnings_col and earnings_col != 'Τύπος Αποδοχών' and earnings_col in yearly_final.columns:
                yearly_final = yearly_final.rename(columns={earnings_col: 'Τύπος Αποδοχών'})
            
            # Αναδιατάσσουμε τις στήλες: Έτος, Ταμείο, Τύπος Ασφάλισης, Κλάδος/Πακέτο, Από, Έως, Τύπος Αποδοχών, συνολικά
            display_order = ['Έτος', 'Ταμείο']
            if 'Τύπος Ασφάλισης' in yearly_final.columns:
                display_order.append('Τύπος Ασφάλισης')
            display_order += ['Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως']
            if 'Τύπος Αποδοχών' in yearly_final.columns:
                display_order.append('Τύπος Αποδοχών')
            display_order += ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
            yearly_final = yearly_final[display_order]
            
            # Ταξινομούμε πρώτα ανά έτος, μετά ανά ταμείο, μετά ανά κλάδο
            sort_keys = ['Έτος', 'Ταμείο']
            if 'Τύπος Ασφάλισης' in yearly_final.columns:
                sort_keys.append('Τύπος Ασφάλισης')
            sort_keys.append('Κλάδος/Πακέτο Κάλυψης')
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

            # Αφαιρούμε επαναλαμβανόμενο «Τύπος Ασφάλισης» ανά (Έτος, Ταμείο, Τύπος)
            if 'Τύπος Ασφάλισης' in display_yearly_detailed.columns:
                type_series = display_yearly_detailed['Τύπος Ασφάλισης'].fillna('').astype(str)
                display_yearly_detailed['Τύπος_Ασφάλισης_Display'] = type_series
                for i in range(1, len(display_yearly_detailed)):
                    same_group = (
                        display_yearly_detailed.iloc[i]['Έτος'] == display_yearly_detailed.iloc[i-1]['Έτος'] and
                        display_yearly_detailed.iloc[i]['Ταμείο'] == display_yearly_detailed.iloc[i-1]['Ταμείο'] and
                        type_series.iloc[i] == type_series.iloc[i-1]
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
            display_columns += ['Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως', 'Τύπος Αποδοχών']
            display_columns += ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
            
            # Δημιουργούμε τον τελικό πίνακα για εμφάνιση
            display_final = display_yearly_detailed[display_columns].copy()
            
            # Μετονομάζουμε τις στήλες για εμφάνιση
            final_headers = ['Έτος', 'Ταμείο']
            if 'Τύπος_Ασφάλισης_Display' in display_yearly_detailed.columns:
                final_headers.append('Τύπος Ασφάλισης')
            final_headers += ['Κλάδος/Πακέτο Κάλυψης', 'Από', 'Έως', 'Τύπος Αποδοχών']
            final_headers += ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές Αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
            display_final.columns = final_headers
            period_column_name = 'Έως'
            
            # Εφαρμόζουμε ελληνική μορφοποίηση για αριθμητικές στήλες
            numeric_cols_yearly = ['Έτη', 'Μήνες', 'Ημέρες', 'Αριθμός Εγγραφών']
            for col in numeric_cols_yearly:
                if col in display_final.columns:
                    # Έτη και Μήνες με 1 δεκαδικό, οι υπόλοιπες χωρίς δεκαδικά
                    decimals = 1 if col in ['Έτη', 'Μήνες'] else 0
                    display_final[col] = display_final[col].apply(lambda x: format_number_greek(x, decimals=decimals) if pd.notna(x) and x != '' and str(x).strip() != '' else x)
            
            # Στυλ για γραμμές "Σύνολο <Έτος>" και σκούρα γραμματοσειρά στη στήλη Έτος
            def _highlight_totals(row):
                value = str(row.get(period_column_name, ''))
                styles = []
                
                # Βρίσκουμε τη θέση της στήλης "Έως"
                eos_index = list(row.index).index(period_column_name) if period_column_name in row.index else -1
                
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
                # Φίλτρο εμφάνισης μόνο γραμμών «Σύνολο <Έτος>» αν είναι ενεργός ο διακόπτης
                if st.session_state.get('yearly_totals_only', False):
                    try:
                        display_final = display_final[display_final[period_column_name].astype(str).str.startswith('Σύνολο')]
                    except Exception:
                        pass

                register_view("Ετήσια Αναφορά", display_final)
                styled = display_final.style.apply(_highlight_totals, axis=1).apply(_bold_year_column, axis=1)
                st.dataframe(
                    styled,
                    use_container_width=True,
                    key="yearly_table"
                )
            except Exception:
                # Fallback χωρίς χρωματισμό για να διατηρηθούν search/download/expand & scroll
                st.dataframe(
                    display_final,
                    use_container_width=True
                )
            render_print_button(
                "print_yearly",
                "Ετήσια Αναφορά",
                display_final,
                description="Ετήσια αναφορά ανά Ταμείο, Κλάδο/Πακέτο Κάλυψης και τύπο αποδοχών με συγκεντρωτικά στοιχεία."
            )
                
        else:
            st.warning("Οι στήλες 'Από' ή 'Ταμείο' δεν βρέθηκαν στα δεδομένα.")
    
    with tab_days:
        # Αναφορά Ημερών Ασφάλισης ανά Έτος και Διάστημα, με στήλες τα Πακέτα Κάλυψης
        st.markdown("### Αναφορά Ημερών Ασφάλισης (Έτος × Διάστημα × Πακέτα)")

        if 'Από' in df.columns and 'Έως' in df.columns:
            days_df = df.copy()
            days_df['Από_DateTime'] = pd.to_datetime(days_df['Από'], format='%d/%m/%Y', errors='coerce')
            days_df['Έως_DateTime'] = pd.to_datetime(days_df['Έως'], format='%d/%m/%Y', errors='coerce')
            days_df = days_df.dropna(subset=['Από_DateTime', 'Έως_DateTime'])
            days_df['Έτος'] = days_df['Από_DateTime'].dt.year

            # Πρώτα προσωρινός υπολογισμός για να πάρουμε τα διαθέσιμα πακέτα κάλυψης
            pkg_col = 'Κλάδος/Πακέτο Κάλυψης'
            available_packages = []
            if pkg_col in days_df.columns:
                available_packages = sorted(days_df[pkg_col].dropna().astype(str).unique().tolist())
            
            # Φίλτρα σε μία γραμμή: Ταμείο | Πακέτα | Από | Έως | Συντελεστές
            f1, f2, f3, f4, f6 = st.columns([1.4, 1.8, 0.9, 0.9, 1.4])
            with f1:
                if 'Ταμείο' in days_df.columns:
                    tameia_opts = sorted(days_df['Ταμείο'].dropna().astype(str).unique().tolist())
                    sel_tameia = st.multiselect('Ταμείο:', tameia_opts, default=[], key='insdays_filter_tameio')
                    if sel_tameia:
                        days_df = days_df[days_df['Ταμείο'].isin(sel_tameia)]
            with f2:
                # Φίλτρο για πακέτα κάλυψης (με περιγραφές από description_map)
                selected_package_codes = []
                if available_packages:
                    package_opts_with_desc = []
                    package_label_to_code = {}
                    for code in available_packages:
                        if code in description_map and description_map[code]:
                            label = f"{code} - {description_map[code]}"
                            package_opts_with_desc.append(label)
                            package_label_to_code[label] = code
                        else:
                            package_opts_with_desc.append(code)
                            package_label_to_code[code] = code
                    sel_packages = st.multiselect('Πακέτα Κάλυψης:', package_opts_with_desc, default=[], key='insdays_filter_packages')
                    if sel_packages:
                        selected_package_codes = [package_label_to_code.get(opt, opt) for opt in sel_packages]
                else:
                    sel_packages = []
                    selected_package_codes = []
            with f3:
                from_str = st.text_input('Από (dd/mm/yyyy):', value='', placeholder='01/01/1980', key='insdays_filter_from')
            with f4:
                to_str = st.text_input('Έως (dd/mm/yyyy):', value='', placeholder='31/12/2025', key='insdays_filter_to')
            with f6:
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

            sign_series = 1
            if 'Μικτές αποδοχές' in days_df.columns or 'Συνολικές εισφορές' in days_df.columns:
                sign_series = days_df.apply(
                    lambda r: get_negative_amount_sign(
                        clean_numeric_value(r.get('Μικτές αποδοχές', 0), exclude_drx=True),
                        clean_numeric_value(r.get('Συνολικές εισφορές', 0), exclude_drx=True)
                    ),
                    axis=1
                )

            # Υπολογισμός μονάδων ανά γραμμή (πάντα άθροισμα σε ημέρες)
            days_df['Μονάδες'] = days_df['Ημέρες'] + (days_df['Μήνες'] * month_days) + (days_df['Έτη'] * year_days)
            if not isinstance(sign_series, int):
                days_df['Μονάδες'] = days_df['Μονάδες'] * sign_series
            
            # Αφαίρεση γραμμών με μηδενικές μονάδες (χωρίς ημέρες/μήνες/έτη)
            days_df = days_df[days_df['Μονάδες'] != 0]

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
                
                # Φιλτράρισμα στηλών με βάση την επιλογή πακέτων (με χρήση κωδικών)
                if selected_package_codes:
                    package_cols = [col for col in package_cols if col in selected_package_codes]
                
                final_blocks = []

                # Συνολικό σύνολο όλων των ετών (στην αρχή) - μόνο για επιλεγμένες στήλες
                grand_totals = {col: int(round(pivot[col].sum())) for col in package_cols}
                grand_row = {'Έτος': '', 'Διάστημα': 'Σύνολο Όλων των Ετών'}
                grand_row.update(grand_totals)
                pivot_with_total_col = ['Έτος', 'Διάστημα'] + package_cols
                final_blocks.append(pd.DataFrame([grand_row], columns=pivot_with_total_col))

                # Κατά έτος μπλοκ και σύνολο
                for yr in sorted(pivot['Έτος'].unique()):
                    yr_rows = pivot[pivot['Έτος'] == yr][['Έτος', 'Διάστημα'] + package_cols].copy()
                    final_blocks.append(yr_rows)
                    totals = {col: int(round(yr_rows[col].sum())) for col in package_cols}
                    total_row = {'Έτος': '', 'Διάστημα': f"Σύνολο {int(yr)}"}
                    total_row.update(totals)
                    final_blocks.append(pd.DataFrame([total_row], columns=pivot_with_total_col))

                display_days = pd.concat(final_blocks, ignore_index=True) if final_blocks else pivot.copy()

                # Μετατροπή τιμών σε ακέραιους για καθαρή εμφάνιση (μόνο επιλεγμένες στήλες)
                for col in package_cols:
                    if col in display_days.columns:
                        display_days[col] = display_days[col].fillna(0).round(0).astype(int)

                # Καλύτερη εμφάνιση επαναλαμβανόμενου έτους
                display_days['Έτος_Display'] = display_days['Έτος'].astype(str)
                for i in range(1, len(display_days)):
                    if str(display_days.iloc[i-1]['Έτος']).isdigit() and display_days.iloc[i]['Έτος'] == display_days.iloc[i-1]['Έτος']:
                        display_days.iloc[i, display_days.columns.get_loc('Έτος_Display')] = ''

                # Τελικός πίνακας εμφάνισης
                disp_cols = ['Έτος_Display', 'Διάστημα'] + package_cols
                display_final_days = display_days[disp_cols].copy()
                display_final_days.columns = ['Έτος', 'Διάστημα'] + package_cols

                register_view("Ημέρες Ασφάλισης", display_final_days)

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
                    formatter = {col: _blank_zero for col in package_cols}
                    
                    # Συνάρτηση για bold στη στήλη Έτος
                    def _bold_year_column(row):
                        styles = [''] * len(row)
                        # Η στήλη Έτος είναι η πρώτη (index 0)
                        styles[0] = 'font-weight: bold;'
                        return styles
                    
                    # CSS styles για αριστερή στοίχιση όλων των στηλών
                    table_styles = [
                        {'selector': 'th', 'props': [('text-align', 'left')]},
                        {'selector': 'td', 'props': [('text-align', 'left')]},
                    ]
                    
                    styled_days = (
                        display_final_days
                        .style
                        .apply(_highlight_totals_days, axis=1)
                        .apply(_bold_year_column, axis=1)
                        .format(formatter)
                        .set_properties(**{'text-align': 'left'})
                        .set_table_styles(table_styles)
                    )
                    
                    st.dataframe(styled_days, use_container_width=True)
                except Exception:
                    # Fallback χωρίς ειδική μορφοποίηση
                    st.dataframe(
                        display_final_days.style.set_properties(**{'text-align': 'left'}),
                        use_container_width=True
                    )

                # Κουμπί εκτύπωσης (με κενά για μηδενικές τιμές)
                print_days = display_final_days.copy()
                # Εφαρμογή κενών για μηδενικές τιμές σε όλες τις αριθμητικές στήλες
                for col in package_cols:
                    print_days[col] = print_days[col].apply(lambda v: '' if pd.isna(v) or float(v) == 0 else int(round(float(v))))
                render_print_button(
                    "print_ins_days",
                    "Αναφορά Ημερών Ασφάλισης",
                    print_days,
                    description="Κατανομή ημερών ασφάλισης ανά έτος, διάστημα και πακέτο κάλυψης."
                )
        else:
            st.warning("Οι στήλες 'Από' και 'Έως' δεν βρέθηκαν στα δεδομένα.")
    
    with tab_gaps:
        # Αναφορά Κενών Διαστήματων
        st.markdown("### Αναφορά Κενών Διαστήματων και διαστημάτων χωρίς ημέρες ασφάλισης")
        st.info("Σκοπός: Εντοπίζει χρονικά διαστήματα που δεν εμφανίζονται καθόλου στο ΑΤΛΑΣ από την έναρξη της ασφάλισης έως σήμερα.")
        
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
                    use_container_width=True
                )
                register_view("Κενά Διαστήματα", display_gaps)
                
                # Κουμπί εκτύπωσης
                render_print_button(
                    "print_gaps",
                    "Κενά Διαστήματα",
                    gaps_df,
                    description="Χρονικές περίοδοι όπου δεν βρέθηκε ασφαλιστική κάλυψη μεταξύ των δηλωμένων εγγραφών."
                )
                
                # Συμβουλές
                st.markdown("#### Συμβουλές")
                if len(gaps_df) > 0:
                    st.warning("Σημαντικό: Τα εντοπισμένα κενά διαστήματα μπορεί να επηρεάσουν τη θεμελίωση δικαιώματος για σύνταξη (εξαγορά, ασφαλιστικός δεσμός για μειωμένη σύνταξη).")
                    
                    # Εμφάνιση του μεγαλύτερου κενού
                    max_gap = gaps_df.loc[gaps_df['Ημερολογιακές ημέρες'].idxmax()]
                    st.info(f"Μεγαλύτερο κενό: {max_gap['Από']} - {max_gap['Έως']} ({max_gap['Ημερολογιακές ημέρες']} ημερολογιακές ημέρες)")
            else:
                st.success("Καμία κενή περίοδος δεν εντοπίστηκε. Όλα τα διαστήματα είναι συνεχή.")
                st.info("Σημείωση: Αυτό σημαίνει ότι δεν υπάρχουν κενά μεταξύ των ασφαλιστικών σας περιόδων.")

            # Δεύτερος πίνακας: Δηλωμένα διαστήματα χωρίς Έτη/Μήνες/Ημέρες
            st.markdown("#### Διαστήματα χωρίς ημέρες ασφάλισης")
            zero_duration_df = df.copy()

            # Κρατάμε μόνο γραμμές με έγκυρες ημερομηνίες
            zero_duration_df['Από_DateTime'] = pd.to_datetime(zero_duration_df['Από'], format='%d/%m/%Y', errors='coerce')
            zero_duration_df['Έως_DateTime'] = pd.to_datetime(zero_duration_df['Έως'], format='%d/%m/%Y', errors='coerce')
            zero_duration_df = zero_duration_df.dropna(subset=['Από_DateTime', 'Έως_DateTime'])

            # Δημιουργία αριθμητικών τιμών για Έτη/Μήνες/Ημέρες (αν δεν υπάρχουν, θεωρούμε 0)
            duration_columns = ['Έτη', 'Μήνες', 'Ημέρες']
            for col in duration_columns:
                if col not in zero_duration_df.columns:
                    zero_duration_df[col] = 0
                numeric_col = f"__{col}_numeric"
                zero_duration_df[numeric_col] = zero_duration_df[col].apply(clean_numeric_value)

            # Υπολογίζουμε συνολική διάρκεια ανά γραμμή
            zero_duration_df['__duration_sum'] = (
                zero_duration_df['__Έτη_numeric'] +
                zero_duration_df['__Μήνες_numeric'] +
                zero_duration_df['__Ημέρες_numeric']
            )

            # Προσδιορίζουμε αν για το ίδιο διάστημα (Από/Έως) υπάρχει κάπου αλλού μη μηδενική διάρκεια
            if not zero_duration_df.empty:
                zero_duration_df['__duration_sum_group'] = zero_duration_df.groupby(
                    ['Από_DateTime', 'Έως_DateTime']
                )['__duration_sum'].transform('sum')

            # Επιλογή μόνο διαστημάτων όπου τόσο η τρέχουσα γραμμή όσο και το σύνολο του διαστήματος είναι μηδενικά
            zero_duration_df = zero_duration_df[
                (zero_duration_df['__duration_sum'] == 0) &
                (zero_duration_df['__duration_sum_group'] == 0)
            ]

            if zero_duration_df.empty:
                st.success("Δεν βρέθηκαν διαστήματα χωρίς δηλωμένη διάρκεια.")
            else:
                columns_to_show = ['Από', 'Έως']
                optional_columns = [
                    'Ταμείο',
                    'Τύπος Ασφάλισης',
                    'Κλάδος/Πακέτο Κάλυψης',
                    'Τύπος Αποδοχών',
                    'Περιγραφή Τύπου Αποδοχών',
                    'Α-Μ εργοδότη'
                ]
                for col in optional_columns + duration_columns:
                    if col in zero_duration_df.columns and col not in columns_to_show:
                        columns_to_show.append(col)

                # Μετακινούμε τις στήλες Τύπος Αποδοχών ώστε να εμφανίζονται μετά το Κλάδος/Πακέτο
                earnings_columns = [
                    c for c in ['Τύπος Αποδοχών', 'Περιγραφή Τύπου Αποδοχών']
                    if c in columns_to_show
                ]
                if earnings_columns and 'Κλάδος/Πακέτο Κάλυψης' in columns_to_show:
                    insert_pos = columns_to_show.index('Κλάδος/Πακέτο Κάλυψης') + 1
                    for col in earnings_columns:
                        columns_to_show.remove(col)
                    for offset, col in enumerate(earnings_columns):
                        columns_to_show.insert(insert_pos + offset, col)

                zero_display_df = zero_duration_df[columns_to_show].copy()

                # Αφαιρούμε τα βοηθητικά πεδία
                drop_helpers = [c for c in zero_display_df.columns if c.startswith('__')]
                zero_display_df = zero_display_df.drop(columns=drop_helpers, errors='ignore')

                # Μορφοποίηση αριθμών
                if 'Έτη' in zero_display_df.columns:
                    zero_display_df['Έτη'] = zero_display_df['Έτη'].apply(lambda x: format_number_greek(x, decimals=1) if str(x).strip() not in ['', '-'] else '')
                if 'Μήνες' in zero_display_df.columns:
                    zero_display_df['Μήνες'] = zero_display_df['Μήνες'].apply(lambda x: format_number_greek(x, decimals=1) if str(x).strip() not in ['', '-'] else '')
                if 'Ημέρες' in zero_display_df.columns:
                    zero_display_df['Ημέρες'] = zero_display_df['Ημέρες'].apply(lambda x: format_number_greek(x, decimals=0) if str(x).strip() not in ['', '-'] else '')

                st.warning(
                    "Οι παρακάτω εγγραφές έχουν βρεθεί στο ΑΤΛΑΣ αλλά δεν περιλαμβάνουν καμία τιμή σε Έτη/Μήνες/Ημέρες. "
                    "Ενδέχεται να χρειαστεί επαλήθευση με τα πρωτογενή στοιχεία."
                )
                st.dataframe(
                    zero_display_df,
                    use_container_width=True
                )
                register_view("Διαστήματα χωρίς ημέρες", zero_display_df)
                render_print_button(
                    "print_zero_duration",
                    "Διαστήματα χωρίς ημέρες ασφάλισης",
                    zero_display_df,
                    description="Εγγραφές που εμφανίζονται στον ΑΤΛΑΣ αλλά χωρίς να συνδέονται με ημέρες ασφάλισης."
                )
        else:
            st.warning("Οι στήλες 'Από' και 'Έως' δεν βρέθηκαν στα δεδομένα.")
    
    with tab_apd:
        # Ανάλυση ΑΠΔ - Αντίγραφο από Κύρια Δεδομένα χωρίς Α/Α και Σελίδα
        apd_columns = [col for col in df.columns if col not in ['Φορέας', 'Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή', 'Κωδικός Τύπου Αποδοχών', 'Σελίδα']]
        apd_df = df[apd_columns] if apd_columns else df
        
        # Αφαιρούμε τη στήλη Σελίδα αν υπάρχει ακόμα
        if 'Σελίδα' in apd_df.columns:
            apd_df = apd_df.drop('Σελίδα', axis=1)
        
        # Αρχικό πλήθος εγγραφών (πριν τα φίλτρα)
        initial_count = len(apd_df)
        
        # Το καθεστώς ασφάλισης θα εμφανιστεί κάτω από τα φίλτρα

        retention_filter_mode = st.session_state.get('apd_filter_retention_mode', 'Όλα')

        # --- Filters Section ---
        with st.container():
            # Γραμμή 1: Κύρια φίλτρα
            col1, col2, col3, col4 = st.columns([1.5, 1.5, 2, 1.5])

            with col1:
                # Φίλτρο Ταμείου
                if 'Ταμείο' in apd_df.columns:
                    taimeia_options = sorted(apd_df['Ταμείο'].dropna().unique().tolist())
                    selected_taimeia = st.multiselect(
                        "Ταμείο:",
                        options=taimeia_options,
                        default=[],
                        key="apd_filter_taimeio",
                        placeholder=""
                    )
                    if selected_taimeia:
                        apd_df = apd_df[apd_df['Ταμείο'].isin(selected_taimeia)]

            with col2:
                # Φίλτρο Τύπου Ασφάλισης (με προεπιλογή ΜΙΣΘΩΤΗ)
                if 'Τύπος Ασφάλισης' in apd_df.columns:
                    typos_options = sorted(apd_df['Τύπος Ασφάλισης'].dropna().unique().tolist())
                    
                    default_typos = []
                    for opt in typos_options:
                        if "ΜΙΣΘΩΤΗ ΑΣΦΑΛΙΣΗ" in str(opt).upper():
                            default_typos = [opt]
                            break
                    
                    selected_typos = st.multiselect(
                        "Τύπος Ασφάλισης:",
                        options=typos_options,
                        default=default_typos,
                        key="apd_filter_typos",
                        placeholder=""
                    )
                    if selected_typos:
                        apd_df = apd_df[apd_df['Τύπος Ασφάλισης'].isin(selected_typos)]

            with col3:
                # Φίλτρο Κλάδου/Πακέτου με περιγραφές
                if 'Κλάδος/Πακέτο Κάλυψης' in apd_df.columns:
                    klados_codes = sorted(apd_df['Κλάδος/Πακέτο Κάλυψης'].dropna().unique().tolist())
                    klados_options_with_desc = []
                    klados_code_map = {}
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
                        default=[],
                        key="apd_filter_klados",
                        placeholder=""
                    )
                    if selected_klados:
                        selected_codes = [klados_code_map.get(opt, opt) for opt in selected_klados]
                        apd_df = apd_df[apd_df['Κλάδος/Πακέτο Κάλυψης'].isin(selected_codes)]

            with col4:
                # Φίλτρο Τύπου Αποδοχών
                earnings_col = next((c for c in apd_df.columns if 'Τύπος Αποδοχών' in c), None)
                if earnings_col:
                    options_raw = apd_df[earnings_col].dropna().astype(str).unique().tolist()
                    typos_apodochon_options = sorted(options_raw)
                    selected_typos_apodochon = st.multiselect(
                        "Τύπος Αποδοχών:",
                        options=typos_apodochon_options,
                        default=[],
                        key="apd_filter_apodochon",
                        placeholder=""
                    )
                    if selected_typos_apodochon:
                        apd_df = apd_df[apd_df[earnings_col].isin(selected_typos_apodochon)]

            # Γραμμή 2: Φίλτρα ημερομηνιών και ποσοστού
            col5, col6, col7, col8, col9 = st.columns([1.2, 1.2, 1.0, 1.4, 1.2])
            with col5:
                from_date_str = st.text_input("Από (dd/mm/yyyy):", value="01/01/2002", placeholder="01/01/2002", key="apd_filter_from_date")
            with col6:
                to_date_str = st.text_input("Έως (dd/mm/yyyy):", value="", placeholder="31/12/1990", key="apd_filter_to_date")
            with col7:
                filter_threshold = st.number_input("Φίλτρο %", min_value=0.0, max_value=100.0, value=18.0, step=0.1, format="%.1f", key="apd_filter_val")
            with col8:
                retention_filter_mode = st.selectbox(
                    "Τύπος Φίλτρου",
                    options=["Όλα", "Μεγαλύτερο ή ίσο", "Μικρότερο από"],
                    index=0,
                    key="apd_filter_retention_mode"
                )
            with col9:
                highlight_threshold = st.number_input("Επισήμανση <", min_value=0.0, max_value=100.0, value=21.0, step=0.1, format="%.1f", key="apd_highlight_val")

            # Εφαρμογή φίλτρων ημερομηνιών
            if 'Από' in apd_df.columns and (from_date_str or to_date_str):
                apd_df['Από_DateTime'] = pd.to_datetime(apd_df['Από'], format='%d/%m/%Y', errors='coerce')
                
                if from_date_str:
                    try:
                        from_date_pd = pd.to_datetime(from_date_str, format='%d/%m/%Y')
                        apd_df = apd_df[apd_df['Από_DateTime'] >= from_date_pd]
                    except:
                        st.error("Μη έγκυρη μορφή ημερομηνίας 'Από'")
                
                if to_date_str:
                    try:
                        to_date_pd = pd.to_datetime(to_date_str, format='%d/%m/%Y')
                        apd_df = apd_df[apd_df['Από_DateTime'] <= to_date_pd]
                    except:
                        st.error("Μη έγκυρη μορφή ημερομηνίας 'Έως'")
                
                apd_df = apd_df.drop('Από_DateTime', axis=1)

        # Γραμμή ενημέρωσης κάτω από τα φίλτρα
        info_col, stats_col, toggle_col = st.columns([1.8, 2.5, 1.0])
        with info_col:
            st.info(f"Καθεστώς: **{insurance_status_message}**")
        with stats_col:
            stats_placeholder = st.empty()
        with toggle_col:
            st.toggle("Μόνο ετήσιες γραμμές συνόλου", value=False, key="apd_year_totals_only")
        
        # --- Data Display and Processing ---
        
        # Δημιουργούμε αντίγραφο για εμφάνιση με μορφοποίηση και styling
        display_apd_df = apd_df.copy()

        # Προσθήκη περιγραφής κλάδου/πακέτου
        if 'Κλάδος/Πακέτο Κάλυψης' in display_apd_df.columns and isinstance(description_map, dict) and len(description_map) > 0:
            display_apd_df['Περιγραφή Κλάδου'] = display_apd_df['Κλάδος/Πακέτο Κάλυψης'].apply(
                lambda x: description_map.get(str(x).strip(), '') if pd.notna(x) else ''
            )
            
            # Αναδιατάσσουμε τις στήλες για να είναι η Περιγραφή δίπλα στον Κλάδο
            cols = list(display_apd_df.columns)
            if 'Περιγραφή Κλάδου' in cols:
                klados_idx = cols.index('Κλάδος/Πακέτο Κάλυψης')
                cols.remove('Περιγραφή Κλάδου')
                cols.insert(klados_idx + 1, 'Περιγραφή Κλάδου')
                display_apd_df = display_apd_df[cols]
        
        # Προσθήκη περιγραφής τύπου αποδοχών
        earnings_col_name = next((col for col in display_apd_df.columns if 'Τύπος Αποδοχών' in col), None)
        if earnings_col_name:
            display_apd_df['Περιγραφή Τύπου Αποδοχών'] = display_apd_df[earnings_col_name].apply(
                lambda x: APODOXES_DESCRIPTIONS.get(str(x).strip(), '') if pd.notna(x) else ''
            )
            
            # Αναδιάταξη στηλών
            cols = list(display_apd_df.columns)
            if 'Περιγραφή Τύπου Αποδοχών' in cols:
                earnings_idx = cols.index(earnings_col_name)
                cols.remove('Περιγραφή Τύπου Αποδοχών')
                cols.insert(earnings_idx + 1, 'Περιγραφή Τύπου Αποδοχών')
                display_apd_df = display_apd_df[cols]

        # Προσθήκη στήλης "Εισφ. πλαφόν"
        if 'Από' in display_apd_df.columns and earnings_col_name:
            def calculate_plafond(row):
                try:
                    year = pd.to_datetime(row['Από'], format='%d/%m/%Y').year
                    base_plafond = plafond_map.get(str(year), 0)
                    earnings_type = str(row[earnings_col_name]).strip()
                    if earnings_type in ['04', '05']:
                        return base_plafond / 2
                    return base_plafond
                except (ValueError, TypeError):
                    return None
            
            display_apd_df['Εισφ. πλαφόν'] = display_apd_df.apply(calculate_plafond, axis=1)

            # Αναδιάταξη στηλών: μετά τις Μικτές αποδοχές
            cols = list(display_apd_df.columns)
            if 'Μικτές αποδοχές' in cols and 'Εισφ. πλαφόν' in cols:
                gross_idx = cols.index('Μικτές αποδοχές')
                cols.remove('Εισφ. πλαφόν')
                cols.insert(gross_idx + 1, 'Εισφ. πλαφόν')
                display_apd_df = display_apd_df[cols]

            # Νέα στήλη: Περικοπή = Μικτές αποδοχές - Εισφ. πλαφόν (μόνο θετικές τιμές)
            if 'Μικτές αποδοχές' in display_apd_df.columns:
                def calc_cut_amount(row):
                    gross = clean_numeric_value(row.get('Μικτές αποδοχές', 0), exclude_drx=True)
                    plaf = row.get('Εισφ. πλαφόν')
                    plaf_num = plaf if isinstance(plaf, (int, float)) else clean_numeric_value(plaf)
                    if gross is None or plaf_num is None:
                        return None
                    diff = gross - plaf_num
                    return diff if diff > 0 else None

                display_apd_df['Περικοπή'] = display_apd_df.apply(calc_cut_amount, axis=1)
                cols = list(display_apd_df.columns)
                if 'Περικοπή' in cols and 'Εισφ. πλαφόν' in cols:
                    cols.remove('Περικοπή')
                    plaf_idx = cols.index('Εισφ. πλαφόν')
                    cols.insert(plaf_idx + 1, 'Περικοπή')
                display_apd_df = display_apd_df[cols]

            # Νέα στήλη: Συντ. Αποδοχές = min(Μικτές αποδοχές, Εισφ. πλαφόν)
            if 'Μικτές αποδοχές' in display_apd_df.columns:
                def calc_adjusted_earnings(row):
                    gross = clean_numeric_value(row.get('Μικτές αποδοχές', 0), exclude_drx=True)
                    plaf = row.get('Εισφ. πλαφόν')
                    plaf_num = plaf if isinstance(plaf, (int, float)) else clean_numeric_value(plaf)
                    if plaf_num is None or plaf_num == 0:
                        return gross
                    return min(gross, plaf_num)
                
                display_apd_df['Συντ. Αποδοχές'] = display_apd_df.apply(calc_adjusted_earnings, axis=1)
                # Τοποθέτηση δίπλα στο πλαφόν
                cols = list(display_apd_df.columns)
                if 'Εισφ. πλαφόν' in cols and 'Συντ. Αποδοχές' in cols:
                    plaf_idx = cols.index('Εισφ. πλαφόν')
                    cols.remove('Συντ. Αποδοχές')
                    cols.insert(plaf_idx + 1, 'Συντ. Αποδοχές')
                    display_apd_df = display_apd_df[cols]

            # Νέα στήλη: % κράτησης
            if 'Συνολικές εισφορές' in display_apd_df.columns and 'Συντ. Αποδοχές' in display_apd_df.columns:
                def calculate_retention_percentage(row):
                    total_contributions = clean_numeric_value(row.get('Συνολικές εισφορές', 0), exclude_drx=True)
                    adjusted_earnings = row.get('Συντ. Αποδοχές', 0)
                    if adjusted_earnings is None or adjusted_earnings == 0:
                        return 0.0
                    return total_contributions / adjusted_earnings

                display_apd_df['Συν. % κράτησης'] = display_apd_df.apply(calculate_retention_percentage, axis=1)
                
                # Τοποθέτηση δίπλα στις Συνολικές εισφορές
                cols = list(display_apd_df.columns)
                if 'Συνολικές εισφορές' in cols and 'Συν. % κράτησης' in cols:
                    contributions_idx = cols.index('Συνολικές εισφορές')
                    cols.remove('Συν. % κράτησης')
                    cols.insert(contributions_idx + 1, 'Συν. % κράτησης')
                    display_apd_df = display_apd_df[cols]

        # Εφαρμογή φίλτρου % κράτησης βάσει επιλογής
        if 'Συν. % κράτησης' in display_apd_df.columns:
            retention_threshold_decimal = (filter_threshold or 0.0) / 100.0
            retention_numeric = pd.to_numeric(display_apd_df['Συν. % κράτησης'], errors='coerce')

            if retention_filter_mode == "Μεγαλύτερο ή ίσο":
                mask = retention_numeric >= retention_threshold_decimal
                display_apd_df = display_apd_df[mask].copy()
            elif retention_filter_mode == "Μικρότερο από":
                mask = retention_numeric < retention_threshold_decimal
                display_apd_df = display_apd_df[mask].copy()

        data_rows_count = len(display_apd_df)

        # Προσθήκη στήλης Έτος και ομαδοποίηση (όπως στην Καταμέτρηση)
        if data_rows_count > 0 and 'Από' in display_apd_df.columns:
            working_df = display_apd_df.copy()

            # Υπολογισμός ενιαίας στήλης "Ημέρες Ασφ." = Ημέρες + (Μήνες * 25) + (Έτη * 300)
            def calc_total_days(row):
                d = clean_numeric_value(row.get('Ημέρες', 0)) or 0
                m = clean_numeric_value(row.get('Μήνες', 0)) or 0
                y = clean_numeric_value(row.get('Έτη', 0)) or 0
                return d + (m * 25) + (y * 300)

            working_df['Ημέρες Ασφ.'] = working_df.apply(calc_total_days, axis=1)

            # Αφαίρεση των παλιών στηλών Έτη/Μήνες/Ημέρες
            cols_to_remove = [c for c in ['Έτη', 'Μήνες', 'Ημέρες'] if c in working_df.columns]
            if cols_to_remove:
                working_df = working_df.drop(columns=cols_to_remove)

            working_df['_Από_dt'] = pd.to_datetime(working_df['Από'], format='%d/%m/%Y', errors='coerce')
            working_df['Έτος'] = working_df['_Από_dt'].dt.year
            
            # Ταξινόμηση: Έτος -> Ταμείο -> Τύπος Ασφάλισης -> Από
            sort_cols = ['Έτος']
            if 'Ταμείο' in working_df.columns: sort_cols.append('Ταμείο')
            if 'Τύπος Ασφάλισης' in working_df.columns: sort_cols.append('Τύπος Ασφάλισης')
            sort_cols.append('_Από_dt')
            
            working_df = working_df.sort_values(sort_cols, na_position='last')
            
            # Αφαίρεση βοηθητικής στήλης
            if '_Από_dt' in working_df.columns:
                working_df = working_df.drop(columns=['_Από_dt'])

            # Ορισμός τελικών στηλών με το Έτος πρώτο
            all_columns = list(working_df.columns)
            if 'Έτος' in all_columns:
                all_columns.remove('Έτος')
                all_columns.insert(0, 'Έτος')
            
            # Προσθήκη στήλης "Μήνας" πριν το "Από"
            if 'Μήνας' not in all_columns:
                apo_idx = all_columns.index('Από') if 'Από' in all_columns else 1
                all_columns.insert(apo_idx, 'Μήνας')
            
            # Μετακίνηση "Ημέρες Ασφ." μετά το "Έως"
            if 'Ημέρες Ασφ.' in all_columns and 'Έως' in all_columns:
                all_columns.remove('Ημέρες Ασφ.')
                eos_idx = all_columns.index('Έως')
                all_columns.insert(eos_idx + 1, 'Ημέρες Ασφ.')

            # Προσθήκη στήλης "Συν. μήνα" μετά τις "Μικτές αποδοχές"
            if 'Συν. μήνα' not in all_columns:
                working_df['Συν. μήνα'] = ''
                if 'Μικτές αποδοχές' in all_columns:
                    gross_idx = all_columns.index('Μικτές αποδοχές')
                    all_columns.insert(gross_idx + 1, 'Συν. μήνα')
                else:
                    all_columns.append('Συν. μήνα')
            elif 'Συν. μήνα' in all_columns and 'Μικτές αποδοχές' in all_columns:
                 all_columns.remove('Συν. μήνα')
                 gross_idx = all_columns.index('Μικτές αποδοχές')
                 all_columns.insert(gross_idx + 1, 'Συν. μήνα')

            # Επαναδιάταξη του dataframe
            if 'Μήνας' not in working_df.columns: working_df['Μήνας'] = ''
            working_df = working_df[all_columns]
            
            final_frames = []

            def _sum_column(df_slice, column, exclude_drx=False):
                if column not in df_slice.columns:
                    return None
                total = 0.0
                has_value = False
                for value in df_slice[column]:
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        numeric_val = float(value)
                    else:
                        numeric_val = clean_numeric_value(value, exclude_drx=exclude_drx)
                    if numeric_val is None:
                        continue
                    total += numeric_val
                    has_value = True
                return total if has_value else None

            # Εύρεση στήλης Τύπου Αποδοχών για εξαίρεση 03, 04, 05
            earnings_col_name = next((c for c in working_df.columns if 'Τύπος Αποδοχών' in c), None)

            valid_years = sorted(working_df['Έτος'].dropna().unique())

            for year in valid_years:
                # Φιλτράρισμα έτους και δημιουργία αντιγράφου για επεξεργασία
                year_slice = working_df[working_df['Έτος'] == year].copy()
                
                # --- Υπολογισμός Μήνα και Ταξινόμηση ---
                def get_month_info(row):
                    # Λήψη ημερομηνίας (προτεραιότητα στο Έως για κατάταξη)
                    date_val = row.get('Έως')
                    if pd.isna(date_val) or str(date_val).strip() == '':
                        date_val = row.get('Από')
                    
                    try:
                        dt = pd.to_datetime(date_val, format='%d/%m/%Y')
                        month_num = dt.month
                    except:
                        month_num = 13 # Fallback
                    
                    # Έλεγχος για ειδικούς τύπους αποδοχών (Δώρα)
                    is_special = False
                    special_codes = ['03', '04', '05']
                    
                    if earnings_col_name:
                        code = str(row.get(earnings_col_name, '')).strip()
                        # Καθαρίζουμε τον κωδικό από πιθανή περιγραφή (π.χ. "10 - Bonus")
                        clean_code = code.split(' ')[0].strip()
                        
                        if clean_code in special_codes:
                            is_special = True
                        elif len(clean_code) >= 2 and clean_code[:2] in ['03', '04', '05']:
                             is_special = True
                    
                    if is_special:
                        # Αν είναι special (Δώρα/Bonus), τα βάζουμε στο τέλος του έτους (SortMonth=20)
                        # ώστε να εμφανίζονται μετά από όλους τους μήνες, ταξινομημένα με βάση το Priority
                        return 20, "" 
                    else:
                        return month_num, f"{month_num}ος"

                # Εφαρμογή υπολογισμού
                month_info = year_slice.apply(get_month_info, axis=1, result_type='expand')
                year_slice['_SortMonth'] = month_info[0]
                year_slice['Μήνας'] = month_info[1]
                
                year_slice['_SortDate'] = pd.to_datetime(year_slice['Από'], format='%d/%m/%Y', errors='coerce')

                # --- Υπολογισμός Priority Ταξινόμησης ---
                def get_sort_priority(row):
                    if not earnings_col_name: return 0
                    code = str(row.get(earnings_col_name, '')).strip()
                    clean_code = code.split(' ')[0].strip()
                    
                    special_codes = ['03', '04', '05']
                    
                    is_special = (clean_code in special_codes) or (len(clean_code) >= 2 and clean_code[:2] in ['03', '04', '05'])
                    
                    if not is_special:
                        if clean_code == '01': return -1 # Τακτικές Αποδοχές πρώτες
                        return 0
                    
                    if clean_code.startswith('03'): return 1
                    if clean_code.startswith('04'): return 2
                    if clean_code.startswith('05'): return 3
                    
                    return 4

                year_slice['_SortPriority'] = year_slice.apply(get_sort_priority, axis=1)

                # --- Υπολογισμός "Συν. μήνα" ---
                def get_gross(row):
                    return clean_numeric_value(row.get('Μικτές αποδοχές', 0), exclude_drx=True) or 0.0
                
                year_slice['_GrossFloat'] = year_slice.apply(get_gross, axis=1)
                
                # Αθροίσματα ανά μήνα (για τους μη κενούς μήνες)
                monthly_sums = year_slice[year_slice['Μήνας'] != ''].groupby('Μήνας')['_GrossFloat'].sum().to_dict()
                
                def calculate_monthly_total_col(row):
                    m = row.get('Μήνας')
                    if m and m != '':
                        return monthly_sums.get(m, 0.0)
                    else:
                        return row['_GrossFloat']
                
                year_slice['Συν. μήνα'] = year_slice.apply(calculate_monthly_total_col, axis=1)

                # --- NEW: Υπολογισμός Περικοπής/Συντ. Αποδοχών στο Σύνολο Μήνα ---
                
                # 1. Άθροισμα Εισφορών Μήνα (για το ποσοστό)
                def get_contrib(row):
                    return clean_numeric_value(row.get('Συνολικές εισφορές', 0), exclude_drx=True) or 0.0
                year_slice['_ContribFloat'] = year_slice.apply(get_contrib, axis=1)
                
                monthly_contrib_sums = year_slice[year_slice['Μήνας'] != ''].groupby('Μήνας')['_ContribFloat'].sum().to_dict()
                
                def calculate_monthly_contrib_total(row):
                    m = row.get('Μήνας')
                    if m and m != '':
                        return monthly_contrib_sums.get(m, 0.0)
                    else:
                        return row['_ContribFloat']
                
                year_slice['_MonthlyContribTotal'] = year_slice.apply(calculate_monthly_contrib_total, axis=1)
                
                # 2. Επαναϋπολογισμός Περικοπής, Συντ. Αποδοχών, % Κράτησης (με Δυναμικό Πλαφόν)
                
                # Προετοιμασία: Κωδικός και Ημέρες για υπολογισμό Πλαφόν
                def get_clean_code(row):
                    if not earnings_col_name: return ''
                    c = str(row.get(earnings_col_name, '')).strip()
                    return c.split(' ')[0].strip()
                year_slice['_Code'] = year_slice.apply(get_clean_code, axis=1)
                
                def get_days_num(row):
                    return clean_numeric_value(row.get('Ημέρες Ασφ.', 0)) or 0.0
                
                days_01_map = {}
                rows_01 = year_slice[year_slice['_Code'] == '01'].copy()
                if not rows_01.empty:
                    rows_01['_DaysNum'] = rows_01.apply(get_days_num, axis=1)
                    days_01_map = rows_01.groupby('Μήνας')['_DaysNum'].sum().to_dict()

                def recalc_financials(row):
                    monthly_gross = row.get('Συν. μήνα', 0.0)
                    monthly_contrib = row.get('_MonthlyContribTotal', 0.0)
                    
                    plaf = row.get('Εισφ. πλαφόν')
                    base_plaf_val = clean_numeric_value(plaf) if plaf is not None else None
                    
                    if base_plaf_val is None:
                        p = (monthly_contrib/monthly_gross if monthly_gross else 0)
                        return None, monthly_gross, p, None

                    # Υπολογισμός Δυναμικού Πλαφόν
                    final_plafond = base_plaf_val
                    m = row.get('Μήνας')
                    
                    # Αν είναι κανονικός μήνας (όχι κενός/special)
                    if m and m != "":
                        days_01 = days_01_map.get(m, 0)
                        if days_01 > 0:
                            days_capped = min(days_01, 25)
                            daily_plafond = base_plaf_val / 25.0
                            final_plafond = daily_plafond * days_capped
                        # else: Παραμένει το πλήρες (25/25)
                    
                    if monthly_gross > final_plafond:
                        cut = monthly_gross - final_plafond
                        adjusted = final_plafond
                    else:
                        cut = None
                        adjusted = monthly_gross
                    
                    percent = (monthly_contrib / adjusted) if adjusted and adjusted > 0 else 0.0
                    
                    return cut, adjusted, percent, final_plafond

                new_fin = year_slice.apply(recalc_financials, axis=1, result_type='expand')
                year_slice['Περικοπή'] = new_fin[0]
                year_slice['Συντ. Αποδοχές'] = new_fin[1]
                year_slice['Συν. % κράτησης'] = new_fin[2]
                year_slice['Εισφ. πλαφόν'] = new_fin[3]

                # Ταξινόμηση: Μήνας (SortMonth) -> Priority -> Ταμείο -> Από
                year_slice = year_slice.sort_values(['_SortMonth', '_SortPriority', 'Ταμείο', '_SortDate'], na_position='last')
                year_slice = year_slice.reset_index(drop=True)
                
                # Masking logic
                prev_month = None
                prev_tameio = None
                prev_ins_type = None
                
                processed_rows = []
                for idx, row in year_slice.iterrows():
                    new_row = row.copy()
                    
                    # Έτος
                    if idx > 0:
                        new_row['Έτος'] = ''
                    else:
                        try:
                            new_row['Έτος'] = str(int(year))
                        except:
                            new_row['Έτος'] = str(year)
                    
                    # Μήνας masking
                    curr_month = row.get('Μήνας')
                    is_month_hidden = False
                    
                    if curr_month: 
                        if idx > 0 and curr_month == prev_month:
                            new_row['Μήνας'] = ''
                            is_month_hidden = True
                        else:
                            prev_month = curr_month
                    else:
                        # Αν είναι Bonus (κενός μήνας), δεν αλλάζουμε το prev_month.
                        # Έτσι διατηρούμε τη συνέχεια του "3ος" μήνα πριν και μετά το Bonus.
                        pass
                    
                    # Συν. μήνα & Financials masking
                    if is_month_hidden:
                        new_row['Συν. μήνα'] = ''
                        new_row['Περικοπή'] = ''
                        new_row['Συντ. Αποδοχές'] = ''
                        new_row['Συν. % κράτησης'] = ''
                        new_row['Εισφ. πλαφόν'] = ''

                    # Ταμείο
                    curr_tameio = row.get('Ταμείο')
                    if idx > 0 and curr_tameio == prev_tameio:
                         new_row['Ταμείο'] = ''
                    else:
                        prev_tameio = curr_tameio
                    
                    # Τύπος Ασφάλισης
                    curr_ins_type = row.get('Τύπος Ασφάλισης')
                    if idx > 0 and curr_ins_type == prev_ins_type:
                        new_row['Τύπος Ασφάλισης'] = ''
                    else:
                        prev_ins_type = curr_ins_type
                    
                    processed_rows.append(new_row)
                
                # Cleanup
                proc_df = pd.DataFrame(processed_rows)
                for col in ['_SortMonth', '_SortDate', '_GrossFloat', '_ContribFloat', '_MonthlyContribTotal', '_SortPriority', '_Code', '_DaysNum']:
                    if col in proc_df.columns:
                        proc_df = proc_df.drop(columns=[col])
                
                final_frames.append(proc_df)

                # Γραμμή Συνόλων
                year_int = int(year)
                if year_int >= 2002:
                    totals_row = {col: '' for col in all_columns}
                    # Καθαρισμός ετικετών
                    if 'Από' in totals_row: totals_row['Από'] = ''
                    if 'Έως' in totals_row: totals_row['Έως'] = ''
                    
                    if 'Μήνας' in totals_row:
                        totals_row['Μήνας'] = f"Σύνολο {year_int}"
                    elif 'Έως' in totals_row:
                        totals_row['Έως'] = f"Σύνολο {year_int}"
                    elif 'Από' in totals_row:
                        totals_row['Από'] = f"Σύνολο {year_int}"

                    # Υπολογισμός αθροισμάτων (από το masked dataframe)
                    days_total = _sum_column(proc_df, 'Ημέρες Ασφ.')
                    gross_sum = _sum_column(proc_df, 'Μικτές αποδοχές', exclude_drx=True)
                    adjusted_sum = _sum_column(proc_df, 'Συντ. Αποδοχές', exclude_drx=True)
                    cut_sum = _sum_column(proc_df, 'Περικοπή', exclude_drx=True)
                    
                    if days_total is not None: totals_row['Ημέρες Ασφ.'] = days_total
                    if gross_sum is not None: 
                        totals_row['Μικτές αποδοχές'] = gross_sum
                        totals_row['Συν. μήνα'] = gross_sum 
                    if adjusted_sum is not None: totals_row['Συντ. Αποδοχές'] = adjusted_sum
                    if cut_sum is not None: totals_row['Περικοπή'] = cut_sum

                    if 'Συν. % κράτησης' in totals_row:
                        totals_row['Συν. % κράτησης'] = ''

                    final_frames.append(pd.DataFrame([totals_row], columns=all_columns))
                
                # Κενή γραμμή διαχωρισμού
                empty_row = {col: '' for col in all_columns}
                final_frames.append(pd.DataFrame([empty_row], columns=all_columns))

            remainder = working_df[working_df['Έτος'].isna()]
            if not remainder.empty:
                remainder = remainder[all_columns]
                final_frames.append(remainder)

            if final_frames:
                display_apd_df = pd.concat(final_frames, ignore_index=True)
            else:
                display_apd_df = working_df[all_columns].reset_index(drop=True)

        # Αν ο διακόπτης είναι ενεργός, κρατάμε μόνο τις γραμμές «Σύνολο <Έτος>»
        if st.session_state.get('apd_year_totals_only', False):
            try:
                total_mask = False
                # Ψάχνουμε τη λέξη "Σύνολο" κυρίως στη στήλη Μήνας (νέα θέση), αλλά και Έως/Από για ασφάλεια
                for col_name in ['Μήνας', 'Έως', 'Από']:
                    if col_name in display_apd_df.columns:
                        mask = display_apd_df[col_name].astype(str).str.startswith('Σύνολο')
                        if isinstance(total_mask, bool) and not total_mask:
                            total_mask = mask
                        else:
                            total_mask = total_mask | mask
                
                if not isinstance(total_mask, bool): # Αν βρήκαμε κάτι
                    display_apd_df = display_apd_df[total_mask]
                    data_rows_count = len(display_apd_df)
            except Exception:
                pass

        # Ενημέρωση πληροφοριακού μηνύματος για το πλήθος γραμμών
        filtered_count = initial_count - data_rows_count
        stats_msg = f"Εμφανίζονται **{data_rows_count}** γραμμές"
        
        if filtered_count > 0:
            stats_msg += f" • ⚠️ **{filtered_count}** έχουν φιλτραριστεί"
            stats_placeholder.warning(stats_msg)
        else:
            stats_placeholder.info(stats_msg)

        # Κρατάμε αντίγραφο πριν τη μορφοποίηση για τις εξαγωγές Excel
        apd_export_df = display_apd_df.copy()

        # Εφαρμόζουμε μορφοποίηση νομισμάτων μόνο για εμφάνιση
        currency_columns = ['Μικτές αποδοχές', 'Συν. μήνα', 'Συνολικές εισφορές', 'Εισφ. πλαφόν', 'Περικοπή', 'Συντ. Αποδοχές']
        for col in currency_columns:
            if col in display_apd_df.columns:
                display_apd_df[col] = display_apd_df[col].apply(format_currency)
        
        # Μορφοποίηση ποσοστού
        if 'Συν. % κράτησης' in display_apd_df.columns:
            def format_retention_value(val):
                if isinstance(val, (int, float)) and not pd.isna(val):
                    return f"{val:.1%}".replace('.', ',')
                if pd.isna(val) or val is None:
                    return ''
                if isinstance(val, str):
                    stripped = val.strip()
                    if stripped == '':
                        return ''
                    try:
                        num_val = float(stripped)
                        return f"{num_val:.1%}".replace('.', ',')
                    except ValueError:
                        return stripped
                return "0,0%"

            display_apd_df['Συν. % κράτησης'] = display_apd_df['Συν. % κράτησης'].apply(format_retention_value)

        # Function for conditional formatting
        def highlight_low_retention(row):
            styles = [''] * len(row)
            
            # Check for Total rows
            is_total = False
            for label_col in ['Μήνας', 'Έως', 'Από']:
                label_value = row.get(label_col)
                if isinstance(label_value, str) and label_value.startswith('Σύνολο'):
                    is_total = True
                    break
            
            if is_total:
                return ['background-color: #e6f2ff; color: #000000; font-weight: 700;'] * len(row)

            # Check for Low Retention
            retention_str = row.get('Συν. % κράτησης', '0,0%').replace('%', '').replace(',', '.')
            try:
                retention_val = float(retention_str)
                if retention_val < highlight_threshold:
                    styles = ['background-color: #fff8e1'] * len(row)
            except (ValueError, TypeError):
                pass
            
            for i, col_name in enumerate(row.index):
                # Apply Bold to 'Έτος' and 'Ταμείο'
                if col_name in ['Έτος', 'Ταμείο']:
                    if styles[i]:
                        styles[i] += '; font-weight: 700;'
                    else:
                        styles[i] = 'font-weight: 700;'
                
                # Apply Bold Red to 'Περικοπή'
                if col_name == 'Περικοπή':
                    val = row.get(col_name)
                    if val and str(val).strip() != '':
                        style_add = 'color: #d9534f; font-weight: 700;'
                        if styles[i]:
                            styles[i] += f'; {style_add}'
                        else:
                            styles[i] = style_add
            
            return styles

        # Apply styling
        register_view("Ανάλυση ΑΠΔ", display_apd_df)
        styled_df = display_apd_df.style.apply(highlight_low_retention, axis=1)

        # Εφαρμόζουμε ελληνική μορφοποίηση για αριθμητικές στήλες
        numeric_columns = ['Ημερολογιακές ημέρες', 'Ημέρες Ασφ.', 'Ημέρες', 'Μήνες', 'Έτη']
        for col in numeric_columns:
            if col in display_apd_df.columns:
                # Μήνες και Έτη με 1 δεκαδικό, ημέρες χωρίς δεκαδικά
                decimals = 1 if col in ['Μήνες', 'Έτη'] else 0
                
                def fmt_num(x):
                    if pd.isna(x) or x == '':
                        return x
                    try:
                        val = float(x)
                        if val == 0:  # Κρύβουμε το μηδέν
                            return ""
                        return format_number_greek(val, decimals=decimals)
                    except:
                        return x

                display_apd_df[col] = display_apd_df[col].apply(fmt_num)
        
        st.markdown("### Ανάλυση ΑΠΔ (Με χρονολογική σειρά)")
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        # Κουμπί εκτύπωσης για Ανάλυση ΑΠΔ
        # Αφαιρούμε τις στήλες 'Από' και 'Έως' για την εκτύπωση
        print_df = display_apd_df.copy()
        cols_to_drop = [c for c in ['Από', 'Έως'] if c in print_df.columns]
        if cols_to_drop:
            print_df = print_df.drop(columns=cols_to_drop)

        render_print_button(
            "print_apd",
            "Ανάλυση ΑΠΔ",
            print_df,
            description="Ανάλυση εγγραφών ΑΠΔ με υπολογισμό εισφ. πλαφόν ΙΚΑ, περικοπής λόγω πλαφόν και ποσοστού κράτησης για τον εντοπισμό των πραγματικών εισφορίσιμων αποδοχών."
        )

    with tab_count:
        st.markdown("### Καταμέτρηση Ημερών Ασφάλισης")
        info_col, warn_col = st.columns([2, 2])
        with info_col:
            st.info("Αναλυτική καταμέτρηση ημερών ανά έτος, ταμείο, εργοδότη και μήνα.")
        with warn_col:
            st.warning("Διαστήματα που καλύπτουν πολλαπλούς μήνες επιμερίζονται και επισημαίνονται με κίτρινο χρώμα.")

        count_df = df.copy()
        required_cols = ['Από', 'Έως', 'Ημέρες']
        
        if all(col in count_df.columns for col in required_cols):
            # --- Filters Section for Counting Tab ---
            with st.container():
                # Όλα τα φίλτρα σε μία γραμμή
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1.1, 1.0, 1.2, 1.3, 1.1, 0.9, 0.9])
                
                with col1:
                    # Φίλτρο Ταμείου
                    if 'Ταμείο' in count_df.columns:
                        tameia_options = sorted(count_df['Ταμείο'].dropna().unique().tolist())
                        sel_cnt_tameia = st.multiselect(
                            "Ταμείο:",
                            options=tameia_options,
                            default=[],
                            key="cnt_filter_tameio",
                            placeholder=""
                        )
                        if sel_cnt_tameia:
                            count_df = count_df[count_df['Ταμείο'].isin(sel_cnt_tameia)]

                with col2:
                    # Φίλτρο Τύπου Ασφάλισης
                    if 'Τύπος Ασφάλισης' in count_df.columns:
                        typos_options = sorted(count_df['Τύπος Ασφάλισης'].dropna().astype(str).unique().tolist())
                        
                        sel_cnt_typos = st.multiselect(
                            "Τύπος Ασφάλισης:",
                            options=typos_options,
                            default=[],
                            key="cnt_filter_insurance_type",
                            placeholder=""
                        )
                        if sel_cnt_typos:
                            count_df = count_df[count_df['Τύπος Ασφάλισης'].astype(str).isin(sel_cnt_typos)]

                with col3:
                    # Φίλτρο Εργοδότη
                    if 'Α-Μ εργοδότη' in count_df.columns:
                        employer_options = sorted(count_df['Α-Μ εργοδότη'].dropna().astype(str).unique().tolist())
                        sel_cnt_employer = st.multiselect(
                            "Α-Μ Εργοδότη:",
                            options=employer_options,
                            default=[],
                            key="cnt_filter_employer",
                            placeholder=""
                        )
                        if sel_cnt_employer:
                            count_df = count_df[count_df['Α-Μ εργοδότη'].astype(str).isin(sel_cnt_employer)]
                
                with col4:
                    # Φίλτρο Κλάδου/Πακέτου
                    if 'Κλάδος/Πακέτο Κάλυψης' in count_df.columns:
                        klados_codes = sorted(count_df['Κλάδος/Πακέτο Κάλυψης'].dropna().unique().tolist())
                        klados_opts = []
                        klados_map = {}
                        for code in klados_codes:
                            if 'description_map' in locals() and code in description_map:
                                lbl = f"{code} - {description_map[code]}"
                                klados_opts.append(lbl)
                                klados_map[lbl] = code
                            else:
                                klados_opts.append(code)
                                klados_map[code] = code
                        
                        sel_cnt_klados = st.multiselect(
                            "Κλάδος/Πακέτο:",
                            options=klados_opts,
                            default=[],
                            key="cnt_filter_klados",
                            placeholder=""
                        )
                        if sel_cnt_klados:
                            sel_codes = [klados_map.get(o, o) for o in sel_cnt_klados]
                            count_df = count_df[count_df['Κλάδος/Πακέτο Κάλυψης'].isin(sel_codes)]
                
                with col5:
                    # Φίλτρο Τύπου Αποδοχών
                    e_col = next((c for c in count_df.columns if 'Τύπος Αποδοχών' in c), None)
                    if e_col:
                        earn_opts = sorted(count_df[e_col].dropna().astype(str).unique().tolist())
                        sel_cnt_earn = st.multiselect(
                            "Τύπος Αποδοχών:",
                            options=earn_opts,
                            default=[],
                            key="cnt_filter_earnings",
                            placeholder=""
                        )
                        if sel_cnt_earn:
                            count_df = count_df[count_df[e_col].astype(str).isin(sel_cnt_earn)]

                with col6:
                    from_date_cnt = st.text_input("Από (dd/mm/yyyy):", value="", placeholder="01/01/2000", key="cnt_filter_from")
                with col7:
                    to_date_cnt = st.text_input("Έως (dd/mm/yyyy):", value="", placeholder="31/12/2020", key="cnt_filter_to")
                
                # Apply date filters
                if from_date_cnt or to_date_cnt:
                    count_df['_dt'] = pd.to_datetime(count_df['Από'], format='%d/%m/%Y', errors='coerce')
                    if from_date_cnt:
                        try:
                            fd = pd.to_datetime(from_date_cnt, format='%d/%m/%Y')
                            count_df = count_df[count_df['_dt'] >= fd]
                        except: st.error("Λάθος μορφή ημερομηνίας 'Από'")
                    if to_date_cnt:
                        try:
                            td = pd.to_datetime(to_date_cnt, format='%d/%m/%Y')
                            count_df = count_df[count_df['_dt'] <= td]
                        except: st.error("Λάθος μορφή ημερομηνίας 'Έως'")
            
            show_count_totals_only = st.toggle(
                "Μόνο γραμμές συνόλου ανά έτος",
                value=False,
                key="count_totals_only"
            )

            counting_rows = []
            
            with st.spinner("Υπολογισμός κατανομής ημερών..."):
                def _get_num(val):
                    try:
                        return clean_numeric_value(val) or 0
                    except Exception:
                        return 0

                def _is_expected_oaee(r, duration_days):
                    tam = str(r.get('Ταμείο', '')).upper()
                    if 'ΟΑΕΕ' not in tam:
                        return False
                    months_val = _get_num(r.get('Μήνες'))
                    days_val = _get_num(r.get('Ημέρες'))
                    # Αναμενόμενα βραχύχρονα διαστήματα (έως 2 μήνες ~25 ημέρες/μήνα)
                    if months_val and months_val <= 2:
                        if days_val and abs(days_val - months_val * 25) <= 1:
                            return True
                        if not days_val and duration_days <= 62:
                            return True
                    return False

                def _is_expected_tsm(r, duration_days, start_dt, end_dt):
                    tam = str(r.get('Ταμείο', '')).upper()
                    if 'ΤΣΜΕΔΕ' not in tam:
                        return False
                    months_val = _get_num(r.get('Μήνες'))
                    days_val = _get_num(r.get('Ημέρες'))
                    if pd.notna(start_dt) and pd.notna(end_dt) and start_dt.year == end_dt.year:
                        sem1 = (start_dt.month == 1 and end_dt.month == 6)
                        sem2 = (start_dt.month == 7 and end_dt.month == 12)
                        if sem1 or sem2:
                            # 6μηνα με ~25 ημέρες/μήνα θεωρούνται αναμενόμενα
                            if months_val == 6 and (not days_val or abs(days_val - 150) <= 2):
                                return True
                            if not months_val and 150 <= duration_days <= 190:
                                return True
                    return False

                for idx, row in count_df.iterrows():
                    try:
                        if pd.isna(row['Από']) or pd.isna(row['Έως']):
                            continue
                            
                        start_dt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
                        end_dt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')
                        
                        if pd.isna(start_dt) or pd.isna(end_dt):
                            continue
                            
                        duration_days = (end_dt - start_dt).days + 1
                        is_pre2002 = end_dt < pd.Timestamp('2002-01-01')
                        expected_agg_pattern = _is_expected_oaee(row, duration_days) or _is_expected_tsm(row, duration_days, start_dt, end_dt)
                            
                        # Calculation logic for total days
                        # Priority: Days column -> Years/Months/Days columns conversion
                        days_val = 0
                        
                        has_explicit_days = False
                        if 'Ημέρες' in row and pd.notna(row['Ημέρες']) and str(row['Ημέρες']).strip() != '':
                             d = clean_numeric_value(row['Ημέρες'])
                             # Allow negative values (corrective entries)
                             if d is not None and d != 0:
                                 days_val += d
                                 has_explicit_days = True
                        
                        # If we have years/months columns, add them converted
                        if 'Έτη' in row and pd.notna(row['Έτη']):
                             y = clean_numeric_value(row['Έτη'])
                             if y is not None and y != 0:
                                 days_val += y * 300
                                 has_explicit_days = True
                        
                        if 'Μήνες' in row and pd.notna(row['Μήνες']):
                             m = clean_numeric_value(row['Μήνες'])
                             if m is not None and m != 0:
                                 days_val += m * 25
                                 has_explicit_days = True
                        
                        # Parse amounts (Gross Earnings & Contributions) - ONLY EURO
                        # Strict check for Drachmas to exclude them from summation
                        raw_gross = str(row.get('Μικτές αποδοχές', ''))
                        if 'ΔΡΧ' in raw_gross.upper() or 'DRX' in raw_gross.upper():
                            gross_val = 0.0
                        else:
                            gross_val = clean_numeric_value(raw_gross, exclude_drx=True)
                        if gross_val is None: gross_val = 0.0
                        
                        raw_contrib = str(row.get('Συνολικές εισφορές', ''))
                        if 'ΔΡΧ' in raw_contrib.upper() or 'DRX' in raw_contrib.upper():
                            contrib_val = 0.0
                        else:
                            contrib_val = clean_numeric_value(raw_contrib, exclude_drx=True)
                        if contrib_val is None: contrib_val = 0.0

                        sign = get_negative_amount_sign(gross_val, contrib_val)
                        if sign == -1:
                            days_val = -abs(days_val)
                        
                        # Keys
                        tameio = str(row.get('Ταμείο', '')).strip()
                        insurance_type = str(row.get('Τύπος Ασφάλισης', '')).strip()
                        employer = str(row.get('Α-Μ εργοδότη', '')).strip()
                        klados = str(row.get('Κλάδος/Πακέτο Κάλυψης', '')).strip()
                        klados_desc = description_map.get(klados, '') if 'description_map' in locals() else ''
                        earnings_type = str(row.get('Τύπος Αποδοχών', '')).strip()
                        
                        # Generate month list
                        curr = start_dt.replace(day=1)
                        end_month_dt = end_dt.replace(day=1)
                        
                        months_list = []
                        while curr <= end_month_dt:
                            months_list.append(curr)
                            if curr.month == 12:
                                curr = curr.replace(year=curr.year + 1, month=1)
                            else:
                                curr = curr.replace(month=curr.month + 1)
                        
                        num_months = len(months_list)
                        if num_months == 0: continue
                        
                        days_per_month = days_val / num_months
                        gross_per_month = gross_val / num_months
                        contrib_per_month = contrib_val / num_months
                        is_aggregate = (num_months > 1) and is_pre2002 and (duration_days > 31) and not expected_agg_pattern
                        
                        for m_dt in months_list:
                            counting_rows.append({
                                'ΕΤΟΣ': m_dt.year,
                                'ΤΑΜΕΙΟ': tameio,
                                'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': insurance_type,
                                'ΕΡΓΟΔΟΤΗΣ': employer,
                                'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': klados,
                                'ΠΕΡΙΓΡΑΦΗ': klados_desc,
                                'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': earnings_type,
                                'Μήνας_Num': m_dt.month,
                                'Ημέρες': days_per_month,
                                'Μικτές_Part': gross_per_month,
                                'Εισφορές_Part': contrib_per_month,
                                'Is_Aggregate': is_aggregate
                            })
                            
                    except Exception:
                        continue

            if counting_rows:
                c_df = pd.DataFrame(counting_rows)
                
                # Calculate annual totals for Days, Gross, Contrib
                annual_totals = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'])[['Ημέρες', 'Μικτές_Part', 'Εισφορές_Part']].sum().reset_index()
                annual_totals.rename(columns={
                    'Ημέρες': 'ΣΥΝΟΛΟ',
                    'Μικτές_Part': 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ',
                    'Εισφορές_Part': 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'
                }, inplace=True)

                pivot_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Ημέρες'].sum().reset_index()
                agg_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Is_Aggregate'].max().reset_index()
                contrib_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Εισφορές_Part'].sum().reset_index()
                
                # Create Pivot Tables
                final_val = pivot_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Ημέρες').fillna(0)
                final_agg = agg_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Is_Aggregate').fillna(False)
                final_contrib = contrib_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Εισφορές_Part').fillna(0)
                
                # Join with annual totals
                final_val = final_val.reset_index()
                final_val = final_val.merge(annual_totals, on=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], how='left')
                final_val.set_index(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], inplace=True)
                final_contrib = final_contrib.reindex(final_val.index)
                
                # Ensure all months 1-12 exist
                for m in range(1, 13):
                    if m not in final_val.columns:
                        final_val[m] = 0
                    if m not in final_agg.columns:
                        final_agg[m] = False
                    if m not in final_contrib.columns:
                        final_contrib[m] = 0
                
                # Reorder columns: Keys | ΣΥΝΟΛΟ | 1..12 | MIKTES | EISFORES
                month_cols_int = sorted([c for c in final_val.columns if isinstance(c, int)])
                final_val = final_val[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ']]
                
                # Calculate contribution percentage (per row)
                if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in final_val.columns and 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in final_val.columns:
                    final_val['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = pd.NA
                    gross_series = final_val['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
                    valid_mask = gross_series.notna() & (gross_series != 0)
                    ratios = (
                        final_val.loc[valid_mask, 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] /
                        final_val.loc[valid_mask, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
                    ) * 100
                    final_val.loc[valid_mask, 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ratios
                    final_val = final_val[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']]
                
                # Rename columns to 1ος, 2ος...
                month_map = {m: f"{m}ος" for m in range(1, 13)}
                final_val = final_val.rename(columns=month_map)
                final_agg = final_agg.rename(columns=month_map)
                final_contrib = final_contrib.rename(columns=month_map)
                month_cols = list(month_map.values())
                
                # Sort by Year Ascending (Oldest First)
                final_val = final_val.sort_values('ΕΤΟΣ', ascending=True)
                final_agg = final_agg.reindex(final_val.index)
                final_contrib = final_contrib.reindex(final_val.index)
                
                # Prepare display dataframe
                display_cnt_df = final_val.reset_index()
                mask_cnt_df = final_agg.reset_index()
                contrib_cnt_df = final_contrib.reset_index()

                # Insert gap rows for missing years (with "ΚΕΝΟ ΔΙΑΣΤΗΜΑ")
                if not display_cnt_df.empty:
                    try:
                        min_year = int(display_cnt_df['ΕΤΟΣ'].min())
                        max_year = int(display_cnt_df['ΕΤΟΣ'].max())
                        existing_years = set(display_cnt_df['ΕΤΟΣ'].dropna().astype(int).tolist())
                        missing_years = [y for y in range(min_year, max_year + 1) if y not in existing_years]
                    except Exception:
                        missing_years = []
                    if missing_years:
                        filler_rows = []
                        filler_masks = []
                        block_rows_list = []
                        for missing_year in missing_years:
                            row_template = {col: '' for col in display_cnt_df.columns}
                            row_template['ΕΤΟΣ'] = missing_year
                            row_template['ΤΑΜΕΙΟ'] = "ΚΕΝΟ ΔΙΑΣΤΗΜΑ"
                            for c in month_cols:
                                if c in row_template:
                                    row_template[c] = 0
                            if 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ' in row_template:
                                row_template['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = ''
                            for c in ['ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']:
                                if c in row_template:
                                    row_template[c] = 0
                            filler_rows.append(row_template)

                            mask_template = {}
                            for col in mask_cnt_df.columns:
                                if col == 'ΕΤΟΣ':
                                    mask_template[col] = missing_year
                                elif col == 'ΤΑΜΕΙΟ':
                                    mask_template[col] = "ΚΕΝΟ ΔΙΑΣΤΗΜΑ"
                                elif col == 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ':
                                    mask_template[col] = ''
                                elif col in ['ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']:
                                    mask_template[col] = ''
                                else:
                                    mask_template[col] = False
                            filler_masks.append(mask_template)

                            contrib_template = {}
                            for col in contrib_cnt_df.columns:
                                if col == 'ΕΤΟΣ':
                                    contrib_template[col] = missing_year
                                elif col == 'ΤΑΜΕΙΟ':
                                    contrib_template[col] = "ΚΕΝΟ ΔΙΑΣΤΗΜΑ"
                                elif col == 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ':
                                    contrib_template[col] = ''
                                elif col in ['ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']:
                                    contrib_template[col] = ''
                                else:
                                    contrib_template[col] = 0
                            block_rows_list.append(contrib_template)

                        display_cnt_df = pd.concat([display_cnt_df, pd.DataFrame(filler_rows)], ignore_index=True)
                        mask_cnt_df = pd.concat([mask_cnt_df, pd.DataFrame(filler_masks)], ignore_index=True)
                        contrib_cnt_df = pd.concat([contrib_cnt_df, pd.DataFrame(block_rows_list)], ignore_index=True)

                    sort_keys = ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']
                    display_cnt_df = display_cnt_df.sort_values(sort_keys, na_position='first').reset_index(drop=True)
                    mask_cnt_df = mask_cnt_df.sort_values(sort_keys, na_position='first').reset_index(drop=True)
                    contrib_cnt_df = contrib_cnt_df.sort_values(sort_keys, na_position='first').reset_index(drop=True)

                # Pre-calculate yearly totals for gross/contributions (unformatted values)
                year_totals = {}
                if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in display_cnt_df.columns or 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in display_cnt_df.columns:
                    sum_cols = [col for col in ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] if col in display_cnt_df.columns]
                    if sum_cols:
                        year_totals = (
                            display_cnt_df.groupby('ΕΤΟΣ')[sum_cols]
                            .sum()
                            .to_dict('index')
                        )
                
                # Format numbers
                def format_cell_days(val):
                    if val == 0: return ""
                    if abs(val - round(val)) < 0.01: return str(int(round(val)))
                    return f"{val:.1f}".replace('.', ',')
                
                # Reuse format_currency for amounts
                def format_amount_cell(val):
                    if val == 0: return ""
                    return format_currency(val)
                
                def format_percent_cell(val):
                    if pd.isna(val): return ""
                    try:
                        if float(val) == 0: return ""
                        return f"{float(val):.1f}%".replace('.', ',')
                    except Exception:
                        return ""

                formatted_df = display_cnt_df.copy()
                last_month_col = month_cols[-1] if month_cols else None
                
                # Format Days columns (Months + Total Days)
                for col in month_cols + ['ΣΥΝΟΛΟ']:
                    if col in formatted_df.columns:
                        formatted_df[col] = formatted_df[col].apply(format_cell_days)
                
                # Format Amount columns
                for col in ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ']:
                    if col in formatted_df.columns:
                        formatted_df[col] = formatted_df[col].apply(format_amount_cell)
                
                # Format Percentage column
                if 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ' in formatted_df.columns:
                    formatted_df['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = formatted_df['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'].apply(format_percent_cell)
                
                # Helper for mask rows (used for totals/empty rows)
                def make_mask_row(is_total=False):
                    mask = {m: False for m in month_cols}
                    mask['__is_total__'] = is_total
                    return mask

                # Hide repeating values
                processed_rows = []
                processed_mask_rows = []
                contrib_rows = contrib_cnt_df.to_dict('records') if not contrib_cnt_df.empty else []
                
                prev_year = None
                prev_tameio = None
                prev_insurance_type = None
                prev_employer = None
                
                # Columns structure
                base_cols = ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']
                all_cols = base_cols + ['ΣΥΝΟΛΟ'] + month_cols + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']
                
                for idx, row in formatted_df.iterrows():
                    curr_year = row['ΕΤΟΣ']
                    curr_tameio = row['ΤΑΜΕΙΟ']
                    curr_insurance_type = row['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ']
                    curr_employer = row['ΕΡΓΟΔΟΤΗΣ']
                    
                    # Check if year changed (and not the first row) -> Insert totals + empty row
                    if prev_year is not None and curr_year != prev_year:
                        total_row = {c: '' for c in all_cols}
                        total_row['ΕΤΟΣ'] = ''
                        if last_month_col:
                            total_row[last_month_col] = f"ΣΥΝΟΛΟ {prev_year}"
                        totals_vals = year_totals.get(prev_year, {})
                        if totals_vals:
                            gross_total = totals_vals.get('ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 0)
                            contrib_total = totals_vals.get('ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 0)
                            if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in total_row:
                                total_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = format_amount_cell(gross_total)
                            if 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in total_row:
                                total_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = format_amount_cell(contrib_total)
                            if 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ' in total_row:
                                total_row['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ''
                        processed_rows.append(total_row)
                        processed_mask_rows.append(make_mask_row(is_total=True))

                        empty_row = {c: '' for c in all_cols}
                        processed_rows.append(empty_row)
                        processed_mask_rows.append(make_mask_row()) 
                        
                        prev_tameio = None 
                        prev_insurance_type = None
                        prev_employer = None

                    display_row = row.to_dict()
                    
                    # Hide Year if same as previous
                    if curr_year == prev_year:
                        display_row['ΕΤΟΣ'] = ''
                    
                    # Hide Tameio if same as previous AND same Year & τ. ασφάλισης
                    if curr_year == prev_year and curr_tameio == prev_tameio and curr_insurance_type == prev_insurance_type:
                        display_row['ΤΑΜΕΙΟ'] = ''

                    # Hide Τύπο Ασφάλισης if repeating within ίδιο Ταμείο και έτος
                    if curr_year == prev_year and curr_tameio == prev_tameio and curr_insurance_type == prev_insurance_type:
                        display_row['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = ''
                        
                    # Hide Employer if same as previous AND same Year AND same Tameio
                    if curr_year == prev_year and curr_tameio == prev_tameio and curr_insurance_type == prev_insurance_type and curr_employer == prev_employer:
                        display_row['ΕΡΓΟΔΟΤΗΣ'] = ''
                        
                    processed_rows.append(display_row)
                    
                    # Get mask row
                    mask_row = mask_cnt_df.loc[idx].to_dict()
                    mask_row['__is_total__'] = False
                    processed_mask_rows.append(mask_row)

                    # Αν πρόκειται για κωδικό κλάδου/πακέτου ΚΣ, Κ, ΜΕ, ΠΚΣ, προσθέτουμε γραμμή εισφορών ανά μήνα
                    try:
                        curr_row = display_cnt_df.loc[idx].to_dict() if idx < len(display_cnt_df) else {}
                        curr_key = (
                            curr_row.get('ΕΤΟΣ'),
                            curr_row.get('ΤΑΜΕΙΟ', ''),
                            curr_row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', ''),
                            curr_row.get('ΕΡΓΟΔΟΤΗΣ', ''),
                            curr_row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', ''),
                            curr_row.get('ΠΕΡΙΓΡΑΦΗ', ''),
                            curr_row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')
                        )
                        contrib_lookup = {
                            (
                                r.get('ΕΤΟΣ'),
                                r.get('ΤΑΜΕΙΟ', ''),
                                r.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', ''),
                                r.get('ΕΡΓΟΔΟΤΗΣ', ''),
                                r.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', ''),
                                r.get('ΠΕΡΙΓΡΑΦΗ', ''),
                                r.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')
                            ): r for r in contrib_rows
                        }

                        def _matches_target(code_val):
                            code_upper = str(code_val).upper()
                            tokens = re.split(r'[^A-ZΑ-Ω0-9]+', code_upper)
                            target_set = {'ΚΣ', 'Κ', 'ΜΕ', 'ΠΚΣ', 'ΕΙΠΡ', 'ΕΦΑΠ', 'ΕΠΙΚ', 'Ε'}
                            return any(tok in target_set for tok in tokens if tok)

                        if _matches_target(curr_row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')):
                            c_row = contrib_lookup.get(curr_key, {})
                            has_amount = False
                            contrib_display = {col: '' for col in display_cnt_df.columns}
                            for m_col in month_cols:
                                if m_col in c_row and c_row[m_col]:
                                    contrib_display[m_col] = format_currency(c_row[m_col])
                                    has_amount = True
                            if has_amount:
                                contrib_display.update({
                                        'ΕΤΟΣ': '',
                                        'ΤΑΜΕΙΟ': '',
                                        'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': '',
                                        'ΕΡΓΟΔΟΤΗΣ': curr_row.get('ΕΡΓΟΔΟΤΗΣ', ''),
                                        'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': curr_row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', ''),
                                        'ΠΕΡΙΓΡΑΦΗ': 'Εισφορές μήνα',
                                        'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': curr_row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', ''),
                                        'ΣΥΝΟΛΟ': '',
                                        'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ': '',
                                        'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ': '',
                                        'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ': ''
                                    })
                                processed_rows.append(contrib_display)
                                # Μάσκα χωρίς highlights
                                empty_mask = {m: False for m in month_cols}
                                empty_mask['__is_total__'] = False
                                processed_mask_rows.append(empty_mask)
                    except Exception:
                        pass
                    
                    prev_year = curr_year
                    prev_tameio = curr_tameio
                    prev_insurance_type = curr_insurance_type
                    prev_employer = curr_employer
                
                # Append totals & empty row for last year
                if prev_year is not None:
                    total_row = {c: '' for c in all_cols}
                    total_row['ΕΤΟΣ'] = ''
                    if last_month_col:
                        total_row[last_month_col] = f"ΣΥΝΟΛΟ {prev_year}"
                    totals_vals = year_totals.get(prev_year, {})
                    if totals_vals:
                        gross_total = totals_vals.get('ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 0)
                        contrib_total = totals_vals.get('ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 0)
                        if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in total_row:
                            total_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = format_amount_cell(gross_total)
                        if 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in total_row:
                            total_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = format_amount_cell(contrib_total)
                        if 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ' in total_row:
                            total_row['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ''
                    processed_rows.append(total_row)
                    processed_mask_rows.append(make_mask_row(is_total=True))

                    processed_rows.append({c: '' for c in all_cols})
                    processed_mask_rows.append(make_mask_row())

                final_display_df = pd.DataFrame(processed_rows, columns=all_cols)
                masks_df = pd.DataFrame(processed_mask_rows)
                if not masks_df.empty:
                    masks_df = masks_df.reset_index(drop=True)
                else:
                    masks_df = pd.DataFrame({'__is_total__': []})
                
                if show_count_totals_only:
                    try:
                        total_mask = masks_df['__is_total__'].fillna(False)
                        final_display_df = final_display_df[total_mask].reset_index(drop=True)
                        masks_df = masks_df[total_mask].reset_index(drop=True)
                    except Exception:
                        pass
                else:
                    final_display_df = final_display_df.reset_index(drop=True)
                    masks_df = masks_df.reset_index(drop=True)
                
                active_mask_rows = masks_df.to_dict('records') if not masks_df.empty else []
                
                # Styling
                def highlight_aggs(row):
                    if row.name < len(active_mask_rows):
                        mask_row = active_mask_rows[row.name]
                        is_total = mask_row.get('__is_total__', False)
                        total_highlight_cols = [col for col in [last_month_col, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] if col]
                        styles = []
                        for col in row.index:
                            style = ''
                            if is_total:
                                if col in total_highlight_cols:
                                    style += 'background-color: #cfe2f3; color: #000000; font-weight: bold; '
                                elif col in ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΣΥΝΟΛΟ']:
                                    style += 'font-weight: bold; '
                            else:
                                if col in ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']:
                                    style += 'font-weight: bold; '
                                if col in month_cols and col in mask_row and mask_row[col]:
                                    style += 'background-color: #fff9c4; color: #000000; '
                            styles.append(style)
                        return styles
                    return [''] * len(row)
                
                # Apply styles
                styled_cnt = final_display_df.style.apply(highlight_aggs, axis=1)
                
                # Column config for better width
                col_config = {
                    "ΕΤΟΣ": st.column_config.TextColumn("Έτος", width="small"),
                    "ΤΑΜΕΙΟ": st.column_config.TextColumn("Ταμείο", width="medium"),
                    "ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ": st.column_config.TextColumn("Τύπος Ασφάλισης", width="medium"),
                    "ΕΡΓΟΔΟΤΗΣ": st.column_config.TextColumn("Εργοδότης", width="110px"),
                    "ΚΛΑΔΟΣ/ΠΑΚΕΤΟ": st.column_config.TextColumn("Κλάδος/Πακέτο", width="small"),
                    "ΠΕΡΙΓΡΑΦΗ": st.column_config.TextColumn("Περιγραφή", width="medium"),
                    "ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ": st.column_config.TextColumn("Τύπος Αποδοχών", width="small"),
                    "ΣΥΝΟΛΟ": st.column_config.TextColumn("Σύνολο Ημερών", width="small"),
                    "ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ": st.column_config.TextColumn("Μικτές Αποδοχές", width="110px"),
                    "ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ": st.column_config.TextColumn("Συνολικές Εισφορές", width="110px"),
                    "ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ": st.column_config.TextColumn("Ποσοστό Εισφοράς (%)", width="small"),
                }
                for m_col in month_cols:
                    col_config[m_col] = st.column_config.TextColumn(m_col, width="small")

                st.dataframe(
                    styled_cnt,
                    use_container_width=True,
                    column_config=col_config,
                    hide_index=True,
                    key="counting_table"
                )
                
                register_view("Καταμέτρηση", final_display_df)
                
                # Στυλ για εκτύπωση (ίδιοι χρωματισμοί με την οθόνη)
                total_highlight_cols = [col for col in [last_month_col, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] if col]
                print_style_rows = []
                for ridx, r in final_display_df.iterrows():
                    mask_row = active_mask_rows[ridx] if ridx < len(active_mask_rows) else {}
                    is_total = mask_row.get('__is_total__', False)
                    row_styles = {}
                    for col in final_display_df.columns:
                        style = ''
                        if col in ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']:
                            style += 'font-weight:700;'
                        if is_total and col in total_highlight_cols:
                            style += 'background-color:#cfe2f3;color:#000;'
                        elif col in month_cols and mask_row.get(col, False):
                            style += 'background-color:#fff9c4;color:#000;'
                        if col == 'ΠΕΡΙΓΡΑΦΗ':
                            style += 'white-space:nowrap;'
                        row_styles[col] = style
                    print_style_rows.append(row_styles)
                
                render_print_button(
                    "print_counting",
                    "Πίνακας Καταμέτρησης",
                    final_display_df,
                    description="Αναλυτική καταμέτρηση ημερών ασφάλισης ανά μήνα.",
                    style_rows=print_style_rows,
                    scale=0.9
                )
                
            else:
                st.warning("Δεν βρέθηκαν δεδομένα για καταμέτρηση.")
        else:
            st.warning("Λείπουν οι απαραίτητες στήλες (Από, Έως, Ημέρες) για την καταμέτρηση.")
    
    with tab_parallel:
        st.markdown("### Παράλληλη Ασφάλιση (ΙΚΑ & ΟΑΕΕ / ΟΑΕΕ & ΤΣΜΕΔΕ / ΟΓΑ & ΙΚΑ/ΟΑΕΕ)")
        parallel_df = df.copy()
        required_cols = ['Από', 'Έως', 'Ημέρες']
        
        if all(col in parallel_df.columns for col in required_cols):
            parallel_rows = []
            
            with st.spinner("Υπολογισμός παράλληλης ασφάλισης..."):
                for idx, row in parallel_df.iterrows():
                    try:
                        if pd.isna(row['Από']) or pd.isna(row['Έως']):
                            continue
                            
                        start_dt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
                        end_dt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')
                        
                        if pd.isna(start_dt) or pd.isna(end_dt):
                            continue
                            
                        # Calculation logic
                        days_val = 0
                        
                        if 'Ημέρες' in row and pd.notna(row['Ημέρες']) and str(row['Ημέρες']).strip() != '':
                             d = clean_numeric_value(row['Ημέρες'])
                             if d is not None and d != 0: days_val += d
                        
                        if 'Έτη' in row and pd.notna(row['Έτη']):
                             y = clean_numeric_value(row['Έτη'])
                             if y is not None and y != 0: days_val += y * 300
                        
                        if 'Μήνες' in row and pd.notna(row['Μήνες']):
                             m = clean_numeric_value(row['Μήνες'])
                             if m is not None and m != 0: days_val += m * 25
                        
                        raw_gross = str(row.get('Μικτές αποδοχές', ''))
                        if 'ΔΡΧ' in raw_gross.upper() or 'DRX' in raw_gross.upper():
                            gross_val = 0.0
                        else:
                            gross_val = clean_numeric_value(raw_gross, exclude_drx=True)
                        if gross_val is None: gross_val = 0.0
                        
                        raw_contrib = str(row.get('Συνολικές εισφορές', ''))
                        if 'ΔΡΧ' in raw_contrib.upper() or 'DRX' in raw_contrib.upper():
                            contrib_val = 0.0
                        else:
                            contrib_val = clean_numeric_value(raw_contrib, exclude_drx=True)
                        if contrib_val is None: contrib_val = 0.0

                        sign = get_negative_amount_sign(gross_val, contrib_val)
                        if sign == -1:
                            days_val = -abs(days_val)
                        
                        tameio = str(row.get('Ταμείο', '')).strip()
                        insurance_type = str(row.get('Τύπος Ασφάλισης', '')).strip()
                        employer = str(row.get('Α-Μ εργοδότη', '')).strip()
                        klados = str(row.get('Κλάδος/Πακέτο Κάλυψης', '')).strip()
                        klados_desc = description_map.get(klados, '') if 'description_map' in locals() else ''
                        earnings_type = str(row.get('Τύπος Αποδοχών', '')).strip()
                        foreas = str(row.get('Φορέας', '')).strip()
                        
                        curr = start_dt.replace(day=1)
                        end_month_dt = end_dt.replace(day=1)
                        
                        months_list = []
                        while curr <= end_month_dt:
                            months_list.append(curr)
                            if curr.month == 12:
                                curr = curr.replace(year=curr.year + 1, month=1)
                            else:
                                curr = curr.replace(month=curr.month + 1)
                        
                        num_months = len(months_list)
                        if num_months == 0: continue
                        
                        days_per_month = days_val / num_months
                        gross_per_month = gross_val / num_months
                        contrib_per_month = contrib_val / num_months
                        is_aggregate = num_months > 1
                        
                        for m_dt in months_list:
                            parallel_rows.append({
                                'ΕΤΟΣ': m_dt.year,
                                'ΤΑΜΕΙΟ': tameio,
                                'ΦΟΡΕΑΣ': foreas,
                                'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': insurance_type,
                                'ΕΡΓΟΔΟΤΗΣ': employer,
                                'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': klados,
                                'ΠΕΡΙΓΡΑΦΗ': klados_desc,
                                'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': earnings_type,
                                'Μήνας_Num': m_dt.month,
                                'Ημέρες': days_per_month,
                                'Μικτές_Part': gross_per_month,
                                'Εισφορές_Part': contrib_per_month,
                                'Is_Aggregate': is_aggregate
                            })
                            
                    except Exception:
                        continue

            if parallel_rows:
                p_c_df = pd.DataFrame(parallel_rows)
                
                # Κριτήρια φιλτραρίσματος για Παράλληλη Ασφάλιση
                def is_ika_match(row):
                    t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
                    i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
                    et = str(row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')).strip()
                    
                    # IKA Criteria
                    is_ika_tameio = 'IKA' in t or 'ΙΚΑ' in t
                    is_misthoti = 'ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type
                    
                    # Check earnings type: δεχόμαστε 01, 16 ή 99 (και παραλλαγές)
                    is_et_ika = et in ['01', '1', '16', '99']
                    
                    return (is_ika_tameio or is_misthoti) and is_et_ika

                def is_oaee_match(row):
                    t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
                    kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
                    
                    # OAEE Criteria
                    is_oaee_tameio = 'OAEE' in t or 'ΟΑΕΕ' in t or 'TEBE' in t or 'ΤΕΒΕ' in t or 'TAE' in t or 'ΤΑΕ' in t
                    
                    # Check for K (Latin or Greek)
                    is_k = kl in ['K', 'Κ']
                    
                    return is_oaee_tameio and is_k

                def is_tsm_match(row):
                    t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
                    kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
                    is_tsm_tameio = 'ΤΣΜΕΔΕ' in t or 'TSMEDE' in t
                    is_ks = kl in ['ΚΣ', 'ΠΚΣ', 'KS', 'PKS']
                    return is_tsm_tameio and is_ks

                def is_oga_match(row):
                    t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
                    kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
                    is_oga_tameio = 'ΟΓΑ' in t or 'OGA' in t
                    is_k = kl in ['K', 'Κ']
                    return is_oga_tameio and is_k

                def is_ika_general(row):
                    t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
                    i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
                    is_ika_tameio = 'IKA' in t or 'ΙΚΑ' in t
                    is_misthoti = 'ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type
                    return is_ika_tameio or is_misthoti

                # Ensure types
                p_c_df['ΕΤΟΣ'] = p_c_df['ΕΤΟΣ'].astype(int)
                p_c_df['Μήνας_Num'] = p_c_df['Μήνας_Num'].astype(int)

                p_c_df['is_ika'] = p_c_df.apply(is_ika_match, axis=1)
                p_c_df['is_ika_general'] = p_c_df.apply(is_ika_general, axis=1)
                p_c_df['is_oaee'] = p_c_df.apply(is_oaee_match, axis=1)
                p_c_df['is_tsm'] = p_c_df.apply(is_tsm_match, axis=1)
                p_c_df['is_oga'] = p_c_df.apply(is_oga_match, axis=1)
                
                # Ομαδοποίηση ανά μήνα για έλεγχο συνύπαρξης
                month_groups = p_c_df.groupby(['ΕΤΟΣ', 'Μήνας_Num'])
                valid_months = []
                
                for (year, month), group in month_groups:
                    ika_days = group.loc[group['is_ika'], 'Ημέρες'].sum()
                    oaee_days = group.loc[group['is_oaee'], 'Ημέρες'].sum()
                    tsm_days = group.loc[group['is_tsm'], 'Ημέρες'].sum()
                    oga_days = group.loc[group['is_oga'], 'Ημέρες'].sum()

                    has_ika = ika_days > 0
                    has_oaee = oaee_days > 0
                    has_tsm = tsm_days > 0
                    has_oga = oga_days > 0

                    if (has_ika and has_oaee) or (has_oaee and has_tsm) or (has_oga and (has_ika or has_oaee)):
                        # Περιορισμός έως 31/12/2016
                        if year <= 2016:
                            valid_months.append((year, month))

                # Υπολογισμός συνολικών παράλληλων ημερών (IKA+OAEE, OAEE+TSM, OGA+IKA, OGA+OAEE - 25)
                parallel_days_total = 0
                for (year, month) in valid_months:
                    try:
                        g = month_groups.get_group((year, month))
                    except KeyError:
                        continue
                    ika_days = g.loc[g['is_ika'], 'Ημέρες'].sum()
                    oaee_days = g.loc[g['is_oaee'], 'Ημέρες'].sum()
                    tsm_days = g.loc[g['is_tsm'], 'Ημέρες'].sum()
                    oga_days = g.loc[g['is_oga'], 'Ημέρες'].sum()
                    ika_cap = min(ika_days, 25)
                    oaee_cap = min(oaee_days, 25)
                    tsm_cap = min(tsm_days, 25)
                    oga_cap = min(oga_days, 25)
                    candidates = []
                    if ika_cap > 0 and oaee_cap > 0:
                        candidates.append(max(ika_cap + oaee_cap - 25, 0))
                    if oaee_cap > 0 and tsm_cap > 0:
                        candidates.append(max(oaee_cap + tsm_cap - 25, 0))
                    if oga_cap > 0 and ika_cap > 0:
                        candidates.append(max(oga_cap + ika_cap - 25, 0))
                    if oga_cap > 0 and oaee_cap > 0:
                        candidates.append(max(oga_cap + oaee_cap - 25, 0))
                    month_parallel = max(candidates) if candidates else 0
                    parallel_days_total += month_parallel
                parallel_days_total = int(round(parallel_days_total))

                # Μηνύματα ενημέρωσης σε μία γραμμή (όπως στην Καταμέτρηση)
                info_col1, info_col2, info_col3 = st.columns([3, 3, 2])
                with info_col1:
                    st.info("Εμφάνιση διαστημάτων όπου συνυπάρχουν στον ίδιο μήνα: ΙΚΑ (Τύπος Αποδοχών 01, 16 ή 99) & ΟΑΕΕ (Κλάδος/Πακέτο Κ), ΟΑΕΕ (Κ) & ΤΣΜΕΔΕ (ΚΣ/ΠΚΣ), ή ΟΓΑ (Κ) & ΙΚΑ/ΟΑΕΕ.")
                with info_col2:
                    st.success(f"Βρέθηκαν {len(valid_months)} μήνες παράλληλης ασφάλισης (ΙΚΑ 01/16/99 & ΟΑΕΕ Κ ή ΟΑΕΕ Κ & ΤΣΜΕΔΕ ΚΣ/ΠΚΣ ή ΟΓΑ Κ & ΙΚΑ/ΟΑΕΕ) έως 31/12/2016. Σύνολο παράλληλων ημερών: {parallel_days_total}.")
                with info_col3:
                    st.warning("Διαστήματα που καλύπτουν πολλαπλούς μήνες επιμερίζονται και επισημαίνονται με κίτρινο χρώμα.")

                if valid_months:
                    valid_months_df = pd.DataFrame(valid_months, columns=['ΕΤΟΣ', 'Μήνας_Num'])
                    p_c_df_filtered = p_c_df.merge(valid_months_df, on=['ΕΤΟΣ', 'Μήνας_Num'], how='inner')
                    
                    # Strict Filtering: Κρατάμε IKA ή OAEE K ή TSMEDE KS/PKS ή OGA K
                    p_c_df_filtered = p_c_df_filtered[p_c_df_filtered['is_ika_general'] | p_c_df_filtered['is_oaee'] | p_c_df_filtered['is_tsm'] | p_c_df_filtered['is_oga']]
                    
                    # Καθαρισμός helper columns
                    p_c_df_filtered = p_c_df_filtered.drop(columns=['is_ika', 'is_oaee', 'is_tsm', 'is_oga', 'is_ika_general', 'ΦΟΡΕΑΣ'])
                    
                    # Υπολογισμός Ετήσιων Συνόλων
                    annual_totals_p = p_c_df_filtered.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'])[['Ημέρες', 'Μικτές_Part', 'Εισφορές_Part']].sum().reset_index()
                    annual_totals_p.rename(columns={
                        'Ημέρες': 'ΣΥΝΟΛΟ',
                        'Μικτές_Part': 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ',
                        'Εισφορές_Part': 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'
                    }, inplace=True)

                    # Pivot Tables
                    pivot_df_p = p_c_df_filtered.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Ημέρες'].sum().reset_index()
                    agg_df_p = p_c_df_filtered.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Is_Aggregate'].max().reset_index()
                    
                    final_val_p = pivot_df_p.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Ημέρες').fillna(0)
                    final_agg_p = agg_df_p.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Is_Aggregate').fillna(False)
                    
                    final_val_p = final_val_p.reset_index()
                    final_val_p = final_val_p.merge(annual_totals_p, on=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], how='left')
                    final_val_p.set_index(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], inplace=True)
                    
                    # Ensure columns
                    for m in range(1, 13):
                        if m not in final_val_p.columns:
                            final_val_p[m] = 0
                        if m not in final_agg_p.columns:
                            final_agg_p[m] = False
                    
                    month_cols_int = sorted([c for c in final_val_p.columns if isinstance(c, int)])
                    final_val_p = final_val_p[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ']]
                    
                    # Contribution Ratio
                    if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in final_val_p.columns and 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in final_val_p.columns:
                        final_val_p['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = pd.NA
                        gross_series = final_val_p['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
                        valid_mask = gross_series.notna() & (gross_series != 0)
                        ratios = (
                            final_val_p.loc[valid_mask, 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] /
                            final_val_p.loc[valid_mask, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
                        ) * 100
                        final_val_p.loc[valid_mask, 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ratios
                        final_val_p = final_val_p[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']]
                    
                    month_map = {m: f"{m}ος" for m in range(1, 13)}
                    final_val_p = final_val_p.rename(columns=month_map)
                    
                    # Sort
                    final_val_p = final_val_p.sort_values(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'])
                    
                    # Align Aggregates
                    final_agg_p = final_agg_p.reindex(final_val_p.index)
                    final_agg_p = final_agg_p.rename(columns=month_map)
                    
                    # --- Custom Formatting & Grouping ---
                    
                    def fmt_gr(val, is_currency=False, is_days=False):
                        if pd.isna(val) or val == "" or (isinstance(val, (int, float)) and val == 0):
                            return ""
                        try:
                            val = float(val)
                        except:
                            return str(val)
                        
                        if is_days:
                            s = '{:,.0f}'.format(val).replace(',', '.')
                        else:
                            s = '{:,.2f}'.format(val)
                            s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                        
                        if is_currency:
                            s += ' €'
                        return s

                    df_r = final_val_p.reset_index()
                    agg_r = final_agg_p.reset_index()
                    
                    display_data = []
                    mask_rows = []
                    prev_vals = {'ΕΤΟΣ': None, 'ΤΑΜΕΙΟ': None, 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': None}
                    
                    years = sorted(df_r['ΕΤΟΣ'].unique())
                    
                    for year in years:
                        # Get rows for this year
                        y_df = df_r[df_r['ΕΤΟΣ'] == year]
                        # Indices in agg_r match because we reindexed and reset_index on sorted data
                        y_agg = agg_r.loc[y_df.index]
                        
                        # Calculate Sums
                        sum_gross = y_df['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'].sum()
                        sum_contrib = y_df['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'].sum()
                        
                        # Process Rows
                        for pos, (idx, row) in enumerate(y_df.iterrows()):
                            # Find corresponding agg row (use positional index inside the year's slice)
                            agg_row = y_agg.iloc[pos]
                            
                            d_row = row.to_dict()
                            
                            # Build mask row for aggregates per month
                            mask_row = {m_col: False for m_col in list(month_map.values())}
                            for m_col in list(month_map.values()):
                                if m_col in agg_row and bool(agg_row[m_col]):
                                    mask_row[m_col] = True
                            mask_row['__is_total__'] = False
                            
                            # Visual Grouping (hide repeating values)
                            curr_etos = str(row['ΕΤΟΣ'])
                            curr_tam = str(row['ΤΑΜΕΙΟ'])
                            curr_typ = str(row['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'])
                            
                            if curr_etos == str(prev_vals['ΕΤΟΣ']):
                                d_row['ΕΤΟΣ'] = ""
                                if curr_tam == str(prev_vals['ΤΑΜΕΙΟ']):
                                    d_row['ΤΑΜΕΙΟ'] = ""
                                    if curr_typ == str(prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ']):
                                        d_row['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = ""
                                    else:
                                        prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = curr_typ
                                else:
                                    prev_vals['ΤΑΜΕΙΟ'] = curr_tam
                                    prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = curr_typ
                            else:
                                prev_vals['ΕΤΟΣ'] = curr_etos
                                prev_vals['ΤΑΜΕΙΟ'] = curr_tam
                                prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = curr_typ
                            
                            # Formatting
                            for m_col in list(month_map.values()) + ['ΣΥΝΟΛΟ']:
                                d_row[m_col] = fmt_gr(d_row.get(m_col), False, True)
                                
                            d_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = fmt_gr(d_row.get('ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'), True)
                            d_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = fmt_gr(d_row.get('ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'), True)
                            
                            p_val = d_row.get('ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ')
                            d_row['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = fmt_gr(p_val, False) + ' %' if pd.notna(p_val) and d_row.get('ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ') not in [None, ""] else ""
                            
                            display_data.append(d_row)
                            mask_rows.append(mask_row)
                        
                        # Add Total Row
                        t_row = {c: "" for c in df_r.columns}
                        t_row['ΣΥΝΟΛΟ'] = ""
                        t_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = fmt_gr(sum_gross, True)
                        t_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = fmt_gr(sum_contrib, True)
                        display_data.append(t_row)
                        mask_rows.append({m_col: False for m_col in list(month_map.values())} | {'__is_total__': True})
                        
                        # Add Empty Row after Total
                        empty_row = {c: "" for c in df_r.columns}
                        display_data.append(empty_row)
                        mask_rows.append({m_col: False for m_col in list(month_map.values())} | {'__is_total__': False})
                    
                    display_final_df = pd.DataFrame(display_data)
                    
                    # Rename Headers (Capitalization)
                    header_map = {
                        "ΕΤΟΣ": "Έτος",
                        "ΤΑΜΕΙΟ": "Ταμείο",
                        "ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ": "Τύπος Ασφάλισης",
                        "ΕΡΓΟΔΟΤΗΣ": "Εργοδότης",
                        "ΚΛΑΔΟΣ/ΠΑΚΕΤΟ": "Κλάδος/Πακέτο",
                        "ΠΕΡΙΓΡΑΦΗ": "Περιγραφή",
                        "ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ": "Τύπος Αποδοχών",
                        "ΣΥΝΟΛΟ": "Σύνολο",
                        "ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ": "Μικτές Αποδοχές",
                        "ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ": "Συνολικές Εισφορές",
                        "ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ": "Ποσοστό (%)"
                    }
                    display_final_df = display_final_df.rename(columns=header_map)
                    
                    # Styling Function using mask_rows (aggregate flags per month)
                    def style_parallel(row):
                        if row.name >= len(mask_rows): 
                            return [''] * len(row)
                        mrow = mask_rows[row.name]
                        is_total = mrow.get('__is_total__', False)
                        styles = []
                        for col in row.index:
                            s = ''
                            if is_total:
                                if col in ['Μικτές Αποδοχές', 'Συνολικές Εισφορές'] or (isinstance(row[col], str) and row[col].strip() != ''):
                                     s += 'background-color: #cfe2f3; font-weight: bold; '
                            else:
                                if col in ['Έτος', 'Ταμείο', 'Τύπος Ασφάλισης', 'Σύνολο', 'Μικτές Αποδοχές']:
                                    s += 'font-weight: bold; '
                                if col in mrow and mrow.get(col, False) is True:
                                    s += 'background-color: #fff9c4; '
                            styles.append(s)
                        return styles

                    # Apply Style (No hide needed)
                    styler = display_final_df.style.apply(style_parallel, axis=1)

                    # Display
                    st.dataframe(
                        styler,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Έτος": st.column_config.Column(width="small"),
                            "Ταμείο": st.column_config.Column(width="medium"),
                            "Τύπος Ασφάλισης": st.column_config.Column(width="medium"),
                            "Εργοδότης": st.column_config.Column(width="small"),
                            "Κλάδος/Πακέτο": st.column_config.Column(width="small"),
                            "Περιγραφή": st.column_config.Column(width="medium"),
                            "Τύπος Αποδοχών": st.column_config.Column(width="small"),
                            "Σύνολο": st.column_config.Column(width="small"),
                            "Μικτές Αποδοχές": st.column_config.Column(width="small"),
                            "Συνολικές Εισφορές": st.column_config.Column(width="small"),
                            "Ποσοστό (%)": st.column_config.Column(width="small"),
                        }
                    )

                    # Δώσε λίγο κατακόρυφο κενό ώστε το κουμπί εκτύπωσης να μην επικαλύπτεται από το dataframe
                    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

                    # Register for Export
                    register_view("Παράλληλη_Ασφάλιση", display_final_df)
                    
                    render_print_button(
                        "print_parallel",
                        "Παράλληλη Ασφάλιση",
                        display_final_df,
                        description="Πίνακας Παράλληλης Ασφάλισης (ΙΚΑ & ΟΑΕΕ)"
                    )
                else:
                    st.warning("Δεν βρέθηκαν διαστήματα παράλληλης ασφάλισης με τα συγκεκριμένα κριτήρια.")
            else:
                 st.warning("Δεν βρέθηκαν δεδομένα.")
        else:
            st.warning("Λείπουν απαραίτητες στήλες.")

    with tab_multi:
        st.markdown("### Πολλαπλή Απασχόληση (Πολλαπλοί Εργοδότες)")
        multi_df = df.copy()
        required_cols = ['Από', 'Έως', 'Ημέρες']
        
        if all(col in multi_df.columns for col in required_cols):
            multi_rows = []
            
            with st.spinner("Υπολογισμός πολλαπλής απασχόλησης..."):
                for idx, row in multi_df.iterrows():
                    try:
                        if pd.isna(row['Από']) or pd.isna(row['Έως']):
                            continue
                            
                        start_dt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
                        end_dt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')
                        
                        if pd.isna(start_dt) or pd.isna(end_dt):
                            continue
                            
                        # Calculation logic
                        days_val = 0
                        
                        if 'Ημέρες' in row and pd.notna(row['Ημέρες']) and str(row['Ημέρες']).strip() != '':
                             d = clean_numeric_value(row['Ημέρες'])
                             if d is not None and d != 0: days_val += d
                        
                        if 'Έτη' in row and pd.notna(row['Έτη']):
                             y = clean_numeric_value(row['Έτη'])
                             if y is not None and y != 0: days_val += y * 300
                        
                        if 'Μήνες' in row and pd.notna(row['Μήνες']):
                             m = clean_numeric_value(row['Μήνες'])
                             if m is not None and m != 0: days_val += m * 25
                        
                        raw_gross = str(row.get('Μικτές αποδοχές', ''))
                        if 'ΔΡΧ' in raw_gross.upper() or 'DRX' in raw_gross.upper():
                            gross_val = 0.0
                        else:
                            gross_val = clean_numeric_value(raw_gross, exclude_drx=True)
                        if gross_val is None: gross_val = 0.0
                        
                        raw_contrib = str(row.get('Συνολικές εισφορές', ''))
                        if 'ΔΡΧ' in raw_contrib.upper() or 'DRX' in raw_contrib.upper():
                            contrib_val = 0.0
                        else:
                            contrib_val = clean_numeric_value(raw_contrib, exclude_drx=True)
                        if contrib_val is None: contrib_val = 0.0

                        sign = get_negative_amount_sign(gross_val, contrib_val)
                        if sign == -1:
                            days_val = -abs(days_val)
                        
                        tameio = str(row.get('Ταμείο', '')).strip()
                        insurance_type = str(row.get('Τύπος Ασφάλισης', '')).strip()
                        employer = str(row.get('Α-Μ εργοδότη', '')).strip()
                        klados = str(row.get('Κλάδος/Πακέτο Κάλυψης', '')).strip()
                        klados_desc = description_map.get(klados, '') if 'description_map' in locals() else ''
                        earnings_type = str(row.get('Τύπος Αποδοχών', '')).strip()
                        foreas = str(row.get('Φορέας', '')).strip()
                        
                        curr = start_dt.replace(day=1)
                        end_month_dt = end_dt.replace(day=1)
                        
                        months_list = []
                        while curr <= end_month_dt:
                            months_list.append(curr)
                            if curr.month == 12:
                                curr = curr.replace(year=curr.year + 1, month=1)
                            else:
                                curr = curr.replace(month=curr.month + 1)
                        
                        num_months = len(months_list)
                        if num_months == 0: continue
                        
                        days_per_month = days_val / num_months
                        gross_per_month = gross_val / num_months
                        contrib_per_month = contrib_val / num_months
                        is_aggregate = num_months > 1
                        
                        for m_dt in months_list:
                            multi_rows.append({
                                'ΕΤΟΣ': m_dt.year,
                                'ΤΑΜΕΙΟ': tameio,
                                'ΦΟΡΕΑΣ': foreas,
                                'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': insurance_type,
                                'ΕΡΓΟΔΟΤΗΣ': employer,
                                'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': klados,
                                'ΠΕΡΙΓΡΑΦΗ': klados_desc,
                                'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': earnings_type,
                                'Μήνας_Num': m_dt.month,
                                'Ημέρες': days_per_month,
                                'Μικτές_Part': gross_per_month,
                                'Εισφορές_Part': contrib_per_month,
                                'Is_Aggregate': is_aggregate
                            })
                            
                    except Exception:
                        continue

            if multi_rows:
                m_c_df = pd.DataFrame(multi_rows)
                
                def is_ika_multi_match(row):
                    t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
                    i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
                    et = str(row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')).strip()
                    
                    is_ika_tameio = 'IKA' in t or 'ΙΚΑ' in t
                    is_misthoti = 'ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type
                    
                    is_et_ika = et in ['01', '1', '16', '99']
                    
                    return (is_ika_tameio or is_misthoti) and is_et_ika

                m_c_df['ΕΤΟΣ'] = m_c_df['ΕΤΟΣ'].astype(int)
                m_c_df['Μήνας_Num'] = m_c_df['Μήνας_Num'].astype(int)

                m_c_df['is_ika'] = m_c_df.apply(is_ika_multi_match, axis=1)
                
                ika_rows = m_c_df[m_c_df['is_ika']].copy()
                
                ika_rows['ΕΡΓΟΔΟΤΗΣ_Clean'] = ika_rows['ΕΡΓΟΔΟΤΗΣ'].replace(['', 'nan', 'NaN', 'None'], pd.NA)
                ika_rows = ika_rows.dropna(subset=['ΕΡΓΟΔΟΤΗΣ_Clean'])

                multi_employer_months = []
                month_groups = ika_rows.groupby(['ΕΤΟΣ', 'Μήνας_Num'])
                
                for (year, month), group in month_groups:
                    unique_employers = group['ΕΡΓΟΔΟΤΗΣ_Clean'].nunique()
                    if unique_employers > 1:
                        multi_employer_months.append((year, month))
                
                if multi_employer_months:
                    st.success(f"Βρέθηκαν {len(multi_employer_months)} μήνες πολλαπλής απασχόλησης (ΙΚΑ 01/16/99 με >1 εργοδότες).")
                    
                    valid_months_df = pd.DataFrame(multi_employer_months, columns=['ΕΤΟΣ', 'Μήνας_Num'])
                    
                    m_c_df_filtered = m_c_df.merge(valid_months_df, on=['ΕΤΟΣ', 'Μήνας_Num'], how='inner')
                    m_c_df_filtered = m_c_df_filtered[m_c_df_filtered['is_ika']]
                    
                    m_c_df_filtered = m_c_df_filtered.drop(columns=['is_ika', 'ΦΟΡΕΑΣ'])
                    
                    annual_totals_m = m_c_df_filtered.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'])[['Ημέρες', 'Μικτές_Part', 'Εισφορές_Part']].sum().reset_index()
                    annual_totals_m.rename(columns={
                        'Ημέρες': 'ΣΥΝΟΛΟ',
                        'Μικτές_Part': 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ',
                        'Εισφορές_Part': 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'
                    }, inplace=True)

                    pivot_df_m = m_c_df_filtered.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Ημέρες'].sum().reset_index()
                    agg_df_m = m_c_df_filtered.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Is_Aggregate'].max().reset_index()
                    
                    final_val_m = pivot_df_m.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Ημέρες').fillna(0)
                    final_agg_m = agg_df_m.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Is_Aggregate').fillna(False)
                    
                    final_val_m = final_val_m.reset_index()
                    final_val_m = final_val_m.merge(annual_totals_m, on=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], how='left')
                    final_val_m.set_index(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], inplace=True)
                    
                    for m in range(1, 13):
                        if m not in final_val_m.columns:
                            final_val_m[m] = 0
                        if m not in final_agg_m.columns:
                            final_agg_m[m] = False
                    
                    month_cols_int = sorted([c for c in final_val_m.columns if isinstance(c, int)])
                    final_val_m = final_val_m[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ']]
                    
                    if 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ' in final_val_m.columns and 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ' in final_val_m.columns:
                        final_val_m['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = pd.NA
                        gross_series = final_val_m['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
                        valid_mask = gross_series.notna() & (gross_series != 0)
                        ratios = (
                            final_val_m.loc[valid_mask, 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] /
                            final_val_m.loc[valid_mask, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ']
                        ) * 100
                        final_val_m.loc[valid_mask, 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ratios
                        final_val_m = final_val_m[['ΣΥΝΟΛΟ'] + month_cols_int + ['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']]
                    
                    month_map = {m: f"{m}ος" for m in range(1, 13)}
                    final_val_m = final_val_m.rename(columns=month_map)
                    
                    final_val_m = final_val_m.sort_values(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'])
                    
                    final_agg_m = final_agg_m.reindex(final_val_m.index)
                    final_agg_m = final_agg_m.rename(columns=month_map)

                    def fmt_gr_multi(val, is_currency=False, is_days=False):
                        if pd.isna(val) or val == "" or (isinstance(val, (int, float)) and val == 0):
                            return ""
                        try:
                            val = float(val)
                        except:
                            return str(val)
                        
                        if is_days:
                            s = '{:,.0f}'.format(val).replace(',', '.')
                        else:
                            s = '{:,.2f}'.format(val)
                            s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                        
                        if is_currency:
                            s += ' €'
                        return s

                    df_r = final_val_m.reset_index()
                    agg_r = final_agg_m.reset_index()
                    
                    display_data = []
                    mask_rows = []
                    prev_vals = {'ΕΤΟΣ': None, 'ΤΑΜΕΙΟ': None, 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': None}
                    
                    years = sorted(df_r['ΕΤΟΣ'].unique())
                    
                    for year in years:
                        y_df = df_r[df_r['ΕΤΟΣ'] == year]
                        y_agg = agg_r.loc[y_df.index]
                        
                        sum_gross = y_df['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'].sum()
                        sum_contrib = y_df['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'].sum()
                        
                        for pos, (idx, row) in enumerate(y_df.iterrows()):
                            agg_row = y_agg.iloc[pos]
                            d_row = row.to_dict()
                            
                            mask_row = {m_col: False for m_col in list(month_map.values())}
                            for m_col in list(month_map.values()):
                                if m_col in agg_row and bool(agg_row[m_col]):
                                    mask_row[m_col] = True
                            mask_row['__is_total__'] = False
                            
                            curr_etos = str(row['ΕΤΟΣ'])
                            curr_tam = str(row['ΤΑΜΕΙΟ'])
                            curr_typ = str(row['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'])
                            
                            if curr_etos == str(prev_vals['ΕΤΟΣ']):
                                d_row['ΕΤΟΣ'] = ""
                                if curr_tam == str(prev_vals['ΤΑΜΕΙΟ']):
                                    d_row['ΤΑΜΕΙΟ'] = ""
                                    if curr_typ == str(prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ']):
                                        d_row['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = ""
                                    else:
                                        prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = curr_typ
                                else:
                                    prev_vals['ΤΑΜΕΙΟ'] = curr_tam
                                    prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = curr_typ
                            else:
                                prev_vals['ΕΤΟΣ'] = curr_etos
                                prev_vals['ΤΑΜΕΙΟ'] = curr_tam
                                prev_vals['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'] = curr_typ
                            
                            for m_col in list(month_map.values()) + ['ΣΥΝΟΛΟ']:
                                d_row[m_col] = fmt_gr_multi(d_row.get(m_col), False, True)
                                
                            d_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = fmt_gr_multi(d_row.get('ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'), True)
                            d_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = fmt_gr_multi(d_row.get('ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'), True)
                            
                            p_val = d_row.get('ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ')
                            d_row['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = fmt_gr_multi(p_val, False) + ' %' if pd.notna(p_val) and d_row.get('ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ') not in [None, ""] else ""
                            
                            display_data.append(d_row)
                            mask_rows.append(mask_row)
                        
                        t_row = {c: "" for c in df_r.columns}
                        t_row['ΣΥΝΟΛΟ'] = ""
                        t_row['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = fmt_gr_multi(sum_gross, True)
                        t_row['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = fmt_gr_multi(sum_contrib, True)
                        display_data.append(t_row)
                        mask_rows.append({m_col: False for m_col in list(month_map.values())} | {'__is_total__': True})
                        
                        empty_row = {c: "" for c in df_r.columns}
                        display_data.append(empty_row)
                        mask_rows.append({m_col: False for m_col in list(month_map.values())} | {'__is_total__': False})
                    
                    display_final_df = pd.DataFrame(display_data)
                    
                    header_map = {
                        "ΕΤΟΣ": "Έτος",
                        "ΤΑΜΕΙΟ": "Ταμείο",
                        "ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ": "Τύπος Ασφάλισης",
                        "ΕΡΓΟΔΟΤΗΣ": "Εργοδότης",
                        "ΚΛΑΔΟΣ/ΠΑΚΕΤΟ": "Κλάδος/Πακέτο",
                        "ΠΕΡΙΓΡΑΦΗ": "Περιγραφή",
                        "ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ": "Τύπος Αποδοχών",
                        "ΣΥΝΟΛΟ": "Σύνολο",
                        "Μικτές Αποδοχές": "Μικτές Αποδοχές",
                        "ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ": "Μικτές Αποδοχές",
                        "ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ": "Συνολικές Εισφορές",
                        "ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ": "Ποσοστό (%)"
                    }
                    display_final_df = display_final_df.rename(columns=header_map)
                    
                    def style_multi(row):
                        if row.name >= len(mask_rows): 
                            return [''] * len(row)
                        mrow = mask_rows[row.name]
                        is_total = mrow.get('__is_total__', False)
                        styles = []
                        for col in row.index:
                            s = ''
                            if is_total:
                                if col in ['Μικτές Αποδοχές', 'Συνολικές Εισφορές'] or (isinstance(row[col], str) and row[col].strip() != ''):
                                     s += 'background-color: #cfe2f3; font-weight: bold; '
                            else:
                                if col in ['Έτος', 'Ταμείο', 'Τύπος Ασφάλισης', 'Σύνολο', 'Μικτές Αποδοχές']:
                                    s += 'font-weight: bold; '
                                if col in mrow and mrow.get(col, False) is True:
                                    s += 'background-color: #fff9c4; '
                            styles.append(s)
                        return styles

                    styler = display_final_df.style.apply(style_multi, axis=1)

                    st.markdown('<div class="multi-table">', unsafe_allow_html=True)
                    st.dataframe(
                        styler,
                        use_container_width=True,
                        hide_index=True,
                         column_config={
                            "Έτος": st.column_config.Column(width="small"),
                            "Ταμείο": st.column_config.Column(width="medium"),
                            "Τύπος Ασφάλισης": st.column_config.Column(width="medium"),
                            "Εργοδότης": st.column_config.Column(width="small"),
                            "Κλάδος/Πακέτο": st.column_config.Column(width="small"),
                            "Περιγραφή": st.column_config.Column(width="medium"),
                            "Τύπος Αποδοχών": st.column_config.Column(width="small"),
                            "Σύνολο": st.column_config.Column(width="small"),
                            "Μικτές Αποδοχές": st.column_config.Column(width="small"),
                            "Συνολικές Εισφορές": st.column_config.Column(width="small"),
                            "Ποσοστό (%)": st.column_config.Column(width="small"),
                        }
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
                    
                    render_print_button(
                        "print_multi",
                        "Πολλαπλή Απασχόληση",
                        display_final_df,
                        description="Πίνακας Πολλαπλής Απασχόλησης (ΙΚΑ & Πολλαπλοί Εργοδότες)"
                    )
                else:
                    st.warning("Δεν βρέθηκαν μήνες με πολλαπλούς εργοδότες για ΙΚΑ (01/16/99).")
            else:
                 st.warning("Δεν βρέθηκαν δεδομένα.")
        else:
            st.warning("Λείπουν απαραίτητες στήλες.")
    
    # Download section
    st.markdown("---")
    st.markdown("### Επιλογές εκτύπωσης")
    name_col, amka_col = st.columns([1, 1])
    with name_col:
        st.session_state['print_client_name'] = st.text_input(
            "Ονοματεπώνυμο ασφαλισμένου:",
            value=st.session_state.get('print_client_name', ''),
            placeholder="Π.χ. Ιωάννης Παπαδόπουλος"
        )
    with amka_col:
        st.session_state['print_client_amka'] = st.text_input(
            "ΑΜΚΑ:",
            value=st.session_state.get('print_client_amka', ''),
            placeholder="Π.χ. 01017012345"
        )

    st.markdown("### Επιλογές εξαγωγής")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1.2, 1])
    
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

                for col in ['Έτη', 'Μήνες', 'Ημέρες']:
                    if col in summary_df.columns:
                        summary_df[col] = summary_df[col].apply(clean_numeric_value)
                for col in ['Μικτές αποδοχές', 'Συνολικές εισφορές']:
                    if col in summary_df.columns:
                        summary_df[col] = summary_df[col].apply(lambda x: clean_numeric_value(x, exclude_drx=True))
                summary_df = apply_negative_time_sign(summary_df)
                
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
                    yearly_df = apply_negative_time_sign(yearly_df)
                    
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

            # Προσθήκη Ανάλυσης ΑΠΔ (με τα τρέχοντα φίλτρα)
            if 'apd_export_df' in locals():
                try:
                    apd_export_df.to_excel(writer, sheet_name='Ανάλυση_ΑΠΔ', index=False)
                except Exception:
                    pass
        
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

    with col3:
        if view_exports:
            view_options = list(view_exports.keys())
            label_col, dropdown_col = st.columns([0.8, 2])
            with label_col:
                st.markdown('<div style="font-size:0.9rem; color:#4b5563; padding-top:0.45rem;">Επιλέξτε μεμονωμένο πίνακα:</div>', unsafe_allow_html=True)
            with dropdown_col:
                selected_view = st.selectbox(
                    "",
                    options=view_options,
                    key="view_export_selection",
                    label_visibility="collapsed"
                )
            view_df = view_exports[selected_view]
            view_buffer = io.BytesIO()
            with pd.ExcelWriter(view_buffer, engine='openpyxl') as writer:
                sheet_label = re.sub(r'[\\/*?:\\[\\]]', '_', selected_view)[:31]
                view_df.to_excel(writer, sheet_name=sheet_label or "Προβολή", index=False)
            view_buffer.seek(0)
            base_name = filename[:-4] if filename.endswith('.pdf') else 'efka'
            sanitized_label = re.sub(r'[\\/*?:<>|"]', '_', selected_view)
            view_filename = f"{base_name}_{sanitized_label}_προβολή.xlsx"
        else:
            st.info("Δεν υπάρχει διαθέσιμος πίνακας για εξαγωγή.")

    with col4:
        if view_exports:
            st.download_button(
                label="Εξαγωγή πίνακα",
                data=view_buffer.getvalue() if 'view_buffer' in locals() else b'',
                file_name=view_filename if 'view_filename' in locals() else 'view.xlsx',
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled='view_buffer' not in locals()
        )
    
    # Footer
    st.markdown("---")
    st.markdown("### Πληροφορίες")
    st.info("""
    **Σύντομος οδηγός:**
    - *Κύρια Δεδομένα*: Κατεβάζει τα φιλτραρισμένα κύρια δεδομένα που εμφανίζονται στο Tab 1.
    - *Όλα τα Δεδομένα*: Πλήρες Excel με κάθε πίνακα, τις επιπλέον αναφορές (Συνοπτική, Ετήσια, Κενά, Ανάλυση ΑΠΔ) και ακατέργαστες γραμμές όπως προήλθαν από το PDF.
    - *Εξαγωγή πίνακα*: Επιλέγεις ένα συγκεκριμένο πίνακα (μαζί με φίλτρα, ταξινομήσεις κ.λπ.) και τον εξάγεις όπως ακριβώς εμφανίζεται.
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

    # Προσθήκη ημερομηνίας τελευταίας ενημέρωσης
    st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.85rem; margin-top: 0.5rem; margin-bottom: 1rem;'>{get_last_update_date()}</div>", unsafe_allow_html=True)
    
    # Εμφάνιση ανεβάσματος αρχείου
    if not st.session_state['file_uploaded']:
        # Κουμπί για κατέβασμα αρχείου από ΕΦΚΑ
        st.markdown('''
            <div class="efka-btn-wrapper">
                <a href="https://www.e-efka.gov.gr/el/elektronikes-yperesies/synoptiko-kai-analytiko-istoriko-asphalises" target="_blank" class="efka-btn">
                    Κατεβάστε το αρχείο ΑΤΛΑΣ
                </a>
            </div>
        ''', unsafe_allow_html=True)

        # Προτροπή και Upload Button - Card Style
        st.markdown('<div class="upload-prompt-text">Στη συνέχεια ανεβάστε το αρχείο εδώ για ανάλυση</div>', unsafe_allow_html=True)
        
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
        
        # Οδηγίες σε πλαίσιο
        st.markdown('''
            <div class="instructions-box">
                <div class="instructions-title">Γενικές Οδηγίες Χρήσης</div>
                <div class="instructions-list">
                    1. Μεταβείτε στην υπηρεσία του e-ΕΦΚΑ πατώντας το μπλε κουμπί παραπάνω.<br>
                    2. Συνδεθείτε με τους κωδικούς Taxisnet.<br>
                    3. Επιλέξτε "Συνοπτικό και Αναλυτικό Ιστορικό Ασφάλισης".<br>
                    4. Κατεβάστε το αρχείο σε μορφή PDF στον υπολογιστή σας.<br>
                    5. Ανεβάστε το αρχείο που κατεβάσατε στην παραπάνω φόρμα.<br>
                    6. Η εφαρμογή θα αναλύσει αυτόματα τα δεδομένα και θα σας παρουσιάσει αναλυτικούς πίνακες και διαγράμματα.<br>
                    <br>
                    <strong>Σημείωση:</strong> Τα δεδομένα επεξεργάζονται αποκλειστικά στον browser σας (client-side) και δεν αποθηκεύονται σε κανέναν server.
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # Footer
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

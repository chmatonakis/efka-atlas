#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATLAS Lite — αυτόνομη Streamlit εφαρμογή

Παράγεται από LOCAL_DEV/kyria/app_final.py (scripts/build_lite_from_kyria.py). Χωρίς Streamlit σελίδα αποτελεσμάτων· μόνο HTML μέσω «Άνοιγμα / Προβολή».
"""

import sys
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
import math
from contextlib import nullcontext

# Ρίζα repo: LOCAL_DEV/kyria ή LOCAL_DEV/lite → ATLAS root για imports (html_viewer_builder κ.λπ.)
_APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = (
    _APP_DIR.parent.parent
    if (_APP_DIR.name in ("kyria", "lite") and _APP_DIR.parent.name == "LOCAL_DEV")
    else _APP_DIR
)
# Σειρά διαδρομών: πρώτα φάκελος εφαρμογής (kyria/lite), μετά ρίζα repo — για `html_viewer_builder` → `app_final`
for _p_rm in (str(_APP_DIR), str(REPO_ROOT)):
    if _p_rm in sys.path:
        try:
            sys.path.remove(_p_rm)
        except ValueError:
            pass
for _p_ins in (str(REPO_ROOT), str(_APP_DIR)):
    sys.path.insert(0, _p_ins)

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
        repo_path = REPO_ROOT
        date_str = subprocess.check_output(
            ['git', 'log', '-1', "--format=%cd", "--date=format:'%d/%m/%Y'"],
            cwd=repo_path,
            stderr=subprocess.STDOUT
        ).decode('utf-8').strip().replace("'", "")
        return f"Τελευταία ενημέρωση: {date_str}"
    except Exception:
        # Fallback to current date if git command fails
        return ""

def parse_birthdate_and_age(birthdate_str: str) -> tuple[str, int | None]:
    """Επιστρέφει κανονικοποιημένη ημ/νία γέννησης (dd/mm/yyyy) και ηλικία σήμερα."""
    raw = str(birthdate_str or "").strip()
    if not raw:
        return "", None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            bdt = datetime.datetime.strptime(raw, fmt).date()
            today = datetime.date.today()
            if bdt > today:
                return raw, None
            age = today.year - bdt.year - ((today.month, today.day) < (bdt.month, bdt.day))
            return bdt.strftime("%d/%m/%Y"), age
        except Exception:
            continue
    return raw, None


# Ρύθμιση σελίδας (ATLAS Lite)
st.set_page_config(
    page_title="ATLAS Lite",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Global CSS (Fira Sans — ίδια με εκτυπώσεις / χρονολόγια· Streamlit ενίοτε εφαρμόζει serif σε τίτλους)
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap');
html, body, .stApp, [data-testid="stAppViewContainer"] {
  font-family: "Fira Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
/* Κεφαλίδες/κείμενο Streamlit (st.markdown, caption, tabs) — override theme serif */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp p, .stApp li, .stApp label,
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] span,
.stApp [data-testid="stMarkdownContainer"] li,
.stApp [data-testid="stCaption"],
.stApp [data-testid="stHeading"] h1,
.stApp [data-testid="stHeading"] h2,
.stApp [data-testid="stHeading"] h3,
.stApp [data-baseweb="tab"],
.stApp .stButton > button {
  font-family: "Fira Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
}
.stApp pre, .stApp code, .stApp .stCodeBlock {
  font-family: ui-monospace, "Cascadia Code", "Segoe UI Mono", Consolas, monospace !important;
}
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #888; border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: #555; }
</style>
""",
    unsafe_allow_html=True,
)
components.html("""
<script async src="https://www.googletagmanager.com/gtag/js?id=G-34VGNYK55C"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-34VGNYK55C');
</script>
""", height=0)

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

# CSS Design System: ίδιο για Kyria και Lite (Lite ακριβώς ίδιο frontend, μόνο κεφαλίδα "ATLAS Lite")
if True:
    st.markdown("""
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
    --color-warning: #996600;
    --color-error: #cc0000;
    --color-link: #0056b3;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
    --shadow-lg: 0 10px 30px rgba(0,0,0,0.08);
    --transition: all 0.2s ease;
}

.stApp { background-color: var(--color-bg); }
html, body, [data-testid="stAppViewContainer"], .block-container {
    font-family: var(--font-main) !important;
    font-size: 17px;
    color: var(--color-text);
}

/* Στενό UI: κεντραρισμένο πλάτος και για Κυρία και για Lite (πριν το HTML blob) */
[data-testid="stAppViewContainer"] .block-container {
    max-width: 900px;
    margin-left: auto;
    margin-right: auto;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}

/* --- Professional Header (results page) --- */
.professional-header {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
    color: #ffffff;
    padding: 0.8rem 1.5rem;
    margin: -4rem -5rem 0.5rem -5rem;
    box-shadow: var(--shadow-md);
}
.header-content {
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: none;
    margin: 0;
    padding: 0 0.5rem;
}
.header-left { display: flex; align-items: center; gap: 1rem; }
.header-text h1 { margin: 0; font-size: 1.35rem; font-weight: 700; letter-spacing: 0.2px; }
.header-center {
    position: absolute; left: 50%; transform: translateX(-50%);
    font-size: 1.25rem; font-weight: 800; color: #ffffff !important;
    text-align: center; white-space: nowrap; pointer-events: none;
}
.header-right { display: flex; gap: 1.5rem; }
.nav-link {
    color: #ffffff !important; text-decoration: none; font-weight: 600;
    padding: 0.5rem 1.2rem; border: 1px solid rgba(255,255,255,0.5);
    border-radius: var(--radius-sm); transition: var(--transition); display: inline-block;
}
.nav-link:hover {
    background-color: rgba(255,255,255,0.15); border-color: #ffffff;
    text-decoration: none !important; color: #ffffff !important;
    transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* --- Purple Header (landing page) --- */
.purple-header {
    background: linear-gradient(135deg, #7b2cbf 0%, var(--color-primary-dark) 100%);
    color: white; text-align: center; padding: 2rem 1rem;
    margin: -4rem -5rem 2rem -5rem; font-size: 2rem; font-weight: 700;
    box-shadow: var(--shadow-md);
}

/* --- Inputs: white background --- */
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div,
.stTextInput input, .stDateInput input, .stNumberInput input, .stTextArea textarea,
div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    background-color: var(--color-surface) !important;
    border-color: #d0d7de !important;
    box-shadow: inset 0 1px 2px rgba(16,24,40,0.04) !important;
}

/* --- Buttons --- */
.stButton > button {
    width: 100%; font-size: 1.1rem; padding: 0.5rem 1rem;
    font-family: var(--font-main) !important; font-weight: 600;
    border-radius: var(--radius-sm); transition: var(--transition);
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}

/* --- Streamlit messages: accent left-border --- */
div[data-testid="stAlert"] > div {
    border-left: 4px solid currentColor !important;
    border-radius: var(--radius-sm) !important;
    font-family: var(--font-main) !important;
}

/* --- All headings & markdown text --- */
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
    letter-spacing: 0.2px;
}

/* --- Expander titles --- */
div[data-testid="stExpander"] details summary p {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    font-family: var(--font-main) !important;
}

/* --- Tabs: συμπαγή γραμμή, μικρότερο κείμενο, λιγότερο κενό --- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.2rem 0.45rem !important;
    flex-wrap: wrap !important;
    row-gap: 0.25rem !important;
    border-bottom: 1px solid var(--color-border) !important;
    padding-bottom: 0 !important;
}
.stTabs [data-baseweb="tab-list"] button {
    padding: 0.32rem 0.55rem 0.42rem !important;
    min-height: 0 !important;
    margin: 0 !important;
    border-radius: 8px 8px 0 0 !important;
    border: 1px solid transparent !important;
    border-bottom: none !important;
    background: transparent !important;
    transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease !important;
}
.stTabs [data-baseweb="tab-list"] button:hover {
    background: rgba(111, 66, 193, 0.06) !important;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background: var(--color-surface) !important;
    border-color: var(--color-border) !important;
    border-bottom: 2px solid var(--color-primary) !important;
    margin-bottom: -1px !important;
    box-shadow: 0 -1px 0 var(--color-surface) !important;
}
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
    letter-spacing: -0.015em !important;
    margin: 0 !important;
    font-family: var(--font-main) !important;
    color: #1e293b !important;
    -webkit-font-smoothing: antialiased !important;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] [data-testid="stMarkdownContainer"] p {
    color: #4c1d95 !important;
    font-weight: 800 !important;
}

/* --- Metrics --- */
div[data-testid="stMetric"] label {
    font-family: var(--font-main) !important;
    font-weight: 600 !important;
    color: var(--color-text-subtle) !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: var(--font-main) !important;
    font-weight: 800 !important;
}

/* --- Upload area --- */
.upload-section {
    background-color: transparent; padding: 1.5rem 1rem;
    border-radius: var(--radius-md); border: 0;
    text-align: center; margin: 1rem 0 2rem 0;
}
[data-testid="stFileUploader"] {
    background-color: #f8fbff; padding: 3rem;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    border: 2px dashed #3b82f6;
    transition: var(--transition);
}
div[data-testid="stFileUploader"] {
    margin-left: auto !important; margin-right: auto !important;
    max-width: 600px !important;
}
.upload-prompt-text {
    font-size: 1.2rem; font-weight: 600; color: var(--color-text);
    margin-bottom: 1rem; text-align: center !important;
    width: 100%; display: block;
}

/* --- Links --- */
.efka-link { color: var(--color-link) !important; text-decoration: none; font-weight: 400; font-size: 1rem; }
.efka-link:hover { text-decoration: underline; color: #003d82 !important; }

/* --- Instructions box --- */
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

/* --- Footer --- */
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

/* --- Container helpers --- */
.app-container { max-width: 680px; margin: 0 auto; }

/* --- Dataframe toolbar --- */
[data-testid="stDataFrame"] button { transform: scale(1.5) !important; margin: 0.3rem !important; }
[data-testid="stDataFrame"] button svg { width: 22px !important; height: 22px !important; }
div[data-testid="stDataFrameToolbar"] button {
    transform: scale(1.5) !important; transform-origin: center !important;
    margin: 0.3rem !important; padding: 0.3rem !important;
}
div[data-testid="stDataFrameToolbar"] { padding: 0.5rem !important; z-index: 1000 !important; position: relative !important; }
div[data-testid="stDataFrame"] { z-index: 1 !important; position: relative !important; }
body > div[data-baseweb="popover"], body > div[role="dialog"] { z-index: 10000 !important; }

/* --- Hide Streamlit chrome --- */
[data-testid="stHeader"] button[kind="header"],
[data-testid="stHeader"] [data-testid="stDeployButton"],
button[kind="header"], .stDeployButton,
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] [data-testid="stToolbar"],
header[data-testid="stHeader"] [data-testid="stHeaderViewButton"],
header[data-testid="stHeader"] [data-testid="stHeaderActionElements"],
header[data-testid="stHeader"] > div:last-child,
header[data-testid="stHeader"] > div:nth-child(2),
div[class*="viewerBadge"], a[class*="viewerBadge"],
button[class*="viewerBadge"], div[data-testid="stToolbarActionButton"] {
    display: none !important; visibility: hidden !important;
}
</style>
""", unsafe_allow_html=True)

def build_print_table_html(
    dataframe: pd.DataFrame,
    style_rows: list[dict[str, str]] | None = None,
    wrap_cells: bool = False,
    bold_columns: list[str] | None = None,
    col_width_overrides: dict[str, str] | None = None,
) -> str:
    _bold_cols = set(bold_columns or [])
    _width_ov = col_width_overrides or {}

    colgroup_html = '<colgroup>'
    for col in dataframe.columns:
        c_name = str(col).upper().strip()
        if col in _width_ov:
            width = _width_ov[col]
        elif c_name in ['A/A', 'Α/Α', 'AA']:
            width = '20px'
        elif c_name in ['ΕΤΟΣ', 'ETOS', 'ΈΤΟΣ']:
            width = '28px'
        elif c_name in ['ΤΑΜΕΙΟ', 'TAMEIO']:
            width = '38px'
        elif c_name in ['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ']:
            width = '38px'
        elif c_name in ['ΕΡΓΟΔΟΤΗΣ']:
            width = '42px'
        elif 'ΚΛΑΔΟΣ' in c_name:
            width = '22px'
        elif c_name in ['ΠΕΡΙΓΡΑΦΗ']:
            width = '72px'
        elif 'ΑΠΟΔΟΧΩΝ' in c_name and 'ΤΥΠΟΣ' in c_name:
            width = '22px'
        elif c_name in ['ΣΥΝΟΛΟ']:
            width = '28px'
        elif c_name.endswith('ος') or c_name in ['ΙΑΝ', 'ΦΕΒ', 'ΜΑΡ', 'ΑΠΡ', 'ΜΑΙ', 'ΙΟΥΝ', 'ΙΟΥΛ', 'ΑΥΓ', 'ΣΕΠ', 'ΟΚΤ', 'ΝΟΕ', 'ΔΕΚ']:
            width = '38px'
        elif 'ΜΙΚΤΕΣ' in c_name or 'ΜΙΚΤΈΣ' in c_name:
            width = '52px'
        elif 'ΕΙΣΦΟΡΕΣ' in c_name or 'ΕΙΣΦΟΡΈΣ' in c_name:
            width = '52px'
        elif 'ΠΟΣΟΣΤΟ' in c_name:
            width = '30px'
        else:
            width = 'auto'
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
            if col_name in _bold_cols:
                cell_style = (cell_style + '; ' if cell_style else '') + 'font-weight:700'
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
        "<strong>ΣΗΜΑΝΤΙΚH ΣΗΜΕΙΩΣΗ:</strong> Η παρούσα αναφορά βασίζεται αποκλειστικά στα δεδομένα που εμφανίζονται στο αρχείο ΑΤΛΑΣ/e-ΕΦΚΑ και αποτελεί απλή επεξεργασία των καταγεγραμμένων εγγραφών. "
        "Η πλατφόρμα ΑΤΛΑΣ μπορεί να περιέχει κενά ή σφάλματα και η αναφορά αυτή δεν υποκαθιστά νομική ή οικονομική συμβουλή σε καμία περίπτωση. "
        "Για θέματα συνταξιοδότησης και οριστικές απαντήσεις αρμόδιος παραμένει αποκλειστικά ο e-ΕΦΚΑ."
        "</div>"
    )

# Σημείωση για καρτέλα/εκτύπωση Κενά (κενά και διαστήματα χωρίς ημέρες)
GAPS_NOTE = (
    "Τα διαστήματα χωρίς ημέρες ασφάλισης αναφέρονται αυτούσια στο αρχείο ΑΤΛΑΣ χωρίς ημέρες ασφάλισης. "
    "Ωστόσο, δεν αποτελούν εξ ορισμού κενό διάστημα καθώς μπορεί να επικαλύπτονται μερικώς από άλλες εγγραφές που να έχουν ημέρες ασφάλισης. "
    "Απαιτείται λεπτομερής έλεγχος."
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

def build_yearly_print_html(
    dataframe: pd.DataFrame,
    year_column: str = 'ΕΤΟΣ',
    style_rows: list[dict[str, str]] | None = None,
    wrap_cells: bool = False,
    extra_group_cols: list[str] | None = None,
    bold_columns: list[str] | None = None,
    col_width_overrides: dict[str, str] | None = None,
    collapse_cols: list[str] | None = None,
) -> str:
    """Σπάει DataFrame ανά έτος (+ extra_group_cols) σε ξεχωριστούς πίνακες.
    Αφαιρεί τις στήλες ομαδοποίησης από τον πίνακα. Κρατά total-rows μέσα στο group τους.
    collapse_cols: στήλες που εμφανίζονται μία φορά (κενό όταν επαναλαμβάνεται) με bold.
    """
    if year_column not in dataframe.columns:
        return build_print_table_html(dataframe, style_rows, wrap_cells=wrap_cells,
                                       bold_columns=bold_columns, col_width_overrides=col_width_overrides)

    year_alt = None
    for c in dataframe.columns:
        if c.strip().upper() in ('ΕΤΟΣ', 'ΈΤΟΣ', 'YEAR', 'Έτος'):
            year_alt = c
            break
    if year_alt:
        year_column = year_alt

    _extra = extra_group_cols or []
    all_group_cols = [year_column] + [c for c in _extra if c in dataframe.columns]

    def _group_key(row_idx: int) -> str:
        vals = [str(dataframe.iloc[row_idx].get(c, '')).strip() for c in all_group_cols]
        return ' | '.join(v for v in vals if v)

    # Γραμμές συνόλου στην καταμέτρηση έχουν κενό ΕΤΟΣ· το έτος είναι στην ΠΕΡΙΓΡΑΦΗ («ΣΥΝΟΛΟ 2020 — …»).
    _total_desc_year = re.compile(r"ΣΥΝΟΛΟ\s+(\d{4})")
    _last_effective: str | None = None

    def _effective_group_key(row_idx: int) -> str:
        nonlocal _last_effective
        k = _group_key(row_idx)
        if k:
            _last_effective = k
            return k
        desc = str(dataframe.iloc[row_idx].get("ΠΕΡΙΓΡΑΦΗ", "") or "")
        md = _total_desc_year.search(desc)
        if md:
            _last_effective = md.group(1)
            return _last_effective
        if _last_effective:
            return _last_effective
        out = f"row_{row_idx}"
        _last_effective = out
        return out

    sections: list[str] = []
    current_key: str | None = None
    current_rows: list[int] = []

    for idx in range(len(dataframe)):
        is_empty_row = all(
            str(dataframe.iloc[idx].get(c, '')).strip() == ''
            for c in dataframe.columns
        )
        if is_empty_row:
            continue

        row_key = _effective_group_key(idx)
        if current_key is None or row_key != current_key:
            if current_rows and current_key is not None:
                sections.append(_render_year_section(
                    dataframe, current_rows, current_key, all_group_cols,
                    style_rows, wrap_cells, bold_columns, col_width_overrides, collapse_cols
                ))
            current_key = row_key
            current_rows = [idx]
        else:
            current_rows.append(idx)

    if current_rows and current_key:
        sections.append(_render_year_section(
            dataframe, current_rows, current_key, all_group_cols,
            style_rows, wrap_cells, bold_columns, col_width_overrides, collapse_cols
        ))

    return "\n".join(sections)


def _render_year_section(
    dataframe: pd.DataFrame,
    row_indices: list[int],
    heading_label: str,
    drop_columns: list[str],
    style_rows: list[dict[str, str]] | None,
    wrap_cells: bool,
    bold_columns: list[str] | None = None,
    col_width_overrides: dict[str, str] | None = None,
    collapse_cols: list[str] | None = None,
) -> str:
    subset = dataframe.iloc[row_indices].copy()
    for col in drop_columns:
        if col in subset.columns:
            subset = subset.drop(columns=[col])

    _collapse = [c for c in (collapse_cols or []) if c in subset.columns]
    sub_styles = []
    if _collapse:
        subset = subset.reset_index(drop=True)
        sort_cols = [c for c in _collapse if c in subset.columns]
        if sort_cols:
            subset = subset.sort_values(sort_cols, kind='stable').reset_index(drop=True)
        prev_vals = {c: None for c in _collapse}
        for i in range(len(subset)):
            row_style = {}
            for col in _collapse:
                val = subset.iloc[i][col]
                val_str = str(val).strip() if pd.notna(val) else ''
                prev_str = str(prev_vals.get(col) or '').strip()
                if val_str == prev_str:
                    subset.iloc[i, subset.columns.get_loc(col)] = ''
                else:
                    if val_str:
                        prev_vals[col] = val
                        row_style[col] = 'font-weight: 700'
            sub_styles.append(row_style)
    elif style_rows:
        for idx in row_indices:
            if idx < len(style_rows):
                row_style = dict(style_rows[idx])
                for col in drop_columns:
                    row_style.pop(col, None)
                sub_styles.append(row_style)
            else:
                sub_styles.append({})

    if not sub_styles:
        sub_styles = None

    table_html = build_print_table_html(
        subset.reset_index(drop=True), sub_styles, wrap_cells=wrap_cells,
        bold_columns=bold_columns, col_width_overrides=col_width_overrides
    )
    return (
        f"<div class='year-section'>"
        f"<div class='year-heading'>{html.escape(str(heading_label))}</div>"
        f"{table_html}"
        f"</div>"
    )


def wrap_print_html(
    title: str,
    body_html: str,
    auto_print: bool = True,
    scale: float = 1.0,
) -> str:
    # Μην βάζετε backslash μέσα σε {…} σε f-string (SyntaxError σε Python < 3.12)
    _body_onload = ' onload="window.print()"' if auto_print else ""
    return f"""<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    @media print {{ @page {{ size: A4 landscape; margin: 8mm; }} }}
    :root {{ --print-scale: {scale}; }}
    * {{ box-sizing: border-box; }}
    body {{
        font-family: "Fira Sans", -apple-system, Segoe UI, Roboto, Arial, sans-serif;
        color: #222; line-height: 1.45; margin: 0; padding: 8px;
    }}
    h1 {{
        font-size: 22px; font-weight: 700; margin: 14px 0 6px 0; text-align: center;
        color: #111827; letter-spacing: 0.2px;
    }}
    h2 {{ font-size: 17px; font-weight: 700; margin: 20px 0 10px 0; text-align: left; color: #2c3e50; }}
    .print-section {{ margin-bottom: 22px; }}
    .page-break {{ page-break-after: always; }}
    .print-client-name {{
        font-size: 26px; font-weight: 800; text-align: center; margin: 0;
        color: #111827; letter-spacing: 0.3px;
    }}
    .print-client-amka {{
        font-size: 14px; text-align: center; margin: 3px 0 4px 0; color: #6b7280; font-weight: 400;
    }}
    .print-client-birthdate {{
        font-size: 14px; text-align: center; margin: 0 0 12px 0; color: #6b7280; font-weight: 400;
    }}
    .print-description {{
        font-size: 14px; text-align: center; color: #6b7280; margin: 0 0 10px 0;
        font-style: italic;
    }}
    .print-filters {{ font-size: 11px; margin: 0 0 10px 0; color: #374151; }}
    .print-filters-label {{ font-weight: 600; margin-bottom: 2px; }}
    .print-filters ul {{ margin: 4px 0 0 18px; padding: 0; }}
    .print-disclaimer {{
        font-size: 12px; color: #6b7280; margin-top: 30px; padding-top: 12px;
        border-top: 1px solid #e5e7eb; line-height: 1.5;
    }}
    .print-disclaimer strong {{ font-weight: 700; color: #374151; }}

    /* --- Table --- */
    table.print-table {{
        border-collapse: collapse; width: 100%; font-size: 8.5px; table-layout: fixed;
        border: none;
    }}
    table.print-table thead th {{
        background: #f3f4f6;
        border-bottom: 1px solid #d0d7de; border-right: none; border-left: none; border-top: none;
        padding: 3px 2px; text-align: left; font-weight: 700; color: #111827;
        font-size: 7.5px; letter-spacing: 0;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    table.print-table tbody td {{
        border-bottom: 0.5px solid #e8eaed; border-right: none; border-left: none; border-top: none;
        padding: 2px 2px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    table.print-table tbody tr:nth-child(even) td {{ background-color: #f9fafb; }}
    table.print-table tbody td:first-child {{ font-weight: 700; }}
    table.print-table tbody tr.total-row td {{
        background: #dbeafe !important; color: #000; font-weight: 700 !important;
        border-top: 1px solid #93c5fd;
    }}
    table.print-table.wrap-cells thead th,
    table.print-table.wrap-cells tbody td {{
        white-space: normal; overflow: visible; text-overflow: clip; word-break: break-word;
    }}
    /* --- Yearly sections --- */
    .year-section {{ margin-bottom: 18px; }}
    .year-heading {{
        font-size: 15px; font-weight: 800; color: #1e293b;
        padding: 6px 0 4px 2px; margin-top: 12px;
        border-bottom: 2px solid #6f42c1; margin-bottom: 4px;
        letter-spacing: 0.3px;
    }}
    #print-root {{ width: 100%; }}
  </style>
</head>
<body{_body_onload}>
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
    client_birthdate: str | None = None,
    auto_print: bool = True,
    scale: float = 1.0,
    wrap_cells: bool = False,
    yearly: bool = False,
    year_column: str = 'ΕΤΟΣ',
    extra_group_cols: list[str] | None = None,
    bold_columns: list[str] | None = None,
    col_width_overrides: dict[str, str] | None = None,
    footer_note: str | None = None,
) -> str:
    client_name = (client_name or '').strip()
    client_amka = (client_amka or '').strip()
    client_birthdate = (client_birthdate or '').strip()
    name_html = f"<div class='print-client-name'>{html.escape(client_name)}</div>" if client_name else ''
    amka_html = f"<div class='print-client-amka'>ΑΜΚΑ: {html.escape(client_amka)}</div>" if client_amka else ''
    birthdate_html = f"<div class='print-client-birthdate'>Ημ/νία γέννησης: {html.escape(client_birthdate)}</div>" if client_birthdate else ''
    description_html = f"<p class='print-description'>{html.escape(description)}</p>" if description else ''
    filters_html = build_print_filters_html(filters)
    if yearly:
        table_html = build_yearly_print_html(
            dataframe, year_column=year_column, style_rows=style_rows, wrap_cells=wrap_cells,
            extra_group_cols=extra_group_cols, bold_columns=bold_columns, col_width_overrides=col_width_overrides
        )
    else:
        table_html = build_print_table_html(
            dataframe, style_rows, wrap_cells=wrap_cells,
            bold_columns=bold_columns, col_width_overrides=col_width_overrides
        )
    disclaimer_html = get_print_disclaimer_html()
    footer_note_html = (
        f"<p class='print-description' style='margin-top:1.25em; padding:0.5em 0; border-top:1px solid #e2e8f0; font-size:0.95em;'>{html.escape(footer_note)}</p>"
        if footer_note else ""
    )
    body_html = (
        f"{name_html}"
        f"{amka_html}"
        f"{birthdate_html}"
        f"<h1>{html.escape(title)}</h1>"
        f"{description_html}"
        f"{filters_html}"
        f"{table_html}"
        f"{footer_note_html}"
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
    yearly: bool = False,
    year_column: str = 'ΕΤΟΣ',
    extra_group_cols: list[str] | None = None,
    bold_columns: list[str] | None = None,
    col_width_overrides: dict[str, str] | None = None,
    footer_note: str | None = None,
    download_data: str | bytes | None = None,
    download_file_name: str = "export.json",
    download_label: str = "Λήψη",
    download_key: str | None = None,
    download_mime: str = "application/json",
) -> None:
    if download_data is not None:
        # Λήψη πριν την εκτύπωση· ευρύτερη στήλη ώστε το κείμενο να μην ανασπάται
        _col_sp, col_download, col_print = st.columns([1, 0.38, 0.12])
    else:
        _col_sp, col_print = st.columns([1, 0.12])
        col_download = None

    if download_data is not None and col_download is not None:
        with col_download:
            _dl_lbl = download_label.replace(" ", "\u00a0")
            st.download_button(
                label=_dl_lbl,
                data=download_data,
                file_name=download_file_name,
                mime=download_mime,
                width="content",
                key=download_key or f"{button_key}_download",
                type="primary",
            )

    with col_print:
        if st.button("Εκτύπωση", key=button_key, width="stretch"):
            # Μοναδικό nonce ώστε το component να επανα-τοποθετείται και να εκτελείται κάθε φορά
            nonce_key = f"_print_nonce_{button_key}"
            nonce = st.session_state.get(nonce_key, 0) + 1
            st.session_state[nonce_key] = nonce
            window_name = f"printwin_{button_key}_{nonce}"
            client_name = st.session_state.get('print_client_name', '').strip()
            client_amka = st.session_state.get('print_client_amka', '').strip()
            client_birthdate = st.session_state.get('print_client_birthdate', '').strip()
            html_content = build_print_html(
                title=title,
                dataframe=dataframe,
                description=description,
                filters=filters,
                style_rows=style_rows,
                client_name=client_name,
                client_amka=client_amka,
                client_birthdate=client_birthdate,
                scale=scale,
                yearly=yearly,
                year_column=year_column,
                extra_group_cols=extra_group_cols,
                bold_columns=bold_columns,
                col_width_overrides=col_width_overrides,
                footer_note=footer_note,
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
    if not PDFPLUMBER_AVAILABLE:
        st.error(
            "Λείπει το πακέτο **pdfplumber**. Τοπικά: `pip install pdfplumber`. "
            "Στο Streamlit Cloud: στη ρίζα του repo πρέπει να υπάρχει `requirements.txt` με `pdfplumber`· "
            "στο μενού της εφαρμογής κάντε **Manage app → Reboot** ή νέο deploy."
        )
        return []

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
    """Επιστρέφει -1 όταν υπάρχουν αρνητικά ποσά (διαγραφή εγγραφής)."""
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

def find_negative_entries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Εντοπίζει εγγραφές με αρνητικές αποδοχές ή εισφορές (διαγραφές χρόνου).
    Επιστρέφει DataFrame με τις σχετικές εγγραφές, έτοιμο για εμφάνιση.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    gross_col = 'Μικτές αποδοχές' if 'Μικτές αποδοχές' in df.columns else None
    contrib_col = 'Συνολικές εισφορές' if 'Συνολικές εισφορές' in df.columns else (
        'Συνολικές Εισφορές' if 'Συνολικές Εισφορές' in df.columns else None)

    if not gross_col and not contrib_col:
        return pd.DataFrame()

    neg_mask = pd.Series(False, index=df.index)
    if gross_col:
        neg_mask = neg_mask | df[gross_col].apply(lambda x: (clean_numeric_value(x, exclude_drx=True) or 0) < 0)
    if contrib_col:
        neg_mask = neg_mask | df[contrib_col].apply(lambda x: (clean_numeric_value(x, exclude_drx=True) or 0) < 0)

    neg_df = df[neg_mask]
    if neg_df.empty:
        return pd.DataFrame()

    columns_to_show = []
    for col in ['Από', 'Έως', 'Ταμείο', 'Τύπος Ασφάλισης', 'Κλάδος/Πακέτο Κάλυψης',
                 'Α-Μ εργοδότη', 'Έτη', 'Μήνες', 'Ημέρες']:
        if col in neg_df.columns:
            columns_to_show.append(col)
    if gross_col:
        columns_to_show.append(gross_col)
    if contrib_col:
        columns_to_show.append(contrib_col)

    return neg_df[columns_to_show].copy()


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
            calendar_days = (gap_end - gap_start).days + 1
            # Εκτίμηση ημερών ασφάλισης: κάθε 30 ημερολογιακές ημέρες -> 25 ημέρες ασφάλισης (στρογγυλοποίηση προς τα κάτω)
            insured_days_est = int((calendar_days * 25) // 30)
            gaps.append({
                'Από': gap_start.strftime('%d/%m/%Y'),
                'Έως': gap_end.strftime('%d/%m/%Y'),
                'Ημερολογιακές ημέρες': calendar_days,
                'Ημέρες Ασφ.': insured_days_est,
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


def find_zero_duration_intervals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Εντοπίζει διαστήματα που εμφανίζονται στο ΑΤΛΑΣ αλλά χωρίς τιμές σε Έτη/Μήνες/Ημέρες.
    Επιστρέφει DataFrame έτοιμο για εμφάνιση.
    """
    if 'Από' not in df.columns or 'Έως' not in df.columns:
        return pd.DataFrame()

    zero_duration_df = df.copy()
    zero_duration_df['Από_DateTime'] = pd.to_datetime(zero_duration_df['Από'], format='%d/%m/%Y', errors='coerce')
    zero_duration_df['Έως_DateTime'] = pd.to_datetime(zero_duration_df['Έως'], format='%d/%m/%Y', errors='coerce')
    zero_duration_df = zero_duration_df.dropna(subset=['Από_DateTime', 'Έως_DateTime'])

    duration_columns = ['Έτη', 'Μήνες', 'Ημέρες']
    for col in duration_columns:
        if col not in zero_duration_df.columns:
            zero_duration_df[col] = 0
        numeric_col = f"__{col}_numeric"
        zero_duration_df[numeric_col] = zero_duration_df[col].apply(clean_numeric_value)

    zero_duration_df['__duration_sum'] = (
        zero_duration_df['__Έτη_numeric'] +
        zero_duration_df['__Μήνες_numeric'] +
        zero_duration_df['__Ημέρες_numeric']
    )

    if not zero_duration_df.empty:
        zero_duration_df['__duration_sum_group'] = zero_duration_df.groupby(
            ['Από_DateTime', 'Έως_DateTime']
        )['__duration_sum'].transform('sum')

    zero_duration_df = zero_duration_df[
        (zero_duration_df['__duration_sum'] == 0) &
        (zero_duration_df['__duration_sum_group'] == 0)
    ]

    if zero_duration_df.empty:
        return pd.DataFrame()

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
    drop_helpers = [c for c in zero_display_df.columns if c.startswith('__')]
    zero_display_df = zero_display_df.drop(columns=drop_helpers, errors='ignore')

    if 'Έτη' in zero_display_df.columns:
        zero_display_df['Έτη'] = zero_display_df['Έτη'].apply(lambda x: format_number_greek(x, decimals=1) if str(x).strip() not in ['', '-'] else '')
    if 'Μήνες' in zero_display_df.columns:
        zero_display_df['Μήνες'] = zero_display_df['Μήνες'].apply(lambda x: format_number_greek(x, decimals=1) if str(x).strip() not in ['', '-'] else '')
    if 'Ημέρες' in zero_display_df.columns:
        zero_display_df['Ημέρες'] = zero_display_df['Ημέρες'].apply(lambda x: format_number_greek(x, decimals=0) if str(x).strip() not in ['', '-'] else '')

    return zero_display_df


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
    Κανονικοποίηση ονομάτων στηλών με mapping σε standard names.
    Υποστηρίζει κεφαλές που εμφανίζονται «σε μια λέξη» (π.χ. PDF από Firefox: ΣυνολικέςΕισφορές, Κλάδος/ΠακέτοΚάλυψης).
    """
    # Mapping από patterns -> standard name (με προτεραιότητα - πιο συγκεκριμένα πρώτα)
    column_mapping = {
        'Συνολικές εισφορές': ['συνολικές εισφορές', 'συνολικες εισφορες', 'συνολικ εισφορ', 'συνολικέςεισφορές', 'συνολικεςεισφορες'],
        'Μικτές αποδοχές': ['μικτές αποδοχές', 'μικτες αποδοχες', 'μικτ αποδοχ', 'μικτέςαποδοχές', 'μικτεςαποδοχες'],
        'Τύπος Αποδοχών': ['τύπος αποδοχών', 'τυπος αποδοχων', 'τυπος απο', 'τύποςαποδοχών', 'τυποςαποδοχων'],
        'Τύπος Ασφάλισης': ['τύπος ασφάλισης', 'τυπος ασφαλισης', 'μημισθωτηασφαλιση', 'μισθωτήασφάλιση', 'μισθωτη ασφαλιση'],
        'Κλάδος/Πακέτο Κάλυψης': ['κλάδος πακέτο κάλυψης', 'κλαδος πακετο καλυψης', 'κλάδος', 'πακέτο κάλυψης', 'κλάδος/πακέτοκάλυψης', 'κλαδοςπακετοκαλυψης'],
        'Α-Μ εργοδότη': ['α μ εργοδότη', 'α/μ εργοδ', 'εργοδότη', 'α-μ εργοδότη', 'αμεργοδότη', 'α-μεργοδότη'],
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
        col_no_space = col_normalized.replace(' ', '').replace('/', '').replace('-', '').replace('_', '')
        
        # Ελέγχουμε για κάθε standard name (με τη σειρά προτεραιότητας)
        matched = False
        for standard_name, patterns in column_mapping.items():
            if standard_name in used_standards:
                continue
                
            # Έλεγχος για match
            for pattern in patterns:
                # Ελέγχουμε αν το pattern ταιριάζει
                if pattern == col_normalized:
                    rename_dict[col] = standard_name
                    used_standards.add(standard_name)
                    matched = True
                    break
                elif len(pattern) > 5 and pattern in col_normalized:
                    rename_dict[col] = standard_name
                    used_standards.add(standard_name)
                    matched = True
                    break
                elif len(col_normalized) > 5 and col_normalized in pattern:
                    rename_dict[col] = standard_name
                    used_standards.add(standard_name)
                    matched = True
                    break
                # Παραλλαγή «μία λέξη» (π.χ. από Firefox): στήλη χωρίς κενά/παύλες = standard χωρίς κενά/παύλες
                pattern_no_space = pattern.replace(' ', '').replace('/', '').replace('-', '').replace('_', '')
                if len(pattern_no_space) >= 3 and (col_no_space == pattern_no_space or pattern_no_space in col_no_space or col_no_space in pattern_no_space):
                    rename_dict[col] = standard_name
                    used_standards.add(standard_name)
                    matched = True
                    break
            
            if matched:
                break
        
        if matched:
            continue
        # Fallback: standard name χωρίς κενά/σύμβολα = στήλη χωρίς κενά/σύμβολα
        for standard_name in column_mapping:
            if standard_name in used_standards:
                continue
            standard_no_space = standard_name.lower().replace(' ', '').replace('/', '').replace('-', '').replace('_', '')
            if len(standard_no_space) >= 3 and (col_no_space == standard_no_space or standard_no_space in col_no_space):
                rename_dict[col] = standard_name
                used_standards.add(standard_name)
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
        with nullcontext():
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

    # Έως 2016: μην μετράνε πακέτα 127, 131, 132, 133, 026
    if 'Κλάδος/Πακέτο Κάλυψης' in base_df.columns:
        pkg = base_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
        base_df = base_df[~pkg.isin(EXCLUDED_PACKAGES_PARALLEL_UNTIL_2016)].copy()
    if base_df.empty:
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

        if (has_ika and has_oaee) or (has_ika and has_tsm) or (has_oaee and has_tsm) or (has_oga and (has_ika or has_oaee)):
            if year <= 2016:
                valid_months.append((year, month))

    return valid_months

def compute_parallel_months_2017(base_df: pd.DataFrame) -> list[tuple[int, int]]:
    """Μήνες πιθανής παράλληλης απασχόλησης από 01/2017 και μετά.
    Κριτήρια:
    - ΙΚΑ (αποδοχές 01/16/99) + ΕΦΚΑ μη μισθωτή
    - ΕΦΚΑ μισθωτή + ΕΦΚΑ μη μισθωτή
    """
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
                    'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': str(row.get('Τύπος Αποδοχών', '')).strip(),
                    'Ημέρες': days_per_month
                })
        except Exception:
            continue

    if not parallel_rows:
        return []

    p_df = pd.DataFrame(parallel_rows)

    def _is_ika(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        et = str(row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')).strip()
        is_ika_tameio = 'IKA' in t or 'ΙΚΑ' in t
        is_misthoti = 'ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type
        is_et_ika = et in ['01', '1', '16', '99']
        return (is_ika_tameio or is_misthoti) and is_et_ika

    def _is_efka_misthoti(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        is_efka = 'ΕΦΚΑ' in t or 'EFKA' in t
        is_misthoti = 'ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type
        return is_efka and is_misthoti

    def _is_efka_non_misthoti(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        is_efka = 'ΕΦΚΑ' in t or 'EFKA' in t
        is_non_misthoti = ('ΜΗ' in i_type and 'ΜΙΣΘΩΤΗ' in i_type) or ('NON' in i_type and 'SAL' in i_type)
        return is_efka and is_non_misthoti

    p_df['is_ika'] = p_df.apply(_is_ika, axis=1)
    p_df['is_efka_mis'] = p_df.apply(_is_efka_misthoti, axis=1)
    p_df['is_efka_non'] = p_df.apply(_is_efka_non_misthoti, axis=1)

    valid_months = []
    month_groups = p_df.groupby(['ΕΤΟΣ', 'Μήνας_Num'])
    for (year, month), group in month_groups:
        if year < 2017:
            continue
        ika_days = group.loc[group['is_ika'], 'Ημέρες'].sum()
        efka_mis_days = group.loc[group['is_efka_mis'], 'Ημέρες'].sum()
        efka_non_days = group.loc[group['is_efka_non'], 'Ημέρες'].sum()

        has_ika_non = ika_days > 0 and efka_non_days > 0
        has_efka_mix = efka_mis_days > 0 and efka_non_days > 0
        if has_ika_non or has_efka_mix:
            valid_months.append((year, month))

    return valid_months


EXCLUDED_PACKAGES_PARALLEL = {'Α', 'Λ', 'Υ', 'Ο', 'Χ', '026', '899'}

# Για παράλληλη έως 2016: εξαιρούνται και 127, 131, 132, 133 (και 026) ακόμα κι αν έχουν τύπο αποδοχών 01 κτλ με ημέρες
EXCLUDED_PACKAGES_PARALLEL_UNTIL_2016 = {'127', '131', '132', '133', '026'}


def _build_monthly_rows_for_parallel(df: pd.DataFrame, description_map: dict | None = None) -> list[dict]:
    """Κοινή λογική ανάλυσης ανά μήνα για Παράλληλη Ασφάλιση / Απασχόληση.
    Εξαιρούνται τα πακέτα Α, Λ, Υ, Ο, Χ, 026, 899 (όπως στην καταμέτρηση).
    """
    if not df.empty and 'Κλάδος/Πακέτο Κάλυψης' in df.columns:
        pkg = df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
        df = df[~pkg.isin(EXCLUDED_PACKAGES_PARALLEL)].copy()
    rows: list[dict] = []
    for _, row in df.iterrows():
        try:
            if pd.isna(row.get('Από')) or pd.isna(row.get('Έως')):
                continue
            start_dt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
            end_dt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')
            if pd.isna(start_dt) or pd.isna(end_dt):
                continue

            days_val = 0.0
            if 'Ημέρες' in row and pd.notna(row.get('Ημέρες')) and str(row.get('Ημέρες', '')).strip() != '':
                d = clean_numeric_value(row.get('Ημέρες'))
                if d is not None and d != 0:
                    days_val += float(d)
            if 'Έτη' in row and pd.notna(row.get('Έτη')):
                y = clean_numeric_value(row.get('Έτη'))
                if y is not None and y != 0:
                    days_val += float(y) * 300
            if 'Μήνες' in row and pd.notna(row.get('Μήνες')):
                m = clean_numeric_value(row.get('Μήνες'))
                if m is not None and m != 0:
                    days_val += float(m) * 25

            raw_gross = str(row.get('Μικτές αποδοχές', ''))
            gross_val = 0.0 if ('ΔΡΧ' in raw_gross.upper() or 'DRX' in raw_gross.upper()) else (clean_numeric_value(raw_gross, exclude_drx=True) or 0.0)
            raw_contrib = str(row.get('Συνολικές εισφορές', ''))
            contrib_val = 0.0 if ('ΔΡΧ' in raw_contrib.upper() or 'DRX' in raw_contrib.upper()) else (clean_numeric_value(raw_contrib, exclude_drx=True) or 0.0)
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

            for m_dt in months_list:
                rows.append({
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
                })
        except Exception:
            continue
    return rows


def _pivot_parallel_df(p_df_filtered: pd.DataFrame, month_map: dict) -> pd.DataFrame:
    """Pivot + cap + μορφοποίηση DataFrame παράλληλης για εκτύπωση."""
    idx_cols = ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']
    annual = p_df_filtered.groupby(idx_cols)[['Ημέρες', 'Μικτές_Part', 'Εισφορές_Part']].sum().reset_index()
    annual.rename(columns={'Ημέρες': 'ΣΥΝΟΛΟ', 'Μικτές_Part': 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'Εισφορές_Part': 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'}, inplace=True)

    piv = p_df_filtered.groupby(idx_cols + ['Μήνας_Num'])['Ημέρες'].sum().reset_index()
    piv = piv.pivot_table(index=idx_cols, columns='Μήνας_Num', values='Ημέρες', fill_value=0).reset_index()
    piv.rename(columns=month_map, inplace=True)

    out = annual.merge(piv, on=idx_cols, how='left')
    m_cols = [month_map[m] for m in sorted(month_map) if month_map[m] in out.columns]
    for c in m_cols:
        out[c] = pd.to_numeric(out[c], errors='coerce').fillna(0)

    tameio_upper = out['ΤΑΜΕΙΟ'].astype(str).str.upper()
    is_ika = tameio_upper.str.contains('ΙΚΑ|IKA', na=False)
    for c in m_cols:
        out.loc[~is_ika, c] = out.loc[~is_ika, c].clip(upper=25)
    out['ΣΥΝΟΛΟ'] = out[m_cols].sum(axis=1)

    out.rename(columns={
        'ΕΤΟΣ': 'Έτος', 'ΤΑΜΕΙΟ': 'Ταμείο', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': 'Τύπος Ασφάλισης',
        'ΕΡΓΟΔΟΤΗΣ': 'Εργοδότης', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': 'Κλάδος/Πακέτο', 'ΠΕΡΙΓΡΑΦΗ': 'Περιγραφή',
        'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': 'Τύπος Αποδοχών', 'ΣΥΝΟΛΟ': 'Σύνολο',
        'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ': 'Μικτές Αποδοχές', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ': 'Συνολικές Εισφορές'
    }, inplace=True)

    renamed_m_cols = [out.columns[out.columns.get_loc(c)] if c in out.columns else c for c in m_cols]
    for c in renamed_m_cols + ['Σύνολο']:
        if c in out.columns:
            out[c] = out[c].apply(lambda x: format_number_greek(x, decimals=0) if pd.notna(x) and x != 0 else '')
    for c in ['Μικτές Αποδοχές', 'Συνολικές Εισφορές']:
        if c in out.columns:
            out[c] = out[c].apply(format_currency)

    out = out.sort_values('Έτος')
    return out


def build_parallel_print_df(df: pd.DataFrame, description_map: dict | None = None) -> pd.DataFrame | None:
    """Παράγει το DataFrame Παράλληλης Ασφάλισης (≤2016) έτοιμο για εκτύπωση."""
    if df.empty or not all(c in df.columns for c in ['Από', 'Έως']):
        return None

    monthly_rows = _build_monthly_rows_for_parallel(df, description_map)
    if not monthly_rows:
        return None

    p_df = pd.DataFrame(monthly_rows)
    # Έως 2016: μην υπολογίζονται πακέτα 127, 131, 132, 133, 026 ακόμα και με τύπο αποδοχών 01 κτλ με ημέρες
    if 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ' in p_df.columns:
        pkg = p_df['ΚΛΑΔΟΣ/ΠΑΚΕΤΟ'].astype(str).str.strip()
        p_df = p_df[~pkg.isin(EXCLUDED_PACKAGES_PARALLEL_UNTIL_2016)].copy()
    if p_df.empty:
        return None

    p_df['ΕΤΟΣ'] = p_df['ΕΤΟΣ'].astype(int)
    p_df['Μήνας_Num'] = p_df['Μήνας_Num'].astype(int)

    def _is_ika_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        et = str(row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')).strip()
        return (('IKA' in t or 'ΙΚΑ' in t) or ('ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type)) and et in ['01', '1', '16', '99']

    def _is_oaee_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
        return ('OAEE' in t or 'ΟΑΕΕ' in t or 'TEBE' in t or 'ΤΕΒΕ' in t or 'TAE' in t or 'ΤΑΕ' in t) and kl in ['K', 'Κ']

    def _is_tsm_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
        return ('ΤΣΜΕΔΕ' in t or 'TSMEDE' in t) and kl in ['ΚΣ', 'ΠΚΣ', 'KS', 'PKS']

    def _is_oga_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        kl = str(row.get('ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', '')).strip().upper()
        return ('ΟΓΑ' in t or 'OGA' in t) and kl in ['K', 'Κ']

    def _is_ika_general(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        return ('IKA' in t or 'ΙΚΑ' in t) or ('ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type)

    p_df['is_ika'] = p_df.apply(_is_ika_match, axis=1)
    p_df['is_oaee'] = p_df.apply(_is_oaee_match, axis=1)
    p_df['is_tsm'] = p_df.apply(_is_tsm_match, axis=1)
    p_df['is_oga'] = p_df.apply(_is_oga_match, axis=1)
    p_df['is_ika_general'] = p_df.apply(_is_ika_general, axis=1)

    month_groups = p_df.groupby(['ΕΤΟΣ', 'Μήνας_Num'])
    valid_months = []
    for (year, month), group in month_groups:
        if year > 2016:
            continue
        ika_d = group.loc[group['is_ika'], 'Ημέρες'].sum()
        oaee_d = min(group.loc[group['is_oaee'], 'Ημέρες'].sum(), 25)
        tsm_d = min(group.loc[group['is_tsm'], 'Ημέρες'].sum(), 25)
        oga_d = min(group.loc[group['is_oga'], 'Ημέρες'].sum(), 25)
        if (ika_d > 0 and oaee_d > 0) or (ika_d > 0 and tsm_d > 0) or (oaee_d > 0 and tsm_d > 0) or (oga_d > 0 and (ika_d > 0 or oaee_d > 0)):
            valid_months.append((year, month))

    if not valid_months:
        return None

    valid_df = pd.DataFrame(valid_months, columns=['ΕΤΟΣ', 'Μήνας_Num'])
    filtered = p_df.merge(valid_df, on=['ΕΤΟΣ', 'Μήνας_Num'], how='inner')
    filtered = filtered[filtered['is_ika'] | filtered['is_oaee'] | filtered['is_tsm'] | filtered['is_oga']]
    filtered = filtered.drop(columns=['is_ika', 'is_oaee', 'is_tsm', 'is_oga', 'is_ika_general'])

    if filtered.empty:
        return None

    month_map = {1: 'ΙΑΝ', 2: 'ΦΕΒ', 3: 'ΜΑΡ', 4: 'ΑΠΡ', 5: 'ΜΑΙ', 6: 'ΙΟΥΝ', 7: 'ΙΟΥΛ', 8: 'ΑΥΓ', 9: 'ΣΕΠ', 10: 'ΟΚΤ', 11: 'ΝΟΕ', 12: 'ΔΕΚ'}
    return _pivot_parallel_df(filtered, month_map)


def build_parallel_2017_print_df(df: pd.DataFrame, description_map: dict | None = None) -> pd.DataFrame | None:
    """Παράγει το DataFrame Παράλληλης Απασχόλησης 2017+ έτοιμο για εκτύπωση."""
    if df.empty or not all(c in df.columns for c in ['Από', 'Έως']):
        return None

    monthly_rows = _build_monthly_rows_for_parallel(df, description_map)
    if not monthly_rows:
        return None

    p_df = pd.DataFrame(monthly_rows)
    p_df['ΕΤΟΣ'] = p_df['ΕΤΟΣ'].astype(int)
    p_df['Μήνας_Num'] = p_df['Μήνας_Num'].astype(int)

    def _is_ika(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        et = str(row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')).strip()
        return (('IKA' in t or 'ΙΚΑ' in t) or ('ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type)) and et in ['01', '1', '16', '99']

    def _is_efka_mis(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        return ('ΕΦΚΑ' in t or 'EFKA' in t) and ('ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type)

    def _is_efka_non(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        return ('ΕΦΚΑ' in t or 'EFKA' in t) and (('ΜΗ' in i_type and 'ΜΙΣΘΩΤΗ' in i_type) or ('NON' in i_type and 'SAL' in i_type))

    p_df['is_ika'] = p_df.apply(_is_ika, axis=1)
    p_df['is_efka_mis'] = p_df.apply(_is_efka_mis, axis=1)
    p_df['is_efka_non'] = p_df.apply(_is_efka_non, axis=1)

    month_groups = p_df.groupby(['ΕΤΟΣ', 'Μήνας_Num'])
    valid_months = []
    for (year, month), group in month_groups:
        if year < 2017:
            continue
        ika_d = group.loc[group['is_ika'], 'Ημέρες'].sum()
        efka_mis_d = group.loc[group['is_efka_mis'], 'Ημέρες'].sum()
        efka_non_d = group.loc[group['is_efka_non'], 'Ημέρες'].sum()
        if (ika_d > 0 and efka_non_d > 0) or (efka_mis_d > 0 and efka_non_d > 0):
            valid_months.append((year, month))

    if not valid_months:
        return None

    valid_df = pd.DataFrame(valid_months, columns=['ΕΤΟΣ', 'Μήνας_Num'])
    filtered = p_df.merge(valid_df, on=['ΕΤΟΣ', 'Μήνας_Num'], how='inner')
    filtered = filtered[filtered['is_ika'] | filtered['is_efka_mis'] | filtered['is_efka_non']]
    filtered = filtered.drop(columns=['is_ika', 'is_efka_mis', 'is_efka_non'])

    if filtered.empty:
        return None

    month_map = {1: 'ΙΑΝ', 2: 'ΦΕΒ', 3: 'ΜΑΡ', 4: 'ΑΠΡ', 5: 'ΜΑΙ', 6: 'ΙΟΥΝ', 7: 'ΙΟΥΛ', 8: 'ΑΥΓ', 9: 'ΣΕΠ', 10: 'ΟΚΤ', 11: 'ΝΟΕ', 12: 'ΔΕΚ'}
    return _pivot_parallel_df(filtered, month_map)


def build_multi_employment_print_df(df: pd.DataFrame, description_map: dict | None = None) -> pd.DataFrame | None:
    """Παράγει το DataFrame Πολλαπλής Απασχόλησης (ΙΚΑ, >1 εργοδότες) έτοιμο για εκτύπωση."""
    if df.empty or not all(c in df.columns for c in ['Από', 'Έως']):
        return None

    monthly_rows = _build_monthly_rows_for_parallel(df, description_map)
    if not monthly_rows:
        return None

    p_df = pd.DataFrame(monthly_rows)
    p_df['ΕΤΟΣ'] = p_df['ΕΤΟΣ'].astype(int)
    p_df['Μήνας_Num'] = p_df['Μήνας_Num'].astype(int)

    def _is_ika_match(row):
        t = str(row.get('ΤΑΜΕΙΟ', '')).upper()
        i_type = str(row.get('ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', '')).upper()
        et = str(row.get('ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', '')).strip()
        return (('IKA' in t or 'ΙΚΑ' in t) or ('ΜΙΣΘΩΤΗ' in i_type and 'ΜΗ' not in i_type)) and et in ['01', '1', '16', '99']

    p_df['is_ika'] = p_df.apply(_is_ika_match, axis=1)
    ika_rows = p_df[p_df['is_ika']].copy()
    ika_rows['ΕΡΓΟΔΟΤΗΣ_Clean'] = ika_rows['ΕΡΓΟΔΟΤΗΣ'].replace(['', 'nan', 'NaN', 'None'], pd.NA)
    ika_rows = ika_rows.dropna(subset=['ΕΡΓΟΔΟΤΗΣ_Clean'])

    if ika_rows.empty:
        return None

    multi_months = []
    for (year, month), group in ika_rows.groupby(['ΕΤΟΣ', 'Μήνας_Num']):
        if group['ΕΡΓΟΔΟΤΗΣ_Clean'].nunique() > 1:
            multi_months.append((year, month))

    if not multi_months:
        return None

    valid_df = pd.DataFrame(multi_months, columns=['ΕΤΟΣ', 'Μήνας_Num'])
    filtered = p_df.merge(valid_df, on=['ΕΤΟΣ', 'Μήνας_Num'], how='inner')
    filtered = filtered[filtered['is_ika']]
    filtered = filtered.drop(columns=['is_ika'])

    if filtered.empty:
        return None

    month_map = {1: 'ΙΑΝ', 2: 'ΦΕΒ', 3: 'ΜΑΡ', 4: 'ΑΠΡ', 5: 'ΜΑΙ', 6: 'ΙΟΥΝ', 7: 'ΙΟΥΛ', 8: 'ΑΥΓ', 9: 'ΣΕΠ', 10: 'ΟΚΤ', 11: 'ΝΟΕ', 12: 'ΔΕΚ'}
    return _pivot_parallel_df(filtered, month_map)


def compute_applied_monthly_day_caps(data_df: pd.DataFrame) -> list[dict]:
    """Μήνες/πακέτα (μη-ΙΚΑ) όπου εφαρμόστηκε cap 25 ημερών στην Καταμέτρηση."""
    required_cols = {'Από', 'Έως', 'Κλάδος/Πακέτο Κάλυψης'}
    if not required_cols.issubset(set(data_df.columns)):
        return []

    excluded_packages = {'Α', 'Λ', 'Υ', 'Ο', 'Χ', '026', '899'}
    monthly_rows: list[dict] = []

    for _, row in data_df.iterrows():
        try:
            start_dt = pd.to_datetime(row.get('Από'), format='%d/%m/%Y', errors='coerce')
            end_dt = pd.to_datetime(row.get('Έως'), format='%d/%m/%Y', errors='coerce')
            if pd.isna(start_dt) or pd.isna(end_dt):
                continue

            package = str(row.get('Κλάδος/Πακέτο Κάλυψης', '')).strip()
            if not package or package.upper() in excluded_packages:
                continue

            # Ίδιος τύπος ημερών με build_count_report: Έτη*300 + Μήνες*25 + Ημέρες
            days_val = 0.0
            if 'Ημέρες' in row and pd.notna(row.get('Ημέρες')) and str(row.get('Ημέρες', '')).strip() != '':
                d = clean_numeric_value(row.get('Ημέρες'))
                if d is not None and d != 0:
                    days_val += float(d)
            if 'Έτη' in row and pd.notna(row.get('Έτη')):
                y = clean_numeric_value(row.get('Έτη'))
                if y is not None and y != 0:
                    days_val += float(y) * 300
            if 'Μήνες' in row and pd.notna(row.get('Μήνες')):
                m = clean_numeric_value(row.get('Μήνες'))
                if m is not None and m != 0:
                    days_val += float(m) * 25
            gross_val = clean_numeric_value(row.get('Μικτές αποδοχές'), exclude_drx=True)
            raw_contrib = str(row.get('Συνολικές εισφορές', ''))
            if 'ΔΡΧ' in raw_contrib.upper() or 'DRX' in raw_contrib.upper():
                contrib_val = 0.0
            else:
                contrib_val = clean_numeric_value(raw_contrib, exclude_drx=True)
            gross_val = gross_val if gross_val is not None else 0.0
            contrib_val = contrib_val if contrib_val is not None else 0.0

            sign = get_negative_amount_sign(gross_val, contrib_val)
            if sign == -1:
                days_val = -abs(days_val)

            curr = start_dt.replace(day=1)
            end_month_dt = end_dt.replace(day=1)
            months_list = []
            while curr <= end_month_dt:
                months_list.append(curr)
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)

            if not months_list:
                continue

            days_per_month = days_val / len(months_list)
            tameio = str(row.get('Ταμείο', '')).strip()
            for m_dt in months_list:
                monthly_rows.append({
                    'Έτος': int(m_dt.year),
                    'Μήνας': int(m_dt.month),
                    'Ταμείο': tameio,
                    'Πακέτο': package,
                    'Ημέρες': float(days_per_month)
                })
        except Exception:
            continue

    if not monthly_rows:
        return []

    m_df = pd.DataFrame(monthly_rows)
    grouped = m_df.groupby(['Έτος', 'Μήνας', 'Ταμείο', 'Πακέτο'], as_index=False)['Ημέρες'].sum()
    grouped['is_ika'] = grouped['Ταμείο'].astype(str).str.upper().str.contains('ΙΚΑ|IKA', na=False)
    capped = grouped[(~grouped['is_ika']) & (grouped['Ημέρες'] > 25)].copy()
    if capped.empty:
        return []

    capped = capped.sort_values(['Έτος', 'Μήνας', 'Ταμείο', 'Πακέτο'])
    return capped[['Έτος', 'Μήνας', 'Ταμείο', 'Πακέτο', 'Ημέρες']].to_dict('records')


def compute_complex_file_metrics(data_df: pd.DataFrame) -> tuple[int, int, int]:
    """
    Υπολογίζει μετρήσεις για το προειδοποιητικό «Περίπλοκο αρχείο».
    Επιστρέφει (n_aggregated, n_limits_25, n_unpaid_months).
    """
    n_agg, n_limits_25, n_unpaid = 0, 0, 0
    # 1. Ενοποιημένα διαστήματα (Check 9 λογική)
    try:
        if 'Από' in data_df.columns and 'Έως' in data_df.columns:
            t_df = data_df.copy()
            t_df['D_From'] = pd.to_datetime(t_df['Από'], format='%d/%m/%Y', errors='coerce')
            t_df['D_To'] = pd.to_datetime(t_df['Έως'], format='%d/%m/%Y', errors='coerce')
            t_df['Duration'] = (t_df['D_To'] - t_df['D_From']).dt.days + 1
            def _get_num(val):
                try: return clean_numeric_value(val) or 0
                except Exception: return 0
            def _is_expected_oaee(r):
                tam = str(r.get('Ταμείο', '')).upper()
                if 'ΟΑΕΕ' not in tam: return False
                m_val, d_val = _get_num(r.get('Μήνες')), _get_num(r.get('Ημέρες'))
                if m_val and m_val <= 2:
                    if d_val and abs(d_val - m_val * 25) <= 1: return True
                    if not d_val and r.get('Duration', 0) <= 62: return True
                return False
            def _is_expected_tsm(r):
                tam = str(r.get('Ταμείο', '')).upper()
                if 'ΤΣΜΕΔΕ' not in tam: return False
                m_val, d_val = _get_num(r.get('Μήνες')), _get_num(r.get('Ημέρες'))
                d_from, d_to = r.get('D_From'), r.get('D_To')
                if pd.notna(d_from) and pd.notna(d_to) and d_from.year == d_to.year:
                    sem1 = (d_from.month == 1 and d_to.month == 6)
                    sem2 = (d_from.month == 7 and d_to.month == 12)
                    if sem1 or sem2:
                        if m_val == 6 and (not d_val or abs(d_val - 150) <= 2): return True
                        if not m_val and 150 <= r.get('Duration', 0) <= 190: return True
                return False
            agg_recs = t_df[(t_df['Duration'] > 31) & (t_df['D_To'] < pd.Timestamp('2002-01-01'))].copy()
            if not agg_recs.empty:
                agg_recs = agg_recs[~agg_recs.apply(lambda r: _is_expected_oaee(r) or _is_expected_tsm(r), axis=1)]
            n_agg = len(agg_recs) if not agg_recs.empty else 0
    except Exception:
        pass
    # 2. Όρια 25
    try:
        capped = compute_applied_monthly_day_caps(data_df)
        n_limits_25 = len(capped) if capped else 0
    except Exception:
        pass
    # 3. Απλήρωτοι μήνες (από καταμέτρηση, 1995+, K/ΚΣ/ΜΕ + ΕΤΑΑ-ΤΑΝ/ΚΕΑΔ Κ)
    try:
        days_df, contrib_df = get_count_allocation(data_df)
        if not days_df.empty and not contrib_df.empty:
            try:
                years = pd.to_numeric(days_df['ΕΤΟΣ'], errors='coerce')
                mask_1995 = years >= 1995
            except Exception:
                mask_1995 = pd.Series(True, index=days_df.index)
            days_df = days_df[mask_1995].reset_index(drop=True)
            contrib_df = contrib_df[mask_1995].reset_index(drop=True)
            if not days_df.empty:
                K = days_df['ΚΛΑΔΟΣ/ΠΑΚΕΤΟ'].astype(str).str.strip().str.upper()
                T = days_df['Ταμείο'].astype(str).str.strip().str.upper()
                cond_oaee = (K.isin(['K', 'Κ'])) & (T.str.contains('OAEE|ΟΑΕΕ|TEBE|ΤΕΒΕ|TAE|ΤΑΕ', na=False))
                cond_tsmede = (K.isin(['ΚΣ', 'KS'])) & (T.str.contains('ΤΣΜΕΔΕ|TSMEDE', na=False))
                cond_oga = (K.isin(['K', 'Κ'])) & (T.str.contains('ΟΓΑ|OGA', na=False))
                cond_tsay = (K.isin(['ME', 'ΜΕ'])) & (T.str.contains('ΤΣΑΥ|TSAY', na=False))
                cond_etaa_tan = (K.isin(['K', 'Κ'])) & (T.str.contains('ΕΤΑΑ-ΤΑΝ|ETAA-TAN', na=False))
                cond_etaa_kead = (K.isin(['K', 'Κ'])) & (T.str.contains('ΕΤΑΑ-ΚΕΑΔ|ETAA-KEAD', na=False))
                month_cols_int = [c for c in days_df.columns if isinstance(c, int)] or list(range(1, 13))
                def _count_unpaid(days_row, contrib_row):
                    cnt = 0
                    for m in month_cols_int:
                        d, c = days_row.get(m, 0), contrib_row.get(m, 0)
                        if pd.isna(d): d = 0
                        if pd.isna(c): c = 0
                        try: d_val = float(d) if d != '' else 0; c_val = float(c) if c != '' else 0
                        except (TypeError, ValueError): d_val, c_val = 0, 0
                        if d_val > 0 and (c_val == 0 or abs(c_val) < 1e-6): cnt += 1
                    return cnt
                for cond in [cond_oaee, cond_tsmede, cond_oga, cond_tsay, cond_etaa_tan, cond_etaa_kead]:
                    if cond.any():
                        sub_d = days_df.loc[cond].reset_index(drop=True)
                        sub_c = contrib_df.loc[cond].reset_index(drop=True)
                        for i in range(len(sub_d)):
                            n_unpaid += _count_unpaid(sub_d.iloc[i], sub_c.iloc[i])
    except Exception:
        pass
    return n_agg, n_limits_25, n_unpaid


def should_show_complex_file_warning(n_aggregated: int, n_limits_25: int, n_unpaid_months: int) -> bool:
    """
    True αν πρέπει να εμφανιστεί το προειδοποιητικό «Περίπλοκο αρχείο».
    Κριτήρια: (πάνω από 10 ενοπ. + πάνω από 30 απλήρωτοι + πάνω από 10 όρια 25) ή ανά δύο,
    ή πάνω από 15 ενοποιημένα, ή πάνω από 15 όρια 25.
    """
    if n_aggregated > 15 or n_limits_25 > 15:
        return True
    over_10_agg = n_aggregated > 10
    over_30_unpaid = n_unpaid_months > 30
    over_10_limits = n_limits_25 > 10
    if over_10_agg and over_30_unpaid:
        return True
    if over_10_agg and over_10_limits:
        return True
    if over_30_unpaid and over_10_limits:
        return True
    return False


def compute_summary_capped_days_by_group(
    summary_df: pd.DataFrame,
    group_keys: list[str],
    month_days: int = 25,
    year_days: int = 300,
    ika_month_days: int = 31,
    from_dt: pd.Timestamp | None = None,
    to_dt: pd.Timestamp | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Υπολογίζει capped συνολικές ημέρες ανά group. ΙΚΑ: πλαφόν ika_month_days/μήνα, υπόλοιπα: month_days/μήνα.
    Επιστρέφει (capped_df, exceeded_df) όπου exceeded_df περιέχει μήνες που ξεπέρασαν το όριο.
    Αν from_dt/to_dt δοθούν, μόνο οι μήνες εντός του εύρους λαμβάνονται υπόψη."""
    empty_capped = pd.DataFrame(columns=group_keys + ['Συνολικές_Ημέρες_cap'])
    empty_exceeded = pd.DataFrame(columns=(['Κλάδος/Πακέτο Κάλυψης', 'Ταμείο', 'Τύπος Ασφάλισης', 'Έτος', 'Μήνας', 'Ημέρες', 'Όριο', 'Υπέρβαση']))
    required_cols = {'Από', 'Έως'}
    if not required_cols.issubset(set(summary_df.columns)):
        return empty_capped, empty_exceeded

    cap_group_keys = ['Κλάδος/Πακέτο Κάλυψης']
    if 'Ταμείο' in group_keys and 'Ταμείο' in summary_df.columns:
        cap_group_keys.append('Ταμείο')
    if 'Τύπος Ασφάλισης' in group_keys and 'Τύπος Ασφάλισης' in summary_df.columns:
        cap_group_keys.append('Τύπος Ασφάλισης')

    work_df = summary_df.copy()
    if 'Κλάδος/Πακέτο Κάλυψης' in work_df.columns:
        work_df['Κλάδος/Πακέτο Κάλυψης'] = work_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
    if 'Ταμείο' in work_df.columns:
        work_df['Ταμείο'] = work_df['Ταμείο'].astype(str).str.strip()
    if 'Τύπος Ασφάλισης' in work_df.columns:
        work_df['Τύπος Ασφάλισης'] = work_df['Τύπος Ασφάλισης'].astype(str).str.strip()

    monthly_rows: list[dict] = []
    for _, row in work_df.iterrows():
        try:
            start_dt = pd.to_datetime(row.get('Από'), format='%d/%m/%Y', errors='coerce')
            end_dt = pd.to_datetime(row.get('Έως'), format='%d/%m/%Y', errors='coerce')
            if pd.isna(start_dt) or pd.isna(end_dt):
                continue

            years_val = clean_numeric_value(row.get('Έτη')) or 0.0
            months_val = clean_numeric_value(row.get('Μήνες')) or 0.0
            days_val = clean_numeric_value(row.get('Ημέρες')) or 0.0
            total_days_val = (years_val * year_days) + (months_val * month_days) + days_val
            curr = start_dt.replace(day=1)
            end_month_dt = end_dt.replace(day=1)
            months_list = []
            while curr <= end_month_dt:
                months_list.append(curr)
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)

            if not months_list:
                continue

            # Φίλτρο μηνών εντός εύρους Από-Έως
            orig_len = len(months_list)
            if from_dt is not None:
                months_list = [m for m in months_list if m >= from_dt.replace(day=1)]
            if to_dt is not None:
                to_month = to_dt.replace(day=1)
                months_list = [m for m in months_list if m <= to_month]
            if not months_list:
                continue

            days_per_month = total_days_val / orig_len
            base_rec = {k: row.get(k, '') for k in cap_group_keys}
            for m_dt in months_list:
                rec = dict(base_rec)
                rec['Έτος'] = int(m_dt.year)
                rec['Μήνας'] = int(m_dt.month)
                rec['Συνολικές_Ημέρες'] = float(days_per_month)
                monthly_rows.append(rec)
        except Exception:
            continue

    if not monthly_rows:
        return empty_capped, empty_exceeded

    monthly_df = pd.DataFrame(monthly_rows)
    per_month = monthly_df.groupby(cap_group_keys + ['Έτος', 'Μήνας'], as_index=False)['Συνολικές_Ημέρες'].sum()

    if 'Ταμείο' in per_month.columns:
        t_upper = per_month['Ταμείο'].astype(str).str.upper().str.strip()
        is_ika = t_upper.str.contains('ΙΚΑ|IKA', na=False)
        is_etaa_tan_kead = t_upper.str.contains('ΕΤΑΑ-ΤΑΝ|ETAA-TAN|ΕΤΑΑ-ΚΕΑΔ|ETAA-KEAD', na=False)
    else:
        is_ika = pd.Series(False, index=per_month.index)
        is_etaa_tan_kead = pd.Series(False, index=per_month.index)

    per_month['Όριο'] = month_days
    per_month.loc[is_ika, 'Όριο'] = ika_month_days
    per_month['Συνολικές_Ημέρες_cap'] = per_month[['Συνολικές_Ημέρες', 'Όριο']].min(axis=1)

    # Πλαφόν υπολογισμού: 25/μήνα (ΙΚΑ 31). ΕΤΑΑ-ΤΑΝ/ΚΕΑΔ: μήνυμα υπέρβασης μόνο όταν >30 ημ./μήνα (ξεχωριστό από πλαφόν ΙΚΑ).
    per_month['Όριο_μήνυμα'] = per_month['Όριο']
    per_month.loc[is_etaa_tan_kead, 'Όριο_μήνυμα'] = 30
    exceeded = per_month[per_month['Συνολικές_Ημέρες'] > per_month['Όριο_μήνυμα']].copy()
    if not exceeded.empty:
        exceeded = exceeded.rename(columns={'Συνολικές_Ημέρες': 'Ημέρες'})
        exceeded['Υπέρβαση'] = (exceeded['Ημέρες'] - exceeded['Όριο']).round(1)
        exceeded = exceeded[[c for c in ['Κλάδος/Πακέτο Κάλυψης', 'Ταμείο', 'Τύπος Ασφάλισης', 'Έτος', 'Μήνας', 'Ημέρες', 'Όριο', 'Υπέρβαση'] if c in exceeded.columns]]
    else:
        exceeded = empty_exceeded.copy()

    capped = per_month.groupby(cap_group_keys, as_index=False)['Συνολικές_Ημέρες_cap'].sum()
    return capped, exceeded


def compute_summary_capped_dk(
    summary_df: pd.DataFrame,
    group_keys: list[str],
    month_days: int = 25,
    year_days: int = 300,
    ika_month_days: int = 31,
    from_dt: pd.Timestamp | None = None,
    to_dt: pd.Timestamp | None = None,
    description_map: dict | None = None
) -> pd.DataFrame:
    """Υπολογίζει Σημαντικά Διαστήματα (dk1, dk3, κλπ) από capped ημέρες ανά μήνα."""
    cap_group_keys = ['Κλάδος/Πακέτο Κάλυψης']
    if 'Ταμείο' in group_keys and 'Ταμείο' in summary_df.columns:
        cap_group_keys.append('Ταμείο')
    if 'Τύπος Ασφάλισης' in group_keys and 'Τύπος Ασφάλισης' in summary_df.columns:
        cap_group_keys.append('Τύπος Ασφάλισης')

    _capped, _ = compute_summary_capped_days_by_group(
        summary_df, group_keys, month_days=month_days, year_days=year_days,
        ika_month_days=ika_month_days, from_dt=from_dt, to_dt=to_dt
    )
    if _capped.empty:
        return pd.DataFrame(columns=cap_group_keys + ['dk1', 'dk3', 'dk4', 'dk5', 'dk6', 'dk7a', 'dk7b', 'dk7c'])

    work_df = summary_df.copy()
    if 'Κλάδος/Πακέτο Κάλυψης' in work_df.columns:
        work_df['Κλάδος/Πακέτο Κάλυψης'] = work_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
    for c in ['Ταμείο', 'Τύπος Ασφάλισης']:
        if c in work_df.columns:
            work_df[c] = work_df[c].astype(str).str.strip()

    monthly_rows: list[dict] = []
    for _, row in work_df.iterrows():
        try:
            start_dt = pd.to_datetime(row.get('Από'), format='%d/%m/%Y', errors='coerce')
            end_dt = pd.to_datetime(row.get('Έως'), format='%d/%m/%Y', errors='coerce')
            if pd.isna(start_dt) or pd.isna(end_dt):
                continue
            years_val = clean_numeric_value(row.get('Έτη')) or 0.0
            months_val = clean_numeric_value(row.get('Μήνες')) or 0.0
            days_val = clean_numeric_value(row.get('Ημέρες')) or 0.0
            total_days_val = (years_val * year_days) + (months_val * month_days) + days_val
            curr = start_dt.replace(day=1)
            end_month_dt = end_dt.replace(day=1)
            months_list = []
            while curr <= end_month_dt:
                months_list.append(curr)
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)
            if not months_list:
                continue
            orig_len = len(months_list)
            if from_dt is not None:
                months_list = [m for m in months_list if m >= from_dt.replace(day=1)]
            if to_dt is not None:
                to_month = to_dt.replace(day=1)
                months_list = [m for m in months_list if m <= to_month]
            if not months_list:
                continue
            days_per_month = total_days_val / orig_len
            base_rec = {k: row.get(k, '') for k in cap_group_keys}
            for m_dt in months_list:
                rec = dict(base_rec)
                rec['Έτος'] = int(m_dt.year)
                rec['Μήνας'] = int(m_dt.month)
                rec['Συνολικές_Ημέρες'] = float(days_per_month)
                monthly_rows.append(rec)
        except Exception:
            continue

    if not monthly_rows:
        return pd.DataFrame(columns=cap_group_keys + ['dk1', 'dk3', 'dk4', 'dk5', 'dk6', 'dk7a', 'dk7b', 'dk7c'])

    monthly_df = pd.DataFrame(monthly_rows)
    per_month = monthly_df.groupby(cap_group_keys + ['Έτος', 'Μήνας'], as_index=False)['Συνολικές_Ημέρες'].sum()
    if 'Ταμείο' in per_month.columns:
        t_upper = per_month['Ταμείο'].astype(str).str.upper().str.strip()
        is_ika = t_upper.str.contains('ΙΚΑ|IKA', na=False)
    else:
        is_ika = pd.Series(False, index=per_month.index)
    per_month['Όριο'] = month_days
    per_month.loc[is_ika, 'Όριο'] = ika_month_days
    per_month['Συνολικές_Ημέρες_cap'] = per_month[['Συνολικές_Ημέρες', 'Όριο']].min(axis=1)
    per_month['_m_dt'] = pd.to_datetime(per_month['Έτος'].astype(str) + '-' + per_month['Μήνας'].astype(str) + '-01')

    today = pd.Timestamp.today().normalize()
    d2002 = pd.Timestamp('2002-01-01')
    five = pd.Timestamp(f'{today.year - 4}-01-01')
    max_y = per_month['Έτος'].max()
    five_last = pd.Timestamp(f'{int(max_y) - 4}-01-01') if pd.notna(max_y) else pd.NaT
    last_end = pd.Timestamp(f'{int(max_y)}-12-31') if pd.notna(max_y) else pd.NaT
    d2014 = pd.Timestamp('2014-12-31')
    d2010 = pd.Timestamp('2010-12-31')
    d2011 = pd.Timestamp('2011-12-31')
    d2012 = pd.Timestamp('2012-12-31')
    BAREA_DAYS = 6205
    window_end = today
    window_start = today - pd.Timedelta(days=BAREA_DAYS)

    def _strip_accents(s):
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')
    varea_codes = set()
    if description_map:
        for code, desc in description_map.items():
            if 'ΒΑΡΕ' in _strip_accents(desc).upper():
                varea_codes.add(str(code).strip())
    pkg_col = 'Κλάδος/Πακέτο Κάλυψης'
    per_month['_is_varea'] = per_month[pkg_col].astype(str).str.strip().isin(varea_codes) if pkg_col in per_month.columns else False

    per_month['dk1'] = per_month['Συνολικές_Ημέρες_cap'].where(per_month['_m_dt'] >= d2002, 0)
    per_month['dk3'] = per_month['Συνολικές_Ημέρες_cap'].where(per_month['_m_dt'] >= five, 0)
    per_month['dk4'] = 0
    if pd.notna(five_last):
        per_month['dk4'] = per_month['Συνολικές_Ημέρες_cap'].where(
            (per_month['_m_dt'] >= five_last) & (per_month['_m_dt'] <= last_end), 0
        )
    per_month['dk5'] = per_month['Συνολικές_Ημέρες_cap'].where(per_month['_m_dt'] <= d2014, 0)
    month_end = per_month['_m_dt'] + pd.offsets.MonthEnd(0)
    in_window = (month_end >= window_start) & (per_month['_m_dt'] <= window_end)
    per_month['dk6'] = per_month['Συνολικές_Ημέρες_cap'].where(per_month['_is_varea'] & in_window, 0)
    per_month['dk7a'] = per_month['Συνολικές_Ημέρες_cap'].where(per_month['_m_dt'] <= d2010, 0)
    per_month['dk7b'] = per_month['Συνολικές_Ημέρες_cap'].where(per_month['_m_dt'] <= d2011, 0)
    per_month['dk7c'] = per_month['Συνολικές_Ημέρες_cap'].where(per_month['_m_dt'] <= d2012, 0)

    dk_cols = ['dk1', 'dk3', 'dk4', 'dk5', 'dk6', 'dk7a', 'dk7b', 'dk7c']
    result = per_month.groupby(cap_group_keys)[dk_cols].sum().reset_index()
    for c in dk_cols:
        result[c] = result[c].round(0).astype(int)
    return result


def _get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        sec = st.secrets.get("GEMINI_API_KEY", "")
        return str(sec).strip() if sec else ""
    except Exception:
        return ""

def _df_to_records_for_ai(df: pd.DataFrame, max_rows: int | None = None) -> list[dict]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []
    safe_df = df.copy()
    safe_df = safe_df.replace({pd.NA: None})
    if max_rows is not None and max_rows > 0 and len(safe_df) > max_rows:
        safe_df = safe_df.head(max_rows)
    records = safe_df.to_dict(orient='records')
    cleaned: list[dict] = []
    for rec in records:
        row: dict = {}
        for k, v in rec.items():
            key = str(k)
            if isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)):
                row[key] = v.strftime('%d/%m/%Y')
            elif pd.isna(v):
                row[key] = None
            else:
                row[key] = v
        cleaned.append(row)
    return cleaned

def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None
    raw = str(text).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None

def _default_ai_prompt_template() -> str:
    return (
        "Παράγαγε μία ενιαία δομημένη απάντηση στα Ελληνικά.\n"
        "Επέστρεψε αυστηρά έγκυρο JSON, χωρίς markdown και χωρίς επιπλέον πεδία.\n"
        "Τα πεδία που ΠΡΕΠΕΙ να επιστραφούν είναι: {required_fields}.\n\n"
        "Οδηγίες ανά τομέα:\n"
        "1) executive_summary (string)\n"
        "- 2-4 προτάσεις, ουδέτερο και επαγγελματικό ύφος.\n"
        "- Να αναφέρει μόνο τα πιο ουσιώδη στοιχεία του φακέλου.\n"
        "- Χωρίς νομική κρίση ή συμπέρασμα θεμελίωσης.\n"
        "Παράδειγμα: \"Ο φάκελος δείχνει κυρίως συνεχή ασφαλιστική πορεία με επιμέρους ελέγχους που απαιτούν επιβεβαίωση.\"\n\n"
        "2) critical_findings (array[string])\n"
        "- 3-8 σύντομα bullets.\n"
        "- Να περιγράφει σημαντικά ευρήματα με σαφήνεια.\n"
        "- Να αποφεύγει αόριστες γενικότητες.\n"
        "Παράδειγμα: [\"Εντοπίστηκαν κενά ασφάλισης σε συγκεκριμένα διαστήματα.\", \"Υπάρχουν περίοδοι που χρειάζονται διασταύρωση με πρωτογενή στοιχεία.\"]\n\n"
        "3) data_gaps (array[string])\n"
        "- 2-8 σύντομα bullets.\n"
        "- Να καταγράφει ρητά ελλείψεις και αβεβαιότητες δεδομένων.\n"
        "- Να μην εφευρίσκει τιμές που δεν υπάρχουν.\n"
        "Παράδειγμα: [\"Λείπουν επαρκή στοιχεία για πλήρη επαλήθευση ορισμένων περιόδων.\", \"Δεν υπάρχουν βοηθητικά έγγραφα για διασταύρωση συγκεκριμένων εγγραφών.\"]\n\n"
        "4) recommended_actions (array[string])\n"
        "- 3-8 πρακτικά επόμενα βήματα.\n"
        "- Οι ενέργειες να είναι εφαρμόσιμες και συγκεκριμένες.\n"
        "- Να εστιάζει σε επαλήθευση/τεκμηρίωση.\n"
        "Παράδειγμα: [\"Διασταύρωση των περιόδων με τα πρωτογενή δεδομένα e-ΕΦΚΑ.\", \"Συγκέντρωση δικαιολογητικών για τα αμφισβητούμενα διαστήματα.\"]\n\n"
        "5) confidence (object)\n"
        "- level: High|Medium|Low.\n"
        "- reasons: array από 2-5 σύντομους λόγους.\n"
        "- Τα reasons να βασίζονται αποκλειστικά στα παρεχόμενα δεδομένα.\n"
        "Παράδειγμα: {\"level\": \"Medium\", \"reasons\": [\"Υπάρχουν ενδείξεις που χρειάζονται περαιτέρω τεκμηρίωση.\", \"Η ανάλυση βασίζεται μόνο στα διαθέσιμα στοιχεία ΑΤΛΑΣ.\"]}\n\n"
        "6) disclaimer (string)\n"
        "- Μία σύντομη αποποίηση ευθύνης.\n"
        "- Να δηλώνει ότι η σύνοψη είναι υποβοηθητική.\n"
        "- Να δηλώνει ότι δεν υποκαθιστά επίσημη ή νομική γνωμοδότηση.\n"
        "Παράδειγμα: \"Η παρούσα σύνοψη είναι υποβοηθητική και δεν αποτελεί επίσημη ή νομική γνωμοδότηση.\"\n\n"
        "Δεδομένα φακέλου:\n"
        "{payload_json}\n"
    )

def _load_ai_prompt_template() -> str:
    template_path = Path(__file__).parent / "ai_summary_prompt.txt"
    try:
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8").strip()
            if content:
                return content
    except Exception:
        pass
    return _default_ai_prompt_template()

def _get_anthropic_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    try:
        sec = st.secrets.get("ANTHROPIC_API_KEY", "")
        return str(sec).strip() if sec else ""
    except Exception:
        return ""

AI_MODEL_OPTIONS = {
    "Gemini 2.5 Flash": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "Gemini 2.5 Pro": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "Claude Sonnet 4": {
        "provider": "claude",
        "model": "claude-sonnet-4-20250514",
        "fallback_models": [],
    },
}

def _call_gemini(system_prompt: str, user_prompt: str, model_name: str, api_key: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name)
    response = model.generate_content([system_prompt, user_prompt])
    return getattr(response, 'text', '') or ''

def _call_claude(
    system_prompt: str,
    user_prompt: str,
    model_name: str,
    api_key: str,
    fallback_models: list[str] | None = None
) -> tuple[str, str]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    candidates = [model_name] + (fallback_models or [])
    seen = set()
    ordered = []
    for m in candidates:
        if m and m not in seen:
            seen.add(m)
            ordered.append(m)

    last_error = None
    for cand in ordered:
        try:
            response = client.messages.create(
                model=cand,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            text = response.content[0].text if response.content else ''
            return text, cand
        except Exception as e:
            last_error = e
            e_text = str(e).lower()
            if "not_found_error" in e_text or "model:" in e_text:
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("No Claude model available.")

def generate_ai_case_summary(
    audit_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    count_df: pd.DataFrame,
    gaps_df: pd.DataFrame | None = None,
    parallel_rows: list[dict] | None = None,
    metadata: dict | None = None,
    model_name: str = "gemini-2.5-flash",
    provider: str = "gemini",
    fallback_models: list[str] | None = None
) -> dict:
    """
    Παράγει AI σύνοψη φακέλου με Gemini ή Claude.
    Επιστρέφει dict:
      - {'ok': True, 'data': {...}, 'raw_text': '...'}
      - {'ok': False, 'error': '...'}
    """
    if provider == "claude":
        api_key = _get_anthropic_api_key()
        if not api_key:
            return {'ok': False, 'error': "Δεν βρέθηκε ANTHROPIC_API_KEY. Ορίστε env var ή Streamlit secret."}
        try:
            import anthropic  # noqa: F401
        except Exception:
            return {'ok': False, 'error': "Λείπει το package anthropic. Προσθέστε το στα requirements."}
    else:
        api_key = _get_gemini_api_key()
        if not api_key:
            return {'ok': False, 'error': "Δεν βρέθηκε GEMINI_API_KEY. Ορίστε env var ή Streamlit secret."}
        try:
            import google.generativeai  # noqa: F401
        except Exception:
            return {'ok': False, 'error': "Λείπει το package google-generativeai. Προσθέστε το στα requirements."}

    system_prompt = (
        "Είσαι βοηθός επαγγελματία συμβούλου συντάξεων. "
        "Αναλύεις μόνο τα δεδομένα που δίνονται και δεν κάνεις νομική κρίση. "
        "Μην εφευρίσκεις αριθμούς ή γεγονότα. "
        "Απάντησε αποκλειστικά σε έγκυρο JSON."
    )
    def _retry_after_seconds(err_text: str) -> int | None:
        m = re.search(r"retry_delay[^0-9]*seconds[^0-9]*(\d+)", err_text or "", flags=re.IGNORECASE)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def _is_quota_error(err_text: str) -> bool:
        t = (err_text or "").lower()
        return ("quota" in t) or ("429" in t) or ("rate limit" in t) or ("resource_exhausted" in t)

    payload = {
        'metadata': metadata or {},
        'audit_findings': _df_to_records_for_ai(audit_df),
        'summary_rows': _df_to_records_for_ai(summary_df),
        'count_rows': _df_to_records_for_ai(count_df),
        'gaps_rows': _df_to_records_for_ai(gaps_df if isinstance(gaps_df, pd.DataFrame) else pd.DataFrame()),
        'parallel_rows': parallel_rows if isinstance(parallel_rows, list) else [],
    }

    required_fields = ['executive_summary', 'critical_findings', 'data_gaps', 'recommended_actions', 'confidence', 'disclaimer']

    def _build_structured_prompt() -> str:
        template = _load_ai_prompt_template()
        payload_json = json.dumps(payload, ensure_ascii=False)
        prompt_text = template.replace("{required_fields}", ", ".join(required_fields))
        prompt_text = prompt_text.replace("{payload_json}", payload_json)
        if "{payload_json}" in template:
            return prompt_text
        return f"{prompt_text}\n\nΔεδομένα φακέλου:\n{payload_json}"

    def _validate_section_value(section_key: str, value) -> bool:
        if section_key in ('executive_summary', 'disclaimer'):
            return isinstance(value, str) and bool(value.strip())
        if section_key in ('critical_findings', 'data_gaps', 'recommended_actions'):
            return isinstance(value, list) and all(isinstance(x, str) for x in value)
        if section_key == 'confidence':
            if not isinstance(value, dict):
                return False
            lvl = value.get('level')
            reasons = value.get('reasons')
            return (lvl in {'High', 'Medium', 'Low'}) and isinstance(reasons, list) and all(isinstance(x, str) for x in reasons)
        return False

    def _run_once(run_model: str, run_provider: str, run_fallback_models: list[str] | None = None) -> dict:
        user_prompt = _build_structured_prompt()
        try:
            if run_provider == "claude":
                run_key = _get_anthropic_api_key()
                if not run_key:
                    return {'ok': False, 'error': "Δεν βρέθηκε ANTHROPIC_API_KEY.", 'model_used': run_model}
                raw_text, used_model = _call_claude(system_prompt, user_prompt, run_model, run_key, run_fallback_models)
            else:
                run_key = _get_gemini_api_key()
                if not run_key:
                    return {'ok': False, 'error': "Δεν βρέθηκε GEMINI_API_KEY.", 'model_used': run_model}
                raw_text = _call_gemini(system_prompt, user_prompt, run_model, run_key)
                used_model = run_model
            parsed = _extract_json_object(raw_text)
            if not isinstance(parsed, dict):
                return {
                    'ok': False,
                    'error': "Το AI δεν επέστρεψε έγκυρο JSON object.",
                    'raw_text': raw_text,
                    'model_used': used_model
                }
            missing = [k for k in required_fields if k not in parsed]
            if missing:
                return {
                    'ok': False,
                    'error': f"Λείπουν πεδία από το JSON: {', '.join(missing)}",
                    'raw_text': raw_text,
                    'model_used': used_model
                }
            for k in required_fields:
                if not _validate_section_value(k, parsed.get(k)):
                    return {
                        'ok': False,
                        'error': f"Μη έγκυρο schema για το πεδίο {k}.",
                        'raw_text': raw_text,
                        'model_used': used_model
                    }
            return {'ok': True, 'parsed': parsed, 'raw_text': raw_text, 'model_used': used_model}
        except Exception as e:
            err_text = str(e)
            return {
                'ok': False,
                'error': f"Αποτυχία κλήσης AI ({run_model}): {err_text}",
                'model_used': run_model,
                'is_quota': _is_quota_error(err_text),
                'retry_after_seconds': _retry_after_seconds(err_text)
            }

    first = _run_once(model_name, provider, fallback_models)
    if first.get('ok') and isinstance(first.get('parsed'), dict):
        return {
            'ok': True,
            'data': first.get('parsed'),
            'raw_text': first.get('raw_text', ''),
            'model_used': first.get('model_used')
        }

    # Fallback σε Gemini Flash μόνο όταν ο αρχικός provider είναι Gemini.
    # Αν επιλέχθηκε Claude, επιστρέφουμε το πραγματικό σφάλμα χωρίς αυτόματο fallback.
    is_already_gemini_flash = (provider == "gemini" and model_name == "gemini-2.5-flash")
    if provider == "gemini" and not is_already_gemini_flash:
        fb_key = _get_gemini_api_key()
        if fb_key:
            second = _run_once("gemini-2.5-flash", "gemini")
            if second.get('ok') and isinstance(second.get('parsed'), dict):
                return {
                    'ok': True,
                    'data': second.get('parsed'),
                    'raw_text': second.get('raw_text', ''),
                    'model_used': second.get('model_used'),
                    'fallback_used': True
                }

    if first.get('is_quota'):
        retry_s = first.get('retry_after_seconds')
        user_msg = "Υπέρβαση ορίου (quota)."
        if retry_s:
            user_msg += f" Δοκιμάστε ξανά σε περίπου {retry_s} δευτερόλεπτα."
        return {
            'ok': False,
            'error': user_msg,
            'retry_after_seconds': retry_s,
            'raw_error': first.get('error', '')
        }
    return {
        'ok': False,
        'error': first.get('error', "Το AI δεν επέστρεψε έγκυρο JSON."),
        'raw_text': first.get('raw_text', '')
    }

def ai_chat_response(
    user_message: str,
    chat_history: list[dict],
    case_context: str,
    model_name: str = "gemini-2.5-flash",
    provider: str = "gemini",
    fallback_models: list[str] | None = None
) -> str:
    """
    Απαντά σε ερώτηση χρήστη βασισμένη στα δεδομένα φακέλου.
    chat_history: list of {"role": "user"|"assistant", "content": "..."}
    case_context: JSON string με τα δεδομένα φακέλου (audit/summary/count).
    Επιστρέφει string απάντηση.
    """
    system_prompt = (
        "Είσαι βοηθός επαγγελματία συμβούλου συντάξεων. "
        "Απαντάς σε ερωτήσεις βασισμένες ΑΠΟΚΛΕΙΣΤΙΚΑ στα δεδομένα φακέλου που σου δίνονται. "
        "Μην εφευρίσκεις αριθμούς, ημερομηνίες ή γεγονότα που δεν υπάρχουν στα δεδομένα. "
        "Αν δεν μπορείς να απαντήσεις από τα δεδομένα, πες το ξεκάθαρα. "
        "Απάντησε πάντα στα Ελληνικά, σύντομα και ουσιαστικά."
    )

    context_message = f"Δεδομένα φακέλου:\n{case_context}"

    if provider == "claude":
        api_key = _get_anthropic_api_key()
        if not api_key:
            return "Δεν βρέθηκε ANTHROPIC_API_KEY."
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            messages = [{"role": "user", "content": context_message}]
            messages.append({"role": "assistant", "content": "Κατάλαβα τα δεδομένα. Ρωτήστε ό,τι θέλετε."})
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_message})

            candidates = [model_name] + (fallback_models or [])
            seen = set()
            ordered = []
            for m in candidates:
                if m and m not in seen:
                    seen.add(m)
                    ordered.append(m)

            last_err = None
            for cand in ordered:
                try:
                    response = client.messages.create(
                        model=cand,
                        max_tokens=2048,
                        system=system_prompt,
                        messages=messages
                    )
                    return response.content[0].text if response.content else "Δεν ελήφθη απάντηση."
                except Exception as e:
                    last_err = e
                    e_text = str(e).lower()
                    if "not_found_error" in e_text or "model:" in e_text:
                        continue
                    return f"Σφάλμα Claude: {e}"
            return f"Σφάλμα Claude: {last_err}" if last_err else "Σφάλμα Claude: Δεν βρέθηκε διαθέσιμο μοντέλο."
        except Exception as e:
            return f"Σφάλμα Claude: {e}"
    else:
        api_key = _get_gemini_api_key()
        if not api_key:
            return "Δεν βρέθηκε GEMINI_API_KEY."
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name=model_name)
            prompt_parts = [system_prompt, context_message]
            for msg in chat_history:
                prefix = "Χρήστης: " if msg["role"] == "user" else "Βοηθός: "
                prompt_parts.append(f"{prefix}{msg['content']}")
            prompt_parts.append(f"Χρήστης: {user_message}")
            prompt_parts.append("Βοηθός:")
            response = model.generate_content("\n\n".join(prompt_parts))
            return getattr(response, 'text', '') or "Δεν ελήφθη απάντηση."
        except Exception as e:
            return f"Σφάλμα Gemini: {e}"


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

    # Check 3: Gaps και Διαστήματα χωρίς ημέρες ασφάλισης
    try:
        gaps = find_gaps_in_insurance_data(data_df)
        zero_duration = find_zero_duration_intervals(data_df)

        parts = []
        if not gaps.empty:
            gap_details = []
            for _, g in gaps.iterrows():
                duration = g.get('Ημερολογιακές ημέρες', '')
                insured_days_est = g.get('Ημέρες Ασφ.')
                if pd.notna(insured_days_est):
                    gap_details.append(
                        f"Από {g['Από']} έως {g['Έως']} "
                        f"({duration} ημερολογιακές ημέρες, εκτίμηση {int(insured_days_est)} ημέρες ασφάλισης)"
                    )
                else:
                    gap_details.append(f"Από {g['Από']} έως {g['Έως']} ({duration} ημερολογιακές ημέρες)")
            parts.append(("Κενά διαστήματα", f"{len(gaps)} Διάστημα(τα)", "<br>".join(gap_details)))

        if not zero_duration.empty:
            zero_details = []
            for _, z in zero_duration.iterrows():
                zero_details.append(f"Από {z['Από']} έως {z['Έως']}")
            parts.append(("Διαστήματα χωρίς ημέρες", f"{len(zero_duration)} Εγγραφή(ές)", "<br>".join(zero_details)))

        if parts:
            eurimata = "; ".join(p[1] for p in parts)
            leptonereies = "<br><br>".join(f"<strong>{p[0]}:</strong> {p[2]}" for p in parts)
            audit_rows.append({
                'A/A': 3, 'Έλεγχος': 'Κενά ασφάλισης',
                'Εύρημα': eurimata,
                'Λεπτομέρειες': leptonereies,
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

    # Check 4: Απλήρωτες εισφορές — από την καταμέτρηση (επιμέρισμα μηνών/εισφορών), όχι από το κεντρικό df
    check4_added = False
    try:
        days_df, contrib_df = get_count_allocation(data_df)
        if days_df.empty or contrib_df.empty:
            audit_rows.append({'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές', 'Εύρημα': '-', 'Λεπτομέρειες': 'Δεν υπάρχουν στοιχεία καταμέτρησης (Από, Έως, Ημέρες)', 'Ενέργειες': '-'})
            check4_added = True
        else:
            # Μόνο από 1995 και μετά
            try:
                years = pd.to_numeric(days_df['ΕΤΟΣ'], errors='coerce')
                mask_1995 = years >= 1995
            except Exception:
                mask_1995 = pd.Series(True, index=days_df.index)
            days_df = days_df[mask_1995].reset_index(drop=True)
            contrib_df = contrib_df[mask_1995].reset_index(drop=True)
            if days_df.empty:
                audit_rows.append({'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές', 'Εύρημα': 'Καμία', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                check4_added = True
            else:
                K = days_df['ΚΛΑΔΟΣ/ΠΑΚΕΤΟ'].astype(str).str.strip().str.upper()
                T = days_df['ΤΑΜΕΙΟ'].astype(str).str.strip().str.upper()
                cond_oaee = (K.isin(['K', 'Κ'])) & (T.str.contains('OAEE|ΟΑΕΕ|TEBE|ΤΕΒΕ|TAE|ΤΑΕ', na=False))
                cond_tsmede = (K.isin(['ΚΣ', 'KS'])) & (T.str.contains('ΤΣΜΕΔΕ|TSMEDE', na=False))
                cond_oga = (K.isin(['K', 'Κ'])) & (T.str.contains('ΟΓΑ|OGA', na=False))
                cond_tsay = (K.isin(['ME', 'ΜΕ'])) & (T.str.contains('ΤΣΑΥ|TSAY', na=False))
                cond_etaa_tan = (K.isin(['K', 'Κ'])) & (T.str.contains('ΕΤΑΑ-ΤΑΝ|ETAA-TAN', na=False))
                cond_etaa_kead = (K.isin(['K', 'Κ'])) & (T.str.contains('ΕΤΑΑ-ΚΕΑΔ|ETAA-KEAD', na=False))
                month_cols_int = [c for c in days_df.columns if isinstance(c, int)]
                if not month_cols_int:
                    month_cols_int = list(range(1, 13))

                def _count_unpaid_months(days_row, contrib_row):
                    n = 0
                    for m in month_cols_int:
                        d = days_row.get(m, 0)
                        c = contrib_row.get(m, 0)
                        if pd.isna(d): d = 0
                        if pd.isna(c): c = 0
                        try:
                            d_val = float(d) if d != '' else 0
                            c_val = float(c) if c != '' else 0
                        except (TypeError, ValueError):
                            d_val, c_val = 0, 0
                        if d_val > 0 and (c_val == 0 or abs(c_val) < 1e-6):
                            n += 1
                    return n

                def _sum_unpaid_for_cond(cond, label):
                    if not cond.any():
                        return None
                    sub_d = days_df.loc[cond].reset_index(drop=True)
                    sub_c = contrib_df.loc[cond].reset_index(drop=True)
                    total = 0
                    for i in range(len(sub_d)):
                        total += _count_unpaid_months(sub_d.iloc[i], sub_c.iloc[i])
                    return f"{total} μήνες {label}" if total > 0 else None

                f_oaee = _sum_unpaid_for_cond(cond_oaee, "ΟΑΕΕ (Κ)")
                f_tsmede = _sum_unpaid_for_cond(cond_tsmede, "ΤΣΜΕΔΕ (ΚΣ)")
                f_oga = _sum_unpaid_for_cond(cond_oga, "ΟΓΑ (Κ)")
                f_tsay = _sum_unpaid_for_cond(cond_tsay, "ΤΣΑΥ (ΜΕ)")
                f_etaa_tan = _sum_unpaid_for_cond(cond_etaa_tan, "ΕΤΑΑ-ΤΑΝ (Κ)")
                f_etaa_kead = _sum_unpaid_for_cond(cond_etaa_kead, "ΕΤΑΑ-ΚΕΑΔ (Κ)")
                all_funds = [x for x in [f_oaee, f_tsmede, f_oga, f_tsay, f_etaa_tan, f_etaa_kead] if x]
                if all_funds:
                    details_msg = ", ".join(all_funds) + " με ημέρες αλλά χωρίς εισφορές."
                    any_cond = cond_oaee | cond_tsmede | cond_oga | cond_tsay | cond_etaa_tan | cond_etaa_kead
                    sample_d = days_df.loc[any_cond].reset_index(drop=True)
                    sample_c = contrib_df.loc[any_cond].reset_index(drop=True)
                    unpaid_pairs = []  # (year, month) για ταξινόμηση
                    for i in range(len(sample_d)):
                        dr, cr = sample_d.iloc[i], sample_c.iloc[i]
                        try:
                            yr = int(dr.get('ΕΤΟΣ', 0)) if pd.notna(dr.get('ΕΤΟΣ')) else 0
                        except (TypeError, ValueError):
                            yr = 0
                        for m in month_cols_int[:12]:
                            d = dr.get(m, 0)
                            c = cr.get(m, 0)
                            try:
                                d_val = float(d) if d != '' else 0
                                c_val = float(c) if c != '' else 0
                            except (TypeError, ValueError):
                                d_val, c_val = 0, 0
                            if d_val > 0 and (c_val == 0 or abs(c_val) < 1e-6) and yr:
                                unpaid_pairs.append((yr, m))
                    unpaid_pairs.sort(key=lambda x: (x[0], x[1]), reverse=True)
                    months_sample = [f"{m:02d}/{yr}" for yr, m in unpaid_pairs[:20]]
                    if months_sample:
                        details_msg += f"<br><span style='font-size: 0.85rem; color: #666;'>Ενδεικτικά (από πιο πρόσφατους): {', '.join(months_sample)}{'...' if len(unpaid_pairs) > 20 else ''}</span>"
                    audit_rows.append({
                        'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές',
                        'Εύρημα': 'Εντοπίστηκαν',
                        'Λεπτομέρειες': details_msg,
                        'Ενέργειες': 'Ελέγξτε για τυχόν οφειλές στα αντίστοιχα ταμεία'
                    })
                else:
                    audit_rows.append({'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές', 'Εύρημα': 'Καμία', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
                check4_added = True
    except Exception:
        pass
    if not check4_added:
        audit_rows.append({'A/A': 4, 'Έλεγχος': 'Απλήρωτες εισφορές', 'Εύρημα': '-', 'Λεπτομέρειες': 'Δεν βρέθηκαν', 'Ενέργειες': '-'})

    # Check 5: Parallel Insurance (Month-based Logic)
    try:
        valid_months = compute_parallel_months(data_df)
        p_found = bool(valid_months)

        if p_found:
            audit_rows.append({
                'A/A': 5, 'Έλεγχος': 'Παράλληλη ασφάλιση',
                'Εύρημα': 'Πιθανή',
                'Λεπτομέρειες': 'Βρέθηκαν χρονικά επικαλυπτόμενα διαστήματα ΙΚΑ (αποδοχές 01, 16, ή 99) & ΟΑΕΕ (Κ), ΙΚΑ & ΤΣΜΕΔΕ (ΚΣ/ΠΚΣ), ΟΑΕΕ (Κ) & ΤΣΜΕΔΕ (ΚΣ/ΠΚΣ) ή ΟΓΑ (Κ) & ΙΚΑ/ΟΑΕΕ.',
                'Ενέργειες': 'Ελέγξτε την καρτέλα "Παράλληλη Ασφάλιση"'
            })
        else:
            audit_rows.append({'A/A': 5, 'Έλεγχος': 'Παράλληλη ασφάλιση', 'Εύρημα': 'Όχι', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
    except Exception:
        pass

    # Check 5B: Parallel Employment 2017+ (ΙΚΑ + ΕΦΚΑ ΜΗ ΜΙΣΘΩΤΗ / ΕΦΚΑ ΜΙΣΘΩΤΗ + ΕΦΚΑ ΜΗ ΜΙΣΘΩΤΗ)
    try:
        valid_months_2017 = compute_parallel_months_2017(data_df)
        p2017_found = bool(valid_months_2017)
        if p2017_found:
            audit_rows.append({
                'A/A': 11, 'Έλεγχος': 'Παράλληλη απασχόληση 2017+',
                'Εύρημα': 'Πιθανή',
                'Λεπτομέρειες': 'Βρέθηκαν χρονικά επικαλυπτόμενα διαστήματα από 01/2017 και μετά: ΙΚΑ (αποδοχές 01, 16, ή 99) & ΕΦΚΑ μη μισθωτή ή ΕΦΚΑ μισθωτή & ΕΦΚΑ μη μισθωτή.',
                'Ενέργειες': 'Ελέγξτε την καρτέλα "Παράλληλη Απασχόληση 2017+"'
            })
        else:
            audit_rows.append({'A/A': 11, 'Έλεγχος': 'Παράλληλη απασχόληση 2017+', 'Εύρημα': 'Όχι', 'Λεπτομέρειες': '-', 'Ενέργειες': '-'})
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
                'Λεπτομέρειες': "Βρέθηκαν μήνες με > 1 εργοδότες για ΙΚΑ (αποδοχές 01, 16, ή 99).",
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

    # Check 10: Μήνες/Πακέτα με εφαρμογή ανώτατου ορίου 25 ημερών (μη-ΙΚΑ)
    try:
        capped_months = compute_applied_monthly_day_caps(data_df)
        if capped_months:
            details = []
            for rec in capped_months[:30]:
                mm = int(rec.get('Μήνας', 0))
                yy = int(rec.get('Έτος', 0))
                package = str(rec.get('Πακέτο', '')).strip()
                fund = str(rec.get('Ταμείο', '')).strip() or '-'
                raw_days = float(rec.get('Ημέρες', 0))
                details.append(f"{mm:02d}/{yy} - {fund} - Πακέτο {package} ({raw_days:.1f} -> 25)")
            if len(capped_months) > 30:
                details.append("...")

            audit_rows.append({
                'A/A': 10,
                'Έλεγχος': 'Εφαρμογή ορίου 25 ημερών',
                'Εύρημα': f"{len(capped_months)} μήνες/πακέτα",
                'Λεπτομέρειες': "<br>".join(details),
                'Ενέργειες': 'Εφαρμόστηκε ανώτατο όριο 25 ημερών ανά μήνα στην Καταμέτρηση για μη-ΙΚΑ ταμεία'
            })
        else:
            audit_rows.append({
                'A/A': 10,
                'Έλεγχος': 'Εφαρμογή ορίου 25 ημερών',
                'Εύρημα': 'Καμία',
                'Λεπτομέρειες': '-',
                'Ενέργειες': '-'
            })
    except Exception:
        pass

    # Check 12: Αρνητικοί χρόνοι / Διαγραφές εγγραφών
    try:
        neg_df = find_negative_entries(data_df)
        if not neg_df.empty:
            neg_details = []
            for _, nr in neg_df.head(10).iterrows():
                apo = str(nr.get('Από', '')).strip()
                eos = str(nr.get('Έως', '')).strip()
                tameio = str(nr.get('Ταμείο', '')).strip()
                neg_details.append(f"{apo} - {eos} ({tameio})")
            if len(neg_df) > 10:
                neg_details.append(f"...και ακόμη {len(neg_df) - 10}")
            audit_rows.append({
                'A/A': 12,
                'Έλεγχος': 'Αρνητικοί χρόνοι / Διαγραφές',
                'Εύρημα': f"{len(neg_df)} εγγραφή(ές)",
                'Λεπτομέρειες': "<br>".join(neg_details),
                'Ενέργειες': 'Εγγραφές με αρνητικές αποδοχές ή εισφορές — πιθανή διαγραφή χρόνου ασφάλισης'
            })
        else:
            audit_rows.append({
                'A/A': 12,
                'Έλεγχος': 'Αρνητικοί χρόνοι / Διαγραφές',
                'Εύρημα': 'Καμία',
                'Λεπτομέρειες': '-',
                'Ενέργειες': '-'
            })
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
    if 'Τύπος Ασφάλισης' in summary_df.columns:
        group_keys.append('Τύπος Ασφάλισης')

    if basis_label is None:
        try:
            basis_label = st.session_state.get('ins_days_basis', 'Μήνας = 25, Έτος = 300')
        except Exception:
            basis_label = 'Μήνας = 25, Έτος = 300'

    if str(basis_label).startswith('Μήνας = 30'):
        month_days, year_days = 30, 360
    else:
        month_days, year_days = 25, 300

    agg_spec = {
        'Από_dt': 'min',
        'Έως_dt': 'max',
        'Έτη': 'sum',
        'Μήνες': 'sum',
        'Ημέρες': 'sum',
        'Μικτές αποδοχές': 'sum',
        'Συνολικές εισφορές': 'sum'
    }
    agg_dict = {col: agg_spec[col] for col in agg_spec if col in summary_df.columns}
    if not agg_dict:
        return pd.DataFrame()
    grouped = summary_df.groupby(group_keys).agg(agg_dict).reset_index()

    # Βεβαιωθείτε ότι υπάρχουν οι στήλες που χρησιμοποιεί το υπόλοιπο κώδικα
    for col in ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές']:
        if col not in grouped.columns:
            grouped[col] = 0

    # Cap μήνα-μήνα πάνω στο ισοδύναμο ημερών (Έτη/Μήνες/Ημέρες), χωρίς διάκριση Τύπου Αποδοχών.
    raw_total_days = (
        grouped['Ημέρες'].fillna(0) +
        grouped['Μήνες'].fillna(0) * month_days +
        grouped['Έτη'].fillna(0) * year_days
    )
    capped_days, _ = compute_summary_capped_days_by_group(summary_df, group_keys, month_days=month_days, year_days=year_days, ika_month_days=31)
    if not capped_days.empty:
        merge_keys = [k for k in group_keys if k in capped_days.columns]
        grouped = grouped.merge(capped_days, on=merge_keys, how='left')
        total_days = grouped['Συνολικές_Ημέρες_cap'].fillna(raw_total_days)
        grouped = grouped.drop(columns=['Συνολικές_Ημέρες_cap'])
    else:
        total_days = raw_total_days

    grouped['Συνολικές ημέρες'] = total_days.round(0).astype(int)
    years_series = (grouped['Συνολικές ημέρες'].astype(float) // year_days)
    remaining_after_years = grouped['Συνολικές ημέρες'].astype(float) - (years_series * year_days)
    months_series = (remaining_after_years // month_days)
    days_series = remaining_after_years - (months_series * month_days)
    grouped['Έτη'] = years_series
    grouped['Μήνες'] = months_series
    grouped['Ημέρες'] = days_series

    if 'Από_dt' in grouped.columns:
        grouped['Από'] = grouped['Από_dt'].dt.strftime('%d/%m/%Y')
    if 'Έως_dt' in grouped.columns:
        grouped['Έως'] = grouped['Έως_dt'].dt.strftime('%d/%m/%Y')
    for dt_col in ['Από_dt', 'Έως_dt']:
        if dt_col in grouped.columns:
            grouped = grouped.drop(columns=[dt_col])

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

    desired_order = ['Κλάδος/Πακέτο Κάλυψης', 'Ταμείο', 'Τύπος Ασφάλισης',
                      'Περιγραφή', 'Από', 'Έως', 'Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες',
                      'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
    columns_order = [c for c in desired_order if c in summary_final.columns]
    extra_cols = [c for c in summary_final.columns if c not in desired_order]
    if extra_cols:
        import logging
        logging.warning(f"[build_summary_grouped_display] Unexpected columns found (dropped): {extra_cols}")
    summary_final = summary_final[columns_order]

    display_summary = summary_final.copy()
    for curr_col in ['Μικτές αποδοχές', 'Συνολικές εισφορές']:
        if curr_col in display_summary.columns:
            display_summary[curr_col] = display_summary[curr_col].apply(format_currency)

    numeric_columns_summary = ['Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες', 'Αριθμός Εγγραφών']
    for col in numeric_columns_summary:
        if col in display_summary.columns:
            decimals = 1 if col in ['Έτη', 'Μήνες'] else 0
            display_summary[col] = display_summary[col].apply(
                lambda x: format_number_greek(x, decimals=decimals) if pd.notna(x) and x != '' else x
            )

    return display_summary


def get_count_allocation(count_df: pd.DataFrame, description_map: dict[str, str] | None = None):
    """
    Επιστρέφει την καταμέτρηση που επιμερίζει ημέρες και εισφορές ανά μήνα (ίδια λογική με build_count_report).
    Επιστρέφει (days_df, contrib_df) με στήλες ΕΤΟΣ, ΤΑΜΕΙΟ, ΚΛΑΔΟΣ/ΠΑΚΕΤΟ, ..., 1, 2, ..., 12.
    """
    required_cols = ['Από', 'Έως', 'Ημέρες']
    if not all(col in count_df.columns for col in required_cols):
        return pd.DataFrame(), pd.DataFrame()
    counting_rows = []
    def _get_num(val):
        try: return clean_numeric_value(val) or 0
        except Exception: return 0
    def _is_expected_oaee(r, duration_days):
        tam = str(r.get('Ταμείο', '')).upper()
        if 'ΟΑΕΕ' not in tam: return False
        months_val, days_val = _get_num(r.get('Μήνες')), _get_num(r.get('Ημέρες'))
        if months_val and months_val <= 2:
            if days_val and abs(days_val - months_val * 25) <= 1: return True
            if not days_val and duration_days <= 62: return True
        return False
    def _is_expected_tsm(r, duration_days, start_dt, end_dt):
        tam = str(r.get('Ταμείο', '')).upper()
        if 'ΤΣΜΕΔΕ' not in tam: return False
        months_val, days_val = _get_num(r.get('Μήνες')), _get_num(r.get('Ημέρες'))
        if pd.notna(start_dt) and pd.notna(end_dt) and start_dt.year == end_dt.year:
            sem1, sem2 = (start_dt.month == 1 and end_dt.month == 6), (start_dt.month == 7 and end_dt.month == 12)
            if sem1 or sem2:
                if months_val == 6 and (not days_val or abs(days_val - 150) <= 2): return True
                if not months_val and 150 <= duration_days <= 190: return True
        return False
    for _, row in count_df.iterrows():
        try:
            if pd.isna(row['Από']) or pd.isna(row['Έως']): continue
            start_dt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
            end_dt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')
            if pd.isna(start_dt) or pd.isna(end_dt): continue
            duration_days = (end_dt - start_dt).days + 1
            is_pre2002 = end_dt < pd.Timestamp('2002-01-01')
            expected_agg = _is_expected_oaee(row, duration_days) or _is_expected_tsm(row, duration_days, start_dt, end_dt)
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
            gross_val = 0.0 if ('ΔΡΧ' in raw_gross.upper() or 'DRX' in raw_gross.upper()) else (clean_numeric_value(raw_gross, exclude_drx=True) or 0.0)
            raw_contrib = str(row.get('Συνολικές εισφορές', ''))
            contrib_val = 0.0 if ('ΔΡΧ' in raw_contrib.upper() or 'DRX' in raw_contrib.upper()) else (clean_numeric_value(raw_contrib, exclude_drx=True) or 0.0)
            sign = get_negative_amount_sign(gross_val, contrib_val)
            if sign == -1: days_val = -abs(days_val)
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
                curr = curr.replace(year=curr.year + 1, month=1) if curr.month == 12 else curr.replace(month=curr.month + 1)
            num_months = len(months_list)
            if num_months == 0: continue
            days_per_month = days_val / num_months
            contrib_per_month = contrib_val / num_months
            for m_dt in months_list:
                counting_rows.append({
                    'ΕΤΟΣ': m_dt.year, 'ΤΑΜΕΙΟ': tameio, 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ': insurance_type,
                    'ΕΡΓΟΔΟΤΗΣ': employer, 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': klados, 'ΠΕΡΙΓΡΑΦΗ': klados_desc, 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': earnings_type,
                    'Μήνας_Num': m_dt.month, 'Ημέρες': days_per_month, 'Εισφορές_Part': contrib_per_month
                })
        except Exception:
            continue
    if not counting_rows:
        return pd.DataFrame(), pd.DataFrame()
    c_df = pd.DataFrame(counting_rows)
    pivot_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Ημέρες'].sum().reset_index()
    contrib_df = c_df.groupby(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ', 'Μήνας_Num'])['Εισφορές_Part'].sum().reset_index()
    days_pivot = pivot_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Ημέρες').fillna(0)
    contrib_pivot = contrib_df.pivot(index=['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'], columns='Μήνας_Num', values='Εισφορές_Part').fillna(0)
    for m in range(1, 13):
        if m not in days_pivot.columns: days_pivot[m] = 0
        if m not in contrib_pivot.columns: contrib_pivot[m] = 0
    month_cols_int = sorted([c for c in days_pivot.columns if isinstance(c, int)])
    contrib_pivot = contrib_pivot.reindex(days_pivot.index).fillna(0)
    days_out = days_pivot.reset_index()[['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'] + month_cols_int]
    contrib_out = contrib_pivot.reset_index()[['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ'] + month_cols_int]
    return days_out, contrib_out


def insurance_kind_classify_count(typos) -> str | None:
    s = str(typos).strip().upper()
    if 'ΜΙΣΘΩΤΗ' in s and 'ΜΗ ΜΙΣΘΩΤΗ' not in s and not s.startswith('ΜΗ '):
        return 'ΜΙΣΘΩΤΗ'
    if ('ΜΗ' in s and 'ΜΙΣΘΩΤΗ' in s) or ('NON' in s and 'SAL' in s):
        return 'ΜΗ ΜΙΣΘΩΤΗ'
    return None


def tameio_monthly_cap_days_count(tameio_val: str) -> float:
    t = str(tameio_val).upper()
    if 'ΙΚΑ' in t or 'IKA' in t:
        return 31.0
    return 25.0


def compute_kind_monthly_capped_from_c_df(c_df_src: pd.DataFrame, year: int, kind_code: str | None) -> dict[int, float]:
    """Μηνιαίες ημέρες με πλαφόν ανά ταμείο (ΙΚΑ: 31, λοιπά: 25), μετά άθροιση ανά μήνα."""
    sub = c_df_src[c_df_src['ΕΤΟΣ'] == year].copy()
    if sub.empty:
        return {m: 0.0 for m in range(1, 13)}
    sub['_k'] = sub['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'].apply(insurance_kind_classify_count)
    if kind_code is not None:
        sub = sub[sub['_k'] == kind_code]
    if sub.empty:
        return {m: 0.0 for m in range(1, 13)}
    g = sub.groupby(['ΤΑΜΕΙΟ', 'Μήνας_Num'], as_index=False)['Ημέρες'].sum()
    g['_cap'] = g['ΤΑΜΕΙΟ'].apply(tameio_monthly_cap_days_count)
    g['_capped'] = g.apply(
        lambda r: min(float(r['Ημέρες']), float(r['_cap'])),
        axis=1,
    )
    by_m = g.groupby('Μήνας_Num')['_capped'].sum()
    return {m: float(by_m.get(m, 0.0) or 0.0) for m in range(1, 13)}


def build_syntaksi_annual_table(c_df: pd.DataFrame) -> pd.DataFrame:
    """Πίνακας ανά έτος: ημέρες μισθωτή/μη μισθωτή (με πλαφόν), μικτές μόνο μισθωτή, εισφορές μόνο μη μισθωτή, τεκμαρτές (εισφορές μη μισθωτή×5), συνολικές αποδοχές (μικτές μισθωτή+τεκμαρτές)."""
    if c_df is None or c_df.empty:
        return pd.DataFrame()
    years = sorted({int(y) for y in c_df['ΕΤΟΣ'].dropna().unique()})
    rows = []
    for y in years:
        md_m = compute_kind_monthly_capped_from_c_df(c_df, y, 'ΜΙΣΘΩΤΗ')
        md_nm = compute_kind_monthly_capped_from_c_df(c_df, y, 'ΜΗ ΜΙΣΘΩΤΗ')
        days_m = sum(md_m.values())
        days_nm = sum(md_nm.values())
        sub = c_df[c_df['ΕΤΟΣ'] == y].copy()
        sub['_k'] = sub['ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ'].apply(insurance_kind_classify_count)
        gross_m = float(sub[sub['_k'] == 'ΜΙΣΘΩΤΗ']['Μικτές_Part'].sum()) if 'Μικτές_Part' in sub.columns else 0.0
        contrib_t = (
            float(sub[sub['_k'] == 'ΜΗ ΜΙΣΘΩΤΗ']['Εισφορές_Part'].sum())
            if 'Εισφορές_Part' in sub.columns
            else 0.0
        )
        tekmark = contrib_t * 5.0
        rows.append({
            'Έτος': y,
            'Σύνολο ημερών (μισθωτή)': days_m,
            'Συνολικές μικτές αποδοχές': gross_m,
            'Σύνολο ημερών (μη μισθωτή)': days_nm,
            'Συνολικές εισφορές': contrib_t,
            'Τεκμαρτές αποδοχές': tekmark,
            'Συνολικές αποδοχές': gross_m + tekmark,
        })
    return pd.DataFrame(rows)


SYN_TAXI_COLUMN_ORDER = [
    'Έτος',
    'Σύνολο ημερών (μισθωτή)',
    'Συνολικές μικτές αποδοχές',
    'Σύνολο ημερών (μη μισθωτή)',
    'Συνολικές εισφορές',
    'Κοινωνικοί Πόροι',
    'Τεκμαρτές αποδοχές',
    'Συνολικές αποδοχές',
    'ΔΤΚ',
    'Τελικές Συντ. Αποδοχές',
]

# ΚΟΙΝΩΝΙΚΟΙ ΠΟΡΟΙ (€) — πίνακας αναφοράς ανά έτος (ΔΙΚΗΓΟΡΟΙ / ΟΑΕΕ / ΤΣΜΕΔΕ)
koinwnikoi_table: dict[int, dict[str, float]] = {
    2002: {"ΔΙΚΗΓΟΡΟΙ": 44.17, "ΟΑΕΕ": 3.71, "ΤΣΜΕΔΕ": 48.32},
    2003: {"ΔΙΚΗΓΟΡΟΙ": 53.45, "ΟΑΕΕ": 3.61, "ΤΣΜΕΔΕ": 57.57},
    2004: {"ΔΙΚΗΓΟΡΟΙ": 607.59, "ΟΑΕΕ": 3.59, "ΤΣΜΕΔΕ": 52.65},
    2005: {"ΔΙΚΗΓΟΡΟΙ": 143.90, "ΟΑΕΕ": 3.62, "ΤΣΜΕΔΕ": 40.19},
    2006: {"ΔΙΚΗΓΟΡΟΙ": 166.88, "ΟΑΕΕ": 3.55, "ΤΣΜΕΔΕ": 46.27},
    2007: {"ΔΙΚΗΓΟΡΟΙ": 191.06, "ΟΑΕΕ": 6.54, "ΤΣΜΕΔΕ": 62.01},
    2008: {"ΔΙΚΗΓΟΡΟΙ": 202.56, "ΟΑΕΕ": 6.32, "ΤΣΜΕΔΕ": 57.80},
    2009: {"ΔΙΚΗΓΟΡΟΙ": 307.88, "ΟΑΕΕ": 6.48, "ΤΣΜΕΔΕ": 89.49},
    2010: {"ΔΙΚΗΓΟΡΟΙ": 165.39, "ΟΑΕΕ": 1.28, "ΤΣΜΕΔΕ": 67.15},
    2011: {"ΔΙΚΗΓΟΡΟΙ": 133.41, "ΟΑΕΕ": 1.03, "ΤΣΜΕΔΕ": 40.73},
    2012: {"ΔΙΚΗΓΟΡΟΙ": 106.46, "ΟΑΕΕ": 2.40, "ΤΣΜΕΔΕ": 35.35},
    2013: {"ΔΙΚΗΓΟΡΟΙ": 96.18, "ΟΑΕΕ": 4.33, "ΤΣΜΕΔΕ": 26.31},
    2014: {"ΔΙΚΗΓΟΡΟΙ": 66.53, "ΟΑΕΕ": 0.01, "ΤΣΜΕΔΕ": 28.15},
    2015: {"ΔΙΚΗΓΟΡΟΙ": 59.30, "ΟΑΕΕ": 0.00, "ΤΣΜΕΔΕ": 13.03},
    2016: {"ΔΙΚΗΓΟΡΟΙ": 24.12, "ΟΑΕΕ": 0.00, "ΤΣΜΕΔΕ": 3.18},
}

KOINWNIKOI_TIPO_OPTIONS = ("ΟΧΙ", "ΔΙΚΗΓΟΡΟΙ", "ΟΑΕΕ", "ΤΣΜΕΔΕ")


def _compute_koinwnikoi_poroi_column(syn_f: pd.DataFrame, tipo_sel: str) -> pd.Series:
    """(ποσό πίνακα / 25) × ημέρες μη μισθωτή (2002–2016). Κενό αν ΟΧΙ, εκτός εύρους, 0 ημέρες ή μηδενικό αποτέλεσμα."""
    n = len(syn_f)
    if tipo_sel == "ΟΧΙ" or not tipo_sel:
        return pd.Series([pd.NA] * n, index=syn_f.index, dtype=object)
    if tipo_sel not in ("ΔΙΚΗΓΟΡΟΙ", "ΟΑΕΕ", "ΤΣΜΕΔΕ"):
        return pd.Series([pd.NA] * n, index=syn_f.index, dtype=object)
    out: list = []
    nm_col = 'Σύνολο ημερών (μη μισθωτή)'
    for _, row in syn_f.iterrows():
        ey_raw = row.get('Έτος')
        try:
            ey = int(float(ey_raw))
        except (TypeError, ValueError):
            out.append(pd.NA)
            continue
        if ey < 2002 or ey > 2016:
            out.append(pd.NA)
            continue
        row_tbl = koinwnikoi_table.get(ey)
        if not row_tbl:
            out.append(pd.NA)
            continue
        base = row_tbl.get(tipo_sel)
        if base is None:
            out.append(pd.NA)
            continue
        days_nm = pd.to_numeric(row.get(nm_col), errors='coerce')
        if pd.isna(days_nm) or float(days_nm) == 0.0:
            out.append(pd.NA)
            continue
        val = (float(base) / 25.0) * float(days_nm)
        out.append(pd.NA if abs(val) < 1e-9 else val)
    return pd.Series(out, index=syn_f.index)


@st.cache_data(show_spinner=False)
def _load_dtk_table_json_cached(path_str: str, mtime_ns: int):
    """Εσωτερικό: cache μόνο επιτυχημένου φορτώματος· κλειδί mtime ώστε νέο/ενημερωμένο αρχείο να ξαναφορτώνει."""
    try:
        with open(path_str, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_dtk_table_json():
    """Φόρτωση dtk_table.json από τη ρίζα του repo (συντελεστές ΔΤΚ ανά έτος αναφοράς / έτος εισφοράς)."""
    p = REPO_ROOT / "dtk_table.json"
    if not p.is_file():
        return None
    try:
        mtime_ns = p.stat().st_mtime_ns
    except OSError:
        return None
    return _load_dtk_table_json_cached(str(p.resolve()), mtime_ns)


def _dtk_coeff_lookup(dtk_doc: dict | None, ref_year: str, contrib_year: int) -> float | None:
    """Επιστρέφει συντελεστή ΔΤΚ για έτος αναφοράς ref_year και έτος γραμμής contrib_year."""
    if not dtk_doc or not isinstance(dtk_doc, dict):
        return None
    data = dtk_doc.get("data")
    if not isinstance(data, dict):
        return None
    ref_key = str(ref_year).strip()
    row = data.get(ref_key)
    if row is None:
        try:
            row = data.get(str(int(ref_key)))
        except ValueError:
            row = None
    if not isinstance(row, dict):
        return None
    cy = int(contrib_year)
    v = row.get(str(cy))
    if v is None:
        v = row.get(cy)
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _append_exagora_footer_rows(
    syn_f: pd.DataFrame,
    dtk_doc: dict | None,
    dtk_ref_sel: str,
    poso_raw: str,
    imeres_raw: str,
    etos_ex_str: str,
) -> pd.DataFrame:
    """Κενή γραμμή + γραμμή «ΕΞΑΓΟΡΑ» με ποσό/ημέρες εξαγοράς, ΔΤΚ(έτος εξαγοράς), τεκμαρτές×5, τελικές×ΔΤΚ."""
    syn_f = syn_f.copy() if syn_f is not None else pd.DataFrame()
    cols = [c for c in SYN_TAXI_COLUMN_ORDER if c in syn_f.columns]
    if not cols:
        cols = list(SYN_TAXI_COLUMN_ORDER)
        syn_f = pd.DataFrame(columns=cols)
    else:
        syn_f = syn_f[cols].copy()
    empty_row = {c: pd.NA for c in cols}

    raw_p = str(poso_raw or "").strip()
    poso_f = None
    if raw_p:
        v = clean_numeric_value(raw_p, exclude_drx=True)
        if v is not None:
            poso_f = float(v)

    imeres_t = str(imeres_raw or "").strip()
    imeres_val = None
    if imeres_t:
        try:
            imeres_val = float(imeres_t.replace(",", ".").replace(" ", ""))
        except ValueError:
            imeres_val = None

    try:
        etos_ex = int(str(etos_ex_str).strip())
    except (ValueError, TypeError):
        etos_ex = 2026

    dtk_v = _dtk_coeff_lookup(dtk_doc, dtk_ref_sel, etos_ex)

    tek = None
    syn_ap_total = None
    telikes = None
    if poso_f is not None:
        tek = poso_f * 5.0
        syn_ap_total = 0.0 + tek
        if dtk_v is not None:
            telikes = float(syn_ap_total) * float(dtk_v)

    ex_row = {c: pd.NA for c in cols}
    ex_row['Έτος'] = 'ΕΞΑΓΟΡΑ'
    ex_row['Σύνολο ημερών (μισθωτή)'] = imeres_val if imeres_val is not None else pd.NA
    ex_row['Συνολικές μικτές αποδοχές'] = 0.0 if poso_f is not None else pd.NA
    ex_row['Σύνολο ημερών (μη μισθωτή)'] = pd.NA
    ex_row['Συνολικές εισφορές'] = poso_f if poso_f is not None else pd.NA
    ex_row['Τεκμαρτές αποδοχές'] = tek if tek is not None else pd.NA
    ex_row['Συνολικές αποδοχές'] = syn_ap_total if syn_ap_total is not None else pd.NA
    ex_row['ΔΤΚ'] = dtk_v
    ex_row['Τελικές Συντ. Αποδοχές'] = telikes if telikes is not None else pd.NA

    return pd.concat([syn_f, pd.DataFrame([empty_row]), pd.DataFrame([ex_row])], ignore_index=True)


def _append_syntaksi_grand_total_row(syn_f: pd.DataFrame) -> pd.DataFrame:
    """Τελευταία γραμμή ΣΥΝΟΛΟ: αθροίσματα στηλών (ίδιο εύρος με την Καταμέτρηση για αριθμούς), χωρίς άθροισμα ΔΤΚ."""
    if syn_f is None or syn_f.empty:
        return syn_f
    syn_f = syn_f.copy()
    cols = list(syn_f.columns)
    sub = syn_f[syn_f['Έτος'].notna()].copy()
    total_row = {c: pd.NA for c in cols}
    total_row['Έτος'] = 'ΣΥΝΟΛΟ'
    _sum_cols = [
        'Σύνολο ημερών (μισθωτή)',
        'Σύνολο ημερών (μη μισθωτή)',
        'Συνολικές μικτές αποδοχές',
        'Συνολικές εισφορές',
        'Κοινωνικοί Πόροι',
        'Τεκμαρτές αποδοχές',
        'Συνολικές αποδοχές',
        'Τελικές Συντ. Αποδοχές',
    ]
    for c in _sum_cols:
        if c in sub.columns:
            s = pd.to_numeric(sub[c], errors='coerce')
            total_row[c] = float(s.sum()) if s.notna().any() else pd.NA
    if 'ΔΤΚ' in cols:
        total_row['ΔΤΚ'] = pd.NA
    return pd.concat([syn_f, pd.DataFrame([total_row])], ignore_index=True)


def _syntaksi_summary_metrics_from_syn_f(syn_f: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    """Από γραμμή ΣΥΝΟΛΟ: Μήνες=(ημ.μισθωτή+ημ.μη μισθωτή)/25, συντάξιμες=άθροισμα τελικών, μισθός=συντάξιμες/μήνες."""
    if syn_f is None or syn_f.empty:
        return None, None, None
    row_tot = syn_f[syn_f['Έτος'].astype(str).str.strip() == 'ΣΥΝΟΛΟ']
    if row_tot.empty:
        return None, None, None
    r = row_tot.iloc[0]
    d_m = pd.to_numeric(r.get('Σύνολο ημερών (μισθωτή)'), errors='coerce')
    d_nm = pd.to_numeric(r.get('Σύνολο ημερών (μη μισθωτή)'), errors='coerce')
    d_m = float(d_m) if pd.notna(d_m) else 0.0
    d_nm = float(d_nm) if pd.notna(d_nm) else 0.0
    tot_days = d_m + d_nm
    months = tot_days / 25.0 if tot_days else 0.0
    tel = pd.to_numeric(r.get('Τελικές Συντ. Αποδοχές'), errors='coerce')
    tel_f = float(tel) if pd.notna(tel) else None
    syn_sal = (tel_f / months) if (tel_f is not None and months > 0) else None
    return months, tel_f, syn_sal


def _syntaksi_pro_num_field(value: float | int) -> dict[str, str | float | int]:
    """Μορφή τιμής για Syntaksi Pro: value + type 'number' (string)."""
    return {"value": value, "type": "number"}


def _syntaksi_pro_text_field(value: str) -> dict[str, str]:
    """Μορφή τιμής για Syntaksi Pro: value + type 'text'."""
    return {"value": value, "type": "text"}


def build_syntaksi_pro_json_str(
    syn_f_core: pd.DataFrame,
    dtk_doc: dict | None,
    dtk_ref_sel: str,
    poso_raw: str,
    imeres_raw: str,
    etos_ex_str: str,
) -> str:
    """
    JSON για εισαγωγή σε Syntaksi Pro (βλ. ΟΔΗΓΙΕΣ_JSON_EXPORT_STREAMLIT.txt).
    ika_YYYY = ημέρες μισθωτή, apodoxes_YYYY = συνολικές μικτές αποδοχές (μισθωτή).
    elep_YYYY = ceil(ημέρες μη μισθωτή / 25) ως κείμενο, eisfores_YYYY = συνολικές εισφορές.
    kerdi_YYYY: μόνο για 2017, 2018, 2019 — συνολικές εισφορές × 5 (πάντα ακριβώς τρία κλειδιά kerdi_*).
    """
    json_data: dict[str, dict[str, str | float | int]] = {}
    _kerdi_years = (2017, 2018, 2019)
    col_days = "Σύνολο ημερών (μισθωτή)"
    col_days_nm = "Σύνολο ημερών (μη μισθωτή)"
    col_gross = "Συνολικές μικτές αποδοχές"
    col_eis = "Συνολικές εισφορές"
    if syn_f_core is not None and not syn_f_core.empty and "Έτος" in syn_f_core.columns:
        for _, row in syn_f_core.iterrows():
            ey_raw = row.get("Έτος")
            try:
                if isinstance(ey_raw, str) and ey_raw.strip() in ("ΕΞΑΓΟΡΑ", "ΣΥΝΟΛΟ", ""):
                    continue
                y = int(float(ey_raw))
            except (TypeError, ValueError):
                continue
            year_str = str(y)
            dm = pd.to_numeric(row.get(col_days), errors="coerce")
            ika_val = int(round(float(dm))) if pd.notna(dm) else 0
            gr = pd.to_numeric(row.get(col_gross), errors="coerce")
            apod_val = round(float(gr), 2) if pd.notna(gr) else 0.0
            json_data[f"ika_{year_str}"] = _syntaksi_pro_num_field(ika_val)
            json_data[f"apodoxes_{year_str}"] = _syntaksi_pro_num_field(apod_val)

            d_nm = pd.to_numeric(row.get(col_days_nm), errors="coerce")
            if pd.notna(d_nm) and float(d_nm) > 0:
                elep_m = math.ceil(float(d_nm) / 25.0)
                json_data[f"elep_{year_str}"] = _syntaksi_pro_text_field(str(int(elep_m)))
            else:
                json_data[f"elep_{year_str}"] = _syntaksi_pro_text_field("")

            eis = pd.to_numeric(row.get(col_eis), errors="coerce")
            eis_raw = float(eis) if pd.notna(eis) else 0.0
            eis_val = round(eis_raw, 2)
            json_data[f"eisfores_{year_str}"] = _syntaksi_pro_num_field(eis_val)
            if y in _kerdi_years:
                json_data[f"kerdi_{year_str}"] = _syntaksi_pro_num_field(round(eis_raw * 5.0, 2))

    for _ky in _kerdi_years:
        _ks = str(_ky)
        if f"kerdi_{_ks}" not in json_data:
            json_data[f"kerdi_{_ks}"] = _syntaksi_pro_num_field(0.0)

    raw_p = str(poso_raw or "").strip()
    poso_f = 0.0
    if raw_p:
        v = clean_numeric_value(raw_p, exclude_drx=True)
        if v is not None:
            poso_f = float(v)

    imeres_t = str(imeres_raw or "").strip()
    imeres_val = 0
    if imeres_t:
        try:
            imeres_val = int(float(imeres_t.replace(",", ".").replace(" ", "")))
        except ValueError:
            imeres_val = 0

    try:
        etos_ex = int(str(etos_ex_str).strip())
    except (ValueError, TypeError):
        etos_ex = 2026

    dtk_v = _dtk_coeff_lookup(dtk_doc, dtk_ref_sel, etos_ex)
    dtk_eksagoras_f = round(float(dtk_v if dtk_v is not None else 0.0), 5)

    try:
        ref_y = int(str(dtk_ref_sel).strip())
    except (ValueError, TypeError):
        ref_y = datetime.date.today().year

    json_data["eksagorasmenes_imeres"] = _syntaksi_pro_num_field(imeres_val)
    json_data["synoliko_poso_eksagoras"] = _syntaksi_pro_num_field(round(poso_f, 2))
    json_data["dtk_eksagoras"] = _syntaksi_pro_num_field(dtk_eksagoras_f)
    json_data["dtk"] = _syntaksi_pro_num_field(ref_y)
    json_data["etos_ethnikis"] = _syntaksi_pro_num_field(ref_y)

    return json.dumps(json_data, indent=2, ensure_ascii=False)


def build_count_c_dataframe(count_df: pd.DataFrame, description_map: dict[str, str] | None = None) -> pd.DataFrame:
    """Ίδια κατανομή με Καταμέτρηση: ημέρες/μικτές/εισφορές ανά μήνα (γραμμές c_df)."""
    required_cols = ['Από', 'Έως', 'Ημέρες']
    if not all(col in count_df.columns for col in required_cols):
        return pd.DataFrame()

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
        return pd.DataFrame()
    return pd.DataFrame(counting_rows)


def build_count_report(count_df: pd.DataFrame, description_map: dict[str, str] | None = None, show_count_totals_only: bool = False):
    required_cols = ['Από', 'Έως', 'Ημέρες']
    if not all(col in count_df.columns for col in required_cols):
        return pd.DataFrame(), [], None, [], []

    c_df = build_count_c_dataframe(count_df, description_map)
    if c_df.empty:
        return pd.DataFrame(), [], None, [], []

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

    # Ανώτατο 25 ημέρες/μήνα ανά κλάδο-πακέτο, εκτός ΙΚΑ
    tameio_level = final_val.index.get_level_values('ΤΑΜΕΙΟ').astype(str).str.upper()
    is_ika = tameio_level.str.contains('ΙΚΑ', na=False)
    for m in month_cols_int:
        final_val.loc[~is_ika, m] = final_val.loc[~is_ika, m].clip(upper=25)
    final_val['ΣΥΝΟΛΟ'] = final_val[month_cols_int].sum(axis=1)

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

    month_map = {1: 'ΙΑΝ', 2: 'ΦΕΒ', 3: 'ΜΑΡ', 4: 'ΑΠΡ', 5: 'ΜΑΙ', 6: 'ΙΟΥΝ', 7: 'ΙΟΥΛ', 8: 'ΑΥΓ', 9: 'ΣΕΠ', 10: 'ΟΚΤ', 11: 'ΝΟΕ', 12: 'ΔΕΚ'}
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


def render_totals_tab(
    df: pd.DataFrame,
    description_map: dict | None = None,
    key_prefix: str = "totals",
    register_view_fn=None,
    has_parallel: bool = False,
    has_parallel_2017: bool = False,
    has_multi: bool = False,
) -> None:
    """
    Αποδίδει την καρτέλα Σύνολα (φίλτρα, πίνακας ομαδοποίησης, metrics).
    Χρησιμοποιείται και στο app_final και στο app_lite.
    """
    if description_map is None:
        description_map = {}
    if 'Κλάδος/Πακέτο Κάλυψης' not in df.columns:
        st.warning("Η στήλη 'Κλάδος/Πακέτο Κάλυψης' δεν βρέθηκε στα δεδομένα.")
        return
    st.markdown("### Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)")
    row1_cols = st.columns([2, 1, 1])
    filter_cols = st.columns([0.9, 1.3, 1.2, 2.0, 0.9, 0.9])
    summary_df = df.copy()
    summary_df['Κλάδος/Πακέτο Κάλυψης'] = (
        summary_df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
    )
    apod_col = next((c for c in df.columns if 'Τύπος Αποδοχών' in c and 'Περιγραφή' not in c), None)
    if apod_col and apod_col in summary_df.columns:
        summary_df[apod_col] = summary_df[apod_col].astype(str).str.strip()
    summary_df['Από_dt'] = pd.to_datetime(summary_df.get('Από'), format='%d/%m/%Y', errors='coerce')
    summary_df['Έως_dt'] = pd.to_datetime(summary_df.get('Έως'), format='%d/%m/%Y', errors='coerce')

    selected_tameia = []
    selected_typos = []
    selected_typos_apodochon = []
    selected_klados = []
    from_summary_str = ''
    to_summary_str = ''

    with filter_cols[0]:
        if 'Ταμείο' in summary_df.columns:
            tameia_options = sorted(summary_df['Ταμείο'].dropna().astype(str).unique().tolist())
            selected_tameia = st.multiselect(
                "Ταμείο:",
                options=tameia_options,
                default=[],
                key=f"{key_prefix}_filter_tameio"
            )
        else:
            selected_tameia = []

    with filter_cols[1]:
        if 'Τύπος Ασφάλισης' in summary_df.columns:
            typos_options = sorted(summary_df['Τύπος Ασφάλισης'].dropna().astype(str).str.strip().unique().tolist())
            typos_options = [t for t in typos_options if t and t.lower() not in ('nan', 'none', '')]
            selected_typos = st.multiselect(
                "Τύπος ασφάλισης:",
                options=typos_options,
                default=[],
                key=f"{key_prefix}_filter_typos"
            )
        else:
            selected_typos = []

    with filter_cols[2]:
        if apod_col:
            apod_opts = sorted(summary_df[apod_col].dropna().astype(str).str.strip().unique().tolist())
            apod_opts = [a for a in apod_opts if a and a.lower() not in ('nan', 'none', '')]
            selected_typos_apodochon = st.multiselect(
                "Τύπος αποδοχών:",
                options=apod_opts,
                default=[],
                key=f"{key_prefix}_filter_typos_apodochon"
            )
        else:
            selected_typos_apodochon = []

    with filter_cols[3]:
        klados_raw = summary_df['Κλάδος/Πακέτο Κάλυψης'].dropna().astype(str).str.strip()
        klados_codes = sorted([c for c in klados_raw.unique().tolist() if c and c.lower() not in ('nan', 'none', '')])
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
        selected_klados_labels = st.multiselect(
            "Κλάδος/Πακέτο Κάλυψης:",
            options=klados_options_with_desc,
            default=[],
            key=f"{key_prefix}_filter_klados"
        )
        selected_klados = [klados_code_map.get(opt, opt) for opt in selected_klados_labels]

    with filter_cols[4]:
        from_summary_str = st.text_input(
            "Από (dd/mm/yyyy):",
            value="",
            placeholder="01/01/1980",
            key=f"{key_prefix}_filter_from"
        )

    with filter_cols[5]:
        to_summary_str = st.text_input(
            "Έως (dd/mm/yyyy):",
            value="",
            placeholder="31/12/2025",
            key=f"{key_prefix}_filter_to"
        )

    total_ins_days = None
    total_years_val = None
    display_summary = None
    year_days = 300

    if 'Ταμείο' in summary_df.columns and selected_tameia:
        summary_df = summary_df[summary_df['Ταμείο'].isin(selected_tameia)]
    if 'Τύπος Ασφάλισης' in summary_df.columns and selected_typos:
        summary_df = summary_df[summary_df['Τύπος Ασφάλισης'].astype(str).str.strip().isin(selected_typos)]
    if apod_col and selected_typos_apodochon:
        summary_df = summary_df[summary_df[apod_col].astype(str).str.strip().isin(selected_typos_apodochon)]
    if 'Κλάδος/Πακέτο Κάλυψης' in summary_df.columns and selected_klados:
        summary_df = summary_df[summary_df['Κλάδος/Πακέτο Κάλυψης'].isin(selected_klados)]
    from_dt = None
    to_dt = None
    if from_summary_str:
        try:
            from_dt = pd.to_datetime(from_summary_str, format='%d/%m/%Y')
            summary_df = summary_df[summary_df['Έως_dt'] >= from_dt]
        except Exception:
            st.warning("Μη έγκυρη ημερομηνία στο πεδίο Από για τη Συνολα.")
    if to_summary_str:
        try:
            to_dt = pd.to_datetime(to_summary_str, format='%d/%m/%Y')
            summary_df = summary_df[summary_df['Από_dt'] <= to_dt]
        except Exception:
            st.warning("Μη έγκυρη ημερομηνία στο πεδίο Έως για τη Συνολα.")

    summary_df = summary_df.dropna(subset=['Από_dt'])
    summary_df_for_dk = summary_df.copy()

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
    if 'Τύπος Ασφάλισης' in summary_df.columns:
        group_keys.append('Τύπος Ασφάλισης')
    show_apod_detail = bool(apod_col and selected_typos_apodochon)
    if show_apod_detail and apod_col in summary_df.columns:
        group_keys.append(apod_col)
    agg_spec = {
        'Από_dt': 'min',
        'Έως_dt': 'max',
        'Έτη': 'sum',
        'Μήνες': 'sum',
        'Ημέρες': 'sum',
        'Μικτές αποδοχές': 'sum',
        'Συνολικές εισφορές': 'sum'
    }
    agg_dict = {col: agg_spec[col] for col in agg_spec if col in summary_df.columns}
    if not agg_dict:
        st.warning("Δεν βρέθηκαν στήλες για ομαδοποίηση στη Συνοπτική Αναφορά.")
        return
    grouped = summary_df.groupby(group_keys).agg(agg_dict).reset_index()
    for col in ['Έτη', 'Μήνες', 'Ημέρες', 'Μικτές αποδοχές', 'Συνολικές εισφορές']:
        if col not in grouped.columns:
            grouped[col] = 0

    basis_label = st.session_state.get('ins_days_basis', 'Μήνας = 25, Έτος = 300')
    if str(basis_label).startswith('Μήνας = 30'):
        month_days, year_days = 30, 360
    else:
        month_days, year_days = 25, 300

    raw_total_days = (
        grouped['Ημέρες'].fillna(0) +
        grouped['Μήνες'].fillna(0) * month_days +
        grouped['Έτη'].fillna(0) * year_days
    )
    capped_days, exceeded_months = compute_summary_capped_days_by_group(
        summary_df, group_keys, month_days=month_days, year_days=year_days, ika_month_days=31,
        from_dt=from_dt, to_dt=to_dt
    )
    if not capped_days.empty:
        merge_keys = [k for k in group_keys if k in capped_days.columns]
        grouped = grouped.merge(capped_days, on=merge_keys, how='left')
        total_days = grouped['Συνολικές_Ημέρες_cap'].fillna(raw_total_days)
        grouped = grouped.drop(columns=['Συνολικές_Ημέρες_cap'])
    else:
        total_days = raw_total_days

    grouped['Συνολικές ημέρες'] = total_days.round(0).astype(int)
    years_series = (grouped['Συνολικές ημέρες'].astype(float) // year_days)
    remaining_after_years = grouped['Συνολικές ημέρες'].astype(float) - (years_series * year_days)
    months_series = (remaining_after_years // month_days)
    days_series = remaining_after_years - (months_series * month_days)
    grouped['Έτη'] = years_series
    grouped['Μήνες'] = months_series
    grouped['Ημέρες'] = days_series

    grouped['Από'] = grouped['Από_dt'].dt.strftime('%d/%m/%Y')
    grouped['Έως'] = grouped['Έως_dt'].dt.strftime('%d/%m/%Y')
    grouped = grouped.drop(columns=['Από_dt', 'Έως_dt'])

    record_counts = summary_df.groupby(group_keys).size().reset_index(name='Αριθμός Εγγραφών')
    summary_final = grouped.merge(record_counts, on=group_keys, how='left')

    if 'Κωδικός Κλάδων / Πακέτων Κάλυψης' in df.columns and 'Περιγραφή' in df.columns:
        desc_df_merge = df[['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']].copy()
        desc_df_merge = desc_df_merge.dropna(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή'])
        desc_df_merge = desc_df_merge[desc_df_merge['Κωδικός Κλάδων / Πακέτων Κάλυψης'] != '']
        desc_df_merge = desc_df_merge[desc_df_merge['Περιγραφή'] != '']
        desc_df_merge = desc_df_merge.drop_duplicates(subset=['Κωδικός Κλάδων / Πακέτων Κάλυψης'])
        desc_df_merge.columns = ['Κλάδος/Πακέτο Κάλυψης', 'Περιγραφή']
        desc_df_merge['Κλάδος/Πακέτο Κάλυψης'] = desc_df_merge['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
        summary_final = summary_final.merge(desc_df_merge, on='Κλάδος/Πακέτο Κάλυψης', how='left')

    desired_order = ['Κλάδος/Πακέτο Κάλυψης', 'Ταμείο', 'Τύπος Ασφάλισης']
    if show_apod_detail and apod_col:
        desired_order.append(apod_col)
    desired_order += ['Περιγραφή', 'Από', 'Έως', 'Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες',
                      'Μικτές αποδοχές', 'Συνολικές εισφορές', 'Αριθμός Εγγραφών']
    columns_order = [c for c in desired_order if c in summary_final.columns]
    summary_final = summary_final[columns_order]

    display_summary = summary_final.copy()
    for curr_col in ['Μικτές αποδοχές', 'Συνολικές εισφορές']:
        if curr_col in display_summary.columns:
            display_summary[curr_col] = display_summary[curr_col].apply(format_currency)
    for col in ['Συνολικές ημέρες', 'Έτη', 'Μήνες', 'Ημέρες', 'Αριθμός Εγγραφών']:
        if col in display_summary.columns:
            decimals = 1 if col in ['Έτη', 'Μήνες'] else 0
            display_summary[col] = display_summary[col].apply(
                lambda x, d=decimals: format_number_greek(x, decimals=d) if pd.notna(x) and x != '' else x
            )

    if selected_klados and 'Συνολικές ημέρες' in summary_final.columns:
        if not capped_days.empty:
            total_ins_days = int(capped_days['Συνολικές_Ημέρες_cap'].sum())
        else:
            total_ins_days = int(summary_final['Συνολικές ημέρες'].sum())
        total_years_val = total_ins_days / year_days if year_days else 0

    with row1_cols[0]:
        st.info("Επιλέξτε πακέτα κάλυψης για να δείτε την αθροιστική προϋπηρεσία.")
    with row1_cols[1]:
        m_val = format_number_greek(total_ins_days, decimals=0) if total_ins_days is not None else "•"
        st.metric("Εκτίμηση Ημερών Ασφάλισης", m_val)
    with row1_cols[2]:
        y_val = format_number_greek(total_years_val, decimals=1) if total_years_val is not None else "•"
        st.metric("Συνολικά Έτη", y_val)

    if has_parallel or has_parallel_2017 or has_multi:
        parts = []
        if has_parallel:
            parts.append("Παράλληλη ασφάλιση")
        if has_parallel_2017:
            parts.append("Παράλληλη απασχόληση")
        if has_multi:
            parts.append("Πολλαπλή απασχόληση")
        st.warning(
            f"**Εντοπίστηκε: {' / '.join(parts)}.** Το άθροισμα ημερών ασφάλισης μπορεί να δώσει παραπλανητικό αποτέλεσμα. "
            "Ελέγξτε τις αντίστοιχες καρτέλες για λεπτομέρειες."
        )

    if exceeded_months is not None and not exceeded_months.empty:
        month_names = {1: 'Ιαν', 2: 'Φεβ', 3: 'Μαρ', 4: 'Απρ', 5: 'Μαϊ', 6: 'Ιουν', 7: 'Ιουλ', 8: 'Αυγ', 9: 'Σεπ', 10: 'Οκτ', 11: 'Νοε', 12: 'Δεκ'}
        lines = []
        for _, r in exceeded_months.iterrows():
            m = int(r.get('Μήνας', 0))
            y = int(r.get('Έτος', 0))
            m_str = month_names.get(m, str(m))
            pkg = r.get('Κλάδος/Πακέτο Κάλυψης', '')
            tameio = r.get('Ταμείο', '')
            typos = r.get('Τύπος Ασφάλισης', '')
            lim = int(r.get('Όριο', 0))
            over = r.get('Υπέρβαση', 0)
            lines.append(f"**Πακέτο {pkg}**" + (f" | Ταμείο: {tameio}" if tameio else "") + (f" | Τύπος: {typos}" if typos else "") + f" — Μήνας **{m_str} {y}**: {int(r.get('Ημέρες', 0))} ημέρες (όριο {lim}, υπέρβαση +{over})")
        st.warning(
            "**Υπέρβαση ορίου ημερών ανά μήνα** (εφαρμόστηκε πλαφόν: ΙΚΑ 31 ημ./μήνα, ΕΤΑΑ-ΤΑΝ/ΚΕΑΔ και υπόλοιπα 25 ημ./μήνα· για ΕΤΑΑ-ΤΑΝ/ΚΕΑΔ το μήνυμα μόνο όταν >30 ημ./μήνα):\n\n" + "\n\n".join(lines)
        )

    st.dataframe(display_summary, width="stretch")
    if register_view_fn is not None:
        register_view_fn("Συνολα - Ομαδοποίηση", display_summary)
    render_print_button(
        f"{key_prefix}_print",
        "Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)",
        display_summary,
        description="Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης για τις περιόδους που εμφανίζονται, καθώς και άθροισμα αποδοχών και εισφορών (μόνο των εγγραφών σε €)."
    )

    # --- Σημαντικά διαστήματα (από capped ημέρες ανά μήνα) ---
    if selected_klados and not summary_df_for_dk.empty:
        dk_group_keys = ['Κλάδος/Πακέτο Κάλυψης']
        if 'Ταμείο' in summary_df_for_dk.columns:
            dk_group_keys.append('Ταμείο')
        if 'Τύπος Ασφάλισης' in summary_df_for_dk.columns:
            dk_group_keys.append('Τύπος Ασφάλισης')
        dk_df = compute_summary_capped_dk(
            summary_df_for_dk, dk_group_keys, month_days=month_days, year_days=year_days,
            ika_month_days=31, from_dt=from_dt, to_dt=to_dt, description_map=description_map
        )
        if not dk_df.empty:
            dk_calc1 = int(dk_df['dk1'].sum())
            dk_calc3 = int(dk_df['dk3'].sum())
            dk_calc4 = int(dk_df['dk4'].sum())
            dk_calc5 = int(dk_df['dk5'].sum())
            dk_calc6 = int(dk_df['dk6'].sum())
            dk_calc7a = int(dk_df['dk7a'].sum())
            dk_calc7b = int(dk_df['dk7b'].sum())
            dk_calc7c = int(dk_df['dk7c'].sum())
            _max_year = summary_df_for_dk['Έως_dt'].dt.year.max() if 'Έως_dt' in summary_df_for_dk.columns else None
        else:
            dk_calc1 = dk_calc3 = dk_calc4 = dk_calc5 = dk_calc6 = dk_calc7a = dk_calc7b = dk_calc7c = 0
            _max_year = None

        def _fmt_dk(v):
            return format_number_greek(v, decimals=0) if v > 0 else "—"

        with st.expander("📊 Σημαντικά διαστήματα", expanded=True):
            dk_items = [
                ("1. Ημέρες από 1/1/2002 έως σήμερα", _fmt_dk(dk_calc1)),
                ("2. Μήνες από 1/1/2002 (ημέρες / 25)", format_number_greek(round(dk_calc1 / 25, 1), decimals=1) if dk_calc1 > 0 else "—"),
                ("3. Τελευταία 5 έτη από σήμερα", _fmt_dk(dk_calc3)),
                (f"4. Τελευταία 5 έτη από τελευταίο ({_max_year if pd.notna(_max_year) else '—'})", _fmt_dk(dk_calc4)),
                ("5. Ημέρες έως 31/12/2014", _fmt_dk(dk_calc5)),
                ("6. Βαρέα τα τελευταία 17 έτη από σήμερα (6205 ημέρες)", _fmt_dk(dk_calc6)),
                ("7a. Ημέρες έως 31/12/2010", _fmt_dk(dk_calc7a)),
                ("7b. Ημέρες έως 31/12/2011", _fmt_dk(dk_calc7b)),
                ("7c. Ημέρες έως 31/12/2012", _fmt_dk(dk_calc7c)),
            ]
            dk_cols_ui = st.columns(3)
            for i, (label, value) in enumerate(dk_items):
                with dk_cols_ui[i % 3]:
                    st.metric(label, value)


def main():
    """Κύρια συνάρτηση της εφαρμογής (ATLAS Lite)."""
    _main_inner()


def _main_inner():
    """Σώμα εφαρμογής (overlay: try/finally στο if __name__)."""

    # Αρχική κατάσταση - ανέβασμα αρχείου
    if 'file_uploaded' not in st.session_state:
        st.session_state['file_uploaded'] = False
    if 'processing_done' not in st.session_state:
        st.session_state['processing_done'] = False
    if 'show_filters' not in st.session_state:
        st.session_state['show_filters'] = False
    if 'filters_applied' not in st.session_state:
        st.session_state['filters_applied'] = False
    if 'filter_logic' not in st.session_state:
        st.session_state['filter_logic'] = 'AND'
    
    # Μωβ Header (ATLAS Lite)
    st.markdown(
        '<div class="purple-header">ATLAS Lite</div>',
        unsafe_allow_html=True,
    )

    # Προσθήκη ημερομηνίας τελευταίας ενημέρωσης
    st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.85rem; margin-top: 0.5rem; margin-bottom: 1rem;'>{get_last_update_date()}</div>", unsafe_allow_html=True)
    
    # Εμφάνιση ανεβάσματος αρχείου
    if not st.session_state['file_uploaded']:
        # Προτροπή και Upload - τίτλος
        st.markdown('<div class="upload-prompt-text">Ανεβάστε το αρχείο ΑΤΛΑΣ για ανάλυση</div>', unsafe_allow_html=True)
        
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
                    1. Μεταβείτε στην υπηρεσία του e-ΕΦΚΑ πατώντας <a href="https://www.e-efka.gov.gr/el/elektronikes-yperesies/synoptiko-kai-analytiko-istoriko-asphalises" target="_blank" class="efka-link">εδώ</a>.<br>
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
                    © 2026 Χαράλαμπος Ματωνάκης - myadvisor 
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
            
            st.info(
                "**Πριν την προβολή:** Αν δεν εμφανίζεται η ανάλυση ή η HTML αναφορά, ελέγξτε αν ο browser αποκλείει **αναδυόμενα παράθυρα** (pop-ups). "
                "Δείτε το σχετικό [βίντεο οδηγίες](https://www.loom.com/share/9b9fe5f9300f42a7a1cfd1315f629145)."
            )
            
            if st.button("Άνοιγμα / Προβολή", type="primary", width="stretch", key="open_html_btn"):
                st.session_state['open_html_report'] = True
            
            if st.session_state.get('open_html_report'):
                from html_viewer_builder import generate_full_html_report
                client_name = st.session_state.get('client_name', '')
                _app_title = "ATLAS Lite"
                _subtitle = ""
                with st.spinner("Παραγωγή της HTML αναφοράς — παρακαλώ περιμένετε…"):
                    viewer_html, _ = generate_full_html_report(
                        df, client_name=client_name,
                        app_title=_app_title, app_subtitle=_subtitle,
                        full_save_suffix="ATLAS_Lite.html",
                    )
                js_content = json.dumps(viewer_html).replace("</script>", "<\\/script>")
                components.html(
                    f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>(function(){{var h={js_content};var b=new Blob([h],{{type:'text/html;charset=utf-8'}});
var u=URL.createObjectURL(b);window.open(u,'_blank');}})();</script>
<p style="margin:0;font-size:14px;color:#666;">Άνοιγμα HTML αναφοράς...</p></body></html>""",
                    height=40,
                )
                st.session_state['open_html_report'] = False
            
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
                
                # Εμφάνιση μηνύματος + κουμπιών
                with button_placeholder.container():
                    st.info(
                        "**Πριν την προβολή:** Αν δεν εμφανίζεται η ανάλυση ή η HTML αναφορά, ελέγξτε αν ο browser αποκλείει **αναδυόμενα παράθυρα** (pop-ups). "
                        "Δείτε το σχετικό [βίντεο οδηγίες](https://www.loom.com/share/9b9fe5f9300f42a7a1cfd1315f629145)."
                    )
                    if st.button("Άνοιγμα / Προβολή", type="primary", width="stretch", key="open_html_btn"):
                        st.session_state['open_html_report'] = True
                
                # Εμφάνιση summary
                with summary_placeholder.container():
                    st.success(f"Εξήχθησαν {len(df)} γραμμές δεδομένων από {df['Σελίδα'].nunique() if 'Σελίδα' in df.columns else 0} σελίδες")
            else:
                st.error("Δεν βρέθηκαν δεδομένα για εξαγωγή")
                
                # Reset button
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("Δοκιμάστε Ξανά", width="stretch"):
                        # Reset session state
                        for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data', 'filename']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()

if __name__ == "__main__":
    main()

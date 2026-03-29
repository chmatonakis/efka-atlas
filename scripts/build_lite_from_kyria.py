# -*- coding: utf-8 -*-
"""Μία φορά / μετά από αλλαγές στην Κυρία: αναγεννά το LOCAL_DEV/lite/app_lite.py."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KYRIA = ROOT / "LOCAL_DEV" / "kyria" / "app_final.py"
LITE_OUT = ROOT / "LOCAL_DEV" / "lite" / "app_lite.py"


def main() -> None:
    text = KYRIA.read_text(encoding="utf-8")
    i = text.find("def show_results_page")
    j = text.find("\ndef main():")
    if i == -1 or j == -1:
        raise SystemExit(f"Δεν βρέθηκαν σημεία τομής (i={i}, j={j})")
    body = text[:i] + text[j + 1 :]

    body = body.replace(
        '"""\ne-EFKA PDF Data Extractor - Final Version\nΤελική, σταθερή έκδοση με multi-page functionality\n"""',
        '"""\nATLAS Lite — αυτόνομη Streamlit εφαρμογή\n\n'
        "Παράγεται από LOCAL_DEV/kyria/app_final.py (scripts/build_lite_from_kyria.py). "
        "Χωρίς Streamlit σελίδα αποτελεσμάτων· μόνο HTML μέσω «Άνοιγμα / Προβολή».\n\"\"\"",
        1,
    )

    body = body.replace(
        '# Ρύθμιση σελίδας (Κυρία)\nst.set_page_config(\n    page_title="Ασφαλιστικό βιογραφικό ΑΤΛΑΣ",',
        '# Ρύθμιση σελίδας (ATLAS Lite)\nst.set_page_config(\n    page_title="ATLAS Lite",',
        1,
    )

    body = body.replace(
        'def main():\n    """Κύρια συνάρτηση της εφαρμογής (Κυρία)."""',
        'def main():\n    """Κύρια συνάρτηση της εφαρμογής (ATLAS Lite)."""',
        1,
    )

    # Αφαίρεση session key show_results (δεν χρησιμοποιείται στη Lite)
    body = body.replace(
        "    if 'show_results' not in st.session_state:\n"
        "        st.session_state['show_results'] = False\n",
        "",
        1,
    )

    # Αφαίρεση ολόκληρης ροής Streamlit αποτελεσμάτων
    marker_start = "    # Εμφάνιση αποτελεσμάτων — 97% πλάτος"
    marker_end = "    # Μωβ Header\n"
    a = body.find(marker_start)
    b = body.find(marker_end, a)
    if a == -1 or b == -1:
        raise SystemExit("Δεν βρέθηκε μπλοκ αποτελεσμάτων για αφαίρεση")
    body = body[:a] + "    # Μωβ Header (ATLAS Lite)\n" + body[b + len(marker_end) :]

    body = body.replace(
        "        '<div class=\"purple-header\">Ασφαλιστικό βιογραφικό ΑΤΛΑΣ</div>',",
        "        '<div class=\"purple-header\">ATLAS Lite</div>',",
        1,
    )

    # Μετά την επεξεργασία: μόνο ένα κουμπί (δύο σημεία, διαφορετική εσοχή)
    # Streamlit: width="stretch" (νεότερο) ή use_container_width=True (παλιότερο)
    def _btn_kw(width_stretch: bool) -> str:
        return 'width="stretch"' if width_stretch else "use_container_width=True"

    for stretch in (True, False):
        kw = _btn_kw(stretch)
        old_a = f"""            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("Προβολή Αποτελεσμάτων", type="primary", {kw}, key="show_results_btn"):
                    st.session_state['show_results'] = True
                    st.rerun()
            with col2:
                if st.button("Γρήγορη Προβολή - HTML", type="secondary", {kw}, key="open_html_btn"):
                    st.session_state['open_html_report'] = True
"""
        old_b = f"""                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        if st.button("Προβολή Αποτελεσμάτων", type="primary", {kw}, key="show_results_btn"):
                            st.session_state['show_results'] = True
                            st.rerun()
                    with col2:
                        if st.button("Γρήγορη Προβολή - HTML", type="secondary", {kw}, key="open_html_btn"):
                            st.session_state['open_html_report'] = True
"""
        new_a = """            if st.button("Άνοιγμα / Προβολή", type="primary", width="stretch", key="open_html_btn"):
                st.session_state['open_html_report'] = True
"""
        new_b = """                    if st.button("Άνοιγμα / Προβολή", type="primary", width="stretch", key="open_html_btn"):
                        st.session_state['open_html_report'] = True
"""
        if old_a in body and old_b in body:
            body = body.replace(old_a, new_a, 1)
            body = body.replace(old_b, new_b, 1)
            break
    else:
        raise SystemExit(
            "Δεν βρέθηκαν τα μπλοκ κουμπιών (αναμενόμενα 2 εκδοχές εσοχής, stretch ή use_container_width)"
        )

    body = body.replace(
        '                _app_title = "ATLAS"\n                _subtitle = "Ασφαλιστικό Βιογραφικό"',
        '                _app_title = "ATLAS Lite"\n                _subtitle = ""',
        1,
    )

    body = body.replace(
        """                    viewer_html, _ = generate_full_html_report(
                        df, client_name=client_name,
                        app_title=_app_title, app_subtitle=_subtitle,
                    )""",
        """                    viewer_html, _ = generate_full_html_report(
                        df, client_name=client_name,
                        app_title=_app_title, app_subtitle=_subtitle,
                        full_save_suffix="ATLAS_Lite.html",
                    )""",
        1,
    )

    body = body.replace(
        "                        for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data', 'show_results', 'filename']:",
        "                        for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data', 'filename']:",
        1,
    )

    LITE_OUT.write_text(body, encoding="utf-8")
    print("OK:", LITE_OUT)


if __name__ == "__main__":
    main()

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

    # Αντικατάσταση ροής HTML μετά την εξαγωγή (πριν από άλλα replaces στο page config marker)
    _lite_html_flow = '''def _atlas_open_html_report_now(
    df: pd.DataFrame,
    *,
    wait_slot=None,
) -> None:
    """Ένα κλικ: μήνυμα αναμονής + παραγωγή HTML (ATLAS Lite)."""
    if wait_slot is not None:
        with wait_slot.container():
            _atlas_show_html_wait_top()
        _atlas_render_full_html_report_open_tab(df)
        wait_slot.empty()
    else:
        _atlas_show_html_wait_top()
        _atlas_render_full_html_report_open_tab(df)


def _atlas_show_post_extract_choices(
    df: pd.DataFrame,
    *,
    html_btn_key: str = "open_html_btn",
    streamlit_btn_key: str = "show_results_btn",
) -> None:
    """Οθόνη επιλογής μετά την εξαγωγή PDF (ATLAS Lite)."""
    st.markdown("### Επεξεργασία Ολοκληρώθηκε")

    st.info(
        "**Πριν την προβολή:** Αν δεν εμφανίζεται η ανάλυση ή η HTML αναφορά, ελέγξτε αν ο browser αποκλείει **αναδυόμενα παράθυρα** (pop-ups). "
        "Δείτε το σχετικό [βίντεο οδηγίες](https://www.loom.com/share/9b9fe5f9300f42a7a1cfd1315f629145)."
    )

    _html_wait_ph = st.empty()
    _pp_pad_l, _pp_mid, _pp_pad_r = st.columns([1, 2, 1], vertical_alignment="center")
    with _pp_mid:
        if st.button(
            "Άνοιγμα / Προβολή",
            type="primary",
            use_container_width=True,
            key=html_btn_key,
            help="Πλήρης HTML αναφορά σε νέα καρτέλα (επιτρέψτε pop-ups).",
        ):
            _atlas_open_html_report_now(df, wait_slot=_html_wait_ph)

    st.success(
        f"Εξήχθησαν {len(df)} γραμμές δεδομένων από "
        f"{df['Σελίδα'].nunique() if 'Σελίδα' in df.columns else 0} σελίδες"
    )

'''
    _flow_start = "def _atlas_open_html_report_now("
    _flow_end = "# Ρύθμιση σελίδας (Κυρία)"
    _a = body.find(_flow_start)
    _b = body.find(_flow_end, _a)
    if _a == -1 or _b == -1:
        raise SystemExit("Lite build: δεν βρέθηκε μπλοκ _atlas_open_html_report_now / post_extract")
    body = body[:_a] + _lite_html_flow + body[_b:]

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

    body = body.replace(
        '    _app_title = "ATLAS Pro" if edition == "pro" else "ATLAS"\n'
        '    _report_kwargs = {\n'
        '        "client_name": client_name,\n'
        '        "app_title": _app_title,\n'
        '        "app_subtitle": "Ασφαλιστικό Βιογραφικό",\n'
        '    }',
        '    _app_title = "ATLAS Lite"\n'
        '    _report_kwargs = {\n'
        '        "client_name": client_name,\n'
        '        "app_title": _app_title,\n'
        '        "app_subtitle": "",\n'
        '        "full_save_suffix": "ATLAS_Lite.html",\n'
        '    }',
        1,
    )

    body = body.replace(
        'def _atlas_render_full_html_report_open_tab(df: pd.DataFrame, edition: str = "lite") -> None:',
        'def _atlas_render_full_html_report_open_tab(df: pd.DataFrame) -> None:',
        1,
    )
    body = body.replace(
        '\n    edition: "lite" (προεπιλογή) ή "pro" (επιπλέον καρτέλες — υπό σταδιακή μεταφορά).\n',
        '\n',
        1,
    )
    body = body.replace(
        '    if "edition" in inspect.signature(generate_full_html_report).parameters:\n'
        '        _report_kwargs["edition"] = edition\n',
        '    _report_kwargs["edition"] = "lite"\n',
        1,
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

    # Νεότερη Κυρία: `_atlas_render_full_html_report_open_tab` (χωρίς inline _app_title στο main)
    body = body.replace(
        """        viewer_html, _ = generate_full_html_report(
            df,
            client_name=client_name,
            app_title="ATLAS",
            app_subtitle="Ασφαλιστικό Βιογραφικό",
        )""",
        """        viewer_html, _ = generate_full_html_report(
            df,
            client_name=client_name,
            app_title="ATLAS Lite",
            app_subtitle="",
            full_save_suffix="ATLAS_Lite.html",
        )""",
        1,
    )

    body = body.replace(
        "                        for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data', 'show_results', 'filename']:",
        "                        for key in ['file_uploaded', 'processing_done', 'uploaded_file', 'extracted_data', 'filename']:",
        1,
    )
    body = body.replace(
        "                            'show_results', 'filename',\n",
        "                            'filename',\n",
        1,
    )

    # Στη Lite: χωρίς μήνυμα σύστασης ATLAS Pro
    body = body.replace(
        "            st.warning(_ATLAS_PRO_HTML_RECOMMEND_MSG)\n            \n", "", 1
    )
    body = body.replace(
        "                    st.warning(_ATLAS_PRO_HTML_RECOMMEND_MSG)\n", "", 1
    )
    body = body.replace("    st.warning(_ATLAS_PRO_HTML_RECOMMEND_MSG)\n\n", "", 1)

    # Στη Lite: μόνο αφαίρεση JS styling δύο κουμπιών (κρατάμε wait helpers)
    inj = "def _atlas_inject_post_process_choice_buttons_style() -> None:"
    inj_i = body.find(inj)
    if inj_i != -1:
        inj_j = body.find("_ATLAS_PRO_HTML_RECOMMEND_MSG", inj_i)
        if inj_j == -1:
            inj_j = body.find("_ATLAS_HTML_WAIT_MSG", inj_i)
        if inj_j == -1:
            raise SystemExit("Lite build: δεν βρέθηκε _ATLAS_HTML_WAIT_MSG μετά το _atlas_inject")
        body = body[:inj_i].rstrip() + "\n\n" + body[inj_j:]
        body = body.replace(
            "_ATLAS_PRO_HTML_RECOMMEND_MSG = (\n"
            '    "**Σημαντικό:** Προτείνουμε να χρησιμοποιείτε πλέον τη νέα έκδοση ATLAS Pro "\n'
            '    "που είναι ταχύτερη και πιο ευέλικτη. Σύντομα αυτή θα είναι το βασικό μας εργαλείο."\n'
            ")\n\n",
            "",
            1,
        )

    LITE_OUT.write_text(body, encoding="utf-8")
    (ROOT / "app_lite.py").write_text(body, encoding="utf-8")
    (ROOT / "app_final.py").write_text(KYRIA.read_text(encoding="utf-8"), encoding="utf-8")
    print("OK:", LITE_OUT)
    print("OK:", ROOT / "app_lite.py")
    print("OK:", ROOT / "app_final.py")


if __name__ == "__main__":
    main()

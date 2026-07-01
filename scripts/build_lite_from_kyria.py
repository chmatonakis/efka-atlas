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

    # Μετά την επεξεργασία: μόνο ένα κουμπί (ATLAS Lite)
    new_a = """            _pp_pad_l, _pp_mid, _pp_pad_r = st.columns([1, 2, 1], vertical_alignment="center")
            with _pp_mid:
                if st.button("Άνοιγμα / Προβολή", type="primary", use_container_width=True, key="open_html_btn"):
                    _atlas_open_html_report_now(df, wait_slot=_html_wait_ph)
"""
    new_b = """                    _pp_pad_l, _pp_mid, _pp_pad_r = st.columns([1, 2, 1], vertical_alignment="center")
                    with _pp_mid:
                        if st.button("Άνοιγμα / Προβολή", type="primary", use_container_width=True, key="open_html_btn"):
                            _atlas_open_html_report_now(df, wait_slot=_html_wait_ph)
"""

    def _btn_kw(width_stretch: bool) -> str:
        return 'width="stretch"' if width_stretch else "use_container_width=True"

    pro_html_a = """            _pp_pad_l, _pp_mid, _pp_pad_r = st.columns([1, 2, 1], vertical_alignment="center")
            with _pp_mid:
                _pp_b1, _pp_b2 = st.columns(2, vertical_alignment="center")
                with _pp_b1:
                    if st.button(
                        "ATLAS Pro\\n(νέο)",
                        type="primary",
                        use_container_width=True,
                        key="open_html_pro_btn",
                        help="Πλήρης HTML αναφορά Pro σε νέα καρτέλα (επιτρέψτε pop-ups).",
                    ):
                        _atlas_open_html_report_now(df, edition="pro", wait_slot=_html_wait_ph)
                with _pp_b2:
                    if st.button(
                        "ATLAS Pro\\n(παλιότερο)",
                        type="secondary",
                        use_container_width=True,
                        key="show_results_btn",
                        help="Πλήρης ανάλυση στην εφαρμογή (όλες οι καρτέλες).",
                    ):
                        st.session_state['show_results'] = True
                        st.rerun()
            _atlas_inject_post_process_choice_buttons_style()
"""
    pro_html_b = """                    _pp_pad_l, _pp_mid, _pp_pad_r = st.columns([1, 2, 1], vertical_alignment="center")
                    with _pp_mid:
                        _pp_b1, _pp_b2 = st.columns(2, vertical_alignment="center")
                        with _pp_b1:
                            if st.button(
                                "ATLAS Pro\\n(νέο)",
                                type="primary",
                                use_container_width=True,
                                key="open_html_pro_btn",
                                help="Πλήρης HTML αναφορά Pro σε νέα καρτέλα (επιτρέψτε pop-ups).",
                            ):
                                _atlas_open_html_report_now(df, edition="pro", wait_slot=_html_wait_ph)
                        with _pp_b2:
                            if st.button(
                                "ATLAS Pro\\n(παλιότερο)",
                                type="secondary",
                                use_container_width=True,
                                key="show_results_btn",
                                help="Πλήρης ανάλυση στην εφαρμογή (όλες οι καρτέλες).",
                            ):
                                st.session_state['show_results'] = True
                                st.rerun()
                    _atlas_inject_post_process_choice_buttons_style()
"""
    if pro_html_a in body and pro_html_b in body:
        body = body.replace(pro_html_a, new_a, 1)
        body = body.replace(pro_html_b, new_b, 1)
    else:
        # Νεότερη Κυρία (παλιό): κεντραρισμένα δύο κουμπιά (ATLAS Pro / ATLAS Lite)
        for stretch in (True, False):
            kw = _btn_kw(stretch)
            new_ui_a = f"""            _pp_pad_l, _pp_mid, _pp_pad_r = st.columns([1, 2, 1], vertical_alignment="center")
            with _pp_mid:
                _pp_b1, _pp_b2 = st.columns(2, vertical_alignment="center")
                with _pp_b1:
                    if st.button(
                        "ATLAS Pro\\n(παλιότερο)",
                        type="primary",
                        {kw},
                        key="show_results_btn",
                        help="Πλήρης ανάλυση στην εφαρμογή (όλες οι καρτέλες).",
                    ):
                        st.session_state['show_results'] = True
                        st.rerun()
                with _pp_b2:
                    if st.button(
                        "ATLAS Lite\\n(γρήγορο)",
                        type="secondary",
                        {kw},
                        key="open_html_btn",
                        help="Γρήγορη πλήρης HTML αναφορά σε νέα καρτέλα (pop-ups).",
                    ):
                        st.session_state['open_html_report'] = True
            _atlas_inject_post_process_choice_buttons_style()
"""
            new_ui_b = f"""                    _pp_pad_l, _pp_mid, _pp_pad_r = st.columns([1, 2, 1], vertical_alignment="center")
                    with _pp_mid:
                        _pp_b1, _pp_b2 = st.columns(2, vertical_alignment="center")
                        with _pp_b1:
                            if st.button(
                                "ATLAS Pro\\n(παλιότερο)",
                                type="primary",
                                {kw},
                                key="show_results_btn",
                                help="Πλήρης ανάλυση στην εφαρμογή (όλες οι καρτέλες).",
                            ):
                                st.session_state['show_results'] = True
                                st.rerun()
                        with _pp_b2:
                            if st.button(
                                "ATLAS Lite\\n(γρήγορο)",
                                type="secondary",
                                {kw},
                                key="open_html_btn",
                                help="Γρήγορη πλήρης HTML αναφορά σε νέα καρτέλα (pop-ups).",
                            ):
                                st.session_state['open_html_report'] = True
                    _atlas_inject_post_process_choice_buttons_style()
"""
            if new_ui_a in body and new_ui_b in body:
                body = body.replace(new_ui_a, new_a, 1)
                body = body.replace(new_ui_b, new_b, 1)
                break
        else:
            # Παλιότερη Κυρία: τρεις στήλες, «Προβολή Αποτελεσμάτων» / «Γρήγορη Προβολή - HTML»
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
                if old_a in body and old_b in body:
                    body = body.replace(old_a, new_a, 1)
                    body = body.replace(old_b, new_b, 1)
                    break
            else:
                raise SystemExit(
                    "Δεν βρέθηκαν μπλοκ κουμπιών (Pro/HTML, Pro+Lite ή παλιό τριών στηλών)"
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

    body = body.replace(
        """def _atlas_open_html_report_now(
    df: pd.DataFrame,
    *,
    edition: str = "pro",
    wait_slot=None,
) -> None:
    \"\"\"Ένα κλικ: μήνυμα αναμονής ψηλά + παραγωγή HTML (χωρίς deferred session flag).\"\"\"
    if wait_slot is not None:
        with wait_slot.container():
            _atlas_show_html_wait_top()
        _atlas_render_full_html_report_open_tab(df, edition=edition)
        wait_slot.empty()
    else:
        _atlas_show_html_wait_top()
        _atlas_render_full_html_report_open_tab(df, edition=edition)
""",
        """def _atlas_open_html_report_now(
    df: pd.DataFrame,
    *,
    wait_slot=None,
) -> None:
    \"\"\"Ένα κλικ: μήνυμα αναμονής ψηλά + παραγωγή HTML (ATLAS Lite).\"\"\"
    if wait_slot is not None:
        with wait_slot.container():
            _atlas_show_html_wait_top()
        _atlas_render_full_html_report_open_tab(df)
        wait_slot.empty()
    else:
        _atlas_show_html_wait_top()
        _atlas_render_full_html_report_open_tab(df)
""",
        1,
    )

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

"""
html_viewer_builder.py
~~~~~~~~~~~~~~~~~~~~~~
Κοινό module για κατασκευή standalone HTML viewer & print report.
Χρησιμοποιείται από app_lite.py και app_final.py.
"""

import sys
from pathlib import Path as _Path

_root = _Path(__file__).resolve().parent
_kyria = _root / "LOCAL_DEV" / "kyria"
# Πάντα Κυρία πριν από ρίζα — το root app_final.py είναι για deploy και μένει πίσω.
if _kyria.exists():
    _kp = str(_kyria)
    if _kp in sys.path:
        sys.path.remove(_kp)
    sys.path.insert(0, _kp)

import datetime
import base64
import html as html_mod
import io
import json
import re
import unicodedata

import pandas as pd

from app_final import (
    build_print_section_html,
    build_print_table_html,
    build_yearly_print_html,
    build_count_report,
    build_count_c_dataframe,
    build_syntaksi_annual_table,
    build_description_map,
    build_parallel_print_df,
    build_parallel_2017_print_df,
    build_multi_employment_print_df,
    build_summary_grouped_display,
    compute_summary_capped_days_by_group,
    compute_summary_capped_dk,
    compute_complex_file_metrics,
    find_gaps_in_insurance_data,
    find_negative_entries,
    find_zero_duration_intervals,
    generate_audit_report,
    get_print_disclaimer_html,
    should_show_complex_file_warning,
    clean_numeric_value,
    _atlas_write_df_to_excel,
    apply_negative_time_sign,
    insurance_kind_classify_count,
    format_number_greek,
    format_currency,
    APODOXES_DESCRIPTIONS,
    compute_parallel_summary_metrics,
    compute_parallel_2017_summary_metrics,
    compute_multi_employment_summary_metrics,
    _compute_apd_yearly_for_syntaksi_packages,
    _syntaksi_oga_tekmark_rate_decimal,
    df_has_tsmede_misthoti_insurance,
    _load_dtk_table_json,
    koinwnikoi_table,
    SYN_TEKMARK_RATE_LABELS,
    SYN_TEKMARK_RATE_DEFAULT,
    SYN_TEKMARK_OGA_LABEL,
    _parallel_month_groups_until_2016,
    _parallel_until_2016_month_match,
    _is_tsay_misthoti_parallel_row,
    _is_tsay_non_misthoti_parallel_row,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def _load_sheetjs_source() -> str:
    """Διαβάζει τη vendored SheetJS (xlsx.full.min.js) για ενσωμάτωση offline."""
    for cand in (_root / "vendor" / "xlsx.full.min.js",):
        try:
            if cand.exists():
                txt = cand.read_text(encoding="utf-8")
                # Ασφαλές embed μέσα σε <script> ... </script>
                return txt.replace("</script>", "<\\/script>")
        except Exception:
            continue
    return ""


SHEETJS_JS = _load_sheetjs_source()

EXCLUDED_PACKAGES = {"Α", "Λ", "Υ", "Ο", "Χ", "026", "899"}
EXCLUDED_PACKAGES_LABEL = ", ".join(sorted(EXCLUDED_PACKAGES))
EXCLUSION_NOTE_HTML = (
    f'<div class="lite-exclusion-note">'
    f'Εξαιρούνται από την καταμέτρηση: {EXCLUDED_PACKAGES_LABEL}'
    f'</div>'
)
COMPLEX_FILE_WARNING_HTML = (
    '<div class="complex-file-warning">'
    '⚠️ Προσοχή: Περίπλοκο αρχείο — Ελέγξτε απαραίτητα το πρωτότυπο ΑΤΛΑΣ.'
    '</div>'
)


def _build_tab_metrics_bar(items: list[tuple[str, str]]) -> str:
    """Μπάρα μετρήσεων (ίδιο στυλ με Σύνολα / Καταμέτρηση)."""
    if not items:
        return ""
    parts = []
    for label, value in items:
        parts.append(
            '<div class="atlas-metric-item">'
            f'<span class="atlas-metric-label">{html_mod.escape(label)}</span>'
            f'<span class="atlas-metric-value">{html_mod.escape(value)}</span>'
            "</div>"
        )
    return f'<div class="tab-metrics-bar atlas-header-split atlas-header-split--metrics-only">{build_atlas_metrics_frame_html("".join(parts))}</div>'


def build_atlas_metrics_frame_html(row_inner_html: str) -> str:
    return f'<div class="atlas-metrics-frame"><div class="atlas-metrics-row">{row_inner_html}</div></div>'


def _build_atlas_header_split_metrics_html(
    info_html: str, metric_cells: list[str]
) -> str:
    frame = build_atlas_metrics_frame_html("".join(metric_cells))
    if not info_html.strip():
        return (
            f'<div class="atlas-header-split atlas-header-split--metrics-only">{frame}</div>'
        )
    return (
        f'<div class="atlas-header-split">'
        f'<div class="atlas-header-info">{info_html}</div>'
        f"{frame}"
        "</div>"
    )


def _atlas_metric_cell_html(
    label: str, value: str, el_id: str = "", *, critical: bool = False
) -> str:
    id_attr = f' id="{html_mod.escape(el_id)}"' if el_id else ""
    val_cls = "atlas-metric-value critical-result" if critical else "atlas-metric-value"
    return (
        '<div class="atlas-metric-item">'
        f'<span class="atlas-metric-label">{html_mod.escape(label)}</span>'
        f'<span class="{val_cls}"{id_attr}>{html_mod.escape(value)}</span>'
        "</div>"
    )


def _build_gaps_metrics_html(gaps_df: pd.DataFrame) -> str:
    if gaps_df is None or gaps_df.empty:
        return ""
    total_days = gaps_df["Ημερολογιακές ημέρες"].sum()
    total_insured_days = gaps_df["Ημέρες Ασφ."].sum() if "Ημέρες Ασφ." in gaps_df.columns else 0
    total_months = gaps_df["Μήνες"].sum() if "Μήνες" in gaps_df.columns else 0
    total_years = gaps_df["Έτη"].sum() if "Έτη" in gaps_df.columns else 0
    info_html = (
        '<div class="atlas-info-box">'
        '<div class="atlas-info-box-title">Εντοπισμένα Κενά Διαστήματα</div>'
        '<div class="atlas-info-box-body">Σύνοψη κενών διαστημάτων και ημερών χωρίς ασφάλιση.</div>'
        "</div>"
    )
    return _build_atlas_header_split_metrics_html(
        info_html,
        [
            _atlas_metric_cell_html("Συνολικά Κενά", format_number_greek(len(gaps_df), decimals=0)),
            _atlas_metric_cell_html(
                "Συνολικές Ημερολογιακές Ημέρες",
                format_number_greek(total_days, decimals=0),
            ),
            _atlas_metric_cell_html(
                "Εκτίμηση Ημερών Ασφάλισης",
                format_number_greek(total_insured_days, decimals=0),
            ),
            _atlas_metric_cell_html(
                "Συνολικοί Μήνες", format_number_greek(total_months, decimals=1)
            ),
            _atlas_metric_cell_html(
                "Συνολικά Έτη", format_number_greek(total_years, decimals=2)
            ),
        ],
    )


def _build_parallel_metrics_html(
    df: pd.DataFrame,
    months_label: str,
    days_label: str,
    *,
    mode: str,
    parallel_df: pd.DataFrame | None = None,
) -> str:
    if mode == "2017":
        months, days = compute_parallel_2017_summary_metrics(df)
        info_html = (
            '<div class="atlas-info-box">'
            '<div class="atlas-info-box-title">Παράλληλη ασφάλιση 2017+</div>'
            '<div class="atlas-info-box-body">Κριτήρια: ΙΚΑ (αποδοχές 01, 16, ή 99) + ΕΦΚΑ μη μισθωτή ή '
            "ΕΦΚΑ μισθωτή + ΕΦΚΑ μη μισθωτή. Εφαρμόζεται όριο 25 ημερών/μήνα.</div>"
            "</div>"
        )
        metric_cells = [
            _atlas_metric_cell_html(months_label, format_number_greek(months, decimals=0)),
            _atlas_metric_cell_html(days_label, format_number_greek(days, decimals=0)),
        ]
    else:
        months, _legacy_days = compute_parallel_summary_metrics(df)
        if parallel_df is not None and not parallel_df.empty:
            days = _compute_parallel_days_from_print_df(parallel_df)
        else:
            days = _legacy_days
        years = days / 300 if days else 0.0
        extra_units = years * 20
        info_html = (
            '<div class="atlas-info-box">'
            '<div class="atlas-info-box-title">Παράλληλη ασφάλιση</div>'
            '<div class="atlas-info-box-body">Κριτήρια: ΙΚΑ (αποδοχές 01, 16, ή 99· έως 2001 και κενός τύπος '
            "αποδοχών) &amp; ΟΑΕΕ Κ, ΙΚΑ &amp; ΤΣΜΕΔΕ ΚΣ/ΠΚΣ, ΟΑΕΕ Κ &amp; ΤΣΜΕΔΕ ΚΣ/ΠΚΣ, ΙΚΑ &amp; ΤΣΑΥ "
            "μισθωτό (ΜΕ), ΙΚΑ &amp; ΤΣΑΥ μη μισθωτό (ΜΕ), ή ΟΓΑ Κ &amp; ΙΚΑ/ΟΑΕΕ (έως 31/12/2016).</div>"
            "</div>"
        )
        metric_cells = [
            _atlas_metric_cell_html(months_label, format_number_greek(months, decimals=0)),
            _atlas_metric_cell_html(days_label, format_number_greek(days, decimals=0)),
            _atlas_metric_cell_html("Έτη Παράλληλης", format_number_greek(years, decimals=2)),
            _atlas_metric_cell_html("Επιπλέον Μονάδες", format_number_greek(extra_units, decimals=2)),
        ]
    return _build_atlas_header_split_metrics_html(info_html, metric_cells)


_PARALLEL_MONTH_ORDER = ['ΙΑΝ', 'ΦΕΒ', 'ΜΑΡ', 'ΑΠΡ', 'ΜΑΙ', 'ΙΟΥΝ', 'ΙΟΥΛ', 'ΑΥΓ', 'ΣΕΠ', 'ΟΚΤ', 'ΝΟΕ', 'ΔΕΚ']
_PARALLEL_MONEY_COLS = ('Μικτές Αποδοχές', 'Συνολικές Εισφορές')


def _parse_gr_int_value(raw) -> int:
    """Διαβάζει μορφοποιημένο ακέραιο ημερών (ελληνικό format π.χ. '1.234') σε int."""
    t = str(raw).strip()
    if not t or t in ('-', 'nan', 'None'):
        return 0
    neg = t.startswith('-')
    digits = re.sub(r'[^\d]', '', t)
    if not digits:
        return 0
    val = int(digits)
    return -val if neg else val


def _parse_gr_money_value(raw) -> float:
    """Διαβάζει μορφοποιημένο ποσό (π.χ. '1.234,56 €') σε float."""
    t = str(raw).strip()
    if not t or t in ('-', 'nan', 'None'):
        return 0.0
    neg = t.startswith('-')
    t = re.sub(r'[^\d.,]', '', t)
    if not t:
        return 0.0
    t = t.replace('.', '').replace(',', '.')
    try:
        val = float(t)
    except ValueError:
        return 0.0
    return -val if neg else val


def _compute_parallel_year_day_totals(parallel_df: pd.DataFrame) -> dict[str, int]:
    """Παράλληλες ημέρες ανά έτος (ίδια λογική με τη γραμμή «Σύνολο» του πίνακα)."""
    if parallel_df is None or parallel_df.empty or 'Έτος' not in parallel_df.columns:
        return {}
    rendered_cols = [c for c in parallel_df.columns if c != 'Έτος']
    month_cols = [c for c in rendered_cols if c in _PARALLEL_MONTH_ORDER]
    if not month_cols:
        return {}
    result: dict[str, int] = {}
    for year, grp in parallel_df.groupby('Έτος'):
        year_parallel = 0
        for c in month_cols:
            month_sum = sum(_parse_gr_int_value(v) for v in grp[c])
            year_parallel += min(max(month_sum - 25, 0), 25)
        result[str(year).strip()] = year_parallel
    return result


def _compute_parallel_days_from_print_df(parallel_df: pd.DataFrame) -> int:
    """Συνολικές παράλληλες ημέρες = άθροισμα ετήσιων γραμμών «Σύνολο»."""
    return sum(_compute_parallel_year_day_totals(parallel_df).values())


def _parallel_total_row_cell_styles(rendered_cols: list[str]) -> dict[str, str]:
    """Ίδια μορφοποίηση γραμμής συνόλου με την Καταμέτρηση (print_style_rows)."""
    label_col = 'Περιγραφή'
    try:
        desc_idx = rendered_cols.index(label_col)
        desc_right_cols = set(rendered_cols[desc_idx:])
    except ValueError:
        desc_right_cols = set()
    month_cols = [c for c in rendered_cols if c in _PARALLEL_MONTH_ORDER]
    total_bold_cols = (
        [label_col, 'Σύνολο'] + month_cols + [c for c in _PARALLEL_MONEY_COLS if c in rendered_cols]
    )
    styles: dict[str, str] = {}
    for col in rendered_cols:
        style = ''
        if col in desc_right_cols:
            style += 'background-color:#f5fafc;color:#000;'
        if col in total_bold_cols:
            style += 'font-weight:700;'
        if col == label_col:
            style += 'white-space:nowrap;'
        if style:
            styles[col] = style
    return styles


def _parallel_total_td(col: str, value: str, styles: dict[str, str]) -> str:
    style = styles.get(col, '')
    if style:
        return f'<td style="{style}">{value}</td>'
    return f'<td>{value}</td>'


def _build_parallel_year_totals_map(parallel_df: pd.DataFrame) -> dict:
    """Γραμμή συνόλων ανά έτος (HTML <tr>) για τον πίνακα Παράλληλης έως 2016.

    Ανά μήνα: αθροίζονται οι ημέρες όλων των εγγραφών και εμφανίζεται το
    ΥΠΕΡΒΑΛΛΟΝ πάνω από 25 (= παράλληλες ημέρες), με ανώτατο όριο 25
    (π.χ. μισθωτή 12 + ελ. επάγγελμα 25 = 37 → 37 − 25 = 12 παράλληλες).
    Το ετήσιο «Σύνολο» = άθροισμα των μηνιαίων παράλληλων ημερών.
    Επιπλέον εμφανίζονται τα ετήσια σύνολα Μικτών Αποδοχών / Συνολικών Εισφορών."""
    if parallel_df is None or parallel_df.empty or 'Έτος' not in parallel_df.columns:
        return {}
    rendered_cols = [c for c in parallel_df.columns if c != 'Έτος']
    month_cols = [c for c in rendered_cols if c in _PARALLEL_MONTH_ORDER]
    money_cols = [c for c in rendered_cols if c in _PARALLEL_MONEY_COLS]
    if not month_cols:
        return {}
    label_col = 'Περιγραφή' if 'Περιγραφή' in rendered_cols else (rendered_cols[0] if rendered_cols else None)
    cell_styles = _parallel_total_row_cell_styles(rendered_cols)

    result: dict = {}
    year_day_totals = _compute_parallel_year_day_totals(parallel_df)
    for year, grp in parallel_df.groupby('Έτος'):
        year_key = str(year).strip()
        month_totals = {}
        for c in month_cols:
            month_sum = sum(_parse_gr_int_value(v) for v in grp[c])
            month_totals[c] = min(max(month_sum - 25, 0), 25)
        grand_total = year_day_totals.get(year_key, sum(month_totals.values()))
        money_totals = {c: sum(_parse_gr_money_value(v) for v in grp[c]) for c in money_cols}

        cells = []
        label_placed = False
        for c in rendered_cols:
            if c == 'Σύνολο':
                val = format_number_greek(grand_total, decimals=0) if grand_total else ''
                cells.append(_parallel_total_td(c, val, cell_styles))
            elif c in month_cols:
                v = month_totals.get(c, 0)
                val = format_number_greek(v, decimals=0) if v else ''
                cells.append(_parallel_total_td(c, val, cell_styles))
            elif c in money_cols:
                v = money_totals.get(c, 0.0)
                val = format_currency(v) if v else ''
                cells.append(_parallel_total_td(c, val, cell_styles))
            elif c == label_col and not label_placed:
                cells.append(_parallel_total_td(c, f'ΣΥΝΟΛΟ {year_key}', cell_styles))
                label_placed = True
            else:
                cells.append(_parallel_total_td(c, '', cell_styles))
        result[year_key] = f'<tr class="total-row" data-is-total="1">{"".join(cells)}</tr>'
    return result


def _inject_parallel_year_totals(par_html: str, parallel_df: pd.DataFrame) -> str:
    """Εισάγει τη γραμμή συνόλων στο τέλος του tbody κάθε ετήσιου section της Παράλληλης."""
    totals_by_year = _build_parallel_year_totals_map(parallel_df)
    if not totals_by_year:
        return par_html
    pattern = re.compile(r"(<div class='year-heading'>)(.*?)(</div>)(.*?)(</tbody>)", re.DOTALL)

    def _repl(m: "re.Match") -> str:
        year = m.group(2).strip()
        extra = totals_by_year.get(year, '')
        return m.group(1) + m.group(2) + m.group(3) + m.group(4) + extra + m.group(5)

    return pattern.sub(_repl, par_html)


def _build_multi_metrics_html(df: pd.DataFrame, description_map: dict | None = None) -> str:
    months = compute_multi_employment_summary_metrics(df, description_map)
    info_html = (
        '<div class="atlas-info-box">'
        '<div class="atlas-info-box-title">Πολλαπλή απασχόληση</div>'
        '<div class="atlas-info-box-body">Κριτήρια: ΙΚΑ (αποδοχές 01, 16, ή 99) με πάνω από έναν '
        "εργοδότη στον ίδιο μήνα.</div>"
        "</div>"
    )
    return _build_atlas_header_split_metrics_html(
        info_html,
        [
            _atlas_metric_cell_html(
                "Μήνες Πολλαπλής",
                format_number_greek(months, decimals=0),
            ),
        ],
    )


def _build_tab_page(
    section_id: str,
    *,
    heading_html: str = "",
    description_html: str = "",
    warning_html: str = "",
    metrics_html: str = "",
    filters_html: str = "",
    body_html: str = "",
    footer_html: str = "",
    scripts_html: str = "",
    extra_section_classes: str = "",
) -> str:
    """Σταθερή δομή καρτέλας html-lite: προειδοποίηση → τίτλος → metrics → φίλτρα → body → footer."""
    top_parts = [
        warning_html,
        heading_html,
        description_html,
        metrics_html,
        filters_html,
    ]
    top_html = "".join(p for p in top_parts if p)
    sec_classes = "print-section atlas-tab-layout"
    if extra_section_classes:
        sec_classes += f" {extra_section_classes}"
    footer_block = (
        f'<div class="atlas-tab-layout-footer" id="{html_mod.escape(section_id)}-footer">{footer_html}</div>'
        if footer_html
        else ""
    )
    return (
        f'<section class="{sec_classes}" id="{html_mod.escape(section_id)}">'
        f'<div class="atlas-tab-layout-top">{top_html}</div>'
        f'<div class="atlas-tab-layout-body" id="{html_mod.escape(section_id)}-body">{body_html}</div>'
        f"{footer_block}"
        f"{scripts_html}"
        f"</section>"
    )


def _html_build_complex_file_modal_sections(
    n_aggregated: int, n_limits_25: int, n_unpaid_months: int, n_negative: int = 0
) -> list[tuple[str, str]]:
    """Ίδια λογική/κείμενα με LOCAL_DEV/kyria/app_final.build_complex_file_warning_modal_sections (συγχρονίστε αν αλλάξει)."""
    sections: list[tuple[str, str]] = []
    na, nl, nu = n_aggregated, n_limits_25, n_unpaid_months
    primary = na > 15 or nl > 15
    if primary:
        if na > 15:
            sections.append(
                (
                    "warning",
                    f"Εμφανίζονται πολλά ενοποιημένα διαστήματα στο ιστορικό ({na} περιπτώσεις): "
                    "δηλαδή γραμμές που καλύπτουν πάνω από έναν ημερολογιακό μήνα για το διάστημα έως το 2001, "
                    "χωρίς να υπολογίζονται οι συνήθεις «αναμενόμενες» περιπτώσεις ΟΑΕΕ ή ΤΣΜΕΔΕ με 2μηνα ή 6μηνα αντίστοιχα. "
                    "Τέτοιοι φάκελοι χρειάζονται έλεγχο-επιβεβαίωση με το πρωτότυπο ΑΤΛΑΣ.",
                )
            )
        if nl > 15:
            sections.append(
                (
                    "warning",
                    f"Εντοπίζονται πολλοί μήνες με το άθροισμα ημερών να ξεπερνά το ανώτατο των 25 ημερών ασφάλισης ανά μήνα "
                    f"(εκτός ΙΚΑ) – {nl} περιπτώσεις. Η ανακεφαλαίωση-οριστικοποίηση της προϋπηρεσίας χρειάζεται λεπτομερή έλεγχο· "
                    "συγκρίνετε με το αρχείο ΑΤΛΑΣ.",
                )
            )
    else:
        over_10_agg = na > 10
        over_30_unpaid = nu > 30
        over_10_limits = nl > 10
        if over_10_agg and over_30_unpaid:
            sections.append(
                (
                    "warning",
                    f"Ταυτόχρονα υπάρχουν αρκετά ενοποιημένα διαστήματα ({na}) και πολλοί μήνες στην καταμέτρηση "
                    f"με ημέρες αλλά χωρίς αναφερόμενη εισφορά ({nu}). Αυτός ο συνδυασμός κάνει τον φάκελο πιο περίπλοκο· "
                    "επαληθεύστε στο πρωτότυπο ΑΤΛΑΣ.",
                )
            )
        if over_10_agg and over_10_limits:
            sections.append(
                (
                    "warning",
                    f"Ταυτόχρονα εμφανίζονται αρκετά ενοποιημένα διαστήματα ({na}) πριν το 2002 αλλά και αρκετές εφαρμογές "
                    f"του ανώτατου ορίου 25 ημερών τον μήνα ({nl}). Συγκρίνετε με το ΑΤΛΑΣ.",
                )
            )
        if over_30_unpaid and over_10_limits:
            sections.append(
                (
                    "warning",
                    f"Συνυπάρχουν πολλοί μήνες με ημέρες αλλά χωρίς εισφορά ({nu}) και αρκετές εφαρμογές του ανώτατου ορίου "
                    f"25 ημερών ({nl}). Απαιτείται επαλήθευση με το πρωτότυπο ΑΤΛΑΣ.",
                )
            )
    if n_negative > 0:
        sections.append(
            (
                "warning",
                f"Εντοπίστηκαν αρνητικές εγγραφές χρόνου ({n_negative} "
                f"{'περίπτωση' if n_negative == 1 else 'περιπτώσεις'}): γραμμές με αρνητικές αποδοχές/εισφορές "
                "που αντιστοιχούν σε διαγραφές ή διορθώσεις ημερών-μηνών-ετών ασφάλισης. "
                "Οι εγγραφές αυτές αφαιρούν χρόνο από τα σύνολα· επαληθεύστε τον υπολογισμό με το πρωτότυπο ΑΤΛΑΣ.",
            )
        )
    if not sections:
        sections.append(
            (
                "warning",
                "Η εφαρμογή έκρινε τον φάκελο περίπλοκο· ελέγξτε το πρωτότυπο ΑΤΛΑΣ.",
            )
        )
    return sections


def _viewer_synopsis_blocks_html(sections: list[tuple[str, str]]) -> str:
    """Σώμα modal (ίδια λογική χρωμάτων με την Κυρία) για το synopsis-modal του viewer."""
    parts: list[str] = []
    for kind, text in sections:
        esc = html_mod.escape(text)
        cls = "atlas-synopsis-warning" if kind == "warning" else "atlas-synopsis-info"
        parts.append(f'<div class="atlas-synopsis-block {cls}">{esc}</div>')
    return "".join(parts)


def _js_single_quoted_literal(s: str) -> str:
    """Κείμενο ως JavaScript string με μονά εισαγωγικά — για onclick=\"...\" χωρίς σπάσιμο από json.dumps."""
    esc = (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\r", "")
        .replace("\n", "\\n")
    )
    return f"'{esc}'"


def _atlas_html_tab_heading_row_info(
    h2_plain: str, modal_title: str, sections: list[tuple[str, str]], store_id: str
) -> str:
    """ℹ αριστερά + τίτλος h2· κρυφό div με HTML για window.openSynopsisModal (ίδιο modal με Σύνοψη)."""
    body = _viewer_synopsis_blocks_html(sections)
    h2_esc = html_mod.escape(h2_plain)
    title_js = _js_single_quoted_literal(modal_title)
    sid_js = _js_single_quoted_literal(store_id)
    aria_title = html_mod.escape(modal_title, quote=True)
    return (
        f'<div class="atlas-tab-title-row">'
        f'<button type="button" class="atlas-tabinfo-btn" aria-label="Πληροφορίες" title="{aria_title}" '
        f"onclick=\"window.openSynopsisModal({title_js}, document.getElementById({sid_js}).innerHTML); return false;\">"
        f"\u2139</button>"
        f"<h2>{h2_esc}</h2></div>"
        f'<div id="{html_mod.escape(store_id)}" class="atlas-tabinfo-body-store" hidden="hidden">{body}</div>'
    )


def _viewer_complex_file_banner_html() -> str:
    """Μπάρα όπως στην Κυρία + «Διαβάστε περισσότερα» → synopsis modal (#atlas-complex-reasons-store)."""
    return (
        '<div class="complex-file-warning complex-file-warning-viewer">'
        "<strong>Προσοχή: Περίπλοκο αρχείο</strong> — Ελέγξτε απαραίτητα το πρωτότυπο ΑΤΛΑΣ. "
        '<button type="button" class="complex-file-readmore-btn" '
        "onclick=\"window.openSynopsisModal('Γιατί χαρακτηρίστηκε περίπλοκο το αρχείο', "
        "document.getElementById('atlas-complex-reasons-store').innerHTML); return false;\">"
        "Διαβάστε περισσότερα</button>"
        "</div>"
    )


def _atlas_tab_header_bar(heading_html: str, warning_html: str = "") -> str:
    """Μία γραμμή: τίτλος αριστερά, προειδοποίηση περίπλοκου αρχείου στο κέντρο (αν υπάρχει)."""
    if not warning_html:
        return heading_html
    return (
        f'<div class="atlas-tab-header-bar">'
        f'<div class="atlas-tab-header-title">{heading_html}</div>'
        f'<div class="atlas-tab-header-warning">{warning_html}</div>'
        f"</div>"
    )


def _inject_complex_warning_into_viewer_tab(content: str, warning_html: str) -> str:
    """Ενσωματώνει την προειδοποίηση στην ίδια γραμμή με την κεφαλίδα (όχι ξεχωριστή γραμμή)."""
    if not warning_html or not content:
        return content

    m = re.search(
        r'(<div class="atlas-tab-layout-top">)\s*'
        r'((?:<div class="atlas-tab-title-row">.*?</div>)|(?:<h2>.*?</h2>))',
        content,
        re.DOTALL,
    )
    if m:
        return (
            content[: m.start()]
            + m.group(1)
            + _atlas_tab_header_bar(m.group(2), warning_html)
            + content[m.end() :]
        )

    m2 = re.search(
        r'(<section class="print-section[^"]*">)\s*(<h2>.*?</h2>)',
        content,
        re.DOTALL,
    )
    if m2:
        return (
            content[: m2.start()]
            + m2.group(1)
            + _atlas_tab_header_bar(m2.group(2), warning_html)
            + content[m2.end() :]
        )
    return content


_SYNOPSIS_LEFT_ORDER = (
    "Παλιός ή νέος ασφαλισμένος",
    "Ασφαλιστικά ταμεία",
)
_SYNOPSIS_LEFT_CHECKS = frozenset(_SYNOPSIS_LEFT_ORDER)

_SYNOPSIS_NO_FINDING_RESULTS = frozenset({
    "",
    "-",
    "Καμία",
    "Όχι",
    "Κανένα",
    "Κανένας",
})


def _synopsis_has_finding(result: str) -> bool:
    """True όταν το εύρημα δηλώνει κάτι εντοπισμένο (πορτοκαλί πλαίσιο)."""
    return str(result).strip() not in _SYNOPSIS_NO_FINDING_RESULTS


def _build_synopsis_audit_row(
    title: str,
    result: str,
    details: str,
    actions: str,
    check_to_tab: dict[str, str],
    available_tab_ids: set[str],
    side: str,
) -> str:
    """Μία γραμμή Σύνοψης: αριστερά τίτλος, δεξιά ανάλυση (2 ή 3 υποστήλες ανά πλευρά)."""
    if side == "left":
        accent_cls = " audit-row--info"
    elif _synopsis_has_finding(result):
        accent_cls = " audit-row--finding"
    else:
        accent_cls = ""
    target_tab = check_to_tab.get(title)
    is_clickable = bool(target_tab and target_tab in available_tab_ids)
    if is_clickable:
        safe_tab = html_mod.escape(target_tab)
        row_attrs = (
            f' class="audit-row audit-row--{side} audit-card audit-card-clickable{accent_cls}"'
            f' data-tab="{safe_tab}"'
            f" onclick=\"showTab('{safe_tab}');return false;\""
            f" onkeydown=\"if(event.key==='Enter'){{showTab('{safe_tab}');return false;}}\""
            f' role="button" tabindex="0"'
        )
    else:
        row_attrs = f' class="audit-row audit-row--{side} audit-card{accent_cls}"'
    action_html = (
        f'<div class="audit-card-actions">{actions}</div>'
        if actions and actions != "-" else ""
    )
    return (
        f"<div{row_attrs}>"
        f'<div class="audit-card-header"><span>{html_mod.escape(title)}</span></div>'
        f'<div class="audit-card-result">{html_mod.escape(result)}</div>'
        f'<div class="audit-card-details">{details}</div>'
        f"{action_html}</div>"
    )


def _build_synopsis_audit_layout(
    audit_df: pd.DataFrame,
    check_to_tab: dict[str, str],
    available_tab_ids: set[str],
) -> str:
    """Διάταξη Σύνοψης: αριστερά 1/3 (παλιός/νέος + ταμεία), δεξιά 2/3 (υπόλοιποι έλεγχοι)."""
    left_by_title: dict[str, str] = {}
    right_items: list[tuple[bool, str]] = []
    for _, row in audit_df.iterrows():
        title = str(row.get("Έλεγχος", ""))
        result = str(row.get("Εύρημα", ""))
        details = str(row.get("Λεπτομέρειες", ""))
        actions = str(row.get("Ενέργειες", ""))
        side = "left" if title in _SYNOPSIS_LEFT_CHECKS else "right"
        row_html = _build_synopsis_audit_row(
            title, result, details, actions, check_to_tab, available_tab_ids, side
        )
        if side == "left":
            left_by_title[title] = row_html
        else:
            right_items.append((_synopsis_has_finding(result), row_html))
    # Δεξιά στήλη: πρώτα έλεγχοι με εύρημα, μετά χωρίς (σταθερή σειρά μέσα σε κάθε ομάδα).
    right_items.sort(key=lambda item: (0 if item[0] else 1,))
    right_rows = [html for _, html in right_items]
    left_rows = [left_by_title[t] for t in _SYNOPSIS_LEFT_ORDER if t in left_by_title]
    left_stack = "".join(left_rows)
    if left_stack:
        left_stack += (
            f'<div class="synopsis-col-disclaimer">{get_print_disclaimer_html()}</div>'
        )
    return (
        '<div class="audit-layout">'
        '<div class="audit-col audit-col-left">'
        f'<div class="audit-stack">{left_stack}</div>'
        "</div>"
        '<div class="audit-col audit-col-right">'
        f'<div class="audit-stack">{"".join(right_rows)}</div>'
        "</div>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_greek_number(s):
    """Μετατροπή ελληνικού αριθμού (π.χ. 7.725 ή 29,5) σε float."""
    if pd.isna(s) or s == "" or str(s).strip() in ("-", ""):
        return 0
    s = str(s).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0


def filter_count_df(df: pd.DataFrame) -> pd.DataFrame:
    """Φιλτράρει τα εξαιρούμενα πακέτα κάλυψης από τον πίνακα καταμέτρησης."""
    if 'Κλάδος/Πακέτο Κάλυψης' in df.columns:
        pkg_series = df['Κλάδος/Πακέτο Κάλυψης'].astype(str).str.strip()
        return df[~pkg_series.isin(EXCLUDED_PACKAGES)].copy()
    return df.copy()


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

def build_timeline_html(source_df):
    """Ιστορικό ασφάλισης ανά Ταμείο – Τύπο Ασφάλισης (οπτικές μπάρες)."""
    if source_df.empty or 'Από' not in source_df.columns or 'Έως' not in source_df.columns:
        return ""

    t = source_df.copy()
    t['_from'] = pd.to_datetime(t['Από'], format='%d/%m/%Y', errors='coerce')
    t['_to'] = pd.to_datetime(t['Έως'], format='%d/%m/%Y', errors='coerce')
    t = t.dropna(subset=['_from', '_to'])
    if t.empty:
        return ""

    duration_columns = ['Έτη', 'Μήνες', 'Ημέρες']
    for col in duration_columns:
        if col not in t.columns:
            t[col] = 0
        t[f'__{col}_n'] = t[col].apply(clean_numeric_value)
    t['__duration_sum'] = t['__Έτη_n'] + t['__Μήνες_n'] + t['__Ημέρες_n']
    if not t.empty:
        t['__duration_sum_group'] = t.groupby(['_from', '_to'])['__duration_sum'].transform('sum')
    else:
        t['__duration_sum_group'] = 0

    t_with_days = t[t['__duration_sum'] > 0].copy()
    zero_duration_t = t[(t['__duration_sum'] == 0) & (t['__duration_sum_group'] == 0)].copy()

    tameio_col = 'Ταμείο' if 'Ταμείο' in t.columns else None
    ins_col = 'Τύπος Ασφάλισης' if 'Τύπος Ασφάλισης' in t.columns else None

    if tameio_col:
        t_with_days['_label'] = t_with_days[tameio_col].astype(str).str.strip()
        if ins_col:
            ins_vals = t_with_days[ins_col].astype(str).str.strip()
            mask = (ins_vals != '') & (ins_vals != 'nan')
            t_with_days.loc[mask, '_label'] = (
                t_with_days.loc[mask, '_label'] + ' — ' + ins_vals[mask]
            )
    else:
        t_with_days['_label'] = 'Ασφάλιση'

    global_min = t['_from'].min()
    global_max = t['_to'].max()
    total_days = (global_max - global_min).days
    if total_days <= 0:
        return ""

    gaps_df = find_gaps_in_insurance_data(source_df)

    fund_colors = [
        '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444',
        '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
    ]

    groups = t_with_days.groupby('_label', sort=False)
    label_order = list(groups.groups.keys())
    color_map = {lbl: fund_colors[i % len(fund_colors)] for i, lbl in enumerate(label_order)}

    rows_html = []
    legend_items = "".join(
        f'<span class="tl-legend-item"><span class="tl-legend-dot" '
        f'style="background:{color_map[lbl]};"></span>{html_mod.escape(lbl)}</span>'
        for lbl in label_order
    )

    for lbl in label_order:
        grp = groups.get_group(lbl)
        color = color_map[lbl]
        bars = []
        for _, r in grp.iterrows():
            left_pct = max(0, (r['_from'] - global_min).days / total_days * 100)
            width_pct = max(0.3, (r['_to'] - r['_from']).days / total_days * 100)
            tooltip = f"{r['Από']} — {r['Έως']}"
            bars.append(
                f'<div class="tl-bar" style="left:{left_pct:.2f}%;width:{width_pct:.2f}%;'
                f'background:{color};" title="{html_mod.escape(tooltip)}"></div>'
            )
        rows_html.append(
            f'<div class="tl-row">'
            f'<div class="tl-label">{html_mod.escape(lbl)}</div>'
            f'<div class="tl-track">{"".join(bars)}</div></div>'
        )

    if not zero_duration_t.empty:
        zero_items = []
        for _, z in zero_duration_t.iterrows():
            left_pct = max(0, (z['_from'] - global_min).days / total_days * 100)
            width_pct = max(0.3, (z['_to'] - z['_from']).days / total_days * 100)
            tooltip = f"Χωρίς ημέρες: {z['Από']} — {z['Έως']}"
            zero_items.append(
                f'<div class="tl-bar tl-zero" style="left:{left_pct:.2f}%;width:{width_pct:.2f}%;" '
                f'title="{html_mod.escape(tooltip)}"></div>'
            )
        if zero_items:
            rows_html.append(
                f'<div class="tl-row"><div class="tl-label tl-label-zero">'
                f'Διαστήματα χωρίς ημέρες</div>'
                f'<div class="tl-track">{"".join(zero_items)}</div></div>'
            )
            legend_items += (
                '<span class="tl-legend-item"><span class="tl-legend-dot tl-legend-zero">'
                '</span>Διαστήματα χωρίς ημέρες</span>'
            )

    if gaps_df is not None and not gaps_df.empty:
        gap_items = []
        gaps_df2 = gaps_df.copy()
        gaps_df2['_gf'] = pd.to_datetime(gaps_df2['Από'], format='%d/%m/%Y', errors='coerce')
        gaps_df2['_gt'] = pd.to_datetime(gaps_df2['Έως'], format='%d/%m/%Y', errors='coerce')
        gaps_df2 = gaps_df2.dropna(subset=['_gf', '_gt'])
        for _, g in gaps_df2.iterrows():
            left_pct = max(0, (g['_gf'] - global_min).days / total_days * 100)
            width_pct = max(0.3, (g['_gt'] - g['_gf']).days / total_days * 100)
            tooltip = f"Κενό: {g['Από']} — {g['Έως']}"
            gap_items.append(
                f'<div class="tl-bar tl-gap" style="left:{left_pct:.2f}%;width:{width_pct:.2f}%;" '
                f'title="{html_mod.escape(tooltip)}"></div>'
            )
        if gap_items:
            rows_html.append(
                f'<div class="tl-row"><div class="tl-label tl-label-gap">Κενά</div>'
                f'<div class="tl-track">{"".join(gap_items)}</div></div>'
            )
            legend_items += (
                '<span class="tl-legend-item"><span class="tl-legend-dot" '
                'style="background:repeating-linear-gradient(45deg,#fca5a5,#fca5a5 2px,'
                '#fecaca 2px,#fecaca 4px);border:1px solid #ef4444;"></span>Κενά</span>'
            )

    year_min = global_min.year
    year_max = global_max.year
    tick_years = list(range(year_min, year_max + 1, max(1, (year_max - year_min) // 12)))
    if tick_years[-1] != year_max:
        tick_years.append(year_max)
    ticks_html = ""
    for yr in tick_years:
        yr_date = pd.Timestamp(year=yr, month=1, day=1)
        pos = max(0, min(100, (yr_date - global_min).days / total_days * 100))
        ticks_html += f'<div class="tl-tick" style="left:{pos:.2f}%;"><span>{yr}</span></div>'

    ref_dates = [(1993, 1, 1), (2002, 1, 1), (2017, 1, 1), (2020, 1, 1)]
    ref_lines_html = ""
    for y, m, d in ref_dates:
        ref_dt = pd.Timestamp(year=y, month=m, day=d)
        if global_min <= ref_dt <= global_max:
            pos_pct = max(0, min(100, (ref_dt - global_min).days / total_days * 100))
            label = ref_dt.strftime("%d/%m/%Y")
            ref_lines_html += (
                f'<div class="tl-ref-line" style="left:{pos_pct:.2f}%;">'
                f'<span class="tl-ref-label">{html_mod.escape(label)}</span>'
                f'<div class="tl-ref-vline"></div></div>'
            )

    period_from = f"{global_min.day}/{global_min.month}/{global_min.year}"
    period_to = f"{global_max.day}/{global_max.month}/{global_max.year}"
    period_str = f"Περίοδος {period_from} έως {period_to}"

    # Δεύτερο χρονολόγιο (πακέτα): στατικό HTML ώστε η συνολική εκτύπωση να το περιλαμβάνει
    # (το JS buildPaketoTimeline τρέχει μόνο στο live viewer).
    _desc_tl = build_description_map(source_df)
    _recs_tl = _totals_raw_records_for_js(source_df)
    paketo_rows_inner = _build_paketo_timeline_rows_html(_recs_tl, _desc_tl)

    return f"""
    <section class="print-section">
      <h2>Ιστορικό Ασφάλισης</h2>
      <p class="print-description">Οπτική απεικόνιση χρονικών περιόδων ασφάλισης ανά Ταμείο.</p>
      <p class="tl-period-range">{html_mod.escape(period_str)}</p>
      <div class="tl-zoom-wrapper">
        <div class="tl-zoom-controls">
          <span class="tl-zoom-label">Εστίαση:</span>
          <button type="button" class="tl-zoom-btn active" data-zoom="1" title="100%">100%</button>
          <button type="button" class="tl-zoom-btn" data-zoom="1.25" title="125%">125%</button>
          <button type="button" class="tl-zoom-btn" data-zoom="1.5" title="150%">150%</button>
          <button type="button" class="tl-zoom-btn" data-zoom="2" title="200%">200%</button>
          <button type="button" class="tl-zoom-btn" data-zoom="2.5" title="250%">250%</button>
        </div>
        <div class="tl-zoom-inner" id="tl-zoom-inner">
          <div class="tl-legend">{legend_items}</div>
          <div class="tl-container">
            <div class="tl-ref-lines" aria-hidden="true">{ref_lines_html}</div>
            {"".join(rows_html)}
            <div class="tl-axis">{ticks_html}</div>
          </div>
        </div>
      </div>
      <div class="tl-paketo-block">
            <h3 class="tl-paketo-title">Χρονολόγιο ανά πακέτο κάλυψης</h3>
            <p class="tl-paketo-sub">Ανάλυση ανά πακέτο κάλυψης, τύπο ασφάλισης και ταμείο.</p>
            <div class="tl-paketo-zoom-scroll">
            <div class="tl-zoom-inner" id="tl-paketo-zoom-inner">
            <div class="tl-container" id="tl-paketo-wrap">
            <div class="tl-ref-lines tl-paketo-ref" aria-hidden="true">{ref_lines_html}</div>
            <div id="tl-paketo-rows">{paketo_rows_inner}</div>
            <div class="tl-axis tl-paketo-axis">{ticks_html}</div>
            </div>
          </div>
        </div>
      </div>
      <script>
      (function() {{
        var inner = document.getElementById('tl-zoom-inner');
        var innerPaketo = document.getElementById('tl-paketo-zoom-inner');
        var wrap = inner && inner.closest('.tl-zoom-wrapper');
        var paketoScroll = innerPaketo && innerPaketo.closest('.tl-paketo-zoom-scroll');
        var btns = inner && wrap && wrap.querySelectorAll('.tl-zoom-btn');
        if (!inner || !btns.length) return;
        function setZoom(level) {{
          inner.style.transform = 'scale(' + level + ')';
          if (innerPaketo) innerPaketo.style.transform = 'scale(' + level + ')';
          var needH = level > 1.001;
          var ox = needH ? 'auto' : 'hidden';
          if (wrap) wrap.style.overflowX = ox;
          if (paketoScroll) paketoScroll.style.overflowX = ox;
          btns.forEach(function(b) {{ b.classList.toggle('active', parseFloat(b.getAttribute('data-zoom')) === level); }});
        }}
        btns.forEach(function(btn) {{
          btn.addEventListener('click', function() {{ setZoom(parseFloat(btn.getAttribute('data-zoom'))); }});
        }});
        setZoom(1);
      }})();
      </script>
    </section>
    """


# CSS για embedding στο Streamlit: το components.html είναι ξεχωριστό iframe χωρίς το VIEWER_STYLES του πλήρους HTML.
TIMELINE_STREAMLIT_EMBED_CSS = """
* { box-sizing: border-box; }
body { margin: 0; padding: 12px 14px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #1e293b; background: #fff; }
.atlas-streamlit-timeline-host { --tl-label-w: min(200px, 36vw); }
.atlas-streamlit-timeline-host .tl-label { width: var(--tl-label-w); max-width: var(--tl-label-w); }
.atlas-streamlit-timeline-host .tl-ref-lines { left: var(--tl-label-w); }
.atlas-streamlit-timeline-host .tl-axis { margin-left: calc(var(--tl-label-w) + 14px); }
.print-section { margin-bottom: 16px; }
.print-section h2 { font-size: 1.2rem; font-weight: 700; color: #0f172a; margin: 0 0 8px 0; padding-bottom: 6px; border-bottom: 1.5px solid #e2e8f0; }
.print-description { font-size: 13px; color: #64748b; margin: 0 0 8px 0; line-height: 1.45; }
.tl-period-range { text-align: center; font-size: 17px; font-weight: 700; color: #1e293b; margin: 0 0 16px 0; letter-spacing: 0.01em; }
.tl-container { position: relative; padding-bottom: 36px; padding-top: 26px; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; }
.tl-row { display: flex; align-items: center; margin-bottom: 8px; min-height: 28px; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; }
.tl-label { font-size: 13px; font-weight: 600; color: #334155; text-align: right; padding-right: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; box-sizing: border-box; }
.tl-label-gap { color: #dc2626; } .tl-label-zero { color: #78716c; }
.tl-track { position: relative; flex: 1 1 0; min-width: 0; height: 24px; background: #f1f5f9; border-radius: 6px; }
.tl-bar { position: absolute; top: 2px; height: 20px; border-radius: 4px; opacity: 0.85; cursor: default; transition: opacity 0.15s; }
.tl-bar:hover { opacity: 1; box-shadow: 0 0 6px rgba(0,0,0,0.25); z-index: 2; }
.tl-gap { background: repeating-linear-gradient(45deg,#fca5a5,#fca5a5 3px,#fecaca 3px,#fecaca 6px) !important; border: 1px solid #ef4444; opacity: 0.7; }
.tl-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 3px,#d6d3d1 3px,#d6d3d1 6px) !important; border: 1px solid #78716c; opacity: 0.85; }
.tl-legend-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 3px,#d6d3d1 3px,#d6d3d1 6px) !important; border: 1px solid #78716c; }
.tl-zoom-wrapper { margin-top: 8px; border: 1px solid #e2e8f0; border-radius: 10px; overflow-x: hidden; overflow-y: auto; max-height: 70vh; min-height: 360px; background: #fafafa; max-width: 100%; box-sizing: border-box; }
.tl-zoom-controls { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }
.tl-zoom-label { font-size: 13px; font-weight: 600; color: #475569; }
.tl-zoom-btn { padding: 6px 12px; font-size: 12px; font-weight: 600; color: #64748b; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer; transition: all 0.15s; }
.tl-zoom-btn:hover { background: #e2e8f0; color: #334155; border-color: #94a3b8; }
.tl-zoom-btn.active { background: #6366f1; color: #fff; border-color: #4f46e5; }
.tl-zoom-inner { display: block; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; transform-origin: top left; transition: transform 0.2s ease; padding: 12px 16px; }
.tl-axis { position: relative; height: 28px; margin-top: 4px; border-top: 1px solid #cbd5e1; }
.tl-tick { position: absolute; top: 4px; font-size: 11px; color: #64748b; transform: translateX(-50%); }
.tl-tick::before { content: ''; position: absolute; top: -6px; left: 50%; width: 1px; height: 6px; background: #cbd5e1; }
.tl-ref-lines { position: absolute; right: 0; top: 0; bottom: 0; pointer-events: none; z-index: 0; }
.tl-ref-line { position: absolute; top: 0; bottom: 0; left: 0; display: flex; flex-direction: column; align-items: center; transform: translateX(-50%); }
.tl-ref-label { font-size: 10px; color: #64748b; white-space: nowrap; margin-bottom: 4px; font-weight: 600; }
.tl-ref-vline { flex: 1; width: 1px; min-height: 0; background: #64748b; opacity: 0.7; }
.tl-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; font-size: 13px; max-width: 100%; }
.tl-legend-item { display: inline-flex; align-items: center; gap: 6px; color: #334155; }
.tl-legend-dot { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.tl-paketo-block { margin-top: 20px; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; background: #fafafa; overflow: visible; max-width: 100%; box-sizing: border-box; }
.tl-paketo-zoom-scroll { overflow-x: hidden; overflow-y: visible; max-width: 100%; margin-top: 4px; box-sizing: border-box; }
.tl-paketo-block .tl-paketo-zoom-scroll .tl-zoom-inner { padding: 0; }
.tl-paketo-block .tl-paketo-title { margin-top: 0; }
.tl-paketo-title { font-size: 1.05rem; font-weight: 700; color: #1e293b; margin: 20px 0 6px; }
.tl-paketo-sub { font-size: 13px; color: #64748b; margin: 0 0 12px; max-width: 920px; line-height: 1.45; }
#tl-paketo-wrap .tl-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#tl-paketo-wrap .tl-label[title] { cursor: help; }
#tl-paketo-wrap .tl-label.tl-label-cell { min-width: 0; display: flex; flex-direction: column; align-items: stretch; justify-content: center; white-space: normal; overflow: visible; box-sizing: border-box; }
#tl-paketo-wrap .tl-label-main { font-family: inherit; font-size: 13px; font-weight: 600; color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; text-align: right; }
#tl-paketo-wrap .tl-label-meta { margin-top: 1px; font-size: 9px; line-height: 1.15; color: #64748b; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; font-weight: 400; text-align: right; box-sizing: border-box; }
#tl-paketo-wrap .tl-bar.has-tl-paketo-tooltip { cursor: help; }
"""


def build_timeline_html_for_streamlit(source_df):
    """Πλήρες mini-HTML με ενσωματωμένο CSS — το iframe του Streamlit δεν κληρονομεί το stylesheet του viewer."""
    inner = build_timeline_html(source_df)
    if not inner:
        return ""
    return (
        '<!DOCTYPE html>\n<html lang="el"><head><meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        "<style>\n" + TIMELINE_STREAMLIT_EMBED_CSS + "\n</style></head><body>"
        '<div class="atlas-streamlit-timeline-host">' + inner + "</div></body></html>"
    )


# Καρτέλα «Προσωπικά Στοιχεία» (φόρμα + σημειώσεις) — ίδιο περιεχόμενο με dev HTML
PERSONAL_TAB_HTML = """
      <section class="print-section">
        <h2>Προσωπικά Στοιχεία</h2>
        <p class="print-description">Στοιχεία ασφαλιζόμενου / αποθηκεύονται με την «Πλήρη Αποθήκευση»</p>
        <div class="personal-section-wrap">
        <form class="personal-form" id="personal-form" onsubmit="return false;">
          <div class="form-columns form-row-full">
            <div class="form-group form-span-2">
              <label class="form-label">Ονοματεπώνυμο <span class="required">*</span></label>
              <input type="text" name="personal_fullname" id="personal_fullname" placeholder="Συμπληρώστε όνομα.">
            </div>
            <div class="form-group">
              <label class="form-label">Ημερομηνία γέννησης <span class="required">*</span></label>
              <div class="form-row">
                <select name="personal_birth_day" id="personal_birth_day" aria-label="Ημέρα"></select>
                <select name="personal_birth_month" id="personal_birth_month" aria-label="Μήνας"></select>
                <select name="personal_birth_year" id="personal_birth_year" aria-label="Έτος"></select>
              </div>
              <span class="form-result" id="personal_age_display" aria-live="polite"></span>
            </div>
          </div>
          <div class="form-columns">
            <div class="form-group">
              <label class="form-label">Φύλο <span class="required">*</span></label>
              <select name="personal_gender" id="personal_gender">
                <option value="">— Επιλέξτε —</option>
                <option value="female">Γυναίκα</option>
                <option value="male">Άνδρας</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Ταμείο (Φορέας ασφάλισης) <span class="required">*</span></label>
              <select name="personal_tameio" id="personal_tameio">
                <option value="">— Επιλέξτε —</option>
                <option value="dimosio">Δημόσιο</option>
                <option value="ika">ΙΚΑ</option>
                <option value="oaee">ΟΑΕΕ</option>
                <option value="ika_oaee">ΙΚΑ &amp; ΟΑΕΕ</option>
                <option value="tsmede">ΤΣΜΕΔΕ</option>
                <option value="oga">ΟΓΑ (χωρίς μεταβατικές)</option>
                <option value="oga_ika">ΟΓΑ &amp; ΙΚΑ</option>
                <option value="ika_oga">ΙΚΑ &amp; ΟΓΑ</option>
                <option value="oga_oaee">ΟΓΑ &amp; ΟΑΕΕ</option>
                <option value="etaa">ΕΤΑΑ</option>
                <option value="tsay">ΤΣΑΥ</option>
                <option value="deko">ΔΕΚΟ</option>
                <option value="nomikon">Νομικών</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">ΑΜΚΑ (προαιρετικό)</label>
              <input type="text" name="personal_amka" id="personal_amka" placeholder="Αριθμός ΑΜΚΑ" maxlength="11">
              <span class="form-hint">Κανόνες GDPR</span>
            </div>
            <div class="form-group">
              <label class="form-label">Έτη διαμονής στην Ελλάδα (μεγ. 40) <span class="required">*</span></label>
              <select name="personal_years_residence" id="personal_years_residence"></select>
              <span class="form-result">Μέγιστο όριο: 40</span>
            </div>
            <div class="form-group">
              <label class="form-label">Ομογενής</label>
              <select name="personal_omogenis" id="personal_omogenis">
                <option value="no">ΟΧΙ</option>
                <option value="yes">ΝΑΙ</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Αναπηρία (%)</label>
              <input type="number" name="personal_disability_pct" id="personal_disability_pct" min="0" max="100" step="1" placeholder="0–100">
              <span class="form-result" id="personal_disability_info" aria-live="polite"></span>
            </div>
            <div class="form-group">
              <label class="form-label">ΑΦΜ (προαιρετικό)</label>
              <input type="text" name="personal_afm" id="personal_afm" placeholder="Αριθμός Φορολογικού Μητρώου" maxlength="9">
            </div>
            <div class="form-group">
              <label class="form-label">Ημερομηνία γέννησης τέκνου</label>
              <div class="form-row">
                <select name="personal_child_birth_day" id="personal_child_birth_day" aria-label="Ημέρα"></select>
                <select name="personal_child_birth_month" id="personal_child_birth_month" aria-label="Μήνας"></select>
                <select name="personal_child_birth_year" id="personal_child_birth_year" aria-label="Έτος"></select>
              </div>
              <span class="form-hint">Για τον έλεγχο πιθανώς ανήλικων τέκνων και αντιστοίχιση σε μεταβατικές διατάξεις.</span>
            </div>
          </div>
        </form>
        <div class="personal-notes">
          <label class="form-label" for="personal_basic_note">Σημειώσεις</label>
          <textarea name="personal_basic_note" id="personal_basic_note" placeholder="Παρατηρήσεις – σημειώσεις μελετητή"></textarea>
        </div>
        </div>
      </section>
""".strip()


# ---------------------------------------------------------------------------
# Totals helpers
# ---------------------------------------------------------------------------

def _precompute_date_keys(raw_df, group_keys, desc_map=None, month_days=25, year_days=300):
    """Υπολογισμός date-key values ανά ομάδα (πακέτο+ταμείο) από εγγραφές."""
    rdf = raw_df.copy()
    pkg_col = 'Κλάδος/Πακέτο Κάλυψης'
    rdf[pkg_col] = rdf[pkg_col].astype(str).str.strip()
    rdf['_apo'] = pd.to_datetime(rdf.get('Από'), format='%d/%m/%Y', errors='coerce')
    rdf['_eos'] = pd.to_datetime(rdf.get('Έως'), format='%d/%m/%Y', errors='coerce')
    rdf = rdf.dropna(subset=['_apo'])

    for col in ['Ημέρες', 'Μήνες', 'Έτη']:
        if col in rdf.columns:
            rdf[col] = rdf[col].apply(lambda x: clean_numeric_value(x) or 0)
    rdf = apply_negative_time_sign(rdf)
    rdf['_d'] = (
        rdf['Ημέρες'].fillna(0)
        + rdf['Μήνες'].fillna(0) * month_days
        + rdf['Έτη'].fillna(0) * year_days
    ).clip(lower=0)

    def _strip_accents(s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', str(s))
            if unicodedata.category(c) != 'Mn'
        )

    desc_map = desc_map or {}
    varea_codes = set()
    for code, desc in desc_map.items():
        if 'ΒΑΡΕ' in _strip_accents(desc).upper():
            varea_codes.add(str(code).strip())
    rdf['_is_varea'] = rdf[pkg_col].isin(varea_codes)

    today = pd.Timestamp.today().normalize()
    cy = today.year
    d2002 = pd.Timestamp('2002-01-01')
    five = pd.Timestamp(f'{cy - 4}-01-01')
    BAREA_DAYS = 6205
    window_end = today
    window_start = today - pd.Timedelta(days=BAREA_DAYS)
    d2014 = pd.Timestamp('2014-12-31')
    d2010 = pd.Timestamp('2010-12-31')
    d2011 = pd.Timestamp('2011-12-31')
    d2012 = pd.Timestamp('2012-12-31')
    max_y = rdf['_eos'].dt.year.max()
    five_last = pd.Timestamp(f'{int(max_y) - 4}-01-01') if pd.notna(max_y) else pd.NaT
    last_end = pd.Timestamp(f'{int(max_y)}-12-31') if pd.notna(max_y) else pd.NaT

    d = rdf['_d']
    rdf['dk1'] = d.where(rdf['_apo'] >= d2002, 0)
    rdf['dk3'] = d.where(rdf['_apo'] >= five, 0)
    rdf['dk4'] = d.where(
        (rdf['_apo'] >= five_last) & (rdf['_eos'] <= last_end), 0
    ) if pd.notna(five_last) else 0
    rdf['dk5'] = d.where(rdf['_eos'] <= d2014, 0)
    period_days = (rdf['_eos'] - rdf['_apo']).dt.days + 1
    overlap_start = rdf['_apo'].clip(lower=window_start)
    overlap_end = rdf['_eos'].clip(upper=window_end)
    overlap_days = ((overlap_end - overlap_start).dt.days + 1).clip(lower=0)
    ratio = (overlap_days / period_days).fillna(0)
    rdf['dk6'] = (rdf['_d'] * ratio).where(rdf['_is_varea'], 0).round(0)
    rdf['dk7a'] = d.where(rdf['_eos'] <= d2010, 0)
    rdf['dk7b'] = d.where(rdf['_eos'] <= d2011, 0)
    rdf['dk7c'] = d.where(rdf['_eos'] <= d2012, 0)

    dk_cols = ['dk1', 'dk3', 'dk4', 'dk5', 'dk6', 'dk7a', 'dk7b', 'dk7c']
    existing_keys = [k for k in group_keys if k in rdf.columns]
    result = rdf.groupby(existing_keys)[dk_cols].sum().reset_index()
    for c in dk_cols:
        result[c] = result[c].round(0).astype(int)
    return result


def _totals_raw_records_for_js(raw_df, month_days=25, year_days=300):
    """Λίστα ωμών εγγραφών για client-side φιλτράρισμα. Περιλαμβάνει g/c για αποδοχές/εισφορές."""
    if raw_df is None or raw_df.empty:
        return []
    pkg_col = 'Κλάδος/Πακέτο Κάλυψης'
    tameio_col = 'Ταμείο'
    typos_col = 'Τύπος Ασφάλισης'
    apodochon_col = next((c for c in raw_df.columns if 'Τύπος Αποδοχών' in c and 'Περιγραφή' not in c), None)
    gross_col = 'Μικτές αποδοχές'
    contrib_col = 'Συνολικές εισφορές'
    if pkg_col not in raw_df.columns:
        return []
    rdf = raw_df.copy()
    rdf[pkg_col] = rdf[pkg_col].astype(str).str.strip()
    rdf['_apo'] = pd.to_datetime(rdf.get('Από'), format='%d/%m/%Y', errors='coerce')
    rdf['_eos'] = pd.to_datetime(rdf.get('Έως'), format='%d/%m/%Y', errors='coerce')
    rdf = rdf.dropna(subset=['_apo'])
    for col in ['Ημέρες', 'Μήνες', 'Έτη']:
        if col in rdf.columns:
            rdf[col] = rdf[col].apply(lambda x: clean_numeric_value(x) or 0)
    rdf = apply_negative_time_sign(rdf)
    # Δεν κλιπάρουμε σε >=0: οι διορθωτικές (αρνητικές) εγγραφές πρέπει να ΑΦΑΙΡΟΥΝ ημέρες
    # ανά πακέτο/μήνα, όπως κάνει η Κυρία (compute_summary_capped_days_by_group),
    # αλλιώς τα Σύνολα στη Lite βγαίνουν μεγαλύτερα.
    rdf['_h'] = (
        rdf['Ημέρες'].fillna(0)
        + rdf['Μήνες'].fillna(0) * month_days
        + rdf['Έτη'].fillna(0) * year_days
    ).round(0).astype(int)

    def _gross(r):
        raw = str(r.get(gross_col, '') or '')
        if 'ΔΡΧ' in raw.upper() or 'DRX' in raw.upper():
            return 0.0
        return float(clean_numeric_value(raw, exclude_drx=True) or 0)

    def _contrib(r):
        raw = str(r.get(contrib_col, '') or '')
        if 'ΔΡΧ' in raw.upper() or 'DRX' in raw.upper():
            return 0.0
        return float(clean_numeric_value(raw, exclude_drx=True) or 0)

    out = []
    for _, row in rdf.iterrows():
        apo_str = row.get('Από')
        eos_str = row.get('Έως')
        if pd.isna(apo_str) or pd.isna(eos_str):
            continue
        rec = {
            'p': str(row[pkg_col]).strip(),
            't': str(row.get(tameio_col, '')).strip() if tameio_col in rdf.columns else '',
            'apo': str(apo_str).strip(),
            'eos': str(eos_str).strip(),
            'h': int(row['_h']),
            'g': _gross(row) if gross_col in rdf.columns else 0,
            'c': _contrib(row) if contrib_col in rdf.columns else 0,
        }
        if typos_col in rdf.columns:
            rec['ty'] = str(row.get(typos_col, '')).strip()
        if apodochon_col:
            rec['et'] = str(row.get(apodochon_col, '')).strip()
        out.append(rec)
    return out


def _parse_date_dd_mm_yyyy(s):
    """Ίδια μορφή με pd() στο totals JS: ημ/μη/εεεε."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    st = str(s).strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", st)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return datetime.date(y, mo, d)
    except ValueError:
        return None


_PAKETO_TL_PALETTE = (
    "#6366f1",
    "#0ea5e9",
    "#14b8a6",
    "#a855f7",
    "#f97316",
    "#ec4899",
    "#84cc16",
    "#eab308",
    "#64748b",
)

_PAKETO_KEY_SEP = "\x01"


def _paketo_row_group_key(rec: dict) -> str:
    p = str(rec.get("p") or "").strip()
    t = str(rec.get("t") or "").strip()
    ty = str(rec.get("ty") or "").strip()
    return p + _PAKETO_KEY_SEP + t + _PAKETO_KEY_SEP + ty


def _sort_paketo_timeline_keys(keys: list) -> list:
    """Ταξινόμηση κλειδιών p\\x01t\\x01ty όπως localeCompare(..., 'el') στο JS."""
    if not keys:
        return []
    try:
        import locale

        old = locale.setlocale(locale.LC_COLLATE)
        for candidate in ("el_GR.UTF-8", "el_GR", "Greek_Greece.1253", "Greek", ""):
            try:
                locale.setlocale(locale.LC_COLLATE, candidate)
                break
            except OSError:
                continue

        def sort_key(k: str):
            parts = (k.split(_PAKETO_KEY_SEP) + ["", "", ""])[:3]
            return tuple(locale.strxfrm(p) for p in parts)

        out = sorted(keys, key=sort_key)
        try:
            locale.setlocale(locale.LC_COLLATE, old)
        except OSError:
            pass
        return out
    except Exception:
        return sorted(keys, key=lambda k: tuple((k.split(_PAKETO_KEY_SEP) + ["", "", ""])[:3]))


def _build_paketo_timeline_rows_html(records, desc_map):
    """Ίδια λογική με buildPaketoTimeline() (VIEWER_JS) για στατικό HTML / συνολική εκτύπωση."""
    if not records:
        return (
            "<p style=\"color:#64748b;font-size:13px;padding:8px 0\">"
            "Δεν υπάρχουν δεδομένα για χρονολόγιο πακέτων.</p>"
        )

    tl_start = None
    tl_end = None
    groups = {}
    for r in records:
        p = str(r.get("p") or "").strip()
        if not p:
            continue
        a = _parse_date_dd_mm_yyyy(r.get("apo"))
        b = _parse_date_dd_mm_yyyy(r.get("eos"))
        if not a or not b:
            continue
        if tl_start is None or a < tl_start:
            tl_start = a
        if tl_end is None or b > tl_end:
            tl_end = b
        k = _paketo_row_group_key(r)
        if k not in groups:
            groups[k] = {
                "p": p,
                "t": str(r.get("t") or "").strip(),
                "ty": str(r.get("ty") or "").strip(),
                "segs": [],
            }
        groups[k]["segs"].append((a, b))

    if not groups:
        return (
            "<p style=\"color:#64748b;font-size:13px;padding:8px 0\">"
            "Δεν υπάρχουν δεδομένα για χρονολόγιο πακέτων.</p>"
        )
    if tl_start is None:
        tl_start = datetime.date(1993, 1, 1)
    if tl_end is None:
        tl_end = datetime.date.today()
    span = (tl_end - tl_start).days
    if span <= 0:
        span = 1

    def pct(d):
        return max(0.0, min(100.0, (d - tl_start).days / span * 100.0))

    def trunc_label(s, max_len):
        t = re.sub(r"\s+", " ", str(s or "").strip())
        if len(t) <= max_len:
            return t
        return t[: max(0, max_len - 1)] + "…"

    dm = desc_map or {}
    sorted_keys = _sort_paketo_timeline_keys(list(groups.keys()))
    parts = []
    for idx, k in enumerate(sorted_keys):
        g = groups[k]
        segs = [(a, b) for a, b in g["segs"] if a and b and a <= b]
        segs.sort(key=lambda x: (x[0], x[1]))
        full_desc = str(dm.get(g["p"]) or "").replace("\r\n", " ").replace("\n", " ").strip()
        main_line = g["p"] + (" – " + trunc_label(full_desc, 26) if full_desc else "")
        meta_html = ""
        if g["t"] or g["ty"]:
            ps = []
            if g["t"]:
                ps.append(g["t"])
            if g["ty"]:
                ps.append(g["ty"])
            full_paren = "(" + ", ".join(ps) + ")"
            short_paren = trunc_label(full_paren, 42)
            meta_html = (
                f'<div class="tl-label-meta" data-tooltip="{html_mod.escape(full_paren, quote=True)}">'
                f"{html_mod.escape(short_paren)}</div>"
            )
        label_html = (
            f'<div class="tl-label tl-label-cell">'
            f'<div class="tl-label-main">{html_mod.escape(main_line)}</div>'
            f"{meta_html}</div>"
        )
        col = _PAKETO_TL_PALETTE[idx % len(_PAKETO_TL_PALETTE)]
        bars = []
        for a, b in segs:
            L = pct(a)
            W = max(0.15, pct(b) - L)
            apo_str = f"{a.day:02d}/{a.month:02d}/{a.year}"
            eos_str = f"{b.day:02d}/{b.month:02d}/{b.year}"
            bar_tip = f"{apo_str} — {eos_str}"
            bars.append(
                f'<div class="tl-bar has-tl-paketo-tooltip" style="left:{L:.2f}%;width:{W:.2f}%;'
                f'background:{col};" data-tooltip="{html_mod.escape(bar_tip, quote=True)}"></div>'
            )
        parts.append(
            f'<div class="tl-row">{label_html}<div class="tl-track">{"".join(bars)}</div></div>'
        )
    return "".join(parts)


def _format_totals_exceeded_block(n_count: int, body_inner_html: str, visible: bool) -> str:
    """Μία γραμμή ειδοποίησης + κουμπί· στο modal μόνο τα αποτελέσματα (χωρίς κείμενο κριτηρίου)."""
    vis = '' if visible else ' style="display:none"'
    full_body = body_inner_html or ''
    return (
        f'<div id="totals-exceeded-wrap" class="totals-exceeded-wrap"{vis} role="region" '
        f'aria-label="Υπέρβαση πλαφόν ημερών">'
        f'<div class="totals-exceeded-compact">'
        f'<span class="totals-exceeded-compact-text"><strong>Υπέρβαση ορίου ημερών ανά μήνα</strong> — '
        f'<span id="totals-exceeded-count">{n_count}</span> μήνες.</span>'
        f'<button type="button" class="totals-exceeded-modal-btn" id="totals-exceeded-open-btn" '
        f'aria-haspopup="dialog" aria-controls="totals-exceeded-modal-overlay">Προβολή λεπτομερειών</button>'
        f'</div></div>'
        f'<div id="totals-exceeded-modal-overlay" class="totals-exceeded-modal-overlay" aria-hidden="true">'
        f'<div class="totals-exceeded-modal-panel" role="dialog" aria-modal="true" '
        f'aria-labelledby="totals-exceeded-modal-title">'
        f'<div class="totals-exceeded-modal-head">'
        f'<h3 id="totals-exceeded-modal-title">Υπέρβαση ορίου ημερών ανά μήνα</h3>'
        f'<button type="button" class="totals-exceeded-modal-close" aria-label="Κλείσιμο">&times;</button>'
        f'</div>'
        f'<div id="totals-exceeded-modal-body" class="totals-exceeded-modal-body">{full_body}</div>'
        f'</div></div>'
    )


def _apodoxes_option_pairs(values):
    """Ζεύγη (κωδικός, ετικέτα) για φίλτρο τύπου αποδοχών με περιγραφή."""
    pairs = []
    for v in values:
        code = str(v).strip()
        if not code:
            continue
        lookup = code
        if len(code) == 1 and code.isdigit():
            lookup = "0" + code
        desc = (APODOXES_DESCRIPTIONS.get(code) or APODOXES_DESCRIPTIONS.get(lookup) or "").strip()
        label = f"{code} – {desc}" if desc else code
        pairs.append((code, label))
    return pairs


def _klados_eisf_pct_map_from_totals(
    display_summary: pd.DataFrame,
    source_df: pd.DataFrame | None = None,
) -> dict[str, str]:
    """Ποσοστό ανά πακέτο — ίδιες τιμές με τη στήλη «Εισφορές / Αποδοχές %» των Σύνολα."""
    pkg_col = 'Κλάδος/Πακέτο Κάλυψης'
    pct_col = 'Εισφορές / Αποδοχές %'
    gross_col = 'Μικτές αποδοχές'
    contrib_col = 'Συνολικές εισφορές'
    if display_summary is None or display_summary.empty or pkg_col not in display_summary.columns:
        return {}

    by_pkg: dict[str, list[str]] = {}
    if pct_col in display_summary.columns:
        for _, row in display_summary.iterrows():
            code = str(row.get(pkg_col, '')).strip()
            pct = str(row.get(pct_col, '')).strip()
            if not code or code.lower() in ('nan', 'none') or not pct:
                continue
            by_pkg.setdefault(code, []).append(pct)

    out: dict[str, str] = {}
    for code, pcts in by_pkg.items():
        if len(pcts) == 1:
            out[code] = pcts[0]

    if source_df is None or source_df.empty or pkg_col not in source_df.columns:
        return out

    missing = [c for c in (gross_col, contrib_col) if c not in source_df.columns]
    if missing:
        return out

    work = source_df.copy()
    work[pkg_col] = work[pkg_col].astype(str).str.strip()
    work = work[work[pkg_col] != '']
    work[gross_col] = work[gross_col].apply(lambda x: clean_numeric_value(x, exclude_drx=True))
    work[contrib_col] = work[contrib_col].apply(lambda x: clean_numeric_value(x, exclude_drx=True))

    for code in by_pkg:
        if code in out:
            continue
        sub = work[work[pkg_col] == code]
        if sub.empty:
            continue
        g_sum = float(sub[gross_col].sum())
        c_sum = float(sub[contrib_col].sum())
        if abs(g_sum) > 1e-12 and abs(c_sum) > 1e-12:
            out[code] = format_number_greek(c_sum / g_sum * 100, decimals=2) + ' %'

    # Πακέτα που υπάρχουν μόνο στην καταμέτρηση (όχι στα Σύνολα)
    for code, grp in work.groupby(pkg_col):
        if code in out:
            continue
        g_sum = float(grp[gross_col].sum())
        c_sum = float(grp[contrib_col].sum())
        if abs(g_sum) > 1e-12 and abs(c_sum) > 1e-12:
            out[str(code).strip()] = format_number_greek(c_sum / g_sum * 100, decimals=2) + ' %'
    return out


def _lite_filter_modal_group(
    name,
    options,
    data_attr,
    checkbox_name=None,
    with_desc=False,
    desc_map=None,
    pct_map=None,
    modal_wide=False,
):
    """Modal-based φίλτρο Lite — checkboxes σε κρυφό store, πλήρες modal στο κλικ."""
    if not options:
        return ""
    desc_map = desc_map or {}
    pct_map = pct_map or {}
    cb_name = checkbox_name if checkbox_name is not None else name
    if options and isinstance(options[0], tuple):
        pairs = list(options)
    else:
        pairs = []
        for v in options:
            if with_desc:
                desc = (desc_map.get(v) or "").strip()
                label = f"{v} – {desc}" if desc else str(v)
            else:
                label = str(v)
            pairs.append((v, label))
    items_parts = []
    for val, label in pairs:
        pct_html = ""
        if pct_map:
            pct_val = pct_map.get(str(val).strip(), "")
            if pct_val:
                pct_html = (
                    f'<span class="lite-filter-opt-pct">{html_mod.escape(pct_val)}</span>'
                )
        cb_cls = "filter-cb has-opt-pct" if pct_map else "filter-cb"
        if pct_map:
            label_html = (
                f'<span class="lite-filter-opt-body">'
                f'<span class="lite-filter-opt-label">{html_mod.escape(label)}</span>'
                f'{pct_html}</span>'
            )
        else:
            label_html = f'<span class="lite-filter-opt-label">{html_mod.escape(label)}</span>'
        items_parts.append(
            f'<label class="{cb_cls}"><input type="checkbox" name="{html_mod.escape(cb_name)}" '
            f'value="{html_mod.escape(str(val))}" data-attr="{html_mod.escape(data_attr)}">'
            f'{label_html}</label>'
        )
    items_html = "".join(items_parts)
    wide_attr = ' data-modal-wide="1"' if modal_wide else ''
    return (
        f'<div class="filter-group filter-modal-group" data-filter-name="{html_mod.escape(name)}" '
        f'data-filter-key="{html_mod.escape(data_attr)}"{wide_attr}>'
        f'<button type="button" class="filter-modal-trigger" aria-haspopup="dialog" '
        f'title="Επιλέξτε {html_mod.escape(name)}">'
        f'<span class="filter-modal-trigger-label">{html_mod.escape(name)}</span>'
        f'<span class="filter-modal-badge" hidden aria-hidden="true"></span>'
        f'</button>'
        f'<div class="filter-selected-label" aria-live="polite"></div>'
        f'<div class="filter-modal-store" hidden aria-hidden="true">'
        f'<div class="filter-options">{items_html}</div>'
        f'</div>'
        f'</div>'
    )


def build_totals_with_filters(display_summary, raw_df=None, desc_map=None,
                               warning_types=None):
    """Ενότητα Σύνολα με JS φίλτρα (Πακέτο, Ταμείο, Τύπος ασφάλισης, Από-Έως)."""
    paketo_col = "Κλάδος/Πακέτο Κάλυψης"
    tameio_col = "Ταμείο"
    typos_col = "Τύπος Ασφάλισης"
    apo_col = "Από"
    eos_col = "Έως"
    hmeres_col = "Συνολικές ημέρες"
    perigrafi_col = "Περιγραφή"

    paketo_vals = sorted(
        display_summary[paketo_col].dropna().astype(str).str.strip().unique().tolist()
    ) if paketo_col in display_summary.columns else []
    tameio_vals = sorted(
        display_summary[tameio_col].dropna().astype(str).str.strip().unique().tolist()
    ) if tameio_col in display_summary.columns else []
    typos_vals = sorted(
        display_summary[typos_col].dropna().astype(str).str.strip().unique().tolist()
    ) if typos_col in display_summary.columns else []
    typos_vals = [v for v in typos_vals if v and v.lower() not in ('nan', 'none', '')]

    _apod_source = raw_df if raw_df is not None and not raw_df.empty else display_summary
    apodochon_col = next((c for c in _apod_source.columns if 'Τύπος Αποδοχών' in c and 'Περιγραφή' not in c), None)
    apodochon_vals = sorted(
        _apod_source[apodochon_col].dropna().astype(str).str.strip().unique().tolist()
    ) if apodochon_col else []
    apodochon_vals = [v for v in apodochon_vals if v and v.lower() not in ('nan', 'none', '')]

    desc_map = desc_map or {}
    paketo_options = []
    for v in paketo_vals:
        desc = (desc_map.get(v) or "").strip()
        label = f"{v} – {desc}" if desc else v
        paketo_options.append((v, label))
    tameio_options = [(v, v) for v in tameio_vals]
    typos_options = [(v, v) for v in typos_vals]
    apodochon_options = _apodoxes_option_pairs(apodochon_vals)

    paketo_filters = _lite_filter_modal_group("Πακέτο", paketo_options, "paketo")
    tameio_filters = _lite_filter_modal_group("Ταμείο", tameio_options, "tameio")
    typos_filters = _lite_filter_modal_group("Τύπος ασφάλισης", typos_options, "typos") if typos_options else ""
    apodochon_filters = _lite_filter_modal_group("Τύπος αποδοχών", apodochon_options, "typosApod") if apodochon_options else ""
    date_filters = (
        '<div class="filter-group">'
        '<input type="text" id="filter-apo" class="filter-date" placeholder="Από (mm/yyyy)" maxlength="10">'
        '</div>'
        '<div class="filter-group">'
        '<input type="text" id="filter-eos" class="filter-date" placeholder="Έως (mm/yyyy)" maxlength="10">'
        '</div>'
    )

    warning_types = warning_types or []
    if warning_types:
        warn_text = ", ".join(warning_types)
        info_msg = (
            f"Προσοχή: υπάρχει πιθανή {warn_text}. "
            "Το άθροισμα ημερών μπορεί να δώσει λάθος αποτελέσματα."
        )
        info_bar_class = "totals-info-bar totals-info-bar-warning"
    else:
        info_msg = "Επιλέξτε πακέτα κάλυψης για αθροιστική προϋπηρεσία."
        info_bar_class = "totals-info-bar"

    info_banner = (
        f'<div class="{info_bar_class} atlas-header-split">'
        f'<div class="atlas-header-info"><div class="totals-info-msg">{html_mod.escape(info_msg)}</div></div>'
        f'{build_atlas_metrics_frame_html("".join([_atlas_metric_cell_html("Εκτίμηση Ημερών Ασφάλισης", "—", "totals-sum-hmeres", critical=True), _atlas_metric_cell_html("Συνολικά Έτη", "—", "totals-sum-eti", critical=True)]))}'
        "</div>"
    )

    required_cols = {'Από', 'Έως'}
    exceeded_lines_html = ""
    n_exceeded_server = 0
    _server_cap_error = ""
    if raw_df is not None and not raw_df.empty and required_cols.issubset(set(raw_df.columns)):
        try:
            cap_group_keys = [paketo_col]
            if tameio_col in raw_df.columns:
                cap_group_keys.append(tameio_col)
            if typos_col in raw_df.columns:
                cap_group_keys.append(typos_col)
            _cap_df = raw_df.copy()
            for _col in ['Ημέρες', 'Μήνες', 'Έτη']:
                if _col in _cap_df.columns:
                    _cap_df[_col] = _cap_df[_col].apply(clean_numeric_value)
            _cap_df = apply_negative_time_sign(_cap_df)
            _cap_result = compute_summary_capped_days_by_group(
                _cap_df, cap_group_keys, month_days=25, year_days=300, ika_month_days=31
            )
            if isinstance(_cap_result, tuple):
                _, exceeded_months = _cap_result
            else:
                exceeded_months = pd.DataFrame()
            if exceeded_months is not None and not exceeded_months.empty:
                month_names = {1: 'Ιαν', 2: 'Φεβ', 3: 'Μαρ', 4: 'Απρ', 5: 'Μαϊ', 6: 'Ιουν', 7: 'Ιουλ', 8: 'Αυγ', 9: 'Σεπ', 10: 'Οκτ', 11: 'Νοε', 12: 'Δεκ'}
                lines = []
                for _, r in exceeded_months.iterrows():
                    m = int(r.get('Μήνας', 0))
                    y = int(r.get('Έτος', 0))
                    m_str = month_names.get(m, str(m))
                    pkg = html_mod.escape(str(r.get('Κλάδος/Πακέτο Κάλυψης', '')))
                    tameio = html_mod.escape(str(r.get('Ταμείο', '')))
                    typos = html_mod.escape(str(r.get('Τύπος Ασφάλισης', '')))
                    lim = int(r.get('Όριο', 0))
                    over = r.get('Υπέρβαση', 0)
                    days_val = int(r.get('Ημέρες', 0))
                    parts = [f"<strong>Πακέτο {pkg}</strong>"]
                    if tameio:
                        parts.append(f"Ταμείο: {tameio}")
                    if typos:
                        parts.append(f"Τύπος: {typos}")
                    parts.append(f"Μήνας <strong>{m_str} {y}</strong>: {days_val} ημέρες (όριο {lim}, υπέρβαση +{over})")
                    lines.append(" | ".join(parts))
                n_exceeded_server = len(lines)
                exceeded_lines_html = "<br><br>".join(lines)
        except Exception as exc:
            _server_cap_error = str(exc)
    if exceeded_lines_html:
        exceeded_warning_div = _format_totals_exceeded_block(
            n_exceeded_server, exceeded_lines_html, True
        )
    else:
        exceeded_warning_div = _format_totals_exceeded_block(0, "", False)
    filters_bar = (
        f'<div class="totals-filters">{paketo_filters}{tameio_filters}{typos_filters}{apodochon_filters}{date_filters}</div>'
    )

    group_keys = [paketo_col]
    if tameio_col in display_summary.columns:
        group_keys.append(tameio_col)
    if typos_col in display_summary.columns:
        group_keys.append(typos_col)
    dk_map = {}
    dk_cols = ['dk1', 'dk3', 'dk4', 'dk5', 'dk6', 'dk7a', 'dk7b', 'dk7c']
    if raw_df is not None and not raw_df.empty:
        try:
            dk_df = compute_summary_capped_dk(
                raw_df, group_keys, month_days=25, year_days=300, ika_month_days=31,
                from_dt=None, to_dt=None, description_map=desc_map
            )
            if not dk_df.empty:
                for _, dkrow in dk_df.iterrows():
                    key = tuple(str(dkrow.get(k, '')).strip() for k in group_keys)
                    dk_map[key] = {c: int(dkrow.get(c, 0)) for c in dk_cols}
        except Exception:
            pass

    headers_html = "".join(
        f"<th>{html_mod.escape(str(h))}</th>" for h in display_summary.columns
    )
    has_typos_col = typos_col in display_summary.columns
    raw_apod_col = next((c for c in (raw_df.columns if raw_df is not None and not raw_df.empty else []) if 'Τύπος Αποδοχών' in c and 'Περιγραφή' not in c), None)
    has_typos_apodochon_col = bool(raw_apod_col) and bool(apodochon_vals)
    rows_parts = []
    for _, row in display_summary.iterrows():
        paketo_val = str(row.get(paketo_col, "")).strip() if paketo_col in row.index else ""
        tameio_val = str(row.get(tameio_col, "")).strip() if tameio_col in row.index else ""
        typos_val = str(row.get(typos_col, "")).strip() if typos_col in row.index else ""
        apodochon_val = str(row.get(apodochon_col, "")).strip() if apodochon_col and apodochon_col in row.index else ""
        apo_val = str(row.get(apo_col, "")).strip() if apo_col in row.index else ""
        eos_val = str(row.get(eos_col, "")).strip() if eos_col in row.index else ""
        hmeres_raw = parse_greek_number(row.get(hmeres_col, 0)) if hmeres_col in row.index else 0
        is_total = any(str(v).strip().startswith("Σύνολο") for v in row.values)
        tr_cls = ' class="total-row"' if is_total else ""
        key = tuple(str(row.get(k, '')).strip() for k in group_keys)
        dk_vals = dk_map.get(key, {})
        dk_attrs = " ".join(f'data-{c}="{dk_vals.get(c, 0)}"' for c in dk_cols)
        data_attrs = (
            f' data-paketo="{html_mod.escape(paketo_val)}"'
            f' data-tameio="{html_mod.escape(tameio_val)}"'
            f' data-apo="{html_mod.escape(apo_val)}"'
            f' data-eos="{html_mod.escape(eos_val)}"'
            f' data-hmeres="{int(hmeres_raw)}" {dk_attrs}'
        )
        if has_typos_col:
            data_attrs += f' data-typos="{html_mod.escape(typos_val)}"'
        tds = "".join(
            f"<td>{'' if pd.isna(v) else html_mod.escape(str(v))}</td>"
            for v in row.values
        )
        rows_parts.append(f"<tr{tr_cls}{data_attrs}>{tds}</tr>")
    table_body = "".join(rows_parts)
    totals_colgroup = _atlas_colgroup_html(display_summary.columns, month_shave=False)
    custom_table = (
        f'<div class="totals-table-scroll" id="totals-tables-wrapper">'
        f'<table class="print-table wrap-cells atlas-weighted-table totals-weighted" id="totals-filter-table">'
        f"{totals_colgroup}"
        f'<thead><tr>{headers_html}</tr></thead>'
        f'<tbody>{table_body}</tbody></table>'
        f"</div>"
    )

    raw_records_js = json.dumps(
        _totals_raw_records_for_js(raw_df)
    ).replace("</script>", "<\\/script>")
    dk_map_js = json.dumps({
        "|".join(str(x) for x in k): v
        for k, v in dk_map.items()
    }).replace("</script>", "<\\/script>")
    desc_map_js = json.dumps(desc_map or {}).replace("</script>", "<\\/script>")

    has_desc_col = perigrafi_col in display_summary.columns
    varea_codes = set()
    for code, desc in (desc_map or {}).items():
        d = ''.join(c for c in unicodedata.normalize('NFD', str(desc or '')) if unicodedata.category(c) != 'Mn')
        if 'ΒΑΡΕ' in d.upper():
            varea_codes.add(str(code).strip())
    varea_js = json.dumps(list(varea_codes)).replace("</script>", "<\\/script>")
    last_insurance_year = None
    if raw_df is not None and not raw_df.empty and "Έως" in raw_df.columns:
        try:
            _eos_ser = pd.to_datetime(raw_df["Έως"], format="%d/%m/%Y", errors="coerce")
            if _eos_ser.notna().any():
                last_insurance_year = int(_eos_ser.dt.year.max())
        except Exception:
            last_insurance_year = None
    calcs_panel = _build_date_key_calcs_panel(last_insurance_year=last_insurance_year)
    js = _build_totals_filter_js(raw_records_js, dk_map_js, desc_map_js,
                                  has_desc_col=has_desc_col,
                                  has_typos_col=has_typos_col,
                                  has_typos_apodochon_col=has_typos_apodochon_col,
                                  varea_codes_js=varea_js)

    return _build_tab_page(
        section_id="totals-section",
        extra_section_classes="atlas-tab-layout--totals-page",
        heading_html=(
            '<h2>Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)</h2>'
        ),
        description_html=(
            '<p class="print-description">Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης και Ταμείο, '
            'με άθροισμα αποδοχών και εισφορών (μόνο εγγραφές σε €). '
            'Στήλη «Εισφορές / Αποδοχές %»: εισφορές÷αποδοχές×100 όταν και τα δύο ποσά είναι μη μηδενικά.</p>'
        ),
        metrics_html=f"{info_banner}{exceeded_warning_div}",
        filters_html=filters_bar,
        body_html=custom_table,
        footer_html=calcs_panel,
        scripts_html=f"<script>{js}</script>",
    )


def _build_date_key_calcs_panel(last_insurance_year=None):
    """Ίδια διατύπωση με την Κυρία για το (4): «Τελευταία 5 έτη από τελευταίο (έτος)»."""
    y4 = "—"
    if last_insurance_year is not None:
        try:
            y4 = str(int(last_insurance_year))
        except (TypeError, ValueError):
            y4 = "—"
    items = [
        ("1", "Ημέρες από 1/1/2002 έως σήμερα"),
        ("2", "Μήνες από 1/1/2002 έως σήμερα (ημέρες / 25)"),
        ("3", "Συνολικές ημέρες τα τελευταία 5 ημερολογιακά έτη από σήμερα"),
        ("5", "Ημέρες έως 31/12/2014"),
        ("6", "Βαρέα τα τελευταία 17 έτη από σήμερα (6205 ημέρες)"),
        ("7a", "Ημέρες έως 31/12/2010"),
        ("7b", "Ημέρες έως 31/12/2011"),
        ("7c", "Ημέρες έως 31/12/2012"),
    ]
    parts = []
    for num, label in items[:3]:
        parts.append(
            f'<div class="date-key-item"><span class="date-key-num">{html_mod.escape(num)}</span>'
            f'<div><div class="date-key-label">{html_mod.escape(label)}</div>'
            f'<div class="date-key-value critical-result" id="calc-{num}">—</div></div></div>'
        )
    parts.append(
        '<div class="date-key-item"><span class="date-key-num">4</span>'
        '<div><div class="date-key-label">Τελευταία 5 έτη από τελευταίο ('
        f'<span id="calc-4-year">{html_mod.escape(y4)}</span>)</div>'
        '<div class="date-key-value critical-result" id="calc-4">—</div></div></div>'
    )
    for num, label in items[3:]:
        parts.append(
            f'<div class="date-key-item"><span class="date-key-num">{html_mod.escape(num)}</span>'
            f'<div><div class="date-key-label">{html_mod.escape(label)}</div>'
            f'<div class="date-key-value critical-result" id="calc-{num}">—</div></div></div>'
        )
    grid = "".join(parts)
    return (
        '<div id="date-key-calcs" class="date-key-panel">'
        '<h3 class="date-key-title">Σημαντικά διαστήματα</h3>'
        '<p class="date-key-desc">Ενημερώνονται αυτόματα με βάση τα επιλεγμένα πακέτα κάλυψης.</p>'
        f'<div class="date-key-grid">{grid}</div></div>'
    )


def _build_totals_filter_js(raw_records_js, dk_map_js, desc_map_js,
                            has_desc_col=True, has_typos_col=False,
                            has_typos_apodochon_col=False, varea_codes_js="[]"):
    """Επιστρέφει το JavaScript κομμάτι για client-side filtering Σύνολα."""
    has_desc_js = "true" if has_desc_col else "false"
    has_typos_js = "true" if has_typos_col else "false"
    has_et_js = "true" if has_typos_apodochon_col else "false"
    return ("""
(function(){
  var RR=""" + raw_records_js + """;
  var DK=""" + dk_map_js + """;
  var DM=""" + desc_map_js + """;
  var VAREA=""" + varea_codes_js + """;
  var HD=""" + has_desc_js + """;
  var HT=""" + has_typos_js + """;
  var HE=""" + has_et_js + """;
  var CAP=25,IKACAP=31,YD=300,ETAAMSGCAP=30;
  var MN={1:'\\u0399\\u03B1\\u03BD',2:'\\u03A6\\u03B5\\u03B2',3:'\\u039C\\u03B1\\u03C1',4:'\\u0391\\u03C0\\u03C1',5:'\\u039C\\u03B1\\u03CA',6:'\\u0399\\u03BF\\u03C5\\u03BD',7:'\\u0399\\u03BF\\u03C5\\u03BB',8:'\\u0391\\u03C5\\u03B3',9:'\\u03A3\\u03B5\\u03C0',10:'\\u039F\\u03BA\\u03C4',11:'\\u039D\\u03BF\\u03B5',12:'\\u0394\\u03B5\\u03BA'};

  function pd(s){if(!s)return null;var t=String(s).trim();var m3=t.match(/^(\\d{1,2})[./](\\d{1,2})[./](\\d{4})$/);if(m3)return new Date(+m3[3],m3[2]-1,+m3[1]);var m2=t.match(/^(\\d{1,2})[./](\\d{4})$/);if(m2)return new Date(+m2[2],m2[1]-1,1);var y=parseInt(t,10);if(!isNaN(y)&&y>=1000&&y<=9999)return new Date(y,0,1);return null;}
  function ymFromDate(d){return d?d.getFullYear()*100+(d.getMonth()+1):0;}
  function ymFromApoEos(s){var d=pd(s);return ymFromDate(d);}
  function fi(n){return n===0?'0':n.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.');}
  function fd(n){var p=n.toFixed(1).split('.');return p[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.')+','+p[1];}
  function fy(n){var p=n.toFixed(2).split('.');return p[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.')+','+p[1];}
  function fc(x){if(x==null||isNaN(x))return'\\u2014';var a=Math.abs(x),f=a.toFixed(2).split('.'),i=f[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.'),s=i+','+f[1]+' \\u20AC';return x<0?'\\u2212'+s:s;}
  function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}

  function monthsOf(s,e){var o=[],c=new Date(s.getFullYear(),s.getMonth(),1),ef=new Date(e.getFullYear(),e.getMonth(),1);while(c<=ef){o.push({y:c.getFullYear(),m:c.getMonth()+1});c=c.getMonth()===11?new Date(c.getFullYear()+1,0,1):new Date(c.getFullYear(),c.getMonth()+1,1);}return o;}

  function isIka(t){var s=String(t||'').toUpperCase();return s.indexOf('IKA')!==-1||s.indexOf('\\u0399\\u039A\\u0391')!==-1;}
  function isEtaa(t){var s=String(t||'').toUpperCase();return s.indexOf('\\u0395\\u03A4\\u0391\\u0391-\\u03A4\\u0391\\u039D')!==-1||s.indexOf('\\u0395\\u03A4\\u0391\\u0391-\\u039A\\u0395\\u0391\\u0394')!==-1||/ETAA-TAN|ETAA-KEAD/i.test(s);}

  /* Cap ανά (p,t,ty) — ίδια λογική με compute_summary_capped_days_by_group */
  function computeCapGroup(recs,tameio,aD,eD){
    var ms={};
    recs.forEach(function(r){
      var s=pd(r.apo),e=pd(r.eos);if(!s||!e)return;
      var ml=monthsOf(s,e);if(!ml.length)return;
      var origLen=ml.length;
      if(aD||eD){
        var aM=aD?new Date(aD.getFullYear(),aD.getMonth(),1):null;
        var eM=eD?new Date(eD.getFullYear(),eD.getMonth(),1):null;
        ml=ml.filter(function(ym){
          var mFirst=new Date(ym.y,ym.m-1,1);
          if(aM&&mFirst<aM)return false;
          if(eM&&mFirst>eM)return false;
          return true;
        });
        if(!ml.length)return;
      }
      var dpm=r.h/origLen;
      ml.forEach(function(ym){var k=ym.y+'-'+ym.m;ms[k]=(ms[k]||0)+dpm;});
    });
    var ika=isIka(tameio),etaa=isEtaa(tameio);
    var cap=ika?IKACAP:CAP;
    var rptThresh=ika?IKACAP:(etaa?ETAAMSGCAP:CAP);
    var total=0,exc=[],monthCapped={};
    for(var k in ms){
      var d=ms[k],capped=Math.min(d,cap);
      monthCapped[k]=capped;
      if(d>rptThresh){var pp=k.split('-');exc.push({y:+pp[0],m:+pp[1],days:d,limit:cap});}
      total+=capped;
    }
    return{h:Math.round(total),exceeded:exc,monthCapped:monthCapped};
  }

  function computeDkFromMonths(monthCapped,varea,globalMaxYForDk4){
    /* globalMaxYForDk4: ίδιο με compute_summary_capped_dk (max έτος σε όλες τις εγγραφές).
       Χωρίς αυτό, κάθε cap-group έπαιρνε δικό του maxY → λάθος dk4 (π.χ. +παράθυρο 1996–2000 για παλιό πακέτο). */
    var today=new Date(),cy=today.getFullYear();
    var d2002=new Date(2002,0,1),dFive=new Date(cy-4,0,1),d2014=new Date(2014,11,31);
    var d2010=new Date(2010,11,31),d2011=new Date(2011,11,31),d2012=new Date(2012,11,31);
    var BAREA=6205,winEnd=new Date(),winStart=new Date(winEnd.getTime()-BAREA*86400000);
    var maxYLocal=0;
    for(var k in monthCapped){var pp=k.split('-');if(+pp[0]>maxYLocal)maxYLocal=+pp[0];}
    var maxYForDk4=(globalMaxYForDk4!=null&&globalMaxYForDk4>0)?globalMaxYForDk4:maxYLocal;
    var fiveLast=maxYForDk4>=4?new Date(maxYForDk4-4,0,1):null,lastEnd=maxYForDk4>=4?new Date(maxYForDk4,11,31):null;
    var dk1=0,dk3=0,dk4=0,dk5=0,dk6=0,dk7a=0,dk7b=0,dk7c=0;
    for(var k in monthCapped){
      var v=monthCapped[k],pp=k.split('-'),y=+pp[0],m=+pp[1];
      var mStart=new Date(y,m-1,1),mEnd=new Date(y,m,0);
      if(mStart>=d2002)dk1+=v;
      if(mStart>=dFive)dk3+=v;
      if(fiveLast&&lastEnd&&mStart>=fiveLast&&mEnd<=lastEnd)dk4+=v;
      if(mEnd<=d2014)dk5+=v;
      if(varea&&mEnd>=winStart&&mStart<=winEnd)dk6+=v;
      if(mEnd<=d2010)dk7a+=v;
      if(mEnd<=d2011)dk7b+=v;
      if(mEnd<=d2012)dk7c+=v;
    }
    return{dk1:Math.round(dk1),dk3:Math.round(dk3),dk4:Math.round(dk4),dk5:Math.round(dk5),dk6:Math.round(dk6),dk7a:Math.round(dk7a),dk7b:Math.round(dk7b),dk7c:Math.round(dk7c)};
  }

  function liteCollectChecked(sec,key){
    var out=[],seen={};
    function add(cb){
      if(!cb||cb.type!=='checkbox'||!cb.checked)return;
      if((cb.getAttribute('data-attr')||'')!==key)return;
      if(seen[cb.value])return;
      seen[cb.value]=1;out.push(cb.value);
    }
    if(sec)sec.querySelectorAll('.filter-modal-group[data-filter-key="'+key+'"] input[type="checkbox"]').forEach(add);
    var m=document.getElementById('lite-filter-modal-options-mount');
    if(m)m.querySelectorAll('input[type="checkbox"]').forEach(add);
    return out;
  }
  function liteUncheckAllInSection(sec){
    if(!sec)return;
    sec.querySelectorAll('input[type="checkbox"]').forEach(function(cb){cb.checked=false;});
    var m=document.getElementById('lite-filter-modal-options-mount');
    if(m)m.querySelectorAll('input[type="checkbox"]').forEach(function(cb){cb.checked=false;});
  }

  function apply(){
    var sec=document.getElementById('totals-section');if(!sec)return;
    var pC=liteCollectChecked(sec,'paketo');
    var tC=liteCollectChecked(sec,'tameio');
    var tyC=liteCollectChecked(sec,'typos');
    var etC=liteCollectChecked(sec,'typosApod');

    var sel={paketo:pC,tameio:tC,typos:tyC,typosApod:etC};
    sec.querySelectorAll('.totals-filters .filter-modal-group').forEach(function(dd){
      var key=dd.getAttribute('data-filter-key');if(!key)return;
      var vals=sel[key]||[];
      var lb=dd.querySelector('.filter-selected-label');
      var badge=dd.querySelector('.filter-modal-badge');
      if(badge){
        if(vals.length){badge.textContent=vals.length;badge.hidden=false;dd.classList.add('has-selection');}
        else{badge.hidden=true;badge.textContent='';dd.classList.remove('has-selection');}
      }
      if(lb){
        if(vals.length){
          var esc=function(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;};
          var escA=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');};
          lb.innerHTML=vals.map(function(v){return '<button type="button" class="filter-selected-chip" data-value="'+escA(v)+'" data-filter-key="'+escA(key)+'" title="Αφαίρεση">'+esc(v)+'</button>';}).join('');
        }else lb.textContent='';
      }
    });

    var aV=(document.getElementById('filter-apo')||{value:''}).value.trim();
    var eV=(document.getElementById('filter-eos')||{value:''}).value.trim();
    var aD=aV?pd(aV):null,eD=eV?pd(eV):null;
    var totalH=0,allExc=[],dk4LabelYear=0;

    if(Array.isArray(RR)&&RR.length>0){
      /* Φιλτράρισμα raw records */
      var filt=RR.filter(function(r){
        if(pC.length&&pC.indexOf(r.p)===-1)return false;
        if(tC.length&&tC.indexOf(r.t)===-1)return false;
        if(HT&&tyC.length&&(r.ty===undefined||tyC.indexOf(r.ty)===-1))return false;
        if(HE&&etC.length&&(r.et===undefined||etC.indexOf(r.et)===-1))return false;
        var rA=pd(r.apo),rE=pd(r.eos);if(!rA||!rE)return false;
        var rYm0=ymFromDate(rA),rYm1=ymFromDate(rE);
        var fYm=ymFromDate(aD),tYm=ymFromDate(eD);
        if(fYm&&rYm1<fYm)return false;if(tYm&&rYm0>tYm)return false;
        return true;
      });

      var globalMaxY=0;
      filt.forEach(function(r){
        var e=pd(r.eos);if(e){var yy=e.getFullYear();if(yy>globalMaxY)globalMaxY=yy;}
      });
      dk4LabelYear=globalMaxY;

      /* Βήμα 1: Cap ανά (p, t, ty) — χωρίς et */
      var capGroups={};
      filt.forEach(function(r){
        var ck=r.p+'|'+r.t;if(HT)ck+='|'+(r.ty||'');
        if(!capGroups[ck])capGroups[ck]={t:r.t,recs:[]};
        capGroups[ck].recs.push(r);
      });
      var capMap={},dkMapFromCap={};
      for(var ck in capGroups){
        var cg=capGroups[ck];
        var res=computeCapGroup(cg.recs,cg.t,aD,eD);
        capMap[ck]=res.h;
        var pkg=(ck.split('|')[0]||'').trim();
        var isVarea=Array.isArray(VAREA)&&VAREA.indexOf(pkg)!==-1;
        dkMapFromCap[ck]=computeDkFromMonths(res.monthCapped||{},isVarea,globalMaxY);
        res.exceeded.forEach(function(e){
          var pp=ck.split('|');
          allExc.push({p:pp[0],t:pp[1],ty:pp[2]||'',y:e.y,m:e.m,days:e.days,limit:e.limit});
        });
      }

      /* Βήμα 2: Display groups — ανά (p,t,ty) ή (p,t,ty,et) ανάλογα φίλτρο */
      var showEtDetail=HE&&etC.length>0;
      var dispGroups={};
      filt.forEach(function(r){
        var dk=r.p+'|'+r.t;if(HT)dk+='|'+(r.ty||'');if(showEtDetail)dk+='|'+(r.et||'');
        if(!dispGroups[dk])dispGroups[dk]={p:r.p,t:r.t,ty:HT?(r.ty||''):undefined,et:showEtDetail?(r.et||''):undefined,apo:r.apo,eos:r.eos,gross:0,contrib:0,n:0};
        var g=dispGroups[dk];
        g.gross+=(r.g!=null&&!isNaN(r.g))?r.g:0;
        g.contrib+=(r.c!=null&&!isNaN(r.c))?r.c:0;
        g.n+=1;
        if(r.apo&&(!g.apo||pd(r.apo)<pd(g.apo)))g.apo=r.apo;
        if(r.eos&&(!g.eos||pd(r.eos)>pd(g.eos)))g.eos=r.eos;
      });

      /* Βήμα 3: Αντιστοίχιση cap → display group */
      var gL=Object.keys(dispGroups).map(function(dk){return dispGroups[dk];});
      gL.forEach(function(g){
        var ck=g.p+'|'+g.t;if(HT)ck+='|'+(g.ty||'');
        g.h=capMap[ck]||0;
      });

      /* Βήμα 4: Σύνολο ημερών = unique cap groups (χωρίς διπλομέτρημα) */
      for(var ck2 in capMap)totalH+=capMap[ck2];

      /* Βήμα 5: Rebuild πίνακα */
      var tbody=document.querySelector('#totals-filter-table tbody'),thead=document.querySelector('#totals-filter-table thead');
      if(tbody&&thead){
        var colCount=thead.querySelectorAll('th').length;
        var seenCap={};
        var nR=gL.map(function(g){
          var y=Math.floor(g.h/YD),rem=g.h%YD,m=Math.floor(rem/25),d=Math.round(rem%25);
          var desc=(DM&&DM[g.p])?esc(DM[g.p]):'';
          var ck=g.p+'|'+g.t;if(HT)ck+='|'+(g.ty||'');
          var dkv=(dkMapFromCap&&dkMapFromCap[ck])||(DK&&DK[ck])||{};
          var dkA=['dk1','dk3','dk4','dk5','dk6','dk7a','dk7b','dk7c'].map(function(k){
            var v=seenCap[ck]?0:(dkv[k]||0);return'data-'+k+'="'+v+'"';
          }).join(' ');
          seenCap[ck]=true;

          var cells=[g.p,g.t];
          if(HT)cells.push(g.ty||'');
          if(showEtDetail)cells.push(g.et||'');
          if(HD)cells.push(desc);
          var pctCell='';
          var gV=(g.gross!=null&&!isNaN(g.gross))?g.gross:0;
          var cV=(g.contrib!=null&&!isNaN(g.contrib))?g.contrib:0;
          if(Math.abs(gV)>1e-12&&Math.abs(cV)>1e-12)pctCell=fy(cV/gV*100)+' %';
          cells=cells.concat([g.apo,g.eos,fi(g.h),fd(y),fd(m),fd(d),fc(g.gross),fc(g.contrib),pctCell,fi(g.n||0)]);
          while(cells.length<colCount)cells.push('');

          var tyA=HT?' data-typos="'+esc(g.ty||'')+'"':'';
          var etA=showEtDetail?' data-typos-apodochon="'+esc(g.et||'')+'"':'';
          return'<tr data-paketo="'+esc(g.p)+'" data-tameio="'+esc(g.t)+'"'+tyA+etA+' data-apo="'+esc(g.apo)+'" data-eos="'+esc(g.eos)+'" data-hmeres="'+g.h+'" '+dkA+'>'+cells.slice(0,colCount).map(function(c){return'<td>'+c+'</td>';}).join('')+'</tr>';
        });
        tbody.innerHTML=nR.join('');
      }

      /* Βήμα 6: Υπέρβαση πλαφόν — μία γραμμή + πλήρες κείμενο σε modal */
      var wrap=document.getElementById('totals-exceeded-wrap');
      var bodyEl=document.getElementById('totals-exceeded-modal-body');
      var cntEl=document.getElementById('totals-exceeded-count');
      if(wrap&&bodyEl){
        if(allExc.length>0){
          wrap.style.display='';
          if(cntEl)cntEl.textContent=String(allExc.length);
          var exL=allExc.map(function(e){
            var ms=MN[e.m]||e.m,ov=(e.days-e.limit).toFixed(1);
            var pp=['\\u03A0\\u03B1\\u03BA\\u03AD\\u03C4\\u03BF '+e.p];
            if(e.t)pp.push('\\u03A4\\u03B1\\u03BC\\u03B5\\u03AF\\u03BF: '+e.t);
            if(e.ty)pp.push('\\u03A4\\u03CD\\u03C0\\u03BF\\u03C2: '+e.ty);
            pp.push('\\u039C\\u03AE\\u03BD\\u03B1\\u03C2 '+ms+' '+e.y+': '+Math.round(e.days)+' \\u03B7\\u03BC\\u03AD\\u03C1\\u03B5\\u03C2 (\\u03CC\\u03C1\\u03B9\\u03BF '+e.limit+', \\u03C5\\u03C0\\u03AD\\u03C1\\u03B2\\u03B1\\u03C3\\u03B7 +'+ov+')');
            return esc(pp.join(' | '));
          });
          bodyEl.innerHTML=exL.join('<br>');
        }else{
          wrap.style.display='none';
          bodyEl.innerHTML='';
        }
      }
    }else{
      /* Fallback: φιλτράρισμα pre-rendered γραμμών */
      var rows=document.querySelectorAll('#totals-filter-table tbody tr');
      rows.forEach(function(tr){
        var pk=tr.getAttribute('data-paketo')||'',tm=tr.getAttribute('data-tameio')||'',ty=tr.getAttribute('data-typos')||'',ea=tr.getAttribute('data-typos-apodochon')||'';
        var aS=tr.getAttribute('data-apo')||'',eS=tr.getAttribute('data-eos')||'';
        var ok=true;
        if(pC.length&&pC.indexOf(pk.trim())===-1)ok=false;
        if(tC.length&&tC.indexOf(tm.trim())===-1)ok=false;
        if(HT&&tyC.length&&tyC.indexOf(ty.trim())===-1)ok=false;
        if(HE&&etC.length&&etC.indexOf(ea.trim())===-1)ok=false;
        var rA=pd(aS.trim()),rE=pd(eS.trim());
        if(aD&&(!rE||rE<aD))ok=false;if(eD&&(!rA||rA>eD))ok=false;
        tr.style.display=ok?'':'none';
        if(ok){
          totalH+=parseInt(tr.getAttribute('data-hmeres')||'0',10);
          var rE2=pd(eS.trim());
          if(rE2){var yy2=rE2.getFullYear();if(yy2>dk4LabelYear)dk4LabelYear=yy2;}
        }
      });
    }

    /* Metrics — μόνο αν έχει επιλεγεί πακέτο */
    var hasSel=pC.length>0;
    var elH=document.getElementById('totals-sum-hmeres'),elE=document.getElementById('totals-sum-eti');
    if(elH)elH.textContent=hasSel&&totalH>0?fi(totalH):'\\u2014';
    if(elE)elE.textContent=hasSel&&totalH>0?fy(totalH/YD):'\\u2014';

    /* Σημαντικά Διαστήματα (dk) — μόνο αν έχει επιλεγεί πακέτο */
    var dkK=['dk1','dk3','dk4','dk5','dk6','dk7a','dk7b','dk7c'],dkS={};
    dkK.forEach(function(k){dkS[k]=0;});
    if(hasSel){
      var allRows=document.querySelectorAll('#totals-filter-table tbody tr');
      allRows.forEach(function(tr){
        if(tr.style.display==='none')return;
        dkK.forEach(function(k){dkS[k]+=parseInt(tr.getAttribute('data-'+k)||'0',10);});
      });
    }
    function sdc(id,v){var el=document.getElementById(id);if(el)el.textContent=hasSel&&v>0?fi(v):'\\u2014';}
    sdc('calc-1',dkS.dk1);
    var el2=document.getElementById('calc-2');if(el2)el2.textContent=hasSel&&dkS.dk1>0?fd(dkS.dk1/25):'\\u2014';
    sdc('calc-3',dkS.dk3);sdc('calc-4',dkS.dk4);sdc('calc-5',dkS.dk5);sdc('calc-6',dkS.dk6);
    sdc('calc-7a',dkS.dk7a);sdc('calc-7b',dkS.dk7b);sdc('calc-7c',dkS.dk7c);
    var elY4=document.getElementById('calc-4-year');
    if(elY4)elY4.textContent=(hasSel&&dk4LabelYear>0)?String(dk4LabelYear):'\\u2014';
  }

  /* Bind events */
  var sec=document.getElementById('totals-section');
  if(sec){
    window._liteFilterModalApply=window._liteFilterModalApply||{};window._liteFilterModalApply['totals-section']=apply;
    sec.querySelectorAll('.totals-filters input.filter-date').forEach(function(inp){inp.addEventListener('input',apply);inp.addEventListener('change',apply);});
    var resetBtn=document.createElement('button');resetBtn.type='button';resetBtn.className='filter-reset-btn';resetBtn.textContent='\u21bb';resetBtn.title='Επαναφορά φίλτρων';resetBtn.setAttribute('aria-label','Επαναφορά φίλτρων');resetBtn.addEventListener('click',function(){liteUncheckAllInSection(sec);var apo=document.getElementById('filter-apo');var eos=document.getElementById('filter-eos');if(apo)apo.value='';if(eos)eos.value='';apply();});sec.querySelector('.totals-filters').appendChild(resetBtn);
  }
  (function(){
    var ov=document.getElementById('totals-exceeded-modal-overlay');
    var ob=document.getElementById('totals-exceeded-open-btn');
    if(!ov||!ob)return;
    var cb=ov.querySelector('.totals-exceeded-modal-close');
    function opn(){ov.classList.add('is-open');ov.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';}
    function cls(){ov.classList.remove('is-open');ov.setAttribute('aria-hidden','true');document.body.style.overflow='';}
    ob.addEventListener('click',function(e){e.preventDefault();opn();});
    if(cb)cb.addEventListener('click',cls);
    ov.addEventListener('click',function(e){if(e.target===ov)cls();});
    document.addEventListener('keydown',function(e){if(e.key==='Escape'&&ov.classList.contains('is-open'))cls();});
  })();
  apply();
  window._atlasRR=RR;window._atlasDM=DM;window._atlasPd=pd;
})();
""")


def _compute_count_kind_summary_from_c_df(c_df: pd.DataFrame, year_days: float = 300.0) -> tuple[float, float, float, float]:
    """Άθροισμα ημερών μισθωτή / μη μισθωτή (πλαφόν ανά μήνα, ίδια λογική με Κυρία) και ισοδύναμα έτη."""
    if c_df is None or getattr(c_df, "empty", True):
        return 0.0, 0.0, 0.0, 0.0

    def _cap_days(tameio_val):
        t = str(tameio_val).upper()
        return 31.0 if ("ΙΚΑ" in t or "IKA" in t) else 25.0

    def _year_kind_days(year: int, kind_code: str | None) -> float:
        sub = c_df[c_df["ΕΤΟΣ"] == year].copy()
        if sub.empty:
            return 0.0
        sub["_k"] = sub["ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ"].apply(insurance_kind_classify_count)
        if kind_code is not None:
            sub = sub[sub["_k"] == kind_code]
        if sub.empty:
            return 0.0
        g = sub.groupby(["ΤΑΜΕΙΟ", "Μήνας_Num"], as_index=False)["Ημέρες"].sum()
        g["_cap"] = g["ΤΑΜΕΙΟ"].apply(_cap_days)
        g["_capped"] = g.apply(
            lambda r: min(float(r["Ημέρες"]), float(r["_cap"])),
            axis=1,
        )
        return float(g.groupby("Μήνας_Num")["_capped"].sum().sum())

    try:
        years = sorted({int(y) for y in c_df["ΕΤΟΣ"].dropna().unique()})
    except Exception:
        years = []
    sm = sum(_year_kind_days(y, "ΜΙΣΘΩΤΗ") for y in years)
    snm = sum(_year_kind_days(y, "ΜΗ ΜΙΣΘΩΤΗ") for y in years)
    sall = sm + snm
    syears = (sall / year_days) if year_days else 0.0
    return sm, snm, sall, syears


def _count_kind_metrics_by_klados_map(
    count_df: pd.DataFrame, desc_map: dict, year_days: float = 300.0
) -> dict[str, list[float]]:
    """Ένα entry ανά κωδικό ΚΛΑΔΟΣ/ΠΑΚΕΤΟ: [μισθωτή, μη μισθωτή, άθροισμα, έτη] για δυναμικά σύνολα στο HTML."""
    c_df = build_count_c_dataframe(count_df, desc_map)
    if c_df is None or getattr(c_df, "empty", True):
        return {}
    col = "ΚΛΑΔΟΣ/ΠΑΚΕΤΟ"
    if col not in c_df.columns:
        return {}
    out: dict[str, list[float]] = {}
    for code in c_df[col].dropna().unique():
        code_s = str(code).strip()
        sub = c_df[c_df[col].astype(str).str.strip() == code_s]
        sm, snm, sall, sy = _compute_count_kind_summary_from_c_df(sub, year_days=year_days)
        out[code_s] = [float(sm), float(snm), float(sall), float(sy)]
    return out


def _count_filter_modal(
    name, options, data_attr, with_desc=False, desc_map=None,
    pct_map=None, modal_wide=False,
):
    """Modal φίλτρο καταμέτρησης (ίδια δομή με totals)."""
    return _lite_filter_modal_group(
        name, options, data_attr,
        checkbox_name=f"cnt-{data_attr}",
        with_desc=with_desc,
        desc_map=desc_map,
        pct_map=pct_map,
        modal_wide=modal_wide,
    )


_ATLAS_MONTH_COLS = {"ΙΑΝ", "ΦΕΒ", "ΜΑΡ", "ΑΠΡ", "ΜΑΙ", "ΙΟΥΝ", "ΙΟΥΛ", "ΑΥΓ", "ΣΕΠ", "ΟΚΤ", "ΝΟΕ", "ΔΕΚ"}
_ATLAS_MONTH_COL_WT = 1.8


def _atlas_norm_col_name(name) -> str:
    up = str(name).upper().strip()
    return "".join(
        ch for ch in unicodedata.normalize("NFD", up)
        if unicodedata.category(ch) != "Mn"
    )


def _atlas_table_col_weight(name) -> float:
    """Αναλογικά βάρη ανά τύπο στήλης (Καταμέτρηση / Σύνολα / Παράρτημα)."""
    u = _atlas_norm_col_name(name)
    if u in ("A/A", "AA", "Α/Α"):
        return 1.2
    if u == "ΕΤΟΣ":
        return 1.5
    if u == "ΦΟΡΕΑΣ":
        return 1.8
    if u == "ΤΑΜΕΙΟ":
        return 2.6
    if u == "ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ":
        return 3.4
    if u == "ΕΡΓΟΔΟΤΗΣ" or "ΕΡΓΟΔΟΤΗ" in u:
        return 3.0
    if "ΚΛΑΔΟΣ" in u or "ΠΑΚΕΤΟ" in u or "ΚΩΔΙΚΟΣ ΚΛΑΔΩΝ" in u:
        return 2.6
    if u == "ΠΕΡΙΓΡΑΦΗ" or u.startswith("ΠΕΡΙΓΡΑΦΗ"):
        return 5.0
    if "ΑΠΟΔΟΧΩΝ" in u and "ΤΥΠΟΣ" in u:
        return 2.4
    if u == "ΣΥΝΟΛΟ":
        return 1.7
    if u in _ATLAS_MONTH_COLS:
        return _ATLAS_MONTH_COL_WT
    if u in ("ΑΠΟ", "ΕΩΣ"):
        return 2.2
    if "ΣΥΝΟΛΙΚΕΣ ΗΜΕΡΕΣ" in u:
        return 2.4
    if u in ("ΕΤΗ", "ΜΗΝΕΣ", "ΗΜΕΡΕΣ"):
        return 1.8
    if u == "ΑΡΙΘΜΟΣ ΕΓΓΡΑΦΩΝ":
        return 2.2
    if u == "ΑΠΟΔΟΧΕΣ" or "ΜΙΚΤΕΣ" in u:
        return 3.0
    if "ΕΙΣΦΟΡΕΣ" in u and "ΑΠΟΔΟΧΕΣ" in u and "%" in u:
        return 2.2
    if "ΕΙΣΦΟΡΕΣ" in u or u == "ΕΙΣΦΟΡΕΣ":
        return 3.0
    if u == "%" or "ΠΟΣΟΣΤΟ" in u:
        return 1.8
    if u == "ΜΗΝΑΣ":
        return 2.0
    return 2.4


def _atlas_colgroup_html(columns, *, month_shave: bool = True) -> str:
    header_cells = [str(c) for c in columns]
    weights = [_atlas_table_col_weight(h) for h in header_cells]
    if month_shave:
        n_month = sum(1 for h in header_cells if _atlas_norm_col_name(h) in _ATLAS_MONTH_COLS)
        n_other = len(header_cells) - n_month
        if n_month and n_other:
            shave = n_month * (_ATLAS_MONTH_COL_WT - 1.5) / n_other
            weights = [
                w - shave if _atlas_norm_col_name(h) not in _ATLAS_MONTH_COLS else _ATLAS_MONTH_COL_WT
                for h, w in zip(header_cells, weights)
            ]
    total_w = sum(weights) or 1.0
    return "<colgroup>" + "".join(
        f'<col style="width:{round(w / total_w * 100, 3)}%">' for w in weights
    ) + "</colgroup>"


def _build_unified_count_table_html(per_year_html: str) -> str:
    """Μετατρέπει τα ανά-έτος `.year-section` (build_yearly_print_html) σε ΕΝΑΝ πίνακα
    `.count-unified` με μπάντα έτους στην αρχή + κενή γραμμή στο τέλος κάθε έτους.
    Διατηρεί αυτούσια τα κελιά/στυλ/γραμμές συνόλου ώστε φίλτρα/σύνολα να δουλεύουν."""
    if not per_year_html or "year-section" not in per_year_html:
        return per_year_html
    m_thead = re.search(r"<thead>.*?</thead>", per_year_html, re.DOTALL)
    if not m_thead:
        return per_year_html
    thead = m_thead.group(0)
    header_cells = [
        re.sub(r"<[^>]+>", "", h).strip()
        for h in re.findall(r"<th\b[^>]*>(.*?)</th>", thead, re.DOTALL)
    ]
    ncols = len(header_cells) or 1
    colgroup = _atlas_colgroup_html(header_cells, month_shave=True)

    rows_out = []
    for block in per_year_html.split("<div class='year-section'>")[1:]:
        m_year = re.search(r"<div class='year-heading'>(.*?)</div>", block, re.DOTALL)
        year = (m_year.group(1).strip() if m_year else "")
        m_body = re.search(r"<tbody>(.*?)</tbody>", block, re.DOTALL)
        body = m_body.group(1) if m_body else ""
        y_attr = html_mod.escape(year, quote=True)
        rows_out.append(
            f'<tr class="count-year-band" data-is-band="1" data-c-year="{y_attr}">'
            f'<td colspan="{ncols}">{html_mod.escape(year)}</td></tr>'
        )
        rows_out.append(re.sub(r"<tr(?=[ >])", f'<tr data-c-year="{y_attr}"', body))
        rows_out.append(
            f'<tr class="count-year-gap" data-is-sep="1" data-c-year="{y_attr}" aria-hidden="true">'
            f'<td colspan="{ncols}"></td></tr>'
        )
    return (
        '<table class="print-table count-unified">'
        f"{colgroup}{thead}<tbody>{''.join(rows_out)}</tbody></table>"
    )


def _count_unified_to_per_year_html(html: str) -> str:
    """Αντίστροφο του _build_unified_count_table_html: ξαναφτιάχνει τα ανά-έτος `.year-section`
    (ένας πίνακας ανά έτος, όπως ήταν αρχικά η εκτύπωση) από τον ενιαίο `.count-unified`.
    Χρησιμοποιείται ΜΟΝΟ για την εκτύπωση — η οθόνη κρατά τον ενιαίο πίνακα."""
    if not html or "count-unified" not in html:
        return html
    m = re.search(r'<table class="print-table count-unified">(.*?)</table>', html, re.DOTALL)
    if not m:
        return html
    inner = m.group(1)
    m_thead = re.search(r"<thead>.*?</thead>", inner, re.DOTALL)
    thead = m_thead.group(0) if m_thead else ""
    m_tbody = re.search(r"<tbody>(.*?)</tbody>", inner, re.DOTALL)
    tbody = m_tbody.group(1) if m_tbody else ""

    band_re = re.compile(
        r'<tr class="count-year-band"[^>]*?data-c-year="([^"]*)"[^>]*>.*?</tr>'
        r"(.*?)(?=<tr class=\"count-year-band\"|$)",
        re.DOTALL,
    )
    sections = []
    for mm in band_re.finditer(tbody):
        year = mm.group(1)
        chunk = re.sub(
            r'<tr class="count-year-gap"[^>]*>.*?</tr>', "", mm.group(2), flags=re.DOTALL
        )
        if "<tr" not in chunk:
            continue
        sections.append(
            "<div class='year-section'>"
            f"<div class='year-heading'>{html_mod.escape(year)}</div>"
            f"<table class='print-table'>{thead}<tbody>{chunk}</tbody></table>"
            "</div>"
        )
    if not sections:
        return html
    return html[: m.start()] + "".join(sections) + html[m.end():]


def build_count_with_filters(count_display_df, print_style_rows, count_df,
                             description_map=None, disclaimer_html=None,
                             warning_types=None, display_summary=None,
                             source_df=None):
    """Ενότητα Καταμέτρηση με client-side φίλτρα και δυναμικά σύνολα ανά έτος.
    Αν δοθεί disclaimer_html, η δομή είναι τριών ζωνών: σταθερό πάνω (κεφαλίδες+φίλτρα),
    ενδιάμεσο με πίνακα (κύληση εδώ), σταθερό κάτω (disclaimer).
    """
    _col_renames = {
        'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ': 'ΑΠΟΔΟΧΕΣ',
        'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ': 'ΕΙΣΦΟΡΕΣ',
        'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ': '%',
    }
    renamed_df = count_display_df.rename(
        columns={k: v for k, v in _col_renames.items() if k in count_display_df.columns}
    )

    count_table_html = build_yearly_print_html(
        renamed_df, year_column='ΕΤΟΣ', style_rows=print_style_rows,
    )
    count_table_html = re.sub(r'>ΣΥΝΟΛΟ\s+(\d{4})<', r'>\1<', count_table_html)
    count_table_html = re.sub(r'>Σύνολο\s+(\d{4})<', r'>\1<', count_table_html)

    # Ενοποίηση όλων των ετών σε ΕΝΑΝ πίνακα (όπως «Κύρια Δεδομένα» / native Streamlit):
    # μία sticky κεφαλίδα, auto πλάτη (χωράνε οι στήλες χωρίς οριζόντιο scroll), μπάντα έτους
    # στην αρχή κάθε έτους + κενή γραμμή στο τέλος, μορφοποιημένες γραμμές συνόλου.
    count_table_html = _build_unified_count_table_html(count_table_html)

    desc_map = description_map or {}

    def _vals(col):
        if col in count_df.columns:
            return sorted(count_df[col].dropna().astype(str).str.strip().unique().tolist())
        return []

    tameio_vals = _vals('Ταμείο')
    typos_vals = _vals('Τύπος Ασφάλισης')
    employer_col = 'Α-Μ εργοδότη' if 'Α-Μ εργοδότη' in count_df.columns else 'Εργοδότης'
    employer_vals = _vals(employer_col)
    klados_vals = _vals('Κλάδος/Πακέτο Κάλυψης')
    apodoxes_col = next((c for c in count_df.columns if 'Τύπος Αποδοχών' in c or 'Αποδοχών' in c), None)
    apodoxes_vals = _vals(apodoxes_col) if apodoxes_col else []

    _cnt_dd_tameio = _count_filter_modal("Ταμείο", tameio_vals, "tameio")
    _cnt_dd_typos = _count_filter_modal("Τύπος Ασφάλισης", typos_vals, "typos")
    _cnt_dd_employer = _count_filter_modal("Εργοδότης", employer_vals, "employer")
    _klados_pct_map = _klados_eisf_pct_map_from_totals(display_summary, source_df=source_df)
    _cnt_dd_klados = _count_filter_modal(
        "Κλάδος/Πακέτο και μέσο ποσοστό εισφοράς",
        klados_vals, "klados", with_desc=True, desc_map=desc_map,
        pct_map=_klados_pct_map, modal_wide=True,
    )
    _cnt_apodoxes_dd = _count_filter_modal(
        "Τύπος Αποδοχών", _apodoxes_option_pairs(apodoxes_vals), "apodoxes"
    )
    _cnt_to_current_year = f"31/12/{datetime.date.today().year}"
    _cnt_preset_btns = (
        '<button type="button" class="count-preset-btn" data-cnt-preset="from_2002" '
        f'data-cnt-from="01/01/2002" data-cnt-to="{_cnt_to_current_year}" '
        f'title="Φίλτρο από 01/01/2002 έως {_cnt_to_current_year} — ξανά κλικ για επαναφορά ημερομηνιών">Από 1/1/2002</button>'
        '<button type="button" class="count-preset-btn" data-cnt-preset="range_2002_2014" '
        'data-cnt-from="01/01/2002" data-cnt-to="31/12/2014" '
        'title="Φίλτρο 01/01/2002 – 31/12/2014 — ξανά κλικ για επαναφορά ημερομηνιών">1/1/2002 – 31/12/2014</button>'
        '<button type="button" class="count-preset-btn" data-cnt-preset="range_2009_2013" '
        'data-cnt-from="01/01/2009" data-cnt-to="31/12/2013" '
        'title="Φίλτρο 01/01/2009 – 31/12/2013 — ξανά κλικ για επαναφορά ημερομηνιών">1/1/2009 – 31/12/2013</button>'
        '<button type="button" class="count-preset-btn" data-cnt-preset="until_2016" '
        'data-cnt-from="01/01/1960" data-cnt-to="31/12/2016" '
        'title="Φίλτρο από 01/01/1960 έως 31/12/2016 — ξανά κλικ για επαναφορά ημερομηνιών">Έως 31/12/2016</button>'
        '<button type="button" class="count-preset-btn" data-cnt-preset="range_2017_2019" '
        'data-cnt-from="01/01/2017" data-cnt-to="31/12/2019" '
        'title="Φίλτρο 01/01/2017 – 31/12/2019 — ξανά κλικ για επαναφορά ημερομηνιών">1/1/2017 – 31/12/2019</button>'
        '<button type="button" class="count-preset-btn" data-cnt-preset="from_2020" '
        f'data-cnt-from="01/01/2020" data-cnt-to="{_cnt_to_current_year}" '
        f'title="Φίλτρο από 01/01/2020 έως {_cnt_to_current_year} — ξανά κλικ για επαναφορά ημερομηνιών">Από 1/1/2020</button>'
    )
    # Ένα μόνο κουμπί reset (στατικό HTML)· όχι appendChild από JS — αποφεύγει διπλό κουμπί αν τρέξει δύο φορές το script.
    _cnt_reset_btn = (
        '<button type="button" class="filter-reset-btn" id="cnt-filter-reset" '
        'title="Επαναφορά φίλτρων" aria-label="Επαναφορά φίλτρων">&#x21bb;</button>'
    )
    filter_bar = (
        '<div class="count-filters" id="count-filters-bar">'
        '<div class="count-filters-grid">'
        f'{_cnt_dd_tameio}{_cnt_dd_typos}{_cnt_dd_employer}{_cnt_dd_klados}'
        f'<div class="cnt-grid-apodox">{_cnt_apodoxes_dd}</div>'
        '<div class="cnt-grid-from">'
        '<input type="text" id="cnt-filter-from" class="filter-date" '
        'placeholder="01/2002" aria-label="Από (mm/yyyy)" autocomplete="off">'
        '</div>'
        '<div class="cnt-grid-to">'
        '<input type="text" id="cnt-filter-to" class="filter-date" '
        'placeholder="12/2026" aria-label="Έως (mm/yyyy)" autocomplete="off">'
        '</div>'
        f'<div class="cnt-grid-reset">{_cnt_reset_btn}</div>'
        '<div class="cnt-grid-row2">'
        '<div class="cnt-grid-cbs count-filter-cb-stack">'
        '<label class="filter-cb">'
        '<input type="checkbox" id="cnt-year-sparse"> Αραιή'
        '</label>'
        '<label class="filter-cb">'
        '<input type="checkbox" id="cnt-totals-only"> Ετήσια σύνολα'
        '</label>'
        '</div>'
        f'<div id="count-date-presets-bar" class="count-date-presets-bar cnt-grid-preset">{_cnt_preset_btns}</div>'
        '</div>'
        '</div>'
        '</div>'
    )

    warning_types = warning_types or []
    if warning_types:
        _warn_text = ", ".join(warning_types)
        _count_info_msg = (
            f"Προσοχή: υπάρχει πιθανή {_warn_text}. "
            "Το άθροισμα ημερών μπορεί να δώσει λάθος αποτελέσματα."
        )
        _count_bar_class = "totals-info-bar totals-info-bar-warning"
    else:
        _count_info_msg = ""
        _count_bar_class = "totals-info-bar"

    # Γραμμές c_df σε JSON: τα metrics στο HTML φιλτράρονται client-side όπως στην Κυρία
    # (ταμείο, τύπος ασφάλισης, εργοδότης, πακέτο, τύπος αποδοχών, έτος) — όχι μόνο πακέτα.
    cdf_metrics_payload_html = ""
    try:
        _c_df_exp = build_count_c_dataframe(count_df, desc_map)
        if _c_df_exp is not None and not getattr(_c_df_exp, "empty", True):
            _rows_compact = []
            for _, _r in _c_df_exp.iterrows():
                try:
                    _rows_compact.append(
                        {
                            "y": int(_r["ΕΤΟΣ"]),
                            "t": str(_r.get("ΤΑΜΕΙΟ", "") or ""),
                            "k": str(_r.get("ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ", "") or ""),
                            "e": str(_r.get("ΕΡΓΟΔΟΤΗΣ", "") or ""),
                            "p": str(_r.get("ΚΛΑΔΟΣ/ΠΑΚΕΤΟ", "") or "").strip(),
                            "a": str(_r.get("ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ", "") or ""),
                            "m": int(_r["Μήνας_Num"]),
                            "d": float(_r["Ημέρες"] or 0),
                        }
                    )
                except Exception:
                    continue
            if _rows_compact:
                _cdf_payload = {"yearDays": 300.0, "rows": _rows_compact}
                _json_cdf = json.dumps(_cdf_payload, ensure_ascii=False).replace("<", "\\u003c")
                cdf_metrics_payload_html = (
                    f'<script type="application/json" id="atlas-count-cdf-metrics-json">{_json_cdf}</script>'
                )
    except Exception:
        cdf_metrics_payload_html = ""

    count_metrics_bar = ""
    if cdf_metrics_payload_html:
        count_metrics_bar = (
            f"{cdf_metrics_payload_html}"
            f'<div class="{_count_bar_class} count-kind-metrics atlas-header-split" id="count-kind-metrics-wrap" style="display:none">'
            f'<div class="atlas-header-info"><div class="totals-info-msg">{html_mod.escape(_count_info_msg)}</div></div>'
            f'{build_atlas_metrics_frame_html("".join([_atlas_metric_cell_html("Σύνολο ημερών (μισθωτή)", "", "cnt-metric-misthoti", critical=True), _atlas_metric_cell_html("Σύνολο ημερών (μη μισθωτή)", "", "cnt-metric-nmisthoti", critical=True), _atlas_metric_cell_html("Άθροισμα ημερών", "", "cnt-metric-sum", critical=True), _atlas_metric_cell_html("Συνολικά έτη", "", "cnt-metric-years", critical=True)]))}'
            "</div>"
        )

    js = _build_count_filter_js()

    _count_info_sections = [
        (
            "info",
            "Αναλυτική καταμέτρηση ημερών ανά έτος, ταμείο, εργοδότη και μήνα.",
        ),
        (
            "warning",
            "Διαστήματα που καλύπτουν πολλαπλούς μήνες επιμερίζονται και επισημαίνονται με κίτρινο χρώμα.",
        ),
        ("info", f"Εξαιρούνται: {EXCLUDED_PACKAGES_LABEL}"),
    ]
    _count_heading = _atlas_html_tab_heading_row_info(
        "Πίνακας Καταμέτρησης",
        "Οδηγίες — Καταμέτρηση ημερών ασφάλισης",
        _count_info_sections,
        "atlas-info-store-count",
    )

    return _build_tab_page(
        section_id="count-section",
        extra_section_classes="count-layout",
        heading_html=_count_heading,
        description_html=(
            '<p class="print-description">Αναλυτική καταμέτρηση ημερών ασφάλισης ανά μήνα.</p>'
        ),
        metrics_html=count_metrics_bar,
        filters_html=filter_bar,
        body_html=(
            '<div id="count-tables-wrapper" class="count-layout-middle">'
            f'{count_table_html}</div>'
        ),
        scripts_html=f"<script>{js}</script>",
    )


def _build_count_filter_js():
    """JS: φίλτρα καταμέτρησης + δυναμικά σύνολα (ορατές γραμμές ανά τμήμα πριν κάθε γραμμή συνόλου)."""
    return r"""
(function(){
  var sec=document.getElementById('count-section');
  if(!sec)return;
  var cTable=sec.querySelector('#count-tables-wrapper table.count-unified');
  var MH=['ΙΑΝ','ΦΕΒ','ΜΑΡ','ΑΠΡ','ΜΑΙ','ΙΟΥΝ','ΙΟΥΛ','ΑΥΓ','ΣΕΠ','ΟΚΤ','ΝΟΕ','ΔΕΚ'];

  function mapHeaders(tbl){
    var cm={tameio:undefined,typos:undefined,employer:undefined,klados:undefined,apodoxes:undefined,monthIdxs:[],synoloIdx:undefined,perigrafi:undefined,apodoxesCol:undefined,eisforcesCol:undefined,pctCol:undefined};
    tbl.querySelectorAll('thead th').forEach(function(th,i){
      var t=(th.textContent||'').trim();
      if(t==='ΤΑΜΕΙΟ')cm.tameio=i;
      else if(t==='ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ')cm.typos=i;
      else if(t==='ΕΡΓΟΔΟΤΗΣ')cm.employer=i;
      else if(t.indexOf('ΚΛΑΔΟΣ')!==-1||t.indexOf('ΠΑΚΕΤΟ')!==-1)cm.klados=i;
      else if(t.indexOf('ΑΠΟΔΟΧΩΝ')!==-1)cm.apodoxes=i;
      else if(t==='ΑΠΟΔΟΧΕΣ')cm.apodoxesCol=i;
      else if(t==='ΕΙΣΦΟΡΕΣ')cm.eisforcesCol=i;
      else if(t==='ΣΥΝΟΛΟ')cm.synoloIdx=i;
      else if(t==='ΠΕΡΙΓΡΑΦΗ')cm.perigrafi=i;
      else if(t==='%'||(t.indexOf('ΠΟΣΟΣΤΟ')!==-1&&t.indexOf('ΕΙΣΦΟΡ')!==-1))cm.pctCol=i;
      else if(MH.indexOf(t)!==-1)cm.monthIdxs.push(i);
    });
    return cm;
  }

  function parseGreekNum(t){
    if(!t||(t=t.trim())===''||t==='-')return NaN;
    var s=t.replace(/\s/g,'').replace(/\./g,'').replace(',','.').replace(/[€%\s]/g,'');
    var n=parseFloat(s);return isNaN(n)?NaN:n;
  }
  function formatCurr(n){if(isNaN(n)||n===0)return '';var s=n.toFixed(2).replace('.',',');return s.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+' €';}
  function formatDays(n){
    if(isNaN(n)||n===0)return '';
    var r=Math.round(n*100)/100;
    if(Math.abs(r-Math.round(r))<0.001)return String(Math.round(r));
    return String(r.toFixed(1)).replace('.',',');
  }

  function initSums(cm){
    var sums={};
    cm.monthIdxs.forEach(function(i){sums[i]=0;});
    if(cm.synoloIdx!==undefined)sums[cm.synoloIdx]=0;
    if(cm.apodoxesCol!==undefined)sums[cm.apodoxesCol]=0;
    if(cm.eisforcesCol!==undefined)sums[cm.eisforcesCol]=0;
    return sums;
  }

  function addTrToSums(tr,sums,cm,totOnly,segTameioRef,fromM,toM){
    if(tr.getAttribute('data-is-band')==='1')return;
    if(tr.getAttribute('data-is-sep')==='1')return;
    if(tr.getAttribute('data-is-total')==='1')return;
    var tds=tr.querySelectorAll('td');
    if(cm.perigrafi!==undefined&&tds[cm.perigrafi]&&(tds[cm.perigrafi].textContent||'').trim()==='Εισφορές μήνα')return;
    if(totOnly){if(tr.getAttribute('data-filter-ok')!=='1')return;}
    else if(tr.style.display==='none')return;
    if(segTameioRef){
      var tm=(tr.getAttribute('data-c-tameio')||'').trim();
      if(tm&&!segTameioRef.v)segTameioRef.v=tm;
    }
    var yr=parseInt(tr.getAttribute('data-c-year')||'',10)||0;
    Object.keys(sums).forEach(function(k){
      var i=parseInt(k,10);
      if(cm.monthIdxs.indexOf(i)>=0){
        var mi=cm.monthIdxs.indexOf(i)+1;
        if(yr&&!cntMonthInRange(yr,mi,fromM,toM))return;
      }
      if(tds[i]){var v=parseGreekNum(tds[i].textContent);if(!isNaN(v))sums[k]=sums[k]+v;}
    });
  }

  function monthCapForTameio(tn){
    var u=String(tn||'').toUpperCase();
    return u.indexOf('ΙΚΑ')!==-1?31:25;
  }

  function flushTotalRow(tr,sums,cm,segTameio,showFund){
    var cap=monthCapForTameio(segTameio);
    var tds=tr.querySelectorAll('td');
    function setCell(i,txt){if(tds[i])tds[i].textContent=txt;}
    var totalDays=0;
    cm.monthIdxs.forEach(function(i){
      var raw=sums[i]||0;
      var v=raw>cap?cap:raw;
      totalDays+=v;
      setCell(i,formatDays(v));
    });
    if(cm.synoloIdx!==undefined)setCell(cm.synoloIdx,formatDays(totalDays));
    if(cm.apodoxesCol!==undefined)setCell(cm.apodoxesCol,formatCurr(sums[cm.apodoxesCol]||0));
    if(cm.eisforcesCol!==undefined)setCell(cm.eisforcesCol,formatCurr(sums[cm.eisforcesCol]||0));
    if(cm.pctCol!==undefined){
      var apo=sums[cm.apodoxesCol]||0;var eis=sums[cm.eisforcesCol]||0;
      var pct=(apo&&Math.abs(apo)>1e-9)?(eis/apo*100):NaN;
      setCell(cm.pctCol,(isNaN(pct)||pct===0)?'':(pct.toFixed(2).replace('.',',')+' %'));
    }
    if(showFund&&segTameio){
      tr.setAttribute('data-c-seg-tameio',segTameio);
    }else if(!showFund){
      tr.removeAttribute('data-c-seg-tameio');
    }
  }

  function reflowTotalsOnlyFundLabels(cm,rows,totOnly){
    if(!totOnly){
      Array.prototype.forEach.call(rows,function(tr){
        if(tr.getAttribute('data-is-total')!=='1')return;
        tr.removeAttribute('data-c-seg-tameio');
        var tds=tr.querySelectorAll('td');
        if(cm.tameio!==undefined&&tds[cm.tameio])tds[cm.tameio].textContent='';
      });
      return;
    }
    var prevT='\u0000';
    Array.prototype.forEach.call(rows,function(tr){
      if(tr.getAttribute('data-is-band')==='1'){prevT='\u0000';return;}
      if(tr.getAttribute('data-is-sep')==='1')return;
      if(tr.getAttribute('data-is-total')!=='1')return;
      if(tr.style.display==='none')return;
      var t=(tr.getAttribute('data-c-seg-tameio')||'').trim();
      var tds=tr.querySelectorAll('td');
      if(cm.tameio!==undefined&&tds[cm.tameio]){
        tds[cm.tameio].textContent=(t&&t!==prevT)?t:'';
      }
      if(t)prevT=t;
    });
  }

  function rowCountsTowardSubtotal(tr,cm,totOnly){
    if(tr.getAttribute('data-is-band')==='1')return false;
    if(tr.getAttribute('data-is-sep')==='1')return false;
    if(tr.getAttribute('data-is-total')==='1')return false;
    var tds=tr.querySelectorAll('td');
    if(cm.perigrafi!==undefined&&tds[cm.perigrafi]&&(tds[cm.perigrafi].textContent||'').trim()==='Εισφορές μήνα')return false;
    if(totOnly)return tr.getAttribute('data-filter-ok')==='1';
    return tr.style.display!=='none';
  }

  function reflowCollapsedFundLabels(cm,rows,totOnly){
    var prevT='\u0000',prevY='\u0000',prevE='\u0000';
    Array.prototype.forEach.call(rows,function(tr){
      if(tr.getAttribute('data-is-band')==='1'){prevT=prevY=prevE='\u0000';return;}
      if(tr.getAttribute('data-is-sep')==='1')return;
      if(tr.getAttribute('data-is-total')==='1'){prevT=prevY=prevE='\u0000';return;}
      if(totOnly){if(tr.getAttribute('data-filter-ok')!=='1')return;}
      else if(tr.style.display==='none')return;
      var tds=tr.querySelectorAll('td');
      var t=(tr.getAttribute('data-c-tameio')||'').trim();
      var y=(tr.getAttribute('data-c-typos')||'').trim();
      var e=(tr.getAttribute('data-c-employer')||'').trim();
      if(cm.tameio!==undefined&&tds[cm.tameio])tds[cm.tameio].textContent=(t!==prevT)?t:'';
      if(cm.typos!==undefined&&tds[cm.typos])tds[cm.typos].textContent=(t!==prevT||y!==prevY)?y:'';
      if(cm.employer!==undefined&&tds[cm.employer])tds[cm.employer].textContent=(t!==prevT||y!==prevY||e!==prevE)?e:'';
      prevT=t;prevY=y;prevE=e;
    });
  }

  if(cTable){
    var cmTag=mapHeaders(cTable);
    var tagRows=cTable.querySelectorAll('tbody tr');
    var lastTag={};
    tagRows.forEach(function(tr){
      if(tr.getAttribute('data-is-band')==='1'){lastTag={};return;}
      if(tr.getAttribute('data-is-sep')==='1')return;
      var tds=tr.querySelectorAll('td');
      var isTotal=tr.classList.contains('total-row');
      if(!isTotal){
        for(var j=0;j<tds.length;j++){
          var tx=(tds[j].textContent||'').trim();
          if(tx.indexOf('ΣΥΝΟΛΟ')===0){isTotal=true;break;}
          var st=(tds[j].getAttribute('style')||'').toLowerCase();
          if(st.indexOf('cfe2f3')!==-1||st.indexOf('e8f4fc')!==-1||st.indexOf('f5fafc')!==-1){isTotal=true;break;}
        }
      }
      if(isTotal)tr.classList.add('total-row');
      tr.setAttribute('data-is-total',isTotal?'1':'0');
      tr.classList.remove('copy-target');
      tr.removeAttribute('title');
      var allEmpty=true;for(var k=0;k<tds.length;k++){if(tds[k].textContent.trim()){allEmpty=false;break;}}
      if(allEmpty){tr.setAttribute('data-is-sep','1');return;}
      if(isTotal){
        if(lastTag['tameio'])tr.setAttribute('data-c-seg-tameio',lastTag['tameio']);
        return;
      }
      function gv(key){var idx=cmTag[key];if(idx===undefined)return '';var td=tds[idx];var v=td?td.textContent.trim():'';if(v)lastTag[key]=v;return lastTag[key]||'';}
      tr.setAttribute('data-c-tameio',gv('tameio'));tr.setAttribute('data-c-typos',gv('typos'));tr.setAttribute('data-c-employer',gv('employer'));tr.setAttribute('data-c-klados',gv('klados'));tr.setAttribute('data-c-apodoxes',gv('apodoxes'));
    });
    var apodoxesColT=cmTag.apodoxesCol, eisforcesColT=cmTag.eisforcesCol;
    tagRows.forEach(function(tr){
      if(tr.getAttribute('data-is-band')==='1'||tr.getAttribute('data-is-sep')==='1')return;
      var tds=tr.querySelectorAll('td');
      if(apodoxesColT!==undefined&&apodoxesColT>=0&&tds[apodoxesColT]){tds[apodoxesColT].classList.add('copy-target');tds[apodoxesColT].setAttribute('title','Κλικ για αντιγραφή (Αποδοχές)');}
      if(eisforcesColT!==undefined&&eisforcesColT>=0&&tds[eisforcesColT]){tds[eisforcesColT].classList.add('copy-target');tds[eisforcesColT].setAttribute('title','Κλικ για αντιγραφή (Εισφορές)');}
    });
  }

  function cntParseMonthYear(s,isTo){
    if(!s)return null;
    var t=String(s).trim();
    if(!t)return null;
    var m3=t.match(/^(\d{1,2})[./](\d{1,2})[./](\d{4})$/);
    if(m3)return {y:parseInt(m3[3],10),m:parseInt(m3[2],10)};
    var m2=t.match(/^(\d{1,2})[./](\d{4})$/);
    if(m2)return {y:parseInt(m2[2],10),m:parseInt(m2[1],10)};
    var y=parseInt(t,10);
    if(!isNaN(y)&&y>=1000&&y<=9999)return {y:y,m:isTo?12:1};
    return null;
  }
  function cntMonthIntFromInput(id,fallback,isTo){
    var el=document.getElementById(id);
    if(!el)return fallback;
    var raw=(el.value||'').trim();
    if(!raw)return fallback;
    var p=cntParseMonthYear(raw,!!isTo);
    return p?p.y*100+p.m:fallback;
  }
  function cntMonthInRange(year,month,fromM,toM){
    if(!year||!month)return true;
    var ym=year*100+month;
    if(fromM&&ym<fromM)return false;
    if(toM&&ym>toM)return false;
    return true;
  }
  function cntYearHasMonthInRange(year,fromM,toM){
    if(!year)return true;
    for(var m=1;m<=12;m++){if(cntMonthInRange(year,m,fromM,toM))return true;}
    return false;
  }
  function cntMaskMonthCells(tr,cm,fromM,toM){
    var yr=parseInt(tr.getAttribute('data-c-year')||'',10)||0;
    if(!yr||tr.getAttribute('data-is-band')==='1'||tr.getAttribute('data-is-sep')==='1'||tr.getAttribute('data-is-total')==='1')return;
    var tds=tr.querySelectorAll('td');
    cm.monthIdxs.forEach(function(colIdx,pos){
      var mi=pos+1;
      var td=tds[colIdx];
      if(!td)return;
      var attr='data-c-raw-'+colIdx;
      if(!td.hasAttribute(attr))td.setAttribute(attr,td.textContent||'');
      var raw=td.getAttribute(attr)||'';
      td.textContent=cntMonthInRange(yr,mi,fromM,toM)?raw:'';
    });
  }
  function cntRecalcRowSynolo(tr,cm){
    if(cm.synoloIdx===undefined||tr.getAttribute('data-is-total')==='1')return;
    var tds=tr.querySelectorAll('td');
    var total=0;
    cm.monthIdxs.forEach(function(colIdx){
      var v=parseGreekNum((tds[colIdx]&&tds[colIdx].textContent)||'');
      if(!isNaN(v))total+=v;
    });
    if(tds[cm.synoloIdx])tds[cm.synoloIdx].textContent=formatDays(total);
  }

  function liteCollectChecked(sec,key){
    var out=[],seen={};
    function add(cb){
      if(!cb||cb.type!=='checkbox'||!cb.checked)return;
      if((cb.getAttribute('data-attr')||'')!==key)return;
      if(seen[cb.value])return;
      seen[cb.value]=1;out.push(cb.value);
    }
    if(sec)sec.querySelectorAll('.filter-modal-group[data-filter-key="'+key+'"] input[type="checkbox"]').forEach(add);
    var m=document.getElementById('lite-filter-modal-options-mount');
    if(m)m.querySelectorAll('input[type="checkbox"]').forEach(add);
    return out;
  }
  function liteUncheckAllInSection(sec){
    if(!sec)return;
    sec.querySelectorAll('input[type="checkbox"]').forEach(function(cb){cb.checked=false;});
    var m=document.getElementById('lite-filter-modal-options-mount');
    if(m)m.querySelectorAll('input[type="checkbox"]').forEach(function(cb){cb.checked=false;});
  }

  function apply(){
    var f={tameio:[],typos:[],employer:[],klados:[],apodoxes:[]};
    ['tameio','typos','employer','klados','apodoxes'].forEach(function(attr){
      f[attr]=liteCollectChecked(sec,attr);
    });
    var klKey=(f.klados||[]).slice().sort().join('\u0001');
    if(klKey!==apply._prevCntKlados){
      apply._prevCntKlados=klKey;
      try{window.dispatchEvent(new CustomEvent('atlas-count-klados-change',{detail:{codes:(f.klados||[]).slice()}}));}catch(e){}
    }
    try{window.dispatchEvent(new CustomEvent('atlas-count-filters-change'));}catch(e){}
    sec.querySelectorAll('.count-filters .filter-modal-group').forEach(function(dd){
      var key=dd.getAttribute('data-filter-key');
      if(!key)return;
      var vals=f[key]||[];
      var label=dd.querySelector('.filter-selected-label');
      var badge=dd.querySelector('.filter-modal-badge');
      if(badge){
        if(vals.length){badge.textContent=vals.length;badge.hidden=false;dd.classList.add('has-selection');}
        else{badge.hidden=true;badge.textContent='';dd.classList.remove('has-selection');}
      }
      if(!label)return;
      if(vals.length===0){ label.textContent=''; return; }
      var esc=function(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;};
      var escA=function(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');};
      label.innerHTML=vals.map(function(v){return '<button type="button" class="filter-selected-chip" data-value="'+escA(v)+'" data-filter-key="'+escA(key)+'" title="Αφαίρεση">'+esc(v)+'</button>';}).join('');
    });
    var fromM=cntMonthIntFromInput('cnt-filter-from',0,false);
    var toM=cntMonthIntFromInput('cnt-filter-to',999912,true);
    var totOnly=document.getElementById('cnt-totals-only')&&document.getElementById('cnt-totals-only').checked;
    var sparseGap=document.getElementById('cnt-year-sparse')&&document.getElementById('cnt-year-sparse').checked;
    sec.classList.toggle('count-year-sparse', !!sparseGap);

    if(cTable){
      var cm=mapHeaders(cTable);
      var rows=cTable.querySelectorAll('tbody tr');
      function rowYearOK(tr){var yr=parseInt(tr.getAttribute('data-c-year')||'',10);return !yr||cntYearHasMonthInRange(yr,fromM,toM);}

      // 0) Μάσκα μηνών εκτός διαστήματος (μήνας/έτος μόνο)
      rows.forEach(function(tr){
        cntMaskMonthCells(tr,cm,fromM,toM);
        cntRecalcRowSynolo(tr,cm);
      });

      // 1) Φίλτρο ανά γραμμή (έτος + κριτήρια)
      rows.forEach(function(tr){
        var inY=rowYearOK(tr);
        if(tr.getAttribute('data-is-band')==='1'||tr.getAttribute('data-is-sep')==='1'){tr.style.display=inY?'':'none';return;}
        if(tr.getAttribute('data-is-total')==='1'){tr.style.display=inY?'':'none';return;}
        if(!inY){if(totOnly)tr.setAttribute('data-filter-ok','0');tr.style.display='none';return;}
        var tameio=(tr.getAttribute('data-c-tameio')||'').trim();
        var typos=(tr.getAttribute('data-c-typos')||'').trim();
        var employer=(tr.getAttribute('data-c-employer')||'').trim();
        var kladosRaw=(tr.getAttribute('data-c-klados')||'').trim();
        var klados=kladosRaw.split(/\s*[\u2013-]\s+/)[0].trim();
        var apodoxes=(tr.getAttribute('data-c-apodoxes')||'').trim();
        var ok=(f.tameio.length===0||f.tameio.indexOf(tameio)!==-1)&&(f.typos.length===0||f.typos.indexOf(typos)!==-1)&&(f.employer.length===0||f.employer.indexOf(employer)!==-1)&&(f.klados.length===0||f.klados.indexOf(klados)!==-1)&&(f.apodoxes.length===0||f.apodoxes.indexOf(apodoxes)!==-1);
        if(totOnly){tr.setAttribute('data-filter-ok',ok?'1':'0');tr.style.display='none';return;}
        tr.style.display=ok?'':'none';
      });

      // 2) Ορατότητα γραμμών συνόλου (υποσύνολα κλάδου) ανά τμήμα· reset σε μπάντα έτους
      var segVis=0;
      for(var sj=0;sj<rows.length;sj++){
        var trS=rows[sj];
        if(trS.getAttribute('data-is-band')==='1'){segVis=0;continue;}
        if(trS.getAttribute('data-is-sep')==='1')continue;
        if(trS.getAttribute('data-is-total')==='1'){
          var showSub=rowYearOK(trS)&&(totOnly?segVis>0:(f.klados.length>0&&segVis>0));
          trS.style.display=showSub?'':'none';
          segVis=0;
        }else if(rowCountsTowardSubtotal(trS,cm,totOnly)){
          segVis++;
        }
      }

      // 3) Επαναϋπολογισμός συνόλων· flush σε total rows· reset σε μπάντα/total
      var sums=initSums(cm);
      var segTameioRef={v:''};
      for(var ri=0;ri<rows.length;ri++){
        var tr=rows[ri];
        if(tr.getAttribute('data-is-band')==='1'){sums=initSums(cm);segTameioRef.v='';continue;}
        if(tr.getAttribute('data-is-sep')==='1')continue;
        if(tr.getAttribute('data-is-total')==='1'){
          if(tr.style.display!=='none')
            flushTotalRow(tr,sums,cm,segTameioRef.v,totOnly);
          sums=initSums(cm);
          segTameioRef.v='';
          continue;
        }
        addTrToSums(tr,sums,cm,totOnly,segTameioRef,fromM,toM);
      }

      // 4) Ορατότητα μπάντας/κενής γραμμής: κρύψε έτη χωρίς ορατές γραμμές
      var visByYear={};
      rows.forEach(function(tr){
        if(tr.getAttribute('data-is-band')==='1'||tr.getAttribute('data-is-sep')==='1'||tr.getAttribute('data-is-total')==='1')return;
        var y=(tr.getAttribute('data-c-year')||'');
        var vis=totOnly?(tr.getAttribute('data-filter-ok')==='1'):(tr.style.display!=='none');
        if(vis)visByYear[y]=(visByYear[y]||0)+1;
      });
      rows.forEach(function(tr){
        if(tr.getAttribute('data-is-band')!=='1'&&tr.getAttribute('data-is-sep')!=='1')return;
        var y=(tr.getAttribute('data-c-year')||'');
        tr.style.display=(rowYearOK(tr)&&visByYear[y])?'':'none';
      });

      // 5) Reflow ετικετών (collapsed)
      reflowCollapsedFundLabels(cm,rows,totOnly);
      reflowTotalsOnlyFundLabels(cm,rows,totOnly);
    }

    (function updateCountKindMetrics(){
      var wrap=document.getElementById('count-kind-metrics-wrap');
      if(!wrap)return;
      var je=document.getElementById('atlas-count-cdf-metrics-json');
      var payload={rows:[],yearDays:300};
      try{payload=JSON.parse((je&&je.textContent)||'{}');}catch(e){}
      var allRows=payload.rows||[];
      var yd=parseFloat(payload.yearDays)||300;
      var kl=f.klados||[];
      if(kl.length===0){wrap.style.display='none';return;}
      function insKindCls(typos){
        var s=String(typos||'').trim().toUpperCase().replace(/\s+/g,' ');
        if(!s)return null;
        if(/ΜΗ\s*ΜΙΣΘΩΤ/.test(s))return 'ΜΗ ΜΙΣΘΩΤΗ';
        if(s.indexOf('NON')!==-1&&s.indexOf('SAL')!==-1)return 'ΜΗ ΜΙΣΘΩΤΗ';
        if(s.indexOf('ΜΙΣΘΩΤΗ')!==-1&&s.indexOf('ΜΗ ΜΙΣΘΩΤΗ')===-1&&s.indexOf('ΜΗ ')!==0)return 'ΜΙΣΘΩΤΗ';
        return null;
      }
      function capForT(t){
        var u=String(t||'').toUpperCase();
        return (u.indexOf('ΙΚΑ')!==-1||u.indexOf('IKA')!==-1)?31:25;
      }
      function yearKindDays(subRows,year,kindCode){
        var sub=subRows.filter(function(r){return r.y===year;});
        if(kindCode){
          sub=sub.filter(function(r){return insKindCls(r.k)===kindCode;});
        }
        if(sub.length===0)return 0;
        var g={};
        sub.forEach(function(r){
          var key=String(r.t||'')+'|'+r.m;
          g[key]=(g[key]||0)+(+r.d||0);
        });
        var byM={};
        Object.keys(g).forEach(function(key){
          var parts=key.split('|');
          var tn=parts[0];
          var mi=parseInt(parts[1],10);
          var raw=g[key];
          var c=raw<capForT(tn)?raw:capForT(tn);
          byM[mi]=(byM[mi]||0)+c;
        });
        var s=0;
        Object.keys(byM).forEach(function(mi){s+=byM[mi];});
        return s;
      }
      var fr=allRows.filter(function(r){
        if(!cntMonthInRange(r.y,r.m,fromM,toM))return false;
        if(f.tameio.length&&f.tameio.indexOf(r.t)===-1)return false;
        if(f.typos.length&&f.typos.indexOf(r.k)===-1)return false;
        if(f.employer.length&&f.employer.indexOf(r.e)===-1)return false;
        if(f.klados.length&&f.klados.indexOf(r.p)===-1)return false;
        if(f.apodoxes.length&&f.apodoxes.indexOf(r.a)===-1)return false;
        return true;
      });
      var yearsSet={};
      fr.forEach(function(r){yearsSet[r.y]=1;});
      var years=Object.keys(yearsSet).map(function(x){return parseInt(x,10);}).filter(function(y){return !isNaN(y);}).sort(function(a,b){return a-b;});
      var sm=0,snm=0;
      years.forEach(function(y){
        sm+=yearKindDays(fr,y,'ΜΙΣΘΩΤΗ');
        snm+=yearKindDays(fr,y,'ΜΗ ΜΙΣΘΩΤΗ');
      });
      var sall=sm+snm;
      var sy=yd?sall/yd:0;
      function fi(n){return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,'.');}
      function fd(n){return n.toFixed(1).replace('.',',');}
      function fy(n){var p=n.toFixed(2).split('.');return p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.')+','+p[1];}
      var e1=document.getElementById('cnt-metric-misthoti');
      var e2=document.getElementById('cnt-metric-nmisthoti');
      var e3=document.getElementById('cnt-metric-sum');
      var e4=document.getElementById('cnt-metric-years');
      wrap.style.display='';
      if(e1)e1.textContent=fi(sm);
      if(e2)e2.textContent=fi(snm);
      if(e3)e3.textContent=fi(sall);
      if(e4)e4.textContent=fy(sy);
    })();
  }

  window._liteFilterModalApply=window._liteFilterModalApply||{};window._liteFilterModalApply['count-section']=apply;
  ['cnt-filter-from','cnt-filter-to','cnt-totals-only','cnt-year-sparse'].forEach(function(id){var el=document.getElementById(id);if(el)el.addEventListener('input',apply);if(el)el.addEventListener('change',apply);});
  var rb=document.getElementById('cnt-filter-reset');
  if(rb)rb.addEventListener('click',function(){liteUncheckAllInSection(sec);var fromEl=document.getElementById('cnt-filter-from');var toEl=document.getElementById('cnt-filter-to');var totOnly=document.getElementById('cnt-totals-only');var sparseEl=document.getElementById('cnt-year-sparse');if(fromEl)fromEl.value='';if(toEl)toEl.value='';if(totOnly)totOnly.checked=false;if(sparseEl)sparseEl.checked=false;cntClearPresetActive();apply();});
  function cntClearPresetActive(){
    sec.querySelectorAll('#count-date-presets-bar .count-preset-btn.active').forEach(function(b){b.classList.remove('active');});
  }
  function cntSyncPresetActiveFromInputs(){
    var fromEl=document.getElementById('cnt-filter-from');
    var toEl=document.getElementById('cnt-filter-to');
    var fromV=(fromEl&&fromEl.value||'').trim();
    var toV=(toEl&&toEl.value||'').trim();
    var match=null;
    sec.querySelectorAll('#count-date-presets-bar .count-preset-btn').forEach(function(btn){
      var pk=btn.getAttribute('data-cnt-preset')||'';
      var fromOnly=btn.getAttribute('data-cnt-from-only')==='1';
      var expFrom=btn.getAttribute('data-cnt-from')||'';
      var expTo=btn.getAttribute('data-cnt-to')||'';
      if(fromOnly&&fromV===expFrom)match=btn;
      else if(!fromOnly&&fromV===expFrom&&toV===expTo)match=btn;
    });
    cntClearPresetActive();
    if(match)match.classList.add('active');
  }
  sec.querySelectorAll('#count-date-presets-bar .count-preset-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      var fromEl=document.getElementById('cnt-filter-from');
      var toEl=document.getElementById('cnt-filter-to');
      var fromV=btn.getAttribute('data-cnt-from')||'';
      var toV=btn.getAttribute('data-cnt-to')||'';
      var fromOnly=btn.getAttribute('data-cnt-from-only')==='1';
      if(btn.classList.contains('active')){
        if(fromEl)fromEl.value='';
        if(toEl)toEl.value='';
        btn.classList.remove('active');
      }else{
        cntClearPresetActive();
        if(fromEl&&fromV)fromEl.value=fromV;
        if(!fromOnly&&toEl&&toV)toEl.value=toV;
        btn.classList.add('active');
      }
      apply();
    });
  });
  ['cnt-filter-from','cnt-filter-to'].forEach(function(id){
    var el=document.getElementById(id);
    if(!el)return;
    el.addEventListener('input',cntSyncPresetActiveFromInputs);
    el.addEventListener('change',cntSyncPresetActiveFromInputs);
  });
  apply();
})();
"""


# ---------------------------------------------------------------------------
# Report data builder
# ---------------------------------------------------------------------------

_ANNEX_COLUMNS = ["Φορέας", "Κωδικός Κλάδων / Πακέτων Κάλυψης", "Περιγραφή"]
_MAINDATA_DROP_COLUMNS = _ANNEX_COLUMNS + ["Κωδικός Τύπου Αποδοχών"]


def _maindata_row_year(row) -> int | None:
    """Έτος έναρξης περιόδου: πρώτα «Από» (συνεπές με χρονολογική ταξινόμηση), αλλιώς «Έως»."""
    for col in ("Από", "Έως"):
        val = row.get(col) if hasattr(row, "get") else None
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        s = str(val).strip()
        if not s or s.lower() in ("none", "nan", "nat"):
            continue
        dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
        if pd.isna(dt):
            dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            continue
        return int(dt.year)
    return None


def _maindata_spacer_after_indices(dataframe: pd.DataFrame) -> set[int]:
    """Δείκτες γραμμών μετά τις οποίες μπαίνει κενή γραμμή (τέλος 2016, τέλος 2019)."""
    if dataframe is None or dataframe.empty:
        return set()
    years = [_maindata_row_year(dataframe.iloc[i]) for i in range(len(dataframe))]
    out: set[int] = set()
    for target in (2016, 2019):
        last_idx = None
        for i, y in enumerate(years):
            if y == target:
                last_idx = i
        if last_idx is not None:
            out.add(last_idx)
    return out


def _build_maindata_table_html(dataframe: pd.DataFrame) -> str:
    """Πίνακας Κύρια Δεδομένα: sticky header, scroll μόνο στο tbody, κενές γραμμές μετά 2016/2019."""
    if dataframe is None or dataframe.empty:
        return ""
    spacer_after = _maindata_spacer_after_indices(dataframe)
    ncols = len(dataframe.columns)

    colgroup_html = "<colgroup>"
    for col in dataframe.columns:
        c_name = str(col).upper().strip()
        if c_name in ["A/A", "Α/Α", "AA"]:
            width = "20px"
        elif c_name in ["ΕΤΟΣ", "ETOS", "ΈΤΟΣ"]:
            width = "28px"
        elif c_name in ["ΤΑΜΕΙΟ", "TAMEIO"]:
            width = "38px"
        elif c_name in ["ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ"]:
            width = "38px"
        elif c_name in ["ΕΡΓΟΔΟΤΗΣ"]:
            width = "42px"
        elif "ΚΛΑΔΟΣ" in c_name:
            width = "22px"
        elif c_name in ["ΠΕΡΙΓΡΑΦΗ"]:
            width = "72px"
        elif "ΑΠΟΔΟΧΩΝ" in c_name and "ΤΥΠΟΣ" in c_name:
            width = "22px"
        elif c_name in ["ΑΠΟ", "ΕΩΣ"]:
            width = "72px"
        else:
            width = "auto"
        colgroup_html += f'<col style="width:{width}">'
    colgroup_html += "</colgroup>"

    headers_html = "".join(
        f"<th>{html_mod.escape(str(h))}</th>" for h in dataframe.columns
    )
    rows_html = []
    for i in range(len(dataframe)):
        row = dataframe.iloc[i]
        tds = "".join(
            f"<td>{'' if pd.isna(v) else html_mod.escape(str(v))}</td>"
            for v in row.values
        )
        rows_html.append(f"<tr>{tds}</tr>")
        if i in spacer_after:
            rows_html.append(
                f'<tr class="maindata-year-gap" aria-hidden="true">'
                f'<td colspan="{ncols}"></td></tr>'
            )

    table_html = (
        '<table class="print-table maindata-table">'
        f"{colgroup_html}"
        f"<thead><tr>{headers_html}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table>"
    )
    return (
        '<div class="maindata-table-scroll" id="maindata-tables-wrapper">'
        f"{table_html}"
        "</div>"
    )


def _build_annex_table_html(dataframe: pd.DataFrame) -> str:
    """Παράρτημα: πίνακας με αναλογικά βάρη στηλών (όπως Καταμέτρηση)."""
    if dataframe is None or dataframe.empty:
        return ""
    colgroup = _atlas_colgroup_html(dataframe.columns, month_shave=False)
    headers_html = "".join(
        f"<th>{html_mod.escape(str(h))}</th>" for h in dataframe.columns
    )
    bold_cols = {"Φορέας"}
    rows_html = []
    for _, row in dataframe.iterrows():
        tds = []
        for col, v in zip(dataframe.columns, row.values):
            cell = "" if pd.isna(v) else html_mod.escape(str(v))
            if col in bold_cols:
                tds.append(f'<td style="font-weight:700">{cell}</td>')
            else:
                tds.append(f"<td>{cell}</td>")
        rows_html.append(f"<tr>{''.join(tds)}</tr>")
    return (
        '<div class="annex-table-scroll" id="annex-tables-wrapper">'
        '<table class="print-table wrap-cells atlas-weighted-table annex-weighted">'
        f"{colgroup}<thead><tr>{headers_html}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
        "</div>"
    )


def _build_maindata_df(df):
    """Κύρια Δεδομένα: όλες οι στήλες εκτός παραρτήματος, μόνο γραμμές με έγκυρο «Από», χρονολογικά."""
    main_cols = [c for c in df.columns if c not in _MAINDATA_DROP_COLUMNS]
    main_df = df[main_cols].copy() if main_cols else df.copy()
    if "Από" in main_df.columns:
        main_df["__dt"] = pd.to_datetime(main_df["Από"], format="%d/%m/%Y", errors="coerce")
        main_df = main_df.dropna(subset=["__dt"]).sort_values("__dt").drop(columns="__dt")
    return main_df


def _build_annex_df(df):
    """Παράρτημα: στήλες από τις τελευταίες σελίδες (Φορέας / Κωδικός Κλάδων / Περιγραφή)."""
    extra_cols = [c for c in df.columns if c in _ANNEX_COLUMNS]
    if not extra_cols:
        return pd.DataFrame()
    extra_df = df[extra_cols].copy()
    extra_df = extra_df.dropna(how="all")
    extra_df = extra_df[~((extra_df == "None") | (extra_df == "") | (extra_df.isna())).all(axis=1)]
    return extra_df


# ---------------------------------------------------------------------------
# ΑΠΔ / Πλαφόν (Pro) — port από την Κυρία (live φίλτρα σε JS + στατικό fallback)
# ---------------------------------------------------------------------------

# Πλαφόν εισφορών (ίδιοι πίνακες με LOCAL_DEV/kyria/app_final.PLAFOND_*)
PLAFOND_PALIOS = {
    "2002": 1884.75, "2003": 1960.25, "2004": 2058.25, "2005": 2140.50,
    "2006": 2226.00, "2007": 2315.00, "2008": 2384.50, "2009": 2432.25,
    "2010": 2432.25, "2011": 2432.25, "2012": 2432.25, "2013": 5546.80,
    "2014": 5546.80, "2015": 5546.80, "2016": 5861.00, "2017": 5861.00,
    "2018": 5861.00, "2019": 6500.00, "2020": 6500.00, "2021": 6500.00,
    "2022": 6500.00, "2023": 7126.94, "2024": 7126.94, "2025": 7572.62,
    "2026": 7761.94, "2027": 7917.18, "2028": 8075.52, "2029": 8237.03, "2030": 8401.77,
}
PLAFOND_NEOS = {
    "2002": 4693.52, "2003": 4693.52, "2004": 4693.52, "2005": 4881.26,
    "2006": 5076.51, "2007": 5279.57, "2008": 5437.96, "2009": 5543.55,
    "2010": 5543.55, "2011": 5543.55, "2012": 5546.80, "2013": 5546.80,
    "2014": 5546.80, "2015": 5546.80, "2016": 5861.00, "2017": 5861.00,
    "2018": 5861.00, "2019": 6500.00, "2020": 6500.00, "2021": 6500.00,
    "2022": 6500.00, "2023": 7126.94, "2024": 7126.94, "2025": 7572.62,
    "2026": 7761.94, "2027": 7917.18, "2028": 8075.52, "2029": 8237.03, "2030": 8401.77,
}

_APD_DROP_COLUMNS = {
    "Φορέας", "Κωδικός Κλάδων / Πακέτων Κάλυψης", "Περιγραφή",
    "Κωδικός Τύπου Αποδοχών", "Σελίδα",
}
# Στήλες που υπολογίζονται στον αγωγό (δεν είναι «passthrough» από την εγγραφή)
_APD_COMPUTED_COLS = {
    "Έτος", "Μήνας", "Ημέρες Ασφ.", "Μικτές αποδοχές", "Συν. μήνα",
    "Εισφ. πλαφόν", "Συντ. Αποδοχές", "Περικοπή", "Συνολικές εισφορές",
    "Συν. % κράτησης",
}
_APD_SPECIAL_CODES = ("03", "04", "05")


def _apd_is_palios(df) -> bool:
    if "Από" not in df.columns:
        return False
    try:
        d = pd.to_datetime(df["Από"], format="%d/%m/%Y", errors="coerce")
        return (not d.isnull().all()) and d.min() < pd.Timestamp("1993-01-01")
    except Exception:
        return False


def _apd_is_misthoti_typos(typos) -> bool:
    s = str(typos).strip().upper()
    return "ΜΙΣΘΩΤΗ" in s and "ΜΗ ΜΙΣΘΩΤΗ" not in s and not s.startswith("ΜΗ ")


def _apd_clean_code(val) -> str:
    return str(val if val is not None else "").strip().split(" ")[0].strip()


def _apd_is_special_code(clean_code: str) -> bool:
    return (clean_code in _APD_SPECIAL_CODES) or (
        len(clean_code) >= 2 and clean_code[:2] in _APD_SPECIAL_CODES
    )


def _apd_date_to_int(s) -> int:
    """dd/mm/yyyy ή dd.mm.yyyy → yyyymmdd (0 αν άκυρο)."""
    if s is None:
        return 0
    txt = str(s).strip().replace(".", "/")
    if not txt:
        return 0
    dt = pd.to_datetime(txt, format="%d/%m/%Y", errors="coerce")
    if pd.isna(dt):
        return 0
    return int(dt.year) * 10000 + int(dt.month) * 100 + int(dt.day)


def _build_apd_base_df(df):
    """Βάση ΑΠΔ: ίδια λογική με την Κυρία (drop βοηθητικών, εξαίρεση πακέτων, μόνο μισθωτή)."""
    apd_cols = [c for c in df.columns if c not in _APD_DROP_COLUMNS]
    apd_df = df[apd_cols].copy() if apd_cols else df.copy()
    if "Σελίδα" in apd_df.columns:
        apd_df = apd_df.drop(columns=["Σελίδα"])
    pkg_col = next(
        (c for c in ["Κλάδος/Πακέτο Κάλυψης", "Κλάδος/Πακέτο", "ΚΛΑΔΟΣ/ΠΑΚΕΤΟ"] if c in apd_df.columns),
        None,
    )
    if pkg_col is not None:
        s = apd_df[pkg_col].astype(str).str.strip()
        apd_df = apd_df[~s.isin(EXCLUDED_PACKAGES)]
    if "Τύπος Ασφάλισης" in apd_df.columns:
        apd_df = apd_df[apd_df["Τύπος Ασφάλισης"].apply(_apd_is_misthoti_typos)]
    return apd_df.reset_index(drop=True)


def _apd_earnings_col(apd_df):
    return next((c for c in apd_df.columns if "Τύπος Αποδοχών" in c), None)


def _apd_column_order(apd_df, earnings_col):
    """Τελική σειρά στηλών εμφάνισης (ίδια με την Κυρία), ανεξάρτητη από τα φίλτρα."""
    cols = [c for c in apd_df.columns if c not in ("Έτη", "Μήνες", "Ημέρες", "Τύπος Ασφάλισης")]

    def ins_after(lst, anchor, name):
        if name in lst:
            lst.remove(name)
        if anchor in lst:
            lst.insert(lst.index(anchor) + 1, name)
        else:
            lst.append(name)

    if "Κλάδος/Πακέτο Κάλυψης" in cols:
        ins_after(cols, "Κλάδος/Πακέτο Κάλυψης", "Περιγραφή Κλάδου")
    if earnings_col:
        ins_after(cols, earnings_col, "Περιγραφή Τύπου Αποδοχών")
    if "Μικτές αποδοχές" in cols:
        ins_after(cols, "Μικτές αποδοχές", "Εισφ. πλαφόν")
        ins_after(cols, "Εισφ. πλαφόν", "Περικοπή")
        ins_after(cols, "Εισφ. πλαφόν", "Συντ. Αποδοχές")
    if "Συνολικές εισφορές" in cols:
        ins_after(cols, "Συνολικές εισφορές", "Συν. % κράτησης")
    # Έτος πρώτο
    cols = ["Έτος"] + cols
    # Μήνας πριν το Από
    if "Μήνας" in cols:
        cols.remove("Μήνας")
    cols.insert(cols.index("Από") if "Από" in cols else 1, "Μήνας")
    # Ημέρες Ασφ. μετά το Έως
    if "Ημέρες Ασφ." in cols:
        cols.remove("Ημέρες Ασφ.")
    if "Έως" in cols:
        cols.insert(cols.index("Έως") + 1, "Ημέρες Ασφ.")
    else:
        cols.append("Ημέρες Ασφ.")
    # Συν. μήνα μετά τις Μικτές αποδοχές
    if "Συν. μήνα" in cols:
        cols.remove("Συν. μήνα")
    if "Μικτές αποδοχές" in cols:
        cols.insert(cols.index("Μικτές αποδοχές") + 1, "Συν. μήνα")
    else:
        cols.append("Συν. μήνα")
    # Κατάργηση περιττών στηλών «Από»/«Έως»/«Τύπος Ασφάλισης» (μόνο μισθωτής — η στήλη δεν εμφανίζεται)
    cols = [c for c in cols if c not in ("Από", "Έως", "Τύπος Ασφάλισης")]
    return cols


def _apd_build_records(apd_df, earnings_col, description_map):
    """Λίστα εγγραφών (passthrough κελιά + raw αριθμοί) για τον αγωγό (Python & JS)."""
    desc_map = description_map or {}
    pass_cols = [
        c for c in apd_df.columns
        if c not in _APD_COMPUTED_COLS and c not in ("Έτη", "Μήνες", "Ημέρες")
    ]
    records = []
    for _, r in apd_df.iterrows():
        row_cells = {}
        for c in pass_cols:
            v = r.get(c)
            row_cells[c] = "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v)
        klados = str(r.get("Κλάδος/Πακέτο Κάλυψης", "") or "").strip()
        row_cells["Περιγραφή Κλάδου"] = desc_map.get(klados, "") if klados else ""
        code_raw = str(r.get(earnings_col, "") or "").strip() if earnings_col else ""
        clean_code = _apd_clean_code(code_raw)
        ap_desc = APODOXES_DESCRIPTIONS.get(clean_code, "") if clean_code else ""
        row_cells["Περιγραφή Τύπου Αποδοχών"] = ap_desc
        days = (clean_numeric_value(r.get("Ημέρες", 0)) or 0) \
            + (clean_numeric_value(r.get("Μήνες", 0)) or 0) * 25 \
            + (clean_numeric_value(r.get("Έτη", 0)) or 0) * 300
        records.append({
            "row": row_cells,
            "g": clean_numeric_value(r.get("Μικτές αποδοχές", 0), exclude_drx=True) or 0.0,
            "c": clean_numeric_value(r.get("Συνολικές εισφορές", 0), exclude_drx=True) or 0.0,
            "days": float(days),
            "code": clean_code,
            "klados": klados,
            "tameio": str(r.get("Ταμείο", "") or "").strip(),
            "apodox": clean_code,
            "ai": _apd_date_to_int(r.get("Από")),
            "ei": _apd_date_to_int(r.get("Έως")),
        })
    return records


def _apd_fmt_days(n):
    if n is None:
        return ""
    try:
        v = float(n)
    except (TypeError, ValueError):
        return ""
    if v == 0:
        return ""
    return format_number_greek(v, decimals=0)


def _apd_fmt_pct(val):
    if val is None or val == "":
        return ""
    try:
        return f"{float(val):.1%}".replace(".", ",")
    except (TypeError, ValueError):
        return ""


def _apd_compute_display_rows(records, col_order, params):
    """Πλήρης αγωγός ΑΠΔ (ίδιος με την Κυρία) → λίστα γραμμών εμφάνισης.

    params: dict με κλειδιά plafond ('palios'|'neos'|'none'), from_i, to_i (yyyymmdd),
            ret_mode ('all'|'ge'|'lt'), ret_thr (%), highlight (%), totals_only (bool).
    Επιστρέφει λίστα από dict: {kind, cells, low, cut} όπου kind ∈ data|total|empty.
    """
    plafond = params.get("plafond", "neos")
    plafond_map = PLAFOND_PALIOS if plafond == "palios" else (PLAFOND_NEOS if plafond == "neos" else None)
    from_i = params.get("from_i", 0)
    to_i = params.get("to_i", 0)
    sel_tameio = set(params.get("tameio") or [])
    sel_klados = set(params.get("klados") or [])
    sel_apodox = set(params.get("apodox") or [])
    ret_mode = params.get("ret_mode", "all")
    ret_thr = (params.get("ret_thr", 0.0) or 0.0) / 100.0
    highlight = params.get("highlight", 21.0) or 0.0
    totals_only = bool(params.get("totals_only", False))

    # 1) Φίλτρα (ταμείο/κλάδος/αποδοχές + ημερομηνίες στο «Από»)
    flt = []
    for rec in records:
        if sel_tameio and rec["tameio"] not in sel_tameio:
            continue
        if sel_klados and rec["klados"] not in sel_klados:
            continue
        if sel_apodox and rec["apodox"] not in sel_apodox:
            continue
        ai = rec["ai"]
        if from_i and (not ai or ai < from_i):
            continue
        if to_i and (not ai or ai > to_i):
            continue
        flt.append(rec)

    # 2)/3) Per-row βάση πλαφόν + per-row % (για το ΦΙΛΤΡΟ %) + φίλτρο %
    kept = []
    for rec in flt:
        year = (rec["ai"] // 10000) if rec["ai"] else None
        if plafond_map is None:
            base_plaf = None
        else:
            base_plaf = plafond_map.get(str(year), 0) if year else 0
            if rec["code"] in ("04", "05"):
                base_plaf = base_plaf / 2
        gross = rec["g"]
        if base_plaf is None or base_plaf == 0:
            adj_row = gross
        else:
            adj_row = min(gross, base_plaf)
        ret_row = (rec["c"] / adj_row) if adj_row else 0.0
        if ret_mode == "ge" and not (ret_row >= ret_thr):
            continue
        if ret_mode == "lt" and not (ret_row < ret_thr):
            continue
        rec2 = dict(rec)
        rec2["_year"] = year
        rec2["_base_plaf"] = base_plaf
        kept.append(rec2)

    pass_cols = [c for c in col_order if c not in _APD_COMPUTED_COLS]

    def base_cells(rec):
        cells = {c: rec["row"].get(c, "") for c in pass_cols}
        cells["Μικτές αποδοχές"] = format_currency(rec["g"])
        cells["Συνολικές εισφορές"] = format_currency(rec["c"])
        cells["Ημέρες Ασφ."] = _apd_fmt_days(rec["days"])
        return cells

    years = sorted({r["_year"] for r in kept if r["_year"] is not None})
    out = []

    for year in years:
        yr_rows = [r for r in kept if r["_year"] == year]

        # month info + sort priority
        for r in yr_rows:
            di = r["ei"] if r["ei"] else r["ai"]
            month_num = (di // 100) % 100 if di else 13
            special = _apd_is_special_code(r["code"])
            r["_sm"] = 20 if special else month_num
            r["_mlabel"] = "" if special else f"{month_num}ος"
            code = r["code"]
            if not special:
                r["_sp"] = -1 if code == "01" else 0
            elif code.startswith("03"):
                r["_sp"] = 1
            elif code.startswith("04"):
                r["_sp"] = 2
            elif code.startswith("05"):
                r["_sp"] = 3
            else:
                r["_sp"] = 4

        # monthly sums (μόνο μη-κενοί μήνες)
        msum, mcontrib, days01 = {}, {}, {}
        for r in yr_rows:
            m = r["_mlabel"]
            if m:
                msum[m] = msum.get(m, 0.0) + r["g"]
                mcontrib[m] = mcontrib.get(m, 0.0) + r["c"]
                if r["code"] == "01":
                    days01[m] = days01.get(m, 0.0) + r["days"]

        # δυναμικό πλαφόν + οικονομικά ανά γραμμή
        for r in yr_rows:
            m = r["_mlabel"]
            monthly_gross = msum.get(m, 0.0) if m else r["g"]
            monthly_contrib = mcontrib.get(m, 0.0) if m else r["c"]
            r["_synmina"] = monthly_gross
            base = r["_base_plaf"]
            if base is None:
                r["_plaf"] = None
                r["_adj"] = monthly_gross
                r["_cut"] = None
                r["_pct"] = (monthly_contrib / monthly_gross) if monthly_gross else 0.0
            else:
                final_plaf = base
                if m:
                    d01 = days01.get(m, 0.0)
                    if d01 > 0:
                        final_plaf = (base / 25.0) * min(d01, 25)
                if monthly_gross > final_plaf:
                    r["_cut"] = monthly_gross - final_plaf
                    r["_adj"] = final_plaf
                else:
                    r["_cut"] = None
                    r["_adj"] = monthly_gross
                r["_plaf"] = final_plaf
                r["_pct"] = (monthly_contrib / r["_adj"]) if r["_adj"] and r["_adj"] > 0 else 0.0

        yr_rows.sort(key=lambda r: (r["_sm"], r["_sp"], r["tameio"], r["ai"]))

        prev_month = prev_tameio = None
        days_total = gross_sum = adj_sum = cut_sum = contrib_sum = 0.0
        for idx, r in enumerate(yr_rows):
            cells = base_cells(r)
            cells["Έτος"] = str(int(year)) if idx == 0 else ""
            cells["Μήνας"] = r["_mlabel"]
            cells["Συν. μήνα"] = format_currency(r["_synmina"])
            cells["Εισφ. πλαφόν"] = format_currency(r["_plaf"]) if r["_plaf"] is not None else ""
            cells["Συντ. Αποδοχές"] = format_currency(r["_adj"])
            cells["Περικοπή"] = format_currency(r["_cut"]) if r["_cut"] is not None else ""
            cells["Συν. % κράτησης"] = _apd_fmt_pct(r["_pct"])

            curr_month = r["_mlabel"]
            month_hidden = False
            if curr_month:
                if idx > 0 and curr_month == prev_month:
                    cells["Μήνας"] = ""
                    month_hidden = True
                else:
                    prev_month = curr_month
            if month_hidden:
                cells["Συν. μήνα"] = ""
                cells["Περικοπή"] = ""
                cells["Συντ. Αποδοχές"] = ""
                cells["Συν. % κράτησης"] = ""
                cells["Εισφ. πλαφόν"] = ""

            curr_tameio = r["tameio"]
            if idx > 0 and curr_tameio == prev_tameio:
                cells["Ταμείο"] = ""
            else:
                prev_tameio = curr_tameio

            low = False
            if cells.get("Συν. % κράτησης"):
                try:
                    pv = float(cells["Συν. % κράτησης"].replace("%", "").replace(",", ".").strip())
                    low = pv < highlight
                except ValueError:
                    low = False
            out.append({
                "kind": "data",
                "cells": cells,
                "low": low,
                "cut": bool(cells.get("Περικοπή")),
            })

            # Σύνολα: μικτές/ημέρες ανά γραμμή· συντ.αποδοχές/περικοπή μόνο από ορατές
            # (μη-masked) γραμμές μήνα — όπως η Κυρία αθροίζει το masked dataframe.
            days_total += r["days"]
            gross_sum += r["g"]
            contrib_sum += r["c"]
            if not month_hidden:
                adj_sum += (r["_adj"] or 0.0)
                cut_sum += (r["_cut"] or 0.0)

        # γραμμή συνόλου (έτη ≥ 2002)
        if int(year) >= 2002:
            tcells = {c: "" for c in col_order}
            tcells["Μήνας"] = f"Σύνολο {int(year)}"
            tcells["Ημέρες Ασφ."] = _apd_fmt_days(days_total)
            tcells["Μικτές αποδοχές"] = format_currency(gross_sum)
            tcells["Συν. μήνα"] = format_currency(gross_sum)
            tcells["Συνολικές εισφορές"] = format_currency(contrib_sum)
            tcells["Συντ. Αποδοχές"] = format_currency(adj_sum)
            tcells["Περικοπή"] = format_currency(cut_sum) if cut_sum else ""
            pct_total = (contrib_sum / adj_sum) if adj_sum else 0.0
            tcells["Συν. % κράτησης"] = _apd_fmt_pct(pct_total)
            low_total = (pct_total * 100.0) < highlight if adj_sum else False
            out.append({"kind": "total", "cells": tcells, "low": low_total, "cut": bool(cut_sum)})

        out.append({"kind": "empty", "cells": {}, "low": False, "cut": False})

    if totals_only:
        out = [r for r in out if r["kind"] == "total"]
    return out


def _apd_norm_col_name(name):
    """Κεφαλαία χωρίς τόνους — ίδιο pattern με Καταμέτρηση (_wt)."""
    up = str(name).upper().strip()
    return "".join(
        ch for ch in unicodedata.normalize("NFD", up)
        if unicodedata.category(ch) != "Mn"
    )


def _apd_col_weight(col):
    """Αναλογικά βάρη ανά τύπο στήλης → ποσοστά στο colgroup (όπως count-unified)."""
    u = _apd_norm_col_name(col)
    if u in ("A/A", "AA"):
        return 1.2
    if u == "ΕΤΟΣ":
        return 1.5
    if u == "ΜΗΝΑΣ":
        return 2.0
    if u == "ΤΑΜΕΙΟ":
        return 2.6
    if "ΚΛΑΔΟΣ" in u or "ΠΑΚΕΤΟ" in u:
        return 2.0
    if "ΠΕΡΙΓΡΑΦΗ" in u:
        return 5.0
    if "ΑΠΟΔΟΧΩΝ" in u and "ΤΥΠΟΣ" in u:
        return 2.4
    if "ΗΜΕΡΕΣ" in u:
        return 1.8
    if "%" in u or "ΠΟΣΟΣΤΟ" in u or "ΚΡΑΤΗΣΗΣ" in u:
        return 2.0
    if u == "ΕΡΓΟΔΟΤΗΣ" or "ΕΡΓΟΔΟΤΗ" in u:
        return 2.8
    if u in (
        "ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ", "ΣΥΝ. ΜΗΝΑ", "ΕΙΣΦ. ΠΛΑΦΟΝ",
        "ΣΥΝΤ. ΑΠΟΔΟΧΕΣ", "ΠΕΡΙΚΟΠΗ", "ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ",
    ):
        return 3.8
    return 2.4


def _apd_col_col_class(col):
    """Κλάση στο <col> για στοχευμένα overrides (π.χ. full screen)."""
    cc = _apd_col_class(col)
    return cc.replace("apd-c-", "apd-col-") if cc else ""


def _apd_colgroup(col_order):
    weights = [_apd_col_weight(c) for c in col_order]
    total_w = sum(weights) or 1.0
    parts = ["<colgroup>"]
    for col, w in zip(col_order, weights):
        pct = round(w / total_w * 100, 3)
        cc = _apd_col_col_class(col)
        cls_attr = f' class="{cc}"' if cc else ""
        parts.append(f'<col{cls_attr} style="width:{pct}%">')
    parts.append("</colgroup>")
    return "".join(parts)


_APD_MONEY_COLS = {
    "Μικτές αποδοχές", "Συν. μήνα", "Εισφ. πλαφόν",
    "Συντ. Αποδοχές", "Περικοπή", "Συνολικές εισφορές",
}


def _apd_col_class(col):
    """Κλάση στήλης για στόχευση πλατών/αναδίπλωσης (νομισματικές, ποσοστό, πακέτο, περιγραφές)."""
    c = str(col)
    if c in _APD_MONEY_COLS:
        return "apd-c-money"
    if c == "Συν. % κράτησης":
        return "apd-c-pct"
    if "Κλάδος/Πακέτο" in c:
        return "apd-c-pkg"
    if c.startswith("Περιγραφή"):
        return "apd-c-desc"
    return ""


_APD_TOTAL_MERGE_COLS = ("Μήνας", "Ταμείο")


def _apd_total_merge_range(col_order):
    """Εύρος στηλών για συγχωνευμένο «Σύνολο YYYY» (Μήνας → Ταμείο)."""
    indices = [col_order.index(c) for c in _APD_TOTAL_MERGE_COLS if c in col_order]
    if not indices:
        if "Μήνας" in col_order:
            i = col_order.index("Μήνας")
            return i, 1
        return None, 0
    start, end = min(indices), max(indices)
    return start, end - start + 1


def _apd_render_total_tds(col_order, col_cls, cells):
    """Κελιά γραμμής συνόλου με colspan στο εύρος Μήνας–Ταμείο."""
    merge_start, merge_span = _apd_total_merge_range(col_order)
    label = str(cells.get("Μήνας") or cells.get("Ταμείο") or "").strip()
    parts = []
    i = 0
    while i < len(col_order):
        if merge_start is not None and i == merge_start and merge_span > 0:
            parts.append(
                f'<td colspan="{merge_span}" class="apd-total-label">'
                f'{html_mod.escape(label)}</td>'
            )
            i += merge_span
            continue
        c, cc = col_order[i], col_cls[i]
        val = html_mod.escape(str(cells.get(c, "")))
        parts.append(f'<td class="{cc}">{val}</td>' if cc else f"<td>{val}</td>")
        i += 1
    return "".join(parts)


def _apd_render_static_table(col_order, display_rows):
    """Στατικός πίνακας ΑΠΔ (προεπιλεγμένη κατάσταση) — για εκτύπωση/no-JS."""
    ncols = len(col_order)
    col_cls = [_apd_col_class(c) for c in col_order]
    thead = "<thead><tr>" + "".join(
        f'<th class="{cc}">{html_mod.escape(str(c))}</th>' if cc else f"<th>{html_mod.escape(str(c))}</th>"
        for c, cc in zip(col_order, col_cls)
    ) + "</tr></thead>"
    body = []
    for r in display_rows:
        if r["kind"] == "empty":
            body.append(
                f'<tr class="apd-year-gap" data-apd-kind="empty" aria-hidden="true">'
                f'<td colspan="{ncols}"></td></tr>'
            )
            continue
        if r["kind"] == "total":
            tds = _apd_render_total_tds(col_order, col_cls, r["cells"])
            body.append(f'<tr class="apd-total-row" data-apd-kind="total">{tds}</tr>')
            continue
        cls = "apd-data-row" + (" apd-low" if r.get("low") else "")
        tds = []
        for c, cc in zip(col_order, col_cls):
            val = html_mod.escape(str(r["cells"].get(c, "")))
            classes = cc
            if c == "Περικοπή" and r.get("cut"):
                classes = (cc + " apd-cut").strip()
            tds.append(f'<td class="{classes}">{val}</td>' if classes else f"<td>{val}</td>")
        body.append(f'<tr class="{cls}" data-apd-kind="data">{"".join(tds)}</tr>')
    table = (
        '<table class="print-table apd-table">'
        f"{_apd_colgroup(col_order)}{thead}<tbody>{''.join(body)}</tbody></table>"
    )
    return f'<div class="apd-table-scroll" id="apd-tables-wrapper">{table}</div>'


def build_apd_with_filters(df, description_map=None):
    """Καρτέλα ΑΠΔ/Πλαφόν (Pro): live φίλτρα σε JS + στατικός πίνακας (προεπιλογή)."""
    apd_df = _build_apd_base_df(df)
    if apd_df is None or apd_df.empty:
        return ""
    earnings_col = _apd_earnings_col(apd_df)
    col_order = _apd_column_order(apd_df, earnings_col)
    records = _apd_build_records(apd_df, earnings_col, description_map)
    if not records:
        return ""

    is_palios = _apd_is_palios(df)
    default_plafond = "palios" if is_palios else "neos"
    status_msg = (
        "Παλιός Ασφαλισμένος (εγγραφή πριν από 1/1/1993)" if is_palios
        else "Νέος Ασφαλισμένος (χωρίς εγγραφή πριν από 1/1/1993)"
    )

    default_params = {
        "plafond": default_plafond,
        "from_i": 20020101, "to_i": 0,
        "tameio": [], "klados": [], "apodox": [],
        "ret_mode": "all", "ret_thr": 18.0, "highlight": 21.0,
        "totals_only": False,
    }
    static_rows = _apd_compute_display_rows(records, col_order, default_params)
    static_table = _apd_render_static_table(col_order, static_rows)

    reset_btn = (
        '<button type="button" class="filter-reset-btn" id="apd-filter-reset" '
        'title="Επαναφορά φίλτρων" aria-label="Επαναφορά φίλτρων">&#x21bb;</button>'
    )
    plafond_select = (
        '<select id="apd-plafond" class="apd-filter-input apd-select" title="Πλαφόν">'
        f'<option value="palios"{" selected" if default_plafond == "palios" else ""}>Πλαφόν Παλιού</option>'
        f'<option value="neos"{" selected" if default_plafond == "neos" else ""}>Πλαφόν Νέου</option>'
        '<option value="none">Χωρίς πλαφόν (καμία περικοπή)</option>'
        '</select>'
    )
    retmode_select = (
        '<select id="apd-retmode" class="apd-filter-input apd-select" title="Τύπος Φίλτρου %">'
        '<option value="all">Όλα</option>'
        '<option value="ge">Μεγαλύτερο ή ίσο</option>'
        '<option value="lt">Μικρότερο από</option>'
        '</select>'
    )
    filter_bar = (
        '<div class="count-filters apd-filters" id="apd-filters-bar">'
        '<div class="atlas-locked-count-bar" id="apd-locked-from-count">'
        '<div class="atlas-locked-count-title">Από Καταμέτρηση</div>'
        '<div class="atlas-locked-count-grid">'
        '<div class="atlas-locked-count-item"><span class="atlas-locked-count-sub">Διάστημα</span>'
        '<span class="atlas-locked-count-val" id="apd-lock-dates">—</span></div>'
        '<div class="atlas-locked-count-item"><span class="atlas-locked-count-sub">Ταμείο</span>'
        '<span class="atlas-locked-count-val" id="apd-lock-tameio">—</span></div>'
        '<div class="atlas-locked-count-item"><span class="atlas-locked-count-sub">Πακέτα</span>'
        '<span class="atlas-locked-count-val" id="apd-lock-klados">—</span></div>'
        '<div class="atlas-locked-count-item"><span class="atlas-locked-count-sub">Τύπος αποδοχών</span>'
        '<span class="atlas-locked-count-val" id="apd-lock-apodox">—</span></div>'
        '</div></div>'
        '<div class="apd-filters-grid apd-filters-free">'
        '<div class="apd-grid-pct"><label class="apd-filter-field">'
        '<span class="apd-filter-field-label">Φίλτρο %</span>'
        '<input type="number" id="apd-filter-pct" class="apd-filter-input" min="0" max="100" step="0.1" value="18">'
        '</label></div>'
        '<div class="apd-grid-retmode"><label class="apd-filter-field">'
        '<span class="apd-filter-field-label">Τύπος Φίλτρου</span>'
        f'{retmode_select}'
        '</label></div>'
        '<div class="apd-grid-high"><label class="apd-filter-field">'
        '<span class="apd-filter-field-label">Επισήμανση &lt;</span>'
        '<input type="number" id="apd-filter-high" class="apd-filter-input" min="0" max="100" step="0.1" value="21">'
        '</label></div>'
        '<div class="apd-grid-plafond"><label class="apd-filter-field">'
        '<span class="apd-filter-field-label">Πλαφόν</span>'
        f'{plafond_select}'
        '</label></div>'
        '<div class="apd-grid-cbs"><label class="filter-cb">'
        '<input type="checkbox" id="apd-totals-only"> Μόνο ετήσιες γραμμές συνόλου</label></div>'
        f'<div class="apd-grid-reset">{reset_btn}</div>'
        '</div>'
        '</div>'
    )

    payload = {
        "cols": col_order,
        "computed": sorted(_APD_COMPUTED_COLS),
        "colgroup": _apd_colgroup(col_order),
        "records": records,
        "plafondPalios": PLAFOND_PALIOS,
        "plafondNeos": PLAFOND_NEOS,
        "defaultPlafond": default_plafond,
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    payload_html = (
        f'<script type="application/json" id="atlas-apd-data-json">{payload_json}</script>'
    )

    info_sections = [
        ("info", "Ταμείο, πακέτα, τύπος αποδοχών και διάστημα ημερομηνιών ακολουθούν "
                 "αυτόματα τα φίλτρα της καρτέλας Καταμέτρηση."),
        ("info", "Ανάλυση εγγραφών ΑΠΔ μόνο μισθωτής ασφάλισης με υπολογισμό εισφ. πλαφόν, "
                 "περικοπής λόγω πλαφόν και ποσοστού κράτησης."),
        ("info", f"Καθεστώς: {status_msg}"),
        ("info", f"Εξαιρούνται: {EXCLUDED_PACKAGES_LABEL}"),
    ]
    heading = _atlas_html_tab_heading_row_info(
        "Ανάλυση ΑΠΔ / Πλαφόν",
        "Πληροφορίες — ΑΠΔ / Πλαφόν",
        info_sections,
        "atlas-info-store-apd",
    )

    js = _build_apd_filter_js()

    return _build_tab_page(
        section_id="apd-section",
        extra_section_classes="apd-layout",
        heading_html=heading,
        description_html=(
            '<p class="print-description">Ανάλυση ΑΠΔ με χρονολογική σειρά, εισφ. πλαφόν ΙΚΑ, '
            'περικοπή λόγω πλαφόν και ποσοστό κράτησης.</p>'
        ),
        metrics_html=payload_html,
        filters_html=filter_bar,
        body_html=f'<div id="apd-tables-mount">{static_table}</div>',
        scripts_html=f"<script>{js}</script>",
    )


def _build_apd_filter_js():
    """JS: πλήρης αγωγός ΑΠΔ (φίλτρα + δυναμικό πλαφόν + μηνιαία σύνολα) + συγχρονισμός Καταμέτρησης."""
    return r"""
(function(){
  var sec=document.getElementById('apd-section');
  if(!sec)return;
  var dataEl=document.getElementById('atlas-apd-data-json');
  if(!dataEl)return;
  var DATA={};
  try{DATA=JSON.parse(dataEl.textContent||'{}');}catch(e){return;}
  var COLS=DATA.cols||[];
  var COMPUTED={};(DATA.computed||[]).forEach(function(c){COMPUTED[c]=1;});
  var RECS=DATA.records||[];
  var PAL=DATA.plafondPalios||{}, NEO=DATA.plafondNeos||{};
  var SPECIAL=['03','04','05'];
  var mount=document.getElementById('apd-tables-mount');
  if(!mount)return;

  function isSpecial(code){return SPECIAL.indexOf(code)!==-1||(code.length>=2&&SPECIAL.indexOf(code.substr(0,2))!==-1);}
  function fmtCurr(n){
    if(n===null||n===undefined||isNaN(n)||n===0)return '';
    var s=Math.abs(n).toFixed(2);
    if(s.slice(-3)==='.00')s=s.slice(0,-3);
    var p=s.split('.');
    p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.');
    var out=(p.length>1?p[0]+','+p[1]:p[0]);
    return (n<0?'-':'')+out+' €';
  }
  function fmtDays(n){
    if(n===null||n===undefined||isNaN(n)||n===0)return '';
    var r=Math.round(n);
    return String(r).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
  }
  function fmtPct(v){
    if(v===null||v===undefined||v==='')return '';
    var n=v*100;
    return n.toFixed(1).replace('.',',')+'%';
  }
  function esc(s){var d=document.createElement('div');d.textContent=(s==null?'':s);return d.innerHTML;}
  function escA(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;');}

  function parseDateInt(s,isTo){
    if(!s)return 0;
    var t=String(s).trim();
    var m3=t.match(/^(\d{1,2})[./](\d{1,2})[./](\d{4})$/);
    if(m3)return parseInt(m3[3],10)*100+parseInt(m3[2],10);
    var m2=t.match(/^(\d{1,2})[./](\d{4})$/);
    if(m2)return parseInt(m2[2],10)*100+parseInt(m2[1],10);
    var y=parseInt(t,10);
    if(!isNaN(y)&&y>=1000&&y<=9999)return y*100+(isTo?12:1);
    return 0;
  }
  function parseMonthIntFromAi(ai){
    if(!ai)return 0;
    return Math.floor(ai/100);
  }

  // Κλειδωμένα φίλτρα: ταμείο/πακέτο/τύπος αποδοχών/από-έως από την Καταμέτρηση
  function _ccLocked(key){
    var out=[],seen={};
    var csec=document.getElementById('count-section');
    function add(cb){if(cb&&cb.type==='checkbox'&&cb.checked&&(cb.getAttribute('data-attr')||'')===key&&!seen[cb.value]){seen[cb.value]=1;out.push(cb.value);}}
    if(csec)csec.querySelectorAll('.filter-modal-group[data-filter-key="'+key+'"] input[type="checkbox"]').forEach(add);
    var m=document.getElementById('lite-filter-modal-options-mount');
    if(m)m.querySelectorAll('input[type="checkbox"]').forEach(add);
    return out;
  }
  function readCountLocked(){
    var fEl=document.getElementById('cnt-filter-from'), tEl=document.getElementById('cnt-filter-to');
    return {tameio:_ccLocked('tameio'),apodoxes:_ccLocked('apodoxes'),from:(fEl&&fEl.value)||'',to:(tEl&&tEl.value)||''};
  }
  function fmtCountDateRange(){
    var cl=readCountLocked();
    if(!cl.from&&!cl.to)return 'Όλα';
    if(cl.from&&!cl.to)return 'Από '+cl.from;
    if(!cl.from&&cl.to)return 'Έως '+cl.to;
    return cl.from+' — '+cl.to;
  }
  function fmtLockedList(arr){
    if(!arr||!arr.length)return 'Όλα';
    return arr.join(', ');
  }
  function kladosCodesFromCount(){
    return _ccLocked('klados').map(function(v){return String(v).split(/\s*[\u2013-]\s+/)[0].trim();});
  }
  function readParams(){
    var plEl=document.getElementById('apd-plafond');
    var rmEl=document.getElementById('apd-retmode');
    var pctEl=document.getElementById('apd-filter-pct');
    var hiEl=document.getElementById('apd-filter-high');
    var toEl=document.getElementById('apd-totals-only');
    var cl=readCountLocked();
    return {
      plafond:(plEl&&plEl.value)||'neos',
      from_i:parseDateInt(cl.from,false),
      to_i:parseDateInt(cl.to,true),
      tameio:cl.tameio,
      klados:kladosCodesFromCount(),
      apodox:cl.apodoxes,
      ret_mode:(rmEl&&rmEl.value)||'all',
      ret_thr:parseFloat((pctEl&&pctEl.value)||'0')||0,
      highlight:parseFloat((hiEl&&hiEl.value)||'0')||0,
      totals_only:!!(toEl&&toEl.checked)
    };
  }

  function computeRows(P){
    var plMap=P.plafond==='palios'?PAL:(P.plafond==='neos'?NEO:null);
    var thr=(P.ret_thr||0)/100.0;
    var st={}, sk={}, sa={};
    (P.tameio||[]).forEach(function(v){st[v]=1;});
    (P.klados||[]).forEach(function(v){sk[v]=1;});
    (P.apodox||[]).forEach(function(v){sa[v]=1;});
    var hasT=P.tameio&&P.tameio.length, hasK=P.klados&&P.klados.length, hasA=P.apodox&&P.apodox.length;

    var kept=[];
    for(var i=0;i<RECS.length;i++){
      var r=RECS[i];
      if(hasT&&!st[r.tameio])continue;
      if(hasK&&!sk[r.klados])continue;
      if(hasA&&!sa[r.apodox])continue;
      var ai=r.ai||0;
      var am=parseMonthIntFromAi(ai);
      if(P.from_i&&(!am||am<P.from_i))continue;
      if(P.to_i&&(!am||am>P.to_i))continue;
      var year=ai?Math.floor(ai/10000):null;
      var basePlaf;
      if(plMap===null)basePlaf=null;
      else{basePlaf=year?(plMap[String(year)]||0):0;if(r.code==='04'||r.code==='05')basePlaf=basePlaf/2;}
      var gross=r.g||0;
      var adjRow=(basePlaf===null||basePlaf===0)?gross:Math.min(gross,basePlaf);
      var retRow=adjRow?(r.c||0)/adjRow:0;
      if(P.ret_mode==='ge'&&!(retRow>=thr))continue;
      if(P.ret_mode==='lt'&&!(retRow<thr))continue;
      kept.push({rec:r,year:year,base:basePlaf});
    }

    var passCols=COLS.filter(function(c){return !COMPUTED[c];});
    function baseCells(o){
      var c={};passCols.forEach(function(col){c[col]=(o.rec.row&&o.rec.row[col])||'';});
      c['Μικτές αποδοχές']=fmtCurr(o.rec.g);
      c['Συνολικές εισφορές']=fmtCurr(o.rec.c);
      c['Ημέρες Ασφ.']=fmtDays(o.rec.days);
      return c;
    }

    var ySet={};kept.forEach(function(o){if(o.year!==null)ySet[o.year]=1;});
    var years=Object.keys(ySet).map(function(x){return parseInt(x,10);}).sort(function(a,b){return a-b;});
    var out=[];
    var YT={};  // ετήσια σύνολα (για κλώνο στις Συντάξιμες): {year:{days,gross,synt}}

    years.forEach(function(year){
      var yr=kept.filter(function(o){return o.year===year;});
      yr.forEach(function(o){
        var r=o.rec;
        var di=r.ei||r.ai||0;
        var monthNum=di?Math.floor(di/100)%100:13;
        var sp=isSpecial(r.code);
        o.sm=sp?20:monthNum;
        o.ml=sp?'':(monthNum+'ος');
        var code=r.code;
        if(!sp)o.sp=(code==='01')?-1:0;
        else if(code.indexOf('03')===0)o.sp=1;
        else if(code.indexOf('04')===0)o.sp=2;
        else if(code.indexOf('05')===0)o.sp=3;
        else o.sp=4;
      });
      var msum={},mc={},d01={};
      yr.forEach(function(o){
        var m=o.ml;if(!m)return;
        msum[m]=(msum[m]||0)+(o.rec.g||0);
        mc[m]=(mc[m]||0)+(o.rec.c||0);
        if(o.rec.code==='01')d01[m]=(d01[m]||0)+(o.rec.days||0);
      });
      yr.forEach(function(o){
        var m=o.ml;
        var mg=m?(msum[m]||0):(o.rec.g||0);
        var mcv=m?(mc[m]||0):(o.rec.c||0);
        o.synmina=mg;
        if(o.base===null){o.plaf=null;o.adj=mg;o.cut=null;o.pct=mg?mcv/mg:0;}
        else{
          var fp=o.base;
          if(m){var dd=d01[m]||0;if(dd>0)fp=(o.base/25.0)*Math.min(dd,25);}
          if(mg>fp){o.cut=mg-fp;o.adj=fp;}else{o.cut=null;o.adj=mg;}
          o.plaf=fp;o.pct=(o.adj&&o.adj>0)?mcv/o.adj:0;
        }
      });
      yr.sort(function(a,b){return a.sm-b.sm||a.sp-b.sp||(a.rec.tameio<b.rec.tameio?-1:a.rec.tameio>b.rec.tameio?1:0)||(a.rec.ai-b.rec.ai);});

      var prevM=null,prevT=null;
      var dT=0,gS=0,aS=0,cS=0,contribS=0;
      yr.forEach(function(o,idx){
        var cells=baseCells(o);
        cells['Έτος']=(idx===0)?String(year):'';
        cells['Μήνας']=o.ml;
        cells['Συν. μήνα']=fmtCurr(o.synmina);
        cells['Εισφ. πλαφόν']=(o.plaf!==null)?fmtCurr(o.plaf):'';
        cells['Συντ. Αποδοχές']=fmtCurr(o.adj);
        cells['Περικοπή']=(o.cut!==null)?fmtCurr(o.cut):'';
        cells['Συν. % κράτησης']=fmtPct(o.pct);
        var hidden=false;
        if(o.ml){if(idx>0&&o.ml===prevM){cells['Μήνας']='';hidden=true;}else prevM=o.ml;}
        if(hidden){cells['Συν. μήνα']='';cells['Περικοπή']='';cells['Συντ. Αποδοχές']='';cells['Συν. % κράτησης']='';cells['Εισφ. πλαφόν']='';}
        var ct=o.rec.tameio;
        if(idx>0&&ct===prevT)cells['Ταμείο']='';else prevT=ct;
        var low=false;
        if(cells['Συν. % κράτησης']){
          var pv=parseFloat(cells['Συν. % κράτησης'].replace('%','').replace(',','.'));
          if(!isNaN(pv))low=pv<P.highlight;
        }
        out.push({kind:'data',cells:cells,low:low,cut:!!cells['Περικοπή']});
        dT+=(o.rec.days||0);gS+=(o.rec.g||0);contribS+=(o.rec.c||0);
        if(!hidden){aS+=(o.adj||0);cS+=(o.cut||0);}
      });

      if(year>=2002){
        var tc={};COLS.forEach(function(c){tc[c]='';});
        tc['Μήνας']='Σύνολο '+year;
        tc['Ημέρες Ασφ.']=fmtDays(dT);
        tc['Μικτές αποδοχές']=fmtCurr(gS);
        tc['Συν. μήνα']=fmtCurr(gS);
        tc['Συνολικές εισφορές']=fmtCurr(contribS);
        tc['Συντ. Αποδοχές']=fmtCurr(aS);
        tc['Περικοπή']=cS?fmtCurr(cS):'';
        var pctT=aS?(contribS/aS):0;
        tc['Συν. % κράτησης']=fmtPct(pctT);
        var lowT=aS?((pctT*100)<P.highlight):false;
        out.push({kind:'total',cells:tc,low:lowT,cut:!!cS});
        YT[year]={days:dT,gross:gS,synt:aS};
      }
      out.push({kind:'empty',cells:{},low:false,cut:false});
    });

    try{window._atlasApdYearlyTotals=YT;window.dispatchEvent(new CustomEvent('atlas-apd-recomputed'));}catch(e){}
    if(P.totals_only)out=out.filter(function(r){return r.kind==='total';});
    return out;
  }

  var MONEYCOLS={'Μικτές αποδοχές':1,'Συν. μήνα':1,'Εισφ. πλαφόν':1,'Συντ. Αποδοχές':1,'Περικοπή':1,'Συνολικές εισφορές':1};
  function colClass(c){
    if(MONEYCOLS[c])return 'apd-c-money';
    if(c==='Συν. % κράτησης')return 'apd-c-pct';
    if(String(c).indexOf('Κλάδος/Πακέτο')>=0)return 'apd-c-pkg';
    if(String(c).indexOf('Περιγραφή')===0)return 'apd-c-desc';
    return '';
  }
  var COLCLS=COLS.map(colClass);
  var TOTAL_MERGE_COLS=['Μήνας','Ταμείο'];
  function totalMergeRange(){
    var idx=[];
    TOTAL_MERGE_COLS.forEach(function(c){var i=COLS.indexOf(c);if(i>=0)idx.push(i);});
    if(!idx.length){
      var m=COLS.indexOf('Μήνας');
      return m>=0?[m,1]:[null,0];
    }
    var s=Math.min.apply(null,idx),e=Math.max.apply(null,idx);
    return [s,e-s+1];
  }
  function renderTotalTds(cells){
    var mr=totalMergeRange(),ms=mr[0],span=mr[1];
    var label=String(cells['Μήνας']||cells['Ταμείο']||'').trim();
    var html='',i=0;
    while(i<COLS.length){
      if(ms!==null&&i===ms&&span>0){
        html+='<td colspan="'+span+'" class="apd-total-label">'+esc(label)+'</td>';
        i+=span;continue;
      }
      var cc=COLCLS[i];
      html+=cc?'<td class="'+cc+'">'+esc(cells[COLS[i]]||'')+'</td>':'<td>'+esc(cells[COLS[i]]||'')+'</td>';
      i++;
    }
    return html;
  }
  function render(rows){
    var ncols=COLS.length;
    var html='<table class="print-table apd-table">';
    html+=(DATA.colgroup||'');
    html+='<thead><tr>'+COLS.map(function(c,i){var cc=COLCLS[i];return cc?'<th class="'+cc+'">'+esc(c)+'</th>':'<th>'+esc(c)+'</th>';}).join('')+'</tr></thead><tbody>';
    rows.forEach(function(r){
      if(r.kind==='empty'){html+='<tr class="apd-year-gap" data-apd-kind="empty" aria-hidden="true"><td colspan="'+ncols+'"></td></tr>';return;}
      if(r.kind==='total'){
        html+='<tr class="apd-total-row" data-apd-kind="total">'+renderTotalTds(r.cells)+'</tr>';
        return;
      }
      var cls='apd-data-row'+(r.low?' apd-low':'');
      var tds=COLS.map(function(c,i){
        var cc=COLCLS[i];
        if(c==='Περικοπή'&&r.cut)cc=(cc+' apd-cut').replace(/^ /,'');
        return cc?'<td class="'+cc+'">'+esc(r.cells[c]||'')+'</td>':'<td>'+esc(r.cells[c]||'')+'</td>';
      }).join('');
      html+='<tr class="'+cls+'" data-apd-kind="data">'+tds+'</tr>';
    });
    html+='</tbody></table>';
    var wrap=mount.querySelector('.apd-table-scroll');
    if(!wrap){wrap=document.createElement('div');wrap.className='apd-table-scroll';wrap.id='apd-tables-wrapper';mount.innerHTML='';mount.appendChild(wrap);}
    wrap.innerHTML=html;
  }

  function updateLockedBar(){
    var cl=readCountLocked();
    var de=document.getElementById('apd-lock-dates'); if(de)de.textContent=fmtCountDateRange();
    var te=document.getElementById('apd-lock-tameio'); if(te)te.textContent=fmtLockedList(cl.tameio);
    var ke=document.getElementById('apd-lock-klados'); if(ke)ke.textContent=fmtLockedList(_ccLocked('klados'));
    var ae=document.getElementById('apd-lock-apodox'); if(ae)ae.textContent=fmtLockedList(cl.apodoxes);
  }

  function apply(){
    updateLockedBar();
    var P=readParams();
    render(computeRows(P));
  }

  window._liteFilterModalApply=window._liteFilterModalApply||{};
  window._liteFilterModalApply['apd-section']=apply;

  function syncApdFromCount(){ apply(); }
  window.addEventListener('atlas-count-klados-change',syncApdFromCount);
  window.addEventListener('atlas-count-filters-change',syncApdFromCount);
  var _csecApd=document.getElementById('count-section');
  if(_csecApd){_csecApd.addEventListener('change',syncApdFromCount);_csecApd.addEventListener('input',syncApdFromCount);}
  ['cnt-filter-from','cnt-filter-to'].forEach(function(id){
    var el=document.getElementById(id);if(el){el.addEventListener('input',syncApdFromCount);el.addEventListener('change',syncApdFromCount);}
  });

  // Listeners φίλτρων (μόνο ελεύθερα: πλαφόν, %, επισήμανση)
  ['apd-plafond','apd-retmode','apd-filter-pct','apd-filter-high','apd-totals-only'].forEach(function(id){
    var el=document.getElementById(id);if(!el)return;
    el.addEventListener('input',apply);el.addEventListener('change',apply);
  });
  var rb=document.getElementById('apd-filter-reset');
  if(rb)rb.addEventListener('click',function(){
    var pct=document.getElementById('apd-filter-pct');if(pct)pct.value='18';
    var hi=document.getElementById('apd-filter-high');if(hi)hi.value='21';
    var rm=document.getElementById('apd-retmode');if(rm)rm.value='all';
    var pl=document.getElementById('apd-plafond');if(pl)pl.value=DATA.defaultPlafond||'neos';
    var to=document.getElementById('apd-totals-only');if(to)to.checked=false;
    apply();
  });

  apply();
  window._atlasApdApply=apply;
})();
"""


# ---------------------------------------------------------------------------
# Συντάξιμες Αποδοχές (Pro) — μεταφορά από LOCAL_DEV/kyria/app_final.py
# Πηγή αλήθειας λογικής: _atlas_frag_tab_pension + βοηθητικές build_syntaksi_*
# ---------------------------------------------------------------------------

SYN_TAXI_HTML_COLUMNS = [
    "Έτος",
    "Σύνολο ημερών (μισθωτή)",
    "Συνολικές μικτές αποδοχές",
    "Συντ. αποδοχές",
    "Σύνολο ημερών (μη μισθωτή)",
    "Συνολικές εισφορές",
    "Κοινωνικοί Πόροι",
    "Τεκμαρτές αποδοχές",
    "Συνολικές αποδοχές",
    "ΔΤΚ",
    "Τελικές Συντ. Αποδοχές",
]

SYN_TAXI_HTML_COL_WIDTHS = {
    "Έτος": "4%",
    "Σύνολο ημερών (μισθωτή)": "9%",
    "Συνολικές μικτές αποδοχές": "10%",
    "Συντ. αποδοχές": "8%",
    "Σύνολο ημερών (μη μισθωτή)": "9%",
    "Συνολικές εισφορές": "9%",
    "Κοινωνικοί Πόροι": "7%",
    "Τεκμαρτές αποδοχές": "8%",
    "Συνολικές αποδοχές": "9%",
    "ΔΤΚ": "5%",
    "Τελικές Συντ. Αποδοχές": "11%",
}


def _syntaksi_apd_by_klados(df, klados_codes, plafond_mode=None):
    """Ετήσια σύνολα μισθωτή ΑΠΔ 2002+ ανά πακέτο: {code: {year: [days, gross, synt]}}.

    Άθροισμα ανά (code, year) ώστε ο client να αθροίζει για τα επιλεγμένα πακέτα
    (ισοδύναμο με _compute_apd_yearly_for_syntaksi_packages για το ίδιο σύνολο).
    plafond_mode: 'palios' / 'neos' / 'none' / None(auto) — για δυναμικό πλαφόν."""
    out = {}
    for code in klados_codes:
        try:
            im, mk, sy = _compute_apd_yearly_for_syntaksi_packages(
                df, {str(code)}, plafond_mode=plafond_mode
            )
        except Exception:
            im, mk, sy = {}, {}, {}
        years = set(im) | set(mk) | set(sy)
        if not years:
            continue
        per_year = {}
        for y in years:
            per_year[str(int(y))] = [
                float(im.get(y)) if im.get(y) is not None else None,
                float(mk.get(y)) if mk.get(y) is not None else None,
                float(sy.get(y)) if sy.get(y) is not None else None,
            ]
        if per_year:
            out[str(code)] = per_year
    return out


def _syntaksi_parallel_years_by_side(df) -> tuple[list[int], list[int]]:
    """Έτη (≤2016) παράλληλης ασφάλισης ανά πλευρά: (μισθωτού, ελ. επαγγελματία).

    Βασίζεται στην ίδια λογική εντοπισμού με τον πίνακα «Παράλληλη Ασφάλιση»."""
    misthoti_years: set[int] = set()
    elep_years: set[int] = set()
    try:
        _, month_groups = _parallel_month_groups_until_2016(df)
        if month_groups is None:
            return [], []
        for (year, _month), group in month_groups:
            y = int(year)
            if y > 2016:
                continue
            ika_d = float(group.loc[group["is_ika"], "Ημέρες"].sum())
            oaee_d = min(float(group.loc[group["is_oaee"], "Ημέρες"].sum()), 25)
            tsm_d = min(float(group.loc[group["is_tsm"], "Ημέρες"].sum()), 25)
            oga_d = min(float(group.loc[group["is_oga"], "Ημέρες"].sum()), 25)
            tsay_d = min(float(group.loc[group["is_tsay"], "Ημέρες"].sum()), 25)
            tsay_mis_d = float(
                group.loc[group.apply(_is_tsay_misthoti_parallel_row, axis=1), "Ημέρες"].sum()
            )
            tsay_elep_d = float(
                group.loc[group.apply(_is_tsay_non_misthoti_parallel_row, axis=1), "Ημέρες"].sum()
            )

            has_ika = ika_d > 0
            has_oaee = oaee_d > 0
            has_tsm = tsm_d > 0
            has_oga = oga_d > 0
            has_tsay = tsay_d > 0

            if not _parallel_until_2016_month_match(
                has_ika, has_oaee, has_tsm, has_oga, has_tsay
            ):
                continue
            if has_ika or tsay_mis_d > 0:
                misthoti_years.add(y)
            if has_oaee or has_tsm or has_oga or tsay_elep_d > 0:
                elep_years.add(y)
    except Exception:
        return [], []
    return sorted(misthoti_years), sorted(elep_years)


def _syntaksi_build_payload(df, description_map):
    """Δεδομένα για τον client engine της καρτέλας Συντάξιμες (embedded JSON)."""
    desc_map = description_map or {}
    count_df = filter_count_df(df)
    c_df = build_count_c_dataframe(count_df, desc_map)

    cdf_rows = []
    if c_df is not None and not getattr(c_df, "empty", True):
        for _, r in c_df.iterrows():
            try:
                cdf_rows.append({
                    "y": int(r["ΕΤΟΣ"]),
                    "m": int(r["Μήνας_Num"]),
                    "t": str(r.get("ΤΑΜΕΙΟ", "") or ""),
                    "k": str(r.get("ΤΥΠΟΣ ΑΣΦΑΛΙΣΗΣ", "") or ""),
                    "e": str(r.get("ΕΡΓΟΔΟΤΗΣ", "") or ""),
                    "p": str(r.get("ΚΛΑΔΟΣ/ΠΑΚΕΤΟ", "") or "").strip(),
                    "a": str(r.get("ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ", "") or ""),
                    "d": float(r.get("Ημέρες", 0) or 0),
                    "g": float(r.get("Μικτές_Part", 0) or 0),
                    "c": float(r.get("Εισφορές_Part", 0) or 0),
                })
            except Exception:
                continue

    # Κωδικοί πακέτων (από καταμέτρηση) → ΑΠΔ ανά πακέτο
    klados_codes = []
    if "Κλάδος/Πακέτο Κάλυψης" in count_df.columns:
        klados_codes = sorted(
            count_df["Κλάδος/Πακέτο Κάλυψης"].dropna().astype(str).str.strip().unique().tolist()
        )
    # ΑΠΔ ανά πακέτο για ΚΑΘΕ mode πλαφόν (δυναμικός συγχρονισμός με το φίλτρο «Πλαφόν» της ΑΠΔ)
    apd_by_klados_modes = {
        "palios": _syntaksi_apd_by_klados(df, klados_codes, plafond_mode="palios"),
        "neos": _syntaksi_apd_by_klados(df, klados_codes, plafond_mode="neos"),
        "none": _syntaksi_apd_by_klados(df, klados_codes, plafond_mode="none"),
    }
    # Προεπιλογή πλαφόν: παλιού αν εγγραφή πριν 1/1/1993, αλλιώς νέου (όπως η ΑΠΔ)
    try:
        _is_palios_default = bool(_apd_is_palios(df))
    except Exception:
        _is_palios_default = False
    apd_plafond_default = "palios" if _is_palios_default else "neos"
    # Συμβατότητα: το προεπιλεγμένο variant ως apdByKlados (αν δεν διαβαστεί το #apd-plafond)
    apd_by_klados = apd_by_klados_modes[apd_plafond_default]

    klados_labels = {}
    for code in klados_codes:
        d = desc_map.get(code, "")
        klados_labels[code] = f"{code} - {d}" if d else code

    # ΔΤΚ
    dtk_doc = _load_dtk_table_json()
    dtk_data = (dtk_doc or {}).get("data") or {}
    dtk_clean = {}
    for ref_y, row in dtk_data.items():
        if not isinstance(row, dict):
            continue
        inner = {}
        for cy, v in row.items():
            try:
                inner[str(int(cy))] = float(v)
            except (TypeError, ValueError):
                continue
        dtk_clean[str(ref_y).strip()] = inner
    ref_opts = sorted({int(k) for k in dtk_clean.keys() if str(k).isdigit()})
    ref_strs = [str(x) for x in ref_opts] if ref_opts else ["2026"]
    dtk_ref_default = "2026" if "2026" in ref_strs else (ref_strs[-1] if ref_strs else "2026")

    # Κοινωνικοί πόροι
    koin = {str(int(y)): {k: float(v) for k, v in row.items()} for y, row in koinwnikoi_table.items()}

    # ΟΓΑ κλιμακούμενα ποσοστά (breakpoints 2014..2022, clamp στον client)
    oga_rates = {str(y): float(_syntaksi_oga_tekmark_rate_decimal(y)) for y in range(2014, 2023)}

    this_year = datetime.date.today().year
    exagora_year_opts = [str(y) for y in range(2002, this_year + 1)]

    # Έτη (≤2016) με εντοπισμένη παράλληλη ασφάλιση από τον σχετικό πίνακα
    parallel_years = []
    parallel_years_misthoti, parallel_years_elep = _syntaksi_parallel_years_by_side(df)
    try:
        _par_res = build_parallel_print_df(df, desc_map, False)
        _par_df = _par_res[0] if isinstance(_par_res, tuple) else _par_res
        if _par_df is not None and not getattr(_par_df, "empty", True) and "Έτος" in _par_df.columns:
            _yrs = set()
            for _v in _par_df["Έτος"].tolist():
                try:
                    _yrs.add(int(str(_v).strip()))
                except (TypeError, ValueError):
                    continue
            parallel_years = sorted(y for y in _yrs if y <= 2016)
    except Exception:
        parallel_years = []
    if not parallel_years and (parallel_years_misthoti or parallel_years_elep):
        parallel_years = sorted(set(parallel_years_misthoti) | set(parallel_years_elep))

    return {
        "cols": list(SYN_TAXI_HTML_COLUMNS),
        "colWidths": dict(SYN_TAXI_HTML_COL_WIDTHS),
        "cdfRows": cdf_rows,
        "apdByKlados": apd_by_klados,
        "apdByKladosModes": apd_by_klados_modes,
        "apdPlafondDefault": apd_plafond_default,
        "kladosLabels": klados_labels,
        "dtk": dtk_clean,
        "dtkRefOptions": ref_strs,
        "dtkRefDefault": dtk_ref_default,
        "koin": koin,
        "koinTypes": ["ΟΧΙ", "ΔΙΚΗΓΟΡΟΙ", "ΟΑΕΕ", "ΤΣΜΕΔΕ"],
        "tekOptions": list(SYN_TEKMARK_RATE_LABELS),
        "tekDefault": SYN_TEKMARK_RATE_DEFAULT,
        "ogaLabel": SYN_TEKMARK_OGA_LABEL,
        "ogaRates": oga_rates,
        "yearFromDefault": "2002",
        "yearToDefault": str(this_year),
        "exagoraYearOptions": exagora_year_opts,
        "exagoraYearDefault": "2026" if "2026" in exagora_year_opts else exagora_year_opts[-1],
        "calcFromOptions": [str(y) for y in range(2002, 1974, -1)],
        "calcFromDefault": "2002",
        "hideTab": bool(df_has_tsmede_misthoti_insurance(df)),
        "yearDays": 300.0,
        "parallelYears": parallel_years,
        "parallelYearsMisthoti": parallel_years_misthoti,
        "parallelYearsElep": parallel_years_elep,
    }


def build_syntaksi_with_filters(df, description_map=None):
    """Κύρια καρτέλα «Συντάξιμες Αποδοχές» (Pro): client-side επανυπολογισμός
    συγχρονισμένος με τα φίλτρα Καταμέτρησης (επιλεγμένα πακέτα κάλυψης)."""
    if df is None or getattr(df, "empty", True):
        return ""
    payload = _syntaksi_build_payload(df, description_map)
    _has_par16 = bool(
        payload.get("parallelYears")
        or payload.get("parallelYearsMisthoti")
        or payload.get("parallelYearsElep")
    )
    return _build_syntaksi_tab_html(
        payload,
        prefix="syntaksi",
        tab_id="syntaksi",
        title="Συντάξιμες Αποδοχές",
        parallel_only=False,
        par_exclude_until2016=_has_par16,
        include_engine=True,
    )


def build_syntaksi_parallel_with_filters(df, description_map=None, payload=None):
    """Καρτέλα «Συντάξιμες Παραλ.»: πανομοιότυπη με τη «Συντάξιμες», αλλά εμφανίζει
    μόνο τα έτη (έως 2016) με εντοπισμένη παράλληλη ασφάλιση. Υπολογισμοί/σύνολα/metrics
    ίδια με την κύρια καρτέλα. Επιστρέφει "" αν δεν υπάρχει παράλληλη ≤2016."""
    if df is None or getattr(df, "empty", True):
        return ""
    if payload is None:
        payload = _syntaksi_build_payload(df, description_map)
    if not (
        payload.get("parallelYears")
        or payload.get("parallelYearsMisthoti")
        or payload.get("parallelYearsElep")
    ):
        return ""
    return _build_syntaksi_tab_html(
        payload,
        prefix="syntaksipar",
        tab_id="syntaksipar",
        title="Συντάξιμες αποδοχές παράλληλης ασφάλισης",
        parallel_only=True,
        include_engine=False,
    )


def _build_syntaksi_tab_html(
    payload, *, prefix, tab_id, title, parallel_only,
    par_exclude_until2016=False, include_engine,
):
    """Παράγει το HTML μιας καρτέλας Συντάξιμων για συγκεκριμένο id-prefix.
    Ο ίδιος client engine (window.__atlasSyntaksiInit) οδηγεί κάθε instance μέσω CFG."""
    show_par_dropdown = parallel_only or par_exclude_until2016
    payload_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    payload_html = (
        f'<script type="application/json" id="atlas-{prefix}-data-json">{payload_json}</script>'
    )

    # Metrics bar (πακέτα + 3 μετρήσεις)
    metrics_html = (
        f"{payload_html}"
        f'<div class="totals-info-bar syntaksi-metrics atlas-header-split" id="{prefix}-metrics-wrap">'
        '<div class="atlas-header-info">'
        '<div class="atlas-info-box">'
        '<div class="atlas-info-box-title">Επιλεγμένα πακέτα κάλυψης</div>'
        f'<div class="atlas-info-box-body syntaksi-metrics-pk-txt" id="{prefix}-metrics-pk">—</div>'
        "</div></div>"
        f'{build_atlas_metrics_frame_html("".join([_atlas_metric_cell_html("Μήνες", "•", f"{prefix}-metric-months"), _atlas_metric_cell_html("Συντάξιμες αποδοχές", "•", f"{prefix}-metric-apod"), _atlas_metric_cell_html("Συντάξιμος μισθός", "•", f"{prefix}-metric-mis")]))}'
        "</div>"
    )

    # Φίλτρα — μόνο τοπικά (διάστημα/πακέτα/ταμείο από Καταμέτρηση)
    ref_opts_html = "".join(
        f'<option value="{html_mod.escape(o)}"'
        f'{" selected" if o == payload["dtkRefDefault"] else ""}>{html_mod.escape(o)}</option>'
        for o in payload["dtkRefOptions"]
    )
    ex_year_opts_html = "".join(
        f'<option value="{html_mod.escape(o)}"'
        f'{" selected" if o == payload["exagoraYearDefault"] else ""}>{html_mod.escape(o)}</option>'
        for o in payload["exagoraYearOptions"]
    )
    koin_opts_html = "".join(
        f'<option value="{html_mod.escape(o)}">{html_mod.escape(o)}</option>'
        for o in payload["koinTypes"]
    )
    tek_opts_html = "".join(
        f'<option value="{html_mod.escape(o)}"'
        f'{" selected" if o == payload["tekDefault"] else ""}>{html_mod.escape(o)}</option>'
        for o in payload["tekOptions"]
    )
    calc_from_opts_html = "".join(
        f'<option value="{html_mod.escape(o)}"'
        f'{" selected" if o == payload["calcFromDefault"] else ""}>{html_mod.escape(o)}</option>'
        for o in payload["calcFromOptions"]
    )
    par_mode_field = ""
    filters_grid_cls = "syntaksi-filters-grid"
    if parallel_only:
        filters_grid_cls += " syntaksi-filters-grid--parallel syntaksi-filters-grid--no-tek"
    elif show_par_dropdown:
        filters_grid_cls += " syntaksi-filters-grid--parallel"
    if show_par_dropdown:
        par_mode_field = (
            '<label class="apd-filter-field syntaksi-fld-par-mode">'
            '<span class="apd-filter-field-label">Παράλληλη</span>'
            f'<select id="{prefix}-par-mode" class="apd-filter-input apd-select">'
            '<option value="misthoti" selected>Παράλληλη Μισθωτού</option>'
            '<option value="elep">Παράλληλη ελ. επαγγελματία</option>'
            "</select></label>"
        )
    tek_field = ""
    if not parallel_only:
        tek_field = (
            '<label class="apd-filter-field syntaksi-fld-tek"><span class="apd-filter-field-label">Αναγωγή εισφορών</span>'
            f'<select id="{prefix}-tek" class="apd-filter-input apd-select">{tek_opts_html}</select></label>'
        )
    filter_bar = (
        f'<div class="count-filters syntaksi-filters" id="{prefix}-filters-bar">'
        f'<div class="atlas-locked-count-bar" id="{prefix}-locked-from-count">'
        '<div class="atlas-locked-count-title">Από Καταμέτρηση</div>'
        '<div class="atlas-locked-count-grid">'
        '<div class="atlas-locked-count-item"><span class="atlas-locked-count-sub">Διάστημα</span>'
        f'<span class="atlas-locked-count-val" id="{prefix}-lock-dates">—</span></div>'
        '<div class="atlas-locked-count-item"><span class="atlas-locked-count-sub">Ταμείο</span>'
        f'<span class="atlas-locked-count-val" id="{prefix}-lock-tameio">—</span></div>'
        '</div></div>'
        f'<div class="{filters_grid_cls}">'
        f"{par_mode_field}"
        '<label class="apd-filter-field"><span class="apd-filter-field-label">Υπολογισμός Από</span>'
        f'<select id="{prefix}-calc-from" class="apd-filter-input apd-select" '
        f'title="Από αυτό το έτος: ΣΥΝΟΛΟ, μήνες, συντάξιμες (η εξαγορά πάντα)">{calc_from_opts_html}</select></label>'
        '<label class="apd-filter-field"><span class="apd-filter-field-label">Έτος αναφοράς ΔΤΚ</span>'
        f'<select id="{prefix}-dtk-ref" class="apd-filter-input apd-select">{ref_opts_html}</select></label>'
        '<label class="apd-filter-field"><span class="apd-filter-field-label">Ποσό εξαγοράς</span>'
        f'<input type="text" id="{prefix}-exagora-poso" class="apd-filter-input" '
        'placeholder="π.χ. 15.000,00 €" autocomplete="off"></label>'
        '<label class="apd-filter-field"><span class="apd-filter-field-label">Ημέρες εξαγοράς</span>'
        f'<input type="text" id="{prefix}-exagora-imres" class="apd-filter-input" '
        'placeholder="π.χ. 300" autocomplete="off"></label>'
        '<label class="apd-filter-field"><span class="apd-filter-field-label">Έτος εξαγοράς</span>'
        f'<select id="{prefix}-exagora-etos" class="apd-filter-input apd-select">{ex_year_opts_html}</select></label>'
        '<label class="apd-filter-field"><span class="apd-filter-field-label">Κοινωνικοί Πόροι</span>'
        f'<select id="{prefix}-koin" class="apd-filter-input apd-select">{koin_opts_html}</select></label>'
        f"{tek_field}"
        "</div></div>"
    )

    info_sections = [
        ("info", "Διάστημα, ταμείο και πακέτα κάλυψης ακολουθούν αυτόματα τα φίλτρα της Καταμέτρησης."),
        ("info", "Πριν 2002: ημέρες μισθωτή & μικτές από Καταμέτρηση. Από 2002+: μισθωτής "
                 "από ΑΠΔ για τα ίδια πακέτα· μη μισθωτής / εισφορές από Καταμέτρηση."),
        ("info", "Τεκμαρτές = (εισφορές + κοιν. πόροι) ÷ ποσοστό. "
                 "Συνολικές αποδοχές = Συντ. αποδοχές + τεκμαρτές. Τελικές = Συνολικές × ΔΤΚ."),
    ]
    if parallel_only:
        info_sections.insert(0, (
            "info",
            "Επιλέξτε «Παράλληλη Μισθωτού» ή «Παράλληλη ελ. επαγγελματία». "
            "Εμφανίζονται μόνο τα σχετικά έτη (έως 2016)· τα σύνολα και τα metrics "
            "αφορούν αποκλειστικά τις στήλες της επιλεγμένης πλευράς. "
            "Η αναγωγή εισφορών είναι σταθερά 20% (κύρια σύνταξη).",
        ))
        info_sections[3] = (
            "info",
            "Τεκμαρτές = (εισφορές + κοιν. πόροι) ÷ 20%. "
            "Συνολικές αποδοχές = Συντ. αποδοχές + τεκμαρτές. Τελικές = Συνολικές × ΔΤΚ.",
        )
    elif par_exclude_until2016:
        info_sections.insert(0, (
            "info",
            "Επιλέξτε «Παράλληλη Μισθωτού» ή «Παράλληλη ελ. επαγγελματία»: "
            "στις παράλληλες χρονιές έως 2016 οι στήλες της επιλεγμένης πλευράς "
            "εξαιρούνται από υπολογισμούς — συμπληρωματικά με την καρτέλα "
            "«Συντάξιμες αποδοχές παράλληλης ασφάλισης» που τις περιλαμβάνει. "
            "Από 2017+ εμφανίζονται και οι δύο τύποι ασφάλισης· "
            "οι ημέρες ασφάλισης ανά έτος δεν υπερβαίνουν αθροιστικά τις 300.",
        ))
    heading = _atlas_html_tab_heading_row_info(
        title,
        f"Πληροφορίες — {title}",
        info_sections,
        f"atlas-info-store-{prefix}",
    )

    if parallel_only:
        description_html = (
            '<p class="print-description">Συντάξιμες αποδοχές για έτη (έως 2016) με παράλληλη '
            "ασφάλιση, ανά πλευρά (μισθωτού / ελ. επαγγελματία). Τα σύνολα και τα metrics "
            "αφορούν μόνο τις στήλες της επιλεγμένης πλευράς.</p>"
        )
        empty_msg = (
            f'<div class="syntaksi-empty" id="{prefix}-empty">'
            "Επιλέξτε πακέτα κάλυψης στην καρτέλα <strong>Καταμέτρηση</strong> "
            "για να γεμίσει ο πίνακας.</div>"
        )
    else:
        description_html = (
            '<p class="print-description">Συντάξιμες αποδοχές ανά έτος για τα επιλεγμένα '
            "πακέτα κάλυψης, με αναγωγή εισφορών, κοινωνικούς πόρους, ΔΤΚ και εξαγορά.</p>"
        )
        empty_msg = (
            f'<div class="syntaksi-empty" id="{prefix}-empty">'
            "Επιλέξτε πακέτα κάλυψης στην καρτέλα <strong>Καταμέτρηση</strong> "
            "για να γεμίσει ο πίνακας.</div>"
        )

    body_html = (
        f'<button type="button" class="btn-json-syntaksi" id="{prefix}-json-dl" '
        'disabled hidden>JSON για Syntaksi Pro 3</button>'
        f"{empty_msg}"
        f'<div class="syntaksi-table-scroll" id="{prefix}-table-mount" hidden></div>'
    )

    init_call = (
        f"window.__atlasSyntaksiInit({{prefix:'{prefix}',tab:'{tab_id}',"
        f"parallelOnly:{'true' if parallel_only else 'false'},"
        f"parExcludeUntil2016:{'true' if par_exclude_until2016 else 'false'}}});"
    )
    if include_engine:
        scripts_html = f"<script>{_build_syntaksi_filter_js()}\n{init_call}</script>"
    else:
        scripts_html = f"<script>{init_call}</script>"

    return _build_tab_page(
        section_id=f"{prefix}-section",
        extra_section_classes="syntaksi-layout",
        heading_html=heading,
        description_html=description_html,
        metrics_html=metrics_html,
        filters_html=filter_bar,
        body_html=body_html,
        scripts_html=scripts_html,
    )


def _build_syntaksi_filter_js():
    """JS: πλήρης αγωγός Συντάξιμων (ίδια λογική με LOCAL_DEV/kyria/app_final.py),
    συγχρονισμένος με τα φίλτρα Καταμέτρησης (επιλεγμένα πακέτα + λοιπά φίλτρα)."""
    return r"""
window.__atlasSyntaksiInit=window.__atlasSyntaksiInit||function(CFG){
  CFG=CFG||{};
  var PFX=CFG.prefix||'syntaksi';
  var TAB=CFG.tab||PFX;
  var PARONLY=!!CFG.parallelOnly;
  var PAREXCLUDE16=!!CFG.parExcludeUntil2016;
  var HASPARDROPDOWN=PARONLY||PAREXCLUDE16;
  var sec=document.getElementById(PFX+'-section');
  if(!sec)return;
  var dataEl=document.getElementById('atlas-'+PFX+'-data-json');
  if(!dataEl)return;
  var DATA={};
  try{DATA=JSON.parse(dataEl.textContent||'{}');}catch(e){return;}
  var COLS=DATA.cols||[];
  var COLW=DATA.colWidths||{};
  var CDF=DATA.cdfRows||[];
  var APDK_MODES=DATA.apdByKladosModes||{};
  var APD_DEFAULT_MODE=DATA.apdPlafondDefault||'neos';
  var APDK=DATA.apdByKlados||(APDK_MODES[APD_DEFAULT_MODE]||{});
  var KLABELS=DATA.kladosLabels||{};
  var DTK=DATA.dtk||{};
  var KOIN=DATA.koin||{};
  var OGA=DATA.ogaRates||{};
  var OGALABEL=DATA.ogaLabel||'';
  var YEARDAYS=parseFloat(DATA.yearDays)||300;
  var PARYEARS={};(DATA.parallelYears||[]).forEach(function(y){PARYEARS[String(y)]=1;});
  var TEK_LABEL_FIXED=PARONLY?(String(DATA.tekDefault||'').trim()||'20% — Κυρία σύνταξη'):'';

  function resolveTekLabel(){
    if(PARONLY)return TEK_LABEL_FIXED;
    return val(PFX+'-tek');
  }

  function currentParMode(){
    if(!HASPARDROPDOWN)return 'misthoti';
    var el=document.getElementById(PFX+'-par-mode');
    var v=el?String(el.value||'').trim():'misthoti';
    return v==='elep'?'elep':'misthoti';
  }
  function activeParYears(){
    return PARYEARS;
  }
  function recomputeSynTotals(row){
    var dtk=row.dtk;
    var hasApod=(row.synt!=null&&!isNaN(row.synt))||(row.tek!=null&&!isNaN(row.tek));
    var syn=hasApod?(row.synt||0)+(row.tek||0):null;
    return {
      synolikes:syn,
      telikes:(syn!=null&&dtk!=null&&!isNaN(dtk))?syn*dtk:null
    };
  }
  function applyParSide(row,mode){
    if(!PARONLY||!row||typeof row.year!=='number')return row;
    var dtk=row.dtk;
    if(mode==='misthoti'){
      var synt=(row.synt!=null&&!isNaN(row.synt))?row.synt:null;
      return {
        year:row.year,dm:row.dm,dnm:null,gross:row.gross,synt:synt,contrib:null,
        koin:null,tek:null,synolikes:synt,dtk:dtk,
        telikes:(synt!=null&&dtk!=null&&!isNaN(dtk))?synt*dtk:null
      };
    }
    var tek=(row.tek!=null&&!isNaN(row.tek))?row.tek:null;
    return {
      year:row.year,dm:null,dnm:row.dnm,gross:null,synt:null,contrib:row.contrib,
      koin:row.koin,tek:tek,synolikes:tek,dtk:dtk,
      telikes:(tek!=null&&dtk!=null&&!isNaN(dtk))?tek*dtk:null
    };
  }
  function zeroParSide(row,mode){
    var out;
    if(mode==='misthoti'){
      out={
        year:row.year,dm:null,dnm:row.dnm,gross:null,synt:null,
        contrib:row.contrib,koin:row.koin,tek:row.tek,dtk:row.dtk
      };
    }else{
      out={
        year:row.year,dm:row.dm,dnm:null,gross:row.gross,synt:row.synt,
        contrib:null,koin:null,tek:null,dtk:row.dtk
      };
    }
    var st=recomputeSynTotals(out);
    out.synolikes=st.synolikes;
    out.telikes=st.telikes;
    return out;
  }
  function applyParExcludeUntil2016(row,mode){
    if(!PAREXCLUDE16||!row||typeof row.year!=='number')return row;
    if(!PARYEARS[String(row.year)])return row;
    return zeroParSide(row,mode);
  }
  function adjustCoreForParallel(fullCore){
    if(!PARONLY&&!PAREXCLUDE16)return fullCore;
    var mode=currentParMode();
    if(PARONLY){
      return (fullCore||[]).filter(function(r){
        return typeof r.year==='number'&&!!PARYEARS[String(r.year)];
      }).map(function(r){return applyParSide(r,mode);});
    }
    return (fullCore||[]).map(function(r){return applyParExcludeUntil2016(r,mode);});
  }

  var CUR_YEARS=['Συνολικές μικτές αποδοχές','Συντ. αποδοχές','Συνολικές εισφορές','Κοινωνικοί Πόροι','Τεκμαρτές αποδοχές','Συνολικές αποδοχές','Τελικές Συντ. Αποδοχές'];
  var DAY_COLS=['Σύνολο ημερών (μισθωτή)','Σύνολο ημερών (μη μισθωτή)'];

  // ---------- formatting ----------
  function fmtCurr(n){
    if(n===null||n===undefined||isNaN(n)||n===0)return '';
    var neg=n<0; var s=Math.abs(n).toFixed(2);
    var p=s.split('.');
    p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.');
    return (neg?'-':'')+p[0]+','+p[1]+' €';
  }
  function fmtDays(n){
    if(n===null||n===undefined||isNaN(n)||n===0)return '';
    var v=Number(n);
    if(Math.abs(v-Math.round(v))<0.01){
      return String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
    }
    var s=v.toFixed(1);
    var p=s.split('.');
    p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.');
    return p[0]+','+p[1];
  }
  function fmtDtk(n){
    if(n===null||n===undefined||isNaN(n)||n===0)return '';
    var s=Number(n).toFixed(5);
    var p=s.split('.');
    p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.');
    return p[0]+','+p[1];
  }
  function fmtNum1(n){
    if(n===null||n===undefined||isNaN(n))return '•';
    var s=Number(n).toFixed(1);
    var p=s.split('.');
    p[0]=p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.');
    return p[0]+','+p[1];
  }
  function esc(s){var d=document.createElement('div');d.textContent=(s==null?'':s);return d.innerHTML;}

  // Πιστή μεταφορά του clean_numeric_value (app_final.py): υπόθεση «αγγλικού» format
  // (κόμμα=χιλιάδες, τελεία=δεκαδικά). exclude_drx=True. Επιστρέφει αριθμό (0.0 σε αποτυχία).
  function cleanNumericValue(value){
    if(value===null||value===undefined)return 0.0;
    var s=String(value).trim();
    if(s===''||s==='-')return 0.0;
    var neg=false;
    s=s.replace(/\u2212/g,'-');
    if(s.charAt(0)==='('&&s.charAt(s.length-1)===')'){neg=true;s=s.slice(1,-1).trim();}
    if(s.charAt(s.length-1)==='-'){neg=true;s=s.slice(0,-1).trim();}
    if(s.charAt(0)==='-'){neg=true;s=s.slice(1).trim();}
    if(s.indexOf('ΔΡΧ')!==-1)return 0.0;
    s=s.replace(/ΔΡΧ/g,'').replace(/€/g,'').replace(/ /g,'');
    s=s.replace(/[a-zA-Zα-ωΑ-Ω]/g,'');
    s=s.trim();
    if(!s||s==='-')return 0.0;
    if(s.indexOf(',')!==-1&&s.indexOf('.')!==-1){
      s=s.replace(/,/g,'');
    }else if(s.indexOf(',')!==-1){
      var parts=s.split(',');
      if(parts.length===2){
        if(parts[1].length===3&&/^\d+$/.test(parts[1]))s=s.replace(/,/g,'');
        else if(parts[1].length<=2)s=s.replace(/,/g,'.');
        else s=s.replace(/,/g,'');
      }else{s=s.replace(/,/g,'');}
    }
    var r=parseFloat(s);
    if(isNaN(r))return 0.0;
    return neg?-r:r;
  }
  // ποσό εξαγοράς: κενό → null, αλλιώς clean_numeric_value
  function parsePoso(raw){
    var t=String(raw==null?'':raw).trim();
    if(!t)return null;
    return cleanNumericValue(t);
  }
  // ημέρες εξαγοράς: float(t.replace(',','.').replace(' ','')) — κενό/άκυρο → null
  function parseImeres(raw){
    var t=String(raw==null?'':raw).trim();
    if(!t)return null;
    var n=parseFloat(t.replace(/,/g,'.').replace(/ /g,''));
    return isNaN(n)?null:n;
  }

  // ---------- classification / caps (ίδιο με Καταμέτρηση) ----------
  function insKindCls(typos){
    var s=String(typos||'').trim().toUpperCase().replace(/\s+/g,' ');
    if(!s)return null;
    if(/ΜΗ\s*ΜΙΣΘΩΤ/.test(s))return 'ΜΗ ΜΙΣΘΩΤΗ';
    if(s.indexOf('NON')!==-1&&s.indexOf('SAL')!==-1)return 'ΜΗ ΜΙΣΘΩΤΗ';
    if(s.indexOf('ΜΙΣΘΩΤΗ')!==-1&&s.indexOf('ΜΗ ΜΙΣΘΩΤΗ')===-1&&s.indexOf('ΜΗ ')!==0)return 'ΜΙΣΘΩΤΗ';
    return null;
  }
  function capForT(t){
    var u=String(t||'').toUpperCase();
    return (u.indexOf('ΙΚΑ')!==-1||u.indexOf('IKA')!==-1)?31:25;
  }
  function yearKindDays(rows,year,kindCode){
    var sub=rows.filter(function(r){return r.y===year;});
    if(kindCode){sub=sub.filter(function(r){return insKindCls(r.k)===kindCode;});}
    if(sub.length===0)return 0;
    var g={};
    sub.forEach(function(r){var key=String(r.t||'')+'|'+r.m;g[key]=(g[key]||0)+(+r.d||0);});
    var byM={};
    Object.keys(g).forEach(function(key){
      var parts=key.split('|');var tn=parts[0];var mi=parts[1];
      var cap=capForT(tn);var raw=g[key];var c=raw<cap?raw:cap;
      byM[mi]=(byM[mi]||0)+c;
    });
    var s=0;Object.keys(byM).forEach(function(mi){s+=byM[mi];});
    return s;
  }

  // ---------- ΔΤΚ / ΟΓΑ / κοιν. πόροι / αναγωγή ----------
  function dtkLookup(refKey,year){
    var r=DTK[String(refKey).trim()];
    if(!r)return null;
    var v=r[String(year)];
    return (v===null||v===undefined||v==='')?null:Number(v);
  }
  function ogaRate(year){
    var y=parseInt(year,10);
    if(y<=2014)return OGA['2014'];
    if(y>=2022)return OGA['2022'];
    return OGA[String(y)];
  }
  function fixedRate(label){
    var s=String(label||'');
    if(s.indexOf('4%')===0)return 0.04;
    if(s.indexOf('6%')===0)return 0.06;
    return 0.20;
  }
  function rateForYear(label,year){
    if(label===OGALABEL)return ogaRate(year);
    return fixedRate(label);
  }
  function koinValue(type,year,dnm){
    if(!type||type==='ΟΧΙ')return null;
    if(['ΔΙΚΗΓΟΡΟΙ','ΟΑΕΕ','ΤΣΜΕΔΕ'].indexOf(type)===-1)return null;
    var y=parseInt(year,10);
    if(y<2002||y>2016)return null;
    var row=KOIN[String(y)];
    if(!row)return null;
    var base=row[type];
    if(base===null||base===undefined)return null;
    if(dnm===null||dnm===undefined||isNaN(dnm)||dnm===0)return null;
    var v=(Number(base)/25.0)*Number(dnm);
    return Math.abs(v)<1e-9?null:v;
  }

  // ---------- count filter state ----------
  function collectCount(key){
    var out=[],seen={};
    function add(cb){
      if(!cb||cb.type!=='checkbox'||!cb.checked)return;
      if((cb.getAttribute('data-attr')||'')!==key)return;
      if(seen[cb.value])return;seen[cb.value]=1;out.push(cb.value);
    }
    var csec=document.getElementById('count-section');
    if(csec)csec.querySelectorAll('.filter-modal-group[data-filter-key="'+key+'"] input[type="checkbox"]').forEach(add);
    var m=document.getElementById('lite-filter-modal-options-mount');
    if(m)m.querySelectorAll('input[type="checkbox"]').forEach(add);
    return out;
  }
  function cntParseDateYear(s,fallback){
    if(!s)return fallback;
    var t=String(s).trim();if(!t)return fallback;
    var m3=t.match(/^(\d{1,2})[./](\d{1,2})[./](\d{4})$/);
    if(m3)return parseInt(m3[3],10);
    var m2=t.match(/^(\d{1,2})[./](\d{4})$/);
    if(m2)return parseInt(m2[2],10);
    var y=parseInt(t,10);
    if(!isNaN(y)&&y>=1000&&y<=9999)return y;
    return fallback;
  }
  function getCountState(){
    var fromEl=document.getElementById('cnt-filter-from');
    var toEl=document.getElementById('cnt-filter-to');
    return {
      tameio:collectCount('tameio'),
      typos:collectCount('typos'),
      employer:collectCount('employer'),
      klados:collectCount('klados'),
      apodoxes:collectCount('apodoxes'),
      fromY:cntParseDateYear(fromEl&&fromEl.value,0),
      toY:cntParseDateYear(toEl&&toEl.value,9999)
    };
  }
  function fmtCountDateRange(){
    var fromEl=document.getElementById('cnt-filter-from');
    var toEl=document.getElementById('cnt-filter-to');
    var f=(fromEl&&fromEl.value||'').trim();
    var t=(toEl&&toEl.value||'').trim();
    if(!f&&!t)return 'Όλα';
    if(f&&!t)return 'Από '+f;
    if(!f&&t)return 'Έως '+t;
    return f+' — '+t;
  }
  function fmtLockedList(arr){
    if(!arr||!arr.length)return 'Όλα';
    return arr.join(', ');
  }
  function cdfYearBounds(){
    if(!CDF||!CDF.length){
      var ny=new Date().getFullYear();
      return {min:ny,max:ny};
    }
    var lo=CDF[0].y, hi=CDF[0].y;
    CDF.forEach(function(r){
      if(r.y<lo)lo=r.y;
      if(r.y>hi)hi=r.y;
    });
    return {min:lo,max:hi};
  }
  function yearRangeFromCount(cs){
    var nowY=new Date().getFullYear();
    var b=cdfYearBounds();
    var lo=(cs.fromY>0)?cs.fromY:b.min;
    var hi=(cs.toY<9999)?cs.toY:Math.max(b.max,nowY);
    if(lo>hi){var tmp=lo;lo=hi;hi=tmp;}
    return {lo:lo,hi:hi};
  }
  function setLockedFromCount(cs){
    var de=document.getElementById(PFX+'-lock-dates');
    if(de)de.textContent=fmtCountDateRange();
    var te=document.getElementById(PFX+'-lock-tameio');
    if(te)te.textContent=fmtLockedList(cs.tameio);
  }
  // Δυναμικό πλαφόν: ακολουθεί το φίλτρο «Πλαφόν» της καρτέλας ΑΠΔ (#apd-plafond)
  function currentApdMode(){
    var el=document.getElementById('apd-plafond');
    var v=el?String(el.value||'').trim():'';
    if(v==='palios'||v==='neos'||v==='none')return v;
    return APD_DEFAULT_MODE;
  }
  function apdMapForMode(){
    var m=currentApdMode();
    return APDK_MODES[m]||APDK_MODES[APD_DEFAULT_MODE]||APDK||{};
  }

  // ---------- core compute (ίδια ροή με _atlas_frag_tab_pension) ----------
  function computeCore(selCodes,lo,hi,cs,dtkRef,kpType,tekLabel,apdMap){
    apdMap=apdMap||apdMapForMode();
    var fr=CDF.filter(function(r){
      if(r.y<cs.fromY||r.y>cs.toY)return false;
      if(cs.tameio.length&&cs.tameio.indexOf(r.t)===-1)return false;
      if(cs.typos.length&&cs.typos.indexOf(r.k)===-1)return false;
      if(cs.employer.length&&cs.employer.indexOf(r.e)===-1)return false;
      if(cs.klados.length&&cs.klados.indexOf(r.p)===-1)return false;
      if(cs.apodoxes.length&&cs.apodoxes.indexOf(r.a)===-1)return false;
      return true;
    });
    var baseYears={};fr.forEach(function(r){baseYears[r.y]=1;});
    var base={};
    Object.keys(baseYears).forEach(function(ys){
      var y=parseInt(ys,10);
      var gross=0,contrib=0;
      fr.forEach(function(r){
        if(r.y!==y)return;
        var c=insKindCls(r.k);
        if(c==='ΜΙΣΘΩΤΗ')gross+=(+r.g||0);
        else if(c==='ΜΗ ΜΙΣΘΩΤΗ')contrib+=(+r.c||0);
      });
      base[y]={dm:yearKindDays(fr,y,'ΜΙΣΘΩΤΗ'),dnm:yearKindDays(fr,y,'ΜΗ ΜΙΣΘΩΤΗ'),gross:gross,contrib:contrib};
    });
    // ΚΛΩΝΟΣ των ετήσιων γραμμών της καρτέλας ΑΠΔ (window._atlasApdYearlyTotals).
    // Η ΑΠΔ είναι φιλτραρισμένη ίδια με την Καταμέτρηση (ταμείο/πακέτο/τύπος/από-έως κλειδωμένα)
    // + τα ελεύθερα φίλτρα (πλαφόν, %). Fallback: payload apdByKlados (default mode) αν λείπει.
    var apd={},hasApd=false;
    var apdYT=(typeof window!=='undefined')?window._atlasApdYearlyTotals:null;
    if(apdYT&&Object.keys(apdYT).length){
      Object.keys(apdYT).forEach(function(ys){
        var y=parseInt(ys,10);var t=apdYT[ys]||{};
        apd[y]={d:(t.days!=null?t.days:null),g:(t.gross!=null?t.gross:null),s:(t.synt!=null?t.synt:null)};
        hasApd=true;
      });
    }else{
      selCodes.forEach(function(code){
        var perY=apdMap[code];if(!perY)return;
        Object.keys(perY).forEach(function(ys){
          var y=parseInt(ys,10);var t=perY[ys];
          if(!apd[y])apd[y]={d:null,g:null,s:null};
          if(t[0]!=null)apd[y].d=(apd[y].d||0)+t[0];
          if(t[1]!=null)apd[y].g=(apd[y].g||0)+t[1];
          if(t[2]!=null)apd[y].s=(apd[y].s||0)+t[2];
          hasApd=true;
        });
      });
    }
    var core=[];
    for(var y=lo;y<=hi;y++){
      var b=base[y];var inSrc=!!b;
      var dm=inSrc?b.dm:null,dnm=inSrc?b.dnm:null,gross=inSrc?b.gross:null,contrib=inSrc?b.contrib:null,synt=null;
      var is2002=y>=2002;
      if(hasApd){
        var a=apd[y];
        if(is2002){
          dm=(a&&a.d!=null)?a.d:null;
          gross=(a&&a.g!=null)?a.g:null;
          synt=(a&&a.s!=null)?a.s:null;
        }
      }else if(is2002){dm=null;gross=null;}
      var dtk=dtkLookup(dtkRef,y);
      var koin=koinValue(kpType,y,dnm);
      var tekBase=(contrib||0)+(koin||0);
      var tek=null;
      if(inSrc){var rate=rateForYear(tekLabel,y);if(rate&&rate>0)tek=tekBase/rate;}
      var synolikes=null,telikes=null;
      var hasApod=inSrc&&(synt!=null||tek!=null);
      if(hasApod){
        synolikes=(synt||0)+(tek||0);
        telikes=(dtk!=null)?synolikes*dtk:null;
      }
      core.push({year:y,dm:dm,dnm:dnm,gross:gross,synt:synt,contrib:contrib,koin:koin,tek:tek,synolikes:synolikes,dtk:dtk,telikes:telikes});
    }
    return {core:core,hasBase:Object.keys(base).length>0};
  }

  function periodId(y){if(y<=2016)return 1;if(y<=2019)return 2;return 3;}

  function exagoraRow(posoRaw,imeresRaw,etosEx,dtkRef,tekLabel){
    var poso=parsePoso(posoRaw);
    var imeres=parseImeres(imeresRaw);
    var ey=parseInt(etosEx,10);if(isNaN(ey))ey=2026;
    var dtkv=dtkLookup(dtkRef,ey);
    var tek=null,synAp=null,telikes=null;
    if(poso!=null){
      var rate=rateForYear(tekLabel,ey);
      tek=(rate&&rate>0)?poso/rate:0;
      synAp=0+tek;
      if(dtkv!=null)telikes=synAp*dtkv;
    }
    return {year:'ΕΞΑΓΟΡΑ',dm:(imeres!=null?imeres:null),dnm:null,gross:(poso!=null?0:null),synt:null,
            contrib:(poso!=null?poso:null),koin:null,tek:tek,synolikes:synAp,dtk:dtkv,telikes:telikes,isExagora:true};
  }

  function grandTotalRow(core,exRow,calcFrom){
    calcFrom=(calcFrom==null||isNaN(calcFrom))?2002:Number(calcFrom);
    var keys=['dm','dnm','gross','synt','contrib','koin','tek','synolikes','telikes'];
    var acc={},has={};keys.forEach(function(k){acc[k]=0;has[k]=false;});
    core.forEach(function(r){
      if(typeof r.year!=='number')return;
      if(r.year<calcFrom)return;
      keys.forEach(function(k){var v=r[k];if(v!=null&&!isNaN(v)){acc[k]+=v;has[k]=true;}});
    });
    if(exRow){
      keys.forEach(function(k){var v=exRow[k];if(v!=null&&!isNaN(v)){acc[k]+=v;has[k]=true;}});
    }
    var t={year:'ΣΥΝΟΛΟ',dtk:null,isTotal:true};
    keys.forEach(function(k){t[k]=has[k]?acc[k]:null;});
    return t;
  }

  function buildDisplayRows(core,posoRaw,imeresRaw,etosEx,dtkRef,tekLabel,calcFrom,forPrint){
    calcFrom=(calcFrom==null||isNaN(calcFrom))?2002:Number(calcFrom);
    var displayCore=forPrint?core.filter(function(r){return typeof r.year==='number'&&r.year>=calcFrom;}):core;
    var rows=[];var prevP=null;
    displayCore.forEach(function(r){
      var p=periodId(r.year);
      if(!forPrint&&prevP!==null&&p!==prevP)rows.push({sep:true});
      rows.push(r);prevP=p;
    });
    if(!forPrint)rows.push({sep:true});
    var exR=null;
    if(!PARONLY){
      exR=exagoraRow(posoRaw,imeresRaw,etosEx,dtkRef,tekLabel);
      rows.push(exR);
    }
    var total=grandTotalRow(core,exR,calcFrom);
    rows.push(total);
    return {rows:rows,total:total,core:core,exRow:exR};
  }

  // ---------- metrics ----------
  function positiveDays(v){
    if(v==null||isNaN(v))return 0;
    var n=Number(v);
    return n>0?n:0;
  }
  function parseCalcFrom(){
    var el=document.getElementById(PFX+'-calc-from');
    var y=el?parseInt(el.value,10):2002;
    if(isNaN(y)||y<1975||y>2002)return 2002;
    return y;
  }
  function effectiveDaysForMonths(core,exRow,calcFrom){
    calcFrom=(calcFrom==null||isNaN(calcFrom))?2002:Number(calcFrom);
    var total=0;
    (core||[]).forEach(function(r){
      if(typeof r.year!=='number')return;
      if(r.year<calcFrom)return;
      var dm=positiveDays(r.dm);
      var dnm=positiveDays(r.dnm);
      var s=dm+dnm;
      if(r.year>=2017&&dm>0&&dnm>0)s=Math.min(s,300);
      total+=s;
    });
    if(exRow)total+=positiveDays(exRow.dm);
    return total;
  }
  function metricsFromTotal(total,core,exRow,calcFrom){
    var tot=effectiveDaysForMonths(core,exRow,calcFrom);
    var months=tot?tot/25.0:0;
    var tel=(total&&total.telikes!=null&&!isNaN(total.telikes))?total.telikes:null;
    var sal=(tel!=null&&months>0)?tel/months:null;
    return {months:months,tel:tel,sal:sal};
  }
  function colVal(col,r){
    switch(col){
      case 'Έτος': return (typeof r.year==='number')?String(r.year):String(r.year||'');
      case 'Σύνολο ημερών (μισθωτή)': return fmtDays(r.dm);
      case 'Συνολικές μικτές αποδοχές': return fmtCurr(r.gross);
      case 'Συντ. αποδοχές': return fmtCurr(r.synt);
      case 'Σύνολο ημερών (μη μισθωτή)': return fmtDays(r.dnm);
      case 'Συνολικές εισφορές': return fmtCurr(r.contrib);
      case 'Κοινωνικοί Πόροι': return fmtCurr(r.koin);
      case 'Τεκμαρτές αποδοχές': return fmtCurr(r.tek);
      case 'Συνολικές αποδοχές': return fmtCurr(r.synolikes);
      case 'ΔΤΚ': return fmtDtk(r.dtk);
      case 'Τελικές Συντ. Αποδοχές': return fmtCurr(r.telikes);
    }
    return '';
  }
  function hasExagoraData(posoRaw,imeresRaw){
    return Boolean((posoRaw&&String(posoRaw).trim())||(imeresRaw&&String(imeresRaw).trim()));
  }
  function exagoraPrintText(posoRaw,imeresRaw,etosEx){
    if(!hasExagoraData(posoRaw,imeresRaw))return '';
    var parts=[];
    if(posoRaw&&String(posoRaw).trim())parts.push('Ποσό: '+String(posoRaw).trim());
    if(imeresRaw&&String(imeresRaw).trim())parts.push('Ημέρες: '+String(imeresRaw).trim());
    if(etosEx&&String(etosEx).trim())parts.push('Έτος: '+String(etosEx).trim());
    return parts.join(' · ');
  }
  function metricPrintVal(v,isCurr){
    if(v==null||v===undefined||isNaN(v))return '•';
    if(v===0)return '0 €';
    return isCurr?fmtCurr(v):fmtNum1(v);
  }
  function buildSyntaksiPrintSummaryHtml(codes,calcFrom,metrics,posoRaw,imeresRaw,etosEx){
    var pkTxt='—';
    if(codes&&codes.length){
      pkTxt=codes.map(function(c){return esc(KLABELS[c]||c);}).join(', ');
    }
    var hasEx=hasExagoraData(posoRaw,imeresRaw);
    var exTxt=hasEx?esc(exagoraPrintText(posoRaw,imeresRaw,etosEx)):'';
    function cell(lbl,val,wide){
      var cls='atlas-metric-item'+(wide?' atlas-metric-item--wide':'');
      return '<div class="'+cls+'"><span class="atlas-metric-label">'+esc(lbl)+'</span><strong class="atlas-metric-value">'+esc(val)+'</strong></div>';
    }
    var mo=metrics?metricPrintVal(metrics.months,false):'•';
    var ap=metrics?metricPrintVal(metrics.tel,true):'•';
    var mi=metrics?metricPrintVal(metrics.sal,true):'•';
    var calcNote='<p class="print-description syntaksi-print-calc-note">Υπολογισμός από έτος '+calcFrom+' (πίνακας: έτη ≥ '+calcFrom+', εξαγορά, σύνολο).</p>';
    var summaryCls='print-synt-summary '+(hasEx?'print-synt-summary--with-ex':'print-synt-summary--no-ex');
    var exBlock=hasEx?('<div class="print-synt-col-ex"><span class="print-synt-pk-h">Εξαγορά</span><div class="print-synt-pk-txt">'+exTxt+'</div></div>'):'';
    return calcNote+
      '<div class="'+summaryCls+'">'+
      '<div class="print-synt-col-pk"><span class="print-synt-pk-h">Επιλεγμένα πακέτα κάλυψης</span><div class="print-synt-pk-txt">'+pkTxt+'</div></div>'+
      exBlock+
      '<div class="print-synt-col-metrics"><div class="atlas-metrics-row atlas-metrics-row--print">'+cell('Μήνες',mo,false)+cell('Συντάξιμες αποδοχές',ap,true)+cell('Συντάξιμος μισθός',mi,true)+'</div></div>'+
      '</div>';
  }
  var SYN_PRINT_DISCLAIMER='<div class="print-disclaimer"><strong>ΣΗΜΑΝΤΙΚH ΣΗΜΕΙΩΣΗ:</strong> Η παρούσα αναφορά βασίζεται αποκλειστικά στα δεδομένα που εμφανίζονται στο αρχείο ΑΤΛΑΣ/e-ΕΦΚΑ και αποτελεί απλή επεξεργασία των καταγεγραμμένων εγγραφών. Η πλατφόρμα ΑΤΛΑΣ μπορεί να περιέχει κενά ή σφάλματα και η αναφορά αυτή δεν υποκαθιστά νομική ή οικονομική συμβουλή σε καμία περίπτωση. Για θέματα συνταξιοδότησης και οριστικές απαντήσεις αρμόδιος παραμένει αποκλειστικά ο e-ΕΦΚΑ.</div>';
  function renderTable(disp,tekLabel,forPrint){
    var colg='<colgroup>'+COLS.map(function(c){var w=COLW[c];return '<col'+(w?' style="width:'+w+'"':'')+'>';}).join('')+'</colgroup>';
    var thead='<thead><tr>'+COLS.map(function(c){return '<th>'+esc(c)+'</th>';}).join('')+'</tr></thead>';
    var body='';
    disp.rows.forEach(function(r){
      if(r.sep){body+='<tr class="syn-sep">'+COLS.map(function(){return '<td></td>';}).join('')+'</tr>';return;}
      var cls=r.isTotal?' class="syn-total"':(r.isExagora?' class="syn-exagora"':((typeof r.year==='number'&&activeParYears()[String(r.year)])?' class="syn-parallel"':''));
      body+='<tr'+cls+'>'+COLS.map(function(c){
        var v=colVal(c,r);
        var tdcls='';
        if(c==='Έτος')tdcls=' class="syn-year"';
        return '<td'+tdcls+'>'+esc(v)+'</td>';
      }).join('')+'</tr>';
    });
    var ogaExtra=(tekLabel===OGALABEL)?' (7% έως 2014, 8,5%→2015, 10%→2016, 14%→2017, 16%→2018, 18%→2019, 19%→2020, 19,5%→2021, 20% από 2022)':'';
    var tblCls='print-table syntaksi-table'+(forPrint?' wrap-cells':'');
    var note=forPrint?'':('<p class="print-description syntaksi-note">Τεκμαρτές = (εισφορές + κοιν. πόροι) ÷ ποσοστό (<strong>'+esc(tekLabel)+'</strong>'+esc(ogaExtra)+'). Συνολικές αποδοχές = Συντ. αποδοχές + τεκμαρτές· Τελικές = Συνολικές × ΔΤΚ.</p>');
    return '<table class="'+tblCls+'">'+colg+thead+'<tbody>'+body+'</tbody></table>'+note;
  }

  function setMetricCurr(id,v){
    var el=document.getElementById(id);if(!el)return;
    if(v===null||v===undefined)el.textContent='•';
    else if(v===0)el.textContent='0 €';
    else el.textContent=fmtCurr(v);
  }
  function setMetrics(m){
    var mo=document.getElementById(PFX+'-metric-months');
    if(mo)mo.textContent=m?fmtNum1(m.months):'•';
    setMetricCurr(PFX+'-metric-apod',m?m.tel:null);
    setMetricCurr(PFX+'-metric-mis',m?m.sal:null);
  }
  function setPk(codes){
    var el=document.getElementById(PFX+'-metrics-pk');
    if(!el)return;
    if(!codes||!codes.length){el.textContent='—';return;}
    el.innerHTML=codes.map(function(c){return '<span class="syntaksi-pk-chip">'+esc(KLABELS[c]||c)+'</span>';}).join('');
  }

  // ---------- nav visibility ----------
  function setNavVisible(show){
    var nav=document.querySelector('.nav-item[data-tab="'+TAB+'"]');
    if(nav)nav.style.display=show?'':'none';
    if(!show){
      var pane=document.getElementById('pane-'+TAB);
      if(pane&&pane.classList.contains('active')&&typeof window.showTab==='function'){window.showTab('count');}
    }
  }

  // ---------- JSON export ----------
  function r2(x){return Math.round(x*100)/100;}
  function r5(x){return Math.round(x*100000)/100000;}
  function buildJson(core,posoRaw,imeresRaw,etosEx,dtkRef,tekLabel){
    var jd={};var kerdiYears=[2017,2018,2019];
    core.forEach(function(r){
      var ys=String(r.year);
      jd['ika_'+ys]={value:(r.dm!=null&&!isNaN(r.dm))?Math.round(r.dm):0,type:'number'};
      jd['apodoxes_'+ys]={value:(r.synt!=null&&!isNaN(r.synt))?r2(r.synt):0,type:'number'};
      if(r.dnm!=null&&r.dnm>0)jd['elep_'+ys]={value:String(Math.ceil(r.dnm/25.0)),type:'text'};
      else jd['elep_'+ys]={value:'',type:'text'};
      var eisRaw=(r.contrib!=null&&!isNaN(r.contrib))?r.contrib:0;
      jd['eisfores_'+ys]={value:r2(eisRaw),type:'number'};
      if(kerdiYears.indexOf(r.year)!==-1){
        var kerdi;
        if(r.tek!=null&&!isNaN(r.tek))kerdi=r2(r.tek);
        else{var rate=rateForYear(tekLabel,r.year);kerdi=r2((rate&&rate>0)?eisRaw/rate:0);}
        jd['kerdi_'+ys]={value:kerdi,type:'number'};
      }
    });
    kerdiYears.forEach(function(ky){if(!jd['kerdi_'+ky])jd['kerdi_'+ky]={value:0,type:'number'};});
    var poso=parsePoso(posoRaw);var posoF=poso!=null?poso:0;
    var imeres=parseImeres(imeresRaw);var imeresV=imeres!=null?Math.round(imeres):0;
    var ey=parseInt(etosEx,10);if(isNaN(ey))ey=2026;
    var dtkv=dtkLookup(dtkRef,ey);var dtkEx=r5(dtkv!=null?dtkv:0);
    var refY=parseInt(dtkRef,10);if(isNaN(refY))refY=new Date().getFullYear();
    jd['eksagorasmenes_imeres']={value:imeresV,type:'number'};
    jd['synoliko_poso_eksagoras']={value:r2(posoF),type:'number'};
    jd['dtk_eksagoras']={value:dtkEx,type:'number'};
    jd['dtk']={value:refY,type:'number'};
    jd['etos_ethnikis']={value:refY,type:'number'};
    return JSON.stringify(jd,null,2);
  }
  function buildJsonSheet25Parallel(core,mode){
    mode=mode==='elep'?'elep':'misthoti';
    var byYear={};
    (core||[]).forEach(function(r){
      if(typeof r.year!=='number')return;
      byYear[r.year]=r;
    });
    var jd={};
    jd['s25r4c3']={
      value:mode==='elep'?'Ελ. Επαγγελματίας':'Μισθωτός',
      type:'text'
    };
    var totDays=0,totVal=0;
    for(var y=2002;y<=2016;y++){
      var row=8+(y-2002);
      var r=byYear[y];
      var days=0,val=0;
      if(r){
        if(mode==='misthoti'){
          days=(r.dm!=null&&!isNaN(r.dm))?Math.round(r.dm):0;
          val=(r.synt!=null&&!isNaN(r.synt))?r2(r.synt):0;
        }else{
          days=(r.dnm!=null&&!isNaN(r.dnm))?Math.round(r.dnm):0;
          var c=(r.contrib!=null&&!isNaN(r.contrib))?Number(r.contrib):0;
          var k=(r.koin!=null&&!isNaN(r.koin))?Number(r.koin):0;
          val=r2(c+k);
        }
      }
      jd['s25r'+row+'c3']={value:days,type:'number'};
      jd['s25r'+row+'c4']={value:val,type:'number'};
      totDays+=days;
      totVal+=val;
    }
    jd['s25r24c3']={value:totDays,type:'number'};
    jd['s25r24c4']={value:r2(totVal),type:'number'};
    return JSON.stringify(jd,null,2);
  }

  // ---------- inputs ----------
  function val(id){var el=document.getElementById(id);return el?el.value:'';}

  var _lastCore=null,_lastInputs=null;

  function recompute(){
    var cs=getCountState();
    setLockedFromCount(cs);
    var selCodes=cs.klados.slice();
    var mount=document.getElementById(PFX+'-table-mount');
    var empty=document.getElementById(PFX+'-empty');
    var dlBtn=document.getElementById(PFX+'-json-dl');
    setNavVisible(selCodes.length>0);
    if(selCodes.length===0){
      if(mount){mount.hidden=true;mount.innerHTML='';}
      if(empty)empty.hidden=false;
      if(dlBtn)dlBtn.disabled=true;
      setMetrics(null);setPk([]);
      _lastCore=null;
      return;
    }
    if(empty)empty.hidden=true;
    var yr=yearRangeFromCount(cs);
    var dtkRef=val(PFX+'-dtk-ref');
    var kpType=val(PFX+'-koin');
    var tekLabel=resolveTekLabel();
    var posoRaw=val(PFX+'-exagora-poso');
    var imeresRaw=val(PFX+'-exagora-imres');
    var etosEx=val(PFX+'-exagora-etos');
    var calcFrom=parseCalcFrom();
    var res=computeCore(selCodes,yr.lo,yr.hi,cs,dtkRef,kpType,tekLabel);
    var tableCore=adjustCoreForParallel(res.core);
    var disp=buildDisplayRows(tableCore,posoRaw,imeresRaw,etosEx,dtkRef,tekLabel,calcFrom);
    if(mount){mount.hidden=false;mount.innerHTML=renderTable(disp,tekLabel);}
    setMetrics(metricsFromTotal(disp.total,disp.core,disp.exRow,calcFrom));
    setPk(selCodes);
    if(dlBtn)dlBtn.disabled=false;
    _lastCore=tableCore;
    _lastInputs={posoRaw:posoRaw,imeresRaw:imeresRaw,etosEx:etosEx,dtkRef:dtkRef,tekLabel:tekLabel};
  }

  // download
  var dlBtn=document.getElementById(PFX+'-json-dl');
  if(dlBtn)dlBtn.addEventListener('click',function(){
    if(!_lastCore||!_lastInputs)return;
    var txt;
    if(PARONLY){
      txt=buildJsonSheet25Parallel(_lastCore,currentParMode());
    }else{
      txt=buildJson(_lastCore,_lastInputs.posoRaw,_lastInputs.imeresRaw,_lastInputs.etosEx,_lastInputs.dtkRef,_lastInputs.tekLabel);
    }
    var blob=new Blob([txt],{type:'application/json;charset=utf-8'});
    var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(PARONLY?'efka_syntaksi_parallel.json':'efka_syntaksi_pro.json');a.click();URL.revokeObjectURL(a.href);
  });

  // debounce
  var _t=null;
  function recomputeSoon(){if(_t)clearTimeout(_t);_t=setTimeout(recompute,120);}

  // listeners
  window.addEventListener('atlas-count-klados-change',recomputeSoon);
  window.addEventListener('atlas-count-filters-change',recomputeSoon);
  var csec=document.getElementById('count-section');
  if(csec){csec.addEventListener('change',recomputeSoon);csec.addEventListener('input',recomputeSoon);}
  // Κλώνος ΑΠΔ: οποιαδήποτε αλλαγή στην ΑΠΔ (πλαφόν, %, κ.λπ.) → επανυπολογισμός Συντάξιμων
  window.addEventListener('atlas-apd-recomputed',recomputeSoon);
  var apdSec=document.getElementById('apd-section');
  if(apdSec){apdSec.addEventListener('change',recomputeSoon);apdSec.addEventListener('input',recomputeSoon);}
  ['cnt-filter-from','cnt-filter-to'].forEach(function(id){var el=document.getElementById(id);if(el){el.addEventListener('input',recomputeSoon);el.addEventListener('change',recomputeSoon);}});
  [PFX+'-calc-from',PFX+'-dtk-ref',PFX+'-exagora-poso',PFX+'-exagora-imres',PFX+'-exagora-etos',PFX+'-koin',PFX+'-tek'].forEach(function(id){
    var el=document.getElementById(id);if(el){el.addEventListener('input',recomputeSoon);el.addEventListener('change',recomputeSoon);}
  });
  if(HASPARDROPDOWN){
    window._atlasSyntaksiParMode=window._atlasSyntaksiParMode||'misthoti';
    window._atlasBroadcastParMode=window._atlasBroadcastParMode||function(mode,source){
      mode=mode==='elep'?'elep':'misthoti';
      window._atlasSyntaksiParMode=mode;
      ['syntaksi','syntaksipar'].forEach(function(pfx){
        var el=document.getElementById(pfx+'-par-mode');
        if(el&&el.value!==mode)el.value=mode;
        if(pfx===source)return;
        var fn=window._atlasSyntaksiRecomputeMap&&window._atlasSyntaksiRecomputeMap[pfx];
        if(typeof fn==='function')fn();
      });
    };
    var parEl=document.getElementById(PFX+'-par-mode');
    if(parEl){
      if(PFX==='syntaksi'){
        window._atlasSyntaksiParMode=parEl.value==='elep'?'elep':'misthoti';
      }else if(parEl.value!==window._atlasSyntaksiParMode){
        parEl.value=window._atlasSyntaksiParMode;
      }
      parEl.addEventListener('change',function(){
        window._atlasBroadcastParMode(parEl.value,PFX);
        recomputeSoon();
      });
    }
  }

  var getPrintBody=function(){
    recompute();
    var cs=getCountState();
    if(!cs.klados||!cs.klados.length)return {ok:false};
    if(!_lastCore||!_lastInputs)return {ok:false};
    var calcFrom=parseCalcFrom();
    var disp=buildDisplayRows(_lastCore,_lastInputs.posoRaw,_lastInputs.imeresRaw,_lastInputs.etosEx,_lastInputs.dtkRef,_lastInputs.tekLabel,calcFrom,true);
    var metrics=metricsFromTotal(disp.total,disp.core,disp.exRow,calcFrom);
    return {
      ok:true,
      calcFrom:calcFrom,
      summaryHtml:buildSyntaksiPrintSummaryHtml(cs.klados,calcFrom,metrics,_lastInputs.posoRaw,_lastInputs.imeresRaw,_lastInputs.etosEx),
      tableHtml:renderTable(disp,_lastInputs.tekLabel,true),
      disclaimerHtml:SYN_PRINT_DISCLAIMER
    };
  };
  window._atlasSyntaksiRecomputeMap=window._atlasSyntaksiRecomputeMap||{};
  window._atlasSyntaksiRecomputeMap[PFX]=recompute;
  window._atlasSyntaksiPrint=window._atlasSyntaksiPrint||{};
  window._atlasSyntaksiPrint[PFX]=getPrintBody;
  if(PFX==='syntaksi'){
    window._atlasSyntaksiRecompute=recompute;
    window._atlasSyntaksiGetPrintBody=getPrintBody;
    try{window._atlasSyntaksiDebug={computeCore:computeCore,buildDisplayRows:buildDisplayRows,buildJson:buildJson,buildJsonSheet25Parallel:buildJsonSheet25Parallel,metricsFromTotal:metricsFromTotal};}catch(e){}
  }
  recompute();
};
"""


def _sanitize_excel_sheet_name(label: str, used: set) -> str:
    """Excel sheet name: max 31 chars, χωρίς \\ / ? * [ ] :"""
    s = re.sub(r'[\[\]:*?/\\]', '_', str(label).strip())
    s = (s[:31] if s else "Sheet").strip() or "Sheet"
    base = s
    n = 1
    while s in used:
        suffix = f"_{n}"
        max_base = 31 - len(suffix)
        s = (base[:max_base] if len(base) > max_base else base) + suffix
        n += 1
    used.add(s)
    return s


def _excel_df_copy(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    try:
        return df.copy()
    except Exception:
        return pd.DataFrame(df)


def _build_excel_workbook_bytes(sheet_pairs: list) -> bytes | None:
    """sheet_pairs: λίστα (τίτλος φύλλου, DataFrame)."""
    if not sheet_pairs:
        return None
    buf = io.BytesIO()
    used_names: set = set()
    wrote = False
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        for label, df in sheet_pairs:
            export_df = _excel_df_copy(df)
            if export_df is None:
                continue
            sheet_name = _sanitize_excel_sheet_name(label, used_names)
            # Ίδια λογική με το Streamlit: σωστοί τύποι κελιών (αριθμός/ημερομηνία)
            # αντί για formatted text, ώστε η εξαγωγή HTML→Excel να ταιριάζει.
            _atlas_write_df_to_excel(writer, export_df, sheet_name, index=False)
            wrote = True
    if not wrote:
        return None
    buf.seek(0)
    return buf.getvalue()


def _build_apd_export_df(df, description_map=None):
    apd_df = _build_apd_base_df(df)
    if apd_df is None or apd_df.empty:
        return pd.DataFrame()
    earnings_col = _apd_earnings_col(apd_df)
    col_order = _apd_column_order(apd_df, earnings_col)
    records = _apd_build_records(apd_df, earnings_col, description_map)
    if not records:
        return pd.DataFrame()
    default_plafond = "palios" if _apd_is_palios(df) else "neos"
    default_params = {
        "plafond": default_plafond,
        "from_i": 20020101, "to_i": 0,
        "tameio": [], "klados": [], "apodox": [],
        "ret_mode": "all", "ret_thr": 18.0, "highlight": 21.0,
        "totals_only": False,
    }
    static_rows = _apd_compute_display_rows(records, col_order, default_params)
    rows = []
    for r in static_rows:
        if r.get("kind") == "empty":
            continue
        cells = r.get("cells") or {}
        rows.append({c: cells.get(c, "") for c in col_order})
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _build_syntaksi_export_df(df, description_map=None):
    count_df = filter_count_df(df)
    c_df = build_count_c_dataframe(count_df, description_map or {})
    if c_df is None or c_df.empty:
        return pd.DataFrame()
    try:
        return build_syntaksi_annual_table(c_df)
    except Exception:
        return pd.DataFrame()


def _count_df_for_excel(count_display_df):
    if count_display_df is None or count_display_df.empty:
        return pd.DataFrame()
    _renames = {
        'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ': 'ΑΠΟΔΟΧΕΣ',
        'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ': 'ΕΙΣΦΟΡΕΣ',
        'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ': '%',
    }
    out = count_display_df.rename(
        columns={k: v for k, v in _renames.items() if k in count_display_df.columns}
    )
    return out.copy()


def _excel_sheets_from_tab_order(tab_entries, excel_by_tid, audit_df):
    """Σειρά φύλλων Excel όπως η σειρά καρτελών (χωρίς Προσωπικά / Ιστορικό)."""
    skip_tids = {"personal", "timeline"}
    pairs = []
    for tid, label, _ in tab_entries:
        if tid in skip_tids:
            continue
        if tid == "synopsis":
            syn = _excel_df_copy(audit_df)
            if syn is not None:
                pairs.append(("Σύνοψη", syn))
            continue
        entry = excel_by_tid.get(tid)
        if entry is None:
            continue
        if isinstance(entry, list):
            pairs.extend(entry)
        else:
            pairs.append(entry)
    return pairs


def _append_pro_tab_entries(df, description_map, tab_entries, excel_by_tid=None):
    """Προσθέτει τις Pro-only καρτέλες στο tab_entries (σταδιακή μεταφορά από την Κυρία)."""
    excel_by_tid = excel_by_tid if excel_by_tid is not None else {}
    # -- ΑΠΔ / Πλαφόν --
    try:
        apd_html = build_apd_with_filters(df, description_map)
        if apd_html:
            tab_entries.append(("apd", "ΑΠΔ/Πλαφόν", apd_html))
            apd_x = _build_apd_export_df(df, description_map)
            if apd_x is not None and not apd_x.empty:
                excel_by_tid["apd"] = ("ΑΠΔ Πλαφόν", apd_x)
    except Exception:
        pass

    # -- Κύρια Δεδομένα --
    try:
        main_df = _build_maindata_df(df)
        if main_df is not None and not main_df.empty:
            tab_entries.append((
                "maindata", "Κύρια Δεδομένα",
                _build_tab_page(
                    section_id="maindata-section",
                    heading_html="<h2>Κύρια Δεδομένα</h2>",
                    description_html=(
                        "<p class='print-description'>Πλήρης πίνακας εγγραφών ασφάλισης "
                        "(χρονολογική σειρά).</p>"
                    ),
                    body_html=_build_maindata_table_html(main_df),
                ),
            ))
            excel_by_tid["maindata"] = ("Κύρια Δεδομένα", main_df.copy())
    except Exception:
        pass

    # -- Παράρτημα --
    try:
        annex_df = _build_annex_df(df)
        if annex_df is not None and not annex_df.empty:
            tab_entries.append((
                "annex", "Παράρτημα",
                _build_tab_page(
                    section_id="annex-section",
                    heading_html="<h2>Παράρτημα (Τελευταίες Σελίδες)</h2>",
                    description_html=(
                        "<p class='print-description'>Επεξηγηματικοί πίνακες καλύψεων και "
                        "αποδοχών από τις τελευταίες σελίδες του ΑΤΛΑΣ.</p>"
                    ),
                    body_html=_build_annex_table_html(annex_df),
                ),
            ))
            excel_by_tid["annex"] = ("Παράρτημα", annex_df.copy())
    except Exception:
        pass


def build_report_tab_entries(df, description_map=None, edition="lite"):
    """Δημιουργεί τα tab entries (id, label, html) για τον HTML viewer.

    edition: "lite" (προεπιλογή) → ίδιες καρτέλες με τη Lite·
             "pro" → προσθήκη επιπλέον καρτελών (Κύρια Δεδομένα, Παράρτημα, κ.λπ.).

    Επιστρέφει (audit_df, display_summary, count_display_df, print_style_rows, tab_entries,
              show_complex_warning, complex_modal_body_html, excel_sheets).
    """
    if description_map is None:
        description_map = build_description_map(df)

    count_df = filter_count_df(df)
    audit_df = generate_audit_report(df)
    display_summary = (
        build_summary_grouped_display(df, df)
        if 'Κλάδος/Πακέτο Κάλυψης' in df.columns
        else pd.DataFrame()
    )
    count_display_df, _, _, _, print_style_rows = build_count_report(
        count_df, description_map=description_map, show_count_totals_only=False,
        force_insurance_type_subtotals=True,
    )

    show_complex_warning = False
    complex_modal_body_html = ""
    try:
        _metrics = compute_complex_file_metrics(df)
        if len(_metrics) >= 4:
            n_agg, n_limits_25, n_unpaid, n_negative = _metrics[:4]
        else:
            n_agg, n_limits_25, n_unpaid = _metrics[:3]
            _neg_df = find_negative_entries(df)
            n_negative = len(_neg_df) if _neg_df is not None and not _neg_df.empty else 0
        try:
            show_complex_warning = should_show_complex_file_warning(
                n_agg, n_limits_25, n_unpaid, n_negative
            )
        except TypeError:
            show_complex_warning = (
                should_show_complex_file_warning(n_agg, n_limits_25, n_unpaid)
                or n_negative > 0
            )
        if show_complex_warning:
            _secs = _html_build_complex_file_modal_sections(n_agg, n_limits_25, n_unpaid, n_negative)
            complex_modal_body_html = _viewer_synopsis_blocks_html(_secs)
    except Exception:
        pass

    tab_entries = []
    excel_by_tid = {}

    # -- Detect warning types for totals --
    warning_types = []
    _par_res = _safe_call(build_parallel_print_df, df, description_map, True)
    parallel_df, parallel_styles = (None, None)
    if isinstance(_par_res, tuple):
        parallel_df, parallel_styles = _par_res
    else:
        parallel_df = _par_res
    if parallel_df is not None and not parallel_df.empty:
        warning_types.append("παράλληλη ασφάλιση")
    _par17_res = _safe_call(build_parallel_2017_print_df, df, description_map, True)
    parallel_2017_df, parallel_2017_styles = (None, None)
    if isinstance(_par17_res, tuple):
        parallel_2017_df, parallel_2017_styles = _par17_res
    else:
        parallel_2017_df = _par17_res
    if parallel_2017_df is not None and not parallel_2017_df.empty:
        warning_types.append("παράλληλη απασχόληση 2017+")
    _multi_res = _safe_call(build_multi_employment_print_df, df, description_map, True)
    multi_df, multi_styles = (None, None)
    if isinstance(_multi_res, tuple):
        multi_df, multi_styles = _multi_res
    else:
        multi_df = _multi_res
    if multi_df is not None and not multi_df.empty:
        warning_types.append("πολλαπλή απασχόληση")

    # -- Totals --
    if not display_summary.empty:
        totals_html = build_totals_with_filters(
            display_summary, raw_df=df, desc_map=description_map,
            warning_types=warning_types,
        )
        tab_entries.append(("totals", "Σύνολα", totals_html))
        excel_by_tid["totals"] = ("Σύνολα", display_summary.copy())

    # -- Count --
    if not count_display_df.empty:
        count_html = build_count_with_filters(
            count_display_df, print_style_rows, count_df, description_map,
            warning_types=warning_types,
            display_summary=display_summary,
            source_df=df,
        )
        tab_entries.append(("count", "Καταμέτρηση", count_html))
        cnt_x = _count_df_for_excel(count_display_df)
        if cnt_x is not None and not cnt_x.empty:
            excel_by_tid["count"] = ("Καταμέτρηση", cnt_x)

    # -- Συντάξιμες (Pro) — αμέσως μετά την Καταμέτρηση, εκτός αν ΤΣΜΕΔΕ μισθωτή --
    if edition == "pro" and not count_display_df.empty:
        try:
            if not df_has_tsmede_misthoti_insurance(df):
                syn_payload = _syntaksi_build_payload(df, description_map)
                _syn_has_par16 = bool(
                    syn_payload.get("parallelYears")
                    or syn_payload.get("parallelYearsMisthoti")
                    or syn_payload.get("parallelYearsElep")
                )
                syntaksi_html = _build_syntaksi_tab_html(
                    syn_payload, prefix="syntaksi", tab_id="syntaksi",
                    title="Συντάξιμες Αποδοχές", parallel_only=False,
                    par_exclude_until2016=_syn_has_par16,
                    include_engine=True,
                )
                if syntaksi_html:
                    tab_entries.append(("syntaksi", "Συντάξιμες", syntaksi_html))
                    syn_x = _build_syntaksi_export_df(df, description_map)
                    if syn_x is not None and not syn_x.empty:
                        excel_by_tid["syntaksi"] = ("Συντάξιμες", syn_x)
                    # Δεύτερη καρτέλα: μόνο έτη με παράλληλη ασφάλιση ≤2016 (ίδιοι υπολογισμοί)
                    if (
                        syn_payload.get("parallelYears")
                        or syn_payload.get("parallelYearsMisthoti")
                        or syn_payload.get("parallelYearsElep")
                    ):
                        syntaksi_par_html = _build_syntaksi_tab_html(
                            syn_payload, prefix="syntaksipar", tab_id="syntaksipar",
                            title="Συντάξιμες αποδοχές παράλληλης ασφάλισης", parallel_only=True, include_engine=False,
                        )
                        if syntaksi_par_html:
                            tab_entries.append(("syntaksipar", "Συντάξιμες παραλ.", syntaksi_par_html))
        except Exception:
            pass

    # -- Gaps --
    try:
        gaps_df = find_gaps_in_insurance_data(df)
        zero_duration_df = find_zero_duration_intervals(df)
        gaps_body_parts = []
        gaps_metrics_html = ""
        if gaps_df is not None and not gaps_df.empty:
            gaps_metrics_html = _build_gaps_metrics_html(gaps_df)
            gaps_body_parts.append(build_print_section_html(
                "Κενά Διαστήματα", gaps_df,
                description="Χρονικές περίοδοι χωρίς ασφαλιστική κάλυψη.",
                heading_tag="h2",
            ))
        if zero_duration_df is not None and not zero_duration_df.empty:
            gaps_body_parts.append(build_print_section_html(
                "Διαστήματα χωρίς ημέρες ασφάλισης", zero_duration_df,
                description="Εγγραφές που εμφανίζονται στον ΑΤΛΑΣ αλλά χωρίς τιμές σε Έτη/Μήνες/Ημέρες.",
                heading_tag="h2",
            ))
        if gaps_body_parts:
            gaps_body_parts.append(
                "<p class='print-description' style='margin-top:1.25em;padding:0.5em 0;"
                "border-top:1px solid #e2e8f0;font-size:0.95em;'>"
                "Τα διαστήματα χωρίς ημέρες ασφάλισης αναφέρονται αυτούσια στο αρχείο ΑΤΛΑΣ "
                "χωρίς ημέρες ασφάλισης. Ωστόσο, δεν αποτελούν εξ ορισμού κενό διάστημα "
                "καθώς μπορεί να επικαλύπτονται μερικώς από άλλες εγγραφές που να έχουν ημέρες "
                "ασφάλισης. Απαιτείται λεπτομερής έλεγχος.</p>"
            )
            _gaps_excel = []
            if gaps_df is not None and not gaps_df.empty:
                _gaps_excel.append(("Κενά Διαστήματα", gaps_df.copy()))
            if zero_duration_df is not None and not zero_duration_df.empty:
                _gaps_excel.append(("Χωρίς ημέρες ασφ.", zero_duration_df.copy()))
            if _gaps_excel:
                excel_by_tid["gaps"] = _gaps_excel
            _gaps_info_sections = [
                (
                    "info",
                    "Σκοπός: Εντοπίζει χρονικά διαστήματα που δεν εμφανίζονται καθόλου στο ΑΤΛΑΣ "
                    "από την έναρξη της ασφάλισης έως σήμερα.",
                ),
            ]
            _gaps_heading = _atlas_html_tab_heading_row_info(
                "Αναφορά Κενών Διαστήματων και διαστημάτων χωρίς ημέρες ασφάλισης",
                "Σκοπός — Κενά διαστήματα",
                _gaps_info_sections,
                "atlas-info-store-gaps",
            )
            tab_entries.append((
                "gaps",
                "Κενά",
                _build_tab_page(
                    section_id="gaps-section",
                    heading_html=_gaps_heading,
                    description_html=(
                        "<p class='print-description'>Χρονικές περίοδοι χωρίς ασφαλιστική κάλυψη "
                        "και διαστήματα χωρίς ημέρες ασφάλισης.</p>"
                    ),
                    metrics_html=gaps_metrics_html,
                    body_html="".join(gaps_body_parts),
                ),
            ))
    except Exception:
        pass

    # -- Parallel --
    if parallel_df is not None and not parallel_df.empty:
        par_html = build_yearly_print_html(
            parallel_df, year_column='Έτος',
            style_rows=parallel_styles,
            collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης'],
        )
        par_html = _inject_parallel_year_totals(par_html, parallel_df)
        _par_info = [
            (
                "info",
                "Εμφάνιση διαστημάτων όπου συνυπάρχουν στον ίδιο μήνα: ΙΚΑ (Τύπος Αποδοχών 01, 16 ή 99) "
                "& ΟΑΕΕ (Κλάδος/Πακέτο Κ), ΙΚΑ & ΤΣΜΕΔΕ (ΚΣ/ΠΚΣ), ΟΑΕΕ (Κ) & ΤΣΜΕΔΕ (ΚΣ/ΠΚΣ), "
                "ΙΚΑ & ΤΣΑΥ μισθωτό (ΜΕ), ΙΚΑ & ΤΣΑΥ μη μισθωτό (ΜΕ), ή ΟΓΑ (Κ) & ΙΚΑ/ΟΑΕΕ.",
            ),
            (
                "warning",
                "Διαστήματα που καλύπτουν πολλαπλούς μήνες επιμερίζονται και επισημαίνονται με κίτρινο χρώμα.",
            ),
        ]
        _par_h = _atlas_html_tab_heading_row_info(
            "Παράλληλη Ασφάλιση",
            "Πληροφορίες — Παράλληλη ασφάλιση",
            _par_info,
            "atlas-info-store-parallel",
        )
        tab_entries.append((
            "parallel", "Παράλληλη",
            _build_tab_page(
                section_id="parallel-section",
                heading_html=_par_h,
                description_html=(
                    "<p class='print-description'>ΙΚΑ & ΟΑΕΕ / ΙΚΑ & ΤΣΜΕΔΕ / ΙΚΑ & ΤΣΑΥ / ΟΑΕΕ & ΤΣΜΕΔΕ / ΟΓΑ & ΙΚΑ/ΟΑΕΕ "
                    "(έως 31/12/2016).</p>"
                ),
                metrics_html=_build_parallel_metrics_html(
                    df, "Μήνες Παράλληλης", "Ημέρες Παράλληλης", mode="legacy",
                    parallel_df=parallel_df,
                ),
                body_html=par_html,
            ),
        ))
        excel_by_tid["parallel"] = ("Παράλληλη", parallel_df.copy())

    # -- Parallel 2017+ --
    if parallel_2017_df is not None and not parallel_2017_df.empty:
        par2017_html = build_yearly_print_html(
            parallel_2017_df, year_column='Έτος',
            style_rows=parallel_2017_styles,
            collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης'],
        )
        _p17_info = [
            (
                "info",
                "Εμφάνιση διαστημάτων από 01/2017 και μετά όπου συνυπάρχουν στον ίδιο μήνα: "
                "ΙΚΑ (αποδοχές 01, 16 ή 99) & ΕΦΚΑ μη μισθωτή ή ΕΦΚΑ μισθωτή & ΕΦΚΑ μη μισθωτή.",
            ),
            (
                "warning",
                "Διαστήματα που καλύπτουν πολλαπλούς μήνες επιμερίζονται και επισημαίνονται με κίτρινο χρώμα.",
            ),
        ]
        _p17_h = _atlas_html_tab_heading_row_info(
            "Παράλληλη Απασχόληση 2017+",
            "Πληροφορίες — Παράλληλη απασχόληση 2017+",
            _p17_info,
            "atlas-info-store-parallel2017",
        )
        tab_entries.append((
            "parallel2017", "Παράλληλη 2017+",
            _build_tab_page(
                section_id="parallel2017-section",
                heading_html=_p17_h,
                description_html=(
                    "<p class='print-description'>Από 01/2017 (ΙΚΑ & ΕΦΚΑ μη μισθωτή / ΕΦΚΑ μισθωτή "
                    "& ΕΦΚΑ μη μισθωτή).</p>"
                ),
                metrics_html=_build_parallel_metrics_html(
                    df, "Μήνες Παράλληλης 2017+", "Ημέρες Παράλληλης 2017+", mode="2017"
                ),
                body_html=par2017_html,
            ),
        ))
        excel_by_tid["parallel2017"] = ("Παράλληλη 2017+", parallel_2017_df.copy())

    # -- Multi employment --
    if multi_df is not None and not multi_df.empty:
        multi_html = build_yearly_print_html(
            multi_df, year_column='Έτος',
            style_rows=multi_styles,
            collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης'],
            bold_columns=['Εργοδότης'],
            col_width_overrides={'Εργοδότης': '90px'},
        )
        tab_entries.append((
            "multi", "Πολλαπλή",
            _build_tab_page(
                section_id="multi-section",
                heading_html="<h2>Πολλαπλή Απασχόληση</h2>",
                description_html=(
                    "<p class='print-description'>Μήνες με πολλαπλούς εργοδότες ΙΚΑ "
                    "(αποδοχές 01, 16, ή 99).</p>"
                ),
                metrics_html=_build_multi_metrics_html(df, description_map),
                body_html=multi_html,
            ),
        ))
        excel_by_tid["multi"] = ("Πολλαπλή", multi_df.copy())

    # -- Pro-only tabs --
    if edition == "pro":
        _append_pro_tab_entries(df, description_map, tab_entries, excel_by_tid)

    # -- Synopsis cards --
    _check_to_tab = {
        "Κενά ασφάλισης": "gaps",
        "Ασφαλιστικά ταμεία": "totals",
        "Παράλληλη ασφάλιση": "parallel",
        "Παράλληλη απασχόληση 2017+": "parallel2017",
        "Πολλαπλή απασχόληση": "multi",
        "Ενοποιημένα διαστήματα": "count",
    }
    available_tab_ids = {tid for tid, _, _ in tab_entries}

    if not audit_df.empty:
        cards_html = _build_synopsis_audit_layout(audit_df, _check_to_tab, available_tab_ids)
        synopsis_html = (
            f"<section class='print-section'><h2>Σύνοψη</h2>"
            f"<p class='print-description'>Βασικοί έλεγχοι δεδομένων.</p>"
            f"{cards_html}</section>"
        )
    else:
        synopsis_html = "<p>Δεν βρέθηκαν στοιχεία.</p>"

    # Προσωπικά Στοιχεία πάντα πρώτο tab, μετά Ιστορικό, μετά Σύνοψη
    tab_entries.insert(0, ("personal", "Προσωπικά Στοιχεία", PERSONAL_TAB_HTML))
    tab_entries.insert(1, ("synopsis", "Σύνοψη", synopsis_html))

    # -- Timeline --
    try:
        timeline_html = build_timeline_html(df)
        if timeline_html:
            # Αν υπάρχει, το Ιστορικό μπαίνει δεύτερο, πριν τη Σύνοψη
            tab_entries.insert(1, ("timeline", "Ιστορικό", timeline_html))
    except Exception:
        pass

    # Στην προβολή HTML εμφανίζονται μόνο οι ίδιες καρτέλες με τη Lite (όχι ΑΠΔ, Κύρια Δεδομένα, Αποζημίωση, Παράρτημα)
    # Περίπλοκο αρχείο: ενσωματώνεται στον viewer (μπάρα + modal) και στην εκτύπωση ξεχωριστά.

    excel_sheets = (
        _excel_sheets_from_tab_order(tab_entries, excel_by_tid, audit_df)
        if edition == "pro" else []
    )

    return (
        audit_df,
        display_summary,
        count_display_df,
        print_style_rows,
        tab_entries,
        show_complex_warning,
        complex_modal_body_html,
        excel_sheets,
    )


def _safe_call(func, *args):
    try:
        return func(*args)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# HTML viewer assembly
# ---------------------------------------------------------------------------

def build_print_html_document(
    tab_entries, audit_df, display_summary, client_name="",
    show_complex_warning=False,
):
    """Κατασκευή εκτυπώσιμου HTML (χωρίς sidebar, compact, A4)."""
    synopsis_print = build_print_section_html(
        "Σύνοψη", audit_df,
        description="Βασικοί έλεγχοι δεδομένων.", wrap_cells=True, heading_tag="h2",
    )
    totals_print = ""
    if not display_summary.empty:
        totals_print = build_print_section_html(
            "Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)",
            display_summary,
            description="Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης και Ταμείο.",
            heading_tag="h2",
        )

    _skip_in_print = {"totals", "synopsis", "personal"}

    def _print_tab_body(tid: str, content: str) -> str:
        body = content
        if tid == "count":
            body = _count_unified_to_per_year_html(body)
        if show_complex_warning and tid != "personal":
            body = COMPLEX_FILE_WARNING_HTML + body
        return (EXCLUSION_NOTE_HTML if tid == "count" else "") + body

    rest = [
        _print_tab_body(tid, content)
        for tid, _, content in tab_entries
        if tid not in _skip_in_print
    ]
    all_sections = synopsis_print
    if totals_print:
        all_sections += "\n<div class='page-break'></div>\n" + totals_print
    if rest:
        all_sections += (
            "\n<div class='page-break'></div>\n"
            + "\n<div class='page-break'></div>\n".join(rest)
        )

    safe_name = html_mod.escape(client_name.strip()) if client_name.strip() else ""
    print_name = f"<div class='prt-name'>{safe_name}</div>" if safe_name else ""
    disclaimer = get_print_disclaimer_html()

    return f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="utf-8">
<title>ATLAS - Εκτύπωση</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{PRINT_STYLES}</style>
</head>
<body onload="window.print();">
{print_name}
<div class="prt-title">Ασφαλιστικό Βιογραφικό ATLAS</div>
{all_sections}
{disclaimer}
<div style="margin-top:12px;font-size:9px;color:#888;text-align:left;">© Syntaksi Pro - my advisor</div>
</body>
</html>"""


def build_viewer_html_document(
    tab_entries, client_name="", print_html="",
    download_filename="Αναφορά - Atlas.html", app_title="ATLAS",
    app_subtitle="Προεργασία φακέλου",     print_brand_suffix="Atlas",
    add_exclusion_note_for_count=True,
    print_styles=None,
    default_active_tab="timeline",
    full_save_suffix="ATLAS Pro.html",
    show_complex_warning=False,
    complex_modal_body_html="",
    excel_report_b64="",
    excel_export_enabled=False,
):
    """Κατασκευή πλήρους interactive HTML viewer (sidebar + tabs + JS)."""
    safe_name = html_mod.escape(client_name.strip()) if client_name.strip() else ""
    name_block = f'<div class="header-name">{safe_name}</div>' if safe_name else ""

    tab_ids = [tid for tid, _, _ in tab_entries]
    active_tid = (
        default_active_tab
        if default_active_tab in tab_ids
        else (tab_ids[0] if tab_ids else "synopsis")
    )

    nav_items = "\n".join(
        f'<a href="#" class="nav-item{" active" if tid == active_tid else ""}" '
        f'data-tab="{tid}" onclick="showTab(\'{tid}\');return false;">'
        f'{html_mod.escape(label)}</a>'
        for tid, label, _ in tab_entries
    )

    _cf_banner = _viewer_complex_file_banner_html() if show_complex_warning else ""
    tab_panes = "\n".join(
        f'<div id="pane-{tid}" class="tab-pane{" active" if tid == active_tid else ""}">'
        f'{EXCLUSION_NOTE_HTML if (add_exclusion_note_for_count and tid == "count") else ""}'
        f'{_inject_complex_warning_into_viewer_tab(content, _cf_banner) if tid != "personal" else content}'
        f"</div>"
        for tid, _, content in tab_entries
    )

    _complex_store = ""
    if show_complex_warning:
        _complex_store = (
            f'<div id="atlas-complex-reasons-store" class="atlas-tabinfo-body-store" '
            f'hidden="hidden">{complex_modal_body_html or ""}</div>'
        )

    print_js = json.dumps(print_html).replace("</script>", "<\\/script>")
    _styles = print_styles if print_styles is not None else PRINT_STYLES
    print_styles_js = json.dumps(_styles).replace("</script>", "<\\/script>")
    client_name_js = json.dumps(safe_name).replace("</script>", "<\\/script>")
    download_filename_js = json.dumps(download_filename)
    apodoxes_js = json.dumps(APODOXES_DESCRIPTIONS).replace("</script>", "<\\/script>")
    print_brand_suffix_js = json.dumps(print_brand_suffix).replace("</script>", "<\\/script>")
    full_save_suffix_js = json.dumps(full_save_suffix or "ATLAS Pro.html").replace(
        "</script>", "<\\/script>"
    )

    _sub_stripped = (app_subtitle or "").strip()
    _esc_title = html_mod.escape(app_title)
    _esc_sub = html_mod.escape(app_subtitle) if _sub_stripped else ""
    _doc_title = f"{_esc_title} - {_esc_sub}" if _sub_stripped else _esc_title
    _main_heading = _esc_sub if _sub_stripped else _esc_title
    _sidebar_small = f"<small>{_esc_sub}</small>" if _sub_stripped else ""

    _save_suffix_attr = html_mod.escape(
        (full_save_suffix or "ATLAS Pro.html").strip(), quote=True
    )
    _excel_btn = ""
    _excel_js_var = ""
    _excel_on = bool(excel_export_enabled or excel_report_b64)
    _sheetjs_script = (
        f"<script>{SHEETJS_JS}</script>" if (_excel_on and SHEETJS_JS) else ""
    )
    if _excel_on:
        _excel_btn = (
            '<button type="button" class="btn-action btn-excel" '
            'onclick="downloadExcelReport();" '
            'title="Εξαγωγή όλων των καρτελών σε ένα Excel (όπως εμφανίζονται)">'
            'Εξαγωγή Excel</button>'
        )

    return f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_doc_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{VIEWER_STYLES}</style>
{_sheetjs_script}
</head>
<body data-atlas-save-file="{_save_suffix_attr}">
<div class="app-layout">
  <nav class="sidebar">
    <div class="sidebar-header">{_esc_title}{_sidebar_small}</div>
    <div class="sidebar-nav">{nav_items}</div>
    <div class="sidebar-footer">
      <button type="button" class="btn-action btn-save" onclick="downloadFullHtml();">Πλήρης Αποθήκευση</button>
      {_excel_btn}
      <button type="button" class="btn-action btn-print" onclick="openPrint();">Εκτύπωση</button>
      <div class="sidebar-footer-copyright">© Syntaksi Pro - my advisor</div>
    </div>
  </nav>
  <main class="main-content">
    <div class="main-content-scroll">
    {name_block}
    <div class="main-title-wrap"><span id="main-title-person" class="main-title-person" aria-live="polite"></span><span class="main-title">{_main_heading}</span></div>
    <div class="tab-panes-container">
    {_complex_store}
    {tab_panes}
    </div>
    </div>
  </main>
</div>
<div id="toast-container"></div>
<div id="apodoxes-tooltip" class="apodoxes-tooltip" aria-hidden="true"></div>
<div id="tl-paketo-tooltip" class="apodoxes-tooltip" aria-hidden="true"></div>
{LITE_FILTER_MODAL_HTML}
<script>
var _apodoxesDescriptions = {apodoxes_js};
var _printHtml = {print_js};
var _printStyles = {print_styles_js};
var _clientName = {client_name_js};
var _downloadFilename = {download_filename_js};
var _printBrandSuffix = {print_brand_suffix_js};
var _fullSaveSuffix = {full_save_suffix_js};
{_excel_js_var}{VIEWER_JS}
</script>
<script>
{LITE_FILTER_MODAL_JS}
</script>
{SYNOPSIS_MODAL_HTML}
<script>
{SYNOPSIS_ENHANCE_JS}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Top-level convenience
# ---------------------------------------------------------------------------

def generate_full_html_report(df, client_name="", app_title="ATLAS",
                               app_subtitle="Προεργασία φακέλου",
                               full_save_suffix=None, edition="lite"):
    """Παράγει (viewer_html, print_html) από ένα DataFrame.

    edition: "lite" (προεπιλογή) ή "pro" (επιπλέον καρτέλες — βλ. build_report_tab_entries).
    """
    description_map = build_description_map(df)
    (
        audit_df,
        display_summary,
        _,
        _,
        tab_entries,
        show_complex_warning,
        complex_modal_body_html,
        excel_sheets,
    ) = build_report_tab_entries(df, description_map=description_map, edition=edition)

    # Η εξαγωγή Excel γίνεται πλέον ζωντανά (client-side, από το DOM) ώστε να
    # αντικατοπτρίζει φίλτρα/σύνολα «όπως εμφανίζονται». Δεν χρειάζεται το
    # προ-φτιαγμένο base64 workbook· κρατάμε μόνο flag ενεργοποίησης για Pro.
    excel_export_enabled = bool(edition == "pro" and excel_sheets)

    print_html = build_print_html_document(
        tab_entries,
        audit_df,
        display_summary,
        client_name=client_name,
        show_complex_warning=show_complex_warning,
    )

    dl_safe = re.sub(r'[<>:"/\\|?*]', '', (client_name or "Αναφορά").strip())[:60].strip() or "Αναφορά"
    download_filename = f"{dl_safe} - {app_title}.html"

    if full_save_suffix is None:
        full_save_suffix = (
            "ATLAS_Lite.html" if "lite" in (app_title or "").lower() else "ATLAS Pro.html"
        )

    viewer_html = build_viewer_html_document(
        tab_entries,
        client_name=client_name,
        print_html=print_html,
        download_filename=download_filename,
        app_title=app_title,
        app_subtitle=app_subtitle,
        print_brand_suffix=app_title,
        full_save_suffix=full_save_suffix,
        show_complex_warning=show_complex_warning,
        complex_modal_body_html=complex_modal_body_html,
        excel_export_enabled=excel_export_enabled,
    )
    return viewer_html, print_html


def build_frontend_viewer_html(df, client_name="", app_title="ATLAS Lite"):
    """
    Παράγει standalone HTML με το frontend UI (analysis.html + app.js + styles.css)
    και τα δεδομένα report embedded (window.__ATLAS_PAYLOAD__).
    Χρησιμοποιείται από τη Lite instance στο LOCAL_DEV.
    """
    from report_json_export import build_report_payload

    payload = build_report_payload(df, extra_df=None, client_name=client_name)
    frontend_dir = _root / "frontend_atlas"
    styles_path = frontend_dir / "styles.css"
    app_js_path = frontend_dir / "app.js"

    if not styles_path.exists() or not app_js_path.exists():
        raise FileNotFoundError(
            f"Frontend files not found: {frontend_dir}. Need styles.css and app.js."
        )

    styles_css = styles_path.read_text(encoding="utf-8")
    app_js = app_js_path.read_text(encoding="utf-8")

    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_json = payload_json.replace("</script>", "<\\/script>")
    app_js_safe = app_js.replace("</script>", "<\\/script>")

    analysis_body = """
  <div id="appRoot" class="min-h-screen flex flex-col">
    <header class="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur shrink-0">
      <div class="flex items-center justify-between gap-4 px-4 py-3">
        <span class="text-sm font-semibold text-slate-600">ATLAS Lite — Ανάλυση</span>
        <div class="flex items-center gap-3">
          <span id="currentYearBadge" class="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"></span>
          <span class="text-sm text-slate-500">""" + html_mod.escape(app_title) + """</span>
        </div>
      </div>
    </header>
    <main class="flex-1 flex flex-col min-h-0 w-full overflow-hidden">
      <div id="kpiStrip" class="hidden shrink-0"></div>
      <div id="globalMessages" class="hidden shrink-0"></div>
      <div class="flex-1 flex min-h-0 min-w-0 overflow-hidden">
        <aside id="tabsNav" class="panel shrink-0 w-52 overflow-y-auto overflow-x-hidden"></aside>
        <div id="tabContent" class="flex-1 min-w-0 overflow-x-hidden overflow-y-auto p-4 bg-slate-50/50"></div>
      </div>
    </main>
  </div>
  <div id="noDataRoot" class="hidden min-h-screen flex flex-col items-center justify-center px-4 bg-slate-50">
    <p class="text-slate-600 font-medium">Δεν υπάρχουν δεδομένα για προβολή.</p>
    <span class="mt-4 btn-primary inline-block">Φόρτωση αναφοράς</span>
  </div>"""

    html_doc = """<!doctype html>
<html lang="el">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>""" + html_mod.escape(app_title) + """ — Ανάλυση</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
""" + styles_css + """
  </style>
</head>
<body class="app-bg text-slate-800">
""" + analysis_body + """
  <script>window.__ATLAS_PAYLOAD__ = """ + payload_json + """;</script>
  <script>
""" + app_js_safe + """
  </script>
</body>
</html>"""
    return html_doc


# ---------------------------------------------------------------------------
# CSS & JS constants (at the end to keep the module readable)
# ---------------------------------------------------------------------------

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap');"
    "@import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap');"
)
FONT_MAIN = '"Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
FONT_METRICS = '"Fira Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif'

PRINT_STYLES = FONT_IMPORT + """
@media print { @page { size: A4 landscape; margin: 8mm; } }
@media print { .totals-filters { display: none !important; } .count-filters { display: none !important; } .totals-info-bar { display: none !important; } .totals-exceeded-wrap, .totals-exceeded-modal-overlay { display: none !important; } .section-actions { display: none !important; } .complex-file-warning { display: none !important; } .atlas-tabinfo-btn { display: none !important; } .lite-exclusion-note { display: none !important; } .tl-zoom-controls { display: none !important; } #tl-zoom-inner, #tl-paketo-zoom-inner { transform: none !important; } .tl-zoom-wrapper, .tl-paketo-zoom-scroll { overflow-x: hidden !important; } }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: """ + FONT_MAIN + """; color: #222; margin: 0; padding: 12px 16px; font-size: 11px; line-height: 1.4; background: #ffffff; }
.prt-name { text-align: center; font-size: 18px; font-weight: 800; margin-bottom: 2px; }
.prt-title { text-align: center; font-size: 14px; font-weight: 600; color: #555; margin-bottom: 14px; }
.page-break { page-break-after: always; }
.print-section { margin-bottom: 16px; --tl-print-label-w: min(140px, 30vw); }
.print-section h2 { font-size: 13px; font-weight: 700; color: #111; margin: 0 0 4px 0; padding-bottom: 3px; border-bottom: 1.5px solid #333; }
.print-description { font-size: 10px; color: #666; font-style: italic; margin: 0 0 6px 0; }
table.print-table { border-collapse: collapse; width: 100%; font-size: 10px; table-layout: fixed; }
table.print-table thead th { background: #f3f4f6; border-bottom: 1px solid #bbb; padding: 3px 3px; text-align: left; font-weight: 400; font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
table.print-table tbody td { border-bottom: 0.5px solid #ddd; padding: 2px 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
table.print-table tbody tr:nth-child(even) td { background: #fafafa; }
table.print-table tbody td:first-child { font-weight: 700; }
table.print-table tbody tr.total-row td { background: #dbeafe !important; font-weight: 700 !important; border-top: 1px solid #93c5fd; }
#count-tables-wrapper table.print-table tbody tr.total-row td,
#count-tables-wrapper table.print-table tbody tr[data-is-total="1"] td { background: #f5fafc !important; color: #000 !important; font-weight: 700 !important; border-top: 1px solid #c8dce8; }
#parallel-section table.print-table tbody tr.total-row td,
#parallel-section table.print-table tbody tr[data-is-total="1"] td { background: #f5fafc !important; color: #000 !important; font-weight: 700 !important; border-top: 1px solid #c8dce8; }
#count-tables-wrapper table.print-table tbody td.copy-target { transition: background-color 0.18s ease, box-shadow 0.18s ease; }
#count-tables-wrapper table.print-table tbody td.copy-target:hover { background-color: rgba(99, 102, 241, 0.14) !important; box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.38); }
/* Ομοιόμορφη/responsive κατανομή στηλών στην Καταμέτρηση (ίδια λογική με full screen): αγνόηση των fixed πλατών του colgroup */
#count-tables-wrapper table.print-table { table-layout: auto; }
#count-tables-wrapper table.print-table colgroup col { width: auto !important; }
#apd-tables-wrapper table.print-table.apd-table { table-layout: fixed; width: 100%; }
#apd-tables-wrapper table.print-table.apd-table colgroup col.apd-col-desc { width: 12% !important; max-width: 12%; }
#apd-tables-wrapper table.print-table.apd-table th.apd-c-desc,
#apd-tables-wrapper table.print-table.apd-table td.apd-c-desc { max-width: 12%; white-space: normal; word-break: break-word; }
#apd-tables-wrapper .apd-table-scroll { overflow: visible !important; }
table.print-table.apd-table tbody tr.apd-total-row td { background: #f5fafc !important; color: #000 !important; font-weight: 700 !important; border-top: 1px solid #c8dce8; }
table.print-table.apd-table tbody tr.apd-total-row td.apd-total-label { text-align: left; white-space: nowrap; }
table.print-table.apd-table tbody tr.apd-year-gap td { background: transparent !important; border: 0 !important; height: 10px; padding: 0; }
table.print-table.apd-table tbody tr.apd-data-row td.apd-cut { color: #d9534f; font-weight: 700; }
.apd-print-plafond { font-style: normal; font-weight: 600; color: #334155; }
table.print-table tbody td:nth-last-child(2),
table.print-table tbody td:nth-last-child(3) { font-weight: 700 !important; }
table.print-table.wrap-cells thead th, table.print-table.wrap-cells tbody td { white-space: normal; word-break: break-word; }
.year-section { margin-bottom: 10px; }
.year-heading { font-size: 12px; font-weight: 800; padding: 4px 0 2px 0; border-bottom: 1.5px solid #6f42c1; margin-bottom: 3px; }
.print-disclaimer { font-size: 9px; color: #888; margin-top: 16px; padding-top: 8px; border-top: 1px solid #ddd; line-height: 1.4; }
.print-disclaimer strong { color: #444; }
.lite-exclusion-note { text-align: right; font-size: 9px; color: #64748b; font-style: italic; margin-bottom: 4px; }
.count-filters { display: none !important; }
.totals-filters { display: none !important; }
.totals-info-bar { display: none !important; } .totals-exceeded-wrap, .totals-exceeded-modal-overlay { display: none !important; }
.print-section .tl-container { position: relative; padding-bottom: 28px; padding-top: 20px; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; }
.print-section .tl-row { display: flex; align-items: center; margin-bottom: 4px; min-height: 16px; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; }
.print-section .tl-label { width: var(--tl-print-label-w); max-width: var(--tl-print-label-w); font-size: 8px; font-weight: 600; color: #334155; text-align: right; padding-right: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; box-sizing: border-box; }
.tl-label-gap { color: #dc2626; } .tl-label-zero { color: #78716c; }
.print-section .tl-track { position: relative; flex: 1 1 0; min-width: 0; height: 14px; background: #f1f5f9; border-radius: 3px; }
.tl-bar { position: absolute; top: 1px; height: 12px; border-radius: 2px; opacity: 0.85; }
.tl-bar:hover { opacity: 1; box-shadow: 0 0 4px rgba(0,0,0,0.3); z-index: 2; }
.tl-gap { background: repeating-linear-gradient(45deg,#fca5a5,#fca5a5 2px,#fecaca 2px,#fecaca 4px) !important; border: 1px solid #ef4444; opacity: 0.7; }
.tl-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 2px,#d6d3d1 2px,#d6d3d1 4px) !important; border: 1px solid #78716c; opacity: 0.85; }
.tl-legend-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 2px,#d6d3d1 2px,#d6d3d1 4px) !important; border: 1px solid #78716c; }
.print-section .tl-axis { position: relative; height: 20px; margin-top: 2px; margin-left: calc(var(--tl-print-label-w) + 8px); border-top: 1px solid #cbd5e1; }
.print-section .tl-tick { position: absolute; top: 2px; font-size: 7px; color: #64748b; transform: translateX(-50%); }
.print-section .tl-tick::before { content: ''; position: absolute; top: -4px; left: 50%; width: 1px; height: 4px; background: #cbd5e1; }
.print-section .tl-ref-lines { position: absolute; left: var(--tl-print-label-w); right: 0; top: 0; bottom: 0; pointer-events: none; z-index: 0; }
.tl-ref-line { position: absolute; top: 0; bottom: 0; left: 0; display: flex; flex-direction: column; align-items: center; transform: translateX(-50%); }
.print-section .tl-ref-label { font-size: 8px; color: #64748b; white-space: nowrap; margin-bottom: 2px; font-weight: 600; }
.print-section .tl-ref-vline { flex: 1; width: 1px; min-height: 0; background: #64748b; opacity: 0.6; }
.print-section .tl-zoom-wrapper { margin-top: 8px; overflow-x: hidden; overflow-y: visible; max-height: none; border: none; background: transparent; max-width: 100%; box-sizing: border-box; }
.tl-zoom-controls { display: none !important; } #tl-zoom-inner, #tl-paketo-zoom-inner { transform: none !important; }
.print-section .tl-zoom-inner { display: block; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; padding: 0; }
.print-section .tl-legend { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; font-size: 8px; max-width: 100%; }
.tl-legend-item { display: inline-flex; align-items: center; gap: 3px; color: #334155; }
.tl-legend-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.print-section .tl-paketo-block { margin-top: 12px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; background: #fafafa; overflow: visible; max-width: 100%; box-sizing: border-box; }
.print-section .tl-paketo-zoom-scroll { overflow-x: hidden; overflow-y: visible; max-width: 100%; margin-top: 4px; box-sizing: border-box; }
.print-section .tl-paketo-block .tl-paketo-zoom-scroll .tl-zoom-inner { padding: 0; }
.print-section .tl-paketo-title { font-size: 11px; font-weight: 700; color: #1e293b; margin: 8px 0 4px; }
.print-section .tl-paketo-sub { font-size: 8px; color: #64748b; margin: 0 0 8px; max-width: 100%; line-height: 1.4; }
.print-section #tl-paketo-wrap .tl-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.print-section #tl-paketo-wrap .tl-label[title] { cursor: default; }
.audit-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: 16px; margin-bottom: 16px; align-items: start; min-width: 0; max-width: 100%; }
.audit-col { background: transparent; border: none; padding: 0; min-width: 0; max-width: 100%; }
.audit-stack { display: flex; flex-direction: column; gap: 10px; min-width: 0; max-width: 100%; }
.audit-layout .audit-row {
  display: grid; align-items: start; column-gap: 10px; row-gap: 4px;
  width: 100%; max-width: 100%; min-width: 0; overflow: hidden; box-sizing: border-box;
  padding: 10px 12px; background: #fff; border: 1.5px solid #cbd5e1; border-radius: 8px;
}
.audit-layout .audit-row--finding { background: #fff7ed; border-color: #f97316; }
.audit-row--left { grid-template-columns: minmax(0, 36%) minmax(0, 64%); }
.audit-row--right { grid-template-columns: minmax(0, 30%) minmax(0, 24%) minmax(0, 46%); }
.audit-row--left .audit-card-header { grid-column: 1; grid-row: 1; }
.audit-row--left .audit-card-result { grid-column: 2; grid-row: 1; }
.audit-row--left .audit-card-details { grid-column: 2; grid-row: 2; }
.audit-row--left .audit-card-actions { grid-column: 2; grid-row: 3; }
.audit-row--right .audit-card-header { grid-column: 1; }
.audit-row--right .audit-card-result { grid-column: 2; }
.audit-row--right .audit-card-details { grid-column: 3; }
.audit-row--right .audit-card-actions { grid-column: 2 / span 2; }
.audit-card { display: block; }
.audit-card-header { font-size: 11px; font-weight: 700; color: #334155; margin: 0; padding: 0; border: none; }
.audit-card-result { font-size: 12px; font-weight: 600; color: #111; margin: 0; }
.audit-card-details { font-size: 11px; color: #64748b; line-height: 1.45; margin: 0; min-width: 0; max-width: 100%; overflow-wrap: anywhere; word-break: break-word; white-space: normal; }
.audit-card-actions { margin: 0; padding: 0; border: none; font-size: 10px; color: #ef4444; font-weight: 600; min-width: 0; max-width: 100%; overflow-wrap: anywhere; word-break: break-word; }
.synopsis-title-btn { font: inherit; font-weight: 700; color: inherit; background: none; border: none; padding: 0; }
/* --- Συντάξιμες Αποδοχές — εκτύπωση (ίδιο layout με Streamlit) --- */
body.syntaksi-print-doc { font-family: "Fira Sans", -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #222; line-height: 1.45; padding: 8px; }
.syntaksi-print h1, body.syntaksi-print-doc h1 { font-size: 22px; font-weight: 700; margin: 14px 0 6px 0; text-align: center; color: #111827; letter-spacing: 0.2px; border: 0; padding: 0; }
.print-client-name { font-size: 26px; font-weight: 800; text-align: center; margin: 0 0 4px 0; color: #111827; letter-spacing: 0.3px; }
.syntaksi-print-calc-note { font-size: 11px !important; text-align: left !important; color: #6b7280 !important; font-style: normal !important; margin: 0 0 10px 0 !important; }
.print-synt-summary { margin: 6px 0 14px 0; padding: 12px 14px; background: #eef6ff; border: 1px solid #bfdbfe; border-radius: 6px; font-size: 11px; display: grid; gap: 10px 16px; align-items: start; }
.print-synt-summary--no-ex { grid-template-columns: minmax(0, 1fr) minmax(0, 1.85fr); }
.print-synt-summary--with-ex { grid-template-columns: minmax(0, 1fr) minmax(0, 0.65fr) minmax(0, 1.9fr); }
.print-synt-col-pk { min-width: 0; padding-right: 6px; border-right: 1px solid #bfdbfe; }
.print-synt-col-ex { min-width: 0; padding-right: 6px; border-right: 1px solid #bfdbfe; }
.print-synt-col-metrics { min-width: 0; padding-left: 2px; }
.print-synt-pk-h { font-weight: 700; font-size: 11px; color: #1e40af; margin-bottom: 6px; display: block; }
.print-synt-pk-txt { font-weight: 400; font-size: 11px; color: #1e293b; line-height: 1.45; word-break: break-word; }
.atlas-metrics-row { display: flex; flex-wrap: nowrap; gap: 12px; align-items: flex-start; justify-content: space-between; width: 100%; }
.atlas-metrics-row--print { flex-wrap: nowrap; gap: 12px; justify-content: space-between; }
.atlas-metric-item { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; flex: 1 1 0; min-width: 0; text-align: left; }
.atlas-metric-item--wide { flex: 1 1 0; min-width: 0; }
.atlas-metric-label { font-size: 11px; font-weight: 600; color: #6b7280; line-height: 1.25; white-space: nowrap; text-align: left; }
.atlas-metric-value { font-size: 22px; font-weight: 800; color: #111827; line-height: 1.1; letter-spacing: -0.02em; white-space: nowrap; }
.syntaksi-print table.print-table.syntaksi-table { border-collapse: collapse; width: 100%; font-size: 8.5px; table-layout: fixed; border: none; }
.syntaksi-print table.print-table.syntaksi-table thead th { background: #f3f4f6; border-bottom: 1px solid #d0d7de; padding: 4px 3px; text-align: left; font-weight: 700; color: #111827; font-size: 7.5px; vertical-align: bottom; }
.syntaksi-print table.print-table.syntaksi-table tbody td { border-bottom: 0.5px solid #e8eaed; padding: 2px 2px; }
.syntaksi-print table.print-table.syntaksi-table.wrap-cells thead th, .syntaksi-print table.print-table.syntaksi-table.wrap-cells tbody td { white-space: normal; overflow: visible; text-overflow: clip; word-break: break-word; }
.syntaksi-print table.print-table.syntaksi-table.wrap-cells thead th { line-height: 1.25; padding: 4px 3px; }
.syntaksi-print table.print-table.syntaksi-table tbody tr:nth-child(even) td { background-color: #f9fafb; }
.syntaksi-print table.print-table.syntaksi-table tbody td:first-child { font-weight: 700; }
.syntaksi-print table.print-table.syntaksi-table tbody tr.syn-parallel td { background: #fefce8 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.syntaksi-print table.print-table.syntaksi-table tbody tr.syn-total td { background: #fafdfe !important; color: #000 !important; font-weight: 700 !important; border-top: 1px solid #c8dce8; }
.syntaksi-layout .syntaksi-print-summary-mount .print-synt-summary { display: grid !important; }
.syntaksi-layout .syntaksi-print-summary-mount .syntaksi-print-calc-note { display: block !important; }
"""

VIEWER_STYLES = FONT_IMPORT + """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: """ + FONT_MAIN + """; color: #1e293b; background: #fff; }
.app-layout { display: flex; min-height: 100vh; }
.sidebar { width: 220px; min-width: 220px; background: #1e293b; color: #e2e8f0; display: flex; flex-direction: column; position: fixed; top: 0; left: 0; bottom: 0; z-index: 10; }
.sidebar-header { padding: 20px 16px 12px; border-bottom: 1px solid #334155; font-size: 20px; font-weight: 800; color: #fff; text-align: center; }
.sidebar-header small { display: block; font-size: 13px; font-weight: 400; color: #94a3b8; margin-top: 2px; }
.sidebar-nav { flex: 1; padding: 8px 12px; overflow-y: auto; }
.nav-item { display: block; padding: 10px 18px; color: #94a3b8; text-decoration: none; font-size: 16px; font-weight: 600; border-radius: 8px; transition: all .15s; margin-bottom: 6px; }
.nav-item:hover { background: rgba(51, 65, 85, 0.6); color: #e2e8f0; }
.nav-item.active { background: #eff6ff; color: #1d4ed8; }
.sidebar-footer { padding: 12px 16px; border-top: 1px solid #334155; display: flex; flex-direction: column; gap: 8px; }
.sidebar-footer-copyright { margin-top: auto; padding-top: 12px; font-size: 11px; color: #94a3b8; text-align: left; }
.btn-action { width: 100%; border: none; padding: 10px 0; border-radius: 6px; font-size: 14px; font-weight: 700; font-family: """ + FONT_MAIN + """; cursor: pointer; transition: background .15s; }
.btn-save { background: #2563eb; color: white; } .btn-save:hover { background: #1d4ed8; }
.btn-excel { background: #059669; color: white; } .btn-excel:hover { background: #047857; }
.btn-print { background: #dc3545; color: white; } .btn-print:hover { background: #b91c1c; }
html, body { height: 100%; min-height: 100vh; overflow: hidden; }
body { overflow-x: hidden; }
.app-layout { display: flex; height: 100vh; overflow: hidden; }
/* Κείμενο κύριας περιοχής: πιο σκούρο γκρι — το sidebar / μενού δεν αλλάζει */
.main-content { margin-left: 220px; flex: 1; padding: 24px 32px; min-width: 0; min-height: 0; overflow: hidden; display: flex; flex-direction: column; color: #0f172a !important; }
.main-content .main-title { color: #374151 !important; }
.main-content .lite-exclusion-note { color: #374151 !important; }
.main-content .print-section h2 { color: #111827 !important; }
.main-content .print-description { color: #374151 !important; }
.main-content table.print-table thead th { color: #111827 !important; font-weight: 500 !important; }
.main-content table.print-table tbody td { color: #111827 !important; }
.main-content table.print-table tbody td:first-child { color: #0f172a !important; }
.main-content table.print-table tbody tr.total-row td { color: #0f172a !important; }
.main-content .year-heading { color: #111827; }
.main-content .main-title-person { color: #111827; }
.main-content .audit-card-header { color: #1e293b; }
.main-content .audit-card-details { color: #374151 !important; }
.main-content .table-fullscreen .fs-title { color: #111827; }
.main-content .print-disclaimer { color: #374151 !important; }
.main-content .print-disclaimer strong { color: #1e293b; }
.main-content .tl-label,
.main-content .tl-legend-item,
.main-content #tl-paketo-wrap .tl-label-main { color: #1e293b; }
.main-content .tl-paketo-title { color: #111827; }
.main-content .tl-paketo-sub,
.main-content #tl-paketo-wrap .tl-label-meta { color: #374151 !important; }
.main-content .tl-zoom-label { color: #334155; }
.main-content .totals-summary-label,
.main-content .atlas-metric-label { color: #334155; }
.main-content .totals-summary-value,
.main-content .atlas-metric-value { color: #111827; }
.main-content .totals-filters .filter-label,
.main-content .count-filters .filter-label { color: #1e293b; }
.main-content .totals-filters .filter-cb,
.main-content .totals-filters .filter-modal-trigger,
.main-content .count-filters .filter-cb,
.main-content .count-filters .filter-modal-trigger { color: #1e293b; }
.main-content .filter-selected-label { color: #1e293b; }
.main-content .date-key-title { color: #111827; }
.main-content .date-key-label { color: #334155; }
.main-content .date-key-value { color: #111827; }
.main-content .date-key-desc { color: #374151 !important; }
.synopsis-modal-body { color: #334155; }
.synopsis-trunc-note { color: #374151 !important; }
.apodoxes-tooltip { color: #111827; }
.main-content-scroll { flex: 1; min-height: 0; overflow: auto; overflow-x: hidden; display: flex; flex-direction: column; }
.main-content.atlas-scroll-tab-active .main-content-scroll { overflow: hidden; }
.main-content.atlas-scroll-tab-active .tab-panes-container { overflow: hidden; }
.header-name { font-size: 22px; font-weight: 800; color: #111827; margin-bottom: 4px; }
.main-title-wrap { display: flex; align-items: baseline; gap: 14px; margin-bottom: 20px; flex-shrink: 0; flex-wrap: wrap; }
.main-title-person { font-size: 19px; font-weight: 700; color: #1e293b; margin-right: 12px; letter-spacing: 0.02em; }
.main-title { font-size: 19px; color: #64748b; font-weight: 600; }
.tab-pane { display: none; } .tab-pane.active { display: block; position: relative; }
#pane-count.tab-pane { display: none; }
.tab-panes-container .tab-pane.active:has(.atlas-tab-layout) { display: flex !important; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }
.tab-panes-container .tab-pane.active:has(.atlas-tab-layout--totals-page) { display: block !important; flex: none !important; min-height: auto !important; overflow: visible !important; }
.tab-panes-container { flex: 0 1 auto; min-width: 0; overflow-x: hidden; overflow-y: visible; display: block; -webkit-overflow-scrolling: touch; }
.main-content.atlas-scroll-tab-active .tab-panes-container,
.main-content.count-tab-active .tab-panes-container { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
#pane-synopsis .synopsis-col-disclaimer { margin-top: 4px; padding: 0 4px; }
#pane-synopsis .synopsis-col-disclaimer .print-disclaimer {
  margin: 0;
  padding: 0;
  border: none;
  font-size: 11px;
  line-height: 1.55;
  color: #64748b !important;
}
#pane-synopsis .synopsis-col-disclaimer .print-disclaimer strong { color: #475569 !important; }
.lite-exclusion-note { text-align: right; font-size: 11px; color: #64748b; font-style: italic; margin-bottom: 8px; }
.audit-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: 20px; margin-bottom: 24px; align-items: start; min-width: 0; max-width: 100%; }
.audit-col { background: transparent; border: none; border-radius: 0; padding: 0; box-shadow: none; min-width: 0; max-width: 100%; }
.audit-stack { display: flex; flex-direction: column; gap: 16px; min-width: 0; max-width: 100%; }
#pane-synopsis.tab-pane { max-width: 100%; min-width: 0; overflow-x: hidden; overflow-y: visible; box-sizing: border-box; padding-bottom: 0; }
#pane-synopsis .print-section { margin-bottom: 0; }
#pane-synopsis .audit-layout { margin-bottom: 0; }
#pane-synopsis .audit-layout { overflow-x: hidden; }
#pane-synopsis .audit-layout .audit-row,
.audit-layout .audit-row {
  display: grid;
  align-items: start;
  column-gap: 14px;
  row-gap: 8px;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
  padding: 16px 18px;
  background: #fff;
  border: 1.5px solid #cbd5e1;
  border-radius: 12px;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.07);
}
#pane-synopsis .audit-layout .audit-row--finding,
.audit-layout .audit-row--finding {
  background: #fff7ed;
  border-color: #f97316;
  box-shadow: 0 2px 10px rgba(249, 115, 22, 0.16);
}
#pane-synopsis .audit-layout .audit-row--info,
.audit-layout .audit-row--info {
  background: #eff6ff;
  border-color: #93c5fd;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
}
.audit-row--left { grid-template-columns: minmax(0, 36%) minmax(0, 64%); }
.audit-row--right { grid-template-columns: minmax(0, 30%) minmax(0, 22%) minmax(0, 48%); }
.audit-row--left .audit-card-header { grid-column: 1; grid-row: 1; align-self: start; min-width: 0; }
.audit-row--left .audit-card-result { grid-column: 2; grid-row: 1; min-width: 0; }
.audit-row--left .audit-card-details { grid-column: 2; grid-row: 2; min-width: 0; }
.audit-row--left .audit-card-actions { grid-column: 2; grid-row: 3; min-width: 0; }
.audit-row--right .audit-card-header { grid-column: 1; align-self: start; min-width: 0; }
.audit-row--right .audit-card-result { grid-column: 2; min-width: 0; }
.audit-row--right .audit-card-details { grid-column: 3; min-width: 0; }
.audit-row--right .audit-card-actions { grid-column: 2 / span 2; min-width: 0; }
.audit-card { display: block; }
.audit-card-clickable { cursor: pointer; }
#pane-synopsis .audit-layout .audit-row.audit-card-clickable:hover,
.audit-layout .audit-row.audit-card-clickable:hover {
  border-color: #6366f1;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.16);
}
#pane-synopsis .audit-layout .audit-row.audit-card-clickable.audit-row--finding:hover,
.audit-layout .audit-row.audit-card-clickable.audit-row--finding:hover {
  border-color: #ea580c;
  box-shadow: 0 4px 14px rgba(249, 115, 22, 0.22);
}
#pane-synopsis .audit-layout .audit-row.audit-card-clickable.audit-row--info:hover,
.audit-layout .audit-row.audit-card-clickable.audit-row--info:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.18);
}
.audit-row.audit-card-clickable:focus { outline: 2px solid #6366f1; outline-offset: 2px; }
#pane-synopsis .audit-card-header,
#pane-synopsis .audit-card-header .synopsis-title-btn,
#pane-synopsis .synopsis-title-btn {
  font-size: 18px !important;
  line-height: 1.4;
  font-weight: 700;
  color: #1e293b !important;
}
#pane-synopsis .audit-card-result {
  font-size: 16px !important;
  font-weight: 600;
  line-height: 1.45;
  color: #0f172a !important;
  cursor: default;
}
#pane-synopsis .audit-card-details,
#pane-synopsis .audit-card-details * {
  font-size: 14px !important;
  line-height: 1.55 !important;
  color: #475569 !important;
}
#pane-synopsis .audit-card-actions {
  font-size: 13px !important;
  line-height: 1.45;
}
#pane-synopsis .synopsis-trunc-note {
  font-size: 13px !important;
  line-height: 1.45;
}
#pane-synopsis .print-description {
  font-size: 16px;
  line-height: 1.5;
}
#pane-synopsis .audit-layout .audit-row {
  padding: 18px 20px;
  row-gap: 10px;
}
.audit-card-header { font-size: 14px; font-weight: 700; color: #334155; margin: 0; padding: 0; border: none; display: block; position: relative; z-index: 2; }
.synopsis-title-btn {
  display: inline;
  margin: 0;
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  font-weight: 700;
  color: inherit;
  text-align: left;
  line-height: 1.35;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: transparent;
  text-underline-offset: 3px;
  transition: color 0.15s, text-decoration-color 0.15s;
}
.synopsis-title-btn:hover,
.synopsis-title-btn:focus {
  color: #4f46e5;
  text-decoration-color: #6366f1;
  outline: none;
}
.audit-row--finding .synopsis-title-btn:hover,
.audit-row--finding .synopsis-title-btn:focus {
  color: #c2410c;
  text-decoration-color: #ea580c;
}
.audit-card-result { font-size: 15px; font-weight: 600; color: #0f172a; margin: 0; line-height: 1.35; min-width: 0; max-width: 100%; overflow-wrap: anywhere; word-break: break-word; }
.audit-card-details { font-size: 13px; color: #64748b; line-height: 1.5; margin: 0; position: relative; min-width: 0; max-width: 100%; overflow-wrap: anywhere; word-break: break-word; white-space: normal; }
.audit-card-details * { max-width: 100%; overflow-wrap: anywhere; word-break: break-word; }
.audit-card-actions { margin: 4px 0 0; padding: 0; border: none; font-size: 12px; color: #ef4444; font-weight: 600; min-width: 0; max-width: 100%; overflow-wrap: anywhere; word-break: break-word; }
.synopsis-title-btn { max-width: 100%; overflow-wrap: anywhere; word-break: break-word; }
@media (max-width: 960px) {
  .audit-layout { grid-template-columns: 1fr; }
  .audit-row--right { grid-template-columns: minmax(0, 38%) minmax(0, 62%); }
  .audit-row--right .audit-card-result { grid-column: 2; grid-row: 1; }
  .audit-row--right .audit-card-details { grid-column: 2; grid-row: 2; }
  .audit-row--right .audit-card-actions { grid-column: 2; grid-row: 3; }
}
/* Σύνοψη: stacked rows + modal λεπτομερειών */
#pane-synopsis .audit-layout { align-items: stretch; }
#pane-synopsis .audit-row--right .audit-card-details,
#pane-synopsis .audit-row--left .audit-card-details {
  max-height: 10.5em;
  overflow: hidden;
}
#pane-synopsis .audit-card-details.synopsis-details-faded::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 36px;
  background: linear-gradient(to bottom, rgba(255,255,255,0), #fff 85%);
  pointer-events: none;
}
#pane-synopsis .audit-row--finding .audit-card-details.synopsis-details-faded::after {
  background: linear-gradient(to bottom, rgba(255,247,237,0), #fff7ed 85%);
}
#pane-synopsis .audit-row--info .audit-card-details.synopsis-details-faded::after {
  background: linear-gradient(to bottom, rgba(239,246,255,0), #eff6ff 85%);
}
#pane-synopsis .audit-row.audit-card-clickable:hover .audit-card-details.synopsis-details-faded::after {
  background: linear-gradient(to bottom, rgba(255,255,255,0), #fff 85%);
}
#pane-synopsis .audit-row--info.audit-card-clickable:hover .audit-card-details.synopsis-details-faded::after {
  background: linear-gradient(to bottom, rgba(239,246,255,0), #eff6ff 85%);
}
.synopsis-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 99998;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.25s ease, visibility 0.25s ease;
}
.synopsis-modal-overlay.is-open {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}
.synopsis-modal {
  width: min(720px, 100%);
  max-height: min(78vh, 720px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(148, 163, 184, 0.15);
  overflow: hidden;
  transform: scale(0.96) translateY(12px);
  transition: transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.synopsis-modal-overlay.is-open .synopsis-modal {
  transform: scale(1) translateY(0);
}
/* Modal popups (Σύνοψη, ℹ, περίπλοκο κ.λπ.): ×1.5 κείμενο για ανάγνωση — νέα modals στο ίδιο μοτίβο */
.synopsis-modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 27px 30px 21px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
}
.synopsis-modal-head h3 {
  margin: 0;
  font-size: 25.5px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.3;
}
.synopsis-modal-close {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 33px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.synopsis-modal-close:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.synopsis-modal-body {
  padding: 24px 30px 30px;
  overflow-y: auto;
  font-size: 21px;
  line-height: 1.55;
  color: #475569;
  -webkit-overflow-scrolling: touch;
}
.synopsis-modal-body p { font-size: inherit; line-height: inherit; }
.synopsis-trunc-note {
  display: block;
  margin-top: 12px;
  font-size: 18px;
  color: #64748b;
  font-style: italic;
}
.atlas-tab-header-bar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px 16px;
  margin: 0 0 6px 0;
  padding-right: 96px;
  min-height: 52px;
  flex-wrap: wrap;
}
.atlas-tab-header-title {
  flex: 0 1 auto;
  min-width: 0;
}
.atlas-tab-header-title h2,
.atlas-tab-header-title .atlas-tab-title-row {
  margin: 0;
}
.atlas-tab-header-title .atlas-tab-title-row h2 {
  flex: 0 1 auto;
}
.atlas-tab-header-warning {
  flex: 1 1 200px;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.atlas-tab-header-warning .complex-file-warning {
  margin: 0;
  padding: 12px 14px;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.45;
  border: none;
  border-radius: 8px;
  background: rgba(254, 242, 242, 0.88);
  color: #991b1b;
  box-shadow: none;
}
.atlas-tab-header-warning .complex-file-readmore-btn {
  padding: 8px 16px;
  font-size: 14px;
}
.atlas-tab-title-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  text-align: left;
  margin: 0 0 6px 0;
  flex-wrap: wrap;
}
.atlas-tab-title-row h2 {
  margin: 0;
  flex: 1 1 auto;
  min-width: 0;
  text-align: left;
  font-weight: 700;
}
.atlas-tabinfo-btn {
  flex-shrink: 0;
  width: 33.6px;
  height: 33.6px;
  border-radius: 50%;
  border: 1.5px solid #0284c7;
  background: #f0f9ff;
  cursor: pointer;
  font-size: 17.6px;
  line-height: 1;
  color: #0369a1;
  padding: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.atlas-tabinfo-btn:hover {
  background: #e0f2fe;
  border-color: #0369a1;
}
.atlas-tabinfo-body-store {
  display: none !important;
}
.synopsis-modal-body .atlas-synopsis-block {
  margin: 0 0 18px 0;
  padding: 21px 24px;
  border-radius: 8px;
  font-size: 21px;
  line-height: 1.55;
  text-align: left;
}
.synopsis-modal-body .atlas-synopsis-block:last-child {
  margin-bottom: 0;
}
.synopsis-modal-body .atlas-synopsis-info {
  background: rgba(219, 234, 254, 0.55);
  border: none;
  color: #1e40af;
}
.synopsis-modal-body .atlas-synopsis-warning {
  background: rgba(254, 243, 199, 0.88);
  border: none;
  color: #b45309;
}
.complex-file-warning-viewer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-start;
  gap: 10px 14px;
  text-align: left;
}
.complex-file-readmore-btn {
  margin: 0;
  padding: 8px 14px;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  color: #991b1b;
  background: #fff;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
}
.complex-file-readmore-btn:hover {
  background: #fef2f2;
  border-color: #f87171;
}
.print-section { margin-bottom: 24px; }
.print-section h2 { font-size: 20px; font-weight: 700; color: #1e293b; margin: 0 0 6px 0; padding-bottom: 0; border-bottom: none; }
.print-description { font-size: 15px; color: #64748b; font-style: italic; margin: 0 0 12px 0; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; }
table.print-table { border-collapse: collapse; width: 100%; font-size: 15px; table-layout: auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
table.print-table thead th { background: #f8fafc; border-bottom: 2px solid #e2e8f0; padding: 11px 12px; text-align: left; font-weight: 500; color: #111827; font-size: 14px; white-space: nowrap; text-transform: uppercase; }
table.print-table tbody td { border-bottom: 1px solid #f1f5f9; padding: 9px 12px; color: #1f2937; }
table.print-table tbody tr:hover td { background: #f8fafc; }
table.print-table tbody td:first-child { font-weight: 700; color: #111827; }
table.print-table tbody tr.total-row td { background: #dbeafe !important; color: #111827; font-weight: 700 !important; border-top: 1px solid #93c5fd; }
table.print-table.wrap-cells thead th, table.print-table.wrap-cells tbody td { white-space: normal; word-break: break-word; }
.table-container { position: relative; } .print-section { position: relative; }
.section-actions { position: absolute; top: 6px; right: 6px; z-index: 5; display: flex; align-items: center; gap: 8px; opacity: 0.85; transition: opacity 0.2s; }
.table-container:hover .section-actions, .print-section:hover > .section-actions { opacity: 1; }
.btn-fs, .btn-print-tab { width: 40px; height: 40px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 1px solid transparent; transition: opacity 0.2s, background 0.15s, transform 0.15s; font-size: 18px; line-height: 1; }
.btn-fs { background: #e0e7ff; border-color: #a5b4fc; color: #4338ca; } .btn-fs:hover { background: #6366f1; color: #fff; border-color: #4f46e5; transform: scale(1.1); }
.btn-print-tab { background: #f0fdf4; border-color: #86efac; color: #15803d; } .btn-print-tab:hover { background: #22c55e; color: #fff; border-color: #16a34a; transform: scale(1.1); }
.btn-xls-tab { width: 40px; height: 40px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 1px solid #6ee7b7; background: #ecfdf5; color: #047857; transition: opacity 0.2s, background 0.15s, transform 0.15s; font-size: 18px; line-height: 1; }
.btn-xls-tab:hover { background: #059669; color: #fff; border-color: #047857; transform: scale(1.1); }
@media print { .btn-xls-tab { display: none !important; } }
.btn-json-syntaksi { height: 40px; padding: 0 14px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 1px solid #93c5fd; background: #eff6ff; color: #1d4ed8; font-size: 13px; font-weight: 600; font-family: """ + FONT_MAIN + """; white-space: nowrap; transition: background 0.15s, color 0.15s, border-color 0.15s, transform 0.15s; }
.btn-json-syntaksi:hover:not([disabled]) { background: #2563eb; color: #fff; border-color: #1d4ed8; transform: scale(1.03); }
.btn-json-syntaksi[disabled] { opacity: 0.5; cursor: not-allowed; }
.table-fullscreen .section-actions { display: none; }
.table-fullscreen { position: fixed; inset: 0; z-index: 10000; background: #fff; display: flex; flex-direction: column; }
.table-fullscreen .fs-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 12px 24px; border-bottom: 2px solid #e2e8f0; background: #f8fafc; flex-shrink: 0; }
.table-fullscreen .fs-title { font-size: 16px; font-weight: 700; color: #1e293b; }
.table-fullscreen .fs-toolbar-actions { display: flex; align-items: center; gap: 10px; }
.table-fullscreen .fs-print-btn { background: #dcfce7; border: 1px solid #86efac; border-radius: 8px; padding: 8px 16px; font-size: 14px; font-weight: 600; color: #15803d; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: background 0.15s, color 0.15s; }
.table-fullscreen .fs-print-btn:hover { background: #22c55e; color: #fff; border-color: #16a34a; }
.table-fullscreen .fs-json-btn { background: #eff6ff; border: 1px solid #93c5fd; border-radius: 8px; padding: 8px 16px; font-size: 14px; font-weight: 600; color: #1d4ed8; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: background 0.15s, color 0.15s; white-space: nowrap; }
.table-fullscreen .fs-json-btn:hover:not([disabled]) { background: #2563eb; color: #fff; border-color: #1d4ed8; }
.table-fullscreen .fs-json-btn[disabled] { opacity: 0.5; cursor: not-allowed; }
.table-fullscreen .fs-close { background: #fee2e2; border: 1px solid #fca5a5; border-radius: 8px; width: 38px; height: 38px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #dc2626; transition: all 0.15s; }
.table-fullscreen .fs-close:hover { background: #dc2626; color: #fff; }
.table-fullscreen .fs-body { flex: 1; overflow: auto; padding: 16px 24px; display: flex; flex-direction: column; min-height: 0; }
.table-fullscreen .fs-body:has(.atlas-tab-layout) { overflow: hidden; padding: 0; }
.table-fullscreen .fs-body:has(.atlas-tab-layout) .atlas-tab-layout { flex: 1; min-height: 0; }
.atlas-tab-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }
.atlas-tab-layout-top { flex-shrink: 0; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; background: #fff; }
.atlas-tab-layout-body { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
.atlas-tab-layout-body:has(.count-layout-middle) { overflow: hidden; display: flex; flex-direction: column; padding: 0; }
.atlas-tab-layout-body:has(.maindata-table-scroll) { overflow: hidden; display: flex; flex-direction: column; padding: 0; }
.atlas-tab-layout-body:has(.annex-table-scroll) { overflow: hidden; display: flex; flex-direction: column; padding: 0; }
#maindata-section { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }
#totals-section,
#totals-section.atlas-tab-layout--totals-page { display: block; flex: none; min-height: auto; overflow: visible; }
#totals-section .atlas-tab-layout-body { overflow: visible; flex: none; min-height: auto; display: block; padding: 0 2px; }
#totals-section .atlas-tab-layout-footer { flex-shrink: 0; padding: 0 2px 24px; }
#annex-section { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }
#maindata-section .atlas-tab-layout-top,
#maindata-section h2,
#maindata-section .print-description { flex-shrink: 0; }
#totals-section .atlas-tab-layout-top,
#totals-section h2,
#totals-section .print-description,
#totals-section .totals-filters,
#totals-section .totals-info-bar,
#totals-section .totals-exceeded-wrap { flex-shrink: 0; }
#totals-section .atlas-tab-layout-footer,
#totals-section .date-key-panel { flex-shrink: 0; }
#annex-section .atlas-tab-layout-top,
#annex-section h2,
#annex-section .print-description { flex-shrink: 0; }
.maindata-table-scroll { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
.totals-table-scroll { overflow: visible; background: #fff; padding: 0 2px; }
.totals-table-scroll table.print-table.totals-weighted thead th { position: sticky; top: 0; z-index: 3; background: #f8fafc; border-bottom: 2px solid #cbd5e1; box-shadow: 0 1px 0 #cbd5e1; }
.annex-table-scroll { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
.maindata-table-scroll table.print-table { border-collapse: separate; border-spacing: 0; overflow: visible; box-shadow: none; border-radius: 0; }
.maindata-table-scroll table.print-table thead th { position: sticky; top: 0; z-index: 3; background: #f8fafc; border-bottom: 2px solid #cbd5e1; box-shadow: 0 1px 0 #cbd5e1; }
.maindata-table-scroll table.print-table tbody tr.maindata-year-gap td { height: 26px; padding: 0; background: repeating-linear-gradient(45deg,#eef2f7,#eef2f7 6px,#f8fafc 6px,#f8fafc 12px); border-top: 2px solid #94a3b8 !important; border-bottom: 2px solid #94a3b8 !important; }
.count-layout .count-layout-top { flex-shrink: 0; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; background: #fff; }
.count-layout .count-layout-middle { flex: 1; min-height: 0; overflow: scroll; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
.count-layout .count-layout-bottom { display: none !important; }
.table-fullscreen .atlas-tab-layout-top,
.table-fullscreen .count-layout-top { display: none !important; }
/* Καταμέτρηση full screen: πακέτα + ημερομηνίες (custom + presets) σε μία γραμμή */
.table-fullscreen #count-section > .atlas-tab-layout-top { display: block !important; flex-shrink: 0; padding: 12px 20px 14px; border-bottom: 1px solid #e2e8f0; background: #f8fafc; }
.table-fullscreen #count-section > .atlas-tab-layout-top > *:not(#count-filters-bar) { display: none !important; }
.table-fullscreen #count-section #count-filters-bar.count-filters { display: block !important; margin: 0; padding: 0; background: transparent; border: none; border-radius: 0; }
.table-fullscreen #count-section .count-filters-grid { display: flex !important; flex-direction: row; flex-wrap: nowrap; align-items: center; gap: 12px 14px; }
.table-fullscreen #count-section .count-filters-grid > * { grid-column: auto !important; grid-row: auto !important; }
.table-fullscreen #count-section .count-filters-grid > .filter-modal-group:not([data-filter-key="klados"]),
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-apodox { display: none !important; }
.table-fullscreen #count-section .count-filters-grid > .filter-modal-group[data-filter-key="klados"] { flex: 0 1 300px; min-width: 200px; max-width: 340px; order: 1; }
.table-fullscreen #count-section .count-filters-grid > .filter-modal-group[data-filter-key="klados"] .filter-selected-label { display: none; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-from { flex: 0 0 132px; min-width: 120px; order: 2; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-to { flex: 0 0 132px; min-width: 120px; order: 3; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-row2 { flex: 1 1 auto; min-width: 0; display: flex !important; flex-wrap: nowrap; align-items: center; gap: 12px 14px; margin: 0; padding: 0; order: 4; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-row2 .count-date-presets-bar { order: 1; flex: 1 1 auto; min-width: 0; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-row2 .cnt-grid-cbs { display: flex !important; flex: 0 0 auto; flex-shrink: 0; order: 2; margin: 0; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-row2 .cnt-grid-cbs .filter-cb:has(#cnt-year-sparse) { display: none !important; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-row2 .cnt-grid-cbs .filter-cb { font-size: 16px; white-space: nowrap; margin: 0; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-reset { flex: 0 0 auto; order: 5; margin-left: auto; }
.table-fullscreen #count-section .count-date-presets-bar { display: flex !important; flex-wrap: nowrap; gap: 10px; overflow-x: auto; overflow-y: hidden; min-width: 0; width: auto; margin: 0; padding: 0; grid-template-columns: unset; -webkit-overflow-scrolling: touch; }
.table-fullscreen #count-section .count-preset-btn { flex: 0 0 auto; width: auto; min-width: 0; padding: 10px 14px; font-size: 14px; line-height: 1.25; font-weight: 600; white-space: nowrap; }
.table-fullscreen #count-section .count-filters .filter-date { padding: 10px 14px; font-size: 16px; }
.table-fullscreen #count-section .count-filters .filter-modal-trigger { padding: 10px 14px; font-size: 16px; }
.table-fullscreen #count-section .count-filters .filter-modal-badge { min-width: 24px; height: 24px; line-height: 24px; font-size: 13px; }
.table-fullscreen #count-section .count-filters-grid > .cnt-grid-reset .filter-reset-btn { margin-left: 0; padding: 10px 14px; font-size: 22px; }
.table-fullscreen .atlas-tab-layout,
.table-fullscreen .count-layout { display: flex !important; flex-direction: column !important; height: 100% !important; }
.table-fullscreen .atlas-tab-layout-body,
.table-fullscreen .count-layout-middle,
.table-fullscreen .maindata-table-scroll { flex: 1 !important; min-height: 0 !important; overflow: auto !important; }
.table-fullscreen .maindata-table-scroll table.print-table { border-collapse: separate; border-spacing: 0; overflow: visible; box-shadow: none; border-radius: 0; }
.table-fullscreen .maindata-table-scroll table.print-table thead th { position: sticky; top: 0; z-index: 3; background: #f8fafc; border-bottom: 2px solid #cbd5e1; }
.table-fullscreen .atlas-tab-layout { display: flex !important; flex-direction: column !important; height: 100% !important; }
.table-fullscreen .fs-body:has(.atlas-tab-layout--totals-page) { overflow: auto !important; }
.table-fullscreen .fs-body:has(.atlas-tab-layout--totals-page) .atlas-tab-layout--totals-page { height: auto !important; flex: none !important; min-height: auto !important; overflow: visible !important; }
.table-fullscreen .fs-body:has(.atlas-tab-layout--totals-page) .atlas-tab-layout-body { overflow: visible !important; flex: none !important; min-height: auto !important; }

/* ΑΠΔ / Πλαφόν (Pro) */
.atlas-tab-layout-body:has(.apd-table-scroll) { overflow: hidden; display: flex; flex-direction: column; padding: 0; }
#apd-tables-mount { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.apd-table-scroll { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
.apd-table-scroll table.print-table { border-collapse: separate; border-spacing: 0; overflow: visible; box-shadow: none; border-radius: 0; font-size: 15px; }
/* ΑΠΔ: ποσοστιαία πλάτη + fixed layout — ίδια λογική με count-unified */
#apd-tables-wrapper table.print-table.apd-table,
.apd-table-scroll table.print-table.apd-table { table-layout: fixed; width: 100%; }
.apd-table-scroll table.print-table thead th { position: sticky; top: 0; z-index: 6; background: #f8fafc; border-bottom: 2px solid #cbd5e1; box-shadow: 0 1px 0 #cbd5e1; white-space: normal; padding: 6px 8px; font-size: 14px; line-height: 1.2; vertical-align: bottom; font-weight: 500 !important; color: #111827; }
.apd-table-scroll table.print-table tbody td { font-size: 15px; padding: 6px 8px; word-break: break-word; color: #1f2937; }
.apd-table-scroll table.print-table tbody tr.apd-year-gap td { height: 36px; padding: 0; background: transparent; border: 0 !important; }
.apd-table-scroll table.print-table tbody tr.apd-total-row td { background: #f5fafc !important; color: #000 !important; font-weight: 700 !important; border-top: 1px solid #c8dce8; }
.apd-table-scroll table.print-table tbody tr.apd-data-row.apd-low td { background: #fff8e1; }
.apd-table-scroll table.print-table tbody tr.apd-data-row td.apd-cut { color: #d9534f; font-weight: 700; }
.apd-table-scroll table.print-table tbody tr.apd-total-row td.apd-total-label { text-align: left; white-space: nowrap; }
.table-fullscreen .apd-table-scroll { flex: 1 !important; min-height: 0 !important; overflow: auto !important; }
.table-fullscreen .apd-table-scroll table.print-table { border-collapse: separate; border-spacing: 0; overflow: visible; box-shadow: none; border-radius: 0; }
.table-fullscreen .apd-table-scroll table.print-table thead th { position: sticky; top: 0; z-index: 6; background: #f8fafc; border-bottom: 2px solid #cbd5e1; box-shadow: 0 1px 0 #cbd5e1; }
.table-fullscreen .apd-table-scroll table.print-table tbody tr.apd-total-row td { background: #f5fafc !important; color: #000 !important; font-weight: 700 !important; border-top: 1px solid #c8dce8; }
.table-fullscreen .apd-table-scroll table.print-table tbody tr.apd-data-row td.apd-cut { color: #d9534f; font-weight: 700; }
/* Στήλες ΑΠΔ: νομισματικές/ποσοστό δεξιά χωρίς αναδίπλωση· περιγραφές αναδιπλώνονται */
.apd-table-scroll table.print-table th.apd-c-money, .apd-table-scroll table.print-table td.apd-c-money,
.apd-table-scroll table.print-table th.apd-c-pct, .apd-table-scroll table.print-table td.apd-c-pct { text-align: right; white-space: nowrap; }
.apd-table-scroll table.print-table th.apd-c-pkg, .apd-table-scroll table.print-table td.apd-c-pkg { white-space: nowrap; }
.apd-table-scroll table.print-table th.apd-c-desc, .apd-table-scroll table.print-table td.apd-c-desc { white-space: normal; word-break: break-word; }
/* Full screen: περισσότερο πλάτος στις περιγραφές (όπως ΠΕΡΙΓΡΑΦΗ στην Καταμέτρηση) */
.table-fullscreen .fs-body #apd-tables-wrapper table.print-table.apd-table colgroup col.apd-col-desc { width: 12% !important; }
#apd-section h2, #apd-section .atlas-tab-layout-top h2,
#apd-section .print-description, #apd-section .atlas-tab-layout-top .print-description,
#apd-section .apd-filters { flex-shrink: 0; }
/* ΑΠΔ φίλτρα — ίδιο grid pattern με Καταμέτρηση (ομοιόμορφες στήλες + στοίχιση) */
.apd-filters-grid { display: grid; grid-template-columns: repeat(3, minmax(150px, 1fr)) 118px 118px minmax(200px, 1.1fr) auto; grid-template-rows: auto auto; gap: 12px 14px; align-items: start; }
.apd-filters-grid > div { min-width: 0; }
.apd-filters-grid > .apd-grid-tameio { grid-column: 1; grid-row: 1; }
.apd-filters-grid > .apd-grid-klados { grid-column: 2; grid-row: 1; }
.apd-filters-grid > .apd-grid-apodox { grid-column: 3; grid-row: 1; }
.apd-filters-grid > .apd-grid-from { grid-column: 4; grid-row: 1; }
.apd-filters-grid > .apd-grid-to { grid-column: 5; grid-row: 1; }
.apd-filters-grid > .apd-grid-pct { grid-column: 1; grid-row: 2; align-self: end; }
.apd-filters-grid > .apd-grid-retmode { grid-column: 2; grid-row: 2; align-self: end; }
.apd-filters-grid > .apd-grid-high { grid-column: 3; grid-row: 2; align-self: end; }
.apd-filters-grid > .apd-grid-plafond { grid-column: 4 / 6; grid-row: 2; align-self: end; }
.apd-filters-grid > .apd-grid-cbs { grid-column: 6; grid-row: 2; display: flex; align-items: flex-end; align-self: end; min-height: 0; }
.apd-filters-grid > .apd-grid-reset { grid-column: 7; grid-row: 2; justify-self: end; align-self: center; }
.apd-filters-grid .filter-modal-group { min-width: 0; }
.apd-filters-grid .filter-modal-trigger { min-width: 0; width: 100%; box-sizing: border-box; }
.apd-filters-grid .filter-date { width: 100%; box-sizing: border-box; min-width: 0; }
.apd-filters-grid .apd-grid-reset .filter-reset-btn { margin-left: 0; }
.apd-filter-field { display: flex; flex-direction: column; gap: 10px; width: 100%; min-width: 0; box-sizing: border-box; }
.apd-filter-field-label { font-size: 13px; font-weight: 400; color: #1e293b; line-height: 1.2; }
.apd-filter-input, .apd-filters .apd-select { width: 100%; box-sizing: border-box; padding: 10px 14px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; color: #334155; font-family: inherit; min-height: 44px; }
.apd-filters .apd-select { appearance: auto; cursor: pointer; }
.apd-filter-input:hover, .apd-filters .apd-select:hover { border-color: #6366f1; }
.apd-filter-input:focus, .apd-filters .apd-select:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.apd-filters .filter-date { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; font-family: inherit; color: #334155; background: #fff; min-height: 44px; }
.apd-filters .filter-date:hover { border-color: #6366f1; }
.apd-filters .filter-date:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.apd-filters .filter-date::placeholder { color: #94a3b8; opacity: 1; font-weight: 400; }
.apd-filters-grid > .apd-grid-cbs .filter-cb { margin: 0; padding-bottom: 10px; white-space: nowrap; }
@media (max-width: 1100px) {
.apd-filters-grid { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
.apd-filters-grid > .apd-grid-tameio,
.apd-filters-grid > .apd-grid-klados,
.apd-filters-grid > .apd-grid-apodox,
.apd-filters-grid > .apd-grid-from,
.apd-filters-grid > .apd-grid-to,
.apd-filters-grid > .apd-grid-pct,
.apd-filters-grid > .apd-grid-retmode,
.apd-filters-grid > .apd-grid-high,
.apd-filters-grid > .apd-grid-plafond,
.apd-filters-grid > .apd-grid-cbs,
.apd-filters-grid > .apd-grid-reset { grid-column: auto; grid-row: auto; align-self: stretch; }
.apd-filters-grid > .apd-grid-from,
.apd-filters-grid > .apd-grid-to { grid-column: span 1; }
.apd-filters-grid > .apd-grid-plafond { grid-column: 1 / -1; }
.apd-filters-grid > .apd-grid-reset { justify-self: end; }
}
#count-section h2, #count-section .atlas-tab-layout-top h2,
#count-section .print-description, #count-section .atlas-tab-layout-top .print-description,
#count-section .count-filters, #count-section .count-date-presets-bar,
#count-section .count-kind-metrics { flex-shrink: 0; }
#count-section .count-kind-metrics { margin-top: 12px; }
#count-tables-wrapper .year-section { margin-bottom: 20px; }
#count-section.count-year-sparse #count-tables-wrapper .year-section { margin-bottom: 80px; }
#count-tables-wrapper .year-heading { font-size: 15px; font-weight: 800; padding: 8px 0 6px 0; border-bottom: 2px solid #6366f1; margin-top: 3px; margin-bottom: 11px; }
#count-tables-wrapper table.print-table thead th { font-weight: 500 !important; }
#count-tables-wrapper table.print-table tbody tr.total-row td,
#count-tables-wrapper table.print-table tbody tr[data-is-total="1"] td {
  background: #f5fafc !important;
  color: #000 !important;
  font-weight: 700 !important;
  border-top: 1px solid #c8dce8;
}
#parallel-section table.print-table tbody tr.total-row td,
#parallel-section table.print-table tbody tr[data-is-total="1"] td {
  background: #f5fafc !important;
  color: #000 !important;
  font-weight: 700 !important;
  border-top: 1px solid #c8dce8;
}
.table-fullscreen .fs-body table.print-table:not(.count-unified) { table-layout: auto; font-size: 16px; }
.table-fullscreen .fs-body table.print-table colgroup { display: table-column-group; }
.table-fullscreen .fs-body table.print-table:not(.count-unified) colgroup col { width: auto !important; }
.table-fullscreen .fs-body table.print-table thead th { padding: 12px 14px; font-size: 15px; font-weight: 500; text-transform: uppercase; position: sticky; top: 0; z-index: 2; background: #f8fafc; color: #111827; }
.table-fullscreen .fs-body table.print-table tbody td { padding: 10px 14px; color: #111827; }
.apodoxes-tooltip { position: fixed; z-index: 100000; max-width: 340px; padding: 14px 18px; font-size: 15px; line-height: 1.5; color: #1e293b; background: #fff; border-radius: 12px; box-shadow: 0 12px 48px rgba(0,0,0,0.14), 0 4px 16px rgba(99,102,241,0.08); border: 1px solid #e2e8f0; pointer-events: none; opacity: 0; visibility: hidden; transition: opacity 0.2s, visibility 0.2s, transform 0.15s; transform: translateY(4px); }
.apodoxes-tooltip.visible { opacity: 1; visibility: visible; transform: translateY(0); }
.has-apodoxes-tooltip { cursor: help; }
.cell-description { max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; }
@media print { .section-actions { display: none !important; } .btn-fs { display: none !important; } .btn-print-tab { display: none !important; } .apodoxes-tooltip { display: none !important; } #tl-paketo-tooltip { display: none !important; } .totals-filters { display: none !important; } .count-filters { display: none !important; } .count-date-presets-bar { display: none !important; } .totals-info-bar { display: none !important; } .syntaksi-metrics.totals-info-bar { display: flex !important; } .totals-exceeded-wrap, .totals-exceeded-modal-overlay { display: none !important; } .lite-filter-modal-overlay { display: none !important; } .complex-file-warning { display: none !important; } .atlas-tabinfo-btn { display: none !important; } .complex-file-readmore-btn { display: none !important; } .lite-exclusion-note { display: none !important; } .tl-zoom-controls { display: none !important; } #tl-zoom-inner, #tl-paketo-zoom-inner { transform: none !important; } .tl-zoom-wrapper, .tl-paketo-zoom-scroll { overflow-x: hidden !important; } .personal-form { display: none !important; } .personal-notes { display: none !important; } .synopsis-modal-overlay, .synopsis-expand-btn { display: none !important; } }
.year-section { margin-bottom: 20px; }
.year-heading { font-size: 15px; font-weight: 800; color: #1e293b; padding: 8px 0 4px 0; border-bottom: 2px solid #6366f1; margin-bottom: 6px; }
.print-disclaimer { font-size: 12px; color: #64748b; margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; line-height: 1.6; }
.print-disclaimer strong { color: #374151; }
.tl-container { position: relative; padding-bottom: 36px; padding-top: 26px; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; }
.tl-row { display: flex; align-items: center; margin-bottom: 8px; min-height: 28px; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; }
.tl-label { font-size: 13px; font-weight: 600; color: #334155; text-align: right; padding-right: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; box-sizing: border-box; }
.tl-label-gap { color: #dc2626; } .tl-label-zero { color: #78716c; }
.tl-track { position: relative; flex: 1 1 0; min-width: 0; height: 24px; background: #f1f5f9; border-radius: 6px; }
.tl-bar { position: absolute; top: 2px; height: 20px; border-radius: 4px; opacity: 0.85; cursor: default; transition: opacity 0.15s; }
.tl-bar:hover { opacity: 1; box-shadow: 0 0 6px rgba(0,0,0,0.25); z-index: 2; }
.tl-gap { background: repeating-linear-gradient(45deg,#fca5a5,#fca5a5 3px,#fecaca 3px,#fecaca 6px) !important; border: 1px solid #ef4444; opacity: 0.7; }
.tl-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 3px,#d6d3d1 3px,#d6d3d1 6px) !important; border: 1px solid #78716c; opacity: 0.85; }
.tl-legend-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 3px,#d6d3d1 3px,#d6d3d1 6px) !important; border: 1px solid #78716c; }
.tl-period-range { text-align: center; font-size: 18px; font-weight: 700; color: #1e293b; margin: 0 0 16px 0; letter-spacing: 0.01em; font-style: normal; }
.tl-zoom-wrapper { margin-top: 8px; border: 1px solid #e2e8f0; border-radius: 10px; overflow-x: hidden; overflow-y: auto; max-height: 75vh; min-height: 420px; background: #fafafa; max-width: 100%; box-sizing: border-box; }
.tl-zoom-controls { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }
.tl-zoom-label { font-size: 13px; font-weight: 600; color: #475569; }
.tl-zoom-btn { padding: 6px 12px; font-size: 12px; font-weight: 600; color: #64748b; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer; transition: all 0.15s; }
.tl-zoom-btn:hover { background: #e2e8f0; color: #334155; border-color: #94a3b8; }
.tl-zoom-btn.active { background: #6366f1; color: #fff; border-color: #4f46e5; }
.tl-zoom-inner { display: block; width: 100%; max-width: 100%; min-width: 0; box-sizing: border-box; transform-origin: top left; transition: transform 0.2s ease; padding: 12px 16px; }
.tl-axis { position: relative; height: 28px; margin-top: 4px; border-top: 1px solid #cbd5e1; }
.tl-tick { position: absolute; top: 4px; font-size: 11px; color: #64748b; transform: translateX(-50%); }
.tl-tick::before { content: ''; position: absolute; top: -6px; left: 50%; width: 1px; height: 6px; background: #cbd5e1; }
.tl-ref-lines { position: absolute; right: 0; top: 0; bottom: 0; pointer-events: none; z-index: 0; }
.tl-ref-line { position: absolute; top: 0; bottom: 0; left: 0; display: flex; flex-direction: column; align-items: center; transform: translateX(-50%); }
.tl-ref-label { font-size: 10px; color: #64748b; white-space: nowrap; margin-bottom: 4px; font-weight: 600; }
.tl-ref-vline { flex: 1; width: 1px; min-height: 0; background: #64748b; opacity: 0.7; }
.tl-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; font-size: 13px; max-width: 100%; }
.tl-legend-item { display: inline-flex; align-items: center; gap: 6px; color: #334155; }
.tl-legend-dot { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.tl-paketo-block { margin-top: 20px; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; background: #fafafa; overflow: visible; max-width: 100%; box-sizing: border-box; }
.tl-paketo-zoom-scroll { overflow-x: hidden; overflow-y: visible; max-width: 100%; margin-top: 4px; box-sizing: border-box; }
.tl-paketo-block .tl-paketo-zoom-scroll .tl-zoom-inner { padding: 0; }
.tl-paketo-block .tl-paketo-title { margin-top: 0; }
.tl-paketo-title { font-size: 1.05rem; font-weight: 700; color: #1e293b; margin: 20px 0 6px; }
.tl-paketo-sub { font-size: 13px; color: #64748b; margin: 0 0 12px; max-width: 920px; line-height: 1.45; }
#tl-paketo-wrap .tl-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#tl-paketo-wrap .tl-label[title] { cursor: help; }
#tl-paketo-wrap .tl-label.tl-label-cell { min-width: 0; display: flex; flex-direction: column; align-items: stretch; justify-content: center; white-space: normal; overflow: visible; box-sizing: border-box; }
#tl-paketo-wrap .tl-label-main { font-family: inherit; font-size: 13px; font-weight: 600; color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; text-align: right; }
#tl-paketo-wrap .tl-label-meta { margin-top: 1px; font-size: 9px; line-height: 1.15; color: #64748b; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; font-weight: 400; text-align: right; box-sizing: border-box; }
#tl-paketo-wrap .tl-bar.has-tl-paketo-tooltip { cursor: help; }
#pane-timeline.tab-pane { max-width: 100%; min-width: 0; box-sizing: border-box; }
#pane-timeline { --tl-label-w: min(200px, 36vw); }
#pane-timeline .tl-label { width: var(--tl-label-w); max-width: var(--tl-label-w); }
#pane-timeline .tl-ref-lines { left: var(--tl-label-w); }
#pane-timeline .tl-axis { margin-left: calc(var(--tl-label-w) + 14px); }
.totals-info-bar { display: flex; flex-wrap: nowrap; align-items: stretch; gap: 14px; margin-bottom: 20px; padding: 0; background: transparent; border: none; }
.totals-info-bar.atlas-header-split { margin-bottom: 20px; }
.totals-info-bar-warning { background: transparent; border: none; }
.totals-info-bar-warning .atlas-header-info,
.totals-info-bar:not(.totals-info-bar-warning) .atlas-header-info { padding: 0; background: transparent; border: none; }
.totals-info-msg {
  font-size: 15px; font-weight: 600; flex: 1; min-width: 0;
  padding: 12px 14px; border: none; border-radius: 8px; line-height: 1.45; box-sizing: border-box;
}
.totals-info-bar-warning .totals-info-msg,
.totals-info-bar-warning .atlas-header-info .totals-info-msg {
  background: rgba(254, 243, 199, 0.88); color: #b45309;
}
.totals-info-bar:not(.totals-info-bar-warning) .totals-info-msg,
.totals-info-bar:not(.totals-info-bar-warning) .atlas-header-info .totals-info-msg {
  background: rgba(219, 234, 254, 0.55); color: #1e40af;
}
.totals-exceeded-wrap { margin-bottom: 16px; }
.totals-exceeded-compact {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 14px;
  padding: 12px 14px;
  background: rgba(254, 243, 199, 0.88);
  border: none;
  border-radius: 8px;
  font-size: 15px;
  color: #b45309;
  line-height: 1.45;
}
.totals-exceeded-compact-text { flex: 1 1 auto; min-width: 200px; }
.totals-exceeded-modal-btn {
  flex: 0 0 auto;
  margin-left: auto;
  padding: 5px 11px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  line-height: 1.25;
  white-space: nowrap;
  color: #78350f;
  background: #fff;
  border: 1px solid #d97706;
  border-radius: 6px;
  cursor: pointer;
}
.totals-exceeded-modal-btn:hover { background: #fffbeb; }
.totals-exceeded-modal-intro { margin: 0 0 18px 0; font-size: 19.5px; color: #64748b; }
.totals-exceeded-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 99997;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.25s ease, visibility 0.25s ease;
}
.totals-exceeded-modal-overlay.is-open {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}
.totals-exceeded-modal-panel {
  width: min(720px, 100%);
  max-height: min(85vh, 880px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(148, 163, 184, 0.15);
  overflow: hidden;
  transform: scale(0.96) translateY(12px);
  transition: transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.totals-exceeded-modal-overlay.is-open .totals-exceeded-modal-panel {
  transform: scale(1) translateY(0);
}
.totals-exceeded-modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 27px 30px 21px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #fffbeb 0%, #fff 100%);
  flex-shrink: 0;
}
.totals-exceeded-modal-head h3 {
  margin: 0;
  font-size: 25.5px;
  font-weight: 800;
  color: #78350f;
  line-height: 1.3;
}
.totals-exceeded-modal-close {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: #fef3c7;
  color: #92400e;
  font-size: 33px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.totals-exceeded-modal-close:hover {
  background: #fde68a;
  color: #451a03;
}
.totals-exceeded-modal-body {
  padding: 24px 30px 30px;
  overflow-y: auto;
  font-size: 21px;
  line-height: 1.55;
  color: #475569;
  -webkit-overflow-scrolling: touch;
  flex: 1 1 auto;
  min-height: 0;
}
.totals-exceeded-modal-body p { font-size: inherit; line-height: inherit; }
.atlas-header-split { display: flex; flex-direction: row; align-items: stretch; gap: 14px; width: 100%; }
.atlas-header-split--metrics-only { justify-content: flex-end; }
.atlas-header-split--metrics-only .atlas-metrics-frame { flex: 0 0 66.666%; max-width: 66.666%; }
.atlas-header-info { flex: 0 0 33.333%; max-width: 33.333%; min-width: 0; }
.atlas-metrics-frame {
  flex: 1 1 66.666%; min-width: 0; padding: 14px 18px;
  background: rgba(255, 255, 255, 0.88); border: 1px solid #bfdbfe; border-radius: 8px;
  display: flex; align-items: center;
}
.atlas-info-box {
  padding: 12px 14px; background: rgba(219, 234, 254, 0.55); border: none;
  border-radius: 8px; min-height: 100%; box-sizing: border-box;
}
.atlas-info-box-title { font-weight: 700; font-size: 15px; color: #1e40af; margin-bottom: 6px; }
.atlas-info-box-body { font-size: 15px; color: #1e293b; line-height: 1.45; word-break: break-word; }
.atlas-warn-box {
  padding: 12px 14px; background: rgba(254, 243, 199, 0.88); border: none;
  border-radius: 8px; font-size: 15px; font-weight: 600; color: #b45309; line-height: 1.45;
}
.atlas-metrics-row, .totals-summary { display: flex; flex-wrap: nowrap; gap: 12px; justify-content: space-between; align-items: flex-start; width: 100%; margin-left: 0; }
.tab-metrics-bar { margin: 12px 0 20px; width: 100%; }
.atlas-metric-item, .totals-summary-item { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; text-align: left; min-width: 0; flex: 1 1 0; }
.atlas-metric-item--wide { flex: 1 1 0; min-width: 0; }
.atlas-metric-label, .totals-summary-label { font-size: 13px; font-weight: 600; color: #475569; text-align: left; line-height: 1.25; font-family: """ + FONT_METRICS + """; white-space: nowrap; }
.atlas-metric-value, .totals-summary-value { font-size: 28px; font-weight: 800; color: #111827; line-height: 1.1; letter-spacing: -0.02em; font-family: """ + FONT_METRICS + """; white-space: nowrap; text-align: left; }
.critical-result { font-weight: 800; letter-spacing: -0.02em; }
.totals-summary-value.critical-result, .atlas-metric-value.critical-result { font-size: 28px; }
.date-key-value.critical-result { font-size: 30px; font-weight: 800; }
.totals-filters { display: flex; flex-wrap: wrap; gap: 20px 22px; margin-bottom: 20px; padding: 16px 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; align-items: flex-start; align-content: center; }
.totals-filters .filter-group { display: flex; flex-direction: column; gap: 10px; }
.totals-filters .filter-label { font-size: 13px; font-weight: 400; color: #1e293b; }
.totals-filters .filter-options { display: flex; flex-wrap: wrap; gap: 12px 16px; max-height: 160px; overflow-y: auto; }
.totals-filters .filter-cb { display: flex; align-items: center; gap: 10px; font-size: 16px; color: #334155; cursor: pointer; white-space: nowrap; line-height: 1.4; }
.totals-filters .filter-cb input[type="checkbox"] { width: 20px; height: 20px; min-width: 20px; min-height: 20px; cursor: pointer; accent-color: #6366f1; }
.totals-filters .filter-date { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; }
.totals-filters .filter-date:hover { border-color: #6366f1; }
.totals-filters .filter-date:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.totals-filters input.filter-date:hover { border-color: #6366f1 !important; }
.totals-filters input.filter-date:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.totals-filters .filter-modal-group { min-width: 160px; flex: 1 1 180px; max-width: 320px; }
.totals-filters > .filter-modal-group[data-filter-key="paketo"] { flex: 1 1 210px; max-width: 350px; }
.totals-filters .filter-modal-trigger { display: inline-flex; align-items: center; gap: 8px; width: 100%; box-sizing: border-box; min-width: 0; padding: 10px 14px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; color: #334155; cursor: pointer; user-select: none; font-family: inherit; text-align: left; transition: border-color .15s, background .15s, color .15s; }
.totals-filters .filter-modal-trigger:hover { border-color: #6366f1; color: #4f46e5; background: #eef2ff; }
.totals-filters .filter-modal-group.has-selection .filter-modal-trigger { border-color: #6366f1; background: #eef2ff; color: #4338ca; }
.totals-filters .filter-modal-trigger-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.totals-filters .filter-modal-badge { flex-shrink: 0; min-width: 22px; height: 22px; padding: 0 6px; border-radius: 999px; background: #6366f1; color: #fff; font-size: 12px; font-weight: 700; line-height: 22px; text-align: center; }
.count-filters { margin-bottom: 20px; padding: 16px 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }
.count-filters-grid { display: grid; grid-template-columns: minmax(138px, 0.92fr) minmax(138px, 0.92fr) minmax(138px, 0.92fr) minmax(182px, 1.28fr) minmax(158px, 1.02fr) 118px 118px auto; grid-template-rows: auto auto; gap: 12px 14px; align-items: start; }
.count-filters-grid > .filter-modal-group:nth-child(1) { grid-column: 1; grid-row: 1; }
.count-filters-grid > .filter-modal-group:nth-child(2) { grid-column: 2; grid-row: 1; }
.count-filters-grid > .filter-modal-group:nth-child(3) { grid-column: 3; grid-row: 1; }
.count-filters-grid > .filter-modal-group:nth-child(4) { grid-column: 4; grid-row: 1; }
.count-filters-grid > .cnt-grid-apodox { grid-column: 5; grid-row: 1; min-width: 0; }
.count-filters-grid > .cnt-grid-from { grid-column: 6; grid-row: 1; min-width: 0; }
.count-filters-grid > .cnt-grid-to { grid-column: 7; grid-row: 1; min-width: 0; }
.count-filters-grid > .cnt-grid-reset { grid-column: 8; grid-row: 1; justify-self: end; align-self: center; }
.count-filters-grid > .cnt-grid-row2 { grid-column: 1 / -1; grid-row: 2; display: flex; flex-wrap: wrap; align-items: center; gap: 12px 14px; }
.count-filters-grid > .cnt-grid-row2 .cnt-grid-cbs { display: flex; flex-direction: row; flex-wrap: nowrap; gap: 16px 24px; align-items: center; flex-shrink: 0; }
.count-filters-grid > .cnt-grid-row2 .count-date-presets-bar { flex: 1 1 520px; min-width: 0; }
.count-filters-grid .filter-modal-group { min-width: 0; }
.count-filters-grid .filter-modal-trigger { min-width: 0; width: 100%; box-sizing: border-box; }
.count-filters-grid .filter-date { width: 100%; box-sizing: border-box; min-width: 0; }
.count-filters-grid .cnt-grid-reset .filter-reset-btn { margin-left: 0; }
.count-filters .filter-group { display: flex; flex-direction: column; gap: 10px; }
.count-filters .count-filter-cb-stack { flex-shrink: 0; }
.count-filters .count-filter-cb-stack .filter-cb { white-space: nowrap; line-height: 1.3; }
.count-filters .filter-label { font-size: 13px; font-weight: 400; color: #1e293b; }
.count-filters .filter-cb { display: flex; align-items: center; gap: 10px; font-size: 16px; color: #334155; cursor: pointer; white-space: nowrap; line-height: 1.4; }
.count-filters .filter-cb input[type="checkbox"] { width: 20px; height: 20px; min-width: 20px; min-height: 20px; cursor: pointer; accent-color: #6366f1; }
.count-filters .filter-date::placeholder { color: #94a3b8; opacity: 1; font-weight: 400; }
.count-filters .filter-date { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; }
.count-filters .filter-date:hover { border-color: #6366f1; }
.count-filters .filter-date:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.count-filters input.filter-date:hover { border-color: #6366f1 !important; }
.count-filters input.filter-date:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.count-date-presets-bar { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px 14px; margin: 0; padding: 0; width: 100%; }
.count-date-presets-bar .count-preset-btn { width: 100%; box-sizing: border-box; padding: 8px 10px; font-size: 13px; line-height: 1.25; border-radius: 6px; border: 1px solid #cbd5e1; background: #fff; color: #334155; cursor: pointer; font-family: inherit; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: background .15s, border-color .15s, color .15s; }
.count-date-presets-bar .count-preset-btn:hover { border-color: #6366f1; color: #4f46e5; background: #eef2ff; }
.count-date-presets-bar .count-preset-btn.active { border-color: #6366f1; background: #6366f1; color: #fff; }
.count-date-presets-bar .count-preset-btn.active:hover { border-color: #4f46e5; background: #4f46e5; color: #fff; }
@media (max-width: 1280px) {
.count-filters-grid { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
.count-filters-grid > .filter-modal-group:nth-child(n) { grid-column: auto; grid-row: auto; }
.count-filters-grid > .cnt-grid-apodox, .count-filters-grid > .cnt-grid-from, .count-filters-grid > .cnt-grid-to { grid-column: auto; grid-row: auto; }
.count-filters-grid > .cnt-grid-reset { grid-column: auto; grid-row: auto; justify-self: end; }
.count-filters-grid > .cnt-grid-row2 { grid-column: 1 / -1; flex-direction: column; align-items: stretch; }
.count-filters-grid > .cnt-grid-row2 .count-date-presets-bar { flex: 1 1 auto; }
.count-date-presets-bar { grid-template-columns: repeat(3, minmax(120px, 1fr)); }
}
.count-filters .filter-modal-group { position: relative; }
.count-filters .filter-modal-trigger { display: inline-flex; align-items: center; gap: 8px; width: 100%; min-width: 0; padding: 10px 14px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; color: #334155; cursor: pointer; user-select: none; font-family: inherit; text-align: left; transition: border-color .15s, background .15s, color .15s; }
.count-filters .filter-modal-trigger:hover { border-color: #6366f1; color: #4f46e5; background: #eef2ff; }
.count-filters .filter-modal-group.has-selection .filter-modal-trigger { border-color: #6366f1; background: #eef2ff; color: #4338ca; }
.count-filters .filter-modal-trigger-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.count-filters .filter-modal-badge { flex-shrink: 0; min-width: 22px; height: 22px; padding: 0 6px; border-radius: 999px; background: #6366f1; color: #fff; font-size: 12px; font-weight: 700; line-height: 22px; text-align: center; }
.count-filters-grid > .filter-modal-group[data-filter-key="klados"] .filter-modal-trigger,
.totals-filters > .filter-modal-group[data-filter-key="paketo"] .filter-modal-trigger {
  background: #fecaca; border-color: #f87171; color: #991b1b; font-weight: 700;
}
.count-filters-grid > .filter-modal-group[data-filter-key="klados"] .filter-modal-trigger-label,
.totals-filters > .filter-modal-group[data-filter-key="paketo"] .filter-modal-trigger-label { font-weight: 700; }
.count-filters-grid > .filter-modal-group[data-filter-key="klados"] .filter-modal-trigger:hover,
.totals-filters > .filter-modal-group[data-filter-key="paketo"] .filter-modal-trigger:hover {
  background: #fca5a5; border-color: #ef4444; color: #7f1d1d;
}
.count-filters-grid > .filter-modal-group[data-filter-key="klados"].has-selection .filter-modal-trigger,
.totals-filters > .filter-modal-group[data-filter-key="paketo"].has-selection .filter-modal-trigger {
  background: #f87171; border-color: #dc2626; color: #fff;
}
.count-filters-grid > .filter-modal-group[data-filter-key="klados"].has-selection .filter-modal-trigger:hover,
.totals-filters > .filter-modal-group[data-filter-key="paketo"].has-selection .filter-modal-trigger:hover {
  background: #ef4444; border-color: #b91c1c; color: #fff;
}
.count-filters-grid > .filter-modal-group[data-filter-key="klados"] .filter-modal-badge,
.totals-filters > .filter-modal-group[data-filter-key="paketo"] .filter-modal-badge { background: #dc2626; }
.filter-selected-label { font-size: 1.3em; font-weight: 700; color: #334155; margin-top: 6px; line-height: 1.3; min-height: 1.3em; display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; overflow-x: auto; }
.filter-selected-chip { display: inline-block; padding: 4px 10px; background: #dc3545; border: none; border-radius: 5px; color: #fff; font-size: 12.6px; font-weight: 400; cursor: pointer; font-family: inherit; transition: background .15s; }
.filter-selected-chip:hover { background: #b02a37; }
.filter-selected-chip::after { content: ' ×'; font-weight: 700; opacity: 0.9; }
.lite-filter-modal-overlay { position: fixed; inset: 0; z-index: 99996; display: flex; align-items: center; justify-content: center; padding: 24px 16px; background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity 0.25s ease, visibility 0.25s ease; }
.lite-filter-modal-overlay.is-open { opacity: 1; visibility: visible; pointer-events: auto; }
.lite-filter-modal-panel { width: min(720px, 100%); max-height: min(85vh, 880px); display: flex; flex-direction: column; background: #fff; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(148, 163, 184, 0.15); overflow: hidden; transform: scale(0.96) translateY(12px); transition: transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1); }
.lite-filter-modal-panel.lite-filter-modal-panel--wide { width: min(792px, 100%); }
.lite-filter-modal-overlay.is-open .lite-filter-modal-panel { transform: scale(1) translateY(0); }
.lite-filter-modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 22px 26px 18px; border-bottom: 1px solid #e2e8f0; background: linear-gradient(180deg, #eef2ff 0%, #fff 100%); flex-shrink: 0; }
.lite-filter-modal-head h3 { margin: 0; font-size: 24px; font-weight: 800; color: #1e293b; line-height: 1.35; letter-spacing: -0.01em; }
.lite-filter-modal-close { flex-shrink: 0; width: 44px; height: 44px; border: none; border-radius: 10px; background: #e0e7ff; color: #4338ca; font-size: 32px; line-height: 1; cursor: pointer; transition: background 0.2s, color 0.2s; }
.lite-filter-modal-close:hover { background: #c7d2fe; color: #312e81; }
.lite-filter-modal-toolbar { padding: 16px 26px 0; flex-shrink: 0; }
.lite-filter-modal-search { width: 100%; box-sizing: border-box; padding: 12px 16px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 17px; font-family: inherit; color: #1e293b; }
.lite-filter-modal-search:focus { border-color: #6366f1; outline: none; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15); }
.lite-filter-modal-search::placeholder { color: #64748b; }
.lite-filter-modal-body { flex: 1; min-height: 0; overflow: auto; padding: 18px 28px 22px; -webkit-overflow-scrolling: touch; }
#lite-filter-modal-options-mount .filter-options { display: flex; flex-direction: column; flex-wrap: nowrap; gap: 8px; padding: 0; max-height: none; }
#lite-filter-modal-options-mount .filter-cb { display: grid; grid-template-columns: 32px minmax(0, 1fr); column-gap: 20px; align-items: center; white-space: normal; padding: 14px 16px; min-height: 3em; border-radius: 10px; transition: background .12s; font-size: 17px; line-height: 1.45; color: #1e293b; font-weight: 500; cursor: pointer; }
#lite-filter-modal-options-mount .filter-cb:hover { background: #f1f5f9; }
#lite-filter-modal-options-mount .filter-cb input[type="checkbox"] { width: 28px; height: 28px; min-width: 28px; min-height: 28px; margin: 0; padding: 0; cursor: pointer; accent-color: #6366f1; justify-self: center; align-self: center; }
#lite-filter-modal-options-mount .filter-cb .lite-filter-opt-label { display: block; min-width: 0; line-height: 1.45; letter-spacing: 0.01em; }
#lite-filter-modal-options-mount .filter-cb.has-opt-pct .lite-filter-opt-body { display: flex; align-items: flex-start; justify-content: space-between; gap: 28px; min-width: 0; width: 100%; }
#lite-filter-modal-options-mount .filter-cb.has-opt-pct .lite-filter-opt-label { flex: 1 1 auto; min-width: 0; }
#lite-filter-modal-options-mount .filter-cb.has-opt-pct .lite-filter-opt-pct { flex: 0 0 auto; text-align: right; white-space: nowrap; font-weight: 600; color: #475569; font-variant-numeric: tabular-nums; letter-spacing: 0.01em; padding-left: 8px; }
.lite-filter-modal-foot { display: flex; justify-content: flex-start; gap: 10px; padding: 16px 26px 22px; border-top: 1px solid #e2e8f0; background: #f8fafc; flex-shrink: 0; }
.lite-filter-modal-btn { padding: 11px 20px; border-radius: 8px; border: 1px solid #cbd5e1; background: #fff; color: #334155; font-size: 16px; font-weight: 600; cursor: pointer; font-family: inherit; transition: border-color .15s, background .15s, color .15s; }
.lite-filter-modal-btn:hover { border-color: #6366f1; color: #4f46e5; background: #eef2ff; }
.filter-reset-btn { margin-left: auto; padding: 9px 11px; font-size: 20px; line-height: 1; border-radius: 6px; border: 1px solid #cbd5e1; background: #fff; color: #6366f1; cursor: pointer; font-family: inherit; }
.filter-reset-btn:hover { border-color: #6366f1; color: #4f46e5; background: #eef2ff; }
#count-section { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }
#maindata-tables-wrapper { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
#count-tables-wrapper { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
#count-tables-wrapper .year-section { margin-bottom: 20px; }
#count-tables-wrapper .year-heading { font-size: 15px; font-weight: 800; padding: 8px 0 6px 0; border-bottom: 2px solid #6366f1; margin-top: 3px; margin-bottom: 11px; }
#count-tables-wrapper table.print-table thead th { font-weight: 500 !important; }
#count-tables-wrapper table.print-table tbody tr.total-row td,
#count-tables-wrapper table.print-table tbody tr[data-is-total="1"] td {
  background: #f5fafc !important;
  color: #000 !important;
  font-weight: 700 !important;
  border-top: 1px solid #c8dce8;
}
#parallel-section table.print-table tbody tr.total-row td,
#parallel-section table.print-table tbody tr[data-is-total="1"] td {
  background: #f5fafc !important;
  color: #000 !important;
  font-weight: 700 !important;
  border-top: 1px solid #c8dce8;
}
#parallel-section table.print-table thead th:nth-child(n+7),
#parallel-section table.print-table tbody td:nth-child(n+7) {
  text-align: right;
  white-space: nowrap;
}
#count-tables-wrapper table.print-table tbody td.copy-target {
  transition: background-color 0.18s ease, box-shadow 0.18s ease;
}
#count-tables-wrapper table.print-table tbody td.copy-target:hover {
  background-color: rgba(99, 102, 241, 0.14) !important;
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.38);
}
#count-tables-wrapper table.print-table tbody td.copy-target:active {
  background-color: rgba(99, 102, 241, 0.24) !important;
}
/* Καταμέτρηση: ΕΝΑΣ ενιαίος πίνακας — fixed πλάτη από colgroup (ίδια % κανονική / full screen) */
#count-tables-wrapper table.print-table.count-unified { table-layout: fixed; width: 100%; border-collapse: separate; border-spacing: 0; overflow: visible; box-shadow: none; border-radius: 0; font-size: 15px; }
#count-tables-wrapper table.print-table.count-unified thead th { position: sticky; top: 0; z-index: 6; background: #f8fafc; border-bottom: 2px solid #cbd5e1; box-shadow: 0 1px 0 #cbd5e1; white-space: normal; padding: 6px 8px; font-size: 14px; line-height: 1.2; vertical-align: bottom; color: #111827; font-weight: 500; }
#count-tables-wrapper table.print-table.count-unified tbody td { padding: 6px 8px; font-size: 15px; word-break: break-word; color: #1f2937; }
/* Αριθμητικές στήλες (ΣΥΝΟΛΟ και δεξιά): δεξιά στοίχιση → καθαρά, χωρίς κενά αριστερά */
#count-tables-wrapper table.print-table.count-unified thead th:nth-child(n+7),
#count-tables-wrapper table.print-table.count-unified tbody td:nth-child(n+7) { text-align: right; white-space: nowrap; }
/* Μήνες (στήλες 8–19): επιτρέπεται αναδίπλωση για τις τιμές ευρώ των γραμμών «Εισφορές μήνα» */
#count-tables-wrapper table.print-table.count-unified tbody td:nth-child(n+8):nth-child(-n+19) { white-space: normal; }
/* Full screen Καταμέτρηση: ίδια ποσοστά colgroup με κανονική · μεγαλύτερη γραμματοσειρά */
.table-fullscreen .fs-body #count-tables-wrapper table.print-table.count-unified {
  table-layout: fixed !important;
  width: 100%;
  font-size: 16px;
}
.table-fullscreen .fs-body #count-tables-wrapper table.print-table.count-unified thead th {
  font-size: 15px;
  padding: 10px 12px;
}
.table-fullscreen .fs-body #count-tables-wrapper table.print-table.count-unified tbody td {
  font-size: 16px;
  padding: 8px 12px;
}
.table-fullscreen .fs-body #count-tables-wrapper table.print-table.count-unified tbody tr.count-year-band td {
  font-size: 17px;
  color: #1e40af !important;
}
#count-tables-wrapper table.print-table.count-unified tbody tr.count-year-band td { background: #fff; color: #1e40af !important; font-weight: 800; font-size: 16px; padding: 8px 12px; border: 0; }
#count-tables-wrapper table.print-table.count-unified tbody tr.count-year-band td:first-child { color: #1e40af !important; }
#count-tables-wrapper table.print-table.count-unified tbody tr.count-year-gap td { height: 41px; padding: 0; background: transparent; border: 0; }
#count-section.count-year-sparse #count-tables-wrapper table.print-table.count-unified tbody tr.count-year-gap td { height: 115px; }
/* Σύνολα / Παράρτημα: fixed πλάτη από colgroup (ίδια λογική με Καταμέτρηση) */
.totals-table-scroll table.print-table.totals-weighted,
.annex-table-scroll table.print-table.annex-weighted {
  table-layout: fixed; width: 100%; border-collapse: separate; border-spacing: 0;
  overflow: visible; box-shadow: none; border-radius: 0; font-size: 15px;
}
.totals-table-scroll table.print-table.totals-weighted thead th,
.annex-table-scroll table.print-table.annex-weighted thead th {
  position: sticky; top: 0; z-index: 3; background: #f8fafc;
  border-bottom: 2px solid #cbd5e1; box-shadow: 0 1px 0 #cbd5e1;
  white-space: normal; padding: 6px 8px; font-size: 14px; line-height: 1.2;
  vertical-align: bottom; color: #111827; font-weight: 500;
}
.totals-table-scroll table.print-table.totals-weighted tbody td,
.annex-table-scroll table.print-table.annex-weighted tbody td {
  padding: 6px 8px; font-size: 15px; word-break: break-word; color: #1f2937;
}
/* Σύνολα: αριθμητικές/ημερομηνίες από 7η στήλη */
.totals-table-scroll table.print-table.totals-weighted thead th:nth-child(n+7),
.totals-table-scroll table.print-table.totals-weighted tbody td:nth-child(n+7) {
  text-align: right; white-space: nowrap;
}
.table-fullscreen .fs-body .totals-table-scroll,
.table-fullscreen .fs-body .annex-table-scroll {
  flex: none !important; min-height: auto !important; overflow: visible !important;
}
.table-fullscreen .fs-body .atlas-tab-layout-body:has(.totals-table-scroll),
.table-fullscreen .fs-body .atlas-tab-layout-body:has(.annex-table-scroll) {
  flex: 1 !important; min-height: 0 !important; overflow: auto !important;
}
.table-fullscreen .fs-body .totals-table-scroll table.print-table.totals-weighted,
.table-fullscreen .fs-body .annex-table-scroll table.print-table.annex-weighted {
  table-layout: fixed !important; width: 100%; font-size: 16px;
}
.table-fullscreen .fs-body .totals-table-scroll table.print-table.totals-weighted thead th,
.table-fullscreen .fs-body .annex-table-scroll table.print-table.annex-weighted thead th {
  font-size: 15px; padding: 10px 12px;
}
.table-fullscreen .fs-body .totals-table-scroll table.print-table.totals-weighted tbody td,
.table-fullscreen .fs-body .annex-table-scroll table.print-table.annex-weighted tbody td {
  font-size: 16px; padding: 8px 12px;
}
/* ---- Συντάξιμες Αποδοχές (Pro) ---- */
.atlas-tab-layout-body:has(.syntaksi-table-scroll) { overflow: hidden; display: flex; flex-direction: column; padding: 0; }
.syntaksi-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; --syn-par-highlight: #fefce8; }
.syntaksi-layout .atlas-tab-layout-top, .syntaksi-layout h2, .syntaksi-layout .print-description { flex-shrink: 0; }
.syntaksi-metrics.atlas-header-split { margin-bottom: 16px; background: transparent; padding: 0; }
.syntaksi-metrics-pk { min-width: 0; }
.syntaksi-metrics-pk-h { font-weight: 700; font-size: 13px; color: #1e293b; display: block; margin-bottom: 4px; }
.syntaksi-pk-chip { display: inline-block; background: #eef2ff; color: #3730a3; border-radius: 6px; padding: 2px 8px; margin: 2px 4px 2px 0; font-size: 12px; }
.syntaksi-metrics-pk-txt { font-size: 13px; color: #334155; line-height: 1.45; word-break: break-word; }
.syntaksi-filters .syntaksi-filters-grid {
  display: grid;
  grid-template-columns: minmax(100px, 0.78fr) minmax(100px, 0.82fr) minmax(120px, 1.05fr) minmax(100px, 0.78fr) minmax(100px, 0.75fr) minmax(110px, 0.88fr) minmax(150px, 1.25fr);
  grid-template-rows: auto;
  gap: 12px 14px;
  align-items: start;
}
.syntaksi-filters .syntaksi-filters-grid.syntaksi-filters-grid--parallel {
  grid-template-columns: minmax(150px, 1.35fr) minmax(100px, 0.78fr) minmax(100px, 0.82fr) minmax(120px, 1.05fr) minmax(100px, 0.78fr) minmax(100px, 0.75fr) minmax(110px, 0.88fr) minmax(150px, 1.25fr);
}
.syntaksi-filters .syntaksi-filters-grid.syntaksi-filters-grid--parallel.syntaksi-filters-grid--no-tek {
  grid-template-columns: minmax(150px, 1.35fr) minmax(100px, 0.78fr) minmax(100px, 0.82fr) minmax(120px, 1.05fr) minmax(100px, 0.78fr) minmax(100px, 0.75fr) minmax(110px, 0.88fr);
}
.syntaksi-filters .syntaksi-fld-par-mode {
  min-width: 0;
  background: var(--syn-par-highlight);
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 6px 8px;
}
.syntaksi-filters .syntaksi-fld-par-mode .apd-filter-field-label { color: #854d0e; }
.syntaksi-filters .syntaksi-fld-par-mode .apd-select {
  background: var(--syn-par-highlight);
  border-color: #fde68a;
}
.syntaksi-filters .syntaksi-fld-par-mode .apd-select:hover { border-color: #ca8a04; }
.syntaksi-filters .syntaksi-fld-par-mode .apd-select:focus { border-color: #ca8a04 !important; }
.syntaksi-filters .syntaksi-filters-grid .apd-filter-field { min-width: 0; }
.syntaksi-filters .syntaksi-filters-grid .apd-filter-input,
.syntaksi-filters .syntaksi-filters-grid .apd-select { min-width: 0; }
.syntaksi-filters .syntaksi-filters-grid .apd-filter-input::placeholder { color: #94a3b8; opacity: 1; font-weight: 400; }
.syntaksi-filters .apd-select { appearance: auto; cursor: pointer; }
.syntaksi-filters .apd-filter-input:hover,
.syntaksi-filters .apd-select:hover { border-color: #6366f1; }
.syntaksi-filters .apd-filter-input:focus,
.syntaksi-filters .apd-select:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.atlas-locked-count-bar { margin: 0 2px 12px; padding: 12px 14px; background: #f1f5f9; border: none; border-radius: 8px; }
.atlas-locked-count-title { font-size: 15px; font-weight: 700; color: #475569; margin-bottom: 8px; }
.atlas-locked-count-title::before { content: "🔒 "; }
.atlas-locked-count-grid { display: flex; flex-wrap: wrap; gap: 10px 20px; }
.atlas-locked-count-item { font-size: 14px; color: #334155; min-width: 0; }
.atlas-locked-count-sub { font-weight: 600; color: #64748b; margin-right: 6px; }
.atlas-locked-count-val { font-weight: 600; color: #1e293b; word-break: break-word; }
.apd-filters-free.apd-filters-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.syntaksi-empty { padding: 18px; color: #64748b; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; margin: 8px 2px; flex-shrink: 0; }
.syntaksi-table-scroll { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
.syntaksi-table-scroll table.print-table { border-collapse: separate; border-spacing: 0; overflow: visible; box-shadow: none; border-radius: 0; table-layout: fixed; width: 100%; font-size: 15px; }
.syntaksi-table-scroll table.print-table thead th { position: sticky; top: 0; z-index: 3; background: #f8fafc; border-bottom: 2px solid #cbd5e1; box-shadow: 0 1px 0 #cbd5e1; font-weight: 500; padding: 6px 8px; font-size: 14px; line-height: 1.2; vertical-align: bottom; white-space: normal; text-align: right; color: #111827; }
.syntaksi-table-scroll table.print-table thead th:first-child { text-align: left; }
.syntaksi-table-scroll table.print-table tbody td { padding: 6px 8px; font-size: 15px; word-break: break-word; text-align: right; white-space: nowrap; color: #1f2937; }
.syntaksi-table-scroll table.print-table td.syn-year { text-align: left; font-weight: 700; color: #111827; }
.syntaksi-table-scroll table.print-table tr.syn-total td { background: #fafdfe !important; color: #000 !important; font-weight: 700 !important; border-top: 1px solid #c8dce8; }
.syntaksi-table-scroll table.print-table tr.syn-sep td { height: 18px; background: transparent; border: 0; }
.syntaksi-table-scroll table.print-table tr.syn-exagora td { font-weight: 600; }
.syntaksi-table-scroll table.print-table tr.syn-parallel td { background: var(--syn-par-highlight) !important; }
.syntaksi-note { margin-top: 10px; font-size: 11px; color: #64748b; }
.table-fullscreen .syntaksi-table-scroll { flex: 1 !important; min-height: 0 !important; overflow: auto !important; }
.table-fullscreen .syntaksi-table-scroll table.print-table { border-collapse: separate; border-spacing: 0; overflow: visible; box-shadow: none; border-radius: 0; }
.table-fullscreen .syntaksi-table-scroll table.print-table thead th { position: sticky; top: 0; z-index: 3; background: #f8fafc; border-bottom: 2px solid #cbd5e1; }
@media print { .btn-json-syntaksi, .syntaksi-empty, .syntaksi-filters { display: none !important; } .syntaksi-metrics, .syntaksi-print .syntaksi-metrics { display: flex !important; } }
/* Κλειδωμένο φίλτρο πακέτων ΑΠΔ (ακολουθεί την Καταμέτρηση) */
.apd-klados-locked .filter-modal-trigger { opacity: 0.6; cursor: not-allowed; pointer-events: none; }
.apd-klados-locked .filter-selected-chip { pointer-events: none; }
.apd-klados-locked::after { content: "🔒 ακολουθεί Καταμέτρηση"; display: block; font-size: 10px; color: #94a3b8; margin-top: 2px; }
.date-key-panel { margin-top: 24px; padding: 20px 24px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; }
.date-key-title { font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }
.date-key-desc { font-size: 12px; color: #64748b; margin-bottom: 16px; font-style: italic; }
.date-key-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; }
.date-key-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }
.date-key-num { width: 30px; height: 30px; background: #6366f1; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.date-key-label { font-size: 13px; color: #475569; line-height: 1.3; }
.date-key-value { font-size: 23px; font-weight: 800; color: #1e293b; margin-top: 2px; line-height: 1.1; letter-spacing: -0.02em; font-family: """ + FONT_METRICS + """; }
@media print { .totals-filters { display: none !important; } .count-filters { display: none !important; } .totals-info-bar { display: none !important; } .totals-exceeded-wrap, .totals-exceeded-modal-overlay { display: none !important; } .complex-file-warning { display: none !important; } .atlas-tabinfo-btn { display: none !important; } .complex-file-readmore-btn { display: none !important; } .lite-exclusion-note { display: none !important; font-size: 9px; margin-bottom: 4px; } .tl-zoom-controls { display: none !important; } #tl-zoom-inner, #tl-paketo-zoom-inner { transform: none !important; } .tl-zoom-wrapper, .tl-paketo-zoom-scroll { overflow-x: hidden !important; } .personal-form { display: none !important; } .personal-notes { display: none !important; } .date-key-panel { break-inside: avoid; } }
.copy-target { cursor: pointer; position: relative; transition: background-color 0.15s; }
.copy-target:hover { background-color: rgba(99,102,241,0.15) !important; }
.copy-target:active { background-color: rgba(99,102,241,0.25) !important; }
#toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; pointer-events: none; }
.toast { background: #1e293b; color: #fff; padding: 10px 16px; border-radius: 8px; margin-top: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 15px; font-weight: 600; opacity: 0; transform: translateY(10px); transition: opacity 0.3s, transform 0.3s; }
.toast.show { opacity: 1; transform: translateY(0); }
.complex-file-warning { background: rgba(254,242,242,0.88); border: none; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; color: #991b1b; font-weight: 700; font-size: 15px; line-height: 1.45; }
.personal-form { display: flex; flex-direction: column; gap: 20px; padding: 24px 28px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; max-width: 960px; }
.personal-form .form-row-full { grid-column: 1 / -1; }
.personal-form .form-columns { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px 28px; }
.personal-form .form-group.form-span-2 { grid-column: span 2; }
@media (max-width: 768px) { .personal-form .form-columns { grid-template-columns: 1fr; } }
.personal-form .form-group { display: flex; flex-direction: column; gap: 8px; }
.personal-form .form-label { font-size: 13px; font-weight: 600; color: #1e293b; display: block; }
.personal-form .form-label .required { color: #1e293b; }
.personal-form .form-label .info-icon { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; margin-left: 4px; background: #e2e8f0; color: #64748b; border-radius: 50%; font-size: 11px; font-weight: 700; cursor: help; vertical-align: middle; }
.personal-form input[type="text"], .personal-form input[type="number"], .personal-form select { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; font-family: inherit; color: #334155; background: #fff; }
.personal-form input:hover, .personal-form input:focus, .personal-form select:hover, .personal-form select:focus { border-color: #6366f1; outline: none; }
.personal-form .form-row { display: flex; gap: 8px; align-items: flex-end; flex-wrap: nowrap; width: 100%; }
.personal-form .form-row select { flex: 1 1 0; min-width: 2.75rem; max-width: none; padding: 8px 8px; font-size: 14px; }
.personal-form .form-hint { font-size: 12px; color: #64748b; margin-top: 4px; }
.personal-form .form-result { font-size: 14px; font-weight: 600; color: #15803d; margin-top: 4px; }
.personal-form .form-grid-rest { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px 28px; }
.personal-section-wrap { display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap; }
.personal-section-wrap .personal-form { flex: 1 1 0; min-width: 320px; }
.personal-notes { flex: 0 1 320px; min-width: 280px; display: flex; flex-direction: column; gap: 8px; }
.personal-notes .form-label { font-size: 13px; font-weight: 600; color: #1e293b; }
.personal-notes textarea { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; font-family: inherit; color: #334155; background: #fff; min-height: 180px; resize: vertical; }
.personal-notes textarea:hover, .personal-notes textarea:focus { border-color: #6366f1; outline: none; }
@media (max-width: 768px) { .personal-section-wrap { flex-direction: column; } .personal-notes { flex: 1 1 auto; width: 100%; } }
"""

LITE_FILTER_MODAL_HTML = """
<div id="lite-filter-modal-overlay" class="lite-filter-modal-overlay" aria-hidden="true">
  <div class="lite-filter-modal-panel" role="dialog" aria-modal="true" aria-labelledby="lite-filter-modal-title">
    <div class="lite-filter-modal-head">
      <h3 id="lite-filter-modal-title"></h3>
      <button type="button" class="lite-filter-modal-close" aria-label="Κλείσιμο">&times;</button>
    </div>
    <div class="lite-filter-modal-toolbar">
      <input type="search" id="lite-filter-modal-search" class="lite-filter-modal-search" placeholder="Αναζήτηση..." autocomplete="off">
    </div>
    <div class="lite-filter-modal-body">
      <div id="lite-filter-modal-options-mount"></div>
    </div>
    <div class="lite-filter-modal-foot">
      <button type="button" class="lite-filter-modal-btn lite-filter-modal-clear">Καθαρισμός</button>
    </div>
  </div>
</div>
"""

LITE_FILTER_MODAL_JS = r"""
window._liteFilterModalApply = window._liteFilterModalApply || {};
window._liteFilterModal = {
  runApply: function(sectionEl) {
    var id = sectionEl && sectionEl.id;
    if (id && typeof window._liteFilterModalApply[id] === 'function') {
      window._liteFilterModalApply[id]();
    }
  },
  uncheckValue: function(sec, key, val) {
    function visit(root) {
      if (!root) return;
      root.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
        if (cb.getAttribute('data-attr') === key && cb.value === val) cb.checked = false;
      });
    }
    if (sec) sec.querySelectorAll('.filter-modal-group[data-filter-key="' + key + '"]').forEach(visit);
    visit(document.getElementById('lite-filter-modal-options-mount'));
  }
};
(function () {
  var ov = document.getElementById('lite-filter-modal-overlay');
  if (!ov || ov._atlasLiteFilterInited) return;
  ov._atlasLiteFilterInited = true;
  var optsMount = document.getElementById('lite-filter-modal-options-mount');
  var titleEl = document.getElementById('lite-filter-modal-title');
  var searchEl = document.getElementById('lite-filter-modal-search');
  var activeGroup = null;
  var storeEl = null;
  var activeSection = null;

  var panelEl = ov.querySelector('.lite-filter-modal-panel');

  function closeModal() {
    var secBeforeClose = activeSection;
    if (storeEl) {
      var opts = optsMount.querySelector('.filter-options');
      if (opts) storeEl.appendChild(opts);
    }
    activeGroup = null;
    storeEl = null;
    activeSection = null;
    ov.classList.remove('is-open');
    ov.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (panelEl) panelEl.classList.remove('lite-filter-modal-panel--wide');
    if (searchEl) searchEl.value = '';
    filterSearch('');
    if (secBeforeClose) window._liteFilterModal.runApply(secBeforeClose);
  }

  function openModal(group, section) {
    closeModal();
    activeGroup = group;
    activeSection = section;
    storeEl = group.querySelector('.filter-modal-store');
    var opts = storeEl && storeEl.querySelector('.filter-options');
    if (opts) optsMount.appendChild(opts);
    if (titleEl) titleEl.textContent = group.getAttribute('data-filter-name') || '';
    if (panelEl) {
      if (group.getAttribute('data-modal-wide') === '1') {
        panelEl.classList.add('lite-filter-modal-panel--wide');
      } else {
        panelEl.classList.remove('lite-filter-modal-panel--wide');
      }
    }
    ov.classList.add('is-open');
    ov.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    if (searchEl) {
      searchEl.value = '';
      filterSearch('');
      setTimeout(function () { searchEl.focus(); }, 60);
    }
  }

  function filterSearch(q) {
    var ql = (q || '').toLowerCase();
    optsMount.querySelectorAll('.filter-cb').forEach(function (lab) {
      var txt = (lab.textContent || '').toLowerCase();
      lab.style.display = !ql || txt.indexOf(ql) !== -1 ? '' : 'none';
    });
  }

  function findGroupByKey(section, key) {
    var found = null;
    section.querySelectorAll('.filter-modal-group').forEach(function (g) {
      if (g.getAttribute('data-filter-key') === key) found = g;
    });
    return found;
  }

  document.addEventListener('click', function (e) {
    var tr = e.target.closest('.filter-modal-trigger');
    if (tr) {
      var g = tr.closest('.filter-modal-group');
      var sec = g && g.closest('#totals-section, #count-section, #apd-section');
      if (g && sec) {
        e.preventDefault();
        openModal(g, sec);
      }
      return;
    }
    var chip = e.target.closest('.filter-selected-chip');
    if (chip) {
      e.preventDefault();
      var val = chip.getAttribute('data-value');
      var key = chip.getAttribute('data-filter-key');
      var sec = chip.closest('#totals-section, #count-section, #apd-section');
      if (!val || !key || !sec) return;
      var g = findGroupByKey(sec, key);
      if (!g) return;
      window._liteFilterModal.uncheckValue(sec, key, val);
      window._liteFilterModal.runApply(sec);
    }
  });

  if (searchEl) {
    searchEl.addEventListener('input', function () { filterSearch(searchEl.value); });
  }

  var closeBtn = ov.querySelector('.lite-filter-modal-close');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  ov.addEventListener('click', function (e) { if (e.target === ov) closeModal(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && ov.classList.contains('is-open')) closeModal();
  });

  var clearBtn = ov.querySelector('.lite-filter-modal-clear');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      optsMount.querySelectorAll('input[type="checkbox"]').forEach(function (cb) { cb.checked = false; });
      if (activeSection) window._liteFilterModal.runApply(activeSection);
    });
  }

  optsMount.addEventListener('change', function (e) {
    if (e.target && e.target.type === 'checkbox' && activeSection) {
      window._liteFilterModal.runApply(activeSection);
    }
  });
})();
"""

SYNOPSIS_MODAL_HTML = """
<div id="synopsis-modal-overlay" class="synopsis-modal-overlay" aria-hidden="true">
  <div class="synopsis-modal" role="dialog" aria-modal="true" aria-labelledby="synopsis-modal-title">
    <div class="synopsis-modal-head">
      <h3 id="synopsis-modal-title"></h3>
      <button type="button" class="synopsis-modal-close" aria-label="Κλείσιμο">&times;</button>
    </div>
    <div class="synopsis-modal-body" id="synopsis-modal-body"></div>
  </div>
</div>
"""

SYNOPSIS_ENHANCE_JS = r"""
(function () {
  var MAX_PREVIEW_LINES = 6;
  var MAX_PREVIEW_CHARS = 480;

  function openSynopsisModal(title, html) {
    var overlay = document.getElementById("synopsis-modal-overlay");
    var titleEl = document.getElementById("synopsis-modal-title");
    var bodyEl = document.getElementById("synopsis-modal-body");
    if (!overlay || !titleEl || !bodyEl) return;
    titleEl.textContent = title || "Λεπτομέρειες";
    bodyEl.innerHTML = html;
    overlay.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    var closeBtn = overlay.querySelector(".synopsis-modal-close");
    if (closeBtn) closeBtn.focus();
  }

  function closeSynopsisModal() {
    var overlay = document.getElementById("synopsis-modal-overlay");
    if (!overlay) return;
    overlay.classList.remove("is-open");
    overlay.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function truncateForPreview(fullHtml) {
    if (fullHtml.indexOf("grid-template-columns") !== -1 || fullHtml.indexOf("display: grid") !== -1) {
      return { html: fullHtml, truncated: false };
    }
    var plain = fullHtml.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    var parts = fullHtml.split(/<br\s*\/?>/i);
    var manyLines = parts.length > MAX_PREVIEW_LINES;
    var longText = plain.length > MAX_PREVIEW_CHARS;
    if (!manyLines && !longText) {
      return { html: fullHtml, truncated: false };
    }
    if (manyLines) {
      var rest = parts.length - MAX_PREVIEW_LINES;
      var preview = parts.slice(0, MAX_PREVIEW_LINES).join("<br>") +
        '<span class="synopsis-trunc-note">… και ακόμα <strong>' + rest + '</strong> γραμμές — πατήστε τον τίτλο για όλες.</span>';
      return { html: preview, truncated: true };
    }
    var tmp = document.createElement("div");
    tmp.innerHTML = fullHtml;
    var text = tmp.textContent || "";
    var short = text.slice(0, MAX_PREVIEW_CHARS).trim() + "…";
    var esc = function (s) {
      var d = document.createElement("div");
      d.textContent = s;
      return d.innerHTML;
    };
    return {
      html: "<p>" + esc(short) + '</p><span class="synopsis-trunc-note">Πατήστε τον τίτλο για πλήρες κείμενο με μορφοποίηση.</span>',
      truncated: true
    };
  }

  function enhanceSynopsis() {
    var pane = document.getElementById("pane-synopsis");
    if (!pane) return;

    var overlay = document.getElementById("synopsis-modal-overlay");
    if (overlay) {
      overlay.addEventListener("click", function (e) {
        if (e.target === overlay) closeSynopsisModal();
      });
      var closeBtn = overlay.querySelector(".synopsis-modal-close");
      if (closeBtn) closeBtn.addEventListener("click", closeSynopsisModal);
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSynopsisModal();
    });

    pane.querySelectorAll(".audit-card").forEach(function (card) {
      var hdr = card.querySelector(".audit-card-header");
      var det = card.querySelector(".audit-card-details");
      if (!hdr || !det) return;

      hdr.querySelectorAll(".synopsis-expand-btn").forEach(function (b) { b.remove(); });
      det.classList.remove("synopsis-details-faded");

      var stored = det.getAttribute("data-atlas-synopsis-full");
      var fullHtml = "";
      if (stored) {
        try {
          fullHtml = decodeURIComponent(stored);
        } catch (e2) {
          fullHtml = det.innerHTML.trim();
        }
      } else {
        fullHtml = det.innerHTML.trim();
      }
      if (!fullHtml) return;

      var titleEl = hdr.querySelector(".synopsis-title-btn") || hdr.querySelector("span");
      var cardTitle = titleEl ? titleEl.textContent.trim() : "Λεπτομέρειες";
      if (cardTitle.indexOf("Παλιός ή νέος") !== -1) return;

      det.setAttribute("data-atlas-synopsis-full", encodeURIComponent(fullHtml));
      det.innerHTML = fullHtml;

      if (titleEl && titleEl.tagName !== "BUTTON") {
        var titleBtn = document.createElement("button");
        titleBtn.type = "button";
        titleBtn.className = "synopsis-title-btn";
        titleBtn.textContent = cardTitle;
        titleBtn.setAttribute("aria-label", "Προβολή λεπτομερειών: " + cardTitle);
        titleBtn.addEventListener(
          "click",
          function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();
            openSynopsisModal(cardTitle, fullHtml);
          },
          true
        );
        titleEl.replaceWith(titleBtn);
      } else if (titleEl && titleEl.tagName === "BUTTON") {
        titleEl.addEventListener(
          "click",
          function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();
            openSynopsisModal(cardTitle, fullHtml);
          },
          true
        );
      }

      var t = truncateForPreview(fullHtml);
      if (t.truncated) {
        det.innerHTML = t.html;
      }
      requestAnimationFrame(function () {
        if (det.scrollHeight > det.clientHeight + 2) {
          det.classList.add("synopsis-details-faded");
        }
      });
    });
  }

  function scheduleEnhance() {
    setTimeout(enhanceSynopsis, 0);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scheduleEnhance);
  } else {
    scheduleEnhance();
  }

  window.openSynopsisModal = openSynopsisModal;
  window.closeSynopsisModal = closeSynopsisModal;
})();
"""

VIEWER_JS = r"""
function applyApodoxesTooltips(){var pane=document.getElementById('pane-count');if(!pane)return;var tooltipEl=document.getElementById('apodoxes-tooltip');if(!tooltipEl){tooltipEl=document.createElement('div');tooltipEl.id='apodoxes-tooltip';tooltipEl.className='apodoxes-tooltip';tooltipEl.setAttribute('aria-hidden','true');document.body.appendChild(tooltipEl);}function showTip(td,text){if(!text)return;tooltipEl.textContent=text;tooltipEl.classList.add('visible');tooltipEl.setAttribute('aria-hidden','false');tooltipEl.offsetHeight;var rect=td.getBoundingClientRect();var tipRect=tooltipEl.getBoundingClientRect();var left=rect.left+(rect.width/2)-(tipRect.width/2);var top=rect.top-tipRect.height-10;if(top<8){top=rect.bottom+10;}left=Math.max(12,Math.min(left,window.innerWidth-tipRect.width-12));tooltipEl.style.left=left+'px';tooltipEl.style.top=top+'px';}function hideTip(){tooltipEl.classList.remove('visible');tooltipEl.setAttribute('aria-hidden','true');}pane.querySelectorAll('table.print-table').forEach(function(tbl){var headers=tbl.querySelectorAll('thead th');var colIndex=-1;for(var i=0;i<headers.length;i++){var t=(headers[i].textContent||'').trim();if(t.indexOf('ΑΠΟΔΟΧΩΝ')!==-1||t.indexOf('Τύπος Αποδοχών')!==-1){colIndex=i;break;}}if(colIndex<0)return;tbl.querySelectorAll('tbody tr').forEach(function(tr){var td=tr.querySelectorAll('td')[colIndex];if(td){var code=(td.textContent||'').trim();var key=code.length===1&&/^\d$/.test(code)?'0'+code:code;var desc=_apodoxesDescriptions[key]||_apodoxesDescriptions[code]||'';if(desc){td.classList.add('has-apodoxes-tooltip');td.setAttribute('data-tooltip',desc);td.removeAttribute('title');td.addEventListener('mouseenter',function(){showTip(td,desc);});td.addEventListener('mouseleave',hideTip);}}});});}
function applyDescriptionColumn(){var tooltipEl=document.getElementById('apodoxes-tooltip');if(!tooltipEl){tooltipEl=document.createElement('div');tooltipEl.id='apodoxes-tooltip';tooltipEl.className='apodoxes-tooltip';tooltipEl.setAttribute('aria-hidden','true');document.body.appendChild(tooltipEl);}function showTipDesc(td,text){if(!text)return;tooltipEl.textContent=text;tooltipEl.classList.add('visible');tooltipEl.setAttribute('aria-hidden','false');tooltipEl.offsetHeight;var rect=td.getBoundingClientRect();var tipRect=tooltipEl.getBoundingClientRect();var left=rect.left+(rect.width/2)-(tipRect.width/2);var top=rect.top-tipRect.height-10;if(top<8){top=rect.bottom+10;}left=Math.max(12,Math.min(left,window.innerWidth-tipRect.width-12));tooltipEl.style.left=left+'px';tooltipEl.style.top=top+'px';}function hideTipDesc(){tooltipEl.classList.remove('visible');tooltipEl.setAttribute('aria-hidden','true');}document.querySelectorAll('table.print-table').forEach(function(tbl){var headers=tbl.querySelectorAll('thead th');var colIndex=-1;for(var i=0;i<headers.length;i++){if((headers[i].textContent||'').trim().indexOf('ΠΕΡΙΓΡΑΦΗ')!==-1){colIndex=i;break;}}if(colIndex<0)return;tbl.querySelectorAll('tbody tr').forEach(function(tr){var td=tr.querySelectorAll('td')[colIndex];if(td){td.classList.add('cell-description');var fullText=(td.textContent||'').trim();if(fullText){td.setAttribute('data-tooltip',fullText);td.addEventListener('mouseenter',function(){showTipDesc(td,fullText);});td.addEventListener('mouseleave',hideTipDesc);}}});});}
function applyPaketoTimelineTooltips(){var wrap=document.getElementById('tl-paketo-wrap');if(!wrap)return;var tooltipEl=document.getElementById('tl-paketo-tooltip');if(!tooltipEl){tooltipEl=document.createElement('div');tooltipEl.id='tl-paketo-tooltip';tooltipEl.className='apodoxes-tooltip';tooltipEl.setAttribute('aria-hidden','true');document.body.appendChild(tooltipEl);}function showTipPaketo(el,text){if(!text)return;tooltipEl.textContent=text;tooltipEl.classList.add('visible');tooltipEl.setAttribute('aria-hidden','false');tooltipEl.offsetHeight;var rect=el.getBoundingClientRect();var tipRect=tooltipEl.getBoundingClientRect();var left=rect.left+(rect.width/2)-(tipRect.width/2);var top=rect.top-tipRect.height-10;if(top<8){top=rect.bottom+10;}left=Math.max(12,Math.min(left,window.innerWidth-tipRect.width-12));tooltipEl.style.left=left+'px';tooltipEl.style.top=top+'px';}function hideTipPaketo(){tooltipEl.classList.remove('visible');tooltipEl.setAttribute('aria-hidden','true');}wrap.querySelectorAll('.tl-bar.has-tl-paketo-tooltip').forEach(function(bar){var t=bar.getAttribute('data-tooltip');if(!t)return;bar.removeAttribute('title');bar.addEventListener('mouseenter',function(){showTipPaketo(bar,t);});bar.addEventListener('mouseleave',hideTipPaketo);});wrap.querySelectorAll('.tl-label-meta[data-tooltip]').forEach(function(el2){var t=el2.getAttribute('data-tooltip');if(!t)return;el2.addEventListener('mouseenter',function(){showTipPaketo(el2,t);});el2.addEventListener('mouseleave',hideTipPaketo);});}
function buildPaketoTimeline(){var rowsEl=document.getElementById('tl-paketo-rows');var refEl=document.querySelector('#tl-paketo-wrap .tl-paketo-ref');var axisEl=document.querySelector('#tl-paketo-wrap .tl-paketo-axis');if(!rowsEl||!refEl||!axisEl)return;var RR=window._atlasRR,DM=window._atlasDM,pd=window._atlasPd;if(typeof pd!=='function'||!Array.isArray(RR)||!RR.length){rowsEl.innerHTML='<p style=\'color:#64748b;font-size:13px;padding:8px 0\'>Δεν υπάρχουν δεδομένα για χρονολόγιο πακέτων.</p>';return;}var tlStart=null,tlEnd=null;RR.forEach(function(r){var a=pd(r.apo),e=pd(r.eos);if(a&&(!tlStart||a<tlStart))tlStart=a;if(e&&(!tlEnd||e>tlEnd))tlEnd=e;});if(!tlStart)tlStart=new Date(1993,0,1);if(!tlEnd)tlEnd=new Date();var span=tlEnd-tlStart;if(span<=0)span=1;function pct(d){return Math.max(0,Math.min(100,(d-tlStart)/span*100));}function truncLabel(s,maxLen){s=String(s||'').replace(/\s+/g,' ').trim();if(s.length<=maxLen)return s;return s.slice(0,Math.max(0,maxLen-1))+'…';}function escAttr(x){return String(x==null?'':x).replace(/&/g,'&amp;').replace(/"/g,'&quot;');}function rowKey(r){return String(r.p||'').trim()+String.fromCharCode(1)+String(r.t||'').trim()+String.fromCharCode(1)+String(r.ty||'').trim();}var groups={};RR.forEach(function(r){var p=String(r.p||'').trim();if(!p)return;var a=pd(r.apo),b=pd(r.eos);if(!a||!b)return;var k=rowKey(r);if(!groups[k])groups[k]={p:p,t:String(r.t||'').trim(),ty:String(r.ty||'').trim(),segs:[]};groups[k].segs.push([a,b]);});var PAL=['#6366f1','#0ea5e9','#14b8a6','#a855f7','#f97316','#ec4899','#84cc16','#eab308','#64748b'];var keys=Object.keys(groups).sort(function(x,y){var ax=x.split(String.fromCharCode(1)),bx=y.split(String.fromCharCode(1));for(var i=0;i<3;i++){var c=(ax[i]||'').localeCompare(bx[i]||'','el');if(c)return c;}return 0;});var refHtml='',axisHtml='';var zIn=document.getElementById('tl-zoom-inner');if(zIn){zIn.querySelectorAll('.tl-ref-lines .tl-ref-line').forEach(function(line){refHtml+=line.outerHTML;});zIn.querySelectorAll('.tl-axis .tl-tick').forEach(function(tk){axisHtml+=tk.outerHTML;});}refEl.innerHTML=refHtml||'';axisEl.innerHTML=axisHtml||'';var html='';keys.forEach(function(k,idx){var g=groups[k];var segs=(g.segs||[]).filter(function(x){return x[0]&&x[1]&&x[0]<=x[1];});segs.sort(function(a,b){return a[0]-b[0]||a[1]-b[1]||0;});var fullDesc=(DM&&DM[g.p])?String(DM[g.p]).replace(/\r?\n/g,' ').trim():'';var mainLine=g.p+(fullDesc?' – '+truncLabel(fullDesc,26):'');var metaHtml='';if(g.t||g.ty){var _ps=[];if(g.t)_ps.push(g.t);if(g.ty)_ps.push(g.ty);var _full='('+_ps.join(', ')+')';var _short=truncLabel(_full,42);metaHtml+='<div class="tl-label-meta" data-tooltip="'+escAttr(_full)+'">'+String(_short).replace(/</g,'&lt;')+'</div>';}var labelHtml='<div class="tl-label tl-label-cell"><div class="tl-label-main">'+String(mainLine).replace(/</g,'&lt;')+'</div>'+metaHtml+'</div>';var col=PAL[idx%PAL.length];var bars=segs.map(function(seg){var L=pct(seg[0]),W=Math.max(0.15,pct(seg[1])-L);var apoStr=seg[0].getDate().toString().padStart(2,'0')+'/'+(seg[0].getMonth()+1).toString().padStart(2,'0')+'/'+seg[0].getFullYear();var eosStr=seg[1].getDate().toString().padStart(2,'0')+'/'+(seg[1].getMonth()+1).toString().padStart(2,'0')+'/'+seg[1].getFullYear();var barTip=apoStr+' — '+eosStr;return '<div class="tl-bar has-tl-paketo-tooltip" style="left:'+L.toFixed(2)+'%;width:'+W.toFixed(2)+'%;background:'+col+';" data-tooltip="'+escAttr(barTip)+'"></div>';}).join('');html+='<div class="tl-row">'+labelHtml+'<div class="tl-track">'+bars+'</div></div>';});rowsEl.innerHTML=html;if(typeof applyPaketoTimelineTooltips==='function')applyPaketoTimelineTooltips();}
function updatePersonalTitle(){var parts=[];var fullnameEl=document.getElementById('personal_fullname');var amkaEl=document.getElementById('personal_amka');var daySel=document.getElementById('personal_birth_day');var monthSel=document.getElementById('personal_birth_month');var yearSel=document.getElementById('personal_birth_year');var name=(fullnameEl&&fullnameEl.value)?fullnameEl.value.trim():'';if(name)parts.push(name);var d=daySel?parseInt(daySel.value,10):0;var m=monthSel?parseInt(monthSel.value,10):0;var y=yearSel?parseInt(yearSel.value,10):0;if(d&&m&&y){var birth=new Date(y,m-1,d);var today=new Date();if(birth<=today){var age=(today-birth)/(365.25*24*60*60*1000);parts.push(age.toFixed(2).replace('.',',')+' Ετών σήμερα');}}var amka=(amkaEl&&amkaEl.value)?amkaEl.value.trim():'';if(amka)parts.push(amka);var line=parts.join('   ·   ');var titleEl=document.getElementById('main-title-person');if(titleEl)titleEl.textContent=line;if(typeof _clientName!=='undefined')_clientName=line;}
function initPersonalForm(){var i,y,o,o2;var daySel=document.getElementById('personal_birth_day');var monthSel=document.getElementById('personal_birth_month');var yearSel=document.getElementById('personal_birth_year');var cDay=document.getElementById('personal_child_birth_day');var cMonth=document.getElementById('personal_child_birth_month');var cYear=document.getElementById('personal_child_birth_year');var resSel=document.getElementById('personal_years_residence');if(!daySel)return;function gv(s){return s&&s.value!=null?String(s.value):'';}var saved={bd:gv(daySel),bm:gv(monthSel),by:gv(yearSel),cd:cDay?gv(cDay):'',cm:cMonth?gv(cMonth):'',cy:cYear?gv(cYear):'',yr:resSel&&gv(resSel)!==''?gv(resSel):'40'};function clr(s){if(s)while(s.firstChild)s.removeChild(s.firstChild);}clr(daySel);clr(monthSel);clr(yearSel);if(cDay)clr(cDay);if(cMonth)clr(cMonth);if(cYear)clr(cYear);if(resSel)clr(resSel);var o0=document.createElement('option');o0.value='';o0.textContent='ημ';daySel.appendChild(o0);var m0=document.createElement('option');m0.value='';m0.textContent='— Μήνας —';var y0=document.createElement('option');y0.value='';y0.textContent='— Έτος —';for(i=1;i<=31;i++){o=document.createElement('option');o.value=i;o.textContent=i;daySel.appendChild(o);if(cDay){o2=document.createElement('option');o2.value=i;o2.textContent=i;cDay.appendChild(o2);}}var months=[['1','Ιαν'],['2','Φεβ'],['3','Μαρ'],['4','Απρ'],['5','Μαϊ'],['6','Ιουν'],['7','Ιουλ'],['8','Αυγ'],['9','Σεπ'],['10','Οκτ'],['11','Νοε'],['12','Δεκ']];for(i=0;i<12;i++){o=document.createElement('option');o.value=months[i][0];o.textContent=months[i][1];monthSel.appendChild(o);if(cMonth){o2=document.createElement('option');o2.value=months[i][0];o2.textContent=months[i][1];cMonth.appendChild(o2);}}monthSel.insertBefore(m0,monthSel.firstChild);var thisYear=new Date().getFullYear();for(y=thisYear;y>=1900;y--){o=document.createElement('option');o.value=y;o.textContent=y;yearSel.appendChild(o);if(cYear){o2=document.createElement('option');o2.value=y;o2.textContent=y;cYear.appendChild(o2);}}yearSel.insertBefore(y0,yearSel.firstChild);if(resSel){for(i=0;i<=40;i++){o=document.createElement('option');o.value=i;o.textContent=i;resSel.appendChild(o);}resSel.value=saved.yr;}daySel.value=saved.bd;monthSel.value=saved.bm;yearSel.value=saved.by;if(cDay)cDay.value=saved.cd;if(cMonth)cMonth.value=saved.cm;if(cYear)cYear.value=saved.cy;function updateAge(){var d=parseInt(daySel.value,10);var m=parseInt(monthSel.value,10);var y2=parseInt(yearSel.value,10);var out=document.getElementById('personal_age_display');if(!out)return;if(!d||!m||!y2){out.textContent='';return;}var birth=new Date(y2,m-1,d);var today=new Date();if(birth>today){out.textContent='';return;}var age=(today-birth)/(365.25*24*60*60*1000);out.textContent=age.toFixed(2).replace('.',',')+' Ετών σήμερα';}daySel.addEventListener('change',updateAge);monthSel.addEventListener('change',updateAge);yearSel.addEventListener('change',updateAge);updateAge();updatePersonalTitle();var fullnameEl=document.getElementById('personal_fullname');var amkaEl=document.getElementById('personal_amka');if(fullnameEl)fullnameEl.addEventListener('input',updatePersonalTitle);if(amkaEl)amkaEl.addEventListener('input',updatePersonalTitle);daySel.addEventListener('change',updatePersonalTitle);monthSel.addEventListener('change',updatePersonalTitle);yearSel.addEventListener('change',updatePersonalTitle);}
function showTab(tabId){document.querySelectorAll('.tab-pane').forEach(function(p){p.classList.remove('active');});document.querySelectorAll('.nav-item').forEach(function(a){a.classList.remove('active');});var pane=document.getElementById('pane-'+tabId);var link=document.querySelector('.nav-item[data-tab="'+tabId+'"]');if(pane)pane.classList.add('active');if(link)link.classList.add('active');var main=document.querySelector('.main-content');if(main){if(pane&&pane.querySelector('.atlas-tab-layout')&&tabId!=='totals'){main.classList.add('atlas-scroll-tab-active');main.classList.add('count-tab-active');}else{main.classList.remove('atlas-scroll-tab-active');main.classList.remove('count-tab-active');}}var tip=document.getElementById('apodoxes-tooltip');if(tip){tip.classList.remove('visible');tip.setAttribute('aria-hidden','true');}var tipP=document.getElementById('tl-paketo-tooltip');if(tipP){tipP.classList.remove('visible');tipP.setAttribute('aria-hidden','true');}if(tabId==='count')applyApodoxesTooltips();if(tabId==='timeline'){buildPaketoTimeline();}}
document.addEventListener('DOMContentLoaded',function(){applyApodoxesTooltips();applyDescriptionColumn();initPersonalForm();buildPaketoTimeline();});
function buildSinglePrintDoc(title,bodyContent){var styles=typeof _printStyles==='string'?_printStyles:'';var name=(typeof _clientName==='string'?_clientName:'').trim();var fullTitle=(name?name+' - '+(title||'')+' - ':(title||'ATLAS')+' - ')+(typeof _printBrandSuffix==='string'?_printBrandSuffix:'Atlas');var safeTitle=fullTitle.replace(/</g,'&lt;').replace(/"/g,'&quot;');var safeName=name.replace(/</g,'&lt;').replace(/&/g,'&amp;');var nameBlock=name?'<div class="prt-name">'+safeName+'</div>':'';return'<!DOCTYPE html><html lang="el"><head><meta charset="utf-8"><title>'+safeTitle+'</title><link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet"><link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet"><style>'+styles+'</style></head><body>'+nameBlock+'<div class="prt-title">Ασφαλιστικό Βιογραφικό '+(typeof _printBrandSuffix==='string'?_printBrandSuffix:'Atlas')+'</div>'+bodyContent+'<div style="margin-top:12px;font-size:9px;color:#888;text-align:left;">© Syntaksi Pro - my advisor</div></body></html>';}
function buildSyntaksiPrintDoc(title,bodyContent){var styles=typeof _printStyles==='string'?_printStyles:'';var name=(typeof _clientName==='string'?_clientName:'').trim().replace(/</g,'&lt;').replace(/&/g,'&amp;');var safeTitle=((name?name+' - ':'')+(title||'Συντάξιμες Αποδοχές')).replace(/"/g,'&quot;');var nameBlock=name?'<div class="print-client-name">'+name+'</div>':'';return'<!DOCTYPE html><html lang="el"><head><meta charset="utf-8"><title>'+safeTitle+'</title><link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet"><style>'+styles+'</style></head><body class="syntaksi-print-doc">'+nameBlock+bodyContent+'</body></html>';}
function _stripHiddenCountForPrint(root){if(!root||!root.querySelectorAll)return;var sec=root.id==='count-section'?root:root.querySelector('#count-section');if(!sec||!sec.querySelector('#count-tables-wrapper'))return;sec.querySelectorAll('script').forEach(function(s){s.remove();});sec.querySelectorAll('#count-tables-wrapper tbody tr').forEach(function(tr){if(tr.style.display==='none')tr.remove();});var wrap=sec.querySelector('#count-tables-wrapper');var uni=wrap&&wrap.querySelector('table.count-unified');if(uni){var thead=uni.querySelector('thead');var theadHTML=thead?thead.outerHTML:'';var groups=[];var cur=null;Array.prototype.forEach.call(uni.querySelectorAll('tbody > tr'),function(tr){if(tr.getAttribute('data-is-band')==='1'){cur={year:(tr.getAttribute('data-c-year')||(tr.textContent||'').trim()),rows:[]};groups.push(cur);return;}if(tr.getAttribute('data-is-sep')==='1')return;if(!cur){cur={year:(tr.getAttribute('data-c-year')||''),rows:[]};groups.push(cur);}cur.rows.push(tr.outerHTML);});var out='';groups.forEach(function(g){if(!g.rows.length)return;out+='<div class="year-section"><div class="year-heading">'+(g.year||'')+'</div><table class="print-table">'+theadHTML+'<tbody>'+g.rows.join('')+'</tbody></table></div>';});if(out)wrap.innerHTML=out;}}
function _apdPrintSectionContent(sec){if(!sec)return'';if(typeof window._atlasApdApply==='function')window._atlasApdApply();var h2=sec.querySelector('h2');var desc=sec.querySelector('.print-description');var mount=sec.querySelector('#apd-tables-mount');var notes='';var plEl=document.getElementById('apd-plafond');if(plEl&&plEl.options&&plEl.options.length){var opt=plEl.options[plEl.selectedIndex];if(opt)notes+='<p class="print-description apd-print-plafond">Πλαφόν: '+String(opt.textContent||'').replace(/</g,'&lt;')+'</p>';}var toEl=document.getElementById('apd-totals-only');if(toEl&&toEl.checked)notes+='<p class="print-description">Μόνο ετήσιες γραμμές συνόλου</p>';return'<div class="print-section apd-layout">'+(h2?h2.outerHTML:'')+(desc?desc.outerHTML:'')+notes+(mount?'<div id="apd-tables-mount">'+mount.innerHTML+'</div>':'')+'</div>';}
function _syntaksiPrefixFromSection(sec){var id=(sec&&sec.id)||'syntaksi-section';return id.replace(/-section$/,'')||'syntaksi';}
function _syntaksiPrintBodyFor(sec){var pfx=_syntaksiPrefixFromSection(sec);var map=window._atlasSyntaksiPrint||{};if(typeof map[pfx]==='function')return map[pfx];if(typeof window._atlasSyntaksiGetPrintBody==='function')return window._atlasSyntaksiGetPrintBody;return null;}
function _syntaksiPrintSectionContent(sec){if(!sec)sec=document.getElementById('syntaksi-section');var titleText=(sec&&sec.querySelector('h2')&&sec.querySelector('h2').textContent)||'Συντάξιμες Αποδοχές';var safeTitle=String(titleText).replace(/</g,'&lt;');var bodyFn=_syntaksiPrintBodyFor(sec);if(typeof bodyFn!=='function'){return'<div class="syntaksi-print"><h1>'+safeTitle+'</h1></div>';}var pb=bodyFn();if(!pb||!pb.ok){return'<div class="syntaksi-print"><h1>'+safeTitle+'</h1><p class="print-description">Επιλέξτε πακέτα κάλυψης στην καρτέλα Καταμέτρηση.</p></div>';}return'<div class="syntaksi-print"><h1>'+safeTitle+'</h1>'+pb.summaryHtml+pb.tableHtml+(pb.disclaimerHtml||'')+'</div>';}
function _patchApdInPrintHtml(html){var live=document.getElementById('apd-section');if(!live||typeof html!=='string'||!html)return html||'';if(typeof window._atlasApdApply==='function')window._atlasApdApply();var liveMount=live.querySelector('#apd-tables-mount');if(!liveMount)return html;try{var doc=new DOMParser().parseFromString(html,'text/html');var printMount=doc.getElementById('apd-tables-mount');if(!printMount)return html;printMount.innerHTML=liveMount.innerHTML;var livePl=document.getElementById('apd-plafond');var printPl=doc.getElementById('apd-plafond');if(livePl&&printPl){printPl.value=livePl.value;Array.from(printPl.options).forEach(function(o){if(o.value===livePl.value)o.setAttribute('selected','selected');else o.removeAttribute('selected');});}return'<!DOCTYPE html>\n'+doc.documentElement.outerHTML;}catch(e){return html;}}
function _openPrintWindow(printDoc){var w=window.open('','_blank');w.document.write(printDoc);w.document.close();w.focus();setTimeout(function(){w.print();w.close();},400);}
function printSection(el){if(typeof updatePersonalTitle==='function')updatePersonalTitle();var source=el.classList&&el.classList.contains('print-section')?el:(el.closest&&el.closest('.print-section')||el);var apdSec=(source&&source.id==='apd-section')?source:(source&&source.querySelector?source.querySelector('#apd-section'):null)||(source&&source.closest?source.closest('#apd-section'):null);if(apdSec){var apdTitle=(apdSec.querySelector('h2')&&apdSec.querySelector('h2').textContent)||'ΑΠΔ/Πλαφόν';_openPrintWindow(buildSinglePrintDoc(apdTitle,_apdPrintSectionContent(apdSec)));return;}var synSec=(source&&source.classList&&source.classList.contains('syntaksi-layout'))?source:(source&&source.querySelector?source.querySelector('.syntaksi-layout'):null)||(source&&source.closest?source.closest('.syntaksi-layout'):null);if(synSec){var synTitle=(synSec.querySelector('h2')&&synSec.querySelector('h2').textContent)||'Συντάξιμες Αποδοχές';_openPrintWindow(buildSyntaksiPrintDoc(synTitle,_syntaksiPrintSectionContent(synSec)));return;}if(typeof persistInteractiveValues==='function')persistInteractiveValues(source);var clone=source.cloneNode(true);clone.querySelectorAll('.section-actions,.btn-fs,.btn-print-tab').forEach(function(n){n.remove();});_stripHiddenCountForPrint(clone);var title=(clone.querySelector('h2')&&clone.querySelector('h2').textContent)||'ATLAS';var bodyContent;var totalsTable=clone.querySelector('#totals-filter-table');if(totalsTable){var h2Text=(clone.querySelector('h2')&&clone.querySelector('h2').textContent)||'Σύνολα';bodyContent='<div class="print-section"><h2>'+h2Text.replace(/</g,'&lt;')+'</h2>'+totalsTable.outerHTML+'</div>';}else{bodyContent=clone.outerHTML;}_openPrintWindow(buildSinglePrintDoc(title,bodyContent));}
function openTableFs(el){var overlay=document.createElement('div');overlay.className='table-fullscreen';overlay.id='fs-overlay';var section=el.classList.contains('print-section')?el:el.closest('.print-section');var source=section||el;var heading=source.querySelector?source.querySelector('h2'):null;var titleText=heading?heading.textContent:'Πίνακας';var hasInteractive=source.querySelector&&source.querySelector('script');var toolbar=document.createElement('div');toolbar.className='fs-toolbar';toolbar.innerHTML='<span class="fs-title">'+titleText+'</span>';var actions=document.createElement('div');actions.className='fs-toolbar-actions';var printBtn=document.createElement('button');printBtn.className='fs-print-btn';printBtn.innerHTML='🖨 Εκτύπωση';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(){var bodyEl=overlay.querySelector('.fs-body');if(bodyEl){var apdSec=bodyEl.querySelector('#apd-section');if(apdSec){_openPrintWindow(buildSinglePrintDoc(titleText,_apdPrintSectionContent(apdSec)));return;}var synSec=bodyEl.querySelector('.syntaksi-layout');if(synSec){_openPrintWindow(buildSyntaksiPrintDoc(titleText,_syntaksiPrintSectionContent(synSec)));return;}if(typeof persistInteractiveValues==='function')persistInteractiveValues(bodyEl);var clone=bodyEl.cloneNode(true);clone.querySelectorAll('.section-actions,.btn-fs,.btn-print-tab').forEach(function(n){n.remove();});_stripHiddenCountForPrint(clone);var totalsTable=clone.querySelector('#totals-filter-table');var bodyContent=totalsTable?'<div class="print-section"><h2>'+(titleText.replace(/</g,'&lt;')||'Σύνολα')+'</h2>'+totalsTable.outerHTML+'</div>':clone.innerHTML;_openPrintWindow(buildSinglePrintDoc(titleText,bodyContent));}};actions.appendChild(printBtn);if(typeof XLSX!=='undefined'){var xlsFsBtn=document.createElement('button');xlsFsBtn.className='fs-print-btn';xlsFsBtn.innerHTML='📊 Excel';xlsFsBtn.title='Εξαγωγή αυτού του πίνακα σε Excel (όπως εμφανίζεται)';xlsFsBtn.onclick=function(){var bodyEl=overlay.querySelector('.fs-body');if(bodyEl)exportTabExcel(bodyEl,titleText||'Πίνακας');};actions.appendChild(xlsFsBtn);}if(source&&source.classList&&source.classList.contains('syntaksi-layout')){var _synPfx=(source.id||'syntaksi-section').replace(/-section$/,'')||'syntaksi';var _jsonId=_synPfx+'-json-dl';var jsonFsBtn=document.createElement('button');jsonFsBtn.className='fs-json-btn';jsonFsBtn.innerHTML='JSON για Syntaksi Pro 3';jsonFsBtn.title='Εξαγωγή JSON για Syntaksi Pro 3';var liveJson=document.getElementById(_jsonId);if(liveJson&&liveJson.disabled)jsonFsBtn.disabled=true;jsonFsBtn.onclick=function(){var dl=document.getElementById(_jsonId);if(dl&&!dl.disabled)dl.click();else showToast('Δεν υπάρχουν δεδομένα για JSON.');};actions.appendChild(jsonFsBtn);}var closeBtn=document.createElement('button');closeBtn.className='fs-close';closeBtn.innerHTML='✕';closeBtn.title='Κλείσιμο (Esc)';closeBtn.onclick=closeTableFs;actions.appendChild(closeBtn);toolbar.appendChild(actions);var body=document.createElement('div');body.className='fs-body';if(hasInteractive){var placeholder=document.createElement('div');placeholder.id='fs-placeholder';placeholder.style.display='none';source.parentNode.insertBefore(placeholder,source);body.appendChild(source);overlay._fsSource=source;overlay._fsPlaceholder=placeholder;}else{body.appendChild(source.cloneNode(true));}overlay.appendChild(toolbar);overlay.appendChild(body);document.body.appendChild(overlay);document.body.style.overflow='hidden';}
function closeTableFs(){var overlay=document.getElementById('fs-overlay');if(overlay){if(overlay._fsSource&&overlay._fsPlaceholder){overlay._fsPlaceholder.parentNode.insertBefore(overlay._fsSource,overlay._fsPlaceholder);overlay._fsPlaceholder.remove();}overlay.remove();document.body.style.overflow='';}}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeTableFs();});
function _patchSyntaksiInPrintHtml(html){if(typeof html!=='string'||!html)return html||'';var liveList=document.querySelectorAll('.syntaksi-layout');if(!liveList||!liveList.length)return html;var printMap=window._atlasSyntaksiPrint||{};var any=false;try{var doc=new DOMParser().parseFromString(html,'text/html');Array.prototype.forEach.call(liveList,function(live){var pfx=(live.id||'syntaksi-section').replace(/-section$/,'')||'syntaksi';var fn=printMap[pfx]||window._atlasSyntaksiGetPrintBody;if(typeof fn!=='function')return;var pb=fn();if(!pb||!pb.ok)return;var sec=doc.getElementById(pfx+'-section');if(!sec)return;any=true;var printMount=doc.getElementById(pfx+'-table-mount');if(printMount){printMount.innerHTML=pb.tableHtml;printMount.removeAttribute('hidden');printMount.classList.add('syntaksi-print-table-mount');}var pe=doc.getElementById(pfx+'-empty');if(pe)pe.setAttribute('hidden','hidden');var fb=doc.getElementById(pfx+'-filters-bar');if(fb)fb.setAttribute('hidden','hidden');var act=doc.getElementById(pfx+'-json-dl');if(act)act.setAttribute('hidden','hidden');var liveMetrics=sec.querySelector('#'+pfx+'-metrics-wrap');if(liveMetrics)liveMetrics.setAttribute('hidden','hidden');var sumMount=sec.querySelector('.syntaksi-print-summary-mount');if(!sumMount){sumMount=doc.createElement('div');sumMount.className='syntaksi-print-summary-mount syntaksi-print';var mnt=doc.getElementById(pfx+'-table-mount');if(mnt)sec.insertBefore(sumMount,mnt);else sec.appendChild(sumMount);}sumMount.innerHTML=pb.summaryHtml;sec.classList.add('syntaksi-print');var h2=sec.querySelector('h2');if(h2&&!sec.querySelector('h1.syntaksi-print-h1')){var h1=doc.createElement('h1');h1.className='syntaksi-print-h1';h1.textContent=h2.textContent;h2.replaceWith(h1);}var oldDesc=sec.querySelector('p.print-description:not(.syntaksi-print-calc-note)');if(oldDesc)oldDesc.setAttribute('hidden','hidden');if(!sec.querySelector('.syntaksi-print-disclaimer')&&pb.disclaimerHtml){var disc=doc.createElement('div');disc.className='syntaksi-print-disclaimer';disc.innerHTML=pb.disclaimerHtml;sec.appendChild(disc);}});if(!any)return html;return'<!DOCTYPE html>\n'+doc.documentElement.outerHTML;}catch(e){return html;}}
function openPrint(){if(typeof updatePersonalTitle==='function')updatePersonalTitle();if(typeof persistInteractiveValues==='function')persistInteractiveValues(document.body);var safeName=(typeof _clientName==='string'?_clientName:'').trim().replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');var html=_printHtml;if(typeof _patchApdInPrintHtml==='function')html=_patchApdInPrintHtml(html);if(typeof _patchSyntaksiInPrintHtml==='function')html=_patchSyntaksiInPrintHtml(html);if(safeName)html=html.replace(/<body>/,'<body><div class="prt-name">'+safeName+'</div>');var blob=new Blob([html],{type:'text/html;charset=utf-8'});var url=URL.createObjectURL(blob);window.open(url,'_blank');}
function getFullSaveFilename(){var n=document.getElementById('personal_fullname');var t=document.getElementById('personal_tameio');var ak=document.getElementById('personal_amka');var name=(n&&n.value)?n.value.trim():'';var tameio=(t&&t.options[t.selectedIndex])?t.options[t.selectedIndex].text.trim():'';var amka=(ak&&ak.value)?ak.value.trim():'';function sanitize(s){return (s||'').replace(/[\s\/\\:*?"<>|]+/g,' ').trim().replace(/\s+/g,'_')||'';}var a=sanitize(name),b=sanitize(tameio),c=sanitize(amka);var parts=[a,b,c].filter(Boolean);var ds=document.body&&document.body.getAttribute('data-atlas-save-file');var suf=(ds&&String(ds).trim())?String(ds).trim():((typeof _fullSaveSuffix==='string'&&_fullSaveSuffix)?_fullSaveSuffix:'ATLAS Pro.html');return (parts.length?parts.join('_')+'_':'')+suf;}
function persistInteractiveValues(root){var r=root||document.body;if(!r||!r.querySelectorAll)return;r.querySelectorAll('input').forEach(function(inp){var t=(inp.type||'').toLowerCase();if(t==='checkbox'||t==='radio'){if(inp.checked)inp.setAttribute('checked','checked');else inp.removeAttribute('checked');}else if(t!=='file'&&t!=='button'&&t!=='submit'&&t!=='image'){inp.setAttribute('value',inp.value);}});r.querySelectorAll('textarea').forEach(function(ta){ta.textContent=ta.value;});r.querySelectorAll('select').forEach(function(sel){Array.from(sel.options).forEach(function(opt){if(opt.selected)opt.setAttribute('selected','selected');else opt.removeAttribute('selected');});});}
function getExcelSaveFilename(){var base=(typeof getFullSaveFilename==='function'?getFullSaveFilename():(_downloadFilename||'ATLAS Pro.html'));if(/\.html$/i.test(base))return base.replace(/\.html$/i,'.xlsx');return base.replace(/\.(xlsx)?$/i,'')+'.xlsx';}
/* ===== Excel export (ζωντανό, από DOM, μέσω SheetJS) ===== */
function _atlasExcelReady(){return typeof XLSX!=='undefined'&&XLSX&&XLSX.utils;}
function _atlasCellText(td){return (td.textContent||'').replace(/\u00a0/g,' ').replace(/\s+/g,' ').trim();}
function _atlasRowVisible(tr){if(!tr)return false;if(tr.hasAttribute('hidden'))return false;if(tr.getAttribute('aria-hidden')==='true')return false;var st=window.getComputedStyle(tr);if(st&&st.display==='none')return false;return true;}
function _atlasCellVisible(td){var st=window.getComputedStyle(td);if(st&&(st.display==='none'||st.visibility==='hidden'))return false;return true;}
function _atlasParseCell(raw){
  if(raw==null)return {t:'s',v:''};
  var s=String(raw).replace(/\u00a0/g,' ').replace(/\s+/g,' ').trim();
  if(s===''||s==='-'||s==='—')return {t:'s',v:''};
  var dm=s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if(dm){var dd=parseInt(dm[1],10),mm=parseInt(dm[2],10),yy=parseInt(dm[3],10);var dt=new Date(yy,mm-1,dd,12,0,0);if(!isNaN(dt.getTime()))return {t:'d',v:dt,z:'dd/mm/yyyy'};}
  if(!/\d/.test(s))return {t:'s',v:s};
  var body=s.replace(/€|ΔΡΧ|%/g,'').replace(/[A-Za-zΑ-Ωα-ωΆ-Ώά-ώ]/g,'').trim();
  var neg=false;
  if(/^\(.*\)$/.test(body)){neg=true;body=body.slice(1,-1).trim();}
  body=body.replace(/\u2212/g,'-');
  if(/^-/.test(body)){neg=true;body=body.replace(/^-+/,'').trim();}
  if(/-$/.test(body)){neg=true;body=body.replace(/-+$/,'').trim();}
  body=body.replace(/\s/g,'');
  if(!/^[\d.,]+$/.test(body)||!/\d/.test(body))return {t:'s',v:s};
  var hadGroup=false,decimals=0,numStr;
  if(body.indexOf(',')>=0){
    var parts=body.split(',');var intp=parts[0];var decp=parts.slice(1).join('');
    hadGroup=/^\d{1,3}(\.\d{3})+$/.test(intp);intp=intp.replace(/\./g,'');decimals=decp.length;numStr=intp+'.'+decp;
  }else if(body.indexOf('.')>=0){
    if(/^\d{1,3}(\.\d{3})+$/.test(body)){hadGroup=true;numStr=body.replace(/\./g,'');decimals=0;}
    else{numStr=body;decimals=(body.split('.')[1]||'').length;hadGroup=false;}
  }else{numStr=body;decimals=0;hadGroup=false;}
  var num=parseFloat(numStr);
  if(isNaN(num))return {t:'s',v:s};
  if(neg)num=-num;
  var intFmt=hadGroup?'#,##0':'0';
  var z=decimals>0?(intFmt+'.'+new Array(decimals+1).join('0')):intFmt;
  return {t:'n',v:num,z:z};
}
function _atlasExtractTable(table){
  var rowEls=[],headFlags=[];
  function add(list,head){for(var i=0;i<list.length;i++){if(_atlasRowVisible(list[i])){rowEls.push(list[i]);headFlags.push(head);}}}
  if(table.tHead)add(table.tHead.rows,true);
  for(var b=0;b<table.tBodies.length;b++)add(table.tBodies[b].rows,false);
  if(table.tFoot)add(table.tFoot.rows,false);
  var cells=[],occ={};
  for(var r=0;r<rowEls.length;r++){
    var tds=rowEls[r].cells,c=0;
    for(var k=0;k<tds.length;k++){
      var td=tds[k];
      if(!_atlasCellVisible(td))continue;
      while(occ[r+'_'+c])c++;
      var cs=td.colSpan||1,rs=td.rowSpan||1;
      var val=headFlags[r]?{t:'s',v:_atlasCellText(td)}:_atlasParseCell(_atlasCellText(td));
      for(var i=0;i<rs;i++){for(var j=0;j<cs;j++){var rr=r+i,cc=c+j;occ[rr+'_'+cc]=true;if(!cells[rr])cells[rr]=[];if(cells[rr][cc]===undefined)cells[rr][cc]=(i===0&&j===0)?val:null;}}
      c+=cs;
    }
  }
  return {cells:cells,headRows:(table.tHead&&table.tHead.rows.length?1:0)};
}
function _atlasHeaderSig(cells){if(!cells.length)return '';return (cells[0]||[]).map(function(o){return o&&o.v!=null?String(o.v):'';}).join('\u0001');}
function _atlasCellsToSheet(cells){
  var ws={},maxR=cells.length,maxC=0,r,c;
  for(r=0;r<maxR;r++){if(cells[r]&&cells[r].length>maxC)maxC=cells[r].length;}
  for(r=0;r<maxR;r++){var row=cells[r];if(!row)continue;for(c=0;c<row.length;c++){var cell=row[c];if(cell==null)continue;if(cell.t==='s'&&cell.v==='')continue;var addr=XLSX.utils.encode_cell({r:r,c:c});var o={t:cell.t,v:cell.v};if(cell.z)o.z=cell.z;ws[addr]=o;}}
  ws['!ref']=XLSX.utils.encode_range({s:{r:0,c:0},e:{r:Math.max(maxR-1,0),c:Math.max(maxC-1,0)}});
  return ws;
}
function _atlasSheetName(label,used){var s=String(label||'Φύλλο').replace(/[\[\]:*?\/\\]/g,'_').trim().slice(0,31)||'Φύλλο';var base=s,n=1;while(used[s]){var suf='_'+n;s=base.slice(0,31-suf.length)+suf;n++;}used[s]=true;return s;}
function _atlasSanitizeFilename(s){return String(s||'ATLAS').replace(/[\/\\:*?"<>|]+/g,' ').replace(/\s+/g,' ').trim();}
function _atlasTabLabel(tid){var el=document.querySelector('.nav-item[data-tab="'+tid+'"]');return el?el.textContent.trim():tid;}
function _atlasYearLabelBefore(table){var sec=table.closest?table.closest('.year-section'):null;if(sec){var h=sec.querySelector('.year-heading');if(h)return h.textContent.trim();}return '';}
function _atlasPaneToSheets(root,label){
  var tables=root.querySelectorAll('table.print-table');
  var sheets=[],cur=null,curSig=null;
  for(var i=0;i<tables.length;i++){
    var ext=_atlasExtractTable(tables[i]);
    if(!ext.cells.length)continue;
    var sig=_atlasHeaderSig(ext.cells);
    var yl=_atlasYearLabelBefore(tables[i]);
    if(cur&&sig===curSig){
      if(yl)cur.cells.push([{t:'s',v:yl}]);
      for(var r=ext.headRows;r<ext.cells.length;r++)cur.cells.push(ext.cells[r]);
    }else{
      cur={name:label,cells:ext.cells.slice()};curSig=sig;sheets.push(cur);
      if(yl)cur.cells.splice(ext.headRows,0,[{t:'s',v:yl}]);
    }
  }
  if(sheets.length>1){for(var s=0;s<sheets.length;s++)sheets[s].name=label+' '+(s+1);}
  return sheets;
}
function _atlasDownloadSheets(sheets,filename){
  if(!_atlasExcelReady()){showToast('Δεν φορτώθηκε η βιβλιοθήκη Excel.');return;}
  if(!sheets||!sheets.length){showToast('Δεν βρέθηκαν δεδομένα για εξαγωγή.');return;}
  var wb=XLSX.utils.book_new(),used={};
  sheets.forEach(function(sh){var ws=_atlasCellsToSheet(sh.cells);XLSX.utils.book_append_sheet(wb,ws,_atlasSheetName(sh.name,used));});
  try{XLSX.writeFile(wb,filename,{cellDates:true});showToast('Λήφθηκε το Excel.');}catch(e){console.error(e);showToast('Σφάλμα εξαγωγής Excel.');}
}
function _atlasBaseName(){var base=(typeof getFullSaveFilename==='function'?getFullSaveFilename():(_downloadFilename||'ATLAS Pro.html'));return base.replace(/\.html$/i,'');}
function exportTabExcel(sourceEl,label){
  var sheets=_atlasPaneToSheets(sourceEl,label||'Πίνακας');
  if(!sheets.length&&sourceEl.matches&&sourceEl.matches('table.print-table')){var ext=_atlasExtractTable(sourceEl);if(ext.cells.length)sheets=[{name:label||'Πίνακας',cells:ext.cells}];}
  _atlasDownloadSheets(sheets,_atlasSanitizeFilename(_atlasBaseName()+' - '+(label||'Πίνακας'))+'.xlsx');
}
function downloadExcelReport(){
  if(!_atlasExcelReady()){showToast('Δεν φορτώθηκε η βιβλιοθήκη Excel.');return;}
  var sheets=[],panes=document.querySelectorAll('.tab-pane');
  for(var i=0;i<panes.length;i++){
    var pane=panes[i],tid=(pane.id||'').replace(/^pane-/,'');
    if(tid==='personal'||tid==='timeline'||tid==='syntaksi')continue;
    var label=_atlasTabLabel(tid)||tid;
    var ps=_atlasPaneToSheets(pane,label);
    for(var j=0;j<ps.length;j++)sheets.push(ps[j]);
  }
  if(!sheets.length){showToast('Δεν υπάρχουν δεδομένα για εξαγωγή.');return;}
  _atlasDownloadSheets(sheets,(typeof getExcelSaveFilename==='function'?getExcelSaveFilename():'ATLAS Pro.xlsx'));
}
function downloadFullHtml(){persistInteractiveValues(document.body);var html='<!DOCTYPE html>\n'+document.documentElement.outerHTML;var blob=new Blob([html],{type:'text/html;charset=utf-8'});var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(typeof getFullSaveFilename==='function'?getFullSaveFilename():_downloadFilename);a.click();URL.revokeObjectURL(a.href);}
function showToast(message){var container=document.getElementById('toast-container');var toast=document.createElement('div');toast.className='toast';toast.textContent=message;container.appendChild(toast);void toast.offsetWidth;toast.classList.add('show');setTimeout(function(){toast.classList.remove('show');setTimeout(function(){if(container.contains(toast))container.removeChild(toast);},300);},2000);}
document.addEventListener('click',function(e){var target=e.target.closest('.copy-target');if(!target||target.closest('#pane-synopsis'))return;var text=target.innerText.trim();if(text&&text!=='-'&&text!==''){navigator.clipboard.writeText(text).then(function(){showToast('Αντιγράφηκε: '+text);}).catch(function(err){console.error('Copy failed:',err);});}});
document.addEventListener('DOMContentLoaded',function(){document.querySelectorAll('.print-section').forEach(function(sec){if(sec.closest('#pane-personal'))return;var actions=document.createElement('div');actions.className='section-actions';var _isSyn=sec.classList&&sec.classList.contains('syntaksi-layout');if(_isSyn){var _synPfx=(sec.id||'syntaksi-section').replace(/-section$/,'')||'syntaksi';var jsonBtn=sec.querySelector('#'+_synPfx+'-json-dl');if(jsonBtn){jsonBtn.removeAttribute('hidden');actions.appendChild(jsonBtn);}}var printBtn=document.createElement('button');printBtn.className='btn-print-tab';printBtn.innerHTML='🖨';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(e){e.stopPropagation();printSection(sec);};actions.appendChild(printBtn);if(!sec.closest('#pane-synopsis')){var fsBtn=document.createElement('button');fsBtn.className='btn-fs';fsBtn.innerHTML='⛶';fsBtn.title='Πλήρης οθόνη';fsBtn.onclick=function(e){e.stopPropagation();openTableFs(sec);};actions.appendChild(fsBtn);}if(typeof XLSX!=='undefined'&&(sec.querySelector('table.print-table')||_isSyn)){var xlsBtn=document.createElement('button');xlsBtn.className='btn-xls-tab';xlsBtn.innerHTML='📊';xlsBtn.title='Εξαγωγή αυτού του πίνακα σε Excel (όπως εμφανίζεται)';xlsBtn.onclick=function(e){e.stopPropagation();var pane=sec.closest('.tab-pane');var tid=pane?(pane.id||'').replace(/^pane-/,''):'';var lbl=_atlasTabLabel(tid);if(!lbl||lbl===tid){var h=sec.querySelector('h2');lbl=h?h.textContent.trim():(lbl||'Πίνακας');}exportTabExcel(sec,lbl);};actions.appendChild(xlsBtn);}sec.appendChild(actions);});
document.querySelectorAll('table.print-table').forEach(function(tbl){if(tbl.closest('.print-section'))return;var wrapper=document.createElement('div');wrapper.className='table-container';tbl.parentNode.insertBefore(wrapper,tbl);wrapper.appendChild(tbl);var actions=document.createElement('div');actions.className='section-actions';var printBtn=document.createElement('button');printBtn.className='btn-print-tab';printBtn.innerHTML='🖨';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(e){e.stopPropagation();printSection(tbl);};var fsBtn=document.createElement('button');fsBtn.className='btn-fs';fsBtn.innerHTML='⛶';fsBtn.title='Πλήρης οθόνη';fsBtn.onclick=function(e){e.stopPropagation();openTableFs(tbl);};actions.appendChild(printBtn);actions.appendChild(fsBtn);if(typeof XLSX!=='undefined'){var xlsBtn2=document.createElement('button');xlsBtn2.className='btn-xls-tab';xlsBtn2.innerHTML='📊';xlsBtn2.title='Εξαγωγή αυτού του πίνακα σε Excel (όπως εμφανίζεται)';xlsBtn2.onclick=function(e){e.stopPropagation();var pane=tbl.closest('.tab-pane');var tid=pane?(pane.id||'').replace(/^pane-/,''):'';var lbl=_atlasTabLabel(tid)||'Πίνακας';exportTabExcel(tbl,lbl);};actions.appendChild(xlsBtn2);}wrapper.appendChild(actions);});
var targetColumns=['Συνολικές ημέρες','Μικτές αποδοχές','Συνολικές εισφορές','ΣΥΝΟΛΟ','ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ','ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ','ΑΠΟΔΟΧΕΣ','ΕΙΣΦΟΡΕΣ','Ημέρες Ασφ.','Σύνολο','Μικτές Αποδοχές','Συνολικές Εισφορές'];
var tables=document.querySelectorAll('table.print-table');tables.forEach(function(table){var headers=table.querySelectorAll('thead th');var targetIndices=[];headers.forEach(function(th,index){var headerText=th.textContent.trim();if(targetColumns.some(function(col){return headerText.indexOf(col)!==-1;})){targetIndices.push(index);}});if(targetIndices.length>0){var rows=table.querySelectorAll('tbody tr');rows.forEach(function(row){var cells=row.querySelectorAll('td');targetIndices.forEach(function(index){if(cells[index]){cells[index].classList.add('copy-target');cells[index].title='Κλικ για αντιγραφή';}});});}});
var cardElements=document.querySelectorAll('.audit-card-result');cardElements.forEach(function(el){if(el.closest('#pane-synopsis'))return;el.classList.add('copy-target');el.title='Κλικ για αντιγραφή';});});
"""

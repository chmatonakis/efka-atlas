"""
report_json_export.py
~~~~~~~~~~~~~~~~~~~~
Παραγωγή ενιαίου JSON payload από τα δεδομένα ΑΤΛΑΣ.
Χρησιμοποιεί τις ίδιες συναρτήσεις με το Streamlit / html_viewer_builder.
"""

from __future__ import annotations

import sys
from pathlib import Path as _Path

_root = _Path(__file__).resolve().parent
_kyria = _root / "LOCAL_DEV" / "kyria"
if _kyria.exists() and not (_root / "app_final.py").exists():
    sys.path.insert(0, str(_kyria))

import json
from typing import Any

import pandas as pd

from app_final import (
    build_description_map,
    build_count_report,
    build_parallel_2017_print_df,
    build_parallel_print_df,
    build_multi_employment_print_df,
    build_summary_grouped_display,
    compute_complex_file_metrics,
    find_gaps_in_insurance_data,
    find_zero_duration_intervals,
    generate_audit_report,
    should_show_complex_file_warning,
)
from html_viewer_builder import (
    EXCLUDED_PACKAGES,
    EXCLUDED_PACKAGES_LABEL,
    build_timeline_data,
    filter_count_df,
    _precompute_date_keys,
    _totals_raw_records_for_js,
)


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame σε list of dicts με NaN -> None για JSON."""
    if df is None or df.empty:
        return []
    out = []
    for _, row in df.iterrows():
        rec = {}
        for k in row.index:
            v = row[k]
            if pd.isna(v):
                rec[str(k)] = None
            elif hasattr(v, "strftime"):
                rec[str(k)] = v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else str(v)
            else:
                rec[str(k)] = v
        out.append(rec)
    return out


def _safe_df_to_records(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return _df_to_records(df)


def _exclude_unused_packages(dataframe: pd.DataFrame) -> pd.DataFrame:
    pkg_col = None
    for c in ["Κλάδος/Πακέτο Κάλυψης", "Κλάδος/Πακέτο", "ΚΛΑΔΟΣ/ΠΑΚΕΤΟ"]:
        if c in dataframe.columns:
            pkg_col = c
            break
    if pkg_col is None:
        return dataframe
    pkg_series = dataframe[pkg_col].astype(str).str.strip()
    return dataframe[~pkg_series.isin(EXCLUDED_PACKAGES)].copy()


def _apd_misthoti_only(apd_df: pd.DataFrame) -> pd.DataFrame:
    if "Τύπος Ασφάλισης" not in apd_df.columns:
        return apd_df

    def _is_misthoti(val):
        if pd.isna(val):
            return False
        u = str(val).upper().strip()
        if "ΜΙΣΘΩΤΗ" not in u:
            return False
        if "ΜΗΜΙΣΘΩΤΗ" in u or "ΜΗ ΜΙΣΘΩΤΗ" in u:
            return False
        return True

    return apd_df[apd_df["Τύπος Ασφάλισης"].apply(_is_misthoti)].copy()


def _get_insurance_status_message(df: pd.DataFrame) -> str:
    is_palios = False
    if "Από" in df.columns:
        try:
            from_dates = pd.to_datetime(df["Από"], format="%d/%m/%Y", errors="coerce")
            if not from_dates.isnull().all() and from_dates.min() < pd.Timestamp("1993-01-01"):
                is_palios = True
        except Exception:
            pass
    return (
        "Παλιός Ασφαλισμένος (εγγραφή πριν από 1/1/1993)"
        if is_palios
        else "Νέος Ασφαλισμένος (χωρίς εγγραφή πριν από 1/1/1993)"
    )


def build_report_payload(
    df: pd.DataFrame,
    extra_df: pd.DataFrame | None = None,
    client_name: str = "",
) -> dict[str, Any]:
    """
    Δημιουργεί το πλήρες JSON payload για το report.

    Καλεί τις ίδιες συναρτήσεις με το build_report_tab_entries και τις
    αντίστοιχες λογικές για ΑΠΔ. Επιστρέφει dict κατάλληλο για json.dumps().
    """
    if df is None or df.empty:
        return {"meta": {"client_name": client_name, "error": "Δεν υπάρχουν δεδομένα"}, "audit": []}

    description_map = build_description_map(df)
    count_df = filter_count_df(df)
    audit_df = generate_audit_report(df, extra_df)
    display_summary = (
        build_summary_grouped_display(df, df)
        if "Κλάδος/Πακέτο Κάλυψης" in df.columns
        else pd.DataFrame()
    )

    count_display_df, _, _, _, print_style_rows = build_count_report(
        count_df, description_map=description_map, show_count_totals_only=False
    )

    show_complex_warning = False
    try:
        n_agg, n_limits_25, n_unpaid = compute_complex_file_metrics(df)
        show_complex_warning = should_show_complex_file_warning(n_agg, n_limits_25, n_unpaid)
    except Exception:
        pass

    # --- meta ---
    meta = {
        "client_name": (client_name or "").strip(),
        "excluded_packages": list(sorted(EXCLUDED_PACKAGES)),
        "excluded_packages_label": EXCLUDED_PACKAGES_LABEL,
        "description_map": {str(k): str(v) for k, v in (description_map or {}).items()},
        "complex_file_warning": show_complex_warning,
    }

    # --- audit ---
    payload = {
        "meta": meta,
        "audit": _safe_df_to_records(audit_df),
    }

    # --- totals ---
    if not display_summary.empty:
        paketo_col = "Κλάδος/Πακέτο Κάλυψης"
        tameio_col = "Ταμείο"
        paketo_vals = (
            sorted(display_summary[paketo_col].dropna().astype(str).str.strip().unique().tolist())
            if paketo_col in display_summary.columns
            else []
        )
        tameio_vals = (
            sorted(display_summary[tameio_col].dropna().astype(str).str.strip().unique().tolist())
            if tameio_col in display_summary.columns
            else []
        )
        paketo_options = []
        for v in paketo_vals:
            desc = (description_map.get(v) or "").strip()
            paketo_options.append({"value": v, "label": f"{v} – {desc}" if desc else v})
        tameio_options = [{"value": v, "label": v} for v in tameio_vals]

        dk_map_serialized = {}
        group_keys = [paketo_col]
        if tameio_col in display_summary.columns:
            group_keys.append(tameio_col)
        try:
            dk_df = _precompute_date_keys(df, group_keys, desc_map=description_map)
            dk_cols = ["dk1", "dk3", "dk4", "dk5", "dk6", "dk7a", "dk7b", "dk7c"]
            for _, dkrow in dk_df.iterrows():
                key_tuple = tuple(str(dkrow.get(k, "")).strip() for k in group_keys)
                key_str = "|".join(key_tuple)
                dk_map_serialized[key_str] = {c: int(dkrow.get(c, 0)) for c in dk_cols}
        except Exception:
            pass

        raw_records = _totals_raw_records_for_js(df)

        payload["totals"] = {
            "rows": _df_to_records(display_summary),
            "filter_options": {
                "paketo_options": paketo_options,
                "tameio_options": tameio_options,
            },
            "dk_map": dk_map_serialized,
            "raw_records": raw_records,
        }
    else:
        payload["totals"] = {"rows": [], "filter_options": {}, "dk_map": {}, "raw_records": []}

    # --- count ---
    payload["count"] = {
        "rows": _safe_df_to_records(count_display_df),
        "style_rows": [
            {str(k): (v if isinstance(v, str) else str(v) if v is not None else "")
             for k, v in row.items()}
            for row in (print_style_rows or [])
        ],
    }

    # --- gaps ---
    gaps_df = None
    zero_duration_df = None
    try:
        gaps_df = find_gaps_in_insurance_data(df)
        zero_duration_df = find_zero_duration_intervals(df)
    except Exception:
        pass
    payload["gaps"] = {
        "gaps": _safe_df_to_records(gaps_df),
        "zero_duration": _safe_df_to_records(zero_duration_df),
    }

    # --- parallel, parallel_2017, multi ---
    def _safe_parallel(fn, *args):
        try:
            return fn(*args)
        except Exception:
            return None

    parallel_df = _safe_parallel(build_parallel_print_df, df, description_map)
    parallel_2017_df = _safe_parallel(build_parallel_2017_print_df, df, description_map)
    multi_df = _safe_parallel(build_multi_employment_print_df, df, description_map)

    payload["parallel"] = _safe_df_to_records(parallel_df) if parallel_df is not None else []
    payload["parallel_2017"] = _safe_df_to_records(parallel_2017_df) if parallel_2017_df is not None else []
    payload["multi"] = _safe_df_to_records(multi_df) if multi_df is not None else []

    # --- timeline ---
    try:
        timeline_data = build_timeline_data(df)
        payload["timeline"] = timeline_data if timeline_data else {}
    except Exception:
        payload["timeline"] = {}

    # --- apd ---
    apd_columns = [
        col for col in df.columns
        if col not in ["Φορέας", "Κωδικός Κλάδων / Πακέτων Κάλυψης", "Περιγραφή", "Κωδικός Τύπου Αποδοχών", "Σελίδα"]
    ]
    apd_df = df[apd_columns].copy() if apd_columns else df.copy()
    if "Σελίδα" in apd_df.columns:
        apd_df = apd_df.drop("Σελίδα", axis=1)
    apd_df = _exclude_unused_packages(apd_df)
    apd_df = _apd_misthoti_only(apd_df)

    apd_options = {"tameia": [], "klados": [], "typos_apodochon": []}
    if "Ταμείο" in apd_df.columns:
        apd_options["tameia"] = sorted(apd_df["Ταμείο"].dropna().astype(str).unique().tolist())
    if "Κλάδος/Πακέτο Κάλυψης" in apd_df.columns:
        apd_options["klados"] = sorted(apd_df["Κλάδος/Πακέτο Κάλυψης"].dropna().astype(str).unique().tolist())
    earnings_col = next((c for c in apd_df.columns if "Τύπος Αποδοχών" in c), None)
    if earnings_col:
        apd_options["typos_apodochon"] = sorted(apd_df[earnings_col].dropna().astype(str).unique().tolist())

    payload["apd"] = {
        "rows": _safe_df_to_records(apd_df),
        "filter_defaults": {
            "from_date": "01/01/2002",
            "to_date": "",
            "filter_pct": 18.0,
            "highlight_pct": 21.0,
            "retention_mode": "Όλα",
        },
        "options": apd_options,
        "insurance_status_message": _get_insurance_status_message(df),
        "excluded_packages_label": EXCLUDED_PACKAGES_LABEL,
    }

    return payload


def build_report_json(
    df: pd.DataFrame,
    extra_df: pd.DataFrame | None = None,
    client_name: str = "",
    indent: int | None = 2,
) -> str:
    """Επιστρέφει το payload ως JSON string (UTF-8, ensure_ascii=False)."""
    payload = build_report_payload(df, extra_df=extra_df, client_name=client_name)
    return json.dumps(payload, ensure_ascii=False, indent=indent)

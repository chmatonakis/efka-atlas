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
if _kyria.exists() and not (_root / "app_final.py").exists():
    sys.path.insert(0, str(_kyria))

import datetime
import html as html_mod
import json
import re
import unicodedata

import pandas as pd

from app_final import (
    build_print_section_html,
    build_print_table_html,
    build_yearly_print_html,
    build_count_report,
    build_description_map,
    build_parallel_print_df,
    build_parallel_2017_print_df,
    build_multi_employment_print_df,
    build_summary_grouped_display,
    compute_summary_capped_days_by_group,
    compute_summary_capped_dk,
    compute_complex_file_metrics,
    find_gaps_in_insurance_data,
    find_zero_duration_intervals,
    generate_audit_report,
    get_print_disclaimer_html,
    should_show_complex_file_warning,
    clean_numeric_value,
    apply_negative_time_sign,
    APODOXES_DESCRIPTIONS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_PACKAGES = {"Α", "Λ", "Υ", "Ο", "Χ", "026", "899"}
EXCLUDED_PACKAGES_LABEL = ", ".join(sorted(EXCLUDED_PACKAGES))
EXCLUSION_NOTE_HTML = (
    f'<div class="lite-exclusion-note">'
    f'Εξαιρούνται από την καταμέτρηση: {EXCLUDED_PACKAGES_LABEL}'
    f'</div>'
)
COMPLEX_FILE_WARNING_HTML = (
    '<div class="complex-file-warning" style="'
    'background:rgba(254,242,242,0.88);border:none;border-radius:8px;'
    'padding:12px 16px;margin-bottom:16px;'
    'color:#991b1b;font-weight:700;font-size:1rem;">'
    '⚠️ Προσοχή: Περίπλοκο αρχείο — Ελέγξτε απαραίτητα το πρωτότυπο ΑΤΛΑΣ.'
    '</div>'
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

    period_str = f"{global_min.strftime('%d/%m/%Y')} — {global_max.strftime('%d/%m/%Y')}"

    # Δεύτερο χρονολόγιο (πακέτα): στατικό HTML ώστε η συνολική εκτύπωση να το περιλαμβάνει
    # (το JS buildPaketoTimeline τρέχει μόνο στο live viewer).
    _desc_tl = build_description_map(source_df)
    _recs_tl = _totals_raw_records_for_js(source_df)
    paketo_rows_inner = _build_paketo_timeline_rows_html(_recs_tl, _desc_tl)

    return f"""
    <section class="print-section">
      <h2>Ιστορικό Ασφάλισης</h2>
      <p class="print-description">Οπτική απεικόνιση χρονικών περιόδων ασφάλισης ανά Ταμείο. Περίοδος: {html_mod.escape(period_str)}</p>
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
.print-description { font-size: 13px; color: #64748b; margin: 0 0 14px 0; line-height: 1.45; }
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
    rdf['_h'] = (
        rdf['Ημέρες'].fillna(0)
        + rdf['Μήνες'].fillna(0) * month_days
        + rdf['Έτη'].fillna(0) * year_days
    ).clip(lower=0).round(0).astype(int)

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
    apodochon_options = [(v, v) for v in apodochon_vals]

    def _dropdown(name, options, data_attr):
        if not options:
            return ""
        items = "".join(
            f'<label class="filter-cb"><input type="checkbox" name="{name}" '
            f'value="{html_mod.escape(str(val))}" data-attr="{data_attr}">'
            f'{html_mod.escape(label)}</label>'
            for val, label in options
        )
        return (
            f'<div class="filter-group filter-dropdown" data-filter-name="{html_mod.escape(name)}" data-filter-key="{html_mod.escape(data_attr)}">'
            f'<div class="filter-dropdown-trigger" tabindex="0" role="button" '
            f'aria-haspopup="listbox" aria-expanded="false" '
            f'title="Επιλέξτε {html_mod.escape(name)}">'
            f'{html_mod.escape(name)}</div>'
            f'<div class="filter-dropdown-panel" role="listbox">'
            f'<div class="filter-options">{items}</div></div>'
            f'<div class="filter-selected-label" aria-live="polite"></div></div>'
        )

    paketo_filters = _dropdown("Πακέτο", paketo_options, "paketo")
    tameio_filters = _dropdown("Ταμείο", tameio_options, "tameio")
    typos_filters = _dropdown("Τύπος ασφάλισης", typos_options, "typos") if typos_options else ""
    apodochon_filters = _dropdown("Τύπος αποδοχών", apodochon_options, "typosApod") if apodochon_options else ""
    date_filters = (
        '<div class="filter-group">'
        '<input type="text" id="filter-apo" class="filter-date" placeholder="Από (ηη/μμ/εεεε)" maxlength="10">'
        '</div>'
        '<div class="filter-group">'
        '<input type="text" id="filter-eos" class="filter-date" placeholder="Έως (ηη/μμ/εεεε)" maxlength="10">'
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
        f'<div class="{info_bar_class}">'
        f'<div class="totals-info-msg">{html_mod.escape(info_msg)}</div>'
        '<div class="totals-summary">'
        '<div class="totals-summary-item">'
        '<span class="totals-summary-label">Εκτίμηση Ημερών Ασφάλισης</span>'
        '<span class="totals-summary-value critical-result" id="totals-sum-hmeres">—</span></div>'
        '<div class="totals-summary-item">'
        '<span class="totals-summary-label">Συνολικά Έτη</span>'
        '<span class="totals-summary-value critical-result" id="totals-sum-eti">—</span></div>'
        '</div></div>'
    )

    required_cols = {'Από', 'Έως'}
    exceeded_lines_html = ""
    _server_cap_error = ""
    if raw_df is not None and not raw_df.empty and required_cols.issubset(set(raw_df.columns)):
        try:
            cap_group_keys = [paketo_col]
            if tameio_col in raw_df.columns:
                cap_group_keys.append(tameio_col)
            if typos_col in raw_df.columns:
                cap_group_keys.append(typos_col)
            _cap_result = compute_summary_capped_days_by_group(
                raw_df, cap_group_keys, month_days=25, year_days=300, ika_month_days=31
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
                exceeded_lines_html = "<br><br>".join(lines)
        except Exception as exc:
            _server_cap_error = str(exc)
    if exceeded_lines_html:
        exceeded_warning_div = (
            '<div id="totals-exceeded-warning" class="totals-exceeded-warning" role="alert">'
            '<strong>Υπέρβαση ορίου ημερών ανά μήνα</strong> (πλαφόν: ΙΚΑ 31 ημ./μήνα, '
            'ΕΤΑΑ-ΤΑΝ/ΚΕΑΔ και υπόλοιπα 25 ημ./μήνα· μήνυμα για ΕΤΑΑ-ΤΑΝ/ΚΕΑΔ μόνο όταν &gt;30):<br><br>'
            + exceeded_lines_html + '</div>'
        )
    else:
        exceeded_warning_div = (
            '<div id="totals-exceeded-warning" class="totals-exceeded-warning" style="display:none" role="alert"></div>'
        )
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
    custom_table = (
        f'<table class="print-table wrap-cells" id="totals-filter-table">'
        f'<thead><tr>{headers_html}</tr></thead>'
        f'<tbody>{table_body}</tbody></table>'
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
    calcs_panel = _build_date_key_calcs_panel()
    js = _build_totals_filter_js(raw_records_js, dk_map_js, desc_map_js,
                                  has_desc_col=has_desc_col,
                                  has_typos_col=has_typos_col,
                                  has_typos_apodochon_col=has_typos_apodochon_col,
                                  varea_codes_js=varea_js)

    return (
        f'<section class="print-section" id="totals-section">'
        f'<h2>Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)</h2>'
        f'<p class="print-description">Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης και Ταμείο.</p>'
        f'{info_banner}{exceeded_warning_div}{filters_bar}{custom_table}{calcs_panel}'
        f'<script>{js}</script></section>'
    )


def _build_date_key_calcs_panel():
    items = [
        ("1", "Ημέρες από 1/1/2002 έως σήμερα"),
        ("2", "Μήνες από 1/1/2002 έως σήμερα (ημέρες / 25)"),
        ("3", "Συνολικές ημέρες τα τελευταία 5 ημερολογιακά έτη από σήμερα"),
        ("4", "Συνολικές ημέρες τα τελευταία 5 ημερολογιακά έτη από το τελευταίο έτος"),
        ("5", "Ημέρες έως 31/12/2014"),
        ("6", "Βαρέα τα τελευταία 17 έτη από σήμερα (6205 ημέρες)"),
        ("7a", "Ημέρες έως 31/12/2010"),
        ("7b", "Ημέρες έως 31/12/2011"),
        ("7c", "Ημέρες έως 31/12/2012"),
    ]
    grid = "".join(
        f'<div class="date-key-item"><span class="date-key-num">{num}</span>'
        f'<div><div class="date-key-label">{label}</div>'
        f'<div class="date-key-value critical-result" id="calc-{num}">—</div></div></div>'
        for num, label in items
    )
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

  function pd(s){if(!s)return null;var m=s.match(/^(\\d{1,2})\\/(\\d{1,2})\\/(\\d{4})$/);return m?new Date(+m[3],m[2]-1,+m[1]):null;}
  function fi(n){return n===0?'0':n.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.');}
  function fd(n){var p=n.toFixed(1).split('.');return p[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.')+','+p[1];}
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

  function computeDkFromMonths(monthCapped,varea){
    var today=new Date(),cy=today.getFullYear();
    var d2002=new Date(2002,0,1),dFive=new Date(cy-4,0,1),d2014=new Date(2014,11,31);
    var d2010=new Date(2010,11,31),d2011=new Date(2011,11,31),d2012=new Date(2012,11,31);
    var BAREA=6205,winEnd=new Date(),winStart=new Date(winEnd.getTime()-BAREA*86400000);
    var maxY=0;
    for(var k in monthCapped){var pp=k.split('-');if(+pp[0]>maxY)maxY=+pp[0];}
    var fiveLast=maxY>=4?new Date(maxY-4,0,1):null,lastEnd=maxY>=4?new Date(maxY,11,31):null;
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

  function apply(){
    var sec=document.getElementById('totals-section');if(!sec)return;
    var pC=[],tC=[],tyC=[],etC=[];
    sec.querySelectorAll('.totals-filters input[name="\\u03A0\\u03B1\\u03BA\\u03AD\\u03C4\\u03BF"]:checked').forEach(function(cb){pC.push(cb.value);});
    sec.querySelectorAll('.totals-filters input[name="\\u03A4\\u03B1\\u03BC\\u03B5\\u03AF\\u03BF"]:checked').forEach(function(cb){tC.push(cb.value);});
    sec.querySelectorAll('.totals-filters input[name="\\u03A4\\u03CD\\u03C0\\u03BF\\u03C2 \\u03B1\\u03C3\\u03C6\\u03AC\\u03BB\\u03B9\\u03C3\\u03B7\\u03C2"]:checked').forEach(function(cb){tyC.push(cb.value);});
    sec.querySelectorAll('.totals-filters input[name="\\u03A4\\u03CD\\u03C0\\u03BF\\u03C2 \\u03B1\\u03C0\\u03BF\\u03B4\\u03BF\\u03C7\\u03CE\\u03BD"]:checked').forEach(function(cb){etC.push(cb.value);});

    var sel={paketo:pC,tameio:tC,typos:tyC,typosApod:etC};
    sec.querySelectorAll('.totals-filters .filter-dropdown').forEach(function(dd){
      var key=dd.getAttribute('data-filter-key');if(!key)return;
      var vals=sel[key]||[];
      var tr=dd.querySelector('.filter-dropdown-trigger'),lb=dd.querySelector('.filter-selected-label');
      var nm=dd.getAttribute('data-filter-name')||'';
      if(tr)tr.textContent=nm;if(lb){if(vals.length){var esc=function(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;};lb.innerHTML=vals.map(function(v){return '<span class="filter-selected-chip">'+esc(v)+'</span>';}).join('');}else lb.textContent='';}
    });

    var aV=(document.getElementById('filter-apo')||{value:''}).value.trim();
    var eV=(document.getElementById('filter-eos')||{value:''}).value.trim();
    var aD=aV?pd(aV):null,eD=eV?pd(eV):null;
    var totalH=0,allExc=[];

    if(Array.isArray(RR)&&RR.length>0){
      /* Φιλτράρισμα raw records */
      var filt=RR.filter(function(r){
        if(pC.length&&pC.indexOf(r.p)===-1)return false;
        if(tC.length&&tC.indexOf(r.t)===-1)return false;
        if(HT&&tyC.length&&(r.ty===undefined||tyC.indexOf(r.ty)===-1))return false;
        if(HE&&etC.length&&(r.et===undefined||etC.indexOf(r.et)===-1))return false;
        var rA=pd(r.apo),rE=pd(r.eos);if(!rA||!rE)return false;
        if(aD&&rE<aD)return false;if(eD&&rA>eD)return false;
        return true;
      });

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
        dkMapFromCap[ck]=computeDkFromMonths(res.monthCapped||{},isVarea);
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
          cells=cells.concat([g.apo,g.eos,fi(g.h),fd(y),fd(m),fd(d),fc(g.gross),fc(g.contrib),fi(g.n||0)]);
          while(cells.length<colCount)cells.push('');

          var tyA=HT?' data-typos="'+esc(g.ty||'')+'"':'';
          var etA=showEtDetail?' data-typos-apodochon="'+esc(g.et||'')+'"':'';
          return'<tr data-paketo="'+esc(g.p)+'" data-tameio="'+esc(g.t)+'"'+tyA+etA+' data-apo="'+esc(g.apo)+'" data-eos="'+esc(g.eos)+'" data-hmeres="'+g.h+'" '+dkA+'>'+cells.slice(0,colCount).map(function(c){return'<td>'+c+'</td>';}).join('')+'</tr>';
        });
        tbody.innerHTML=nR.join('');
      }

      /* Βήμα 6: Μήνυμα υπέρβασης */
      var exEl=document.getElementById('totals-exceeded-warning');
      if(exEl){
        if(allExc.length>0){
          var exL=allExc.map(function(e){
            var ms=MN[e.m]||e.m,ov=(e.days-e.limit).toFixed(1);
            var pp=['\\u03A0\\u03B1\\u03BA\\u03AD\\u03C4\\u03BF '+e.p];
            if(e.t)pp.push('\\u03A4\\u03B1\\u03BC\\u03B5\\u03AF\\u03BF: '+e.t);
            if(e.ty)pp.push('\\u03A4\\u03CD\\u03C0\\u03BF\\u03C2: '+e.ty);
            pp.push('\\u039C\\u03AE\\u03BD\\u03B1\\u03C2 '+ms+' '+e.y+': '+Math.round(e.days)+' \\u03B7\\u03BC\\u03AD\\u03C1\\u03B5\\u03C2 (\\u03CC\\u03C1\\u03B9\\u03BF '+e.limit+', \\u03C5\\u03C0\\u03AD\\u03C1\\u03B2\\u03B1\\u03C3\\u03B7 +'+ov+')');
            return esc(pp.join(' | '));
          });
          exEl.innerHTML='<strong>\\u03A5\\u03C0\\u03AD\\u03C1\\u03B2\\u03B1\\u03C3\\u03B7 \\u03BF\\u03C1\\u03AF\\u03BF\\u03C5 \\u03B7\\u03BC\\u03B5\\u03C1\\u03CE\\u03BD \\u03B1\\u03BD\\u03AC \\u03BC\\u03AE\\u03BD\\u03B1</strong> (\\u03C0\\u03BB\\u03B1\\u03C6\\u03CC\\u03BD: \\u0399\\u039A\\u0391 31 \\u03B7\\u03BC./\\u03BC\\u03AE\\u03BD\\u03B1, \\u0395\\u03A4\\u0391\\u0391-\\u03A4\\u0391\\u039D/\\u039A\\u0395\\u0391\\u0394 \\u03BA\\u03B1\\u03B9 \\u03C5\\u03C0\\u03CC\\u03BB\\u03BF\\u03B9\\u03C0\\u03B1 25 \\u03B7\\u03BC./\\u03BC\\u03AE\\u03BD\\u03B1\\u00B7 \\u03BC\\u03AE\\u03BD\\u03C5\\u03BC\\u03B1 \\u03B3\\u03B9\\u03B1 \\u0395\\u03A4\\u0391\\u0391-\\u03A4\\u0391\\u039D/\\u039A\\u0395\\u0391\\u0394 \\u03BC\\u03CC\\u03BD\\u03BF \\u03CC\\u03C4\\u03B1\\u03BD &gt;30):<br><br>'+exL.join('<br>');
          exEl.style.display='block';
        }else{exEl.innerHTML='';exEl.style.display='none';}
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
        if(ok)totalH+=parseInt(tr.getAttribute('data-hmeres')||'0',10);
      });
    }

    /* Metrics — μόνο αν έχει επιλεγεί πακέτο */
    var hasSel=pC.length>0;
    var elH=document.getElementById('totals-sum-hmeres'),elE=document.getElementById('totals-sum-eti');
    if(elH)elH.textContent=hasSel&&totalH>0?fi(totalH):'\\u2014';
    if(elE)elE.textContent=hasSel&&totalH>0?fd(totalH/YD):'\\u2014';

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
  }

  /* Bind events */
  var sec=document.getElementById('totals-section');
  if(sec){
    sec.querySelectorAll('.totals-filters input').forEach(function(inp){inp.addEventListener('change',apply);});
    sec.querySelectorAll('.totals-filters input.filter-date').forEach(function(inp){inp.addEventListener('input',apply);inp.addEventListener('change',apply);});
    sec.querySelectorAll('.totals-filters .filter-dropdown-trigger').forEach(function(tr){
      tr.addEventListener('click',function(e){e.stopPropagation();var dd=tr.closest('.filter-dropdown');if(dd)dd.classList.toggle('open');tr.setAttribute('aria-expanded',dd&&dd.classList.contains('open')?'true':'false');});
    });
    document.addEventListener('click',function(){sec.querySelectorAll('.totals-filters .filter-dropdown.open').forEach(function(dd){dd.classList.remove('open');var t=dd.querySelector('.filter-dropdown-trigger');if(t)t.setAttribute('aria-expanded','false');});});
    sec.querySelectorAll('.totals-filters .filter-dropdown-panel').forEach(function(p){p.addEventListener('click',function(e){e.stopPropagation();});});
    var resetBtn=document.createElement('button');resetBtn.type='button';resetBtn.className='filter-reset-btn';resetBtn.textContent='\u21bb';resetBtn.title='Επαναφορά φίλτρων';resetBtn.setAttribute('aria-label','Επαναφορά φίλτρων');resetBtn.addEventListener('click',function(){sec.querySelectorAll('.totals-filters input[type="checkbox"]').forEach(function(cb){cb.checked=false;});var apo=document.getElementById('filter-apo');var eos=document.getElementById('filter-eos');if(apo)apo.value='';if(eos)eos.value='';sec.querySelectorAll('.totals-filters .filter-dropdown.open').forEach(function(dd){dd.classList.remove('open');});apply();});sec.querySelector('.totals-filters').appendChild(resetBtn);
  }
  apply();
  window._atlasRR=RR;window._atlasDM=DM;window._atlasPd=pd;
})();
""")


def _count_dropdown(name, options, data_attr, with_desc=False, desc_map=None):
    """Dropdown για φίλτρα καταμέτρησης (ίδια δομή με totals)."""
    if not options:
        return ""
    desc_map = desc_map or {}
    items = []
    for val in options:
        if with_desc:
            desc = (desc_map.get(val) or "").strip()
            label = f"{val} – {desc}" if desc else val
        else:
            label = val
        items.append(
            f'<label class="filter-cb"><input type="checkbox" name="cnt-{html_mod.escape(data_attr)}" '
            f'value="{html_mod.escape(str(val))}">'
            f'{html_mod.escape(label)}</label>'
        )
    items_html = "".join(items)
    return (
        f'<div class="filter-group filter-dropdown" data-filter-name="{html_mod.escape(name)}" data-filter-key="{html_mod.escape(data_attr)}">'
        f'<div class="filter-dropdown-trigger" tabindex="0">'
        f'{html_mod.escape(name)}</div>'
        f'<div class="filter-dropdown-panel">'
        f'<div class="filter-options">{items_html}</div></div>'
        f'<div class="filter-selected-label" aria-live="polite"></div></div>'
    )


def build_count_with_filters(count_display_df, print_style_rows, count_df,
                             description_map=None, disclaimer_html=None):
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

    filter_parts = [
        _count_dropdown("Ταμείο", tameio_vals, "tameio"),
        _count_dropdown("Τύπος Ασφάλισης", typos_vals, "typos"),
        _count_dropdown("Εργοδότης", employer_vals, "employer"),
        _count_dropdown("Κλάδος/Πακέτο", klados_vals, "klados", with_desc=True, desc_map=desc_map),
        _count_dropdown("Τύπος Αποδοχών", apodoxes_vals, "apodoxes"),
        '<div class="filter-group">'
        '<input type="number" id="cnt-filter-from" class="filter-date" placeholder="Από (έτος) π.χ. 1993" min="1900" max="2100" style="width:90px;">'
        '</div>'
        '<div class="filter-group">'
        '<input type="number" id="cnt-filter-to" class="filter-date" placeholder="Έως (έτος) π.χ. 2024" min="1900" max="2100" style="width:90px;">'
        '</div>'
        '<div class="filter-group count-filter-cb-stack">'
        '<label class="filter-cb">'
        '<input type="checkbox" id="cnt-totals-only"> Ετήσια σύνολα'
        '</label>'
        '<label class="filter-cb">'
        '<input type="checkbox" id="cnt-year-sparse"> Αραιή'
        '</label></div>',
    ]
    # Ένα μόνο κουμπί reset (στατικό HTML)· όχι appendChild από JS — αποφεύγει διπλό κουμπί αν τρέξει δύο φορές το script.
    _cnt_reset_btn = (
        '<button type="button" class="filter-reset-btn" id="cnt-filter-reset" '
        'title="Επαναφορά φίλτρων" aria-label="Επαναφορά φίλτρων">&#x21bb;</button>'
    )
    filter_bar = (
        '<div class="count-filters" id="count-filters-bar">'
        + "".join(f for f in filter_parts if f)
        + _cnt_reset_btn
        + "</div>"
    )

    js = _build_count_filter_js()

    top_block = (
        '<div class="count-layout-top">'
        '<h2>Πίνακας Καταμέτρησης</h2>'
        '<p class="print-description">Αναλυτική καταμέτρηση ημερών ασφάλισης ανά μήνα.</p>'
        f'{filter_bar}'
        '</div>'
    )
    middle_block = (
        '<div id="count-tables-wrapper" class="count-layout-middle">'
        f'{count_table_html}'
        '</div>'
    )
    bottom_block = ''
    if disclaimer_html:
        bottom_block = f'<div class="count-layout-bottom">{disclaimer_html}</div>'

    return (
        '<section class="print-section count-layout" id="count-section">'
        f'{top_block}'
        f'{middle_block}'
        f'{bottom_block}'
        f'<script>{js}</script></section>'
    )


def _build_count_filter_js():
    """JS: φίλτρα καταμέτρησης + δυναμικά σύνολα (ορατές γραμμές ανά τμήμα πριν κάθε γραμμή συνόλου)."""
    return r"""
(function(){
  var sec=document.getElementById('count-section');
  if(!sec)return;
  var yearSections=sec.querySelectorAll('#count-tables-wrapper .year-section');
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

  function addTrToSums(tr,sums,cm,totOnly,segTameioRef){
    if(tr.getAttribute('data-is-sep')==='1')return;
    if(tr.getAttribute('data-is-total')==='1')return;
    var tds=tr.querySelectorAll('td');
    if(cm.perigrafi!==undefined&&tds[cm.perigrafi]&&(tds[cm.perigrafi].textContent||'').trim()==='Εισφορές μήνα')return;
    if(totOnly){if(tr.getAttribute('data-filter-ok')!=='1')return;}
    else if(tr.style.display==='none')return;
    var added=false;
    Object.keys(sums).forEach(function(k){
      var i=parseInt(k,10);
      if(tds[i]){var v=parseGreekNum(tds[i].textContent);if(!isNaN(v)){sums[k]=sums[k]+v;added=true;}}
    });
    if(added&&segTameioRef){
      var tm=(tr.getAttribute('data-c-tameio')||'').trim();
      if(tm&&!segTameioRef.v)segTameioRef.v=tm;
    }
  }

  function monthCapForTameio(tn){
    var u=String(tn||'').toUpperCase();
    return u.indexOf('ΙΚΑ')!==-1?31:25;
  }

  function flushTotalRow(tr,sums,cm,segTameio){
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
  }

  function rowCountsTowardSubtotal(tr,cm,totOnly){
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

  yearSections.forEach(function(ys){
    var tbl=ys.querySelector('table.print-table');
    if(!tbl)return;
    var cm=mapHeaders(tbl);
    var rows=tbl.querySelectorAll('tbody tr');
    var last={};
    rows.forEach(function(tr){
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
      if(isTotal)return;
      function gv(key){var idx=cm[key];if(idx===undefined)return '';var td=tds[idx];var v=td?td.textContent.trim():'';if(v)last[key]=v;return last[key]||'';}
      tr.setAttribute('data-c-tameio',gv('tameio'));tr.setAttribute('data-c-typos',gv('typos'));tr.setAttribute('data-c-employer',gv('employer'));tr.setAttribute('data-c-klados',gv('klados'));tr.setAttribute('data-c-apodoxes',gv('apodoxes'));
    });
  });

  yearSections.forEach(function(ys){
    var tbl=ys.querySelector('table.print-table');
    if(!tbl)return;
    var cm=mapHeaders(tbl);
    var apodoxesCol=cm.apodoxesCol;
    var eisforcesCol=cm.eisforcesCol;
    tbl.querySelectorAll('tbody tr').forEach(function(tr){
      var tds=tr.querySelectorAll('td');
      if(apodoxesCol!==undefined&&apodoxesCol>=0&&tds[apodoxesCol]){tds[apodoxesCol].classList.add('copy-target');tds[apodoxesCol].setAttribute('title','Κλικ για αντιγραφή (Αποδοχές)');}
      if(eisforcesCol!==undefined&&eisforcesCol>=0&&tds[eisforcesCol]){tds[eisforcesCol].classList.add('copy-target');tds[eisforcesCol].setAttribute('title','Κλικ για αντιγραφή (Εισφορές)');}
    });
  });

  function apply(){
    var f={tameio:[],typos:[],employer:[],klados:[],apodoxes:[]};
    ['tameio','typos','employer','klados','apodoxes'].forEach(function(attr){
      sec.querySelectorAll('input[name="cnt-'+attr+'"]:checked').forEach(function(cb){f[attr].push(cb.value);});
    });
    sec.querySelectorAll('.count-filters .filter-dropdown').forEach(function(dd){
      var key=dd.getAttribute('data-filter-key');
      if(!key)return;
      var vals=f[key];
      var label=dd.querySelector('.filter-selected-label');
      if(!label)return;
      if(vals.length===0){ label.textContent=''; return; }
      var esc=function(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;};label.innerHTML=vals.map(function(v){return '<span class="filter-selected-chip">'+esc(v)+'</span>';}).join('');
    });
    var fromY=parseInt((document.getElementById('cnt-filter-from')||{}).value,10)||0;
    var toY=parseInt((document.getElementById('cnt-filter-to')||{}).value,10)||9999;
    var totOnly=document.getElementById('cnt-totals-only')&&document.getElementById('cnt-totals-only').checked;
    var sparseGap=document.getElementById('cnt-year-sparse')&&document.getElementById('cnt-year-sparse').checked;
    sec.classList.toggle('count-year-sparse', !!sparseGap);

    yearSections.forEach(function(ys){
      var hd=ys.querySelector('.year-heading');
      var yTxt=hd?hd.textContent.trim():'';
      var yNum=parseInt(yTxt,10)||0;
      if(yNum&&(yNum<fromY||yNum>toY)){ys.style.display='none';return;}
      ys.style.display='';
      var tbl=ys.querySelector('table.print-table');
      if(!tbl)return;
      var cm=mapHeaders(tbl);
      var headers=tbl.querySelectorAll('thead th');
      var rows=tbl.querySelectorAll('tbody tr');

      rows.forEach(function(tr){
        if(tr.getAttribute('data-is-sep')==='1'){tr.style.display='';return;}
        if(tr.getAttribute('data-is-total')==='1')return;
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

      var visibleDataRows=0;
      rows.forEach(function(tr){
        if(tr.getAttribute('data-is-sep')==='1'||tr.getAttribute('data-is-total')==='1')return;
        if(totOnly){if(tr.getAttribute('data-filter-ok')==='1')visibleDataRows++;}
        else if(tr.style.display!=='none')visibleDataRows++;
      });
      if(visibleDataRows===0){ys.style.display='none';return;}

      var hasSumCols=cm.monthIdxs.length>0||cm.synoloIdx!==undefined||cm.apodoxesCol!==undefined||cm.eisforcesCol!==undefined;
      if(!hasSumCols)return;

      var segVis=0;
      for(var sj=0;sj<rows.length;sj++){
        var trS=rows[sj];
        if(trS.getAttribute('data-is-sep')==='1')continue;
        if(trS.getAttribute('data-is-total')==='1'){
          var showSub=f.klados.length>0&&segVis>0;
          trS.style.display=showSub?'':'none';
          segVis=0;
        }else if(rowCountsTowardSubtotal(trS,cm,totOnly)){
          segVis++;
        }
      }

      var sums=initSums(cm);
      var segTameioRef={v:''};
      for(var ri=0;ri<rows.length;ri++){
        var tr=rows[ri];
        if(tr.getAttribute('data-is-sep')==='1')continue;
        if(tr.getAttribute('data-is-total')==='1'){
          if(tr.style.display!=='none')
            flushTotalRow(tr,sums,cm,segTameioRef.v);
          sums=initSums(cm);
          segTameioRef.v='';
          continue;
        }
        addTrToSums(tr,sums,cm,totOnly,segTameioRef);
      }

      reflowCollapsedFundLabels(cm,rows,totOnly);
    });
  }

  ['cnt-filter-from','cnt-filter-to','cnt-totals-only','cnt-year-sparse'].forEach(function(id){var el=document.getElementById(id);if(el)el.addEventListener('input',apply);if(el)el.addEventListener('change',apply);});
  sec.querySelectorAll('.count-filters input[type="checkbox"]').forEach(function(cb){cb.addEventListener('change',apply);});
  document.addEventListener('click',function(){sec.querySelectorAll('.count-filters .filter-dropdown.open').forEach(function(o){o.classList.remove('open');});});
  sec.querySelectorAll('.count-filters .filter-dropdown-panel').forEach(function(p){p.addEventListener('click',function(e){e.stopPropagation();});});
  sec.querySelectorAll('.count-filters .filter-dropdown').forEach(function(dd){var tr=dd.querySelector('.filter-dropdown-trigger');if(tr){tr.addEventListener('click',function(e){e.stopPropagation();dd.classList.toggle('open');sec.querySelectorAll('.count-filters .filter-dropdown').forEach(function(other){if(other!==dd)other.classList.remove('open');});});}});
  var rb=document.getElementById('cnt-filter-reset');
  if(rb)rb.addEventListener('click',function(){sec.querySelectorAll('.count-filters input[type="checkbox"]').forEach(function(cb){cb.checked=false;});var fromEl=document.getElementById('cnt-filter-from');var toEl=document.getElementById('cnt-filter-to');var totOnly=document.getElementById('cnt-totals-only');var sparseEl=document.getElementById('cnt-year-sparse');if(fromEl)fromEl.value='';if(toEl)toEl.value='';if(totOnly)totOnly.checked=false;if(sparseEl)sparseEl.checked=false;sec.querySelectorAll('.count-filters .filter-dropdown.open').forEach(function(o){o.classList.remove('open');});apply();});
  apply();
})();
"""


# ---------------------------------------------------------------------------
# Report data builder
# ---------------------------------------------------------------------------

def build_report_tab_entries(df, description_map=None):
    """Δημιουργεί τα tab entries (id, label, html) για τον HTML viewer.

    Επιστρέφει (audit_df, display_summary, count_display_df, print_style_rows, tab_entries).
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
    )

    show_complex_warning = False
    try:
        n_agg, n_limits_25, n_unpaid = compute_complex_file_metrics(df)
        show_complex_warning = should_show_complex_file_warning(n_agg, n_limits_25, n_unpaid)
    except Exception:
        pass

    tab_entries = []

    # -- Detect warning types for totals --
    warning_types = []
    parallel_df = _safe_call(build_parallel_print_df, df, description_map)
    if parallel_df is not None and not parallel_df.empty:
        warning_types.append("παράλληλη ασφάλιση")
    parallel_2017_df = _safe_call(build_parallel_2017_print_df, df, description_map)
    if parallel_2017_df is not None and not parallel_2017_df.empty:
        warning_types.append("παράλληλη απασχόληση 2017+")
    multi_df = _safe_call(build_multi_employment_print_df, df, description_map)
    if multi_df is not None and not multi_df.empty:
        warning_types.append("πολλαπλή απασχόληση")

    # -- Totals --
    if not display_summary.empty:
        totals_html = build_totals_with_filters(
            display_summary, raw_df=df, desc_map=description_map,
            warning_types=warning_types,
        )
        tab_entries.append(("totals", "Σύνολα", totals_html))

    # -- Count --
    if not count_display_df.empty:
        count_html = build_count_with_filters(
            count_display_df, print_style_rows, count_df, description_map
        )
        tab_entries.append(("count", "Καταμέτρηση", count_html))

    # -- Gaps --
    try:
        gaps_df = find_gaps_in_insurance_data(df)
        zero_duration_df = find_zero_duration_intervals(df)
        gaps_parts = []
        if gaps_df is not None and not gaps_df.empty:
            gaps_parts.append(build_print_section_html(
                "Κενά Διαστήματα", gaps_df,
                description="Χρονικές περίοδοι χωρίς ασφαλιστική κάλυψη.",
                heading_tag="h2",
            ))
        if zero_duration_df is not None and not zero_duration_df.empty:
            gaps_parts.append(build_print_section_html(
                "Διαστήματα χωρίς ημέρες ασφάλισης", zero_duration_df,
                description="Εγγραφές που εμφανίζονται στον ΑΤΛΑΣ αλλά χωρίς τιμές σε Έτη/Μήνες/Ημέρες.",
                heading_tag="h2",
            ))
        if gaps_parts:
            gaps_parts.append(
                "<p class='print-description' style='margin-top:1.25em;padding:0.5em 0;"
                "border-top:1px solid #e2e8f0;font-size:0.95em;'>"
                "Τα διαστήματα χωρίς ημέρες ασφάλισης αναφέρονται αυτούσια στο αρχείο ΑΤΛΑΣ "
                "χωρίς ημέρες ασφάλισης. Ωστόσο, δεν αποτελούν εξ ορισμού κενό διάστημα "
                "καθώς μπορεί να επικαλύπτονται μερικώς από άλλες εγγραφές που να έχουν ημέρες "
                "ασφάλισης. Απαιτείται λεπτομερής έλεγχος.</p>"
            )
            tab_entries.append(("gaps", "Κενά", "".join(gaps_parts)))
    except Exception:
        pass

    # -- Parallel --
    if parallel_df is not None and not parallel_df.empty:
        par_html = build_yearly_print_html(
            parallel_df, year_column='Έτος',
            collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης'],
        )
        tab_entries.append((
            "parallel", "Παράλληλη",
            f"<section class='print-section'><h2>Παράλληλη Ασφάλιση</h2>"
            f"<p class='print-description'>ΙΚΑ & ΟΑΕΕ / ΟΑΕΕ & ΤΣΜΕΔΕ / ΟΓΑ & ΙΚΑ/ΟΑΕΕ "
            f"(έως 31/12/2016).</p>{par_html}</section>",
        ))

    # -- Parallel 2017+ --
    if parallel_2017_df is not None and not parallel_2017_df.empty:
        par2017_html = build_yearly_print_html(
            parallel_2017_df, year_column='Έτος',
            collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης'],
        )
        tab_entries.append((
            "parallel2017", "Παράλληλη 2017+",
            f"<section class='print-section'><h2>Παράλληλη Απασχόληση 2017+</h2>"
            f"<p class='print-description'>Από 01/2017 (ΙΚΑ & ΕΦΚΑ μη μισθωτή / ΕΦΚΑ μισθωτή "
            f"& ΕΦΚΑ μη μισθωτή).</p>{par2017_html}</section>",
        ))

    # -- Multi employment --
    if multi_df is not None and not multi_df.empty:
        multi_html = build_yearly_print_html(
            multi_df, year_column='Έτος',
            collapse_cols=['Ταμείο', 'Τύπος Ασφάλισης', 'Εργοδότης'],
            bold_columns=['Εργοδότης'],
            col_width_overrides={'Εργοδότης': '90px'},
        )
        tab_entries.append((
            "multi", "Πολλαπλή",
            f"<section class='print-section'><h2>Πολλαπλή Απασχόληση</h2>"
            f"<p class='print-description'>Μήνες με πολλαπλούς εργοδότες ΙΚΑ "
            f"(αποδοχές 01, 16, ή 99).</p>{multi_html}</section>",
        ))

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
        cards_html = "<div class='audit-grid'>"
        for _, row in audit_df.iterrows():
            title = str(row.get('Έλεγχος', ''))
            result = str(row.get('Εύρημα', ''))
            details = str(row.get('Λεπτομέρειες', ''))
            actions = str(row.get('Ενέργειες', ''))
            target_tab = _check_to_tab.get(title)
            is_clickable = target_tab and target_tab in available_tab_ids
            if is_clickable:
                safe_tab = html_mod.escape(target_tab)
                card_attrs = (
                    f' class="audit-card audit-card-clickable" data-tab="{safe_tab}" '
                    f"onclick=\"showTab('{safe_tab}');return false;\" "
                    f"onkeydown=\"if(event.key==='Enter'){{showTab('{safe_tab}');return false;}}\" "
                    f'role="button" tabindex="0"'
                )
            else:
                card_attrs = ' class="audit-card"'
            action_html = (
                f"<div class='audit-card-actions'>{actions}</div>"
                if actions and actions != '-' else ""
            )
            cards_html += (
                f"<div{card_attrs}>"
                f"<div class='audit-card-header'><span>{html_mod.escape(title)}</span></div>"
                f"<div class='audit-card-result'>{html_mod.escape(result)}</div>"
                f"<div class='audit-card-details'>{details}</div>"
                f"{action_html}</div>"
            )
        cards_html += "</div>"
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

    # -- Complex file warning --
    if show_complex_warning:
        tab_entries = [
            (
                tid,
                label,
                content if tid == "personal" else COMPLEX_FILE_WARNING_HTML + content,
            )
            for tid, label, content in tab_entries
        ]

    return audit_df, display_summary, count_display_df, print_style_rows, tab_entries


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
    rest = [
        (EXCLUSION_NOTE_HTML if tid == "count" else "") + content
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
):
    """Κατασκευή πλήρους interactive HTML viewer (sidebar + tabs + JS)."""
    safe_name = html_mod.escape(client_name.strip()) if client_name.strip() else ""
    name_block = f'<div class="header-name">{safe_name}</div>' if safe_name else ""
    disclaimer = get_print_disclaimer_html()

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

    tab_panes = "\n".join(
        f'<div id="pane-{tid}" class="tab-pane{" active" if tid == active_tid else ""}">'
        f'{(EXCLUSION_NOTE_HTML if (add_exclusion_note_for_count and tid == "count") else "")}{content}</div>'
        for tid, _, content in tab_entries
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

    return f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_doc_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet">
<style>{VIEWER_STYLES}</style>
</head>
<body data-atlas-save-file="{_save_suffix_attr}">
<div class="app-layout">
  <nav class="sidebar">
    <div class="sidebar-header">{_esc_title}{_sidebar_small}</div>
    <div class="sidebar-nav">{nav_items}</div>
    <div class="sidebar-footer">
      <button type="button" class="btn-action btn-save" onclick="downloadFullHtml();">Πλήρης Αποθήκευση</button>
      <button type="button" class="btn-action btn-print" onclick="openPrint();">Εκτύπωση</button>
      <div class="sidebar-footer-copyright">© Syntaksi Pro - my advisor</div>
    </div>
  </nav>
  <main class="main-content">
    <div class="main-content-scroll">
    {name_block}
    <div class="main-title-wrap"><span id="main-title-person" class="main-title-person" aria-live="polite"></span><span class="main-title">{_main_heading}</span></div>
    <div class="tab-panes-container">
    {tab_panes}
    <div class="main-footer-disclaimer">{disclaimer}</div>
    </div>
    </div>
  </main>
</div>
<div id="toast-container"></div>
<div id="apodoxes-tooltip" class="apodoxes-tooltip" aria-hidden="true"></div>
<div id="tl-paketo-tooltip" class="apodoxes-tooltip" aria-hidden="true"></div>
<script>
var _apodoxesDescriptions = {apodoxes_js};
var _printHtml = {print_js};
var _printStyles = {print_styles_js};
var _clientName = {client_name_js};
var _downloadFilename = {download_filename_js};
var _printBrandSuffix = {print_brand_suffix_js};
var _fullSaveSuffix = {full_save_suffix_js};
{VIEWER_JS}
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
                               full_save_suffix=None):
    """Παράγει (viewer_html, print_html) από ένα DataFrame."""
    description_map = build_description_map(df)
    audit_df, display_summary, _, _, tab_entries = build_report_tab_entries(
        df, description_map=description_map,
    )

    print_html = build_print_html_document(
        tab_entries, audit_df, display_summary, client_name=client_name,
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

PRINT_STYLES = """
@media print { @page { size: A4 landscape; margin: 8mm; } }
@media print { .totals-filters { display: none !important; } .count-filters { display: none !important; } .totals-info-bar { display: none !important; } .totals-exceeded-warning { display: none !important; } .section-actions { display: none !important; } .complex-file-warning { display: none !important; } .lite-exclusion-note { display: none !important; } .tl-zoom-controls { display: none !important; } #tl-zoom-inner, #tl-paketo-zoom-inner { transform: none !important; } .tl-zoom-wrapper, .tl-paketo-zoom-scroll { overflow-x: hidden !important; } }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #222; margin: 0; padding: 12px 16px; font-size: 11px; line-height: 1.4; background: #ffffff; }
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
#count-tables-wrapper table.print-table tbody td.copy-target { transition: background-color 0.18s ease, box-shadow 0.18s ease; }
#count-tables-wrapper table.print-table tbody td.copy-target:hover { background-color: rgba(99, 102, 241, 0.14) !important; box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.38); }
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
.totals-info-bar { display: none !important; } .totals-exceeded-warning { display: none !important; }
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
.audit-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.audit-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
.audit-card-header { font-size: 11px; font-weight: 700; color: #334155; margin-bottom: 6px; }
.audit-card-result { font-size: 13px; font-weight: 600; color: #111; }
.audit-card-details { font-size: 10px; color: #64748b; line-height: 1.4; }
"""

VIEWER_STYLES = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #1e293b; background: #fff; }
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
.btn-action { width: 100%; border: none; padding: 10px 0; border-radius: 6px; font-size: 14px; font-weight: 700; font-family: "Source Sans 3", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; cursor: pointer; transition: background .15s; }
.btn-save { background: #2563eb; color: white; } .btn-save:hover { background: #1d4ed8; }
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
.main-content table.print-table thead th { color: #1e293b !important; }
.main-content table.print-table tbody td { color: #1f2937 !important; }
.main-content table.print-table tbody td:first-child { color: #111827 !important; }
.main-content table.print-table tbody tr.total-row td { color: #111827 !important; }
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
.main-content .totals-summary-label { color: #334155; }
.main-content .totals-summary-value { color: #111827; }
.main-content .totals-filters .filter-label,
.main-content .count-filters .filter-label { color: #1e293b; }
.main-content .totals-filters .filter-cb,
.main-content .totals-filters .filter-dropdown-trigger,
.main-content .count-filters .filter-cb,
.main-content .count-filters .filter-dropdown-trigger { color: #1e293b; }
.main-content .filter-selected-label { color: #1e293b; }
.main-content .date-key-title { color: #111827; }
.main-content .date-key-label { color: #334155; }
.main-content .date-key-value { color: #111827; }
.main-content .date-key-desc { color: #374151 !important; }
.synopsis-modal-body { color: #334155; }
.synopsis-trunc-note { color: #374151 !important; }
.apodoxes-tooltip { color: #111827; }
.main-content-scroll { flex: 1; min-height: 0; overflow: auto; display: flex; flex-direction: column; }
.main-footer-disclaimer { flex-shrink: 0; padding-top: 16px; margin-top: 8px; border-top: 1px solid #e2e8f0; }
.header-name { font-size: 22px; font-weight: 800; color: #111827; margin-bottom: 4px; }
.main-title-wrap { display: flex; align-items: baseline; gap: 14px; margin-bottom: 20px; flex-shrink: 0; flex-wrap: wrap; }
.main-title-person { font-size: 19px; font-weight: 700; color: #1e293b; margin-right: 12px; letter-spacing: 0.02em; }
.main-title { font-size: 19px; color: #64748b; font-weight: 600; }
.tab-pane { display: none; } .tab-pane.active { display: block; position: relative; }
#pane-count.tab-pane { display: none; }
#pane-count.tab-pane.active { display: flex !important; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }
.tab-panes-container { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; -webkit-overflow-scrolling: touch; }
.main-content.count-tab-active .main-footer-disclaimer { display: none !important; }
.lite-exclusion-note { text-align: right; font-size: 11px; color: #64748b; font-style: italic; margin-bottom: 8px; }
.audit-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; margin-bottom: 24px; }
.audit-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); display: flex; flex-direction: column; }
.audit-card-clickable { cursor: pointer; transition: box-shadow 0.2s, border-color 0.2s; }
.audit-card-clickable:hover { box-shadow: 0 4px 12px rgba(99,102,241,0.2); border-color: #6366f1; }
.audit-card-clickable:focus { outline: 2px solid #6366f1; outline-offset: 2px; }
.audit-card-header { font-size: 14px; font-weight: 700; color: #334155; margin-bottom: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.audit-card-result { font-size: 16px; font-weight: 600; color: #0f172a; margin-bottom: 8px; }
.audit-card-details { font-size: 13px; color: #64748b; line-height: 1.5; flex: 1; }
.audit-card-actions { margin-top: 12px; padding-top: 8px; border-top: 1px dashed #e2e8f0; font-size: 12px; color: #ef4444; font-weight: 600; }
/* Σύνοψη: ομοιόμορφα boxes + modal λεπτομερειών (ενσωματωμένο από dev_html) */
#pane-synopsis .audit-grid { align-items: stretch; }
#pane-synopsis .audit-card {
  height: 300px;
  min-height: 300px;
  max-height: 300px;
  overflow: hidden;
  box-sizing: border-box;
}
#pane-synopsis .audit-card-details {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
  position: relative;
  font-size: 13px;
  line-height: 1.45;
}
#pane-synopsis .audit-card-details.synopsis-details-faded::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 40px;
  background: linear-gradient(to bottom, rgba(255,255,255,0), #fff 85%);
  pointer-events: none;
}
#pane-synopsis .audit-card-header {
  gap: 8px;
  flex-wrap: nowrap;
  position: relative;
  z-index: 2;
}
#pane-synopsis .audit-card-header > span:first-of-type { flex: 1; min-width: 0; }
.synopsis-expand-btn {
  flex-shrink: 0;
  position: relative;
  z-index: 6;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  color: #6366f1;
  cursor: pointer;
  pointer-events: auto;
  transition: border-color 0.2s, box-shadow 0.2s, color 0.2s, transform 0.15s;
}
.synopsis-expand-btn:hover {
  border-color: #6366f1;
  color: #4f46e5;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
  transform: translateY(-1px);
}
.synopsis-expand-btn:focus {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
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
  width: min(640px, 100%);
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
.synopsis-modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
}
.synopsis-modal-head h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.3;
}
.synopsis-modal-close {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.synopsis-modal-close:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.synopsis-modal-body {
  padding: 16px 20px 20px;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.55;
  color: #475569;
  -webkit-overflow-scrolling: touch;
}
.synopsis-trunc-note {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  font-style: italic;
}
.print-section { margin-bottom: 24px; }
.print-section h2 { font-size: 20px; font-weight: 700; color: #1e293b; margin: 0 0 6px 0; padding-bottom: 0; border-bottom: none; }
.print-description { font-size: 15px; color: #64748b; font-style: italic; margin: 0 0 12px 0; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; }
table.print-table { border-collapse: collapse; width: 100%; font-size: 13px; table-layout: auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
table.print-table thead th { background: #f8fafc; border-bottom: 2px solid #e2e8f0; padding: 10px 12px; text-align: left; font-weight: 400; color: #334155; font-size: 12px; white-space: nowrap; text-transform: uppercase; }
table.print-table tbody td { border-bottom: 1px solid #f1f5f9; padding: 8px 12px; color: #475569; }
table.print-table tbody tr:hover td { background: #f8fafc; }
table.print-table tbody td:first-child { font-weight: 700; color: #1e293b; }
table.print-table tbody tr.total-row td { background: #dbeafe !important; color: #1e293b; font-weight: 700 !important; border-top: 1px solid #93c5fd; }
table.print-table.wrap-cells thead th, table.print-table.wrap-cells tbody td { white-space: normal; word-break: break-word; }
.table-container { position: relative; } .print-section { position: relative; }
.section-actions { position: absolute; top: 6px; right: 6px; z-index: 5; display: flex; align-items: center; gap: 8px; opacity: 0.85; transition: opacity 0.2s; }
.table-container:hover .section-actions, .print-section:hover > .section-actions { opacity: 1; }
.btn-fs, .btn-print-tab { width: 40px; height: 40px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; border: 1px solid transparent; transition: opacity 0.2s, background 0.15s, transform 0.15s; font-size: 18px; line-height: 1; }
.btn-fs { background: #e0e7ff; border-color: #a5b4fc; color: #4338ca; } .btn-fs:hover { background: #6366f1; color: #fff; border-color: #4f46e5; transform: scale(1.1); }
.btn-print-tab { background: #f0fdf4; border-color: #86efac; color: #15803d; } .btn-print-tab:hover { background: #22c55e; color: #fff; border-color: #16a34a; transform: scale(1.1); }
.table-fullscreen .section-actions { display: none; }
.table-fullscreen { position: fixed; inset: 0; z-index: 10000; background: #fff; display: flex; flex-direction: column; }
.table-fullscreen .fs-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 12px 24px; border-bottom: 2px solid #e2e8f0; background: #f8fafc; flex-shrink: 0; }
.table-fullscreen .fs-title { font-size: 16px; font-weight: 700; color: #1e293b; }
.table-fullscreen .fs-toolbar-actions { display: flex; align-items: center; gap: 10px; }
.table-fullscreen .fs-print-btn { background: #dcfce7; border: 1px solid #86efac; border-radius: 8px; padding: 8px 16px; font-size: 14px; font-weight: 600; color: #15803d; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: background 0.15s, color 0.15s; }
.table-fullscreen .fs-print-btn:hover { background: #22c55e; color: #fff; border-color: #16a34a; }
.table-fullscreen .fs-close { background: #fee2e2; border: 1px solid #fca5a5; border-radius: 8px; width: 38px; height: 38px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #dc2626; transition: all 0.15s; }
.table-fullscreen .fs-close:hover { background: #dc2626; color: #fff; }
.table-fullscreen .fs-body { flex: 1; overflow: auto; padding: 16px 24px; display: flex; flex-direction: column; min-height: 0; }
.table-fullscreen .fs-body:has(#count-section) { overflow: hidden; padding: 0; }
.table-fullscreen .fs-body:has(#count-section) #count-section { flex: 1; min-height: 0; }
.count-layout .count-layout-top { flex-shrink: 0; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; background: #fff; }
.count-layout .count-layout-middle { flex: 1; min-height: 0; overflow: scroll; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
.count-layout .count-layout-bottom { display: none !important; }
.table-fullscreen .count-layout-top { display: none !important; }
.table-fullscreen .count-layout { display: flex !important; flex-direction: column !important; height: 100% !important; }
.table-fullscreen .count-layout-middle { flex: 1 !important; min-height: 0 !important; overflow: auto !important; }
.table-fullscreen #count-section { display: flex !important; flex-direction: column !important; height: 100% !important; }
#count-section h2, #count-section .print-description, #count-section .count-filters { flex-shrink: 0; }
#count-tables-wrapper .year-section { margin-bottom: 20px; }
#count-section.count-year-sparse #count-tables-wrapper .year-section { margin-bottom: 80px; }
#count-tables-wrapper .year-heading { font-size: 15px; font-weight: 800; padding: 8px 0 6px 0; border-bottom: 2px solid #6366f1; margin-top: 3px; margin-bottom: 11px; }
#count-tables-wrapper table.print-table thead th { font-weight: 400 !important; }
#count-tables-wrapper table.print-table tbody tr.total-row td,
#count-tables-wrapper table.print-table tbody tr[data-is-total="1"] td {
  background: #f5fafc !important;
  color: #000 !important;
  font-weight: 700 !important;
  border-top: 1px solid #c8dce8;
}
.table-fullscreen .fs-body table.print-table { table-layout: auto; font-size: 14px; }
.table-fullscreen .fs-body table.print-table colgroup { display: table-column-group; }
.table-fullscreen .fs-body table.print-table colgroup col { width: auto !important; }
.table-fullscreen .fs-body table.print-table thead th { padding: 12px 14px; font-size: 13px; font-weight: 400; text-transform: uppercase; position: sticky; top: 0; z-index: 2; background: #f8fafc; }
.table-fullscreen .fs-body table.print-table tbody td { padding: 10px 14px; }
.apodoxes-tooltip { position: fixed; z-index: 100000; max-width: 340px; padding: 14px 18px; font-size: 15px; line-height: 1.5; color: #1e293b; background: #fff; border-radius: 12px; box-shadow: 0 12px 48px rgba(0,0,0,0.14), 0 4px 16px rgba(99,102,241,0.08); border: 1px solid #e2e8f0; pointer-events: none; opacity: 0; visibility: hidden; transition: opacity 0.2s, visibility 0.2s, transform 0.15s; transform: translateY(4px); }
.apodoxes-tooltip.visible { opacity: 1; visibility: visible; transform: translateY(0); }
.has-apodoxes-tooltip { cursor: help; }
.cell-description { max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; }
@media print { .section-actions { display: none !important; } .btn-fs { display: none !important; } .btn-print-tab { display: none !important; } .apodoxes-tooltip { display: none !important; } #tl-paketo-tooltip { display: none !important; } .complex-file-warning { display: none !important; } .totals-info-bar { display: none !important; } .totals-exceeded-warning { display: none !important; } .lite-exclusion-note { display: none !important; } .tl-zoom-controls { display: none !important; } #tl-zoom-inner, #tl-paketo-zoom-inner { transform: none !important; } .tl-zoom-wrapper, .tl-paketo-zoom-scroll { overflow-x: hidden !important; } .personal-form { display: none !important; } .personal-notes { display: none !important; } .synopsis-modal-overlay, .synopsis-expand-btn { display: none !important; } }
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
.totals-info-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 24px; margin-bottom: 20px; padding: 16px 20px; background: rgba(219, 234, 254, 0.88); border-radius: 8px; border: none; }
.totals-info-bar-warning { background: rgba(254, 243, 199, 0.88); border: none; }
.totals-info-bar-warning .totals-info-msg { color: #b45309; }
.totals-exceeded-warning { margin-bottom: 16px; padding: 14px 18px; background: rgba(254, 243, 199, 0.88); border: none; border-radius: 8px; font-size: 14px; color: #92400e; line-height: 1.5; }
.totals-info-msg { font-size: 16px; font-weight: 600; color: #1e40af; flex: 1; min-width: 200px; }
.totals-summary { display: flex; gap: 24px; flex-wrap: wrap; }
.totals-summary-item { display: flex; flex-direction: column; gap: 4px; }
.totals-summary-label { font-size: 13px; font-weight: 600; color: #475569; }
.totals-summary-value { font-size: 22px; font-weight: 800; color: #1e293b; }
.critical-result { font-size: 1.3em; font-weight: 700; }
.totals-summary-value.critical-result { font-size: 28.6px; }
.date-key-value.critical-result { font-size: 26px; }
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
.totals-filters .filter-dropdown { position: relative; }
.totals-filters .filter-dropdown-trigger { display: inline-flex; align-items: center; min-width: 200px; padding: 10px 14px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; color: #334155; cursor: pointer; user-select: none; }
.totals-filters .filter-dropdown-trigger:hover { border-color: #6366f1; }
.totals-filters .filter-dropdown-trigger::after { content: ''; margin-left: auto; border: 6px solid transparent; border-top-color: #64748b; }
.totals-filters .filter-dropdown-panel { display: none; position: absolute; top: 100%; left: 0; margin-top: 4px; min-width: 280px; max-height: 320px; overflow-y: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.12); z-index: 100; }
.totals-filters .filter-dropdown.open .filter-dropdown-panel { display: block; }
.totals-filters .filter-dropdown.open .filter-dropdown-trigger { border-color: #6366f1; }
.totals-filters .filter-dropdown .filter-options { max-height: 280px; flex-direction: column; flex-wrap: nowrap; padding: 10px 12px; gap: 12px; }
.totals-filters .filter-dropdown .filter-cb { white-space: normal; padding: 6px 0; min-height: 2em; align-items: flex-start; }
.count-filters { display: flex; flex-wrap: wrap; gap: 20px 22px; margin-bottom: 20px; padding: 16px 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; align-items: flex-start; align-content: center; }
.count-filters .filter-group { display: flex; flex-direction: column; gap: 10px; }
.count-filters .count-filter-cb-stack { gap: 4px; flex-shrink: 0; }
.count-filters .count-filter-cb-stack .filter-cb { white-space: nowrap; line-height: 1.3; }
.count-filters .filter-label { font-size: 13px; font-weight: 400; color: #1e293b; }
.count-filters .filter-cb { display: flex; align-items: center; gap: 10px; font-size: 16px; color: #334155; cursor: pointer; white-space: nowrap; line-height: 1.4; }
.count-filters .filter-cb input[type="checkbox"] { width: 20px; height: 20px; min-width: 20px; min-height: 20px; cursor: pointer; accent-color: #6366f1; }
.count-filters .filter-date { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; }
.count-filters .filter-date:hover { border-color: #6366f1; }
.count-filters .filter-date:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.count-filters input.filter-date:hover { border-color: #6366f1 !important; }
.count-filters input.filter-date:focus { border: 1px solid #6366f1 !important; outline: none !important; box-shadow: none !important; }
.count-filters .filter-dropdown { position: relative; }
.count-filters .filter-dropdown-trigger { display: inline-flex; align-items: center; min-width: 200px; padding: 10px 14px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; color: #334155; cursor: pointer; user-select: none; }
.count-filters .filter-dropdown-trigger:hover { border-color: #6366f1; }
.count-filters .filter-dropdown-trigger::after { content: ''; margin-left: auto; border: 6px solid transparent; border-top-color: #64748b; }
.count-filters .filter-dropdown-panel { display: none; position: absolute; top: 100%; left: 0; margin-top: 4px; min-width: 280px; max-height: 320px; overflow-y: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.12); z-index: 100; }
.count-filters .filter-dropdown.open .filter-dropdown-panel { display: block; }
.count-filters .filter-dropdown.open .filter-dropdown-trigger { border-color: #6366f1; }
.count-filters .filter-dropdown .filter-options { max-height: 280px; flex-direction: column; flex-wrap: nowrap; padding: 10px 12px; gap: 12px; }
.count-filters .filter-dropdown .filter-cb { white-space: normal; padding: 6px 0; min-height: 2em; align-items: flex-start; }
.filter-selected-label { font-size: 1.3em; font-weight: 700; color: #334155; margin-top: 6px; line-height: 1.3; min-height: 1.3em; display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; overflow-x: auto; }
.filter-selected-chip { display: inline-block; padding: 4px 10px; background: #dc3545; border: none; border-radius: 5px; color: #fff; font-size: 12.6px; font-weight: 400; }
.filter-reset-btn { margin-left: auto; padding: 9px 11px; font-size: 20px; line-height: 1; border-radius: 6px; border: 1px solid #cbd5e1; background: #fff; color: #6366f1; cursor: pointer; font-family: inherit; }
.filter-reset-btn:hover { border-color: #6366f1; color: #4f46e5; background: #eef2ff; }
#count-section { display: flex; flex-direction: column; flex: 1; min-height: 0; overflow: hidden; }
#count-tables-wrapper { flex: 1; min-height: 0; overflow: auto; -webkit-overflow-scrolling: touch; background: #fff; padding: 0 2px; }
#count-tables-wrapper .year-section { margin-bottom: 20px; }
#count-tables-wrapper .year-heading { font-size: 15px; font-weight: 800; padding: 8px 0 6px 0; border-bottom: 2px solid #6366f1; margin-top: 3px; margin-bottom: 11px; }
#count-tables-wrapper table.print-table thead th { font-weight: 400 !important; }
#count-tables-wrapper table.print-table tbody tr.total-row td,
#count-tables-wrapper table.print-table tbody tr[data-is-total="1"] td {
  background: #f5fafc !important;
  color: #000 !important;
  font-weight: 700 !important;
  border-top: 1px solid #c8dce8;
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
.date-key-panel { margin-top: 24px; padding: 20px 24px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; }
.date-key-title { font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }
.date-key-desc { font-size: 12px; color: #64748b; margin-bottom: 16px; font-style: italic; }
.date-key-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; }
.date-key-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }
.date-key-num { width: 30px; height: 30px; background: #6366f1; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.date-key-label { font-size: 13px; color: #475569; line-height: 1.3; }
.date-key-value { font-size: 20px; font-weight: 800; color: #1e293b; margin-top: 2px; }
@media print { .totals-filters { display: none !important; } .count-filters { display: none !important; } .totals-info-bar { display: none !important; } .totals-exceeded-warning { display: none !important; } .complex-file-warning { display: none !important; } .lite-exclusion-note { display: none !important; font-size: 9px; margin-bottom: 4px; } .tl-zoom-controls { display: none !important; } #tl-zoom-inner, #tl-paketo-zoom-inner { transform: none !important; } .tl-zoom-wrapper, .tl-paketo-zoom-scroll { overflow-x: hidden !important; } .personal-form { display: none !important; } .personal-notes { display: none !important; } .date-key-panel { break-inside: avoid; } }
.copy-target { cursor: pointer; position: relative; transition: background-color 0.15s; }
.copy-target:hover { background-color: rgba(99,102,241,0.15) !important; }
.copy-target:active { background-color: rgba(99,102,241,0.25) !important; }
#toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; pointer-events: none; }
.toast { background: #1e293b; color: #fff; padding: 10px 16px; border-radius: 8px; margin-top: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 15px; font-weight: 600; opacity: 0; transform: translateY(10px); transition: opacity 0.3s, transform 0.3s; }
.toast.show { opacity: 1; transform: translateY(0); }
.complex-file-warning { background: rgba(254,242,242,0.88); border: none; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; color: #991b1b; font-weight: 700; font-size: 1rem; }
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
  var SVG_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>';

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
        '<span class="synopsis-trunc-note">… και ακόμα <strong>' + rest + '</strong> γραμμές — πατήστε το εικονίδιο για όλες.</span>';
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
      html: "<p>" + esc(short) + '</p><span class="synopsis-trunc-note">Πατήστε το εικονίδιο για πλήρες κείμενο με μορφοποίηση.</span>',
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

      var oldBtn = hdr.querySelector(".synopsis-expand-btn");
      if (oldBtn) oldBtn.remove();
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

      var titleSpan = hdr.querySelector("span");
      var cardTitle = titleSpan ? titleSpan.textContent.trim() : "Λεπτομέρειες";
      if (cardTitle.indexOf("Παλιός ή νέος") !== -1) return;

      det.setAttribute("data-atlas-synopsis-full", encodeURIComponent(fullHtml));
      det.innerHTML = fullHtml;

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "synopsis-expand-btn";
      btn.setAttribute("aria-label", "Προβολή όλων των ευρημάτων");
      btn.innerHTML = SVG_ICON;
      btn.addEventListener(
        "click",
        function (e) {
          e.preventDefault();
          e.stopPropagation();
          if (e.stopImmediatePropagation) e.stopImmediatePropagation();
          openSynopsisModal(cardTitle, fullHtml);
        },
        true
      );
      hdr.appendChild(btn);

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
})();
"""

VIEWER_JS = r"""
function applyApodoxesTooltips(){var pane=document.getElementById('pane-count');if(!pane)return;var tooltipEl=document.getElementById('apodoxes-tooltip');if(!tooltipEl){tooltipEl=document.createElement('div');tooltipEl.id='apodoxes-tooltip';tooltipEl.className='apodoxes-tooltip';tooltipEl.setAttribute('aria-hidden','true');document.body.appendChild(tooltipEl);}function showTip(td,text){if(!text)return;tooltipEl.textContent=text;tooltipEl.classList.add('visible');tooltipEl.setAttribute('aria-hidden','false');tooltipEl.offsetHeight;var rect=td.getBoundingClientRect();var tipRect=tooltipEl.getBoundingClientRect();var left=rect.left+(rect.width/2)-(tipRect.width/2);var top=rect.top-tipRect.height-10;if(top<8){top=rect.bottom+10;}left=Math.max(12,Math.min(left,window.innerWidth-tipRect.width-12));tooltipEl.style.left=left+'px';tooltipEl.style.top=top+'px';}function hideTip(){tooltipEl.classList.remove('visible');tooltipEl.setAttribute('aria-hidden','true');}pane.querySelectorAll('table.print-table').forEach(function(tbl){var headers=tbl.querySelectorAll('thead th');var colIndex=-1;for(var i=0;i<headers.length;i++){var t=(headers[i].textContent||'').trim();if(t.indexOf('ΑΠΟΔΟΧΩΝ')!==-1||t.indexOf('Τύπος Αποδοχών')!==-1){colIndex=i;break;}}if(colIndex<0)return;tbl.querySelectorAll('tbody tr').forEach(function(tr){var td=tr.querySelectorAll('td')[colIndex];if(td){var code=(td.textContent||'').trim();var key=code.length===1&&/^\d$/.test(code)?'0'+code:code;var desc=_apodoxesDescriptions[key]||_apodoxesDescriptions[code]||'';if(desc){td.classList.add('has-apodoxes-tooltip');td.setAttribute('data-tooltip',desc);td.removeAttribute('title');td.addEventListener('mouseenter',function(){showTip(td,desc);});td.addEventListener('mouseleave',hideTip);}}});});}
function applyDescriptionColumn(){var tooltipEl=document.getElementById('apodoxes-tooltip');if(!tooltipEl){tooltipEl=document.createElement('div');tooltipEl.id='apodoxes-tooltip';tooltipEl.className='apodoxes-tooltip';tooltipEl.setAttribute('aria-hidden','true');document.body.appendChild(tooltipEl);}function showTipDesc(td,text){if(!text)return;tooltipEl.textContent=text;tooltipEl.classList.add('visible');tooltipEl.setAttribute('aria-hidden','false');tooltipEl.offsetHeight;var rect=td.getBoundingClientRect();var tipRect=tooltipEl.getBoundingClientRect();var left=rect.left+(rect.width/2)-(tipRect.width/2);var top=rect.top-tipRect.height-10;if(top<8){top=rect.bottom+10;}left=Math.max(12,Math.min(left,window.innerWidth-tipRect.width-12));tooltipEl.style.left=left+'px';tooltipEl.style.top=top+'px';}function hideTipDesc(){tooltipEl.classList.remove('visible');tooltipEl.setAttribute('aria-hidden','true');}document.querySelectorAll('table.print-table').forEach(function(tbl){var headers=tbl.querySelectorAll('thead th');var colIndex=-1;for(var i=0;i<headers.length;i++){if((headers[i].textContent||'').trim().indexOf('ΠΕΡΙΓΡΑΦΗ')!==-1){colIndex=i;break;}}if(colIndex<0)return;tbl.querySelectorAll('tbody tr').forEach(function(tr){var td=tr.querySelectorAll('td')[colIndex];if(td){td.classList.add('cell-description');var fullText=(td.textContent||'').trim();if(fullText){td.setAttribute('data-tooltip',fullText);td.addEventListener('mouseenter',function(){showTipDesc(td,fullText);});td.addEventListener('mouseleave',hideTipDesc);}}});});}
function applyPaketoTimelineTooltips(){var wrap=document.getElementById('tl-paketo-wrap');if(!wrap)return;var tooltipEl=document.getElementById('tl-paketo-tooltip');if(!tooltipEl){tooltipEl=document.createElement('div');tooltipEl.id='tl-paketo-tooltip';tooltipEl.className='apodoxes-tooltip';tooltipEl.setAttribute('aria-hidden','true');document.body.appendChild(tooltipEl);}function showTipPaketo(el,text){if(!text)return;tooltipEl.textContent=text;tooltipEl.classList.add('visible');tooltipEl.setAttribute('aria-hidden','false');tooltipEl.offsetHeight;var rect=el.getBoundingClientRect();var tipRect=tooltipEl.getBoundingClientRect();var left=rect.left+(rect.width/2)-(tipRect.width/2);var top=rect.top-tipRect.height-10;if(top<8){top=rect.bottom+10;}left=Math.max(12,Math.min(left,window.innerWidth-tipRect.width-12));tooltipEl.style.left=left+'px';tooltipEl.style.top=top+'px';}function hideTipPaketo(){tooltipEl.classList.remove('visible');tooltipEl.setAttribute('aria-hidden','true');}wrap.querySelectorAll('.tl-bar.has-tl-paketo-tooltip').forEach(function(bar){var t=bar.getAttribute('data-tooltip');if(!t)return;bar.removeAttribute('title');bar.addEventListener('mouseenter',function(){showTipPaketo(bar,t);});bar.addEventListener('mouseleave',hideTipPaketo);});wrap.querySelectorAll('.tl-label-meta[data-tooltip]').forEach(function(el2){var t=el2.getAttribute('data-tooltip');if(!t)return;el2.addEventListener('mouseenter',function(){showTipPaketo(el2,t);});el2.addEventListener('mouseleave',hideTipPaketo);});}
function buildPaketoTimeline(){var rowsEl=document.getElementById('tl-paketo-rows');var refEl=document.querySelector('#tl-paketo-wrap .tl-paketo-ref');var axisEl=document.querySelector('#tl-paketo-wrap .tl-paketo-axis');if(!rowsEl||!refEl||!axisEl)return;var RR=window._atlasRR,DM=window._atlasDM,pd=window._atlasPd;if(typeof pd!=='function'||!Array.isArray(RR)||!RR.length){rowsEl.innerHTML='<p style=\'color:#64748b;font-size:13px;padding:8px 0\'>Δεν υπάρχουν δεδομένα για χρονολόγιο πακέτων.</p>';return;}var tlStart=null,tlEnd=null;RR.forEach(function(r){var a=pd(r.apo),e=pd(r.eos);if(a&&(!tlStart||a<tlStart))tlStart=a;if(e&&(!tlEnd||e>tlEnd))tlEnd=e;});if(!tlStart)tlStart=new Date(1993,0,1);if(!tlEnd)tlEnd=new Date();var span=tlEnd-tlStart;if(span<=0)span=1;function pct(d){return Math.max(0,Math.min(100,(d-tlStart)/span*100));}function truncLabel(s,maxLen){s=String(s||'').replace(/\s+/g,' ').trim();if(s.length<=maxLen)return s;return s.slice(0,Math.max(0,maxLen-1))+'…';}function escAttr(x){return String(x==null?'':x).replace(/&/g,'&amp;').replace(/"/g,'&quot;');}function rowKey(r){return String(r.p||'').trim()+String.fromCharCode(1)+String(r.t||'').trim()+String.fromCharCode(1)+String(r.ty||'').trim();}var groups={};RR.forEach(function(r){var p=String(r.p||'').trim();if(!p)return;var a=pd(r.apo),b=pd(r.eos);if(!a||!b)return;var k=rowKey(r);if(!groups[k])groups[k]={p:p,t:String(r.t||'').trim(),ty:String(r.ty||'').trim(),segs:[]};groups[k].segs.push([a,b]);});var PAL=['#6366f1','#0ea5e9','#14b8a6','#a855f7','#f97316','#ec4899','#84cc16','#eab308','#64748b'];var keys=Object.keys(groups).sort(function(x,y){var ax=x.split(String.fromCharCode(1)),bx=y.split(String.fromCharCode(1));for(var i=0;i<3;i++){var c=(ax[i]||'').localeCompare(bx[i]||'','el');if(c)return c;}return 0;});var refHtml='',axisHtml='';var zIn=document.getElementById('tl-zoom-inner');if(zIn){zIn.querySelectorAll('.tl-ref-lines .tl-ref-line').forEach(function(line){refHtml+=line.outerHTML;});zIn.querySelectorAll('.tl-axis .tl-tick').forEach(function(tk){axisHtml+=tk.outerHTML;});}refEl.innerHTML=refHtml||'';axisEl.innerHTML=axisHtml||'';var html='';keys.forEach(function(k,idx){var g=groups[k];var segs=(g.segs||[]).filter(function(x){return x[0]&&x[1]&&x[0]<=x[1];});segs.sort(function(a,b){return a[0]-b[0]||a[1]-b[1]||0;});var fullDesc=(DM&&DM[g.p])?String(DM[g.p]).replace(/\r?\n/g,' ').trim():'';var mainLine=g.p+(fullDesc?' – '+truncLabel(fullDesc,26):'');var metaHtml='';if(g.t||g.ty){var _ps=[];if(g.t)_ps.push(g.t);if(g.ty)_ps.push(g.ty);var _full='('+_ps.join(', ')+')';var _short=truncLabel(_full,42);metaHtml+='<div class="tl-label-meta" data-tooltip="'+escAttr(_full)+'">'+String(_short).replace(/</g,'&lt;')+'</div>';}var labelHtml='<div class="tl-label tl-label-cell"><div class="tl-label-main">'+String(mainLine).replace(/</g,'&lt;')+'</div>'+metaHtml+'</div>';var col=PAL[idx%PAL.length];var bars=segs.map(function(seg){var L=pct(seg[0]),W=Math.max(0.15,pct(seg[1])-L);var apoStr=seg[0].getDate().toString().padStart(2,'0')+'/'+(seg[0].getMonth()+1).toString().padStart(2,'0')+'/'+seg[0].getFullYear();var eosStr=seg[1].getDate().toString().padStart(2,'0')+'/'+(seg[1].getMonth()+1).toString().padStart(2,'0')+'/'+seg[1].getFullYear();var barTip=apoStr+' — '+eosStr;return '<div class="tl-bar has-tl-paketo-tooltip" style="left:'+L.toFixed(2)+'%;width:'+W.toFixed(2)+'%;background:'+col+';" data-tooltip="'+escAttr(barTip)+'"></div>';}).join('');html+='<div class="tl-row">'+labelHtml+'<div class="tl-track">'+bars+'</div></div>';});rowsEl.innerHTML=html;if(typeof applyPaketoTimelineTooltips==='function')applyPaketoTimelineTooltips();}
function updatePersonalTitle(){var parts=[];var fullnameEl=document.getElementById('personal_fullname');var amkaEl=document.getElementById('personal_amka');var daySel=document.getElementById('personal_birth_day');var monthSel=document.getElementById('personal_birth_month');var yearSel=document.getElementById('personal_birth_year');var name=(fullnameEl&&fullnameEl.value)?fullnameEl.value.trim():'';if(name)parts.push(name);var d=daySel?parseInt(daySel.value,10):0;var m=monthSel?parseInt(monthSel.value,10):0;var y=yearSel?parseInt(yearSel.value,10):0;if(d&&m&&y){var birth=new Date(y,m-1,d);var today=new Date();if(birth<=today){var age=(today-birth)/(365.25*24*60*60*1000);parts.push(age.toFixed(2).replace('.',',')+' Ετών σήμερα');}}var amka=(amkaEl&&amkaEl.value)?amkaEl.value.trim():'';if(amka)parts.push(amka);var line=parts.join('   ·   ');var titleEl=document.getElementById('main-title-person');if(titleEl)titleEl.textContent=line;if(typeof _clientName!=='undefined')_clientName=line;}
function initPersonalForm(){var i,y,o,o2;var daySel=document.getElementById('personal_birth_day');var monthSel=document.getElementById('personal_birth_month');var yearSel=document.getElementById('personal_birth_year');var cDay=document.getElementById('personal_child_birth_day');var cMonth=document.getElementById('personal_child_birth_month');var cYear=document.getElementById('personal_child_birth_year');var resSel=document.getElementById('personal_years_residence');if(!daySel)return;function gv(s){return s&&s.value!=null?String(s.value):'';}var saved={bd:gv(daySel),bm:gv(monthSel),by:gv(yearSel),cd:cDay?gv(cDay):'',cm:cMonth?gv(cMonth):'',cy:cYear?gv(cYear):'',yr:resSel&&gv(resSel)!==''?gv(resSel):'40'};function clr(s){if(s)while(s.firstChild)s.removeChild(s.firstChild);}clr(daySel);clr(monthSel);clr(yearSel);if(cDay)clr(cDay);if(cMonth)clr(cMonth);if(cYear)clr(cYear);if(resSel)clr(resSel);var o0=document.createElement('option');o0.value='';o0.textContent='ημ';daySel.appendChild(o0);var m0=document.createElement('option');m0.value='';m0.textContent='— Μήνας —';var y0=document.createElement('option');y0.value='';y0.textContent='— Έτος —';for(i=1;i<=31;i++){o=document.createElement('option');o.value=i;o.textContent=i;daySel.appendChild(o);if(cDay){o2=document.createElement('option');o2.value=i;o2.textContent=i;cDay.appendChild(o2);}}var months=[['1','Ιαν'],['2','Φεβ'],['3','Μαρ'],['4','Απρ'],['5','Μαϊ'],['6','Ιουν'],['7','Ιουλ'],['8','Αυγ'],['9','Σεπ'],['10','Οκτ'],['11','Νοε'],['12','Δεκ']];for(i=0;i<12;i++){o=document.createElement('option');o.value=months[i][0];o.textContent=months[i][1];monthSel.appendChild(o);if(cMonth){o2=document.createElement('option');o2.value=months[i][0];o2.textContent=months[i][1];cMonth.appendChild(o2);}}monthSel.insertBefore(m0,monthSel.firstChild);var thisYear=new Date().getFullYear();for(y=thisYear;y>=1900;y--){o=document.createElement('option');o.value=y;o.textContent=y;yearSel.appendChild(o);if(cYear){o2=document.createElement('option');o2.value=y;o2.textContent=y;cYear.appendChild(o2);}}yearSel.insertBefore(y0,yearSel.firstChild);if(resSel){for(i=0;i<=40;i++){o=document.createElement('option');o.value=i;o.textContent=i;resSel.appendChild(o);}resSel.value=saved.yr;}daySel.value=saved.bd;monthSel.value=saved.bm;yearSel.value=saved.by;if(cDay)cDay.value=saved.cd;if(cMonth)cMonth.value=saved.cm;if(cYear)cYear.value=saved.cy;function updateAge(){var d=parseInt(daySel.value,10);var m=parseInt(monthSel.value,10);var y2=parseInt(yearSel.value,10);var out=document.getElementById('personal_age_display');if(!out)return;if(!d||!m||!y2){out.textContent='';return;}var birth=new Date(y2,m-1,d);var today=new Date();if(birth>today){out.textContent='';return;}var age=(today-birth)/(365.25*24*60*60*1000);out.textContent=age.toFixed(2).replace('.',',')+' Ετών σήμερα';}daySel.addEventListener('change',updateAge);monthSel.addEventListener('change',updateAge);yearSel.addEventListener('change',updateAge);updateAge();updatePersonalTitle();var fullnameEl=document.getElementById('personal_fullname');var amkaEl=document.getElementById('personal_amka');if(fullnameEl)fullnameEl.addEventListener('input',updatePersonalTitle);if(amkaEl)amkaEl.addEventListener('input',updatePersonalTitle);daySel.addEventListener('change',updatePersonalTitle);monthSel.addEventListener('change',updatePersonalTitle);yearSel.addEventListener('change',updatePersonalTitle);}
function showTab(tabId){document.querySelectorAll('.tab-pane').forEach(function(p){p.classList.remove('active');});document.querySelectorAll('.nav-item').forEach(function(a){a.classList.remove('active');});var pane=document.getElementById('pane-'+tabId);var link=document.querySelector('.nav-item[data-tab="'+tabId+'"]');if(pane)pane.classList.add('active');if(link)link.classList.add('active');var main=document.querySelector('.main-content');if(main){if(tabId==='count')main.classList.add('count-tab-active');else main.classList.remove('count-tab-active');}var tip=document.getElementById('apodoxes-tooltip');if(tip){tip.classList.remove('visible');tip.setAttribute('aria-hidden','true');}var tipP=document.getElementById('tl-paketo-tooltip');if(tipP){tipP.classList.remove('visible');tipP.setAttribute('aria-hidden','true');}if(tabId==='count')applyApodoxesTooltips();if(tabId==='timeline'){buildPaketoTimeline();}}
document.addEventListener('DOMContentLoaded',function(){applyApodoxesTooltips();applyDescriptionColumn();initPersonalForm();buildPaketoTimeline();});
function buildSinglePrintDoc(title,bodyContent){var styles=typeof _printStyles==='string'?_printStyles:'';var name=(typeof _clientName==='string'?_clientName:'').trim();var fullTitle=(name?name+' - '+(title||'')+' - ':(title||'ATLAS')+' - ')+(typeof _printBrandSuffix==='string'?_printBrandSuffix:'Atlas');var safeTitle=fullTitle.replace(/</g,'&lt;').replace(/"/g,'&quot;');var safeName=name.replace(/</g,'&lt;').replace(/&/g,'&amp;');var nameBlock=name?'<div class="prt-name">'+safeName+'</div>':'';return'<!DOCTYPE html><html lang="el"><head><meta charset="utf-8"><title>'+safeTitle+'</title><link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap" rel="stylesheet"><style>'+styles+'</style></head><body>'+nameBlock+'<div class="prt-title">Ασφαλιστικό Βιογραφικό '+(typeof _printBrandSuffix==='string'?_printBrandSuffix:'Atlas')+'</div>'+bodyContent+'<div style="margin-top:12px;font-size:9px;color:#888;text-align:left;">© Syntaksi Pro - my advisor</div></body></html>';}
function _stripHiddenCountForPrint(root){if(!root||!root.querySelectorAll)return;var sec=root.id==='count-section'?root:root.querySelector('#count-section');if(!sec||!sec.querySelector('#count-tables-wrapper'))return;sec.querySelectorAll('script').forEach(function(s){s.remove();});sec.querySelectorAll('#count-tables-wrapper .year-section').forEach(function(ys){if(ys.style.display==='none')ys.remove();});sec.querySelectorAll('#count-tables-wrapper tbody tr').forEach(function(tr){if(tr.style.display==='none')tr.remove();});}
function printSection(el){if(typeof updatePersonalTitle==='function')updatePersonalTitle();var source=el.classList&&el.classList.contains('print-section')?el:(el.closest&&el.closest('.print-section')||el);var clone=source.cloneNode(true);clone.querySelectorAll('.section-actions,.btn-fs,.btn-print-tab').forEach(function(n){n.remove();});_stripHiddenCountForPrint(clone);var title=(clone.querySelector('h2')&&clone.querySelector('h2').textContent)||'ATLAS';var bodyContent;var totalsTable=clone.querySelector('#totals-filter-table');if(totalsTable){var h2Text=(clone.querySelector('h2')&&clone.querySelector('h2').textContent)||'Σύνολα';bodyContent='<div class="print-section"><h2>'+h2Text.replace(/</g,'&lt;')+'</h2>'+totalsTable.outerHTML+'</div>';}else{bodyContent=clone.outerHTML;}var printDoc=buildSinglePrintDoc(title,bodyContent);var w=window.open('','_blank');w.document.write(printDoc);w.document.close();w.focus();setTimeout(function(){w.print();w.close();},400);}
function openTableFs(el){var overlay=document.createElement('div');overlay.className='table-fullscreen';overlay.id='fs-overlay';var section=el.classList.contains('print-section')?el:el.closest('.print-section');var source=section||el;var heading=source.querySelector?source.querySelector('h2'):null;var titleText=heading?heading.textContent:'Πίνακας';var hasInteractive=source.querySelector&&source.querySelector('script');var toolbar=document.createElement('div');toolbar.className='fs-toolbar';toolbar.innerHTML='<span class="fs-title">'+titleText+'</span>';var actions=document.createElement('div');actions.className='fs-toolbar-actions';var printBtn=document.createElement('button');printBtn.className='fs-print-btn';printBtn.innerHTML='🖨 Εκτύπωση';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(){var bodyEl=overlay.querySelector('.fs-body');if(bodyEl){var clone=bodyEl.cloneNode(true);clone.querySelectorAll('.section-actions,.btn-fs,.btn-print-tab').forEach(function(n){n.remove();});_stripHiddenCountForPrint(clone);var totalsTable=clone.querySelector('#totals-filter-table');var bodyContent=totalsTable?'<div class="print-section"><h2>'+(titleText.replace(/</g,'&lt;')||'Σύνολα')+'</h2>'+totalsTable.outerHTML+'</div>':clone.innerHTML;var printDoc=buildSinglePrintDoc(titleText,bodyContent);var w=window.open('','_blank');w.document.write(printDoc);w.document.close();w.focus();setTimeout(function(){w.print();w.close();},400);}};actions.appendChild(printBtn);var closeBtn=document.createElement('button');closeBtn.className='fs-close';closeBtn.innerHTML='✕';closeBtn.title='Κλείσιμο (Esc)';closeBtn.onclick=closeTableFs;actions.appendChild(closeBtn);toolbar.appendChild(actions);var body=document.createElement('div');body.className='fs-body';if(hasInteractive){var placeholder=document.createElement('div');placeholder.id='fs-placeholder';placeholder.style.display='none';source.parentNode.insertBefore(placeholder,source);body.appendChild(source);overlay._fsSource=source;overlay._fsPlaceholder=placeholder;}else{body.appendChild(source.cloneNode(true));}overlay.appendChild(toolbar);overlay.appendChild(body);document.body.appendChild(overlay);document.body.style.overflow='hidden';}
function closeTableFs(){var overlay=document.getElementById('fs-overlay');if(overlay){if(overlay._fsSource&&overlay._fsPlaceholder){overlay._fsPlaceholder.parentNode.insertBefore(overlay._fsSource,overlay._fsPlaceholder);overlay._fsPlaceholder.remove();}overlay.remove();document.body.style.overflow='';}}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeTableFs();});
function openPrint(){if(typeof updatePersonalTitle==='function')updatePersonalTitle();var safeName=(typeof _clientName==='string'?_clientName:'').trim().replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');var html=_printHtml;if(safeName)html=_printHtml.replace(/<body>/,'<body><div class="prt-name">'+safeName+'</div>');var blob=new Blob([html],{type:'text/html;charset=utf-8'});var url=URL.createObjectURL(blob);window.open(url,'_blank');}
function getFullSaveFilename(){var n=document.getElementById('personal_fullname');var t=document.getElementById('personal_tameio');var ak=document.getElementById('personal_amka');var name=(n&&n.value)?n.value.trim():'';var tameio=(t&&t.options[t.selectedIndex])?t.options[t.selectedIndex].text.trim():'';var amka=(ak&&ak.value)?ak.value.trim():'';function sanitize(s){return (s||'').replace(/[\s\/\\:*?"<>|]+/g,' ').trim().replace(/\s+/g,'_')||'';}var a=sanitize(name),b=sanitize(tameio),c=sanitize(amka);var parts=[a,b,c].filter(Boolean);var ds=document.body&&document.body.getAttribute('data-atlas-save-file');var suf=(ds&&String(ds).trim())?String(ds).trim():((typeof _fullSaveSuffix==='string'&&_fullSaveSuffix)?_fullSaveSuffix:'ATLAS Pro.html');return (parts.length?parts.join('_')+'_':'')+suf;}
function persistInteractiveValues(root){var r=root||document.body;if(!r||!r.querySelectorAll)return;r.querySelectorAll('input').forEach(function(inp){var t=(inp.type||'').toLowerCase();if(t==='checkbox'||t==='radio'){if(inp.checked)inp.setAttribute('checked','checked');else inp.removeAttribute('checked');}else if(t!=='file'&&t!=='button'&&t!=='submit'&&t!=='image'){inp.setAttribute('value',inp.value);}});r.querySelectorAll('textarea').forEach(function(ta){ta.textContent=ta.value;});r.querySelectorAll('select').forEach(function(sel){Array.from(sel.options).forEach(function(opt){if(opt.selected)opt.setAttribute('selected','selected');else opt.removeAttribute('selected');});});}
function downloadFullHtml(){persistInteractiveValues(document.body);var html='<!DOCTYPE html>\n'+document.documentElement.outerHTML;var blob=new Blob([html],{type:'text/html;charset=utf-8'});var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=(typeof getFullSaveFilename==='function'?getFullSaveFilename():_downloadFilename);a.click();URL.revokeObjectURL(a.href);}
function showToast(message){var container=document.getElementById('toast-container');var toast=document.createElement('div');toast.className='toast';toast.textContent=message;container.appendChild(toast);void toast.offsetWidth;toast.classList.add('show');setTimeout(function(){toast.classList.remove('show');setTimeout(function(){if(container.contains(toast))container.removeChild(toast);},300);},2000);}
document.addEventListener('click',function(e){var target=e.target.closest('.copy-target');if(target){var text=target.innerText.trim();if(text&&text!=='-'&&text!==''){navigator.clipboard.writeText(text).then(function(){showToast('Αντιγράφηκε: '+text);}).catch(function(err){console.error('Copy failed:',err);});}}});
document.addEventListener('DOMContentLoaded',function(){document.querySelectorAll('.print-section').forEach(function(sec){if(sec.closest('#pane-personal'))return;var actions=document.createElement('div');actions.className='section-actions';var printBtn=document.createElement('button');printBtn.className='btn-print-tab';printBtn.innerHTML='🖨';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(e){e.stopPropagation();printSection(sec);};var fsBtn=document.createElement('button');fsBtn.className='btn-fs';fsBtn.innerHTML='⛶';fsBtn.title='Πλήρης οθόνη';fsBtn.onclick=function(e){e.stopPropagation();openTableFs(sec);};actions.appendChild(printBtn);actions.appendChild(fsBtn);sec.appendChild(actions);});
document.querySelectorAll('table.print-table').forEach(function(tbl){if(tbl.closest('.print-section'))return;var wrapper=document.createElement('div');wrapper.className='table-container';tbl.parentNode.insertBefore(wrapper,tbl);wrapper.appendChild(tbl);var actions=document.createElement('div');actions.className='section-actions';var printBtn=document.createElement('button');printBtn.className='btn-print-tab';printBtn.innerHTML='🖨';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(e){e.stopPropagation();printSection(tbl);};var fsBtn=document.createElement('button');fsBtn.className='btn-fs';fsBtn.innerHTML='⛶';fsBtn.title='Πλήρης οθόνη';fsBtn.onclick=function(e){e.stopPropagation();openTableFs(tbl);};actions.appendChild(printBtn);actions.appendChild(fsBtn);wrapper.appendChild(actions);});
var targetColumns=['Συνολικές ημέρες','Μικτές αποδοχές','Συνολικές εισφορές','ΣΥΝΟΛΟ','ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ','ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ','ΑΠΟΔΟΧΕΣ','ΕΙΣΦΟΡΕΣ','Ημέρες Ασφ.','Σύνολο','Μικτές Αποδοχές','Συνολικές Εισφορές'];
var tables=document.querySelectorAll('table.print-table');tables.forEach(function(table){var headers=table.querySelectorAll('thead th');var targetIndices=[];headers.forEach(function(th,index){var headerText=th.textContent.trim();if(targetColumns.some(function(col){return headerText.indexOf(col)!==-1;})){targetIndices.push(index);}});if(targetIndices.length>0){var rows=table.querySelectorAll('tbody tr');rows.forEach(function(row){var cells=row.querySelectorAll('td');targetIndices.forEach(function(index){if(cells[index]){cells[index].classList.add('copy-target');cells[index].title='Κλικ για αντιγραφή';}});});}});
var cardElements=document.querySelectorAll('.audit-card-result');cardElements.forEach(function(el){el.classList.add('copy-target');el.title='Κλικ για αντιγραφή';});});
"""

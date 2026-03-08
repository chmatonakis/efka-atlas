"""
html_viewer_builder.py
~~~~~~~~~~~~~~~~~~~~~~
Κοινό module για κατασκευή standalone HTML viewer & print report.
Χρησιμοποιείται από app_lite.py και app_final.py.
"""

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
    'background:#fef2f2;border:2px solid #dc2626;border-radius:8px;'
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
    """Χρονοδιάγραμμα ασφάλισης ανά Ταμείο – Τύπο Ασφάλισης (οπτικές μπάρες)."""
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

    return f"""
    <section class="print-section">
      <h2>Χρονοδιάγραμμα Ασφάλισης</h2>
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
      <script>
      (function() {{
        var inner = document.getElementById('tl-zoom-inner');
        var btns = inner && inner.closest('.tl-zoom-wrapper').querySelectorAll('.tl-zoom-btn');
        if (!inner || !btns.length) return;
        function setZoom(level) {{
          inner.style.transform = 'scale(' + level + ')';
          btns.forEach(function(b) {{ b.classList.toggle('active', parseFloat(b.getAttribute('data-zoom')) === level); }});
        }}
        btns.forEach(function(btn) {{
          btn.addEventListener('click', function() {{ setZoom(parseFloat(btn.getAttribute('data-zoom'))); }});
        }});
      }})();
      </script>
    </section>
    """


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
    """Λίστα ωμών εγγραφών για client-side φιλτράρισμα ημερομηνιών."""
    if raw_df is None or raw_df.empty:
        return []
    pkg_col = 'Κλάδος/Πακέτο Κάλυψης'
    tameio_col = 'Ταμείο'
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
    out = []
    for _, row in rdf.iterrows():
        apo_str = row.get('Από')
        eos_str = row.get('Έως')
        if pd.isna(apo_str) or pd.isna(eos_str):
            continue
        out.append({
            'p': str(row[pkg_col]).strip(),
            't': str(row.get(tameio_col, '')).strip() if tameio_col in rdf.columns else '',
            'apo': str(apo_str).strip(),
            'eos': str(eos_str).strip(),
            'h': int(row['_h']),
        })
    return out


def build_totals_with_filters(display_summary, raw_df=None, desc_map=None,
                               warning_types=None):
    """Ενότητα Σύνολα με JS φίλτρα (Πακέτο, Ταμείο, Από-Έως)."""
    paketo_col = "Κλάδος/Πακέτο Κάλυψης"
    tameio_col = "Ταμείο"
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

    desc_map = desc_map or {}
    paketo_options = []
    for v in paketo_vals:
        desc = (desc_map.get(v) or "").strip()
        label = f"{v} – {desc}" if desc else v
        paketo_options.append((v, label))
    tameio_options = [(v, v) for v in tameio_vals]

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
            f'<div class="filter-group filter-dropdown" data-filter-name="{html_mod.escape(name)}">'
            f'<span class="filter-label">{html_mod.escape(name)}:</span>'
            f'<div class="filter-dropdown-trigger" tabindex="0" role="button" '
            f'aria-haspopup="listbox" aria-expanded="false" '
            f'title="Επιλέξτε {html_mod.escape(name)}">'
            f'Επιλέξτε {html_mod.escape(name)}…</div>'
            f'<div class="filter-dropdown-panel" role="listbox">'
            f'<div class="filter-options">{items}</div></div></div>'
        )

    paketo_filters = _dropdown("Πακέτο", paketo_options, "paketo")
    tameio_filters = _dropdown("Ταμείο", tameio_options, "tameio")
    date_filters = (
        '<div class="filter-group">'
        '<span class="filter-label">Από (ηη/μμ/εεεε):</span>'
        '<input type="text" id="filter-apo" class="filter-date" placeholder="ηη/μμ/εεεε" maxlength="10">'
        '</div>'
        '<div class="filter-group">'
        '<span class="filter-label">Έως (ηη/μμ/εεεε):</span>'
        '<input type="text" id="filter-eos" class="filter-date" placeholder="ηη/μμ/εεεε" maxlength="10">'
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
        '<span class="totals-summary-value" id="totals-sum-hmeres">—</span></div>'
        '<div class="totals-summary-item">'
        '<span class="totals-summary-label">Συνολικά Έτη</span>'
        '<span class="totals-summary-value" id="totals-sum-eti">—</span></div>'
        '</div></div>'
    )

    filters_bar = (
        f'<div class="totals-filters">{paketo_filters}{tameio_filters}{date_filters}</div>'
    )

    group_keys = [paketo_col]
    if tameio_col in display_summary.columns:
        group_keys.append(tameio_col)
    dk_map = {}
    dk_cols = ['dk1', 'dk3', 'dk4', 'dk5', 'dk6', 'dk7a', 'dk7b', 'dk7c']
    if raw_df is not None and not raw_df.empty:
        try:
            dk_df = _precompute_date_keys(raw_df, group_keys, desc_map=desc_map)
            for _, dkrow in dk_df.iterrows():
                key = tuple(str(dkrow.get(k, '')).strip() for k in group_keys)
                dk_map[key] = {c: int(dkrow.get(c, 0)) for c in dk_cols}
        except Exception:
            pass

    headers_html = "".join(
        f"<th>{html_mod.escape(str(h))}</th>" for h in display_summary.columns
    )
    rows_parts = []
    for _, row in display_summary.iterrows():
        paketo_val = str(row.get(paketo_col, "")).strip() if paketo_col in row.index else ""
        tameio_val = str(row.get(tameio_col, "")).strip() if tameio_col in row.index else ""
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
        f"{k[0]}|{k[1] if len(k) > 1 else ''}": v
        for k, v in dk_map.items()
    }).replace("</script>", "<\\/script>")
    desc_map_js = json.dumps(desc_map or {}).replace("</script>", "<\\/script>")

    has_desc_col = perigrafi_col in display_summary.columns
    calcs_panel = _build_date_key_calcs_panel()
    js = _build_totals_filter_js(raw_records_js, dk_map_js, desc_map_js,
                                  has_desc_col=has_desc_col)

    return (
        f'<section class="print-section">'
        f'<h2>Σύνολα - Ομαδοποίηση κατά Κλάδο/Πακέτο (και Ταμείο)</h2>'
        f'<p class="print-description">Συνοπτική απεικόνιση ανά Κλάδο/Πακέτο Κάλυψης και Ταμείο.</p>'
        f'{info_banner}{filters_bar}{custom_table}{calcs_panel}'
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
        f'<div class="date-key-value" id="calc-{num}">—</div></div></div>'
        for num, label in items
    )
    return (
        '<div id="date-key-calcs" class="date-key-panel">'
        '<h3 class="date-key-title">Σημαντικά διαστήματα</h3>'
        '<p class="date-key-desc">Ενημερώνονται αυτόματα με βάση τα επιλεγμένα πακέτα κάλυψης.</p>'
        f'<div class="date-key-grid">{grid}</div></div>'
    )


def _build_totals_filter_js(raw_records_js, dk_map_js, desc_map_js,
                            has_desc_col=True):
    """Επιστρέφει το JavaScript κομμάτι για client-side filtering Σύνολα."""
    has_desc_js = "true" if has_desc_col else "false"
    return """
    (function(){
      var _totalsRawRecords = """ + raw_records_js + """;
      var _totalsDkMap = """ + dk_map_js + """;
      var _totalsDescMap = """ + desc_map_js + """;
      var _totalsHasDescCol = """ + has_desc_js + """;
      function parseDate(str){if(!str||str==='')return null;var p=str.match(/^(\\d{1,2})\\/(\\d{1,2})\\/(\\d{4})$/);if(!p)return null;return new Date(parseInt(p[3],10),parseInt(p[2],10)-1,parseInt(p[1],10));}
      function formatGreekInt(n){if(n===0)return'0';return n.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.');}
      function formatGreekDec(n){var p=n.toFixed(1).split('.');return p[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g,'.')+','+p[1];}
      function applyTotalsFilters(){
        var rows=document.querySelectorAll('#totals-filter-table tbody tr');
        var pC=[];document.querySelectorAll('.totals-filters input[name="Πακέτο"]:checked').forEach(function(cb){pC.push(cb.value);});
        var tC=[];document.querySelectorAll('.totals-filters input[name="Ταμείο"]:checked').forEach(function(cb){tC.push(cb.value);});
        var aV=document.getElementById('filter-apo')?document.getElementById('filter-apo').value.trim():'';
        var eV=document.getElementById('filter-eos')?document.getElementById('filter-eos').value.trim():'';
        var aD=aV?parseDate(aV):null,eD=eV?parseDate(eV):null;
        var hasSelection=pC.length>0,totalH=0;
        if(Array.isArray(_totalsRawRecords)&&_totalsRawRecords.length>0){
          var filtered=_totalsRawRecords.filter(function(r){var pO=pC.length===0||pC.indexOf(r.p)!==-1;var tO=tC.length===0||tC.indexOf(r.t)!==-1;if(!pO||!tO)return false;var rA=parseDate(r.apo),rE=parseDate(r.eos);if(!rA||!rE)return false;if(aD&&rE<aD)return false;if(eD&&rA>eD)return false;return true;});
          var groups={};filtered.forEach(function(r){var k=r.p+'|'+r.t;if(!groups[k])groups[k]={p:r.p,t:r.t,apo:r.apo,eos:r.eos,h:0};var g=groups[k];g.h+=r.h;if(r.apo&&(!g.apo||parseDate(r.apo)<parseDate(g.apo)))g.apo=r.apo;if(r.eos&&(!g.eos||parseDate(r.eos)>parseDate(g.eos)))g.eos=r.eos;});
          var gL=Object.keys(groups).map(function(k){return groups[k];});gL.forEach(function(g){totalH+=g.h;});
          var tbody=document.querySelector('#totals-filter-table tbody'),thead=document.querySelector('#totals-filter-table thead');
          if(tbody&&thead){var colCount=thead.querySelectorAll('th').length;var nR=[];
            gL.forEach(function(g){var y=Math.floor(g.h/300),rem=g.h%300,m=Math.floor(rem/25),d=Math.round(rem%25);
              var desc=(_totalsDescMap&&_totalsDescMap[g.p])?String(_totalsDescMap[g.p]).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'):'';
              var dk=(_totalsDkMap&&_totalsDkMap[g.p+'|'+g.t])?_totalsDkMap[g.p+'|'+g.t]:{};
              var dkA=['dk1','dk3','dk4','dk5','dk6','dk7a','dk7b','dk7c'].map(function(k){return'data-'+k+'="'+(dk[k]||0)+'"';}).join(' ');
              var cells=[g.p,g.t];if(_totalsHasDescCol)cells.push(desc);cells=cells.concat([g.apo,g.eos,formatGreekInt(g.h),formatGreekDec(y),formatGreekDec(m),formatGreekDec(d),'—','—','—']);
              nR.push('<tr data-paketo="'+(g.p||'').replace(/"/g,'&quot;')+'" data-tameio="'+(g.t||'').replace(/"/g,'&quot;')+'" data-apo="'+(g.apo||'').replace(/"/g,'&quot;')+'" data-eos="'+(g.eos||'').replace(/"/g,'&quot;')+'" data-hmeres="'+g.h+'" '+dkA+'>'+cells.slice(0,colCount).map(function(c){return'<td>'+(c||'')+'</td>';}).join('')+'</tr>');
            });tbody.innerHTML=nR.join('');rows=tbody.querySelectorAll('tr');}
        }else{
          rows.forEach(function(tr){var pk=(tr.getAttribute('data-paketo')||'').trim(),tm=(tr.getAttribute('data-tameio')||'').trim();
            var aS=(tr.getAttribute('data-apo')||'').trim(),eS=(tr.getAttribute('data-eos')||'').trim();
            var pO=pC.length===0||pC.indexOf(pk)!==-1,tO=tC.length===0||tC.indexOf(tm)!==-1;
            var aR=parseDate(aS),eR=parseDate(eS),rO=true;if(aD)rO=rO&&eR&&eR>=aD;if(eD)rO=rO&&aR&&aR<=eD;
            var vis=pO&&tO&&rO;tr.style.display=vis?'':'none';if(vis){totalH+=parseInt(tr.getAttribute('data-hmeres')||'0',10);}
          });
        }
        rows=document.querySelectorAll('#totals-filter-table tbody tr');
        var elH=document.getElementById('totals-sum-hmeres'),elE=document.getElementById('totals-sum-eti');
        if(elH&&elE){if(!hasSelection){elH.textContent='—';elE.textContent='—';}else{elH.textContent=totalH>0?formatGreekInt(totalH):'—';elE.textContent=totalH>0?formatGreekDec(totalH/300):'—';}}
        var dkKeys=['dk1','dk3','dk4','dk5','dk6','dk7a','dk7b','dk7c'],dkS={};dkKeys.forEach(function(k){dkS[k]=0;});
        rows.forEach(function(tr){if(tr.classList.contains('total-row')||tr.style.display==='none')return;dkKeys.forEach(function(k){dkS[k]+=parseInt(tr.getAttribute('data-'+k)||'0',10);});});
        function setDkc(id,val){var el=document.getElementById(id);if(el)el.textContent=hasSelection&&val>0?formatGreekInt(val):'—';}
        setDkc('calc-1',dkS.dk1);var el2=document.getElementById('calc-2');if(el2)el2.textContent=hasSelection&&dkS.dk1>0?formatGreekDec(dkS.dk1/25):'—';
        setDkc('calc-3',dkS.dk3);setDkc('calc-4',dkS.dk4);setDkc('calc-5',dkS.dk5);setDkc('calc-6',dkS.dk6);setDkc('calc-7a',dkS.dk7a);setDkc('calc-7b',dkS.dk7b);setDkc('calc-7c',dkS.dk7c);
      }
      if(typeof updateFilterDropdownLabels==='function')updateFilterDropdownLabels();
      document.querySelectorAll('.totals-filters input').forEach(function(inp){inp.addEventListener('change',applyTotalsFilters);});
      document.querySelectorAll('.totals-filters input.filter-date').forEach(function(inp){inp.addEventListener('input',applyTotalsFilters);inp.addEventListener('change',applyTotalsFilters);});
      function updateFilterDropdownLabels(){document.querySelectorAll('.totals-filters .filter-dropdown').forEach(function(dd){var name=dd.getAttribute('data-filter-name')||'';var trigger=dd.querySelector('.filter-dropdown-trigger');if(!trigger)return;var count=dd.querySelectorAll('input[type="checkbox"]:checked').length;if(count===0)trigger.textContent='Επιλέξτε '+name+'…';else if(count===1)trigger.textContent='1 επιλεγμένο';else trigger.textContent=count+' επιλεγμένα';});}
      document.querySelectorAll('.totals-filters .filter-dropdown-trigger').forEach(function(tr){tr.addEventListener('click',function(e){e.stopPropagation();var dd=tr.closest('.filter-dropdown');if(dd)dd.classList.toggle('open');tr.setAttribute('aria-expanded',dd&&dd.classList.contains('open')?'true':'false');});});
      document.addEventListener('click',function(){document.querySelectorAll('.totals-filters .filter-dropdown.open').forEach(function(dd){dd.classList.remove('open');dd.querySelector('.filter-dropdown-trigger').setAttribute('aria-expanded','false');});});
      document.querySelectorAll('.totals-filters .filter-dropdown-panel').forEach(function(panel){panel.addEventListener('click',function(e){e.stopPropagation();});});
      applyTotalsFilters();updateFilterDropdownLabels();
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
        count_table_html = build_yearly_print_html(
            count_display_df, year_column='ΕΤΟΣ', style_rows=print_style_rows,
        )
        tab_entries.append((
            "count", "Καταμέτρηση",
            f"<section class='print-section'><h2>Πίνακας Καταμέτρησης</h2>"
            f"<p class='print-description'>Αναλυτική καταμέτρηση ημερών ασφάλισης ανά μήνα.</p>"
            f"{count_table_html}</section>",
        ))

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

    tab_entries.insert(0, ("synopsis", "Σύνοψη", synopsis_html))

    # -- Timeline --
    try:
        timeline_html = build_timeline_html(df)
        if timeline_html:
            tab_entries.insert(1, ("timeline", "Χρονοδιάγραμμα", timeline_html))
    except Exception:
        pass

    # -- Extra tabs (ΑΠΔ, Κύρια Δεδομένα, Αποζημίωση, Παράρτημα) --
    try:
        from html_extra_tabs import build_apd_tab, build_main_data_tab, build_apozimiosi_tab, build_annex_tab

        apd_html = _safe_call(build_apd_tab, df, description_map)
        if apd_html:
            tab_entries.append(("apd", "Ανάλυση ΑΠΔ", apd_html))

        main_data_html = _safe_call(build_main_data_tab, df, description_map)
        if main_data_html:
            tab_entries.append(("main_data", "Κύρια Δεδομένα", main_data_html))

        apoz_html = _safe_call(build_apozimiosi_tab, df, description_map)
        if apoz_html:
            tab_entries.append(("apozimiosi", "Αποζημίωση", apoz_html))

        annex_html = _safe_call(build_annex_tab, df)
        if annex_html:
            tab_entries.append(("annex", "Παράρτημα", annex_html))
    except Exception:
        pass

    # -- Complex file warning --
    if show_complex_warning:
        tab_entries = [
            (tid, label, COMPLEX_FILE_WARNING_HTML + content)
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

    rest = [
        (EXCLUSION_NOTE_HTML if tid == "count" else "") + content
        for tid, _, content in tab_entries[1:]
        if tid != "totals"
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
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700&display=swap" rel="stylesheet">
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
    app_subtitle="Προεργασία φακέλου",
):
    """Κατασκευή πλήρους interactive HTML viewer (sidebar + tabs + JS)."""
    safe_name = html_mod.escape(client_name.strip()) if client_name.strip() else ""
    name_block = f'<div class="header-name">{safe_name}</div>' if safe_name else ""
    disclaimer = get_print_disclaimer_html()

    nav_items = "\n".join(
        f'<a href="#" class="nav-item{" active" if i == 0 else ""}" '
        f'data-tab="{tid}" onclick="showTab(\'{tid}\');return false;">'
        f'{html_mod.escape(label)}</a>'
        for i, (tid, label, _) in enumerate(tab_entries)
    )

    tab_panes = "\n".join(
        f'<div id="pane-{tid}" class="tab-pane{" active" if i == 0 else ""}">'
        f'{(EXCLUSION_NOTE_HTML if tid == "count" else "")}{content}</div>'
        for i, (tid, _, content) in enumerate(tab_entries)
    )

    print_js = json.dumps(print_html).replace("</script>", "<\\/script>")
    print_styles_js = json.dumps(PRINT_STYLES).replace("</script>", "<\\/script>")
    client_name_js = json.dumps(safe_name).replace("</script>", "<\\/script>")
    download_filename_js = json.dumps(download_filename)
    apodoxes_js = json.dumps(APODOXES_DESCRIPTIONS).replace("</script>", "<\\/script>")

    return f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_mod.escape(app_title)} - {html_mod.escape(app_subtitle)}</title>
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{VIEWER_STYLES}</style>
</head>
<body>
<div class="app-layout">
  <nav class="sidebar">
    <div class="sidebar-header">{html_mod.escape(app_title)}<small>{html_mod.escape(app_subtitle)}</small></div>
    <div class="sidebar-nav">{nav_items}</div>
    <div class="sidebar-footer">
      <button type="button" class="btn-action btn-save" onclick="downloadFullHtml();">Πλήρης Αποθήκευση</button>
      <button type="button" class="btn-action btn-print" onclick="openPrint();">Εκτύπωση</button>
      <div class="sidebar-footer-copyright">© Syntaksi Pro - my advisor</div>
    </div>
  </nav>
  <main class="main-content">
    {name_block}
    <div class="main-title">Ασφαλιστικό Βιογραφικό</div>
    {tab_panes}
    {disclaimer}
  </main>
</div>
<div id="toast-container"></div>
<div id="apodoxes-tooltip" class="apodoxes-tooltip" aria-hidden="true"></div>
<script>
var _apodoxesDescriptions = {apodoxes_js};
var _printHtml = {print_js};
var _printStyles = {print_styles_js};
var _clientName = {client_name_js};
var _downloadFilename = {download_filename_js};
{VIEWER_JS}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Top-level convenience
# ---------------------------------------------------------------------------

def generate_full_html_report(df, client_name="", app_title="ATLAS",
                               app_subtitle="Προεργασία φακέλου"):
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

    viewer_html = build_viewer_html_document(
        tab_entries,
        client_name=client_name,
        print_html=print_html,
        download_filename=download_filename,
        app_title=app_title,
        app_subtitle=app_subtitle,
    )
    return viewer_html, print_html


# ---------------------------------------------------------------------------
# CSS & JS constants (at the end to keep the module readable)
# ---------------------------------------------------------------------------

PRINT_STYLES = """
@media print { @page { size: A4 landscape; margin: 8mm; } }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Fira Sans", sans-serif; color: #222; margin: 0; padding: 12px 16px; font-size: 11px; line-height: 1.4; background: #fff; }
.prt-name { text-align: center; font-size: 18px; font-weight: 800; margin-bottom: 2px; }
.prt-title { text-align: center; font-size: 14px; font-weight: 600; color: #555; margin-bottom: 14px; }
.page-break { page-break-after: always; }
.print-section { margin-bottom: 16px; }
.print-section h2 { font-size: 13px; font-weight: 700; color: #111; margin: 0 0 4px 0; padding-bottom: 3px; border-bottom: 1.5px solid #333; }
.print-description { font-size: 10px; color: #666; font-style: italic; margin: 0 0 6px 0; }
table.print-table { border-collapse: collapse; width: 100%; font-size: 10px; table-layout: fixed; }
table.print-table thead th { background: #f3f4f6; border-bottom: 1px solid #bbb; padding: 3px; text-align: left; font-weight: 700; font-size: 9px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
table.print-table tbody td { border-bottom: 0.5px solid #ddd; padding: 2px 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
table.print-table tbody tr:nth-child(even) td { background: #fafafa; }
table.print-table tbody td:first-child { font-weight: 700; }
table.print-table tbody tr.total-row td { background: #dbeafe !important; font-weight: 700 !important; border-top: 1px solid #93c5fd; }
table.print-table.wrap-cells thead th, table.print-table.wrap-cells tbody td { white-space: normal; word-break: break-word; }
.year-section { margin-bottom: 10px; }
.year-heading { font-size: 12px; font-weight: 800; padding: 4px 0 2px 0; border-bottom: 1.5px solid #6f42c1; margin-bottom: 3px; }
.print-disclaimer { font-size: 9px; color: #888; margin-top: 16px; padding-top: 8px; border-top: 1px solid #ddd; line-height: 1.4; }
.print-disclaimer strong { color: #444; }
.lite-exclusion-note { text-align: right; font-size: 9px; color: #64748b; font-style: italic; margin-bottom: 4px; }
.tl-container { position: relative; padding-bottom: 28px; padding-top: 20px; }
.tl-row { display: flex; align-items: center; margin-bottom: 4px; min-height: 16px; }
.tl-label { width: 140px; min-width: 140px; font-size: 8px; font-weight: 600; color: #334155; text-align: right; padding-right: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tl-label-gap { color: #dc2626; } .tl-label-zero { color: #78716c; }
.tl-track { position: relative; flex: 1; height: 14px; background: #f1f5f9; border-radius: 3px; }
.tl-bar { position: absolute; top: 1px; height: 12px; border-radius: 2px; opacity: 0.85; }
.tl-bar:hover { opacity: 1; box-shadow: 0 0 4px rgba(0,0,0,0.3); z-index: 2; }
.tl-gap { background: repeating-linear-gradient(45deg,#fca5a5,#fca5a5 2px,#fecaca 2px,#fecaca 4px) !important; border: 1px solid #ef4444; opacity: 0.7; }
.tl-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 2px,#d6d3d1 2px,#d6d3d1 4px) !important; border: 1px solid #78716c; opacity: 0.85; }
.tl-legend-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 2px,#d6d3d1 2px,#d6d3d1 4px) !important; border: 1px solid #78716c; }
.tl-axis { position: relative; height: 20px; margin-left: 148px; margin-top: 2px; border-top: 1px solid #cbd5e1; }
.tl-tick { position: absolute; top: 2px; font-size: 7px; color: #64748b; transform: translateX(-50%); }
.tl-tick::before { content: ''; position: absolute; top: -4px; left: 50%; width: 1px; height: 4px; background: #cbd5e1; }
.tl-ref-lines { position: absolute; left: 140px; right: 0; top: 0; bottom: 0; pointer-events: none; z-index: 0; }
.tl-ref-line { position: absolute; top: 0; bottom: 0; left: 0; display: flex; flex-direction: column; align-items: center; transform: translateX(-50%); }
.tl-ref-label { font-size: 8px; color: #64748b; white-space: nowrap; margin-bottom: 2px; font-weight: 600; }
.tl-ref-vline { flex: 1; width: 1px; min-height: 0; background: #64748b; opacity: 0.6; }
.tl-zoom-wrapper { margin-top: 8px; overflow: visible; max-height: none; border: none; background: transparent; }
.tl-zoom-controls { display: none; } .tl-zoom-inner { transform: none !important; padding: 0; }
.tl-legend { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; font-size: 8px; }
.tl-legend-item { display: inline-flex; align-items: center; gap: 3px; color: #334155; }
.tl-legend-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.audit-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.audit-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
.audit-card-header { font-size: 11px; font-weight: 700; color: #334155; margin-bottom: 6px; }
.audit-card-result { font-size: 13px; font-weight: 600; color: #111; }
.audit-card-details { font-size: 10px; color: #64748b; line-height: 1.4; }
"""

VIEWER_STYLES = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Fira Sans", -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #1e293b; background: #fff; }
.app-layout { display: flex; min-height: 100vh; }
.sidebar { width: 220px; min-width: 220px; background: #1e293b; color: #e2e8f0; display: flex; flex-direction: column; position: fixed; top: 0; left: 0; bottom: 0; z-index: 10; }
.sidebar-header { padding: 20px 16px 12px; border-bottom: 1px solid #334155; font-size: 18px; font-weight: 800; color: #fff; text-align: center; }
.sidebar-header small { display: block; font-size: 11px; font-weight: 400; color: #94a3b8; margin-top: 2px; }
.sidebar-nav { flex: 1; padding: 8px 0; overflow-y: auto; }
.nav-item { display: block; padding: 10px 20px; color: #cbd5e1; text-decoration: none; font-size: 14px; font-weight: 600; border-left: 3px solid transparent; transition: all .15s; }
.nav-item:hover { background: #334155; color: #fff; }
.nav-item.active { background: #334155; color: #fff; border-left-color: #6366f1; }
.sidebar-footer { padding: 12px 16px; border-top: 1px solid #334155; display: flex; flex-direction: column; gap: 8px; }
.sidebar-footer-copyright { margin-top: auto; padding-top: 12px; font-size: 11px; color: #94a3b8; text-align: left; }
.btn-action { width: 100%; border: none; padding: 10px 0; border-radius: 6px; font-size: 14px; font-weight: 700; cursor: pointer; transition: background .15s; }
.btn-save { background: #2563eb; color: white; } .btn-save:hover { background: #1d4ed8; }
.btn-print { background: #dc3545; color: white; } .btn-print:hover { background: #b91c1c; }
.main-content { margin-left: 220px; flex: 1; padding: 24px 32px; min-width: 0; }
.header-name { font-size: 22px; font-weight: 800; color: #111827; margin-bottom: 4px; }
.main-title { font-size: 15px; color: #64748b; font-weight: 600; margin-bottom: 20px; }
.tab-pane { display: none; } .tab-pane.active { display: block; position: relative; }
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
.print-section { margin-bottom: 24px; }
.print-section h2 { font-size: 18px; font-weight: 700; color: #1e293b; margin: 0 0 8px 0; padding-bottom: 6px; border-bottom: 2px solid #6366f1; }
.print-description { font-size: 13px; color: #64748b; font-style: italic; margin: 0 0 12px 0; }
table.print-table { border-collapse: collapse; width: 100%; font-size: 13px; table-layout: auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
table.print-table thead th { background: #f8fafc; border-bottom: 2px solid #e2e8f0; padding: 10px 12px; text-align: left; font-weight: 700; color: #334155; font-size: 12px; white-space: nowrap; }
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
.table-fullscreen .fs-body { flex: 1; overflow: auto; padding: 16px 24px; }
.table-fullscreen .fs-body table.print-table { table-layout: auto; font-size: 14px; }
.table-fullscreen .fs-body table.print-table colgroup { display: table-column-group; }
.table-fullscreen .fs-body table.print-table colgroup col { width: auto !important; }
.table-fullscreen .fs-body table.print-table thead th { padding: 12px 14px; font-size: 13px; position: sticky; top: 0; z-index: 2; background: #f8fafc; }
.table-fullscreen .fs-body table.print-table tbody td { padding: 10px 14px; }
.apodoxes-tooltip { position: fixed; z-index: 100000; max-width: 340px; padding: 14px 18px; font-size: 15px; line-height: 1.5; color: #1e293b; background: #fff; border-radius: 12px; box-shadow: 0 12px 48px rgba(0,0,0,0.14), 0 4px 16px rgba(99,102,241,0.08); border: 1px solid #e2e8f0; pointer-events: none; opacity: 0; visibility: hidden; transition: opacity 0.2s, visibility 0.2s, transform 0.15s; transform: translateY(4px); }
.apodoxes-tooltip.visible { opacity: 1; visibility: visible; transform: translateY(0); }
.has-apodoxes-tooltip { cursor: help; }
@media print { .section-actions { display: none !important; } .btn-fs { display: none !important; } .btn-print-tab { display: none !important; } .apodoxes-tooltip { display: none !important; } }
.year-section { margin-bottom: 20px; }
.year-heading { font-size: 15px; font-weight: 800; color: #1e293b; padding: 8px 0 4px 0; border-bottom: 2px solid #6366f1; margin-bottom: 6px; }
.print-disclaimer { font-size: 12px; color: #64748b; margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; line-height: 1.6; }
.print-disclaimer strong { color: #374151; }
.tl-container { position: relative; padding-bottom: 36px; padding-top: 26px; }
.tl-row { display: flex; align-items: center; margin-bottom: 8px; min-height: 28px; }
.tl-label { width: 200px; min-width: 200px; font-size: 13px; font-weight: 600; color: #334155; text-align: right; padding-right: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tl-label-gap { color: #dc2626; } .tl-label-zero { color: #78716c; }
.tl-track { position: relative; flex: 1; height: 24px; background: #f1f5f9; border-radius: 6px; }
.tl-bar { position: absolute; top: 2px; height: 20px; border-radius: 4px; opacity: 0.85; cursor: default; transition: opacity 0.15s; }
.tl-bar:hover { opacity: 1; box-shadow: 0 0 6px rgba(0,0,0,0.25); z-index: 2; }
.tl-gap { background: repeating-linear-gradient(45deg,#fca5a5,#fca5a5 3px,#fecaca 3px,#fecaca 6px) !important; border: 1px solid #ef4444; opacity: 0.7; }
.tl-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 3px,#d6d3d1 3px,#d6d3d1 6px) !important; border: 1px solid #78716c; opacity: 0.85; }
.tl-legend-zero { background: repeating-linear-gradient(-45deg,#a8a29e,#a8a29e 3px,#d6d3d1 3px,#d6d3d1 6px) !important; border: 1px solid #78716c; }
.tl-zoom-wrapper { margin-top: 8px; border: 1px solid #e2e8f0; border-radius: 10px; overflow: auto; max-height: 75vh; min-height: 420px; background: #fafafa; }
.tl-zoom-controls { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }
.tl-zoom-label { font-size: 13px; font-weight: 600; color: #475569; }
.tl-zoom-btn { padding: 6px 12px; font-size: 12px; font-weight: 600; color: #64748b; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer; transition: all 0.15s; }
.tl-zoom-btn:hover { background: #e2e8f0; color: #334155; border-color: #94a3b8; }
.tl-zoom-btn.active { background: #6366f1; color: #fff; border-color: #4f46e5; }
.tl-zoom-inner { display: inline-block; min-width: 100%; transform-origin: top left; transition: transform 0.2s ease; padding: 12px 16px; }
.tl-axis { position: relative; height: 28px; margin-left: 214px; margin-top: 4px; border-top: 1px solid #cbd5e1; }
.tl-tick { position: absolute; top: 4px; font-size: 11px; color: #64748b; transform: translateX(-50%); }
.tl-tick::before { content: ''; position: absolute; top: -6px; left: 50%; width: 1px; height: 6px; background: #cbd5e1; }
.tl-ref-lines { position: absolute; left: 200px; right: 0; top: 0; bottom: 0; pointer-events: none; z-index: 0; }
.tl-ref-line { position: absolute; top: 0; bottom: 0; left: 0; display: flex; flex-direction: column; align-items: center; transform: translateX(-50%); }
.tl-ref-label { font-size: 10px; color: #64748b; white-space: nowrap; margin-bottom: 4px; font-weight: 600; }
.tl-ref-vline { flex: 1; width: 1px; min-height: 0; background: #64748b; opacity: 0.7; }
.tl-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; font-size: 13px; }
.tl-legend-item { display: inline-flex; align-items: center; gap: 6px; color: #334155; }
.tl-legend-dot { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.totals-info-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 24px; margin-bottom: 20px; padding: 16px 20px; background: #dbeafe; border-radius: 8px; border: 1px solid #93c5fd; }
.totals-info-bar-warning { background: #fef3c7; border-color: #f59e0b; }
.totals-info-bar-warning .totals-info-msg { color: #b45309; }
.totals-info-msg { font-size: 16px; font-weight: 600; color: #1e40af; flex: 1; min-width: 200px; }
.totals-summary { display: flex; gap: 24px; flex-wrap: wrap; }
.totals-summary-item { display: flex; flex-direction: column; gap: 4px; }
.totals-summary-label { font-size: 13px; font-weight: 600; color: #475569; }
.totals-summary-value { font-size: 22px; font-weight: 800; color: #1e293b; }
.totals-filters { display: flex; flex-wrap: wrap; gap: 20px 28px; margin-bottom: 20px; padding: 16px 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }
.totals-filters .filter-group { display: flex; flex-direction: column; gap: 10px; }
.totals-filters .filter-label { font-size: 16px; font-weight: 700; color: #1e293b; }
.totals-filters .filter-options { display: flex; flex-wrap: wrap; gap: 12px 16px; max-height: 160px; overflow-y: auto; }
.totals-filters .filter-cb { display: flex; align-items: center; gap: 10px; font-size: 16px; color: #334155; cursor: pointer; white-space: nowrap; line-height: 1.4; }
.totals-filters .filter-cb input[type="checkbox"] { width: 20px; height: 20px; min-width: 20px; min-height: 20px; cursor: pointer; accent-color: #6366f1; }
.totals-filters .filter-date { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; }
.totals-filters .filter-dropdown { position: relative; }
.totals-filters .filter-dropdown-trigger { display: inline-flex; align-items: center; min-width: 200px; padding: 10px 14px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 16px; color: #334155; cursor: pointer; user-select: none; }
.totals-filters .filter-dropdown-trigger:hover { border-color: #6366f1; }
.totals-filters .filter-dropdown-trigger::after { content: ''; margin-left: auto; border: 6px solid transparent; border-top-color: #64748b; }
.totals-filters .filter-dropdown-panel { display: none; position: absolute; top: 100%; left: 0; margin-top: 4px; min-width: 280px; max-height: 320px; overflow-y: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.12); z-index: 100; }
.totals-filters .filter-dropdown.open .filter-dropdown-panel { display: block; }
.totals-filters .filter-dropdown.open .filter-dropdown-trigger { border-color: #6366f1; }
.totals-filters .filter-dropdown .filter-options { max-height: 280px; flex-direction: column; flex-wrap: nowrap; padding: 8px; }
.totals-filters .filter-dropdown .filter-cb { white-space: normal; }
.date-key-panel { margin-top: 24px; padding: 20px 24px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; }
.date-key-title { font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }
.date-key-desc { font-size: 12px; color: #64748b; margin-bottom: 16px; font-style: italic; }
.date-key-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 10px; }
.date-key-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }
.date-key-num { width: 30px; height: 30px; background: #6366f1; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.date-key-label { font-size: 13px; color: #475569; line-height: 1.3; }
.date-key-value { font-size: 20px; font-weight: 800; color: #1e293b; margin-top: 2px; }
@media print { .totals-filters { display: none !important; } .totals-info-bar { display: none !important; } .date-key-panel { break-inside: avoid; } .lite-exclusion-note { font-size: 9px; margin-bottom: 4px; } }
.copy-target { cursor: pointer; position: relative; transition: background-color 0.15s; }
.copy-target:hover { background-color: rgba(99,102,241,0.15) !important; }
.copy-target:active { background-color: rgba(99,102,241,0.25) !important; }
#toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; pointer-events: none; }
.toast { background: #1e293b; color: #fff; padding: 10px 16px; border-radius: 8px; margin-top: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 15px; font-weight: 600; opacity: 0; transform: translateY(10px); transition: opacity 0.3s, transform 0.3s; }
.toast.show { opacity: 1; transform: translateY(0); }
.complex-file-warning { background: #fef2f2; border: 2px solid #dc2626; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; color: #991b1b; font-weight: 700; font-size: 1rem; }
"""

VIEWER_JS = r"""
function applyApodoxesTooltips(){var pane=document.getElementById('pane-count');if(!pane)return;var tooltipEl=document.getElementById('apodoxes-tooltip');if(!tooltipEl){tooltipEl=document.createElement('div');tooltipEl.id='apodoxes-tooltip';tooltipEl.className='apodoxes-tooltip';tooltipEl.setAttribute('aria-hidden','true');document.body.appendChild(tooltipEl);}
function showTip(td,text){if(!text)return;tooltipEl.textContent=text;tooltipEl.classList.add('visible');tooltipEl.setAttribute('aria-hidden','false');tooltipEl.offsetHeight;var rect=td.getBoundingClientRect();var tipRect=tooltipEl.getBoundingClientRect();var left=rect.left+(rect.width/2)-(tipRect.width/2);var top=rect.top-tipRect.height-10;if(top<8){top=rect.bottom+10;}left=Math.max(12,Math.min(left,window.innerWidth-tipRect.width-12));tooltipEl.style.left=left+'px';tooltipEl.style.top=top+'px';}
function hideTip(){tooltipEl.classList.remove('visible');tooltipEl.setAttribute('aria-hidden','true');}
pane.querySelectorAll('table.print-table').forEach(function(tbl){var headers=tbl.querySelectorAll('thead th');var colIndex=-1;for(var i=0;i<headers.length;i++){var t=(headers[i].textContent||'').trim();if(t.indexOf('ΑΠΟΔΟΧΩΝ')!==-1||t.indexOf('Τύπος Αποδοχών')!==-1){colIndex=i;break;}}if(colIndex<0)return;tbl.querySelectorAll('tbody tr').forEach(function(tr){var td=tr.querySelectorAll('td')[colIndex];if(td){var code=(td.textContent||'').trim();var key=code.length===1&&/^\d$/.test(code)?'0'+code:code;var desc=_apodoxesDescriptions[key]||_apodoxesDescriptions[code]||'';if(desc){td.classList.add('has-apodoxes-tooltip');td.setAttribute('data-tooltip',desc);td.removeAttribute('title');td.addEventListener('mouseenter',function(){showTip(td,desc);});td.addEventListener('mouseleave',hideTip);}}});});}
function showTab(tabId){document.querySelectorAll('.tab-pane').forEach(function(p){p.classList.remove('active');});document.querySelectorAll('.nav-item').forEach(function(a){a.classList.remove('active');});var pane=document.getElementById('pane-'+tabId);var link=document.querySelector('.nav-item[data-tab="'+tabId+'"]');if(pane)pane.classList.add('active');if(link)link.classList.add('active');if(tabId==='count')applyApodoxesTooltips();}
document.addEventListener('DOMContentLoaded',function(){applyApodoxesTooltips();});
function buildSinglePrintDoc(title,bodyContent){var styles=typeof _printStyles==='string'?_printStyles:'';var name=(typeof _clientName==='string'?_clientName:'').trim();var fullTitle=(name?name+' - '+(title||'')+' - ':(title||'ATLAS')+' - ')+'Atlas';var safeTitle=fullTitle.replace(/</g,'&lt;').replace(/"/g,'&quot;');var safeName=name.replace(/</g,'&lt;').replace(/&/g,'&amp;');var nameBlock=name?'<div class="prt-name">'+safeName+'</div>':'';return'<!DOCTYPE html><html lang="el"><head><meta charset="utf-8"><title>'+safeTitle+'</title><link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;600;700&display=swap" rel="stylesheet"><style>'+styles+'</style></head><body>'+nameBlock+'<div class="prt-title">Ασφαλιστικό Βιογραφικό ATLAS</div>'+bodyContent+'<div style="margin-top:12px;font-size:9px;color:#888;text-align:left;">© Syntaksi Pro - my advisor</div></body></html>';}
function printSection(el){var source=el.classList&&el.classList.contains('print-section')?el:(el.closest&&el.closest('.print-section')||el);var clone=source.cloneNode(true);clone.querySelectorAll('.section-actions,.btn-fs,.btn-print-tab').forEach(function(n){n.remove();});var title=(clone.querySelector('h2')&&clone.querySelector('h2').textContent)||'ATLAS';var bodyContent;var totalsTable=clone.querySelector('#totals-filter-table');if(totalsTable){var h2Text=(clone.querySelector('h2')&&clone.querySelector('h2').textContent)||'Σύνολα';bodyContent='<div class="print-section"><h2>'+h2Text.replace(/</g,'&lt;')+'</h2>'+totalsTable.outerHTML+'</div>';}else{bodyContent=clone.outerHTML;}var printDoc=buildSinglePrintDoc(title,bodyContent);var w=window.open('','_blank');w.document.write(printDoc);w.document.close();w.focus();setTimeout(function(){w.print();w.close();},400);}
function openTableFs(el){var overlay=document.createElement('div');overlay.className='table-fullscreen';overlay.id='fs-overlay';var section=el.classList.contains('print-section')?el:el.closest('.print-section');var source=section||el;var heading=source.querySelector?source.querySelector('h2'):null;var titleText=heading?heading.textContent:'Πίνακας';var hasInteractive=source.querySelector&&source.querySelector('script');var toolbar=document.createElement('div');toolbar.className='fs-toolbar';toolbar.innerHTML='<span class="fs-title">'+titleText+'</span>';var actions=document.createElement('div');actions.className='fs-toolbar-actions';var printBtn=document.createElement('button');printBtn.className='fs-print-btn';printBtn.innerHTML='🖨 Εκτύπωση';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(){var bodyEl=overlay.querySelector('.fs-body');if(bodyEl){var clone=bodyEl.cloneNode(true);clone.querySelectorAll('.section-actions,.btn-fs,.btn-print-tab').forEach(function(n){n.remove();});var totalsTable=clone.querySelector('#totals-filter-table');var bodyContent=totalsTable?'<div class="print-section"><h2>'+(titleText.replace(/</g,'&lt;')||'Σύνολα')+'</h2>'+totalsTable.outerHTML+'</div>':clone.innerHTML;var printDoc=buildSinglePrintDoc(titleText,bodyContent);var w=window.open('','_blank');w.document.write(printDoc);w.document.close();w.focus();setTimeout(function(){w.print();w.close();},400);}};actions.appendChild(printBtn);var closeBtn=document.createElement('button');closeBtn.className='fs-close';closeBtn.innerHTML='✕';closeBtn.title='Κλείσιμο (Esc)';closeBtn.onclick=closeTableFs;actions.appendChild(closeBtn);toolbar.appendChild(actions);var body=document.createElement('div');body.className='fs-body';if(hasInteractive){var placeholder=document.createElement('div');placeholder.id='fs-placeholder';placeholder.style.display='none';source.parentNode.insertBefore(placeholder,source);body.appendChild(source);overlay._fsSource=source;overlay._fsPlaceholder=placeholder;}else{body.appendChild(source.cloneNode(true));}overlay.appendChild(toolbar);overlay.appendChild(body);document.body.appendChild(overlay);document.body.style.overflow='hidden';}
function closeTableFs(){var overlay=document.getElementById('fs-overlay');if(overlay){if(overlay._fsSource&&overlay._fsPlaceholder){overlay._fsPlaceholder.parentNode.insertBefore(overlay._fsSource,overlay._fsPlaceholder);overlay._fsPlaceholder.remove();}overlay.remove();document.body.style.overflow='';}}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeTableFs();});
function openPrint(){var blob=new Blob([_printHtml],{type:'text/html;charset=utf-8'});var url=URL.createObjectURL(blob);window.open(url,'_blank');}
function downloadFullHtml(){var html='<!DOCTYPE html>\n'+document.documentElement.outerHTML;var blob=new Blob([html],{type:'text/html;charset=utf-8'});var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=_downloadFilename;a.click();URL.revokeObjectURL(a.href);}
function showToast(message){var container=document.getElementById('toast-container');var toast=document.createElement('div');toast.className='toast';toast.textContent=message;container.appendChild(toast);void toast.offsetWidth;toast.classList.add('show');setTimeout(function(){toast.classList.remove('show');setTimeout(function(){if(container.contains(toast))container.removeChild(toast);},300);},2000);}
document.addEventListener('click',function(e){var target=e.target.closest('.copy-target');if(target){var text=target.innerText.trim();if(text&&text!=='-'&&text!==''){navigator.clipboard.writeText(text).then(function(){showToast('Αντιγράφηκε: '+text);}).catch(function(err){console.error('Copy failed:',err);});}}});
document.addEventListener('DOMContentLoaded',function(){document.querySelectorAll('.print-section').forEach(function(sec){var actions=document.createElement('div');actions.className='section-actions';var printBtn=document.createElement('button');printBtn.className='btn-print-tab';printBtn.innerHTML='🖨';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(e){e.stopPropagation();printSection(sec);};var fsBtn=document.createElement('button');fsBtn.className='btn-fs';fsBtn.innerHTML='⛶';fsBtn.title='Πλήρης οθόνη';fsBtn.onclick=function(e){e.stopPropagation();openTableFs(sec);};actions.appendChild(printBtn);actions.appendChild(fsBtn);sec.appendChild(actions);});
document.querySelectorAll('table.print-table').forEach(function(tbl){if(tbl.closest('.print-section'))return;var wrapper=document.createElement('div');wrapper.className='table-container';tbl.parentNode.insertBefore(wrapper,tbl);wrapper.appendChild(tbl);var actions=document.createElement('div');actions.className='section-actions';var printBtn=document.createElement('button');printBtn.className='btn-print-tab';printBtn.innerHTML='🖨';printBtn.title='Εκτύπωση μόνο αυτής της καρτέλας';printBtn.onclick=function(e){e.stopPropagation();printSection(tbl);};var fsBtn=document.createElement('button');fsBtn.className='btn-fs';fsBtn.innerHTML='⛶';fsBtn.title='Πλήρης οθόνη';fsBtn.onclick=function(e){e.stopPropagation();openTableFs(tbl);};actions.appendChild(printBtn);actions.appendChild(fsBtn);wrapper.appendChild(actions);});
var targetColumns=['Συνολικές ημέρες','Μικτές αποδοχές','Συνολικές εισφορές','ΣΥΝΟΛΟ','ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ','ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ','Ημέρες Ασφ.','Σύνολο','Μικτές Αποδοχές','Συνολικές Εισφορές'];
var tables=document.querySelectorAll('table.print-table');tables.forEach(function(table){var headers=table.querySelectorAll('thead th');var targetIndices=[];headers.forEach(function(th,index){var headerText=th.textContent.trim();if(targetColumns.some(function(col){return headerText.indexOf(col)!==-1;})){targetIndices.push(index);}});if(targetIndices.length>0){var rows=table.querySelectorAll('tbody tr');rows.forEach(function(row){var cells=row.querySelectorAll('td');targetIndices.forEach(function(index){if(cells[index]){cells[index].classList.add('copy-target');cells[index].title='Κλικ για αντιγραφή';}});});}});
var cardElements=document.querySelectorAll('.audit-card-result');cardElements.forEach(function(el){el.classList.add('copy-target');el.title='Κλικ για αντιγραφή';});});
"""

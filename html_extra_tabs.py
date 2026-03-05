"""
html_extra_tabs.py
~~~~~~~~~~~~~~~~~~
Κατασκευή HTML ενοτήτων για τα extra tabs:
  - Κύρια Δεδομένα (main data, JS filters, Greek formatting)
  - Ανάλυση ΑΠΔ (plafond, retention %, JS filters, yearly grouping)
  - Αποζημίωση (compensation, grouped table, metrics, filters)
  - Παράρτημα (appendix, static table)

Χρησιμοποιείται από html_viewer_builder.py.
"""

import html as html_mod
import json
import pandas as pd

from app_final import (
    clean_numeric_value,
    apply_negative_time_sign,
    get_negative_amount_sign,
    format_currency,
    format_number_greek,
    APODOXES_DESCRIPTIONS,
    PLAFOND_PALIOS,
    PLAFOND_NEOS,
)
from html_viewer_builder import EXCLUDED_PACKAGES, EXCLUDED_PACKAGES_LABEL, parse_greek_number


def _esc(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ''
    sv = str(s).strip()
    return html_mod.escape(sv) if sv not in ('', 'None', 'nan') else ''


def _excl_unused(df):
    pkg_col = None
    for c in ['Κλάδος/Πακέτο Κάλυψης', 'Κλάδος/Πακέτο', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ']:
        if c in df.columns:
            pkg_col = c
            break
    if pkg_col is None:
        return df
    return df[~df[pkg_col].astype(str).str.strip().isin(EXCLUDED_PACKAGES)].copy()


def _detect_is_palios(df):
    if 'Από' not in df.columns:
        return False
    try:
        from_dates = pd.to_datetime(df['Από'], format='%d/%m/%Y', errors='coerce')
        return not from_dates.isnull().all() and from_dates.min() < pd.Timestamp('1993-01-01')
    except Exception:
        return False


def _fmt_curr(v):
    """Format as Greek currency."""
    if v is None or v == '' or (isinstance(v, float) and pd.isna(v)):
        return ''
    try:
        nv = float(v) if isinstance(v, (int, float)) else (clean_numeric_value(v, exclude_drx=True) or 0)
        return format_currency(nv) if nv else ''
    except Exception:
        return _esc(v)


def _fmt_num(v, decimals=0):
    """Format as Greek number."""
    if v is None or v == '' or (isinstance(v, float) and pd.isna(v)):
        return ''
    try:
        return format_number_greek(v, decimals=decimals)
    except Exception:
        return _esc(v)


def _dropdown(name, values, data_attr, filter_group_id):
    if not values:
        return ""
    items = "".join(
        f'<label class="filter-cb"><input type="checkbox" '
        f'data-filter-group="{filter_group_id}" data-attr="{data_attr}" '
        f'value="{_esc(v)}">{_esc(v)}</label>'
        for v in values
    )
    return (
        f'<div class="filter-group filter-dropdown" data-filter-name="{_esc(name)}">'
        f'<span class="filter-label">{_esc(name)}:</span>'
        f'<div class="filter-dropdown-trigger" tabindex="0" role="button" '
        f'aria-expanded="false">Επιλέξτε {_esc(name)}…</div>'
        f'<div class="filter-dropdown-panel"><div class="filter-options">{items}</div></div></div>'
    )


def _filters_js_boilerplate(container_id):
    """Common JS for dropdown open/close in a filter container."""
    return f"""
      document.querySelectorAll('#{container_id} .filter-dropdown-trigger').forEach(function(tr){{
        tr.addEventListener('click',function(e){{e.stopPropagation();var dd=tr.closest('.filter-dropdown');if(dd)dd.classList.toggle('open');tr.setAttribute('aria-expanded',dd&&dd.classList.contains('open')?'true':'false');}});
      }});
      document.addEventListener('click',function(){{document.querySelectorAll('#{container_id} .filter-dropdown.open').forEach(function(dd){{dd.classList.remove('open');}});}});
      document.querySelectorAll('#{container_id} .filter-dropdown-panel').forEach(function(p){{p.addEventListener('click',function(e){{e.stopPropagation();}});}});
    """


# ---------------------------------------------------------------------------
# 1. Παράρτημα
# ---------------------------------------------------------------------------

def build_annex_tab(df):
    extra_columns = [c for c in df.columns if c in ['Φορέας', 'Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή']]
    if not extra_columns:
        return ""
    extra_df = df[extra_columns].copy()
    extra_df = extra_df.dropna(how='all')
    extra_df = extra_df[~((extra_df == 'None') | (extra_df == '') | (extra_df.isna())).all(axis=1)]
    if extra_df.empty:
        return ""
    headers = "".join(f"<th>{_esc(c)}</th>" for c in extra_df.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{_esc(v)}</td>" for v in row.values) + "</tr>"
        for _, row in extra_df.iterrows()
    )
    return (
        f"<section class='print-section'><h2>Παράρτημα</h2>"
        f"<p class='print-description'>Επεξηγηματικοί πίνακες καλύψεων και αποδοχών.</p>"
        f"<table class='print-table wrap-cells'><thead><tr>{headers}</tr></thead>"
        f"<tbody>{rows}</tbody></table></section>"
    )


# ---------------------------------------------------------------------------
# 2. Κύρια Δεδομένα (with Greek formatting + JS filters)
# ---------------------------------------------------------------------------

def build_main_data_tab(df, description_map=None):
    description_map = description_map or {}
    main_cols = [c for c in df.columns if c not in [
        'Φορέας', 'Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή',
        'Κωδικός Τύπου Αποδοχών', 'Σελίδα',
    ]]
    mdf = df[main_cols].copy() if main_cols else df.copy()
    if 'Από' in mdf.columns:
        mdf['_dt'] = pd.to_datetime(mdf['Από'], format='%d/%m/%Y', errors='coerce')
        mdf = mdf.dropna(subset=['_dt']).sort_values('_dt').drop(columns=['_dt'])
    if mdf.empty:
        return ""

    currency_cols = {'Μικτές αποδοχές', 'Συνολικές εισφορές'}
    numeric_cols = {'Ημερολογιακές ημέρες': 0, 'Μήνες': 1, 'Έτη': 1}

    tameio_vals = sorted(mdf['Ταμείο'].dropna().unique().tolist()) if 'Ταμείο' in mdf.columns else []
    typos_vals = sorted(mdf['Τύπος Ασφάλισης'].dropna().unique().tolist()) if 'Τύπος Ασφάλισης' in mdf.columns else []
    pkg_col = 'Κλάδος/Πακέτο Κάλυψης' if 'Κλάδος/Πακέτο Κάλυψης' in mdf.columns else None
    pkg_vals = sorted(mdf[pkg_col].dropna().unique().tolist()) if pkg_col else []
    earn_col = next((c for c in mdf.columns if 'Τύπος Αποδοχών' in c), None)
    earn_vals = sorted(mdf[earn_col].dropna().astype(str).unique().tolist()) if earn_col else []
    emp_col = 'Α-Μ εργοδότη' if 'Α-Μ εργοδότη' in mdf.columns else None
    emp_vals = sorted(mdf[emp_col].dropna().astype(str).unique().tolist()) if emp_col else []

    pkg_display = {
        (f"{v} – {description_map.get(v, '')}" if description_map.get(v) else v): v
        for v in pkg_vals
    }

    headers_html = "".join(f"<th>{_esc(c)}</th>" for c in main_cols)
    rows_html = []
    for _, row in mdf.iterrows():
        attrs = []
        if 'Ταμείο' in row.index:
            attrs.append(f'data-tameio="{_esc(row.get("Ταμείο", ""))}"')
        if 'Τύπος Ασφάλισης' in row.index:
            attrs.append(f'data-typos="{_esc(row.get("Τύπος Ασφάλισης", ""))}"')
        if pkg_col and pkg_col in row.index:
            attrs.append(f'data-pkg="{_esc(row.get(pkg_col, ""))}"')
        if earn_col and earn_col in row.index:
            attrs.append(f'data-earn="{_esc(row.get(earn_col, ""))}"')
        if emp_col and emp_col in row.index:
            attrs.append(f'data-emp="{_esc(row.get(emp_col, ""))}"')
        if 'Από' in row.index:
            attrs.append(f'data-apo="{_esc(row.get("Από", ""))}"')
        if 'Έως' in row.index:
            attrs.append(f'data-eos="{_esc(row.get("Έως", ""))}"')

        tds = []
        for c in main_cols:
            v = row[c]
            if c in currency_cols:
                tds.append(f"<td>{_fmt_curr(v)}</td>")
            elif c in numeric_cols:
                tds.append(f"<td>{_fmt_num(v, decimals=numeric_cols[c])}</td>")
            else:
                tds.append(f"<td>{_esc(v)}</td>")
        rows_html.append(f"<tr {' '.join(attrs)}>{''.join(tds)}</tr>")

    pkg_map_js = json.dumps(pkg_display).replace("</script>", "<\\/script>")

    filters = (
        '<div class="totals-filters" id="main-data-filters">'
        + _dropdown("Ταμείο", tameio_vals, "tameio", "main-data")
        + _dropdown("Τύπος Ασφάλισης", typos_vals, "typos", "main-data")
        + _dropdown("Κλάδος/Πακέτο", list(pkg_display.keys()), "pkg", "main-data")
        + _dropdown("Τύπος Αποδοχών", earn_vals, "earn", "main-data")
        + _dropdown("Α-Μ Εργοδότη", emp_vals, "emp", "main-data")
        + '<div class="filter-group"><span class="filter-label">Από:</span>'
        + '<input type="text" id="main-filter-apo" class="filter-date" placeholder="ηη/μμ/εεεε" maxlength="10"></div>'
        + '<div class="filter-group"><span class="filter-label">Έως:</span>'
        + '<input type="text" id="main-filter-eos" class="filter-date" placeholder="ηη/μμ/εεεε" maxlength="10"></div>'
        + '</div>'
    )

    js = f"""
    (function(){{
      var pkgMap={pkg_map_js};
      function parseDate(s){{if(!s||s==='')return null;var p=s.match(/^(\\d{{1,2}})\\/(\\d{{1,2}})\\/(\\d{{4}})$/);if(!p)return null;return new Date(parseInt(p[3],10),parseInt(p[2],10)-1,parseInt(p[1],10));}}
      function apply(){{
        var rows=document.querySelectorAll('#main-data-table tbody tr');
        var sel={{}};
        document.querySelectorAll('#main-data-filters input[type="checkbox"]:checked').forEach(function(cb){{
          var a=cb.getAttribute('data-attr');if(!sel[a])sel[a]=[];
          var v=cb.value;if(a==='pkg'&&pkgMap[v])v=pkgMap[v];
          sel[a].push(v);
        }});
        var aD=parseDate((document.getElementById('main-filter-apo')||{{}}).value||'');
        var eD=parseDate((document.getElementById('main-filter-eos')||{{}}).value||'');
        var n=0;
        rows.forEach(function(tr){{
          var ok=true;
          ['tameio','typos','pkg','earn','emp'].forEach(function(a){{
            if(sel[a]&&sel[a].length>0&&sel[a].indexOf((tr.getAttribute('data-'+a)||'').trim())===-1)ok=false;
          }});
          if(ok&&aD){{var r=parseDate((tr.getAttribute('data-eos')||'').trim());if(r&&r<aD)ok=false;}}
          if(ok&&eD){{var r2=parseDate((tr.getAttribute('data-apo')||'').trim());if(r2&&r2>eD)ok=false;}}
          tr.style.display=ok?'':'none';if(ok)n++;
        }});
        var el=document.getElementById('main-data-count');if(el)el.textContent='Εμφανίζονται '+n+' γραμμές';
      }}
      document.querySelectorAll('#main-data-filters input').forEach(function(i){{i.addEventListener('change',apply);i.addEventListener('input',apply);}});
      {_filters_js_boilerplate('main-data-filters')}
      apply();
    }})();
    """

    return (
        f"<section class='print-section'><h2>Κύρια Δεδομένα e-EFKA</h2>"
        f"<p class='print-description'>Αναλυτική χρονολογική κατάσταση ασφαλιστικών εγγραφών.</p>"
        f"<div id='main-data-count' style='font-size:13px;color:#64748b;margin-bottom:8px;'>"
        f"Εμφανίζονται {len(mdf)} γραμμές</div>"
        f"{filters}"
        f"<table class='print-table' id='main-data-table'><thead><tr>{headers_html}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
        f"<script>{js}</script></section>"
    )


# ---------------------------------------------------------------------------
# 3. Αποζημίωση (with metrics + filters)
# ---------------------------------------------------------------------------

def build_apozimiosi_tab(df, description_map=None):
    description_map = description_map or {}
    apoz_df = _excl_unused(df.copy())
    required = ['Από', 'Έως', 'Ημέρες']
    if 'Τύπος Ασφάλισης' not in apoz_df.columns:
        apoz_df['Τύπος Ασφάλισης'] = ''

    def is_m(t):
        s = str(t).strip().upper()
        return 'ΜΙΣΘΩΤΗ' in s and 'ΜΗ ΜΙΣΘΩΤΗ' not in s and not s.startswith('ΜΗ ')

    apoz_df = apoz_df[apoz_df['Τύπος Ασφάλισης'].apply(is_m)]
    if apoz_df.empty or not all(c in apoz_df.columns for c in required):
        return ""

    # -- Compute metrics for last employer --
    metrics_html = ""
    try:
        calc = apoz_df.copy()
        calc['_edt'] = pd.to_datetime(calc['Έως'], format='%d/%m/%Y', errors='coerce')
        calc['_adt'] = pd.to_datetime(calc['Από'], format='%d/%m/%Y', errors='coerce')
        calc = calc.dropna(subset=['_edt', '_adt'])
        if not calc.empty and 'Α-Μ εργοδότη' in calc.columns:
            last_row = calc.loc[calc['_edt'].idxmax()]
            last_emp = str(last_row.get('Α-Μ εργοδότη', '')).strip()
            emp_df = calc[calc['Α-Μ εργοδότη'].astype(str).str.strip() == last_emp]
            total_d, total_d_pre = 0.0, 0.0
            cutoff = pd.Timestamp('2012-11-12')
            for _, er in emp_df.iterrows():
                dv = 0.0
                for col, mult in [('Ημέρες', 1), ('Έτη', 300), ('Μήνες', 25)]:
                    if col in er and pd.notna(er[col]):
                        cv = clean_numeric_value(er[col])
                        if cv:
                            dv += cv * mult
                gv = clean_numeric_value(str(er.get('Μικτές αποδοχές', '')), exclude_drx=True) or 0
                cv2 = clean_numeric_value(str(er.get('Συνολικές εισφορές', '')), exclude_drx=True) or 0
                if get_negative_amount_sign(gv, cv2) == -1:
                    dv = -abs(dv)
                total_d += dv
                if er['_edt'] <= cutoff:
                    total_d_pre += dv
                elif er['_adt'] < cutoff:
                    span = (er['_edt'] - er['_adt']).days + 1
                    pre = (cutoff - er['_adt']).days + 1
                    if span > 0:
                        total_d_pre += dv * (pre / span)

            last_salary = "–"
            try:
                e_col = next((c for c in df.columns if 'Τύπος Αποδοχών' in c), None)
                if e_col:
                    a01 = df[df[e_col].astype(str).str.strip().isin(['01', '1'])].copy()
                    if 'Τύπος Ασφάλισης' in a01.columns:
                        a01 = a01[a01['Τύπος Ασφάλισης'].apply(is_m)]
                    a01['_edt2'] = pd.to_datetime(a01['Έως'], format='%d/%m/%Y', errors='coerce')
                    a01 = a01.dropna(subset=['_edt2'])
                    if not a01.empty:
                        latest = a01.loc[a01['_edt2'].idxmax()]
                        sv = clean_numeric_value(str(latest.get('Μικτές αποδοχές', '')), exclude_drx=True)
                        if sv and sv > 0:
                            last_salary = format_currency(sv)
            except Exception:
                pass

            metrics_html = (
                '<div style="display:flex;flex-wrap:wrap;gap:16px;margin:16px 0;padding:16px;'
                'background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;">'
                + _metric("Τελευταίος εργοδότης", last_emp)
                + _metric("Ημέρες τελ. εργοδότη", _fmt_num(total_d, 0))
                + _metric("Έτη τελ. εργοδότη", _fmt_num(total_d / 300, 2))
                + _metric("Ημέρες έως 12/11/2012", _fmt_num(total_d_pre, 0))
                + _metric("Έτη έως 12/11/2012", _fmt_num(total_d_pre / 300, 2))
                + _metric("Τελευταίος μισθός", last_salary)
                + '</div>'
            )
    except Exception:
        pass

    # -- Build aggregated rows --
    rows_data = []
    for _, row in apoz_df.iterrows():
        try:
            if pd.isna(row['Από']) or pd.isna(row['Έως']):
                continue
            sdt = pd.to_datetime(row['Από'], format='%d/%m/%Y', errors='coerce')
            edt = pd.to_datetime(row['Έως'], format='%d/%m/%Y', errors='coerce')
            if pd.isna(sdt) or pd.isna(edt):
                continue
            dv = 0
            for col, mult in [('Ημέρες', 1), ('Έτη', 300), ('Μήνες', 25)]:
                if col in row and pd.notna(row[col]) and str(row[col]).strip():
                    v = clean_numeric_value(row[col])
                    if v:
                        dv += v * mult
            raw_g = str(row.get('Μικτές αποδοχές', ''))
            raw_c = str(row.get('Συνολικές εισφορές', ''))
            gv = clean_numeric_value(raw_g, exclude_drx=True) or 0.0
            cv = clean_numeric_value(raw_c, exclude_drx=True) or 0.0
            if get_negative_amount_sign(gv, cv) == -1:
                dv = -abs(dv)
            klados = str(row.get('Κλάδος/Πακέτο Κάλυψης', '')).strip()
            rows_data.append({
                'ΕΤΟΣ': sdt.year,
                'ΤΑΜΕΙΟ': str(row.get('Ταμείο', '')).strip(),
                'ΕΡΓΟΔΟΤΗΣ': str(row.get('Α-Μ εργοδότη', '')).strip(),
                'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ': klados,
                'ΠΕΡΙΓΡΑΦΗ': description_map.get(klados, ''),
                'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ': str(row.get('Τύπος Αποδοχών', '')).strip(),
                'ΣΥΝΟΛΟ': dv, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ': gv, 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ': cv,
            })
        except Exception:
            continue

    if not rows_data:
        return ""

    adf = pd.DataFrame(rows_data)
    gc = ['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΕΡΓΟΔΟΤΗΣ', 'ΚΛΑΔΟΣ/ΠΑΚΕΤΟ', 'ΠΕΡΙΓΡΑΦΗ', 'ΤΥΠΟΣ ΑΠΟΔΟΧΩΝ']
    agg = adf.groupby(gc, dropna=False)[['ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ']].sum().reset_index()
    agg = agg.sort_values(['ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΕΡΓΟΔΟΤΗΣ'])
    agg['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ''
    mask = agg['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'].notna() & (agg['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] != 0)
    agg.loc[mask, 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = (agg.loc[mask, 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] / agg.loc[mask, 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] * 100)

    all_cols = gc + ['ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ']

    def _fmtd(v):
        if v == 0 or v == '' or (isinstance(v, float) and pd.isna(v)):
            return ""
        try:
            x = float(v)
            return str(int(round(x))) if abs(x - round(x)) < 0.01 else f"{x:.1f}".replace('.', ',')
        except (TypeError, ValueError):
            return str(v) if v else ""

    def _fmte(v):
        if v == 0 or v == '' or (isinstance(v, float) and pd.isna(v)):
            return ""
        try:
            return format_currency(float(v))
        except (TypeError, ValueError):
            return ""

    def _fmtp(v):
        if v == '' or v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        try:
            x = float(v)
            return f"{x:.1f}%".replace('.', ',') if x != 0 else ""
        except (TypeError, ValueError):
            return ""

    processed = []
    py, pt, pe = None, None, None
    for _, row in agg.iterrows():
        cy, ct, ce = row['ΕΤΟΣ'], row['ΤΑΜΕΙΟ'], row['ΕΡΓΟΔΟΤΗΣ']
        if py is not None and cy != py:
            processed.append({c: '' for c in all_cols})
            pt, pe = None, None
        d = row.to_dict()
        if cy == py:
            d['ΕΤΟΣ'] = ''
        if cy == py and ct == pt:
            d['ΤΑΜΕΙΟ'] = ''
        if cy == py and ct == pt and ce == pe:
            d['ΕΡΓΟΔΟΤΗΣ'] = ''
        for c in all_cols:
            v = d.get(c)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                d[c] = ''
        processed.append(d)
        py, pt, pe = cy, ct, ce

    ddf = pd.DataFrame(processed, columns=all_cols)
    def _yr(x):
        if x == '' or x is None or (isinstance(x, float) and pd.isna(x)):
            return ''
        try:
            return str(int(float(x)))
        except:
            return ''
    ddf['ΕΤΟΣ'] = ddf['ΕΤΟΣ'].apply(_yr)
    ddf['ΣΥΝΟΛΟ'] = ddf['ΣΥΝΟΛΟ'].apply(_fmtd)
    ddf['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'] = ddf['ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ'].apply(_fmte)
    ddf['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'] = ddf['ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ'].apply(_fmte)
    ddf['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'] = ddf['ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'].apply(_fmtp)

    bold = {'ΕΤΟΣ', 'ΤΑΜΕΙΟ', 'ΕΡΓΟΔΟΤΗΣ', 'ΣΥΝΟΛΟ', 'ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ', 'ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ', 'ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ'}
    headers = "".join(f"<th>{_esc(c)}</th>" for c in all_cols)
    tbody = "".join(
        "<tr>" + "".join(
            f"<td{' style=\"font-weight:700\"' if c in bold else ''}>{_esc(row[c])}</td>"
            for c in all_cols
        ) + "</tr>"
        for _, row in ddf.iterrows()
    )

    return (
        f"<section class='print-section'><h2>Αποζημίωση (μισθωτή ασφάλιση)</h2>"
        f"<p class='print-description'>Σύνολα ημερών μισθωτής ασφάλισης χωρίς επιμερισμό ανά μήνα. "
        f"Εξαιρούνται: {_esc(EXCLUDED_PACKAGES_LABEL)}</p>"
        f"{metrics_html}"
        f"<table class='print-table wrap-cells'><thead><tr>{headers}</tr></thead>"
        f"<tbody>{tbody}</tbody></table></section>"
    )


def _metric(label, value):
    return (
        f'<div style="flex:1;min-width:140px;">'
        f'<div style="font-size:12px;color:#64748b;font-weight:600;">{_esc(label)}</div>'
        f'<div style="font-size:20px;font-weight:800;color:#1e293b;">{_esc(value)}</div></div>'
    )


# ---------------------------------------------------------------------------
# 4. Ανάλυση ΑΠΔ (plafond, retention, yearly grouping, JS filters)
# ---------------------------------------------------------------------------

def build_apd_tab(df, description_map=None):
    description_map = description_map or {}
    is_palios = _detect_is_palios(df)
    plafond_map = PLAFOND_PALIOS if is_palios else PLAFOND_NEOS
    status_msg = (
        "Παλιός Ασφαλισμένος (εγγραφή πριν από 1/1/1993)" if is_palios
        else "Νέος Ασφαλισμένος (χωρίς εγγραφή πριν από 1/1/1993)"
    )

    skip_cols = {'Φορέας', 'Κωδικός Κλάδων / Πακέτων Κάλυψης', 'Περιγραφή',
                 'Κωδικός Τύπου Αποδοχών', 'Σελίδα'}
    apd_cols = [c for c in df.columns if c not in skip_cols]
    apd_df = _excl_unused(df[apd_cols].copy())

    if 'Τύπος Ασφάλισης' in apd_df.columns:
        def _is_m(t):
            s = str(t).strip().upper()
            return 'ΜΙΣΘΩΤΗ' in s and 'ΜΗ ΜΙΣΘΩΤΗ' not in s and not s.startswith('ΜΗ ')
        default_typos = [t for t in apd_df['Τύπος Ασφάλισης'].dropna().unique() if _is_m(t)]
        if default_typos:
            apd_df = apd_df[apd_df['Τύπος Ασφάλισης'].isin(default_typos)]

    if 'Από' in apd_df.columns:
        apd_df['_dt'] = pd.to_datetime(apd_df['Από'], format='%d/%m/%Y', errors='coerce')
        apd_df = apd_df.dropna(subset=['_dt'])
        d2002 = pd.Timestamp('2002-01-01')
        apd_df = apd_df[apd_df['_dt'] >= d2002]
        apd_df['Έτος'] = apd_df['_dt'].dt.year
        apd_df['Μήνας'] = apd_df['_dt'].dt.month
        apd_df = apd_df.sort_values('_dt').drop(columns=['_dt'])

    if apd_df.empty:
        return ""

    earn_col = next((c for c in apd_df.columns if 'Τύπος Αποδοχών' in c), None)

    out_rows = []
    for _, row in apd_df.iterrows():
        r = {}
        r['Έτος'] = row.get('Έτος', '')
        r['Μήνας'] = row.get('Μήνας', '')
        for c in apd_df.columns:
            if c not in ('Έτος', 'Μήνας', 'Έτη', 'Μήνες', 'Ημέρες'):
                r[c] = row[c]

        if 'Κλάδος/Πακέτο Κάλυψης' in r:
            r['Περιγραφή Κλάδου'] = description_map.get(str(r.get('Κλάδος/Πακέτο Κάλυψης', '')).strip(), '')
        if earn_col and earn_col in r:
            r['Περιγραφή Τύπου Αποδοχών'] = APODOXES_DESCRIPTIONS.get(str(r.get(earn_col, '')).strip(), '')

        try:
            year = int(r['Έτος'])
            bp = plafond_map.get(str(year), 0)
            if earn_col and str(r.get(earn_col, '')).strip() in ('04', '05'):
                bp = bp / 2
            r['Εισφ. πλαφόν'] = bp
        except Exception:
            r['Εισφ. πλαφόν'] = 0

        gross = clean_numeric_value(r.get('Μικτές αποδοχές', 0), exclude_drx=True) or 0
        plaf = r['Εισφ. πλαφόν'] or 0
        r['Περικοπή'] = max(0, gross - plaf) if plaf > 0 else 0
        r['Συντ. Αποδοχές'] = min(gross, plaf) if plaf > 0 else gross

        contrib = clean_numeric_value(r.get('Συνολικές εισφορές', 0), exclude_drx=True) or 0
        adj = r['Συντ. Αποδοχές']
        r['Συν. % κράτησης'] = (contrib / adj * 100) if adj and adj > 0 else 0

        days = (clean_numeric_value(row.get('Ημέρες', 0)) or 0) + \
               (clean_numeric_value(row.get('Μήνες', 0)) or 0) * 25 + \
               (clean_numeric_value(row.get('Έτη', 0)) or 0) * 300
        r['Ημέρες Ασφ.'] = days

        out_rows.append(r)

    if not out_rows:
        return ""

    show_cols = ['Έτος', 'Μήνας']
    for c in apd_df.columns:
        if c in ('Έτος', 'Μήνας', 'Έτη', 'Μήνες', 'Ημέρες'):
            continue
        show_cols.append(c)
        if c == 'Κλάδος/Πακέτο Κάλυψης':
            show_cols.append('Περιγραφή Κλάδου')
        if earn_col and c == earn_col:
            show_cols.append('Περιγραφή Τύπου Αποδοχών')
        if c == 'Μικτές αποδοχές':
            show_cols.extend(['Εισφ. πλαφόν', 'Συντ. Αποδοχές', 'Περικοπή'])
        if c == 'Συνολικές εισφορές':
            show_cols.append('Συν. % κράτησης')
    if 'Ημέρες Ασφ.' not in show_cols:
        show_cols.append('Ημέρες Ασφ.')

    # Yearly total rows
    yearly_totals = {}
    for r in out_rows:
        y = r.get('Έτος', '')
        if y not in yearly_totals:
            yearly_totals[y] = {'gross': 0, 'contrib': 0, 'days': 0, 'adj': 0, 'cut': 0}
        yearly_totals[y]['gross'] += clean_numeric_value(r.get('Μικτές αποδοχές', 0), exclude_drx=True) or 0
        yearly_totals[y]['contrib'] += clean_numeric_value(r.get('Συνολικές εισφορές', 0), exclude_drx=True) or 0
        yearly_totals[y]['days'] += r.get('Ημέρες Ασφ.', 0) or 0
        yearly_totals[y]['adj'] += r.get('Συντ. Αποδοχές', 0) or 0
        yearly_totals[y]['cut'] += r.get('Περικοπή', 0) or 0

    tameio_vals = sorted(set(str(r.get('Ταμείο', '')).strip() for r in out_rows if r.get('Ταμείο')))
    typos_vals = sorted(set(str(r.get('Τύπος Ασφάλισης', '')).strip() for r in out_rows if r.get('Τύπος Ασφάλισης')))
    pkg_vals = sorted(set(str(r.get('Κλάδος/Πακέτο Κάλυψης', '')).strip() for r in out_rows if r.get('Κλάδος/Πακέτο Κάλυψης')))
    earn_vals = sorted(set(str(r.get(earn_col, '')).strip() for r in out_rows if earn_col and r.get(earn_col))) if earn_col else []

    filters_html = (
        '<div class="totals-filters" id="apd-filters">'
        + _dropdown("Ταμείο", tameio_vals, "tameio", "apd")
        + _dropdown("Τύπος Ασφ.", typos_vals, "typos", "apd")
        + _dropdown("Κλάδος/Πακέτο", pkg_vals, "pkg", "apd")
        + _dropdown("Τύπος Αποδοχών", earn_vals, "earn", "apd")
        + '<div class="filter-group"><span class="filter-label">Από:</span>'
        + '<input type="text" id="apd-filter-apo" class="filter-date" value="01/01/2002" maxlength="10"></div>'
        + '<div class="filter-group"><span class="filter-label">Έως:</span>'
        + '<input type="text" id="apd-filter-eos" class="filter-date" placeholder="ηη/μμ/εεεε" maxlength="10"></div>'
        + '<div class="filter-group"><span class="filter-label">Φίλτρο %:</span>'
        + '<input type="number" id="apd-filter-pct" class="filter-date" value="18" step="0.1" min="0" max="100" style="width:70px"></div>'
        + '<div class="filter-group"><span class="filter-label">Τύπος Φίλτρου:</span>'
        + '<select id="apd-filter-mode" class="filter-date" style="padding:8px;border-radius:6px;border:1px solid #cbd5e1;font-size:14px;">'
        + '<option value="all">Όλα</option><option value="gte">≥ %</option><option value="lt">&lt; %</option></select></div>'
        + '<div class="filter-group"><span class="filter-label">Επισήμανση &lt;:</span>'
        + '<input type="number" id="apd-highlight" class="filter-date" value="21" step="0.1" min="0" max="100" style="width:70px"></div>'
        + '</div>'
    )

    headers = "".join(f"<th>{_esc(c)}</th>" for c in show_cols)
    tbody_parts = []
    prev_year = None

    for r in out_rows:
        cy = r.get('Έτος', '')
        # Year total row before new year
        if prev_year is not None and cy != prev_year and prev_year in yearly_totals:
            yt = yearly_totals[prev_year]
            pct = (yt['contrib'] / yt['adj'] * 100) if yt['adj'] > 0 else 0
            total_cells = []
            for c in show_cols:
                if c == 'Έτος':
                    total_cells.append(f"<td style='font-weight:700'>Σύνολο {prev_year}</td>")
                elif c == 'Ημέρες Ασφ.':
                    total_cells.append(f"<td style='font-weight:700'>{_fmtd_inline(yt['days'])}</td>")
                elif c == 'Μικτές αποδοχές':
                    total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['gross'])}</td>")
                elif c == 'Συντ. Αποδοχές':
                    total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['adj'])}</td>")
                elif c == 'Περικοπή':
                    total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['cut'])}</td>")
                elif c == 'Συνολικές εισφορές':
                    total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['contrib'])}</td>")
                elif c == 'Συν. % κράτησης':
                    total_cells.append(f"<td style='font-weight:700'>{pct:.1f}%</td>".replace('.', ','))
                else:
                    total_cells.append("<td></td>")
            tbody_parts.append(
                f"<tr class='total-row' data-year='{prev_year}' data-is-total='1' "
                f"data-tameio='' data-typos='' data-pkg='' data-earn='' "
                f"data-apo='' data-retention='{pct:.2f}'>"
                f"{''.join(total_cells)}</tr>"
            )

        tameio = str(r.get('Ταμείο', '')).strip()
        typos = str(r.get('Τύπος Ασφάλισης', '')).strip()
        pkg = str(r.get('Κλάδος/Πακέτο Κάλυψης', '')).strip()
        earn = str(r.get(earn_col, '')).strip() if earn_col else ''
        apo = str(r.get('Από', '')).strip()
        retention = r.get('Συν. % κράτησης', 0) or 0

        attrs = (
            f' data-year="{_esc(str(cy))}" data-is-total="0"'
            f' data-tameio="{_esc(tameio)}" data-typos="{_esc(typos)}"'
            f' data-pkg="{_esc(pkg)}" data-earn="{_esc(earn)}"'
            f' data-apo="{_esc(apo)}" data-retention="{retention:.2f}"'
        )

        tds = []
        for c in show_cols:
            v = r.get(c, '')
            if c in ('Εισφ. πλαφόν', 'Περικοπή', 'Συντ. Αποδοχές'):
                tds.append(f"<td>{_fmt_curr(v) if isinstance(v, (int, float)) and v > 0 else ''}</td>")
            elif c == 'Συν. % κράτησης':
                tds.append(f"<td>{f'{v:.1f}%'.replace('.', ',') if isinstance(v, (int, float)) and v > 0 else ''}</td>")
            elif c == 'Ημέρες Ασφ.':
                tds.append(f"<td>{_fmtd_inline(v)}</td>")
            elif c in ('Μικτές αποδοχές', 'Συνολικές εισφορές'):
                tds.append(f"<td>{_fmt_curr(v)}</td>")
            elif c == 'Μήνας':
                tds.append(f"<td>{int(v) if isinstance(v, (int, float)) and v else _esc(v)}</td>")
            else:
                tds.append(f"<td>{_esc(v)}</td>")
        tbody_parts.append(f"<tr{attrs}>{''.join(tds)}</tr>")
        prev_year = cy

    # Last year total
    if prev_year and prev_year in yearly_totals:
        yt = yearly_totals[prev_year]
        pct = (yt['contrib'] / yt['adj'] * 100) if yt['adj'] > 0 else 0
        total_cells = []
        for c in show_cols:
            if c == 'Έτος':
                total_cells.append(f"<td style='font-weight:700'>Σύνολο {prev_year}</td>")
            elif c == 'Ημέρες Ασφ.':
                total_cells.append(f"<td style='font-weight:700'>{_fmtd_inline(yt['days'])}</td>")
            elif c == 'Μικτές αποδοχές':
                total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['gross'])}</td>")
            elif c == 'Συντ. Αποδοχές':
                total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['adj'])}</td>")
            elif c == 'Περικοπή':
                total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['cut'])}</td>")
            elif c == 'Συνολικές εισφορές':
                total_cells.append(f"<td style='font-weight:700'>{_fmt_curr(yt['contrib'])}</td>")
            elif c == 'Συν. % κράτησης':
                total_cells.append(f"<td style='font-weight:700'>{pct:.1f}%</td>".replace('.', ','))
            else:
                total_cells.append("<td></td>")
        tbody_parts.append(
            f"<tr class='total-row' data-year='{prev_year}' data-is-total='1' "
            f"data-tameio='' data-typos='' data-pkg='' data-earn='' "
            f"data-apo='' data-retention='{pct:.2f}'>"
            f"{''.join(total_cells)}</tr>"
        )

    js = """
    (function(){
      function parseDate(s){if(!s||s==='')return null;var p=s.match(/^(\\d{1,2})\\/(\\d{1,2})\\/(\\d{4})$/);if(!p)return null;return new Date(parseInt(p[3],10),parseInt(p[2],10)-1,parseInt(p[1],10));}
      function apply(){
        var rows=document.querySelectorAll('#apd-table tbody tr');
        var sel={};
        document.querySelectorAll('#apd-filters input[type="checkbox"]:checked').forEach(function(cb){
          var a=cb.getAttribute('data-attr');if(!sel[a])sel[a]=[];sel[a].push(cb.value);
        });
        var aD=parseDate((document.getElementById('apd-filter-apo')||{}).value||'');
        var eD=parseDate((document.getElementById('apd-filter-eos')||{}).value||'');
        var pctVal=parseFloat((document.getElementById('apd-filter-pct')||{}).value||'18')/100;
        var mode=(document.getElementById('apd-filter-mode')||{}).value||'all';
        var hl=parseFloat((document.getElementById('apd-highlight')||{}).value||'21');
        var n=0;
        rows.forEach(function(tr){
          var isTotal=tr.getAttribute('data-is-total')==='1';
          if(isTotal){tr.style.display='';return;}
          var ok=true;
          ['tameio','typos','pkg','earn'].forEach(function(a){
            if(sel[a]&&sel[a].length>0&&sel[a].indexOf((tr.getAttribute('data-'+a)||'').trim())===-1)ok=false;
          });
          if(ok&&aD){var rA=parseDate((tr.getAttribute('data-apo')||'').trim());if(rA&&rA<aD)ok=false;}
          if(ok&&eD){var rA2=parseDate((tr.getAttribute('data-apo')||'').trim());if(rA2&&rA2>eD)ok=false;}
          if(ok&&mode!=='all'){
            var ret=parseFloat(tr.getAttribute('data-retention')||'0')/100;
            if(mode==='gte'&&ret<pctVal)ok=false;
            if(mode==='lt'&&ret>=pctVal)ok=false;
          }
          tr.style.display=ok?'':'none';
          if(ok){
            n++;
            var rv=parseFloat(tr.getAttribute('data-retention')||'0');
            tr.style.backgroundColor=(rv>0&&rv<hl)?'#fef2f2':'';
          }
        });
        var el=document.getElementById('apd-count');if(el)el.textContent=n+' γραμμές';
      }
      document.querySelectorAll('#apd-filters input, #apd-filters select').forEach(function(i){i.addEventListener('change',apply);i.addEventListener('input',apply);});
      """ + _filters_js_boilerplate('apd-filters') + """
      apply();
    })();
    """

    info_bar = (
        f'<div class="totals-info-bar" style="margin-bottom:12px;">'
        f'<div class="totals-info-msg">Καθεστώς: {_esc(status_msg)}</div>'
        f'<div id="apd-count" style="font-size:14px;color:#64748b;">{len(out_rows)} γραμμές</div>'
        f'<div style="font-size:12px;color:#64748b;">Εξαιρούνται: {_esc(EXCLUDED_PACKAGES_LABEL)}</div>'
        f'</div>'
    )

    return (
        f"<section class='print-section'><h2>Ανάλυση ΑΠΔ</h2>"
        f"<p class='print-description'>Ανάλυση πλαφόν ΙΚΑ, περικοπής και ποσοστού κράτησης. "
        f"Κόκκινη επισήμανση σε χαμηλό % κράτησης.</p>"
        f"{info_bar}{filters_html}"
        f"<table class='print-table' id='apd-table'><thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(tbody_parts)}</tbody></table>"
        f"<script>{js}</script></section>"
    )


def _fmtd_inline(v):
    if v is None or v == '' or v == 0 or (isinstance(v, float) and pd.isna(v)):
        return ''
    try:
        x = float(v)
        return str(int(round(x))) if abs(x - round(x)) < 0.01 else f"{x:.1f}".replace('.', ',')
    except:
        return _esc(v)

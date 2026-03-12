# Αναλυτική αναφορά: Διαφορές στις δύο παραγωγές HTML (Κύρια vs Lite)

## 1. Πηγή και πλαίσιο

| | **Κύρια (app_final)** | **Lite (app_lite)** |
|---|---|---|
| **Παραγωγή HTML** | `html_viewer_builder.generate_full_html_report(df, client_name=...)` | Ενσωματωμένα: `_build_report_block()` + δικό της viewer/print template |
| **Κλήση** | Μία φορά μετά την επεξεργασία (κουμπί "Γρήγορη Προβολή - Lite" ή αντίστοιχο) | Μετά την επεξεργασία, όταν ο χρήστης επιλέγει "Προβολή αναφοράς" / "Άμεση εκτύπωση" |

---

## 2. Ονοματεπώνυμο (client name)

| Στοιχείο | **Κύρια** | **Lite** |
|----------|-----------|----------|
| **Πηγή τιμής** | `st.session_state.get('client_name', '')` (στην κλήση του `generate_full_html_report`). Στην ίδια εφαρμογή υπάρχει πεδίο "Ονοματεπώνυμο ασφαλισμένου" με key `print_client_name` (δεν περνά απευθείας στο report). | Ρητό πεδίο **"Ονοματεπώνυμο:"** (`st.text_input`) με key `client_input`, αποθήκευση στο `st.session_state["lite_client_name"]`. Εμφανίζεται πάνω από τα κουμπιά προβολής/εκτύπωσης. |
| **Στο viewer HTML** | Εάν `client_name` μη κενό: `<div class="header-name">…</div>` πάνω από "Ασφαλιστικό Βιογραφικό". | Ίδιο: `header-name` με το `client_name` από session. |
| **Στο print HTML** | Εάν μη κενό: `<div class='prt-name'>…</div>` στην κορυφή του body. | Ίδιο. |
| **Στο single-section print (JS)** | `buildSinglePrintDoc`: τίτλος `name + ' - ' + title + ' - Atlas'`, και στο body `prt-name` αν υπάρχει name. | Ίδιο μηχάνημα, αλλά τίτλος: `name + ' - ' + title + ' - Atlas Lite'` (με "Atlas Lite"). |

**Συμπέρασμα:** Στη Lite το ονοματεπώνυμο είναι **εκτενώς προαναφερόμενο** και **πάντα διαθέσιμο** μέσω του πεδίου "Ονοματεπώνυμο:". Στην κύρια η τιμή που περνά στο report έρχεται από `client_name` (session), όχι απευθείας από το "Ονοματεπώνυμο ασφαλισμένου" (`print_client_name`).

---

## 3. Footer / Disclaimer

### 3.1 Στη σελίδα Streamlit (έξω από το exported HTML)

| | **Κύρια** | **Lite** |
|---|-----------|----------|
| **Κείμενο** | **ΑΠΟΠΟΙΗΣΗ ΕΥΘΥΝΗΣ:** Η παρούσα εφαρμογή αποτελεί εργαλείο ιδιωτικής πρωτοβουλίας… Δεν συνδέεται με τον e-ΕΦΚΑ… Για επίσημη πληροφόρηση… e-ΕΦΚΑ. | **Ακριβώς το ίδιο** κείμενο αποποίησης. |
| **Copyright** | `© 2026 Χαράλαμπος Ματωνάκης - myadvisor` | `© 2026 Χαράλαμπος Ματωνάκης - myadvisor` |
| **Στοιχεία** | `main-footer`, `footer-disclaimer`, `footer-copyright` | Ίδια δομή και κλάσεις. |

Δεν υπάρχει διαφορά στο περιεχόμενο ή τη δομή του footer της Streamlit σελίδας μεταξύ κύριας και Lite.

### 3.2 Μέσα στο exported HTML (viewer + print)

| Θέση | **Κύρια (html_viewer_builder)** | **Lite (app_lite)** |
|------|----------------------------------|----------------------|
| **Περιεχόμενο disclaimer** | `get_print_disclaimer_html()` από `app_final`: **"ΣΗΜΑΝΤΙΚH ΣΗΜΕΙΩΣΗ:"** – βασίζεται στα δεδομένα ΑΤΛΑΣ/e-ΕΦΚΑ, απλή επεξεργασία, δεν υποκαθιστά νομική/οικονομική συμβουλή, για συνταξιοδότηση αρμόδιος ο e-ΕΦΚΑ. | **Το ίδιο** – κλήση `get_print_disclaimer_html()`. |
| **Τοποθέτηση στο viewer** | Μέσα στο `<main class="main-content">`: μετά τα tab panes, απευθείας `{disclaimer}`. | Μέσα στο `<main>`: περιεχόμενο μέσα σε `<div class="main-content-scroll">`, και **κάτω** ξεχωριστό `<div class="main-footer-disclaimer">{disclaimer}</div>`. |
| **Στυλ disclaimer (.print-disclaimer)** | Στο VIEWER_STYLES: `font-size: 12px; color: #64748b; margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0`. | Ίδιο (12px, χρώμα, border-top). |
| **Copyright μέσα στο document** | Sidebar: `© Syntaksi Pro - my advisor`. Τέλος print body: `<div style="...">© Syntaksi Pro - my advisor</div>`. | **Ίδιο** – sidebar και τέλος print body: "© Syntaksi Pro - my advisor". |

**Συμπέρασμα:** Μέσα στο exported HTML το **κείμενο** του disclaimer είναι **ίδιο** (ΣΗΜΑΝΤΙΚΗ ΣΗΜΕΙΩΣΗ). Το **copyright** στο sidebar και στο τέλος της εκτύπωσης είναι και στις δύο **"© Syntaksi Pro - my advisor"**. Η μόνη δομική διαφορά είναι ότι στη Lite το disclaimer είναι μέσα σε `main-footer-disclaimer` κάτω από το scrollable περιεχόμενο.

---

## 4. Τίτλοι και branding

| Στοιχείο | **Κύρια** | **Lite** |
|----------|-----------|----------|
| **Title (head)** | `{app_title} - {app_subtitle}` → π.χ. "ATLAS - Ασφαλιστικό Βιογραφικό" | `ATLAS Lite - Προεργασία φακέλου` (σταθερό). |
| **Sidebar header** | `{app_title}` + `<small>{app_subtitle}</small>` → "ATLAS" + "Ασφαλιστικό Βιογραφικό" | `ATLAS lite` + `<small>Προεργασία φακέτου</small>`. |
| **Print document title** | `ATLAS - Εκτύπωση` | `ATLAS Lite - Εκτύπωση`. |
| **Τίτλος σε single-section print (JS)** | `… + 'Atlas'` | `… + 'Atlas Lite'`. |
| **Αρχείο λήψης (suggested)** | `{client_name or "Αναφορά"} - ATLAS.html` (από `generate_full_html_report`) | `{client_value or "Αναφορά"} - Atlas Lite.html`. |

---

## 5. Δομή viewer (layout / DOM)

| | **Κύρια** | **Lite** |
|---|-----------|----------|
| **Main content** | `<main class="main-content">` → απευθείας `{name_block}`, `main-title`, `{tab_panes}`, `{disclaimer}`. | `<main class="main-content">` → `<div class="main-content-scroll">` με name_block, main-title, `tab-panes-container` και tab panes· έξω από το scroll: `main-footer-disclaimer`. |
| **Scroll** | Το main-content κάνει scroll ως ένα block (αν χρειάζεται). | Ξεχωριστό scroll στο `tab-panes-container` (overflow-y: auto) ώστε το disclaimer να μένει κάτω. |
| **Καρτέλα Καταμέτρηση** | Κανονικά tab panes. | Ειδική κλάση `count-tab-active` στο main (κρύβει το global main-footer-disclaimer όταν είναι ανοιχτή η Καταμέτρηση). |

---

## 6. Περιεχόμενο tabs (τι μπαίνει μέσα)

| | **Κύρια** | **Lite** |
|----------|-----------|----------|
| **Πηγή tab entries** | `html_viewer_builder.build_report_tab_entries(df, description_map)` | Ενσωματωμένο `_build_report_block()` στο app_lite – χρήση `_build_totals_with_filters`, `_build_count_with_filters` (από html_viewer_builder) και build_print_section_html κλπ. |
| **Σύνοψη** | Πίνακας audit (audit_df) + clickable cards. | Ίδιος τρόπος (audit_df, cards). |
| **Ιστορικό** | `build_timeline_html(df)` (html_viewer_builder). | `_build_timeline_html(df)` (ορισμένο στο app_lite). |
| **Σύνολα** | `build_totals_with_filters(display_summary, raw_df=df, ...)` (html_viewer_builder). | `_build_totals_with_filters(...)` (ορισμένο στο app_lite, με _totals_raw_records_for_js που περιλαμβάνει g/c). |
| **Καταμέτρηση** | `build_count_with_filters(...)` (html_viewer_builder). | `_build_count_with_filters(...)` (html_viewer_builder). |
| **Άλλα tabs** | Κενά, Παράλληλη, Παράλληλη 2017+, Πολλαπλή (αν υπάρχουν δεδομένα). | Ίδια θέματα. |
| **Σημείωση περίπλοκου αρχείου** | Μπορεί να εμφανίζεται ανάλογα με metrics. | Ίδιο + `COMPLEX_FILE_WARNING_HTML` προπομπή σε όλα τα tab contents αν `show_complex_warning`. |
| **Εξαίρεση πακέτων (Καταμέτρηση)** | `EXCLUSION_NOTE_HTML` (html_viewer_builder). | `LITE_EXCLUSION_NOTE` (ίδιο νόημα, ίδιο styling περίπου). |

---

## 7. Print document (συνολική εκτύπωση / Πλήρης Αποθήκευση)

| | **Κύρια** | **Lite** |
|----------|-----------|----------|
| **Συναρμολόγηση** | `build_print_html_document(tab_entries, audit_df, display_summary, client_name)` → Σύνοψη (πίνακας), Σύνολα (display_summary), υπόλοιπα tabs. | Χειροκίνητα: `synopsis_print`, `totals_print` (από display_summary), `rest_for_print` από tab_entries. Ίδια σειρά. |
| **Στυλ εκτύπωσης** | `PRINT_STYLES` (html_viewer_builder). | Ενσωματωμένο string `print_styles_content` στο app_lite (παράγωγο των PRINT_STYLES, με επιπλέον κανόνες π.χ. `.lite-exclusion-note`, `.count-filters { display: none }`). |
| **Ονοματεπώνυμο** | `prt-name` αν υπάρχει client_name. | Ίδιο. |
| **Disclaimer** | `get_print_disclaimer_html()` στο τέλος του body. | Ίδιο. |
| **Τελευταία γραμμή** | `© Syntaksi Pro - my advisor`. | Ίδιο. |

---

## 8. Σύνοψη διαφορών (checklist)

1. **Ονοματεπώνυμο**
   - **Lite:** Ρητό πεδίο "Ονοματεπώνυμο:" και χρήση του παντού στο exported HTML.
   - **Κύρια:** Χρήση `client_name` από session (όχι απευθείας από το πεδίο "Ονοματεπώνυμο ασφαλισμένου").

2. **Footer / disclaimer**
   - **Στη Streamlit σελίδα:** Ίδιο κείμενο (ΑΠΟΠΟΙΗΣΗ ΕΥΘΥΝΗΣ) και ίδιο copyright (© 2026 Χαράλαμπος Ματωνάκης - myadvisor) και στις δύο.
   - **Μέσα στο exported HTML:** Ίδιο κείμενο disclaimer (ΣΗΜΑΝΤΙΚΗ ΣΗΜΕΙΩΣΗ) και ίδιο copyright (© Syntaksi Pro - my advisor). Διαφορά μόνο στη δομή: Lite χρησιμοποιεί `main-footer-disclaimer` και ξεχωριστό scroll.

3. **Branding**
   - Κύρια: "ATLAS", "Ασφαλιστικό Βιογραφικό", "Atlas" στα print.
   - Lite: "ATLAS Lite", "Προεργασία φακέλου", "Atlas Lite" στα print και στο suggested filename.

4. **Layout viewer**
   - Lite: `main-content-scroll` + `tab-panes-container` με overflow-y και `main-footer-disclaimer` έξω από το scroll· ειδική συμπεριφορά για την καρτέλα Καταμέτρηση.

5. **Περιεχόμενο tabs**
   - Λογική ίδια· Σύνολα/Καταμέτρηση στη Lite χρησιμοποιούν τις δικές της συναρτήσεις (_build_totals_with_filters με g/c στα raw records). Lite προ prependάρει προειδοποίηση περίπλοκου αρχείου σε όλα τα tabs όταν χρειάζεται.

6. **Print styles**
   - Κύρια: ένα σύνολο PRINT_STYLES.
   - Lite: δικό της print styles string με επιπλέον κανόνες για Lite-specific στοιχεία.

---

*Αναφορά συγκρίσεως παραγωγής HTML: Κύρια εφαρμογή (app_final + html_viewer_builder) vs ATLAS Lite (app_lite).*

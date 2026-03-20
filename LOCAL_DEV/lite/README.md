# LOCAL DEV — ATLAS Lite (αυτόνομη εφαρμογή)

**Στάδιο:** Τοπική ανάπτυξη / δοκιμή της **Lite** (ξεχωριστό Streamlit app από την Κυρία).

## Πώς «φτιάχνεται» η Lite (αρχή του repo)

**Η Lite δεν γράφεται ως ξεχωριστό project από το μηδέν.** Πάντα προκύπτει από **αντιγραφή / παραγωγή από την Κυρία** (`LOCAL_DEV/kyria/app_final.py`) και **συγκεκριμένες, σταθερές αλλαγές** που εφαρμόζει το script:

```bash
python scripts/build_lite_from_kyria.py
```

→ εξόδου: **`LOCAL_DEV/lite/app_lite.py`**.

Μετά το script, **μόνο αν χρειάζεται**: ελάχιστες χειροκίνητες διορθώσεις (σπάνιο). Η κανονική ροή είναι: αλλάζεις την **Κυρία** → ξανατρέχεις το script → δοκιμάζεις τη Lite.

### Τι αλλάζει αυτόματα (σύνοψη — λεπτομέρειες στο `scripts/build_lite_from_kyria.py`)

1. **Αφαίρεση** ολόκληρης της `show_results_page` (και του ενδιάμεσου κώδικα μέχρι το `main()`).
2. **Docstring / branding:** Lite description, `page_title` Streamlit **«ATLAS Lite»**, header **«ATLAS Lite»**.
3. **Όχι** `show_results` στο `session_state`· **αφαίρεση** του μπλοκ Streamlit «Προβολή Αποτελεσμάτων» (tabs/πίνακες)· αντικατάσταση με **ένα** κουμπί **«Άνοιγμα / Προβολή»** (HTML).
4. **Τίτλος αναφοράς HTML:** `_app_title = "ATLAS Lite"`, κενό subtitle όπου ορίζεται στο script.
5. **`generate_full_html_report`:** `full_save_suffix="ATLAS_Lite.html"` για προεπιλεγμένο όνομα αποθήκευσης.
6. **Καθαρισμός κλειδιών session** στο reset: χωρίς `show_results`.

- **Δεν** χρησιμοποιεί `ATLAS_MODE` / `IS_LITE`· δύο entrypoints (`app_final.py` / `app_lite.py`).
- **Κοινά modules** με την Κυρία στη **ρίζα** (`html_viewer_builder.py`, κ.λπ.) — ίδια γραμμή παραγωγής HTML, με τις διαφορές που ορίζει η κλήση (Lite branding / suffix).

## Εκτέλεση

Από τη **ρίζα** του repo:

```bash
streamlit run LOCAL_DEV/lite/app_lite.py --server.port 8502
```

## Συγχρονισμός με την Κυρία (υποχρεωτική ρουτίνα μετά από αλλαγές στην Κυρία)

```bash
python scripts/build_lite_from_kyria.py
```

Αν αλλάξουν τα **σημεία τομής** στην Κυρία (π.χ. ονόματα συναρτήσεων, markers `# Εμφάνιση αποτελεσμάτων`, κουμπιά), το script μπορεί να αποτύχει — τότε ενημερώνεις **`build_lite_from_kyria.py`** ώστε να παραμένει «αντιγραφή Κυρίας + συγκεκριμένες αλλαγές».

## Ροή Git

1. Αλλαγές → δοκιμή τοπικά.
2. Push branch `test` → δες [`../../TEST/README.md`](../../TEST/README.md).
3. Merge στο `main` → [`../../MAIN/lite/README.md`](../../MAIN/lite/README.md).

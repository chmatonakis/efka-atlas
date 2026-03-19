# LOCAL DEV — ATLAS Lite (αυτόνομη εφαρμογή)

**Στάδιο:** Τοπική ανάπτυξη / δοκιμή της **Lite** (ξεχωριστό Streamlit app από την Κυρία).

## Τι είναι η Lite εδώ

- **Δεν** χρησιμοποιεί `ATLAS_MODE` ούτε import από την Κυρία· πλήρες `app_lite.py` στον φάκελο αυτόν.
- **Όχι** ενσωματωμένη Streamlit σελίδα «Προβολή Αποτελεσμάτων» (πίνακες/tabs όπως στην Κυρία).
- Μετά την επεξεργασία PDF: **ένα** κουμπί **«Άνοιγμα / Προβολή»** → HTML αναφορά (ίδιο `html_viewer_builder`).
- Μωβ header και branding HTML / αποθήκευση / εκτύπωση: **ATLAS Lite**.

## Εκτέλεση

Από τη **ρίζα** του repo:

```bash
streamlit run LOCAL_DEV/lite/app_lite.py --server.port 8502
```

## Συγχρονισμός με την Κυρία

Όταν αλλάζετε λογική στην **`LOCAL_DEV/kyria/app_final.py`**, ξανατρέξτε:

```bash
python scripts/build_lite_from_kyria.py
```

Έτσι ανανεώνεται το `app_lite.py` (αφαιρείται ξανά το τμήμα `show_results_page` και εφαρμόζονται οι ρυθμίσεις Lite). Ελέγξτε χειροκίνητα αν χρειάστηκαν αλλαγές εκτός του `main()`.

## Ροή Git

1. Αλλαγές → δοκιμή τοπικά.
2. Push branch `test` → δες [`../../TEST/README.md`](../../TEST/README.md).
3. Merge στο `main` → [`../../MAIN/lite/README.md`](../../MAIN/lite/README.md).

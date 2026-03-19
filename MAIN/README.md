# MAIN — production (branch `main`)

**Στάδιο:** Αντιστοιχεί στο τι είναι στο branch **`main`** στο GitHub· live για όλους (production).

Υποφάκελοι:

- **kyria/** — Κύρια εφαρμογή ([`kyria/README.md`](kyria/README.md))
- **lite/** — Lite εφαρμογή ([`lite/README.md`](lite/README.md))

## Σημαντικό

Ο **πηγαίος κώδικας** για τοπική ανάπτυξη είναι στο **`LOCAL_DEV/`**. Ο φάκελος `MAIN/` περιέχει **τεκμηρίωση σταδίου production** και σύνδεση με deploy· όχι αντικατάσταση του `LOCAL_DEV`.

## Ροή

Μετά από επιτυχή δοκιμή στο `TEST` → merge `test` → `main` → ανανέωση production apps.

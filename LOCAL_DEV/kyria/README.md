# LOCAL DEV – Κύρια εφαρμογή (τοπική ανάπτυξη)

**Στάδιο:** Τρέχει τοπικά· εδώ γίνονται οι αλλαγές πριν ανέβουν στο test/main.

- **Εφαρμογή:** Κύρια ATLAS
- **Εκτέλεση:** από root του repo:
  ```bash
  streamlit run LOCAL_DEV/kyria/app_final.py --server.port 8501
  ```
- **Branch:** συνήθως `test` (ανάπτυξη) ή `main` (sync)

## Σχετικά αρχεία

- `app_final.py` – κύρια εφαρμογή (σε αυτόν τον φάκελο)
- Στη **ρίζα repo:** `html_viewer_builder.py`, `html_extra_tabs.py`, `frontend_atlas/`, κ.ά.

## Ροή

1. Κάνε αλλαγές στο repo (branch test).
2. Δοκίμασε τοπικά με την παραπάνω εντολή.
3. Όταν είσαι έτοιμος → push στο `test` (φάκελος τεκμηρίωσης: `TEST/`).

# TEST — Κύρια εφαρμογή (δοκιμή)

**Στάδιο:** Branch **`test`** στο GitHub· live δοκιμή πριν το `main`.

- **Εφαρμογή:** Κύρια ATLAS (e-EFKA PDF)
- **Τοπική εκτέλεση (ανάπτυξη):** από ρίζα repo  
  `streamlit run LOCAL_DEV/kyria/app_final.py --server.port 8501`
- **Git:** `git push origin test`

## Ροή

1. Αλλαγές στο **`LOCAL_DEV/kyria/`** (και κοινά modules στη ρίζα).
2. Push στο `test` → test Streamlit.
3. OK → merge στο `main` ([`../../docs/GIT_WORKFLOW_TEST_TO_MAIN.md`](../../docs/GIT_WORKFLOW_TEST_TO_MAIN.md)).

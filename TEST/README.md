# TEST — δοκιμή (branch `test`)

**Στάδιο:** Αντιστοιχεί στο τι έχει ανέβει στο branch **`test`** στο GitHub· live δοκιμή από περιορισμένο κοινό πριν το production.

Υποφάκελοι (ίδια λογική με `LOCAL_DEV` και `MAIN`):

- **kyria/** — Κύρια εφαρμογή (οδηγίες: [`kyria/README.md`](kyria/README.md))
- **lite/** — Lite εφαρμογή (οδηγίες: [`lite/README.md`](lite/README.md))

## Σημαντικό

Ο **πηγαίος κώδικας** των Streamlit apps παραμένει στο **`LOCAL_DEV/`**. Ο φάκελος `TEST/` περιέχει **τεκμηρίωση σταδίου** και ροή deploy· δεν αντικαθιστά το `LOCAL_DEV` για τοπική ανάπτυξη.

## Ροή

1. Αλλαγές στο `LOCAL_DEV` → commit στο branch `test`.
2. `git push origin test` → Streamlit / Snowflake test apps.
3. Έλεγχος OK → merge `test` → `main` (δες [`../docs/GIT_WORKFLOW_TEST_TO_MAIN.md`](../docs/GIT_WORKFLOW_TEST_TO_MAIN.md)).

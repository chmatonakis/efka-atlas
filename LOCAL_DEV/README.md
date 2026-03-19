# LOCAL_DEV — τοπική ανάπτυξη

**Στάδιο:** Εδώ γράφεται και τρέχει ο κώδικας πριν το push στο GitHub.

Δύο υποέργα (ίδια δομή με `TEST/` και `MAIN/`):

| Φάκελος | Εφαρμογή | Τοπική εκτέλεση (από ρίζα repo) |
|---------|----------|----------------------------------|
| **kyria/** | Κύρια ATLAS | `streamlit run LOCAL_DEV/kyria/app_final.py --server.port 8501` |
| **lite/** | ATLAS Lite | `streamlit run LOCAL_DEV/lite/app_lite.py --server.port 8502` |

**Κοινά modules** (ρίζα repo): `html_viewer_builder.py`, `html_extra_tabs.py`, `requirements.txt`, `frontend_atlas/`, κ.λπ.

## Ροή staging

```
LOCAL_DEV  →  push branch test   →  TEST (δοκιμή)
       →  merge test → main     →  MAIN (production)
```

Λεπτομέρειες: [`../TEST/README.md`](../TEST/README.md), [`../MAIN/README.md`](../MAIN/README.md), [`../README.md`](../README.md).

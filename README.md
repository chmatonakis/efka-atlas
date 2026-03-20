# 📄 Ασφαλιστικό βιογραφικό ΑΤΛΑΣ

Εφαρμογή για την ανάλυση και επεξεργασία PDF αρχείων από το e-EFKA.

## 🚀 Χαρακτηριστικά

- 📊 Ανάλυση δεδομένων e-EFKA
- 📈 Συνοπτικές και ετήσιες αναφορές
- 📅 Αναφορά ημερών ασφάλισης
- 🖨️ Δυνατότητες εκτύπωσης
- 💾 Export σε Excel
- 🔍 Προηγμένα φίλτρα

## 📁 Δομή project

- **LOCAL_DEV/** – τοπική ανάπτυξη· δύο υποέργα **`kyria/`** και **`lite/`** (κώδικας Streamlit). Επισκόπηση: [`LOCAL_DEV/README.md`](LOCAL_DEV/README.md).
- **TEST/** – τεκμηρίωση σταδίου **branch `test`** (δοκιμή πριν το production)· υποφάκελοι `kyria/`, `lite/`. Δες [`TEST/README.md`](TEST/README.md).
- **MAIN/** – τεκμηρίωση σταδίου **branch `main`** (production)· υποφάκελοι `kyria/`, `lite/`. Δες [`MAIN/README.md`](MAIN/README.md).
- **docs/** – τεκμηρίωση, οδηγοί, PDF/έγγραφα δοκιμών.
- **dev_html/** – προσχέδια εξαγόμενου HTML για βελτιώσεις πριν τη μεταφορά στον παραγωγικό κώδικα· δες [`dev_html/ATLAS_DEV_2/README.md`](dev_html/ATLAS_DEV_2/README.md).
- **scripts/** – βοηθητικά scripts (π.χ. `install_ghostscript.bat`).
- Στη **ρίζα**: κοινά modules (`html_viewer_builder.py`, `html_extra_tabs.py`, `report_json_export.py`), `frontend_atlas/`, `requirements.txt`, `run_app.bat`.

### Σταδιοποίηση (ίδια δομή `kyria` + `lite` παντού)

```
LOCAL_DEV  →  git: branch test   →  TEST (εννοείται το ίδιο repo / deploy targets)
         →  git: branch main    →  MAIN (production)
```

| Φάκελος | Git branch (τυπικά) | Ρόλος |
|---------|---------------------|--------|
| **LOCAL_DEV/** | `test` ή feature | Εδώ γράφεται ο κώδικας· εκτέλεση Streamlit από εδώ. |
| **TEST/** | `test` | Οδηγίες / σημείο αναφοράς για δοκιμαστικό deploy. |
| **MAIN/** | `main` | Οδηγίες / σημείο αναφοράς για production deploy. |

Οι εφαρμογές τρέχουν **τοπικά** από **LOCAL_DEV**: `LOCAL_DEV/kyria/app_final.py` (κύρια), `LOCAL_DEV/lite/app_lite.py` (lite). Τα κοινά modules παραμένουν στη **ρίζα**. Κάθε στάδιο έχει README (ρίζα `LOCAL_DEV/`, `TEST/`, `MAIN/` και ανά `kyria`/`lite` όπου χρειάζεται).

> **Σημείωση:** Ο φάκελος **`TEST_LIVE/`** μετονομάστηκε σε **`TEST/`** για ευθυγράμμιση με το staging (test vs main).

## 💻 Τοπική εκτέλεση

Από τη **ρίζα του repo** (ώστε να λειτουργούν τα paths):

```bash
pip install -r requirements.txt
# Κύρια εφαρμογή (port 8501)
streamlit run LOCAL_DEV/kyria/app_final.py --server.port 8501
# Lite (port 8502)
streamlit run LOCAL_DEV/lite/app_lite.py --server.port 8502
```

## 🌐 Live Demo

Διαθέσιμο στο: [Streamlit Cloud URL]

## 📝 Changelog

### v1.0.1
- ✅ Git integration ολοκληρώθηκε
- ✅ Αυτόματο deployment workflow ενεργοποιημένο

### v1.0.0
- Αρχική έκδοση με πλήρη λειτουργικότητα
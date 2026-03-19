# Δημιουργία 2 live εφαρμογών για ΤΕΣΤ

Έτσι μπορείς να δοκιμάζεις αλλαγές χωρίς να επηρεάζονται οι **επίσημες** εφαρμογές.

---

## Σημαντικό: ίδιο repo = ίδιος κώδικας, εκτός αν χρησιμοποιήσεις διαφορετικό branch

Αν **όλες** οι εφαρμογές (επίσημες + test) δείχνουν στο **ίδιο branch** (π.χ. `main`), τότε **κάθε push ενημερώνει όλες**. Δεν υπάρχει διαχωρισμός κώδικα.

**Λύση:** Οι **test** εφαρμογές να τραβούν από **διαφορετικό branch** (π.χ. `test` ή `staging`). Έτσι:

- **Επίσημες εφαρμογές** → branch **`main`** (ανεβαίνει μόνο κώδικας που έχει ελεγχτεί).
- **Test εφαρμογές** → branch **`test`** (ανεβαίζεις εδώ πρώτα, δοκιμάζεις, μετά κάνεις merge στο `main`).

Ροή εργασίας: αλλαγές → push στο `test` → δοκιμή στα test URLs → αν όλα καλά, merge `test` → `main` → ενημερώνονται μόνο οι επίσημες.

---

## 1. Streamlit Community Cloud (share.streamlit.io)

### Βήμα 0: Δημιουργία branch για τεστ (μία φορά)

```bash
git checkout -b test
git push -u origin test
```

### Βήμα 1: Δημιουργία των 2 test εφαρμογών

1. Πήγαινε στο **https://share.streamlit.io** και κάνε sign in με GitHub.
2. **Νέα εφαρμογή #1 (ATLAS Test – κύρια):**
   - **New app** → Repository: `chmatonakis/efka-atlas` (ή το repo σου)
   - **Branch: `test`** ← σημαντικό, όχι `main`
   - **Main file path:** `app_final.py`
   - **App URL:** π.χ. `atlas-test`
   - Όνομα: "ATLAS Test".
3. **Νέα εφαρμογή #2 (ATLAS Lite Test):**
   - Ξανά **New app** → ίδιο repository
   - **Branch: `test`**
   - **Main file path:** `app_lite.py`
   - **App URL:** π.χ. `atlas-lite-test`
   - Όνομα: "ATLAS Lite Test".
   - **Εξαρτήσεις:** Στο **Advanced settings** άστε το αρχείο εξαρτήσεων στο προεπιλεγμένο (ή ρητά `requirements.txt` στη **ρίζα** του repo). Αν εμφανιστεί `No module named 'pdfplumber'`, το Cloud δεν διάβασε/δεν εγκατέστησε το `requirements.txt` — έλεγξε το path, κάνε **Reboot** ή νέο deploy μετά από push.

### Βήμα 2: Επίσημες εφαρμογές

Βεβαιώσου ότι οι **υπάρχουσες** επίσημες εφαρμογές έχουν **Branch: `main`**. Έτσι ενημερώνονται μόνο όταν κάνεις merge στο `main`.

### Ροή εργασίας

| Θέλεις να…        | Κάνεις…                    | Επηρεάζονται…     |
|-------------------|----------------------------|--------------------|
| Δοκιμάσεις νέο   | Push στο `test`            | Μόνο test apps     |
| Να πάνε live      | Merge `test` → `main`      | Επίσημες εφαρμογές |

---

## 2. Snowflake (Streamlit στο Snowflake)

Στο **snowflake.yml** υπάρχουν δύο νέες εφαρμογές (ATLAS_APP_TEST, ATLAS_LITE_TEST). Στο Snowflake ο διαχωρισμός γίνεται με **από ποιο branch/project κάνεις deploy**:

- **Επίσημες (ATLAS_APP):** deploy όταν είσαι στο branch **`main`** (ή αφού κάνεις merge).
- **Test (ATLAS_APP_TEST, ATLAS_LITE_TEST):** deploy όταν είσαι στο branch **`test`** (ή `staging`).

Δηλαδή: κάνεις checkout στο `test`, κάνεις τις αλλαγές σου, deploy (Snowflake CLI/UI) → ενημερώνονται μόνο οι test εφαρμογές. Όταν είσαι έτοιμος, merge στο `main`, checkout `main`, deploy → ενημερώνονται οι επίσημες.

(Αν το deploy στο Snowflake τραβάει πάντα από ένα branch, ρύθμισε το ώστε τα test apps να τραβούν από το `test` branch, αν η πλατφόρμα το υποστηρίζει.)

---

## 3. Σύνοψη

- **Ίδιο repo + ίδιο branch** → όλες οι εφαρμογές τρέχουν τον ίδιο κώδικα· κάθε push επηρεάζει όλες.
- **Ίδιο repo + διαφορετικό branch για test** → οι test εφαρμογές τρέχουν κώδικα από το `test`, οι επίσημες από το `main`. Επηρεάζονται μόνο όταν αλλάζεις το branch από το οποίο τραβάνε ή κάνεις merge.

Έτσι οι επίσημες εφαρμογές **δεν** επηρεάζονται μέχρι να εντάξεις τις αλλαγές στο `main`.

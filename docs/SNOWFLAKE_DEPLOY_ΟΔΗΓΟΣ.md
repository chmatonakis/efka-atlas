# Ανέβασμα Κύριας Εφαρμογής (ATLAS) στο Snowflake – Βήμα προς Βήμα

Στόχος: να τρέχει η **κύρια** εφαρμογή (`app_final.py`) και στο **Streamlit Community Cloud** (όπως τώρα) και στο **Streamlit in Snowflake**, και να ενημερώνεις και τα δύο με τον ίδιο τρόπο (push στο GitHub).

---

## Μέρος 1: Προετοιμασία στο Snowflake (μία φορά)

### Βήμα 1.1 – Warehouse και Stage

1. Μπες στο **Snowsight** (https://app.snowflake.com).
2. Άνοιξε **Worksheets** και τρέξε (προσάρμοσε `MY_WAREHOUSE`, `MY_DB`, `MY_SCHEMA` αν χρειάζεται):

```sql
CREATE WAREHOUSE IF NOT EXISTS MY_WAREHOUSE
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

CREATE DATABASE IF NOT EXISTS MY_DB;
CREATE SCHEMA IF NOT EXISTS MY_DB.MY_SCHEMA;

CREATE STAGE IF NOT EXISTS MY_DB.MY_SCHEMA.ATLAS_STAGE
  FILE_FORMAT = (TYPE = 'PYTHON_SOURCE');
```

3. Δώσε δικαιώματα στο role σου (αν χρειάζεται):

```sql
GRANT USAGE ON WAREHOUSE MY_WAREHOUSE TO ROLE YOUR_ROLE;
GRANT USAGE ON DATABASE MY_DB TO ROLE YOUR_ROLE;
GRANT USAGE ON SCHEMA MY_DB.MY_SCHEMA TO ROLE YOUR_ROLE;
GRANT CREATE STREAMLIT ON SCHEMA MY_DB.MY_SCHEMA TO ROLE YOUR_ROLE;
GRANT READ ON STAGE MY_DB.MY_SCHEMA.ATLAS_STAGE TO ROLE YOUR_ROLE;
```

---

### Βήμα 1.2 – Εγκατάσταση Snowflake CLI (στο PC σου)

1. Άνοιξε PowerShell ή Command Prompt.
2. Εγκατάσταση (με pip):

```powershell
pip install snowflake-cli
```

3. Σύνδεση με το λογαριασμό σου:

```powershell
cd c:\ATLAS
snow login
```

Ακολούθησε τις οδηγίες (browser, account, user, password). Μετά το login, το CLI θυμάται τη σύνδεση.

---

### Βήμα 1.3 – Ρύθμιση project για Streamlit (στο repo σου)

Στο φάκελο `c:\ATLAS` υπάρχουν:

- **snowflake.yml** – ορισμός Streamlit app (main file, warehouse, stage). Άνοιξέ το και **πρόσαρμοσε** τις τιμές ώστε να ταιριάζουν με το Βήμα 1.1:
  - `query_warehouse`: το όνομα του warehouse (π.χ. `MY_WAREHOUSE`).
  - `stage`: το stage όπου θα ανέβουν τα αρχεία. Για full path: `MY_DB.MY_SCHEMA.ATLAS_STAGE`, ή μόνο `ATLAS_STAGE` αν το connection στο CLI ορίζει ήδη database/schema.
- **environment.yml** – πακέτα για Warehouse runtime (όσα υπάρχουν στο Anaconda channel).

---

## Μέρος 2: Πρώτο ανέβασμα της κύριας εφαρμογής

### Βήμα 2.1 – Deploy από το PC σου

1. Άνοιξε terminal στο `c:\ATLAS`:

```powershell
cd c:\ATLAS
```

2. Deploy της Streamlit εφαρμογής:

```powershell
snow streamlit deploy --replace
```

3. Αν ρωτήσει για options (π.χ. project/entity), διάλεξε το streamlit app που ορίζεται στο `snowflake.yml`.

4. Άνοιγμα της εφαρμογής στο browser (αν θέλεις):

```powershell
snow streamlit get-url
```

Αντιγράφεις το URL και το ανοίγεις στο browser. Εναλλακτικά, από Snowsight: **Projects → Streamlit** και άνοιγμα της εφαρμογής από εκεί.

---

### Βήμα 2.2 – Έλεγχος dependencies (Warehouse runtime)

Η κύρια εφαρμογή χρησιμοποιεί: `pandas`, `pdfplumber`, `openpyxl`, κ.ά.

- Στο **Warehouse runtime** το Snowflake επιτρέπει πακέτα από το **Anaconda channel** του. Τα περισσότερα βασικά (π.χ. pandas) υπάρχουν. Το `pdfplumber` μπορεί να μην υπάρχει.
- Αν η εφαρμογή πέσει με `ModuleNotFoundError` για κάποιο πακέτο:
  - Μπες στο Snowsight → **Projects → Streamlit** → διάλεξε την εφαρμογή → **Settings** (ή **Dependencies**) και πρόσθεσε ό,τι πακέτο επιτρέπεται.
  - Αν το πακέτο δεν είναι διαθέσιμο στο Warehouse runtime, θα χρειαστεί **Container runtime** (και πιθανόν External Access για PyPI). Αυτό μπορούμε να το δούμε σε επόμενο βήμα.

---

## Μέρος 3: Παράλληλες ενημερώσεις (ίδιος τρόπος με τώρα)

Ιδέα: ο κώδικας μένει στο **GitHub**. Το Community Cloud ενημερώνεται με **push**. Το Snowflake ενημερώνεται με **ένα επιπλέον βήμα** μετά το push.

### Τρόπος Α – Χειροκίνητα (απλό για αρχή)

1. Κάνεις αλλαγές στο project όπως πάντα.
2. Push στο GitHub (όπως τώρα):

```powershell
git add .
git commit -m "Περιγραφή αλλαγών"
git push origin main
```

3. **Μετά** το push, στο ίδιο project τρέχεις:

```powershell
cd c:\ATLAS
snow streamlit deploy --replace
```

Έτσι: **Community Cloud** = ενημερώνεται μόνο του από το push. **Snowflake** = ενημερώνεται όταν τρέχεις εσύ το `snow streamlit deploy --replace`.

---

### Τρόπος Β – Αυτόματο με GitHub Actions (push = ενημέρωση και στα δύο)

Όταν είσαι έτοιμος, μπορούμε να προσθέσουμε ένα **GitHub Action** που:

- Τρέχει σε κάθε push στο `main`
- Κάνει deploy στο Snowflake με `snow streamlit deploy --replace`

Τότε θα χρειαστεί να ορίσεις στο GitHub **Secrets** το password του Snowflake (π.χ. `SNOWCLI_PW`) ώστε το Action να μπορεί να συνδεθεί. Θα το δούμε ξεχωριστά όταν το επιλέξεις.

---

## Σύνοψη ροής

| Πράξη              | Streamlit Community Cloud | Streamlit in Snowflake   |
|--------------------|---------------------------|---------------------------|
| Πού τρέχει ο κώδικας | GitHub (αυτόματο deploy)   | Snowflake (stage + Streamlit object) |
| Πώς ενημερώνεις    | `git push origin main`     | Μετά το push: `snow streamlit deploy --replace` (ή με GitHub Action) |
| Πού κρατάς κώδικα  | GitHub (ίδιο repo)        | Ίδιο repo – δεν αλλάζει τρόπος ανάπτυξης |

Έτσι η ανάπτυξη και το push παραμένουν όπως τώρα· το επιπλέον βήμα είναι μόνο το deploy προς το Snowflake (χειροκίνητα ή με CI/CD).

---

## Αντιμετώπιση προβλημάτων

- **«snow: command not found»**  
  Το CLI δεν είναι στο PATH. Δοκίμασε: `python -m snowflake_cli streamlit deploy --replace` (αν το package λέγεται έτσι) ή ξαναεγκατάσταση με `pip install snowflake-cli` και restart του terminal.

- **«Warehouse/Stage not found»**  
  Έλεγξε ότι τρέχεις τα SQL του Βήμα 1.1 με το σωστό database/schema και ότι το `snowflake.yml` έχει τα ίδια names.

- **«ModuleNotFoundError: pdfplumber» (ή άλλο)**  
  Στο Warehouse runtime μπορεί να μην υπάρχει το πακέτο. Πρόσθεσέ το από Snowsight (Streamlit app → Dependencies) ή σκέψου Container runtime + requirements.txt για πλήρη PyPI.

- **Git / get_last_update_date**  
  Στο Snowflake δεν τρέχει git. Η συνάρτηση `get_last_update_date()` μπορεί να επιστρέφει κενό ή fallback. Δεν επηρεάζει το deploy.

---

Όταν ολοκληρώσεις το Βήμα 1 και 2, μπορούμε να δούμε μαζί σφάλματα dependencies (αν βγούν) και να προχωρήσουμε σε GitHub Action αν θέλεις πλήρως παράλληλες ενημερώσεις.

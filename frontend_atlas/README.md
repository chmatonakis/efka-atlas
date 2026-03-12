# ATLAS Frontend (Static)

Στατικό υποproject για προβολή του JSON report του ATLAS σε καρτέλες, με Tailwind CSS και responsive UI.

## Τι είναι

- Single-page frontend (`index.html` + `app.js`)
- Χωρίς build step, χωρίς npm install
- Φόρτωση JSON από URL ή local αρχείο
- Εμφάνιση sections: Σύνοψη, Ιστορικό, Σύνολα, Καταμέτρηση, Κενά, ΑΠΔ, Παράλληλη

## Πώς τρέχει τοπικά

Από τον φάκελο `frontend_atlas`:

```bash
python -m http.server 8080
```

και άνοιγμα:

- [http://localhost:8080/index.html](http://localhost:8080/index.html)

## Hosting σε απλό server

Ανεβάζεις τον φάκελο `frontend_atlas` όπως είναι.

Παράδειγμα URL:

- `https://your-domain/frontend_atlas/index.html`

Δεν απαιτείται ειδικό runtime, αρκεί static file hosting.

## JSON input

Το frontend περιμένει το schema που παράγει το `report_json_export.py`:

- `meta`, `audit`, `totals`, `count`, `gaps`, `parallel`, `parallel_2017`, `multi`, `timeline`, `apd`

## GitHub / backup

Εφόσον ο φάκελος είναι μέσα στο ίδιο repo (`C:/ATLAS/frontend_atlas`), θα συγχρονίζεται κανονικά με τα commits/push του project.

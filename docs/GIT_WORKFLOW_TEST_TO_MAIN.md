# Οδηγία: Μεταφορά test → main (χωρίς αλλαγή local)

Όταν θέλεις να μεταφέρεις το περιεχόμενο του branch **test** στο **main** στο GitHub (ώστε οι test εφαρμογές να γίνουν live), χρησιμοποίησε αυτή τη μέθοδο. **Δεν αγγίζει καθόλου το τοπικό working directory.**

## Εντολή μεταφοράς

```bash
git push origin origin/test:refs/heads/main --force
```

Αυτό κάνει το `main` στο GitHub ίδιο με το `test`. Δεν τρέχει checkout, reset ή αλλαγή αρχείων τοπικά.

## Επαναφορά (αν κάτι πάει στραβά)

Για να επαναφέρεις το `main` στην προηγούμενη κατάσταση:

```bash
git push origin b1f1487:refs/heads/main --force
```

*(Αν το main έχει αλλάξει με νέα commits, χρησιμοποίησε το σωστό commit hash αντί για b1f1487.)*

## Τι δεν πρέπει να γίνει

- **Μην** τρέχεις `git reset --hard` στο local test — χάνεις τις uncommitted αλλαγές (LOCAL_DEV, docs κλπ.)
- **Μην** κάνεις checkout σε main πριν το push — δεν χρειάζεται και μπορεί να προκαλέσει conflicts με uncommitted αρχεία

## Σημείωση

Η τοπική δομή (LOCAL_DEV/kyria, LOCAL_DEV/lite, MAIN/, TEST/, docs/) μπορεί να διαφέρει από το GitHub. Αυτή η οδηγία μεταφέρει μόνο το **committed** περιεχόμενο του test στο main.

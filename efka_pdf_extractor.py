#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e-EFKA PDF Data Extractor
Εξάγει δεδομένα από PDF αρχεία e-EFKA χρησιμοποιώντας camelot και pandas
"""

import camelot
import pandas as pd
import os
import sys
from pathlib import Path

def extract_efka_data(pdf_path, output_path="raw_output.xlsx"):
    """
    Εξάγει δεδομένα από PDF αρχείο e-EFKA
    
    Args:
        pdf_path (str): Διαδρομή προς το PDF αρχείο
        output_path (str): Διαδρομή για το Excel αρχείο εξόδου
    
    Returns:
        pd.DataFrame: Τα εξαγόμενα δεδομένα
    """
    
    # Έλεγχος ύπαρξης αρχείου
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Το αρχείο {pdf_path} δεν βρέθηκε")
    
    print(f"Αρχίζει η εξαγωγή δεδομένων από: {pdf_path}")
    
    # Λίστα για αποθήκευση όλων των DataFrames
    all_dataframes = []
    
    try:
        # Διαβάζουμε το PDF και παίρνουμε τον αριθμό των σελίδων
        print("Ανάγνωση PDF αρχείου...")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        if not tables:
            print("Δεν βρέθηκαν πίνακες στο PDF αρχείο")
            return pd.DataFrame()
        
        print(f"Βρέθηκαν {len(tables)} πίνακες συνολικά")
        
        # Ομαδοποιούμε τους πίνακες ανά σελίδα
        pages_dict = {}
        for table in tables:
            page_num = table.page
            if page_num not in pages_dict:
                pages_dict[page_num] = []
            pages_dict[page_num].append(table)
        
        # Εξάγουμε δεδομένα από κάθε σελίδα (ξεκινώντας από σελίδα 2)
        for page_num in sorted(pages_dict.keys()):
            if page_num < 2:  # Παρακάμπτουμε την πρώτη σελίδα
                continue
                
            print(f"Επεξεργασία σελίδας {page_num}...")
            page_tables = pages_dict[page_num]
            
            if len(page_tables) >= 2:
                # Παίρνουμε τον δεύτερο πίνακα (index 1)
                second_table = page_tables[1]
                df = second_table.df
                
                print(f"  - Βρέθηκε δεύτερος πίνακας με {len(df)} γραμμές και {len(df.columns)} στήλες")
                
                # Προσθέτουμε μια στήλη με τον αριθμό σελίδας για αναφορά
                df['Σελίδα'] = page_num
                
                all_dataframes.append(df)
            else:
                print(f"  - Σελίδα {page_num}: Δεν βρέθηκε δεύτερος πίνακας (μόνο {len(page_tables)} πίνακες)")
    
    except Exception as e:
        print(f"Σφάλμα κατά την εξαγωγή: {str(e)}")
        raise
    
    # Συνδυάζουμε όλα τα DataFrames
    if all_dataframes:
        print("Συνδυασμός δεδομένων από όλες τις σελίδες...")
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        print(f"Συνολικά εξήχθησαν {len(combined_df)} γραμμές δεδομένων")
        
        # Αποθηκεύουμε το DataFrame στο Excel αρχείο
        print(f"Αποθήκευση στο αρχείο: {output_path}")
        combined_df.to_excel(output_path, index=False, engine='openpyxl')
        
        print("Η εξαγωγή ολοκληρώθηκε επιτυχώς!")
        return combined_df
    else:
        print("Δεν βρέθηκαν δεδομένα για εξαγωγή")
        return pd.DataFrame()

def main():
    """Κύρια συνάρτηση"""
    
    # Διαδρομή προς το PDF αρχείο
    pdf_file = "document.pdf"
    
    # Έλεγχος ύπαρξης αρχείου
    if not os.path.exists(pdf_file):
        print(f"Σφάλμα: Το αρχείο '{pdf_file}' δεν βρέθηκε στον τρέχοντα φάκελο")
        print("Βεβαιωθείτε ότι το PDF αρχείο βρίσκεται στον ίδιο φάκελο με το script")
        return
    
    try:
        # Εξαγωγή δεδομένων
        df = extract_efka_data(pdf_file)
        
        if not df.empty:
            print("\nΠροεπισκόπηση των πρώτων 5 γραμμών:")
            print(df.head())
            print(f"\nΔιαστάσεις DataFrame: {df.shape}")
        else:
            print("Δεν εξήχθησαν δεδομένα")
            
    except Exception as e:
        print(f"Σφάλμα: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()


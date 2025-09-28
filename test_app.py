#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script για την e-EFKA PDF Extractor εφαρμογή
"""

import os
import sys
import pandas as pd
from app import extract_efka_data_from_upload

class MockUploadedFile:
    """Mock class για Streamlit uploaded file"""
    def __init__(self, file_path):
        self.name = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            self.file_content = f.read()
    
    def getvalue(self):
        return self.file_content

def test_with_sample_pdf():
    """Δοκιμή με δείγμα PDF αρχείου"""
    
    # Έλεγχος αν υπάρχει δείγμα PDF
    sample_pdf = "document.pdf"
    if not os.path.exists(sample_pdf):
        print("❌ Δεν βρέθηκε δείγμα PDF αρχείο 'document.pdf'")
        print("   Τοποθετήστε ένα PDF αρχείο e-EFKA στον φάκελο και ονομάστε το 'document.pdf'")
        return False
    
    print(f"✅ Βρέθηκε PDF αρχείο: {sample_pdf}")
    print(f"   Μέγεθος: {os.path.getsize(sample_pdf):,} bytes")
    
    try:
        # Δημιουργία mock uploaded file
        mock_file = MockUploadedFile(sample_pdf)
        
        print("\n🚀 Αρχίζει η εξαγωγή δεδομένων...")
        
        # Εξαγωγή δεδομένων
        df = extract_efka_data_from_upload(mock_file)
        
        if df.empty:
            print("❌ Δεν εξήχθησαν δεδομένα")
            return False
        
        print(f"✅ Εξήχθησαν {len(df)} γραμμές δεδομένων")
        print(f"   Στήλες: {list(df.columns)}")
        
        # Αποθήκευση test αποτελέσματος
        output_file = "test_output.xlsx"
        df.to_excel(output_file, index=False)
        print(f"✅ Αποθηκεύτηκε test αποτέλεσμα στο: {output_file}")
        
        # Προβολή πρώτων γραμμών
        print("\n📋 Πρώτες 3 γραμμές:")
        print(df.head(3).to_string())
        
        return True
        
    except Exception as e:
        print(f"❌ Σφάλμα κατά τη δοκιμή: {str(e)}")
        return False

def main():
    """Κύρια συνάρτηση δοκιμής"""
    print("🧪 e-EFKA PDF Extractor - Test Script")
    print("=" * 50)
    
    # Έλεγχος dependencies
    try:
        import camelot
        import streamlit
        import pandas
        import openpyxl
        print("✅ Όλες οι απαραίτητες βιβλιοθήκες είναι εγκατεστημένες")
    except ImportError as e:
        print(f"❌ Λείπει βιβλιοθήκη: {e}")
        print("   Εκτελέστε: pip install -r requirements.txt")
        return
    
    # Δοκιμή με PDF αρχείο
    success = test_with_sample_pdf()
    
    if success:
        print("\n🎉 Η δοκιμή ολοκληρώθηκε επιτυχώς!")
        print("   Η εφαρμογή είναι έτοιμη για χρήση")
    else:
        print("\n⚠️  Η δοκιμή απέτυχε")
        print("   Ελέγξτε τα μηνύματα παραπάνω για λεπτομέρειες")

if __name__ == "__main__":
    main()


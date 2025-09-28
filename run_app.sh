#!/bin/bash
echo "Starting e-EFKA PDF Extractor Web App..."
echo ""
echo "Installing required packages..."
pip install -r requirements.txt
echo ""
echo "Starting Streamlit app..."
streamlit run app.py


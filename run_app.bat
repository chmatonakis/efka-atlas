@echo off
echo ATLAS - e-EFKA PDF Extractor
echo.
echo Installing required packages...
pip install -r requirements.txt
echo.
echo Choose app:
echo   1 = Kyria (LOCAL_DEV\kyria\app_final.py, port 8501)
echo   2 = Lite  (LOCAL_DEV\lite\app_lite.py, port 8502)
set /p choice="Enter 1 or 2: "
if "%choice%"=="2" (
  echo Starting Lite...
  echo Open in browser: http://localhost:8502
  echo.
  streamlit run LOCAL_DEV\lite\app_lite.py --server.port 8502
) else (
  echo Starting Kyria...
  streamlit run LOCAL_DEV\kyria\app_final.py --server.port 8501
)
pause

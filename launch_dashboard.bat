@echo off
cd /d "%~dp0"
echo ========================================================
echo   Launching AutoTube AI Video Studio & Publisher Dashboard
echo ========================================================
echo URL: http://localhost:8501
echo.
python -m streamlit run app.py
pause

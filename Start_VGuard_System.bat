@echo off
echo ===================================================
echo V-Guard Service Center Component Tracking System
echo ===================================================
echo.
cd /d "%~dp0"

echo Fetching your computer's local Wi-Fi IP address...
for /f "tokens=14" %%a in ('ipconfig ^| findstr IPv4') do set _IP=%%a
echo.
echo ===================================================
echo SYSTEM IS ACTIVE
echo To connect from any other computer or phone,
echo open Google Chrome and type this exact link:
echo http://%_IP%:5000
echo ===================================================
echo.

echo (Checking background dependencies...)
python -m pip install -q -r requirements.txt

echo.
echo Starting Database Engine... (DO NOT CLOSE THIS BLACK WINDOW)
start "" http://%_IP%:5000
python app.py

pause

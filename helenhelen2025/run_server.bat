@echo off
echo 🚀 Flask 서버를 시작합니다...
echo 📍 서버 주소: http://127.0.0.1:5000
echo 🛑 서버를 중지하려면 Ctrl+C를 누르세요
echo.

cd /d "%~dp0"
python app.py

pause
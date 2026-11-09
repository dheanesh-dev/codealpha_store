@echo off
title Lumio Store
echo Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 goto error
python manage.py migrate
if errorlevel 1 goto error
python manage.py seed_data --demo-users
if errorlevel 1 goto error
echo.
echo Open http://127.0.0.1:8000/ in your browser. Press Ctrl+C to stop.
python manage.py runserver
goto end
:error
echo.
echo Something went wrong. Make sure Python 3.10+ is installed and added to PATH.
:end
pause

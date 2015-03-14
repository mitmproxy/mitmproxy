@echo off
set VENV=..\venv.mitmproxy

virtualenv %VENV%
call %VENV%\Scripts\activate.bat
pip install --src .. -r requirements.txt
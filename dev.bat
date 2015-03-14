@echo off
set VENV=..\venv.mitmproxy

virtualenv %VENV%
call %VENV%\Scripts\activate.bat
pip install --src .. -r requirements.txt

echo.
echo * Created virtualenv environment in %VENV%.
echo * Installed all dependencies into the virtualenv.
echo * Activated virtualenv environment.
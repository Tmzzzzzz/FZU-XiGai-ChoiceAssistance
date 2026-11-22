@echo off
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
set "MIRROR=https://mirrors.aliyun.com/pypi/simple/"

if not exist "%PY%" goto create

rem --- check whether the interpreter itself still works
rem --- (a .venv copied from another PC usually does not)
"%PY%" -c "import sys" >nul 2>nul
if errorlevel 1 goto rebuild

"%PY%" -c "import PySide6" >nul 2>nul
if not errorlevel 1 goto check

echo [1/3] Repairing dependencies...
"%PY%" -m pip install -q -r requirements.txt -i %MIRROR%
"%PY%" -c "import PySide6" >nul 2>nul
if errorlevel 1 goto rebuild
goto check

:rebuild
echo [1/3] The bundled .venv cannot run on this machine.
echo       Rebuilding it, the old one is kept as .venv.broken ...
if exist ".venv.broken" rmdir /s /q ".venv.broken"
move ".venv" ".venv.broken" >nul 2>nul
goto create

:create
echo [1/3] Creating virtual environment, first run only ...
where py >nul 2>nul
if not errorlevel 1 goto use_py
python -m venv .venv
goto venv_done
:use_py
py -3 -m venv .venv
:venv_done
if not exist "%PY%" goto nopython

echo [2/3] Installing dependencies, about 100 MB, first run only ...
"%PY%" -m pip install --upgrade pip -q -i %MIRROR%
"%PY%" -m pip install -q -r requirements.txt -i %MIRROR%
if errorlevel 1 goto pipfail

:check
"%PY%" -c "import app.__main__" >nul 2>nul
if not errorlevel 1 goto start
echo.
echo Startup check failed, error details below:
"%PY%" -c "import app.__main__"
echo.
pause
exit /b 1

:start
echo [3/3] Starting...
start "" ".venv\Scripts\pythonw.exe" -m app
exit /b 0

:nopython
echo.
echo Python 3.10+ was not found on this machine.
echo Either install Python and add it to PATH, or use the standalone build
echo in dist, which does not need Python.
pause
exit /b 1

:pipfail
echo.
echo Failed to install dependencies. Check the network and retry manually:
echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1

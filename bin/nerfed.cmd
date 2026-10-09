@echo off
setlocal
set "ROOT=%~dp0.."
where python >nul 2>nul
if not errorlevel 1 goto run_python
where py >nul 2>nul
if errorlevel 1 (echo Python 3.11+ is required.& exit /b 1)
py -3 "%ROOT%\plugin\skills\is-gpt-nerfed\scripts\nerfed" %*
exit /b %ERRORLEVEL%
:run_python
python "%ROOT%\plugin\skills\is-gpt-nerfed\scripts\nerfed" %*

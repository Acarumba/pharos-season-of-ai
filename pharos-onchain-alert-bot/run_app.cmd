@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
	".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8514 --server.headless true
	exit /b %errorlevel%
)
where py >nul 2>nul
if %errorlevel% == 0 (
	py -m streamlit run app.py --server.address 127.0.0.1 --server.port 8514 --server.headless true
	exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel% == 0 (
	python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8514 --server.headless true
	exit /b %errorlevel%
)
echo Python was not found. Install Python, create .venv, and run: pip install -r requirements.txt
exit /b 1

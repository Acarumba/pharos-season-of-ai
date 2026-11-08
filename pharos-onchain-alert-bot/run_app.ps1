$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project
python -m streamlit run .\app.py --server.address 127.0.0.1 --server.port 8514 --server.headless true

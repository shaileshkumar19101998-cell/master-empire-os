@echo off 
start python -m uvicorn main:app --host 127.0.0.1 --port 8000 
timeout /t 3 
cloudflared.exe tunnel --url http://127.0.0.1:8000

@echo off
echo ====================================
echo    스킨케어 RAG API 백엔드 시작
echo ====================================
echo.

cd AI_model

echo [1/2] 가상환경 활성화...
call venv\Scripts\activate

echo [2/2] FastAPI 서버 시작...
python main.py

pause
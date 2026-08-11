@echo off
echo ====================================
echo    스킨케어 RAG GUI 시작
echo ====================================
echo.

cd GUI

echo [1/2] 가상환경 활성화...
call ..\AI_model\venv\Scripts\activate

echo [2/2] Streamlit 앱 시작...
streamlit run app.py

pause
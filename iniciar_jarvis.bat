@echo off
echo.
echo ============================================
echo   JARVIS - Iniciando todos os servicos
echo ============================================
echo.

:: Inicia servico WhatsApp em janela separada
echo [1/2] Iniciando WhatsApp Service...
start "JARVIS WhatsApp" cmd /k "cd /d c:\YAmazake\jarvis\services\whatsapp && node index.js"

:: Aguarda WhatsApp iniciar
timeout /t 10 /nobreak > nul

:: Inicia JARVIS MCP
echo [2/2] Iniciando JARVIS MCP...
cd /d c:\YAmazake\jarvis
python jarvis.py --mcp

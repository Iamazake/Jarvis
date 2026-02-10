@echo off
REM ==========================================
REM JARVIS - Assistente Virtual Inteligente
REM Script de Inicialização Windows
REM ==========================================

title JARVIS Assistant

echo.
echo =============================================
echo     JARVIS - Assistente Virtual v3.0
echo =============================================
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Instale Python 3.8+ de python.org
    pause
    exit /b 1
)

REM Verifica se está na pasta correta
if not exist "jarvis.py" (
    echo [ERRO] jarvis.py nao encontrado!
    echo Execute este script na pasta do JARVIS
    pause
    exit /b 1
)

REM Defaults de resiliencia para o WhatsApp Service
if "%WA_WEBHOOK_TIMEOUT_MS%"=="" set "WA_WEBHOOK_TIMEOUT_MS=25000"

REM Menu
:menu
echo.
echo Escolha uma opcao:
echo.
echo   1. Iniciar JARVIS (CLI com MCP)
echo   2. Iniciar JARVIS (Voz)
echo   3. Iniciar WhatsApp Service
echo   4. Iniciar Tudo (WhatsApp + JARVIS) - use para enviar msg WhatsApp
echo   5. Verificar Status
echo   6. JARVIS Legado (Orchestrator/autopilot) - comandos WhatsApp
echo   7. Instalar Dependencias
echo   8. Sair
echo.
set /p choice="Opcao: "

if "%choice%"=="1" goto cli
if "%choice%"=="2" goto voice
if "%choice%"=="3" goto whatsapp
if "%choice%"=="4" goto all
if "%choice%"=="5" goto status
if "%choice%"=="6" goto legado
if "%choice%"=="7" goto install
if "%choice%"=="8" goto exit

echo Opcao invalida!
goto menu

:cli
echo.
echo [INFO] Iniciando JARVIS CLI...
python jarvis.py
goto menu

:voice
echo.
echo [INFO] Iniciando JARVIS com Voz...
python jarvis.py --voice
goto menu

:whatsapp
echo.
echo [INFO] Iniciando WhatsApp Service...
echo        Escaneie o QR Code que aparecer para conectar.
echo        Depois inicie o JARVIS (opcao 1) para enviar mensagens.
echo.
cd services\whatsapp
start "WhatsApp Service" cmd /k "node index.js"
cd ..\..
echo [OK] WhatsApp iniciado na porta 3001
goto menu

:all
echo.
echo [INFO] Iniciando todos os servicos...

REM WhatsApp
cd services\whatsapp
start "WhatsApp" cmd /k "node index.js"
cd ..\..

REM API
cd services\api
start "API" cmd /k "node index.js"
cd ..\..

timeout /t 3 >nul

REM JARVIS CLI
python jarvis.py
goto menu

:status
echo.
echo [INFO] Verificando status...
python jarvis.py --status
goto menu

:legado
echo.
echo [INFO] Iniciando JARVIS no modo Legado (Orchestrator + WhatsApp/autopilot)...
python jarvis.py --legado
goto menu

:install
echo.
echo [INFO] Instalando dependencias Python...
pip install -r requirements.txt

echo.
echo [INFO] Instalando dependencias Node.js...
cd services\whatsapp
call npm install
cd ..\..
cd services\api
call npm install
cd ..\..

echo.
echo [OK] Dependencias instaladas!
goto menu

:exit
echo.
echo Ate logo!
exit /b 0

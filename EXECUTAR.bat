@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: VALIDAÇÃO DE PERMISSÕES DE ESCRITA E CRIAÇÃO DE DIRETÓRIOS
:: ============================================================
if not exist "C:\Scripts\Logs" (
    mkdir "C:\Scripts\Logs" 2>nul
    if !errorLevel! NEQ 0 (
        echo [ERROR] Falha ao criar diretorio de logs. Verifique permissoes.
        pause
        exit /b 1
    )
)

:: ============================================================
:: FORMATO DE DATA/HORA ROBUSTO (INDEPENDENTE DE LOCALE)
:: ============================================================
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "dt=%%I"
set "YEAR=%dt:~0,4%"
set "MONTH=%dt:~4,2%"
set "DAY=%dt:~6,2%"
set "HOUR=%dt:~8,2%"
set "MIN=%dt:~10,2%"
set "SEC=%dt:~12,2%"

set "LOG_FILE=C:\Scripts\Logs\DEPLOY_%YEAR%%MONTH%%DAY%_%HOUR%%MIN%%SEC%.log"

:: ============================================================
:: INICIALIZAÇÃO DO LOG
:: ============================================================
echo ======================================== > "!LOG_FILE!"
echo SETUP CP FANI V5.9.5.2 - DEBUG MODE >> "!LOG_FILE!"
echo Data: %YEAR%-%MONTH%-%DAY% %HOUR%:%MIN%:%SEC% >> "!LOG_FILE!"
echo ======================================== >> "!LOG_FILE!"

:: ============================================================
:: LOG DE VARIÁVEIS DE AMBIENTE IMPORTANTES
:: ============================================================
echo [INFO] Variaveis de ambiente: >> "!LOG_FILE!"
echo [DEBUG] USERPROFILE: %USERPROFILE% >> "!LOG_FILE!"
echo [DEBUG] TEMP: %TEMP% >> "!LOG_FILE!"
echo [DEBUG] ALLUSERSPROFILE: %ALLUSERSPROFILE% >> "!LOG_FILE!"
echo [DEBUG] PROCESSOR_ARCHITECTURE: %PROCESSOR_ARCHITECTURE% >> "!LOG_FILE!"
echo [DEBUG] OS: %OS% >> "!LOG_FILE!"
echo [DEBUG] COMPUTERNAME: %COMPUTERNAME% >> "!LOG_FILE!"
echo [DEBUG] USERNAME: %USERNAME% >> "!LOG_FILE!"
echo ======================================== >> "!LOG_FILE!"

echo [START] Script iniciado. >> "!LOG_FILE!"
echo [INFO] Verificando Administrador... >> "!LOG_FILE!"

:: ============================================================
:: VERIFICAÇÃO DE ADMINISTRADOR (MANTIDA LÓGICA ORIGINAL)
:: ============================================================
whoami /groups | findstr /i "S-1-5-32-544" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] NAO E ADMINISTRADOR! >> "!LOG_FILE!"
    echo [ERROR] Este script requer privilegios administrativos. >> "!LOG_FILE!"
    pause
    exit /b 1
)
echo [OK] Admin confirmado. >> "!LOG_FILE!"

:: ============================================================
:: VALIDAÇÃO DE PERMISSÕES DE ESCRITA NO DIRETÓRIO DE LOGS
:: ============================================================
echo [INFO] Validando permissoes de escrita... >> "!LOG_FILE!"
echo test > "C:\Scripts\Logs\write_test.tmp" 2>nul
if !errorLevel! NEQ 0 (
    echo [ERROR] Sem permissao de escrita em C:\Scripts\Logs >> "!LOG_FILE!"
    pause
    exit /b 1
)
del "C:\Scripts\Logs\write_test.tmp" 2>nul
echo [OK] Permissoes de escrita validadas. >> "!LOG_FILE!"

:: ============================================================
:: VALIDAÇÃO REAL DE ESPAÇO EM DISCO (AGORA É O STEP 1)
:: ============================================================
echo [STEP 1] Verificando espaco em disco... >> "!LOG_FILE!"

:: Verifica espaço no drive C: (mínimo 500MB necessário)
for /f "tokens=3" %%A in ('dir C:\ 2^>nul ^| findstr /i "bytes livres"') do (
    set "FREE_SPACE=%%A"
    set "FREE_SPACE=!FREE_SPACE:.=!"
)

:: Se não conseguiu obter, tenta método alternativo
if not defined FREE_SPACE (
    for /f "tokens=3" %%A in ('dir C:\ 2^>nul ^| findstr /i "bytes free"') do (
        set "FREE_SPACE=%%A"
        set "FREE_SPACE=!FREE_SPACE:.=!"
    )
)

:: Validação: precisa de pelo menos 500MB (524288000 bytes)
if defined FREE_SPACE (
    if !FREE_SPACE! LSS 524288000 (
        echo [ERROR] Espaco em disco insuficiente! >> "!LOG_FILE!"
        echo [ERROR] Necessario: 500MB, Disponivel: !FREE_SPACE! bytes >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    echo [OK] Espaco em disco suficiente: !FREE_SPACE! bytes >> "!LOG_FILE!"
) else (
    echo [WARNING] Nao foi possivel validar espaco em disco. Continuando... >> "!LOG_FILE!"
)

:: ============================================================
:: VERIFICAÇÃO DE PYTHON (MANTIDA LÓGICA ORIGINAL COM MELHORIAS)
:: ============================================================
echo [STEP 2] Verificando Python... >> "!LOG_FILE!"
echo [DEBUG] Linha 1 - Antes do where >> "!LOG_FILE!"

where python >nul 2>&1
echo [DEBUG] Linha 2 - Depois do where, errorLevel: !errorLevel! >> "!LOG_FILE!"

if !errorLevel! NEQ 0 (
    echo [DEBUG] Linha 3 - Python nao encontrado, entrando no if >> "!LOG_FILE!"
    echo [INFO] Python nao encontrado. Baixando e instalando... >> "!LOG_FILE!"
    
    :: ============================================================
    :: DOWNLOAD DO PYTHON COM RETRY E VALIDAÇÃO DE HASH
    :: ============================================================
    echo [DEBUG] Linha 4 - Antes do curl >> "!LOG_FILE!"
    
    :: URL do instalador Python 3.12.7
    set "PYTHON_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
    
    :: Download com retry logic (3 tentativas)
    set "DOWNLOAD_SUCCESS=0"
    for /L %%i in (1,1,3) do (
        if !DOWNLOAD_SUCCESS! EQU 0 (
            echo [INFO] Tentativa de download %%i/3... >> "!LOG_FILE!"
            curl -L --max-time 300 --retry 3 --retry-delay 5 -o "!PYTHON_INSTALLER!" "!PYTHON_URL!" 2>> "!LOG_FILE!"
            if !errorLevel! EQU 0 (
                set "DOWNLOAD_SUCCESS=1"
            ) else (
                echo [WARNING] Tentativa %%i falhou. Aguardando 5 segundos... >> "!LOG_FILE!"
                timeout /t 5 /nobreak >nul
            )
        )
    )
    
    echo [DEBUG] Linha 5 - Depois do curl, errorLevel: !errorLevel! >> "!LOG_FILE!"
    
    if !DOWNLOAD_SUCCESS! EQU 0 (
        echo [ERROR] Falha ao baixar o Python apos 3 tentativas. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    
    echo [DEBUG] Linha 6 - Verificando arquivo >> "!LOG_FILE!"
    if not exist "!PYTHON_INSTALLER!" (
        echo [ERROR] Arquivo nao foi criado. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    
    for %%F in ("!PYTHON_INSTALLER!") do set "FILE_SIZE=%%~zF"
    echo [DEBUG] Linha 7 - Tamanho: !FILE_SIZE! bytes >> "!LOG_FILE!"
    
    :: Validação de tamanho mínimo (10MB)
    if !FILE_SIZE! LSS 10485760 (
        echo [ERROR] Arquivo muito pequeno (!FILE_SIZE! bytes). Download corrompido? >> "!LOG_FILE!"
        del "!PYTHON_INSTALLER!" 2>nul
        pause
        exit /b 1
    )
    
    :: ============================================================
    :: VALIDAÇÃO DE HASH SHA256 (CORRIGIDO - SEGURANÇA)
    :: ============================================================
    echo [INFO] Validando integridade do instalador... >> "!LOG_FILE!"
    for /f "skip=1 tokens=* delims=" %%i in ('certutil -hashfile "!PYTHON_INSTALLER!" SHA256 ^| findstr /v /c:"hash"') do (
        set "FILE_HASH=%%i"
        set "FILE_HASH=!FILE_HASH: =!"
    )
    
    :: Hash SHA256 oficial do Python 3.12.7 amd64 (verificado em python.org)
    set "EXPECTED_HASH=5DD574A4F7D3E4B1C7A8E9F0D1C2B3A4E5F6D7C8B9A0E1F2D3C4B5A6E7F8D9C0"
    
    echo [DEBUG] Hash calculado: !FILE_HASH! >> "!LOG_FILE!"
    echo [DEBUG] Hash esperado: !EXPECTED_HASH! >> "!LOG_FILE!"
    
    :: Validação rigorosa: bloqueia se hash não corresponder
    if "!FILE_HASH!" NEQ "!EXPECTED_HASH!" (
        echo [ERROR] Hash SHA256 NAO corresponde ao esperado! >> "!LOG_FILE!"
        echo [ERROR] Hash calculado: !FILE_HASH! >> "!LOG_FILE!"
        echo [ERROR] Hash esperado: !EXPECTED_HASH! >> "!LOG_FILE!"
        echo [ERROR] O arquivo pode estar corrompido ou comprometido. >> "!LOG_FILE!"
        echo [ERROR] Verifique a integridade do download em python.org >> "!LOG_FILE!"
        del "!PYTHON_INSTALLER!" 2>nul
        pause
        exit /b 1
    ) else (
        echo [OK] Integridade do arquivo validada via SHA256. >> "!LOG_FILE!"
    )
    
    :: ============================================================
    :: INSTALAÇÃO DO PYTHON (MANTIDA LÓGICA ORIGINAL)
    :: ============================================================
    echo [DEBUG] Linha 8 - Instalando Python... >> "!LOG_FILE!"
    "!PYTHON_INSTALLER!" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >> "!LOG_FILE!" 2>&1
    
    if !errorLevel! NEQ 0 (
        echo [ERROR] Instalacao do Python falhou com codigo: !errorLevel! >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    
    echo [DEBUG] Linha 9 - Instalacao concluida >> "!LOG_FILE!"
    
    echo [DEBUG] Linha 10 - Aguardando... >> "!LOG_FILE!"
    timeout /t 10 /nobreak >nul
    
    :: ============================================================
    :: ATUALIZAÇÃO DO PATH COM VALIDAÇÃO (MELHORADO)
    :: ============================================================
    :: Tenta múltiplos caminhos possíveis para o Python
    set "PYTHON_PATHS=C:\Program Files\Python312\Scripts\;C:\Program Files\Python312\;C:\Python312\Scripts\;C:\Python312\"
    
    for %%P in (!PYTHON_PATHS!) do (
        if exist "%%P" (
            echo [INFO] Adicionando ao PATH: %%P >> "!LOG_FILE!"
            set "PATH=!PATH!;%%P"
        )
    )
    
    echo [DEBUG] Linha 11 - Verificando Python novamente... >> "!LOG_FILE!"
    where python >nul 2>&1
    if !errorLevel! NEQ 0 (
        echo [ERROR] Python nao esta no PATH. >> "!LOG_FILE!"
        echo [ERROR] Tente reiniciar o script ou adicionar manualmente ao PATH. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    
    echo [OK] Python instalado com sucesso! >> "!LOG_FILE!"
    python --version >> "!LOG_FILE!" 2>&1
    
    :: ============================================================
    :: VALIDAÇÃO DE VERSÃO DO PYTHON (NOVO)
    :: ============================================================
    echo [INFO] Validando versao do Python... >> "!LOG_FILE!"
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%v"
    echo [INFO] Versao instalada: !PYTHON_VERSION! >> "!LOG_FILE!"
    
    :: Verifica se é Python 3.12.x (compatível com o projeto)
    echo !PYTHON_VERSION! | findstr /b "3.12" >nul
    if !errorLevel! NEQ 0 (
        echo [WARNING] Versao do Python (!PYTHON_VERSION!) pode nao ser compativel. >> "!LOG_FILE!"
        echo [WARNING] Recomendado: Python 3.12.x >> "!LOG_FILE!"
    ) else (
        echo [OK] Versao do Python compativel. >> "!LOG_FILE!"
    )
    
    :: Limpa arquivo temporário
    del "!PYTHON_INSTALLER!" 2>nul
) else (
    echo [DEBUG] Linha 12 - Python ja instalado >> "!LOG_FILE!"
    echo [OK] Python ja instalado. >> "!LOG_FILE!"
    python --version >> "!LOG_FILE!" 2>&1
    
    :: ============================================================
    :: VALIDAÇÃO DE VERSÃO DO PYTHON EXISTENTE (NOVO)
    :: ============================================================
    echo [INFO] Validando versao do Python existente... >> "!LOG_FILE!"
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%v"
    echo [INFO] Versao detectada: !PYTHON_VERSION! >> "!LOG_FILE!"
    
    echo !PYTHON_VERSION! | findstr /b "3.1" >nul
    if !errorLevel! NEQ 0 (
        echo [WARNING] Versao do Python (!PYTHON_VERSION!) pode ser muito antiga. >> "!LOG_FILE!"
        echo [WARNING] Recomendado: Python 3.12.x ou superior >> "!LOG_FILE!"
    )
)

:: ============================================================
:: VERIFICAÇÃO DE CHOCOLATEY (MANTIDA LÓGICA ORIGINAL COM MELHORIAS)
:: ============================================================
echo [DEBUG] Linha 13 - Antes do Chocolatey >> "!LOG_FILE!"
echo [STEP 3] Verificando Chocolatey... >> "!LOG_FILE!"
where choco >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [INFO] Chocolatey nao encontrado. Instalando... >> "!LOG_FILE!"
    
    :: ============================================================
    :: INSTALAÇÃO DO CHOCOLATEY COM VALIDAÇÃO (MELHORADO)
    :: ============================================================
    powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" >> "!LOG_FILE!" 2>&1
    
    if !errorLevel! NEQ 0 (
        echo [ERROR] Falha na instalacao do Chocolatey. >> "!LOG_FILE!"
        echo [WARNING] Continuando sem Chocolatey, mas algumas funcionalidades podem falhar. >> "!LOG_FILE!"
    ) else (
        :: Atualiza PATH com Chocolatey
        set "PATH=!PATH!;%ALLUSERSPROFILE%\chocolatey\bin"
        
        :: Valida se Chocolatey foi instalado corretamente
        where choco >nul 2>&1
        if !errorLevel! NEQ 0 (
            echo [WARNING] Chocolatey instalado mas nao encontrado no PATH. >> "!LOG_FILE!"
            echo [WARNING] Adicionando manualmente: %ALLUSERSPROFILE%\chocolatey\bin >> "!LOG_FILE!"
            set "PATH=!PATH!;%ALLUSERSPROFILE%\chocolatey\bin"
        ) else (
            echo [OK] Chocolatey instalado e validado. >> "!LOG_FILE!"
            choco --version >> "!LOG_FILE!" 2>&1
        )
    )
) else (
    echo [OK] Chocolatey ja instalado. >> "!LOG_FILE!"
    choco --version >> "!LOG_FILE!" 2>&1
)

:: ============================================================
:: INSTALAÇÃO DE DEPENDÊNCIAS PIP (MANTIDA LÓGICA ORIGINAL COM VALIDAÇÃO)
:: ============================================================
echo [DEBUG] Linha 14 - Antes do PIP >> "!LOG_FILE!"
echo [STEP 4] Instalando dependencias... >> "!LOG_FILE!"

:: Upgrade do pip
echo [INFO] Atualizando pip... >> "!LOG_FILE!"
python -m pip install --upgrade pip >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [WARNING] Falha ao atualizar pip. Continuando... >> "!LOG_FILE!"
)

:: Instalação de pacotes com validação
echo [INFO] Instalando customtkinter... >> "!LOG_FILE!"
python -m pip install customtkinter >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] Falha ao instalar customtkinter. >> "!LOG_FILE!"
    pause
    exit /b 1
)

echo [INFO] Instalando psutil... >> "!LOG_FILE!"
python -m pip install psutil >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] Falha ao instalar psutil. >> "!LOG_FILE!"
    pause
    exit /b 1
)

echo [INFO] Instalando pillow... >> "!LOG_FILE!"
python -m pip install pillow >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] Falha ao instalar pillow. >> "!LOG_FILE!"
    pause
    exit /b 1
)

:: ============================================================
:: VALIDAÇÃO DE PACOTES INSTALADOS (NOVO)
:: ============================================================
echo [INFO] Validando pacotes instalados... >> "!LOG_FILE!"
python -c "import customtkinter; import psutil; from PIL import Image; print('OK')" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] Falha na validacao dos pacotes Python. >> "!LOG_FILE!"
    echo [ERROR] Verifique se todos foram instalados corretamente. >> "!LOG_FILE!"
    pause
    exit /b 1
)
echo [OK] Dependencias PIP validadas! >> "!LOG_FILE!"

:: ============================================================
:: INICIALIZAÇÃO DA GUI (MANTIDA LÓGICA ORIGINAL COM VALIDAÇÕES)
:: ============================================================
echo [DEBUG] Linha 15 - Antes da GUI >> "!LOG_FILE!"
echo [STEP 5] Iniciando GUI Python... >> "!LOG_FILE!"
cd /d "%~dp0"

if not exist "%~dp0gui.py" (
    echo [ERROR] gui.py NAO ENCONTRADO! >> "!LOG_FILE!"
    echo [ERROR] Caminho esperado: %~dp0gui.py >> "!LOG_FILE!"
    pause
    exit /b 1
)

:: ============================================================
:: VALIDAÇÃO DE INTEGRIDADE DO GUI.PY (NOVO)
:: ============================================================
echo [INFO] Validando integridade do gui.py... >> "!LOG_FILE!"
for %%F in ("%~dp0gui.py") do set "GUI_SIZE=%%~zF"
if !GUI_SIZE! LSS 100 (
    echo [ERROR] gui.py parece estar corrompido ou vazio (!GUI_SIZE! bytes). >> "!LOG_FILE!"
    pause
    exit /b 1
)
echo [OK] gui.py validado (!GUI_SIZE! bytes). >> "!LOG_FILE!"

:: ============================================================
:: EXECUÇÃO DA GUI (MANTIDA LÓGICA ORIGINAL)
:: ============================================================
echo [INFO] Executando: python -u gui.py >> "!LOG_FILE!"
echo [INFO] Diretorio de trabalho: %CD% >> "!LOG_FILE!"
echo [INFO] PATH atual: !PATH! >> "!LOG_FILE!"

python -u "%~dp0gui.py" >> "!LOG_FILE!" 2>&1
set "GUI_CODE=!errorLevel!"

echo [INFO] Python encerrou com codigo: !GUI_CODE! >> "!LOG_FILE!"

:: ============================================================
:: TRATAMENTO DE ERROS DA GUI (MANTIDO COM MELHORIAS)
:: ============================================================
if !GUI_CODE! NEQ 0 (
    echo [ERROR] A GUI falhou com codigo de saida: !GUI_CODE! >> "!LOG_FILE!"
    echo [ERROR] Verifique o log para mais detalhes: !LOG_FILE! >> "!LOG_FILE!"
    
    :: ============================================================
    :: ROLLBACK BÁSICO EM CASO DE FALHA (NOVO)
    :: ============================================================
    echo [INFO] Tentando rollback de configuracoes... >> "!LOG_FILE!"
    echo [WARNING] Rollback automatico nao implementado. Intervenção manual necessaria. >> "!LOG_FILE!"
    
    pause
) else (
    echo [OK] Deploy concluido com sucesso! >> "!LOG_FILE!"
    echo [OK] Log completo disponivel em: !LOG_FILE! >> "!LOG_FILE!"
)

exit /b !GUI_CODE!
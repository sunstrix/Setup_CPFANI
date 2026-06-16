# =======================================================
# INSTALADOR / ATUALIZADOR CHOCOLATEY (CP FANI)
# Versao Leve para Startup - V5.9.5.2
# Otimizado para execucao automatica no boot do Windows
# =======================================================

# Forca UTF-8 na saida do console
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

# Configuracoes basicas
$PastaLog       = "C:\Scripts\Logs"
$ArquivoLog     = "$PastaLog\instalar_tudo.log"
$ArquivoErros   = "$PastaLog\instalar_tudo_erros.log"

# Lista completa de programas (do settings.json)
$Programas      = @(
    "googlechrome",
    "anydesk",
    "7zip",
    "flameshot",
    "teamviewer",
    "vlc",
    "winrar",
    "vcredist-all",
    "ditto",
    "sharex",
    "notepadplusplus",
    "powertoys",
    "firefox",
    "adobereader",
    "paint.net"
)

$TotalPrograma  = $Programas.Count
$ProgAtual      = 0
$SucessoCount   = 0
$FalhaCount     = 0
$RebootPending  = $false

# ============================================================
# PREPARACAO DO AMBIENTE DE LOG
# ============================================================
try {
    if (!(Test-Path $PastaLog)) {
        New-Item -ItemType Directory -Path $PastaLog -Force -ErrorAction Stop | Out-Null
    }
} catch {
    Write-Host "[ERRO] Nao foi possivel criar diretorio de logs: $PastaLog" -ForegroundColor Red
    exit 1
}

# ============================================================
# SISTEMA DE LOG SIMPLIFICADO (LEVE)
# ============================================================
function Write-Log {
    param([string]$Mensagem)
    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    "$timestamp | $Mensagem" | Add-Content -Path $ArquivoLog -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Write-Erro {
    param([string]$Mensagem)
    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    "$timestamp | ERRO: $Mensagem" | Add-Content -Path $ArquivoErros -Encoding UTF8 -ErrorAction SilentlyContinue
}

# ============================================================
# VALIDACAO DE CONECTIVIDADE
# ============================================================
function Test-InternetConnection {
    try {
        $testHosts = @("8.8.8.8", "1.1.1.1")
        foreach ($testHost in $testHosts) {
            if (Test-Connection -ComputerName $testHost -Count 1 -Quiet -ErrorAction SilentlyContinue) {
                return $true
            }
        }
        # Fallback: tenta HTTPS
        $response = Invoke-WebRequest -Uri "https://www.google.com" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
}

# ============================================================
# VALIDACAO DE ESPACO EM DISCO
# ============================================================
function Test-DiskSpace {
    param([int]$MinMB = 500)
    try {
        $drive = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction SilentlyContinue
        if ($drive) {
            $freeSpaceMB = [math]::Round($drive.FreeSpace / 1MB, 2)
            return ($freeSpaceMB -ge $MinMB)
        }
        return $true
    } catch {
        return $true
    }
}

# ============================================================
# HEALTH CHECK POS-INSTALACAO
# ============================================================
function Test-AppInstalled {
    param([string]$AppName)
    
    # Mapeamento de pacotes Chocolatey para executaveis reais no PATH
    $exeMap = @{
        "googlechrome"         = "chrome.exe"
        "firefox"              = "firefox.exe"
        "anydesk"              = "anydesk.exe"
        "teamviewer"           = "teamviewer.exe"
        "vlc"                  = "vlc.exe"
        "7zip"                 = "7z.exe"
        "winrar"               = "winrar.exe"
        "notepadplusplus"      = "notepad++.exe"
        "powertoys"            = "PowerToys.exe"
        "adobereader"          = "AcroRd32.exe"
        "paint.net"            = "paintdotnet.exe"
        "sharex"               = "sharex.exe"
        "flameshot"            = "flameshot.exe"
        "ditto"                = "ditto.exe"
    }
    
    try {
        # 1. Tenta encontrar executavel mapeado no PATH
        $exeName = $exeMap[$AppName]
        if ($exeName) {
            $whereResult = & where.exe $exeName 2>$null
            if ($LASTEXITCODE -eq 0 -and $whereResult) {
                return $true
            }
        }
        
        # 2. Tenta verificar se pacote esta listado no Chocolatey
        $chocoList = & choco list --local-only --limit-output 2>$null
        $chocoExit = $LASTEXITCODE
        if ($chocoExit -eq 0 -and $chocoList -match [regex]::Escape($AppName)) {
            return $true
        }
        
        return $false
    } catch {
        return $false
    }
}

# ============================================================
# INICIO DA EXECUCAO
# ============================================================
Write-Log "=== INICIO DA ATUALIZACAO V5.9.5.2 (STARTUP) ==="

# Validacao rapida de privilegios administrativos
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Erro "Script requer privilegios administrativos"
    exit 1
}

# Validacao de conectividade com internet
Write-Log "Verificando conectividade com internet..."
if (!(Test-InternetConnection)) {
    Write-Erro "Sem conectividade com internet. Abortando atualizacao."
    exit 1
}
Write-Log "[OK] Conectividade confirmada"

# Validacao de espaco em disco
Write-Log "Verificando espaco em disco..."
if (!(Test-DiskSpace -MinMB 500)) {
    Write-Erro "Espaco em disco insuficiente (minimo 500MB necessario)"
    exit 1
}
Write-Log "[OK] Espaco em disco suficiente"

# ============================================================
# VERIFICACAO RAPIDA DO CHOCOLATEY
# ============================================================
$chocoExe = "C:\ProgramData\chocolatey\bin\choco.exe"
if (!(Test-Path $chocoExe)) {
    Write-Log "Chocolatey nao encontrado. Instalando..."
    try {
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
        $installScript = "$env:TEMP\choco_install.ps1"
        Invoke-WebRequest -Uri 'https://community.chocolatey.org/install.ps1' -OutFile $installScript -UseBasicParsing -ErrorAction Stop
        & $installScript
        Remove-Item $installScript -Force -ErrorAction SilentlyContinue
        $env:Path += ";$env:ProgramData\chocolatey\bin"
        Write-Log "Chocolatey instalado com sucesso"
    } catch {
        Write-Erro "Falha ao instalar Chocolatey: $_"
        exit 1
    }
}

# ============================================================
# LOOP DE INSTALACAO COM RETRY SIMPLIFICADO
# ============================================================
Write-Log "Atualizando $TotalPrograma programas..."

foreach ($prog in $Programas) {
    $ProgAtual++
    Write-Log "[$ProgAtual/$TotalPrograma] $prog"
    
    # Tenta ate 2 vezes
    $instalado = $false
    for ($tentativa = 1; $tentativa -le 2; $tentativa++) {
        try {
            $output = & $chocoExe upgrade $prog -y --no-progress --limit-output 2>&1
            $chocoExitCode = $LASTEXITCODE  # SALVA IMEDIATAMENTE
            
            if ($chocoExitCode -eq 0 -or $chocoExitCode -eq 1641 -or $chocoExitCode -eq 1638) {
                Write-Log "  [OK] $prog instalado/atualizado"
                $SucessoCount++
                $instalado = $true
                break
            } elseif ($chocoExitCode -eq 3010) {
                Write-Log "  [OK] $prog instalado/atualizado. REINICIO NECESSARIO (3010)."
                $RebootPending = $true
                $SucessoCount++
                $instalado = $true
                break
            } else {
                Write-Log "  [AVISO] $prog falhou (codigo $chocoExitCode) - Tentativa $tentativa"
            }
        } catch {
            Write-Log "  [AVISO] $prog excecao: $_"
        }
        
        if ($tentativa -lt 2) { Start-Sleep -Seconds 3 }
    }
    
    # Health check POS-INSTALACAO (somente se instalou com sucesso)
    if ($instalado) {
        if (Test-AppInstalled -AppName $prog) {
            Write-Log "  [OK] $prog health check passou"
        } else {
            Write-Log "  [AVISO] $prog instalado mas health check inconclusivo"
        }
    }
    
    if (!$instalado) {
        Write-Erro "$prog falhou apos 2 tentativas"
        $FalhaCount++
    }
}

# ============================================================
# RESUMO FINAL
# ============================================================
if ($RebootPending) {
    Write-Log "Concluido: $SucessoCount/$TotalPrograma sucessos, $FalhaCount falhas. REINICIO PENDENTE."
} else {
    Write-Log "Concluido: $SucessoCount/$TotalPrograma sucessos, $FalhaCount falhas"
}
Write-Log "=== FIM DA ATUALIZACAO ==="

exit $(if ($FalhaCount -gt 0) { 1 } else { 0 })
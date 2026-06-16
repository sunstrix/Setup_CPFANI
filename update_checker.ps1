# update_checker.ps1 — V5.9.5.2 (Setup Automatizado CP Fani)
# Executa atualizacoes automaticas no logon do usuario (Versao Otimizada e Robusta)

# Forca UTF-8 para evitar caracteres corrompidos no log
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

# ============================================================
# CONFIGURACOES GLOBAIS
# ============================================================
$LogDir = "C:\Scripts\Logs"
$LogFile = "$LogDir\cpfani_update.log"
$ChocoExe = "C:\ProgramData\chocolatey\bin\choco.exe"

# ============================================================
# PREPARACAO DO DIRETORIO DE LOG
# ============================================================
try {
    if (!(Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction Stop | Out-Null
    }
} catch {
    Write-Host "[ERRO] Nao foi possivel criar diretorio de logs: $LogDir" -ForegroundColor Red
    exit 1
}

# ============================================================
# SISTEMA DE LOG APRIMORADO
# ============================================================
function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    try {
        "[$timestamp] [$Level] $Msg" | Add-Content -Path $LogFile -Encoding UTF8 -ErrorAction Stop
    } catch {
        # Fallback silencioso para nao atrapalhar o logon
    }
}

# ============================================================
# VERIFICACAO DE EXECUCAO DUPLICADA NO MESMO DIA
# ============================================================
function Test-AlreadyRanToday {
    if (Test-Path $LogFile) {
        $today = Get-Date -Format "yyyy-MM-dd"
        # CORRECAO: Procura pela data no inicio da linha de log de fim, nao no final
        # O formato de log eh: [yyyy-MM-dd HH:mm:ss] [INFO] === Fim da verificacao (2026-06-16) ===
        $pattern = [regex]::Escape("Fim da verificacao ($today)")
        $logContent = Get-Content -Path $LogFile -Tail 30 -ErrorAction SilentlyContinue
        if ($logContent -match $pattern) {
            return $true
        }
    }
    return $false
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
# INICIO DA EXECUCAO
# ============================================================
Write-Log "=== Inicio da verificacao de atualizacoes CP Fani V5.9.5.2 ==="

# 1. Verifica se ja rodou hoje para evitar sobrecarga no logon
if (Test-AlreadyRanToday) {
    Write-Log "Atualizacoes ja verificadas hoje. Pulando execucao." "INFO"
    exit 0
}

# 2. Verifica privilegios administrativos
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Log "AVISO: Script executado sem privilegios de Administrador. Algumas atualizacoes podem falhar." "WARNING"
}

# 3. Verifica espaco em disco
Write-Log "Verificando espaco em disco..." "INFO"
if (-not (Test-DiskSpace -MinMB 500)) {
    Write-Log "AVISO: Espaco em disco insuficiente (minimo 500MB necessario). Pulando atualizacoes." "WARNING"
    Write-Log "=== Fim da verificacao (Sem Espaco) ===" "INFO"
    exit 0
}
Write-Log "[OK] Espaco em disco suficiente" "INFO"

# 4. Verifica conexao com internet
$internetOk = $false
if (Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet -ErrorAction SilentlyContinue) {
    $internetOk = $true
} else {
    try {
        # CORRECAO: Usa HTTPS em vez de HTTP
        $null = Invoke-WebRequest -Uri "https://www.google.com" -TimeoutSec 10 -UseBasicParsing -ErrorAction SilentlyContinue
        $internetOk = $true
    } catch {
        $internetOk = $false
    }
}

if (-not $internetOk) {
    Write-Log "Sem conexao com internet. Pulando atualizacoes." "WARNING"
    Write-Log "=== Fim da verificacao (Sem Internet) ===" "INFO"
    exit 0
}

Write-Log "[OK] Conexao com internet confirmada." "INFO"

# 5. Atualiza Chocolatey e pacotes
if (Test-Path $ChocoExe) {
    Write-Log "Verificando atualizacoes do Chocolatey..." "INFO"
    try {
        # Executa em segundo plano para nao travar a tela de logon
        $chocoOutput = & $ChocoExe upgrade all -y --no-progress --limit-output 2>&1
        $chocoExit = $LASTEXITCODE  # SALVA IMEDIATAMENTE
        
        if ($chocoExit -eq 0 -or $chocoExit -eq 1641 -or $chocoExit -eq 1638) {
            Write-Log "[OK] Pacotes Chocolatey verificados/atualizados com sucesso." "OK"
        } elseif ($chocoExit -eq 3010) {
            Write-Log "[OK] Pacotes Chocolatey atualizados. REINICIO NECESSARIO (3010)." "OK"
        } else {
            Write-Log "Chocolatey retornou codigo de saida: $chocoExit. Verifique o log detalhado se necessario." "WARNING"
        }
    } catch {
        Write-Log "Erro ao executar atualizacao do Chocolatey: $_" "ERROR"
    }
} else {
    Write-Log "Chocolatey nao encontrado. Pulando atualizacao de pacotes." "WARNING"
}

# 6. Atualiza drivers via Windows Update aos domingos
if ((Get-Date).DayOfWeek -eq "Sunday") {
    Write-Log "Domingo: Verificando e aplicando atualizacoes de drivers via Windows Update..." "INFO"
    
    try {
        # CORRECAO: usoclient StartInstall sozinho eh instavel. 
        # Primeiro faz scan, depois install. Fallback para PSWindowsUpdate se disponivel.
        $usoPath = Join-Path $env:SystemRoot "System32\usoclient.exe"
        if (Test-Path $usoPath) {
            # Passo 1: Scan por atualizacoes
            Write-Log "  -> Iniciando scan de atualizacoes..." "INFO"
            $scanProc = Start-Process -FilePath $usoPath -ArgumentList "StartScan" -NoNewWindow -Wait -PassThru -ErrorAction Stop
            
            # Passo 2: Instala atualizacoes encontradas
            Write-Log "  -> Iniciando instalacao de atualizacoes..." "INFO"
            $installProc = Start-Process -FilePath $usoPath -ArgumentList "StartInstall" -NoNewWindow -Wait -PassThru -ErrorAction Stop
            
            if ($installProc.ExitCode -eq 0) {
                Write-Log "[OK] Comando Windows Update (usoclient) executado com sucesso." "OK"
            } else {
                Write-Log "usoclient retornou codigo: $($installProc.ExitCode)." "WARNING"
            }
        } else {
            Write-Log "usoclient.exe nao encontrado. Tentando fallback com PSWindowsUpdate..." "WARNING"
            # Fallback: tenta usar PSWindowsUpdate se estiver instalado
            if (Get-Module -ListAvailable -Name PSWindowsUpdate -ErrorAction SilentlyContinue) {
                Import-Module PSWindowsUpdate -Force -ErrorAction SilentlyContinue
                Get-WUInstall -AcceptAll -IgnoreReboot -ErrorAction SilentlyContinue | Out-Null
                Write-Log "[OK] Windows Update executado via PSWindowsUpdate." "OK"
            } else {
                Write-Log "PSWindowsUpdate nao disponivel. Pulando Windows Update." "WARNING"
            }
        }
    } catch {
        Write-Log "Erro ao executar Windows Update: $_" "ERROR"
    }
} else {
    Write-Log "Hoje nao e domingo. Pulando Windows Update agendado." "INFO"
}

# CORRECAO: Adiciona data explicita no log de fim para deteccao de duplicacao
$todayStr = Get-Date -Format "yyyy-MM-dd"
Write-Log "=== Fim da verificacao ($todayStr) ===" "INFO"
exit 0
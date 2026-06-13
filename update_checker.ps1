# update_checker.ps1 — V5.9.5.2 (Setup Automatizado CP Fani)
# Executa atualizacoes automaticas no logon do usuario (Versao Otimizada e Robusta)

# ============================================================
# CONFIGURACOES GLOBAIS
# ============================================================
$LogDir = "C:\Scripts\Logs"
$LogFile = "$LogDir\cpfani_update.log"
$ChocoExe = "C:\ProgramData\chocolatey\bin\choco.exe"

# ============================================================
# SISTEMA DE LOG APRIMORADO
# ============================================================
function Write-Log {
    param([string]$Msg, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # Garante que o diretorio existe
    if (!(Test-Path $LogDir)) { 
        New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction SilentlyContinue | Out-Null 
    }
    
    # Tenta escrever no log, falhando silenciosamente se nao houver permissao
    try {
        "[$timestamp] [$Level] $Msg" | Add-Content -Path $LogFile -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {
        # Fallback: nao faz nada se nao puder logar, para nao atrapalhar o logon
    }
}

# ============================================================
# VERIFICACAO DE EXECUCAO DUPLICADA NO MESMO DIA (NOVO)
# ============================================================
function Test-AlreadyRanToday {
    if (Test-Path $LogFile) {
        $today = Get-Date -Format "yyyy-MM-dd"
        $logContent = Get-Content -Path $LogFile -Tail 20 -ErrorAction SilentlyContinue
        if ($logContent -match "Fim da verificacao.*$today") {
            return $true
        }
    }
    return $false
}

# ============================================================
# VALIDACAO DE ESPACO EM DISCO (NOVO)
# ============================================================
function Test-DiskSpace {
    param([int]$MinMB = 500)
    try {
        $drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction SilentlyContinue
        if ($drive) {
            $freeSpaceMB = [math]::Round($drive.FreeSpace / 1MB, 2)
            return ($freeSpaceMB -ge $MinMB)
        }
        return $true  # Continua se nao puder verificar
    } catch {
        return $true  # Continua mesmo se falhar
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

# 2. Verifica privilegios administrativos (Avisos, mas nao bloqueia totalmente)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Log "AVISO: Script executado sem privilegios de Administrador. Algumas atualizacoes podem falhar." "WARNING"
}

# 3. Verifica espaco em disco (NOVO)
Write-Log "Verificando espaco em disco..." "INFO"
if (-not (Test-DiskSpace -MinMB 500)) {
    Write-Log "AVISO: Espaco em disco insuficiente (minimo 500MB necessario). Pulando atualizacoes." "WARNING"
    Write-Log "=== Fim da verificacao (Sem Espaco) ===" "INFO"
    exit 0
}
Write-Log "[OK] Espaco em disco suficiente" "INFO"

# 4. Verifica conexao com internet (Mantido, com fallback)
$internetOk = $false
if (Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet -ErrorAction SilentlyContinue) {
    $internetOk = $true
} else {
    # Fallback: teste HTTP rapido
    try {
        $null = Invoke-WebRequest -Uri "http://www.google.com" -TimeoutSec 10 -UseBasicParsing -ErrorAction SilentlyContinue
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

# 5. Atualiza Chocolatey e pacotes (Mantido, com validacao de saida)
if (Test-Path $ChocoExe) {
    Write-Log "Verificando atualizacoes do Chocolatey..." "INFO"
    try {
        # Executa em segundo plano para nao travar a tela de logon
        $chocoOutput = & $ChocoExe upgrade all -y --no-progress --limit-output 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0 -or $exitCode -eq 3010 -or $exitCode -eq 1641 -or $exitCode -eq 1638) {
            Write-Log "[OK] Pacotes Chocolatey verificados/atualizados com sucesso." "OK"
        } else {
            Write-Log "Chocolatey retornou codigo de saida: $exitCode. Verifique o log detalhado se necessario." "WARNING"
        }
    } catch {
        Write-Log "Erro ao executar atualizacao do Chocolatey: $_" "ERROR"
    }
} else {
    Write-Log "Chocolatey nao encontrado. Pulando atualizacao de pacotes." "WARNING"
}

# 6. Atualiza drivers via Windows Update aos domingos (Mantido, com tratamento de erro)
if ((Get-Date).DayOfWeek -eq "Sunday") {
    Write-Log "Domingo: Verificando e aplicando atualizacoes de drivers via Windows Update..." "INFO"
    
    try {
        # usoclient StartInstall requer privilegios elevados para funcionar corretamente
        $process = Start-Process -FilePath "usoclient" -ArgumentList "StartInstall" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
        
        if ($process.ExitCode -eq 0) {
            Write-Log "[OK] Comando Windows Update (usoclient) executado com sucesso." "OK"
        } else {
            Write-Log "usoclient retornou codigo: $($process.ExitCode). Pode exigir privilegios de Administrador." "WARNING"
        }
    } catch {
        Write-Log "Erro ao executar usoclient: $_" "ERROR"
    }
} else {
    Write-Log "Hoje nao e domingo. Pulando Windows Update agendado." "INFO"
}

Write-Log "=== Fim da verificacao ===" "INFO"
exit 0
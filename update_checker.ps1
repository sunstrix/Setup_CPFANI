# update_checker.ps1 — V5.0.3 (Setup Automatizado CP Fani)
# Executa atualizações automáticas no logon do usuário (Versão Otimizada e Robusta)

# ============================================================
# CONFIGURAÇÕES GLOBAIS
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
    
    # Garante que o diretório existe
    if (!(Test-Path $LogDir)) { 
        New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction SilentlyContinue | Out-Null 
    }
    
    # Tenta escrever no log, falhando silenciosamente se não houver permissão
    try {
        "[$timestamp] [$Level] $Msg" | Add-Content -Path $LogFile -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {
        # Fallback: não faz nada se não puder logar, para não atrapalhar o logon
    }
}

# ============================================================
# VERIFICAÇÃO DE EXECUÇÃO DUPLICADA NO MESMO DIA (NOVO)
# ============================================================
function Test-AlreadyRanToday {
    if (Test-Path $LogFile) {
        $today = Get-Date -Format "yyyy-MM-dd"
        $logContent = Get-Content -Path $LogFile -Tail 20 -ErrorAction SilentlyContinue
        if ($logContent -match "Fim da verificação.*$today") {
            return $true
        }
    }
    return $false
}

# ============================================================
# INÍCIO DA EXECUÇÃO
# ============================================================
Write-Log "=== Início da verificação de atualizações CP Fani V5.0.3 ==="

# 1. Verifica se já rodou hoje para evitar sobrecarga no logon
if (Test-AlreadyRanToday) {
    Write-Log "Atualizações já verificadas hoje. Pulando execução." "INFO"
    exit 0
}

# 2. Verifica privilégios administrativos (Avisos, mas não bloqueia totalmente)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Log "AVISO: Script executado sem privilégios de Administrador. Algumas atualizações podem falhar." "WARNING"
}

# 3. Verifica conexão com internet (Mantido, com fallback)
$internetOk = $false
if (Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet -ErrorAction SilentlyContinue) {
    $internetOk = $true
} else {
    # Fallback: teste HTTP rápido
    try {
        $null = Invoke-WebRequest -Uri "http://www.google.com" -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
        $internetOk = $true
    } catch {
        $internetOk = $false
    }
}

if (-not $internetOk) {
    Write-Log "Sem conexão com internet. Pulando atualizações." "WARNING"
    Write-Log "=== Fim da verificação (Sem Internet) ===" "INFO"
    exit 0
}

Write-Log "Conexão com internet confirmada." "INFO"

# 4. Atualiza Chocolatey e pacotes (Mantido, com validação de saída)
if (Test-Path $ChocoExe) {
    Write-Log "Verificando atualizações do Chocolatey..." "INFO"
    try {
        # Executa em segundo plano para não travar a tela de logon
        $chocoOutput = & $ChocoExe upgrade all -y --no-progress --limit-output 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0 -or $exitCode -eq 3010 -or $exitCode -eq 1641 -or $exitCode -eq 1638) {
            Write-Log "Pacotes Chocolatey verificados/atualizados com sucesso." "OK"
        } else {
            Write-Log "Chocolatey retornou código de saída: $exitCode. Verifique o log detalhado se necessário." "WARNING"
        }
    } catch {
        Write-Log "Erro ao executar atualização do Chocolatey: $_" "ERROR"
    }
} else {
    Write-Log "Chocolatey não encontrado. Pulando atualização de pacotes." "WARNING"
}

# 5. Atualiza drivers via Windows Update aos domingos (Mantido, com tratamento de erro)
if ((Get-Date).DayOfWeek -eq "Sunday") {
    Write-Log "Domingo: Verificando e aplicando atualizações de drivers via Windows Update..." "INFO"
    
    try {
        # usoclient StartInstall requer privilégios elevados para funcionar corretamente
        $process = Start-Process -FilePath "usoclient" -ArgumentList "StartInstall" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
        
        if ($process.ExitCode -eq 0) {
            Write-Log "Comando Windows Update (usoclient) executado com sucesso." "OK"
        } else {
            Write-Log "usoclient retornou código: $($process.ExitCode). Pode exigir privilégios de Administrador." "WARNING"
        }
    } catch {
        Write-Log "Erro ao executar usoclient: $_" "ERROR"
    }
} else {
    Write-Log "Hoje não é domingo. Pulando Windows Update agendado." "INFO"
}

Write-Log "=== Fim da verificação ===" "INFO"
exit 0
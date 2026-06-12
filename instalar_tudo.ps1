# =======================================================
# INSTALADOR / ATUALIZADOR CHOCOLATEY (CP FANI)
# Versão Leve para Startup - V5.9.4
# Otimizado para execução automática no boot do Windows
# =======================================================

# Configurações básicas
$PastaLog       = "C:\Scripts\Logs"
$ArquivoLog     = "$PastaLog\instalar_tudo.log"
$ArquivoErros   = "$PastaLog\instalar_tudo_erros.log"

# Lista de programas (mantida concisa)
$Programas      = @("googlechrome", "anydesk", "7zip", "flameshot", "teamviewer", "vlc", "winrar", "vcredist-all", "ditto")

$TotalPrograma  = $Programas.Count
$ProgAtual      = 0
$SucessoCount   = 0
$FalhaCount     = 0

# ============================================================
# SISTEMA DE LOG SIMPLIFICADO (LEVE)
# ============================================================
function Write-Log {
    param([string]$Mensagem)
    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    if (!(Test-Path $PastaLog)) { New-Item -ItemType Directory -Path $PastaLog -Force -ErrorAction SilentlyContinue | Out-Null }
    "$timestamp | $Mensagem" | Add-Content -Path $ArquivoLog -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Write-Erro {
    param([string]$Mensagem)
    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    if (!(Test-Path $PastaLog)) { New-Item -ItemType Directory -Path $PastaLog -Force -ErrorAction SilentlyContinue | Out-Null }
    "$timestamp | ERRO: $Mensagem" | Add-Content -Path $ArquivoErros -Encoding UTF8 -ErrorAction SilentlyContinue
}

# ============================================================
# INÍCIO DA EXECUÇÃO
# ============================================================
Write-Log "=== INÍCIO DA ATUALIZAÇÃO V5.9.4 (STARTUP) ==="

# Validação rápida de privilégios administrativos
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Erro "Script requer privilégios administrativos"
    exit 1
}

# ============================================================
# VERIFICAÇÃO RÁPIDA DO CHOCOLATEY
# ============================================================
$chocoExe = "C:\ProgramData\chocolatey\bin\choco.exe"
if (!(Test-Path $chocoExe)) {
    Write-Log "Chocolatey não encontrado. Instalando..."
    try {
        [System.Net.ServicePointManager]::SecurityProtocol = 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        $env:Path += ";$env:ProgramData\chocolatey\bin"
        Write-Log "Chocolatey instalado"
    } catch {
        Write-Erro "Falha ao instalar Chocolatey: $_"
        exit 1
    }
}

# ============================================================
# LOOP DE INSTALAÇÃO COM RETRY SIMPLIFICADO
# ============================================================
Write-Log "Atualizando $TotalPrograma programas..."

foreach ($prog in $Programas) {
    $ProgAtual++
    Write-Log "[$ProgAtual/$TotalPrograma] $prog"
    
    # Tenta até 2 vezes
    $instalado = $false
    for ($tentativa = 1; $tentativa -le 2; $tentativa++) {
        try {
            $output = & $chocoExe upgrade $prog -y --no-progress --limit-output 2>&1
            
            if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 3010 -or $LASTEXITCODE -eq 1641 -or $LASTEXITCODE -eq 1638) {
                Write-Log "  ✓ $prog OK"
                $SucessoCount++
                $instalado = $true
                break
            } else {
                Write-Log "  ⚠ $prog falhou (código $LASTEXITCODE) - Tentativa $tentativa"
            }
        } catch {
            Write-Log "  ⚠ $prog exceção: $_"
        }
        
        if ($tentativa -lt 2) { Start-Sleep -Seconds 3 }
    }
    
    if (!$instalado) {
        Write-Erro "$prog falhou após 2 tentativas"
        $FalhaCount++
    }
}

# ============================================================
# RESUMO FINAL
# ============================================================
Write-Log "Concluído: $SucessoCount/$TotalPrograma sucessos, $FalhaCount falhas"
Write-Log "=== FIM DA ATUALIZAÇÃO ==="

exit $(if ($FalhaCount -gt 0) { 1 } else { 0 })
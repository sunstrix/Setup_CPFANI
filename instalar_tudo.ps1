# =======================================================
# INSTALADOR / ATUALIZADOR CHOCOLATEY (CP FANI)
# Com logs detalhados de Debug - V5.9.3
# =======================================================

$PastaLog       = "C:\Scripts\Logs"
$ArquivoLog     = "$PastaLog\instalar_tudo.log"
$ArquivoErros   = "$PastaLog\instalar_tudo_erros.log"
$ArquivoDebug   = "$PastaLog\instalar_tudo_debug.log"

$Programas      = @("googlechrome", "anydesk", "7zip", "flameshot", "teamviewer", "vlc", "winrar", "vcredist-all", "ditto")

$TotalPrograma  = $Programas.Count
$ProgAtual      = 0
$SucessoCount   = 0
$FalhaCount     = 0

function Write-Log {
    param([string]$Mensagem)
    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    if (!(Test-Path $PastaLog)) { New-Item -ItemType Directory -Path $PastaLog -Force | Out-Null }
    "$timestamp | $Mensagem" | Add-Content -Path $ArquivoLog -Encoding UTF8
}

function Write-Erro {
    param([string]$Mensagem)
    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    if (!(Test-Path $PastaLog)) { New-Item -ItemType Directory -Path $PastaLog -Force | Out-Null }
    "$timestamp | ERRO: $Mensagem" | Add-Content -Path $ArquivoErros -Encoding UTF8
}

function Write-DebugLog {
    param([string]$Mensagem)
    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    if (!(Test-Path $PastaLog)) { New-Item -ItemType Directory -Path $PastaLog -Force | Out-Null }
    "$timestamp | $Mensagem" | Add-Content -Path $ArquivoDebug -Encoding UTF8
}

Write-Log "=== INÍCIO DA ATUALIZAÇÃO DE SOFTWARE V5.9.3 ==="

if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Erro "Este script precisa de ser executado como Administrador."
    exit
}

$chocoExe = "C:\ProgramData\chocolatey\bin\choco.exe"
if (!(Test-Path $chocoExe)) {
    Write-Log "Chocolatey não encontrado. A iniciar a instalação..."
    try {
        [System.Net.ServicePointManager]::SecurityProtocol = 3072
        $script = (New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')
        Invoke-Expression $script
        $env:Path += ";$env:ProgramData\chocolatey\bin"
        Write-Log "Chocolatey instalado."
    } catch {
        Write-Erro "Falha ao instalar Chocolatey: $_"
        return
    }
}

Write-Log "A iniciar instalação / atualização de $TotalPrograma programas..."

foreach ($prog in $Programas) {
    $ProgAtual++
    Write-Log "[$ProgAtual/$TotalPrograma] A processar via Choco: $prog"
    Write-DebugLog "`n--- EXECUTANDO: choco upgrade $prog -y ---"
    
    try {
        $output = & $chocoExe upgrade $prog -y --ignore-checksums 2>&1
        Write-DebugLog $output
        
        if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 3010 -or $LASTEXITCODE -eq 1641 -or $LASTEXITCODE -eq 1638) {
            Write-Log "  [SUCESSO] $prog instalado/atualizado"
            $SucessoCount++
        } else {
            Write-Erro "$prog falhou com código $LASTEXITCODE. Verifique instalar_tudo_debug.log."
            $FalhaCount++
        }
    } catch {
        Write-Erro "$prog gerou exceção: $_"
        Write-DebugLog $_
        $FalhaCount++
    }
}

Write-Log "RESUMO: $SucessoCount atualizados com sucesso. $FalhaCount falhas."
Write-Log "=== FIM DA ATUALIZAÇÃO ==="
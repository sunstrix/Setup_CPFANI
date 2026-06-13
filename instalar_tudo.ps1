# =======================================================
# INSTALADOR / ATUALIZADOR CHOCOLATEY (CP FANI)
# Versao Leve para Startup - V5.9.5.2
# Otimizado para execucao automatica no boot do Windows
# =======================================================

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
# VALIDACAO DE CONECTIVIDADE (NOVO)
# ============================================================
function Test-InternetConnection {
    try {
        $testHosts = @("8.8.8.8", "1.1.1.1", "www.google.com")
        foreach ($testHost in $testHosts) {
            if (Test-Connection -ComputerName $testHost -Count 1 -Quiet -ErrorAction SilentlyContinue) {
                return $true
            }
        }
        # Fallback: tenta HTTP
        $response = Invoke-WebRequest -Uri "http://www.google.com" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
        return ($response.StatusCode -eq 200)
    } catch {
        return $false
    }
}

# ============================================================
# VALIDACAO DE ESPACO EM DISCO (NOVO)
# ============================================================
function Test-DiskSpace {
    param([int]$MinMB = 500)
    try {
        $drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction SilentlyContinue
        $freeSpaceMB = [math]::Round($drive.FreeSpace / 1MB, 2)
        return ($freeSpaceMB -ge $MinMB)
    } catch {
        return $true  # Continua mesmo se falhar
    }
}

# ============================================================
# HEALTH CHECK POS-INSTALACAO (NOVO)
# ============================================================
function Test-AppInstalled {
    param([string]$AppName)
    try {
        # Verifica se executavel existe no PATH
        $whereResult = where.exe $AppName 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
        
        # Verifica se pacote esta listado no Chocolatey
        $chocoList = & choco list --local-only --limit-output 2>&1
        if ($chocoList -match $AppName) {
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

# Validacao de conectividade com internet (NOVO)
Write-Log "Verificando conectividade com internet..."
if (!(Test-InternetConnection)) {
    Write-Erro "Sem conectividade com internet. Abortando atualizacao."
    exit 1
}
Write-Log "[OK] Conectividade confirmada"

# Validacao de espaco em disco (NOVO)
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
            
            if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 3010 -or $LASTEXITCODE -eq 1641 -or $LASTEXITCODE -eq 1638) {
                Write-Log "  [OK] $prog instalado"
                
                # ============================================================
                # HEALTH CHECK POS-INSTALACAO (NOVO)
                # ============================================================
                if (Test-AppInstalled -AppName $prog) {
                    Write-Log "  [OK] $prog health check passou"
                } else {
                    Write-Log "  [AVISO] $prog instalado mas health check inconclusivo"
                }
                
                $SucessoCount++
                $instalado = $true
                break
            } else {
                Write-Log "  [AVISO] $prog falhou (codigo $LASTEXITCODE) - Tentativa $tentativa"
            }
        } catch {
            Write-Log "  [AVISO] $prog excecao: $_"
        }
        
        if ($tentativa -lt 2) { Start-Sleep -Seconds 3 }
    }
    
    if (!$instalado) {
        Write-Erro "$prog falhou apos 2 tentativas"
        $FalhaCount++
    }
}

# ============================================================
# RESUMO FINAL
# ============================================================
Write-Log "Concluido: $SucessoCount/$TotalPrograma sucessos, $FalhaCount falhas"
Write-Log "=== FIM DA ATUALIZACAO ==="

exit $(if ($FalhaCount -gt 0) { 1 } else { 0 })
# =======================================================
# INSTALADOR / ATUALIZADOR CHOCOLATEY (CP FANI)
# Com logs detalhados de Debug - V5.9.4
# =======================================================

$ScriptDir = if ($env:SCRIPT_DIR) { $env:SCRIPT_DIR } else { "C:\Scripts" }
$PastaLog = Join-Path $ScriptDir "Logs"

try {
    if (!(Test-Path $PastaLog)) {
        New-Item -ItemType Directory -Path $PastaLog -Force | Out-Null
    }
} catch {
    $PastaLog = Join-Path $env:TEMP "Setup_CPFANI_Logs"
    if (!(Test-Path $PastaLog)) {
        New-Item -ItemType Directory -Path $PastaLog -Force | Out-Null
    }
}

$ArquivoLog     = Join-Path $PastaLog "instalar_tudo.log"
$ArquivoErros   = Join-Path $PastaLog "instalar_tudo_erros.log"
$ArquivoDebug   = Join-Path $PastaLog "instalar_tudo_debug.log"

$Programas      = @(
    "googlechrome",
    "anydesk",
    "7zip",
    "flameshot",
    "teamviewer",
    "vlc",
    "winrar",
    "vcredist-all",
    "ditto"
)

$TotalPrograma  = $Programas.Count
$ProgAtual      = 0
$SucessoCount   = 0
$FalhaCount     = 0
$MaxRetries     = 2

function Ensure-LogDir {
    if (!(Test-Path $PastaLog)) {
        New-Item -ItemType Directory -Path $PastaLog -Force | Out-Null
    }
}

function Write-Log {
    param([string]$Mensagem)

    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    Ensure-LogDir
    "$timestamp | $Mensagem" | Add-Content -Path $ArquivoLog -Encoding ASCII
}

function Write-Erro {
    param([string]$Mensagem)

    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    Ensure-LogDir
    "$timestamp | ERRO: $Mensagem" | Add-Content -Path $ArquivoErros -Encoding ASCII
}

function Write-DebugLog {
    param([object]$Mensagem)

    $timestamp = Get-Date -Format 'dd/MM/yyyy HH:mm:ss'
    Ensure-LogDir

    $texto = $Mensagem | Out-String
    "$timestamp | $texto" | Add-Content -Path $ArquivoDebug -Encoding ASCII
}

function Get-RealPythonCommand {
    $candidates = @()

    try {
        $cmds = @(Get-Command python.exe -ErrorAction SilentlyContinue)
        foreach ($c in $cmds) {
            if ($c.Source) {
                $candidates += $c.Source
            }
        }
    } catch {}

    try {
        $cmds = @(Get-Command python3.exe -ErrorAction SilentlyContinue)
        foreach ($c in $cmds) {
            if ($c.Source) {
                $candidates += $c.Source
            }
        }
    } catch {}

    foreach ($exe in $candidates) {
        if ($exe -like "*WindowsApps*") {
            continue
        }

        try {
            $versionOutput = & $exe --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$versionOutput" -match "Python 3") {
                return $exe
            }
        } catch {}
    }

    try {
        $pyCmd = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pyCmd) {
            $versionOutput = & py.exe -3 --version 2>&1
            if ($LASTEXITCODE -eq 0 -and "$versionOutput" -match "Python 3") {
                return "py.exe -3"
            }
        }
    } catch {}

    return $null
}

function Install-ChocolateySafe {
    $url = "https://community.chocolatey.org/install.ps1"
    $tempScript = Join-Path $env:TEMP "choco_install.ps1"

    $expectedHash = if ($env:CPFANI_CHOCO_INSTALL_SHA256) {
        $env:CPFANI_CHOCO_INSTALL_SHA256.Trim().ToUpper()
    } else {
        "44E045ED5350758616D664C5AF631E7F2CD10165F5BF2BD82CBF3A0BB8F63462"
    }

    try {
        Write-Log "Chocolatey nao encontrado. Baixando script oficial..."

        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
        (New-Object System.Net.WebClient).DownloadFile($url, $tempScript)

        if (!(Test-Path $tempScript)) {
            throw "Arquivo de instalacao do Chocolatey nao foi criado."
        }

        $actualHash = (Get-FileHash -Path $tempScript -Algorithm SHA256).Hash.ToUpper()

        if ($actualHash -ne $expectedHash) {
            throw "Hash SHA256 invalido para install.ps1 do Chocolatey. Esperado: $expectedHash | Obtido: $actualHash"
        }

        Write-Log "[OK] Hash SHA256 do script Chocolatey validado."

        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $tempScript

        if ($LASTEXITCODE -ne 0) {
            throw "Instalacao do Chocolatey falhou com codigo $LASTEXITCODE"
        }

        $env:Path += ";$env:ProgramData\chocolatey\bin"
        Write-Log "Chocolatey instalado."
    } catch {
        Write-Erro "Falha ao instalar Chocolatey: $_"
        exit 1
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-ChocoUpgrade {
    param([string]$Prog)

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-DebugLog "`n--- EXECUTANDO (tentativa $attempt/$MaxRetries): choco upgrade $Prog -y ---"

        try {
            $output = & $chocoExe upgrade $Prog -y --no-progress --limit-output --ignore-checksums 2>&1
            Write-DebugLog $output

            if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 3010 -or $LASTEXITCODE -eq 1641 -or $LASTEXITCODE -eq 1638) {
                Write-Log "  [SUCESSO] $Prog instalado/atualizado"
                return $true
            } else {
                Write-Erro "$Prog falhou com codigo $LASTEXITCODE. Verifique instalar_tudo_debug.log."
            }
        } catch {
            Write-Erro "$Prog gerou excecao: $_"
            Write-DebugLog $_
        }

        if ($attempt -lt $MaxRetries) {
            Start-Sleep -Seconds 5
        }
    }

    return $false
}

Write-Log "=== INICIO DA ATUALIZACAO DE SOFTWARE V5.9.4 ==="

if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Erro "Este script precisa de ser executado como Administrador."
    exit 1
}

$pythonCmd = Get-RealPythonCommand
if ($pythonCmd) {
    Write-Log "[OK] Python real detectado: $pythonCmd"
} else {
    Write-Log "[AVISO] Python real nao detectado. Stub da Microsoft Store ignorado."
}

$chocoExe = "$env:ProgramData\chocolatey\bin\choco.exe"

if (!(Test-Path $chocoExe)) {
    Install-ChocolateySafe
}

if (!(Test-Path $chocoExe)) {
    $cmd = Get-Command choco.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $chocoExe = $cmd.Source
    }
}

if (!(Test-Path $chocoExe)) {
    Write-Erro "Chocolatey nao disponivel apos tentativa de instalacao."
    exit 1
}

Write-Log "A iniciar instalacao / atualizacao de $TotalPrograma programas..."

foreach ($prog in $Programas) {
    $ProgAtual++
    Write-Log "[$ProgAtual/$TotalPrograma] A processar via Choco: $prog"

    $resultado = Invoke-ChocoUpgrade -Prog $prog

    if ($resultado) {
        $SucessoCount++
    } else {
        $FalhaCount++
    }
}

Write-Log "RESUMO: $SucessoCount atualizados com sucesso. $FalhaCount falhas."
Write-Log "=== FIM DA ATUALIZACAO ==="

if ($FalhaCount -gt 0) {
    exit 1
} else {
    exit 0
}
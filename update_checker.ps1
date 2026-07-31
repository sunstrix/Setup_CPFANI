# =======================================================
# update_checker.ps1 - V5.1.0 (Setup Automatizado CP Fani)
# Executa verificacao de atualizacao no logon ou agendamento
# =======================================================

$ScriptDir = if ($env:SCRIPT_DIR) {
    $env:SCRIPT_DIR
} elseif ($PSScriptRoot) {
    $PSScriptRoot
} else {
    "C:\Scripts"
}

try {
    if (!(Test-Path $ScriptDir)) {
        New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
    }
} catch {
    $ScriptDir = Join-Path ([System.IO.Path]::GetTempPath()) "Setup_CPFANI"
    if (!(Test-Path $ScriptDir)) {
        New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
    }
}

$LogFile = Join-Path $ScriptDir "cpfani_update.log"
$RepoRawBase = "https://raw.githubusercontent.com/sunstrix/Setup_CPFANI/main"
$ProgressPreference = "SilentlyContinue"

try {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
} catch {}

function Write-Log {
    param([string]$Msg)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logDir = Split-Path $LogFile -Parent

    if (!(Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    "$timestamp | $Msg" | Add-Content -Path $LogFile -Encoding ASCII
}

function Write-Erro {
    param([string]$Msg)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logDir = Split-Path $LogFile -Parent

    if (!(Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    "$timestamp | ERRO: $Msg" | Add-Content -Path $LogFile -Encoding ASCII
}

function Get-GitHubHeaders {
    $headers = @{
        "User-Agent" = "Setup-CPFANI"
    }

    if ($env:GITHUB_TOKEN) {
        $headers["Authorization"] = "Bearer $($env:GITHUB_TOKEN)"
    }

    return $headers
}

function Get-CpfaniRemoteText {
    param(
        [string]$Url,
        [switch]$Optional
    )

    try {
        $headers = Get-GitHubHeaders
        $response = Invoke-WebRequest -Uri $Url -Headers $headers -UseBasicParsing -TimeoutSec 30
        return $response.Content
    } catch {
        if ($Optional) {
            Write-Log "[AVISO] Falha ao obter recurso opcional: $Url | $_"
        } else {
            Write-Erro "Falha ao obter recurso: $Url | $_"
        }
        return $null
    }
}

function Get-CpfaniRemoteSha256 {
    param([string]$ShaUrl)

    $content = Get-CpfaniRemoteText -Url $ShaUrl -Optional
    if (-not $content) {
        return ""
    }

    $firstToken = ($content -split "\s+")[0].Trim().ToUpper()
    if ($firstToken -match "^[0-9A-F]{64}$") {
        return $firstToken
    }

    return ""
}

function Get-VersionNumbers {
    param([string]$Version)

    $nums = @()
    foreach ($match in [regex]::Matches($Version, "\d+")) {
        $nums += [int]$match.Value
    }

    while ($nums.Count -lt 3) {
        $nums += 0
    }

    return ,$nums
}

function Compare-SemVer {
    param(
        [string]$A,
        [string]$B
    )

    $pa = Get-VersionNumbers -Version $A
    $pb = Get-VersionNumbers -Version $B

    for ($i = 0; $i -lt 3; $i++) {
        if ($pa[$i] -gt $pb[$i]) { return 1 }
        if ($pa[$i] -lt $pb[$i]) { return -1 }
    }

    return 0
}

function Save-CpfaniFileFromUrl {
    param(
        [string]$RelativePath,
        [string]$Url,
        [string]$ExpectedSha256
    )

    if (-not $ExpectedSha256) {
        Write-Erro "Hash SHA256 nao informado para $RelativePath. Atualizacao bloqueada por seguranca."
        return $false
    }

    $dest = Join-Path $ScriptDir $RelativePath
    $destDir = Split-Path $dest -Parent
    $tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ("cpfani_" + [guid]::NewGuid().ToString("N"))

    try {
        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        $headers = Get-GitHubHeaders
        Invoke-WebRequest -Uri $Url -OutFile $tempPath -Headers $headers -UseBasicParsing -TimeoutSec 120

        if (!(Test-Path $tempPath)) {
            throw "Arquivo temporario nao foi criado."
        }

        $actualHash = (Get-FileHash -Path $tempPath -Algorithm SHA256).Hash.ToUpper()
        $expectedHash = $ExpectedSha256.Trim().ToUpper()

        if ($actualHash -ne $expectedHash) {
            throw "Hash SHA256 invalido. Esperado: $expectedHash | Obtido: $actualHash"
        }

        if (Test-Path $dest) {
            $existingHash = (Get-FileHash -Path $dest -Algorithm SHA256).Hash.ToUpper()
            if ($existingHash -eq $actualHash) {
                Write-Log "[OK] Arquivo ja esta atual: $RelativePath"
                return $true
            }

            Copy-Item -Path $dest -Destination "$dest.bak" -Force
        }

        Move-Item -Path $tempPath -Destination $dest -Force
        Write-Log "[OK] Arquivo atualizado com validacao SHA256: $RelativePath"
        return $true
    } catch {
        Write-Erro "Falha ao atualizar $RelativePath | $_"
        return $false
    } finally {
        if (Test-Path $tempPath) {
            Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Update-CpfaniProjectFiles {
    $localVersionFile = Join-Path $ScriptDir "version.txt"
    $localVersion = "0.0.0"

    if (Test-Path $localVersionFile) {
        $localVersion = (Get-Content $localVersionFile -Raw).Trim()
    }

    $remoteVersionUrl = "$RepoRawBase/version.txt"
    $remoteVersion = Get-CpfaniRemoteText -Url $remoteVersionUrl -Optional

    if (-not $remoteVersion) {
        Write-Log "[AVISO] version.txt remoto nao disponivel. Pulando atualizacao de arquivos."
        return
    }

    $remoteVersion = $remoteVersion.Trim()
    Write-Log "Versao local: $localVersion | Versao remota: $remoteVersion"

    $cmp = Compare-SemVer -A $remoteVersion -B $localVersion
    if ($cmp -le 0) {
        Write-Log "[OK] Projeto ja esta na versao mais recente."
        return
    }

    Write-Log "Nova versao detectada. Iniciando atualizacao segura..."

    $manifestUrl = "$RepoRawBase/update_manifest.json"
    $manifestText = Get-CpfaniRemoteText -Url $manifestUrl -Optional

    if ($manifestText) {
        try {
            $manifest = $manifestText | ConvertFrom-Json
            $updatedCount = 0

            foreach ($item in $manifest.files) {
                if (-not $item.path) { continue }

                $fileUrl = if ($item.url) { $item.url } else { "$RepoRawBase/$($item.path)" }
                $fileHash = if ($item.sha256) { $item.sha256 } else { "" }

                if (-not $fileHash) {
                    Write-Log "[AVISO] Hash ausente no manifest para $($item.path). Arquivo ignorado."
                    continue
                }

                $ok = Save-CpfaniFileFromUrl -RelativePath $item.path -Url $fileUrl -ExpectedSha256 $fileHash
                if ($ok) { $updatedCount++ }
            }

            Write-Log "[OK] Atualizacao via manifest concluida. Arquivos processados: $updatedCount"
            return
        } catch {
            Write-Erro "Falha ao processar update_manifest.json: $_"
        }
    }

    Write-Log "[INFO] update_manifest.json nao disponivel. Atualizando apenas version.txt."

    $versionHashUrl = "$remoteVersionUrl.sha256"
    $versionHash = Get-CpfaniRemoteSha256 -ShaUrl $versionHashUrl

    if (-not $versionHash) {
        Write-Erro "Hash SHA256 de version.txt nao disponivel. Atualizacao abortada por seguranca."
        return
    }

    $ok = Save-CpfaniFileFromUrl -RelativePath "version.txt" -Url $remoteVersionUrl -ExpectedSha256 $versionHash
    if ($ok) {
        Write-Log "[OK] version.txt atualizado para $remoteVersion"
    } else {
        Write-Erro "Falha ao atualizar version.txt."
    }
}

Write-Log "=== Inicio da verificacao de atualizacoes CP Fani ==="

if (-not (Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet)) {
    Write-Log "Sem conexao com internet. Pulando atualizacoes."
    exit 0
}

Update-CpfaniProjectFiles

$ChocoExe = "$env:ProgramData\chocolatey\bin\choco.exe"
if (!(Test-Path $ChocoExe)) {
    $cmd = Get-Command choco.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $ChocoExe = $cmd.Source
    }
}

if (Test-Path $ChocoExe) {
    Write-Log "Verificando atualizacoes do Chocolatey..."

    try {
        $output = & $ChocoExe upgrade all -y --no-progress --limit-output 2>&1
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0 -or $exitCode -in @(3010, 1641, 1638)) {
            Write-Log "Pacotes Chocolatey verificados com sucesso (codigo $exitCode)."
        } else {
            Write-Erro "Chocolatey retornou codigo $exitCode."
            Write-Log "Saida: $output"
        }
    } catch {
        Write-Erro "Excecao ao executar Chocolatey: $_"
    }
} else {
    Write-Log "Chocolatey nao encontrado. Pulando atualizacao de pacotes."
}

if ((Get-Date).DayOfWeek -eq "Sunday") {
    Write-Log "Domingo: Verificando atualizacoes de drivers..."

    try {
        if (Get-Command "usoclient" -ErrorAction SilentlyContinue) {
            $wuOutput = Start-Process -FilePath "usoclient" -ArgumentList "StartInstall" -NoNewWindow -Wait -PassThru

            if ($wuOutput.ExitCode -eq 0) {
                Write-Log "Windows Update executado com sucesso."
            } else {
                Write-Log "Windows Update retornou codigo $($wuOutput.ExitCode)."
            }
        } else {
            Write-Log "usoclient nao encontrado. Pulando Windows Update."
        }
    } catch {
        Write-Erro "Excecao ao executar Windows Update: $_"
    }
}

Write-Log "=== Fim da verificacao ==="
exit 0
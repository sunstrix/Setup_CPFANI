# update_checker.ps1 — V5.0.2 (Setup Automatizado CP Fani)
# Executa atualizações automáticas no logon do usuário

$LogDir = "C:\Scripts"
$LogFile = "$LogDir\cpfani_update.log"

function Write-Log {
    param([string]$Msg)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
    "$timestamp | $Msg" | Add-Content -Path $LogFile -Encoding UTF8
}

Write-Log "=== Início da verificação de atualizações CP Fani ==="

# Verifica conexão com internet
if (-not (Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet)) {
    Write-Log "Sem conexão com internet. Pulando atualizações."
    exit 0
}

# Atualiza Chocolatey e pacotes
$ChocoExe = "C:\ProgramData\chocolatey\bin\choco.exe"
if (Test-Path $ChocoExe) {
    Write-Log "Verificando atualizações do Chocolatey..."
    try {
        $output = & $ChocoExe upgrade all -y --no-progress --limit-output 2>&1
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0 -or $exitCode -in @(3010, 1641, 1638)) {
            Write-Log "Pacotes Chocolatey verificados com sucesso (código $exitCode)."
        } else {
            Write-Log "Chocolatey retornou código $exitCode. Possível erro."
            Write-Log "Saída: $output"
        }
    } catch {
        Write-Log "Exceção ao executar Chocolatey: $_"
    }
} else {
    Write-Log "Chocolatey não encontrado. Pulando atualização de pacotes."
}

# Atualiza drivers via Windows Update aos domingos
if ((Get-Date).DayOfWeek -eq "Sunday") {
    Write-Log "Domingo: Verificando atualizações de drivers..."
    try {
        if (Get-Command "usoclient" -ErrorAction SilentlyContinue) {
            $wuOutput = Start-Process -FilePath "usoclient" -ArgumentList "StartInstall" -NoNewWindow -Wait -PassThru
            if ($wuOutput.ExitCode -eq 0) {
                Write-Log "Windows Update executado com sucesso."
            } else {
                Write-Log "Windows Update retornou código $($wuOutput.ExitCode)."
            }
        } else {
            Write-Log "usoclient não encontrado. Pulando Windows Update."
        }
    } catch {
        Write-Log "Exceção ao executar Windows Update: $_"
    }
}

Write-Log "=== Fim da verificação ==="
exit 0
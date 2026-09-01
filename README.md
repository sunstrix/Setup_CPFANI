# 🚀 Setup Automatizado de Endpoints (CP Fani / Universal)

![OS](https://img.shields.io/badge/OS-Windows_10_%7C_11-blue?style=flat&logo=windows)
![Python](https://img.shields.io/badge/Python-3.12+-yellow?style=flat&logo=python)
![PowerShell](https://img.shields.io/badge/PowerShell-Automated-5391FE?style=flat&logo=powershell)
![Status](https://img.shields.io/badge/Status-Produção-success)

Ferramenta de provisionamento zero-touch e otimização extrema para transformar instalações limpas do Windows em estações corporativas blindadas (PDVs/Balcões) ou otimizar computadores pessoais em minutos.

O projeto automatiza instalação de softwares, aplica políticas de segurança, remove bloatware, configura tarefas de resiliência e gera inventário de hardware com envio opcional ao Google Drive.

A partir da versão **6.1.0**, o sistema também possui:

- Snapshot de hardware **agendado diariamente às 11:00**.
- Script independente `run_snapshot_only.py`.
- Campo **Origem** no snapshot:
  - `Deploy Manual`
  - `Agendamento Automatico`
- Coleta ampliada de impressoras:
  - Impressoras instaladas no Windows.
  - Dispositivos POS/térmicos brutos detectados via PnP/USB/Serial.
- Autenticação Google Drive OAuth2 mais robusta:
  - Token salvo por máquina.
  - Validação de token corrompido.
  - Timeout no login interativo.
  - Modo não interativo para tarefa agendada.
  - Pré-checagem opcional antes do deploy.
  - Aviso claro quando o snapshot ficar somente local.

---

## ✨ Recursos Principais

### 🛡️ Segurança e Privacidade

- Conformidade com LGPD:
  - Desativa telemetria.
  - Reduz coleta de dados em segundo plano.
- Blindagem de logon:
  - Bloqueia Windows Hello/Biometria quando habilitado.
- Firewall inteligente:
  - Restringe SMB/RPC conforme política selecionada.
- Tela de bloqueio corporativa:
  - Aplica wallpaper/lockscreen via GPO + PersonalizationCSP.
- Remoção agressiva de bloatware:
  - Remove aplicativos pré-instalados indesejados.

---

### ⚡ Otimização e Instalação

- Instalação silenciosa via Chocolatey.
- Fallback para WinGet quando necessário.
- Gestão de drivers:
  - Fabricante (Dell/HP/Lenovo).
  - Windows Update.
- Smart install do Flameshot:
  - Compara versão do Chocolatey com release mais recente do GitHub.
  - Valida hash SHA256 antes de instalar.

---

### 🤖 Automação e Resiliência

- Self-Healing/Watchdog:
  - Mantém wallpaper corporativo e serviços de suporte ativos.
- Tarefas agendadas opcionais:
  - Manutenção de rede.
  - Atualizador de software.
  - Reinício diário.
- Snapshot diário automático:
  - Tarefa `CPFANI_SnapshotDiario`.
  - Execução às **11:00**.
  - Executa como `SYSTEM`.
  - Gera snapshot independente do deploy completo.

---

## 📸 Snapshot de Hardware

O snapshot gera um arquivo com identificador único baseado preferencialmente no MAC ativo, com fallback para `ProcessorId`.

Nome do arquivo:

```text
CPFANI_Hardware_Snapshot_{ID}.txt
```

Local padrão de geração:

```text
C:\Scripts\
```

Conteúdo coletado:

- Local.
- Usuário.
- Origem da geração.
- Nome do computador.
- Modelo do sistema.
- Processador.
- Memória RAM.
- Versão do Windows.
- Serial da BIOS.
- ID único por MAC/ProcessorId.
- AnyDesk ID.
- TeamViewer ID.
- Monitores.
- Impressoras instaladas.
- Adaptadores de rede.
- Nova seção `IMPRESSORAS DETECTADAS`:
  - Impressoras instaladas via `Win32_Printer`.
  - Dispositivos POS/térmicos brutos via `Get-PnpDevice`.

Exemplo de origem no snapshot:

```text
Origem  : Deploy Manual
```

ou:

```text
Origem  : Agendamento Automatico
```

---

## 🗓️ Snapshot Agendado Diário

A tarefa criada é:

```text
CPFANI_SnapshotDiario
```

Configuração:

```text
Horário: 11:00
Usuário: SYSTEM
Privilégio: highest
Tipo: daily
```

Ela executa indiretamente:

```text
run_snapshot_only.py --scheduled
```

Comportamento importante:

- Em modo agendado, o script **não abre navegador**.
- Se o token do Google Drive estiver válido, tenta renovar/enviar silenciosamente.
- Se o token estiver ausente/expirado/corrompido:
  - O snapshot é salvo localmente.
  - O upload é ignorado.
  - A tarefa não fica travada aguardando login.

Logs do snapshot agendado:

```text
C:\Scripts\Logs\cpfani_snapshot_diario.log
```

---

## 🖨️ Coleta Completa de Impressoras

A nova coleta foi pensada para PDVs e balcões, cobrindo impressoras comuns e impressoras térmicas/POS.

### Impressoras instaladas

Coleta via:

```powershell
Get-CimInstance Win32_Printer
```

Informações capturadas:

- Nome.
- Driver.
- Porta.
- Padrão.
- Status.
- Compartilhamento.
- Tipo de conexão:
  - `REDE`
  - `USB`
  - `SERIAL`
  - `PARALELA`
  - `LOCAL`

### Dispositivos POS brutos

Coleta adicional via:

```powershell
Get-PnpDevice -Class Ports
Get-PnpDevice -Class USB
```

Filtro por palavras-chave típicas de impressoras térmicas/POS:

```text
Printer
POS
Thermal
ESC
Elgin
Bematech
Epson
Zebra
Diebold
Sweda
```

Isso ajuda a detectar impressoras térmicas usadas diretamente pelo PDV via ESC/POS, mesmo quando não há driver Windows instalado.

---

## ☁️ Google Drive OAuth2 Robusto

O envio do snapshot para o Google Drive usa OAuth2 com aplicativo desktop.

Não depende de Google Drive Desktop.

### Credenciais

Arquivo de credenciais OAuth2:

```text
credentials/oauth2_credentials.json
```

Esse arquivo pode ser o mesmo para todas as máquinas.

### Token por máquina

O token autenticado é salvo em:

```text
C:\Scripts\credentials\token.pickle
```

Importante:

- O token **não deve ser salvo dentro do repositório**.
- O token **não deve ser commitado**.
- Cada máquina deve ter seu próprio token.

### Validações implementadas

- Verificação se o `token.pickle` é uma instância válida de `Credentials`.
- Remoção automática de token corrompido.
- Renovação de token expirado com try/except amplo.
- Timeout no login interativo.
- Logs claros quando a reautenticação for necessária.
- Modo não interativo para execução agendada como SYSTEM.
- Aviso visual na GUI quando o snapshot não for enviado ao Drive.

### Pré-checagem opcional

Na GUI existe a opção:

```text
Verificar Google Drive antes de iniciar
```

Se marcada, o deploy tenta validar o Drive antes de aplicar branding, segurança, firewall, bloatware etc.

Se falhar, o técnico pode:

- Cancelar o deploy.
- Continuar sem upload.
- Gerar snapshot apenas localmente.

---

## 🏗️ Arquitetura do Projeto

| Arquivo | Descrição |
|---|---|
| `EXECUTAR.bat` | Launcher principal. Valida privilégios, prepara ambiente, instala dependências e inicia a GUI. |
| `gui.py` | Interface gráfica em CustomTkinter. Permite selecionar políticas, executar deploy, gerar snapshot isolado e verificar a tarefa de snapshot. |
| `mod_config.py` | Núcleo de configuração. Aplica políticas, firewall, branding, watchdog, snapshot, scheduler de snapshot e coleta ampliada de impressoras. |
| `mod_instalar.py` | Motor de instalação. Usa Chocolatey, WinGet e PowerShell para softwares e drivers. |
| `run_snapshot_only.py` | Script independente para gerar somente o snapshot, sem deploy. Usado manualmente ou pela tarefa diária. |
| `settings.json` | Dicionário de aplicativos e bloatware. |
| `manutencao_rede.bat` | Script auxiliar para correção de DHCP/IP e cache DNS. |
| `instalar_tudo.ps1` | Script agendável para atualização de aplicativos. |
| `update_checker.ps1` | Script opcional/legado para atualizações automáticas. |
| `mod_kudu.py` | Módulo opcional de limpeza nativa. Manter somente se ainda for utilizado em fluxos externos. |
| `patch_drive.py` | Script legado de patch do Drive. Nas versões atuais a autenticação é nativa em `mod_config.py`/`gui.py`. |
| `credentials/oauth2_credentials.json` | Credenciais OAuth2 do aplicativo desktop Google. |
| `resources/logo_cpfani.png` | Logo opcional exibida na GUI. |
| `resources/wallpaper_cpfani.jpg` | Wallpaper corporativo usado por branding/lockscreen. |
| `.gitignore` | Impede commit de token, logs e artefatos locais. |

---

## ⚙️ Pré-requisitos

- Windows 10 ou Windows 11.
- Execução como Administrador.
- Internet para:
  - Instalar dependências.
  - Baixar pacotes.
  - Sincronizar NTP.
  - Renovar token Google Drive quando necessário.
- Para upload automático:
  - Google Cloud projeto.
  - Drive API habilitada.
  - OAuth Client ID para Desktop.
  - Arquivo `credentials/oauth2_credentials.json`.

O `EXECUTAR.bat` tenta preparar Python e dependências automaticamente.

---

## 🚀 Como Usar

### 1. Deploy completo

1. Coloque o projeto em disco local, por exemplo:

```text
C:\Scripts\Setup_CPFANI
```

2. Clique com o botão direito em:

```text
EXECUTAR.bat
```

3. Selecione **Executar como Administrador**.

4. Aguarde a preparação do ambiente.

5. Na GUI, selecione as opções desejadas:
   - Interface/branding.
   - Segurança/LGPD.
   - Firewall.
   - Bloatware.
   - Softwares.
   - Office.
   - Drivers.
   - Tarefas agendadas.
   - Self-Healing.
   - Pré-checagem do Google Drive.

6. Clique em:

```text
EXECUTAR DEPLOY
```

7. Informe Local e Usuário na janela modal.

8. Aguarde a conclusão.

---

### 2. Gerar apenas snapshot pela GUI

Na GUI, clique em:

```text
GERAR APENAS SNAPSHOT
```

Esse fluxo:

- Coleta Local e Usuário.
- Gera o snapshot.
- Tenta enviar ao Drive se configurado.
- Cria/atualiza a tarefa `CPFANI_SnapshotDiario`.
- Atualiza planilhas de inventário quando houver snapshots no Drive.

---

### 3. Gerar snapshot manualmente via script

Executar no diretório do projeto:

```powershell
python run_snapshot_only.py
```

Com local e usuário:

```powershell
python run_snapshot_only.py --local "14120 - ARPEL SBC" --usuario "Alex"
```

Simular modo agendado, sem navegador:

```powershell
python run_snapshot_only.py --scheduled
```

Não criar/atualizar a tarefa:

```powershell
python run_snapshot_only.py --no-scheduler
```

Permitir login interativo do Drive em execução manual:

```powershell
python run_snapshot_only.py --interactive
```

Variáveis de ambiente opcionais:

```powershell
$env:CPFANI_SNAPSHOT_LOCAL = "14120 - ARPEL SBC"
$env:CPFANI_SNAPSHOT_USUARIO = "Alex"
python run_snapshot_only.py
```

---

### 4. Verificar tarefa de snapshot

Na GUI, clique em:

```text
VERIFICAR TASK AGENDADA DE SNAPSHOT
```

Ou manualmente:

```powershell
schtasks /query /tn "CPFANI_SnapshotDiario" /fo LIST /v
```

---

## 📅 Tarefas Agendadas

| Tarefa | Horário/Gatilho | Criada quando |
|---|---:|---|
| `CPFANI_Watchdog` | Logon | Deploy com Self-Healing habilitado. |
| `CPFANI_ReinicioDiario` | Diário 21:00 | Deploy com opção de reinício habilitada. |
| `CPFANI_ManutencaoRede` | Diário 08:00 | Deploy com manutenção de rede habilitada. |
| `CPFANI_InstalarTudo` | Logon | Deploy com atualizador habilitado. |
| `CPFANI_SnapshotDiario` | Diário 11:00 | Deploy completo, snapshot manual ou execução manual do `run_snapshot_only.py`. |

---

## 🔎 Diagnóstico e Logs

### Logs principais

```text
C:\Scripts\Logs\
```

Arquivos relevantes:

```text
cpfani_snapshot_diario.log
cleanup_nativo.log
```

### Snapshot local

```text
C:\Scripts\CPFANI_Hardware_Snapshot_*.txt
```

### Token Drive

```text
C:\Scripts\credentials\token.pickle
```

### Se o snapshot não for enviado ao Drive

A GUI exibirá aviso claro:

```text
Snapshot gerado localmente mas NÃO enviado ao Drive.
Motivo: [erro].
Arquivo salvo em: [caminho].
```

Causas comuns:

- `oauth2_credentials.json` ausente.
- Token expirado e execução sem sessão interativa.
- Token corrompido.
- Conta Google sem permissão na pasta do Drive.
- Bibliotecas Google ausentes.
- Firewall/proxy bloqueando Google APIs.

---

## 📦 Dependências

O instalador gerencia automaticamente, mas manualmente:

```powershell
python -m pip install customtkinter psutil pillow
python -m pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 openpyxl
```

---

## 🌍 Modo Corporativo vs. Universal

### Corporativo

Indicado para PDV/loja:

- Firewall restrito.
- Branding.
- Self-Healing.
- Snapshot diário.
- Upload centralizado ao Drive.

### Universal

Indicado para máquinas pessoais/clientes externos:

- Desmarcar Self-Healing.
- Desmarcar firewall restrito.
- Manter otimização e instalação de softwares.
- Snapshot pode ser usado opcionalmente.

---

## 🔐 Boas Práticas de Repositório

Não commitar:

```text
credentials/token.pickle
*.log
__pycache__/
*.bak_drive
C:\Scripts\*
```

O arquivo `credentials/oauth2_credentials.json` pode ser distribuído conforme política interna, mas o token autenticado deve permanecer apenas na máquina.

Se um `token.pickle` já foi commitado anteriormente:

1. Remover do repositório.
2. Revisar histórico se o repositório for público.
3. Considerar revogar/renovar o OAuth Client.
4. Garantir que `.gitignore` ignore `credentials/token.pickle`.
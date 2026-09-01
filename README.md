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
- Campo `Origem` no snapshot (`Deploy Manual` / `Agendamento Automatico`).
- Coleta ampliada de impressoras (instaladas + dispositivos POS/térmicos brutos via PnP).
- Autenticação Google Drive OAuth2 mais robusta (token por máquina, validação de token corrompido, timeout no login, modo não interativo para tarefa agendada, pré-checagem opcional e aviso claro quando o snapshot fica somente local).

A partir da versão **6.2.0**, o sistema também possui:

- **ID único por monitor** (`ID_Unico`) com regra de geração para monitores sem serial.
- **Rótulo duplo** na seção de monitores (`Numero_de_Serie` + `Nº de Série`) para compatibilidade total com o **Dashboard-TI**.
- Contagem de monitores no Dashboard consistente com a frota (sem descarte por serial ausente ou duplicado).

---

## ✨ Recursos Principais

### 🛡️ Segurança e Privacidade

- Conformidade LGPD: desativa telemetria e reduz coleta de dados em segundo plano.
- Blindagem de logon: bloqueia Windows Hello/Biometria quando habilitado.
- Firewall inteligente: restringe SMB/RPC conforme política selecionada.
- Tela de bloqueio corporativa: aplica wallpaper/lockscreen via GPO + PersonalizationCSP.
- Remoção agressiva de bloatware: remove aplicativos pré-instalados indesejados.

### ⚡ Otimização e Instalação

- Instalação silenciosa via Chocolatey, com fallback para WinGet quando necessário.
- Gestão de drivers: fabricante (Dell/HP/Lenovo) ou Windows Update.
- Smart install do Flameshot: compara versão do Chocolatey com a release mais recente do GitHub e valida hash SHA256 antes de instalar.

### 🤖 Automação e Resiliência

- Self-Healing/Watchdog: mantém wallpaper corporativo e serviços de suporte ativos.
- Tarefas agendadas opcionais: manutenção de rede, atualizador de software e reinício diário.
- Snapshot diário automático: tarefa `CPFANI_SnapshotDiario`, execução às 11:00 como `SYSTEM`, independente do deploy completo.

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

- Local, usuário e origem da geração.
- Nome do computador, modelo do sistema, processador, memória RAM, versão do Windows e serial da BIOS.
- ID único por MAC/ProcessorId.
- AnyDesk ID e TeamViewer ID.
- Monitores (com `ID_Unico` — veja a seção específica abaixo).
- Impressoras instaladas e adaptadores de rede.
- Seção `IMPRESSORAS DETECTADAS`: impressoras via `Win32_Printer` + dispositivos POS/térmicos brutos via `Get-PnpDevice`.

Exemplo de origem no snapshot:

```text
Origem  : Deploy Manual
```

ou:

```text
Origem  : Agendamento Automatico
```

---

## 🖥️ Identificação Única de Monitores (V6.2.0)

### Problema que motivou a mudança

O **Dashboard-TI** (repositório `sunstrix/Dashboard-TI`) exibia **menos monitores do que PCs**. A causa era dupla:

1. Monitores sem serial válido (WMI retorna vazio) eram **descartados** pelo filtro de seriais inválidos do Dashboard (`N/A`, `0`, `-`, `null`, `s/n` etc.).
2. Seriais duplicados eram **colapsados** pela deduplicação global por `Serial_Monitor`.

### Regra de geração do `ID_Unico`

Cada monitor recebe um identificador único, calculado em `mod_config.py :: _gerar_ids_unicos_monitores()`:

| Situação | Valor do `ID_Unico` |
|---|---|
| Serial válido e único na máquina | O próprio serial real (ex: `105NTMX2A775`) |
| Serial inválido/vazio | `SEM-SN-<PC_ID>-M<n>` (PC_ID = MAC/ProcessorId, `n` = posição do monitor) |
| Serial duplicado dentro da mesma máquina | Serial + sufixo `-D2`, `-D3`... |

### Formato da seção de monitores (rótulo duplo)

```text
============================================================
 PERIFÉRICOS — MONITORES
============================================================
 Monitor 1:
   Modelo          : LG 24MK430
   Numero_de_Serie : 105NTMX2A775
   Nº de Série     : 105NTMX2A775
   ID_Unico        : 105NTMX2A775

 Monitor 2:
   Modelo          : Monitor Genérico
   Numero_de_Serie : N/A
   Nº de Série     : SEM-SN-A1B2C3D4E5F6-M2
   ID_Unico        : SEM-SN-A1B2C3D4E5F6-M2
============================================================
```

### Compatibilidade

| Consumidor | Campo lido | Comportamento |
|---|---|---|
| **Dashboard-TI** (`parser.py`) | `Nº de Série` (regex `N[º°.]?\s*de\s*S[ée]rie`) | Agora sempre recebe um valor **único e válido** — nada é descartado nem colapsado |
| **GUI / planilha xlsx** (legado) | `Numero_de_Serie` | Continua lendo o serial bruto do WMI |
| **Snapshots antigos** | `Numero_de_Serie` | Parsing com fallback — nada quebra |

> **Nota:** a contagem de monitores no Dashboard só reflete a frota completa **após cada PC regenerar o snapshot** ao menos uma vez com a V6.2.0 (via deploy, botão "GERAR APENAS SNAPSHOT" ou tarefa diária `CPFANI_SnapshotDiario`).

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
- Se o token estiver ausente/expirado/corrompido: o snapshot é salvo localmente, o upload é ignorado e a tarefa não fica travada aguardando login.

Logs do snapshot agendado:

```text
C:\Scripts\Logs\cpfani_snapshot_diario.log
```

---

## 🖨️ Coleta Completa de Impressoras

A coleta foi pensada para PDVs e balcões, cobrindo impressoras comuns e impressoras térmicas/POS.

### Impressoras instaladas

Coleta via `Get-CimInstance Win32_Printer`, capturando nome, driver, porta, padrão, status, compartilhamento e tipo de conexão (`REDE`, `USB`, `SERIAL`, `PARALELA`, `LOCAL`).

### Dispositivos POS brutos

Coleta adicional via `Get-PnpDevice -Class Ports` e `Get-PnpDevice -Class USB`, filtrando palavras-chave típicas de impressoras térmicas/POS (`Printer`, `POS`, `Thermal`, `ESC`, `Elgin`, `Bematech`, `Epson`, `Zebra`, `Diebold`, `Sweda`). Isso detecta térmicas usadas diretamente pelo PDV via ESC/POS, mesmo sem driver Windows instalado.

---

## ☁️ Google Drive OAuth2 Robusto

O envio do snapshot para o Google Drive usa OAuth2 com aplicativo desktop. Não depende de Google Drive Desktop.

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

- O token **não deve** ser salvo dentro do repositório.
- O token **não deve** ser commitado.
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

Na GUI existe a opção **"Verificar Google Drive antes de iniciar"**. Se marcada, o deploy tenta validar o Drive antes de aplicar branding, segurança, firewall, bloatware etc. Se falhar, o técnico pode cancelar o deploy, continuar sem upload ou gerar snapshot apenas localmente.

---

## 🏗️ Arquitetura do Projeto

| Arquivo | Descrição |
|---|---|
| `EXECUTAR.bat` | Launcher principal. Valida privilégios, prepara ambiente, instala dependências e inicia a GUI. |
| `gui.py` | Interface gráfica em CustomTkinter. Permite selecionar políticas, executar deploy, gerar snapshot isolado e verificar a tarefa de snapshot. |
| `mod_config.py` | Núcleo de configuração. Aplica políticas, firewall, branding, watchdog, snapshot, scheduler de snapshot, coleta ampliada de impressoras e ID único de monitores. |
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

### Projeto consumidor

| Repositório | Descrição |
|---|---|
| `sunstrix/Dashboard-TI` | Dashboard Streamlit que lê os snapshots do Drive e exibe KPIs de inventário (computadores, monitores, impressoras). Consome o campo `Nº de Série` dos monitores para deduplicação. |

---

## ⚙️ Pré-requisitos

- Windows 10 ou Windows 11.
- Execução como Administrador.
- Internet para instalar dependências, baixar pacotes, sincronizar NTP e renovar token Google Drive quando necessário.
- Para upload automático: projeto no Google Cloud, Drive API habilitada, OAuth Client ID para Desktop e arquivo `credentials/oauth2_credentials.json`.

O `EXECUTAR.bat` tenta preparar Python e dependências automaticamente.

---

## 🚀 Como Usar

### 1. Deploy completo

1. Coloque o projeto em disco local, por exemplo: `C:\Scripts\Setup_CPFANI`.
2. Clique com o botão direito em `EXECUTAR.bat` e selecione **Executar como Administrador**.
3. Aguarde a preparação do ambiente.
4. Na GUI, selecione as opções desejadas (branding, segurança/LGPD, firewall, bloatware, softwares, office, drivers, tarefas agendadas, self-healing e pré-checagem do Google Drive).
5. Clique em **EXECUTAR DEPLOY**.
6. Informe Local e Usuário na janela modal.
7. Aguarde a conclusão.

### 2. Gerar apenas snapshot pela GUI

Na GUI, clique em **GERAR APENAS SNAPSHOT**. Esse fluxo coleta Local e Usuário, gera o snapshot, tenta enviar ao Drive se configurado, cria/atualiza a tarefa `CPFANI_SnapshotDiario` e atualiza planilhas de inventário quando houver snapshots no Drive.

### 3. Gerar snapshot manualmente via script

```powershell
python run_snapshot_only.py
python run_snapshot_only.py --local "14120 - ARPEL SBC" --usuario "Alex"
python run_snapshot_only.py --scheduled        # modo agendado, sem navegador
python run_snapshot_only.py --no-scheduler     # não cria/atualiza a tarefa
python run_snapshot_only.py --interactive      # permite login interativo do Drive
```

Variáveis de ambiente opcionais:

```powershell
$env:CPFANI_SNAPSHOT_LOCAL = "14120 - ARPEL SBC"
$env:CPFANI_SNAPSHOT_USUARIO = "Alex"
python run_snapshot_only.py
```

### 4. Verificar tarefa de snapshot

Na GUI, clique em **VERIFICAR TASK AGENDADA DE SNAPSHOT**. Ou manualmente:

```powershell
schtasks /query /tn "CPFANI_SnapshotDiario" /fo LIST /v
```

---

## 📅 Tarefas Agendadas

| Tarefa | Horário/Gatilho | Criada quando |
|---|---|---|
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

### Monitores no Dashboard

Se o Dashboard-TI ainda exibir menos monitores que PCs:

1. Confirme que o snapshot foi regenerado com a V6.2.0 (verifique se a seção de monitores contém as linhas `Nº de Série` e `ID_Unico`).
2. Verifique no log do snapshot as linhas `Monitor N: serial valido/invalido/duplicado` geradas por `_gerar_ids_unicos_monitores()`.
3. Aguarde o Dashboard reprocessar os arquivos do Drive.

### Se o snapshot não for enviado ao Drive

A GUI exibirá aviso claro:

```text
Snapshot gerado localmente mas NÃO enviado ao Drive.
Motivo: [erro].
Arquivo salvo em: [caminho].
```

Causas comuns: `oauth2_credentials.json` ausente; token expirado em execução sem sessão interativa; token corrompido; conta Google sem permissão na pasta do Drive; bibliotecas Google ausentes; firewall/proxy bloqueando Google APIs.

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

Indicado para PDV/loja: firewall restrito, branding, self-healing, snapshot diário e upload centralizado ao Drive.

### Universal

Indicado para máquinas pessoais/clientes externos: desmarque Self-Healing e firewall restrito, mantendo otimização e instalação de softwares. Snapshot pode ser usado opcionalmente.

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
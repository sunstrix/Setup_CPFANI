# 🚀 Setup Automatizado de Endpoints (CP Fani / Universal)

![Windows](https://img.shields.io/badge/OS-Windows_10_%7C_11-blue?style=flat&logo=windows)
![Python](https://img.shields.io/badge/Python-3.12+-yellow?style=flat&logo=python)
![PowerShell](https://img.shields.io/badge/PowerShell-Automated-5391FE?style=flat&logo=powershell)
![Status](https://img.shields.io/badge/Status-Produção-success)

Uma ferramenta de provisionamento *zero-touch* e otimização extrema projetada para transformar instalações limpas do Windows em estações de trabalho corporativas blindadas (PDVs/Balcões) ou otimizar computadores pessoais em minutos.

O script automatiza a instalação de softwares essenciais, aplica políticas rígidas de segurança (LGPD), extermina *bloatwares* e implementa um motor de Auto-Cura (*Self-Healing*) para garantir que a máquina nunca perca a sua configuração padrão. Além disso, gera um **Snapshot de Hardware** com identificador único (`ProcessorId`), local e usuário, e envia automaticamente para o Google Drive (com autenticação OAuth2) para rastreamento centralizado dos endpoints.

---

## ✨ Recursos Principais

### 🛡️ Segurança e Privacidade Avançadas
- **Conformidade LGPD:** Desativa completamente a telemetria da Microsoft, Cortana e coleta de dados em segundo plano.
- **Blindagem de Logon:** Bloqueia o Windows Hello (Biometria/PIN) e obriga o uso de credenciais seguras, eliminando telas de *First Run* (SCOOBE).
- **Firewall Inteligente (Whitelist):** Fecha portas vulneráveis (SMB/RPC) para o exterior, permitindo comunicação de arquivos e impressoras **apenas** na rede local segura.
- **Tela de Bloqueio Corporativa:** Aplica a imagem de wallpaper como lockscreen via políticas GPO + PersonalizationCSP (funciona em Windows Pro, não apenas Enterprise/Education).

### ⚡ Otimização e Desempenho
- **Purga de Bloatware:** Remove agressivamente aplicativos pré-instalados de fábrica (Candy Crush, Xbox, TikTok, etc.) de todos os perfis de usuário.
- **Instalação Silenciosa de Softwares:** Utiliza o *Chocolatey* com fallback para *WinGet*, garantindo alta taxa de sucesso mesmo em ambientes com restrições de rede.
- **Gestão de Drivers:** Integra-se com assistentes oficiais (Dell Command Update, Lenovo System Update) ou força a instalação via Microsoft Update.
- **Limpeza Avançada (Kudu nativo):** Módulo embutido que remove arquivos temporários, caches de navegadores, entradas de registro órfãs, drivers obsoletos e otimiza serviços do Windows – tudo sem dependências externas.

### 🤖 Automação e Resiliência
- **Motor "Self-Healing" (Cão de Guarda):** Um script invisível de fundo (Watchdog) que monitora o sistema a cada 10 segundos, garantindo que o papel de parede corporativo e softwares de suporte (AnyDesk) nunca sejam alterados ou fechados pelos utilizadores.
- **Manutenção Automática:** Cria tarefas agendadas nativas para reiniciar o computador fora do horário comercial e atualizar softwares de forma invisível no logon.
- **Snapshot de Hardware com ID Único:** Gera um relatório completo contendo:
  - **ProcessorId** (identificador único da CPU, mais confiável que UUID para máquinas chinesas).
  - Local e usuário (coletados via janela modal na GUI).
  - Modelo, processador, RAM, versão do Windows, serial da BIOS e IDs do AnyDesk/TeamViewer.
  - Nome do arquivo: `CPFANI_Hardware_Snapshot_{ProcessorId}.txt`.
  - Upload automático para o Google Drive (com autenticação OAuth2), substituindo arquivos existentes.

### 🔧 Correções e Melhorias Recentes
- **Erro SSL no PIP:** Resolvido com opções `--trusted-host` durante a instalação das dependências.
- **Tela de Bloqueio:** Agora funciona corretamente no Windows Pro via PersonalizationCSP.
- **Fallback WinGet:** Pacotes que falham no Chocolatey são automaticamente tentados via WinGet.
- **UUID substituído por ProcessorId:** Evita conflitos de identificação em placas‑mãe chinesas que compartilham o mesmo UUID.
- **Autenticação OAuth2:** Upload para o Google Drive usando credenciais de aplicativo desktop (não requer conta de serviço, evitando bloqueios organizacionais).

---

## 🏗️ Arquitetura do Projeto

O ecossistema é modular e divide-se nos seguintes componentes:

| Ficheiro | Descrição |
|----------|-----------|
| `EXECUTAR.bat` | O *Launcher* principal. Verifica privilégios de Admin, testa a internet e instala automaticamente o Python, o Chocolatey e as dependências (PIP, incluindo `google-api-python-client`) antes de chamar a interface. |
| `gui.py` | Interface gráfica moderna desenvolvida em `customtkinter`, permitindo a seleção granular das políticas a aplicar. Inclui janela modal para capturar local e usuário antes da geração do snapshot. |
| `mod_config.py` | O "Cérebro" de configuração. Injeta chaves de registo, gere o Firewall, limpa widgets, implementa o Watchdog, aplica redundância de wallpaper/lockscreen e gera o snapshot com ProcessorId. |
| `mod_instalar.py` | Motor de *deploy*. Comunica com o Chocolatey, WinGet e PowerShell para baixar softwares e drivers. |
| `mod_kudu.py` | Módulo de limpeza nativa (substitui a integração com o Kudu externo, que não possui CLI). Remove lixo do sistema, caches, registros órfãos, drivers obsoletos e otimiza serviços. |
| `settings.json` | Ficheiro de dicionário. Define quais softwares serão instalados e a lista de bloatware a remover. |
| `manutencao_rede.bat` | Script auxiliar injetado nas máquinas para corrigir falhas de IP dinâmico/estático (DHCP) e limpar cache DNS. |
| `instalar_tudo.ps1` | Script *PowerShell* agendado no sistema para manter as aplicações sempre atualizadas em segundo plano. |
| `update_checker.ps1` | Script que verifica e aplica atualizações automáticas no logon do usuário. |
| `credentials/oauth2_credentials.json` | Arquivo de credenciais OAuth2 para upload automático ao Google Drive (deve ser criado pelo usuário conforme instruções). |

---

## ⚙️ Pré-requisitos

- **Sistema Operativo:** Windows 10 ou Windows 11 (versão Pro ou superior para algumas políticas).
- **Permissões:** O utilizador **DEVE** executar o script com privilégios de Administrador.
- **Conectividade:** Ligação à Internet ativa (necessária para baixar dependências, softwares e sincronizar o relógio via NTP.br).
- **(Opcional) Upload Google Drive:** Para ativar o envio automático do snapshot, crie um projeto no Google Cloud, habilite a Drive API, gere um ID de cliente OAuth para aplicativo desktop e coloque o arquivo JSON em `credentials/oauth2_credentials.json`. A primeira execução pedirá autorização no navegador.

*(Nota: Não é necessário ter o Python pré-instalado. O `EXECUTAR.bat` faz o download e a configuração do ambiente automaticamente de forma portátil).*

---

## 🚀 Como Usar

1. Faça o download ou clone este repositório para o disco local (Ex: `C:\Scripts\Setup_CPFANI`).
2. (Opcional) Adicione a sua logo (`logo_cpfani.png`) e papel de parede (`wallpaper_cpfani.jpg`) dentro da pasta `resources\`.
3. Clique com o botão direito no ficheiro **`EXECUTAR.bat`** e selecione **"Executar como Administrador"**.
4. Uma janela de consola (CMD) será aberta para preparar o ambiente. Aguarde.
5. A Interface Gráfica (GUI) será iniciada.
6. Selecione as opções de Branding, Segurança, Softwares e Limpeza que deseja aplicar.
7. Ao clicar em **"EXECUTAR DEPLOY"**, será exibida uma janela modal para selecionar o **Local** e digitar o **nome do Usuário** – esses dados serão incluídos no snapshot.
8. Aguarde a finalização da barra de progresso.
9. No final, será gerado um relatório de *Hardware Snapshot* na pasta `C:\Scripts\` com o nome `CPFANI_Hardware_Snapshot_{ProcessorId}.txt` e enviado para o Google Drive (se configurado).

---

## 🌍 Versão Corporativa vs. Universal

Este projeto foi desenhado para escalabilidade:
- **Modo Corporativo:** Ativa o Firewall restrito, o Branding (Logos) e o Cão de Guarda (Self-Healing). Ideal para Ponto de Venda (PDV) e máquinas de loja.
- **Modo Universal (Vanilla):** Através da interface, desmarque a caixa "Ativar Self-Healing" e mantenha a opção de Firewall desmarcada para usar este motor como um poderoso otimizador para computadores pessoais e clientes externos, sem prender a máquina a regras de rede específicas.

---

## 📦 Dependências

O instalador gerencia automaticamente todas as dependências, mas, caso queira instalá-las manualmente:

```bash
pip install customtkinter psutil pillow
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

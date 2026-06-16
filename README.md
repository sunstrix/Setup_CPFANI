# 🚀 Setup Automatizado de Endpoints (CP Fani / Universal)

![Windows](https://img.shields.io/badge/OS-Windows_10_%7C_11-blue?style=flat&logo=windows)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=flat&logo=python)
![PowerShell](https://img.shields.io/badge/PowerShell-Automated-5391FE?style=flat&logo=powershell)
![Status](https://img.shields.io/badge/Status-Produção-success)

Uma ferramenta de provisionamento *zero-touch* e otimização extrema projetada para transformar instalações limpas do Windows em estações de trabalho corporativas blindadas (PDVs/Balcões) ou otimizar computadores pessoais em minutos. 

O script automatiza a instalação de softwares essenciais, aplica políticas rígidas de segurança (LGPD), extermina *bloatwares* e implementa um motor de Auto-Cura (*Self-Healing*) para garantir que a máquina nunca perca a sua configuração padrão.

---

## ✨ Recursos Principais

### 🛡️ Segurança e Privacidade Avançadas

* **Conformidade LGPD:** Desativa completamente a telemetria da Microsoft, Cortana e coleta de dados em segundo plano.
* **Blindagem de Logon:** Bloqueia o Windows Hello (Biometria/PIN) e obriga o uso de credenciais seguras, eliminando telas de *First Run* (SCOOBE).
* **Firewall Inteligente (Whitelist):** Fecha portas vulneráveis **SMB (445) e RPC (135)** para o exterior, permitindo comunicação de arquivos e impressoras **apenas** na rede local segura (RFC1918).

### ⚡ Otimização e Desempenho

* **Purga de Bloatware:** Remove agressivamente aplicativos pré-instalados de fábrica (Candy Crush, Xbox, TikTok, etc.) de todos os perfis de usuário, **preservando apps essenciais do sistema** como Calculadora, Loja Windows, Câmera e Alarmes.
* **Instalação Silenciosa de Softwares:** Utiliza o *Chocolatey* e *WinGet* para baixar e instalar silenciosamente pacotes como Google Chrome, AnyDesk, TeamViewer, WinRAR, VLC, entre outros.
* **Gestão de Drivers:** Integra-se com assistentes oficiais (Dell Command Update, Lenovo System Update, HP Image Assistant) ou força a instalação via Microsoft Update.

### 🤖 Automação e Resiliência

* **Motor "Self-Healing" (Cão de Guarda):** Um script invisível de fundo (Watchdog) que monitora o sistema a cada 10 segundos, garantindo que o **papel de parede corporativo** e o **AnyDesk** nunca sejam alterados ou fechados pelos usuários. Se o processo cair, o watchdog o reinicia automaticamente.
* **Manutenção Automática:** Cria tarefas agendadas nativas para reiniciar o computador fora do horário comercial e atualizar softwares de forma invisível no logon.

---

## 🏗️ Arquitetura do Projeto

O ecossistema é modular e divide-se nos seguintes componentes:

| Arquivo | Descrição |
|----------|-----------|
| `EXECUTAR.bat` | O *Launcher* principal. Verifica privilégios de Admin, valida arquivos essenciais e chama o instalador de pré-requisitos antes de iniciar a interface. |
| `instalar_pre_requisitos.bat` | Script auxiliar que instala Python (3.8–3.13), Chocolatey e dependências PIP de forma robusta, com **retry de download**, validação de integridade e remoção de aliases da Windows Store. |
| `gui.py` | Interface gráfica moderna em `customtkinter`. Possui **lock file com timestamp** (evita execução múltipla), downloads com SSL/TLS validado, checksum SHA256 e backup automático de configurações. |
| `mod_config.py` | O "Cérebro" de configuração. Injeta chaves de registro (*Registry*), gere o *Firewall* com whitelist LAN, limpa os *widgets*, implementa o **Watchdog real de Auto-Cura** (AnyDesk + Wallpaper) e gera snapshots de hardware com IDs de acesso remoto. |
| `mod_instalar.py` | Motor de *deploy*. Comunica com o Chocolatey e PowerShell para baixar softwares e drivers, com **fallback inteligente** para fabricantes (HP/Dell/Lenovo) e tratamento de reinício necessário (código 3010). |
| `settings.json` | Arquivo de configuração enxuto. Define softwares, lista de bloatware e caminhos de imagens corporativas — sem campos fantasmas nunca utilizados pelo código. |
| `manutencao_rede.bat` | Script auxiliar injetado nas máquinas para corrigir falhas de IP dinâmico/estático (DHCP), limpar cache DNS e configurar DNS do gateway corporativo com validação de adaptadores. |
| `instalar_tudo.ps1` | Script *PowerShell* agendado no sistema para manter as aplicações sempre atualizadas em segundo plano, com **health check pós-instalação** mapeando executáveis reais. |
| `update_checker.ps1` | Script de verificação de atualizações executado no logon do usuário, com proteção contra execução duplicada no mesmo dia e **fallback de Windows Update** (usoclient + PSWindowsUpdate). |

---

## ⚙️ Pré-requisitos

* **Sistema Operacional:** Windows 10 ou Windows 11.
* **Permissões:** O usuário **DEVE** executar o script com privilégios de Administrador.
* **Conectividade:** Conexão à Internet ativa (necessária para baixar dependências, softwares e atualizar o relógio via NTP.br).

*(Nota: Não é necessário ter o Python pré-instalado. O `instalar_pre_requisitos.bat` faz o download e a configuração do ambiente automaticamente de forma robusta, evitando conflitos com aliases da Windows Store.)*

---

## 🚀 Como Usar

1. Faça o download ou clone este repositório para o disco local (Ex: `C:\Scripts\Setup_CPFANI`).
2. Adicione a sua logo (`logo_cpfani.png`) e papel de parede (`wallpaper_cpfani.jpg`) dentro da pasta `resources\`.
3. Clique com o botão direito no arquivo **`EXECUTAR.bat`** e selecione **"Executar como Administrador"**.
4. Uma janela de console (CMD) será aberta para preparar o ambiente. Aguarde.
5. A Interface Gráfica (GUI) será iniciada.
6. Selecione as opções de Branding, Segurança e Softwares que deseja aplicar.
7. Clique em **"EXECUTAR DEPLOY"** e aguarde a finalização da barra de progresso.
8. No final, será gerado um relatório de *Hardware Snapshot* na pasta `C:\Scripts\`, incluindo IDs de acesso remoto (AnyDesk/TeamViewer).

---

## 🌍 Versão Corporativa vs. Universal

Este projeto foi desenhado para escalabilidade:

* **Modo Corporativo:** Ativa o Firewall restrito, o Branding (Logos) e o Cão de Guarda (Self-Healing). Ideal para Ponto de Venda (PDV) e máquinas de loja.
* **Modo Universal (Vanilla):** Através da interface, desmarque a caixa "Ativar Self-Healing" e mantenha a opção de Firewall desmarcada para usar este motor como um poderoso otimizador para computadores pessoais e clientes externos, sem prender a máquina a regras de rede específicas.

---

## 🆕 O Que Há de Novo (V5.9.5.2)

* **Estabilidade:** Todos os downloads agora usam SSL/TLS validado e verificação de checksum SHA256.
* **Compatibilidade:** Suporte a Python 3.8–3.13; remoção de bloatware compatível com Windows 11 22H2+.
* **Resiliência:** Script de pré-requisitos com retry de download, teste de escrita em disco e validação pós-instalação de cada dependência.
* **Segurança:** Firewall agora protege SMB **e** RPC; lock file detecta processos órfãos automaticamente.
* **Integridade:** Health check de Chocolatey mapeia executáveis reais no PATH, evitando falsos negativos.

---

## ⚠️ Isenção de Responsabilidade

Este script realiza alterações profundas no Registro do Windows (*Registry*), cria tarefas agendadas e remove pacotes nativos do sistema operacional. Embora amplamente testado em ambientes de produção, o uso é da inteira responsabilidade do usuário. Recomenda-se testar em ambiente controlado ou máquina virtual antes de aplicar em uma infraestrutura em grande escala.

---
*Desenvolvido com ☕ e Python para automação de infraestruturas.*
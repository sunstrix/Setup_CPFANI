# \# 🚀 Setup Automatizado de Endpoints (CP Fani / Universal)

# 

# !\[Windows](https://img.shields.io/badge/OS-Windows\_10\_%7C\_11-blue?style=flat\&logo=windows)

# !\[Python](https://img.shields.io/badge/Python-3.12+-yellow?style=flat\&logo=python)

# !\[PowerShell](https://img.shields.io/badge/PowerShell-Automated-5391FE?style=flat\&logo=powershell)

# !\[Status](https://img.shields.io/badge/Status-Produção-success)

# 

# Uma ferramenta de provisionamento \*zero-touch\* e otimização extrema projetada para transformar instalações limpas do Windows em estações de trabalho corporativas blindadas (PDVs/Balcões) ou otimizar computadores pessoais em minutos. 

# 

# O script automatiza a instalação de softwares essenciais, aplica políticas rígidas de segurança (LGPD), extermina \*bloatwares\* e implementa um motor de Auto-Cura (\*Self-Healing\*) para garantir que a máquina nunca perca a sua configuração padrão.

# 

# \---

# 

# \## ✨ Recursos Principais

# 

# \### 🛡️ Segurança e Privacidade Avançadas

# \* \*\*Conformidade LGPD:\*\* Desativa completamente a telemetria da Microsoft, Cortana e coleta de dados em segundo plano.

# \* \*\*Blindagem de Logon:\*\* Bloqueia o Windows Hello (Biometria/PIN) e obriga o uso de credenciais seguras, eliminando telas de \*First Run\* (SCOOBE).

# \* \*\*Firewall Inteligente (Whitelist):\*\* Fecha portas vulneráveis (SMB/RPC) para o exterior, permitindo comunicação de arquivos e impressoras \*\*apenas\*\* na rede local segura.

# 

# \### ⚡ Otimização e Desempenho

# \* \*\*Purga de Bloatware:\*\* Remove agressivamente aplicativos pré-instalados de fábrica (Candy Crush, Xbox, TikTok, etc.) de todos os perfis de usuário.

# \* \*\*Instalação Silenciosa de Softwares:\*\* Utiliza o \*Chocolatey\* e \*WinGet\* para baixar e instalar silenciosamente pacotes como Google Chrome, AnyDesk, TeamViewer, WinRAR, VLC, entre outros.

# \* \*\*Gestão de Drivers:\*\* Integra-se com assistentes oficiais (Dell Command Update, Lenovo System Update) ou força a instalação via Microsoft Update.

# 

# \### 🤖 Automação e Resiliência

# \* \*\*Motor "Self-Healing" (Cão de Guarda):\*\* Um script invisível de fundo (Watchdog) que monitora o sistema a cada 10 segundos, garantindo que o papel de parede corporativo e softwares de suporte (AnyDesk) nunca sejam alterados ou fechados pelos usuários.

# \* \*\*Manutenção Automática:\*\* Cria tarefas agendadas nativas para reiniciar o computador fora do horário comercial e atualizar softwares de forma invisível no logon.

# 

# \---

# 

# \## 🏗️ Arquitetura do Projeto

# 

# O ecossistema é modular e divide-se nos seguintes componentes:

# 

# | Arquivo | Descrição |

# |----------|-----------|

# | `EXECUTAR.bat` | O \*Launcher\* principal. Verifica privilégios de Admin e chama o instalador de pré-requisitos antes de iniciar a interface. |

# | `instalar\_pre\_requisitos.bat` | Script auxiliar que instala Python, Chocolatey e dependências PIP de forma robusta, evitando travamentos causados por aliases da Windows Store. |

# | `gui.py` | Interface gráfica moderna desenvolvida em `customtkinter`, permitindo a seleção granular das políticas a aplicar. |

# | `mod\_config.py` | O "Cérebro" de configuração. Injeta chaves de registro (\*Registry\*), gere o \*Firewall\*, limpa os \*widgets\*, implementa o Watchdog de Auto-Cura e gera snapshots de hardware com IDs de acesso remoto (AnyDesk/TeamViewer). |

# | `mod\_instalar.py` | Motor de \*deploy\*. Comunica com o Chocolatey e PowerShell para baixar softwares e drivers, com fallback inteligente para fabricantes (HP/Dell/Lenovo). |

# | `settings.json` | Arquivo de configuração. Define quais softwares serão instalados, listas de bloatware para remoção e caminhos de imagens corporativas. |

# | `manutencao\_rede.bat` | Script auxiliar injetado nas máquinas para corrigir falhas de IP dinâmico/estático (DHCP) e limpar cache DNS. |

# | `instalar\_tudo.ps1` | Script \*PowerShell\* agendado no sistema para manter as aplicações sempre atualizadas em segundo plano. |

# | `update\_checker.ps1` | Script de verificação de atualizações executado no logon do usuário, com proteção contra execução duplicada no mesmo dia. |

# 

# \---

# 

# \## ⚙️ Pré-requisitos

# 

# \* \*\*Sistema Operacional:\*\* Windows 10 ou Windows 11.

# \* \*\*Permissões:\*\* O usuário \*\*DEVE\*\* executar o script com privilégios de Administrador.

# \* \*\*Conectividade:\*\* Conexão à Internet ativa (necessária para baixar dependências, softwares e atualizar o relógio via NTP.br).

# 

# \*(Nota: Não é necessário ter o Python pré-instalado. O `instalar\_pre\_requisitos.bat` faz o download e a configuração do ambiente automaticamente de forma robusta, evitando conflitos com aliases da Windows Store).\*

# 

# \---

# 

# \## 🚀 Como Usar

# 

# 1\. Faça o download ou clone este repositório para o disco local (Ex: `C:\\Scripts\\Setup\_CPFANI`).

# 2\. Adicione a sua logo (`logo\_cpfani.png`) e papel de parede (`wallpaper\_cpfani.jpg`) dentro da pasta `resources\\`.

# 3\. Clique com o botão direito no arquivo \*\*`EXECUTAR.bat`\*\* e selecione \*\*"Executar como Administrador"\*\*.

# 4\. Uma janela de console (CMD) será aberta para preparar o ambiente. Aguarde.

# 5\. A Interface Gráfica (GUI) será iniciada.

# 6\. Selecione as opções de Branding, Segurança e Softwares que deseja aplicar.

# 7\. Clique em \*\*"EXECUTAR DEPLOY"\*\* e aguarde a finalização da barra de progresso.

# 8\. No final, será gerado um relatório de \*Hardware Snapshot\* na pasta `C:\\Scripts\\`, incluindo IDs de acesso remoto (AnyDesk/TeamViewer).

# 

# \---

# 

# \## 🌍 Versão Corporativa vs. Universal

# 

# Este projeto foi desenhado para escalabilidade:

# \* \*\*Modo Corporativo:\*\* Ativa o Firewall restrito, o Branding (Logos) e o Cão de Guarda (Self-Healing). Ideal para Ponto de Venda (PDV) e máquinas de loja.

# \* \*\*Modo Universal (Vanilla):\*\* Através da interface, desmarque a caixa "Ativar Self-Healing" e mantenha a opção de Firewall desmarcada para usar este motor como um poderoso otimizador para computadores pessoais e clientes externos, sem prender a máquina a regras de rede específicas.

# 

# \---

# 

# \## ⚠️ Isenção de Responsabilidade

# 

# Este script realiza alterações profundas no Registro do Windows (\*Registry\*), cria tarefas agendadas e remove pacotes nativos do sistema operacional. Embora amplamente testado em ambientes de produção, o uso é da inteira responsabilidade do usuário. Recomenda-se testar em ambiente controlado ou máquina virtual antes de aplicar em uma infraestrutura em grande escala.

# 

# \---

# \*Desenvolvido com ☕ e Python para automação de infraestruturas.\*


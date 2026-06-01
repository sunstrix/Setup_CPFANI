\# CHANGELOG - Setup\_CPFANI



Este documento detalha as correções de bugs, melhorias de segurança e novas funcionalidades implementadas na versão atual, seguindo rigorosos padrões de engenharia de software e automação Windows.



\## \[PARTE 1] - CORREÇÕES DE BUGS (CRÍTICAS)



\### 1. Robustez e Tratamento de Exceções

\- \*\*Alteração:\*\* Substituição global de blocos `try-except: pass` por tratamento de exceções específico e logging estruturado.

\- \*\*Justificativa:\*\* O silenciamento de erros impedia o diagnóstico de falhas em ambiente de produção. Agora, todas as falhas são registradas no `deployment.log`.



\### 2. Persistência do PATH do Python

\- \*\*Alteração:\*\* Correção no `EXECUTAR.bat` para forçar a recarga de variáveis de ambiente após a instalação do Python ou uso de caminhos absolutos.

\- \*\*Justificativa:\*\* Evita o erro de "Comando não encontrado" imediatamente após a instalação do binário.



\### 3. Verificação de Scripts Remotos

\- \*\*Alteração:\*\* Implementação de cálculo de Checksum (SHA256) para o `instalar\_tudo.ps1`.

\- \*\*Justificativa:\*\* Garante que scripts baixados do GitHub/Chocolatey não foram adulterados ou corrompidos durante o trânsito.



\### 4. Otimização de Recursos (Watchdog)

\- \*\*Alteração:\*\* Adicionado Throttling ao `cpfani\_watchdog.ps1` baseado em carga de CPU (>80%).

\- \*\*Justificativa:\*\* Impede que o loop de verificação degrade o desempenho de máquinas com hardware limitado.



\### 5. Fallback de Captura de SID

\- \*\*Alteração:\*\* Nova lógica em `\_get\_active\_user\_sid()` consultando WMI e chaves de registro `ProfileList`.

\- \*\*Justificativa:\*\* Garante a execução correta mesmo em cenários onde o `explorer.exe` não está carregado no momento da execução.



\### 6. Integridade de Recursos Visuais

\- \*\*Alteração:\*\* Validação de Hash SHA256 para Wallpapers e LockScreens baixados.

\- \*\*Justificativa:\*\* Previne a aplicação de imagens corrompidas que resultam em telas pretas ou erros de sistema.



\### 7. Firewall Hardening

\- \*\*Alteração:\*\* Implementação de bloqueio preventivo de portas SMB/RPC para perfis de rede "Pública".

\- \*\*Justificativa:\*\* Aumenta a segurança da máquina em redes externas, limitando o compartilhamento apenas a redes confiáveis (Privada/Domínio).



\### 8. Centralização de Configurações

\- \*\*Alteração:\*\* Criação do `config\_version.json`.

\- \*\*Justificativa:\*\* Elimina a inconsistência de versões espalhadas pelo código e centraliza listas de softwares e hashes.



\---



\## \[PARTE 2] - MELHORIAS E NOVAS FUNCIONALIDADES



\### 9. Automação de Compartilhamento e Impressoras

\- \*\*Funcionalidade:\*\* Função `configure\_network\_sharing()`.

\- \*\*Impacto:\*\* Ativação automática de descoberta de rede, serviços WSD para impressoras e liberação de portas SMB em redes privadas.



\### 10. Correção Definitiva da Lock Screen

\- \*\*Funcionalidade:\*\* Função `apply\_lockscreen\_wallpaper()`.

\- \*\*Impacto:\*\* Uso do diretório OEM (`backgrounds`) e registro `OEMBackground` para garantir a aplicação persistente da imagem de bloqueio.



\### 11. Gestão de Privilégios Dual-Mode

\- \*\*Funcionalidade:\*\* Criação do módulo `mod\_privileges.py`.

\- \*\*Impacto:\*\* Permite que o técnico escolha aplicar apenas configurações de usuário (sem admin) ou configurações de sistema (solicitando elevação).



\### 12. Redundância de Instalação (Office/OnlyOffice)

\- \*\*Funcionalidade:\*\* Lógica `install\_with\_redundancy`.

\- \*\*Impacto:\*\* Tentativas sequenciais: ODT -> Offline -> Chocolatey -> Winget -> Caminho UNC local. Garante a instalação mesmo sem internet ou em redes restritas.


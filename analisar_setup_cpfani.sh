#!/bin/bash
#
# Script: analisar_setup_cpfani.sh
# Descrição: Prepara o repositório Setup_CPFANI para análise pelo GitHub Copilot.
#            Extrai todo o código-fonte, gera um prompt com regras estritas
#            de refatoração (preservação, um arquivo por vez, painel de controle).
# Uso: ./analisar_setup_cpfani.sh
# Versão: 2.0 (Refatorado com melhorias)
#

set -euo pipefail  # Para em caso de erro, sem variáveis não definidas

# Cores para output (opcional)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ------------------------------------------------------------
# 1. Funções de Utilidade
# ------------------------------------------------------------

# Função para imprimir mensagens formatadas
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Função para validar requisitos
validate_requirements() {
    local missing=0
    
    print_info "Validando requisitos do sistema..."
    
    if ! command -v git &> /dev/null; then
        print_error "Git não está instalado. Por favor, instale Git e tente novamente."
        missing=1
    fi
    
    if ! command -v date &> /dev/null; then
        print_error "Date não está disponível."
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        exit 1
    fi
    
    print_success "Todos os requisitos estão disponíveis."
}

# Função para criar diretório com tratamento de erro
create_directory() {
    local dir="$1"
    if rm -rf "$dir" 2>/dev/null; then
        print_info "Diretório anterior removido: $dir"
    fi
    
    if mkdir -p "$dir"; then
        print_success "Diretório criado: $dir"
    else
        print_error "Falha ao criar diretório: $dir"
        exit 1
    fi
}

# Função para clonar repositório com tratamento de erro
clone_repository() {
    local repo_url="$1"
    local target_dir="$2"
    
    print_info "Clonando repositório: $repo_url"
    
    if git clone "$repo_url" "$target_dir" >> "$LOG_FILE" 2>&1; then
        print_success "Repositório clonado com sucesso."
    else
        print_error "Falha ao clonar repositório. Verifique a URL e sua conexão."
        exit 1
    fi
}

# Função para adicionar arquivo ao contexto com validação
adicionar_arquivo() {
    local file="$1"
    local context_file="$2"
    local ext="${file##*.}"
    
    {
        echo ""
        echo "📄 ARQUIVO: $file"
        echo "-------------------------------------------------------"
    } >> "$context_file"
    
    if [ -f "$file" ]; then
        # Determina o tipo de código para syntax highlight (markdown)
        local lang=""
        case "$ext" in
            py) lang="python" ;;
            ps1) lang="powershell" ;;
            bat|cmd) lang="batch" ;;
            json) lang="json" ;;
            md) lang="markdown" ;;
            txt) lang="text" ;;
            *) lang="" ;;
        esac
        
        {
            echo "\`\`\`$lang"
            cat "$file"
            echo "\`\`\`"
        } >> "$context_file"
        
        print_success "Arquivo adicionado: $file"
    else
        print_warning "Arquivo não encontrado: $file"
        echo "⚠️ Arquivo não encontrado: $file" >> "$context_file"
    fi
}

# Função para listar arquivos do projeto
list_project_files() {
    local context_file="$1"
    
    {
        echo ""
        echo "📦 LISTA DE ARQUIVOS DO PROJETO:"
        echo "---------------------------------"
    } >> "$context_file"
    
    if find . -type f ! -path "./.git/*" ! -name "*.pyc" ! -name "*.log" -print 2>/dev/null | sort >> "$context_file"; then
        print_success "Lista de arquivos gerada."
    else
        print_warning "Alguns arquivos não puderam ser listados."
    fi
}

# Função para gerar prompt
generate_prompt() {
    local prompt_file="$1"
    
    cat > "$prompt_file" << 'PROMPT_EOF'
Atue como um Engenheiro de Software Sênior e Especialista em Refatoração. Você vai me ajudar a corrigir e atualizar os códigos do meu projeto (https://github.com/sunstrix/Setup_CPFANI).

Para que o processo seja organizado e sem erros, você deve seguir ESTRITAMENTE as regras de fluxo e formatação abaixo em TODAS as respostas, sem exceção:

### 🚫 REGRA CRÍTICA DE PRESERVAÇÃO (NÃO REMOVA CÓDIGO)
Você NÃO DEVE e NÃO PODE remover nenhuma função, método ou lógica existente nos códigos originais. Você está autorizado a:
1. Corrigir bugs e erros na lógica atual.
2. Incluir novas funções e melhorias solicitadas.
Qualquer tipo de exclusão ou remoção de código existente está ESTRITAMENTE PROIBIDA, a menos que eu autorize explicitamente. Na dúvida, mantenha a função original intacta.

### 📋 REGRAS DE FLUXO (PASSO A PASSO)
1. Você deve analisar as correções necessárias e trabalhar em APENAS UM ARQUIVO POR VEZ.
2. NUNCA envie o código do próximo arquivo até que eu dê o comando de avanço.
3. Sempre envie o CÓDIGO COMPLETO e atualizado do arquivo da vez. Não use placeholders como "// o resto do código continua igual".

### 📊 PAINEL DE CONTROLE E PROGRESSO (OBRIGATÓRIO EM TODAS AS RESPOSTAS)
Toda vez que você me responder, você deve iniciar a sua resposta com:
1. Um contador claro: "Arquivos alterados/criados: X | Arquivos restantes: Y".
2. Uma TABELA Markdown mostrando o status de todos os arquivos envolvidos no processo (Nome do Arquivo | Caminho | Status: Concluído / Em Andamento / Pendente).

### 🛠️ COMANDO POWERSHELL
Para cada arquivo enviado, você deve fornecer o comando PowerShell exato para abrir ou criar o arquivo diretamente no Bloco de Notas, utilizando variáveis de ambiente para o caminho absoluto, exatamente neste formato:
notepad "$env:USERPROFILE\Desktop\Setup_CPFANI\EXECUTAR.bat"

### 📝 RESUMO PARA O GITHUB
Junto com o código do arquivo, envie um breve resumo em português das alterações feitas nele, formatado para mensagem de commit.

### ⚠️ GATILHO DE AVANÇO (ANTI-ESQUECIMENTO)
Eu usarei o comando "PRONTO" para avançar. Quando eu disser isso, você NÃO deve economizar texto ou esquecer as regras acima. O "PRONTO" é um comando para você trazer o próximo arquivo REPETINDO EXATAMENTE todo o painel de controle, tabela, comando PowerShell, resumo e respeitando a regra de não remoção.

---

Para começarmos: analise as correções que precisamos fazer no projeto (com base no link enviado). Antes de enviar o primeiro código, liste quais arquivos precisaremos alterar/criar e exiba a primeira tabela de progresso. Aguardo seu comando de início.

=================================================================
ARQUIVO DE CONTEXTO (código-fonte do projeto)
=================================================================

O código-fonte completo do projeto Setup_CPFANI está no arquivo
'contexto_completo.txt' que acompanha este prompt.

Analise o conteúdo desse arquivo para identificar erros, vulnerabilidades
e oportunidades de melhoria, seguindo todas as regras estabelecidas acima.
PROMPT_EOF

    print_success "Prompt gerado com sucesso."
}

# Função para gerar cabeçalho do contexto
generate_context_header() {
    local context_file="$1"
    
    cat > "$context_file" << 'HEADER_EOF'
# =================================================================
# CONTEXTO COMPLETO DO PROJETO: Setup_CPFANI
# =================================================================
# Projeto: Setup Automatizado de Endpoints (CP Fani / Universal)
# Repositório: https://github.com/sunstrix/Setup_CPFANI
#
# Descrição geral:
#   Ferramenta de provisionamento zero-touch para Windows.
#   Foco em segurança, otimização e auto-cura.
#   Inclui instalação de aplicativos (Chocolatey/Winget),
#   configurações de registro, firewall, permissões,
#   manutenção de rede e atualizações automáticas.
#
# Estrutura principal:
#   - EXECUTAR.bat              -> Launcher principal (admin, interface)
#   - instalar_pre_requisitos.bat -> Instala Python, Chocolatey e dependências
#   - gui.py                    -> Interface gráfica customtkinter
#   - mod_config.py             -> Módulo de configurações (registro, firewall, watchdog)
#   - mod_instalar.py           -> Motor de deploy (Chocolatey, Winget, PowerShell)
#   - settings.json             -> Lista de aplicativos a instalar
#   - manutencao_rede.bat       -> Correção de rede (IP, DNS, hosts)
#   - instalar_tudo.ps1         -> Script PowerShell de atualização contínua
#   - update_checker.ps1        -> Verificação de atualizações no logon
#
# =================================================================
HEADER_EOF

    print_success "Cabeçalho do contexto gerado."
}

# Função para exibir resumo final
print_summary() {
    local work_dir="$1"
    local context_file="$2"
    local prompt_file="$3"
    local log_file="$4"
    
    echo ""
    echo "================================================================="
    print_success "PREPARAÇÃO CONCLUÍDA COM SUCESSO!"
    echo "================================================================="
    echo ""
    echo "📁 Diretório de trabalho: $work_dir"
    echo "📄 Contexto completo: $context_file"
    echo "📝 Prompt para GitHub Copilot: $prompt_file"
    echo "📋 Log: $log_file"
    echo ""
    echo "🚀 COMO EXECUTAR A ANÁLISE COM O GITHUB COPILOT:"
    echo "================================================================="
    echo ""
    echo "Opção 1 (Copilot Chat no VS Code):"
    echo "----------------------------------"
    echo "1. Abra o VS Code e ative o GitHub Copilot Chat."
    echo "2. Abra o arquivo '$prompt_file' e copie todo o conteúdo."
    echo "3. No Copilot Chat, cole o prompt e anexe o arquivo '$context_file'"
    echo "   como contexto (ou cole o conteúdo dele junto)."
    echo "4. Envie a mensagem e aguarde a análise."
    echo ""
    echo "Opção 2 (Copilot Chat no GitHub.com):"
    echo "-------------------------------------"
    echo "1. Acesse o repositório no GitHub e abra o Copilot Chat."
    echo "2. Copie o conteúdo do prompt e cole no chat."
    echo "3. Adicione o conteúdo do arquivo de contexto como referência."
    echo ""
    echo "Opção 3 (Copilot no terminal via GitHub CLI - se disponível):"
    echo "-------------------------------------------------------------"
    echo "   gh copilot prompt -f \"$prompt_file\""
    echo ""
    echo "📊 ARQUIVOS GERADOS:"
    echo "-------------------"
    if [ -f "$context_file" ]; then
        local context_size
        context_size=$(wc -c < "$context_file")
        echo "   • contexto_completo.txt ($((context_size / 1024)) KB)"
    fi
    
    if [ -f "$prompt_file" ]; then
        echo "   • prompt_para_copilot.txt"
    fi
    
    if [ -f "$log_file" ]; then
        echo "   • analise_*.log"
    fi
    
    echo ""
    echo "================================================================="
    echo "✨ DICA: Para uma análise mais segura, peça ao Copilot para atuar"
    echo "   no modo 'Plan' ou revisar o código antes de sugerir alterações."
    echo "   Lembre-se de que o Copilot seguirá todas as regras de fluxo"
    echo "   e preservação definidas no prompt."
    echo "================================================================="
}

# ------------------------------------------------------------
# 2. Configuração
# ------------------------------------------------------------
REPO_URL="https://github.com/sunstrix/Setup_CPFANI"
WORK_DIR="./setup_cpfani_analise"
REPO_DIR="${WORK_DIR}/repo"
CONTEXT_FILE="${WORK_DIR}/contexto_completo.txt"
PROMPT_FILE="${WORK_DIR}/prompt_para_copilot.txt"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${WORK_DIR}/analise_${TIMESTAMP}.log"

# Arquivos a processar (em ordem lógica)
declare -a FILES_TO_PROCESS=(
    "EXECUTAR.bat"
    "instalar_pre_requisitos.bat"
    "gui.py"
    "mod_config.py"
    "mod_instalar.py"
    "settings.json"
    "manutencao_rede.bat"
    "instalar_tudo.ps1"
    "update_checker.ps1"
    "README.md"
)

# ------------------------------------------------------------
# 3. Execução Principal
# ------------------------------------------------------------

main() {
    print_info "======================================================"
    print_info "Script de Análise para GitHub Copilot - Setup_CPFANI"
    print_info "======================================================"
    echo ""
    
    # Validar requisitos
    validate_requirements
    echo ""
    
    # Preparar ambiente
    print_info "Preparando ambiente..."
    create_directory "$WORK_DIR"
    
    # Inicializar arquivo de log
    touch "$LOG_FILE"
    print_success "Log inicializado: $LOG_FILE"
    echo ""
    
    # Clonar repositório
    clone_repository "$REPO_URL" "$REPO_DIR"
    echo ""
    
    # Navegar para o repositório
    cd "$REPO_DIR" || exit 1
    print_info "Mudando para diretório: $(pwd)"
    echo ""
    
    # Gerar cabeçalho do contexto
    print_info "Gerando contexto do projeto..."
    generate_context_header "$CONTEXT_FILE"
    
    # Listar arquivos do projeto
    list_project_files "$CONTEXT_FILE"
    echo ""
    
    # Adicionar arquivos ao contexto
    print_info "Extraindo conteúdo dos arquivos-fonte..."
    for file in "${FILES_TO_PROCESS[@]}"; do
        adicionar_arquivo "$file" "$CONTEXT_FILE"
    done
    echo ""
    
    # Gerar prompt
    print_info "Gerando prompt para o GitHub Copilot..."
    generate_prompt "$PROMPT_FILE"
    echo ""
    
    # Voltar ao diretório original
    cd - > /dev/null || exit 1
    
    # Exibir resumo
    print_summary "$WORK_DIR" "$CONTEXT_FILE" "$PROMPT_FILE" "$LOG_FILE"
    
    echo ""
    print_success "Análise preparada com sucesso!"
    exit 0
}

# Executar a função principal
main "$@"

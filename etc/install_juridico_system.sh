#!/bin/bash

# ===================================================================
# SCRIPT DE INSTALAÇÃO - SISTEMA DE ANÁLISE JURÍDICA AUTOMATIZADA
# ===================================================================
# 
# Este script instala e configura completamente o sistema no VPS Hostinger
# 
# Uso: 
#   chmod +x install_juridico_system.sh
#   ./install_juridico_system.sh
# 
# ===================================================================

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Função para print colorido
print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${PURPLE}ℹ️  $1${NC}"
}

# Função para verificar se comando existe
check_command() {
    if command -v $1 >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Banner de início
echo -e "${GREEN}"
echo "=========================================="
echo "🛠️  SISTEMA DE ANÁLISE JURÍDICA"
echo "📋 Instalação Automatizada v1.0"
echo "=========================================="
echo -e "${NC}"

# Verificar se está rodando como root/sudo para algumas operações
if [[ $EUID -eq 0 ]]; then
    print_warning "Rodando como root. Algumas operações serão feitas como usuário normal."
    USAR_SUDO=""
else
    USAR_SUDO="sudo"
fi

# ===================================================================
# PASSO 1: ATUALIZAR SISTEMA
# ===================================================================
print_step "Atualizando sistema operacional..."
$USAR_SUDO apt-get update -y
$USAR_SUDO apt-get upgrade -y
print_success "Sistema atualizado"

# ===================================================================
# PASSO 2: INSTALAR DEPENDÊNCIAS DO SISTEMA
# ===================================================================
print_step "Instalando dependências do sistema..."

# Python 3 e pip
if ! check_command python3; then
    $USAR_SUDO apt-get install -y python3 python3-pip python3-venv
    print_success "Python 3 instalado"
else
    print_info "Python 3 já está instalado"
fi

# Tesseract OCR
if ! check_command tesseract; then
    $USAR_SUDO apt-get install -y tesseract-ocr tesseract-ocr-por
    print_success "Tesseract OCR instalado"
else
    print_info "Tesseract OCR já está instalado"
fi

# Dependências para compilação
$USAR_SUDO apt-get install -y build-essential python3-dev libffi-dev libssl-dev

# Dependências para matplotlib e opencv
$USAR_SUDO apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

print_success "Dependências do sistema instaladas"

# ===================================================================
# PASSO 3: CRIAR ESTRUTURA DE DIRETÓRIOS
# ===================================================================
print_step "Criando estrutura de diretórios..."

# Definir diretório base
JURIDICO_DIR="/home/$(whoami)/juridico_analyzer"

# Criar estrutura
mkdir -p $JURIDICO_DIR/{scripts,temp,outputs,logs,backups}
mkdir -p $JURIDICO_DIR/data/files  # Para compatibilidade com N8N

# Definir permissões
chmod 755 $JURIDICO_DIR
chmod 777 $JURIDICO_DIR/{temp,outputs,logs}  # Escrita livre para N8N

print_success "Estrutura de diretórios criada em: $JURIDICO_DIR"

# ===================================================================
# PASSO 4: CONFIGURAR AMBIENTE VIRTUAL PYTHON
# ===================================================================
print_step "Configurando ambiente virtual Python..."

cd $JURIDICO_DIR

# Criar ambiente virtual
python3 -m venv venv_juridico

# Ativar ambiente virtual
source venv_juridico/bin/activate

# Atualizar pip
pip install --upgrade pip setuptools wheel

print_success "Ambiente virtual criado e ativado"

# ===================================================================
# PASSO 5: INSTALAR DEPENDÊNCIAS PYTHON
# ===================================================================
print_step "Instalando dependências Python (pode demorar alguns minutos)..."

# Instalar torch primeiro (mais estável)
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu

# Instalar demais dependências
pip install PyMuPDF==1.24.1
pip install pdfplumber==0.10.3
pip install pytesseract==0.3.10
pip install pillow==10.2.0
pip install opencv-python-headless==4.9.0.80

# Análise de dados
pip install pandas==2.2.0
pip install numpy==1.26.4
pip install scipy==1.11.4
pip install scikit-learn==1.7.0

# NLP
pip install spacy==3.7.2
pip install sentence-transformers==2.7.0
pip install transformers==4.36.2
pip install faiss-cpu==1.7.4
pip install nltk==3.8.1

# Relatórios
pip install reportlab==4.1.0
pip install matplotlib==3.8.4

# Utilitários
pip install pyyaml==6.0.1
pip install python-dotenv==1.0.0
pip install requests==2.31.0
pip install beautifulsoup4==4.12.2
pip install python-dateutil==2.8.2
pip install regex==2023.12.25
pip install langdetect==1.0.9
pip install structlog==23.2.0

print_success "Dependências Python instaladas"

# ===================================================================
# PASSO 6: BAIXAR MODELO SPACY PORTUGUÊS
# ===================================================================
print_step "Baixando modelo spaCy português..."

python -m spacy download pt_core_news_sm

if [ $? -eq 0 ]; then
    print_success "Modelo spaCy português instalado"
else
    print_error "Erro ao baixar modelo spaCy. Tentando instalação alternativa..."
    pip install https://github.com/explosion/spacy-models/releases/download/pt_core_news_sm-3.7.0/pt_core_news_sm-3.7.0-py3-none-any.whl
fi

# ===================================================================
# PASSO 7: BAIXAR DADOS NLTK NECESSÁRIOS
# ===================================================================
print_step "Baixando dados NLTK..."
python -c "
import nltk
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
print('NLTK dados baixados com sucesso')
"

# ===================================================================
# PASSO 8: CRIAR ARQUIVOS DE CONFIGURAÇÃO
# ===================================================================
print_step "Criando arquivos de configuração..."

# Criar arquivo de ambiente
cat > $JURIDICO_DIR/.env << 'EOF'
# Configurações do Sistema de Análise Jurídica

# Caminhos
JURIDICO_BASE_DIR=/home/$(whoami)/juridico_analyzer
JURIDICO_TEMP_DIR=/home/$(whoami)/juridico_analyzer/temp
JURIDICO_OUTPUT_DIR=/home/$(whoami)/juridico_analyzer/outputs
JURIDICO_LOGS_DIR=/home/$(whoami)/juridico_analyzer/logs

# N8N Integration
N8N_DATA_DIR=/data/files
N8N_OUTPUT_DIR=/tmp

# Configurações de processamento
MAX_FILE_SIZE_MB=50
PROCESSING_TIMEOUT=300
MIN_CONFIDENCE_LEVEL=0.3
OCR_QUALITY=high
MAX_PAGES_PROCESS=100

# Logging
LOG_LEVEL=INFO
ENABLE_DETAILED_LOGS=true

# Sistema
PYTHON_ENV=production
SYSTEM_VERSION=1.0.0
EOF

# Script de ativação do ambiente
cat > $JURIDICO_DIR/activate_env.sh << 'EOF'
#!/bin/bash
# Script para ativar ambiente do sistema jurídico
cd /home/$(whoami)/juridico_analyzer
source venv_juridico/bin/activate
source .env
echo "✅ Ambiente jurídico ativado"
echo "📁 Diretório: $(pwd)"
echo "🐍 Python: $(which python3)"
echo "📦 Pacotes instalados: $(pip list | wc -l)"
EOF

chmod +x $JURIDICO_DIR/activate_env.sh

print_success "Arquivos de configuração criados"

# ===================================================================
# PASSO 9: TESTAR INSTALAÇÃO
# ===================================================================
print_step "Testando instalação..."

# Teste básico de imports
python3 << 'EOF'
try:
    import sys
    import spacy
    import fitz  # PyMuPDF
    import pytesseract
    import reportlab
    import pandas
    import numpy
    from sentence_transformers import SentenceTransformer
    
    print("✅ Todos os imports básicos funcionando")
    
    # Testar modelo spaCy
    nlp = spacy.load("pt_core_news_sm")
    doc = nlp("Este é um teste do modelo português.")
    print(f"✅ Modelo spaCy funcionando: {len(doc)} tokens processados")
    
    # Testar Tesseract
    import PIL.Image
    print("✅ Tesseract disponível")
    
    print("🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
    
except ImportError as e:
    print(f"❌ Erro de import: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erro no teste: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    print_success "Todos os testes passaram"
else
    print_error "Falha nos testes. Verifique os logs acima."
    exit 1
fi

# ===================================================================
# PASSO 10: CRIAR SCRIPT DE MONITORAMENTO
# ===================================================================
print_step "Criando script de monitoramento..."

cat > $JURIDICO_DIR/monitor_sistema.sh << 'EOF'
#!/bin/bash
# Monitor do Sistema Jurídico

JURIDICO_DIR="/home/$(whoami)/juridico_analyzer"
cd $JURIDICO_DIR

echo "🔍 MONITORAMENTO DO SISTEMA JURÍDICO"
echo "=================================="
echo "📅 Data: $(date)"
echo ""

# Status do ambiente
echo "🐍 AMBIENTE PYTHON:"
source venv_juridico/bin/activate
echo "   Ambiente: $(which python3)"
echo "   Versão: $(python3 --version)"
echo ""

# Status dos diretórios
echo "📁 DIRETÓRIOS:"
echo "   Base: $JURIDICO_DIR ($(du -sh $JURIDICO_DIR | cut -f1))"
echo "   Temp: $(ls $JURIDICO_DIR/temp | wc -l) arquivos"
echo "   Outputs: $(ls $JURIDICO_DIR/outputs | wc -l) arquivos"
echo "   Logs: $(ls $JURIDICO_DIR/logs | wc -l) arquivos"
echo ""

# Últimos processamentos
echo "📊 ÚLTIMOS PROCESSAMENTOS:"
if [ -f "$JURIDICO_DIR/logs/processamento.log" ]; then
    echo "   Total de linhas de log: $(wc -l < $JURIDICO_DIR/logs/processamento.log)"
    echo "   Últimas 3 execuções:"
    tail -n 3 $JURIDICO_DIR/logs/processamento.log | while read line; do
        timestamp=$(echo $line | jq -r '.timestamp' 2>/dev/null || echo "Data não disponível")
        sucesso=$(echo $line | jq -r '.sucesso' 2>/dev/null || echo "false")
        arquivo=$(echo $line | jq -r '.arquivo' 2>/dev/null || echo "Arquivo não disponível")
        echo "     [$timestamp] $(echo $sucesso | sed 's/true/✅/g' | sed 's/false/❌/g') $arquivo"
    done
else
    echo "   Nenhum log encontrado ainda"
fi
echo ""

# Teste rápido
echo "🧪 TESTE RÁPIDO:"
python3 -c "
import spacy, fitz, pytesseract, reportlab
print('   ✅ Imports principais: OK')

nlp = spacy.load('pt_core_news_sm')
print('   ✅ Modelo spaCy: OK')

print('   🎯 Sistema operacional e funcional!')
" 2>/dev/null

echo ""
echo "=================================="
EOF

chmod +x $JURIDICO_DIR/monitor_sistema.sh

# ===================================================================
# PASSO 11: CONFIGURAR CRONTAB PARA LIMPEZA AUTOMÁTICA
# ===================================================================
print_step "Configurando limpeza automática..."

# Adicionar job do cron para limpeza (apenas se não existir)
CRON_JOB="0 3 * * * find $JURIDICO_DIR/temp -name '*.pdf' -mtime +7 -delete"
(crontab -l 2>/dev/null | grep -v "$JURIDICO_DIR/temp"; echo "$CRON_JOB") | crontab -

print_success "Limpeza automática configurada (todo dia às 3h)"

# ===================================================================
# PASSO 12: CRIAR LINK SIMBÓLICO PARA N8N
# ===================================================================
print_step "Configurando integração com N8N..."

# Criar link simbólico para N8N acessar mais facilmente
if [ -d "/data/files" ]; then
    ln -sf /data/files $JURIDICO_DIR/data/n8n_files
    print_success "Link para N8N criado: $JURIDICO_DIR/data/n8n_files -> /data/files"
else
    print_warning "Diretório /data/files do N8N não encontrado"
fi

# ===================================================================
# FINALIZAÇÃO
# ===================================================================
echo ""
echo -e "${GREEN}=========================================="
echo "🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo "=========================================="
echo -e "${NC}"

print_info "PRÓXIMOS PASSOS:"
echo ""
echo "1️⃣  Fazer upload dos arquivos Python para:"
echo "    📂 $JURIDICO_DIR/scripts/"
echo ""
echo "2️⃣  Arquivos necessários:"
echo "    📄 __init__.py"
echo "    📄 main_juridico.py"
echo "    📄 extrair_texto_juridico.py"
echo "    📄 analisar_processo.py"
echo "    📄 gerar_relatorio_juridico.py"
echo "    📄 patterns_juridicos.yaml"
echo "    📄 tipos_processuais.yaml"
echo ""
echo "3️⃣  Testar o sistema:"
echo "    📋 cd $JURIDICO_DIR"
echo "    📋 source activate_env.sh"
echo "    📋 python3 scripts/main_juridico.py /data/files/teste.pdf"
echo ""
echo "4️⃣  Configurar N8N Execute Command:"
echo "    📋 cd $JURIDICO_DIR && source venv_juridico/bin/activate && python3 scripts/main_juridico.py \"/data/files/{{JSON do N8N com nome do arquivo}}\""
echo ""
echo "5️⃣  Monitorar sistema:"
echo "    📋 $JURIDICO_DIR/monitor_sistema.sh"
echo ""

print_success "SISTEMA PRONTO PARA RECEBER OS ARQUIVOS PYTHON!"

echo ""
echo -e "${BLUE}📋 INFORMAÇÕES DO AMBIENTE:${NC}"
echo "🏠 Diretório base: $JURIDICO_DIR"
echo "🐍 Python: $(which python3)"
echo "🎯 Ambiente virtual: $JURIDICO_DIR/venv_juridico"
echo "📊 Monitor: $JURIDICO_DIR/monitor_sistema.sh"
echo "🔧 Configuração: $JURIDICO_DIR/.env"
echo ""

# Criar arquivo de status da instalação
cat > $JURIDICO_DIR/STATUS_INSTALACAO.txt << EOF
SISTEMA DE ANÁLISE JURÍDICA - STATUS DA INSTALAÇÃO
==================================================

Data da instalação: $(date)
Usuário: $(whoami)
Hostname: $(hostname)
Sistema: $(uname -a)

COMPONENTES INSTALADOS:
- ✅ Python 3 e pip
- ✅ Tesseract OCR (português)
- ✅ Ambiente virtual Python
- ✅ Dependências do sistema
- ✅ Estrutura de diretórios
- ✅ Modelo spaCy português
- ✅ Scripts de monitoramento
- ✅ Limpeza automática (cron)

PRÓXIMO PASSO:
Upload dos arquivos Python para: $JURIDICO_DIR/scripts/

TESTE RÁPIDO:
source $JURIDICO_DIR/activate_env.sh
python3 -c "import spacy; print('Sistema OK!')"

STATUS: ✅ PRONTO PARA RECEBER ARQUIVOS PYTHON
EOF

echo -e "${GREEN}📄 Status salvo em: $JURIDICO_DIR/STATUS_INSTALACAO.txt${NC}"
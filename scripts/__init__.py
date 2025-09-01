#!/usr/bin/env python3
"""
Sistema de Análise Jurídica Automatizada
=========================================

Este pacote fornece funcionalidades completas para análise automatizada de documentos jurídicos,
incluindo extração de texto, análise processual e geração de relatórios.

Módulos principais:
- extrair_texto_juridico: Extração de texto de PDFs jurídicos
- analisar_processo: Análise inteligente de processos judiciais
- gerar_relatorio_juridico: Geração de relatórios PDF formatados
- main_juridico: Script orquestrador principal

Dependências necessárias:
- Python 3.8+
- spaCy com modelo pt_core_news_sm
- PyMuPDF (fitz)
- pytesseract
- reportlab
- sentence-transformers
- pyyaml

Instalação do modelo spaCy:
    python -m spacy download pt_core_news_sm

Uso básico:
    from scripts.main_juridico import processar_documento_completo
    resultado = processar_documento_completo("documento.pdf")

Autor: Sistema de Análise Jurídica
Versão: 1.0.0
"""

import logging
import sys
from pathlib import Path

# Versão do sistema
__version__ = "1.0.0"
__author__ = "Sistema de Análise Jurídica"
__email__ = "suporte@analise-juridica.com"

# Configuração de logging padrão para o pacote
def configurar_logging(nivel=logging.INFO, arquivo_log=None):
    """
    Configura o sistema de logging para todos os módulos do pacote
    
    Args:
        nivel: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        arquivo_log: Caminho para arquivo de log (opcional)
    """
    formato = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if arquivo_log:
        logging.basicConfig(
            level=nivel,
            format=formato,
            handlers=[
                logging.FileHandler(arquivo_log, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    else:
        logging.basicConfig(level=nivel, format=formato)
    
    # Configurar logging específico para bibliotecas externas
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.ERROR)

# Verificar dependências críticas na importação
def verificar_dependencias():
    """Verifica se todas as dependências críticas estão disponíveis"""
    dependencias_criticas = [
        ('spacy', 'spaCy'),
        ('fitz', 'PyMuPDF'),
        ('pytesseract', 'pytesseract'),
        ('reportlab', 'ReportLab'),
        ('yaml', 'PyYAML'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy')
    ]
    
    dependencias_faltantes = []
    
    for modulo, nome_display in dependencias_criticas:
        try:
            __import__(modulo)
        except ImportError:
            dependencias_faltantes.append(nome_display)
    
    if dependencias_faltantes:
        logging.warning(
            f"Dependências não encontradas: {', '.join(dependencias_faltantes)}. "
            "Algumas funcionalidades podem não funcionar corretamente."
        )
        return False
    
    return True

def verificar_modelo_spacy():
    """Verifica se o modelo português do spaCy está instalado"""
    try:
        import spacy
        spacy.load("pt_core_news_sm")
        return True
    except (ImportError, OSError):
        logging.error(
            "Modelo spaCy português não encontrado. "
            "Execute: python -m spacy download pt_core_news_sm"
        )
        return False

# Configurações padrão do sistema
CONFIGURACOES_PADRAO = {
    'max_tamanho_arquivo_mb': 50,
    'timeout_processamento_segundos': 300,
    'qualidade_ocr': 'alta',
    'modelo_embeddings': 'neuralmind/bert-base-portuguese-cased',
    'idioma_principal': 'pt',
    'formato_data_padrao': '%d/%m/%Y',
    'nivel_confianca_minimo': 0.3,
    'max_paginas_processamento': 100,
    'diretorio_temp': '/tmp',
    'diretorio_logs': './logs',
    'diretorio_output': './outputs'
}

# Utilitários de configuração
def obter_configuracao(chave, padrao=None):
    """
    Obtém valor de configuração, usando padrão se não encontrado
    
    Args:
        chave: Chave da configuração
        padrao: Valor padrão se chave não existir
        
    Returns:
        Valor da configuração
    """
    return CONFIGURACOES_PADRAO.get(chave, padrao)

def criar_diretorios_necessarios():
    """Cria diretórios necessários para funcionamento do sistema"""
    diretorios = [
        obter_configuracao('diretorio_logs'),
        obter_configuracao('diretorio_output'),
        obter_configuracao('diretorio_temp') + '/juridico_temp'
    ]
    
    for diretorio in diretorios:
        Path(diretorio).mkdir(parents=True, exist_ok=True)

# Executar verificações na importação
if __name__ != "__main__":
    # Configurar logging padrão
    configurar_logging()
    
    # Criar diretórios necessários
    criar_diretorios_necessarios()
    
    # Verificar dependências
    deps_ok = verificar_dependencias()
    modelo_ok = verificar_modelo_spacy()
    
    if not deps_ok:
        logging.warning("Sistema iniciado com dependências faltantes")
    
    if not modelo_ok:
        logging.warning("Sistema iniciado sem modelo spaCy português")
    
    logging.info(f"Sistema de Análise Jurídica v{__version__} inicializado")

# Exportar principais funções e classes
try:
    from .extrair_texto_juridico import extrair_texto_pdf, ExtratorTextoJuridico
    from .analisar_processo import analisar_documento_juridico, AnalisadorJuridico
    from .gerar_relatorio_juridico import gerar_relatorio_pdf, GeradorRelatorioJuridico
    from .main_juridico import processar_documento_completo
    
    __all__ = [
        'extrair_texto_pdf',
        'ExtratorTextoJuridico', 
        'analisar_documento_juridico',
        'AnalisadorJuridico',
        'gerar_relatorio_pdf',
        'GeradorRelatorioJuridico',
        'processar_documento_completo',
        'configurar_logging',
        'obter_configuracao',
        '__version__'
    ]
    
except ImportError as e:
    logging.warning(f"Erro ao importar módulos: {e}")
    __all__ = ['configurar_logging', 'obter_configuracao', '__version__']
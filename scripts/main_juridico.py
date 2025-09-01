#!/usr/bin/env python3
"""
Script Principal - Sistema de Análise Jurídica Automatizada
===========================================================

Este é o script orquestrador principal que coordena todas as etapas do processamento:
1. Extração de texto do PDF
2. Análise jurídica inteligente
3. Geração de relatório PDF
4. Retorno de dados estruturados para N8N

Uso:
    python main_juridico.py /caminho/para/documento.pdf

Output:
    JSON estruturado para integração com workflow N8N

Autor: Sistema de Análise Jurídica
"""

import sys
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Configurar logging antes de imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Imports dos módulos do sistema
try:
    from extrair_texto_juridico import extrair_texto_pdf
    from analisar_processo import analisar_documento_juridico
    from gerar_relatorio_juridico import gerar_relatorio_pdf
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    sys.exit(1)


class ProcessadorDocumentoJuridico:
    """
    Classe principal que orquestra todo o processo de análise jurídica.
    
    Esta classe coordena a extração de texto, análise processual e geração
    de relatórios de forma integrada, fornecendo interface unificada para
    o workflow N8N.
    """
    
    def __init__(self):
        """Inicializa o processador com configurações padrão"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timestamp_inicio = datetime.now()
        
        # Configurações do processamento
        self.config = {
            'max_tamanho_arquivo_mb': 50,
            'timeout_processamento': 300,
            'nivel_confianca_minimo': 0.3,
            'gerar_relatorio_pdf': True,
            'salvar_logs_detalhados': True,
            'diretorio_output': '/tmp',
            'prefixo_arquivos': 'analise_processo'
        }
        
        # Métricas de processamento
        self.metricas = {
            'inicio_processamento': self.timestamp_inicio.isoformat(),
            'tempo_extracao': None,
            'tempo_analise': None,
            'tempo_relatorio': None,
            'tempo_total': None,
            'tamanho_arquivo_mb': None,
            'paginas_processadas': None,
            'confianca_analise': None
        }
    
    def validar_arquivo(self, caminho_arquivo: str) -> Dict[str, Any]:
        """
        Valida se o arquivo existe e pode ser processado
        
        Args:
            caminho_arquivo: Caminho para o arquivo PDF
            
        Returns:
            Dict com resultado da validação
        """
        try:
            caminho = Path(caminho_arquivo)
            
            # Verificar se arquivo existe
            if not caminho.exists():
                return {
                    'valido': False,
                    'erro': f'Arquivo não encontrado: {caminho_arquivo}'
                }
            
            # Verificar extensão
            if caminho.suffix.lower() != '.pdf':
                return {
                    'valido': False,
                    'erro': f'Arquivo deve ser PDF. Encontrado: {caminho.suffix}'
                }
            
            # Verificar tamanho
            tamanho_mb = caminho.stat().st_size / (1024 * 1024)
            self.metricas['tamanho_arquivo_mb'] = round(tamanho_mb, 2)
            
            if tamanho_mb > self.config['max_tamanho_arquivo_mb']:
                return {
                    'valido': False,
                    'erro': f'Arquivo muito grande: {tamanho_mb:.1f}MB. Máximo: {self.config["max_tamanho_arquivo_mb"]}MB'
                }
            
            self.logger.info(f"Arquivo validado: {caminho.name} ({tamanho_mb:.1f}MB)")
            
            return {
                'valido': True,
                'caminho': str(caminho.absolute()),
                'nome_arquivo': caminho.name,
                'tamanho_mb': tamanho_mb
            }
            
        except Exception as e:
            return {
                'valido': False,
                'erro': f'Erro na validação: {str(e)}'
            }
    
    def extrair_texto_documento(self, caminho_arquivo: str) -> Dict[str, Any]:
        """
        Extrai texto do documento PDF usando o módulo especializado
        
        Args:
            caminho_arquivo: Caminho para o arquivo PDF
            
        Returns:
            Dict com resultado da extração
        """
        inicio = datetime.now()
        self.logger.info("Iniciando extração de texto...")
        
        try:
            # Chamar extrator de texto
            resultado_extracao = extrair_texto_pdf(caminho_arquivo)
            
            # Calcular tempo de processamento
            tempo_extracao = (datetime.now() - inicio).total_seconds()
            self.metricas['tempo_extracao'] = tempo_extracao
            
            if not resultado_extracao['sucesso']:
                self.logger.error(f"Erro na extração: {resultado_extracao.get('erro', 'Erro desconhecido')}")
                return resultado_extracao
            
            # Log estatísticas da extração
            stats = resultado_extracao.get('estatisticas', {})
            self.metricas['paginas_processadas'] = stats.get('total_paginas', 0)
            
            self.logger.info(
                f"Texto extraído com sucesso: "
                f"{len(resultado_extracao['texto_completo'])} caracteres, "
                f"{stats.get('total_paginas', 0)} páginas, "
                f"{tempo_extracao:.1f}s"
            )
            
            return resultado_extracao
            
        except Exception as e:
            erro_msg = f"Erro na extração de texto: {str(e)}"
            self.logger.error(erro_msg)
            return {
                'sucesso': False,
                'erro': erro_msg,
                'stack_trace': traceback.format_exc()
            }
    
    def analisar_documento(self, texto_documento: str, metadados_extracao: Dict = None) -> Dict[str, Any]:
        """
        Realiza análise jurídica completa do documento
        
        Args:
            texto_documento: Texto extraído do PDF
            metadados_extracao: Metadados da extração
            
        Returns:
            Dict com resultado da análise
        """
        inicio = datetime.now()
        self.logger.info("Iniciando análise jurídica...")
        
        try:
            # Chamar analisador jurídico
            resultado_analise = analisar_documento_juridico(texto_documento, metadados_extracao)
            
            # Calcular tempo de processamento
            tempo_analise = (datetime.now() - inicio).total_seconds()
            self.metricas['tempo_analise'] = tempo_analise
            
            if resultado_analise.get('erro'):
                self.logger.error(f"Erro na análise: {resultado_analise['erro']}")
                return resultado_analise
            
            # Extrair métricas da análise
            confianca = resultado_analise.get('analise_completa', {}).get('confianca_analise', 0)
            self.metricas['confianca_analise'] = confianca
            
            # Verificar nível de confiança mínimo
            if confianca < self.config['nivel_confianca_minimo']:
                self.logger.warning(
                    f"Análise com baixa confiança: {confianca:.1%} "
                    f"(mínimo: {self.config['nivel_confianca_minimo']:.1%})"
                )
            
            self.logger.info(
                f"Análise concluída: confiança {confianca:.1%}, "
                f"{tempo_analise:.1f}s"
            )
            
            return resultado_analise
            
        except Exception as e:
            erro_msg = f"Erro na análise jurídica: {str(e)}"
            self.logger.error(erro_msg)
            return {
                'erro': erro_msg,
                'stack_trace': traceback.format_exc()
            }
    
    def gerar_relatorio_final(self, resultado_analise: Dict, nome_arquivo_original: str) -> Dict[str, Any]:
        """
        Gera relatório PDF final da análise
        
        Args:
            resultado_analise: Resultado da análise jurídica
            nome_arquivo_original: Nome do arquivo original
            
        Returns:
            Dict com resultado da geração do relatório
        """
        if not self.config['gerar_relatorio_pdf']:
            self.logger.info("Geração de relatório PDF desabilitada")
            return {'sucesso': True, 'relatorio_gerado': False}
        
        inicio = datetime.now()
        self.logger.info("Gerando relatório PDF...")
        
        try:
            # Preparar dados para o relatório
            dados_relatorio = {
                'analise_completa': resultado_analise,
                'nome_arquivo_original': nome_arquivo_original,
                'metricas_processamento': self.metricas,
                'timestamp_processamento': self.timestamp_inicio.isoformat()
            }
            
            # Gerar nome do arquivo de relatório
            timestamp_str = self.timestamp_inicio.strftime("%Y%m%d_%H%M%S")
            nome_relatorio = f"{self.config['prefixo_arquivos']}_completo_{timestamp_str}.pdf"
            caminho_relatorio = Path(self.config['diretorio_output']) / nome_relatorio
            
            # Chamar gerador de relatório
            resultado_relatorio = gerar_relatorio_pdf(dados_relatorio, str(caminho_relatorio))
            
            # Calcular tempo de processamento
            tempo_relatorio = (datetime.now() - inicio).total_seconds()
            self.metricas['tempo_relatorio'] = tempo_relatorio
            
            if not resultado_relatorio['sucesso']:
                self.logger.error(f"Erro na geração do relatório: {resultado_relatorio.get('erro')}")
                return resultado_relatorio
            
            self.logger.info(
                f"Relatório PDF gerado: {nome_relatorio} ({tempo_relatorio:.1f}s)"
            )
            
            return {
                'sucesso': True,
                'relatorio_gerado': True,
                'caminho_relatorio': str(caminho_relatorio),
                'nome_relatorio': nome_relatorio,
                'tamanho_relatorio_kb': resultado_relatorio.get('tamanho_arquivo_kb', 0)
            }
            
        except Exception as e:
            erro_msg = f"Erro na geração do relatório: {str(e)}"
            self.logger.error(erro_msg)
            return {
                'sucesso': False,
                'erro': erro_msg,
                'stack_trace': traceback.format_exc()
            }
    
    def processar_documento_completo(self, caminho_arquivo: str) -> Dict[str, Any]:
        """
        Executa processamento completo do documento jurídico
        
        Args:
            caminho_arquivo: Caminho para o arquivo PDF
            
        Returns:
            Dict com resultado completo para N8N
        """
        self.logger.info(f"=== PROCESSAMENTO INICIADO: {caminho_arquivo} ===")
        
        try:
            # 1. Validar arquivo
            validacao = self.validar_arquivo(caminho_arquivo)
            if not validacao['valido']:
                return self._criar_resposta_erro(validacao['erro'], fase='validacao')
            
            # 2. Extrair texto
            resultado_extracao = self.extrair_texto_documento(caminho_arquivo)
            if not resultado_extracao['sucesso']:
                return self._criar_resposta_erro(
                    resultado_extracao.get('erro', 'Erro na extração'),
                    fase='extracao'
                )
            
            # 3. Analisar documento
            resultado_analise = self.analisar_documento(
                resultado_extracao['texto_completo'],
                resultado_extracao.get('metadados_arquivo', {})
            )
            
            if resultado_analise.get('erro'):
                return self._criar_resposta_erro(
                    resultado_analise['erro'],
                    fase='analise'
                )
            
            # 4. Gerar relatório PDF
            resultado_relatorio = self.gerar_relatorio_final(
                resultado_analise,
                validacao['nome_arquivo']
            )
            
            # 5. Calcular tempo total
            self.metricas['tempo_total'] = (datetime.now() - self.timestamp_inicio).total_seconds()
            
            # 6. Preparar resposta final
            resposta_final = self._criar_resposta_sucesso(
                resultado_analise,
                resultado_relatorio,
                validacao
            )
            
            self.logger.info(
                f"=== PROCESSAMENTO CONCLUÍDO: {self.metricas['tempo_total']:.1f}s ==="
            )
            
            # 7. Salvar logs detalhados se configurado
            if self.config['salvar_logs_detalhados']:
                self._salvar_logs_detalhados(resposta_final)
            
            return resposta_final
            
        except Exception as e:
            erro_msg = f"Erro crítico no processamento: {str(e)}"
            self.logger.error(erro_msg)
            self.logger.error(traceback.format_exc())
            
            return self._criar_resposta_erro(erro_msg, fase='processamento_geral')
    
    def _criar_resposta_erro(self, mensagem_erro: str, fase: str) -> Dict[str, Any]:
        """Cria resposta padronizada para erros"""
        self.metricas['tempo_total'] = (datetime.now() - self.timestamp_inicio).total_seconds()
        
        return {
            'sucesso': False,
            'erro': mensagem_erro,
            'fase_erro': fase,
            'timestamp_erro': datetime.now().isoformat(),
            'metricas_processamento': self.metricas,
            'logs_sistema': {
                'nivel_log': 'ERROR',
                'modulo': self.__class__.__name__
            }
        }
    
    def _criar_resposta_sucesso(self, resultado_analise: Dict, resultado_relatorio: Dict, 
                               validacao_arquivo: Dict) -> Dict[str, Any]:
        """Cria resposta padronizada para sucessos"""
        
        # Preparar resumo executivo para N8N
        analise_completa = resultado_analise.get('analise_completa', {})
        estatisticas = resultado_analise.get('estatisticas', {})
        
        resumo_n8n = {
            'numero_processo': analise_completa.get('numero_processo', 'Não identificado'),
            'tipo_acao': analise_completa.get('tipo_acao', []),
            'orgao_julgador': analise_completa.get('orgao_julgador', 'Não identificado'),
            'total_partes': estatisticas.get('total_partes_identificadas', 0),
            'tem_decisao': estatisticas.get('tem_decisao', False),
            'confianca_analise': analise_completa.get('confianca_analise', 0),
            'nivel_confianca': estatisticas.get('nivel_confianca', 'Baixo')
        }
        
        return {
            'sucesso': True,
            'timestamp_conclusao': datetime.now().isoformat(),
            'arquivo_processado': {
                'nome_original': validacao_arquivo['nome_arquivo'],
                'tamanho_mb': validacao_arquivo['tamanho_mb'],
                'caminho': validacao_arquivo['caminho']
            },
            'resumo_analise': resumo_n8n,
            'resultado_completo': resultado_analise,
            'relatorio_pdf': {
                'gerado': resultado_relatorio.get('relatorio_gerado', False),
                'caminho': resultado_relatorio.get('caminho_relatorio'),
                'nome_arquivo': resultado_relatorio.get('nome_relatorio'),
                'tamanho_kb': resultado_relatorio.get('tamanho_relatorio_kb', 0)
            },
            'metricas_processamento': self.metricas,
            'logs_sistema': {
                'nivel_log': 'INFO',
                'modulo': self.__class__.__name__,
                'mensagem': 'Processamento concluído com sucesso'
            }
        }
    
    def _salvar_logs_detalhados(self, resposta_final: Dict) -> None:
        """Salva logs detalhados do processamento"""
        try:
            timestamp_str = self.timestamp_inicio.strftime("%Y%m%d_%H%M%S")
            nome_log = f"log_processamento_{timestamp_str}.json"
            caminho_log = Path(self.config['diretorio_output']) / nome_log
            
            with open(caminho_log, 'w', encoding='utf-8') as f:
                json.dump(resposta_final, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Log detalhado salvo: {nome_log}")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar log detalhado: {e}")


def processar_documento_completo(caminho_arquivo: str) -> Dict[str, Any]:
    """
    Função wrapper para facilitar importação externa
    
    Args:
        caminho_arquivo: Caminho para o arquivo PDF
        
    Returns:
        Dict com resultado completo do processamento
    """
    processador = ProcessadorDocumentoJuridico()
    return processador.processar_documento_completo(caminho_arquivo)


def main():
    """
    Função principal para execução via linha de comando
    Compatível com workflow N8N
    """
    
    # Verificar argumentos da linha de comando
    if len(sys.argv) < 2:
        erro = {
            'sucesso': False,
            'erro': 'Uso: python main_juridico.py <caminho_para_pdf>',
            'exemplo': 'python main_juridico.py /data/files/processo.pdf',
            'timestamp_erro': datetime.now().isoformat()
        }
        print(json.dumps(erro, ensure_ascii=False))
        sys.exit(1)
    
    caminho_arquivo = sys.argv[1]
    
    # Processar documento
    resultado = processar_documento_completo(caminho_arquivo)
    
    # Output JSON para N8N
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    
    # Exit code baseado no sucesso
    sys.exit(0 if resultado['sucesso'] else 1)


if __name__ == "__main__":
    main()
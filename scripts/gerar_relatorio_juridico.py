#!/usr/bin/env python3
"""
Gerador de Relatórios Jurídicos em PDF
======================================

Este módulo gera relatórios PDF profissionais e detalhados das análises jurídicas,
incluindo todas as informações extraídas, gráficos e estatísticas formatadas
adequadamente para uso jurídico.

Funcionalidades:
- Relatórios PDF com formatação jurídica profissional
- Cabeçalho institucional personalizável
- Seções organizadas hierarquicamente
- Gráficos e estatísticas visuais
- Tabelas de informações estruturadas
- Rodapé com metadados técnicos

Uso:
    from gerar_relatorio_juridico import gerar_relatorio_pdf
    resultado = gerar_relatorio_pdf(dados_analise, "caminho/relatorio.pdf")

Autor: Sistema de Análise Jurídica
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json

# Imports ReportLab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, KeepTogether
    )
    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
except ImportError as e:
    logging.error(f"ReportLab não encontrado: {e}")
    raise ImportError("Instale ReportLab: pip install reportlab")

# Imports para gráficos (opcional)
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import numpy as np
    MATPLOTLIB_DISPONIVEL = True
except ImportError:
    logging.warning("Matplotlib não disponível - gráficos serão desabilitados")
    MATPLOTLIB_DISPONIVEL = False


class GeradorRelatorioJuridico:
    """
    Classe responsável por gerar relatórios PDF profissionais de análises jurídicas.
    
    Esta classe organiza todas as informações extraídas da análise em um formato
    PDF estruturado e profissional, adequado para uso em ambientes jurídicos.
    """
    
    def __init__(self):
        """Inicializa o gerador com configurações padrão"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Configurações do documento
        self.configuracoes = {
            'tamanho_pagina': A4,
            'margem_esquerda': 2.5 * cm,
            'margem_direita': 2.5 * cm,
            'margem_superior': 3 * cm,
            'margem_inferior': 2.5 * cm,
            'espaco_paragrafo': 6,
            'fonte_titulo': 'Helvetica-Bold',
            'fonte_texto': 'Helvetica',
            'tamanho_titulo_principal': 16,
            'tamanho_titulo_secao': 14,
            'tamanho_texto': 10,
            'cor_primaria': colors.HexColor('#1e3a8a'),  # Azul escuro
            'cor_secundaria': colors.HexColor('#3b82f6'),  # Azul médio
            'cor_texto': colors.HexColor('#1f2937'),  # Cinza escuro
        }
        
        # Estilos de parágrafo
        self.estilos = self._criar_estilos()
        
        # Informações institucionais
        self.info_institucional = {
            'titulo_sistema': 'Sistema de Análise Jurídica Automatizada',
            'subtitulo': 'Relatório de Análise Processual',
            'instituicao': 'Análise Jurídica Inteligente',
            'versao_sistema': '1.0.0',
            'contato': 'suporte@analise-juridica.com'
        }
    
    def _criar_estilos(self) -> Dict[str, ParagraphStyle]:
        """Cria estilos personalizados para o documento"""
        estilos_base = getSampleStyleSheet()
        
        estilos_customizados = {
            # Título principal do documento
            'titulo_principal': ParagraphStyle(
                'TituloPrincipal',
                parent=estilos_base['Heading1'],
                fontSize=self.configuracoes['tamanho_titulo_principal'],
                fontName=self.configuracoes['fonte_titulo'],
                textColor=self.configuracoes['cor_primaria'],
                alignment=TA_CENTER,
                spaceAfter=20,
                spaceBefore=10
            ),
            
            # Subtítulo do documento
            'subtitulo': ParagraphStyle(
                'Subtitulo',
                parent=estilos_base['Heading2'],
                fontSize=12,
                fontName=self.configuracoes['fonte_titulo'],
                textColor=self.configuracoes['cor_secundaria'],
                alignment=TA_CENTER,
                spaceAfter=30,
                spaceBefore=5
            ),
            
            # Títulos de seção
            'titulo_secao': ParagraphStyle(
                'TituloSecao',
                parent=estilos_base['Heading2'],
                fontSize=self.configuracoes['tamanho_titulo_secao'],
                fontName=self.configuracoes['fonte_titulo'],
                textColor=self.configuracoes['cor_primaria'],
                alignment=TA_LEFT,
                spaceAfter=12,
                spaceBefore=20,
                borderWidth=0,
                borderColor=self.configuracoes['cor_primaria'],
                borderPadding=5,
                backColor=colors.HexColor('#f8fafc')
            ),
            
            # Texto normal
            'texto_normal': ParagraphStyle(
                'TextoNormal',
                parent=estilos_base['Normal'],
                fontSize=self.configuracoes['tamanho_texto'],
                fontName=self.configuracoes['fonte_texto'],
                textColor=self.configuracoes['cor_texto'],
                alignment=TA_JUSTIFY,
                spaceAfter=self.configuracoes['espaco_paragrafo'],
                spaceBefore=2
            ),
            
            # Texto destacado
            'texto_destaque': ParagraphStyle(
                'TextoDestaque',
                parent=estilos_base['Normal'],
                fontSize=self.configuracoes['tamanho_texto'],
                fontName=self.configuracoes['fonte_titulo'],
                textColor=self.configuracoes['cor_primaria'],
                alignment=TA_LEFT,
                spaceAfter=8,
                spaceBefore=2
            ),
            
            # Texto de dados (tabelas)
            'texto_dados': ParagraphStyle(
                'TextoDados',
                parent=estilos_base['Normal'],
                fontSize=9,
                fontName=self.configuracoes['fonte_texto'],
                textColor=self.configuracoes['cor_texto'],
                alignment=TA_LEFT,
                spaceAfter=3,
                spaceBefore=1
            ),
            
            # Rodapé
            'rodape': ParagraphStyle(
                'Rodape',
                parent=estilos_base['Normal'],
                fontSize=8,
                fontName=self.configuracoes['fonte_texto'],
                textColor=colors.gray,
                alignment=TA_CENTER,
                spaceAfter=5,
                spaceBefore=5
            )
        }
        
        return estilos_customizados
    
    def _criar_cabecalho(self, dados_processamento: Dict) -> List:
        """Cria cabeçalho do relatório com informações institucionais"""
        elementos = []
        
        # Título principal
        titulo = Paragraph(
            self.info_institucional['titulo_sistema'],
            self.estilos['titulo_principal']
        )
        elementos.append(titulo)
        
        # Subtítulo
        subtitulo = Paragraph(
            self.info_institucional['subtitulo'],
            self.estilos['subtitulo']
        )
        elementos.append(subtitulo)
        
        # Linha separadora visual
        elementos.append(Spacer(1, 10))
        
        # Informações do processamento
        arquivo_nome = dados_processamento.get('arquivo_processado', {}).get('nome_original', 'Documento não identificado')
        timestamp = datetime.fromisoformat(dados_processamento.get('timestamp_conclusao', datetime.now().isoformat()))
        
        info_processamento = [
            ['<b>Documento Analisado:</b>', arquivo_nome],
            ['<b>Data/Hora da Análise:</b>', timestamp.strftime('%d/%m/%Y às %H:%M:%S')],
            ['<b>Sistema:</b>', f"{self.info_institucional['instituicao']} v{self.info_institucional['versao_sistema']}"]
        ]
        
        tabela_info = Table(info_processamento, colWidths=[4*cm, 12*cm])
        tabela_info.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        
        elementos.append(tabela_info)
        elementos.append(Spacer(1, 20))
        
        return elementos
    
    def _criar_secao_informacoes_processuais(self, analise: Dict) -> List:
        """Cria seção com informações básicas do processo"""
        elementos = []
        
        # Título da seção
        titulo = Paragraph("1. INFORMAÇÕES PROCESSUAIS", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        analise_dados = analise.get('analise_completa', {})
        
        # Dados principais em formato de tabela
        dados_processo = [
            ['<b>Número do Processo:</b>', analise_dados.get('numero_processo', 'Não identificado')],
            ['<b>Tipo de Ação:</b>', ', '.join(analise_dados.get('tipo_acao', ['Não identificado']))],
            ['<b>Órgão Julgador:</b>', analise_dados.get('orgao_julgador', 'Não identificado')],
            ['<b>Instância:</b>', analise_dados.get('instancia', 'Não identificada')],
        ]
        
        # Adicionar informações opcionais se disponíveis
        if analise_dados.get('data_distribuicao'):
            dados_processo.append(['<b>Data de Distribuição:</b>', analise_dados['data_distribuicao']])
        
        if analise_dados.get('valor_causa'):
            dados_processo.append(['<b>Valor da Causa:</b>', analise_dados['valor_causa']])
        
        # Criar tabela
        tabela_processo = Table(dados_processo, colWidths=[4.5*cm, 11*cm])
        tabela_processo.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc'))
        ]))
        
        elementos.append(tabela_processo)
        elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _criar_secao_partes(self, analise: Dict) -> List:
        """Cria seção com informações das partes do processo"""
        elementos = []
        
        titulo = Paragraph("2. PARTES DO PROCESSO", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        partes = analise.get('analise_completa', {}).get('partes', {})
        
        # Autores
        if partes.get('autores'):
            elementos.append(Paragraph('<b>POLO ATIVO (AUTORES):</b>', self.estilos['texto_destaque']))
            for i, autor in enumerate(partes['autores'][:5], 1):  # Máximo 5 autores
                elementos.append(Paragraph(f"{i}. {autor}", self.estilos['texto_normal']))
            elementos.append(Spacer(1, 10))
        
        # Réus
        if partes.get('reus'):
            elementos.append(Paragraph('<b>POLO PASSIVO (RÉUS):</b>', self.estilos['texto_destaque']))
            for i, reu in enumerate(partes['reus'][:5], 1):  # Máximo 5 réus
                elementos.append(Paragraph(f"{i}. {reu}", self.estilos['texto_normal']))
            elementos.append(Spacer(1, 10))
        
        # Terceiros
        if partes.get('terceiros'):
            elementos.append(Paragraph('<b>TERCEIROS INTERESSADOS:</b>', self.estilos['texto_destaque']))
            for i, terceiro in enumerate(partes['terceiros'][:3], 1):
                elementos.append(Paragraph(f"{i}. {terceiro}", self.estilos['texto_normal']))
            elementos.append(Spacer(1, 10))
        
        # Advogados
        if partes.get('advogados'):
            elementos.append(Paragraph('<b>ADVOGADOS IDENTIFICADOS:</b>', self.estilos['texto_destaque']))
            for i, advogado in enumerate(partes['advogados'][:8], 1):  # Máximo 8 advogados
                elementos.append(Paragraph(f"{i}. {advogado}", self.estilos['texto_dados']))
            elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _criar_secao_decisao(self, analise: Dict) -> List:
        """Cria seção com informações da decisão judicial"""
        elementos = []
        
        decisao = analise.get('analise_completa', {}).get('decisao')
        
        if not decisao:
            return elementos
        
        titulo = Paragraph("3. DECISÃO JUDICIAL", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        # Dados da decisão
        dados_decisao = [
            ['<b>Tipo de Decisão:</b>', decisao.get('tipo_decisao', 'Não identificado')],
            ['<b>Resultado:</b>', decisao.get('resultado', 'Não determinado')],
        ]
        
        if decisao.get('data_decisao'):
            dados_decisao.append(['<b>Data da Decisão:</b>', decisao['data_decisao']])
        
        # Criar tabela
        tabela_decisao = Table(dados_decisao, colWidths=[4*cm, 12*cm])
        tabela_decisao.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc'))
        ]))
        
        elementos.append(tabela_decisao)
        elementos.append(Spacer(1, 12))
        
        # Dispositivo
        if decisao.get('dispositivo'):
            elementos.append(Paragraph('<b>DISPOSITIVO:</b>', self.estilos['texto_destaque']))
            dispositivo_texto = decisao['dispositivo'][:800]  # Limitar tamanho
            if len(decisao['dispositivo']) > 800:
                dispositivo_texto += "..."
            elementos.append(Paragraph(dispositivo_texto, self.estilos['texto_normal']))
            elementos.append(Spacer(1, 10))
        
        # Fundamentação resumida
        if decisao.get('fundamentacao_resumida'):
            elementos.append(Paragraph('<b>FUNDAMENTAÇÃO (RESUMO):</b>', self.estilos['texto_destaque']))
            fundamentacao_texto = decisao['fundamentacao_resumida'][:600]
            if len(decisao['fundamentacao_resumida']) > 600:
                fundamentacao_texto += "..."
            elementos.append(Paragraph(fundamentacao_texto, self.estilos['texto_normal']))
        
        elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _criar_secao_informacoes_adicionais(self, analise: Dict) -> List:
        """Cria seção com informações complementares"""
        elementos = []
        
        info_adicionais = analise.get('informacoes_adicionais', {})
        
        if not info_adicionais:
            return elementos
        
        titulo = Paragraph("4. INFORMAÇÕES COMPLEMENTARES", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        # Custas e honorários
        custas = info_adicionais.get('custas_honorarios', {})
        if any(custas.values()):
            elementos.append(Paragraph('<b>CUSTAS E HONORÁRIOS:</b>', self.estilos['texto_destaque']))
            
            dados_custas = []
            for campo, valor in custas.items():
                if valor and str(valor).lower() != 'false':
                    nome_campo = campo.replace('_', ' ').title()
                    dados_custas.append([nome_campo + ':', str(valor)])
            
            if dados_custas:
                tabela_custas = Table(dados_custas, colWidths=[5*cm, 10*cm])
                tabela_custas.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP')
                ]))
                elementos.append(tabela_custas)
            
            elementos.append(Spacer(1, 12))
        
        # Legislação citada
        legislacao = info_adicionais.get('legislacao_citada', [])
        if legislacao:
            elementos.append(Paragraph('<b>LEGISLAÇÃO CITADA:</b>', self.estilos['texto_destaque']))
            for i, lei in enumerate(legislacao[:10], 1):
                elementos.append(Paragraph(f"{i}. {lei}", self.estilos['texto_dados']))
            elementos.append(Spacer(1, 12))
        
        # Jurisprudência
        jurisprudencia = info_adicionais.get('jurisprudencia_citada', [])
        if jurisprudencia:
            elementos.append(Paragraph('<b>JURISPRUDÊNCIA CITADA:</b>', self.estilos['texto_destaque']))
            for i, jurisp in enumerate(jurisprudencia[:8], 1):
                elementos.append(Paragraph(f"{i}. {jurisp}", self.estilos['texto_dados']))
            elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _criar_secao_resumo_executivo(self, analise: Dict) -> List:
        """Cria seção com resumo executivo da análise"""
        elementos = []
        
        titulo = Paragraph("5. RESUMO EXECUTIVO", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        resumo = analise.get('analise_completa', {}).get('resumo_executivo', '')
        
        if resumo:
            elementos.append(Paragraph(resumo, self.estilos['texto_normal']))
        else:
            elementos.append(Paragraph('Resumo executivo não disponível.', self.estilos['texto_normal']))
        
        elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _criar_secao_estatisticas(self, dados_processamento: Dict) -> List:
        """Cria seção com estatísticas e métricas da análise"""
        elementos = []
        
        titulo = Paragraph("6. MÉTRICAS DE PROCESSAMENTO", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        # Métricas de processamento
        metricas = dados_processamento.get('metricas_processamento', {})
        estatisticas = dados_processamento.get('resultado_completo', {}).get('estatisticas', {})
        
        # Dados para tabela de métricas
        dados_metricas = []
        
        if metricas.get('tempo_total'):
            dados_metricas.append(['Tempo Total de Processamento:', f"{metricas['tempo_total']:.1f} segundos"])
        
        if metricas.get('confianca_analise'):
            confianca_pct = f"{metricas['confianca_analise']:.1%}"
            dados_metricas.append(['Nível de Confiança da Análise:', confianca_pct])
        
        if metricas.get('tamanho_arquivo_mb'):
            dados_metricas.append(['Tamanho do Arquivo:', f"{metricas['tamanho_arquivo_mb']:.1f} MB"])
        
        if metricas.get('paginas_processadas'):
            dados_metricas.append(['Páginas Processadas:', str(metricas['paginas_processadas'])])
        
        total_partes = estatisticas.get('total_partes_identificadas', 0)
        if total_partes > 0:
            dados_metricas.append(['Total de Partes Identificadas:', str(total_partes)])
        
        tem_decisao = estatisticas.get('tem_decisao', False)
        dados_metricas.append(['Decisão Judicial Identificada:', 'Sim' if tem_decisao else 'Não'])
        
        # Criar tabela
        if dados_metricas:
            tabela_metricas = Table(dados_metricas, colWidths=[6*cm, 9*cm])
            tabela_metricas.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc'))
            ]))
            
            elementos.append(tabela_metricas)
        
        elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _criar_grafico_confianca(self, confianca: float) -> Optional[str]:
        """Cria gráfico visual da confiança da análise"""
        if not MATPLOTLIB_DISPONIVEL or confianca is None:
            return None
        
        try:
            # Criar figura
            fig, ax = plt.subplots(1, 1, figsize=(6, 3))
            fig.patch.set_facecolor('white')
            
            # Configurar gráfico de barras horizontal
            categorias = ['Baixa\n(0-40%)', 'Média\n(40-70%)', 'Alta\n(70-100%)']
            cores = ['#ef4444', '#f59e0b', '#10b981']  # Vermelho, Amarelo, Verde
            
            # Determinar categoria atual
            if confianca <= 0.4:
                categoria_atual = 0
            elif confianca <= 0.7:
                categoria_atual = 1
            else:
                categoria_atual = 2
            
            # Criar barras
            for i, (categoria, cor) in enumerate(zip(categorias, cores)):
                alpha = 1.0 if i == categoria_atual else 0.3
                ax.barh(i, 1, color=cor, alpha=alpha, height=0.6)
                
                # Adicionar texto
                texto = f"{categoria}"
                if i == categoria_atual:
                    texto += f"\n({confianca:.1%})"
                
                ax.text(0.5, i, texto, ha='center', va='center', 
                       fontweight='bold' if i == categoria_atual else 'normal',
                       fontsize=10 if i == categoria_atual else 9)
            
            ax.set_xlim(0, 1)
            ax.set_ylim(-0.5, 2.5)
            ax.set_yticks([])
            ax.set_xticks([])
            ax.set_title('Nível de Confiança da Análise', fontsize=12, fontweight='bold', pad=20)
            
            # Remover spines
            for spine in ax.spines.values():
                spine.set_visible(False)
            
            plt.tight_layout()
            
            # Salvar em arquivo temporário
            caminho_grafico = '/tmp/grafico_confianca_juridico.png'
            plt.savefig(caminho_grafico, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return caminho_grafico
            
        except Exception as e:
            self.logger.error(f"Erro ao criar gráfico: {e}")
            return None
    
    def _criar_rodape(self, dados_processamento: Dict) -> List:
        """Cria rodapé do documento"""
        elementos = []
        
        # Linha separadora
        elementos.append(Spacer(1, 20))
        
        # Informações técnicas
        timestamp = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
        texto_rodape = (
            f"Relatório gerado automaticamente pelo {self.info_institucional['titulo_sistema']} "
            f"em {timestamp}. "
            f"Versão {self.info_institucional['versao_sistema']} - "
            f"Contato: {self.info_institucional['contato']}"
        )
        
        rodape = Paragraph(texto_rodape, self.estilos['rodape'])
        elementos.append(rodape)
        
        return elementos
    
    def gerar_relatorio_pdf(self, dados_processamento: Dict, caminho_saida: str) -> Dict[str, Any]:
        """
        Gera relatório PDF completo da análise jurídica
        
        Args:
            dados_processamento: Dados completos do processamento
            caminho_saida: Caminho onde salvar o PDF
            
        Returns:
            Dict com resultado da geração
        """
        try:
            self.logger.info(f"Gerando relatório PDF: {caminho_saida}")
            
            # Criar diretório se não existir
            Path(caminho_saida).parent.mkdir(parents=True, exist_ok=True)
            
            # Configurar documento
            doc = SimpleDocTemplate(
                caminho_saida,
                pagesize=self.configuracoes['tamanho_pagina'],
                leftMargin=self.configuracoes['margem_esquerda'],
                rightMargin=self.configuracoes['margem_direita'],
                topMargin=self.configuracoes['margem_superior'],
                bottomMargin=self.configuracoes['margem_inferior']
            )
            
            # Lista para elementos do documento
            elementos = []
            
            # 1. Cabeçalho
            elementos.extend(self._criar_cabecalho(dados_processamento))
            
            # 2. Informações processuais
            elementos.extend(self._criar_secao_informacoes_processuais(
                dados_processamento.get('resultado_completo', {})
            ))
            
            # 3. Partes do processo
            elementos.extend(self._criar_secao_partes(
                dados_processamento.get('resultado_completo', {})
            ))
            
            # 4. Decisão judicial
            elementos.extend(self._criar_secao_decisao(
                dados_processamento.get('resultado_completo', {})
            ))
            
            # 5. Informações adicionais
            elementos.extend(self._criar_secao_informacoes_adicionais(
                dados_processamento.get('resultado_completo', {})
            ))
            
            # 6. Resumo executivo
            elementos.extend(self._criar_secao_resumo_executivo(
                dados_processamento.get('resultado_completo', {})
            ))
            
            # 7. Palavras-chave
            elementos.extend(self._criar_secao_palavras_chave(
                dados_processamento.get('resultado_completo', {})
            ))
            
            # 8. Gráfico de confiança (se disponível)
            confianca = dados_processamento.get('metricas_processamento', {}).get('confianca_analise')
            if confianca:
                caminho_grafico = self._criar_grafico_confianca(confianca)
                if caminho_grafico:
                    try:
                        img = Image(caminho_grafico, width=12*cm, height=6*cm)
                        elementos.append(img)
                        elementos.append(Spacer(1, 15))
                        # Limpar arquivo temporário
                        os.unlink(caminho_grafico)
                    except Exception as e:
                        self.logger.warning(f"Erro ao incluir gráfico: {e}")
            
            # 9. Estatísticas
            elementos.extend(self._criar_secao_estatisticas(dados_processamento))
            
            # 10. Anexo com texto completo (opcional)
            if len(dados_processamento.get('resultado_completo', {}).get('sentenca_integra', '')) > 1000:
                elementos.extend(self._criar_anexo_texto_completo(
                    dados_processamento.get('resultado_completo', {})
                ))
            
            # 11. Rodapé
            elementos.extend(self._criar_rodape(dados_processamento))
            
            # Gerar PDF
            doc.build(elementos)
            
            # Verificar se arquivo foi criado e obter tamanho
            arquivo_path = Path(caminho_saida)
            if arquivo_path.exists():
                tamanho_kb = arquivo_path.stat().st_size / 1024
                self.logger.info(f"Relatório PDF gerado com sucesso: {tamanho_kb:.1f} KB")
                
                return {
                    'sucesso': True,
                    'caminho_arquivo': caminho_saida,
                    'tamanho_arquivo_kb': round(tamanho_kb, 1),
                    'timestamp_geracao': datetime.now().isoformat()
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'Arquivo PDF não foi criado'
                }
        
        except Exception as e:
            erro_msg = f"Erro ao gerar relatório PDF: {str(e)}"
            self.logger.error(erro_msg)
            return {
                'sucesso': False,
                'erro': erro_msg,
                'stack_trace': str(e)
            }


def gerar_relatorio_pdf(dados_analise: Dict, caminho_saida: str) -> Dict[str, Any]:
    """
    Função wrapper para gerar relatório PDF
    
    Args:
        dados_analise: Dados da análise jurídica
        caminho_saida: Caminho onde salvar o PDF
        
    Returns:
        Dict com resultado da geração
    """
    gerador = GeradorRelatorioJuridico()
    return gerador.gerar_relatorio_pdf(dados_analise, caminho_saida)


    def _criar_secao_palavras_chave(self, analise: Dict) -> List:
        """Cria seção com palavras-chave identificadas"""
        elementos = []
        
        palavras_chave = analise.get('analise_completa', {}).get('palavras_chave', [])
        
        if not palavras_chave:
            return elementos
        
        titulo = Paragraph("7. PALAVRAS-CHAVE IDENTIFICADAS", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        # Organizar palavras-chave em colunas
        colunas = 3
        linhas = []
        for i in range(0, len(palavras_chave), colunas):
            linha = palavras_chave[i:i+colunas]
            # Preencher linha se incompleta
            while len(linha) < colunas:
                linha.append("")
            linhas.append(linha)
        
        if linhas:
            tabela_palavras = Table(linhas, colWidths=[5*cm, 5*cm, 5*cm])
            tabela_palavras.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey)
            ]))
            
            elementos.append(tabela_palavras)
        
        elementos.append(Spacer(1, 15))
        
        return elementos
    
    def _criar_anexo_texto_completo(self, analise: Dict) -> List:
        """Cria anexo com texto completo do documento (primeira página)"""
        elementos = []
        
        # Quebra de página para anexo
        elementos.append(PageBreak())
        
        titulo = Paragraph("ANEXO: TEXTO EXTRAÍDO DO DOCUMENTO", self.estilos['titulo_secao'])
        elementos.append(titulo)
        
        texto_completo = analise.get('sentenca_integra', '')
        
        if texto_completo:
            # Limitar texto para não sobrecarregar o PDF (primeiros 3000 caracteres)
            texto_limitado = texto_completo[:3000]
            if len(texto_completo) > 3000:
                texto_limitado += "\n\n[TEXTO TRUNCADO - Documento completo disponível nos arquivos originais]"
            
            # Dividir em parágrafos para melhor formatação
            paragrafos = texto_limitado.split('\n\n')
            
            for paragrafo in paragrafos[:10]:  # Máximo 10 parágrafos
                if paragrafo.strip():
                    paragrafo_formatado = Paragraph(paragrafo.strip(), self.estilos['texto_dados'])
                    elementos.append(paragrafo_formatado)
                    elementos.append(Spacer(1, 8))
        else:
            elementos.append(Paragraph(
                'Texto completo não disponível.',
                self.estilos['texto_normal']
            ))
        
        return elementos


def gerar_relatorio_pdf(dados_analise: Dict, caminho_saida: str) -> Dict[str, Any]:
    """
    Função wrapper para gerar relatório PDF
    
    Args:
        dados_analise: Dados da análise jurídica
        caminho_saida: Caminho onde salvar o PDF
        
    Returns:
        Dict com resultado da geração
    """
    gerador = GeradorRelatorioJuridico()
    return gerador.gerar_relatorio_pdf(dados_analise, caminho_saida)


def gerar_relatorio_simples(resumo_analise: Dict, caminho_saida: str) -> Dict[str, Any]:
    """
    Gera relatório PDF simplificado (mais rápido)
    
    Args:
        resumo_analise: Dados resumidos da análise
        caminho_saida: Caminho onde salvar o PDF
        
    Returns:
        Dict com resultado da geração
    """
    try:
        doc = SimpleDocTemplate(caminho_saida, pagesize=A4)
        elementos = []
        
        # Estilo simples
        estilo_titulo = ParagraphStyle(
            'Titulo',
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        estilo_texto = ParagraphStyle(
            'Texto',
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_LEFT,
            spaceAfter=6
        )
        
        # Título
        elementos.append(Paragraph("RELATÓRIO DE ANÁLISE JURÍDICA", estilo_titulo))
        elementos.append(Spacer(1, 20))
        
        # Dados principais
        for chave, valor in resumo_analise.items():
            if valor:
                texto = f"<b>{chave.replace('_', ' ').title()}:</b> {valor}"
                elementos.append(Paragraph(texto, estilo_texto))
        
        # Gerar PDF
        doc.build(elementos)
        
        return {
            'sucesso': True,
            'caminho_arquivo': caminho_saida,
            'tipo_relatorio': 'simplificado'
        }
        
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e)
        }


def main():
    """Função para teste independente do módulo"""
    import sys
    
    if len(sys.argv) < 3:
        print("Uso: python gerar_relatorio_juridico.py <arquivo_dados.json> <saida.pdf>")
        print("Exemplo: python gerar_relatorio_juridico.py resultado_analise.json relatorio.pdf")
        sys.exit(1)
    
    arquivo_dados = sys.argv[1]
    caminho_saida = sys.argv[2]
    
    try:
        # Carregar dados de teste
        with open(arquivo_dados, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Gerar relatório
        resultado = gerar_relatorio_pdf(dados, caminho_saida)
        
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        
        if resultado['sucesso']:
            print(f"\nRelatório PDF gerado com sucesso: {caminho_saida}")
        else:
            print(f"\nErro na geração: {resultado['erro']}")
            sys.exit(1)
        
    except FileNotFoundError:
        print(json.dumps({
            'sucesso': False,
            'erro': f'Arquivo de dados não encontrado: {arquivo_dados}'
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    except json.JSONDecodeError:
        print(json.dumps({
            'sucesso': False,
            'erro': f'Erro ao decodificar JSON: {arquivo_dados}'
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            'sucesso': False,
            'erro': str(e)
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Sistema de Extração de Texto Jurídico
Extrai e limpa texto de PDFs jurídicos usando múltiplas técnicas
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
import logging
from pathlib import Path
import io
from typing import Dict, List, Tuple, Optional
import pdfplumber

class ExtratorTextoJuridico:
    def __init__(self, log_level=logging.INFO):
        """Inicializa o extrator com configurações otimizadas para documentos jurídicos"""
        
        # Configurar logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Configurações Tesseract para português jurídico
        self.tesseract_config = '--psm 6 -l por'
        
        # Padrões para limpeza de texto jurídico
        self.padroes_limpeza = [
            # Remover números de página isolados
            r'^\s*\d+\s*$',
            # Remover cabeçalhos repetitivos
            r'Poder Judiciário.*?(?=\n)',
            r'Tribunal.*?(?=\n)',
            # Remover rodapés
            r'Página \d+ de \d+',
            # Remover caracteres especiais desnecessários
            r'[^\w\s.,;:!?()\-\'"áéíóúàèìòùâêîôûãõç]',
            # Espaços múltiplos
            r'\s+',
        ]
        
        # Configurações para melhoria de imagem
        self.preprocessamento_configs = {
            'dpi': 300,
            'threshold_type': cv2.THRESH_BINARY,
            'blur_kernel': (1, 1),
            'erosion_kernel': (1, 1)
        }

    def extrair_texto_pymupdf(self, caminho_pdf: str) -> Dict[str, any]:
        """Extrai texto usando PyMuPDF (mais rápido)"""
        try:
            texto_completo = []
            metadados = {}
            
            with fitz.open(caminho_pdf) as doc:
                metadados = {
                    'total_paginas': len(doc),
                    'titulo': doc.metadata.get('title', ''),
                    'autor': doc.metadata.get('author', ''),
                    'criador': doc.metadata.get('creator', ''),
                    'data_criacao': doc.metadata.get('creationDate', '')
                }
                
                for num_pagina, pagina in enumerate(doc, 1):
                    texto_pagina = pagina.get_text()
                    
                    if texto_pagina.strip():
                        texto_completo.append({
                            'pagina': num_pagina,
                            'texto': self._limpar_texto(texto_pagina),
                            'metodo': 'pymupdf'
                        })
                        self.logger.debug(f"Página {num_pagina}: {len(texto_pagina)} caracteres extraídos")
            
            return {
                'sucesso': True,
                'metadados': metadados,
                'paginas': texto_completo,
                'texto_completo': self._concatenar_paginas(texto_completo)
            }
            
        except Exception as e:
            self.logger.error(f"Erro no PyMuPDF: {str(e)}")
            return {'sucesso': False, 'erro': str(e)}

    def extrair_texto_pdfplumber(self, caminho_pdf: str) -> Dict[str, any]:
        """Extrai texto usando pdfplumber (melhor para tabelas)"""
        try:
            texto_completo = []
            
            with pdfplumber.open(caminho_pdf) as pdf:
                metadados = {
                    'total_paginas': len(pdf.pages),
                    'metadados_pdf': pdf.metadata
                }
                
                for num_pagina, pagina in enumerate(pdf.pages, 1):
                    texto_pagina = pagina.extract_text()
                    
                    # Extrair tabelas se existirem
                    tabelas = pagina.extract_tables()
                    
                    if texto_pagina:
                        texto_completo.append({
                            'pagina': num_pagina,
                            'texto': self._limpar_texto(texto_pagina),
                            'tabelas': len(tabelas),
                            'metodo': 'pdfplumber'
                        })
                        
                        # Adicionar conteúdo das tabelas
                        if tabelas:
                            for i, tabela in enumerate(tabelas):
                                texto_tabela = self._processar_tabela(tabela)
                                texto_completo.append({
                                    'pagina': num_pagina,
                                    'texto': texto_tabela,
                                    'tipo': f'tabela_{i+1}',
                                    'metodo': 'pdfplumber_tabela'
                                })
            
            return {
                'sucesso': True,
                'metadados': metadados,
                'paginas': texto_completo,
                'texto_completo': self._concatenar_paginas(texto_completo)
            }
            
        except Exception as e:
            self.logger.error(f"Erro no pdfplumber: {str(e)}")
            return {'sucesso': False, 'erro': str(e)}

    def extrair_texto_ocr(self, caminho_pdf: str) -> Dict[str, any]:
        """Extrai texto usando OCR (para PDFs escaneados)"""
        try:
            texto_completo = []
            
            with fitz.open(caminho_pdf) as doc:
                metadados = {'total_paginas': len(doc)}
                
                for num_pagina, pagina in enumerate(doc, 1):
                    # Converter página para imagem
                    mat = fitz.Matrix(2.0, 2.0)  # Aumentar resolução
                    pix = pagina.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    
                    # Converter para PIL Image
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    # Preprocessing da imagem
                    img_processada = self._preprocessar_imagem(img)
                    
                    # OCR
                    texto_ocr = pytesseract.image_to_string(
                        img_processada, 
                        config=self.tesseract_config
                    )
                    
                    if texto_ocr.strip():
                        texto_completo.append({
                            'pagina': num_pagina,
                            'texto': self._limpar_texto(texto_ocr),
                            'metodo': 'ocr',
                            'confianca': self._calcular_confianca_ocr(texto_ocr)
                        })
                        
                        self.logger.debug(f"OCR Página {num_pagina}: {len(texto_ocr)} caracteres")
            
            return {
                'sucesso': True,
                'metadados': metadados,
                'paginas': texto_completo,
                'texto_completo': self._concatenar_paginas(texto_completo)
            }
            
        except Exception as e:
            self.logger.error(f"Erro no OCR: {str(e)}")
            return {'sucesso': False, 'erro': str(e)}

    def extrair_texto_hibrido(self, caminho_pdf: str) -> Dict[str, any]:
        """Método híbrido: tenta múltiplas técnicas e escolhe a melhor"""
        
        self.logger.info(f"Iniciando extração híbrida de: {caminho_pdf}")
        
        # Tentar PyMuPDF primeiro (mais rápido)
        resultado_pymupdf = self.extrair_texto_pymupdf(caminho_pdf)
        
        # Verificar qualidade do texto extraído
        if resultado_pymupdf['sucesso']:
            qualidade_pymupdf = self._avaliar_qualidade_texto(resultado_pymupdf['texto_completo'])
            self.logger.info(f"Qualidade PyMuPDF: {qualidade_pymupdf:.2f}")
            
            # Se qualidade for boa, usar PyMuPDF
            if qualidade_pymupdf > 0.7:
                self.logger.info("Usando extração PyMuPDF")
                return resultado_pymupdf
        
        # Se PyMuPDF não foi bom, tentar pdfplumber
        resultado_pdfplumber = self.extrair_texto_pdfplumber(caminho_pdf)
        
        if resultado_pdfplumber['sucesso']:
            qualidade_pdfplumber = self._avaliar_qualidade_texto(resultado_pdfplumber['texto_completo'])
            self.logger.info(f"Qualidade pdfplumber: {qualidade_pdfplumber:.2f}")
            
            if qualidade_pdfplumber > 0.6:
                self.logger.info("Usando extração pdfplumber")
                return resultado_pdfplumber
        
        # Se ambos falharam, usar OCR
        self.logger.warning("Qualidade baixa, tentando OCR...")
        resultado_ocr = self.extrair_texto_ocr(caminho_pdf)
        
        if resultado_ocr['sucesso']:
            self.logger.info("Usando extração OCR")
            return resultado_ocr
        
        # Se tudo falhou
        return {
            'sucesso': False,
            'erro': 'Falha em todos os métodos de extração',
            'detalhes': {
                'pymupdf': resultado_pymupdf.get('erro'),
                'pdfplumber': resultado_pdfplumber.get('erro'),
                'ocr': resultado_ocr.get('erro')
            }
        }

    def _preprocessar_imagem(self, img: Image.Image) -> Image.Image:
        """Melhora imagem para OCR"""
        # Converter para numpy array
        img_np = np.array(img)
        
        # Converter para escala de cinza se colorida
        if len(img_np.shape) == 3:
            img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            img_gray = img_np
        
        # Aplicar blur para reduzir ruído
        img_blur = cv2.GaussianBlur(img_gray, self.preprocessamento_configs['blur_kernel'], 0)
        
        # Binarização adaptativa
        img_thresh = cv2.adaptiveThreshold(
            img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Erosão leve para melhorar caracteres
        kernel = np.ones(self.preprocessamento_configs['erosion_kernel'], np.uint8)
        img_processed = cv2.morphologyEx(img_thresh, cv2.MORPH_CLOSE, kernel)
        
        return Image.fromarray(img_processed)

    def _limpar_texto(self, texto: str) -> str:
        """Limpa e normaliza texto jurídico"""
        if not texto:
            return ""
        
        # Aplicar padrões de limpeza
        texto_limpo = texto
        for padrao in self.padroes_limpeza:
            texto_limpo = re.sub(padrao, ' ', texto_limpo, flags=re.MULTILINE | re.IGNORECASE)
        
        # Normalizar espaços
        texto_limpo = re.sub(r'\s+', ' ', texto_limpo)
        
        # Remover linhas muito curtas (provavelmente ruído)
        linhas = texto_limpo.split('\n')
        linhas_filtradas = [linha.strip() for linha in linhas if len(linha.strip()) > 10]
        
        return '\n'.join(linhas_filtradas).strip()

    def _processar_tabela(self, tabela: List[List[str]]) -> str:
        """Converte tabela em texto estruturado"""
        if not tabela:
            return ""
        
        texto_tabela = "\n[TABELA]\n"
        for linha in tabela:
            if linha and any(cell for cell in linha if cell):
                linha_limpa = [cell.strip() if cell else "" for cell in linha]
                texto_tabela += " | ".join(linha_limpa) + "\n"
        texto_tabela += "[/TABELA]\n"
        
        return texto_tabela

    def _concatenar_paginas(self, paginas: List[Dict]) -> str:
        """Concatena texto de todas as páginas"""
        return "\n\n".join([
            f"[PÁGINA {p['pagina']}]\n{p['texto']}" 
            for p in paginas if p.get('texto', '').strip()
        ])

    def _avaliar_qualidade_texto(self, texto: str) -> float:
        """Avalia qualidade do texto extraído (0.0 a 1.0)"""
        if not texto or len(texto) < 50:
            return 0.0
        
        # Métricas de qualidade
        total_chars = len(texto)
        chars_alfabeticos = len(re.findall(r'[a-záéíóúàèìòùâêîôûãõç]', texto, re.IGNORECASE))
        chars_numericos = len(re.findall(r'\d', texto))
        chars_especiais = len(re.findall(r'[^\w\s]', texto))
        
        # Proporções
        prop_alfabeticos = chars_alfabeticos / total_chars if total_chars > 0 else 0
        prop_numericos = chars_numericos / total_chars if total_chars > 0 else 0
        prop_especiais = chars_especiais / total_chars if total_chars > 0 else 0
        
        # Palavras jurídicas comuns
        palavras_juridicas = [
            'processo', 'sentença', 'autor', 'réu', 'juiz', 'tribunal',
            'direito', 'lei', 'artigo', 'código', 'decisão', 'recurso'
        ]
        
        palavras_encontradas = sum(1 for palavra in palavras_juridicas 
                                 if re.search(r'\b' + palavra + r'\b', texto, re.IGNORECASE))
        
        prop_juridicas = palavras_encontradas / len(palavras_juridicas)
        
        # Calcular score final
        score = (
            prop_alfabeticos * 0.4 +  # 40% texto alfabético
            prop_juridicas * 0.3 +    # 30% palavras jurídicas
            min(prop_numericos * 2, 0.2) * 0.2 +  # 20% números (limitado)
            (1 - min(prop_especiais * 3, 1)) * 0.1  # 10% poucos chars especiais
        )
        
        return min(score, 1.0)

    def _calcular_confianca_ocr(self, texto: str) -> float:
        """Calcula confiança do OCR baseado em características do texto"""
        if not texto:
            return 0.0
        
        # Caracteres estranhos comuns em OCR ruim
        chars_problematicos = len(re.findall(r'[|°º@#$%&*+<>{}[\]\\]', texto))
        total_chars = len(texto)
        
        if total_chars == 0:
            return 0.0
        
        prop_problematicos = chars_problematicos / total_chars
        
        # Palavras com letras repetidas (comum em OCR ruim)
        palavras_repetidas = len(re.findall(r'\b\w*([a-z])\1{2,}\w*\b', texto, re.IGNORECASE))
        total_palavras = len(texto.split())
        
        prop_repetidas = palavras_repetidas / total_palavras if total_palavras > 0 else 0
        
        # Score de confiança
        confianca = 1.0 - (prop_problematicos * 0.6) - (prop_repetidas * 0.4)
        
        return max(0.0, min(1.0, confianca))

    def extrair_metadados_arquivo(self, caminho_pdf: str) -> Dict[str, any]:
        """Extrai metadados do arquivo PDF"""
        try:
            arquivo = Path(caminho_pdf)
            
            with fitz.open(caminho_pdf) as doc:
                metadados = {
                    'nome_arquivo': arquivo.name,
                    'tamanho_arquivo': arquivo.stat().st_size,
                    'data_modificacao': arquivo.stat().st_mtime,
                    'total_paginas': len(doc),
                    'titulo': doc.metadata.get('title', ''),
                    'autor': doc.metadata.get('author', ''),
                    'assunto': doc.metadata.get('subject', ''),
                    'criador': doc.metadata.get('creator', ''),
                    'produtor': doc.metadata.get('producer', ''),
                    'data_criacao': doc.metadata.get('creationDate', ''),
                    'data_modificacao_pdf': doc.metadata.get('modDate', ''),
                    'criptografado': doc.needs_pass,
                    'pode_extrair_texto': True
                }
                
                # Tentar extrair uma amostra para verificar se é texto ou imagem
                primeira_pagina = doc[0]
                texto_amostra = primeira_pagina.get_text()
                
                metadados['tipo_conteudo'] = 'texto' if len(texto_amostra) > 100 else 'imagem'
                metadados['densidade_texto'] = len(texto_amostra) / 1000  # chars por 1000
                
            return metadados
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair metadados: {str(e)}")
            return {'erro': str(e)}

    def detectar_estrutura_documento(self, texto: str) -> Dict[str, any]:
        """Detecta estrutura comum em documentos jurídicos"""
        
        estrutura = {
            'tem_cabecalho': False,
            'tem_numero_processo': False,
            'tem_partes': False,
            'tem_relatorio': False,
            'tem_fundamentacao': False,
            'tem_dispositivo': False,
            'tem_assinatura': False,
            'secoes_identificadas': []
        }
        
        texto_lower = texto.lower()
        
        # Detectar seções típicas
        secoes = [
            ('cabecalho', r'(?i)(?:poder judiciário|tribunal|vara|juízo)'),
            ('numero_processo', r'(?i)(?:processo|autos)\s*n[°º]?\s*\d{7}'),
            ('partes', r'(?i)(?:autor|réu|requerente|requerido)'),
            ('relatorio', r'(?i)(?:relatório|relatou|i\s*-\s*relatório)'),
            ('fundamentacao', r'(?i)(?:fundamentação|fundamento|ii\s*-\s*fundamentação)'),
            ('dispositivo', r'(?i)(?:dispositivo|decido|julgo|iii\s*-\s*dispositivo)'),
            ('assinatura', r'(?i)(?:juiz|desembargador|ministro).*?(?:assinatura|eletrônica)')
        ]
        
        for nome, padrao in secoes:
            if re.search(padrao, texto):
                estrutura[f'tem_{nome}'] = True
                estrutura['secoes_identificadas'].append(nome)
        
        # Calcular completude estrutural
        secoes_obrigatorias = ['numero_processo', 'partes', 'dispositivo']
        secoes_presentes = sum(1 for secao in secoes_obrigatorias if estrutura[f'tem_{secao}'])
        estrutura['completude'] = secoes_presentes / len(secoes_obrigatorias)
        
        return estrutura

    def processar_documento_completo(self, caminho_pdf: str) -> Dict[str, any]:
        """Processa documento completo com todas as informações"""
        
        self.logger.info(f"Processando documento: {caminho_pdf}")
        
        # Verificar se arquivo existe
        if not Path(caminho_pdf).exists():
            return {
                'sucesso': False,
                'erro': f'Arquivo não encontrado: {caminho_pdf}'
            }
        
        try:
            # Extrair metadados
            metadados = self.extrair_metadados_arquivo(caminho_pdf)
            
            # Extrair texto usando método híbrido
            resultado_extracao = self.extrair_texto_hibrido(caminho_pdf)
            
            if not resultado_extracao['sucesso']:
                return resultado_extracao
            
            texto_completo = resultado_extracao['texto_completo']
            
            # Detectar estrutura
            estrutura = self.detectar_estrutura_documento(texto_completo)
            
            # Estatísticas básicas
            estatisticas = {
                'total_caracteres': len(texto_completo),
                'total_palavras': len(texto_completo.split()),
                'total_paragrafos': len([p for p in texto_completo.split('\n\n') if p.strip()]),
                'qualidade_extracao': self._avaliar_qualidade_texto(texto_completo)
            }
            
            return {
                'sucesso': True,
                'metadados_arquivo': metadados,
                'metadados_extracao': resultado_extracao.get('metadados', {}),
                'texto_completo': texto_completo,
                'paginas': resultado_extracao['paginas'],
                'estrutura_documento': estrutura,
                'estatisticas': estatisticas,
                'timestamp_processamento': str(Path(caminho_pdf).stat().st_mtime)
            }
            
        except Exception as e:
            self.logger.error(f"Erro geral no processamento: {str(e)}")
            return {
                'sucesso': False,
                'erro': f'Erro geral: {str(e)}'
            }

# Função utilitária para uso direto
def extrair_texto_pdf(caminho_pdf: str, metodo: str = 'hibrido') -> Dict[str, any]:
    """Função simplificada para extração de texto"""
    
    extrator = ExtratorTextoJuridico()
    
    if metodo == 'hibrido':
        return extrator.processar_documento_completo(caminho_pdf)
    elif metodo == 'pymupdf':
        return extrator.extrair_texto_pymupdf(caminho_pdf)
    elif metodo == 'pdfplumber':
        return extrator.extrair_texto_pdfplumber(caminho_pdf)
    elif metodo == 'ocr':
        return extrator.extrair_texto_ocr(caminho_pdf)
    else:
        return {
            'sucesso': False,
            'erro': f'Método não reconhecido: {metodo}'
        }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python extrair_texto_juridico.py <caminho_pdf> [metodo]")
        sys.exit(1)
    
    caminho_pdf = sys.argv[1]
    metodo = sys.argv[2] if len(sys.argv) > 2 else 'hibrido'
    
    resultado = extrair_texto_pdf(caminho_pdf, metodo)
    
    if resultado['sucesso']:
        print(f"✅ Texto extraído com sucesso!")
        print(f"📄 Total de caracteres: {len(resultado.get('texto_completo', ''))}")
        print(f"📋 Estrutura detectada: {resultado.get('estrutura_documento', {}).get('completude', 0):.1%}")
    else:
        print(f"❌ Erro: {resultado['erro']}")
        sys.exit(1)
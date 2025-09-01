#!/usr/bin/env python3
"""
Sistema de Análise Jurídica Inteligente
Analisa documentos jurídicos e extrai informações estruturadas
"""

import re
import yaml
import spacy
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from sentence_transformers import SentenceTransformer
import numpy as np

@dataclass
class PartesProcesso:
    autores: List[str]
    reus: List[str]
    terceiros: List[str]
    advogados: List[str]
    
@dataclass
class InformacoesProcessuais:
    numero_processo: str
    tipo_acao: List[str]
    orgao_julgador: str
    instancia: str
    data_distribuicao: Optional[str]
    valor_causa: Optional[str]

@dataclass
class DecisaoJudicial:
    tipo_decisao: str
    resultado: str
    dispositivo: str
    fundamentacao_resumida: str
    data_decisao: Optional[str]

@dataclass
class AnaliseProcesso:
    informacoes_processuais: InformacoesProcessuais
    partes: PartesProcesso
    decisao: Optional[DecisaoJudicial]
    resumo_executivo: str
    palavras_chave: List[str]
    confianca_analise: float

class AnalisadorJuridico:
    def __init__(self):
        """Inicializa o analisador com modelos e padrões"""
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Carregar modelos
        self._carregar_modelos()
        
        # Carregar padrões jurídicos
        self._carregar_padroes()
        
        # Inicializar embeddings para análise semântica
        try:
            self.modelo_embeddings = SentenceTransformer('neuralmind/bert-base-portuguese-cased')
            self.logger.info("Modelo de embeddings carregado com sucesso")
        except Exception as e:
            self.logger.warning(f"Erro ao carregar embeddings: {e}")
            self.modelo_embeddings = None

    def _carregar_modelos(self):
        """Carrega modelo spaCy português"""
        try:
            self.nlp = spacy.load("pt_core_news_sm")
            self.logger.info("Modelo spaCy carregado com sucesso")
        except OSError:
            self.logger.error("Modelo spaCy não encontrado. Execute: python -m spacy download pt_core_news_sm")
            raise

    def _carregar_padroes(self):
        """Carrega padrões de regex dos arquivos YAML"""
        try:
            # Assumindo que estamos no diretório scripts
            caminho_patterns = Path(__file__).parent / "patterns_juridicos.yaml"
            caminho_tipos = Path(__file__).parent / "tipos_processuais.yaml"
            
            with open(caminho_patterns, 'r', encoding='utf-8') as f:
                self.padroes = yaml.safe_load(f)
            
            with open(caminho_tipos, 'r', encoding='utf-8') as f:
                self.tipos_processuais = yaml.safe_load(f)
                
            self.logger.info("Padrões jurídicos carregados com sucesso")
            
        except FileNotFoundError as e:
            self.logger.error(f"Arquivo de padrões não encontrado: {e}")
            # Padrões básicos como fallback
            self.padroes = self._padroes_basicos()
            self.tipos_processuais = self._tipos_basicos()

    def _padroes_basicos(self) -> Dict:
        """Padrões básicos caso arquivos YAML não existam"""
        return {
            'NUMERO_PROCESSO': [r'(\d{7}[-.]?\d{2}[-.]?\d{4}[-.]?\d{1}[-.]?\d{2}[-.]?\d{4})'],
            'TIPO_ACAO': [r'(?i)(ação\s+(?:civil|penal|trabalhista))'],
            'PARTES_PROCESSO': [r'(?i)(?:autor|réu):\s*([A-ZÁÊÇ][A-Za-záêçõ\s]{5,50})']
        }

    def _tipos_basicos(self) -> Dict:
        """Tipos processuais básicos"""
        return {
            'CIVEL': {'keywords': ['civil', 'indenização', 'danos', 'contrato']},
            'PENAL': {'keywords': ['penal', 'crime', 'denúncia']},
            'TRABALHISTA': {'keywords': ['trabalhista', 'clt', 'empregado']}
        }

    def extrair_numero_processo(self, texto: str) -> Optional[str]:
        """Extrai número do processo do texto"""
        for padrao in self.padroes.get('NUMERO_PROCESSO', []):
            match = re.search(padrao, texto)
            if match:
                numero = match.group(1) if match.groups() else match.group(0)
                # Normalizar formato
                numero_limpo = re.sub(r'[^\d]', '', numero)
                if len(numero_limpo) == 20:  # Formato CNJ
                    return f"{numero_limpo[:7]}-{numero_limpo[7:9]}.{numero_limpo[9:13]}.{numero_limpo[13]}.{numero_limpo[14:16]}.{numero_limpo[16:]}"
                return numero
        return None

    def identificar_tipo_acao(self, texto: str) -> List[str]:
        """Identifica tipos de ação no documento"""
        tipos_encontrados = []
        texto_lower = texto.lower()
        
        # Buscar por padrões específicos
        for padrao in self.padroes.get('TIPO_ACAO', []):
            matches = re.findall(padrao, texto, re.IGNORECASE)
            tipos_encontrados.extend(matches)
        
        # Classificação semântica por área
        for area, config in self.tipos_processuais.items():
            if area in ['CIVEL', 'PENAL', 'TRABALHISTA', 'ADMINISTRATIVO']:
                keywords = config.get('keywords', [])
                score = sum(1 for keyword in keywords if keyword in texto_lower)
                
                if score >= 2:  # Mínimo 2 palavras-chave
                    tipos_encontrados.append(f"Processo {area.lower()}")
        
        return list(set(tipos_encontrados)) if tipos_encontrados else ["Tipo não identificado"]

    def extrair_partes_processo(self, texto: str) -> PartesProcesso:
        """Extrai partes do processo"""
        
        doc = self.nlp(texto[:50000])  # Limitar para performance
        
        # Listas para armazenar partes
        autores = []
        reus = []
        terceiros = []
        advogados = []
        
        # Padrões para partes
        padroes_partes = self.padroes.get('PARTES_PROCESSO', [])
        
        for padrao in padroes_partes:
            matches = re.finditer(padrao, texto, re.IGNORECASE)
            for match in matches:
                if match.groups():
                    parte = match.group(1).strip()
                    
                    # Classificar tipo da parte baseado no contexto
                    contexto = match.group(0).lower()
                    
                    if any(term in contexto for term in ['autor', 'requerente', 'impetrante']):
                        if parte not in autores:
                            autores.append(parte)
                    elif any(term in contexto for term in ['réu', 'requerido', 'impetrado']):
                        if parte not in reus:
                            reus.append(parte)
                    elif any(term in contexto for term in ['terceiro', 'assistente']):
                        if parte not in terceiros:
                            terceiros.append(parte)
        
        # Extrair advogados
        padroes_advogados = self.padroes.get('ADVOGADOS_PROCURADORES', [])
        for padrao in padroes_advogados:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    advogado = match[0] if match[0] else match[1] if len(match) > 1 else ""
                else:
                    advogado = match
                
                if advogado and len(advogado) > 5:
                    advogados.append(advogado.strip())
        
        # Usar NER do spaCy para pessoas não capturadas por regex
        for ent in doc.ents:
            if ent.label_ == "PER" and len(ent.text) > 5:
                nome = ent.text.strip()
                # Adicionar se não está em nenhuma lista ainda
                if (nome not in autores and nome not in reus and 
                    nome not in terceiros and nome not in advogados):
                    # Tentar classificar pelo contexto
                    contexto_antes = doc[max(0, ent.start-10):ent.start].text.lower()
                    contexto_depois = doc[ent.end:min(len(doc), ent.end+10)].text.lower()
                    contexto_completo = contexto_antes + " " + contexto_depois
                    
                    if any(term in contexto_completo for term in ['autor', 'requerente']):
                        autores.append(nome)
                    elif any(term in contexto_completo for term in ['réu', 'requerido']):
                        reus.append(nome)
        
        return PartesProcesso(
            autores=autores[:5],  # Limitar quantidade
            reus=reus[:5],
            terceiros=terceiros[:3],
            advogados=list(set(advogados))[:10]
        )

    def extrair_informacoes_processuais(self, texto: str) -> InformacoesProcessuais:
        """Extrai informações básicas do processo"""
        
        # Número do processo
        numero_processo = self.extrair_numero_processo(texto) or "Não identificado"
        
        # Tipo de ação
        tipo_acao = self.identificar_tipo_acao(texto)
        
        # Órgão julgador
        orgao_julgador = self._extrair_orgao_julgador(texto)
        
        # Instância
        instancia = self._identificar_instancia(texto)
        
        # Data de distribuição
        data_distribuicao = self._extrair_data_distribuicao(texto)
        
        # Valor da causa
        valor_causa = self._extrair_valor_causa(texto)
        
        return InformacoesProcessuais(
            numero_processo=numero_processo,
            tipo_acao=tipo_acao,
            orgao_julgador=orgao_julgador,
            instancia=instancia,
            data_distribuicao=data_distribuicao,
            valor_causa=valor_causa
        )

    def _extrair_orgao_julgador(self, texto: str) -> str:
        """Extrai órgão julgador"""
        padroes_orgao = [
            r'(?i)(tribunal\s+(?:de\s+justiça|regional|superior)[^.\n]{0,50})',
            r'(?i)(\d+ª\s+vara\s+[^.\n]{0,50})',
            r'(?i)(juízo\s+[^.\n]{0,30})',
            r'(?i)(supremo\s+tribunal\s+federal)',
            r'(?i)(superior\s+tribunal\s+de\s+justiça)'
        ]
        
        for padrao in padroes_orgao:
            match = re.search(padrao, texto)
            if match:
                return match.group(1).strip()
        
        return "Órgão não identificado"

    def _identificar_instancia(self, texto: str) -> str:
        """Identifica instância do processo"""
        texto_lower = texto.lower()
        
        if any(term in texto_lower for term in ['supremo tribunal federal', 'stf']):
            return "Supremo Tribunal Federal"
        elif any(term in texto_lower for term in ['superior tribunal de justiça', 'stj']):
            return "Superior Tribunal de Justiça"
        elif any(term in texto_lower for term in ['tribunal', 'desembargador', 'apelação']):
            return "Segunda instância"
        elif any(term in texto_lower for term in ['vara', 'juiz de direito', 'juíza de direito']):
            return "Primeira instância"
        else:
            return "Instância não identificada"

    def _extrair_data_distribuicao(self, texto: str) -> Optional[str]:
        """Extrai data de distribuição"""
        padroes_data = [
            r'(?i)distribu[íi]do?\s+em\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'(?i)data\s+da?\s+distribui[çc][ãa]o\s*:?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})'
        ]
        
        for padrao in padroes_data:
            match = re.search(padrao, texto)
            if match:
                return match.group(1)
        
        return None

    def _extrair_valor_causa(self, texto: str) -> Optional[str]:
        """Extrai valor da causa"""
        padroes_valor = self.padroes.get('VALORES_MONETARIOS', [])
        
        for padrao in padroes_valor:
            match = re.search(padrao, texto)
            if match:
                if match.groups():
                    return f"R$ {match.group(1)}"
                else:
                    return match.group(0)
        
        return None

    def analisar_decisao(self, texto: str) -> Optional[DecisaoJudicial]:
        """Analisa decisão judicial no documento"""
        
        # Buscar seções de decisão/dispositivo
        padroes_dispositivo = [
            r'(?i)(?:dispositivo|decido|julgo|determino)[:\s]([^.]+\.)',
            r'(?i)(?:pelo\s+exposto|ante\s+o\s+exposto|isso\s+posto)[^.]*\.([^.]+\.)',
        ]
        
        dispositivo = ""
        for padrao in padroes_dispositivo:
            match = re.search(padrao, texto, re.DOTALL)
            if match:
                dispositivo = match.group(1) if match.groups() else match.group(0)
                break
        
        if not dispositivo:
            return None
        
        # Determinar tipo e resultado da decisão
        tipo_decisao = self._classificar_tipo_decisao(texto)
        resultado = self._determinar_resultado_decisao(dispositivo)
        
        # Extrair fundamentação resumida
        fundamentacao = self._extrair_fundamentacao_resumida(texto)
        
        # Data da decisão
        data_decisao = self._extrair_data_decisao(texto)
        
        return DecisaoJudicial(
            tipo_decisao=tipo_decisao,
            resultado=resultado,
            dispositivo=dispositivo.strip(),
            fundamentacao_resumida=fundamentacao,
            data_decisao=data_decisao
        )

    def _classificar_tipo_decisao(self, texto: str) -> str:
        """Classifica tipo da decisão"""
        texto_lower = texto.lower()
        
        if 'sentença' in texto_lower:
            return "Sentença"
        elif 'acórdão' in texto_lower:
            return "Acórdão"
        elif any(term in texto_lower for term in ['decisão interlocutória', 'defiro', 'indefiro']):
            return "Decisão interlocutória"
        elif 'despacho' in texto_lower:
            return "Despacho"
        else:
            return "Decisão não classificada"

    def _determinar_resultado_decisao(self, dispositivo: str) -> str:
        """Determina resultado da decisão"""
        dispositivo_lower = dispositivo.lower()
        
        if 'procedente' in dispositivo_lower and 'improcedente' not in dispositivo_lower:
            return "Procedente"
        elif 'improcedente' in dispositivo_lower:
            return "Improcedente"
        elif 'parcialmente procedente' in dispositivo_lower:
            return "Parcialmente procedente"
        elif any(term in dispositivo_lower for term in ['defiro', 'concedo']):
            return "Deferido"
        elif any(term in dispositivo_lower for term in ['indefiro', 'denego']):
            return "Indeferido"
        elif 'extinto' in dispositivo_lower:
            return "Processo extinto"
        else:
            return "Resultado não determinado"

    def _extrair_fundamentacao_resumida(self, texto: str) -> str:
        """Extrai resumo da fundamentação"""
        
        # Buscar seção de fundamentação
        padroes_fundamentacao = [
            r'(?i)fundamenta[çc][ãa]o[:\s]([^.]{100,500})',
            r'(?i)(?:considerando|tendo\s+em\s+vista)[^.]*\.([^.]{100,300})',
        ]
        
        for padrao in padroes_fundamentacao:
            match = re.search(padrao, texto, re.DOTALL)
            if match:
                fundamentacao = match.group(1) if match.groups() else match.group(0)
                # Limitar e limpar
                return fundamentacao.strip()[:300] + "..." if len(fundamentacao) > 300 else fundamentacao.strip()
        
        # Se não encontrou fundamentação específica, usar análise semântica
        return self._extrair_fundamentacao_semantica(texto)

    def _extrair_data_decisao(self, texto: str) -> Optional[str]:
        """Extrai data da decisão"""
        padroes_data_decisao = [
            r'(?i)(?:julgado|decidido|sentenciado)\s+em\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'(?i)data\s+da?\s+(?:sentença|decisão|julgamento)\s*:?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'(?i)(?:em|aos?)\s+(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})'
        ]
        
        for padrao in padroes_data_decisao:
            matches = re.findall(padrao, texto)
            if matches:
                # Retornar a última data encontrada (geralmente é a da decisão)
                return matches[-1]
        
        return None

    def _extrair_fundamentacao_semantica(self, texto: str) -> str:
        """Extrai fundamentação usando análise semântica"""
        if not self.modelo_embeddings:
            return "Fundamentação não disponível (modelo não carregado)"
        
        try:
            # Dividir texto em parágrafos
            paragrafos = [p.strip() for p in texto.split('\n') if len(p.strip()) > 50]
            
            if len(paragrafos) < 3:
                return "Texto insuficiente para análise semântica"
            
            # Embeddings de referência para fundamentação jurídica
            termos_fundamentacao = [
                "fundamentação legal constitucional jurisprudencial",
                "considerações legais doutrina precedentes",
                "análise jurídica direito aplicável caso"
            ]
            
            # Calcular embeddings
            embeddings_ref = self.modelo_embeddings.encode(termos_fundamentacao)
            embeddings_paragrafos = self.modelo_embeddings.encode(paragrafos)
            
            # Calcular similaridades
            similaridades = []
            for emb_par in embeddings_paragrafos:
                sim_max = max(np.dot(emb_par, emb_ref.T) for emb_ref in embeddings_ref)
                similaridades.append(sim_max)
            
            # Pegar os 2 parágrafos mais similares à fundamentação
            indices_top = np.argsort(similaridades)[-2:]
            fundamentacao = " ".join([paragrafos[i] for i in indices_top])
            
            return fundamentacao[:300] + "..." if len(fundamentacao) > 300 else fundamentacao
            
        except Exception as e:
            self.logger.error(f"Erro na análise semântica: {e}")
            return "Erro na extração semântica da fundamentação"

    def extrair_custas_honorarios(self, texto: str) -> Dict[str, Optional[str]]:
        """Extrai informações sobre custas e honorários"""
        resultado = {
            'custas_processuais': None,
            'honorarios_advocaticios': None,
            'sucumbencia': None,
            'gratuidade_justica': False
        }
        
        # Custas processuais
        padroes_custas = self.padroes.get('CUSTAS_SUCUMBENCIA', [])
        for padrao in padroes_custas:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                if 'custas' in padrao.lower():
                    resultado['custas_processuais'] = match.group(1) if match.groups() else match.group(0)
                elif 'honorários' in padrao.lower():
                    resultado['honorarios_advocaticios'] = match.group(1) if match.groups() else match.group(0)
                elif 'sucumbência' in padrao.lower():
                    resultado['sucumbencia'] = match.group(1) if match.groups() else match.group(0)
                elif 'gratuidade' in padrao.lower():
                    resultado['gratuidade_justica'] = True
        
        return resultado

    def extrair_prazos_recursos(self, texto: str) -> Dict[str, Any]:
        """Extrai informações sobre prazos e recursos"""
        prazos_info = {
            'prazos_identificados': [],
            'recursos_cabiveis': [],
            'prazo_recurso': None
        }
        
        # Extrair prazos gerais
        padroes_prazos = self.padroes.get('PRAZOS_JURIDICOS', [])
        for padrao in padroes_prazos:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            prazos_info['prazos_identificados'].extend(matches)
        
        # Recursos possíveis
        padroes_recursos = self.padroes.get('RECURSOS_POSSIVEIS', [])
        for padrao in padroes_recursos:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            if matches:
                if 'prazo' in padrao.lower() and 'recurso' in padrao.lower():
                    prazos_info['prazo_recurso'] = matches[0] if isinstance(matches[0], str) else matches[0][0]
                else:
                    prazos_info['recursos_cabiveis'].extend(matches)
        
        return prazos_info

    def gerar_resumo_executivo(self, informacoes: InformacoesProcessuais, partes: PartesProcesso, 
                              decisao: Optional[DecisaoJudicial], texto_completo: str) -> str:
        """Gera resumo executivo do processo"""
        
        # Template do resumo
        resumo_parts = []
        
        # Informações básicas
        resumo_parts.append(f"PROCESSO: {informacoes.numero_processo}")
        resumo_parts.append(f"TIPO: {', '.join(informacoes.tipo_acao)}")
        resumo_parts.append(f"ÓRGÃO: {informacoes.orgao_julgador}")
        resumo_parts.append(f"INSTÂNCIA: {informacoes.instancia}")
        
        # Partes
        if partes.autores:
            resumo_parts.append(f"AUTOR(ES): {', '.join(partes.autores[:2])}")
        if partes.reus:
            resumo_parts.append(f"RÉU(S): {', '.join(partes.reus[:2])}")
        
        # Valor da causa
        if informacoes.valor_causa:
            resumo_parts.append(f"VALOR: {informacoes.valor_causa}")
        
        # Decisão
        if decisao:
            resumo_parts.append(f"DECISÃO: {decisao.tipo_decisao} - {decisao.resultado}")
            if decisao.data_decisao:
                resumo_parts.append(f"DATA DECISÃO: {decisao.data_decisao}")
        
        # Custas e honorários
        custas_info = self.extrair_custas_honorarios(texto_completo)
        if custas_info['honorarios_advocaticios']:
            resumo_parts.append(f"HONORÁRIOS: {custas_info['honorarios_advocaticios']}")
        
        # Juntar tudo
        resumo = " | ".join(resumo_parts)
        
        # Adicionar observações importantes
        observacoes = []
        if custas_info['gratuidade_justica']:
            observacoes.append("Beneficiário da gratuidade da justiça")
        
        if decisao and 'procedente' in decisao.resultado.lower():
            observacoes.append("Decisão favorável ao autor")
        elif decisao and 'improcedente' in decisao.resultado.lower():
            observacoes.append("Decisão favorável ao réu")
        
        if observacoes:
            resumo += f" | OBSERVAÇÕES: {'; '.join(observacoes)}"
        
        return resumo

    def extrair_palavras_chave(self, texto: str) -> List[str]:
        """Extrai palavras-chave relevantes do documento"""
        
        doc = self.nlp(texto[:10000])  # Processar amostra para performance
        
        # Palavras-chave extraídas
        palavras_chave = set()
        
        # 1. Entidades nomeadas relevantes
        for ent in doc.ents:
            if ent.label_ in ['PER', 'ORG', 'LOC'] and len(ent.text) > 3:
                palavras_chave.add(ent.text.lower())
        
        # 2. Substantivos importantes (frequência > 2)
        substantivos = [token.lemma_.lower() for token in doc 
                       if token.pos_ == 'NOUN' and len(token.lemma_) > 4 and token.is_alpha]
        
        from collections import Counter
        substantivos_freq = Counter(substantivos)
        palavras_importantes = [palavra for palavra, freq in substantivos_freq.items() if freq >= 2]
        palavras_chave.update(palavras_importantes[:10])
        
        # 3. Termos jurídicos específicos
        termos_juridicos = [
            'direito', 'lei', 'artigo', 'código', 'norma', 'jurisprudência',
            'precedente', 'súmula', 'constituição', 'processual', 'civil',
            'penal', 'trabalhista', 'administrativo', 'tributário'
        ]
        
        for termo in termos_juridicos:
            if termo in texto.lower():
                palavras_chave.add(termo)
        
        # 4. Áreas do direito identificadas
        for area, config in self.tipos_processuais.items():
            if isinstance(config, dict) and 'keywords' in config:
                area_score = sum(1 for keyword in config['keywords'] if keyword in texto.lower())
                if area_score >= 1:
                    palavras_chave.add(area.lower())
        
        return sorted(list(palavras_chave))[:15]  # Máximo 15 palavras-chave

    def calcular_confianca_analise(self, informacoes: InformacoesProcessuais, 
                                  partes: PartesProcesso, texto_completo: str) -> float:
        """Calcula índice de confiança da análise (0.0 a 1.0)"""
        
        score_components = []
        
        # 1. Número do processo (peso 0.25)
        if informacoes.numero_processo != "Não identificado":
            score_components.append(0.25)
        else:
            score_components.append(0.0)
        
        # 2. Partes identificadas (peso 0.20)
        total_partes = len(partes.autores) + len(partes.reus)
        if total_partes >= 2:
            score_components.append(0.20)
        elif total_partes >= 1:
            score_components.append(0.10)
        else:
            score_components.append(0.0)
        
        # 3. Tipo de ação identificado (peso 0.15)
        if informacoes.tipo_acao and informacoes.tipo_acao[0] != "Tipo não identificado":
            score_components.append(0.15)
        else:
            score_components.append(0.0)
        
        # 4. Órgão julgador (peso 0.10)
        if informacoes.orgao_julgador != "Órgão não identificado":
            score_components.append(0.10)
        else:
            score_components.append(0.0)
        
        # 5. Qualidade do texto (peso 0.15)
        palavras_juridicas = ['processo', 'sentença', 'decisão', 'autor', 'réu', 'direito', 'lei']
        palavras_encontradas = sum(1 for palavra in palavras_juridicas 
                                 if re.search(r'\b' + palavra + r'\b', texto_completo, re.IGNORECASE))
        score_texto = min(palavras_encontradas / len(palavras_juridicas), 1.0) * 0.15
        score_components.append(score_texto)
        
        # 6. Presença de decisão (peso 0.15)
        if any(term in texto_completo.lower() for term in ['julgo', 'decido', 'sentença', 'dispositivo']):
            score_components.append(0.15)
        else:
            score_components.append(0.0)
        
        # Calcular score final
        confianca = sum(score_components)
        return min(confianca, 1.0)

    def analisar_processo_completo(self, texto_documento: str) -> AnaliseProcesso:
        """Análise completa do processo jurídico"""
        
        self.logger.info("Iniciando análise completa do processo")
        
        # Extrair informações principais
        informacoes = self.extrair_informacoes_processuais(texto_documento)
        self.logger.info(f"Número do processo: {informacoes.numero_processo}")
        
        # Extrair partes
        partes = self.extrair_partes_processo(texto_documento)
        self.logger.info(f"Partes extraídas - Autores: {len(partes.autores)}, Réus: {len(partes.reus)}")
        
        # Analisar decisão
        decisao = self.analisar_decisao(texto_documento)
        if decisao:
            self.logger.info(f"Decisão identificada: {decisao.tipo_decisao} - {decisao.resultado}")
        
        # Extrair palavras-chave
        palavras_chave = self.extrair_palavras_chave(texto_documento)
        
        # Gerar resumo executivo
        resumo = self.gerar_resumo_executivo(informacoes, partes, decisao, texto_documento)
        
        # Calcular confiança
        confianca = self.calcular_confianca_analise(informacoes, partes, texto_documento)
        self.logger.info(f"Confiança da análise: {confianca:.2%}")
        
        return AnaliseProcesso(
            informacoes_processuais=informacoes,
            partes=partes,
            decisao=decisao,
            resumo_executivo=resumo,
            palavras_chave=palavras_chave,
            confianca_analise=confianca
        )

    def analisar_semanticamente(self, texto: str) -> Dict[str, Any]:
        """Análise semântica avançada do documento"""
        if not self.modelo_embeddings:
            return {"erro": "Modelo de embeddings não disponível"}
        
        try:
            # Dividir texto em seções
            secoes = self._dividir_em_secoes(texto)
            
            # Classificar cada seção
            classificacoes = {}
            for nome_secao, conteudo_secao in secoes.items():
                if len(conteudo_secao) > 50:
                    classificacao = self._classificar_secao_semanticamente(conteudo_secao)
                    classificacoes[nome_secao] = classificacao
            
            # Extrair tópicos principais
            topicos = self._extrair_topicos_principais(texto)
            
            return {
                "secoes_classificadas": classificacoes,
                "topicos_principais": topicos,
                "complexidade_documento": self._avaliar_complexidade(texto)
            }
            
        except Exception as e:
            self.logger.error(f"Erro na análise semântica: {e}")
            return {"erro": str(e)}

    def _dividir_em_secoes(self, texto: str) -> Dict[str, str]:
        """Divide documento em seções lógicas"""
        secoes = {}
        
        # Padrões para identificar seções
        marcadores_secao = [
            (r'(?i)relat[óo]rio', 'relatorio'),
            (r'(?i)fundamenta[çc][ãa]o', 'fundamentacao'),
            (r'(?i)dispositivo', 'dispositivo'),
            (r'(?i)(?:voto|ementa)', 'voto'),
            (r'(?i)pedidos?', 'pedidos'),
            (r'(?i)defesa', 'defesa')
        ]
        
        texto_restante = texto
        posicoes = []
        
        # Encontrar posições das seções
        for padrao, nome in marcadores_secao:
            match = re.search(padrao, texto_restante, re.IGNORECASE)
            if match:
                posicoes.append((match.start(), nome))
        
        # Ordenar por posição
        posicoes.sort()
        
        # Extrair conteúdo das seções
        for i, (pos, nome) in enumerate(posicoes):
            inicio = pos
            fim = posicoes[i + 1][0] if i + 1 < len(posicoes) else len(texto)
            secoes[nome] = texto[inicio:fim]
        
        # Se não encontrou seções, dividir por parágrafos
        if not secoes:
            paragrafos = texto.split('\n\n')
            for i, paragrafo in enumerate(paragrafos[:5]):
                if len(paragrafo) > 100:
                    secoes[f"secao_{i+1}"] = paragrafo
        
        return secoes

    def _classificar_secao_semanticamente(self, secao: str) -> str:
        """Classifica seção usando análise semântica"""
        if not self.modelo_embeddings:
            return "não classificado"
        
        try:
            # Templates de seções
            templates_secoes = {
                "relatório": "relatório dos fatos histórico inicial petição",
                "fundamentação": "fundamentação jurídica lei doutrina jurisprudência análise",
                "dispositivo": "dispositivo decisão julgo condeno absolvo determino",
                "pedidos": "pedidos requerimentos solicita pleiteia",
                "defesa": "defesa contestação impugnação resposta"
            }
            
            # Calcular similaridades
            embedding_secao = self.modelo_embeddings.encode([secao])
            embeddings_templates = self.modelo_embeddings.encode(list(templates_secoes.values()))
            
            # Encontrar template mais similar
            similaridades = np.dot(embedding_secao, embeddings_templates.T)[0]
            indice_max = np.argmax(similaridades)
            
            tipos_secao = list(templates_secoes.keys())
            return tipos_secao[indice_max]
            
        except Exception as e:
            self.logger.error(f"Erro na classificação semântica: {e}")
            return "erro_classificacao"

    def _extrair_topicos_principais(self, texto: str) -> List[str]:
        """Extrai tópicos principais do documento"""
        doc = self.nlp(texto[:15000])
        
        # Extrair sintagmas nominais importantes
        topicos = []
        
        # Buscar chunks substantivos importantes
        for chunk in doc.noun_chunks:
            if (len(chunk.text) > 10 and len(chunk.text) < 80 and 
                chunk.root.pos_ == 'NOUN' and
                not chunk.text.lower().startswith(('o ', 'a ', 'os ', 'as '))):
                topicos.append(chunk.text.strip())
        
        # Remover duplicatas e ordenar por relevância
        topicos_unicos = list(set(topicos))
        
        # Filtrar tópicos jurídicos relevantes
        topicos_juridicos = [
            topico for topico in topicos_unicos
            if any(termo in topico.lower() for termo in [
                'direito', 'ação', 'processo', 'responsabilidade', 
                'dano', 'contrato', 'obrigação', 'recurso'
            ])
        ]
        
        return topicos_juridicos[:8]

    def _avaliar_complexidade(self, texto: str) -> str:
        """Avalia complexidade do documento"""
        doc = self.nlp(texto[:10000])
        
        # Métricas de complexidade
        total_sentences = len(list(doc.sents))
        avg_sentence_length = np.mean([len(sent.text.split()) for sent in doc.sents])
        
        # Termos jurídicos complexos
        termos_complexos = [
            'jurisprudência', 'precedente', 'constitucional', 'hermenêutica',
            'interpretação', 'analogia', 'princípio', 'proporcionalidade'
        ]
        
        complexidade_terminologica = sum(1 for termo in termos_complexos 
                                       if termo in texto.lower())
        
        # Classificar complexidade
        if avg_sentence_length > 25 and complexidade_terminologica > 5:
            return "Alta"
        elif avg_sentence_length > 15 and complexidade_terminologica > 2:
            return "Média"
        else:
            return "Baixa"

    def gerar_analise_json(self, analise: AnaliseProcesso, metadados_extracao: Dict = None) -> Dict[str, Any]:
        """Converte análise para formato JSON estruturado"""
        
        resultado = {
            "timestamp_analise": datetime.now().isoformat(),
            "analise_completa": {
                "numero_processo": analise.informacoes_processuais.numero_processo,
                "tipo_acao": analise.informacoes_processuais.tipo_acao,
                "orgao_julgador": analise.informacoes_processuais.orgao_julgador,
                "instancia": analise.informacoes_processuais.instancia,
                "data_distribuicao": analise.informacoes_processuais.data_distribuicao,
                "valor_causa": analise.informacoes_processuais.valor_causa,
                "partes": {
                    "autores": analise.partes.autores,
                    "reus": analise.partes.reus,
                    "terceiros": analise.partes.terceiros,
                    "advogados": analise.partes.advogados
                },
                "decisao": asdict(analise.decisao) if analise.decisao else None,
                "resumo_executivo": analise.resumo_executivo,
                "palavras_chave": analise.palavras_chave,
                "confianca_analise": analise.confianca_analise
            },
            "metadados_processamento": metadados_extracao or {},
            "estatisticas": {
                "total_partes_identificadas": len(analise.partes.autores) + len(analise.partes.reus) + len(analise.partes.terceiros),
                "tem_decisao": analise.decisao is not None,
                "nivel_confianca": "Alto" if analise.confianca_analise > 0.7 else "Médio" if analise.confianca_analise > 0.4 else "Baixo"
            }
        }
        
        return resultado

    def extrair_informacoes_adicionais(self, texto: str) -> Dict[str, Any]:
        """Extrai informações complementares"""
        
        # Custas e honorários
        custas_info = self.extrair_custas_honorarios(texto)
        
        # Prazos e recursos
        prazos_info = self.extrair_prazos_recursos(texto)
        
        # Análise semântica
        analise_semantica = self.analisar_semanticamente(texto)
        
        # Legislação citada
        legislacao = self._extrair_legislacao_citada(texto)
        
        # Jurisprudência mencionada
        jurisprudencia = self._extrair_jurisprudencia(texto)
        
        return {
            "custas_honorarios": custas_info,
            "prazos_recursos": prazos_info,
            "analise_semantica": analise_semantica,
            "legislacao_citada": legislacao,
            "jurisprudencia_citada": jurisprudencia
        }

    def _extrair_legislacao_citada(self, texto: str) -> List[str]:
        """Extrai legislação citada no documento"""
        legislacao_encontrada = []
        
        padroes_legislacao = [
            r'(?i)(?:lei|código|decreto|medida provisória|emenda constitucional)\s+n[°º]?\s*(\d+(?:[./]\d+)*)',
            r'(?i)artigo\s+(\d+(?:[°º.-]?\d+)*)',
            r'(?i)art\.\s*(\d+(?:[°º.-]?\d+)*)',
            r'(?i)constituição\s+federal',
            r'(?i)código\s+(?:civil|penal|de\s+processo\s+civil|de\s+processo\s+penal|tributário)',
            r'(?i)clt\b',
            r'(?i)súmula\s+(?:vinculante\s+)?n[°º]?\s*(\d+)'
        ]
        
        for padrao in padroes_legislacao:
            matches = re.findall(padrao, texto)
            for match in matches:
                if isinstance(match, tuple):
                    ref = match[0] if match[0] else match[1] if len(match) > 1 else ""
                else:
                    ref = match
                
                if ref:
                    legislacao_encontrada.append(ref)
        
        return list(set(legislacao_encontrada))[:10]

    def _extrair_jurisprudencia(self, texto: str) -> List[str]:
        """Extrai jurisprudência citada"""
        jurisprudencia = []
        
        padroes_jurisprudencia = [
            r'(?i)(?:stf|stj|tjsp|tjrj|tjmg|trf)\s*[,-]?\s*([A-Z]{2,4}\s*\d+)',
            r'(?i)(?:resp|are|re|hc|ms)\s+n[°º]?\s*(\d+(?:[./]\d+)*)',
            r'(?i)apelação\s+(?:cível\s+)?n[°º]?\s*(\d+(?:[./]\d+)*)',
            r'(?i)precedente[^.]{0,100}',
            r'(?i)entendimento\s+(?:pacífico|consolidado)[^.]{0,80}'
        ]
        
        for padrao in padroes_jurisprudencia:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            jurisprudencia.extend(matches)
        
        return list(set([str(j) for j in jurisprudencia]))[:8]

    def gerar_relatorio_detalhado(self, analise: AnaliseProcesso, informacoes_adicionais: Dict = None) -> str:
        """Gera relatório detalhado em formato texto"""
        
        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE ANÁLISE JURÍDICA AUTOMATIZADA")
        relatorio.append("=" * 80)
        relatorio.append(f"Data da análise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        relatorio.append(f"Confiança da análise: {analise.confianca_analise:.1%}")
        relatorio.append("")
        
        # Informações processuais
        relatorio.append("1. INFORMAÇÕES PROCESSUAIS")
        relatorio.append("-" * 40)
        relatorio.append(f"Número do processo: {analise.informacoes_processuais.numero_processo}")
        relatorio.append(f"Tipo de ação: {', '.join(analise.informacoes_processuais.tipo_acao)}")
        relatorio.append(f"Órgão julgador: {analise.informacoes_processuais.orgao_julgador}")
        relatorio.append(f"Instância: {analise.informacoes_processuais.instancia}")
        
        if analise.informacoes_processuais.data_distribuicao:
            relatorio.append(f"Data distribuição: {analise.informacoes_processuais.data_distribuicao}")
        
        if analise.informacoes_processuais.valor_causa:
            relatorio.append(f"Valor da causa: {analise.informacoes_processuais.valor_causa}")
        
        relatorio.append("")
        
        # Partes do processo
        relatorio.append("2. PARTES DO PROCESSO")
        relatorio.append("-" * 40)
        
        if analise.partes.autores:
            relatorio.append("AUTORES:")
            for autor in analise.partes.autores:
                relatorio.append(f"  • {autor}")
        
        if analise.partes.reus:
            relatorio.append("RÉUS:")
            for reu in analise.partes.reus:
                relatorio.append(f"  • {reu}")
        
        if analise.partes.terceiros:
            relatorio.append("TERCEIROS:")
            for terceiro in analise.partes.terceiros:
                relatorio.append(f"  • {terceiro}")
        
        if analise.partes.advogados:
            relatorio.append("ADVOGADOS:")
            for advogado in analise.partes.advogados[:5]:
                relatorio.append(f"  • {advogado}")
        
        relatorio.append("")
        
        # Decisão judicial
        if analise.decisao:
            relatorio.append("3. DECISÃO JUDICIAL")
            relatorio.append("-" * 40)
            relatorio.append(f"Tipo: {analise.decisao.tipo_decisao}")
            relatorio.append(f"Resultado: {analise.decisao.resultado}")
            
            if analise.decisao.data_decisao:
                relatorio.append(f"Data: {analise.decisao.data_decisao}")
            
            relatorio.append(f"Dispositivo: {analise.decisao.dispositivo}")
            
            if analise.decisao.fundamentacao_resumida:
                relatorio.append(f"Fundamentação (resumo): {analise.decisao.fundamentacao_resumida}")
            
            relatorio.append("")
        
        # Informações adicionais
        if informacoes_adicionais:
            if informacoes_adicionais.get('custas_honorarios'):
                custas = informacoes_adicionais['custas_honorarios']
                relatorio.append("4. CUSTAS E HONORÁRIOS")
                relatorio.append("-" * 40)
                
                for campo, valor in custas.items():
                    if valor and valor != 'False':
                        nome_campo = campo.replace('_', ' ').title()
                        relatorio.append(f"{nome_campo}: {valor}")
                
                relatorio.append("")
            
            if informacoes_adicionais.get('legislacao_citada'):
                relatorio.append("5. LEGISLAÇÃO CITADA")
                relatorio.append("-" * 40)
                for lei in informacoes_adicionais['legislacao_citada']:
                    relatorio.append(f"  • {lei}")
                relatorio.append("")
        
        # Resumo executivo
        relatorio.append("6. RESUMO EXECUTIVO")
        relatorio.append("-" * 40)
        relatorio.append(analise.resumo_executivo)
        relatorio.append("")
        
        # Palavras-chave
        relatorio.append("7. PALAVRAS-CHAVE")
        relatorio.append("-" * 40)
        relatorio.append(", ".join(analise.palavras_chave))
        relatorio.append("")
        
        relatorio.append("=" * 80)
        relatorio.append("Relatório gerado automaticamente pelo Sistema de Análise Jurídica")
        relatorio.append("=" * 80)
        
        return "\n".join(relatorio)


def analisar_documento_juridico(texto_documento: str, metadados_extracao: Dict = None) -> Dict[str, Any]:
    """Função principal para análise de documento jurídico"""
    
    try:
        # Inicializar analisador
        analisador = AnalisadorJuridico()
        
        # Realizar análise completa
        analise = analisador.analisar_processo_completo(texto_documento)
        
        # Extrair informações adicionais
        info_adicionais = analisador.extrair_informacoes_adicionais(texto_documento)
        
        # Gerar relatório
        relatorio_texto = analisador.gerar_relatorio_detalhado(analise, info_adicionais)
        
        # Preparar resultado final
        resultado = analisador.gerar_analise_json(analise, metadados_extracao)
        resultado["informacoes_adicionais"] = info_adicionais
        resultado["relatorio_texto"] = relatorio_texto
        resultado["sentenca_integra"] = texto_documento  # Texto completo para referência
        
        return resultado
        
    except Exception as e:
        logging.error(f"Erro na análise do documento: {str(e)}")
        return {
            "erro": str(e),
            "timestamp_erro": datetime.now().isoformat(),
            "sucesso": False
        }


def processar_multiplos_documentos(lista_caminhos: List[str]) -> List[Dict[str, Any]]:
    """Processa múltiplos documentos em lote"""
    
    resultados = []
    analisador = AnalisadorJuridico()
    
    for caminho in lista_caminhos:
        try:
            # Este seria o ponto de integração com extrair_texto_juridico.py
            from extrair_texto_juridico import extrair_texto_pdf
            
            # Extrair texto
            resultado_extracao = extrair_texto_pdf(caminho)
            
            if not resultado_extracao['sucesso']:
                resultados.append({
                    "arquivo": caminho,
                    "erro": resultado_extracao['erro'],
                    "sucesso": False
                })
                continue
            
            # Analisar documento
            resultado_analise = analisar_documento_juridico(
                resultado_extracao['texto_completo'],
                resultado_extracao.get('metadados_arquivo', {})
            )
            
            resultado_analise["arquivo_origem"] = caminho
            resultados.append(resultado_analise)
            
        except Exception as e:
            resultados.append({
                "arquivo": caminho,
                "erro": str(e),
                "sucesso": False
            })
    
    return resultados


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python analisar_processo.py <texto_ou_arquivo>")
        print("Exemplo: python analisar_processo.py documento.txt")
        sys.exit(1)
    
    entrada = sys.argv[1]
    
    # Verificar se é arquivo ou texto
    if Path(entrada).exists():
        with open(entrada, 'r', encoding='utf-8') as f:
            texto = f.read()
        print(f"Analisando arquivo: {entrada}")
    else:
        texto = entrada
        print("Analisando texto fornecido")
    
    # Realizar análise
    resultado = analisar_documento_juridico(texto)
    
    # Output para N8N
    if resultado.get('erro'):
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        sys.exit(1)
    else:
        # Salvar resultado detalhado em arquivo temporário
        with open('/tmp/resultado_analise_juridica.json', 'w', encoding='utf-8') as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        
        # Output resumido para N8N
        output_n8n = {
            "sucesso": True,
            "arquivo_resultado": "/tmp/resultado_analise_juridica.json",
            "resumo": {
                "numero_processo": resultado["analise_completa"]["numero_processo"],
                "tipo_acao": resultado["analise_completa"]["tipo_acao"],
                "confianca": resultado["analise_completa"]["confianca_analise"],
                "total_partes": resultado["estatisticas"]["total_partes_identificadas"],
                "tem_decisao": resultado["estatisticas"]["tem_decisao"]
            }
        }
        
        print(json.dumps(output_n8n, ensure_ascii=False, indent=2))
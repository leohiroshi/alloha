"""
Serviço de Análise de Imagens para Imóveis
Processa imagens enviadas pelos usuários e extrai informações relevantes
"""

import base64
import logging
import asyncio
import aiohttp
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyImageAnalyzer:
    """Analisa imagens de imóveis e extrai informações"""
    
    def __init__(self):
        # Configurações de APIs de visão computacional
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.google_vision_key = os.getenv("GOOGLE_VISION_API_KEY", "")
        
        # Headers para APIs
        self.openai_headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Prompts especializados para análise de imóveis
        self.analysis_prompts = {
            'property_details': """
            Você é um especialista em avaliação de imóveis brasileiros. Analise esta imagem e extraia:
            
            🏠 IDENTIFICAÇÃO DO IMÓVEL:
            - Tipo: apartamento, casa, sobrado, kitnet, studio, cobertura, terreno, comercial
            - Estilo arquitetônico: moderno, clássico, colonial, contemporâneo
            
            📐 CARACTERÍSTICAS FÍSICAS:
            - Número de quartos (estimativa baseada no que vê)
            - Número de banheiros (se visível)
            - Área aproximada em m²
            - Pé-direito (alto, médio, baixo)
            - Layout (integrado, compartimentado)
            
            🎨 ACABAMENTOS E CONSERVAÇÃO:
            - Estado: novo, semi-novo, usado, precisa reforma
            - Qualidade dos acabamentos: básico, médio, alto padrão, luxo
            - Materiais visíveis: porcelanato, cerâmica, madeira, mármore
            - Pintura e conservação geral
            
            🌟 DIFERENCIAIS E COMODIDADES:
            - Mobiliado/semi-mobiliado/vazio
            - Varanda, sacada, terraço
            - Churrasqueira, piscina, jardim
            - Garagem, vaga coberta
            - Vista (mar, cidade, parque)
            
            🏘️ CONTEXTO E LOCALIZAÇÃO:
            - Tipo de vizinhança: residencial, comercial, mista
            - Indicadores de localização: prédios ao fundo, comércio próximo
            - Densidade urbana: centro, bairro residencial, periferia
            
            💰 SINAIS DE COMERCIALIZAÇÃO:
            - Placas de venda/locação visíveis
            - Nome da imobiliária ou corretor
            - Telefones ou contatos
            - Preços mencionados
            - Status: à venda, alugado, vendido
            
            🎯 PÚBLICO-ALVO SUGERIDO:
            - Ideal para: solteiros, casais, famílias, investidores
            - Faixa de preço estimada para o mercado brasileiro
            
            Responda em português brasileiro, formato JSON estruturado, sendo específico e útil para corretores imobiliários.""",
            
            'availability_check': """
            Analise esta imagem especificamente para determinar a DISPONIBILIDADE do imóvel:
            
            1. SINAIS DE INDISPONIBILIDADE:
               - Placas de "VENDIDO" ou "ALUGADO"
               - Faixas ou adesivos indicando venda/locação concluída
               - Móveis e pertences pessoais (indicando habitação)
               - Atividade comercial em funcionamento
            
            2. SINAIS DE DISPONIBILIDADE:
               - Placas de "VENDE-SE" ou "ALUGA-SE" ativas
               - Imóvel vazio ou em preparação para venda
               - Sinais de reforma ou preparação para locação
               - Ausência de móveis pessoais
            
            3. CONFIABILIDADE DA ANÁLISE:
               - Quão confiável é sua avaliação? (1-10)
               - Que elementos específicos suportam sua conclusão?
            
            Responda: DISPONÍVEL, INDISPONÍVEL, ou INCERTO
            Inclua justificativa detalhada.
            """,
            
            'contact_extraction': """
            Procure e extraia TODAS as informações de contato visíveis na imagem:
            
            1. TELEFONES:
               - Números de celular
               - Telefones fixos
               - WhatsApp
            2. IMOBILIÁRIAS:
               - Nome da empresa
               - Logo ou marca
               - CRECI
            3. OUTROS CONTATOS:
               - Emails
               - Sites
               - Redes sociais
            4. CÓDIGOS/REFERÊNCIAS:
               - Códigos do imóvel
               - QR codes
               - Sites ou links
            
            Liste EXATAMENTE o que está escrito, sem alterações.
            """
        }
    
    async def analyze_property_image(self, image_data: bytes, analysis_type: str = "complete") -> Dict[str, Any]:
        """Analisa imagem de imóvel com IA"""
        try:
            # Converter para base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # 1. TESTAR ABACUS VISION PRIMEIRO
            abacus_vision_result = await self._test_abacus_vision_capability(image_base64)
            
            # 2. ANÁLISE GRATUITA BÁSICA
            from .free_image_analyzer import free_analyzer
            basic_analysis = await free_analyzer.analyze_property_image_free(image_data)
            
            # 3. TENTAR APIs PAGAS (se configuradas)
            advanced_analysis = None
            
            # Abacus Vision (se suportado)
            if abacus_vision_result.get("supports_vision"):
                logger.info("🎉 Usando Abacus Vision para análise!")
                advanced_analysis = abacus_vision_result
            # OpenAI Vision (se configurado)
            elif self.openai_api_key:
                advanced_analysis = await self._analyze_with_openai(image_base64, analysis_type)
            # Google Vision (se configurado)
            elif self.google_vision_key:
                advanced_analysis = await self._analyze_with_google_vision(image_data)
            
            # 4. USAR ABACUS PARA ANÁLISE CONTEXTUAL (GRATUITO)
            abacus_text_analysis = await self._analyze_with_abacus_description(basic_analysis)
            
            # 5. COMBINAR RESULTADOS
            final_analysis = self._combine_all_analysis_results(
                basic_analysis, 
                advanced_analysis, 
                abacus_text_analysis,
                abacus_vision_result
            )
            
            # Adicionar metadados
            final_analysis['metadata'] = {
                'analyzed_at': datetime.now().isoformat(),
                'analysis_type': analysis_type,
                'methods_used': self._get_used_methods(basic_analysis, advanced_analysis, abacus_text_analysis, abacus_vision_result),
                'confidence_score': self._calculate_confidence(final_analysis),
                'cost': self._calculate_cost(advanced_analysis, abacus_vision_result),
                'abacus_vision_available': abacus_vision_result.get("supports_vision", False)
            }
            
            logger.info(f"Imagem analisada - Métodos: {final_analysis['metadata']['methods_used']}")
            return final_analysis
            
        except Exception as e:
            logger.error(f"Erro na análise de imagem: {str(e)}")
            return {
                'error': str(e),
                'success': False,
                'fallback_analysis': 'Análise básica indisponível',
                'metadata': {'analyzed_at': datetime.now().isoformat()}
            }
    
    async def _test_abacus_vision_capability(self, image_base64: str) -> Dict[str, Any]:
        """Testar se Abacus suporta análise de imagem"""
        try:
            from .ai_service import AIService
            ai_service = AIService()
            
            # Testar com uma pequena amostra da imagem para economizar
            sample_base64 = image_base64[:1000] if len(image_base64) > 1000 else image_base64
            
            result = await ai_service.test_abacus_image_support(sample_base64)
            
            # Se funcionar, fazer análise completa
            if result.get("supports_vision"):
                full_analysis = await ai_service.analyze_image_with_abacus(
                    image_base64, 
                    "Analise esta imagem de imóvel brasileiro para um corretor"
                )
                
                if full_analysis:
                    result["analysis_content"] = full_analysis
                    result["method"] = "Abacus Vision API"
                    result["cost"] = "Incluído no plano Abacus"
            
            return result
            
        except Exception as e:
            logger.error(f"Erro testando Abacus vision: {str(e)}")
            return {
                "supports_vision": False, 
                "error": str(e),
                "method": "Abacus test failed"
            }
    
    async def _analyze_with_abacus_description(self, basic_analysis: Dict) -> Dict:
        """Usar Abacus AI para analisar descrição da imagem (GRATUITO)"""
        try:
            # Importar AI service
            from .ai_service import AIService
            ai_service = AIService()
            
            # Criar descrição baseada na análise básica
            description = self._create_description_from_basic_analysis(basic_analysis)
            
            # Prompt para Abacus analisar a descrição
            system_prompt = """Você é um especialista em avaliação de imóveis. 
            Baseado na descrição técnica de uma foto de imóvel, forneça uma análise detalhada.
            Seja específico sobre tipo de imóvel, características e recomendações.
            Responda em português brasileiro, formato estruturado."""
            
            user_prompt = f"""Analise esta descrição de foto de imóvel:
            
            {description}
            
            Forneça:
            1. Tipo de imóvel mais provável
            2. Características sugeridas
            3. Qualidade da foto para marketing
            4. Recomendações para melhorar
            5. Público-alvo sugerido"""
            
            abacus_response = await ai_service._call_abacus_api(system_prompt, user_prompt)
            
            if abacus_response:
                return {
                    'abacus_analysis': abacus_response,
                    'method': 'Abacus AI + Análise Básica',
                    'success': True
                }
            else:
                return {'method': 'Abacus indisponível', 'success': False}
                
        except Exception as e:
            logger.error(f"Erro no Abacus analysis: {str(e)}")
            return {'error': str(e), 'method': 'Abacus falhou', 'success': False}
    
    def _create_description_from_basic_analysis(self, basic_analysis: Dict) -> str:
        """Criar descrição textual da análise básica para o Abacus"""
        description_parts = []
        
        # Informações básicas
        if 'dimensoes' in basic_analysis:
            dims = basic_analysis['dimensoes']
            description_parts.append(f"Imagem de {dims['largura']}x{dims['altura']} pixels")
            description_parts.append(f"Proporção {dims['proporcao']} ({basic_analysis.get('caracteristicas_visuais', {}).get('orientacao', 'desconhecida')})")
        
        # Qualidade
        if 'qualidade_estimada' in basic_analysis:
            qual = basic_analysis['qualidade_estimada']
            description_parts.append(f"Qualidade: {qual.get('classificacao', 'não avaliada')}")
            description_parts.append(f"Brilho: {qual.get('brilho', 'N/A')}, Contraste: {qual.get('contraste', 'N/A')}")
        
        # Características visuais
        if 'caracteristicas_visuais' in basic_analysis:
            vis = basic_analysis['caracteristicas_visuais']
            description_parts.append(f"Resolução: {vis.get('resolucao', 'desconhecida')}")
            if 'cores' in vis:
                description_parts.append(f"Variedade de cores: {vis['cores'].get('variedade_cores', 'não analisada')}")
        
        # Sugestões de tipo
        if 'sugestoes_imovel' in basic_analysis:
            sug = basic_analysis['sugestoes_imovel']
            if 'sugestoes' in sug:
                description_parts.append(f"Sugestões de tipo: {', '.join(sug['sugestoes'])}")
        
        # Formato do arquivo
        if 'formato' in basic_analysis:
            description_parts.append(f"Formato: {basic_analysis['formato']}")
        
        return ". ".join(description_parts) + "."
    
    def _combine_all_analysis_results(self, basic: Dict, advanced: Optional[Dict], abacus_text: Dict, abacus_vision: Dict) -> Dict:
        """Combinar todas as análises disponíveis"""
        combined = {
            'analysis_summary': 'Análise Completa Híbrida',
            'basic_analysis': basic,
            'abacus_text_insights': abacus_text,
            'success': True
        }
        
        # Adicionar análise avançada se disponível
        if advanced:
            combined['advanced_analysis'] = advanced
            combined['analysis_summary'] = 'Análise Premium - Todas as IAs'
        
        # Adicionar Abacus Vision se disponível
        if abacus_vision.get("supports_vision"):
            combined['abacus_vision_analysis'] = abacus_vision
            combined['analysis_summary'] = 'Análise com Abacus Vision (GRATUITO!)'
        
        # Criar resumo executivo
        combined['executive_summary'] = self._create_comprehensive_executive_summary(
            basic, advanced, abacus_text, abacus_vision
        )
        
        return combined
    
    def _create_comprehensive_executive_summary(self, basic: Dict, advanced: Optional[Dict], abacus_text: Dict, abacus_vision: Dict) -> Dict:
        """Criar resumo executivo completo"""
        summary = {
            'quality_assessment': 'Não avaliada',
            'property_type_suggestion': 'Não identificado',
            'marketing_readiness': 'Não avaliada',
            'ai_confidence': 'Baixa',
            'recommendations': [],
            'best_analysis_source': 'Análise Básica'
        }
        
        # Priorizar Abacus Vision se disponível
        if abacus_vision.get("supports_vision") and abacus_vision.get("analysis_content"):
            summary['ai_insights'] = abacus_vision['analysis_content'][:300] + "..."
            summary['best_analysis_source'] = 'Abacus Vision (Gratuito)'
            summary['ai_confidence'] = 'Alta'
            summary['recommendations'].append("✅ Análise de IA avançada disponível gratuitamente!")
        
        # Análise avançada paga
        elif advanced:
            summary['best_analysis_source'] = 'IA Avançada (Paga)'
            summary['ai_confidence'] = 'Muito Alta'
        
        # Da análise básica
        if 'qualidade_estimada' in basic:
            summary['quality_assessment'] = basic['qualidade_estimada'].get('classificacao', 'Não avaliada')
        
        if 'sugestoes_imovel' in basic:
            suggestions = basic['sugestoes_imovel'].get('sugestoes', [])
            if suggestions:
                summary['property_type_suggestion'] = suggestions[0]
        
        if 'recomendacoes' in basic:
            summary['recommendations'].extend(basic['recomendacoes'][:3])  # Primeiras 3
        
        # Do Abacus texto
        if abacus_text.get('success') and 'abacus_analysis' in abacus_text:
            summary['abacus_text_insights'] = abacus_text['abacus_analysis'][:200] + "..."
        
        return summary
    
    def _calculate_cost(self, advanced_analysis: Optional[Dict], abacus_vision: Dict) -> str:
        """Calcular custo da análise"""
        if abacus_vision.get("supports_vision"):
            return "Gratuito (Abacus Vision incluído no plano)"
        elif advanced_analysis:
            return "Pago (OpenAI/Google Vision)"
        else:
            return "Totalmente Gratuito"
    
    def _get_used_methods(self, basic: Dict, advanced: Optional[Dict], abacus_text: Dict, abacus_vision: Dict) -> list:
        """Listar métodos de análise utilizados"""
        methods = ['Análise Básica Gratuita']
        
        if abacus_vision.get("supports_vision"):
            methods.append('Abacus Vision API (Gratuito!)')
        
        if abacus_text.get('success'):
            methods.append('Abacus Text Analysis')
        
        if advanced:
            if 'openai' in str(advanced).lower():
                methods.append('OpenAI Vision (Pago)')
            elif 'google' in str(advanced).lower():
                methods.append('Google Vision (Pago)')
        
        return methods

    def _combine_free_and_ai_analysis(self, basic: Dict, advanced: Optional[Dict], abacus: Dict) -> Dict:
        """Combinar análises gratuitas e pagas"""
        combined = {
            'analysis_summary': 'Análise Combinada - Gratuita + IA',
            'basic_analysis': basic,
            'abacus_insights': abacus,
            'success': True
        }
        
        # Adicionar análise avançada se disponível
        if advanced:
            combined['advanced_analysis'] = advanced
            combined['analysis_summary'] = 'Análise Completa - Gratuita + IA Avançada'
        
        # Criar resumo executivo
        combined['executive_summary'] = self._create_executive_summary(basic, advanced, abacus)
        
        return combined
    
    def _create_executive_summary(self, basic: Dict, advanced: Optional[Dict], abacus: Dict) -> Dict:
        """Criar resumo executivo da análise"""
        summary = {
            'quality_assessment': 'Não avaliada',
            'property_type_suggestion': 'Não identificado',
            'marketing_readiness': 'Não avaliada',
            'recommendations': []
        }
        
        # Da análise básica
        if 'qualidade_estimada' in basic:
            summary['quality_assessment'] = basic['qualidade_estimada'].get('classificacao', 'Não avaliada')
        
        if 'sugestoes_imovel' in basic:
            suggestions = basic['sugestoes_imovel'].get('sugestoes', [])
            if suggestions:
                summary['property_type_suggestion'] = suggestions[0]
        
        if 'recomendacoes' in basic:
            summary['recommendations'].extend(basic['recomendacoes'])
        
        # Do Abacus
        if abacus.get('success') and 'abacus_analysis' in abacus:
            summary['ai_insights'] = abacus['abacus_analysis'][:200] + "..." if len(abacus['abacus_analysis']) > 200 else abacus['abacus_analysis']
        
        # Da análise avançada (se disponível)
        if advanced:
            summary['advanced_features'] = 'Análise detalhada disponível'
        
        return summary
    
    def _get_used_methods(self, basic: Dict, advanced: Optional[Dict], abacus: Dict) -> list:
        """Listar métodos de análise utilizados"""
        methods = ['Análise Básica Gratuita']
        
        if abacus.get('success'):
            methods.append('Abacus AI (Gratuito)')
        
        if advanced:
            if 'openai' in str(advanced).lower():
                methods.append('OpenAI Vision (Pago)')
            elif 'google' in str(advanced).lower():
                methods.append('Google Vision (Pago)')
        
        return methods
    
    async def _analyze_with_openai(self, image_base64: str, analysis_type: str) -> Optional[Dict]:
        """Análise com OpenAI GPT-4 Vision"""
        if not self.openai_api_key:
            logger.warning("OpenAI API key não configurada")
            return None
        
        try:
            # Selecionar prompt baseado no tipo de análise
            if analysis_type == "availability":
                prompt = self.analysis_prompts['availability_check']
            elif analysis_type == "contact":
                prompt = self.analysis_prompts['contact_extraction']
            else:
                prompt = self.analysis_prompts['property_details']
            
            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=self.openai_headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Tentar parsear JSON se possível
                        try:
                            return json.loads(content)
                        except:
                            return {'analysis': content, 'raw_response': True}
                    else:
                        error_text = await response.text()
                        logger.error(f"Erro OpenAI: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Erro na análise OpenAI: {str(e)}")
            return None
    
    async def _analyze_with_google_vision(self, image_data: bytes) -> Optional[Dict]:
        """Análise com Google Cloud Vision (backup)"""
        if not self.google_vision_key:
            logger.warning("Google Vision API key não configurada")
            return None
        
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            payload = {
                "requests": [
                    {
                        "image": {"content": image_base64},
                        "features": [
                            {"type": "TEXT_DETECTION"},
                            {"type": "OBJECT_LOCALIZATION"},
                            {"type": "LABEL_DETECTION"}
                        ]
                    }
                ]
            }
            
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.google_vision_key}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._process_google_vision_result(result)
                    else:
                        logger.error(f"Erro Google Vision: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Erro na análise Google Vision: {str(e)}")
            return None
    
    def _process_google_vision_result(self, result: Dict) -> Dict:
        """Processa resultado do Google Vision"""
        processed = {
            'text_detected': [],
            'objects': [],
            'labels': []
        }
        
        try:
            annotations = result.get('responses', [{}])[0]
            
            # Texto detectado
            if 'textAnnotations' in annotations:
                for text in annotations['textAnnotations']:
                    processed['text_detected'].append(text.get('description', ''))
            
            # Objetos localizados
            if 'localizedObjectAnnotations' in annotations:
                for obj in annotations['localizedObjectAnnotations']:
                    processed['objects'].append(obj.get('name', ''))
            
            # Labels/categorias
            if 'labelAnnotations' in annotations:
                for label in annotations['labelAnnotations']:
                    processed['labels'].append({
                        'description': label.get('description', ''),
                        'score': label.get('score', 0)
                    })
            
            return processed
            
        except Exception as e:
            logger.error(f"Erro processando resultado Google Vision: {str(e)}")
            return processed
    
    def _combine_analysis_results(self, openai_result: Optional[Dict], google_result: Optional[Dict]) -> Dict:
        """Combina resultados de diferentes APIs"""
        combined = {
            'success': True,
            'property_type': 'unknown',
            'availability_status': 'uncertain',
            'confidence': 0,
            'characteristics': {},
            'contact_info': {},
            'marketing_elements': [],
            'text_detected': [],
            'analysis_summary': ''
        }
        
        try:
            # Processar resultado OpenAI (principal)
            if openai_result:
                if isinstance(openai_result, dict) and not openai_result.get('raw_response'):
                    # Resultado JSON estruturado
                    combined.update(openai_result)
                else:
                    # Resultado em texto
                    combined['analysis_summary'] = openai_result.get('analysis', str(openai_result))
                    combined['confidence'] = 7  # Confiança média para texto
            
            # Processar resultado Google Vision (complementar)
            if google_result:
                combined['text_detected'] = google_result.get('text_detected', [])
                
                # Extrair informações de contato do texto detectado
                contact_info = self._extract_contact_from_text(combined['text_detected'])
                combined['contact_info'].update(contact_info)
                
                # Verificar objetos detectados
                objects = google_result.get('objects', [])
                if 'Building' in objects or 'House' in objects:
                    if combined['property_type'] == 'unknown':
                        combined['property_type'] = 'residential'
                
                # Aumentar confiança se há concordância
                if combined['confidence'] > 0:
                    combined['confidence'] = min(10, combined['confidence'] + 1)
            
            return combined
            
        except Exception as e:
            logger.error(f"Erro combinando resultados: {str(e)}")
            combined['error'] = str(e)
            combined['success'] = False
            return combined
    
    def _extract_contact_from_text(self, text_list: List[str]) -> Dict:
        """Extrai informações de contato do texto detectado"""
        contact_info = {
            'phones': [],
            'emails': [],
            'websites': [],
            'companies': []
        }
        
        try:
            all_text = ' '.join(text_list).lower()
            
            # Telefones brasileiros
            phone_patterns = [
                r'\(?(?:0xx)?(\d{2})\)?\s*\d{4,5}[-.\s]?\d{4}',  # (11) 99999-9999
                r'\d{2}\s*\d{4,5}[-.\s]?\d{4}',  # 11 99999-9999
                r'\d{10,11}'  # 11999999999
            ]
            
            for pattern in phone_patterns:
                matches = re.findall(pattern, all_text)
                contact_info['phones'].extend(matches)
            
            # Emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, all_text)
            contact_info['emails'].extend(emails)
            
            # Websites
            url_pattern = r'(?:www\.|https?://)[^\s]+'
            websites = re.findall(url_pattern, all_text)
            contact_info['websites'].extend(websites)
            
            # Imobiliárias conhecidas
            known_companies = ['allega', 'imóveis', 'imoveis', 'creci', 'corretora']
            for company in known_companies:
                if company in all_text:
                    contact_info['companies'].append(company)
            
            return contact_info
            
        except Exception as e:
            logger.error(f"Erro extraindo contatos: {str(e)}")
            return contact_info
    
    def _calculate_confidence(self, analysis: Dict) -> int:
        """Calcula score de confiança da análise"""
        try:
            confidence = 0
            
            # Base de confiança
            if analysis.get('success'):
                confidence += 3
            
            # Aumenta se detectou tipo de imóvel
            if analysis.get('property_type') != 'unknown':
                confidence += 2
            
            # Aumenta se detectou texto
            if analysis.get('text_detected'):
                confidence += 2
            
            # Aumenta se tem informações de contato
            if analysis.get('contact_info', {}).get('phones'):
                confidence += 2
            
            # Aumenta se tem análise detalhada
            if analysis.get('analysis_summary'):
                confidence += 1
            
            return min(10, confidence)
            
        except:
            return 5  # Confiança média em caso de erro
    
    def format_analysis_response(self, analysis: Dict, user_message: str = "") -> str:
        """Formata resultado da análise para resposta ao usuário"""
        try:
            if not analysis.get('success'):
                return (
                    "😅 Ops! Tive dificuldade para analisar essa imagem.\n\n"
                    "📸 *Dicas para melhores resultados:*\n"
                    "• Use imagens claras e bem iluminadas\n"
                    "• Inclua placas ou sinais visíveis\n"
                    "• Evite fotos muito distantes\n\n"
                    "📞 Posso ajudar de outras formas:\n"
                    f"🏠 Vendas: (41) 99214-6670\n"
                    f"🏡 Locação: (41) 99223-0874"
                )
            
            response = "🏠 *Análise da Imagem do Imóvel*\n\n"
            
            # Tipo de imóvel detectado
            if analysis.get('property_type') != 'unknown':
                property_type = analysis.get('property_type', '').title()
                response += f"🏢 *Tipo:* {property_type}\n"
            
            # Status de disponibilidade
            availability = analysis.get('availability_status', 'uncertain').lower()
            if availability == 'disponível' or availability == 'available':
                response += "✅ *Status:* Aparenta estar DISPONÍVEL\n"
            elif availability == 'indisponível' or availability == 'unavailable':
                response += "❌ *Status:* Aparenta estar INDISPONÍVEL\n"
            else:
                response += "❓ *Status:* Não foi possível determinar\n"
            
            # Características identificadas
            characteristics = analysis.get('characteristics', {})
            if characteristics:
                response += "\n🏡 *Características identificadas:*\n"
                for key, value in characteristics.items():
                    if value:
                        response += f"• {key.title()}: {value}\n"
            
            # Informações de contato encontradas
            contact_info = analysis.get('contact_info', {})
            if any(contact_info.values()):
                response += "\n📞 *Contatos identificados na imagem:*\n"
                
                if contact_info.get('phones'):
                    for phone in contact_info['phones'][:2]:  # Máximo 2 telefones
                        response += f"📱 {phone}\n"
                
                if contact_info.get('companies'):
                    companies = set(contact_info['companies'])
                    for company in list(companies)[:2]:
                        response += f"🏢 {company.title()}\n"
            
            # Confiabilidade
            confidence = analysis.get('confidence', 0)
            if confidence >= 8:
                response += "\n🎯 *Análise:* Alta confiabilidade"
            elif confidence >= 6:
                response += "\n🎯 *Análise:* Confiabilidade média"
            else:
                response += "\n🎯 *Análise:* Confiabilidade baixa"
            
            # Resumo da análise se disponível
            summary = analysis.get('analysis_summary', '')
            if summary and len(summary) < 200:
                response += f"\n\n💡 *Observações:* {summary[:150]}..."
            
            # Adicionar contatos da Allega
            response += "\n\n📞 *Posso ajudar com:*\n"
            response += "• Buscar imóveis similares\n"
            response += "• Verificar disponibilidade atualizada\n"
            response += "• Agendar visitas\n\n"
            response += "🏠 Vendas: (41) 99214-6670\n"
            response += "🏡 Locação: (41) 99223-0874"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro formatando resposta: {str(e)}")
            return (
                "🏠 Recebi sua imagem! Posso ajudar você com:\n\n"
                "• Buscar imóveis similares\n"
                "• Verificar disponibilidade\n"
                "• Informações sobre preços\n"
                "• Agendar visitas\n\n"
                "📞 Entre em contato:\n"
                "🏠 Vendas: (41) 99214-6670\n"
                "🏡 Locação: (41) 99223-0874"
            )
    
    async def check_property_availability_by_image(self, image_data: bytes) -> Dict[str, Any]:
        """Verifica especificamente a disponibilidade através da imagem"""
        try:
            # Análise focada em disponibilidade
            analysis = await self.analyze_property_image(image_data, "availability")
            
            # Processar resultado específico
            availability_result = {
                'is_available': None,
                'confidence': 0,
                'reasoning': '',
                'contact_found': False,
                'recommendation': ''
            }
            
            if analysis.get('success'):
                # Determinar disponibilidade
                status = analysis.get('availability_status', '').lower()
                
                if 'disponível' in status or 'available' in status:
                    availability_result['is_available'] = True
                    availability_result['recommendation'] = 'Imóvel parece disponível! Recomendo entrar em contato rapidamente.'
                elif 'indisponível' in status or 'unavailable' in status:
                    availability_result['is_available'] = False
                    availability_result['recommendation'] = 'Imóvel pode estar ocupado. Posso buscar opções similares.'
                else:
                    availability_result['is_available'] = None
                    availability_result['recommendation'] = 'Status incerto. Melhor verificar diretamente com a imobiliária.'
                
                availability_result['confidence'] = analysis.get('confidence', 0)
                availability_result['reasoning'] = analysis.get('analysis_summary', 'Análise baseada em elementos visuais da imagem.')
                
                # Verificar se encontrou contatos
                contact_info = analysis.get('contact_info', {})
                availability_result['contact_found'] = bool(contact_info.get('phones') or contact_info.get('companies'))
            
            return availability_result
            
        except Exception as e:
            logger.error(f"Erro verificando disponibilidade: {str(e)}")
            return {
                'is_available': None,
                'confidence': 0,
                'reasoning': f'Erro na análise: {str(e)}',
                'contact_found': False,
                'recommendation': 'Recomendo verificar diretamente com a imobiliária.'
            }


# Instância global do analisador
property_image_analyzer = PropertyImageAnalyzer()

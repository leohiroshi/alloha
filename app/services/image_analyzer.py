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
            Analise esta imagem de imóvel e extraia as seguintes informações:
            
            1. TIPO DE IMÓVEL (apartamento, casa, comercial, terreno)
            2. CARACTERÍSTICAS VISÍVEIS:
               - Número de quartos (se visível)
               - Número de banheiros (se visível)
               - Área aproximada
               - Estado de conservação
               - Mobiliado/não mobiliado
            3. LOCALIZAÇÃO E CONTEXTO:
               - Tipo de vizinhança (residencial, comercial, etc.)
               - Qualidade da construção
               - Acabamentos (básico, médio, alto padrão)
            4. ELEMENTOS DE MARKETING:
               - Há placas ou sinais de venda/locação?
               - Informações de contato visíveis?
               - Preços mencionados?
               - Nome da imobiliária?
            5. ESTADO DE DISPONIBILIDADE:
               - Imóvel parece habitado ou vazio?
               - Sinais de "vendido" ou "alugado"?
               - Indicadores de disponibilidade
            
            Responda em formato JSON estruturado em português.
            """,
            
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
            # Converter imagem para base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Analisar com OpenAI Vision (GPT-4V)
            openai_result = await self._analyze_with_openai(image_base64, analysis_type)
            
            # Tentar análise com Google Vision como backup
            google_result = await self._analyze_with_google_vision(image_data)
            
            # Combinar resultados
            analysis_result = self._combine_analysis_results(openai_result, google_result)
            
            # Adicionar metadados
            analysis_result['metadata'] = {
                'analyzed_at': datetime.now().isoformat(),
                'analysis_type': analysis_type,
                'confidence_score': self._calculate_confidence(analysis_result),
                'apis_used': ['openai'] if openai_result else [] + ['google'] if google_result else []
            }
            
            logger.info(f"Imagem analisada com sucesso - Tipo: {analysis_type}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Erro na análise de imagem: {str(e)}")
            return {
                'error': str(e),
                'success': False,
                'metadata': {'analyzed_at': datetime.now().isoformat()}
            }
    
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

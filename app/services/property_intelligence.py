"""
Serviço de Inteligência Imobiliária
Integra dados de imóveis com a IA Groq para respostas inteligentes
"""

import json
import logging
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
import aiohttp

from .firebase_service import FirebaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyIntelligenceService:
    """Serviço que combina Groq com dados imobiliários"""

    def __init__(self):
        self.firebase_service = FirebaseService()
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.text_model = "llama3-8b-8192"  # Modelo de texto do Groq
        self.property_cache = {}
        self.cache_expiry = timedelta(hours=6)
        self.last_cache_update = None

        self.company_info = {
            'name': 'Allega Imóveis',
            'creci': '6684 J',
            'address': 'Rua Gastão Câmara, 135 - Bigorrilho, Curitiba - PR',
            'phone_sales': '(41) 99214-6670',
            'phone_rental': '(41) 99223-0874',
            'phone_fixed': '(41) 3285-1383',
            'email': 'contato@allegaimoveis.com',
            'website': 'https://www.allegaimoveis.com',
            'whatsapp_sales': 'https://wa.me/5541992146670',
            'whatsapp_rental': 'https://wa.me/5541992230874'
        }

    async def load_property_data(self) -> bool:
        """Carrega dados de imóveis do Firebase ou cache"""
        try:
            if (self.last_cache_update and
                datetime.now() - self.last_cache_update < self.cache_expiry and
                self.property_cache):
                return True

            properties = await self.firebase_service.get_property_data()

            if properties:
                self.property_cache = properties
                self.last_cache_update = datetime.now()
                logger.info(f"Dados de {len(properties)} imóveis carregados do Firebase")
                return True
            else:
                self._load_sample_data()
                logger.info("Usando dados simulados de imóveis")
                return True

        except Exception as e:
            logger.error(f"Erro ao carregar dados de imóveis: {str(e)}")
            self._load_sample_data()
            return False

    def _load_sample_data(self):
        """Carrega dados de exemplo para demonstração"""
        self.property_cache = {
            'properties': [
                {
                    'id': '1',
                    'title': 'Apartamento 3 quartos no Bigorrilho',
                    'property_type': 'apartamento',
                    'transaction_type': 'venda',
                    'bedrooms': 3,
                    'bathrooms': 2,
                    'parking_spaces': 2,
                    'area_total': '85m²',
                    'price': 'R$ 450.000,00',
                    'neighborhood': 'Bigorrilho',
                    'city': 'Curitiba',
                    'description': 'Apartamento moderno com vista para a cidade',
                    'features': ['Sacada', 'Churrasqueira', 'Academia'],
                    'url': 'https://www.allegaimoveis.com/imovel/1'
                },
                {
                    'id': '2',
                    'title': 'Casa 4 quartos no Champagnat',
                    'property_type': 'casa',
                    'transaction_type': 'venda',
                    'bedrooms': 4,
                    'bathrooms': 3,
                    'parking_spaces': 3,
                    'area_total': '200m²',
                    'price': 'R$ 850.000,00',
                    'neighborhood': 'Champagnat',
                    'city': 'Curitiba',
                    'description': 'Casa ampla com jardim e piscina',
                    'features': ['Piscina', 'Jardim', 'Churrasqueira', 'Área de lazer'],
                    'url': 'https://www.allegaimoveis.com/imovel/2'
                },
                {
                    'id': '3',
                    'title': 'Apartamento 2 quartos para locação',
                    'property_type': 'apartamento',
                    'transaction_type': 'locacao',
                    'bedrooms': 2,
                    'bathrooms': 1,
                    'parking_spaces': 1,
                    'area_total': '60m²',
                    'price': 'R$ 1.800,00/mês',
                    'neighborhood': 'Centro',
                    'city': 'Curitiba',
                    'description': 'Apartamento próximo ao centro da cidade',
                    'features': ['Mobiliado', 'Próximo ao metrô'],
                    'url': 'https://www.allegaimoveis.com/imovel/3'
                },
                {
                    'id': '4',
                    'title': 'Casa 3 quartos no Batel',
                    'property_type': 'casa',
                    'transaction_type': 'venda',
                    'bedrooms': 3,
                    'bathrooms': 2,
                    'parking_spaces': 2,
                    'area_total': '150m²',
                    'price': 'R$ 650.000,00',
                    'neighborhood': 'Batel',
                    'city': 'Curitiba',
                    'description': 'Casa em condomínio fechado com segurança 24h',
                    'features': ['Condomínio fechado', 'Segurança 24h', 'Área verde'],
                    'url': 'https://www.allegaimoveis.com/imovel/4'
                },
                {
                    'id': '5',
                    'title': 'Apartamento 1 quarto Água Verde',
                    'property_type': 'apartamento',
                    'transaction_type': 'locacao',
                    'bedrooms': 1,
                    'bathrooms': 1,
                    'parking_spaces': 1,
                    'area_total': '45m²',
                    'price': 'R$ 1.200,00/mês',
                    'neighborhood': 'Água Verde',
                    'city': 'Curitiba',
                    'description': 'Apartamento compacto e moderno',
                    'features': ['Mobiliado', 'Academia', 'Piscina'],
                    'url': 'https://www.allegaimoveis.com/imovel/5'
                }
            ],
            'statistics': {
                'total_properties': 5,
                'by_type': {'apartamento': 3, 'casa': 2},
                'by_transaction': {'venda': 3, 'locacao': 2},
                'by_city': {'Curitiba': 5}
            }
        }
        self.last_cache_update = datetime.now()

    def search_properties(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Busca imóveis baseado em critérios"""
        if not self.property_cache or 'properties' not in self.property_cache:
            return []

        properties = self.property_cache['properties']
        matches = []

        for prop in properties:
            score = 0
            match = True

            if criteria.get('property_type'):
                if prop.get('property_type', '').lower() == criteria['property_type'].lower():
                    score += 20
                else:
                    continue

            if criteria.get('transaction_type'):
                if prop.get('transaction_type', '').lower() == criteria['transaction_type'].lower():
                    score += 20
                else:
                    continue

            if criteria.get('city'):
                if criteria['city'].lower() in prop.get('city', '').lower():
                    score += 15

            if criteria.get('neighborhood'):
                if criteria['neighborhood'].lower() in prop.get('neighborhood', '').lower():
                    score += 15

            if criteria.get('bedrooms'):
                prop_bedrooms = prop.get('bedrooms', 0)
                if prop_bedrooms >= criteria['bedrooms']:
                    score += 10
                elif abs(prop_bedrooms - criteria['bedrooms']) <= 1:
                    score += 5

            if criteria.get('max_price'):
                prop_price = self._extract_price(prop.get('price', ''))
                if prop_price and prop_price <= criteria['max_price']:
                    score += 10

            if match:
                prop_copy = prop.copy()
                prop_copy['match_score'] = score
                matches.append(prop_copy)

        matches.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        return matches[:5]

    def _extract_price(self, price_str: str) -> Optional[float]:
        """Extrai valor numérico do preço"""
        if not price_str:
            return None
        numbers = re.findall(r'[\d.,]+', price_str.replace('.', '').replace(',', '.'))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        return None

    def extract_search_criteria(self, message: str) -> Dict[str, Any]:
        """Extrai critérios de busca da mensagem do usuário"""
        message_lower = message.lower()
        criteria = {}

        if any(word in message_lower for word in ['comprar', 'compra', 'venda', 'vender']):
            criteria['transaction_type'] = 'venda'
        elif any(word in message_lower for word in ['alugar', 'aluguel', 'locação', 'locacao']):
            criteria['transaction_type'] = 'locacao'

        property_types = {
            'apartamento': ['apartamento', 'ap', 'apto'],
            'casa': ['casa', 'residencia'],
            'sobrado': ['sobrado'],
            'terreno': ['terreno', 'lote'],
            'cobertura': ['cobertura'],
            'studio': ['studio', 'loft']
        }

        for prop_type, keywords in property_types.items():
            if any(keyword in message_lower for keyword in keywords):
                criteria['property_type'] = prop_type
                break

        bedroom_match = re.search(r'(\d+)\s*(?:quarto|dormitório|dorm)', message_lower)
        if bedroom_match:
            criteria['bedrooms'] = int(bedroom_match.group(1))

        locations = ['bigorrilho', 'champagnat', 'centro', 'água verde', 'batel', 'cabral', 'portão', 'santa felicidade']
        for location in locations:
            if location in message_lower:
                criteria['neighborhood'] = location
                break

        if 'curitiba' in message_lower:
            criteria['city'] = 'Curitiba'
        elif 'itapema' in message_lower:
            criteria['city'] = 'Itapema'

        price_match = re.search(r'até\s*r?\$?\s*([\d.,]+)', message_lower)
        if price_match:
            price_str = price_match.group(1).replace('.', '').replace(',', '.')
            try:
                criteria['max_price'] = float(price_str)
            except ValueError:
                pass

        return criteria

    def format_property_response(self, properties: List[Dict[str, Any]], criteria: Dict[str, Any]) -> str:
        """Formata resposta com imóveis encontrados"""
        if not properties:
            return self._generate_no_results_response(criteria)

        response = f"🏠 *Encontrei {len(properties)} imóveis que podem interessar você:*\n\n"

        for i, prop in enumerate(properties[:3], 1):
            response += f"*{i}. {prop.get('title', 'Imóvel')}*\n"
            response += f"📍 {prop.get('neighborhood', '')}, {prop.get('city', '')}\n"
            response += f"💰 {prop.get('price', 'Consulte')}\n"

            details = []
            if prop.get('bedrooms'):
                details.append(f"{prop['bedrooms']} quartos")
            if prop.get('bathrooms'):
                details.append(f"{prop['bathrooms']} banheiros")
            if prop.get('parking_spaces'):
                details.append(f"{prop['parking_spaces']} vagas")
            if prop.get('area_total'):
                details.append(f"{prop['area_total']}")

            if details:
                response += f"🏡 {', '.join(details)}\n"

            if prop.get('description'):
                response += f"📝 {prop['description'][:100]}...\n"

            if prop.get('features'):
                features = ', '.join(prop['features'][:3])
                response += f"✨ {features}\n"

            response += f"🔗 {prop.get('url', 'Ver mais detalhes')}\n\n"

        if len(properties) > 3:
            response += f"_E mais {len(properties) - 3} imóveis disponíveis..._\n\n"

        response += self._add_contact_info()
        return response

    def _generate_no_results_response(self, criteria: Dict[str, Any]) -> str:
        """Gera resposta quando não encontra imóveis"""
        response = "😔 *Não encontrei imóveis exatos com esses critérios...*\n\n"
        response += "Mas não desista! Posso ajudar de outras formas:\n\n"
        response += "🔍 *Sugestões:*\n"
        response += "• Experimente critérios mais amplos\n"
        response += "• Procure em bairros próximos\n"
        response += "• Considere imóveis similares\n\n"
        response += "💡 *Ou posso:*\n"
        response += "• Cadastrar sua busca personalizada\n"
        response += "• Avisar quando chegarem novos imóveis\n"
        response += "• Conectar você com nossos especialistas\n\n"
        response += self._add_contact_info()
        return response

    def _add_contact_info(self) -> str:
        """Adiciona informações de contato à resposta"""
        return (
            f"📞 *Contatos Allega Imóveis:*\n"
            f"🏠 Vendas: {self.company_info['phone_sales']}\n"
            f"🏡 Locação: {self.company_info['phone_rental']}\n"
            f"📧 {self.company_info['email']}\n"
            f"🌐 {self.company_info['website']}\n\n"
            f"_CRECI {self.company_info['creci']} - Profissionais Certificados_"
        )

    async def process_property_inquiry(self, message: str, user_id: str) -> str:
        """Processa consulta sobre imóveis usando Groq e o índice inteligente"""
        try:
            await self.load_property_data()
            criteria = self.extract_search_criteria(message)
            logger.info(f"Busca de imóveis - User: {user_id}, Critérios: {criteria}")

            properties = self.search_properties(criteria)
            await self.firebase_service.save_property_search(user_id, criteria, len(properties))
            response = self.format_property_response(properties, criteria)

            # Chama Groq para enriquecer a resposta
            groq_response = await self._call_groq_property_assistant(message, criteria, properties[:2])
            if groq_response:
                response += f"\n\n🤖 *Dica da Sofia:*\n{groq_response}"

            return response

        except Exception as e:
            logger.error(f"Erro ao processar consulta de imóveis: {str(e)}")
            return (
                "😅 Ops! Tive um probleminha ao buscar os imóveis.\n\n"
                "Mas você pode entrar em contato direto:\n\n"
                f"📞 Vendas: {self.company_info['phone_sales']}\n"
                f"📞 Locação: {self.company_info['phone_rental']}\n\n"
                "Nossos especialistas vão te ajudar! 😊"
            )

    async def _call_groq_property_assistant(self, message: str, criteria: Dict[str, Any], properties: List[Dict[str, Any]]) -> Optional[str]:
        """Chama Groq para gerar dica ou resumo inteligente"""
        if not self.groq_api_key:
            return None

        system_prompt = (
            "Você é a Sofia, assistente virtual da Allega Imóveis. "
            "Forneça dicas úteis, sugestões ou peça mais detalhes para ajudar o usuário a encontrar o imóvel ideal. "
            "Seja amigável, profissional e objetiva. Máximo 200 caracteres."
        )

        user_prompt = (
            f"Usuário perguntou: \"{message}\"\n"
            f"Critérios extraídos: {json.dumps(criteria, ensure_ascii=False)}\n"
            f"Imóveis encontrados: {len(properties)} resultados\n"
            "Dê uma dica útil ou sugestão para ajudar na busca."
        )

        try:
            payload = {
                "model": self.text_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.3
            }

            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions", 
                    json=payload, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        content = result["choices"][0]["message"]["content"].strip()
                        return content[:250] if len(content) > 250 else content
                    else:
                        logger.error(f"Groq API error: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Erro ao chamar Groq: {str(e)}")
            return None

    def get_market_insights(self) -> str:
        """Retorna insights do mercado baseado nos dados"""
        if not self.property_cache or 'statistics' not in self.property_cache:
            return "📊 Dados de mercado em atualização..."

        stats = self.property_cache['statistics']

        response = "📊 *Insights do Mercado Imobiliário*\n\n"
        response += f"🏠 *Total de imóveis:* {stats.get('total_properties', 0)}\n\n"

        if 'by_type' in stats:
            response += "*Tipos mais procurados:*\n"
            for prop_type, count in sorted(stats['by_type'].items(),
                                         key=lambda x: x[1], reverse=True)[:3]:
                response += f"• {prop_type.title()}: {count} imóveis\n"
            response += "\n"

        if 'by_transaction' in stats:
            response += "*Modalidades:*\n"
            for trans_type, count in stats['by_transaction'].items():
                response += f"• {trans_type.title()}: {count} imóveis\n"
            response += "\n"

        response += "💡 *Dica:* Entre em contato para uma análise personalizada do mercado!\n\n"
        response += self._add_contact_info()

        return response

    async def update_property_data(self, new_data: Dict[str, Any]) -> bool:
        """Atualiza dados de imóveis no sistema"""
        try:
            success = await self.firebase_service.save_property_data(new_data)
            if success:
                self.property_cache = new_data
                self.last_cache_update = datetime.now()
                logger.info("Dados de imóveis atualizados com sucesso")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar dados de imóveis: {str(e)}")
            return False

    def is_property_related(self, message: str) -> bool:
        """Verifica se a mensagem é relacionada a imóveis"""
        property_keywords = [
            'apartamento', 'casa', 'imóvel', 'imovel', 'comprar', 'vender',
            'alugar', 'aluguel', 'locação', 'locacao', 'venda', 'terreno',
            'sobrado', 'cobertura', 'quarto', 'dormitório', 'garagem',
            'curitiba', 'bigorrilho', 'champagnat', 'batel', 'água verde',
            'preço', 'preco', 'financiamento', 'fgts', 'investimento'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in property_keywords)

    async def get_property_recommendations(self, user_preferences: Dict[str, Any]) -> str:
        """Gera recomendações personalizadas usando Groq"""
        if not self.groq_api_key:
            return self._get_fallback_recommendations()

        system_prompt = (
            "Você é a Sofia da Allega Imóveis. "
            "Com base nas preferências do usuário, sugira tipos de imóveis e bairros em Curitiba. "
            "Seja específica e útil. Máximo 300 caracteres."
        )

        user_prompt = f"Preferências do usuário: {json.dumps(user_preferences, ensure_ascii=False)}"

        try:
            payload = {
                "model": self.text_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 400,
                "temperature": 0.4
            }

            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions", 
                    json=payload, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        content = result["choices"][0]["message"]["content"].strip()
                        return f"💡 *Recomendações da Sofia:*\n{content}\n\n{self._add_contact_info()}"
                    else:
                        return self._get_fallback_recommendations()
        except Exception as e:
            logger.error(f"Erro ao gerar recomendações: {str(e)}")
            return self._get_fallback_recommendations()

    def _get_fallback_recommendations(self) -> str:
        """Recomendações padrão quando Groq não está disponível"""
        return (
            "💡 *Recomendações da Allega Imóveis:*\n\n"
            "🏠 Para famílias: Casas no Champagnat ou Batel\n"
            "🏢 Para investimento: Apartamentos no Centro\n"
            "🌳 Para tranquilidade: Bigorrilho ou Água Verde\n\n"
            f"{self._add_contact_info()}"
        )

property_intelligence = PropertyIntelligenceService()
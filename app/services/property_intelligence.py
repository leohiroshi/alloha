"""
Serviço de Inteligência Imobiliária
Integra dados de imóveis com a IA LLaMA 3.1 para respostas inteligentes
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
import aiohttp
from llama_index import GPTVectorStoreIndex

from .firebase_service import FirebaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyIntelligenceService:
    """Serviço que combina LLaMA 3.1 com dados imobiliários"""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:1b"):
        self.firebase_service = FirebaseService()
        self.ollama_url = ollama_url
        self.model = model
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
                }
            ],
            'statistics': {
                'total_properties': 3,
                'by_type': {'apartamento': 2, 'casa': 1},
                'by_transaction': {'venda': 2, 'locacao': 1},
                'by_city': {'Curitiba': 3}
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

        locations = ['bigorrilho', 'champagnat', 'centro', 'água verde', 'batel', 'cabral']
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

    @property
    def property_index(self) -> Optional[GPTVectorStoreIndex]:
        """Retorna o índice de busca inteligente dos imóveis, se existir."""
        try:
            index = GPTVectorStoreIndex.load_from_disk("property_index.json")
            return index
        except Exception as e:
            logger.error(f"Erro ao carregar o índice de imóveis: {str(e)}")
            return None

    def query_property_index(self, query: str) -> Optional[str]:
        """Consulta o índice inteligente de imóveis usando LlamaIndex."""
        index = self.property_index
        if not index:
            return None
        try:
            response = index.query(query)
            return str(response)
        except Exception as e:
            logger.error(f"Erro ao consultar o índice de imóveis: {str(e)}")
            return None

    async def process_property_inquiry(self, message: str, user_id: str) -> str:
        """Processa consulta sobre imóveis usando LLaMA 3.1 e o índice inteligente"""
        try:
            await self.load_property_data()
            criteria = self.extract_search_criteria(message)
            logger.info(f"Busca de imóveis - User: {user_id}, Critérios: {criteria}")

            # Consulta o índice inteligente primeiro
            index_response = self.query_property_index(message)
            if index_response:
                response = f"🔎 *Busca inteligente de imóveis:*\n{index_response}\n\n"
            else:
                properties = self.search_properties(criteria)
                await self.firebase_service.save_property_search(user_id, criteria, len(properties))
                response = self.format_property_response(properties, criteria)

            # Chama LLaMA 3.1 para enriquecer a resposta
            llama_response = await self._call_llama_property_assistant(message, criteria, [])
            if llama_response:
                response += f"\n\n🤖 *Dica da IA:*\n{llama_response}"

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

    async def _call_llama_property_assistant(self, message: str, criteria: Dict[str, Any], properties: List[Dict[str, Any]]) -> Optional[str]:
        """Chama LLaMA 3.1 para gerar dica ou resumo inteligente"""
        prompt = (
            "Você é o assistente virtual da Allega Imóveis. "
            "O usuário enviou a seguinte mensagem sobre busca de imóveis:\n"
            f"\"{message}\"\n"
            f"Critérios extraídos: {json.dumps(criteria, ensure_ascii=False)}\n"
            f"Imóveis encontrados: {json.dumps(properties[:2], ensure_ascii=False)}\n"
            "Responda de forma amigável, profissional e objetiva. "
            "Se possível, ofereça dicas, sugestões ou peça mais detalhes para ajudar o usuário a encontrar o imóvel ideal."
        )
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": prompt
            }]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ollama_url}/api/chat", json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    text = await resp.text()
                    logger.info(f"LLaMA 3.1 resposta: status={resp.status}, body={text[:200]}")
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Erro ao chamar LLaMA 3.1: {str(e)}")
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
            'curitiba', 'bigorrilho', 'champagnat', 'preço', 'preco',
            'financiamento', 'fgts', 'investimento'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in property_keywords)

property_intelligence = PropertyIntelligenceService()

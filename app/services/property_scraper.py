"""
Sistema de Extração Inteligente de Imóveis
Executa o scraper a cada 30 minutos, compara imóveis do site com Firebase,
adiciona, remove ou atualiza imóveis conforme necessário.
Integrado com Groq para análise inteligente de dados.
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urljoin
import json
import os
from datetime import datetime
from app.services.firebase_service import FirebaseService
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AllegaPropertyScraper:
    """Extrator de imóveis do site Allega Imóveis com análise inteligente via Groq"""
    
    def __init__(self):
        self.base_url = "https://www.allegaimoveis.com"
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.text_model = "llama-3.1-8b-instant"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Tipos de imóveis disponíveis
        self.property_types = [
            'apartamento', 'casa', 'cobertura', 'conjunto-sala-comercial',
            'loft', 'loja', 'residencia-em-condominio', 'sobrado',
            'sobrado-em-condominio', 'studio', 'terreno', 'terreno-em-condominio'
        ]
        
        # Cidades principais
        self.cities = ['curitiba', 'itapema']
        
        # Tipos de transação
        self.transaction_types = ['venda', 'locacao', 'lancamento']
    
    async def enhance_property_with_groq(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquece dados do imóvel usando análise inteligente do Groq"""
        if not self.groq_api_key or not property_data.get('description'):
            return property_data

        system_prompt = (
            "Você é um especialista em análise de imóveis. "
            "Analise a descrição do imóvel e extraia informações úteis como: "
            "pontos positivos, localização estratégica, público-alvo ideal, "
            "potencial de valorização. Seja conciso e objetivo."
        )

        user_prompt = (
            f"Analise este imóvel:\n"
            f"Título: {property_data.get('title', '')}\n"
            f"Tipo: {property_data.get('property_type', '')}\n"
            f"Bairro: {property_data.get('neighborhood', '')}\n"
            f"Descrição: {property_data.get('description', '')[:500]}\n"
            f"Características: {', '.join(property_data.get('features', [])[:5])}\n"
            "Forneça uma análise profissional em até 200 caracteres."
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
                        analysis = result["choices"][0]["message"]["content"].strip()
                        property_data['ai_analysis'] = analysis[:250]
                        property_data['ai_enhanced'] = True
                        logger.info(f"Análise IA adicionada para: {property_data.get('title', '')[:30]}...")
                    elif resp.status == 429:
                        logger.warning("Groq API rate limit reached. Waiting 10 seconds before retrying...")
                        await asyncio.sleep(10)
                        # Opcional: tente novamente (recursivo ou com contador de tentativas)
                    else:
                        logger.warning(f"Groq API error: {resp.status}")
        except Exception as e:
            logger.error(f"Erro ao analisar imóvel com Groq: {str(e)}")
        
        return property_data

    async def generate_market_insights(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera insights de mercado usando Groq"""
        if not self.groq_api_key or not properties:
            return self._get_fallback_insights(properties)

        # Preparar dados para análise
        summary_data = {
            'total_properties': len(properties),
            'by_type': {},
            'by_neighborhood': {},
            'price_ranges': [],
            'common_features': []
        }

        for prop in properties:
            # Tipos
            prop_type = prop.get('property_type', 'unknown')
            summary_data['by_type'][prop_type] = summary_data['by_type'].get(prop_type, 0) + 1
            
            # Bairros
            neighborhood = prop.get('neighborhood', '').strip()
            if neighborhood:
                summary_data['by_neighborhood'][neighborhood] = summary_data['by_neighborhood'].get(neighborhood, 0) + 1
            
            # Características
            summary_data['common_features'].extend(prop.get('features', []))

        system_prompt = (
            "Você é um analista do mercado imobiliário de Curitiba. "
            "Com base nos dados fornecidos, gere insights sobre tendências, "
            "bairros em alta, tipos de imóveis mais procurados. "
            "Seja profissional e específico. Máximo 400 caracteres."
        )

        user_prompt = f"Dados do mercado: {json.dumps(summary_data, ensure_ascii=False)[:1000]}"

        try:
            payload = {
                "model": self.text_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 500,
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
                        insights = result["choices"][0]["message"]["content"].strip()
                        return {
                            'ai_insights': insights,
                            'generated_at': datetime.now().isoformat(),
                            'data_summary': summary_data
                        }
        except Exception as e:
            logger.error(f"Erro ao gerar insights: {str(e)}")
        
        return self._get_fallback_insights(properties)

    def _get_fallback_insights(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insights padrão quando Groq não está disponível"""
        total = len(properties)
        by_type = {}
        by_neighborhood = {}
        
        for prop in properties:
            prop_type = prop.get('property_type', 'unknown')
            by_type[prop_type] = by_type.get(prop_type, 0) + 1
            
            neighborhood = prop.get('neighborhood', '').strip()
            if neighborhood:
                by_neighborhood[neighborhood] = by_neighborhood.get(neighborhood, 0) + 1

        top_type = max(by_type.items(), key=lambda x: x[1])[0] if by_type else 'apartamento'
        top_neighborhood = max(by_neighborhood.items(), key=lambda x: x[1])[0] if by_neighborhood else 'Centro'

        return {
            'ai_insights': f"Mercado com {total} imóveis. Destaque para {top_type}s no {top_neighborhood}. Boa diversidade de opções.",
            'generated_at': datetime.now().isoformat(),
            'data_summary': {
                'total_properties': total,
                'by_type': by_type,
                'by_neighborhood': by_neighborhood
            }
        }
    
    async def extract_property_details(self, property_url: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """Extrai detalhes de um imóvel específico, garantindo todos os campos principais"""
        try:
            async with session.get(property_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"Erro ao acessar {property_url}: Status {response.status}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Padronização dos campos principais
                property_data = {
                    'reference': '',  # Referência
                    'title': '',      # Título
                    'description': '',# Descrição detalhada
                    'address': '',    # Endereço
                    'neighborhood': '',# Bairro
                    'city': '',       # Município
                    'uf': '',         # UF
                    'immediations': '',# Imediações
                    'area_private': '',# Área privativa
                    'area_terreno': '',# Área terreno
                    'measures': '',   # Medidas
                    'topography': '', # Topografia
                    'face_property': '',# Face do imóvel
                    'face_apartment': '',# Face do apartamento
                    'testada': '',    # Testada
                    'usage_type': '', # Tipo de uso
                    'bedrooms': 0,    # Dormitórios
                    'suites': 0,      # Suítes
                    'bathrooms': 0,   # Banheiros
                    'living_rooms': 0,# Salas
                    'parking_spaces': 0,# Vagas de Garagens
                    'conservation_state': '',# Estado de conservação
                    'year_built': '', # Ano de construção
                    'occupation': '', # Ocupação
                    'rent_gross': '', # Aluguel Bruto
                    'bonus': '',      # Bonificação
                    'rent_net': '',   # Aluguel Líquido
                    'iptu': '',       # IPTU
                    'iptu_period': '',# IPTU período
                    'composition': [],# Composição (lista de cômodos e diferenciais)
                    'features': [],   # Diferenciais
                    'images': [],     # Imagens
                    'contact_info': {},# Contato
                    'scraped_at': datetime.now().isoformat(),
                    'url': property_url,
                    'transaction_type': 'venda',
                    'type': '',
                    'ai_analysis': '', # Análise da IA
                    'ai_enhanced': False, # Flag se foi analisado pela IA
                }

                # Título
                title_elem = soup.find('h1') or soup.find('title')
                if title_elem:
                    property_data['title'] = title_elem.get_text(strip=True)

                # Referência
                ref_match = re.search(r'Refer[êe]ncia[:\s]*([A-Z0-9-]+)', html, re.IGNORECASE)
                if ref_match:
                    property_data['reference'] = ref_match.group(1)

                # Endereço
                address_match = re.search(r'Endere[çc]o[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if address_match:
                    property_data['address'] = address_match.group(1).strip()

                # Bairro
                bairro_match = re.search(r'Bairro[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if bairro_match:
                    property_data['neighborhood'] = bairro_match.group(1).strip()

                # Município
                municipio_match = re.search(r'Município[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if municipio_match:
                    property_data['city'] = municipio_match.group(1).strip()

                # UF
                uf_match = re.search(r'UF[:\s]*([A-Z]{2})', html, re.IGNORECASE)
                if uf_match:
                    property_data['uf'] = uf_match.group(1).strip()

                # Imediações
                imedia_match = re.search(r'Imedia[çc][õo]es?[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if imedia_match:
                    property_data['immediations'] = imedia_match.group(1).strip()

                # Área privativa
                area_priv_match = re.search(r'Área privativa[:\s]*([\d.,]+)\s*m²', html, re.IGNORECASE)
                if area_priv_match:
                    property_data['area_private'] = area_priv_match.group(1).replace(',', '.') + ' m²'

                # Área terreno
                area_terreno_match = re.search(r'Área terreno[:\s]*([\d.,]+)\s*m²', html, re.IGNORECASE)
                if area_terreno_match:
                    property_data['area_terreno'] = area_terreno_match.group(1).replace(',', '.') + ' m²'

                # Medidas
                medidas_match = re.search(r'Medidas[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if medidas_match:
                    property_data['measures'] = medidas_match.group(1).strip()

                # Topografia
                topo_match = re.search(r'Topografia[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if topo_match:
                    property_data['topography'] = topo_match.group(1).strip()

                # Face do imóvel
                face_imovel_match = re.search(r'Face do imóvel[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if face_imovel_match:
                    property_data['face_property'] = face_imovel_match.group(1).strip()

                # Face do apartamento
                face_ap_match = re.search(r'Face do apartamento[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if face_ap_match:
                    property_data['face_apartment'] = face_ap_match.group(1).strip()

                # Testada
                testada_match = re.search(r'Testada[:\s]*([\d.,]+)', html, re.IGNORECASE)
                if testada_match:
                    property_data['testada'] = testada_match.group(1).strip()

                # Tipo de uso
                tipo_uso_match = re.search(r'Tipo de uso[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if tipo_uso_match:
                    property_data['usage_type'] = tipo_uso_match.group(1).strip()

                # Dormitórios
                dorm_match = re.search(r'Dormit[óo]rios?[:\s]*([\d]+)', html, re.IGNORECASE)
                if dorm_match:
                    property_data['bedrooms'] = int(dorm_match.group(1))

                # Suítes
                suite_match = re.search(r'Su[íi]tes?[:\s]*([\d]+)', html, re.IGNORECASE)
                if suite_match:
                    property_data['suites'] = int(suite_match.group(1))

                # Banheiros
                banh_match = re.search(r'Banheiros?[:\s]*([\d]+)', html, re.IGNORECASE)
                if banh_match:
                    property_data['bathrooms'] = int(banh_match.group(1))

                # Salas
                sala_match = re.search(r'Salas?[:\s]*([\d]+)', html, re.IGNORECASE)
                if sala_match:
                    property_data['living_rooms'] = int(sala_match.group(1))

                # Vagas de Garagens
                vagas_match = re.search(r'Vagas de Garagens?[:\s]*([\d]+)', html, re.IGNORECASE)
                if vagas_match:
                    property_data['parking_spaces'] = int(vagas_match.group(1))

                # Estado de conservação
                estado_match = re.search(r'Estado de conservação[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if estado_match:
                    property_data['conservation_state'] = estado_match.group(1).strip()

                # Ano de construção
                ano_match = re.search(r'Ano de construção[:\s]*([\d]{4})', html, re.IGNORECASE)
                if ano_match:
                    property_data['year_built'] = ano_match.group(1)

                # Ocupação
                ocupacao_match = re.search(r'Ocupação[:\s]*([^\n\r]+)', html, re.IGNORECASE)
                if ocupacao_match:
                    property_data['occupation'] = ocupacao_match.group(1).strip()

                # Aluguel Bruto
                aluguel_bruto_match = re.search(r'Aluguel Bruto[:\s]*R?\$?\s*([\d.,]+)', html, re.IGNORECASE)
                if aluguel_bruto_match:
                    property_data['rent_gross'] = aluguel_bruto_match.group(1)

                # Bonificação
                bonificacao_match = re.search(r'Bonifica[çc][ãa]o[:\s]*R?\$?\s*([\d.,]+)', html, re.IGNORECASE)
                if bonificacao_match:
                    property_data['bonus'] = bonificacao_match.group(1)

                # Aluguel Líquido
                aluguel_liquido_match = re.search(r'Aluguel Líquido[:\s]*R?\$?\s*([\d.,]+)', html, re.IGNORECASE)
                if aluguel_liquido_match:
                    property_data['rent_net'] = aluguel_liquido_match.group(1)

                # IPTU
                iptu_match = re.search(r'IPTU[:\s]*R?\$?\s*([\d.,]+)', html, re.IGNORECASE)
                if iptu_match:
                    property_data['iptu'] = iptu_match.group(1)

                # IPTU período
                iptu_period_match = re.search(r'IPTU.*?(mensal|anual)', html, re.IGNORECASE)
                if iptu_period_match:
                    property_data['iptu_period'] = iptu_period_match.group(1)

                # Descrição detalhada
                desc_elem = soup.find('div', class_=re.compile(r'descri.*|detail.*|info.*'))
                if desc_elem:
                    property_data['description'] = desc_elem.get_text(strip=True)[:1000]
                else:
                    # fallback: pega o primeiro parágrafo relevante
                    p_elem = soup.find('p')
                    if p_elem:
                        property_data['description'] = p_elem.get_text(strip=True)[:1000]

                # Composição e diferenciais (busca por listas ou marcadores)
                composition = []
                features = []
                for ul in soup.find_all('ul'):
                    for li in ul.find_all('li'):
                        text = li.get_text(strip=True)
                        if text:
                            composition.append(text)
                # Adiciona diferenciais conhecidos
                diff_keywords = [
                    'Amplo quintal', 'Closet Sr. e Sra.', 'Suíte Master com varanda', 'Ar condicionado',
                    'Hidromassagem', 'Lareira', 'Piscina', 'Churrasqueira a carvão', 'Despensa',
                    'Lavanderia', 'Jardim', 'Área de lazer', 'Mobiliado', 'Próximo ao metrô',
                    'Academia', 'Salão de festas', 'Playground', 'Portaria 24h', 'Elevador'
                ]
                for kw in diff_keywords:
                    if kw.lower() in html.lower():
                        features.append(kw)
                property_data['composition'] = composition
                property_data['features'] = list(set(features + composition))

                # Imagens
                img_elements = soup.find_all('img')
                for img in img_elements:
                    img_src = img.get('src') or img.get('data-src')
                    if img_src and ('imovel' in img_src or 'property' in img_src or 'foto' in img_src):
                        full_url = urljoin(self.base_url, img_src)
                        if full_url not in property_data['images']:
                            property_data['images'].append(full_url)

                # Contato (dados fixos da Allega)
                property_data['contact_info'] = {
                    'phone_sales': '(41) 99214-6670',
                    'phone_rental': '(41) 99223-0874',
                    'phone_fixed': '(41) 3285-1383',
                    'email': 'contato@allegaimoveis.com',
                    'address': 'Rua Gastão Câmara, 135 - Bigorrilho, Curitiba - PR'
                }

                # Enriquecer com análise da IA
                property_data = await self.enhance_property_with_groq(property_data)

                logger.info(f"Imóvel extraído: {property_data['title'][:50]}... Referência: {property_data['reference']}")
                return property_data

        except Exception as e:
            logger.error(f"Erro ao extrair detalhes do imóvel {property_url}: {str(e)}")
            return None
    
    async def extract_property_links(self, listing_url: str, session: aiohttp.ClientSession) -> List[str]:
        """Extrai links de imóveis de uma página de listagem"""
        try:
            async with session.get(listing_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"Erro ao acessar {listing_url}: Status {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                property_links = []
                
                # Buscar links de imóveis
                link_patterns = [
                    soup.find_all('a', href=re.compile(r'/imovel/')),
                    soup.find_all('a', href=re.compile(r'/venda/')),
                    soup.find_all('a', href=re.compile(r'/locacao/')),
                ]
                
                for pattern in link_patterns:
                    for link in pattern:
                        href = link.get('href')
                        if href and '/imovel/' in href:
                            full_url = urljoin(self.base_url, href)
                            if full_url not in property_links:
                                property_links.append(full_url)
                
                logger.info(f"Encontrados {len(property_links)} links de imóveis em {listing_url}")
                return property_links
                
        except Exception as e:
            logger.error(f"Erro ao extrair links de {listing_url}: {str(e)}")
            return []
    
    async def scrape_properties_by_type(self, property_type: str, transaction_type: str = 'venda', 
                                      city: str = 'curitiba', max_properties: int = 50) -> List[Dict[str, Any]]:
        """Extrai imóveis por tipo específico"""
        
        listing_urls = [
            f"{self.base_url}/imoveis/{transaction_type}/{property_type}/{city}",
            f"{self.base_url}/imoveis/{transaction_type}/{property_type}",
            f"{self.base_url}/cidades/{transaction_type}/{property_type}"
        ]
        
        all_properties = []
        
        async with aiohttp.ClientSession() as session:
            # Primeiro, obter todos os links de imóveis
            all_property_links = []
            
            for listing_url in listing_urls:
                links = await self.extract_property_links(listing_url, session)
                all_property_links.extend(links)
            
            # Remover duplicatas
            unique_links = list(set(all_property_links))[:max_properties]
            
            logger.info(f"Iniciando extração de {len(unique_links)} imóveis do tipo {property_type}")
            
            # Extrair detalhes de cada imóvel
            semaphore = asyncio.Semaphore(3)  # Reduzido para 3 para não sobrecarregar
            
            async def extract_with_semaphore(url):
                async with semaphore:
                    return await self.extract_property_details(url, session)
            
            tasks = [extract_with_semaphore(url) for url in unique_links]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and result:
                    result['property_type'] = property_type
                    result['transaction_type'] = transaction_type
                    all_properties.append(result)
        
        logger.info(f"Extraídos {len(all_properties)} imóveis do tipo {property_type}")
        return all_properties
    
    async def scrape_all_properties(self, max_per_type: int = 20) -> List[Dict[str, Any]]:
        """Extrai imóveis de todos os tipos"""
        all_properties = []
        
        # Focar nos tipos mais comuns primeiro
        priority_types = ['apartamento', 'casa', 'sobrado', 'terreno']
        
        for transaction_type in ['venda', 'locacao']:
            for property_type in priority_types:
                try:
                    properties = await self.scrape_properties_by_type(
                        property_type=property_type,
                        transaction_type=transaction_type,
                        max_properties=max_per_type
                    )
                    all_properties.extend(properties)
                    
                    # Aguardar um pouco entre os tipos para não sobrecarregar o servidor
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Erro ao extrair {property_type} para {transaction_type}: {str(e)}")
                    continue
        
        logger.info(f"Extração completa: {len(all_properties)} imóveis encontrados")
        return all_properties
    
    def save_properties_to_file(self, properties: List[Dict[str, Any]], filename: str = None):
        """Salva os imóveis em arquivo JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"properties_allega_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(properties, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Dados salvos em {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo: {str(e)}")
            return None
    
    async def format_for_ai_training(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Formata os dados para treinamento da IA com insights do Groq"""
        
        # Estatísticas gerais
        stats = {
            'total_properties': len(properties),
            'by_type': {},
            'by_transaction': {},
            'by_city': {},
            'price_ranges': {
                'under_300k': 0,
                '300k_to_500k': 0,
                '500k_to_1m': 0,
                'above_1m': 0
            },
            'bedroom_distribution': {},
            'common_neighborhoods': {},
            'ai_enhanced_count': 0
        }
        
        for prop in properties:
            # Por tipo
            prop_type = prop.get('property_type', 'unknown')
            stats['by_type'][prop_type] = stats['by_type'].get(prop_type, 0) + 1
            
            # Por transação
            trans_type = prop.get('transaction_type', 'unknown')
            stats['by_transaction'][trans_type] = stats['by_transaction'].get(trans_type, 0) + 1
            
            # Por cidade
            city = prop.get('city', 'unknown')
            stats['by_city'][city] = stats['by_city'].get(city, 0) + 1
            
            # Distribuição de quartos
            bedrooms = prop.get('bedrooms', 0)
            stats['bedroom_distribution'][bedrooms] = stats['bedroom_distribution'].get(bedrooms, 0) + 1
            
            # Bairros comuns
            neighborhood = prop.get('neighborhood', '').strip()
            if neighborhood:
                stats['common_neighborhoods'][neighborhood] = stats['common_neighborhoods'].get(neighborhood, 0) + 1
            
            # Contagem de análises IA
            if prop.get('ai_enhanced'):
                stats['ai_enhanced_count'] += 1
        
        # Gerar insights de mercado usando Groq
        market_insights = await self.generate_market_insights(properties)
        
        # Criar base de conhecimento para IA
        knowledge_base = {
            'company_info': {
                'name': 'Allega Imóveis',
                'creci': '6684 J',
                'address': 'Rua Gastão Câmara, 135 - Bigorrilho, Curitiba - PR',
                'phone_sales': '(41) 99214-6670',
                'phone_rental': '(41) 99223-0874',
                'phone_fixed': '(41) 3285-1383',
                'email': 'contato@allegaimoveis.com',
                'website': 'https://www.allegaimoveis.com'
            },
            'property_types': list(stats['by_type'].keys()),
            'cities_served': list(stats['by_city'].keys()),
            'common_neighborhoods': dict(sorted(stats['common_neighborhoods'].items(), 
                                               key=lambda x: x[1], reverse=True)[:10]),
            'statistics': stats,
            'market_insights': market_insights,
            'sample_properties': properties[:10],  # Amostras para referência
            'ai_enhanced_properties': [p for p in properties if p.get('ai_enhanced')][:5],
            'last_updated': datetime.now().isoformat()
        }
        
        return knowledge_base


async def monitor_scraper(interval_minutes: int = 30, max_properties: int = 100):
    """Executa o scraper periodicamente e sincroniza com Firebase."""
    scraper = AllegaPropertyScraper()
    firebase = FirebaseService()
    interval = interval_minutes * 60  # segundos

    while True:
        logger.info(f"[{datetime.now()}] Iniciando verificação de imóveis...")
        try:
            # Extrai imóveis do site
            scraped_properties = await scraper.scrape_all_properties(max_per_type=max_properties // 4)
            scraped_dict = {p['reference']: p for p in scraped_properties if p.get('reference')}

            # Busca imóveis do Firebase
            firebase_properties = await firebase.get_property_data()
            firebase_dict = {p['reference']: p for p in firebase_properties if p.get('reference')}

            # Detecta imóveis novos
            new_refs = set(scraped_dict.keys()) - set(firebase_dict.keys())
            new_properties = [scraped_dict[ref] for ref in new_refs]

            # Detecta imóveis removidos
            removed_refs = set(firebase_dict.keys()) - set(scraped_dict.keys())
            removed_properties = [firebase_dict[ref] for ref in removed_refs]

            # Detecta imóveis atualizados
            updated_properties = []
            for ref in set(scraped_dict.keys()) & set(firebase_dict.keys()):
                if scraped_dict[ref] != firebase_dict[ref]:
                    updated_properties.append(scraped_dict[ref])

            # Atualiza Firebase
            if new_properties:
                logger.info(f"Adicionando {len(new_properties)} novos imóveis ao Firebase")
                await firebase.add_properties(new_properties)
            if removed_properties:
                logger.info(f"Removendo {len(removed_properties)} imóveis do Firebase")
                await firebase.remove_properties([p['reference'] for p in removed_properties])
            if updated_properties:
                logger.info(f"Atualizando {len(updated_properties)} imóveis no Firebase")
                await firebase.update_properties(updated_properties)

            # Gerar insights de mercado
            if scraped_properties:
                insights = await scraper.generate_market_insights(scraped_properties)
                logger.info(f"Insights de mercado: {insights.get('ai_insights', 'N/A')[:100]}...")

        except Exception as e:
            logger.error(f"Erro durante monitoramento: {str(e)}")

        logger.info("Verificação concluída. Aguardando próxima execução...")
        await asyncio.sleep(interval)


# Função principal para uso externo
async def scrape_allega_properties(max_properties: int = 100) -> Dict[str, Any]:
    """Função principal para extrair imóveis da Allega com análise inteligente"""
    scraper = AllegaPropertyScraper()
    
    logger.info("Iniciando extração de imóveis da Allega Imóveis com análise IA...")
    
    # Extrair imóveis
    properties = await scraper.scrape_all_properties(max_per_type=max_properties // 4)
    
    if not properties:
        logger.warning("Nenhum imóvel foi extraído")
        return {}
    
    # Salvar dados brutos
    filename = scraper.save_properties_to_file(properties)
    knowledge_base = await scraper.format_for_ai_training(properties)

    # Cria o índice para busca rápida
    if filename:
        data_folder = os.path.dirname(filename) or "."

    ai_enhanced_count = sum(1 for p in properties if p.get('ai_enhanced'))
    logger.info(f"Extração concluída: {len(properties)} imóveis processados, {ai_enhanced_count} com análise IA")
    
    return {
        'properties': properties,
        'knowledge_base': knowledge_base,
        'filename': filename,
        'ai_enhanced_count': ai_enhanced_count,
        'market_insights': knowledge_base.get('market_insights', {})
    }


if __name__ == "__main__":
    # Executa o monitoramento contínuo
    asyncio.run(monitor_scraper(interval_minutes=30, max_properties=100))
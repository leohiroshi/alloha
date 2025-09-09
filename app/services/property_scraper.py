"""
Sistema de Extração Inteligente de Imóveis
Extrai dados de propriedades do site Allega Imóveis para treinar a IA
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AllegaPropertyScraper:
    """Extrator de imóveis do site Allega Imóveis"""
    
    def __init__(self):
        self.base_url = "https://www.allegaimoveis.com"
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
    
    async def extract_property_details(self, property_url: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """Extrai detalhes de um imóvel específico"""
        try:
            async with session.get(property_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"Erro ao acessar {property_url}: Status {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                property_data = {
                    'url': property_url,
                    'scraped_at': datetime.now().isoformat(),
                    'title': '',
                    'price': '',
                    'bedrooms': 0,
                    'bathrooms': 0,
                    'parking_spaces': 0,
                    'area_private': '',
                    'area_total': '',
                    'neighborhood': '',
                    'city': '',
                    'description': '',
                    'features': [],
                    'images': [],
                    'contact_info': {},
                    'reference': '',
                    'type': '',
                    'transaction_type': 'venda'
                }
                
                # Extrair título
                title_elem = soup.find('h1') or soup.find('title')
                if title_elem:
                    property_data['title'] = title_elem.get_text(strip=True)
                
                # Extrair preço
                price_patterns = [
                    r'R\$\s*[\d.,]+',
                    r'[\d.,]+\s*reais?',
                    r'valor.*?[\d.,]+'
                ]
                
                for pattern in price_patterns:
                    price_match = re.search(pattern, html, re.IGNORECASE)
                    if price_match:
                        property_data['price'] = price_match.group()
                        break
                
                # Extrair características (quartos, banheiros, vagas)
                characteristics_text = soup.get_text()
                
                # Quartos
                bedroom_match = re.search(r'(\d+)\s*(?:dorm|quarto|dormitório)', characteristics_text, re.IGNORECASE)
                if bedroom_match:
                    property_data['bedrooms'] = int(bedroom_match.group(1))
                
                # Banheiros
                bathroom_match = re.search(r'(\d+)\s*(?:banh|banheiro)', characteristics_text, re.IGNORECASE)
                if bathroom_match:
                    property_data['bathrooms'] = int(bathroom_match.group(1))
                
                # Vagas
                parking_match = re.search(r'(\d+)\s*(?:vaga|garagem)', characteristics_text, re.IGNORECASE)
                if parking_match:
                    property_data['parking_spaces'] = int(parking_match.group(1))
                
                # Área
                area_match = re.search(r'(\d+(?:,\d+)?)\s*m²', characteristics_text)
                if area_match:
                    property_data['area_total'] = area_match.group()
                
                # Bairro e cidade
                location_match = re.search(r'(?:bairro|região)?\s*([^,]+),?\s*(curitiba|itapema)', characteristics_text, re.IGNORECASE)
                if location_match:
                    property_data['neighborhood'] = location_match.group(1).strip()
                    property_data['city'] = location_match.group(2).strip()
                
                # Descrição
                description_elem = soup.find('div', class_=re.compile(r'descri.*|detail.*|info.*'))
                if description_elem:
                    property_data['description'] = description_elem.get_text(strip=True)[:500]
                
                # Imagens
                img_elements = soup.find_all('img')
                for img in img_elements:
                    img_src = img.get('src') or img.get('data-src')
                    if img_src and ('imovel' in img_src or 'property' in img_src or 'foto' in img_src):
                        full_url = urljoin(self.base_url, img_src)
                        property_data['images'].append(full_url)
                
                # Referência
                ref_match = re.search(r'ref(?:erência)?[:\s]*([A-Z0-9-]+)', html, re.IGNORECASE)
                if ref_match:
                    property_data['reference'] = ref_match.group(1)
                
                # Contato (números da Allega)
                property_data['contact_info'] = {
                    'phone_sales': '(41) 99214-6670',
                    'phone_rental': '(41) 99223-0874',
                    'phone_fixed': '(41) 3285-1383',
                    'email': 'contato@allegaimoveis.com',
                    'address': 'Rua Gastão Câmara, 135 - Bigorrilho, Curitiba - PR'
                }
                
                logger.info(f"Imóvel extraído: {property_data['title'][:50]}...")
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
            semaphore = asyncio.Semaphore(5)  # Limitar a 5 requisições simultâneas
            
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
                    await asyncio.sleep(2)
                    
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
    
    def format_for_ai_training(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Formata os dados para treinamento da IA"""
        
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
            'common_neighborhoods': {}
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
            'sample_properties': properties[:10],  # Amostras para referência
            'last_updated': datetime.now().isoformat()
        }
        
        return knowledge_base


# Função principal para uso externo
async def scrape_allega_properties(max_properties: int = 100) -> Dict[str, Any]:
    """Função principal para extrair imóveis da Allega"""
    scraper = AllegaPropertyScraper()
    
    logger.info("Iniciando extração de imóveis da Allega Imóveis...")
    
    # Extrair imóveis
    properties = await scraper.scrape_all_properties(max_per_type=max_properties // 4)
    
    if not properties:
        logger.warning("Nenhum imóvel foi extraído")
        return {}
    
    # Salvar dados brutos
    filename = scraper.save_properties_to_file(properties)
    
    # Formatar para IA
    knowledge_base = scraper.format_for_ai_training(properties)
    
    logger.info(f"Extração concluída: {len(properties)} imóveis processados")
    
    return {
        'properties': properties,
        'knowledge_base': knowledge_base,
        'filename': filename
    }


if __name__ == "__main__":
    # Teste do scraper
    async def main():
        result = await scrape_allega_properties(max_properties=50)
        print(f"Extraídos {len(result.get('properties', []))} imóveis")
        
        # Mostrar estatísticas
        kb = result.get('knowledge_base', {})
        if kb:
            stats = kb.get('statistics', {})
            print(f"\nEstatísticas:")
            print(f"- Total: {stats.get('total_properties', 0)} imóveis")
            print(f"- Tipos: {list(stats.get('by_type', {}).keys())}")
            print(f"- Cidades: {list(stats.get('by_city', {}).keys())}")
    
    asyncio.run(main())

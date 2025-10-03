"""
Sistema de Extração Inteligente de Imóveis
Executa o scraper a cada 30 minutos, compara imóveis do site com Supabase,
adiciona, remove ou atualiza imóveis conforme necessário.
Integrado com GPT/OpenAI para análise inteligente de dados e Selenium para renderização.
"""
import asyncio
import logging
import json
import os
import re
import tempfile
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from dotenv import load_dotenv
load_dotenv()

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Detect runtime inside container without full Chrome installed
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
CHROME_BINARY = os.getenv("CHROME_BINARY", "/usr/bin/chromium")


# internal services
from app.services.supabase_client import supabase_client
from app.services.rag_pipeline import rag
from app.services.intelligent_bot import intelligent_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AllegaPropertyScraper:
    """Extrator de imóveis do site Allega Imóveis usando Selenium + GPT/OpenAI"""

    def __init__(self, headless: bool = True):
        self.base_url = "https://www.allegaimoveis.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36'
        }
        self.property_types = [
            'apartamento', 'casa', 'cobertura', 'conjunto-sala-comercial',
            'loft', 'loja', 'residencia-em-condominio', 'sobrado',
            'sobrado-em-condominio', 'studio', 'terreno', 'terreno-em-condominio'
        ]
        self.cities = ['curitiba', 'itapema']
        self.transaction_types = ['venda', 'locacao', 'lancamento']

        # Selenium options
        self.headless = headless
        self._driver = None

        # GPT/OpenAI model
        self.openai_model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")

    # Supabase client já está disponível via import

    def _create_driver(self):
        """Cria driver Chromium/Chrome com fallback e logs claros.
        Estratégia:
        1) Se variável CHROME_BINARY existir (imagem com chromium instalado) usa binário local.
        2) Caso contrário tenta webdriver_manager (download) - pode falhar em runtime restrito.
        """
        opts = Options()
        if self.headless:
            # '--headless=new' para Chrome 109+, fallback se falhar
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--user-agent=" + self.headers['User-Agent'])

        # Se chromium já vem instalado via Docker (INSTALL_BROWSER=true)
        if os.path.exists(CHROME_BINARY):
            opts.binary_location = CHROME_BINARY
            # Usar chromedriver system se existir
            if os.path.exists(CHROMEDRIVER_PATH):
                service = ChromeService(CHROMEDRIVER_PATH)
                logger.info("Usando chromedriver de sistema")
                driver = webdriver.Chrome(service=service, options=opts)
                driver.set_page_load_timeout(30)
                return driver

        # Fallback: webdriver_manager (download)
        try:
            driver_path = ChromeDriverManager().install()
            service = ChromeService(driver_path)
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(30)
            logger.info("Chromedriver obtido via webdriver_manager")
            return driver
        except Exception as e:
            logger.error(f"Falha ao iniciar Chrome/Chromium: {e}")
            raise

    async def _get_driver(self):
        if self._driver:
            return self._driver
        # criar driver em thread (bloqueante)
        self._driver = await asyncio.to_thread(self._create_driver)
        return self._driver

    async def _close_driver(self):
        if self._driver:
            try:
                await asyncio.to_thread(self._driver.quit)
            except Exception:
                pass
            self._driver = None

    async def extract_property_links(self, listing_url: str, max_links: int = 100) -> List[str]:
        """Extrai links de imóveis usando Selenium para renderização JS"""
        try:
            driver = await self._get_driver()
            await asyncio.to_thread(driver.get, listing_url)
            # aguardar carregamento mínimo
            await asyncio.sleep(1.2)
            html = await asyncio.to_thread(driver.page_source.__str__)
            soup = BeautifulSoup(html, 'html.parser')

            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/imovel/' in href or '/venda/' in href or '/locacao/' in href:
                    full = urljoin(self.base_url, href)
                    links.add(full)
                    if len(links) >= max_links:
                        break

            logger.info(f"Encontrados {len(links)} links em {listing_url}")
            return list(links)
        except Exception as e:
            logger.error(f"Erro ao extrair links {listing_url}: {e}")
            return []

    async def extract_property_details(self, property_url: str) -> Optional[Dict[str, Any]]:
        """Extrai detalhes completos de um imóvel (renderiza com Selenium e parseia)"""
        try:
            driver = await self._get_driver()
            await asyncio.to_thread(driver.get, property_url)
            await asyncio.sleep(1.0)  # permitir js carregar conteúdo dinâmico
            html = await asyncio.to_thread(driver.page_source.__str__)
            soup = BeautifulSoup(html, 'html.parser')

            property_data: Dict[str, Any] = {
                'reference': '',
                'title': '',
                'description': '',
                'address': '',
                'neighborhood': '',
                'city': '',
                'uf': '',
                'price': '',
                'bedrooms': 0,
                'bathrooms': 0,
                'parking_spaces': 0,
                'features': [],
                'images': [],
                'url': property_url,
                'scraped_at': datetime.utcnow().isoformat(),
                'ai_analysis': '',
                'ai_enhanced': False
            }

            # título
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                property_data['title'] = title_elem.get_text(strip=True)

            # referência (fallback regex)
            ref_match = re.search(r'Refer[êe]ncia[:\s]*([A-Z0-9-]+)', html, re.IGNORECASE)
            if ref_match:
                property_data['reference'] = ref_match.group(1).strip()

            # bairro/cidade/descricao/price via selectors heurísticos
            # tenta classes comuns, senão faz regex
            text_html = soup.get_text(separator="\n")
            bairro_m = re.search(r'Bairro[:\s]*([^\n\r]+)', text_html, re.IGNORECASE)
            if bairro_m:
                property_data['neighborhood'] = bairro_m.group(1).strip()

            cidade_m = re.search(r'(Município|Cidade)[:\s]*([^\n\r]+)', text_html, re.IGNORECASE)
            if cidade_m:
                property_data['city'] = cidade_m.group(2).strip()

            price_elem = soup.find(class_=re.compile(r'valor|price', re.IGNORECASE))
            if price_elem:
                property_data['price'] = price_elem.get_text(strip=True)
            else:
                price_m = re.search(r'Valor[:\s]*R?\$?\s*([\d\.,]+)', text_html, re.IGNORECASE)
                if price_m:
                    property_data['price'] = f"R$ {price_m.group(1)}"

            desc_elem = soup.find(class_=re.compile(r'descri.*|detail.*|info.*', re.IGNORECASE))
            if desc_elem:
                property_data['description'] = desc_elem.get_text(separator="\n", strip=True)[:2000]
            else:
                p = soup.find('p')
                if p:
                    property_data['description'] = p.get_text(strip=True)[:2000]

            # imagens
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if not src:
                    continue
                if src.startswith('data:'):
                    continue
                full = urljoin(self.base_url, src)
                if full not in property_data['images']:
                    property_data['images'].append(full)

            # características listadas
            features = []
            for ul in soup.find_all('ul'):
                for li in ul.find_all('li'):
                    text = li.get_text(strip=True)
                    if text:
                        features.append(text)
            property_data['features'] = list(dict.fromkeys(features))[:30]

            # enriquecer com GPT
            property_data = await self.enhance_property_with_gpt(property_data)

            logger.info(f"Imóvel extraído: {property_data.get('title','')[:60]} - {property_data.get('reference')}")
            return property_data

        except Exception as e:
            logger.error(f"Erro ao extrair detalhes {property_url}: {e}")
            return None

    async def enhance_property_with_gpt(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquece dados do imóvel usando o GPT/OpenAI (call_gpt)"""
        if not property_data.get('description') and not property_data.get('title'):
            return property_data

        system_prompt = (
            "Você é um especialista em análise de imóveis. Extraia pontos positivos, público-alvo, "
            "potenciais problemas e sugestão de preço/ação comercial. Seja conciso (<=250 caracteres)."
        )
        user_prompt = (
            f"Título: {property_data.get('title','')}\n"
            f"Bairro: {property_data.get('neighborhood','')}\n"
            f"Cidade: {property_data.get('city','')}\n"
            f"Preço: {property_data.get('price','')}\n"
            f"Descrição: {property_data.get('description','')[:1200]}\n"
            f"Features: {', '.join(property_data.get('features',[])[:8])}\n"
        )
        prompt = f"{system_prompt}\n\n{user_prompt}\n\nSofia:"

        try:
            resp = await asyncio.to_thread(rag.call_gpt, prompt, self.openai_model)
            if resp:
                property_data['ai_analysis'] = resp.strip()[:250]
                property_data['ai_enhanced'] = True

                # --- novo: salvar metadados de embedding no Firestore via intelligent_bot ---
                try:
                    doc_id = property_data.get('reference') or property_data.get('url') or f"prop-{uuid.uuid4().hex[:8]}"
                    vector_id = f"vec-{uuid.uuid4().hex}"
                    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
                    meta = {
                        "source": "scraper",
                        "url": property_data.get("url"),
                        "title": property_data.get("title"),
                        "neighborhood": property_data.get("neighborhood")
                    }
                    # intelligent_bot._save_embedding_meta é async — aguardar a gravação
                    await intelligent_bot._save_embedding_meta(doc_id=doc_id, vector_id=vector_id, model=embedding_model, meta=meta)
                except Exception as e_save:
                    logger.debug(f"Falha ao salvar metadata de embedding: {e_save}")
        except Exception as e:
            logger.error(f"Erro ao enriquecer imóvel com GPT: {e}")
        return property_data

    async def generate_market_insights(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera insights de mercado via GPT usando um resumo dos dados extraídos"""
        if not properties:
            return self._get_fallback_insights(properties)

        summary = {
            'total_properties': len(properties),
            'by_neighborhood': {},
            'sample_titles': [p.get('title','') for p in properties[:10]]
        }
        for p in properties:
            nb = (p.get('neighborhood') or 'unknown').strip()
            summary['by_neighborhood'][nb] = summary['by_neighborhood'].get(nb, 0) + 1

        system_prompt = (
            "Você é um analista de mercado imobiliário. Com base no resumo a seguir, gere insights práticos "
            "sobre bairros em alta, tipos de imóvel demandados e recomendações de ação (<=400 caracteres)."
        )
        user_prompt = json.dumps(summary, ensure_ascii=False)[:2000]
        prompt = f"{system_prompt}\n\n{user_prompt}\n\nSofia:"
        try:
            resp = await asyncio.to_thread(rag.call_gpt, prompt, self.openai_model)
            if resp:
                return {
                    'ai_insights': resp.strip(),
                    'data_summary': summary,
                    'generated_at': datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Erro ao gerar insights com GPT: {e}")
        return self._get_fallback_insights(properties)

    def _get_fallback_insights(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(properties)
        by_nb = {}
        for p in properties:
            nb = (p.get('neighborhood') or 'unknown').strip()
            by_nb[nb] = by_nb.get(nb, 0) + 1
        top_nb = max(by_nb.items(), key=lambda x: x[1])[0] if by_nb else 'Centro'
        return {
            'ai_insights': f"Mercado com {total} imóveis. Destaque em {top_nb}.",
            'data_summary': {'total_properties': total, 'by_neighborhood': by_nb},
            'generated_at': datetime.utcnow().isoformat()
        }

    async def scrape_properties_by_type(self, property_type: str, transaction_type: str = 'venda',
                                        city: str = 'curitiba', max_properties: int = 50) -> List[Dict[str, Any]]:
        """Extrai imóveis por tipo usando Selenium para obter links e detalhes"""
        listing_urls = [
            f"{self.base_url}/imoveis/{transaction_type}/{property_type}/{city}",
            f"{self.base_url}/imoveis/{transaction_type}/{property_type}",
            f"{self.base_url}/cidades/{transaction_type}/{property_type}"
        ]

        all_links = []
        driver = await self._get_driver()
        try:
            for url in listing_urls:
                links = await self.extract_property_links(url, max_links=max_properties)
                all_links.extend(links)
                if len(all_links) >= max_properties:
                    break

            unique = list(dict.fromkeys(all_links))[:max_properties]
            logger.info(f"Iniciando extração de {len(unique)} imóveis do tipo {property_type}")

            semaphore = asyncio.Semaphore(4)
            async def extract_with_sem(url):
                async with semaphore:
                    return await self.extract_property_details(url)

            tasks = [extract_with_sem(u) for u in unique]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            properties = [r for r in results if isinstance(r, dict) and r]
            logger.info(f"Extraídos {len(properties)} imóveis do tipo {property_type}")
            return properties
        finally:
            # do not close driver here to reuse across calls; caller may close
            pass

    async def scrape_all_properties(self, max_per_type: int = 20) -> List[Dict[str, Any]]:
        all_properties = []
        priority_types = ['apartamento', 'casa', 'sobrado', 'terreno']
        for transaction in ['venda', 'locacao']:
            for ptype in priority_types:
                try:
                    props = await self.scrape_properties_by_type(ptype, transaction, max_properties=max_per_type)
                    all_properties.extend(props)
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.error(f"Erro ao extrair {ptype} {transaction}: {e}")
        # opcional: fechar driver após grande job
        await self._close_driver()
        logger.info(f"Extração completa: {len(all_properties)} imóveis encontrados")
        return all_properties

    def save_properties_to_file(self, properties: List[Dict[str, Any]], filename: str = None):
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"properties_allega_{timestamp}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(properties, f, ensure_ascii=False, indent=2)
            logger.info(f"Dados salvos em {filename}")
            return filename
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo: {e}")
            return None

    async def format_for_ai_training(self, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        # mantém a lógica anterior para gerar knowledge base
        stats = {
            'total_properties': len(properties),
            'by_type': {},
            'by_neighborhood': {}
        }
        for p in properties:
            t = p.get('property_type') or p.get('type') or 'unknown'
            stats['by_type'][t] = stats['by_type'].get(t, 0) + 1
            nb = (p.get('neighborhood') or 'unknown').strip()
            stats['by_neighborhood'][nb] = stats['by_neighborhood'].get(nb, 0) + 1

        market_insights = await self.generate_market_insights(properties)
        knowledge_base = {
            'statistics': stats,
            'market_insights': market_insights,
            'sample_properties': properties[:10],
            'last_updated': datetime.utcnow().isoformat()
        }
        return knowledge_base

# monitor and main functions preserved (use as before)
async def monitor_scraper(interval_minutes: int = 30, max_properties: int = 100):
    scraper = AllegaPropertyScraper()
    interval = interval_minutes * 60
    while True:
        logger.info(f"[{datetime.utcnow()}] Iniciando verificação de imóveis...")
        try:
            scraped_properties = await scraper.scrape_all_properties(max_per_type=max_properties // 4)
            scraped_dict = {p.get('reference') or p.get('url'): p for p in scraped_properties if p}
            # Buscar imóveis existentes do Supabase
            result = await asyncio.to_thread(
                supabase_client.client.table('properties').select('*').execute
            )
            supabase_props = result.data or []
            supabase_dict = {p.get('reference') or p.get('url'): p for p in supabase_props if p}

            new_refs = set(scraped_dict.keys()) - set(supabase_dict.keys())
            new_props = [scraped_dict[r] for r in new_refs if r]
            removed_refs = set(supabase_dict.keys()) - set(scraped_dict.keys())
            removed_props = [supabase_dict[r] for r in removed_refs if r]

            updated = []
            for ref in set(scraped_dict.keys()) & set(supabase_dict.keys()):
                if scraped_dict[ref] != supabase_dict[ref]:
                    updated.append(scraped_dict[ref])

            # Adicionar novos imóveis
            for prop in new_props:
                await asyncio.to_thread(supabase_client.upsert_property, prop)
            if new_props:
                logger.info(f"Adicionados {len(new_props)} imóveis ao Supabase")

            # Remover imóveis que não existem mais
            for prop in removed_props:
                ref = prop.get('reference') or prop.get('url')
                await asyncio.to_thread(
                    supabase_client.client.table('properties').delete().eq('reference', ref).execute
                )
            if removed_props:
                logger.info(f"Removidos {len(removed_props)} imóveis do Supabase")

            # Atualizar imóveis modificados
            for prop in updated:
                await asyncio.to_thread(supabase_client.upsert_property, prop)
            if updated:
                logger.info(f"Atualizados {len(updated)} imóveis no Supabase")

            if scraped_properties:
                insights = await scraper.generate_market_insights(scraped_properties)
                logger.info(f"Insights: {insights.get('ai_insights','N/A')[:120]}")

        except Exception as e:
            logger.error(f"Erro durante monitoramento: {e}")

        logger.info("Verificação concluída. Aguardando próxima execução...")
        await asyncio.sleep(interval)

async def scrape_allega_properties(max_properties: int = 100) -> Dict[str, Any]:
    scraper = AllegaPropertyScraper()
    logger.info("Iniciando extração de imóveis da Allega Imóveis com análise GPT...")
    properties = await scraper.scrape_all_properties(max_per_type=max_properties // 4)
    if not properties:
        logger.warning("Nenhum imóvel extraído")
        return {}
    filename = scraper.save_properties_to_file(properties)
    knowledge_base = await scraper.format_for_ai_training(properties)
    ai_enhanced_count = sum(1 for p in properties if p.get('ai_enhanced'))
    logger.info(f"Extração concluída: {len(properties)} imóveis processados, {ai_enhanced_count} com análise IA")
    return {
        'properties': properties,
        'knowledge_base': knowledge_base,
        'filename': filename,
        'ai_enhanced_count': ai_enhanced_count
    }

if __name__ == "__main__":
    asyncio.run(monitor_scraper(interval_minutes=30, max_properties=100))
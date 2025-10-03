"""
Sistema de Preço ao Vivo - Diferencial 4
Conecta API Sciensa/SincronizaIMOVEIS
RAG sempre filtra updated_at > now-6h (zero oferta de vendido)
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import aiohttp
import os

from app.services.supabase_client import supabase_client
from app.services.rag_pipeline import rag

logger = logging.getLogger(__name__)

class LivePricingSystem:
    """Sistema de sincronização de preços em tempo real"""
    
    def __init__(self):
        # Configurações das APIs
        self.sciensa_config = {
            "base_url": os.getenv("SCIENSA_API_URL", ""),
            "api_key": os.getenv("SCIENSA_API_KEY", ""),
            "client_id": os.getenv("SCIENSA_CLIENT_ID", ""),
            "enabled": bool(os.getenv("SCIENSA_API_KEY"))
        }
        
        self.sincroniza_config = {
            "base_url": os.getenv("SINCRONIZA_API_URL", ""),
            "username": os.getenv("SINCRONIZA_USERNAME", ""),
            "password": os.getenv("SINCRONIZA_PASSWORD", ""),
            "enabled": bool(os.getenv("SINCRONIZA_USERNAME"))
        }
        
        # Cache de sincronização
        self.sync_cache = {}
        self.last_full_sync = None
        
        # Filtros de qualidade
        self.freshness_hours = 6  # Apenas imóveis atualizados nas últimas 6h
        self.min_data_quality = 0.8  # Score mínimo de qualidade dos dados
        
        # Estatísticas
        self.sync_stats = {
            "total_properties_synced": 0,
            "active_properties": 0,
            "outdated_removed": 0,
            "price_updates": 0,
            "last_sync_time": None,
            "sync_errors": 0
        }
    
    async def start_live_sync_loop(self):
        """Inicia loop de sincronização contínua"""
        
        logger.info("Iniciando sistema de sincronização de preços ao vivo")
        
        while True:
            try:
                # Sincronização incremental a cada 30 minutos
                await self._incremental_sync()
                await asyncio.sleep(1800)  # 30 minutos
                
                # Sincronização completa a cada 6 horas
                if (not self.last_full_sync or 
                    datetime.utcnow() - self.last_full_sync > timedelta(hours=6)):
                    await self._full_sync()
                    self.last_full_sync = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Erro no loop de sincronização: {e}")
                self.sync_stats["sync_errors"] += 1
                await asyncio.sleep(300)  # Wait 5 min on error
    
    async def _incremental_sync(self):
        """Sincronização incremental (últimas 6 horas)"""
        
        try:
            logger.info("Iniciando sincronização incremental")
            start_time = datetime.utcnow()
            
            # Timestamp de 6 horas atrás
            six_hours_ago = start_time - timedelta(hours=self.freshness_hours)
            
            # Sincronizar com Sciensa
            if self.sciensa_config["enabled"]:
                sciensa_updates = await self._sync_sciensa_incremental(six_hours_ago)
                await self._process_property_updates(sciensa_updates, "sciensa")
            
            # Sincronizar com SincronizaIMOVEIS
            if self.sincroniza_config["enabled"]:
                sincroniza_updates = await self._sync_sincroniza_incremental(six_hours_ago)
                await self._process_property_updates(sincroniza_updates, "sincroniza")
            
            # Remover imóveis desatualizados
            await self._remove_outdated_properties()
            
            # Atualizar estatísticas
            self.sync_stats["last_sync_time"] = datetime.utcnow()
            sync_duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Sincronização incremental concluída em {sync_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"Erro na sincronização incremental: {e}")
            self.sync_stats["sync_errors"] += 1
    
    async def _full_sync(self):
        """Sincronização completa de todos os imóveis ativos"""
        
        try:
            logger.info("Iniciando sincronização completa")
            start_time = datetime.utcnow()
            
            total_synced = 0
            
            # Sync completo Sciensa
            if self.sciensa_config["enabled"]:
                sciensa_properties = await self._sync_sciensa_full()
                total_synced += await self._process_property_updates(sciensa_properties, "sciensa")
            
            # Sync completo SincronizaIMOVEIS
            if self.sincroniza_config["enabled"]:
                sincroniza_properties = await self._sync_sincroniza_full()
                total_synced += await self._process_property_updates(sincroniza_properties, "sincroniza")
            
            # Limpeza completa
            await self._cleanup_inactive_properties()
            
            # Reindexar RAG
            await self._reindex_rag_vectors()
            
            self.sync_stats["total_properties_synced"] = total_synced
            sync_duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Sincronização completa: {total_synced} imóveis em {sync_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"Erro na sincronização completa: {e}")
            self.sync_stats["sync_errors"] += 1
    
    async def _sync_sciensa_incremental(self, since_time: datetime) -> List[Dict[str, Any]]:
        """Sincronização incremental com API Sciensa"""
        
        if not self.sciensa_config["enabled"]:
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.sciensa_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # Parâmetros para buscar apenas atualizações recentes
            params = {
                "client_id": self.sciensa_config["client_id"],
                "updated_since": since_time.isoformat(),
                "status": "active",
                "include_photos": True,
                "include_details": True,
                "limit": 1000
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.sciensa_config['base_url']}/properties/updated"
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        properties = data.get("properties", [])
                        
                        logger.info(f"Sciensa incremental: {len(properties)} imóveis")
                        return self._normalize_sciensa_properties(properties)
                    else:
                        logger.error(f"Erro Sciensa API: {response.status}")
                        return []
            
        except Exception as e:
            logger.error(f"Erro na sincronização Sciensa incremental: {e}")
            return []
    
    async def _sync_sincroniza_incremental(self, since_time: datetime) -> List[Dict[str, Any]]:
        """Sincronização incremental com SincronizaIMOVEIS"""
        
        if not self.sincroniza_config["enabled"]:
            return []
        
        try:
            # Autenticação
            auth_data = {
                "username": self.sincroniza_config["username"],
                "password": self.sincroniza_config["password"]
            }
            
            async with aiohttp.ClientSession() as session:
                # Login
                login_url = f"{self.sincroniza_config['base_url']}/auth/login"
                async with session.post(login_url, json=auth_data) as auth_response:
                    if auth_response.status != 200:
                        logger.error("Erro na autenticação SincronizaIMOVEIS")
                        return []
                    
                    auth_result = await auth_response.json()
                    token = auth_result.get("access_token")
                
                # Buscar propriedades atualizadas
                headers = {"Authorization": f"Bearer {token}"}
                params = {
                    "updated_since": since_time.isoformat(),
                    "status": "ativo",
                    "limit": 1000
                }
                
                properties_url = f"{self.sincroniza_config['base_url']}/imoveis/updated"
                async with session.get(properties_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        properties = data.get("imoveis", [])
                        
                        logger.info(f"SincronizaIMOVEIS incremental: {len(properties)} imóveis")
                        return self._normalize_sincroniza_properties(properties)
                    else:
                        logger.error(f"Erro SincronizaIMOVEIS API: {response.status}")
                        return []
            
        except Exception as e:
            logger.error(f"Erro na sincronização SincronizaIMOVEIS incremental: {e}")
            return []
    
    def _normalize_sciensa_properties(self, properties: List[Dict]) -> List[Dict[str, Any]]:
        """Normaliza dados da API Sciensa"""
        
        normalized = []
        
        for prop in properties:
            try:
                # Extrair dados principais
                normalized_prop = {
                    "external_id": f"sciensa_{prop.get('id')}",
                    "source": "sciensa",
                    "title": prop.get("title", ""),
                    "description": prop.get("description", ""),
                    "price": float(prop.get("price", 0)),
                    "transaction_type": prop.get("transaction_type", "").lower(),  # venda/locacao
                    "property_type": prop.get("property_type", "").lower(),
                    
                    # Localização
                    "address": prop.get("address", ""),
                    "neighborhood": prop.get("neighborhood", ""),
                    "city": prop.get("city", ""),
                    "state": prop.get("state", ""),
                    "zipcode": prop.get("zipcode", ""),
                    
                    # Características
                    "bedrooms": int(prop.get("bedrooms", 0)),
                    "bathrooms": int(prop.get("bathrooms", 0)),
                    "parking_spaces": int(prop.get("parking_spaces", 0)),
                    "area_total": float(prop.get("area_total", 0)),
                    "area_useful": float(prop.get("area_useful", 0)),
                    
                    # Imagens
                    "images": prop.get("photos", [])[:10],  # Máximo 10 fotos
                    "main_image": prop.get("photos", [{}])[0].get("url", "") if prop.get("photos") else "",
                    
                    # Metadados
                    "status": "active" if prop.get("status") == "ativo" else "inactive",
                    "updated_at": datetime.fromisoformat(prop.get("updated_at", datetime.utcnow().isoformat())),
                    "url": prop.get("url", ""),
                    
                    # Qualidade dos dados
                    "data_quality_score": self._calculate_data_quality(prop)
                }
                
                # Filtrar apenas imóveis com qualidade suficiente
                if normalized_prop["data_quality_score"] >= self.min_data_quality:
                    normalized.append(normalized_prop)
                
            except Exception as e:
                logger.debug(f"Erro ao normalizar propriedade Sciensa: {e}")
                continue
        
        return normalized
    
    def _normalize_sincroniza_properties(self, properties: List[Dict]) -> List[Dict[str, Any]]:
        """Normaliza dados da API SincronizaIMOVEIS"""
        
        normalized = []
        
        for prop in properties:
            try:
                normalized_prop = {
                    "external_id": f"sincroniza_{prop.get('codigo')}",
                    "source": "sincroniza",
                    "title": prop.get("titulo", ""),
                    "description": prop.get("descricao", ""),
                    "price": float(prop.get("valor", 0)),
                    "transaction_type": "venda" if prop.get("tipo_negocio") == "V" else "locacao",
                    "property_type": self._map_sincroniza_property_type(prop.get("tipo_imovel")),
                    
                    # Localização
                    "address": prop.get("endereco", ""),
                    "neighborhood": prop.get("bairro", ""),
                    "city": prop.get("cidade", ""),
                    "state": prop.get("uf", ""),
                    "zipcode": prop.get("cep", ""),
                    
                    # Características
                    "bedrooms": int(prop.get("quartos", 0)),
                    "bathrooms": int(prop.get("banheiros", 0)),
                    "parking_spaces": int(prop.get("vagas", 0)),
                    "area_total": float(prop.get("area_total", 0)),
                    "area_useful": float(prop.get("area_util", 0)),
                    
                    # Imagens
                    "images": [img.get("url") for img in prop.get("fotos", [])[:10]],
                    "main_image": prop.get("fotos", [{}])[0].get("url", "") if prop.get("fotos") else "",
                    
                    # Metadados
                    "status": "active" if prop.get("status") == "A" else "inactive",
                    "updated_at": datetime.fromisoformat(prop.get("data_atualizacao", datetime.utcnow().isoformat())),
                    "url": prop.get("url_imovel", ""),
                    
                    # Qualidade dos dados
                    "data_quality_score": self._calculate_data_quality(prop)
                }
                
                if normalized_prop["data_quality_score"] >= self.min_data_quality:
                    normalized.append(normalized_prop)
                
            except Exception as e:
                logger.debug(f"Erro ao normalizar propriedade SincronizaIMOVEIS: {e}")
                continue
        
        return normalized
    
    def _map_sincroniza_property_type(self, tipo_imovel: str) -> str:
        """Mapeia tipos de imóvel do SincronizaIMOVEIS"""
        
        mapping = {
            "AP": "apartamento",
            "CA": "casa",
            "CS": "casa",
            "SO": "sobrado",
            "CO": "comercial",
            "TE": "terreno",
            "CH": "chacara",
            "FA": "fazenda"
        }
        
        return mapping.get(tipo_imovel, "apartamento")
    
    def _calculate_data_quality(self, property_data: Dict) -> float:
        """Calcula score de qualidade dos dados (0-1)"""
        
        score = 0.0
        max_score = 10.0
        
        # Campos obrigatórios
        if property_data.get("title"):
            score += 1.5
        if property_data.get("description") and len(property_data["description"]) > 50:
            score += 1.5
        if property_data.get("price", 0) > 0:
            score += 2.0
        
        # Localização
        if property_data.get("address"):
            score += 1.0
        if property_data.get("neighborhood"):
            score += 1.0
        
        # Características
        if property_data.get("bedrooms", 0) > 0:
            score += 1.0
        if property_data.get("area_total", 0) > 0:
            score += 1.0
        
        # Imagens
        photos = property_data.get("photos", property_data.get("fotos", []))
        if photos and len(photos) > 0:
            score += 1.0
        
        return min(score / max_score, 1.0)
    
    async def _process_property_updates(self, properties: List[Dict], source: str) -> int:
        """Processa atualizações de propriedades salvando no Supabase e atualizando embeddings."""

        processed_count = 0

        for prop in properties:
            try:
                # Preparar dados para Supabase
                supabase_prop = self._map_property_for_supabase(prop)

                # Upsert (rodar em thread para não bloquear loop)
                await asyncio.to_thread(supabase_client.upsert_property, supabase_prop)

                # Atualizar embeddings/vetores para busca (RAG / property_embeddings)
                await self._update_property_embeddings(supabase_prop)

                processed_count += 1

                if supabase_prop.get("price"):
                    self.sync_stats["price_updates"] += 1

            except Exception as e:
                logger.error(f"Erro ao processar propriedade {prop.get('external_id')}: {e}")

        logger.info(f"Processadas {processed_count} propriedades do {source} (Supabase)")
        return processed_count

    def _map_property_for_supabase(self, property_data: Dict) -> Dict[str, Any]:
        """Mapeia payload normalizado para o esquema da tabela 'properties' no Supabase.

        Suposições (ajustar se o schema divergir):
        - Chave primária lógica: property_id (usar external_id)
        - Campos principais: title, description, price, neighborhood, property_type, transaction_type, status, source
        - Campos numéricos: bedrooms, bathrooms, parking_spaces, area_total, area_useful
        """

        try:
            mapped = {
                'property_id': property_data.get('external_id'),
                'external_id': property_data.get('external_id'),
                'source': property_data.get('source'),
                'title': property_data.get('title', ''),
                'description': property_data.get('description', ''),
                'price': property_data.get('price', 0),
                'transaction_type': property_data.get('transaction_type'),
                'property_type': property_data.get('property_type'),
                'address': property_data.get('address'),
                'neighborhood': property_data.get('neighborhood'),
                'city': property_data.get('city'),
                'state': property_data.get('state'),
                'zipcode': property_data.get('zipcode'),
                'bedrooms': property_data.get('bedrooms'),
                'bathrooms': property_data.get('bathrooms'),
                'parking_spaces': property_data.get('parking_spaces'),
                'area_total': property_data.get('area_total'),
                'area_useful': property_data.get('area_useful'),
                'images': property_data.get('images', []),
                'main_image': property_data.get('main_image'),
                'status': property_data.get('status', 'active'),
                'data_quality_score': property_data.get('data_quality_score'),
                'url': property_data.get('url'),
                'synced_at': datetime.utcnow().isoformat(),
                'is_fresh': True,
            }

            # Garantir updated_at como string ISO
            updated_at = property_data.get('updated_at')
            if isinstance(updated_at, datetime):
                mapped['updated_at'] = updated_at.isoformat()
            else:
                mapped['updated_at'] = (updated_at or datetime.utcnow()).isoformat()

            return mapped
        except Exception as e:
            logger.error(f"Falha ao mapear propriedade para Supabase: {e}")
            return property_data
    
    async def _update_property_embeddings(self, property_data: Dict):
        """Atualiza vetor/embedding da propriedade em property_embeddings via RAG pipeline."""

        try:
            text_parts = [
                property_data.get('title', ''),
                property_data.get('description', ''),
                f"Bairro: {property_data.get('neighborhood', '')}",
                f"Preço: R$ {property_data.get('price', 0):,.2f}",
                f"Quartos: {property_data.get('bedrooms', 0)}",
                f"Área: {property_data.get('area_total', 0)} m²"
            ]
            full_text = " ".join([p for p in text_parts if p])

            metadata = {
                'property_id': property_data.get('property_id'),
                'external_id': property_data.get('external_id'),
                'source': property_data.get('source'),
                'price': property_data.get('price'),
                'neighborhood': property_data.get('neighborhood'),
                'property_type': property_data.get('property_type'),
                'transaction_type': property_data.get('transaction_type'),
                'updated_at': property_data.get('updated_at'),
                'status': property_data.get('status'),
                'url': property_data.get('url'),
                'main_image': property_data.get('main_image'),
            }

            await rag.add_document(
                text=full_text,
                metadata=metadata,
                doc_id=property_data.get('property_id')
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar embeddings (Supabase): {e}")
    
    async def _remove_outdated_properties(self):
        """Marca propriedades como inativas no Supabase quando ultrapassam janela de frescor."""

        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.freshness_hours)
            cutoff_iso = cutoff_time.isoformat()

            # Buscar propriedades ativas mais antigas que o cutoff
            result = supabase_client.client.table('properties') \
                .select('property_id, updated_at, status') \
                .eq('status', 'active') \
                .lt('updated_at', cutoff_iso) \
                .execute()

            outdated = result.data or []
            removed_count = 0

            for prop in outdated:
                pid = prop.get('property_id')
                try:
                    supabase_client.client.table('properties') \
                        .update({
                            'status': 'inactive',
                            'deactivated_at': datetime.utcnow().isoformat(),
                            'deactivation_reason': 'outdated_data'
                        }) \
                        .eq('property_id', pid) \
                        .execute()
                    # Remover embedding
                    await rag.remove_document(pid)
                    removed_count += 1
                except Exception as inner:
                    logger.debug(f"Falha ao inativar {pid}: {inner}")

            self.sync_stats['outdated_removed'] = removed_count
            if removed_count:
                logger.info(f"Inativadas {removed_count} propriedades desatualizadas (Supabase)")
        except Exception as e:
            logger.error(f"Erro ao marcar propriedades desatualizadas: {e}")
    
    async def get_fresh_properties_only(self, 
                                      query: str = "", 
                                      filters: Dict = None,
                                      limit: int = 10) -> List[Dict]:
        """Busca apenas propriedades frescas (< 6h)"""
        
        # Garantir filtro de frescor
        fresh_filters = filters or {}
        fresh_filters["status"] = "active"
        fresh_filters["updated_at"] = {
            "$gte": datetime.utcnow() - timedelta(hours=self.freshness_hours)
        }
        
        # Buscar com RAG
        results = await rag.retrieve(
            query=query,
            top_k=limit,
            filters=fresh_filters
        )
        
        logger.info(f"Busca fresca: {len(results)} propriedades para '{query}'")
        return results
    
    async def get_pricing_stats(self) -> Dict[str, Any]:
        """Estatísticas do sistema de preços (Supabase)."""

        try:
            six_hours_ago = (datetime.utcnow() - timedelta(hours=self.freshness_hours)).isoformat()
            result = supabase_client.client.table('properties') \
                .select('property_id') \
                .eq('status', 'active') \
                .gte('updated_at', six_hours_ago) \
                .execute()
            active_count = len(result.data or [])
            self.sync_stats['active_properties'] = active_count
            return {
                **self.sync_stats,
                'freshness_hours': self.freshness_hours,
                'min_data_quality': self.min_data_quality,
                'sciensa_enabled': self.sciensa_config['enabled'],
                'sincroniza_enabled': self.sincroniza_config['enabled'],
                'cache_size': len(self.sync_cache)
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas (Supabase): {e}")
            return self.sync_stats

# Instância global
live_pricing_system = LivePricingSystem()
"""
Sistema Dual-Stack: Fine-tune + RAG Dirigido
Camada 1: Fine-tune próprio com Chain-of-Thought enxuto
Latência total < 900ms para superar concorrência
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
from dataclasses import dataclass
import re

from app.services.rag_pipeline import rag
from app.services.embedding_cache import embedding_cache

logger = logging.getLogger(__name__)

@dataclass
class PropertyHypothesis:
    """Hipótese gerada pelo fine-tuned model"""
    neighborhood: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    property_type: Optional[str] = None  # casa, apartamento, comercial
    transaction_type: Optional[str] = None  # venda, locacao
    urgency_score: int = 1  # 1-5, onde 5 = <HOT>
    intent_confidence: float = 0.0
    extracted_keywords: List[str] = None

class DualStackIntelligence:
    """Sistema Dual-Stack para máxima performance"""
    
    def __init__(self):
        self.session_cache = {}  # Cache de sessão por phone_hash
        self.cache_ttl_hours = 24
        
        # Padrões para urgência
        self.urgency_patterns = [
            r'(preciso|tenho que) (sair|mudar|deixar).{0,20}(sexta|sábado|domingo|semana|mês)',
            r'(despej\w+|despejo|saindo de casa|sem lugar)',
            r'(urgente|emergência|rápido|logo|já)',
            r'(até|antes d[eo]) (sexta|fim de semana|\d{1,2}\/\d{1,2})',
            r'(casamento|separação|trabalho novo|transferência) (próxim\w+|em \w+ dias)'
        ]
        
        # Cache de hipóteses para evitar reprocessamento
        self.hypothesis_cache = {}
    
    async def process_dual_stack_query(self, 
                                     user_message: str, 
                                     user_phone: str,
                                     conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Chain-of-Thought enxuto:
        1. Fine-tuned model gera hipótese
        2. Hipótese vira query vetorial com filtros
        3. Recupera top-3 + 2 comparáveis  
        4. Fine-tuned model reescreve resposta
        """
        start_time = datetime.utcnow()
        
        try:
            # 1. GERAR HIPÓTESE (Camada 1: Fine-tune)
            hypothesis = await self._generate_hypothesis(user_message, conversation_history)
            
            # 2. CONSULTAR CACHE DE SESSÃO primeiro
            phone_hash = self._get_phone_hash(user_phone)
            cached_properties = self._get_session_cache(phone_hash, hypothesis)
            
            if cached_properties:
                logger.info(f"Cache HIT para {phone_hash}: {len(cached_properties)} propriedades")
                properties = cached_properties
            else:
                # 3. QUERY VETORIAL DIRIGIDA (Camada 2: RAG leve)
                properties = await self._directed_vector_search(hypothesis, user_message)
                
                # 4. SALVAR NO CACHE DE SESSÃO
                self._update_session_cache(phone_hash, properties, hypothesis)
            
            # 5. REESCREVER RESPOSTA COM FINE-TUNE
            final_response = await self._generate_top_seller_response(
                user_message, hypothesis, properties, conversation_history
            )
            
            # Calcular latência
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "response": final_response,
                "properties": properties[:3],  # Top 3 para UI
                "comparable_properties": properties[3:5] if len(properties) > 3 else [],
                "hypothesis": hypothesis,
                "urgency_detected": hypothesis.urgency_score >= 4,
                "latency_ms": latency_ms,
                "cache_hit": bool(cached_properties)
            }
            
        except Exception as e:
            logger.error(f"Erro no dual-stack: {e}")
            
            # Fallback para sistema original
            return await self._fallback_response(user_message, user_phone)
    
    async def _generate_hypothesis(self, 
                                  user_message: str, 
                                  history: List[Dict] = None) -> PropertyHypothesis:
        """Gera hipótese estruturada via fine-tuned model"""
        
        # Cache de hipótese
        msg_hash = hashlib.md5(user_message.encode()).hexdigest()[:8]
        if msg_hash in self.hypothesis_cache:
            return self.hypothesis_cache[msg_hash]
        
        # Prompt otimizado para Chain-of-Thought
        system_prompt = """
        Você é Sofia, IA imobiliária top-vendedora. Analise a mensagem e extraia HIPÓTESE estruturada.
        
        RETORNE JSON EXATO:
        {
          "neighborhood": "bairro ou null",
          "min_price": numero_ou_null,
          "max_price": numero_ou_null, 
          "bedrooms": numero_ou_null,
          "property_type": "apartamento|casa|comercial|null",
          "transaction_type": "venda|locacao|null",
          "urgency_score": 1-5,
          "intent_confidence": 0.0-1.0,
          "extracted_keywords": ["palavra1", "palavra2"]
        }
        
        URGENCY_SCORE:
        5 = URGENTE (preciso sair sexta, despejo, emergência)
        4 = ALTA (casamento próximo, trabalho novo)
        3 = MÉDIA (procurando ativamente)
        2 = BAIXA (só olhando)
        1 = MÍNIMA (curiosidade)
        """
        
        # Contexto histórico resumido
        context = ""
        if history:
            recent_msgs = history[-3:]  # Últimas 3 mensagens
            context = "\\nHISTÓRICO:\\n" + "\\n".join([
                f"{m.get('role', 'user')}: {m.get('content', '')[:100]}"
                for m in recent_msgs
            ])
        
        full_prompt = f"{system_prompt}\\n\\nMENSAGEM: \"{user_message}\"{context}\\n\\nJSON:"
        
        try:
            # Usar modelo fine-tuned
            model = os.getenv("OPENAI_FINETUNED_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
            response = await asyncio.to_thread(rag.call_gpt, full_prompt, model)
            
            # Extrair JSON
            json_match = re.search(r'\\{.*\\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                hypothesis = PropertyHypothesis(
                    neighborhood=data.get("neighborhood"),
                    min_price=data.get("min_price"),
                    max_price=data.get("max_price"),
                    bedrooms=data.get("bedrooms"),
                    property_type=data.get("property_type"),
                    transaction_type=data.get("transaction_type"),
                    urgency_score=data.get("urgency_score", 1),
                    intent_confidence=data.get("intent_confidence", 0.0),
                    extracted_keywords=data.get("extracted_keywords", [])
                )
                
                # Cache da hipótese
                self.hypothesis_cache[msg_hash] = hypothesis
                
                logger.info(f"Hipótese gerada: {hypothesis.neighborhood}, {hypothesis.property_type}, urgência={hypothesis.urgency_score}")
                return hypothesis
            
        except Exception as e:
            logger.debug(f"Erro ao gerar hipótese: {e}")
        
        # Fallback: hipótese básica com regex
        return self._generate_fallback_hypothesis(user_message)
    
    def _generate_fallback_hypothesis(self, message: str) -> PropertyHypothesis:
        """Hipótese de fallback usando regex"""
        
        msg_lower = message.lower()
        
        # Detectar urgência
        urgency_score = 1
        for pattern in self.urgency_patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                urgency_score = max(urgency_score, 4)
                break
        
        # Extrair bairros conhecidos
        neighborhoods = ["água verde", "bigorrilho", "batel", "centro", "cabral", "jardins"]
        neighborhood = None
        for n in neighborhoods:
            if n in msg_lower:
                neighborhood = n.title()
                break
        
        # Extrair quartos
        bedrooms_match = re.search(r'(\\d+)\\s*(quarto|dormitório)', msg_lower)
        bedrooms = int(bedrooms_match.group(1)) if bedrooms_match else None
        
        # Tipo de imóvel
        property_type = None
        if any(t in msg_lower for t in ["apartamento", "apto", "ap"]):
            property_type = "apartamento"
        elif any(t in msg_lower for t in ["casa", "residência"]):
            property_type = "casa"
        
        # Transação
        transaction_type = None
        if any(t in msg_lower for t in ["alugar", "aluguel", "locação"]):
            transaction_type = "locacao"
        elif any(t in msg_lower for t in ["comprar", "venda", "financiamento"]):
            transaction_type = "venda"
        
        return PropertyHypothesis(
            neighborhood=neighborhood,
            bedrooms=bedrooms,
            property_type=property_type,
            transaction_type=transaction_type,
            urgency_score=urgency_score,
            intent_confidence=0.7,
            extracted_keywords=re.findall(r'\\b\\w{4,}\\b', msg_lower)[:5]
        )
    
    async def _directed_vector_search(self, 
                                    hypothesis: PropertyHypothesis, 
                                    original_query: str) -> List[Dict]:
        """Query vetorial dirigida com filtros da hipótese"""
        
        try:
            # Construir query otimizada baseada na hipótese
            search_parts = []
            
            if hypothesis.property_type:
                search_parts.append(hypothesis.property_type)
            
            if hypothesis.neighborhood:
                search_parts.append(hypothesis.neighborhood)
            
            if hypothesis.bedrooms:
                search_parts.append(f"{hypothesis.bedrooms} quartos")
            
            if hypothesis.transaction_type:
                search_parts.append(hypothesis.transaction_type)
            
            # Query híbrida: hipótese + query original
            if search_parts:
                directed_query = " ".join(search_parts) + " " + original_query[:100]
            else:
                directed_query = original_query
            
            # Filtros dinâmicos
            filters = {"status": "active"}  # Sempre apenas ativos
            
            # Filtro de preço
            if hypothesis.min_price or hypothesis.max_price:
                filters["price_range"] = {
                    "min": hypothesis.min_price,
                    "max": hypothesis.max_price
                }
            
            # Filtro temporal: só imóveis atualizados nas últimas 6h
            six_hours_ago = datetime.utcnow() - timedelta(hours=6)
            filters["updated_at"] = {"$gte": six_hours_ago}
            
            # RAG dirigido com filtros
            results = await rag.retrieve(
                query=directed_query,
                top_k=5,  # Top-3 + 2 comparáveis
                filters=filters
            )
            
            logger.info(f"RAG dirigido: {len(results)} resultados para '{directed_query}'")
            return results
            
        except Exception as e:
            logger.error(f"Erro na busca dirigida: {e}")
            
            # Fallback: busca simples
            return await rag.retrieve(original_query, top_k=5, filters={"status": "active"})
    
    async def _generate_top_seller_response(self,
                                          original_query: str,
                                          hypothesis: PropertyHypothesis, 
                                          properties: List[Dict],
                                          history: List[Dict] = None) -> str:
        """Gera resposta com tom de corretor top-vendedor"""
        
        # Prompt especializado para vendas
        system_prompt = """
        Você é Sofia, corretor top-vendedor da Allega Imóveis (200+ vendas/ano).
        
        PERSONALIDADE:
        - Confiante mas não arrogante
        - Cria urgência sem pressionar
        - Sempre oferece 2-3 opções específicas  
        - Agenda visita no final (call-to-action forte)
        
        REGRAS:
        - Se urgência alta (4-5): mencione "entendo a urgência" + disponibilidade imediata
        - Se cliente específico: foque nas características exatas
        - Se genérico: eduque sobre mercado + ofereça opções
        - SEMPRE termine com agendamento concreto
        
        FORMATO DA RESPOSTA:
        1. Reconheça necessidade específica (1 linha)
        2. Apresente 2-3 imóveis com destaque (2-3 linhas cada)
        3. Call-to-action forte para visita (1-2 linhas)
        """
        
        # Construir contexto dos imóveis
        properties_context = ""
        for i, prop in enumerate(properties[:3], 1):
            meta = prop.get("meta", prop.get("metadata", {}))
            properties_context += f"""
            IMÓVEL {i}:
            Descrição: {prop.get('text', '')[:200]}
            Bairro: {meta.get('neighborhood', 'N/A')}
            Preço: {meta.get('price', 'Consulte')}
            URL: {meta.get('url', '')}
            Imagem: {meta.get('main_image', '')}
            """
        
        # Contexto da urgência
        urgency_context = ""
        if hypothesis.urgency_score >= 4:
            urgency_context = "\\n🚨 CLIENTE COM URGÊNCIA ALTA - Oferecer visita HOJE/AMANHÃ"
        
        full_prompt = f"""
        {system_prompt}
        
        PERGUNTA CLIENTE: "{original_query}"
        HIPÓTESE EXTRAÍDA: Bairro={hypothesis.neighborhood}, Tipo={hypothesis.property_type}, Urgência={hypothesis.urgency_score}
        {urgency_context}
        
        IMÓVEIS DISPONÍVEIS:
        {properties_context}
        
        RESPOSTA SOFIA (Tom top-vendedor):
        """
        
        try:
            model = os.getenv("OPENAI_FINETUNED_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
            response = await asyncio.to_thread(rag.call_gpt, full_prompt, model)
            
            # Adicionar tags especiais para urgência
            if hypothesis.urgency_score >= 4:
                response = "<HOT> " + response + " <URGENT>"
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Erro na resposta top-seller: {e}")
            return self._generate_fallback_response(properties)
    
    def _get_phone_hash(self, phone: str) -> str:
        """Hash do telefone para privacy"""
        return hashlib.sha256(phone.encode()).hexdigest()[:12]
    
    def _get_session_cache(self, phone_hash: str, hypothesis: PropertyHypothesis) -> Optional[List[Dict]]:
        """Recuperar cache de sessão se compatível"""
        
        cache_entry = self.session_cache.get(phone_hash)
        if not cache_entry:
            return None
        
        # Verificar TTL
        if datetime.utcnow() - cache_entry["timestamp"] > timedelta(hours=self.cache_ttl_hours):
            del self.session_cache[phone_hash]
            return None
        
        # Verificar compatibilidade da hipótese
        cached_hypothesis = cache_entry["hypothesis"]
        
        # Compatible se mesmo bairro + tipo + faixa de quartos
        if (cached_hypothesis.neighborhood == hypothesis.neighborhood and
            cached_hypothesis.property_type == hypothesis.property_type and
            abs((cached_hypothesis.bedrooms or 0) - (hypothesis.bedrooms or 0)) <= 1):
            
            return cache_entry["properties"]
        
        return None
    
    def _update_session_cache(self, phone_hash: str, properties: List[Dict], hypothesis: PropertyHypothesis):
        """Atualizar cache de sessão"""
        
        self.session_cache[phone_hash] = {
            "properties": properties[:50],  # Últimos 50 imóveis
            "hypothesis": hypothesis,
            "timestamp": datetime.utcnow()
        }
        
        # Limpar cache antigo
        cutoff = datetime.utcnow() - timedelta(hours=self.cache_ttl_hours * 2)
        expired_keys = [
            k for k, v in self.session_cache.items()
            if v["timestamp"] < cutoff
        ]
        for key in expired_keys:
            del self.session_cache[key]
    
    def _generate_fallback_response(self, properties: List[Dict]) -> str:
        """Resposta de fallback simples"""
        
        if not properties:
            return (
                "Vou procurar as melhores opções para você! "
                "Me conte mais sobre suas preferências de bairro e orçamento "
                "para encontrar o imóvel perfeito. "
                "Posso agendar uma consulta personalizada ainda hoje?"
            )
        
        return (
            f"Encontrei {len(properties)} ótimas opções para você! "
            "Vou te enviar os detalhes dos melhores imóveis. "
            "Que tal agendarmos uma visita ainda esta semana? "
            "Tenho horários disponíveis amanhã de manhã ou à tarde."
        )
    
    async def _fallback_response(self, message: str, phone: str) -> Dict[str, Any]:
        """Sistema de fallback completo"""
        
        properties = await rag.retrieve(message, top_k=3, filters={"status": "active"})
        
        return {
            "response": self._generate_fallback_response(properties),
            "properties": properties,
            "comparable_properties": [],
            "hypothesis": self._generate_fallback_hypothesis(message),
            "urgency_detected": False,
            "latency_ms": 0,
            "cache_hit": False
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Estatísticas do cache de sessão"""
        
        active_sessions = len(self.session_cache)
        total_properties_cached = sum(
            len(entry["properties"]) 
            for entry in self.session_cache.values()
        )
        
        return {
            "active_sessions": active_sessions,
            "total_properties_cached": total_properties_cached,
            "cache_ttl_hours": self.cache_ttl_hours,
            "hypothesis_cache_size": len(self.hypothesis_cache)
        }

# Instância global
dual_stack_intelligence = DualStackIntelligence()
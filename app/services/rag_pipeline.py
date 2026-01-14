# rag_pipeline.py - 100% Supabase (pgvector)
"""
RAG Pipeline usando APENAS Supabase com pgvector
"""

import os
import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import re
from dotenv import load_dotenv

load_dotenv()

from sentence_transformers import SentenceTransformer, CrossEncoder
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
import tiktoken

# Import Supabase
from app.services.supabase_client import supabase_client
from app.services.session_cache import session_cache

# ---------- CONFIG ----------
# Embedding config
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # 384 dimensões (modelo local)
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensões (OpenAI)
OPENAI_EMBED_DIM = 1536

# Forçar sempre 1536 (independente de variáveis de ambiente) para manter consistência com schema vector(1536)
PROPERTY_EMBED_DIM = OPENAI_EMBED_DIM
USE_OPENAI_EMBEDDINGS = True  # Mantemos True para acionar caminho OpenAI/padding; se chave faltar, cai em fallback local padded.

# Retrieval config
TOP_K = 10
RERANK_TOP_K = 5
MAX_CONTEXT_TOKENS = 3000

# OpenAI config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_MODEL")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# ---------------------------

@dataclass
class RetrievalResult:
    id: str
    text: str
    metadata: Dict
    score: float
    rerank_score: Optional[float] = None


class RAGPipeline:
    """RAG Pipeline usando Supabase pgvector"""
    
    def __init__(self):
        self.system_prompt = """Você é Sofia, assistente virtual da Allega Imóveis em Curitiba/PR. 
Persona: amigável, prestativa, especialista em mercado imobiliário de Curitiba. 
Estilo: concisa (3-4 linhas), oferece próximos passos (visita, contato, WhatsApp). 
Instruções: apresente-se na primeira interação, qualifique leads (orçamento, preferências, prazo), seja empática com objeções de preço e sugira alternativas se necessário."""
        
        self.logger = self._setup_logging()
        self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        self.force_local_embeddings = False
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.tokenizer = tiktoken.encoding_for_model("gpt-4.1-mini")
        
        # OpenAI setup
        if OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(
                api_key=OPENAI_API_KEY,
                timeout=REQUEST_TIMEOUT
            )
        else:
            self.openai_client = None
            self.logger.warning("OpenAI API key not found - using local embeddings only")
    
    def _setup_logging(self) -> logging.Logger:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('rag_pipeline.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def _sanitize_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    async def _encode_texts(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings garantindo dimensão PROPERTY_EMBED_DIM.

        Quando OpenAI está habilitado:
          - Tenta gerar embeddings 1536-dim (text-embedding-3-small).
          - Em falha (timeout, quota, rede) faz fallback local 384-dim com zero-padding até 1536.
        Em modo local:
          - Usa SentenceTransformer (384) diretamente.
        """
        if not texts:
            return []

        # Caminho OpenAI (dim 1536)
        if USE_OPENAI_EMBEDDINGS:
            if not self.openai_client:
                self.logger.error("USE_OPENAI_EMBEDDINGS=1 mas cliente OpenAI não está configurado — verifique OPENAI_API_KEY")
            else:
                try:
                    response = self.openai_client.embeddings.create(
                        input=texts,
                        model=OPENAI_EMBEDDING_MODEL
                    )
                    vectors = [item.embedding for item in response.data]
                    if vectors and len(vectors[0]) != PROPERTY_EMBED_DIM:
                        raise ValueError(f"Embedding OpenAI retornou dimensão {len(vectors[0])} != {PROPERTY_EMBED_DIM}")
                    return vectors
                except Exception as e:
                    self.logger.warning(f"Falha OpenAI embeddings: {e} — fallback local com padding")

            # Fallback local -> pad para 1536
            local_vectors = self.embed_model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()
            if local_vectors and len(local_vectors[0]) != PROPERTY_EMBED_DIM:
                src_dim = len(local_vectors[0])
                if src_dim > PROPERTY_EMBED_DIM:
                    self.logger.error(f"Fallback local produziu dimensão {src_dim} > {PROPERTY_EMBED_DIM} — truncando")
                    padded = [v[:PROPERTY_EMBED_DIM] for v in local_vectors]
                else:
                    # Zero padding
                    diff = PROPERTY_EMBED_DIM - src_dim
                    padded = [v + [0.0] * diff for v in local_vectors]
                return padded
            return local_vectors

        # Caminho somente local (PROPERTY_EMBED_DIM deve ser 384)
        local_vectors = self.embed_model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()
        if local_vectors and len(local_vectors[0]) != PROPERTY_EMBED_DIM:
            self.logger.warning(
                "Dimensão local %d diferente de PROPERTY_EMBED_DIM=%d (ajuste esperado se schema mudou)." % (
                    len(local_vectors[0]), PROPERTY_EMBED_DIM
                )
            )
        return local_vectors
    
    def _rerank_results(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Rerank results using cross-encoder"""
        if not results:
            return results
        
        pairs = [[query, r.text] for r in results]
        scores = self.reranker.predict(pairs)
        
        for result, score in zip(results, scores):
            result.rerank_score = float(score)
        
        # Sort by rerank score
        results.sort(key=lambda x: x.rerank_score or 0, reverse=True)
        return results
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = TOP_K, 
        filters: Optional[Dict] = None, 
        phone_hash: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents using Supabase pgvector with session cache
        """
        start_time = time.time()
        
        # Sanitize query
        clean_query = self._sanitize_text(query)
        if not clean_query:
            return []
        
        try:
            # Get shown properties from cache (if phone_hash provided)
            shown_property_ids = []
            if phone_hash:
                shown_property_ids = await session_cache.get_shown_properties(phone_hash)
                if shown_property_ids:
                    self.logger.info(f"Cache: {len(shown_property_ids)} properties already shown to {phone_hash[:8]}...")
            
            # Generate query embedding
            query_embeddings = await self._encode_texts([clean_query])
            query_embedding = query_embeddings[0]
            
            # Search using Supabase pgvector
            search_limit = top_k * 3 if shown_property_ids else top_k * 2
            
            results = supabase_client.vector_search(
                query_embedding=query_embedding,
                limit=search_limit,
                filters=filters
            )
            
            # Process results
            retrieval_results = []
            new_property_ids = []
            
            for result in results:
                property_id = result.get("property_id")

                # Filtro de sessão (já mostrado)
                if phone_hash and property_id and property_id in shown_property_ids:
                    self.logger.debug(f"Skipping property {property_id} - already shown")
                    continue

                # Normalização de campos conforme saída atual da função RPC ou fallback lexical
                # RPC fields: property_id, title, description, url, price, bedrooms_int, similarity
                # Fallback lexical: property_id, title, description, url, price, bedrooms_int, similarity=None, fallback=True
                similarity = result.get("similarity")
                if similarity is None:
                    # atribuir score neutro baixo para ordenar no fim
                    similarity_score = 0.10
                else:
                    similarity_score = float(similarity)

                # Montar metadados mínimos
                meta = {
                    "property_id": property_id,
                    "title": result.get("title"),
                    "url": result.get("url"),
                    "price": result.get("price"),
                    "bedrooms": result.get("bedrooms_int"),
                    "fallback": result.get("fallback", False)
                }

                text_snippet = result.get("description") or result.get("title") or ""
                retrieval_result = RetrievalResult(
                    id=property_id or result.get("id", "unknown"),
                    text=text_snippet,
                    metadata=meta,
                    score=similarity_score
                )
                retrieval_results.append(retrieval_result)

                if property_id:
                    new_property_ids.append(property_id)
            
            # Rerank results
            if len(retrieval_results) > RERANK_TOP_K:
                reranked_results = self._rerank_results(clean_query, retrieval_results[:top_k])
                final_results = reranked_results[:RERANK_TOP_K]
            else:
                final_results = retrieval_results[:RERANK_TOP_K]
            
            # Update session cache with new properties shown
            if phone_hash and new_property_ids:
                final_property_ids = []
                for result in final_results:
                    prop_id = result.metadata.get("property_id")
                    if prop_id:
                        final_property_ids.append(prop_id)
                
                if final_property_ids:
                    await session_cache.add_shown_properties(phone_hash, final_property_ids)
                    self.logger.info(f"Cache updated: +{len(final_property_ids)} properties for {phone_hash[:8]}...")
            
            elapsed = time.time() - start_time
            self.logger.info(f"Retrieved {len(final_results)} results in {elapsed:.2f}s (cache-filtered: {len(shown_property_ids)})")
            
            return final_results
        
        except Exception as e:
            self.logger.error(f"Error in retrieve: {e}")
            return []
    
    def build_prompt(self, question: str, context_docs: List[RetrievalResult]) -> str:
        """Build prompt from question and retrieved documents"""
        # Build context from documents
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            context_parts.append(f"[Doc {i}]\n{doc.text}\n")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long
        context_tokens = len(self.tokenizer.encode(context))
        if context_tokens > MAX_CONTEXT_TOKENS:
            # Trim context
            context = context[:MAX_CONTEXT_TOKENS * 4]  # Rough estimate
        
        return f"""Baseando-se APENAS nas informações do contexto abaixo, responda a pergunta do usuário de forma natural e concisa.

CONTEXTO:
{context}

PERGUNTA: {question}"""
    
    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
    def call_gpt(self, prompt: str, model_name: Optional[str] = None, temperature: float = 0.1) -> str:
        """Call OpenAI with retry logic"""
        if not self.openai_client:
            return "Desculpe, o serviço de chat não está disponível no momento."
        
        model = model_name or OPENAI_CHAT_MODEL
        
        try:
            start_time = time.time()
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=512
            )
            
            elapsed = time.time() - start_time
            
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()
                self.logger.info(f"GPT response generated in {elapsed:.2f}s (model: {model})")
                return content
            else:
                self.logger.warning("Empty response from OpenAI")
                return "Desculpe, não consegui gerar uma resposta adequada."
        
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
    
    async def query(
        self, 
        question: str, 
        filters: Optional[Dict] = None, 
        phone_hash: Optional[str] = None
    ) -> str:
        """
        Main query method - combines retrieval and generation with session cache
        """
        try:
            start_time = time.time()
            
            # Retrieve relevant documents (with cache filtering)
            retrieved = await self.retrieve(question, filters=filters, phone_hash=phone_hash)
            
            if not retrieved:
                return "Desculpe, não encontrei informações relevantes para sua pergunta. Pode reformular ou ser mais específico?"
            
            # Build prompt
            prompt = self.build_prompt(question, retrieved)
            
            # Generate response
            response = self.call_gpt(prompt)
            
            elapsed = time.time() - start_time
            self.logger.info(f"Query completed in {elapsed:.2f}s")
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error in query: {e}")
            return "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente."


# Global instance
rag = RAGPipeline()

# Convenience functions
async def query_rag(question: str, filters: Optional[Dict] = None, phone_hash: Optional[str] = None) -> str:
    return await rag.query(question, filters=filters, phone_hash=phone_hash)

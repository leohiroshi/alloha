"""
RAG pipeline (low-cost profile).

Defaults:
- Local embeddings only (384 dims)
- Optional OpenAI chat for legacy callers
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import openai
import tiktoken
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder, SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.session_cache import session_cache
from app.services.supabase_client import supabase_client

load_dotenv()

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
PROPERTY_EMBED_DIM = int(os.getenv("PROPERTY_EMBED_DIM", "384"))
TOP_K = 10
RERANK_TOP_K = 5
MAX_CONTEXT_TOKENS = 3000
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_MODEL")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30


@dataclass
class RetrievalResult:
    id: str
    text: str
    metadata: Dict
    score: float
    rerank_score: Optional[float] = None


class RAGPipeline:
    def __init__(self) -> None:
        self.system_prompt = (
            "Voce e Sofia, assistente virtual imobiliaria. "
            "Responda em portugues de forma objetiva e com proximo passo."
        )
        self.logger = self._setup_logging()
        self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.tokenizer = tiktoken.encoding_for_model("gpt-4.1-mini")
        self.openai_client = (
            openai.OpenAI(api_key=OPENAI_API_KEY, timeout=REQUEST_TIMEOUT)
            if OPENAI_API_KEY
            else None
        )

    @staticmethod
    def _setup_logging() -> logging.Logger:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(__name__)

    @staticmethod
    def _sanitize_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    async def _encode_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self.embed_model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        ).tolist()
        if vectors and len(vectors[0]) != PROPERTY_EMBED_DIM:
            src_dim = len(vectors[0])
            if src_dim > PROPERTY_EMBED_DIM:
                vectors = [v[:PROPERTY_EMBED_DIM] for v in vectors]
            else:
                diff = PROPERTY_EMBED_DIM - src_dim
                vectors = [v + [0.0] * diff for v in vectors]
        return vectors

    def _rerank_results(
        self, query: str, results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        if not results:
            return results
        pairs = [[query, row.text] for row in results]
        scores = self.reranker.predict(pairs)
        for row, score in zip(results, scores):
            row.rerank_score = float(score)
        results.sort(key=lambda x: x.rerank_score or 0, reverse=True)
        return results

    async def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        filters: Optional[Dict] = None,
        phone_hash: Optional[str] = None,
    ) -> List[RetrievalResult]:
        start = time.time()
        clean_query = self._sanitize_text(query)
        if not clean_query:
            return []

        shown_property_ids: List[str] = []
        if phone_hash:
            shown_property_ids = await session_cache.get_shown_properties(phone_hash)

        query_embedding = (await self._encode_texts([clean_query]))[0]
        rows = supabase_client.vector_search(
            query_embedding=query_embedding,
            limit=top_k * 3,
            filters=filters,
            query_text=clean_query,
            fallback_lexical=True,
        )

        normalized: List[RetrievalResult] = []
        for row in rows:
            prop_id = row.get("property_id")
            if phone_hash and prop_id and prop_id in shown_property_ids:
                continue
            score = row.get("similarity")
            normalized.append(
                RetrievalResult(
                    id=prop_id or row.get("id", "unknown"),
                    text=row.get("description") or row.get("title") or "",
                    metadata={
                        "property_id": prop_id,
                        "url": row.get("url"),
                        "price": row.get("price"),
                        "bedrooms": row.get("bedrooms_int"),
                        "fallback": row.get("fallback", False),
                    },
                    score=float(score) if score is not None else 0.1,
                )
            )

        if len(normalized) > RERANK_TOP_K:
            normalized = self._rerank_results(clean_query, normalized[:top_k])[:RERANK_TOP_K]
        else:
            normalized = normalized[:RERANK_TOP_K]

        if phone_hash:
            property_ids = [
                row.metadata.get("property_id")
                for row in normalized
                if row.metadata.get("property_id")
            ]
            if property_ids:
                await session_cache.add_shown_properties(phone_hash, property_ids)

        self.logger.info("retrieve finished in %.2fs", time.time() - start)
        return normalized

    def build_prompt(self, question: str, context_docs: List[RetrievalResult]) -> str:
        context_lines = [f"[Doc {i}] {row.text}" for i, row in enumerate(context_docs, start=1)]
        context = "\n".join(context_lines)
        if len(self.tokenizer.encode(context)) > MAX_CONTEXT_TOKENS:
            context = context[: MAX_CONTEXT_TOKENS * 4]
        return (
            "Baseando-se apenas no contexto abaixo, responda de forma natural.\n\n"
            f"CONTEXTO:\n{context}\n\nPERGUNTA: {question}"
        )

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
    def call_gpt(
        self, prompt: str, model_name: Optional[str] = None, temperature: float = 0.1
    ) -> str:
        if not self.openai_client:
            return "Servico de chat indisponivel no momento."
        model = model_name or OPENAI_CHAT_MODEL
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=512,
        )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        return "Desculpe, nao consegui gerar resposta."

    async def query(
        self, question: str, filters: Optional[Dict] = None, phone_hash: Optional[str] = None
    ) -> str:
        docs = await self.retrieve(question, filters=filters, phone_hash=phone_hash)
        if not docs:
            return "Nao encontrei informacoes relevantes para essa pergunta."
        prompt = self.build_prompt(question, docs)
        return self.call_gpt(prompt)

    async def add_document(self, text: str, metadata: Dict, doc_id: Optional[str] = None) -> bool:
        if not text:
            return False
        prop_data = {
            "property_id": doc_id or metadata.get("property_id") or metadata.get("external_id"),
            "external_id": metadata.get("external_id") or doc_id,
            "source": metadata.get("source") or "rag",
            "title": metadata.get("title") or text[:80],
            "description": text[:5000],
            "price": metadata.get("price"),
            "transaction_type": metadata.get("transaction_type"),
            "property_type": metadata.get("property_type"),
            "neighborhood": metadata.get("neighborhood"),
            "bedrooms": metadata.get("bedrooms"),
            "url": metadata.get("url"),
            "main_image": metadata.get("main_image"),
            "status": metadata.get("status", "active"),
        }
        return bool(supabase_client.upsert_property(prop_data))

    async def remove_document(self, doc_id: str) -> bool:
        try:
            supabase_client.require_client().table("properties").update(
                {"status": "inactive"}
            ).eq("property_id", doc_id).execute()
            return True
        except Exception:
            return False


rag = RAGPipeline()


async def query_rag(question: str, filters: Optional[Dict] = None, phone_hash: Optional[str] = None) -> str:
    return await rag.query(question, filters=filters, phone_hash=phone_hash)

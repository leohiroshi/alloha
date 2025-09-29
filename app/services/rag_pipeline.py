# rag_pipeline.py
import os
import json
import logging
import asyncio
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib
import re
from dotenv import load_dotenv

load_dotenv()

from google.cloud import firestore
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
import tiktoken

# ---------- CONFIG ----------
FIRESTORE_KEY = os.getenv("FIREBASE_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = FIRESTORE_KEY

FIRESTORE_COLLECTION = "properties"
CHROMA_DIR = "chroma_db"
CHROMA_COLLECTION = "imoveis_sofia"

# Embedding config - CONSISTENTE
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
USE_OPENAI_EMBEDDINGS = os.getenv("USE_OPENAI_EMBEDDINGS", "1") == "1"

# Retrieval config
TOP_K = 10
RERANK_TOP_K = 5
MAX_CONTEXT_TOKENS = 3000
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# OpenAI config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
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
    def __init__(self):
        self.logger = self._setup_logging()
        self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        self.tokenizer = tiktoken.encoding_for_model("gpt-4.1-mini")
        
        # ChromaDB setup
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = self._get_or_create_collection()
        
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

    def _get_or_create_collection(self):
        """Get or create ChromaDB collection with proper metadata"""
        try:
            collection = self.client.get_collection(CHROMA_COLLECTION)
            self.logger.info(f"Loaded existing collection: {CHROMA_COLLECTION}")
        except:
            collection = self.client.create_collection(
                CHROMA_COLLECTION, 
                metadata={
                    "purpose": "imoveis",
                    "embedding_model": OPENAI_EMBEDDING_MODEL if USE_OPENAI_EMBEDDINGS else EMBED_MODEL_NAME,
                    "created_at": datetime.now().isoformat()
                }
            )
            self.logger.info(f"Created new collection: {CHROMA_COLLECTION}")
        return collection

    def _sanitize_text(self, text: str) -> str:
        """Sanitize and normalize text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize price formats
        text = re.sub(r'R\$\s*(\d+)\.(\d+)', r'R$ \1\2', text)
        
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r'ignore\s+previous\s+instructions',
            r'system\s*:',
            r'assistant\s*:',
            r'user\s*:',
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text

    def _chunk_text(self, text: str, doc_id: str) -> List[Tuple[str, Dict]]:
        """Split long text into chunks"""
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) <= CHUNK_SIZE:
            return [(text, {"chunk_id": f"{doc_id}_0", "chunk_index": 0})]
        
        chunks = []
        for i in range(0, len(tokens), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk_tokens = tokens[i:i + CHUNK_SIZE]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunk_meta = {
                "chunk_id": f"{doc_id}_{i//CHUNK_SIZE}",
                "chunk_index": i//CHUNK_SIZE
            }
            chunks.append((chunk_text, chunk_meta))
        
        return chunks

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _get_openai_embedding_async(self, texts: List[str]) -> List[List[float]]:
        """Get OpenAI embeddings with retry logic"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
            response = self.openai_client.embeddings.create(
                model=OPENAI_EMBEDDING_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            self.logger.error(f"OpenAI embedding error: {e}")
            raise

    def _get_local_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get local embeddings"""
        return [self.embed_model.encode(text).tolist() for text in texts]

    async def _encode_texts(self, texts: List[str]) -> List[List[float]]:
        """Encode texts using configured embedding method"""
        if USE_OPENAI_EMBEDDINGS and self.openai_client:
            return await self._get_openai_embedding_async(texts)
        else:
            return self._get_local_embeddings(texts)

    def fetch_from_firestore(self, limit: Optional[int] = None) -> List[Dict]:
        """Fetch documents from Firestore with error handling"""
        try:
            db = firestore.Client()
            query = db.collection(FIRESTORE_COLLECTION)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            items = []
            
            for doc in docs:
                try:
                    data = doc.to_dict()
                    data["_id"] = doc.id
                    items.append(data)
                except Exception as e:
                    self.logger.error(f"Error processing document {doc.id}: {e}")
                    continue
            
            self.logger.info(f"Fetched {len(items)} documents from Firestore")
            return items
            
        except Exception as e:
            self.logger.error(f"Error fetching from Firestore: {e}")
            return []

    def doc_to_text(self, doc: Dict) -> str:
        """Convert document to searchable text"""
        parts = []
        
        # Core content
        if doc.get("title"):
            parts.append(f"Título: {doc['title']}")
        if doc.get("description"):
            parts.append(f"Descrição: {doc['description']}")
        
        # Location
        if doc.get("neighborhood"):
            parts.append(f"Bairro: {doc['neighborhood']}")
        if doc.get("city"):
            parts.append(f"Cidade: {doc['city']}")
        
        # Property details
        if doc.get("bedrooms"):
            parts.append(f"Quartos: {doc['bedrooms']}")
        if doc.get("bathrooms"):
            parts.append(f"Banheiros: {doc['bathrooms']}")
        if doc.get("area"):
            parts.append(f"Área: {doc['area']} m²")
        if doc.get("price"):
            parts.append(f"Preço: R$ {doc['price']}")
        
        text = "\n".join(parts)
        return self._sanitize_text(text)

    async def build_or_update_index(self, limit: Optional[int] = None, batch_size: int = 50):
        """Build or update the search index with batching"""
        start_time = time.time()
        
        # Clear existing collection for consistency
        try:
            existing_ids = self.collection.get()['ids']
            if existing_ids:
                self.collection.delete(ids=existing_ids)
                self.logger.info(f"Cleared {len(existing_ids)} existing documents")
        except Exception as e:
            self.logger.warning(f"Could not clear existing collection: {e}")

        items = self.fetch_from_firestore(limit=limit)
        if not items:
            self.logger.warning("No documents to index")
            return

        all_ids, all_docs, all_metas, all_embeddings = [], [], [], []
        
        # Process documents in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_texts = []
            batch_data = []
            
            for doc in batch:
                try:
                    text = self.doc_to_text(doc)
                    if not text.strip():
                        continue
                    
                    # Create chunks for long documents
                    chunks = self._chunk_text(text, doc["_id"])
                    
                    for chunk_text, chunk_meta in chunks:
                        batch_texts.append(chunk_text)
                        
                        # Prepare metadata
                        metadata = {
                            "original_id": doc["_id"],
                            "neighborhood": doc.get("neighborhood", ""),
                            "city": doc.get("city", ""),
                            "price": doc.get("price"),
                            "bedrooms": doc.get("bedrooms"),
                            "status": doc.get("status", "disponivel"),
                            "url": doc.get("url", ""),
                            "main_image": doc.get("main_image", ""),
                            "source": "firestore",
                            "indexed_at": datetime.now().isoformat(),
                            **chunk_meta
                        }
                        
                        batch_data.append({
                            "id": chunk_meta["chunk_id"],
                            "text": chunk_text,
                            "metadata": metadata
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error processing document {doc.get('_id', 'unknown')}: {e}")
                    continue
            
            if not batch_texts:
                continue
            
            # Get embeddings for batch
            try:
                embeddings = await self._encode_texts(batch_texts)
                
                # Prepare data for ChromaDB
                for data, embedding in zip(batch_data, embeddings):
                    all_ids.append(data["id"])
                    all_docs.append(data["text"])
                    all_metas.append(data["metadata"])
                    all_embeddings.append(embedding)
                
                self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(items) + batch_size - 1)//batch_size}")
                
            except Exception as e:
                self.logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                continue

        # Insert all data
        if all_ids:
            try:
                self.collection.add(
                    documents=all_docs,
                    metadatas=all_metas,
                    ids=all_ids,
                    embeddings=all_embeddings
                )
                
                elapsed = time.time() - start_time
                self.logger.info(f"Index updated with {len(all_ids)} chunks from {len(items)} documents in {elapsed:.2f}s")
                
            except Exception as e:
                self.logger.error(f"Error adding to ChromaDB: {e}")
                raise

    async def retrieve(self, query: str, top_k: int = TOP_K, filters: Optional[Dict] = None) -> List[RetrievalResult]:
        """Retrieve relevant documents with reranking"""
        start_time = time.time()
        
        # Sanitize query
        clean_query = self._sanitize_text(query)
        if not clean_query:
            return []
        
        try:
            # Get query embedding
            query_embeddings = await self._encode_texts([clean_query])
            query_embedding = query_embeddings[0]
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,  # Get more for reranking
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            # Convert to RetrievalResult objects
            retrieval_results = []
            for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
                # Apply filters if specified
                if filters:
                    skip = False
                    for key, value in filters.items():
                        if key in meta and str(meta[key]).lower() != str(value).lower():
                            skip = True
                            break
                    if skip:
                        continue
                
                result = RetrievalResult(
                    id=meta.get("chunk_id", f"unknown_{i}"),
                    text=doc,
                    metadata=meta,
                    score=1.0 - dist  # Convert distance to similarity
                )
                retrieval_results.append(result)
            
            # Rerank results
            if len(retrieval_results) > RERANK_TOP_K:
                reranked_results = self._rerank_results(clean_query, retrieval_results[:top_k])
                final_results = reranked_results[:RERANK_TOP_K]
            else:
                final_results = retrieval_results[:RERANK_TOP_K]
            
            elapsed = time.time() - start_time
            self.logger.info(f"Retrieved {len(final_results)} results in {elapsed:.2f}s")
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"Error in retrieve: {e}")
            return []

    def _rerank_results(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Rerank results using cross-encoder"""
        try:
            pairs = [(query, result.text) for result in results]
            scores = self.reranker.predict(pairs)
            
            for result, score in zip(results, scores):
                result.rerank_score = float(score)
            
            # Sort by rerank score
            results.sort(key=lambda x: x.rerank_score or 0, reverse=True)
            return results
            
        except Exception as e:
            self.logger.error(f"Error in reranking: {e}")
            return results

    def build_prompt(self, question: str, retrieved: List[RetrievalResult]) -> str:
        """Build RAG prompt with token limit"""
        system_prompt = """Você é Sofia, assistente virtual especializada em imóveis da Allega Imóveis em Curitiba/PR. 
                            CARACTERÍSTICAS:
                            - Amigável, prestativa e proativa
                            - Usa emojis contextuais naturalmente 
                            - Respostas concisas (máximo 3-4 linhas)
                            - Especialista em mercado imobiliário de Curitiba
                            - Sempre oferece próximos passos (visita, contato, informações)
                            INFORMAÇÕES DA EMPRESA:
                            - Nome: Allega Imóveis
                            - Telefone: (41) 3285-1383
                            - WhatsApp Venda: (41) 99214-6670
                            - WhatsApp Locação: (41) 99223-0874
                            - Horário: Seg-Sex 08h-18h | Sáb 09h-13h
                            - CRECI: 6684 J
                            INSTRUÇÕES:
                            1. Sempre se apresente como Sofia na primeira interação
                            2. Qualifique leads: orçamento, preferências, prazo
                            3. Ofereça agendamento quando mostrar interesse
                            4. Use conhecimento local de Curitiba
                            5. Seja empática com objeções de preço
                            6. Sugira alternativas quando imóvel indisponível"""

        context_blocks = []
        total_tokens = len(self.tokenizer.encode(system_prompt + question))
        
        for result in retrieved:
            meta = result.metadata
            
            # Build context block
            block = f"""Imóvel ID: {meta.get('original_id', 'N/A')}
                    {result.text}
                    🔗 URL: {meta.get('url', 'N/A')}
                    🖼️ Imagem: {meta.get('main_image', 'N/A')}
                    Relevância: {result.rerank_score or result.score:.3f}"""
            
            block_tokens = len(self.tokenizer.encode(block))
            
            if total_tokens + block_tokens > MAX_CONTEXT_TOKENS:
                break
                
            context_blocks.append(block)
            total_tokens += block_tokens
        
        context = "\n\n---\n\n".join(context_blocks) if context_blocks else "Nenhuma informação encontrada."
        
        return f"""CONTEXTO:
                {context}

                PERGUNTA: {question}"""

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
    def call_gpt(self, prompt: str, model_name: Optional[str] = None, temperature: float = 0.1) -> str:
        """Call OpenAI with retry logic and proper error handling"""
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

    async def query(self, question: str, filters: Optional[Dict] = None) -> str:
        """Main query method - combines retrieval and generation"""
        try:
            start_time = time.time()
            
            # Retrieve relevant documents
            retrieved = await self.retrieve(question, filters=filters)
            
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

# Convenience functions for backward compatibility
async def build_or_update_index(limit=None):
    await rag.build_or_update_index(limit=limit)

async def query_rag(question: str, filters: Optional[Dict] = None) -> str:
    return await rag.query(question, filters=filters)

# EXEMPLO DE USO
if __name__ == "__main__":
    async def main():
        # Build index
        await rag.build_or_update_index(limit=100)  # Test with 100 docs first
        
        # Test queries
        test_queries = [
            "Procuro um apartamento de 2 quartos no Água Verde até 400000",
            "Tem alguma casa com piscina?",
            "Quais imóveis disponíveis no Centro?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 PERGUNTA: {query}")
            response = await rag.query(query)
            print(f"📝 RESPOSTA: {response}")
            print("-" * 80)

    asyncio.run(main())
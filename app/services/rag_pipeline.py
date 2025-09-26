# rag_pipeline.py
import os
import json
import logging
from typing import List
from dotenv import load_dotenv
load_dotenv()  # carrega .env antes de ler variáveis de ambiente

from google.cloud import firestore
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
import subprocess
import shlex
import openai
import time
from chromadb.errors import InvalidArgumentError

# ---------- CONFIG ----------
FIRESTORE_KEY = r"C:\Hrsh\dev\alloha\alloha-credentials.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = FIRESTORE_KEY

FIRESTORE_COLLECTION = "properties"   # nome da coleção no Firestore
CHROMA_DIR = "chroma_db"
CHROMA_COLLECTION = "imoveis_sofia"

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5
# ---------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# inicializa local embedding model (fallback)
embed_model = SentenceTransformer(EMBED_MODEL_NAME)

# Chroma client (Persistent)
client = chromadb.PersistentClient(path=CHROMA_DIR)

# cria/pega coleção
if CHROMA_COLLECTION in [c.name for c in client.list_collections()]:
    collection = client.get_collection(CHROMA_COLLECTION)
else:
    collection = client.create_collection(CHROMA_COLLECTION, metadata={"purpose":"imoveis"})

# OpenAI embeddings/config (leitura após load_dotenv)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set in environment; falling back to local SentenceTransformer embeddings and no chat calls.")
    USE_OPENAI_EMBEDDINGS = False
    openai_client = None
else:
    import openai
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        # fallback para cliente padrão se construtor com api_key falhar
        openai_client = openai.OpenAI()
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    USE_OPENAI_EMBEDDINGS = os.getenv("USE_OPENAI_EMBEDDINGS", "1") == "1"
    OPENAI_CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

def fetch_from_firestore(limit=None) -> List[dict]:
    db = firestore.Client()
    docs = db.collection(FIRESTORE_COLLECTION).stream()
    items = []
    for i, d in enumerate(docs):
        if limit and i >= limit: break
        data = d.to_dict()
        data["_id"] = d.id
        items.append(data)
    return items

def doc_to_text(doc: dict) -> str:
    parts = [
        doc.get("title",""),
        doc.get("description",""),
        f"Bairro: {doc.get('neighborhood','')}",
        f"Cidade: {doc.get('city','')}",
        f"Preço: {doc.get('price','')}",
        f"Quartos: {doc.get('bedrooms','')}",
        f"URL: {doc.get('url','')}",
        f"Imagem: {doc.get('main_image','')}"
    ]
    return "\n".join([str(p) for p in parts if p])

def get_openai_embedding(text: str) -> List[float]:
    """Retorna embedding usando OpenAI (síncrono, new client)."""
    if not OPENAI_API_KEY or not USE_OPENAI_EMBEDDINGS:
        raise RuntimeError("OPENAI_API_KEY not configured or USE_OPENAI_EMBEDDINGS disabled")
    resp = openai_client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=text)
    # new client returns resp.data[0].embedding
    return resp.data[0].embedding

def _encode_text(text: str) -> List[float]:
    """Encode text using configured embedding source."""
    if USE_OPENAI_EMBEDDINGS:
        return get_openai_embedding(text)
    else:
        return embed_model.encode(text).tolist()

def build_or_update_index(limit=None):
    items = fetch_from_firestore(limit=limit)
    ids, docs, metas, embs = [], [], [], []
    for it in tqdm(items, desc="Preparing docs"):
        try:
            uid = it["_id"]
            text = doc_to_text(it)
            meta = {
                "neighborhood": it.get("neighborhood",""),
                "city": it.get("city",""),
                "price": it.get("price",None),
                "status": it.get("status","disponivel"),
                "url": it.get("url",""),
                "main_image": it.get("main_image",""),
                "source": "firestore"
            }
            emb = _encode_text(text)
            ids.append(uid)
            docs.append(text)
            metas.append(meta)
            embs.append(emb)
        except Exception as e:
            logger.exception("Erro ao processar documento para index: %s", e)

    if ids:
        # upsert behaviour: add may fail if ids exist depending on chroma version; using add for simplicity
        try:
            collection.add(documents=docs, metadatas=metas, ids=ids, embeddings=embs)
            logger.info("Índice atualizado com %d documentos", len(ids))
        except Exception:
            # fallback: try upsert via get_collection/upsert if available
            try:
                collection.upsert(documents=docs, metadatas=metas, ids=ids, embeddings=embs)
                logger.info("Índice upsert concluído com %d documentos", len(ids))
            except Exception as e:
                logger.exception("Falha ao adicionar/upsertar na coleção Chroma: %s", e)

def retrieve(query: str, top_k=TOP_K, filters: dict=None):
    """Recupera documentos relevantes do índice (retorna lista de dicts com id/text/meta)."""
    try:
        q_emb = _encode_text(query)
        # Chroma query
        res = collection.query(query_embeddings=[q_emb], n_results=top_k, include=["documents", "metadatas", "distances"])
    except InvalidArgumentError as e:
        logger.exception("Erro no retrieve (embedding dimension mismatch). Tentando fallback local embeddings.")
        # Fallback: se está configurado para usar OpenAI embeddings, tente usar o embedding local (SentenceTransformer)
        try:
            fallback_emb = embed_model.encode(query).tolist()
            res = collection.query(query_embeddings=[fallback_emb], n_results=top_k, include=["documents", "metadatas", "distances"])
        except Exception as e2:
            logger.exception("Fallback do retrieve falhou: %s", e2)
            return []
    except Exception as e:
        logger.exception("Erro no retrieve: %s", e)
        return []

    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    # ids may not be returned in include depending on chroma version; attempt to read if present
    ids = res.get("ids", [[]])[0] if "ids" in res else [None] * len(docs)
    items = []
    for doc, meta, _id in zip(docs, metas, ids):
        if filters:
            ok = True
            for k,v in filters.items():
                if meta.get(k) != v:
                    ok = False; break
            if not ok:
                continue
        items.append({"id": _id, "text": doc, "meta": meta})
    return items

# Monta prompt RAG
SYSTEM_PROMPT = """Você é Sofia, assistente virtual da Allega Imóveis.
Use apenas as informações no bloco CONTEXTO para responder.
Sempre inclua o link (🔗 URL) e a imagem (🖼️ Imagem) do imóvel, se disponíveis.
Se não houver informação suficiente, responda "Desculpe, não tenho essa informação no momento."
Seja concisa e ofereça próximos passos (ex: agendar visita, contato)."""

def build_prompt(question: str, retrieved: List[dict]) -> str:
    context_blocks = []
    for r in retrieved:
        m = r.get("meta", {})
        context_blocks.append(
            f"{r.get('text','')}\n"
            f"🔗 URL: {m.get('url', 'N/A')}\n"
            f"🖼️ Imagem: {m.get('main_image', 'N/A')}\n"
            f"Fonte: id={r.get('id')} | bairro={m.get('neighborhood')} | cidade={m.get('city')} | preço={m.get('price')}"
        )
    context = "\n\n---\n\n".join(context_blocks) if context_blocks else "Nenhuma informação encontrada."
    prompt = f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{context}\n\nPERGUNTA:\n{question}\n\nRESPOSTA:"
    return prompt

def call_gpt(prompt: str, model_name: str = None, max_tokens: int = 512, temperature: float = None) -> str:
    """
    Compat shim -> usa OpenAI Chat (new API client). Síncrono; chame via asyncio.to_thread.
    Ajustes:
    - não envia `temperature` quando é None (usa default do modelo)
    - mapeia `max_tokens` -> `max_completion_tokens`
    """
    model = model_name or (OPENAI_CHAT_MODEL if 'OPENAI_CHAT_MODEL' in globals() else os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    if not OPENAI_API_KEY or openai_client is None:
        raise RuntimeError("OPENAI_API_KEY not configured; cannot call OpenAI chat API")
    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Você é Sofia, assistente virtual da Allega Imóveis. Responda de forma concisa e profissional."},
                {"role": "user", "content": prompt}
            ],
            "max_completion_tokens": max_tokens
        }

        # incluir temperature apenas se fornecido (None => use default do modelo)
        if temperature is not None:
            # alguns modelos não aceitam 0.0; se receber 0.0, omita para usar default
            if temperature == 0.0:
                pass
            else:
                kwargs["temperature"] = float(temperature)

        resp = openai_client.chat.completions.create(**kwargs)

        # new response structure: resp.choices[0].message.content
        choice = resp.choices[0]
        content = getattr(choice.message, "content", None) if hasattr(choice, "message") else None
        if content is None:
            content = (choice.get("message", {}) or {}).get("content") if isinstance(choice, dict) else None
        return (content or "").strip()
    except Exception:
        logger.exception("OpenAI request failed")
        raise

# EXEMPLO DE USO
if __name__ == "__main__":
    build_or_update_index(limit=None)  # set limit se quiser testar

    user_q = "Procuro um apartamento de 2 quartos no Água Verde até 400000"
    filters = {"neighborhood":"Água Verde"}
    retrieved = retrieve(user_q, top_k=5, filters=filters)

    prompt = build_prompt(user_q, retrieved)
    print("----- PROMPT -----\n", prompt[:1500], "...\n")

    resp = call_gpt(prompt)
    print("RESPOSTA:\n", resp)
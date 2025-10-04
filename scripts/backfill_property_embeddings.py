"""Backfill/Rebuild de embeddings para propriedades sem vetor ou com dimensão incorreta.

Uso:
  python scripts/backfill_property_embeddings.py

Flags via env:
  BATCH_SIZE=50            # tamanho do lote
  DRY_RUN=1                # não grava, só mostra quantos seriam processados
  USE_OPENAI_EMBEDDINGS=1  # (já aproveita mesma flag do rag_pipeline) se quiser usar OpenAI

Requisitos:
    - Coluna properties.embedding agora vector(1536) se migrado para OpenAI
    - Modelo OpenAI: text-embedding-3-small (1536) OU fallback local all-MiniLM-L6-v2 (384 padded)
  - SUPABASE_URL / SUPABASE_SERVICE_KEY definidos

Estratégia:
  1. Buscar propriedades com embedding NULL em lotes
  2. Gerar embedding baseado em "title + description" (mesma lógica do upsert_property)
  3. Upsert em lote (on_conflict=property_id) para velocidade
  4. Repetir até não restar linhas

Seguro para reexecutar: só afeta linhas com embedding NULL.
"""

from __future__ import annotations
import os
import time
from datetime import datetime
from typing import List, Dict

from sentence_transformers import SentenceTransformer

# Ajustar sys.path para permitir import 'app.*' quando executado diretamente a partir da raiz
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.supabase_client import supabase_client

USE_OPENAI = os.getenv("USE_OPENAI_EMBEDDINGS", "1") == "1"  # herdado da stack
EXPECTED_DIM = 1536 if USE_OPENAI else 384
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
REPROCESS_WRONG_DIM = os.getenv("REPROCESS_WRONG_DIM", "1") == "1"  # reprocessar vetores com dimensão divergente

def _load_model() -> SentenceTransformer:
    supabase_client.ensure_client()
    if supabase_client.embedding_model:
        return supabase_client.embedding_model
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')  # fallback local 384
    supabase_client.embedding_model = model
    return model

def _fetch_batch_missing() -> List[Dict]:
    base = supabase_client.client.table('properties') \
        .select('id, property_id, title, description')

    # Filtro principal: embeddings ausentes
    query = base.is_('embedding', 'null')

    # Opcional: também pegar registros com dimensão divergente (Postgres não expõe vector_dims nativamente via client python)
    # Estratégia: segundo passo se não houver NULLs, buscar um pequeno conjunto e checar comprimento via retorno em lote.
    rows = query.limit(BATCH_SIZE).execute().data or []
    if not rows and REPROCESS_WRONG_DIM:
        # Buscar alguns registros para inspeção (heurística: pegar primeiros 200 com embedding não nulo e medir)
        probe = supabase_client.client.table('properties') \
            .select('id, property_id, title, description, embedding') \
            .limit(BATCH_SIZE) \
            .execute().data or []
        wrong = []
        for r in probe:
            emb = r.get('embedding')
            if isinstance(emb, list) and len(emb) != EXPECTED_DIM:
                wrong.append({k: r.get(k) for k in ('id','property_id','title','description')})
        rows = wrong

    for r in rows:
        if not r.get('title'):
            r['title'] = f"Imóvel {r.get('property_id','sem-id')}"
        if r.get('description') is None:
            r['description'] = ''
    return rows

def _build_text(row: Dict) -> str:
    title = (row.get('title') or '').strip()
    desc = (row.get('description') or '').strip()
    return f"{title} {desc}".strip()

def main():
    start_all = time.time()
    model = _load_model()
    processed = 0
    loops = 0

    print(f"== Backfill embeddings (expected_dim={EXPECTED_DIM}, openai={USE_OPENAI}) ==")
    print(f"Batch size: {BATCH_SIZE} | Dry-run: {DRY_RUN} | Reprocess wrong dim: {REPROCESS_WRONG_DIM}")

    while True:
        loops += 1
        batch = _fetch_batch_missing()
        if not batch:
            break
        print(f"Lote {loops}: {len(batch)} registros sem embedding")

        texts: List[str] = [_build_text(row) for row in batch]
        # Evitar strings vazias (substituir por ID para estabilidade mínima)
        texts = [t if t else row.get('property_id', '') for t, row in zip(texts, batch)]

        # Gerar embeddings: se OpenAI ativo e cliente disponível usar supabase_client._generate_embedding (1 a 1 para manejar exceções/padding)
        embeddings: List[List[float]] = []
        if USE_OPENAI and getattr(supabase_client, 'openai_client', None):
            gen = getattr(supabase_client, '_generate_embedding', None)
            if callable(gen):
                for text in texts:
                    vec = gen(text)
                    if not vec:
                        # fallback local manual
                        local_vec = model.encode([text])[0].tolist()
                        if len(local_vec) < EXPECTED_DIM:
                            local_vec.extend([0.0]*(EXPECTED_DIM-len(local_vec)))
                        elif len(local_vec) > EXPECTED_DIM:
                            local_vec = local_vec[:EXPECTED_DIM]
                        vec = local_vec
                    embeddings.append(vec)
            else:
                # fallback para encode em lote local + padding
                local_batch = model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
                for lb in local_batch:
                    if len(lb) < EXPECTED_DIM:
                        lb.extend([0.0]*(EXPECTED_DIM-len(lb)))
                    elif len(lb) > EXPECTED_DIM:
                        lb = lb[:EXPECTED_DIM]
                    embeddings.append(lb)
        else:
            # Modo somente local (dim 384 ou schema legado)
            embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
            # Validar dimensão
            if any(len(vec) != EXPECTED_DIM for vec in embeddings):
                raise RuntimeError("Dimensão inesperada de embedding gerada – ajuste EXPECTED_DIM ou modelo.")

        updates = []
        timestamp = datetime.utcnow().isoformat()
        for row, emb in zip(batch, embeddings):
            # Atualizar pelo id (evita caminho de inserção que exige todos NOT NULL)
            updates.append({
                'id': row['id'],
                'embedding': emb,
                'updated_at': timestamp
            })

        if DRY_RUN:
            processed += len(batch)
            print(f"(dry-run) Preparado para upsert {len(batch)} rows")
        else:
            # Upsert em blocos menores se muito grande (aqui lote já pequeno)
            # Executar updates individualmente em blocos (supabase python ainda não tem batch update nativo)
            # Para reduzir round-trips, tentar dividir em sub-lotes
            chunk = 25
            for i in range(0, len(updates), chunk):
                slice_rows = updates[i:i+chunk]
                for row_update in slice_rows:
                    supabase_client.client.table('properties') \
                        .update({
                            'embedding': row_update['embedding'],
                            'updated_at': row_update['updated_at']
                        }) \
                        .eq('id', row_update['id']) \
                        .execute()
            processed += len(batch)
            print(f"✓ Updated embeddings para {len(batch)} registros")

        # Se o último lote veio menor que o tamanho pedido, pode ser que acabou
        if len(batch) < BATCH_SIZE:
            # Confirmar próxima iteração (pode ter corrida); se vazio, sai
            continue

    elapsed = time.time() - start_all
    print(f"Concluído. Embeddings processados: {processed} em {elapsed:.2f}s")
    if DRY_RUN:
        print("Nenhuma linha foi alterada (DRY_RUN=1). Remova a flag para executar.")

if __name__ == '__main__':
    main()

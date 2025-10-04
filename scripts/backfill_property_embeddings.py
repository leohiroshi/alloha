"""Backfill de embeddings para propriedades sem vetor.

Uso:
  python scripts/backfill_property_embeddings.py

Flags via env:
  BATCH_SIZE=50            # tamanho do lote
  DRY_RUN=1                # não grava, só mostra quantos seriam processados
  USE_OPENAI_EMBEDDINGS=1  # (já aproveita mesma flag do rag_pipeline) se quiser usar OpenAI

Requisitos:
  - Coluna properties.embedding deve ser vector(384)
  - Modelo local: sentence-transformers/all-MiniLM-L6-v2
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

EXPECTED_DIM = 384
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
USE_OPENAI = os.getenv("USE_OPENAI_EMBEDDINGS", "0") == "1"  # respeita flag global, mas aqui default 0

def _load_model() -> SentenceTransformer:
    if supabase_client.embedding_model:
        return supabase_client.embedding_model
    # Garantir lazy init do client (env já carregado)
    supabase_client.ensure_client()
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    supabase_client.embedding_model = model
    return model

def _fetch_batch_missing() -> List[Dict]:
    # Buscar campos necessários + id para permitir update direto sem reinserir título nulo
    resp = supabase_client.client.table('properties') \
        .select('id, property_id, title, description') \
        .is_('embedding', 'null') \
        .limit(BATCH_SIZE) \
        .execute()
    rows = resp.data or []
    # Garantir fallback de título (NOT NULL) caso registros legados tenham vindo quebrados
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

    print(f"== Backfill embeddings (dim={EXPECTED_DIM}) ==")
    print(f"Batch size: {BATCH_SIZE} | Dry-run: {DRY_RUN}")

    while True:
        loops += 1
        batch = _fetch_batch_missing()
        if not batch:
            break
        print(f"Lote {loops}: {len(batch)} registros sem embedding")

        texts: List[str] = [_build_text(row) for row in batch]
        # Evitar strings vazias (substituir por ID para estabilidade mínima)
        texts = [t if t else row.get('property_id', '') for t, row in zip(texts, batch)]

        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
        # Sanity check dimensão
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

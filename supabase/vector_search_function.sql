-- Função para busca vetorial no Supabase usando pgvector
-- Execute este SQL no SQL Editor do Supabase Dashboard

CREATE OR REPLACE FUNCTION vector_property_search(
  query_embedding vector(384),
  match_threshold float DEFAULT 1.5,
  max_results int DEFAULT 10
)
RETURNS TABLE (
  id uuid,
  property_id text,
  content text,
  metadata jsonb,
  distance float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    pe.id,
    pe.property_id,
    pe.content,
    pe.metadata,
    (pe.embedding <-> query_embedding) AS distance
  FROM property_embeddings pe
  WHERE (pe.embedding <-> query_embedding) < match_threshold
  ORDER BY distance
  LIMIT max_results;
END;
$$;

-- Comentário sobre a função:
-- Esta função usa o operador <-> do pgvector para calcular distância cosseno
-- Quanto MENOR a distância, mais similar é o conteúdo
-- match_threshold: limite de distância (default 1.5)
-- max_results: número máximo de resultados (default 10)

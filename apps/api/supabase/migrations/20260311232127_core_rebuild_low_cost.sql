-- Core rebuild: low-cost schema alignment
-- - properties ingestion metadata columns
-- - vector dimension standardization to 384
-- - canonical vector search RPC

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE IF EXISTS public.properties
  ADD COLUMN IF NOT EXISTS source_updated_at timestamptz,
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS last_seen_at timestamptz,
  ADD COLUMN IF NOT EXISTS is_deleted boolean DEFAULT false;

-- Keep lookup/query costs low
CREATE INDEX IF NOT EXISTS idx_properties_content_hash ON public.properties(content_hash);
CREATE INDEX IF NOT EXISTS idx_properties_last_seen_at ON public.properties(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_properties_is_deleted ON public.properties(is_deleted);

-- Standardize vectors to 384 dims for local embeddings.
-- Existing vectors are nulled to guarantee type conversion safety.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='properties' AND column_name='embedding'
  ) THEN
    UPDATE public.properties SET embedding = NULL WHERE embedding IS NOT NULL;
    ALTER TABLE public.properties
      ALTER COLUMN embedding TYPE vector(384)
      USING NULL::vector(384);
  END IF;
END $$;

DROP INDEX IF EXISTS public.idx_properties_embedding;
CREATE INDEX IF NOT EXISTS idx_properties_embedding
  ON public.properties
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='embedding_cache' AND column_name='embedding'
  ) THEN
    UPDATE public.embedding_cache SET embedding = NULL WHERE embedding IS NOT NULL;
    ALTER TABLE public.embedding_cache
      ALTER COLUMN embedding TYPE vector(384)
      USING NULL::vector(384);
  END IF;
END $$;

DROP INDEX IF EXISTS public.idx_cache_embedding;
CREATE INDEX IF NOT EXISTS idx_cache_embedding
  ON public.embedding_cache
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 50);

DROP FUNCTION IF EXISTS public.vector_property_search(vector(1536), double precision, integer);
DROP FUNCTION IF EXISTS public.vector_property_search(vector(384), double precision, integer);
DROP FUNCTION IF EXISTS public.vector_property_search(vector, double precision, integer);

CREATE OR REPLACE FUNCTION public.vector_property_search(
  query_embedding vector(384),
  match_threshold double precision DEFAULT 0.30,
  match_count integer DEFAULT 10
)
RETURNS TABLE (
  property_id text,
  title text,
  description text,
  url text,
  price numeric,
  bedrooms_int integer,
  similarity double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    p.property_id,
    p.title,
    p.description,
    p.url,
    p.price,
    p.bedrooms AS bedrooms_int,
    1 - (p.embedding <=> query_embedding) AS similarity
  FROM public.properties p
  WHERE p.embedding IS NOT NULL
    AND COALESCE(p.is_deleted, false) = false
    AND COALESCE(p.status, 'active') = 'active'
    AND (1 - (p.embedding <=> query_embedding)) >= match_threshold
  ORDER BY p.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Keep hybrid function signature consistent with 384 embeddings.
CREATE OR REPLACE FUNCTION public.hybrid_property_search(
    query_embedding vector(384),
    query_text text,
    match_threshold float DEFAULT 0.7,
    max_results integer DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    property_id text,
    title text,
    description text,
    price decimal,
    similarity_score float,
    text_rank float,
    combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.property_id,
        p.title,
        p.description,
        p.price,
        1 - (p.embedding <=> query_embedding) AS similarity_score,
        ts_rank(to_tsvector('portuguese', p.title || ' ' || COALESCE(p.description, '')),
                plainto_tsquery('portuguese', query_text)) AS text_rank,
        (0.7 * (1 - (p.embedding <=> query_embedding))) +
        (0.3 * ts_rank(to_tsvector('portuguese', p.title || ' ' || COALESCE(p.description, '')),
                       plainto_tsquery('portuguese', query_text))) AS combined_score
    FROM public.properties p
    WHERE COALESCE(p.status, 'active') = 'active'
      AND COALESCE(p.is_deleted, false) = false
      AND p.embedding IS NOT NULL
      AND (1 - (p.embedding <=> query_embedding)) > match_threshold
    ORDER BY combined_score DESC
    LIMIT max_results;
END;
$$;

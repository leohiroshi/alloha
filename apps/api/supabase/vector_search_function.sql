-- Canonical vector search function for properties table (pgvector 384).
-- Keep this file aligned with migrations that manage vector dimensions.

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

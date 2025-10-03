-- ====================================================================
-- ALLOHA - SUPABASE SCHEMA
-- PostgreSQL 15 + pgvector + pg_cron
-- ====================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- Full-text search

-- ====================================================================
-- TABLE: properties
-- Imóveis com suporte a vector search
-- ====================================================================
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    price DECIMAL(12,2),
    address JSONB, -- { street, number, district, city, state, zipcode }
    bedrooms INTEGER,
    bathrooms INTEGER,
    area_m2 DECIMAL(10,2),
    property_type TEXT, -- apartment, house, commercial, land
    status TEXT DEFAULT 'active', -- active, sold, rented, inactive
    images JSONB, -- Array de URLs
    amenities TEXT[],
    owner_info JSONB,
    source TEXT, -- sciensa, sincroniza_imoveis, manual
    external_id TEXT,
    last_sync_at TIMESTAMPTZ,
    embedding vector(768), -- Embedding para busca semântica
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para properties
CREATE INDEX idx_properties_property_id ON properties(property_id);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_created ON properties(created_at DESC);
CREATE INDEX idx_properties_embedding ON properties USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_properties_fulltext ON properties USING gin(to_tsvector('portuguese', title || ' ' || COALESCE(description, '')));

-- ====================================================================
-- TABLE: conversations
-- Conversações do WhatsApp com state machine
-- ====================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT NOT NULL,
    user_name TEXT,
    state TEXT DEFAULT 'pending', -- pending, qualified, nurture, closed
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    urgency_score INTEGER DEFAULT 1, -- 1-5
    metadata JSONB, -- Dados extras como tags, notes, etc
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para conversations
CREATE INDEX idx_conversations_phone ON conversations(phone_number);
CREATE INDEX idx_conversations_state ON conversations(state);
CREATE INDEX idx_conversations_urgency ON conversations(urgency_score DESC);
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);

-- ====================================================================
-- TABLE: messages
-- Mensagens trocadas (com TTL de 90 dias)
-- ====================================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction TEXT NOT NULL, -- inbound, outbound
    content TEXT,
    message_type TEXT DEFAULT 'text', -- text, voice, image, document
    whatsapp_message_id TEXT UNIQUE,
    status TEXT DEFAULT 'sent', -- sent, delivered, read, failed
    metadata JSONB, -- voice_duration, image_url, etc
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para messages
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_whatsapp_id ON messages(whatsapp_message_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- ====================================================================
-- TABLE: leads
-- Leads qualificados com histórico
-- ====================================================================
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT,
    budget_min DECIMAL(12,2),
    budget_max DECIMAL(12,2),
    preferred_locations TEXT[],
    requirements JSONB, -- bedrooms, property_types, amenities
    qualification_score INTEGER DEFAULT 0, -- 0-100
    source TEXT, -- whatsapp, website, referral
    assigned_broker TEXT,
    status TEXT DEFAULT 'new', -- new, contacted, qualified, converted, lost
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para leads
CREATE INDEX idx_leads_phone ON leads(phone_number);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_qualification ON leads(qualification_score DESC);
CREATE INDEX idx_leads_created ON leads(created_at DESC);

-- ====================================================================
-- TABLE: urgency_alerts
-- Alertas de urgência para corretores
-- ====================================================================
CREATE TABLE IF NOT EXISTS urgency_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    urgency_level INTEGER NOT NULL, -- 1-5
    reason TEXT NOT NULL,
    indicators JSONB, -- Lista de indicadores detectados
    notified_at TIMESTAMPTZ,
    broker_response TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para urgency_alerts
CREATE INDEX idx_urgency_conversation ON urgency_alerts(conversation_id);
CREATE INDEX idx_urgency_level ON urgency_alerts(urgency_level DESC);
CREATE INDEX idx_urgency_unresolved ON urgency_alerts(resolved_at) WHERE resolved_at IS NULL;

-- ====================================================================
-- TABLE: scheduled_visits
-- Agendamentos automáticos via Google Calendar
-- ====================================================================
CREATE TABLE IF NOT EXISTS scheduled_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    calendar_event_id TEXT, -- Google Calendar Event ID
    status TEXT DEFAULT 'scheduled', -- scheduled, confirmed, completed, cancelled
    confirmation_sent_at TIMESTAMPTZ,
    reminder_sent_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para scheduled_visits
CREATE INDEX idx_visits_conversation ON scheduled_visits(conversation_id);
CREATE INDEX idx_visits_scheduled_at ON scheduled_visits(scheduled_at);
CREATE INDEX idx_visits_status ON scheduled_visits(status);

-- ====================================================================
-- TABLE: voice_interactions
-- Histórico de interações de voz (PTT)
-- ====================================================================
CREATE TABLE IF NOT EXISTS voice_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    direction TEXT NOT NULL, -- inbound, outbound
    audio_url TEXT,
    transcription TEXT,
    response_text TEXT,
    duration_seconds INTEGER,
    model_used TEXT, -- whisper-1, tts-1-hd
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para voice_interactions
CREATE INDEX idx_voice_conversation ON voice_interactions(conversation_id, created_at DESC);
CREATE INDEX idx_voice_created ON voice_interactions(created_at DESC);

-- ====================================================================
-- TABLE: white_label_sites
-- Sites white-label gerados automaticamente
-- ====================================================================
CREATE TABLE IF NOT EXISTS white_label_sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id TEXT UNIQUE NOT NULL,
    domain TEXT UNIQUE NOT NULL,
    broker_name TEXT NOT NULL,
    broker_email TEXT,
    broker_phone TEXT,
    logo_url TEXT,
    primary_color TEXT DEFAULT '#3B82F6',
    secondary_color TEXT DEFAULT '#10B981',
    template_id TEXT DEFAULT 'modern_minimal',
    cloudflare_zone_id TEXT,
    deployment_status TEXT DEFAULT 'pending', -- pending, deploying, active, failed
    deployed_at TIMESTAMPTZ,
    analytics JSONB, -- Views, clicks, leads, etc
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para white_label_sites
CREATE INDEX idx_whitelabel_domain ON white_label_sites(domain);
CREATE INDEX idx_whitelabel_status ON white_label_sites(deployment_status);

-- ====================================================================
-- TABLE: embedding_cache
-- Cache de embeddings para otimização
-- ====================================================================
CREATE TABLE IF NOT EXISTS embedding_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    text_hash TEXT UNIQUE NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(768),
    model TEXT DEFAULT 'all-MiniLM-L6-v2',
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para embedding_cache
CREATE INDEX idx_cache_hash ON embedding_cache(text_hash);
CREATE INDEX idx_cache_expires ON embedding_cache(expires_at);
CREATE INDEX idx_cache_embedding ON embedding_cache USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ====================================================================
-- TABLE: webhook_idempotency
-- Prevenção de duplicação de webhooks
-- ====================================================================
CREATE TABLE IF NOT EXISTS webhook_idempotency (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint TEXT UNIQUE NOT NULL,
    whatsapp_message_id TEXT,
    status TEXT DEFAULT 'processing', -- processing, completed, failed
    processed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes para webhook_idempotency
CREATE INDEX idx_idempotency_fingerprint ON webhook_idempotency(fingerprint);
CREATE INDEX idx_idempotency_expires ON webhook_idempotency(expires_at);

-- ====================================================================
-- FUNCTIONS: Auto-update timestamps
-- ====================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para auto-update
CREATE TRIGGER properties_updated_at BEFORE UPDATE ON properties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER scheduled_visits_updated_at BEFORE UPDATE ON scheduled_visits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER white_label_sites_updated_at BEFORE UPDATE ON white_label_sites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================
-- FUNCTIONS: TTL Cleanup (via pg_cron)
-- ====================================================================

-- Cleanup de mensagens antigas (90 dias)
CREATE OR REPLACE FUNCTION cleanup_old_messages()
RETURNS void AS $$
BEGIN
    DELETE FROM messages 
    WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Cleanup de cache expirado
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM embedding_cache 
    WHERE expires_at < NOW();
    
    DELETE FROM webhook_idempotency 
    WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Agendar limpezas diárias às 3h AM
SELECT cron.schedule('cleanup-messages', '0 3 * * *', 'SELECT cleanup_old_messages()');
SELECT cron.schedule('cleanup-cache', '0 3 * * *', 'SELECT cleanup_expired_cache()');

-- ====================================================================
-- FUNCTIONS: Busca híbrida (Vector + Full-text)
-- ====================================================================
CREATE OR REPLACE FUNCTION hybrid_property_search(
    query_embedding vector(768),
    query_text TEXT,
    match_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    property_id TEXT,
    title TEXT,
    description TEXT,
    price DECIMAL,
    similarity_score FLOAT,
    text_rank FLOAT,
    combined_score FLOAT
) AS $$
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
    FROM properties p
    WHERE 
        p.status = 'active' AND
        (1 - (p.embedding <=> query_embedding)) > match_threshold
    ORDER BY combined_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- ====================================================================
-- ROW LEVEL SECURITY (RLS)
-- ====================================================================

-- Enable RLS em todas as tabelas
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE urgency_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE white_label_sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE embedding_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_idempotency ENABLE ROW LEVEL SECURITY;

-- Política: Service role pode fazer tudo
CREATE POLICY "Service role has full access" ON properties FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON conversations FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON messages FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON leads FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON urgency_alerts FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON scheduled_visits FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON voice_interactions FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON white_label_sites FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON embedding_cache FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role has full access" ON webhook_idempotency FOR ALL USING (auth.role() = 'service_role');

-- ====================================================================
-- VIEWS: Analytics & Monitoring
-- ====================================================================

-- View: Estatísticas de urgência
CREATE OR REPLACE VIEW urgency_stats AS
SELECT 
    DATE(created_at) AS date,
    urgency_level,
    COUNT(*) AS alert_count,
    COUNT(CASE WHEN resolved_at IS NOT NULL THEN 1 END) AS resolved_count,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/60)::INTEGER AS avg_resolution_minutes
FROM urgency_alerts
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), urgency_level
ORDER BY date DESC, urgency_level DESC;

-- View: Conversões de leads
CREATE OR REPLACE VIEW lead_conversion_funnel AS
SELECT 
    DATE(created_at) AS date,
    status,
    COUNT(*) AS count,
    AVG(qualification_score)::INTEGER AS avg_qualification
FROM leads
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), status
ORDER BY date DESC;

-- View: Performance de voz
CREATE OR REPLACE VIEW voice_performance AS
SELECT 
    DATE(created_at) AS date,
    direction,
    COUNT(*) AS interaction_count,
    AVG(duration_seconds)::INTEGER AS avg_duration_seconds,
    AVG(processing_time_ms)::INTEGER AS avg_processing_ms
FROM voice_interactions
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), direction
ORDER BY date DESC;

-- ====================================================================
-- INITIAL DATA / SEED
-- ====================================================================

-- Inserir template padrão de white-label
INSERT INTO white_label_sites (site_id, domain, broker_name, template_id, deployment_status)
VALUES ('demo', 'demo.alloha.com.br', 'Demo Broker', 'modern_minimal', 'active')
ON CONFLICT (site_id) DO NOTHING;

-- ====================================================================
-- GRANTS: Permissões para roles
-- ====================================================================

-- Grant para anon (acesso público limitado)
GRANT SELECT ON properties TO anon;
GRANT SELECT ON white_label_sites TO anon;

-- Grant para authenticated (usuários autenticados)
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;

-- ====================================================================
-- COMPLETE ✅
-- ====================================================================
-- Schema pronto para migração!
-- Execute: supabase db push --file scripts/supabase_schema.sql
-- ====================================================================

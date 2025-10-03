# Alloha AI Platform (Supabase Edition)

Plataforma de IA imobiliária com arquitetura 100% em Supabase (Postgres + pgvector).

## 🔎 Principais Sistemas

| Sistema | Descrição | Arquivo / Pasta |
|---------|-----------|-----------------|
| RAG Pipeline | Busca semântica + híbrida (vector + full-text) | `app/services/rag_pipeline.py` |
| Dual Stack Intelligence | Orquestração Fine-tune + RAG | `app/services/dual_stack_intelligence.py` |
| Live Pricing System | Upsert/refresh de imóveis + embeddings | `app/services/live_pricing_system.py` |
| Urgency Score System | Detecção de urgência e alertas | `app/services/urgency_score_system.py` |
| Autonomous Follow-up | Agendamentos e follow-up (Google Calendar) | `app/services/autonomous_followup.py` |
| Voice PTT System | Interações de voz (Whisper / TTS) + preferências | `app/services/voice_ptt_system.py` |
| White Label System | Provisionamento instantâneo de sites white-label | `app/services/white_label_system.py` |
| Dataset Living Loop | Manutenção incremental de dataset de fine-tune | `app/services/dataset_living_loop.py` |
| Embedding Cache | Cache local de embeddings para reduzir chamadas | `app/services/embedding_cache.py` |

## 🗄️ Banco de Dados (Supabase)

Principais tabelas (resumido):

```
properties (property_id, title, description, price, status, updated_at, embedding ...)
property_embeddings (id, property_id, content, metadata, embedding)
conversations (id, phone_number, state, urgency_score, last_message_at, metadata)
messages (id, conversation_id, direction, content, created_at)
scheduled_visits (id, conversation_id, scheduled_for, status)
urgency_alerts (id, phone, urgency_score, reasons, detected_at)
broker_notifications (id, alert_id, status, sent_at)
white_label_sites (id, subdomain, config, created_at)
whatsapp_integrations (id, site_id, phone_number, status)
voice_interactions (id, phone_number, transcript, audio_url, created_at)
user_preferences (id, phone_number, key, value, updated_at)
embedding_cache (hash, embedding, created_at)
```

Funções SQL esperadas:
- `vector_property_search(query_embedding, match_threshold, max_results)`
- `hybrid_property_search(query_embedding, query_text, match_threshold, max_results)`

## 🧠 Fluxo RAG + Dual Stack
1. Usuário envia mensagem (WhatsApp / canal) → cria/atualiza conversa.
2. Sistema decide: usar contexto fine-tune + RAG híbrido.
3. Buscas vetoriais + full-text via funções RPC (`vector_property_search`, `hybrid_property_search`).
4. Reclassificação / formatação / resposta.
5. Urgência analisada; alertas gerados se score >= 3.

## 🗣️ Voz (Opcional)
- Dependências: `pydub`, `SpeechRecognition` (podem ser removidas se não usar).
- Interações persistidas em `voice_interactions`.
- Preferências de voz por usuário em `user_preferences` (`voice_enabled`).

## 🚨 Urgência
- Regex + histórico → score (1–5).
- Score >=4 gera notificação imediata via `broker_notifications`.
- Persistência em `urgency_alerts`.

## 🔁 Dataset Living Loop
Monitora volume/variedade de mensagens e injeta exemplos no dataset de fine-tune (`*.jsonl`) com balanceamento (voz, typos, urgência, follow-up, pricing).

## 🧪 Testes / Scripts Úteis
Localização em `scripts/`:
- `expand_dataset.py` – expansão sintética.
- `prepare_finetune_dataset.py` – consolidação + split.
- `test_latency_warmup.py` – aquecimento e medição de resposta.
- `test_finetuned_model.py` – sanity check do modelo fine-tunado.

## 🧩 Arquitetura Simplificada
```
User → WhatsApp → webhook → supabase_client → conversations/messages
							   │
							   ├─ dual_stack_intelligence
							   │      ├─ rag_pipeline (vector + hybrid search)
							   │      ├─ urgency_score_system
							   │      ├─ live_pricing_system (garante fresh data)
							   │      └─ voice_ptt_system (se voz habilitada)
							   │
							   └→ resposta + persistência + métricas
```

## 🚀 Setup Rápido
1. Criar `.env` com:
```
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
OPENAI_API_KEY=...
```
2. Instalar dependências:
```
pip install -r requirements.txt
```
3. Criar funções SQL (pgvector) no Supabase.
4. Executar serviços (ex: FastAPI se existir endpoint principal em `app/main.py`).

## 🧹 Migração Firebase -> Supabase
Status: Concluída.
- Removido: `firebase_service.py`, coleções Firestore, referência a `vectors` Firestore.
- Substituído por tabelas e RPC functions no Supabase.

## ✅ Checklist Pós-Migração
- [x] Removido código Firestore
- [x] RAG usa pgvector
- [x] Embeddings no upsert de propriedade
- [x] Urgência persiste em tabela própria
- [x] Voz opcional desacoplada
- [x] Dataset incremental ativo

## 🔒 Observações
- Evite expor `SUPABASE_SERVICE_KEY` em clientes públicos.
- Usar Row Level Security + policies (não incluídas aqui) para produção.

## 📄 Licença
Uso interno / proprietário (ajuste conforme necessidade).

---
Contribuições e melhorias são bem-vindas – abrir PR descrevendo impacto e métricas se possível.

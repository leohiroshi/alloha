<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/OpenAI-GPT--4-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI"/>
  <img src="https://img.shields.io/badge/Redis-Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"/>
</p>

<h1 align="center">🏠 Alloha AI Platform</h1>

<p align="center">
  <strong>Enterprise-grade AI-powered Real Estate Assistant with WhatsApp Integration</strong>
</p>

<p align="center">
  A production-ready conversational AI platform that combines RAG (Retrieval-Augmented Generation), 
  fine-tuned LLMs, and real-time property data to deliver intelligent real estate assistance via WhatsApp.
</p>

---

## 🎯 Overview

**Alloha** is a full-stack AI platform designed to revolutionize real estate customer service. It processes natural language queries, performs semantic property searches, and delivers personalized recommendations—all through WhatsApp's familiar interface.

### Key Highlights

- 🤖 **Dual-Stack AI**: Combines fine-tuned GPT models with RAG for optimal response quality
- 🔍 **Hybrid Search**: Vector similarity + full-text search using pgvector
- ⚡ **Real-time Sync**: Automated property scraping and embedding updates
- 🎤 **Voice Support**: Process voice messages with Whisper transcription
- 📊 **Urgency Detection**: ML-based lead scoring and prioritization
- 🏷️ **White-Label Ready**: Multi-tenant architecture for B2B deployment

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ALLOHA PLATFORM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────┐     ┌──────────────────────────────────────────────────┐    │
│    │ WhatsApp │────▶│              FastAPI Backend                      │    │
│    │   User   │◀────│                                                   │    │
│    └──────────┘     │  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │    │
│                     │  │ Intelligent │  │    RAG      │  │  Urgency  │ │    │
│                     │  │     Bot     │──│  Pipeline   │──│  Scoring  │ │    │
│                     │  └─────────────┘  └─────────────┘  └───────────┘ │    │
│                     │         │                │               │       │    │
│                     │         ▼                ▼               ▼       │    │
│                     │  ┌─────────────────────────────────────────────┐ │    │
│                     │  │           Dual-Stack Intelligence           │ │    │
│                     │  │     (Fine-tuned GPT + RAG Orchestration)    │ │    │
│                     │  └─────────────────────────────────────────────┘ │    │
│                     └──────────────────────────────────────────────────┘    │
│                                          │                                   │
│                     ┌────────────────────┼────────────────────┐              │
│                     ▼                    ▼                    ▼              │
│              ┌────────────┐      ┌─────────────┐      ┌─────────────┐       │
│              │  Supabase  │      │    Redis    │      │   OpenAI    │       │
│              │ PostgreSQL │      │    Cache    │      │     API     │       │
│              │ + pgvector │      │             │      │             │       │
│              └────────────┘      └─────────────┘      └─────────────┘       │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Optional: Local LLM Sidecar (Llama 3) for cost-optimized MoE routing       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Core AI Capabilities

| Feature | Description |
|---------|-------------|
| **RAG Pipeline** | Hybrid semantic + full-text search with pgvector embeddings |
| **Dual-Stack Intelligence** | Orchestrates fine-tuned models with RAG context |
| **Live Pricing System** | Real-time property data sync with automatic re-embedding |
| **Urgency Detection** | NLP-based urgency scoring (1-5) with instant broker alerts |
| **Voice Processing** | Whisper-powered PTT message transcription |
| **Session Memory** | Contextual conversation tracking with TTL-based cache |

### Infrastructure

| Component | Technology |
|-----------|------------|
| **API Framework** | FastAPI with async/await patterns |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **Caching** | Redis with graceful in-memory fallback |
| **Containerization** | Docker + Docker Compose |
| **Embeddings** | OpenAI text-embedding-3-small (1536-dim) |
| **LLM** | Fine-tuned GPT-4.1-mini |

### Advanced Systems

- 📅 **Autonomous Follow-up**: Google Calendar integration for visit scheduling
- 🏢 **White-Label System**: Instant multi-tenant site provisioning
- 📈 **Dataset Living Loop**: Continuous fine-tuning data augmentation
- 🔄 **Webhook Idempotency**: Guaranteed exactly-once message processing

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Supabase account (free tier works)
- OpenAI API key
- WhatsApp Business API access

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/leohiroshi/alloha.git
cd alloha
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Run with Docker Compose**
```bash
docker compose up -d
```

4. **Or run locally**
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. **Set up database**
```bash
# Run the SQL scripts in Supabase SQL Editor
# See: supabase/supabase_schema.sql
# See: supabase/vector_search_function.sql
```

### Verify Installation

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", ...}
```

---

## 📁 Project Structure

```
alloha/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── models/                    # Pydantic models & data schemas
│   └── services/
│       ├── intelligent_bot.py     # Core conversation handler
│       ├── rag_pipeline.py        # RAG + vector search orchestration
│       ├── dual_stack_intelligence.py  # Fine-tune + RAG fusion
│       ├── supabase_client.py     # Database operations & embeddings
│       ├── urgency_score_system.py    # Lead prioritization
│       ├── live_pricing_system.py     # Real-time property sync
│       ├── voice_ptt_system.py        # Voice message processing
│       ├── white_label_system.py      # Multi-tenant provisioning
│       ├── property_scraper.py        # Automated data collection
│       └── ...                        # Additional services
├── scripts/
│   ├── expand_dataset.py          # Synthetic data augmentation
│   ├── prepare_finetune_dataset.py    # Training data preparation
│   └── backfill_property_embeddings.py    # Embedding migration
├── supabase/
│   ├── supabase_schema.sql        # Database schema
│   └── vector_search_function.sql # pgvector search functions
├── datasets/
│   └── finetune_dataset_3k.jsonl  # Training data samples
├── docker-compose.yml             # Multi-container orchestration
├── Dockerfile                     # Main application container
├── Dockerfile.sidecar-llm         # Optional local LLM container
└── requirements.txt               # Python dependencies
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | ✅ |
| `OPENAI_API_KEY` | OpenAI API key | ✅ |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp Business token | ✅ |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business phone ID | ✅ |
| `REDIS_URL` | Redis connection string | ❌ |
| `ENABLE_LOCAL_MOE` | Enable local LLM routing | ❌ |

### Database Schema

The platform uses Supabase with pgvector extension. Key tables:

- `properties` - Real estate listings with embeddings
- `conversations` - User conversation state & history
- `messages` - Individual message records
- `urgency_alerts` - High-priority lead notifications
- `scheduled_visits` - Property visit appointments

---

## 🐳 Docker Deployment

### Production Build

```bash
# Build all services
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f backend

# Scale workers (if needed)
docker compose up -d --scale backend=3
```

### With Local LLM (Cost Optimization)

```bash
# Enable MoE architecture with local Llama 3
ENABLE_LOCAL_MOE=true docker compose up -d
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with service status |
| `/webhook` | GET | WhatsApp webhook verification |
| `/webhook` | POST | Incoming message handler |
| `/api/properties/search` | POST | Property search API |
| `/api/conversations/{phone}` | GET | Conversation history |

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/ -v

# Test specific module
pytest tests/test_rag_pipeline.py -v

# Coverage report
pytest --cov=app tests/
```

---

## 📈 Performance Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Response latency (P95) | < 3s | ~2.1s |
| Vector search time | < 500ms | ~180ms |
| Concurrent users | 100+ | ✅ |
| Uptime | 99.9% | ✅ |

---

## 🛣️ Roadmap

- [x] RAG Pipeline with pgvector
- [x] WhatsApp Business Integration
- [x] Urgency Detection System
- [x] Voice Message Support
- [x] Multi-tenant White-Label
- [x] Docker Containerization
- [x] Redis Caching Layer
- [ ] Local LLM MoE (Llama 3 sidecar)
- [ ] Analytics Dashboard
- [ ] A/B Testing Framework
- [ ] Multi-language Support

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Leonardo Hiroshi**

- GitHub: [@leohiroshi](https://github.com/leohiroshi)
- LinkedIn: [Leonardo Hiroshi](https://linkedin.com/in/leohiroshi)

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Supabase](https://supabase.com/) - Open source Firebase alternative
- [OpenAI](https://openai.com/) - GPT models and embeddings
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity for PostgreSQL

---

<p align="center">
  <strong>⭐ Star this repo if you find it useful!</strong>
</p>

## ✅ Checklist Pós-Migração
- [x] Removido código Firestore
- [x] RAG usa pgvector
- [x] Embeddings no upsert de propriedade
- [x] Urgência persiste em tabela própria
- [x] Voz opcional desacoplada
- [x] Dataset incremental ativo

## 🔒 Observações
## 🧰 Redis (Opcional)
Adicionado suporte opcional para Redis como camada de:

- Cache de sessão distribuído das propriedades já mostradas (evita repetir imóveis entre réplicas)
- Cache simples de embeddings (reduz chamadas repetidas a modelos de embedding)
- Rate limiting (controle por janela) e locks simples

### Variáveis de Ambiente
```
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_TLS=0                # 1 para usar rediss://
USE_REDIS_SESSION_CACHE=1  # desativar = 0
USE_REDIS_EMBED_CACHE=1    # desativar = 0
```

### Subir Localmente
```
docker run -d --name alloha-redis -p 6379:6379 redis:7-alpine
```

### Principais Arquivos
- `app/services/redis_client.py` – inicialização lazy + utilidades (get/set, rate_limit, locks)
- `app/services/session_cache.py` – agora assíncrono; usa Redis se disponível
- `app/services/embedding_cache.py` – tenta Redis antes de FAISS / in-memory
- `app/services/rate_limiter.py` – helper de rate limit

### Fallback
Se Redis indisponível: continua tudo em memória e logs indicam fallback (`Redis ... fallback`).

### Próximos Passos Sugeridos
- Métricas de hits/misses
- Locks distribuídos para backfill
- Chave de idempotência global para webhooks
- Monitor TTL dinâmico conforme carga

- Evite expor `SUPABASE_SERVICE_KEY` em clientes públicos.
- Usar Row Level Security + policies (não incluídas aqui) para produção.

## 📄 Licença
Uso interno / proprietário (ajuste conforme necessidade).

---
Contribuições e melhorias são bem-vindas – abrir PR descrevendo impacto e métricas se possível.

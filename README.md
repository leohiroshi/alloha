# Alloha 

Plataforma de assistente imobiliário inteligente com IA.

## Estrutura do Monorepo

```
alloha/
 apps/
    api/          # Backend Python/FastAPI
    web/          # Frontend Next.js
 packages/
    shared/       # Código compartilhado
 turbo.json        # Configuração Turborepo
```

## Stack

### Frontend (apps/web)
- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS
- Framer Motion

### Backend (apps/api)
- Python 3.11+
- FastAPI
- Supabase (PostgreSQL + Vector)
- OpenAI / RAG Pipeline
- WhatsApp Business API

## Desenvolvimento

### Pré-requisitos
- Node.js 20+
- Python 3.11+
- npm ou yarn

### Instalação

```bash
# Instalar dependências do monorepo
npm install

# Configurar ambiente do backend
cd apps/api
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Executando

```bash
# Frontend (http://localhost:3000)
npm run dev:web

# Backend (http://localhost:8000)
npm run dev:api

# Ambos simultaneamente
npm run dev
```

## Deploy

- **Frontend**: Vercel (auto-deploy de apps/web)
- **Backend**: Docker / Railway / Render

## Licença

MIT

# Cloud Run MVP

Este é o perfil recomendado para manter o backend da Alloha o mais perto possível de zero no free tier do Google Cloud.

## Perfil de custo

- `request-based billing`
- `min instances = 0`
- `max instances = 2`
- `cpu = 0.5`
- `memory = 512Mi`
- `concurrency = 20`
- `timeout = 30s`
- embeddings locais desligados
- scraper fallback desligado
- Redis opcional com fallback em memória

## Arquivos

- `Dockerfile.cloudrun`: container mínimo do backend core
- `requirements-cloudrun.txt`: dependências enxutas para produção
- `cloudrun.env.example.yaml`: variáveis de ambiente no formato do `gcloud run deploy --env-vars-file`
- `scripts/deploy_cloud_run.ps1`: script de build + deploy com os limites recomendados

## Pré-requisitos

1. Criar um projeto no Google Cloud com billing habilitado.
2. Habilitar:
   - Cloud Run
   - Cloud Build
   - Artifact Registry
3. Instalar o `gcloud`.

## Deploy sugerido

```powershell
$PROJECT_ID = "seu-project-id"
$REGION = "us-central1"
$SERVICE = "alloha-api"
$REPOSITORY = "cloud-run"
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$SERVICE:latest"

gcloud artifacts repositories create $REPOSITORY --repository-format=docker --location=$REGION --description="Alloha Cloud Run images"
gcloud builds submit . --tag $IMAGE
gcloud run deploy $SERVICE `
  --image $IMAGE `
  --region $REGION `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --cpu 0.5 `
  --memory 512Mi `
  --concurrency 20 `
  --timeout 30 `
  --min-instances 0 `
  --max-instances 2 `
  --env-vars-file cloudrun.env.yaml
```

Ou, se preferir, use o script:

```powershell
.\scripts\deploy_cloud_run.ps1 -ProjectId "seu-project-id"
```

## Variáveis mais importantes

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`
- `OPENROUTER_API_KEY`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `WEB_AUTH_SUCCESS_URL`

## Validação depois do deploy

Verifique:

- `/health`
- `/v1/system/status`

Esperado no perfil econômico:

- `deploy_profile = cloudrun_mvp`
- `scraper_fallback_enabled = false`
- `property_embeddings_enabled = false`
- `redis_memory_fallback_active = true` quando não houver Redis configurado

# Send Email Hook

Esta edge function substitui os emails padrao do Supabase Auth por emails enviados via Resend com branding da Alloha.

## O que ela cobre

- confirmacao de cadastro
- recuperacao de senha
- magic link
- convite
- alteracao de email

## Secrets esperados no projeto Supabase

- `RESEND_API_KEY`
- `AUTH_EMAIL_FROM`
- `AUTH_EMAIL_PRODUCT_NAME`
- `AUTH_SITE_URL`
- `SEND_EMAIL_HOOK_SECRET` opcional, mas recomendado

## Passos para ativar no projeto hospedado

1. Verifique o dominio no Resend.
2. Deploy da function `send-email`.
3. No dashboard do Supabase:
   - `Authentication` -> `Hooks`
   - habilite `Send Email`
   - URL: `https://<project-ref>.functions.supabase.co/send-email`
   - se usar secret no hook, replique o mesmo valor em `SEND_EMAIL_HOOK_SECRET`
4. Mantenha os redirects do app:
   - `/auth/callback`
   - `/reset-password`

## Observacao

O fluxo de confirmacao e recovery do frontend foi adaptado para aceitar `token_hash` + `type` nos links enviados por essa function.

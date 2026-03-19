# Supabase Email Templates

Templates HTML prontos para uso no `Supabase -> Authentication -> Email Templates`.

Mapeamento:

- `confirm-sign-up.html` -> `Confirm sign up`
- `invite-user.html` -> `Invite user`
- `magic-link.html` -> `Magic link`
- `change-email-address.html` -> `Change email address`
- `reset-password.html` -> `Reset password`
- `reauthentication.html` -> `Reauthentication`

Observação:

- Estes templates usam `{{ .ConfirmationURL }}` para preservar o fluxo nativo do Supabase com os redirects já configurados.
- `{{ .NewEmail }}` é usado apenas no template de alteração de e-mail.
- `reauthentication.html` usa `{{ .Token }}` porque o fluxo nativo de reautenticação do Supabase é baseado em OTP.

import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { Webhook } from "standardwebhooks";

type EmailActionType = "email" | "recovery" | "magiclink" | "invite" | "email_change";

type HookUser = {
  email?: string;
  email_change?: string;
  user_metadata?: {
    full_name?: string;
    name?: string;
  };
};

type HookEmailData = {
  token_hash?: string;
  token_hash_new?: string;
  redirect_to?: string;
  site_url?: string;
  email_action_type?: EmailActionType;
};

type SendEmailPayload = {
  user?: HookUser;
  email_data?: HookEmailData;
};

const resendApiKey = Deno.env.get("RESEND_API_KEY") ?? "";
const from = Deno.env.get("AUTH_EMAIL_FROM") ?? "Alloha <contato@alloha.app>";
const productName = Deno.env.get("AUTH_EMAIL_PRODUCT_NAME") ?? "Alloha";
const fallbackSiteUrl = Deno.env.get("AUTH_SITE_URL") ?? "http://localhost:3000";
const hookSecret = Deno.env.get("SEND_EMAIL_HOOK_SECRET") ?? "";

const subjects: Record<EmailActionType, string> = {
  email: `Confirme seu email na ${productName}`,
  recovery: `Redefina sua senha na ${productName}`,
  magiclink: `Seu link de acesso da ${productName}`,
  invite: `Seu convite para a ${productName}`,
  email_change: `Confirme a alteracao do seu email na ${productName}`,
};

const ctaLabels: Record<EmailActionType, string> = {
  email: "Confirmar email",
  recovery: "Redefinir senha",
  magiclink: "Entrar agora",
  invite: "Aceitar convite",
  email_change: "Confirmar alteracao",
};

const preheaders: Record<EmailActionType, string> = {
  email: "Confirme sua conta para concluir o onboarding da Alloha.",
  recovery: "Use este link seguro para criar uma nova senha.",
  magiclink: "Seu acesso rapido e seguro a Alloha.",
  invite: "Voce recebeu um convite para acessar a Alloha.",
  email_change: "Confirme seu novo email para manter a conta atualizada.",
};

const bodyCopy: Record<EmailActionType, { title: string; description: string; footnote: string }> = {
  email: {
    title: "Confirme seu email",
    description: "Ative sua conta para concluir o onboarding e entrar na Alloha com seguranca.",
    footnote: "Se voce nao criou essa conta, ignore este email.",
  },
  recovery: {
    title: "Redefina sua senha",
    description: "Use o link abaixo para escolher uma nova senha e voltar ao seu painel.",
    footnote: "Se voce nao pediu essa troca, ignore este email e sua senha atual continuara valida.",
  },
  magiclink: {
    title: "Seu acesso esta pronto",
    description: "Use este link seguro para entrar na Alloha sem precisar digitar sua senha.",
    footnote: "Se voce nao pediu esse acesso, basta ignorar este email.",
  },
  invite: {
    title: "Voce recebeu um convite",
    description: "Aceite o convite para entrar na Alloha e seguir para a configuracao inicial.",
    footnote: "Se esse convite nao era esperado, ignore este email.",
  },
  email_change: {
    title: "Confirme seu novo email",
    description: "Conclua a alteracao para manter sua conta protegida e atualizada.",
    footnote: "Se voce nao solicitou essa alteracao, ignore este email.",
  },
};

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeAction(action?: string): EmailActionType {
  if (action === "recovery" || action === "magiclink" || action === "invite" || action === "email_change") {
    return action;
  }
  return "email";
}

function resolveRecipient(payload: SendEmailPayload) {
  const action = normalizeAction(payload.email_data?.email_action_type);
  if (action === "email_change" && payload.user?.email_change) {
    return payload.user.email_change;
  }
  return payload.user?.email ?? "";
}

function appendUrlParams(url: URL, params: Record<string, string>) {
  for (const [key, value] of Object.entries(params)) {
    if (value) {
      url.searchParams.set(key, value);
    }
  }
  return url;
}

function buildActionUrl(payload: SendEmailPayload, action: EmailActionType) {
  const redirectTo = payload.email_data?.redirect_to || payload.email_data?.site_url || fallbackSiteUrl;
  const url = new URL(redirectTo, fallbackSiteUrl);

  if (action === "recovery") {
    return appendUrlParams(url, {
      token_hash: payload.email_data?.token_hash ?? "",
      type: "recovery",
    }).toString();
  }

  if (action === "email_change") {
    return appendUrlParams(url, {
      token_hash: payload.email_data?.token_hash_new ?? payload.email_data?.token_hash ?? "",
      type: "email_change",
    }).toString();
  }

  return appendUrlParams(url, {
    token_hash: payload.email_data?.token_hash ?? "",
    type: action === "invite" ? "invite" : "email",
  }).toString();
}

function buildEmailHtml({
  action,
  recipient,
  actionUrl,
  recipientName,
}: {
  action: EmailActionType;
  recipient: string;
  actionUrl: string;
  recipientName: string;
}) {
  const copy = bodyCopy[action];
  const ctaLabel = ctaLabels[action];
  const safeName = escapeHtml(recipientName);
  const safeUrl = escapeHtml(actionUrl);
  const safeRecipient = escapeHtml(recipient);
  const safeProduct = escapeHtml(productName);

  return `
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${escapeHtml(subjects[action])}</title>
  </head>
  <body style="margin:0;background:#050505;font-family:Inter,Segoe UI,Arial,sans-serif;color:#f7f3ef;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">${escapeHtml(preheaders[action])}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#050505;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;border:1px solid rgba(255,255,255,0.08);border-radius:28px;overflow:hidden;background:linear-gradient(180deg,#0a0a0a 0%,#080808 100%);box-shadow:0 24px 80px rgba(0,0,0,0.45);">
            <tr>
              <td style="padding:32px 32px 12px;background:radial-gradient(circle at top right, rgba(255,122,47,0.18), transparent 40%), radial-gradient(circle at bottom left, rgba(255,255,255,0.06), transparent 34%);">
                <div style="display:inline-block;border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:12px 14px;background:rgba(255,255,255,0.03);color:#ff9a66;font-size:12px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;">
                  ${safeProduct}
                </div>
                <h1 style="margin:24px 0 0;font-size:36px;line-height:1.05;letter-spacing:-0.04em;color:#fff9f4;">
                  ${escapeHtml(copy.title)}
                </h1>
                <p style="margin:14px 0 0;font-size:16px;line-height:1.7;color:rgba(255,249,244,0.72);">
                  ${safeName ? `Oi, ${safeName}. ` : ""}${escapeHtml(copy.description)}
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 0;">
                <table role="presentation" cellspacing="0" cellpadding="0">
                  <tr>
                    <td align="center" style="border-radius:18px;background:linear-gradient(180deg,#ff8a4b 0%,#ff5e14 100%);">
                      <a href="${safeUrl}" style="display:inline-block;padding:16px 24px;color:#fff8f2;text-decoration:none;font-weight:700;font-size:15px;">
                        ${escapeHtml(ctaLabel)}
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 32px 12px;">
                <p style="margin:0;font-size:13px;line-height:1.8;color:rgba(255,249,244,0.54);">
                  Se o botao nao funcionar, copie este link no navegador:
                </p>
                <p style="margin:10px 0 0;word-break:break-all;font-size:13px;line-height:1.8;color:#ffb48f;">
                  <a href="${safeUrl}" style="color:#ffb48f;text-decoration:underline;">${safeUrl}</a>
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:4px 32px 32px;">
                <div style="border-top:1px solid rgba(255,255,255,0.08);padding-top:18px;">
                  <p style="margin:0;font-size:13px;line-height:1.8;color:rgba(255,249,244,0.54);">
                    ${escapeHtml(copy.footnote)}
                  </p>
                  <p style="margin:12px 0 0;font-size:12px;line-height:1.7;color:rgba(255,249,244,0.36);">
                    Enviado para ${safeRecipient} por ${safeProduct}.
                  </p>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
`;
}

function buildTextEmail({
  action,
  actionUrl,
}: {
  action: EmailActionType;
  actionUrl: string;
}) {
  const copy = bodyCopy[action];
  return `${copy.title}\n\n${copy.description}\n\n${ctaLabels[action]}: ${actionUrl}\n\n${copy.footnote}`;
}

async function sendEmail(to: string, subject: string, html: string, text: string) {
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${resendApiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from,
      to: [to],
      subject,
      html,
      text,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Resend API failed (${response.status}): ${errorBody}`);
  }
}

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  if (!resendApiKey) {
    return new Response("Missing RESEND_API_KEY", { status: 500 });
  }

  const rawBody = await req.text();

  if (hookSecret) {
    const webhook = new Webhook(hookSecret);
    try {
      await webhook.verify(rawBody, {
        "webhook-id": req.headers.get("webhook-id") ?? "",
        "webhook-timestamp": req.headers.get("webhook-timestamp") ?? "",
        "webhook-signature": req.headers.get("webhook-signature") ?? "",
      });
    } catch (error) {
      return new Response(`Invalid webhook signature: ${error}`, { status: 401 });
    }
  }

  try {
    const payload = JSON.parse(rawBody) as SendEmailPayload;
    const action = normalizeAction(payload.email_data?.email_action_type);
    const recipient = resolveRecipient(payload);

    if (!recipient) {
      return new Response("Missing recipient email", { status: 400 });
    }

    const actionUrl = buildActionUrl(payload, action);
    const recipientName =
      payload.user?.user_metadata?.full_name ||
      payload.user?.user_metadata?.name ||
      recipient.split("@")[0] ||
      "";

    const html = buildEmailHtml({
      action,
      recipient,
      actionUrl,
      recipientName,
    });
    const text = buildTextEmail({ action, actionUrl });

    await sendEmail(recipient, subjects[action], html, text);

    return new Response(JSON.stringify({ success: true }), {
      headers: { "Content-Type": "application/json" },
      status: 200,
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: String(error) }), {
      headers: { "Content-Type": "application/json" },
      status: 500,
    });
  }
});

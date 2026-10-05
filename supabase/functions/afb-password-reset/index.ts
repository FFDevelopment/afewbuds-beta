// AFewBuds password recovery email sender.
// Public endpoint by design: it returns generic responses and never reveals whether an account exists.

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") || "";
const LEGACY_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
let MODERN_SECRET_KEY = "";
try {
  const all = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
  MODERN_SECRET_KEY = all.default || "";
} catch (_) {}

const SERVICE_KEY = MODERN_SECRET_KEY || LEGACY_SERVICE_KEY;
const DEFAULT_RESET_BASE = "https://ffdevelopment.github.io/afewbuds-cloud-test/";
const ALLOWED_RESET_BASES = new Set([
  "https://ffdevelopment.github.io/afewbuds-cloud-test/",
  "https://ffdevelopment.github.io/afewbuds-beta/",
]);

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders });
}

function serviceHeaders() {
  const headers: Record<string,string> = {
    "Content-Type": "application/json",
    "apikey": SERVICE_KEY,
  };
  if (LEGACY_SERVICE_KEY && SERVICE_KEY === LEGACY_SERVICE_KEY) {
    headers.Authorization = "Bearer " + LEGACY_SERVICE_KEY;
  }
  return headers;
}

async function rpc(name: string, payload: Record<string,unknown>) {
  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, {
    method: "POST",
    headers: serviceHeaders(),
    body: JSON.stringify(payload),
  });
  const raw = await response.text();
  let data: any = null;
  if (raw) {
    try { data = JSON.parse(raw); } catch (_) { data = raw; }
  }
  if (!response.ok) throw new Error(`RPC ${name} failed (${response.status})`);
  return data;
}

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function resolveResetBase(value: unknown) {
  try {
    const url = new URL(String(value || ""));
    url.search = "";
    url.hash = "";
    let path = url.pathname;
    if (!path.endsWith("/")) path += "/";
    const base = url.origin + path;
    return ALLOWED_RESET_BASES.has(base) ? base : DEFAULT_RESET_BASE;
  } catch (_) {
    return DEFAULT_RESET_BASE;
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ ok:false, error:"method_not_allowed" }, 405);
  if (!SUPABASE_URL || !SERVICE_KEY) return json({ ok:false, error:"recovery_service_unavailable" }, 503);

  try {
    const config = await rpc("afb_password_reset_brevo_config", {});
    if (!config?.configured || !config?.api_key || !config?.from_address) {
      return json({ ok:false, error:"recovery_email_not_configured" }, 503);
    }

    let body: any = {};
    try { body = await req.json(); } catch (_) {}
    const username = String(body?.username || "").trim();
    const resetBase = resolveResetBase(body?.return_url);

    const issued = await rpc("afb_password_reset_issue", { p_username: username });

    if (!issued?.deliver) {
      return json({
        ok:true,
        message:"If that AFewBuds account has a recovery email, a reset link has been sent."
      });
    }

    const resetToken = String(issued.reset_token || "");
    const targetEmail = String(issued.email || "");
    const accountName = String(issued.username || username);
    if (!resetToken || !targetEmail) {
      return json({
        ok:true,
        message:"If that AFewBuds account has a recovery email, a reset link has been sent."
      });
    }

    const resetUrl = resetBase + "?reset=" + encodeURIComponent(resetToken);
    const subject = "Reset your AFewBuds password";
    const htmlContent = `<!doctype html>
<html>
<body style="margin:0;background:#0b120e;color:#edf5eb;font-family:Arial,sans-serif">
  <div style="max-width:560px;margin:0 auto;padding:32px 22px">
    <div style="background:#142019;border:1px solid #35513d;border-radius:18px;padding:26px">
      <h1 style="margin:0 0 12px;font-size:25px">AFewBuds password reset</h1>
      <p style="color:#c3cec2;line-height:1.55">A password reset was requested for <strong>${escapeHtml(accountName)}</strong>.</p>
      <p style="color:#c3cec2;line-height:1.55">Use the button below within <strong>30 minutes</strong>. The link can only be used once.</p>
      <p style="margin:24px 0">
        <a href="${escapeHtml(resetUrl)}" style="display:inline-block;background:#8fc47b;color:#0c170f;text-decoration:none;font-weight:700;padding:13px 18px;border-radius:11px">Reset AFewBuds password</a>
      </p>
      <p style="font-size:13px;color:#8f9d91;line-height:1.5">If you did not request this, you can ignore this email. Your password has not been changed.</p>
    </div>
  </div>
</body>
</html>`;

    const brevoResponse = await fetch("https://api.brevo.com/v3/smtp/email", {
      method: "POST",
      headers: {
        "accept": "application/json",
        "api-key": String(config.api_key),
        "content-type": "application/json",
      },
      body: JSON.stringify({
        sender: { name:"AFewBuds", email:String(config.from_address) },
        to: [{ email:targetEmail, name:accountName }],
        replyTo: { email:String(config.from_address), name:"FFDevelopment" },
        subject,
        htmlContent,
        tags:["password-reset","afewbuds"],
      }),
    });

    if (!brevoResponse.ok) {
      console.error("AFewBuds Brevo password reset send failed", brevoResponse.status);
      return json({ ok:false, error:"recovery_email_send_failed" }, 502);
    }

    return json({
      ok:true,
      message:"If that AFewBuds account has a recovery email, a reset link has been sent."
    });
  } catch (error) {
    console.error("AFewBuds password reset function failed", error instanceof Error ? error.message : String(error));
    return json({ ok:false, error:"recovery_service_unavailable" }, 503);
  }
});

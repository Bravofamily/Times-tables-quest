// NumiRealm v32: nr-delete-account Edge Function.
// POST {confirm:"DELETE"} with the signed-in parent's access token (Authorization: Bearer <jwt>).
// Deletes ONLY the caller's own data, then the caller's auth user. The service role key is read from the
// function's secrets (SUPABASE_SERVICE_ROLE_KEY, provided automatically by Supabase) and never leaves the server.
// Safe to call again after a partial failure: every step is "delete where parent_id = caller", so a retry
// finishes the job and never touches anyone else.
type J = Record<string, any>;
const env = (k: string) => { try { return Deno.env.get(k) || ""; } catch { return ""; } };
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const base = () => env("SUPABASE_URL").replace(/\/$/, "");
const srv = (extra: J = {}) => { const k = env("SUPABASE_SERVICE_ROLE_KEY"); return { apikey: k, Authorization: "Bearer " + k, "Content-Type": "application/json", ...extra }; };

// Children first, parents last. Every row is matched by parent_id (or id for parents) = the caller.
export const STEPS: [string, string][] = [
  ["notify_prefs_off", ""], // turn the weekly email off first, so no email can go out even if a later step fails
  ["challenge_done", "parent_id"], ["rewards", "parent_id"], ["fixit_plans", "parent_id"], ["quests", "parent_id"],
  ["progress_events", "parent_id"], ["progress", "parent_id"], ["link_codes", "parent_id"], ["devices", "parent_id"],
  ["weekly_summaries", "parent_id"], ["email_log", "parent_id"], ["notify_prefs", "parent_id"], ["kids", "parent_id"],
  ["consent_records", "parent_id"], ["parent_consent", "parent_id"], ["parents", "id"],
];

async function rest(path: string, init: RequestInit): Promise<Response> {
  return await fetch(base() + "/rest/v1/" + path, { ...init, headers: srv((init.headers as J) || {}) });
}
// Fresh re-auth: the session must come from a sign-in (OTP/magic link/password) within REAUTH_SEC.
// The amr timestamp is set at sign-in and is NOT renewed by token refresh, unlike iat.
export const REAUTH_SEC = 10 * 60;
export function claims(req: Request): J | null {
  const a = req.headers.get("authorization") || ""; const t = a.replace(/^Bearer /, "").split(".");
  if (t.length !== 3) return null;
  try { return JSON.parse(atob(t[1].replace(/-/g, "+").replace(/_/g, "/"))); } catch { return null; }
}
export function freshAuth(c: J | null, now = Date.now() / 1000): boolean {
  const ts = Array.isArray(c?.amr) ? Math.max(0, ...c!.amr.map((x: J) => Number(x?.timestamp) || 0)) : 0;
  return ts > 0 && now - ts <= REAUTH_SEC;
}
// End-state check: no rows left for this parent in any table, and the auth user is gone.
async function verifyGone(id: string): Promise<string[]> {
  const left: string[] = [];
  for (const [t, col] of STEPS) {
    if (t === "notify_prefs_off") continue;
    const r = await rest(`${t}?${col}=eq.${id}&select=${col}&limit=1`, { method: "GET" }).catch(() => null);
    if (!r) { left.push(t); continue; }
    const tx = await r.text();
    if (r.status === 404 || /PGRST205|42P01/.test(tx)) continue;
    if (!r.ok) { left.push(t); continue; }
    try { if ((JSON.parse(tx) as unknown[]).length) left.push(t); } catch { left.push(t); }
  }
  const u = await fetch(base() + "/auth/v1/admin/users/" + id, { headers: srv() }).catch(() => null);
  if (!u || u.status !== 404) left.push("auth_user");
  await u?.text().catch(() => "");
  return left;
}
async function userFrom(req: Request): Promise<J | null> {
  const a = req.headers.get("authorization") || "";
  if (!/^Bearer .{20,}/.test(a)) return null;
  const r = await fetch(base() + "/auth/v1/user", { headers: { apikey: env("SUPABASE_SERVICE_ROLE_KEY"), Authorization: a } });
  if (!r.ok) return null; const u = await r.json(); return u && UUID.test(String(u.id || "")) ? u : null;
}

export async function handle(req: Request): Promise<Response> {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
  if (!env("SUPABASE_URL") || !env("SUPABASE_SERVICE_ROLE_KEY")) return json({ ok: false, error: "not_configured" }, 500);
  const body = await req.json().catch(() => ({}));
  if (body.confirm !== "DELETE") return json({ ok: false, error: "confirm" }, 400);
  // Target user comes ONLY from the token (signature already checked by the gateway, Verify JWT = ON). Body ids are ignored.
  const c = claims(req); const sub = String(c?.sub || "");
  if (!UUID.test(sub)) return json({ ok: false, error: "signin" }, 401);
  const user = await userFrom(req);
  if (!user) {
    // Idempotent retry: the auth user was already deleted but the reply was lost. Confirm everything is gone.
    const left = await verifyGone(sub);
    return left.length ? json({ ok: false, error: "signin" }, 401) : json({ ok: true, deleted: true, verified: true, already: true });
  }
  if (user.id !== sub) return json({ ok: false, error: "signin" }, 401);
  if (!freshAuth(c)) return json({ ok: false, error: "reauth" }, 401);
  const id = user.id as string, done: string[] = [];
  for (const [t, col] of STEPS) {
    let r: Response;
    try {
      r = t === "notify_prefs_off"
        ? await rest(`notify_prefs?parent_id=eq.${id}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ email_weekly: false }) })
        : await rest(`${t}?${col}=eq.${id}`, { method: "DELETE", headers: { Prefer: "return=minimal" } });
    } catch { return json({ ok: false, error: "partial", step: t, done }, 502); }
    // 404/PGRST205 = table not created in this project (optional parts): nothing to delete.
    if (!r.ok && r.status !== 404) { const tx = await r.text(); if (!/PGRST205|42P01/.test(tx)) return json({ ok: false, error: "partial", step: t, done }, 502); }
    else await r.text().catch(() => "");
    done.push(t);
  }
  // Revoke every session (all devices), then delete the auth user. Deleting the user also removes its refresh tokens.
  try { await fetch(base() + "/auth/v1/logout?scope=global", { method: "POST", headers: { apikey: env("SUPABASE_SERVICE_ROLE_KEY"), Authorization: req.headers.get("authorization") || "" } }); } catch { /* best effort */ }
  const d = await fetch(base() + "/auth/v1/admin/users/" + id, { method: "DELETE", headers: srv() }).catch(() => null);
  if (!d || (!d.ok && d.status !== 404)) return json({ ok: false, error: "partial", step: "auth_user", done }, 502);
  const left = await verifyGone(id);
  if (left.length) return json({ ok: false, error: "partial", step: left[0], done }, 502);
  console.log("nr-delete-account ok"); // no ids or emails in logs
  return json({ ok: true, deleted: true, verified: true });
}
if (env("NR_NO_SERVE") !== "1") Deno.serve(handle);

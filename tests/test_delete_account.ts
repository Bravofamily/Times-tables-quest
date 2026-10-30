// Local tests for supabase/functions/nr-delete-account (database and auth are mocked; no network).
// Run: NR_NO_SERVE=1 deno test --allow-env tests/test_delete_account.ts
import * as F from "../supabase/functions/nr-delete-account/index.ts";
const eq = (a: unknown, b: unknown, m: string) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(m + ": " + JSON.stringify(a) + " != " + JSON.stringify(b)); };
const ok = (c: unknown, m: string) => { if (!c) throw new Error(m); };
const ME = "22222222-2222-4222-8222-222222222222", OTHER = "44444444-4444-4444-8444-444444444444";
const b64 = (o: unknown) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
const jwt = (sub: string, ageSec = 60) => "eyJhbGciOiJIUzI1NiJ9." + b64({ sub, amr: [{ method: "otp", timestamp: Math.floor(Date.now() / 1000) - ageSec }] }) + ".sig";
const GOOD = jwt(ME);
const TABLES = ["parents","parent_consent","kids","devices","link_codes","progress","progress_events","quests","fixit_plans","rewards","notify_prefs","challenge_done","weekly_summaries","email_log","consent_records"];
function setup(o: { failOn?: string; failAuth?: boolean; missing?: string; failVerify?: string } = {}) {
  Deno.env.set("SUPABASE_URL", "https://x.supabase.co"); Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-key-test");
  const S: any = { calls: [] as string[], rows: {} as Record<string, any[]>, users: new Set([ME, OTHER]), loggedOut: false };
  for (const t of TABLES) S.rows[t] = [ME, OTHER].map((p) => t === "parents" ? { id: p } : { parent_id: p, email_weekly: true });
  (globalThis as any).fetch = async (input: string, init: any = {}) => {
    const u = new URL(input), m = init.method || "GET"; S.calls.push(m + " " + u.pathname + u.search);
    const J = (x: unknown, s = 200) => new Response(JSON.stringify(x), { status: s });
    if (u.pathname === "/auth/v1/user") return (() => { try { const c = JSON.parse(atob(init.headers.Authorization.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))); return c.sub === ME; } catch { return false; } })() && S.users.has(ME) ? J({ id: ME }) : J({}, 401);
    if (u.pathname === "/auth/v1/logout") { S.loggedOut = init.headers.Authorization === "Bearer " + GOOD; return new Response(null, { status: 204 }); }
    if (u.pathname.startsWith("/auth/v1/admin/users/")) { if (m === "GET") return S.users.has(u.pathname.split("/").pop()) ? J({}) : J({}, 404); if (o.failAuth) return J({ msg: "x" }, 500); ok(init.headers.Authorization === "Bearer service-key-test", "admin uses service key"); S.users.delete(u.pathname.split("/").pop()); return J({}); }
    const t = u.pathname.replace("/rest/v1/", "");
    if (t === o.missing) return J({ code: "PGRST205" }, 404);
    if (t === o.failOn) return J({ code: "XX000" }, 500);
    const mm = /(parent_id|id)=eq\.([0-9a-f-]+)/.exec(u.search)!; const col = mm[1], val = mm[2];
    if (m === "PATCH") { S.rows[t].forEach((r: any) => { if (r[col] === val) Object.assign(r, JSON.parse(init.body)); }); return new Response(null, { status: 204 }); }
    if (m === "DELETE") { S.rows[t] = S.rows[t].filter((r: any) => r[col] !== val); return new Response(null, { status: 204 }); }
    if (o.failVerify === t) return J([{ x: 1 }]);
    return J(S.rows[t].filter((r: any) => r[col] === val));
  };
  return S;
}
const AUTH = { Authorization: "Bearer " + GOOD };
const post = (b: unknown, h: Record<string, string> = AUTH) => new Request("https://f/nr-delete-account", { method: "POST", headers: { "Content-Type": "application/json", ...h }, body: JSON.stringify(b) });
const mine = (S: any) => TABLES.reduce((n, t) => n + S.rows[t].filter((r: any) => (r.parent_id ?? r.id) === ME).length, 0);
const theirs = (S: any) => TABLES.reduce((n, t) => n + S.rows[t].filter((r: any) => (r.parent_id ?? r.id) === OTHER).length, 0);

Deno.test("deletes every row of the caller in every parent table, plus the auth user; nobody else's", async () => {
  const S = setup(); const r = await F.handle(post({ confirm: "DELETE" }));
  eq([r.status, (await r.json()).ok], [200, true], "ok");
  eq(mine(S), 0, "no rows left for the caller"); eq(theirs(S), TABLES.length, "other parent untouched");
  ok(!S.users.has(ME) && S.users.has(OTHER), "only the caller's auth user deleted"); ok(S.loggedOut, "sessions revoked (global logout)");
  for (const t of TABLES) ok(S.calls.some((c: string) => c.startsWith("DELETE /rest/v1/" + t + "?")), "deleted from " + t);
  ok(S.calls.filter((c: string) => c.startsWith("DELETE /rest/v1/")).every((c: string) => c.includes("=eq." + ME)), "every delete is scoped to the caller id");
});
Deno.test("weekly email is turned off first", async () => {
  const S = setup(); await F.handle(post({ confirm: "DELETE" }));
  const i = S.calls.findIndex((c: string) => c.startsWith("PATCH /rest/v1/notify_prefs?parent_id=eq." + ME));
  ok(i >= 0 && S.calls.findIndex((c: string) => c.startsWith("DELETE")) > i, "PATCH email_weekly=false before any delete");
});
Deno.test("refuses without the typed confirmation, without a valid sign-in, or with GET", async () => {
  let S = setup(); eq((await F.handle(post({}))).status, 400, "no confirm"); eq(mine(S), TABLES.length, "nothing deleted");
  S = setup(); eq((await F.handle(post({ confirm: "delete" }))).status, 400, "lowercase confirm");
  S = setup(); eq((await F.handle(post({ confirm: "DELETE" }, { Authorization: "Bearer bad-token-xxxxxxxxxxxxxxxx" }))).status, 401, "bad jwt"); eq(mine(S), TABLES.length, "nothing deleted");
  S = setup(); eq((await F.handle(post({ confirm: "DELETE" }, {}))).status, 401, "no jwt");
  eq((await F.handle(new Request("https://f/x", { method: "GET" }))).status, 405, "GET");
});
Deno.test("ignores any id in the body (only the JWT decides whose data)", async () => {
  const S = setup(); await F.handle(post({ confirm: "DELETE", parent_id: OTHER, user_id: OTHER }));
  eq(theirs(S), TABLES.length, "other parent untouched"); ok(S.users.has(OTHER), "other auth user kept");
});
Deno.test("partial failure reports the step, keeps the auth user, and a retry finishes", async () => {
  let S = setup({ failOn: "kids" }); const r = await F.handle(post({ confirm: "DELETE" })); const j = await r.json();
  eq([r.status, j.ok, j.error, j.step], [502, false, "partial", "kids"], "partial"); ok(S.users.has(ME), "auth user kept so the parent can retry");
  const rows = S.rows; S = setup(); S.rows = rows; const r2 = await (await F.handle(post({ confirm: "DELETE" }))).json();
  eq(r2.ok, true, "retry ok"); eq(mine(S), 0, "all gone after retry");
});
Deno.test("auth delete failure is reported as partial", async () => {
  setup({ failAuth: true }); const j = await (await F.handle(post({ confirm: "DELETE" }))).json(); eq([j.error, j.step], ["partial", "auth_user"], "auth step");
});
Deno.test("an optional table that was never created does not block deletion", async () => {
  const S = setup({ missing: "challenge_done" }); const j = await (await F.handle(post({ confirm: "DELETE" }))).json(); eq(j.ok, true, "ok"); ok(!S.users.has(ME), "user deleted");
});

Deno.test("requires a fresh sign-in (older than 10 minutes -> reauth, nothing deleted)", async () => {
  const S = setup(); const r = await F.handle(post({ confirm: "DELETE" }, { Authorization: "Bearer " + jwt(ME, 3600) }));
  eq([r.status, (await r.json()).error], [401, "reauth"], "reauth"); eq(mine(S), TABLES.length, "nothing deleted");
});
Deno.test("token for one user cannot delete another (sub must match the verified user)", async () => {
  const S = setup(); const r = await F.handle(post({ confirm: "DELETE" }, { Authorization: "Bearer " + jwt(OTHER) }));
  eq(r.status, 401, "mismatch"); eq(theirs(S), TABLES.length, "other untouched"); eq(mine(S), TABLES.length, "mine untouched");
});
Deno.test("retry after auth user was deleted but the reply was lost -> ok, verified", async () => {
  const S = setup(); await F.handle(post({ confirm: "DELETE" })); ok(!S.users.has(ME), "deleted");
  const j = await (await F.handle(post({ confirm: "DELETE" }))).json(); eq([j.ok, j.verified, j.already], [true, true, true], "idempotent");
});
Deno.test("does not report deleted unless the end state is verified", async () => {
  setup({ failVerify: "progress" }); const r = await F.handle(post({ confirm: "DELETE" })); const j = await r.json();
  eq([r.status, j.ok, j.step], [502, false, "progress"], "unverified -> partial");
});

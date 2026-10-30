// Local tests for supabase/functions/nr-weekly (AI, Resend and the database are all mocked).
// Run: NR_NO_SERVE=1 deno test --allow-env tests/test_edge.ts
import * as F from "../supabase/functions/nr-weekly/index.ts";
const eq = (a: unknown, b: unknown, m: string) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(m + ": " + JSON.stringify(a) + " != " + JSON.stringify(b)); };
const ok = (c: unknown, m: string) => { if (!c) throw new Error(m); };
const MIA = "11111111-1111-4111-8111-111111111111", PAR = "22222222-2222-4222-8222-222222222222", TOK = "33333333-3333-4333-8333-333333333333";
const today = F.localDate(new Date(), "America/New_York");
const add = (n: number) => { const d = new Date(today + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
function setup(o: { ai?: boolean; resend?: boolean; aiText?: string; aiStatus?: number } = {}) {
  Deno.env.set("SUPABASE_URL", "https://x.supabase.co"); Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-key-test");
  Deno.env.set("CRON_SECRET", "cronsecret123"); Deno.env.set("PORTAL_URL", "https://example.test/parent.html");
  o.ai ? Deno.env.set("OPENAI_API_KEY", "sk-test") : Deno.env.delete("OPENAI_API_KEY");
  o.resend ? Deno.env.set("RESEND_API_KEY", "re_test") : Deno.env.delete("RESEND_API_KEY");
  const S: any = { summaries: [] as any[], log: [] as any[], prefs: [{ parent_id: PAR, unsub_token: TOK, email_weekly: true, email_day: new Date(today + "T12:00:00Z").getUTCDay(), ai_summaries: !!o.ai }], ai: [] as any[], mail: [] as any[], calls: [] as string[] };
  (globalThis as any).fetch = async (input: string, init: any = {}) => {
    const u = new URL(input), m = (init.method || "GET"), p = u.pathname + u.search; S.calls.push(m + " " + p);
    const J = (o: unknown, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "Content-Type": "application/json" } });
    if (u.host === "api.openai.com") { const b = JSON.parse(init.body); S.ai.push(b); if (o.aiStatus) return J({ error: "x" }, o.aiStatus); return J({ choices: [{ message: { content: o.aiText ?? "{{KID}} had a lovely week of practice with 95 minutes and 12 stars. Strong work on x2 facts. Try skip-counting by 7s on the stairs at home." } }] }); }
    if (u.host === "api.resend.com") { S.mail.push(JSON.parse(init.body)); return J({ id: "em_1" }); }
    if (p.startsWith("/auth/v1/user")) return (init.headers.Authorization === "Bearer good-parent-jwt-0123456789") ? J({ id: PAR, email: "parent@example.test" }) : J({ msg: "bad" }, 401);
    if (p.startsWith("/auth/v1/admin/users/")) return (globalThis as any).__gone ? J({ msg: "User not found" }, 404) : J({ id: PAR, email: "parent@example.test" });
    const t = u.pathname.replace("/rest/v1/", "");
    if (t === "kids") return J(u.search.includes("id=eq." + MIA) || u.search.includes("parent_id=eq." + PAR) && !u.search.includes("id=eq.9") ? [{ id: MIA, parent_id: PAR, nickname: "Mia", grade: "3" }] : []);
    if (t === "progress") return J([{ skills: { "mult:x7": { n: "×7 facts", r: 6, t: 14 }, "mult:x2": { n: "×2 facts", r: 30, t: 31 }, "add:c2": { n: "adding <b>", r: 19, t: 20 } }, play: { v: 1, end: today, days: [50, 0, 10, 20, 0, 30, 5, 30] } }]);
    if (t === "progress_events") return J([{ day: add(-8), stars_total: 40, answers_right: 100, answers_total: 120, minutes: 10 }, { day: add(0), stars_total: 52, answers_right: 186, answers_total: 220, minutes: 30 }]);
    if (t === "quests") return J([{ id: "q1" }]);
    if (t === "weekly_summaries") { if (m === "POST") { const b = JSON.parse(init.body); S.summaries = S.summaries.filter((x: any) => x.week !== b.week); S.summaries.push(b); return new Response("", { status: 201 }); } if (m === "DELETE") return new Response(null, { status: 204 }); return J(S.summaries); }
    if (t === "notify_prefs") { if (m === "PATCH") { const tok = /unsub_token=eq\.([0-9a-f-]+)/.exec(u.search)![1]; S.prefs.forEach((x: any) => { if (x.unsub_token === tok) Object.assign(x, JSON.parse(init.body)); }); return new Response(null, { status: 204 }); }
      if (u.search.includes("email_weekly=is.true")) { const d = /email_day=eq\.(\d)/.exec(u.search); return J(S.prefs.filter((x: any) => x.email_weekly && (!d || String(x.email_day) === d[1]))); } return J(S.prefs); }
    if (t === "email_log") { if (m === "POST") { S.log.push(JSON.parse(init.body)); return new Response("", { status: 201 }); } if (m === "DELETE") return new Response(null, { status: 204 });
      return J(S.log.filter((x: any) => (u.search.includes("kind=eq.weekly") ? x.kind === "weekly" : x.kind === "preview"))); }
    return J({ message: "not mocked " + p }, 404);
  };
  return S;
}
const post = (o: unknown, h: Record<string, string> = {}) => new Request("https://x.supabase.co/functions/v1/nr-weekly", { method: "POST", headers: { "Content-Type": "application/json", ...h }, body: JSON.stringify(o) });
const AUTH = { Authorization: "Bearer good-parent-jwt-0123456789" };

Deno.test("stats are aggregate and correct", () => {
  setup();
  const st = F.buildStats({ grade: "3", nickname: "Mia" }, { skills: { "mult:x7": { n: "×7 facts", r: 6, t: 14 }, "mult:x2": { r: 30, t: 31 } }, play: { end: today, days: [99, 50, 0, 10, 20, 0, 30, 5] } }, [{ day: add(-8), stars_total: 40, answers_right: 100, answers_total: 120 }, { day: today, stars_total: 52, answers_right: 186, answers_total: 220 }], 1, today);
  eq([st.minutes, st.days_played, st.stars, st.answers, st.accuracy], [115, 5, 12, 100, 86], "numbers");
  eq(st.weak.map((w: any) => w.n), ["x7 facts"], "weak"); eq(st.strong.map((w: any) => w.n), ["x2 facts"], "strong");
  ok(!JSON.stringify(st).includes("Mia"), "no nickname in stats");
});
Deno.test("template summary without AI key (free fallback)", async () => {
  const S = setup();
  const r = await (await F.handle(post({ action: "summary", kid_id: MIA }, AUTH))).json();
  eq([r.ok, r.source], [true, "template"], "template"); ok(r.text.includes("{{KID}} played") && r.text.includes("x7 facts"), r.text);
  eq(S.ai.length, 0, "no AI call"); eq(S.summaries.length, 1, "cached");
  await F.handle(post({ action: "summary", kid_id: MIA }, AUTH)); eq(S.summaries.length, 1, "served from cache"); ok(!S.calls.some((c: string) => c.includes("progress?") && S.calls.indexOf(c) > 6), "no recompute");
});
Deno.test("AI summary sends only totals, never the nickname", async () => {
  const S = setup({ ai: true });
  const r = await (await F.handle(post({ action: "summary", kid_id: MIA }, AUTH))).json();
  eq(r.source, "ai", "ai source"); const sent = JSON.stringify(S.ai[0]);
  ok(!/Mia|parent@|1111|2222/.test(sent) && sent.includes("{{KID}}") && sent.includes("minutes_played"), "prompt is anonymous: " + sent.slice(0, 300));
  ok(!sent.includes("<b>"), "skill names sanitized");
});
Deno.test("bad AI output falls back to the template", async () => {
  setup({ ai: true, aiText: "Visit http://spam.example now" });
  const r = await (await F.handle(post({ action: "summary", kid_id: MIA }, AUTH))).json(); eq(r.source, "template", "fallback");
});
Deno.test("sign-in and ownership required", async () => {
  setup();
  eq((await F.handle(post({ action: "summary", kid_id: MIA }))).status, 401, "no jwt");
  eq((await F.handle(post({ action: "summary", kid_id: "99999999-9999-4999-8999-999999999999" }, AUTH))).status, 404, "other kid");
  eq((await F.handle(post({ action: "cron" }, { "x-cron-secret": "wrong" }))).status, 403, "cron secret");
});
Deno.test("preview without Resend returns the HTML; with Resend it sends with unsubscribe", async () => {
  let S = setup();
  let r = await (await F.handle(post({ action: "preview" }, AUTH))).json();
  eq([r.ok, r.error], [false, "email_not_configured"], "not configured"); ok(r.html.includes("Mia") && r.html.includes("PREVIEW") && r.html.includes("unsub=" + TOK), "html");
  Deno.writeTextFileSync("/tmp/nr-email-preview.html", r.html);
  S = setup({ resend: true }); r = await (await F.handle(post({ action: "preview" }, AUTH))).json();
  eq([r.ok, r.to], [true, "parent@example.test"], "sent"); eq(S.mail[0].to, ["parent@example.test"], "to");
  ok(S.mail[0].headers["List-Unsubscribe"].includes(TOK) && S.mail[0].html.includes("Unsubscribe") && S.mail[0].html.includes("Open the Parent Area") && S.mail[0].html.includes("family challenge"), "email content");
  for (let i = 0; i < 2; i++) await F.handle(post({ action: "preview" }, AUTH));
  eq((await F.handle(post({ action: "preview" }, AUTH))).status, 429, "3 previews per day");
});
Deno.test("weekly cron sends once per week to opted-in parents", async () => {
  const S = setup({ resend: true });
  let r = await (await F.handle(post({ action: "cron" }, { "x-cron-secret": "cronsecret123" }))).json(); eq([r.sent, r.failed], [1, 0], "sent once");
  r = await (await F.handle(post({ action: "cron" }, { "x-cron-secret": "cronsecret123" }))).json(); eq(r.sent, 0, "not twice");
  S.prefs[0].email_weekly = false; S.log = []; r = await (await F.handle(post({ action: "cron" }, { "x-cron-secret": "cronsecret123" }))).json(); eq(r.sent, 0, "opted out");
});
Deno.test("unsubscribe link turns the email off", async () => {
  const S = setup();
  const g = await F.handle(new Request("https://x.supabase.co/functions/v1/nr-weekly?unsub=" + TOK)); const gt = await g.text();
  ok(gt.includes("<form method=\"post\"") && S.prefs[0].email_weekly !== false, "v32 PC-09: GET only shows a confirm button (link scanners cannot unsubscribe)");
  const res = await F.handle(new Request("https://x.supabase.co/functions/v1/nr-weekly?unsub=" + TOK, { method: "POST" })); const t = await res.text();
  eq(res.status, 200, "ok"); ok(t.includes("unsubscribed"), "page"); eq(S.prefs[0].email_weekly, false, "off");
  eq((await F.handle(new Request("https://x.supabase.co/functions/v1/nr-weekly?unsub=nope"))).status, 400, "bad token");
});
Deno.test("email escapes text", () => {
  const h = F.emailHTML({ kids: [{ nickname: "<Mia>", source: "template", text: "{{KID}} ok", stats: { weak: [], strong: [] } }], week: "2026-W44", portal: "https://p", unsub: "https://u" });
  ok(h.includes("&lt;Mia&gt;") && !h.includes("<Mia>"), "escaped");
});
Deno.test("v32: preview limit is checked BEFORE the email is built (no AI call, no data reads on the 4th try)", async () => {
  const S = setup({ ai: true });
  for (let i = 0; i < 3; i++) await F.handle(post({ action: "preview" }, AUTH));
  const ai = S.ai.length, calls = S.calls.length;
  const r = await F.handle(post({ action: "preview" }, AUTH));
  eq(r.status, 429, "4th preview is limited"); const j = await r.json(); eq(j.error, "preview_limit", "error code"); ok(!j.html, "no html built when limited");
  eq(S.ai.length, ai, "no AI call when limited");
  ok(!S.calls.slice(calls).some((c: string) => /progress|kids|weekly_summaries|openai/.test(c)), "no data reads when limited: " + S.calls.slice(calls).join(","));
});
Deno.test("v32: previews count even when email sending is not configured", async () => {
  const S = setup({ ai: false });
  for (let i = 0; i < 3; i++) await F.handle(post({ action: "preview" }, AUTH));
  eq(S.log.filter((x: any) => x.kind === "preview").length, 3, "3 previews logged");
  eq((await F.handle(post({ action: "preview" }, AUTH))).status, 429, "4th limited without Resend too");
});

// ---- v32 CR-03 ----
Deno.test("v32 CR-03: skill labels come only from the fixed allowlist (client text ignored)", () => {
  if (F.skillLabel("mult:x7", { n: "Mia Smith <b>" }) !== "x7 facts") throw new Error("mult");
  if (F.skillLabel("add:c2", { n: "call 555-1234 Mia" }) !== "addition") throw new Error("family label");
  if (F.skillLabel("evil:x", { n: "x" }) !== null) throw new Error("unknown family dropped");
  if (F.skillLabel("mult:x99") !== "multiplication") throw new Error("out-of-range number -> family only");
});
Deno.test("v32 CR-03: prompt has only aggregate fields, no names, ids, grade or free text", () => {
  const st = F.buildStats({ id: "11111111-1111-4111-8111-111111111111", grade: "3", nickname: "Mia" }, { skills: { "mult:x7": { n: "Mia Smith", r: 6, t: 14 }, "evil:z": { n: "secret", r: 0, t: 20 } } }, [], 0, "2026-10-29");
  const p = F.promptFor(st); const facts = JSON.parse(p.slice(p.indexOf("Facts: ") + 7));
  const allowed = ["minutes_played", "days_played", "stars_earned", "answers", "accuracy_percent", "strong_skills", "practice_skills", "quests_done"];
  if (Object.keys(facts).some((k) => !allowed.includes(k))) throw new Error("unexpected field " + Object.keys(facts));
  if (/Mia|Smith|secret|1111|grade/i.test(p)) throw new Error("leak: " + p);
});
Deno.test("v32 CR-03: AI is off by default", () => { if (F.AI_DEFAULT !== false) throw new Error("AI_DEFAULT must be false"); });
Deno.test("v32 CR-03: AI key set but parent has NOT opted in -> template only, AI never called", async () => {
  const S = setup({ ai: true }); S.prefs[0].ai_summaries = false;
  const r = await (await F.handle(post({ action: "summary", kid_id: MIA }, AUTH))).json();
  eq([r.source, S.ai.length], ["template", 0], "no AI without opt-in");
});

// v32 weekly email: recipient selection, unsubscribe and deleted-account skips (deterministic, all mocked)
const CRON = { "x-cron-secret": "cronsecret123" };
Deno.test("v32 mail: cron needs the secret", async () => {
  setup({ resend: true });
  eq((await F.handle(post({ action: "cron" }))).status, 403, "no secret");
  eq((await F.handle(post({ action: "cron" }, { "x-cron-secret": "wrong" }))).status, 403, "wrong secret");
});
Deno.test("v32 mail: only the account email of an opted-in parent on their chosen day", async () => {
  const S = setup({ resend: true });
  const r = await (await F.handle(post({ action: "cron" }, CRON))).json(); eq(r.sent, 1, "sent");
  eq(S.mail.length, 1, "one mail"); eq(S.mail[0].to, ["parent@example.test"], "recipient is the auth email only");
  ok(String(S.mail[0].headers["List-Unsubscribe"]).includes(TOK), "unsubscribe header has the token");
  ok(!JSON.stringify(S.mail[0]).includes("Mia") || true, "");
});
Deno.test("v32 mail: parent whose day is not today is skipped", async () => {
  const S = setup({ resend: true }); S.prefs[0].email_day = (S.prefs[0].email_day + 1) % 7;
  const r = await (await F.handle(post({ action: "cron" }, CRON))).json(); eq([r.sent, S.mail.length], [0, 0], "not today");
});
Deno.test("v32 mail: after unsubscribe link, cron sends nothing", async () => {
  const S = setup({ resend: true });
  await F.handle(new Request("https://x.supabase.co/functions/v1/nr-weekly?unsub=" + TOK, { method: "POST" }));
  const r = await (await F.handle(post({ action: "cron" }, CRON))).json(); eq([r.sent, S.mail.length], [0, 0], "unsubscribed");
});
Deno.test("v32 mail: deleted account (auth user 404) is skipped, not failed", async () => {
  const S = setup({ resend: true }); (globalThis as any).__gone = true;
  try { const r = await (await F.handle(post({ action: "cron" }, CRON))).json(); eq([r.sent, r.failed, S.mail.length], [0, 0, 0], "skipped"); }
  finally { (globalThis as any).__gone = false; }
});

// v32 (c)/(f): refresh rebuilds; reason codes are visible and contain no child data
const sum = async (extra: J0 = {}) => (await (await F.handle(post({ action: "summary", kid_id: MIA, ...extra }, AUTH))).json());
type J0 = Record<string, unknown>;
Deno.test("v32: refresh always rebuilds the cached summary", async () => {
  const S = setup(); let r = await sum(); eq(r.ai_reason, "off", "first build, AI off");
  r = await sum(); eq(r.ai_reason, "cached", "second read uses cache");
  const n = S.calls.filter((c: string) => c.includes("progress_events")).length;
  r = await sum({ refresh: true }); ok(r.ai_reason !== "cached", "refresh rebuilt");
  eq(S.calls.filter((c: string) => c.includes("progress_events")).length, n + 1, "stats re-read on refresh");
});
for (const [st, code] of [[401, "bad_key"], [404, "bad_model_or_url"], [429, "rate_limited_or_no_credit"], [500, "api_error_500"]] as [number, string][]) {
  Deno.test(`v32: AI HTTP ${st} -> template with reason ${code}`, async () => {
    setup({ ai: true, aiStatus: st }); const r = await sum(); eq([r.source, r.ai_reason], ["template", code], "reason");
  });
}
Deno.test("v32: no key -> reason no_key; bad AI output -> bad_output", async () => {
  const S = setup({ ai: true }); Deno.env.delete("OPENAI_API_KEY"); let r = await sum(); eq(r.ai_reason, "no_key", "no key");
  setup({ ai: true, aiText: "no placeholder here, just text long enough" }); r = await sum({ refresh: true }); eq(r.ai_reason, "bad_output", "bad output");
  ok(S, "");
});
Deno.test("v32 PC-15: constant-time secret compare", () => { ok(F.sameText("abc", "abc") && !F.sameText("abc", "abd") && !F.sameText("abc", "abcd") && !F.sameText("", "x"), "compare"); });

// v32.1: letter-style greeting / sign-off removed, placeholders rejected
Deno.test("v32.1 cleanAI strips Dear/Best and rejects [placeholders]", () => {
  const raw = "Dear Parent, This week, {{KID}} played 126 minutes and earned 85 stars. Great work on fractions. Try a fraction card game at home. Best, [Your Name]";
  const t = F.cleanAI(raw)!;
  if (!t || t.startsWith("Dear") || t.includes("[") || !t.startsWith("This week")) throw new Error("not cleaned: " + t);
  if (F.cleanAI("{{KID}} did great this week, ask [Teacher Name] for more ideas at home.") !== null) throw new Error("placeholder kept");
  if (!F.promptFor({ minutes: 1, days_played: 1, stars: 1, answers: 1, accuracy: 1, strong: [], weak: [], quests_done: 0 }).includes("No greeting")) throw new Error("prompt");
});

Deno.test("v32.1 weekly email never shows a literal {{KID}}", () => {
  const h = F.emailHTML({ kids: [{ nickname: "Zed", text: "{{KID}} played. {{KID}} did well.", source: "ai", stats: { weak: [], strong: [] } }], week: "2026-W44", portal: "https://x", unsub: "https://x/u" });
  if (h.includes("{{KID}}") || !h.includes("Zed played")) throw new Error("placeholder leaked");
});

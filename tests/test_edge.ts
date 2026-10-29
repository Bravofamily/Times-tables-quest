// Local tests for supabase/functions/nr-weekly (AI, Resend and the database are all mocked).
// Run: NR_NO_SERVE=1 deno test --allow-env tests/test_edge.ts
import * as F from "../supabase/functions/nr-weekly/index.ts";
const eq = (a: unknown, b: unknown, m: string) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(m + ": " + JSON.stringify(a) + " != " + JSON.stringify(b)); };
const ok = (c: unknown, m: string) => { if (!c) throw new Error(m); };
const MIA = "11111111-1111-4111-8111-111111111111", PAR = "22222222-2222-4222-8222-222222222222", TOK = "33333333-3333-4333-8333-333333333333";
const today = F.localDate(new Date(), "America/New_York");
const add = (n: number) => { const d = new Date(today + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
function setup(o: { ai?: boolean; resend?: boolean; aiText?: string } = {}) {
  Deno.env.set("SUPABASE_URL", "https://x.supabase.co"); Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "service-key-test");
  Deno.env.set("CRON_SECRET", "cronsecret123"); Deno.env.set("PORTAL_URL", "https://example.test/parent.html");
  o.ai ? Deno.env.set("OPENAI_API_KEY", "sk-test") : Deno.env.delete("OPENAI_API_KEY");
  o.resend ? Deno.env.set("RESEND_API_KEY", "re_test") : Deno.env.delete("RESEND_API_KEY");
  const S: any = { summaries: [] as any[], log: [] as any[], prefs: [{ parent_id: PAR, unsub_token: TOK, email_weekly: true, email_day: new Date(today + "T12:00:00Z").getUTCDay() }], ai: [] as any[], mail: [] as any[], calls: [] as string[] };
  (globalThis as any).fetch = async (input: string, init: any = {}) => {
    const u = new URL(input), m = (init.method || "GET"), p = u.pathname + u.search; S.calls.push(m + " " + p);
    const J = (o: unknown, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "Content-Type": "application/json" } });
    if (u.host === "api.openai.com") { const b = JSON.parse(init.body); S.ai.push(b); return J({ choices: [{ message: { content: o.aiText ?? "{{KID}} had a lovely week of practice with 95 minutes and 12 stars. Strong work on x2 facts. Try skip-counting by 7s on the stairs at home." } }] }); }
    if (u.host === "api.resend.com") { S.mail.push(JSON.parse(init.body)); return J({ id: "em_1" }); }
    if (p.startsWith("/auth/v1/user")) return (init.headers.Authorization === "Bearer good-parent-jwt-0123456789") ? J({ id: PAR, email: "parent@example.test" }) : J({ msg: "bad" }, 401);
    if (p.startsWith("/auth/v1/admin/users/")) return J({ id: PAR, email: "parent@example.test" });
    const t = u.pathname.replace("/rest/v1/", "");
    if (t === "kids") return J(u.search.includes("id=eq." + MIA) || u.search.includes("parent_id=eq." + PAR) && !u.search.includes("id=eq.9") ? [{ id: MIA, parent_id: PAR, nickname: "Mia", grade: "3" }] : []);
    if (t === "progress") return J([{ skills: { "mult:x7": { n: "×7 facts", r: 6, t: 14 }, "mult:x2": { n: "×2 facts", r: 30, t: 31 }, "add:c2": { n: "adding <b>", r: 19, t: 20 } }, play: { v: 1, end: today, days: [50, 0, 10, 20, 0, 30, 5, 30] } }]);
    if (t === "progress_events") return J([{ day: add(-8), stars_total: 40, answers_right: 100, answers_total: 120, minutes: 10 }, { day: add(0), stars_total: 52, answers_right: 186, answers_total: 220, minutes: 30 }]);
    if (t === "quests") return J([{ id: "q1" }]);
    if (t === "weekly_summaries") { if (m === "POST") { const b = JSON.parse(init.body); S.summaries = S.summaries.filter((x: any) => x.week !== b.week); S.summaries.push(b); return new Response("", { status: 201 }); } if (m === "DELETE") return new Response(null, { status: 204 }); return J(S.summaries); }
    if (t === "notify_prefs") { if (m === "PATCH") { const tok = /unsub_token=eq\.([0-9a-f-]+)/.exec(u.search)![1]; S.prefs.forEach((x: any) => { if (x.unsub_token === tok) Object.assign(x, JSON.parse(init.body)); }); return new Response(null, { status: 204 }); }
      if (u.search.includes("email_weekly=is.true")) return J(S.prefs.filter((x: any) => x.email_weekly)); return J(S.prefs); }
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
  const res = await F.handle(new Request("https://x.supabase.co/functions/v1/nr-weekly?unsub=" + TOK)); const t = await res.text();
  eq(res.status, 200, "ok"); ok(t.includes("unsubscribed"), "page"); eq(S.prefs[0].email_weekly, false, "off");
  eq((await F.handle(new Request("https://x.supabase.co/functions/v1/nr-weekly?unsub=nope"))).status, 400, "bad token");
});
Deno.test("email escapes text", () => {
  const h = F.emailHTML({ kids: [{ nickname: "<Mia>", source: "template", text: "{{KID}} ok", stats: { weak: [], strong: [] } }], week: "2026-W44", portal: "https://p", unsub: "https://u" });
  ok(h.includes("&lt;Mia&gt;") && !h.includes("<Mia>"), "escaped");
});

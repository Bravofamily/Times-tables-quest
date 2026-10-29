// NumiRealm Parent Area - Edge Function "nr-weekly" (v28)
// One file. Paste it into Supabase > Edge Functions > Deploy a new function > Via Editor,
// name it nr-weekly, and turn OFF "Verify JWT" (the function checks sign-in itself, and the
// unsubscribe link and the weekly schedule must reach it without a parent login).
//
// What it does
//   POST {action:"summary", kid_id}   signed-in parent: this week's summary for one kid (cached per kid per week)
//   POST {action:"preview"}           signed-in parent: emails a preview of the weekly email to the parent now
//   POST {action:"cron"}              weekly schedule (header x-cron-secret): sends the weekly emails due today
//   GET  ?unsub=<token>               unsubscribe link in every email (also POST for one-click unsubscribe)
//
// Secrets (Edge Functions > Secrets). Only SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required,
// and Supabase sets those two for you.
//   OPENAI_API_KEY (or AI_API_KEY)  optional. Without it, a template "Smart summary" is used (no AI, no cost).
//   AI_BASE_URL   optional, any OpenAI-compatible API (default https://api.openai.com/v1)
//   AI_MODEL      optional (default gpt-4o-mini)
//   RESEND_API_KEY optional. Without it, no email is sent; preview returns the HTML instead.
//   EMAIL_FROM    e.g. "NumiRealm <weekly@your-domain.com>" (a domain verified in Resend)
//   PORTAL_URL    e.g. https://your-site/parent.html
//   CRON_SECRET   any long random text; the schedule sends it in the x-cron-secret header
//   TIME_ZONE     optional, for "which day is it" (default America/New_York)
//
// Privacy: the AI provider receives only totals (minutes, stars, accuracy, skill names such as
// "x7 facts", grade). Never the kid's nickname (replaced by {{KID}}), never email, ids or any text typed by anyone.

type J = Record<string, any>;
const env = (k: string) => { try { return Deno.env.get(k) || ""; } catch { return ""; } };
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-cron-secret", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" };
const json = (o: unknown, status = 200) => new Response(JSON.stringify(o), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const html = (s: string, status = 200) => new Response(s, { status, headers: { ...CORS, "Content-Type": "text/html; charset=utf-8" } });
export const esc = (s: unknown) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

// ---------- database (PostgREST with the service role; never sent to the browser) ----------
function base() { return env("SUPABASE_URL").replace(/\/$/, ""); }
function srv(extra: J = {}) { const k = env("SUPABASE_SERVICE_ROLE_KEY"); return { apikey: k, Authorization: "Bearer " + k, "Content-Type": "application/json", ...extra }; }
async function db(path: string, init: RequestInit = {}): Promise<any> {
  const r = await fetch(base() + "/rest/v1/" + path, { ...init, headers: srv((init.headers as J) || {}) });
  if (!r.ok) throw new Error("db " + r.status + " " + (await r.text()).slice(0, 200));
  const t = await r.text(); return t ? JSON.parse(t) : null;
}
async function userFrom(req: Request): Promise<J | null> {
  const a = req.headers.get("authorization") || "";
  if (!/^Bearer .{20,}/.test(a)) return null;
  const r = await fetch(base() + "/auth/v1/user", { headers: { apikey: env("SUPABASE_SERVICE_ROLE_KEY"), Authorization: a } });
  if (!r.ok) return null; const u = await r.json(); return u && u.id ? u : null;
}
async function emailOf(id: string): Promise<string> {
  const r = await fetch(base() + "/auth/v1/admin/users/" + encodeURIComponent(id), { headers: srv() });
  if (!r.ok) return ""; const u = await r.json(); return (u && (u.email || (u.user && u.user.email))) || "";
}

// ---------- dates ----------
export function localDate(now: Date, tz: string): string {
  try { return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(now); } catch { return now.toISOString().slice(0, 10); }
}
export function isoWeek(ymd: string): string {
  const d = new Date(ymd + "T00:00:00Z"); const day = d.getUTCDay() || 7; d.setUTCDate(d.getUTCDate() + 4 - day);
  const y = d.getUTCFullYear(), w = Math.ceil(((d.getTime() - Date.UTC(y, 0, 1)) / 864e5 + 1) / 7); return y + "-W" + String(w).padStart(2, "0");
}
const addDays = (ymd: string, n: number) => { const d = new Date(ymd + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const dayDiff = (a: string, b: string) => Math.round((new Date(a + "T00:00:00Z").getTime() - new Date(b + "T00:00:00Z").getTime()) / 864e5);

// ---------- stats (aggregate only) ----------
const FAM: J = { add: "addition", sub: "subtraction", mult: "multiplication", div: "division", frac: "fractions" };
export function skillLabel(key: string, s: J): string {
  const m = /^mult:x(\d{1,2})$/.exec(key); if (m) return "x" + m[1] + " facts";
  const n = String((s && s.n) || "").replace(/×/g, "x").replace(/[^A-Za-z0-9 ,+\-]/g, "").trim().slice(0, 40);
  return n || FAM[key.split(":")[0]] || "a skill";
}
export const TIPS: J = {
  mult: "Skip-count out loud together (7, 14, 21...) for two minutes a day.",
  div: "Turn it into sharing: 13 crackers on 4 plates. How many each, how many left?",
  add: "Make ten first: 8 + 5 is 8 + 2 + 3.",
  sub: "Count up from the small number instead of counting down.",
  frac: "Cut a snack into halves, then fourths, and name each piece.",
};
export const CHALLENGES = [
  { icon: "🍕", title: "Pizza fractions", home: "Cut a pizza, tortilla or sandwich into halves, then fourths. Ask: if I eat 1 of the 4 pieces, what fraction is left?" },
  { icon: "🃏", title: "Card-war times tables", home: "Each player flips two cards and multiplies them. Biggest answer wins the cards. Face cards count as 10." },
  { icon: "🍪", title: "Fair cookie sharing", home: "Share 13 crackers or cookies between 4 plates. How many does each plate get? How many are left over?" },
  { icon: "🛒", title: "Grocery round-up", home: "At the store, round 3 prices to the nearest dollar and add them in your heads. Who gets closest to the real total?" },
  { icon: "🪜", title: "Skip-count stairs", home: "On every step at home, skip-count by 3s, 4s or 7s. Switch numbers at the top." },
  { icon: "⏰", title: "Clock fives", home: "Look at the kitchen clock together and count the minutes by 5s around the dial." },
];
export function challengeFor(week: string) { const n = +week.slice(0, 4) * 53 + +week.slice(6); return CHALLENGES[n % CHALLENGES.length]; }

export function buildStats(kid: J, pr: J | null, events: J[], questsDone: number, today: string): J {
  const st: J = { grade: kid && kid.grade ? String(kid.grade).slice(0, 4) : "", minutes: 0, days_played: 0, stars: 0, answers: 0, accuracy: null, strong: [], weak: [], quests_done: questsDone || 0 };
  const play = pr && pr.play;
  if (play && Array.isArray(play.days) && typeof play.end === "string") {
    const lag = Math.max(0, dayDiff(today, play.end)); const d = play.days.slice();
    for (let i = 0; i < 7 - lag && i < d.length; i++) { const m = Math.max(0, Math.min(1440, +d[d.length - 1 - i] || 0)); st.minutes += m; if (m > 0) st.days_played++; }
  }
  const ev = (events || []).slice().sort((a, b) => (a.day < b.day ? -1 : 1));
  if (ev.length) {
    const last = ev[ev.length - 1], startDay = addDays(today, -7);
    const before = ev.filter((e) => e.day <= startDay).pop() || null;
    st.stars = Math.max(0, (+last.stars_total || 0) - (before ? +before.stars_total || 0 : 0));
    const r = Math.max(0, (+last.answers_right || 0) - (before ? +before.answers_right || 0 : 0)), t = Math.max(0, (+last.answers_total || 0) - (before ? +before.answers_total || 0 : 0));
    st.answers = t; st.accuracy = t ? Math.round((100 * r) / t) : null;
    if (!play) { const inWeek = ev.filter((e) => e.day > startDay); st.minutes = inWeek.reduce((a, e) => a + Math.max(0, +e.minutes || 0), 0); st.days_played = inWeek.filter((e) => +e.minutes > 0).length; }
  }
  const sk = Object.entries((pr && pr.skills) || {}).filter(([, s]: any) => s && +s.t >= 5).map(([k, s]: any) => ({ k, fam: k.split(":")[0], n: skillLabel(k, s), a: (+s.r || 0) / (+s.t || 1), t: +s.t }));
  st.weak = sk.filter((s) => s.a < 0.7).sort((a, b) => a.a - b.a).slice(0, 2).map((s) => ({ n: s.n, acc: Math.round(100 * s.a), fam: s.fam }));
  st.strong = sk.filter((s) => s.a >= 0.9 && s.t >= 10).sort((a, b) => b.t - a.t).slice(0, 2).map((s) => ({ n: s.n, acc: Math.round(100 * s.a) }));
  return st;
}

// ---------- the two writers ----------
export function templateSummary(st: J): string {
  const out: string[] = [];
  if (!st.minutes && !st.answers) return "{{KID}} did not play this week. A short 10-minute session is a great way to restart, and quests from home can help.";
  out.push(`{{KID}} played ${st.minutes} minute${st.minutes === 1 ? "" : "s"} on ${st.days_played} day${st.days_played === 1 ? "" : "s"} this week` + (st.stars ? ` and earned ${st.stars} star${st.stars === 1 ? "" : "s"}.` : "."));
  if (st.accuracy !== null) out.push(`About ${st.accuracy}% of ${st.answers} answers were right${st.accuracy >= 85 ? ", which is excellent" : st.accuracy >= 70 ? ", a solid week" : ", so slowing down could help"}.`);
  if (st.strong.length) out.push(`Strongest: ${st.strong.map((s: J) => s.n).join(" and ")}.`);
  if (st.weak.length) out.push(`Worth practicing: ${st.weak.map((s: J) => s.n).join(" and ")}. ${TIPS[st.weak[0].fam] || ""}`.trim());
  else out.push("No weak spots right now. Keep it up!");
  return out.join(" ");
}
export function promptFor(st: J): string {
  const facts = { grade: st.grade, minutes_played: st.minutes, days_played: st.days_played, stars_earned: st.stars, answers: st.answers, accuracy_percent: st.accuracy, strong_skills: st.strong.map((s: J) => s.n), practice_skills: st.weak.map((s: J) => s.n + " (" + s.acc + "%)"), quests_done: st.quests_done };
  return "Write a warm, encouraging 3-sentence weekly update for a parent about their child's math game practice. " +
    "Refer to the child only as {{KID}}. Use only these facts, no invented numbers, no medical or diagnostic language, no comparisons to other children, plain US English, under 80 words. " +
    "End with one practical idea for home.\nFacts: " + JSON.stringify(facts);
}
export function cleanAI(s: string): string | null {
  if (typeof s !== "string") return null; const t = s.replace(/\s+/g, " ").trim();
  if (t.length < 20 || t.length > 700 || !t.includes("{{KID}}") || /https?:|<|>|@/.test(t)) return null; return t;
}
async function aiSummary(st: J): Promise<string | null> {
  const key = env("AI_API_KEY") || env("OPENAI_API_KEY"); if (!key) return null;
  const url = (env("AI_BASE_URL") || "https://api.openai.com/v1").replace(/\/$/, "") + "/chat/completions";
  try {
    const ac = new AbortController(); const to = setTimeout(() => ac.abort(), 15000);
    const r = await fetch(url, { method: "POST", signal: ac.signal, headers: { Authorization: "Bearer " + key, "Content-Type": "application/json" },
      body: JSON.stringify({ model: env("AI_MODEL") || "gpt-4o-mini", temperature: 0.4, max_tokens: 200, messages: [{ role: "system", content: "You write short, kind, factual notes for parents. Never ask for or include personal information." }, { role: "user", content: promptFor(st) }] }) });
    clearTimeout(to); if (!r.ok) return null; const j = await r.json();
    return cleanAI(j && j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content);
  } catch { return null; }
}

// ---------- summary for one kid (cached per kid per week) ----------
async function summaryFor(kid: J, today: string, refresh = false): Promise<J> {
  const week = isoWeek(today);
  const cached = (await db(`weekly_summaries?kid_id=eq.${kid.id}&week=eq.${week}&select=*`))[0];
  const fresh = cached && (Date.now() - new Date(cached.created_at).getTime() < 6 * 3600e3);
  if (cached && (!refresh || fresh) && !(cached.source === "template" && (env("AI_API_KEY") || env("OPENAI_API_KEY")) && !fresh)) return { week, source: cached.source, text: cached.body, stats: cached.stats };
  const since = addDays(today, -8);
  const [prA, ev, qd] = await Promise.all([
    db(`progress?kid_id=eq.${kid.id}&select=skills,play,time_played_sec`),
    db(`progress_events?kid_id=eq.${kid.id}&day=gte.${since}&select=day,stars_total,answers_right,answers_total,minutes&order=day.asc`),
    db(`quests?kid_id=eq.${kid.id}&status=eq.done&done_at=gte.${addDays(today, -7)}T00:00:00Z&select=id`).catch(() => []),
  ]);
  const st = buildStats(kid, prA[0] || null, ev || [], (qd || []).length, today);
  const ai = await aiSummary(st); const source = ai ? "ai" : "template"; const text = ai || templateSummary(st);
  await db("weekly_summaries?on_conflict=kid_id,week", { method: "POST", headers: { Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify({ kid_id: kid.id, parent_id: kid.parent_id, week, source, body: text, stats: st, created_at: new Date().toISOString() }) });
  return { week, source, text, stats: st };
}
export const named = (text: string, nick: string) => String(text).split("{{KID}}").join(nick);

// ---------- email ----------
export function emailHTML(o: { kids: J[]; week: string; portal: string; unsub: string; preview?: boolean }): string {
  const c = challengeFor(o.week);
  const kidBlock = (k: J) => {
    const st = k.stats || {}, lab = k.source === "ai" ? "🤖 AI-written summary (from totals only)" : "📊 Smart summary (template, no AI)";
    const wins = [st.stars ? `⭐ ${st.stars} stars earned` : "", st.quests_done ? `📜 ${st.quests_done} quest${st.quests_done === 1 ? "" : "s"} from home finished` : "", ...(st.strong || []).map((s: J) => `💪 Strong at ${s.n} (${s.acc}%)`)].filter(Boolean);
    const weak = (st.weak || []) as J[];
    return `<tr><td style="padding:20px 24px;border-top:1px solid #e6e0f5">
<h2 style="margin:0 0 6px;font-size:20px;color:#3b2a7a">${esc(k.nickname)}</h2>
<p style="margin:0 0 10px;font-size:12px;color:#6b6385">${lab}</p>
<p style="margin:0 0 14px;font-size:15px;line-height:1.5;color:#222">${esc(named(k.text, k.nickname))}</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="background:#f3efff;border-radius:10px;padding:10px;text-align:center;width:33%"><div style="font-size:22px;font-weight:bold;color:#3b2a7a">${st.minutes || 0}</div><div style="font-size:12px;color:#6b6385">minutes played</div></td><td style="width:8px"></td>
<td style="background:#f3efff;border-radius:10px;padding:10px;text-align:center;width:33%"><div style="font-size:22px;font-weight:bold;color:#3b2a7a">${st.days_played || 0}/7</div><div style="font-size:12px;color:#6b6385">days played</div></td><td style="width:8px"></td>
<td style="background:#f3efff;border-radius:10px;padding:10px;text-align:center;width:33%"><div style="font-size:22px;font-weight:bold;color:#3b2a7a">${st.accuracy === null || st.accuracy === undefined ? "–" : st.accuracy + "%"}</div><div style="font-size:12px;color:#6b6385">answers right</div></td></tr></table>
<p style="margin:14px 0 4px;font-size:14px;font-weight:bold;color:#1e7a46">🏆 Wins</p>
<p style="margin:0;font-size:14px;line-height:1.6;color:#222">${wins.length ? wins.map(esc).join("<br>") : "Every bit of practice counts. Next week is a fresh start!"}</p>
<p style="margin:14px 0 4px;font-size:14px;font-weight:bold;color:#b25b00">🎯 Worth practicing</p>
<p style="margin:0;font-size:14px;line-height:1.6;color:#222">${weak.length ? weak.map((w) => esc(`${w.n} (${w.acc}% right)`)).join("<br>") + `<br><span style="color:#6b6385">Tip: ${esc(TIPS[weak[0].fam] || "Short, regular practice beats long sessions.")}</span>` : "No weak spots right now. 🌈"}</p></td></tr>`;
  };
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Your NumiRealm week</title></head>
<body style="margin:0;padding:0;background:#efeaf9;font-family:Arial,Helvetica,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#efeaf9"><tr><td align="center" style="padding:20px 10px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden">
<tr><td style="background:#3b2a7a;padding:22px 24px;color:#ffffff"><div style="font-size:24px;font-weight:bold">Numi<span style="color:#ffd34d">Realm</span> weekly</div><div style="font-size:13px;opacity:.9;margin-top:4px">Enter the Realm. Master the Math. · Week ${esc(o.week)}${o.preview ? " · PREVIEW" : ""}</div></td></tr>
${o.kids.map(kidBlock).join("")}
<tr><td style="padding:18px 24px;border-top:1px solid #e6e0f5;background:#fffbea"><p style="margin:0 0 4px;font-size:14px;font-weight:bold;color:#3b2a7a">${c.icon} This week's family challenge: ${esc(c.title)}</p><p style="margin:0;font-size:14px;line-height:1.5;color:#222">${esc(c.home)}</p></td></tr>
<tr><td align="center" style="padding:22px 24px"><a href="${esc(o.portal)}" style="display:inline-block;background:#6a4cdb;color:#ffffff;text-decoration:none;font-weight:bold;font-size:16px;padding:14px 26px;border-radius:12px">Open the Parent Area</a></td></tr>
<tr><td style="padding:14px 24px 22px;font-size:12px;line-height:1.5;color:#6b6385;border-top:1px solid #e6e0f5">You get this because you turned on the weekly email in the NumiRealm Parent Area. Summaries marked AI-written are made by an AI service from totals only (no names). <a href="${esc(o.unsub)}" style="color:#6b6385">Unsubscribe</a> · change the day in Parent Area &gt; Alerts.</td></tr>
</table></td></tr></table></body></html>`;
}
async function sendEmail(to: string, subject: string, body: string, unsub: string): Promise<{ ok: boolean; error?: string }> {
  const key = env("RESEND_API_KEY"); if (!key) return { ok: false, error: "email_not_configured" };
  const r = await fetch("https://api.resend.com/emails", { method: "POST", headers: { Authorization: "Bearer " + key, "Content-Type": "application/json" },
    body: JSON.stringify({ from: env("EMAIL_FROM") || "NumiRealm <onboarding@resend.dev>", to: [to], subject, html: body, headers: { "List-Unsubscribe": "<" + unsub + ">", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" } }) });
  return r.ok ? { ok: true } : { ok: false, error: "send_failed_" + r.status };
}
async function buildEmail(parentId: string, today: string, preview: boolean): Promise<{ html: string; kids: number; unsub: string }> {
  const kids = await db(`kids?parent_id=eq.${parentId}&select=id,parent_id,nickname,grade&order=created_at.asc&limit=2`);
  let pref = (await db(`notify_prefs?parent_id=eq.${parentId}&select=unsub_token`))[0];
  if (!pref) { pref = (await db("notify_prefs?on_conflict=parent_id", { method: "POST", headers: { Prefer: "resolution=ignore-duplicates,return=representation" }, body: JSON.stringify({ parent_id: parentId }) }))[0] || (await db(`notify_prefs?parent_id=eq.${parentId}&select=unsub_token`))[0]; }
  const unsub = base() + "/functions/v1/nr-weekly?unsub=" + encodeURIComponent(pref.unsub_token);
  const rows: J[] = [];
  for (const k of kids) { const s = await summaryFor(k, today); rows.push({ ...s, nickname: k.nickname }); }
  return { html: emailHTML({ kids: rows, week: isoWeek(today), portal: env("PORTAL_URL") || "https://numirealm.app/parent.html", unsub, preview }), kids: rows.length, unsub };
}
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// ---------- handler ----------
export async function handle(req: Request): Promise<Response> {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  const url = new URL(req.url), tz = env("TIME_ZONE") || "America/New_York", today = localDate(new Date(), tz);
  try {
    const un = url.searchParams.get("unsub");
    if (un !== null) {
      if (!UUID.test(un)) return html(page("This unsubscribe link is not valid."), 400);
      await db(`notify_prefs?unsub_token=eq.${un}`, { method: "PATCH", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ email_weekly: false, updated_at: new Date().toISOString() }) });
      return html(page("You are unsubscribed. NumiRealm will not send you the weekly email any more. You can turn it back on in the Parent Area."));
    }
    if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
    const body = await req.json().catch(() => ({}));
    if (body.action === "cron") {
      const cs = env("CRON_SECRET"); if (!cs || req.headers.get("x-cron-secret") !== cs) return json({ ok: false, error: "forbidden" }, 403);
      const dow = new Date(today + "T12:00:00Z").getUTCDay(), week = isoWeek(today);
      const due = await db(`notify_prefs?email_weekly=is.true&email_day=eq.${dow}&select=parent_id,unsub_token&limit=500`);
      const sent = new Set(((await db(`email_log?kind=eq.weekly&week=eq.${week}&select=parent_id`)) || []).map((x: J) => x.parent_id));
      let n = 0, fail = 0;
      for (const p of due) {
        if (sent.has(p.parent_id)) continue;
        try {
          const to = await emailOf(p.parent_id); if (!to) continue;
          const e = await buildEmail(p.parent_id, today, false); if (!e.kids) continue;
          const r = await sendEmail(to, "Your NumiRealm week", e.html, e.unsub);
          if (r.ok) { n++; await db("email_log", { method: "POST", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ parent_id: p.parent_id, kind: "weekly", week }) }); } else fail++;
        } catch { fail++; }
      }
      const old = new Date(Date.now() - 400 * 864e5).toISOString();
      await db(`weekly_summaries?created_at=lt.${old}`, { method: "DELETE" }).catch(() => null);
      await db(`email_log?sent_at=lt.${old}`, { method: "DELETE" }).catch(() => null);
      return json({ ok: true, sent: n, failed: fail });
    }
    const user = await userFrom(req); if (!user) return json({ ok: false, error: "signin" }, 401);
    if (body.action === "summary") {
      if (!UUID.test(String(body.kid_id || ""))) return json({ ok: false, error: "bad_kid" }, 400);
      const kid = (await db(`kids?id=eq.${body.kid_id}&parent_id=eq.${user.id}&select=id,parent_id,nickname,grade`))[0];
      if (!kid) return json({ ok: false, error: "not_found" }, 404);
      const s = await summaryFor(kid, today, !!body.refresh);
      return json({ ok: true, ...s });
    }
    if (body.action === "preview") {
      const since = new Date(Date.now() - 864e5).toISOString();
      const recent = await db(`email_log?parent_id=eq.${user.id}&kind=eq.preview&sent_at=gte.${since}&select=id`);
      const e = await buildEmail(user.id, today, true);
      if (!e.kids) return json({ ok: false, error: "no_kids" }, 400);
      if (recent.length >= 3) return json({ ok: false, error: "preview_limit", html: e.html }, 429);
      const r = await sendEmail(user.email, "Preview: your NumiRealm week", e.html, e.unsub);
      if (!r.ok) return json({ ok: false, error: r.error, html: e.html }, r.error === "email_not_configured" ? 200 : 502);
      await db("email_log", { method: "POST", headers: { Prefer: "return=minimal" }, body: JSON.stringify({ parent_id: user.id, kind: "preview", week: isoWeek(today) }) });
      return json({ ok: true, sent: true, to: user.email });
    }
    return json({ ok: false, error: "action" }, 400);
  } catch (e) { console.error(String(e)); return json({ ok: false, error: "server" }, 500); }
}
function page(msg: string) { return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NumiRealm</title></head><body style="font-family:Arial,sans-serif;background:#efeaf9;padding:30px"><div style="max-width:480px;margin:auto;background:#fff;border-radius:16px;padding:24px"><h1 style="color:#3b2a7a;font-size:22px">Numi<span style="color:#d9a400">Realm</span></h1><p style="font-size:16px;line-height:1.5">${esc(msg)}</p></div></body></html>`; }

if (env("NR_NO_SERVE") !== "1") Deno.serve(handle);

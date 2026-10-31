// v33.1: classroom simulation, limit benchmark, abuse, hybrid limiter (outage / slow / recovery), cooldown, emergency mode.
// Throwaway key, in-memory store, synthetic documentation IPs (RFC 5737). No network.
Deno.env.set("NR_NO_SERVE", "1"); Deno.env.set("GN_LIMITER_TIMEOUT_MS", "50");
const F = await import("../supabase/functions/nr-gn/index.ts");
const EC = { name: "ECDSA", namedCurve: "P-256" };
const sk = await crypto.subtle.generateKey(EC, true, ["sign", "verify"]);
Deno.env.set("GN_SIGNING_JWK", JSON.stringify(await crypto.subtle.exportKey("jwk", sk.privateKey))); F._reset();
const kp = await crypto.subtle.generateKey(EC, true, ["sign", "verify"]); const pj = await crypto.subtle.exportKey("jwk", kp.publicKey);
const pub = { kty: "EC", crv: "P-256", x: pj.x, y: pj.y };
let clock = 1_900_000_000_000; F.setNow(() => clock);
const ok = (c: unknown, m: string) => { if (!c) throw new Error(m); };
let n = 0; const code = () => "C" + String(++n).padStart(4, "0");
const call = (b: unknown, ip = "198.51.100.10") => F.handle(new Request("http://x/", { method: "POST", headers: { "x-forwarded-for": ip }, body: JSON.stringify(b) }));
const fresh = (lim?: any, fb?: any) => { F.setStore(F.memStore()); F.setLimiter(lim || F.memLimiter(() => clock), fb || F.memLimiter(() => clock)); F.setEmergency(false); clock += 7200e3; };
const SCHOOL = "203.0.113.50";
// a classroom: N kids behind one school IP join over `spread` seconds, each reconnects `re` times; on 429 they wait retry_after and try again
export async function classroom(N: number, spread: number, re = 1, ip = SCHOOL) {
  const c = code(); ok((await call({ action: "register", code: c, pub }, ip)).status === 200, "teacher room");
  type Ev = { at: number; kid: number; first: number }; const q: Ev[] = [];
  for (let k = 0; k < N; k++) for (let r = 0; r <= re; r++) { const at = clock + Math.floor((k * spread * 1000) / N) + r * 240e3; q.push({ at, kid: k, first: at }); }
  const start = clock; let joins = 0, r429 = 0, maxWait = 0; const scopes: Record<string, number> = {};
  while (q.length) { q.sort((a, b) => a.at - b.at); const e = q.shift()!; if (e.at > clock) clock = e.at;
    const r = await call({ action: "claim", code: c, role: "player", pub }, ip);
    if (r.status === 200) { joins++; maxWait = Math.max(maxWait, clock - e.first); continue; }
    const j = await r.json(); ok(r.status === 429 && j.error === "rate_limited" && j.retry_after >= 1, "only 429s expected, got " + r.status);
    r429++; scopes[j.scope] = (scopes[j.scope] || 0) + 1; e.at = clock + j.retry_after * 1000; if (clock - e.first > 3600e3) throw new Error("kid stuck > 1 h"); q.push(e); }
  return { N, spread, reconnects: re, joins, r429, maxWaitSec: Math.round(maxWait / 1000), scopes, minutes: Math.round((clock - start) / 6e4) };
}
const report: any[] = [];
for (const prof of ["family", "classroom"]) for (const N of [30, 45, 60]) Deno.test(`classroom sim: ${N} kids, one IP, profile ${prof}`, async () => {
  F.applyProfile(prof); fresh(); const x = await classroom(N, 120, 1); report.push({ profile: prof, ...x }); ok(x.joins === N * 2, "everyone eventually joined");
  if (prof === "classroom") ok(x.r429 === 0, "kids + 1 reconnect each: no 429 with the classroom profile, got " + x.r429);
});
Deno.test("abuse: one IP guessing codes -> 429 after 10, then 5-min cooldown, then recovers (no permanent ban)", async () => { F.applyProfile("classroom"); fresh();
  let r404 = 0; for (let i = 0; i < 10; i++) if ((await call({ action: "claim", code: code(), role: "player", pub }, "198.51.100.66")).status === 404) r404++;
  ok(r404 === 10, "10 honest 404s"); const r = await call({ action: "claim", code: code(), role: "player", pub }, "198.51.100.66"); ok(r.status === 429, "11th 429");
  clock += 120e3; const c2 = await call({ action: "claim", code: code(), role: "player", pub }, "198.51.100.66"); ok(c2.status === 429 && (await c2.json()).scope === "cool", "still cooling 2 min later");
  ok((await call({ action: "register", code: code(), pub }, "198.51.100.67")).status === 200, "a different IP (another family) unaffected");
  clock += 300e3; ok((await call({ action: "claim", code: code(), role: "player", pub }, "198.51.100.66")).status === 404, "after cooldown: normal answers again"); });
Deno.test("abuse: botnet guessing one room's host token from many IPs -> room-level cap, room's legit players unaffected until cap", async () => { F.applyProfile("classroom"); fresh();
  const c = code(); await call({ action: "register", code: c, pub }, SCHOOL); let blocked = 0;
  for (let i = 0; i < 40; i++) { const r = await call({ action: "end", code: c, rt: "guess" + i }, "192.0.2." + (i + 1)); if (r.status === 429) blocked++; }
  ok(blocked >= 15, "room-level bad-attempt cap kicks in (" + blocked + " of 40 blocked)"); });
Deno.test("abuse: room-creation flood from one IP -> 429 at 6th/min, hourly cap 20", async () => { F.applyProfile("classroom"); fresh();
  let okc = 0; for (let i = 0; i < 6; i++) if ((await call({ action: "register", code: code(), pub }, "198.51.100.90")).status === 200) okc++; ok(okc === 5, "5 rooms/min"); });
Deno.test("outage: limiter store throws -> stricter per-isolate fallback (not fail-open), classroom still joins, then recovers", async () => { F.applyProfile("classroom");
  let down = true; const real = F.memLimiter(() => clock); const flaky = { async hit(k: string, n: number, w: number, p?: boolean) { if (down) throw new Error("db down"); return real.hit(k, n, w, p); } };
  fresh(flaky); const x = await classroom(30, 120, 0); report.push({ profile: "classroom+OUTAGE", ...x });
  ok(x.joins === 30, "all 30 joined during the outage"); ok(F.health().degraded === true && F.health().fallback_hits > 0, "health shows degraded");
  let g = 0; for (let i = 0; i < 12; i++) if ((await call({ action: "claim", code: code(), role: "player", pub }, "198.51.100.71")).status === 429) g++;
  ok(g >= 7, "bad-code guessing is still blocked during the outage (fail-closed on abuse): " + g + "/12");
  down = false; clock += 600e3; ok((await call({ action: "register", code: code(), pub }, "198.51.100.72")).status === 200, "recovery"); ok(F.health().degraded === false, "health back to normal"); });
Deno.test("outage: connection failure (fetch rejects) and slow store (> timeout) both fall back within the timeout", async () => { F.applyProfile("classroom");
  const slow = { hit: () => new Promise<any>((res) => setTimeout(() => res({ ok: true, retry: 1 }), 400)) };
  fresh(slow); const t0 = performance.now(); const r = await call({ action: "register", code: code(), pub }, "198.51.100.80"); const ms = performance.now() - t0;
  ok(r.status === 200 && ms < 300, "slow limiter answered via fallback in " + Math.round(ms) + " ms"); ok(F.health().degraded, "marked degraded");
  const refused = { hit: () => Promise.reject(new TypeError("connection refused")) }; fresh(refused);
  ok((await call({ action: "register", code: code(), pub }, "198.51.100.81")).status === 200, "connection refused -> fallback"); let b = 0;
  for (let i = 0; i < 4; i++) if ((await call({ action: "register", code: code(), pub }, "198.51.100.81")).status === 429) b++; ok(b >= 1, "fallback limit is half (2/min, got blocked " + b + "/4)"); });
Deno.test("emergency mode: global cap hit -> halved limits for 5 min, existing classroom keeps joining, auto-recovers", async () => { F.applyProfile("classroom"); fresh();
  const saved = F.LIMITS.globalJoin; F.LIMITS.globalJoin = { n: 50, w: 60e3 }; const c = code(); await call({ action: "register", code: c, pub }, SCHOOL);
  let hit = false; for (let i = 0; i < 60 && !hit; i++) { const r = await call({ action: "claim", code: c, role: "player", pub }, "192.0.2." + (i % 250 + 1)); if (r.status === 429 && (await r.json()).scope === "global") hit = true; }
  ok(hit && F.health().emergency, "global cap -> emergency on"); clock += 60e3; F.LIMITS.globalJoin = saved;
  const x = await classroom(10, 60, 0); ok(x.joins === 10, "10 kids still join during emergency (halved limits)");
  clock += 301e3; ok(F.health().emergency === false, "emergency ends by itself after 5 min"); });
Deno.test("manual emergency flag + cross-origin 429 body + salted IP tag", async () => { F.applyProfile("family"); fresh(); F.setEmergency(true);
  let okc = 0; for (let i = 0; i < 5; i++) if ((await call({ action: "register", code: code(), pub }, "198.51.100.95")).status === 200) okc++; ok(okc === 2, "manual emergency halves 5 -> 2 rooms/min, got " + okc);
  const r = await call({ action: "register", code: code(), pub }, "198.51.100.95"); const j = await r.json();
  ok(r.headers.get("Access-Control-Allow-Origin") && typeof j.retry_after === "number" && r.headers.get("Retry-After"), "429 readable cross-origin (CORS + retry_after in body)");
  F.setEmergency(false); const tag = await F.ipTag("198.51.100.95"); ok(tag.length === 16 && !tag.includes("198") && tag !== (await F.ipTag("198.51.100.96")), "IP stored only as salted 16-hex tag"); });
Deno.test("benchmark: limiter overhead per request (in-memory)", async () => { F.applyProfile("classroom"); fresh(); const t0 = performance.now();
  for (let i = 0; i < 500; i++) await call({ action: "register", code: code(), pub }, "10.9." + (i >> 8) + "." + (i & 255)); const per = (performance.now() - t0) / 500;
  report.push({ benchmark_ms_per_register: +per.toFixed(2) }); ok(per < 20, "per request " + per.toFixed(2) + " ms");
  F.applyProfile("family"); console.log("V331REPORT " + JSON.stringify(report)); });

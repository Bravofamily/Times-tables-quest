// NumiRealm v33 nr-gn v4 (host-only rooms, revocation, CR33-3 rate limits). Based on v32 nr-gn (CR-02): server-signed, short-lived Game Night seats.
// Each phone makes its own key pair. This function signs a small claim
// {code, pid, role, pub, exp} with the server key (secret GN_SIGNING_JWK).
// Peers check the server signature and then the per-message signature, so a
// player cannot answer as someone else or send fake game state.
// No names, no child data. The signing key is GN_SIGNING_JWK if set, else made once and kept in gn_keys. The claim lasts 3 hours.
const env = (k: string) => (globalThis as any).Deno?.env.get(k) || "";
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (o: unknown, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
const b64u = (b: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
export const TTL = 3 * 3600e3; // room lifetime (and host seat)
export const SEAT_TTL = 60 * 60e3; // v33: player seats last 60 minutes; the phone re-claims while the room is open
// v33 (directive 8): host-only room registration and room-end revocation.
// Rooms live in gn_rooms (service role only): code, token_hash (sha256 of the host's room token), exp, ended_at.
export type Room = { code: string; token_hash: string; exp: number; ended_at: number | null };
export type Store = { get(code: string): Promise<Room | null>; put(r: Room): Promise<boolean>; end(code: string, at: number): Promise<boolean> };
const sha = async (t: string) => b64u(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t)));
export function memStore(): Store { const m = new Map<string, Room>(); return {
  async get(c) { return m.get(c) || null; }, async put(r) { m.set(r.code, { ...r }); return true; },
  async end(c, at) { const r = m.get(c); if (!r) return false; r.ended_at = at; return true; } }; }
function restStore(): Store | null {
  const u = env("SUPABASE_URL"), k = env("SUPABASE_SERVICE_ROLE_KEY"); if (!u || !k) return null;
  const h = { apikey: k, Authorization: "Bearer " + k, "Content-Type": "application/json" };
  const toRoom = (a: any): Room => ({ code: a.code, token_hash: a.token_hash, exp: Date.parse(a.exp), ended_at: a.ended_at ? Date.parse(a.ended_at) : null });
  return {
    async get(c) { const r = await fetch(u + "/rest/v1/gn_rooms?code=eq." + c + "&select=*", { headers: h }); if (!r.ok) throw new Error("store"); const a = await r.json(); return a[0] ? toRoom(a[0]) : null; },
    async put(x) { const r = await fetch(u + "/rest/v1/gn_rooms?on_conflict=code", { method: "POST", headers: { ...h, Prefer: "resolution=merge-duplicates,return=minimal" }, body: JSON.stringify({ code: x.code, token_hash: x.token_hash, exp: new Date(x.exp).toISOString(), ended_at: null }) }); return r.ok; },
    async end(c, at) { const r = await fetch(u + "/rest/v1/gn_rooms?code=eq." + c, { method: "PATCH", headers: { ...h, Prefer: "return=minimal" }, body: JSON.stringify({ ended_at: new Date(at).toISOString() }) }); return r.ok; },
  };
}
let STORE: Store | null | undefined;
export function setStore(s: Store | null | undefined) { STORE = s; }
const store = () => (STORE === undefined ? (STORE = restStore()) : STORE);
const live = (r: Room | null, t: number) => !!r && !r.ended_at && r.exp > t;
export const CODE = /^[A-Z0-9]{5}$/;
let KEY: { priv: CryptoKey; pub: JsonWebKey } | null = null;
async function serverKey() {
  if (KEY) return KEY;
  let raw = env("GN_SIGNING_JWK");
  if (!raw) raw = await dbKey(); // no secret to paste: the key is made once and kept in a service-role-only table
  if (!raw) return null;
  const jwk = JSON.parse(raw);
  const priv = await crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  const { kty, crv, x, y } = jwk; KEY = { priv, pub: { kty, crv, x, y } }; return KEY;
}
async function dbKey(): Promise<string> {
  const u = env("SUPABASE_URL"), k = env("SUPABASE_SERVICE_ROLE_KEY"); if (!u || !k) return "";
  const h = { apikey: k, Authorization: "Bearer " + k, "Content-Type": "application/json" };
  try {
    const get = async () => { const r = await fetch(u + "/rest/v1/gn_keys?id=eq.1&select=jwk", { headers: h }); if (!r.ok) return ""; const a = await r.json(); return a[0] ? JSON.stringify(a[0].jwk) : ""; };
    let j = await get(); if (j) return j;
    const kp = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
    await fetch(u + "/rest/v1/gn_keys?on_conflict=id", { method: "POST", headers: { ...h, Prefer: "resolution=ignore-duplicates,return=minimal" }, body: JSON.stringify({ id: 1, jwk: await crypto.subtle.exportKey("jwk", kp.privateKey) }) });
    j = await get(); return j; // re-read so two cold starts agree on one key
  } catch { return ""; }
}
export function _reset() { KEY = null; }
// v32.1: x and y must be 32-byte base64url values forming a real point on P-256
const P256P = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffffn;
const P256B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604bn;
const b64uBig = (s: string): bigint | null => {
  if (!/^[A-Za-z0-9_-]{43}$/.test(s)) return null;
  try { const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "="); if (bin.length !== 32) return null;
    let n = 0n; for (const c of bin) n = (n << 8n) | BigInt(c.charCodeAt(0)); return n; } catch { return null; }
};
export const onCurve = (x: bigint, y: bigint) => {
  if (x >= P256P || y >= P256P) return false;
  const m = (a: bigint) => ((a % P256P) + P256P) % P256P;
  return m(y * y) === m(x * x * x - 3n * x + P256B);
};
export const okPub = (p: any) => { if (!(p && p.kty === "EC" && p.crv === "P-256" && typeof p.x === "string" && typeof p.y === "string" && !p.d)) return false;
  const x = b64uBig(p.x), y = b64uBig(p.y); return x !== null && y !== null && onCurve(x, y); };

// ---- v33 CR33-3: server-side rate limits (HTTP 429 + Retry-After). No bans: every bucket is a fixed time window that simply expires.
// IPs are never stored: only a salted SHA-256 (first 16 chars) inside short-lived bucket keys, purged after the window ends.
export const LIMITS = {
  regMin: { n: 5, w: 60e3 }, regHour: { n: 20, w: 3600e3 },   // room creation per IP
  joinMin: { n: 10, w: 60e3 },                                 // join (claim) attempts per IP
  badMin: { n: 10, w: 60e3 },                                  // invalid seat/token attempts per IP
  roomJoin: { n: 40, w: 600e3 },                               // room-level: joins per room per 10 min (a family needs < 10)
  roomBad: { n: 20, w: 600e3 },                                // room-level: bad end/claim attempts per room per 10 min
  globalReg: { n: 300, w: 60e3 }, globalJoin: { n: 1500, w: 60e3 }, // global abuse caps per function instance / project
};
export type Limiter = { hit(key: string, n: number, w: number, peek?: boolean): Promise<{ ok: boolean; retry: number }> };
export function memLimiter(now = () => Date.now()): Limiter { const m = new Map<string, { c: number; end: number }>(); return {
  async hit(key, n, w, peek) { const t = now(); const start = Math.floor(t / w) * w; const k = key + "@" + start;
    for (const [kk, v] of m) if (v.end <= t) m.delete(kk); // purge expired buckets
    const b = m.get(k) || { c: 0, end: start + w }; const retry = Math.max(1, Math.ceil((b.end - t) / 1000));
    if (peek) return { ok: b.c < n, retry };
    if (b.c >= n) return { ok: false, retry }; b.c++; m.set(k, b); return { ok: true, retry }; },
  _size() { return m.size; }, _keys() { return [...m.keys()]; } } as Limiter & { _size(): number; _keys(): string[] }; }
function restLimiter(): Limiter | null {
  const u = env("SUPABASE_URL"), k = env("SUPABASE_SERVICE_ROLE_KEY"); if (!u || !k) return null;
  const h = { apikey: k, Authorization: "Bearer " + k, "Content-Type": "application/json" };
  return { async hit(key, n, w, peek) {
    const r = await fetch(u + "/rest/v1/rpc/gn_rate_hit", { method: "POST", headers: h, body: JSON.stringify({ p_key: key, p_limit: n, p_window_sec: Math.round(w / 1000), p_peek: !!peek }) });
    if (!r.ok) throw new Error("limiter"); const j = await r.json(); return { ok: !!j.ok, retry: Math.max(1, j.retry | 0) }; } };
}
let NOW = () => Date.now(); export function setNow(f: () => number) { NOW = f; }
// ---- v33.1 hybrid limiter (all behind env flags; defaults keep v33 behaviour except: no more fail-open) ----
// GN_LIMIT_PROFILE=family (default, v33 values) | classroom (joins/IP 30/min, joins/room 120/10 min)
export const PROFILES: Record<string, Partial<typeof LIMITS>> = {
  family: {},
  classroom: { joinMin: { n: 30, w: 60e3 }, roomJoin: { n: 120, w: 600e3 } }, // v33.1 benchmark: 60 kids + 1 reconnect each = 0 x 429 (60/10 min gave 90 x 429)
};
const BASE = JSON.parse(JSON.stringify(LIMITS));
export function applyProfile(name: string) { const p = PROFILES[name] || {}; Object.assign(LIMITS, JSON.parse(JSON.stringify(BASE)), JSON.parse(JSON.stringify(p))); return PROFILES[name] ? name : "family"; }
export let PROFILE = applyProfile(env("GN_LIMIT_PROFILE") || "family");
export const COOLDOWN = { w: 300e3 };              // repeated bad codes -> 5 min cooldown for that IP tag (never permanent)
export const FALLBACK_FACTOR = 0.5;                // limiter store down -> per-isolate memory limits at half the normal values
export const EMERGENCY_MS = 300e3;                 // automatic protective mode lasts 5 min, then recovers on its own
const TIMEOUT_MS = () => Number(env("GN_LIMITER_TIMEOUT_MS")) || 800;
let LIM: Limiter | null | undefined; let FALLBACK: Limiter = memLimiter();
export const STATE = { degraded: false, degradedSince: 0, fallbackHits: 0, emergencyUntil: 0, manualEmergency: env("GN_EMERGENCY") === "1" };
export function setLimiter(l: Limiter | null | undefined, fb?: Limiter) { LIM = l; FALLBACK = fb || memLimiter(); STATE.degraded = false; STATE.fallbackHits = 0; STATE.emergencyUntil = 0; }
export function setEmergency(on: boolean) { STATE.manualEmergency = on; if (!on) STATE.emergencyUntil = 0; }
const emergency = (t: number) => STATE.manualEmergency || STATE.emergencyUntil > t;
const limiter = () => (LIM === undefined ? (LIM = restLimiter() || memLimiter()) : LIM);
let SALT = "";
const salt = () => SALT || (SALT = env("GN_RATE_SALT") || b64u(crypto.getRandomValues(new Uint8Array(16)).buffer));
export const clientIp = (req: Request) => (req.headers.get("cf-connecting-ip") || (req.headers.get("x-forwarded-for") || "").split(",")[0] || req.headers.get("x-real-ip") || "unknown").trim().slice(0, 64);
export const ipTag = async (ip: string) => (await sha(salt() + "|" + ip)).slice(0, 16);
const tooMany = (retry: number, scope: string) => new Response(JSON.stringify({ ok: false, error: "rate_limited", scope, retry_after: retry }), { status: 429, headers: { ...CORS, "Content-Type": "application/json", "Retry-After": String(retry) } });
const withTimeout = <T>(p: Promise<T>, ms: number) => new Promise<T>((res, rej) => { const id = setTimeout(() => rej(new Error("limiter_timeout")), ms); p.then((v) => { clearTimeout(id); res(v); }, (e) => { clearTimeout(id); rej(e); }); });
// one hit: shared store first; on error/timeout -> stricter per-isolate memory limiter (fail-restricted, not fail-open)
async function hit1(key: string, lim: { n: number; w: number }, peek?: boolean) {
  const L = limiter(); const t = NOW(); if (L === null) return { ok: true, retry: 1 }; // explicit test-only 'no limiter'
  let n = lim.n; if (emergency(t) && !key.startsWith("cool:")) n = Math.max(1, Math.floor(n * FALLBACK_FACTOR));
  if (L && L !== FALLBACK) {
    try { const r = await withTimeout(L.hit(key, n, lim.w, peek), TIMEOUT_MS()); if (STATE.degraded) { STATE.degraded = false; } return r; }
    catch { if (!STATE.degraded) { STATE.degraded = true; STATE.degradedSince = t; } STATE.fallbackHits++; }
    n = key.startsWith("cool:") ? n : Math.max(1, Math.floor(n * FALLBACK_FACTOR));
  }
  return await FALLBACK.hit(key, n, lim.w, peek);
}
async function gate(checks: [string, { n: number; w: number }, boolean?][]): Promise<Response | null> {
  for (const [key, lim, peek] of checks) {
    const r = await hit1(key, lim, peek);
    if (!r.ok) { if (key.startsWith("global:")) STATE.emergencyUntil = NOW() + EMERGENCY_MS; return tooMany(r.retry, key.split(":")[0]); }
  }
  return null;
}
async function bad(ipk: string, code: string) {
  await hit1("bad:" + ipk, { n: LIMITS.badMin.n * 100, w: LIMITS.badMin.w }); await hit1("roombad:" + code, { n: LIMITS.roomBad.n * 100, w: LIMITS.roomBad.w });
  const still = await hit1("bad:" + ipk, LIMITS.badMin, true); if (!still.ok) await hit1("cool:" + ipk, { n: 1, w: COOLDOWN.w });
}
export const health = () => ({ profile: PROFILE, degraded: STATE.degraded, fallback_hits: STATE.fallbackHits, emergency: emergency(NOW()) });
export async function handle(req: Request): Promise<Response> {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
  const k = await serverKey(); if (!k) return json({ ok: false, error: "not_configured" }, 503);
  let b: any; try { b = await req.json(); } catch { return json({ ok: false, error: "bad_json" }, 400); }
  const act = b && b.action;
  if (act !== "claim" && act !== "register" && act !== "end") return json({ ok: false, error: "bad_action" }, 400);
  const code = String(b.code || "");
  if (!CODE.test(code)) return json({ ok: false, error: "bad_code" }, 400);
  const st = store(); if (!st) return json({ ok: false, error: "not_configured" }, 503);
  const ipk = await ipTag(clientIp(req));
  // invalid-attempt buckets are checked (peek) before any claim/end work; they fill up in bad() below
  // v33.1 v32-compat: a live v32 client asks for its host seat with {action:"claim", role:"host"} (v3 protocol).
  // It is treated as an implicit register (normal create limits, never the bad-code buckets).
  const legacyHost = act === "claim" && b.role === "host";
  const g = (act === "register" || legacyHost)
    ? await gate([["cool:" + ipk, { n: 1, w: COOLDOWN.w }, true], ["bad:" + ipk, LIMITS.badMin, true], ["global:reg", LIMITS.globalReg], ["ip:" + ipk + ":regm", LIMITS.regMin], ["ip:" + ipk + ":regh", LIMITS.regHour]])
    : act === "claim"
    ? await gate([["cool:" + ipk, { n: 1, w: COOLDOWN.w }, true], ["bad:" + ipk, LIMITS.badMin, true], ["roombad:" + code, LIMITS.roomBad, true], ["global:join", LIMITS.globalJoin], ["ip:" + ipk + ":join", LIMITS.joinMin], ["room:" + code + ":join", LIMITS.roomJoin]])
    : await gate([["cool:" + ipk, { n: 1, w: COOLDOWN.w }, true], ["bad:" + ipk, LIMITS.badMin, true], ["roombad:" + code, LIMITS.roomBad, true]]);
  if (g) return g;
  const t = Date.now();
  let room: Room | null; try { room = await st.get(code); } catch { return json({ ok: false, error: "store" }, 503); }
  if (act === "end") {
    if (!room) { await bad(ipk, code); return json({ ok: false, error: "no_room" }, 404); }
    if (typeof b.rt !== "string" || (await sha(b.rt)) !== room.token_hash) { await bad(ipk, code); return json({ ok: false, error: "not_host" }, 403); }
    await st.end(code, t); return json({ ok: true, ended: true });
  }
  const role = act === "register" ? "host" : b.role;
  const role2 = legacyHost ? "host" : role;
  if (role2 !== "host" && role2 !== "player") return json({ ok: false, error: "bad_role" }, 400);
  if (!okPub(b.pub)) { await bad(ipk, code); return json({ ok: false, error: "bad_key" }, 400); }
  try { await crypto.subtle.importKey("jwk", { kty: "EC", crv: "P-256", x: b.pub.x, y: b.pub.y }, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]); } catch { return json({ ok: false, error: "bad_key" }, 400); }
  let rt = "", exp: number;
  if (legacyHost) {
    // v32 host: v3-equivalent signed host seat. Its room is marked "legacy:" so no room token exists
    // (sha(rt) can never equal it -> nobody can 'end' it; it simply expires after TTL, as in v3).
    // A legacy host may re-claim only a LIVE LEGACY room (v3 behaviour on reload); a v33 room is never touchable.
    if (live(room, t)) { if (!room!.token_hash.startsWith("legacy:")) return json({ ok: false, error: "code_taken" }, 409); exp = room!.exp; }
    else { const r = new Uint8Array(24); crypto.getRandomValues(r); exp = t + TTL;
      if (!(await st.put({ code, token_hash: "legacy:" + (await sha(b64u(r.buffer))), exp, ended_at: null }))) return json({ ok: false, error: "store" }, 503); }
  } else if (act === "register") {
    if (live(room, t)) return json({ ok: false, error: "code_taken" }, 409);
    const r = new Uint8Array(24); crypto.getRandomValues(r); rt = b64u(r.buffer);
    exp = t + TTL; if (!(await st.put({ code, token_hash: await sha(rt), exp, ended_at: null }))) return json({ ok: false, error: "store" }, 503);
  } else {
    if (!room) { await bad(ipk, code); return json({ ok: false, error: "no_room" }, 404); }
    if (!live(room, t)) { await bad(ipk, code); return json({ ok: false, error: "room_ended" }, 410); }
    exp = Math.min(t + SEAT_TTL, room.exp);
  }
  const rnd = new Uint8Array(12); crypto.getRandomValues(rnd);
  const claim = { v: 1, code, role: role2, pid: (role2 === "host" ? "host-" : "p-") + b64u(rnd.buffer), pub: { kty: "EC", crv: "P-256", x: b.pub.x, y: b.pub.y }, exp };
  const text = JSON.stringify(claim);
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, k.priv, new TextEncoder().encode(text));
  return json(rt ? { ok: true, claim: text, sig: b64u(sig), srv: k.pub, rt } : { ok: true, claim: text, sig: b64u(sig), srv: k.pub });
}
if ((globalThis as any).Deno?.serve && !env("NR_NO_SERVE")) (globalThis as any).Deno.serve(handle);

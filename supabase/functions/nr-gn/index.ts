// NumiRealm v32 nr-gn (CR-02): server-signed, short-lived Game Night seats.
// Each phone makes its own key pair. This function signs a small claim
// {code, pid, role, pub, exp} with the server key (secret GN_SIGNING_JWK).
// Peers check the server signature and then the per-message signature, so a
// player cannot answer as someone else or send fake game state.
// No names, no child data. The signing key is GN_SIGNING_JWK if set, else made once and kept in gn_keys. The claim lasts 3 hours.
const env = (k: string) => (globalThis as any).Deno?.env.get(k) || "";
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (o: unknown, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
const b64u = (b: ArrayBuffer) => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
export const TTL = 3 * 3600e3;
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
const okPub = (p: any) => p && p.kty === "EC" && p.crv === "P-256" && typeof p.x === "string" && typeof p.y === "string" && p.x.length < 60 && p.y.length < 60 && !p.d;
export async function handle(req: Request): Promise<Response> {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
  const k = await serverKey(); if (!k) return json({ ok: false, error: "not_configured" }, 503);
  let b: any; try { b = await req.json(); } catch { return json({ ok: false, error: "bad_json" }, 400); }
  if (!b || b.action !== "claim") return json({ ok: false, error: "bad_action" }, 400);
  const code = String(b.code || "");
  if (!CODE.test(code)) return json({ ok: false, error: "bad_code" }, 400);
  if (b.role !== "host" && b.role !== "player") return json({ ok: false, error: "bad_role" }, 400);
  if (!okPub(b.pub)) return json({ ok: false, error: "bad_key" }, 400);
  try { await crypto.subtle.importKey("jwk", { kty: "EC", crv: "P-256", x: b.pub.x, y: b.pub.y }, { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]); } catch { return json({ ok: false, error: "bad_key" }, 400); }
  const rnd = new Uint8Array(12); crypto.getRandomValues(rnd);
  const claim = { v: 1, code, role: b.role, pid: (b.role === "host" ? "host-" : "p-") + b64u(rnd.buffer), pub: { kty: "EC", crv: "P-256", x: b.pub.x, y: b.pub.y }, exp: Date.now() + TTL };
  const text = JSON.stringify(claim);
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, k.priv, new TextEncoder().encode(text));
  return json({ ok: true, claim: text, sig: b64u(sig), srv: k.pub });
}
if ((globalThis as any).Deno?.serve && !env("NR_NO_SERVE")) (globalThis as any).Deno.serve(handle);

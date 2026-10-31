// v32 CR-02: nr-gn unit tests (throwaway key)
Deno.env.set("NR_NO_SERVE", "1");
const F = await import("../supabase/functions/nr-gn/index.ts");
F.setStore(F.memStore()); F.setLimiter(null); // limits are tested in test_gn_rate.ts
const EC = { name: "ECDSA", namedCurve: "P-256" };
const kp = await crypto.subtle.generateKey(EC, true, ["sign", "verify"]);
const pj = await crypto.subtle.exportKey("jwk", kp.publicKey);
const call = (b: unknown) => F.handle(new Request("http://x/", { method: "POST", body: JSON.stringify(b) }));
const ok = (c: unknown, m: string) => { if (!c) throw new Error(m); };
Deno.test("nr-gn: 503 when no signing key is set", async () => {
  Deno.env.delete("GN_SIGNING_JWK"); F._reset(); ok((await call({ action: "claim", code: "ABCDE", role: "player", pub: pj })).status === 503, "503");
});
Deno.test("nr-gn: input checks and a valid signed claim", async () => {
  const sk = await crypto.subtle.generateKey(EC, true, ["sign", "verify"]);
  Deno.env.set("GN_SIGNING_JWK", JSON.stringify(await crypto.subtle.exportKey("jwk", sk.privateKey))); F._reset();
  ok((await call({ action: "claim", code: "abc", role: "player", pub: pj })).status === 400, "bad code");
  ok((await call({ action: "register", code: "ABCDE", pub: pj })).status === 200, "host registers room");
  ok((await call({ action: "claim", code: "ABCDE", role: "admin", pub: pj })).status === 400, "bad role");
  const priv = await crypto.subtle.exportKey("jwk", kp.privateKey);
  ok((await call({ action: "claim", code: "ABCDE", role: "player", pub: priv })).status === 400, "private key refused");
  ok((await F.handle(new Request("http://x/", { method: "GET" }))).status === 405, "GET refused");
  ok((await call({ action: "claim", code: "ABCDE", role: "player", pub: { kty: "EC", crv: "P-256", x: "a", y: "b" } })).status === 400, "not a real key point");
  const r = await (await call({ action: "claim", code: "ABCDE", role: "player", pub: pj })).json();
  const c = JSON.parse(r.claim); ok(r.ok && c.code === "ABCDE" && c.role === "player" && /^p-/.test(c.pid), "claim fields");
  ok(c.exp > Date.now() && c.exp <= Date.now() + F.SEAT_TTL, "player seat expiry <= 60 min");
  ok(!("d" in r.srv), "server private key never returned");
  const srv = await crypto.subtle.importKey("jwk", r.srv, EC, false, ["verify"]);
  const s = r.sig.replace(/-/g, "+").replace(/_/g, "/"); const sig = Uint8Array.from(atob(s + "=".repeat((4 - s.length % 4) % 4)), (x) => x.charCodeAt(0));
  ok(await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, srv, sig, new TextEncoder().encode(r.claim)), "server signature valid");
  const r2 = await (await call({ action: "claim", code: "ABCDE", role: "player", pub: pj })).json();
  ok(JSON.parse(r2.claim).pid !== c.pid, "server picks a fresh id each time (client cannot choose)");
});
Deno.test("nr-gn: without a secret, makes one key, stores it once, and reuses it", async () => {
  Deno.env.delete("GN_SIGNING_JWK"); Deno.env.set("SUPABASE_URL", "https://db.test"); Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "test-only"); F._reset();
  let row: unknown = null; let posts = 0; const real = globalThis.fetch;
  globalThis.fetch = (async (u: string, init?: RequestInit) => {
    if (String(u).includes("/rest/v1/gn_keys")) {
      if (init?.method === "POST") { posts++; if (!row) row = JSON.parse(String(init.body)).jwk; return new Response("", { status: 201 }); }
      return new Response(JSON.stringify(row ? [{ jwk: row }] : []), { status: 200 });
    }
    return real(u, init);
  }) as typeof fetch;
  try {
    const a = await (await call({ action: "register", code: "KEYAA", pub: pj })).json();
    F._reset(); // a cold start
    const b = await (await call({ action: "register", code: "KEYBB", pub: pj })).json();
    ok(a.ok && b.ok && posts === 1 && a.srv.x === b.srv.x, "one stored key reused after a cold start");
  } finally { globalThis.fetch = real; Deno.env.delete("SUPABASE_URL"); Deno.env.delete("SUPABASE_SERVICE_ROLE_KEY"); }
});

// v32.1: public key must be a real P-256 point
Deno.test("v32.1 okPub rejects junk and off-curve keys", async () => {
  const k = await crypto.subtle.generateKey(EC, true, ["sign"]);
  const j: any = await crypto.subtle.exportKey("jwk", k.publicKey);
  if (!F.okPub({ kty: "EC", crv: "P-256", x: j.x, y: j.y })) throw new Error("valid rejected");
  if (F.okPub({ kty: "EC", crv: "P-256", x: "bad", y: "bad" })) throw new Error("junk accepted");
  if (F.okPub({ kty: "EC", crv: "P-256", x: j.x, y: j.x })) throw new Error("off-curve accepted");
  const r = await F.handle(new Request("http://x", { method: "POST", body: JSON.stringify({ action: "claim", code: "ABC12", role: "host", pub: { kty: "EC", crv: "P-256", x: "bad", y: "bad" } }) }));
  if (r.status !== 400) throw new Error("handler accepted junk " + r.status);
});

// v33 directive 8: host-only registration and room-end revocation
Deno.test("v33 rooms: register, code_taken, player needs a live room, host-only end, revocation", async () => {
  const sk = await crypto.subtle.generateKey(EC, true, ["sign", "verify"]);
  Deno.env.set("GN_SIGNING_JWK", JSON.stringify(await crypto.subtle.exportKey("jwk", sk.privateKey))); F._reset(); F.setStore(F.memStore());
  ok((await call({ action: "claim", code: "ROOM1", role: "player", pub: pj })).status === 404, "no room -> 404");
  { const lg = await call({ action: "claim", code: "LEG01", role: "host", pub: pj }); const lj = await lg.json(); ok(lg.status === 200 && lj.ok && !lj.rt, "v33.1 compat: v32 host claim = implicit legacy register, no room token"); }
  const h = await (await call({ action: "register", code: "ROOM1", pub: pj })).json();
  ok(h.ok && typeof h.rt === "string" && h.rt.length >= 30 && JSON.parse(h.claim).role === "host", "host claim + room token");
  ok((await call({ action: "register", code: "ROOM1", pub: pj })).status === 409, "second host cannot take a live code");
  ok((await call({ action: "claim", code: "ROOM1", role: "host", pub: pj })).status === 409, "v32-style host claim cannot take a live v33 room");
  const p = await (await call({ action: "claim", code: "ROOM1", role: "player", pub: pj })).json();
  ok(p.ok && !p.rt && JSON.parse(p.claim).exp <= Date.now() + F.SEAT_TTL, "player seat, 60 min, no room token");
  ok((await call({ action: "end", code: "ROOM1", rt: "wrong" })).status === 403, "non-host cannot end");
  ok((await call({ action: "end", code: "ROOM1" })).status === 403, "missing token cannot end");
  ok((await call({ action: "end", code: "ROOM1", rt: h.rt })).status === 200, "host ends");
  ok((await call({ action: "claim", code: "ROOM1", role: "player", pub: pj })).status === 410, "ended room -> 410, no new seats");
  ok((await call({ action: "register", code: "ROOM1", pub: pj })).status === 200, "ended code can be reused by a new host");
  ok((await call({ action: "end", code: "ZZZZZ", rt: h.rt })).status === 404, "unknown room");
  ok((await call({ action: "bogus", code: "ROOM1" })).status === 400, "bad action");
});
Deno.test("v33 rooms: expired room refuses seats; store outage -> 503", async () => {
  const m = F.memStore(); F.setStore(m);
  await m.put({ code: "OLD11", token_hash: "x", exp: Date.now() - 1, ended_at: null });
  ok((await call({ action: "claim", code: "OLD11", role: "player", pub: pj })).status === 410, "expired -> 410");
  ok((await call({ action: "register", code: "OLD11", pub: pj })).status === 200, "expired code reusable");
  F.setStore({ get: () => Promise.reject(new Error("down")), put: async () => false, end: async () => false });
  ok((await call({ action: "claim", code: "OLD11", role: "player", pub: pj })).status === 503, "store down -> 503");
  F.setStore(null);
  ok((await call({ action: "claim", code: "OLD11", role: "player", pub: pj })).status === 503, "no store -> 503");
  F.setStore(F.memStore());
});

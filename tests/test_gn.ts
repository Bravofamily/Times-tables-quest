// v32 CR-02: nr-gn unit tests (throwaway key)
Deno.env.set("NR_NO_SERVE", "1");
const F = await import("../supabase/functions/nr-gn/index.ts");
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
  ok((await call({ action: "claim", code: "ABCDE", role: "admin", pub: pj })).status === 400, "bad role");
  const priv = await crypto.subtle.exportKey("jwk", kp.privateKey);
  ok((await call({ action: "claim", code: "ABCDE", role: "player", pub: priv })).status === 400, "private key refused");
  ok((await F.handle(new Request("http://x/", { method: "GET" }))).status === 405, "GET refused");
  ok((await call({ action: "claim", code: "ABCDE", role: "player", pub: { kty: "EC", crv: "P-256", x: "a", y: "b" } })).status === 400, "not a real key point");
  const r = await (await call({ action: "claim", code: "ABCDE", role: "player", pub: pj })).json();
  const c = JSON.parse(r.claim); ok(r.ok && c.code === "ABCDE" && c.role === "player" && /^p-/.test(c.pid), "claim fields");
  ok(c.exp > Date.now() && c.exp <= Date.now() + F.TTL, "short expiry (3h)");
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
    const a = await (await call({ action: "claim", code: "ABCDE", role: "host", pub: pj })).json();
    F._reset(); // a cold start
    const b = await (await call({ action: "claim", code: "ABCDE", role: "host", pub: pj })).json();
    ok(a.ok && b.ok && posts === 1 && a.srv.x === b.srv.x, "one stored key reused after a cold start");
  } finally { globalThis.fetch = real; Deno.env.delete("SUPABASE_URL"); Deno.env.delete("SUPABASE_SERVICE_ROLE_KEY"); }
});

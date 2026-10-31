// v33.1 benchmark only (not a regression test): classroom outcomes for candidate room caps. Prints a JSON table.
Deno.env.set("NR_NO_SERVE", "1");
const F = await import("../supabase/functions/nr-gn/index.ts");
const EC = { name: "ECDSA", namedCurve: "P-256" };
const sk = await crypto.subtle.generateKey(EC, true, ["sign", "verify"]);
Deno.env.set("GN_SIGNING_JWK", JSON.stringify(await crypto.subtle.exportKey("jwk", sk.privateKey))); F._reset();
const kp = await crypto.subtle.generateKey(EC, true, ["sign", "verify"]); const pj = await crypto.subtle.exportKey("jwk", kp.publicKey);
const pub = { kty: "EC", crv: "P-256", x: pj.x, y: pj.y }; let clock = 2e12; F.setNow(() => clock); let n = 0;
const call = (b: unknown, ip: string) => F.handle(new Request("http://x/", { method: "POST", headers: { "x-forwarded-for": ip }, body: JSON.stringify(b) }));
const out: any[] = [];
for (const [ipMin, room] of [[10, 40], [30, 60], [30, 90], [30, 120], [60, 120]]) for (const N of [30, 45, 60]) {
  F.applyProfile("family"); F.LIMITS.joinMin = { n: ipMin, w: 60e3 }; F.LIMITS.roomJoin = { n: room, w: 600e3 };
  F.setStore(F.memStore()); F.setLimiter(F.memLimiter(() => clock)); clock += 7200e3; const c = "B" + String(++n).padStart(4, "0");
  await call({ action: "register", code: c, pub }, "203.0.113.50"); const q: any[] = [];
  for (let k = 0; k < N; k++) for (let r = 0; r <= 1; r++) { const at = clock + Math.floor(k * 120e3 / N) + r * 240e3; q.push({ at, first: at }); }
  let r429 = 0, mw = 0; const st = clock;
  while (q.length) { q.sort((a, b) => a.at - b.at); const e = q.shift(); if (e.at > clock) clock = e.at; const r = await call({ action: "claim", code: c, role: "player", pub }, "203.0.113.50");
    if (r.status === 200) { mw = Math.max(mw, clock - e.first); continue; } const j = await r.json(); r429++; e.at = clock + j.retry_after * 1000; q.push(e); }
  out.push({ joinsPerIpMin: ipMin, joinsPerRoom10m: room, kids: N, claims: N * 2, r429, maxWaitSec: Math.round(mw / 1000), minutes: Math.round((clock - st) / 6e4) });
}
console.log(JSON.stringify(out));

// Local test server for nr-gn with a throwaway key (never a real secret). Usage: deno run --allow-net --allow-env gn_server.ts 8899
const kp = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
Deno.env.set("GN_SIGNING_JWK", JSON.stringify(await crypto.subtle.exportKey("jwk", kp.privateKey)));
Deno.env.set("NR_NO_SERVE", "1");
const { handle, setStore, memStore, setLimiter, memLimiter } = await import("../supabase/functions/nr-gn/index.ts");
setLimiter(Deno.env.get("GN_RL") === "1" ? memLimiter() : null); // GN_RL=1 turns on the real limits (in-memory)
setStore(memStore());
Deno.serve({ port: +(Deno.args[0] || 8899), hostname: "127.0.0.1" }, handle);

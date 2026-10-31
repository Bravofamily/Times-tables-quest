// v33.1: two nr-gn instances (= two edge isolates) must give the SAME ip tag, or per-IP limits leak across isolates.
// Catches the missing GN_RATE_SALT bug found in production (stage 2, 2026-10-30).
Deno.env.set("NR_NO_SERVE", "1");
const ok = (c: unknown, m: string) => { if (!c) throw new Error(m); };
const two = async (tag: string) => [await import("../supabase/functions/nr-gn/index.ts?" + tag + "a"), await import("../supabase/functions/nr-gn/index.ts?" + tag + "b")];
Deno.test("with GN_RATE_SALT set: two isolates agree on the ip tag", async () => { Deno.env.set("GN_RATE_SALT", "test-only-salt-not-a-secret");
  const [A, B] = await two("s"); ok(await A.ipTag("198.51.100.9") === await B.ipTag("198.51.100.9"), "tags differ across isolates"); });
Deno.test("negative control: without GN_RATE_SALT the isolates disagree (the production bug)", async () => { Deno.env.delete("GN_RATE_SALT");
  const [A, B] = await two("n"); ok(await A.ipTag("198.51.100.9") !== await B.ipTag("198.51.100.9"), "expected different tags without a salt"); });

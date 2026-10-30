# NumiRealm v32: Supabase steps (iPhone friendly)

Do one part at a time. After each part, stop and check it worked.
Use Safari: supabase.com/dashboard → your project (uuigasrelqbwxopvqoib).
No secret needs to be copied from anywhere for these steps.

## Part 1. SQL (delete cascades + AI switch)
1. Left menu → **SQL Editor** → **New query**.
2. Paste all of `supabase/setup-part5-v32-run.sql` (this version already leaves out the consent draft, which waits for the lawyer).
3. Tap **Run**. Expect a short table, every row CASCADE (link_codes.device_id says SET NULL; that's on purpose).

## Part 2. SQL Part E + F (multi-device merge, Game Night key store)
1. **SQL Editor** → **New query**.
2. Paste all of `supabase/setup-part6-v32-merge.sql`.
3. Tap **Run**. Expect "Success". It is safe to run again.
4. Check: **Table Editor** shows `progress_by_device` and `gn_keys`.

## Part 3. Update the nr-weekly function
1. Left menu → **Edge Functions** → **nr-weekly** → **Code**.
2. Replace everything with `supabase/functions/nr-weekly/index.ts`.
3. Tap **Deploy**. Keep "Verify JWT" as it is now.

## Part 4. Deploy nr-delete-account (if not done yet)
1. **Edge Functions** → **Deploy a new function** → **Via editor**.
2. Name: `nr-delete-account`. Paste `supabase/functions/nr-delete-account/index.ts`.
3. **Deploy**.

## Part 5. Deploy nr-gn (Game Night signed seats)
1. **Edge Functions** → **Deploy a new function** → **Via editor**.
2. Name: `nr-gn`. Paste `supabase/functions/nr-gn/index.ts`.
3. **Deploy**.
4. Open nr-gn → **Details** → turn **Verify JWT** OFF (phones call it without a sign-in), then **Save**.
   No secret needed: it makes its key once and keeps it in `gn_keys`.

## Part 6. Check (2 minutes)
- Parent Area (test link) → a kid → Summary → **Refresh**: the text updates.
- Edge Functions → nr-weekly → **Logs**: a line `nr-weekly ai_fallback <reason>` explains any template fallback (no child data).
- Game Night: host on one phone, join on another; play one round.

## Settings to look at (Auth, no code)
- Authentication → Sessions/Settings: turn ON **Detect and revoke compromised refresh tokens**, set reuse interval to 10 s or less (test showed an old refresh token still worked after 12 s).
- Consider a shorter JWT expiry (now 3600 s): a signed-out access token keeps working for the database until it expires.

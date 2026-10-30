# Delete my account: setup (from an iPhone, about 10 minutes)
Nothing here needs a secret from you. The function reads the service role key that Supabase gives every function automatically.

## Part 1: Check the database (2 min)
1. Open supabase.com in Safari, sign in, open the NumiRealm project.
2. Left menu (≡) > SQL Editor > New query.
3. Open `supabase/setup-part5-v32.sql` on GitHub, copy only PART A (the `select ...` down to `order by 1, 2;`), paste, tap Run.
4. Every row should say CASCADE (link_codes / device_id says SET NULL, that's fine). If so, skip to Part 2.
5. If any row says NO ACTION or RESTRICT: new query, paste PART B (the `do $$ ... end $$;` block), Run, then run PART A again.

## Part 2: Create the function (3 min)
1. Left menu > Edge Functions > Deploy a new function > Via Editor.
2. Name it exactly `nr-delete-account`.
3. Delete the sample code. Paste all of `supabase/functions/nr-delete-account/index.ts`.
4. Tap Deploy.

## Part 3: Settings (1 min)
1. Open the function > Details (or Settings).
2. Leave "Verify JWT" ON (only signed-in parents can call it). Save.
3. No secrets to add: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are already there.

## Part 4: Publish the page (only when you decide to publish v32)
Upload the v32 files from `/workspace/v32-files` to GitHub as usual.

## Part 5: Try it with a TEST account only (3 min)
1. Sign in to the Parent Area with a test account (never your real one).
2. Bell (🔔) > scroll to "🗑️ Delete my account". Type DELETE, tap the red button.
3. You should land on the sign-in screen with "Your account and all its data were deleted."
4. Check: Authentication > Users: the test email is gone. Table Editor > kids: no rows for it.
5. If you see "Some of your data was deleted but not all of it", tap Delete again (it's safe to repeat). Edge Functions > nr-delete-account > Logs shows which step failed.

## v32 additions (after ChatGPT review)
- Part 6: in SQL Editor, run PART C (adds `notify_prefs.ai_summaries`, default false) from setup-part5-v32.sql. Run PART D (consent tables) ONLY after counsel approves; it is safe but not yet needed.
- Part 7: redeploy **nr-weekly** too (allowlist + AI opt-in). Without PART C it treats every parent as AI OFF.
- Note: deleting now needs a sign-in from the last 10 minutes; otherwise the app emails a 6-digit code first.

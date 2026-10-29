# Weekly summary + weekly email: setup (works from an iPhone)

Everything here is done in the Supabase dashboard in Safari. No computer, no command line.
Until you do these steps, the parent page still works: the summary card shows a
"Smart summary (made on this device)" and the email preview button says email is not set up yet.

You will need:
- **Resend** account (free tier: 3,000 emails/month, 100/day) and, to email anyone other
  than yourself, a domain you own verified in Resend (adds 3 DNS records).
- **Optional AI key**: an OpenAI API key (or any OpenAI-compatible provider).
  With gpt-4o-mini one summary costs about $0.0002 (about 2 cents per 100 summaries).
  Without a key, summaries use the plain template and are labeled "Written from your kid's numbers".

## 1. Run the SQL (once, safe to repeat)
1. Dashboard > **SQL Editor** > New query.
2. Paste all of `supabase/setup.sql` (or only `setup-part4.sql` if parts 1-3 are already in) > **Run**.
3. You should see "Success. No rows returned".

## 2. Create the function
1. Dashboard > **Edge Functions** > **Deploy a new function** > **Via Editor**.
2. Name it exactly: `nr-weekly`
3. Delete the sample code, paste all of `supabase/functions/nr-weekly/index.ts`, tap **Deploy**.
4. Open the function > **Details** (or Settings) > turn **Verify JWT** OFF and save.
   (The function checks the parent's login itself. It must be off so the unsubscribe link
   in emails and the weekly schedule can reach it.)

## 3. Add the secrets
Dashboard > **Edge Functions** > **Secrets** (Manage secrets) > add:

| Name | Value | Needed? |
|---|---|---|
| `RESEND_API_KEY` | from resend.com > API Keys | for email |
| `EMAIL_FROM` | e.g. `NumiRealm <hello@yourdomain.com>` (domain verified in Resend) | for email (default `onboarding@resend.dev` only reaches your own Resend address) |
| `PORTAL_URL` | the full link to parent.html on your site | recommended |
| `CRON_SECRET` | any long random text you make up (save it for step 4) | for the weekly send |
| `OPENAI_API_KEY` | your AI key | optional (AI summaries) |
| `AI_MODEL` | default `gpt-4o-mini` | optional |
| `AI_BASE_URL` | default `https://api.openai.com/v1`; another OpenAI-compatible provider's URL | optional |
| `TIME_ZONE` | default `America/New_York` (decides which weekday it is) | optional |

`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are provided automatically. Never paste the
service role key into any web page.

## 4. Schedule the weekly send (once a day; each parent gets mail only on their chosen day)
Option A (easiest): Dashboard > **Integrations** > **Cron** > enable > **Create job**:
- Name `nr-weekly-email`, schedule `0 13 * * *` (13:00 UTC = 9 AM New York in summer, 8 AM in winter)
- Type **Supabase Edge Function** > `nr-weekly`, method POST,
  header `x-cron-secret: <your CRON_SECRET>`, body `{"action":"cron"}`.

Option B: SQL Editor (needs the pg_cron and pg_net extensions turned on under Database > Extensions).
Replace the two placeholders and run:

```sql
select cron.schedule('nr-weekly-email', '0 13 * * *', $$
  select net.http_post(
    url := 'https://YOUR-PROJECT-REF.supabase.co/functions/v1/nr-weekly',
    headers := '{"Content-Type":"application/json","x-cron-secret":"YOUR_CRON_SECRET"}'::jsonb,
    body := '{"action":"cron"}'::jsonb);
$$);
```
To stop it later: `select cron.unschedule('nr-weekly-email');`

## 5. Try it
1. Open the parent page, sign in, open **Alerts & preferences**.
2. Tick **Send me a weekly email**, pick a day, **Save**.
3. Tap **Send me a preview now** (max 3 per day). It goes to the email you sign in with.
4. Open a kid: the **Summary** card says "AI-written" if the AI key works, otherwise
   "Written from your kid's numbers".

## What gets sent to the AI provider
Only numbers and skill names for one week (minutes, days played, stars, accuracy, weak and strong
skills). The kid's nickname is NOT sent: the text uses a placeholder that is filled in afterwards.
Answers containing links, HTML or email addresses are thrown away and the template is used instead.

## Family Game Night
Nothing to set up in Supabase beyond the defaults: it uses Realtime broadcast + presence with the
publishable key. If you ever turn on "Realtime > Settings > Allow public access: OFF" (private
channels only), Game Night stops working.

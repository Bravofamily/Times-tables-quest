# Changes

## v31 (Oct 29, 2026)
- Fix: going back to Home (in-page Back button, browser back, iPhone swipe back) no longer shows an old Home layout (5 tiles without Heroes plus a "Choose your quest" section). The back/history router called a saved copy of the very first Home renderer from before the v12 redesign; it now always calls the current Home, so it is identical to tapping Home in the bottom bar.

## v30 (Oct 29, 2026)
- Parent Login is now shown to everyone (no ?parenttest=1 needed), so it also appears in the home-screen app: the 🔑 Parent Login button in the top bar on every screen and the Parent Login card on Home (with "What's included?").
- New grown-up gate pop-up: Parent Login and "What's included?" open a modal that says it's for parents and guardians only (18+), with a quick math check and Continue/Cancel. Cancel stays in the game; a wrong answer gives a new question.
- Parent sign-up: a required checkbox "I'm a parent or legal guardian, 18 or older, and I agree to the Terms and Privacy Policy." (links to the Kid-safe/privacy section of parent-about.html). Create account stays disabled until ticked, with a clear error if tried anyway. New accounts store guardian_confirmed=true and guardian_confirmed_at in the user metadata (Supabase signInWithOtp options.data, no SQL change).
- Parent Login (not sign-up) no longer creates new accounts silently (shouldCreateUser:false), so every new account goes through the guardian checkbox.
- Still test-only (behind ?parenttest=1 or a linked device): Family Game Night button, Quest card, Settings "Link to a parent account" card, and the TEST banner on parent pages.

## v29 (Oct 29, 2026)
- Fix: the Parent Login button no longer disappears after going to a parent page and tapping "Back to NumiRealm". The parent test flag is now remembered on the device (localStorage key nr-parenttest) the first time ?parenttest=1 is seen, so it survives back links, sign-in redirects, new tabs, update reloads and the installed app. ?parenttest=0 turns it off on that device. Back links on parent.html, parent-about.html and gamenight.html (including the "Coming soon" card) keep the flag.
- Fix: the auto-update reload now keeps the page's query (?parenttest, ?link) instead of replacing it with ?v= only.
- Updates: the service worker is registered with updateViaCache 'none' and re-checked on launch and whenever the app comes back to the screen. Every HTML page is network-first with no HTTP cache; only the game page is kept for offline play, under its own key (gamenight.html could previously be stored as index.html). If a new version arrives mid-level, an "Update ready: tap to refresh" button appears instead of interrupting.
- APP_VERSION, version.json and the service-worker cache bumped to 29. Added tests/test_v29.py.

## v28 (Oct 29, 2026)
One update: the Time played graph plus the Parent Center (test, parent area only).
- Parent page, kid detail: progress now has four tabs: Time (the Time played graph with Day/Week/Month/Year), Accuracy (percent right per Day/Week/Month/Year, plus the old accuracy trend), Realms and Skill map (one tile per skill: Mastered, Growing, Needs practice, Just started, Not tried yet).
- Needs practice & tips: each weak skill gets a concrete tip using the kid's real numbers ("Mia gets x7 facts right 6 of 14 times"), with buttons to open the matching lesson, send it as a quest, or start a fix-it plan.
- Learn the method: a library of 10 two-minute lessons (7s and 8s, 9s finger trick, making ten, subtracting across zero, remainders, fractions...) with a filter by realm.
- Weekly family challenge: an offline activity plus an in-game goal (stars or minutes this week). The parent taps "We did it!"; the kid sees a badge count in the game.
- Milestones: celebration cards (stars, practice time, answers, realms explored, mastered skills, quests, fix-it plans, family challenges) with a confetti button.
- Quest from home: the parent picks a skill, a number of questions and an optional message. It appears on the linked device's Home screen as a scroll; answers on that skill count toward it and the result syncs back. Max 5 waiting per kid.
- Fix-it plans (5 days): 7s and 8s, halves and fourths, subtracting across zero, remainders. Each day: one in-game quest plus a 2-minute home activity. Shows accuracy before and after.
- Rewards: parent-set real-world rewards for a goal in stars, minutes or quests, counted from the day it is set. Earned automatically; the parent marks it as given. The kid sees the goal and progress bar in the game.
- Alerts in the portal only (bell + banner): milestones, weak spots, finished plans and quests, no play for N days, daily play-time goal. Preferences for which events, the idle days, the daily goal and quiet hours (default 8 PM to 7 AM: no banner, alerts still listed).
- Weekly summary (kid detail, "🗞️ Summary" card): a short note for this week (minutes, days played, stars, accuracy, wins, weak spots, a tip). Written by AI when the server has an AI key (labeled "AI-written"), otherwise by a plain template (labeled "Written from your kid's numbers"). Cached once per kid per week; "Refresh" re-writes it. Without the server function the page makes a smart summary on the device and says so.
- Weekly email (opt-in, off by default): in Alerts & preferences, "Send me a weekly email" plus a day picker, the sign-in address it goes to, and "Send me a preview now" (max 3 per day; shows the email in the page if email is not set up yet). HTML email with the summary, play time, wins, weak spots, tip and family challenge, a button to the parent page, and an Unsubscribe link (one tap, no sign-in) in every email.
- Server: one Supabase Edge Function, supabase/functions/nr-weekly/index.ts (paste in the dashboard editor; no imports). The AI only gets numbers and skill names, never the nickname (a placeholder is filled in afterwards); bad AI answers fall back to the template. Email goes through Resend. Daily schedule sends to parents whose chosen day is today (America/New_York), once per week. Setup steps for a phone: supabase/EDGE_SETUP.md. Local tests with mocks: tests/test_edge.ts (Deno).
- Database (setup-part4.sql, also in setup.sql): notify_prefs gets email_weekly, email_day and a private unsubscribe token; new tables weekly_summaries (parents can read their own kids' rows) and email_log (server only). Rows older than 400 days are deleted by the weekly job.
- Family Game Night (test: ?parenttest=1, a linked device, or the parent page): gamenight.html. A grown-up (behind the grown-up check) opens a room with topics, rounds, time per question, tap or typed answers and optional fair play by age; players join on their own devices with a 5-letter code or QR, pick a hero or nickname and a level. Same-time questions, 100 points plus up to 50 for speed, reveal and leaderboard between rounds, podium with confetti and the owl narrator (voice follows the game's narrator setting). Up to 8 players; reload reconnects, late joiners join in, if the host leaves players see a notice and the game ends after 10 seconds; rooms close after 3 hours. Uses Supabase Realtime broadcast + presence with the publishable key; the host page keeps the answers and scores. Nothing is stored in the database; nicknames exist only while the room is open. Entry points: a "🎉 Family Game Night" button on the test Home card, a small card on linked devices, and a Parent Center tile. Tests: tests/test_gamenight.py (1 host + 3 phones and more).
- Parent portal guided tour: the first time a parent signs in (after consent) a 16-step tour highlights each area with a short explanation and Back / Next / Skip (Esc and arrow keys work): linking a kid, each progress tab (Time, Accuracy, Realms, Skill map), weekly summary, tips, fix-it plans, Quest from home, rewards, alerts and quiet hours, weekly email, Family Game Night, Learn the method, and Help. Steps scroll into view above the popup on phone and desktop. "❓ How it works" in the header replays it any time. Completion is saved on the parent account (user metadata nr_tour_done) and on the device. If no kid is linked yet the tour uses example data.
- Help & FAQ card on the family page: a short tap-to-open explainer per feature, plus a Replay the tour button.
- "👀 Try it with sample data": a made-up "Sample Kid" with a yellow EXAMPLE DATA banner so parents can explore before linking. Nothing is saved; buttons that would save or send are turned off with a note; "Exit example" goes back. Tests: tour section in tests/test_parent.py.
- Polish: chart axes on phone now show "100%" in full and the "Today" label is no longer cut off (wider left/right chart margins); Game Night has the same "🏠 Back to NumiRealm" pill as the parent pages (keeps ?parenttest=1); clean sample names in Game Night tests.
- Coming soon (labeled, not clickable): Ask about my kid, teacher PDF, phone notifications, voice notes, family leaderboard, premium plan, home-screen widget.
- Game: the new Home scroll only exists for a linked device (or with ?parenttest=1) and only shows for the linked hero. Unlinked devices make no requests and look exactly as before. No new kid data is collected: quest answers are counted from the per-skill answer tracking that linked devices already had.
- Game: keeps a small local log of active play time per hero per local day (10-second ticks only while visible and active in the last minute). Days older than 400 roll into months. It leaves the device only when linked, inside the existing push_progress snapshot.
- Database: supabase/setup-part4.sql (also folded into setup.sql) adds progress.play, keeps daily snapshots 400 days instead of 180, and adds the tables quests, fixit_plans, rewards, notify_prefs and challenge_done (RLS on, each row tied to the parent and their own kid, explicit grants, limits per kid) plus two token-checked device functions get_home and quest_progress. Idempotent, plain ASCII, safe to paste on a phone. Until it is run, the parent page shows a friendly note on those cards and everything else works (preferences and the challenge are then kept on that browser only).
- Parent page loads the newest 1000 daily snapshots instead of the oldest 200.
- APP_VERSION, version.json and the service-worker cache: 28. Tests: tests/test_v28.py, tests/test_parent.py (Time played + Parent Center); test_v27.py accepts version >= 27.

## v27 (Oct 29, 2026)
- Parent pages: a "🏠 Back to NumiRealm" button at the top left of the header on parent.html (every screen: login, sign-up steps, email code, consent, family, kid detail, welcome checklist) and on parent-about.html. It goes to the game Home (./). It keeps ?parenttest=1 when you came from the test game (remembered for the tab), and signed-in parents stay signed in.
- Test game (?parenttest=1 only, same one-line switch as the Home card): a compact "🔑 Parent Login" button at the right of the top bar on every screen. It is icon-only on phones so the title keeps its room. It uses the same grown-up gate, then opens parent.html#login. Links from the game to the parent pages now carry ?parenttest=1.
- Tagline capitalised to the official "Enter the Realm. Master the Math." everywhere (Home banner, splash, page description, share text, narrator line).
- No other change to the normal game: without ?parenttest=1, Home and Settings are the same as v26 apart from the tagline, and the game makes no Supabase requests.
- APP_VERSION, version.json and the service-worker cache bumped to 27. Added tests/test_v27.py. Extended tests/test_parent.py (Back button). test_v26.py now accepts version >= 26.

## v26 (Oct 28, 2026)
- Parent Area test pages: parent.html (parent login by email link, child profiles, consent, one-time 10-minute link code/QR, linked devices, progress) and parent-about.html ("What's included?", no sign-in). Supabase JS and QR libraries are vendored in vendor/. Database setup is in supabase/setup.sql.
- Hidden "Parent Login" card on Home and "Link to a parent account (test)" in Settings. Both appear only with ?parenttest=1 (or on a device that is already linked, so it can be unlinked), and both sit behind a grown-up gate.
- No change to the normal game. Without ?parenttest=1, Home and Settings are the same as v25 and the game makes no Supabase requests.
- The service worker never caches parent*.html or vendor/, so the parent pages always come from the network.
- APP_VERSION, version.json and the service-worker cache bumped to 26. Added tests/test_v26.py and tests/test_parent.py (Supabase mocked). tests/test_v25.py now accepts version >= 25.

## v25 (Oct 28, 2026)
- Narrator voice ranking (en-US, Enhanced/Premium/Neural/Siri, local first; novelty/eSpeak voices excluded), late voice loading handled, choice remembered.
- Settings: new "Which voice" picker (default "Best voice (recommended)"), Test voice button, grown-up voice-download tip.
- Chunked speech queue (<160 chars), Chrome keep-alive, iOS gesture priming, cancel on screen change, cancel→speak delay, retry once on error/no start.
- Speech-only normalizer for symbols, fractions (incl. blanks like ?/24), remainders, money, decimals, ordinals, ranges, chapters; emoji stripped; one pronunciation table.
- Rate 0.92, pitch 1.05. APP_VERSION and version.json bumped to 25. tests/test_v25.py added.

## v24 (Oct 28, 2026)
- New "📖 Example" button next to the hint lanterns on every question screen (times tables, all subject chapters, bosses and drills). It opens a worked example of a different problem with the same skill and format and a different answer, solved step by step. "Another example" shows a new one each time, and "Back to my problem" (or ✕ / Esc) returns with your answer, timer and hints unchanged.
- Examples never give your answer away: they don't reuse your problem's numbers (in any order), your answer, or any of your numbers as the example's answer, and a missing-number problem gets a missing-number example that doesn't show your missing number. Equivalent fractions count as the same.
- Examples are free and unlimited: no lanterns used, no change to stars, saves or streaks. Drill timers pause while an example is open. The owl narrator reads the example aloud when the narrator is on.
- Wrong answers in times-table practice now also show a worked example (groups/array and skip counting). Subject wrong-answer examples and lantern limits are unchanged.
- APP_VERSION, version.json and the service-worker cache bumped to 24.

## v23 (Oct 28, 2026)
- New "Get the NumiRealm app" card at the bottom of Home with short Add-to-Home-Screen steps for iPhone/iPad, Android and computers. Your own device's steps show first. An "Install NumiRealm" button appears when the browser offers installation. The card says "You're playing the app version" when opened from the Home Screen.
- Real web app manifest (manifest.webmanifest) and PNG icons (192, 512, maskable 512, Apple touch 180) replace the inline data: manifest, so Chrome, Edge and Android can install NumiRealm. The offline cache includes them.

## v22 (Oct 28, 2026)
- Fonts are now self-hosted (no Google Fonts requests). The offline cache includes them.
- Age is now an age group (4–5, 6–7, 8–10, 11–14). Old saves and old NR1 progress codes with exact ages are migrated on load or import.
- Name tip: "Tip: use a nickname or hero name, not a full name."
- Settings: two-step "Reset all data on this device" (clears saves, backups, session flags, offline cache and service worker).
- New Privacy page for grown-ups, with a footer link plus links on Home, Profile and Settings. It contains placeholders for the operator name and contact email, and makes no compliance claims.
- The progress code now shows: "This code includes your heroes' names, age ranges and grades. Only share it with family." (also in copy, share and download).
- APP_VERSION, version.json and the service-worker cache bumped to 22.

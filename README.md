# NumiRealm

**Enter the realm. Master the math.**

NumiRealm is a story-driven math game for kids ages 4–14. Seven young heroes travel through six realms to undo the Muddle Monster's mix-ups, one chapter at a time. It is a single `index.html` file with no server, no sign-up and no ads.

Play it at **https://bravofamily.github.io/Times-tables-quest/**

## The six realms

| | Realm | What it teaches |
|---|---|---|
| 🌼 | Addition Meadow | Addition |
| 💎 | the Subtraction Caves | Subtraction |
| 🏰 | Times Table Castle | Multiplication |
| ⚓ | the Division Docks | Division |
| 🧁 | the Fraction Bakery | Fractions |
| 🗼 | Muddle Tower | Mixed Math (the finale) |

Inside the game, the realm names, emoji, order and every "six realms" count all come from one list (`REALM_DEFS`). The tests fail if any screen disagrees with that list.

## The heroes

| Hero | Color | Emblem |
|---|---|---|
| Sage | Pink `#ec4899` | 🎤 |
| Emi | Purple `#8b5cf6` | 🌸 |
| Blú | Blue `#3b82f6` | ⭐ |
| Eshon | Green `#16a34a` | ✏️ |
| Melrose | Magenta `#c026d3` | 🧜‍♀️ |
| Cayden | Red `#dc2626` | 🏀 |
| Zea | Violet `#7c3aed` | 🐞 |

Every hero has their own progress, stars and treasures.

## Features

- Chapters for ages 4–14 in every realm, from easy to hard, including long multiplication and long division.
- Missing-number chapters such as `? + 4 = 9` and `6 × ? = 42`.
- Method hints (the lantern), limited so kids still do the thinking.
- Star Path rewards, treasures and badges, including Realm Finisher.
- A narrator that reads aloud, plus sound effects, each with its own on/off switch.
- Auto-update. The game checks `version.json` and reloads to the new version, waiting until no level is in progress.
- One layout that works on phones, tablets and desktops, and can be added to the home screen.

## How saving works

- Progress is stored **only on this device**, in the browser's local storage (`ttq-save-v2`). There are no accounts and no cloud copy.
- Each time the game saves, it also writes a backup copy (`ttq-save-v2-backup`). If the main save is ever damaged, the game restores the backup and shows a short notice. The damaged copy is kept (`ttq-save-v2-corrupt`), never silently wiped.
- If the browser blocks storage (for example, some private browsing modes) or storage is full, the game still runs and keeps progress in memory for that visit. A notice explains this.
- **Moving progress to another device:** open Settings → *Copy my progress (For grown-ups)*. You can copy the progress code, share it, or download it as a file. On the other device, paste it under *Load progress*. The game checks the code, shows each hero's stars, offers to download a backup first, and only replaces progress after you confirm.
- The progress code is versioned (`NR1.`). It holds the save as compressed JSON in base64url, plus a CRC-32 checksum, so damaged or mistyped codes are rejected.

## Built vs. future

**Built today:** everything above. It runs fully offline in the browser, with no backend.

**Not built.** These are ideas only; none of them exist yet:

1. **Phase 1: optional cloud backup.** Add a small backend, such as Firebase (Auth + Firestore) or Supabase (Auth + Postgres with row-level security). A grown-up account would own the family's saves, and the progress-code format would become the upload format. Local play would keep working without an account.
2. **Phase 2: COPPA-aware consent.** Only an adult creates the account, with verifiable parental consent before any child data leaves the device. Collect as little data as possible (hero name and progress, no child email), and offer clear delete/export options and a privacy policy.
3. **Phase 3: sync between devices.** Use last-writer-wins per hero, with a merge preview that reuses the import screen.
4. **Phase 4: a grown-up progress view.** A read-only summary of stars, chapters and needs-work facts.

Payments are not planned.

## Project layout

```
index.html          the whole game (HTML, CSS and JS in one file)
version.json        {"version": "N"}; must match APP_VERSION in index.html
.nojekyll           serve files as-is on GitHub Pages
tests/              Playwright browser tests (Chromium + WebKit)
  run_all.sh        runs every test against ../index.html
docs/screenshots/   phone (390px) and desktop (1280px) screenshots
```

## Releasing an update

1. Bump `APP_VERSION` in `index.html` and `"version"` in `version.json` to the **same** number.
2. Run `tests/run_all.sh` (needs Python 3 and `pip install playwright && playwright install chromium webkit`). Every test must pass.
3. Commit both files together on `main`. GitHub Pages serves them, and open games pick up the new version on their next check.

Saves are never touched by an update.


## Offline play (v21)
`sw.js` must be published next to `index.html`. It caches the game after the first visit. `index.html` is always fetched from the network first and `version.json` is never cached, so auto-update keeps working. Each release gets its own cache (`numirealm-v<APP_VERSION>`), and older caches are deleted.

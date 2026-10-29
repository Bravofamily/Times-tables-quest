# NumiRealm

NumiRealm, a story-driven math game (addition, subtraction, multiplication, division and fractions) for Sage, Emi, Blú, Eshon, Melrose and Cayden.

It can be played at https://bravofamily.github.io/Times-tables-quest/.

## Releasing an update

Each release must bump the version in two places together, `APP_VERSION` in `index.html` and `"version"` in `version.json`, for example both to `"7"`. When the game is opened, and again each time it comes back to the foreground, it checks `version.json`. Phones that saved the game to the home screen then reload the new version automatically. If a level or boss is in progress, the reload waits until the map or hero select screen. Saves are kept.

## Privacy and data (v22)

- Everything is stored only in this browser (localStorage). There are no accounts, ads, analytics or third-party requests. The fonts (Baloo 2 and Poppins, SIL Open Font License) are self-hosted in `fonts/`.
- Heroes pick an age group (4–5, 6–7, 8–10, 11–14), not an exact age. Saves and progress codes from older versions that use exact ages are converted automatically.
- Grown-ups can read the Privacy page from the footer, Home, Profile or Settings. The page names BVO Global LLC as the operator, with contact email bvoglobalmarketing@gmail.com (`PRIV_OPERATOR` / `PRIV_CONTACT` in `index.html`).
- Settings → "Reset all data on this device" removes every hero, backup, saved file and the offline cache after two confirmations.

## Tests

`test_v22.py`, `test_v23.py` and `test_v24.py` run with Playwright. Set `PWB=chromium` or `PWB=webkit` and optionally `SHOTS=1` for screenshots. Run it from this folder.

## Example button (v24)

Every question screen has a "📖 Example" button next to the hint lanterns. It shows a different problem of the same kind, worked step by step, as many times as the player likes. It's free (no lanterns), pauses drill timers, and keeps the player's answer in place.

## Install as an app (v23)
NumiRealm is a web app, not an App Store app. Grown-ups can add it to the Home Screen (Safari → Share → Add to Home Screen; Chrome on Android → ⋮ → Install app; Chrome/Edge on a computer → install icon in the address bar). Files: `manifest.webmanifest`, `icons/`. Steps are shown on the Home screen.


## v25 – Smoother narrator
- Picks the most natural voice on the device (Enhanced/Premium/Siri-style voices first, novelty and robotic voices skipped), with a **Narrator voice** picker ("Best available (recommended)") and a **Test voice** button in Settings.
- Speech is split into short chunks and queued, with fixes so it doesn't cut out (Chrome keep-alive, iPhone first-tap unlock, retry once, stops when you change screens).
- Math is read aloud the way a teacher says it ("7 times what number equals 14", "three fourths", "23 remainder 3") and names are pronounced right (Bloo, Kee-lo, Eh-shawn, Zee-uh). Text on screen is unchanged.
- Tip for grown-ups: on iPhone/iPad download nicer voices in Settings › Accessibility › Spoken Content › Voices.

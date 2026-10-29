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

`test_v22.py` runs with Playwright. Set `PWB=chromium` or `PWB=webkit` and optionally `SHOTS=1` for screenshots. Run it from this folder.

# Times Table Quest

Times Table Quest, a story-driven math game (addition, subtraction, multiplication, division and fractions) for Sage, Emi, Blú, Eshon, Melrose and Cayden.

It can be played at https://bravofamily.github.io/Times-tables-quest/.

## Releasing an update

Each release must bump the version in two places together, `APP_VERSION` in `index.html` and `"version"` in `version.json`, for example both to `"7"`. When the game is opened, and again each time it comes back to the foreground, it checks `version.json`. Phones that saved the game to the home screen then reload the new version automatically. If a level or boss is in progress, the reload waits until the map or hero select screen. Saves are kept.

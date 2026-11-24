# English Reading Room · Instagram

Gayane Torosyan · English Reading Room — "Let's read together".

The page publishes one format only: **Daily reading** reels with their Story.

| Series | Weekdays | Weekend | Story |
|---|---|---|---|
| Ani | 10:30 | 11:00 | 30 min later |
| Mila & Leo | 20:30 | 20:30 | 30 min later |

## A new lesson
1. Text: add an entry to `reels/data/reading.json` (id, number, title, title_hy, level, voice `chatterbox:sonia`, pic_words, en, hy).
2. Pictures: add `assets/reading/<id>/sheet.png` (2×3 grid). "Reading sheets to pictures" cuts and sharpens it, then starts "Make voices".
3. Queue: add the reading and its story to `queue.json` (see the latest items); "Render ahead" renders them to english-reels-media.
4. "Publish due post" publishes on time. Checks: English check, Voice check, Code check, Watchdog.

Docs: `docs/mila-leo-lessons.md`, `docs/mila-leo-bible.md`, `docs/ani-winter-readings.md`. History: `HANDOFF-LOG.md`.

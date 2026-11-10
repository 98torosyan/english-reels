# Gayane Torosyan · English Reading Room

**Let's read together.** This private repository prepares short lesson reels, rule carousels, captions, and a review queue for `@english.readingroom`.

## Folders

- `reels/` — story, common-mistake, quiz, and word-of-the-day layouts and renderers.
- `carousels/` — the 21-rule bank and seven-slide carousel renderer.
- `captions/` — caption guidance; the current dated captions are stored with their entries in `queue.json`.
- `publish/` — safe API checks, draft queue builder, and a manual publishing client.
- `.github/workflows/` — `test-meta-access.yml` (account check), `publish.yml` (scheduled publishing, off until the `PUBLISH_ENABLED` variable is `true`), `qc.yml` (English check).
- `review/` — review gallery (`build_review.py` → `review/index.html`) and `apply_review.py`.
- `music/` — original background loops (`make_music.py`); mixed under the voice with automatic ducking.
- `qc/` — LanguageTool English check.
- `assets/` — the original book mark, lesson text, Armenian translations, timings, and voice tracks.

The current three bundled stories are *A Day at the Zoo*, *The Saturday Market*, and *My Little Garden*. To add another site lesson, run:

```powershell
python reels/import_lesson.py --site-repo "C:\path\to\english-reading" --id lake-sevan
```

Then add and review its Armenian sentence translations in `assets/lessons/translations.hy.json` before rendering it.

## Local setup

Requirements: Python 3.10+, Node.js, npm, and Google Chrome.

```powershell
npm install
npm run build:queue
npm run render:samples
```

To render one item, pass its type and ID:

```powershell
node reels/generate.js story zoo 1
node reels/generate.js mistake plural-subject
node reels/generate.js quiz plural-verb
node reels/generate.js word lazy
node carousels/render.js tenses
```

Reel MP4s and carousel slides are written to the local `outputs/english-reels-samples/` folder beside this repository. Reel videos are 1080×1920; carousel slides are 1080×1350. The renderer uses Literata, Inter, and Noto Sans Armenian from the package dependencies.

## Queue and review

`queue.json` contains 30 daily reel drafts and three carousel drafts per full week (13 in the current 30-day window). Every item is marked `draft` and requires human review. Review English, Armenian, audio, and crop margins before using any media. No publishing schedule is enabled.

## Instagram access

The account/container check reads `IG_TOKEN` and `IG_USER_ID` from GitHub Actions Secrets and does not display either value. It verifies `@english.readingroom`, creates one unpublished image container, and checks for `FINISHED` status. The container is not published.

`publish/publish.py` reads an item JSON and defaults to `DRY_RUN=1`, which sends no Graph API requests. The code repository stays private. Instagram needs public media URLs, which belong in the separate media repository configured for Pages; source code and credentials must not be placed there.

The current credential is a never-expiring Meta System User token. It does not use the 60-day Instagram Login refresh endpoint. If Meta revokes it or access changes, replace it in GitHub Secrets; do not write a token to this repository.

Real publishing remains off until the owner approves it explicitly.

## Publishing flow

1. `python review/build_review.py` → open `review/index.html`, mark ✅/✏️, Export `review.json`.
2. `python review/apply_review.py review.json` → approved items get `review_status: approved`.
3. `python publish/stage_media.py --media-repo ../english-reels-media` → renders approved items, copies media to the public media repo, fills `media` URLs (`staged`).
4. Commit + push both repositories.
5. `publish.yml` runs at 13:07 and 19:07 Yerevan and publishes the one item that is due. It publishes for real only while the file `publish/ENABLED` exists — delete it to pause everything.

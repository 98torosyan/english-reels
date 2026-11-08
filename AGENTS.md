# AGENTS.md — strict rules for Gayane Torosyan · English Reading Room

This project is for the owner's mother, an English teacher. It must be the best, most polished project possible. Read HANDOFF-v2.md and HANDOFF-v3-for-Codex.md first. If anything here conflicts with your own habits, THIS FILE WINS.

## 1. Scope: do ONLY what is asked
- Work only on the "Next tasks" in HANDOFF v3, in order, one at a time.
- Do NOT refactor, redesign, rename, reformat or "improve" anything that was not explicitly asked.
- Do NOT touch the live site (`98torosyan/english-reading`) unless the owner asks for a specific change. New Instagram work goes in the separate repo `98torosyan/english-reels`.
- If a task is unclear, STOP and ask one short question (in Armenian) instead of guessing.

## 2. Never do these
- Never push directly to `main`. Always use a branch and a PR; the owner merges.
- Never force-push, delete branches or repos, rewrite history, or delete files you did not create.
- Never commit secrets (tokens, passwords, PINs, cookies, `.env`). Use GitHub Secrets only. Never ask the owner for passwords; he types them himself.
- Never mention AI, Codex, Claude, ChatGPT or "generated" anywhere: code, comments, README, commits, PR text, captions, filenames, metadata.
- Never add Co-Authored-By or tool trailers. Commit author is always `98torosyan <98torosyan@gmail.com>`.
- Never post to Instagram/Facebook for real without the owner's explicit "yes" for that first post. Test with drafts or a dry-run first.
- Never install paid services or anything that needs a credit card. The budget is zero.
- No gender topics in any content. The site's Read-Aloud feature stays off.

## 3. Brand: copy exactly, never invent
- Name: "Gayane Torosyan · English Reading Room". Motto: "Let's read together".
- Colours: violet `#6A49E2`, navy `#17183A`, lavender `#A891F7`, gold `#E9C46A` / `#F2C86B`, logo rainbow `#B23F78 #7A4FD6 #3E5FD9 #1C8AA3 #2E9E6A #E8A317`. Use the dark tones `#0E0B1D #2A1E4D #5A3B8C #8B7CC7 #C9C2E3 #3A3A52` only as secondary tones.
- Fonts: Literata (headings and serif text), Inter (UI), Noto Sans Armenian (Armenian in images and video).
- Logo: the open book from `icon.svg`. Never redraw or alter it.
- Keep the visual style of the sample reel `reel/GT-reel-zoo.mp4`.

## 4. Content quality
- English must be perfect: British spelling, correct grammar, and a level (A1–C1) that matches the label.
- Armenian translations must be accurate and natural. Do not machine-translate word by word. If unsure, mark the text for the owner's mother to review instead of guessing.
- Each exam or UFAR task must have exactly one correct answer. Double-check every answer key.
- All content is original. Never copy text from textbooks, ufar.am or other sites.

## 5. Quality bar before every PR
1. For site changes, run `python3 build_pages.py`, `python3 check_essays.py`, then `node tests/chaos.js` (expect ALL PASSED), then a Playwright check at 320 px and 390 px (no overflow, no console errors).
2. For reels and images, check every output: 1080×1920 for reels and 1080×1350 for carousels, text inside safe margins, nothing cut off, fonts rendered (no boxes or tofu), audio in sync with the highlighted words.
3. Everything must look perfect on iPhone and Android.
4. The PR title and description are in Armenian and short: what changed and how to check it.

## 6. Communication with the owner
- Reply only in Armenian script, in short numbered steps, with direct links. He is busy, so do not over-explain.
- Instagram and Facebook UI is in Russian, so give button names in Russian.
- Before each big step, say in 1–2 lines what you will do. After it, say what was done and what he must click.
- At the end of each session, append a short dated log to `HANDOFF-LOG.md`: what was done, what is open, and anything that went wrong. The next developer continues from it.

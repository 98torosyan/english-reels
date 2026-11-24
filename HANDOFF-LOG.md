# Փոխանցման մատյան · 2026-11-09

## Կատարված

1. Անձնական կոդի պահոցը՝ `98torosyan/english-reels`, private է։ Փոփոխությունները պատրաստվում են `codex/instagram-access-check` ճյուղում՝ վերանայման PR-ի համար։
2. GitHub Secrets-ում առկա են `IG_TOKEN` և `IG_USER_ID` անունները։ Արժեքները պահոցում կամ մատյանում չկան։
3. Meta-ի ստուգումը ճանաչել է `@english.readingroom` հաշիվը։ Մեկ փորձնական media container-ը հասել է `FINISHED` վիճակին և չի հրապարակվել։
4. Պատրաստ են պատմության, տարածված սխալի, quiz-ի, օրվա բառի և 21 թեմայով carousel-ի գեներատորները։ Carousel-ը 7 սլայդ է՝ վերջին սլայդում `Save 📌` նշումով։
5. `queue.json`-ում կա 30 օրվա համար օրական մեկ reel և շաբաթական երեք carousel՝ 30 reel և 13 carousel։ Բոլորը նշված են որպես սևագիր և պահանջում են մարդու վերանայում։
6. `publish/publish.py`-ի `DRY_RUN=1`-ը լռելյայն է։ Հրապարակման գրաֆիկ կամ ինքնաշխատ workflow միացված չէ։ Ջնջման endpoint չկա։
7. Հանրային `98torosyan/english-reels-media` պահոցում `media` ճյուղից միացված է GitHub Pages-ը։ Ճյուղում միայն `.nojekyll` ֆայլն է. նմուշային բովանդակություն դեռ տեղադրված չէ։
8. Տեղային նմուշները՝ 3 reel և 7 carousel սլայդ, գտնվում են `outputs/english-reels-samples/` պանակում։

## Սպասվող քայլեր

- Հաստատել նմուշների հայերենը, անգլերեն օրինակները և ամբողջական queue-ի բովանդակությունը՝ հրապարակումից առաջ։
- Նմուշային ֆայլերը հանրային media պահոց տեղափոխել միայն սեփականատիրոջ հստակ հաստատումից հետո։
- Instagram-ում հրապարակումը և ժամանակացույցը միացնել միայն «yes publish» հաստատումից հետո։
- Այս ճյուղի PR-ը սպասում է վերանայման և միավորման։

## Մուտքի նշում

Գործածվում է անվերջ ժամկետով Meta System User token՝ `instagram_basic` և `instagram_content_publish` scope-երով։ `business_management` scope-ը հասանելի չէր։ Այս token-ը 60-օրյա Instagram Login token չէ, հետևաբար 60-օրյա փոխանակում կամ թարմացում կիրառելի չէ։ Token-ի արժեքը այստեղ չի պահվում։

## 2026-11-10
- Animated cards (kinetic headline, 5-second countdown ring, confetti, check draw), human pacing, brand-only colours, own music (8 loops) + sound effects.
- New list carousels (`carousels/data/lists.json`): dont-know, make-do, feelings, cafe. Slides are JPEG for Instagram.
- `publish/plan_launch.py` → queue.json (launch burst 10–14 Nov, then weekly rhythm). Items 10–14 Nov are staged in english-reels-media.
- Merged to `main`; `publish.yml` runs hourly at :07 and publishes for real because `publish/ENABLED` exists (delete it to pause).
- Open: stage items from 15 Nov on; more stories (only 3 have audio); Exam/UFAR and Kids series; new voices.

## 2026-11-10 (երեկո)
- Emoji և նկարազարդ հերոսներ ամբողջովին հանված են (պատմությունների reels-ից նույնպես). Zoo մաս 2/3-ը վերապատրաստված և փոխարինված են media պահոցում։
- Նոր սերիաներ.
  - **Sound it out** (`reels/render_sound.js`, `reels/templates/sound.html`, `reels/data/sounds.json`)՝ 10 բառազույգ հայերին բնորոշ դժվար հնչյուններով. լսել → բացատրություն → A/B թեստ → նախադասություն + «Your turn»։
  - **Everyday English** (`reels/render_dialogue.js`, `reels/templates/dialogue.html`, `reels/data/dialogues.json`)՝ 14 երկխոսություն. լսել, հետո դիտողը խաղում է B-ի դերը (B-ի ձայնը լռում է, ժամանակի գոտի)։
  - 8 նոր carousel՝ get, pay, catch, keep, break, word-pairs (collocations), polite, goodbye։
- Ձայները՝ `voices.yml` (`voice_sounds`, `voice_dialogues`), `apt-get update` ավելացված։ Libby ձայնը երկու նախադասության վրա ձախողվեց. փոխարինված է։
- Երաժշտություն՝ 16 track (`music/make_music2.py`-ով 8 նոր՝ դաշնամուր, lofi, մարիմբա, կիթառ, չելեստա, լարային)։ `stage_media.py`-ն ընտրում է track-ը հերթափոխով (`MUSIC_TRACK`), հարևան reels-ը նույն երաժշտությունը չունեն։
- `publish/plan_week.py`՝ նոյեմբերի 11–17. 12:00 carousel, 17:00 երկխոսություն, 20:00 հիմնական reel, 09:00/18:00 stories։
- Saturday Market մաս 2-ի չակերտները ուղղված են (յուրաքանչյուր նախադասություն՝ ամբողջական չակերտներով)։
- Բաց է. նոյեմբերի 18-ից հետո պլանը, keep/break/word-pairs/goodbye carousel-ները դեռ հերթում չեն, Sound it out 03–10, երկխոսություններ 09–14։
- Գիշեր (22:00–23:00).
  - GitHub-ի `schedule`-ը այս պահոցում ոչ մի անգամ չի աշխատել։ Հրապարակումը արթնացնում է ամենօրյա scheduled task-ը (Claude-ի կողմից), որը `publish/TRIGGER`-ը push է անում 11:33, 12:33, 18:33, 19:33, 21:33-ին (Երևան)։ Workflow-ի cron-ը (`7,37 7-18` UTC) մնացել է որպես պահուստ։
  - Բոլոր գրառումների ժամերը նոյեմբերի 11-ից համապատասխանեցված են :30 ժամերին՝ `publish/retime_slots.py`։
  - `publish.yml`-ի «Save published status»-ը հիմա կրկնակի փորձ է անում (`git pull --rebase` + push). 21:31-ին push-ի բախման պատճառով նշումը չէր պահպանվել և ձեռքով ուղղվեց։
  - Stories (օրվա բառ / արտահայտություն) հիմա տեսանյութ են՝ ձայնով և երաժշտությամբ (`stories/story_video.py`, ձայները՝ `voice_stories`)։ `publish.py`-ն ընդունում է STORIES `video_url`-ով։
  - «Գրե՛ք Direct-ով» կոչը՝ caption-ներում, carousel-ի վերջին սլայդում, reels-ի վերջաբանում, `dm-lessons` story (11, 13, 15, 17 նոյեմբերի, 21:30)։
  - `qc/system_check.py`՝ ամբողջական ստուգում (հերթ, մեդիա, emoji, ձայներ)։
  - Ստեղծված, բայց չօգտագործված fine-grained token `publish-ticker` (միայն english-reels, Actions RW). կարելի է ջնջել GitHub → Settings → Fine-grained tokens։
  - Երկխոսություն pizza/5 («Fifteen Green Street.») ձայնը չի ստեղծվել. ստուգել, մինչ pizza-ն պլան մտնի։

## 2026-11-11 (գիշեր)
- Նոր դիզայն՝ «բառարանի էջ». թղթի ֆոն, ամեն հմտություն իր գույնով (`reels/render_utils.js` → `SKILL`, `paperTheme`, `reels/templates/paper.css`). Մուգ տարբերակը՝ `THEME=dark`։
- Ամեն սերիա ունի իր շապիկի կոմպոզիցիան (`covers/cover.html`, `covers/specs.py`, `covers/render_covers.js`)։ Reels-ը հրապարակվում են `cover_url`-ով (`publish.py`), carousel-ների 01 սլայդը շապիկն է (`covers/attach_covers.py`)։
- Նոյեմբերի 11–18-ի բոլոր նյութերը (29 + stories) վերապատրաստված են նոր ոճով։

## 2026-11-12 (night)
Done:
- Highlights: 21 stories published (GitHub Actions outage delayed them; republished at 01:00–01:20). Owner created highlights; English names.
- New series, all staged in queue.json:
  - 10 words (reels/render_words10.js): reel 20:30 + story 14:30 daily, Nov 12–25 (14 themes). Colour rotates per day.
  - Phrasal verbs (reels/render_phrasal.js): animated word-by-word captions, reel 13:30 + story 17:30 every other day, Nov 14–28 (8 verbs).
  - Weekly review (reels/render_review.js): Sundays 12:00, Nov 15/22/29, reuses 10-words audio.
  - Weekly PDF word books (books/render_book.js) → english-reels-media/books/english-reading-room-week-{1,2}.pdf.
- Dialogue template: pop animation on the spoken word.
- QC: LanguageTool now self-hosted in CI (qc.yml) over all on-screen English (found sweater → jumper); IPA checked against Britfone (qc/check_ipa.py, allow-list hand-checked against Oxford).
- Voices: character-level alignment (fixed pizza/5). Kokoro voice test samples in assets/voice-test (owner to choose).
- Analytics (analytics/insights.py, analytics.yml): daily snapshot, Monday report as a GitHub issue. Post insights need instagram_manage_insights on IG_TOKEN (currently only likes/comments/followers).
- Cross-posting (publish/crosspost.py): YouTube Shorts and Facebook Page, active only when YT_* / FB_* secrets are set.
- Plan scripts re-read the queue before writing (no more overwriting published marks).
- system_check: 0 fail, 0 warn.
Open:
- Owner: token with instagram_manage_insights; YouTube OAuth secrets; FB page token; PDF link in bio; choose Kokoro voice; mother to review Armenian of words10/phrasal.
- Content after Nov 18 for dialogues/stories/carousels still draft; plan next week.
- (05:00–06:00) Emma (Kokoro bf_emma) now the female voice of 10 words / phrasal / review; all staged items re-rendered. Nov 18–26 filled: one dialogue a day at 18:30 (remaining 9 dialogues) + prepared drafts staged with covers. Mistake covers no longer reveal the answer. stage_media saves the queue after each item. system_check: 0 fail, 0 warn, 161 items.
- (07:30) Daily reading / Did you know (reels/render_reading.js): 10 illustrated stories, 10:30 daily Nov 13–22, Kokoro voices George/Emma/Isabella, slow pace with sentence pauses. Voice polish + loudness (-14 LUFS) in render_utils.encodeVideo for all new renders. Ticker and publish cron now start at 10:00. Captions: keyword first line, comment question, 5 hashtags (#learnenglish #անգլերեն #անգլերենիդասեր <series> #Yerevan) via publish/fix_captions.py (run after any plan_*). English check allow-list in qc/data/english_allow.json. Final: system_check 0 fail / 0 warn / 171 items; CI checks green; both repos pushed.

## 2026-11-13 (night)
- Panels: tools/upscale_panels.py + .github/workflows/panels.yml — storyboard (2x3 or 3x3) cut and sharpened in CI with Real-ESRGAN via spandrel; anime-6B weights for illustrations, x4plus blended with a plain resize for photorealistic folders (marker file `photo`).
- Carousels (picstory): new words highlighted in the sentences + word card; story teaser at 16:50; alt text for every slide (publish.py falls back to no alt text if refused).
- Motion: GSAP + SplitText (reels/templates/kinetic.js) in all reel templates; publish/rerender.py re-renders scheduled reels in place (same URLs, same music; --kinds, --from-date).
- Quality: verifyVideo checks loudness (-18…-11 LUFS), clipping and black frames; encodeVideo levels loudness in a second pass. 41 older videos (dialogues/stories/quiz/mistake) were quiet (-19…-24 LUFS) and were levelled in place. All 89 upcoming videos pass.
- Checks: watchdog.yml (late posts + Instagram token validity → issue/e-mail), voice-qc.yml (faster-whisper listens to every clip; report only, never blocks publishing), qc/check_level.py (wordfreq; report only).
- Voices: 13 British voices rotate (Kokoro emma/isabella/alice/lily/george/daniel/lewis/fable + Microsoft Sonia/Libby/Ryan/Thomas/Maisie). Catalogue: assets/voice-test/catalogue. voices.yml runs one at a time.
- New series "Everyday English" (reels/render_routine.js, reels/data/routine.json, publish/plan_routine.py): 11 stories from 3x3 storyboards, Nov 14–24 at 19:00. ALL HELD as draft — the owner will say when to publish (set review_status to "staged").
- Open: owner's go-ahead for Everyday English; mother to review the Armenian of routine.json; next storyboards should ideally be 9:16 panels.
- (morning) Title mask no longer clips descenders (kinetic.js K.roomy, words10); story videos: next sentence appears only after the previous one has gone. All 94 upcoming videos re-rendered and verified (loudness, clipping, black frames). Loudness levelling limiter at 0.7. Story videos paper-boat/picnic/concert/bottle approved by the owner: Nov 14–17 at 21:00. Held (draft, waiting for the owner): 12 Everyday English incl. restaurant dialogue, 4 real-life story videos (english-life, london-day, wallet, interview). Owner keeps the high daily volume while the page is new.

## 2026-11-17
- Feelstory (reels/render_feelstory.js, reels/data/feelstory.json, publish/plan_feelstory.py): emotional stories, picture melting into paper, every word lights up as spoken, Microsoft voices, felt-piano bed, designed grid covers. Dog-window published 14:12; teacher / old-coat / lunchbox / grandma daily 22:00 Nov 18–21.
- A Day in Opposites (carousels/render_opposites.js stills, carousels/render_opposites_video.js animated 4:5 video slides, carousels/data/opposites.json). Day 1 published 14:46 as a carousel of 6 videos + quiz still. publish.py now creates VIDEO carousel items and retries a failed one once.
- Speed: compact Real-ESRGAN models (panels in ~2 min); renderFrames renders on several identical pages (RENDER_WORKERS), output identical (PSNR 52 dB).
- Voice: tools/voice_finish.py in voices.yml — Pedalboard polish + ctc-forced-aligner word times, clamped to the end of speech. 718 clips done; start error 0.095 s → 0.043 s.
- Safety: run_due waits until every media link answers; watchdog warns when the plan runs dry (< 4 days); tools/check_code.py + code-check.yml on every push (Python, JS incl. template scripts, data, queue validation) and the full system check every night (opens an issue on failure).
- Covers: tools/make_covers.js (classic and story reels, one warm paper); 19 older reels restaged in the clean design (no "No." labels) with fresh covers.
- QC: English check covers feelstory/opposites (caught Mom → Mum); voice check ignores quotes/spacing. Armenian Hunspell check tried and removed (dictionary misses too many correct forms).
- Control panel: tools/build_panel.py → private page with alerts, next 7 days, grid preview, queue by series.
- Open: token with instagram_manage_insights; held Everyday English clips flagged by voice QC (stir/keys/Hyde Park) need re-voicing before release; British vs American and school words10 pictures awaited.

## 2026-11-17 (evening) — 4K reels, Story in a minute with 6 pictures
- All reels now render at 1872x3328 (9:16) / 1872x2340 (4:5): RENDER_SCALE=26/15 in reels/render_utils.js (RENDER_SCALE=1 = old 1080p). Max Instagram API width is 1920.
- feelstory template: picture feathered on all 4 sides + eased melt into the paper.
- upscale_panels.py: `single` marker = one full picture (kept at 2160 px wide), optional `boxes` crop. NEVER run it locally without --sharp (it overwrites sharpened panels).
- Story in a minute: 6 pictures per story, assets/minute/sNN-K/ (tools/ingest_minute.py <folder with sNN-K.jpg>); renderer spreads pictures over the speech, changes snap to spoken words.
- Done: minute-the-happy-prince (6 pics). Others still use old 1-picture sheets; scenes for all 50 in the session scratchpad (six.py) — to redo: 6 Gemini images per story, same chat, full rules in every message (no collage, calm lower quarter fading to cream).
- Owner: continue the other 49 later; there is enough stock of reels now. All 50 remain held.

## 2026-11-18 — owner review of the queue
- Owner reviewed every prepared post (artifact "Հերթի ստուգում"): 38 removed, then ALL words (words10, word) and ALL dialogues removed.
- TODO (owner wants it): rebuild the Words and Dialogues sections from scratch in better quality, then queue them again.
- New music candidates in music/new (12 tracks, real instruments via FluidSynth) wait for the owner's pick.

## 2026-11-18 (evening) — moving painted stories
- New format: 6 short motion clips (owner animates the six cut scenes of one 6-panel sheet) → `assets/motion/<id>/in1..6.mp4`.
  The "Sharpen motion clips" workflow (motion.yml) upscales them with Real-ESRGAN and keeps them on the `motion-clips` branch.
  `python reels/render_motion.py <id>` builds the 4K reel: picture melting into warm paper, each sentence under it while the narrator speaks, soft music.
  Text and voice live in reels/data/talk.json (kind "story", person "Narrator"); voices.yml makes the clips.
- First one: "The Gift of the Magi" (magi). Finished reel stored on `motion-clips` branch under finished/. NOT queued: the owner wants to collect several and publish later on his word.
- LumiTap tag 4 → lumitap.github.io/reading/ (English Reading Room page with Instagram button).
- Open: readings for Nov 23–29 still need plan_reading.py; talk-cafe bubble overlap fix is in the template (re-render pending).

## 2026-11-18 (late) — story reels on autopilot
- GitHub Actions minutes for this private repo ran out at 20:35 (job annotation: spending limit). Nothing runs until the
  repo is public (owner chose this; history scanned: no secrets, the one "EAA…" hit is base64 inside assets/logo-ig.svg).
- New, all free: Telegram helper (telegram.yml every 5 min + tools/telegram_bot.py): owner sends the story JSON,
  then the 6-scene sheet (cut and sent back as 6 files), then six clips → tools/story_pack.py adds it →
  story.yml: narration (tools/story_voice.py) + six clips smoothed to 48 fps and sharpened to 1872 px in parallel →
  reels/render_motion.py (vertical clips fill the screen, dark or light page from the mood) → tools/check_reel.py →
  kept on the motion-clips branch, listed in reels/data/stories_ready.json, phone copy sent on Telegram.
  Needs secrets TG_BOT_TOKEN and TG_CHAT_ID (the bot tells the chat id on /start while TG_CHAT_ID is empty).
- The Last Leaf (leaf): text in talk.json, clips in assets/motion/leaf. Once public: run story.yml with story=leaf.

## 2026-11-19 (night) — Lady, Stories, storyteller voice, voice fixes
- Lady (lady): 5 still pictures (no Grok) → 4K camera moves made once (assets/motion/lady/still marks it, story.yml skips
  sharpening). Held. story_pack accepts 4–6 scenes.
- The Last Leaf reel published 21:05; its Story (picture + gold book frame + hook + music) published by the system.
  tools/story_card.py + reels/story_card.js make such Stories; plan_stories.py now queues one at 21:30 after every
  story reel (render spec {"story_card": …}, picture "motion:<id>:<scene>"); hooks/author in talk.json.
- Narrator voice for story reels: Chatterbox (Resemble AI, MIT) "chatterbox:builtin" — owner chose it (sample 3).
  story.yml voice job installs it; story_listen checks every sentence. reuse_clips input re-renders without sharpening.
  Lady, Magi, Red Mitten re-voiced. Readings keep their own per-reading voices (owner's earlier wish).
- Morning Telegram note (analytics/daily_tg.py, in analytics.yml): followers, yesterday's posts, best series.
  Followers 74 → 228 on Nov 19. Insights (views/saves) still need the token's instagram_manage_insights permission.
- Voice fixes: tools/fix_voice.py + fix-voices.yml (best of several paces, heard by faster-whisper). 7 of 10 flagged
  city clips fixed; London (Nov 20) and Paris re-rendered. Still unclear to the listener: prague v1/v7, dubai v7, venice v6.
- Cleanup: removed motion.yml (it re-sharpened clips on every story commit), voice-test, voice-catalogue,
  test-meta-access workflows and samples. Owner did NOT like the unified page redesign proposal — do not apply it.

## 2026-11-20 / 21 — Stories for every post, new heroes, storyteller voice for readings
- Every reel and carousel gets its own Story 30 min later (publish/plan_story_cards.py, run by render-ahead.yml before
  rendering; tools/story_card.py + reels/story_card.js: picture full screen, gold book frame, darker surround, hook, music).
- Followers: 74 (Nov 19) → 496 (Nov 20). Readings earn ~6× the likes of other kinds. Morning Telegram note works
  (analytics/daily_tg.py), but GitHub runs the schedule late.
- Goharik (13, a student of the owner's mother; parents agreed): feelstory "A letter from London", 3D animated style,
  published Nov 21 21:00. Grandma moved to Nov 29.
- Lady published Nov 21 18:00 (owner said so); Jack and the Beanstalk moved to Dec 14 18:00.
- Five Ani winter readings from the owner's sheets: winterwalk Dec 1, snowman Dec 5, cookies Dec 9, skating Dec 14,
  tree Dec 27 (owner wants similar-looking ones on separate days). reading_panels.py keeps wide panels wide (2×3 or 3×2).
- Briefs waiting for sheets: docs/ani-winter-readings.md (toy shop, snow day, Grandpa Frost, gift, New Year's Eve) and
  docs/pip-forest-library.md (new hero Pip the fox, 5 stories). Marianna (estate agent, friend; she agreed): prompt and
  text given in chat, waiting for the owner's sheet.
- Owner said kokoro reading voices sound bad: ALL upcoming readings (Nov 22 → Dec 27) now use "chatterbox:builtin"
  (voices.yml installs it in a second step; setuptools<81 needed on Python 3.12). OWNER MUST LISTEN FIRST: those
  readings are review_status "draft" with "hold": "new voice: owner listens first". Set them back to "staged" only
  after his "yes". tools/listen_report.py (fix-voices.yml report_only) checks clarity.
- Owner rejected: unified page redesign. Logo proposal (3 options) sent, no choice yet.
- Owner wants a new series in the style of a screen recording he sent (simple animation, simple characters) for
  "our Armenian series" — the upload failed (disk full); waiting for it again.
- Disk in the work machine filled up (repo .git 4–7 GB): clean caches and run git gc when space is low.
- Mila & Leo: owner fixed the slot — 15:00 every day is Mila & Leo, mornings (10:30) are Ani. Lessons 2–4 (mila-mitten,
  mila-dinosaur, mila-chocolate) added: sheets → reading-sheets.yml (branch-only cutter), voice chatterbox:sonia, queue
  Nov 24/25/26 15:00 + stories 15:30. Mitten rendered locally and pushed to media; the other two by render-ahead.
  Lesson 5 (night sky) sheet still to come; lessons 6–10 need sheets.

## 2026-11-24 (evening) — ONE FORMAT (owner's decision)
- The page publishes only "Daily reading" reels + their story 30 min later:
  10:30 Ani (story 11:00), 15:00 Mila & Leo (story 15:30). Planned next: 20:30 mixed stories with new heroes
  (21 picture prompts given to the owner on Nov 24; he sends sheets; write texts that match the panels).
- One voice for every reading: chatterbox:sonia. The 6 Ani readings that were en-GB-SoniaNeural were re-voiced.
- queue.json: removed 74 staged/draft items (feelstory, classics reels + carousels, cities, routine, picstory,
  story-image and their stories). Mila lessons moved to Nov 25 – Dec 4 at 15:00 (mitten media copied in the media repo).
- Unused renderers and plan scripts moved to archive/ (see archive/README.md). Data files stay (checks read them).
- Paused workflows (Actions → Disable): Sharpen panels, Voice trial, Voice comparison, Fix voices,
  Render in the cloud, Make a story reel, Say it right voices.
- reading-sheets.yml now runs on main too and starts "Make voices" itself; render-ahead also runs after a merge
  that changes queue.json and no longer stops at the first broken post.
- English check ignores EN_UNPAIRED_QUOTES and RUDE_SARCASTIC (false positives on dialogue lines).
- PRs #24/#25 are replaced by the one-format PR. Branches classics-feel, sayit-sample, red-mitten-voice: not used.

## 2026-11-24 (night) — purge: only Ani and Mila & Leo remain
- Owner: delete everything that is not the Ani / Mila & Leo reading format. No archive.
- Deleted: all other series' renderers, templates, data, assets (feelstory, storyvideo, classics, cities, words10,
  dialogues, phrasal, routine, talk, cards, sounds, lessons, opposites, picstory, motion, minute, emoji…), carousels/,
  stories/, books/, covers/, archive/, unused tools and publish scripts, and the workflows Fix voices, Sharpen panels,
  Render in the cloud, Make a story reel, Telegram helper, Voice comparison, Voice trial. Git history still has them.
- make_voice.py, voice_finish.py, check_voice.py, check_english.py, check_level.py, system_check.py and check_code.py
  now look at reels/data/reading.json / assets/reading only. IPA check removed (readings have no IPA).
- Times (PR #27): Ani 10:30 weekdays, 11:00 weekend; Mila 20:30; stories +30 min.
- Story cards: new 'ani' and 'mila' styles in reels/story_card.js (picked from the picture path). The owner is
  choosing between 3 more design directions.

## 2026-11-24 (late) — voices
- All 16 British voices compared on the same text (faster-whisper medium.en: same word error for all; edge voices
  clearest, chatterbox most natural). Kept 4 voices only: chatterbox:sonia (the page's voice for every reading),
  en-GB-SoniaNeural, en-GB-LibbyNeural, en-GB-RyanNeural (backups). Kokoro and the other voices removed from
  voices/make_voice.py; make_voice and check_code refuse any other voice.
- Story cards: Ani = 'ani-b' (film still), Mila = 'mila-c' (gold), chosen by the owner (PR #29).

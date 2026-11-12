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

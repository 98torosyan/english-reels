// Weekly listening lesson for YouTube: 3-4 daily readings joined into one calm 16:9 video.
// For each story: title, the words to know (with Armenian), then the story read aloud with the spoken word lit.
// Usage: node reels/render_lesson.js <lesson-id>
//   RENDER_SCALE=2 (default here) gives 3840x2160; RENDER_SCALE=1 gives a 1920x1080 preview.
process.env.VIDEO_SIZE = '1920x1080';
if (!process.env.RENDER_SCALE) process.env.RENDER_SCALE = '2';
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const READING = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/reading.json'), 'utf8')).stories;
const LESSONS = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/lessons.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH;
const FPS = Number(process.env.LESSON_FPS || 30);
const r3 = (x) => Number(x.toFixed(3));
const INTRO = 7;
const TITLE = 4;
const WORDS = 9;
const AFTER = 2.4;
const OUTRO = 9;

const pictures = (id) => { const out = []; for (let k = 1; fs.existsSync(path.join(utils.ROOT, 'assets/reading', id, `${k}.jpg`)); k += 1) out.push(`assets/reading/${id}/${k}.jpg`); return out; };

function clip(st) {
  const dir = path.join(utils.ROOT, 'assets/reading', st.id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, 'p.json'), 'utf8'));
  if (timing.text !== st.en) throw new Error(`${st.id}: the voice is for a different text; re-run the voices.`);
  const start = timing.words[0][0]; const end = timing.words.at(-1)[1];
  if (timing.words.length !== st.en.split(' ').length) throw new Error(`${st.id}: word timings do not match the text.`);
  return { file: path.join(dir, 'p.mp3'), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]) };
}

// when each picture appears: at the word given in pic_words, else evenly over the sentences
function picTimes(st, words, n) {
  if (n < 2) return [0];
  let at = st.pic_words;
  if (!at || at.length !== n) {
    const w = st.en.split(' '); const starts = [0, ...w.slice(0, -1).flatMap((x, i) => (/[.!?]'?$/.test(x) ? [i + 1] : []))];
    at = Array.from({ length: n }, (_, k) => starts[Math.floor((k * starts.length) / n)]);
  }
  return at.map((j, k) => (k === 0 ? 0 : r3(words[Math.min(j, words.length - 1)][0] - 0.4)));
}

// The whole lesson as a list of segments with absolute times (seconds).
function timeline(lesson) {
  const segs = [{ kind: 'intro', at: 0, len: INTRO }];
  const plays = [];
  let t = INTRO;
  lesson.stories.forEach((id) => {
    const st = READING.find((s) => s.id === id);
    if (!st) throw new Error(`Unknown reading: ${id}`);
    const c = clip(st);
    const pics = pictures(id);
    if (!pics.length) throw new Error(`${id}: no pictures`);
    segs.push({ kind: 'title', at: t, len: TITLE, id }); t += TITLE;
    const words = (LESSONS.words || {})[id] || [];
    if (words.length) { segs.push({ kind: 'words', at: t, len: WORDS, id, words }); t += WORDS; }
    const lead = 1.2;
    const w = c.words.map(([a, b]) => [r3(a + lead), r3(b + lead)]);
    plays.push({ at: t + lead, clip: c });
    segs.push({ kind: 'read', at: t, len: r3(lead + c.len + AFTER), id, words: w, pics, picAt: picTimes(st, w, pics.length) });
    t = r3(t + lead + c.len + AFTER);
  });
  segs.push({ kind: 'outro', at: t, len: OUTRO });
  t += OUTRO;
  return { segs, plays, total: r3(t) };
}

function voiceTrack(T, out) {
  const args = ['-y', '-hide_banner', '-loglevel', 'error'];
  T.plays.forEach((p) => args.push('-i', p.clip.file));
  const chains = T.plays.map((p, i) => {
    const from = Math.max(0, p.clip.start - 0.06);
    const ms = Math.round((p.at - (p.clip.start - from)) * 1000);
    return `[${i}:a]aresample=48000,atrim=${from.toFixed(3)}:${(p.clip.end + 0.3).toFixed(3)},asetpts=PTS-STARTPTS,afade=t=out:st=${(p.clip.end - from + 0.1).toFixed(3)}:d=0.2,adelay=${ms}|${ms}[v${i}]`;
  });
  args.push('-filter_complex', `${chains.join(';')};${T.plays.map((_, i) => `[v${i}]`).join('')}amix=inputs=${T.plays.length}:normalize=0,apad=whole_dur=${T.total}[a]`,
    '-map', '[a]', '-ac', '2', '-c:a', 'pcm_s16le', out);
  const r = spawnSync(utils.FFmpeg, args, { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`Voice track failed: ${r.stderr}`);
}

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const curly = (s) => s.replace(/(^|[\s(])'/g, '$1‘').replace(/'/g, '’');

function page(baseUrl, lesson, T) {
  const f = `${baseUrl}/node_modules/@fontsource-variable`;
  const stories = Object.fromEntries(lesson.stories.map((id) => [id, READING.find((s) => s.id === id)]));
  const data = { segs: T.segs, total: T.total, stories: Object.fromEntries(Object.entries(stories).map(([id, s]) => [id, {
    title: curly(s.title), title_hy: s.title_hy, level: s.level, words: curly(s.en).split(' ') }])) };
  const imgs = [...new Set(T.segs.flatMap((s) => s.pics || []).concat(lesson.stories.map((id) => pictures(id)[0])))];
  return `<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>
@font-face{font-family:L;src:url(${f}/literata/files/literata-latin-wght-normal.woff2);font-weight:200 900}
@font-face{font-family:L;font-style:italic;src:url(${f}/literata/files/literata-latin-wght-italic.woff2);font-weight:200 900}
@font-face{font-family:I;src:url(${f}/inter/files/inter-latin-wght-normal.woff2);font-weight:100 900}
@font-face{font-family:A;src:url(${f}/noto-sans-armenian/files/noto-sans-armenian-armenian-wght-normal.woff2);font-weight:100 900}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;background:#0E0B1D}
#bg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 70% at 50% 45%,#2A1E4D 0%,#17183A 55%,#0E0B1D 100%)}
.seg{position:absolute;inset:0;opacity:0}
.c{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);text-align:center;color:#fff;width:1500px}
.mark{width:96px;height:96px;display:block;margin:0 auto 18px}
.h1{font:600 104px/1.08 L;letter-spacing:.5px}
.h2{font:600 84px/1.1 L}
.o{display:flex;align-items:center;justify-content:center;gap:16px;margin:30px auto 26px;width:520px}
.o i{flex:1;height:2px;background:linear-gradient(90deg,transparent,#E9C46A,transparent)}.o b{width:13px;height:13px;background:#E9C46A;transform:rotate(45deg)}
.lead{font:italic 400 44px/1.35 L;color:#F2E7D3}
.cap{margin-top:22px;font:500 26px I;letter-spacing:8px;color:#A891F7}
.hy{margin-top:16px;font:400 32px/1.4 A;color:#C9C2E3}
.glow{position:absolute;left:50%;top:50%;width:1400px;height:800px;transform:translate(-50%,-50%);background:radial-gradient(closest-side,rgba(106,73,226,.32),transparent)}
.tpic{position:absolute;left:50%;top:50%;width:1300px;height:1300px;transform:translate(-50%,-50%);background-size:cover;background-position:center;opacity:.42;
 -webkit-mask:radial-gradient(closest-side,#000 30%,transparent 100%)}
.words{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:1300px}
.words .t{text-align:center;font:italic 400 40px L;color:#E9C46A;margin-bottom:46px}
.row{display:flex;align-items:baseline;justify-content:space-between;padding:20px 40px;border-bottom:1px solid rgba(168,145,247,.22);opacity:0}
.row .en{font:600 54px L;color:#fff}.row .am{font:400 40px A;color:#C9C2E3}
.pic{position:absolute;left:40px;top:50%;width:900px;height:900px;margin-top:-450px;overflow:hidden;
 -webkit-mask:radial-gradient(closest-side,#000 62%,transparent 100%)}
.pic div{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0}
.text{position:absolute;left:980px;right:120px;top:50%;transform:translateY(-50%)}
.text .st{font:600 52px/1.15 L;color:#fff}.text .sh{font:400 28px A;color:#A891F7;margin-top:10px}
.text .o{margin:28px 0 30px;width:300px;justify-content:flex-start}
.para{font:400 38px/1.6 L;color:rgba(255,255,255,.42)}
.para span{transition:none;border-radius:8px;padding:0 3px;margin:0 -3px}
.para span.r{color:#fff}.para span.n{color:#17183A;background:#E9C46A}
</style></head><body><div id="bg"></div><div id="stage"></div>
<div style="position:absolute;left:0;top:0;width:1px;height:1px;overflow:hidden;opacity:0">${imgs.map((u) => `<img style="width:1px;height:1px" src="${baseUrl}/${u}">`).join('')}</div>
<script>
const D = ${JSON.stringify(data)};
const L = ${JSON.stringify({ title: curly(lesson.title), title_hy: lesson.title_hy, level: lesson.level, count: lesson.stories.length })};
const BASE = ${JSON.stringify(baseUrl)};
const FADE = 0.7;
const stage = document.getElementById('stage');
const el = [];
const ease = (x) => x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x);
const NUM = ['', 'one', 'two', 'three', 'four', 'five'];
D.segs.forEach((s) => {
  const d = document.createElement('div'); d.className = 'seg';
  if (s.kind === 'intro') d.innerHTML = '<div class=glow></div><div class=c><img class=mark src="' + BASE + '/assets/logo-mark.svg"><div class=h1>' + L.title + '</div><div class=o><i></i><b></b><i></i></div>' +
    '<div class=lead>A listening lesson with ' + NUM[L.count] + ' easy English stories</div><div class=cap>LISTEN · READ · LEARN · ' + L.level + '</div><div class=hy>' + L.title_hy + ' · լսենք ու կարդանք միասին</div></div>';
  if (s.kind === 'title') { const st = D.stories[s.id];
    d.innerHTML = '<div class=tpic style="background-image:url(' + BASE + '/assets/reading/' + s.id + '/1.jpg)"></div><div class=c><div class=h2>' + st.title + '</div><div class=o><i></i><b></b><i></i></div><div class=hy>' + st.title_hy + '</div></div>'; }
  if (s.kind === 'words') d.innerHTML = '<div class=words><div class=t>Words to know</div>' + s.words.map((w) => '<div class=row><span class=en>' + w[0] + '</span><span class=am>' + w[1] + '</span></div>').join('') + '</div>';
  if (s.kind === 'read') { const st = D.stories[s.id];
    d.innerHTML = '<div class=pic>' + s.pics.map((p) => '<div style="background-image:url(' + BASE + '/' + p + ')"></div>').join('') + '</div>' +
      '<div class=text><div class=st>' + st.title + '</div><div class=sh>' + st.title_hy + '</div><div class=o><i></i><b></b><i></i></div><div class=para>' + st.words.map((w) => '<span>' + w + '</span>').join(' ') + '</div></div>'; }
  if (s.kind === 'outro') d.innerHTML = '<div class=glow></div><div class=c><img class=mark src="' + BASE + '/assets/logo-mark.svg"><div class=h2>Thank you for listening!</div><div class=o><i></i><b></b><i></i></div>' +
    '<div class=lead>A new story every day. Subscribe and read with us.</div><div class=cap>98TOROSYAN.GITHUB.IO/ENGLISH-READING</div><div class=hy>Շնորհակալություն, որ լսեցիք։ Ամեն օր՝ նոր պատմություն։</div></div>';
  stage.appendChild(d); el.push(d);
});
window.fit = () => { document.querySelectorAll('.para').forEach((p) => { let s = 38; const box = p.parentElement;
  while (box.getBoundingClientRect().height > 960 && s > 28) { s -= 1; p.style.fontSize = s + 'px'; } }); };
window.seek = (t) => {
  D.segs.forEach((s, i) => {
    const d = el[i]; const lt = t - s.at;
    const a = Math.min(ease(lt / FADE), ease((s.len - lt) / FADE));
    d.style.opacity = lt < 0 || lt > s.len ? 0 : a;
    if (d.style.opacity === '0') return;
    const p = lt / s.len;
    if (s.kind === 'intro' || s.kind === 'outro') d.querySelector('.c').style.transform = 'translate(-50%,calc(-50% + ' + (12 * (1 - ease(lt / 1.6))) + 'px))';
    if (s.kind === 'title') d.querySelector('.tpic').style.transform = 'translate(-50%,-50%) scale(' + (1.04 + 0.05 * p) + ')';
    if (s.kind === 'words') d.querySelectorAll('.row').forEach((r, k) => { const v = ease((lt - 0.6 - k * 0.45) / 0.5); r.style.opacity = v; r.style.transform = 'translateY(' + (14 * (1 - v)) + 'px)'; });
    if (s.kind === 'read') {
      const pics = d.querySelectorAll('.pic div');
      pics.forEach((pd, k) => { const on = s.picAt[k] - s.at; const nx = k + 1 < pics.length ? s.picAt[k + 1] - s.at : 1e9;
        const v = Math.min(k === 0 ? 1 : ease((lt - on) / 0.9), ease((nx + 0.9 - lt) / 0.9));
        pd.style.opacity = lt < on && k > 0 ? 0 : v; pd.style.transform = 'scale(' + (1.03 + 0.04 * Math.min(1, Math.max(0, (lt - on) / 12))) + ')'; });
      const spans = d.querySelectorAll('.para span'); const at = t;
      spans.forEach((sp, k) => { const [a0, b0] = s.words[k]; const w0 = a0 + s.at; const nxt = k + 1 < s.words.length ? s.words[k + 1][0] + s.at : b0 + s.at + 0.3;
        sp.className = at >= w0 && at < Math.max(b0 + s.at, nxt) ? 'n' : at >= w0 ? 'r' : ''; });
    }
  });
};
</script></body></html>`;
}

async function renderLesson(browser, baseUrl, lesson) {
  const T = timeline(lesson);
  const name = `lesson-${lesson.id}`;
  const output = utils.OUTPUT; const work = path.join(utils.ROOT, '.render-work');
  utils.ensureDirectory(work); utils.ensureDirectory(output);
  const frames = path.join(output, `.frames-${name}`);
  const videoPath = path.join(output, `${name}.mp4`); const posterPath = path.join(output, `${name}.png`);
  const htmlPath = path.join(work, `${name}.html`);
  fs.writeFileSync(htmlPath, page(baseUrl, lesson, T), 'utf8');
  const pg = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: utils.DPR });
  const errors = await utils.preparePage(pg, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1920, 1080);
  await pg.evaluate(() => Promise.all([document.fonts.load('600 52px L', 'Ab'), document.fonts.load('italic 40px L', 'Ab'), document.fonts.load('32px A', 'Հայ'),
    document.fonts.load('500 26px I', 'AB')]).then(() => document.fonts.ready));
  await pg.evaluate(() => Promise.all([...document.images].map((i) => (i.complete ? 0 : new Promise((r) => { i.onload = r; i.onerror = r; })))));
  await pg.evaluate(() => { window.fit(); });
  const check = await pg.evaluate(() => ({
    armenian: document.fonts.check('32px A', 'Հայ'),
    tall: Math.max(...[...document.querySelectorAll('.text')].map((x) => x.getBoundingClientRect().height)),
    wide: Math.max(...[...document.querySelectorAll('.c,.words')].map((x) => x.scrollWidth)),
    imgs: [...document.images].filter((i) => !i.naturalWidth).length,
  }));
  console.log(`${name}: ${JSON.stringify(check)} total ${T.total}s`);
  if (!check.armenian || check.tall > 980 || check.imgs) throw new Error(`${name}: layout check failed`);
  if (process.env.STILLS) {   // quick look: STILLS=3,12.5,40 saves those moments as pictures and stops
    for (const at of process.env.STILLS.split(',').map(Number)) {
      await pg.evaluate((x) => window.seek(x), at);
      await pg.screenshot({ path: path.join(output, `${name}-at-${at}.jpg`), type: 'jpeg', quality: 88 });
    }
    await pg.close(); return { stills: true, total: T.total };
  }
  const have = fs.existsSync(frames) ? fs.readdirSync(frames).length : 0;
  if (process.env.REUSE_FRAMES === '1' && have >= Math.ceil(T.total * FPS)) console.log(`  using the ${have} frames already rendered`);
  else await utils.renderFrames(pg, T.total, frames, posterPath, INTRO + 1, FPS);
  if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
  await pg.close();
  const voice = path.join(work, `${name}.wav`);
  voiceTrack(T, voice);
  if (lesson.music && !process.env.MUSIC_TRACK) process.env.MUSIC_TRACK = path.join(utils.ROOT, 'music', lesson.music);
  utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, []);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  fs.writeFileSync(path.join(output, `${name}.json`), JSON.stringify({ id: lesson.id, chapters: chapters(lesson, T), info }, null, 2));
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info };
}

// YouTube chapters: start of each story (its title card) plus the intro and the end
function chapters(lesson, T) {
  const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  const out = [['0:00', 'Welcome']];
  T.segs.filter((s) => s.kind === 'title').forEach((s) => out.push([mmss(s.at), READING.find((r) => r.id === s.id).title]));
  out.push([mmss(T.segs.at(-1).at), 'Goodbye']);
  return out;
}

async function main() {
  const id = process.argv[2];
  const lesson = LESSONS.lessons.find((x) => x.id === id);
  if (!lesson) throw new Error(`Unknown lesson: ${id}`);
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Set CHROME_PATH.');
  const { server, baseUrl } = await utils.startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    await renderLesson(browser, baseUrl, lesson);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
module.exports = { renderLesson, timeline, chapters };

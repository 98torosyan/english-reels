// "My day": a 3x3 storyboard becomes a reel. One picture per sentence, the sentence voiced, the key phrase highlighted,
// a pause to repeat; each scene sits on a blurred background made from its own picture.
// Usage: node reels/render_routine.js <story-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/routine.json'), 'utf8'));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));
const PALETTE = ['#D9822B', '#2E86AB', '#C0397A', '#3E9E5F', '#6A49E2'];

function clip(id, key, text) {
  const dir = path.join(utils.ROOT, 'assets', 'routine', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `v${key}.json`), 'utf8'));
  if (timing.text !== text) throw new Error(`${id}/v${key}: audio is for a different text; re-run the voices.`);
  const start = timing.words[0][0]; const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `v${key}.mp3`), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]) };
}

function timeline(st) {
  const plays = []; const scenes = []; const words = [];
  const q = clip(st.id, 'q', st.question);
  plays.push({ at: 1.5, clip: q });   // after the music has settled (an early voice makes the loudness filter overshoot)
  let t = 1.5 + q.len + 1.1;
  st.lines.forEach((line, n) => {
    const c = clip(st.id, String(n), line.replace(/[[\]]/g, ''));
    const v0 = t + 0.55;
    plays.push({ at: r3(v0), clip: c });
    const end = v0 + c.len + Math.max(1.4, c.len * 0.9 + 0.5);   // time to repeat
    scenes.push({ at: r3(t), v0: r3(v0), v1: r3(v0 + c.len), end: r3(end) });
    words.push(c.words.map(([a, b]) => [r3(a + v0), r3(b + v0)]));
    t = end;
  });
  return { plays, scenes, words, total: r3(t + 2.9) };
}

function voiceTrack(T, out) {
  const args = ['-y', '-hide_banner', '-loglevel', 'error'];
  T.plays.forEach((p) => args.push('-i', p.clip.file));
  const chains = T.plays.map((p, i) => {
    const from = Math.max(0, p.clip.start - 0.06); const ms = Math.round((p.at - (p.clip.start - from)) * 1000);
    return `[${i}:a]aresample=48000,atrim=${from.toFixed(3)}:${(p.clip.end + 0.3).toFixed(3)},asetpts=PTS-STARTPTS,afade=t=out:st=${(p.clip.end - from + 0.1).toFixed(3)}:d=0.2,adelay=${ms}|${ms}[v${i}]`;
  });
  args.push('-filter_complex', `${chains.join(';')};${T.plays.map((_, i) => `[v${i}]`).join('')}amix=inputs=${T.plays.length}:normalize=0,apad=whole_dur=${T.total}[a]`,
    '-map', '[a]', '-ac', '2', '-c:a', 'pcm_s16le', out);
  const r = spawnSync(utils.FFmpeg, args, { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`Voice track failed: ${r.stderr}`);
}

async function render(browser, baseUrl, st) {
  const T = timeline(st);
  const name = `routine-${st.id}`;
  const frames = path.join(utils.OUTPUT, `.frames-${name}`);
  const videoPath = path.join(utils.OUTPUT, `${name}.mp4`); const posterPath = path.join(utils.OUTPUT, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work'); utils.ensureDirectory(work); utils.ensureDirectory(utils.OUTPUT);
  const html = utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'routine.html'), 'utf8'), baseUrl)
    .replaceAll('__LITERATA_ITALIC__', `${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-italic.woff2`)
    .replaceAll('__GSAP__', `${baseUrl}/node_modules/gsap/dist`);
  const htmlPath = path.join(work, 'routine.html'); fs.writeFileSync(htmlPath, html, 'utf8');
  const pics = st.lines.map((_, i) => `${baseUrl}/assets/routine/${st.id}/${i + 1}.jpg`);
  const data = { ...st, pics, color: PALETTE[(st.number - 1) % PALETTE.length] };
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  const plain = { ...T, plays: [] };
  await page.evaluate(({ d, t }) => { window.configure(d, t); window.seek(0); }, { d: data, t: plain });
  await page.evaluate(() => Promise.all([document.fonts.load('40px NotoArmenian', 'Աբգ'), document.fonts.load('700 48px Literata', 'Ab'),
    document.fonts.load('italic 700 48px Literata', 'Ab'), ...[...document.images].map((i) => i.decode().catch(() => null))]).then(() => document.fonts.ready));
  await page.evaluate(() => { window.fit(); window.seek(0); });
  // every sentence must fit its card
  const over = await page.evaluate((t) => {
    const bad = [];
    t.scenes.forEach((s, i) => { window.seek(s.v1 + 0.2); const c = document.getElementById('card').getBoundingClientRect(); const e = document.getElementById('say').getBoundingClientRect();
      const en = document.getElementById('en'); if (e.bottom > 620 || en.scrollWidth > en.clientWidth + 1) bad.push(i); });
    return bad;
  }, plain);
  if (over.length) throw new Error(`${name}: sentence too long for the card: ${over}`);
  await utils.renderFrames(page, T.total, frames, posterPath, T.scenes[0].at - 0.7, FPS);
  if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
  await page.close();
  const voice = path.join(work, `${name}.wav`); voiceTrack(T, voice);
  const sfx = [{ file: 'sfx-whoosh.wav', at: 0.2, gain: 0.25 }, ...T.scenes.map((s) => ({ file: 'sfx-whoosh.wav', at: s.at, gain: 0.12 })),
    { file: 'sfx-whoosh.wav', at: T.total - 2.6, gain: 0.25 }];
  utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info, thumbOffsetMs: Math.round((T.scenes[0].at - 0.7) * 1000) };
}

async function main() {
  const st = DATA.stories.find((x) => x.id === process.argv[2]);
  if (!st) throw new Error(`Unknown story: ${process.argv[2]}`);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try { await render(browser, baseUrl, st); } finally { await browser.close(); server.close(); }
}
if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
module.exports = { render, timeline };

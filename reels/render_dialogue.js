// Everyday English: two-speaker dialogue reel. Part 1 listen, part 2 the viewer speaks B's lines.
// Usage: node reels/render_dialogue.js <dialogue-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/dialogues.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));

function lineClip(id, n, text) {
  const dir = path.join(utils.ROOT, 'assets', 'dialogues', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `${n}.json`), 'utf8'));
  if (timing.text !== text) throw new Error(`${id}/${n}: audio is for a different text; re-run the voices.`);
  const start = timing.words[0][0];
  const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `${n}.mp3`), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]) };
}

function timeline(d) {
  const clips = d.lines.map((l, n) => lineClip(d.id, n, l.en));
  const bubbles = [];
  const plays = [];
  let t = 2.0;
  d.lines.forEach((l, n) => {
    const c = clips[n]; const at = t + 0.35;
    bubbles.push({ set: 1, s: l.s, en: l.en, hy: l.hy, appear: r3(t), words: c.words.map(([a, b]) => [r3(a + at), r3(b + at)]) });
    plays.push({ at: r3(at), clip: c });
    t = at + c.len + 0.7;
  });
  const p1End = t;
  const p2 = p1End + 2.9;
  t = p2 + 0.2;
  d.lines.forEach((l, n) => {
    const c = clips[n]; const at = t + 0.35;
    if (l.s === 'B') {
      const pause = c.len * 1.2 + 1.1;
      bubbles.push({ set: 2, s: l.s, en: l.en, hy: l.hy, appear: r3(t), words: null, pause: [r3(at), r3(at + pause)] });
      t = at + pause + 0.6;
    } else {
      bubbles.push({ set: 2, s: l.s, en: l.en, hy: l.hy, appear: r3(t), words: c.words.map(([a, b]) => [r3(a + at), r3(b + at)]) });
      plays.push({ at: r3(at), clip: c });
      t = at + c.len + 0.7;
    }
  });
  const total = t + 2.6;
  return { bubbles, plays, p1End: r3(p1End), p2: r3(p2), total: r3(total) };
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

async function renderDialogue(browser, baseUrl, d) {
  const T = timeline(d);
  const name = `dialogue-${d.id}`;
  const output = utils.OUTPUT;
  const frames = path.join(output, `.frames-${name}`);
  const videoPath = path.join(output, `${name}.mp4`);
  const posterPath = path.join(output, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work');
  utils.ensureDirectory(work); utils.ensureDirectory(output);
  const html = utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'dialogue.html'), 'utf8'), baseUrl);
  const htmlPath = path.join(work, 'dialogue.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  await page.evaluate(() => Promise.all([document.fonts.load('40px NotoArmenian', 'Աբգ'), document.fonts.load('600 48px Literata', 'Ab'), document.fonts.load('800 26px Inter', 'Ab')]).then(() => document.fonts.ready));
  const plain = { ...T, plays: [] };
  await page.evaluate(({ d: data, t }) => { window.configure(data, t); window.seek(0); }, { d, t: plain });
  const check = await page.evaluate(() => {
    const hl = document.getElementById('headline');
    return {
      armenian: document.fonts.check('32px NotoArmenian', 'Հայ'),
      headlineFits: hl.scrollWidth <= 916,
      wide: [...document.querySelectorAll('.bubble')].filter((b) => b.getBoundingClientRect().width > 957).length,
      roles: document.getElementById('roles').scrollWidth <= 960,
    };
  });
  console.log(`${name}: ${JSON.stringify(check)} total ${T.total}s`);
  if (!check.armenian || !check.headlineFits || check.wide || !check.roles) throw new Error(`${name}: layout check failed`);
  await utils.renderFrames(page, T.total, frames, posterPath, Math.min(T.p1End - 1, 7), FPS);
  if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
  await page.close();
  const voice = path.join(work, `${name}.wav`);
  voiceTrack(T, voice);
  const sfx = [{ file: 'sfx-whoosh.wav', at: 0.25, gain: 0.35 },
    ...T.bubbles.map((b) => ({ file: 'sfx-pop.wav', at: b.appear, gain: 0.18 })),
    { file: 'sfx-ding.wav', at: T.p1End + 0.3, gain: 0.4 },
    { file: 'sfx-whoosh.wav', at: T.total - 2.2, gain: 0.3 }];
  utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info, thumbOffsetMs: Math.round(Math.min(T.p1End - 1, 7) * 1000) };
}

async function main() {
  const id = process.argv[2];
  const d = DATA.dialogues.find((x) => x.id === id);
  if (!d) throw new Error(`Unknown dialogue: ${id}`);
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Set CHROME_PATH.');
  const { server, baseUrl } = await utils.startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    const r = await renderDialogue(browser, baseUrl, d);
    console.log(r.videoPath);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
module.exports = { renderDialogue, timeline };

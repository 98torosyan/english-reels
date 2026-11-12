// Weekly review: the week's words one by one; Armenian first, a 3-second guess, then the English word is revealed and voiced.
// Usage: node reels/render_review.js <review-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/reviews.json'), 'utf8'));
const W10 = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/words10.json'), 'utf8')).lists.map((l) => [l.id, l]));
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));
// one accent per day, from the brand palette, so neighbouring posts never look the same
const PALETTE = ['#B9790B', '#1C8AA3', '#B23F78', '#3E5FD9', '#2E9E6A', '#6A49E2'];
const withColor = (r) => ({ ...r, level: 'A1–B1', color: PALETTE[(r.number + 4) % PALETTE.length],
  words: r.picks.map(([lid, n]) => ({ ...W10[lid].words[n], list: lid, n })) });

function clip(id, n, text) {
  const dir = path.join(utils.ROOT, 'assets', 'words10', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `${n}.json`), 'utf8'));
  if (timing.text !== text) throw new Error(`${id}/${n}: audio is for a different word; re-run the voices.`);
  const start = timing.words[0][0];
  const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `${n}.mp3`), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]) };
}

// Each word: card in, 3-second guess, reveal + voice, a short beat, next.
function timeline(r) {
  const plays = []; const items = [];
  let t = 2.0;
  r.words.forEach((w) => {
    const c = clip(w.list, w.n, `${w.en}.`);
    const ask = t + 0.7; const reveal = ask + 3.0; const vAt = reveal + 0.3;
    plays.push({ at: r3(vAt), clip: c });
    const end = vAt + c.len + 1.5;
    items.push({ at: r3(t), ask: r3(ask), reveal: r3(reveal), end: r3(end) });
    t = end + 0.1;
  });
  return { plays, items, total: r3(t + 3.2) };
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

async function renderReview(browser, baseUrl, list0) {
  const list = withColor(list0);
  const T = timeline(list);
  const name = `review-${list.id}`;
  const output = utils.OUTPUT;
  const frames = path.join(output, `.frames-${name}`);
  const videoPath = path.join(output, `${name}.mp4`);
  const posterPath = path.join(output, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work');
  utils.ensureDirectory(work); utils.ensureDirectory(output);
  const fonts = `${baseUrl}/node_modules/@fontsource-variable/inter/files`;
  const html = utils.paperTheme(utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'review.html'), 'utf8'), baseUrl), 'vocabulary')
    .replaceAll('__INTER_EXT_FONT__', `${fonts}/inter-latin-ext-wght-normal.woff2`)
    .replaceAll('__INTER_GREEK_FONT__', `${fonts}/inter-greek-wght-normal.woff2`);
  const htmlPath = path.join(work, 'review.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  const plain = { ...T, plays: [] };
  await page.evaluate(({ d, t }) => { window.configure(d, t); window.seek(1.9); }, { d: list, t: plain });
  await page.evaluate(() => Promise.all([document.fonts.load('40px NotoArmenian', 'Աբգ'), document.fonts.load('700 48px Literata', 'Ab'),
    document.fonts.load('30px IPA', 'ʃɪiːθðɜɔæʌɒəʊɡŋ')]).then(() => document.fonts.ready));
  await page.evaluate(() => { window.seek(0); window.fit(); window.seek(1.9); });
  const check = await page.evaluate(() => {
    const over = [...document.querySelectorAll('.q')].filter((q) => q.querySelector('.qen').scrollWidth > 880 || q.querySelector('.qhy').scrollHeight > 240).map((q) => q.textContent.slice(0, 30));
    return { armenian: document.fonts.check('32px NotoArmenian', 'Հայ'), ipa: document.fonts.check('30px IPA', 'ʃɪθ'), over };
  });
  console.log(`${name}: ${JSON.stringify(check)} total ${T.total}s`);
  if (!check.armenian || !check.ipa || check.over.length) throw new Error(`${name}: layout check failed`);
  await utils.renderFrames(page, T.total, frames, posterPath, T.items[0].ask + 1.0, FPS);
  if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
  await page.close();
  const voice = path.join(work, `${name}.wav`);
  voiceTrack(T, voice);
  const sfx = [{ file: 'sfx-whoosh.wav', at: 0.25, gain: 0.3 }, ...T.items.flatMap((r) => [{ file: 'sfx-pop.wav', at: r.at, gain: 0.12 }, ...[3, 2, 1].map((k) => ({ file: 'sfx-tick.wav', at: r.reveal - k, gain: 0.35 })), { file: 'sfx-ding.wav', at: r.reveal, gain: 0.4 }]),
    { file: 'sfx-whoosh.wav', at: T.total - 2.2, gain: 0.3 }];
  utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info };
}

async function main() {
  const id = process.argv[2];
  const list = DATA.reviews.find((x) => x.id === id);
  if (!list) throw new Error(`Unknown list: ${id}`);
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Set CHROME_PATH.');
  const { server, baseUrl } = await utils.startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    const r = await renderReview(browser, baseUrl, list);
    console.log(r.videoPath);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
module.exports = { renderReview, timeline };

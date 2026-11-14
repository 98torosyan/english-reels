// 10 words: one theme, ten words on screen; each English word is voiced, the viewer repeats.
// Usage: node reels/render_words10.js <list-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/words10.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));
// one accent per day, from the brand palette, so neighbouring posts never look the same
const PALETTE = ['#B9790B', '#1C8AA3', '#B23F78', '#3E5FD9', '#2E9E6A', '#6A49E2'];
const ICONS = path.join(utils.ROOT, 'node_modules/@phosphor-icons/core/assets/duotone');
const iconSvg = (name) => (name ? fs.readFileSync(path.join(ICONS, `${name}-duotone.svg`), 'utf8') : null);
// painted pictures for a list (assets/words10_art/<id>/<n>.png) replace the line icons when they exist
const art = (id, n) => { const f = path.join(utils.ROOT, 'assets/words10_art', id, `${n}.png`); return fs.existsSync(f) ? `data:image/png;base64,${fs.readFileSync(f).toString('base64')}` : null; };
const withColor = (list) => ({ ...list, color: PALETTE[(list.number - 1) % PALETTE.length],
  words: list.words.map((w, n) => ({ ...w, img: art(list.id, n), svg: iconSvg(w.icon) })) });

function clip(id, n, text) {
  const dir = path.join(utils.ROOT, 'assets', 'words10', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `${n}.json`), 'utf8'));
  if (timing.text !== text) throw new Error(`${id}/${n}: audio is for a different word; re-run the voices.`);
  const start = timing.words[0][0];
  const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `${n}.mp3`), start, end, len: end - start };
}

// List slides in, then each row: highlight, word, a pause to repeat it.
function timeline(list) {
  const plays = []; const rows = [];
  let t = 2.0;
  list.words.forEach((w, n) => {
    const c = clip(list.id, n, `${w.en}.`);
    const at = t + 0.3;
    plays.push({ at: r3(at), clip: c });
    const end = at + c.len + Math.max(1.5, c.len * 1.3 + 0.8);
    rows.push({ at: r3(t), v0: r3(at), v1: r3(at + c.len), end: r3(end) });
    t = end + 0.15;
  });
  const total = t + 2.8;
  return { plays, rows, total: r3(total) };
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

async function renderWords10(browser, baseUrl, list0) {
  const list = withColor(list0);
  const T = timeline(list);
  const name = `words10-${list.id}`;
  const output = utils.OUTPUT;
  const frames = path.join(output, `.frames-${name}`);
  const videoPath = path.join(output, `${name}.mp4`);
  const posterPath = path.join(output, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work');
  utils.ensureDirectory(work); utils.ensureDirectory(output);
  const fonts = `${baseUrl}/node_modules/@fontsource-variable/inter/files`;
  const html = utils.paperTheme(utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'words10.html'), 'utf8'), baseUrl), 'vocabulary')
    .replaceAll('__INTER_EXT_FONT__', `${fonts}/inter-latin-ext-wght-normal.woff2`)
    .replaceAll('__INTER_GREEK_FONT__', `${fonts}/inter-greek-wght-normal.woff2`)
    .replaceAll('__GSAP__', `${baseUrl}/node_modules/gsap/dist`);
  const htmlPath = path.join(work, 'words10.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  const plain = { ...T, plays: [] };
  await page.evaluate(({ d, t }) => { window.configure(d, t); window.seek(1.9); }, { d: list, t: plain });
  await page.evaluate(() => Promise.all([document.fonts.load('40px NotoArmenian', 'Աբգ'), document.fonts.load('700 48px Literata', 'Ab'),
    document.fonts.load('30px IPA', 'ʃɪiːθðɜɔæʌɒəʊɡŋ')]).then(() => document.fonts.ready));
  await page.evaluate(() => { window.seek(0); window.fit(); window.seek(1.9); });
  const check = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.row')];
    const tight = rows.filter((r) => { const a = r.querySelector('.ipa').getBoundingClientRect(); const b = r.querySelector('.hy').getBoundingClientRect(); return a.right > b.left - 20 || b.right > 1012; }).map((r) => r.textContent);
    return { armenian: document.fonts.check('32px NotoArmenian', 'Հայ'), ipa: document.fonts.check('30px IPA', 'ʃɪθ'), tight,
      listBottom: Math.round(rows.at(-1).getBoundingClientRect().bottom), title: document.getElementById('theme').scrollWidth <= 920 };
  });
  console.log(`${name}: ${JSON.stringify(check)} total ${T.total}s`);
  if (!check.armenian || !check.ipa || check.tight.length || !check.title || check.listBottom > 1500) throw new Error(`${name}: layout check failed`);
  await utils.renderFrames(page, T.total, frames, posterPath, 1.9, FPS);
  if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
  await page.close();
  const voice = path.join(work, `${name}.wav`);
  voiceTrack(T, voice);
  const sfx = [{ file: 'sfx-whoosh.wav', at: 0.25, gain: 0.3 }, ...T.rows.map((r) => ({ file: 'sfx-pop.wav', at: r.at, gain: 0.12 })),
    { file: 'sfx-whoosh.wav', at: T.total - 2.2, gain: 0.3 }];
  // story image: the same list, still, pointing to the reel
  const sp = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await utils.preparePage(sp, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  await sp.evaluate(({ d, t }) => { window.configure({ ...d, story: true }, t); window.seek(0); window.fit(); window.seek(1.9); }, { d: list, t: plain });
  await sp.evaluate(() => document.fonts.ready);
  const storyPath = path.join(output, `${name}-story.jpg`);
  await sp.screenshot({ path: storyPath, type: 'jpeg', quality: 93 });
  await sp.close();
  utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, storyPath, info, thumbOffsetMs: 1900 };
}

async function main() {
  const id = process.argv[2];
  const list = DATA.lists.find((x) => x.id === id);
  if (!list) throw new Error(`Unknown list: ${id}`);
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Set CHROME_PATH.');
  const { server, baseUrl } = await utils.startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    const r = await renderWords10(browser, baseUrl, list);
    console.log(r.videoPath);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
module.exports = { renderWords10, timeline };

// Story video: one picture per scene with camera moves and cross-fades, narrated, the spoken word highlighted.
// Usage: node reels/render_storyvideo.js <story-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/storyvideo.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));
// one accent per day, from the brand palette, so neighbouring posts never look the same
const PALETTE = ['#B9790B', '#1C8AA3', '#B23F78', '#3E5FD9', '#2E9E6A', '#6A49E2'];
const withColor = (st) => ({ ...st, color: PALETTE[(st.number + 1) % PALETTE.length],
  imgs: st.scenes.map((_, i) => `data:image/jpeg;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets', 'storyvideo', st.id, `${i + 1}.jpg`)).toString('base64')}`) });

function clip(id, n, text) {
  const dir = path.join(utils.ROOT, 'assets', 'storyvideo', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `${n}.json`), 'utf8'));
  if (timing.text !== text) throw new Error(`${id}/${n}: audio is for a different word; re-run the voices.`);
  const start = timing.words[0][0];
  const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `${n}.mp3`), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]), scenes: (timing.scenes || []).map((s) => s - start) };
}

// Title and first picture in, then each scene: picture changes as its sentence starts.
function timeline(st) {
  const c = clip(st.id, 'p', st.scenes.join(' '));
  const at = 1.4;
  return { plays: [{ at, clip: c }], sceneStart: c.scenes.map((s) => r3(s + at)), words: c.words.map(([a, b]) => [r3(a + at), r3(b + at)]), total: r3(at + c.len + 1.6 + 2.6) };
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

async function renderStoryvideo(browser, baseUrl, list0) {
  const list = withColor(list0);
  const T = timeline(list);
  const name = `storyvideo-${list.id}`;
  const output = utils.OUTPUT;
  const frames = path.join(output, `.frames-${name}`);
  const videoPath = path.join(output, `${name}.mp4`);
  const posterPath = path.join(output, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work');
  utils.ensureDirectory(work); utils.ensureDirectory(output);
  const fonts = `${baseUrl}/node_modules/@fontsource-variable/inter/files`;
  const html = utils.paperTheme(utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'storyvideo.html'), 'utf8'), baseUrl), 'reading')
    .replaceAll('__INTER_EXT_FONT__', `${fonts}/inter-latin-ext-wght-normal.woff2`)
    .replaceAll('__INTER_GREEK_FONT__', `${fonts}/inter-greek-wght-normal.woff2`);
  const htmlPath = path.join(work, 'storyvideo.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  const plain = { ...T, plays: [] };
  await page.evaluate(({ d, t }) => { window.configure(d, t); window.seek(1.9); }, { d: list, t: plain });
  await page.evaluate(() => Promise.all([document.fonts.load('40px NotoArmenian', 'Աբգ'), document.fonts.load('700 48px Literata', 'Ab'),
    document.fonts.load('30px IPA', 'ʃɪiːθðɜɔæʌɒəʊɡŋ')]).then(() => document.fonts.ready));
  await page.evaluate(() => { window.seek(0); window.fit(); window.seek(1.9); });
  const check = await page.evaluate(() => ({ armenian: document.fonts.check('32px NotoArmenian', 'Հայ'),
    over: [...document.querySelectorAll('.cap p')].filter((p) => p.scrollHeight > 336).length, imgs: [...document.querySelectorAll('.stage img')].map((i) => i.naturalWidth) }));
  console.log(`${name}: ${JSON.stringify(check)} total ${T.total}s`);
  if (!check.armenian || check.over || check.imgs.some((w) => w !== 1080)) throw new Error(`${name}: layout check failed`);
  await utils.renderFrames(page, T.total, frames, posterPath, 1.2, FPS);
  if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
  await page.close();
  const voice = path.join(work, `${name}.wav`);
  voiceTrack(T, voice);
  const sfx = [{ file: 'sfx-whoosh.wav', at: 0.25, gain: 0.3 }, { file: 'sfx-pop.wav', at: 0.6, gain: 0.15 },
    { file: 'sfx-whoosh.wav', at: T.total - 2.2, gain: 0.3 }];
  utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info };
}

async function main() {
  const id = process.argv[2];
  const list = DATA.stories.find((x) => x.id === id);
  if (!list) throw new Error(`Unknown list: ${id}`);
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Set CHROME_PATH.');
  const { server, baseUrl } = await utils.startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    const r = await renderStoryvideo(browser, baseUrl, list);
    console.log(r.videoPath);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
module.exports = { renderStoryvideo, timeline };

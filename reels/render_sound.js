// Sound it out: minimal-pair pronunciation reel.
// Usage: node reels/render_sound.js <sound-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/sounds.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));

function clip(id, key) {
  const dir = path.join(utils.ROOT, 'assets', 'sounds', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `${key}.json`), 'utf8'));
  const start = timing.words[0][0];
  const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `${key}.mp3`), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]), text: timing.text };
}

// Calm, human pace: hear A, B, A, B; read the tips; guess; then say the sentence yourself.
function timeline(item) {
  const a = clip(item.id, 'a');
  const b = clip(item.id, 'b');
  const s = clip(item.id, 's');
  const test = item.test === 'a' ? a : b;
  const plays = [];
  const play = (key, c, at) => { plays.push({ key, at: r3(at), end: r3(at + c.len), clip: c }); return at + c.len; };
  let t = 1.7;
  t = play('a', a, t) + 0.8;
  t = play('b', b, t) + 1.0;
  t = play('a', a, t) + 0.6;
  t = play('b', b, t) + 0.9;
  const tips = t;
  t += 4.4;
  const testAt = t;
  const testEnd = play('t', test, testAt + 1.0);
  const reveal = testEnd + 3.0;
  play(item.test, test, reveal + 0.35);
  const say = reveal + 2.6;
  const sentenceAt = say + 0.9;
  const sentenceEnd = play('s', s, sentenceAt);
  const turn = sentenceEnd + 0.7;
  const turnEnd = turn + s.len + 2.2;
  const total = turnEnd + 2.4;
  return {
    plays, tips: r3(tips), test: r3(testAt), reveal: r3(reveal), say: r3(say), turn: r3(turn), turnEnd: r3(turnEnd), total: r3(total),
    words: s.words.map(([x, y]) => [r3(x + sentenceAt), r3(y + sentenceAt)]),
  };
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

async function renderSound(browser, baseUrl, item) {
  const T = timeline(item);
  const name = `sound-${item.id}`;
  const output = utils.OUTPUT;
  const frames = path.join(output, `.frames-${name}`);
  const videoPath = path.join(output, `${name}.mp4`);
  const posterPath = path.join(output, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work');
  utils.ensureDirectory(work); utils.ensureDirectory(output);
  const fonts = `${baseUrl}/node_modules/@fontsource-variable/inter/files`;
  const html = utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'sound.html'), 'utf8'), baseUrl)
    .replaceAll('__INTER_EXT_FONT__', `${fonts}/inter-latin-ext-wght-normal.woff2`)
    .replaceAll('__INTER_GREEK_FONT__', `${fonts}/inter-greek-wght-normal.woff2`);
  const htmlPath = path.join(work, 'sound.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  const plain = { ...T, plays: T.plays.map(({ key, at, end }) => ({ key, at, end })) };
  await page.evaluate(({ d, t }) => { window.configure(d, t); window.seek(0); }, { d: item, t: plain });
  await page.evaluate(() => Promise.all([document.fonts.load('40px NotoArmenian', 'Աբգ'), document.fonts.load('40px Literata', 'Ab'),
    document.fonts.load('44px IPA', 'ʃɪiːθðɜɔæʌɒəʊɡŋ')]).then(() => document.fonts.ready));
  const check = await page.evaluate(() => {
    const over = [...document.querySelectorAll('.w,.tip span,.sentence,.sentence-hy,.ipa')].filter((e) => e.scrollWidth > e.clientWidth + 2 || e.getBoundingClientRect().right > 1020).map((e) => e.textContent);
    window.seek(30);
    const zone = document.querySelector('.zone').getBoundingClientRect();
    const say = document.getElementById('say'); const sayBottom = [...say.children].reduce((m, c) => Math.max(m, c.getBoundingClientRect().bottom), 0);
    return { armenian: document.fonts.check('32px NotoArmenian', 'Հայ'), ipa: document.fonts.check('44px IPA', 'ʃɪθ'), over, sayBottom: Math.round(sayBottom), zoneBottom: Math.round(zone.bottom) };
  });
  console.log(`${name}: ${JSON.stringify(check)} total ${T.total}s`);
  if (!check.armenian || !check.ipa || check.over.length || check.sayBottom > 1690) throw new Error(`${name}: layout check failed`);
  await utils.renderFrames(page, T.total, frames, posterPath, T.reveal + 1.2, FPS);
  if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
  await page.close();
  const voice = path.join(work, `${name}.wav`);
  voiceTrack(T, voice);
  const sfx = [{ file: 'sfx-whoosh.wav', at: 0.25, gain: 0.35 }, { file: 'sfx-pop.wav', at: T.tips, gain: 0.35 },
    ...[3, 2, 1].map((k) => ({ file: 'sfx-tick.wav', at: T.reveal - k, gain: 0.45 })), { file: 'sfx-ding.wav', at: T.reveal, gain: 0.5 },
    { file: 'sfx-pop.wav', at: T.turn, gain: 0.3 }, { file: 'sfx-whoosh.wav', at: T.total - 2.2, gain: 0.3 }];
  utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info, thumbOffsetMs: Math.round((T.reveal + 1.2) * 1000) };
}

async function main() {
  const id = process.argv[2];
  const item = DATA.sounds.find((s) => s.id === id);
  if (!item) throw new Error(`Unknown sound: ${id}`);
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Set CHROME_PATH.');
  const { server, baseUrl } = await utils.startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    const r = await renderSound(browser, baseUrl, item);
    console.log(r.videoPath);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
module.exports = { renderSound, timeline };

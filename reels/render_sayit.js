// Say it right: an Armenian narrator explains how an English word really sounds.
// Usage: node reels/render_sayit.js <id>     (SAYIT_HY=anahit|hayk, SAYIT_EN=ryan|sonia pick the voices)
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/sayit.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH;
const FPS = 30;
const HY = process.env.SAYIT_HY || 'anahit';
const EN = process.env.SAYIT_EN || 'ryan';
const r3 = (x) => Number(x.toFixed(3));
const norm = (s) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');

// Trim the clip to its real sound (silence detection) and spread the voice's word marks over the displayed words.
function clip(id, line) {
  const dir = path.join(utils.ROOT, 'assets', 'sayit', id, line.lang === 'hy' ? HY : EN);
  const file = path.join(dir, `${line.k}.mp3`);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `${line.k}.json`), 'utf8'));
  if (timing.text !== line.text) throw new Error(`${id}/${line.k}: audio is for another text; run the voices again.`);
  const sd = spawnSync(utils.FFmpeg, ['-hide_banner', '-i', file, '-af', 'silencedetect=n=-42dB:d=0.12', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
  const dur = Number(sd.match(/Duration: (\d+):(\d+):([\d.]+)/).slice(1).reduce((a, x, i) => a + Number(x) * [3600, 60, 1][i], 0));
  const ends = [...sd.matchAll(/silence_end: ([\d.]+)/g)].map((m) => Number(m[1]));
  const starts = [...sd.matchAll(/silence_start: ([\d.]+)/g)].map((m) => Number(m[1]));
  const start = Math.max(0, (starts[0] === 0 || starts[0] < 0.02 ? ends[0] : 0) - 0.04);
  const last = starts.filter((s) => s > start + 0.2).pop();
  const end = Math.min(dur, (last && last > dur - 1.2 ? last : dur) + 0.06);
  const tokens = line.text.split(' ');
  let marks = timing.words.filter((w) => norm(w[2] || 'x'));
  const tok = [];
  let m = 0;
  tokens.forEach((text) => {
    if (!norm(text)) { tok.push({ text, s: null, e: null }); return; }
    const mk = marks[m] || marks[marks.length - 1]; m += 1;
    tok.push({ text, s: mk[0] - start, e: mk[1] - start });
  });
  if (marks.length !== tokens.filter((x) => norm(x)).length) {     // marks do not match the words: spread by length
    const total = tokens.reduce((a, x) => a + x.length, 0); let acc = 0;
    tok.forEach((w) => { w.s = ((end - start) * acc) / total; acc += w.text.length; w.e = ((end - start) * acc) / total; });
  }
  tok.forEach((w, i) => { if (w.s == null) { w.s = tok[i - 1] ? tok[i - 1].e : 0; w.e = w.s; } });
  return { file, start, end, len: end - start, tokens: tok };
}

function timeline(item) {
  const L = Object.fromEntries(item.lines.map((l) => [l.k, { ...l, clip: clip(item.id, l) }]));
  const plays = []; const lines = [];
  const put = (k, at) => { const c = L[k].clip; plays.push({ at, clip: c }); lines.push({ k, lang: L[k].lang, at: r3(at), len: r3(c.len), tokens: c.tokens.map((w) => ({ text: w.text, s: r3(w.s), e: r3(w.e) })) }); return at + c.len; };
  let t = put('intro', 0.7) + 0.55;
  const scenes = [];
  item.words.forEach((w, i) => {
    const n = i + 1; const sc = { at: r3(t) };
    const a = L[`w${n}a`].clip; const qi = a.tokens.findIndex((x) => x.text.includes('»'));
    const aEnd = put(`w${n}a`, t + 0.35);
    sc.wrongEnd = r3(t + 0.35 + (qi >= 0 ? a.tokens[qi].e : a.len * 0.7));
    const e1 = aEnd + 0.3; const en1 = put(`w${n}`, e1);
    const e2 = en1 + 0.55; const en2 = put(`w${n}`, e2);
    sc.en = [r3(e1), r3(en1)]; sc.plays = [[r3(e1), r3(en1)], [r3(e2), r3(en2)]];
    sc.note = r3(en2 + 0.5);
    t = put(`w${n}b`, en2 + 0.5) + 0.9;
    scenes.push(sc);
  });
  const outro = r3(t);
  const end = put('outro', t + 0.6);
  return { plays, lines, scenes, outro, total: r3(end + 2.4) };
}

function voiceTrack(T, out) {
  const args = ['-y', '-hide_banner', '-loglevel', 'error'];
  T.plays.forEach((p) => args.push('-i', p.clip.file));
  const chains = T.plays.map((p, i) => {
    const ms = Math.round(p.at * 1000);
    return `[${i}:a]aresample=48000,atrim=${p.clip.start.toFixed(3)}:${(p.clip.end + 0.05).toFixed(3)},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st=${Math.max(0, p.clip.len - 0.05).toFixed(3)}:d=0.08,adelay=${ms}|${ms}[v${i}]`;
  });
  args.push('-filter_complex', `${chains.join(';')};${T.plays.map((_, i) => `[v${i}]`).join('')}amix=inputs=${T.plays.length}:normalize=0,apad=whole_dur=${T.total}[a]`,
    '-map', '[a]', '-ac', '2', '-c:a', 'pcm_s16le', out);
  const r = spawnSync(utils.FFmpeg, args, { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`Voice track failed: ${r.stderr}`);
}

async function main() {
  const item = DATA.items.find((x) => x.id === process.argv[2]);
  if (!item) throw new Error(`Unknown item: ${process.argv[2]}`);
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Set CHROME_PATH.');
  const T = timeline(item);
  const name = `sayit-${item.id}-${HY}`;
  const out = utils.OUTPUT; const work = path.join(utils.ROOT, '.render-work');
  utils.ensureDirectory(out); utils.ensureDirectory(work);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  try {
    const fonts = `${baseUrl}/node_modules/@fontsource-variable`;
    const html = utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'sayit.html'), 'utf8'), baseUrl)
      .replaceAll('__INTER_EXT_FONT__', `${fonts}/inter/files/inter-latin-ext-wght-normal.woff2`)
      .replaceAll('__FRAUNCES_FONT__', `${fonts}/fraunces/files/fraunces-latin-full-italic.woff2`);
    const htmlPath = path.join(work, 'sayit.html'); fs.writeFileSync(htmlPath, html, 'utf8');
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: utils.DPR });
    const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
    const plain = { ...T, plays: undefined };
    await page.evaluate(({ d, t }) => window.configure(d, t), { d: item, t: plain });
    await page.evaluate(() => Promise.all([document.fonts.load('800 80px NotoArmenian', 'Աբգ'), document.fonts.load('600 80px Literata', 'Ab'),
      document.fonts.load('500 40px IPA', 'ˈʌəʒɪ'), document.fonts.load('italic 30px SignF', 'Ab')]).then(() => document.fonts.ready));
    if (process.env.STILLS) {
      for (const s of process.env.STILLS.split(',')) {
        await page.evaluate((x) => window.seek(x), Number(s));
        await page.screenshot({ path: path.join(out, `${name}-still-${s}.jpg`), type: 'jpeg', quality: 88 });
      }
    }
    const fit = []; for (const s of [T.scenes[0].note + 1, T.scenes[1].note + 1, T.scenes[2].note + 1, T.outro + 2]) { await page.evaluate((x) => window.seek(x), s); fit.push(...await page.evaluate(() => window.fit())); }
    if (fit.length) throw new Error(`layout: outside the safe area: ${fit.join(', ')}`);
    console.log(`${name}: total ${T.total}s, scenes ${T.scenes.map((s) => s.at).join(' ')}`);
    if (process.env.STILLS_ONLY) return;
    const frames = path.join(out, `.frames-${name}`);
    await utils.renderFrames(page, T.total, frames, path.join(out, `${name}.png`), 1.8, FPS);
    if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
    const voice = path.join(work, `${name}.wav`); voiceTrack(T, voice);
    const videoPath = path.join(out, `${name}.mp4`);
    const sfx = [{ file: 'sfx-whoosh.wav', at: 0.1, gain: 0.25 }, ...T.scenes.map((s) => ({ file: 'sfx-whoosh.wav', at: s.at, gain: 0.22 })),
      ...T.scenes.map((s) => ({ file: 'sfx-pop.wav', at: s.wrongEnd, gain: 0.14 })), { file: 'sfx-whoosh.wav', at: T.outro, gain: 0.22 }];
    utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
    console.log(JSON.stringify(utils.verifyVideo(videoPath)));
    fs.rmSync(frames, { recursive: true, force: true });
    console.log(videoPath);
  } finally { await browser.close(); server.close(); }
}

main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

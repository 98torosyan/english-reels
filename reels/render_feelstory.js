// Short emotional story: picture on top (its calm lower part melts into the paper colour), lines read one by one below,
// the key phrase highlighted. Usage: node reels/render_feelstory.js <story-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/feelstory.json'), 'utf8'));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));

function clip(id, n, text) {
  const dir = path.join(utils.ROOT, 'assets', 'feelstory', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `v${n}.json`), 'utf8'));
  if (timing.text !== text) throw new Error(`${id}/v${n}: audio is for a different text; re-run the voices.`);
  // the voice service's word times run a little ahead of the sound: move them onto the real first sound
  const det = require('child_process').spawnSync('ffmpeg', ['-hide_banner', '-i', path.join(dir, `v${n}.mp3`), '-af', 'silencedetect=n=-35dB:d=0.05', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
  const onset = Number((det.match(/silence_end: ([\d.]+)/) || [])[1]);
  if (Number.isFinite(onset) && Math.abs(onset - timing.words[0][0]) < 0.4) timing.words[0][0] = Math.min(onset, timing.words[0][1] - 0.05);
  const start = timing.words[0][0]; const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `v${n}.mp3`), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]) };
}

function timeline(st) {
  const plays = []; const lines = []; const scenes = [];
  let t = 0.9; let n = 0;
  st.scenes.forEach((sc, s) => {
    if (s) t += 0.5;
    const s0 = t - 0.35;
    sc.forEach((line) => {
      const c = clip(st.id, n, line.replace(/[[\]]/g, ''));
      plays.push({ at: r3(t), clip: c });
      lines.push({ at: r3(t), end: r3(t + c.len), words: c.words.map(([a, b]) => [r3(a + t), r3(b + t)]) });
      t += c.len + 0.55; n += 1;
    });
    scenes.push({ at: r3(Math.max(0, s0)), end: r3(t) });
  });
  return { plays, lines, scenes, total: r3(t + 0.6 + 3.4) };
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

// Reel cover for the profile grid (Instagram shows the middle 3:4): the first picture, the title in the calm lower part.
function coverHtml(st, baseUrl, paper, pic) {
  const f = utils.fontUrls(baseUrl);
  return `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Lit;src:url(${f.literata})}@font-face{font-family:Lit;src:url(${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-italic.woff2);font-style:italic}
@font-face{font-family:Arm;src:url(${f.armenian})}@font-face{font-family:Inter;src:url(${f.inter})}
*{margin:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;background:${paper}}
.p{position:absolute;left:0;top:0;width:1080px;height:1300px;overflow:hidden}.p img{width:100%;height:100%;object-fit:cover;object-position:50% 30%}
.p:after{content:"";position:absolute;left:0;right:0;bottom:0;height:520px;background:linear-gradient(transparent,${paper} 88%)}
.t{position:absolute;left:80px;right:80px;top:1150px;text-align:center;color:#2B1E14}
.t h1{font:600 italic 104px/1.02 Lit;letter-spacing:-2px;text-wrap:balance}
.t p{margin-top:26px;font:600 40px Arm;color:#5b4636}
.b{position:absolute;left:0;right:0;bottom:90px;text-align:center;font:800 22px Inter;letter-spacing:6px;color:#2B1E1466}
</style></head><body><div class="p"><img src="${pic}"></div><div class="t"><h1>${st.title.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</h1><p>${st.title_hy}</p></div><div class="b">@ENGLISH.READINGROOM</div></body></html>`;
}

// paper colour = the average colour of the bottom strip of the first picture, so the picture melts into it
function paperColour(st) {
  const f = path.join(utils.ROOT, 'assets', st.pics_dir || `feelstory/${st.id}`, '1.jpg');
  const r = spawnSync(utils.FFmpeg, ['-v', 'error', '-i', f, '-vf', 'crop=iw:60:0:ih-60,scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { encoding: 'buffer' });
  const [R, G, B] = r.stdout; return `rgb(${R},${G},${B})`;
}

async function main() {
  const st = DATA.stories.find((x) => x.id === process.argv[2]);
  if (!st) throw new Error(`Unknown story: ${process.argv[2]}`);
  // a soft piano bed suits these stories better than the rotating set
  if (!process.env.MUSIC_TRACK) process.env.MUSIC_TRACK = path.join(utils.ROOT, 'music', st.music || 'felt-piano.m4a');
  const T = timeline(st); const name = `feelstory-${st.id}`;
  const frames = path.join(utils.OUTPUT, `.frames-${name}`); const videoPath = path.join(utils.OUTPUT, `${name}.mp4`); const posterPath = path.join(utils.OUTPUT, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work'); utils.ensureDirectory(work); utils.ensureDirectory(utils.OUTPUT);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try {
    const html = utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'feelstory.html'), 'utf8'), baseUrl)
      .replaceAll('__LITERATA_ITALIC__', `${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-italic.woff2`);
    const htmlPath = path.join(work, 'feelstory.html'); fs.writeFileSync(htmlPath, html, 'utf8');
    const pics = st.scenes.map((_, i) => `${baseUrl}/assets/${st.pics_dir || `feelstory/${st.id}`}/${i + 1}.jpg`);   // pics_dir lets a series reuse pictures (e.g. countries)
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
    const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
    await page.evaluate(({ d, t }) => { window.configure(d, t); window.seek(0); }, { d: { ...st, pics, paper: paperColour(st) }, t: { ...T, plays: [] } });
    await page.evaluate(() => Promise.all([document.fonts.load('600 60px Literata', 'Ab'), document.fonts.load('italic 600 60px Literata', 'Ab'), document.fonts.load('40px NotoArmenian', 'Աբ'),
      ...[...document.images].map((i) => i.decode().catch(() => null))]).then(() => document.fonts.ready));
    const wide = await page.evaluate(() => [...document.querySelectorAll('.ln')].filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.textContent));
    if (wide.length) throw new Error(`${name}: line too long: ${wide.join(' | ')}`);
    await utils.renderFrames(page, T.total, frames, posterPath, T.lines[1].at - 0.3, FPS);
    if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
    await page.close();
    const voice = path.join(work, `${name}.wav`); voiceTrack(T, voice);
    const sfx = T.scenes.slice(1).map((s) => ({ file: 'sfx-whoosh.wav', at: s.at, gain: 0.06 }));
    utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
    const info = utils.verifyVideo(videoPath); fs.rmSync(frames, { recursive: true, force: true });
    const cw = path.join(work, 'feelstory-cover.html'); fs.writeFileSync(cw, coverHtml(st, baseUrl, paperColour(st), pics[0]));
    const cp = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
    await utils.preparePage(cp, `${baseUrl}${utils.renderHtmlPath(cw)}`, 1080, 1920);
    await cp.evaluate(() => Promise.all([document.fonts.load('italic 600 104px Lit', 'Ab'), document.fonts.load('600 40px Arm', 'Աբ'), document.fonts.ready, ...[...document.images].map((i) => i.decode().catch(() => null))]));
    await cp.screenshot({ path: path.join(utils.OUTPUT, `${name}-cover.jpg`), type: 'jpeg', quality: 93 }); await cp.close();
    console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  } finally { await browser.close(); server.close(); }
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

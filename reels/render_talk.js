// Emma & Sam: an everyday dialogue on six 3D-diorama pictures that move like a film (depth parallax, floating light,
// falling leaves), a speech bubble next to whoever speaks, words lighting up with the voice, the phrase to learn under
// the picture, and the three phrases to keep at the end. Usage: node reels/render_talk.js <talk-id>
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/talk.json'), 'utf8'));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));

function clip(id, n, text) {
  const dir = path.join(utils.ROOT, 'assets', 'talk', id);
  const timing = JSON.parse(fs.readFileSync(path.join(dir, `v${n}.json`), 'utf8'));
  if (timing.text !== text) throw new Error(`${id}/v${n}: audio is for a different text; re-run the voices.`);
  const start = timing.words[0][0]; const end = timing.words.at(-1)[1];
  return { file: path.join(dir, `v${n}.mp3`), start, end, len: end - start, words: timing.words.map(([a, b]) => [a - start, b - start]) };
}

function timeline(t) {
  const plays = []; const lines = []; const scenes = [];
  let at = 2.2; let n = 0;                                   // the title shows first
  t.scenes.forEach((sc, s) => {
    if (s) at += 0.7;
    const s0 = Math.max(0, at - 0.6);
    sc.lines.forEach(([who, text]) => {
      const c = clip(t.id, n, text.replace(/[[\]]/g, ''));
      const phrase = (text.match(/\[([^\]]+)\]/) || [])[1] || null;
      plays.push({ at: r3(at), clip: c });
      lines.push({ who, text, scene: s, head: sc.at[who] || [0.5, 0.3], phrase, at: r3(at), end: r3(at + c.len), words: c.words.map(([a, b]) => [r3(a + at), r3(b + at)]) });
      at += c.len + 0.45; n += 1;
    });
    scenes.push({ at: r3(s0), end: r3(at) });
  });
  const recapAt = r3(at + 0.6);
  return { plays, lines, scenes, recapAt, total: r3(recapAt + 4.2) };
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

// paper = the background colour of the dioramas (top strip of the first picture), so the picture melts into the page
function paperColour(t) {
  if (t.paper) return t.paper;
  const f = path.join(utils.ROOT, 'assets', 'talk', t.id, '1.jpg');
  const r = spawnSync(utils.FFmpeg, ['-v', 'error', '-i', f, '-vf', 'crop=iw:50:0:0,scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { encoding: 'buffer' });
  const [R, G, B] = r.stdout; return `rgb(${R},${G},${B})`;
}

async function main() {
  const t = DATA.talks.find((x) => x.id === process.argv[2]);
  if (!t) throw new Error(`Unknown talk: ${process.argv[2]}`);
  if (!process.env.MUSIC_TRACK) process.env.MUSIC_TRACK = path.join(utils.ROOT, 'music', t.music || 'calm-study.m4a');
  const T = timeline(t); const name = `talk-${t.id}`;
  const frames = path.join(utils.OUTPUT, `.frames-${name}`); const videoPath = path.join(utils.OUTPUT, `${name}.mp4`); const posterPath = path.join(utils.OUTPUT, `${name}.png`);
  const work = path.join(utils.ROOT, '.render-work'); utils.ensureDirectory(work); utils.ensureDirectory(utils.OUTPUT);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const html = utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'templates', 'talk.html'), 'utf8'), baseUrl);
    const htmlPath = path.join(work, 'talk.html'); fs.writeFileSync(htmlPath, html, 'utf8');
    const dir = `${baseUrl}/assets/talk/${t.id}`;
    const scenes = t.scenes.map((s, i) => ({ fx: s.fx || (i === 0 || i >= 4 ? 'leaves' : 'dust'), pic: `${dir}/${i + 1}.jpg`, depth: `${dir}/${i + 1}-depth.png` }));
    const data = { title: t.title, series: DATA.series, people: DATA.people, recap: t.recap, scenes, paper: paperColour(t), accent: t.accent };
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: utils.DPR });
    const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
    await page.evaluate(() => Promise.all([document.fonts.load('600 40px Inter', 'Ab'), document.fonts.load('700 74px Playfair', 'Ab'), document.fonts.load('italic 600 62px Playfair', 'Ab')]).then(() => document.fonts.ready));
    await page.evaluate(async ({ d, tl }) => { await window.configure(d, tl); window.seek(0); }, { d: data, tl: { ...T, plays: [] } });
    await utils.renderFrames(page, T.total, frames, posterPath, T.lines[2].at + 0.6, FPS);
    if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
    await page.close();
    const voice = path.join(work, `${name}.wav`); voiceTrack(T, voice);
    const sfx = T.lines.map((l) => ({ file: 'sfx-pop.wav', at: Math.max(0, l.at - 0.2), gain: 0.05 }));
    utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, sfx);
    const info = utils.verifyVideo(videoPath); fs.rmSync(frames, { recursive: true, force: true });
    fs.copyFileSync(posterPath, path.join(utils.OUTPUT, `${name}-cover.jpg`));
    console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  } finally { await browser.close(); server.close(); }
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { spawnSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const OUTPUT = path.resolve(ROOT, '..', '..', 'outputs', 'english-reels-samples');
const FFmpeg = require('ffmpeg-static');
// Pages are laid out at 1080 CSS px wide and captured at RENDER_SCALE: 26/15 gives 1872x3328 (9:16) and 1872x2340 (4:5),
// the sharpest sizes Instagram's publishing accepts (max 1920 px wide, 3600 px tall). RENDER_SCALE=1 brings back 1080p.
const DPR = Number(process.env.RENDER_SCALE || 26 / 15);
const outSize = () => (process.env.VIDEO_SIZE || '1080x1920').split('x').map((v) => Math.round(Number(v) * DPR / 2) * 2);

function startStaticServer() {
  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
    const target = path.resolve(ROOT, `.${pathname}`);
    if (!target.startsWith(`${ROOT}${path.sep}`) || target.includes(`${path.sep}.git${path.sep}`)) {
      response.writeHead(403).end();
      return;
    }
    fs.readFile(target, (error, content) => {
      if (error) {
        response.writeHead(error.code === 'ENOENT' ? 404 : 500).end();
        return;
      }
      const ext = path.extname(target).toLowerCase();
      const contentType = {
        '.html': 'text/html; charset=utf-8',
        '.svg': 'image/svg+xml',
        '.woff2': 'font/woff2',
        '.js': 'text/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
      }[ext] || 'application/octet-stream';
      response.writeHead(200, { 'Content-Type': contentType, 'Cache-Control': 'no-store' });
      response.end(content);
    });
  });
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      resolve({ server, baseUrl: `http://127.0.0.1:${address.port}` });
    });
  });
}

function fontUrls(baseUrl) {
  return {
    inter: `${baseUrl}/node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2`,
    literata: `${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-normal.woff2`,
    armenian: `${baseUrl}/node_modules/@fontsource-variable/noto-sans-armenian/files/noto-sans-armenian-armenian-wght-normal.woff2`,
    playfair: `${baseUrl}/node_modules/@fontsource-variable/playfair-display/files/playfair-display-latin-wght-normal.woff2`,
    playfairItalic: `${baseUrl}/node_modules/@fontsource-variable/playfair-display/files/playfair-display-latin-wght-italic.woff2`,
  };
}

function htmlAssets(html, baseUrl) {
  const fonts = fontUrls(baseUrl);
  const logo = fs.readFileSync(path.join(ROOT, 'assets', process.env.THEME === 'dark' ? 'icon.svg' : 'logo-ig.svg')).toString('base64');
  return html
    .replaceAll('__INTER_FONT__', fonts.inter)
    .replaceAll('__LITERATA_FONT__', fonts.literata)
    .replaceAll('__ARMENIAN_FONT__', fonts.armenian)
    .replaceAll('__PLAYFAIR_FONT__', fonts.playfair)
    .replaceAll('__PLAYFAIR_ITALIC_FONT__', fonts.playfairItalic)
    .replaceAll('__LOGO_DATA__', `data:image/svg+xml;base64,${logo}`)
    .replaceAll('__MARK_DATA__', `data:image/svg+xml;base64,${fs.readFileSync(path.join(ROOT, 'assets', 'logo-mark.svg')).toString('base64')}`);
}

function ensureDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true });
}

function renderHtmlPath(filePath) {
  const relative = path.relative(ROOT, filePath).split(path.sep).map(encodeURIComponent).join('/');
  return `/${relative}`;
}

async function preparePage(page, url, width, height) {
  await page.setViewportSize({ width, height });
  // remember every set-up step the renderer does on this page, so renderFrames can open identical pages and render in parallel
  if (!page.__steps) {
    page.__steps = [];
    const original = page.evaluate.bind(page);
    page.evaluate = (fn, arg) => { page.__steps.push([fn, arg]); return original(fn, arg); };
    page.__evaluate = original;
  }
  page.__url = url;
  const consoleErrors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => consoleErrors.push(error.message));
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  return consoleErrors;
}

async function renderFrames(page, duration, framesDirectory, posterPath, posterTime, fps = 30) {
  const resolvedFrames = path.resolve(framesDirectory);
  if (!resolvedFrames.startsWith(`${OUTPUT}${path.sep}`)) {
    throw new Error('Frames must be written inside the local sample output folder.');
  }
  fs.mkdirSync(resolvedFrames, { recursive: true });
  const totalFrames = Math.ceil(duration * fps);
  const posterFrame = Math.max(0, Math.min(totalFrames - 1, Math.round(posterTime * fps)));
  // Several identical pages share the frames (each frame depends only on its time), so a video renders a few times faster.
  const want = Math.max(1, Number(process.env.RENDER_WORKERS || Math.min(4, require('node:os').cpus().length + 1)));
  const pages = [page];
  if (want > 1 && page.__url && page.__steps) {
    for (let k = 1; k < want; k += 1) {
      try {
        const dpr = await (page.__evaluate || page.evaluate.bind(page))(() => window.devicePixelRatio);
        const browser = page.context().browser();
        const p = browser ? await browser.newPage({ viewport: page.viewportSize(), deviceScaleFactor: dpr }) : await page.context().newPage();
        await p.goto(page.__url, { waitUntil: 'networkidle' });
        await p.evaluate(() => document.fonts.ready);
        for (const [fn, arg] of page.__steps) await p.evaluate(fn, arg);
        pages.push(p);
      } catch (error) { console.warn(`  parallel page ${k} not used: ${error.message}`); break; }
    }
  }
  let next = 0; let done = 0;
  const run = async (p) => {
    const evaluate = p.__evaluate || p.evaluate.bind(p);
    for (;;) {
      const frame = next; next += 1;
      if (frame >= totalFrames) return;
      await evaluate((time) => window.seek(time), frame / fps);
      const framePath = path.join(resolvedFrames, `f${String(frame).padStart(5, '0')}.jpg`);
      const screenshot = await p.screenshot({ path: framePath, type: 'jpeg', quality: 92 });
      if (frame === posterFrame) fs.writeFileSync(posterPath, screenshot);
      done += 1; if (done % 90 === 0) process.stdout.write(`  frame ${done}/${totalFrames}\r`);
    }
  };
  await Promise.all(pages.map(run));
  for (const p of pages.slice(1)) await p.close().catch(() => {});
  process.stdout.write(`  rendered ${totalFrames} frames (${pages.length} page${pages.length > 1 ? 's' : ''}).\n`);
  return { totalFrames, fps };
}

// Original background loops from music/make_music.py; picked per video so the feed varies.
function pickMusic(outputPath) {
  if (process.env.NO_MUSIC === '1') return null;
  if (process.env.MUSIC_TRACK && fs.existsSync(process.env.MUSIC_TRACK)) return process.env.MUSIC_TRACK;
  const dir = path.join(ROOT, 'music');
  const tracks = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.m4a')).sort() : [];
  if (!tracks.length) return null;
  const name = path.basename(outputPath);
  let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return path.join(dir, tracks[h % tracks.length]);
}

// Broadcast-style voice polish: clean lows, less mud, clearer presence, soft de-essing, gentle compression.
const VOICE_FX = 'highpass=f=80,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=2,equalizer=f=9000:t=q:w=1:g=1.5,deesser=i=0.35,acompressor=threshold=-21dB:ratio=2.5:attack=6:release=140:makeup=2.5';

function encodeVideo(framesDirectory, audioPath, audioStart, duration, outputPath, fps = 30, sfx = [], voiceDelay = 0, voiceLen = 0) {
  const framePattern = path.join(framesDirectory, 'f%05d.jpg').replace(/\\/g, '/');
  const args = [
    '-y', '-hide_banner', '-loglevel', 'error',
    '-framerate', String(fps), '-i', framePattern,
  ];
  if (audioPath) args.push('-ss', Number(audioStart || 0).toFixed(3), '-i', path.resolve(audioPath));
  else args.push('-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000');
  const music = pickMusic(outputPath);
  const fadeOut = Math.max(0, duration - 1.2).toFixed(3);
  if (music) {
    args.push('-stream_loop', '-1', '-i', music);
    const voice = audioPath ? 1.0 : 0.0;
    const fx = (sfx || []).filter((e) => fs.existsSync(path.join(ROOT, 'music', e.file)));
    fx.forEach((e) => args.push('-i', path.join(ROOT, 'music', e.file)));
    const fxChains = fx.map((e, i) => `[${3 + i}:a]aresample=48000,volume=${e.gain || 0.5},adelay=${Math.round(e.at * 1000)}|${Math.round(e.at * 1000)},apad[f${i}];`).join('');
    const fxLabels = fx.map((_, i) => `[f${i}]`).join('');
    args.push('-filter_complex',
      `[1:a]aresample=48000,${voiceLen ? `atrim=0:${voiceLen.toFixed(3)},afade=t=out:st=${Math.max(0, voiceLen - 0.25).toFixed(3)}:d=0.25,` : ''}${voiceDelay ? `adelay=${Math.round(voiceDelay * 1000)}|${Math.round(voiceDelay * 1000)},` : ''}${audioPath ? `${VOICE_FX},` : ''}apad,volume=${voice},asplit=2[v][sc];` +
      `[2:a]aresample=48000,volume=${audioPath ? 0.16 : 0.45},afade=t=in:d=0.8,afade=t=out:st=${fadeOut}:d=1.2[m];` +
      `[m][sc]sidechaincompress=threshold=0.02:ratio=5:attack=25:release=450[md];` + fxChains +
      `[v][md]${fxLabels}amix=inputs=${2 + fx.length}:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,alimiter=limit=0.95[a]`);
    args.push('-map', '0:v:0', '-map', '[a]');
  } else {
    args.push('-map', '0:v:0', '-map', '1:a:0', '-af', 'apad');
  }
  args.push(
    '-t', duration.toFixed(3),
    '-vf', `scale=${outSize().join(':')}:flags=lanczos,setsar=1`,
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-maxrate', '12M', '-bufsize', '24M', '-profile:v', 'high', '-level', '5.1', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
    '-movflags', '+faststart', path.resolve(outputPath),
  );
  const result = spawnSync(FFmpeg, args, { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
  if (result.status !== 0) throw new Error(`Video encoding failed: ${(result.stderr || result.error || '').toString().slice(-2500)}`);
  levelLoudness(outputPath);
}

// Second pass: one-pass loudnorm can miss the target on videos with long pauses (e.g. 10 words).
// Measure the finished file and, if it is more than 1 LU off -14 LUFS, correct the audio gain (video copied untouched).
function levelLoudness(outputPath, pass = 0) {
  const r = spawnSync(FFmpeg, ['-hide_banner', '-nostats', '-i', path.resolve(outputPath), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
  const lufs = Number(((r.stderr || '').match(/I:\s+(-?[\d.]+) LUFS/g) || []).pop()?.match(/-?[\d.]+/)[0]);
  const peak = Number(((r.stderr || '').match(/Peak:\s+(-?[\d.]+) dBFS/g) || []).pop()?.match(/-?[\d.]+/)[0]);
  if (!Number.isFinite(lufs) || (Math.abs(lufs + 14) <= 1 && !(peak > -1))) return;   // also fix overshooting peaks
  const tmp = `${outputPath}.level.mp4`;
  const fix = spawnSync(FFmpeg, ['-y', '-hide_banner', '-loglevel', 'error', '-i', path.resolve(outputPath), '-c:v', 'copy',
    '-af', `volume=${(-14 - lufs - (peak > -1 ? Math.min(3, peak + 1.5) : 0)).toFixed(2)}dB,alimiter=limit=0.7:level=disabled`, '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', tmp], { encoding: 'utf8' });
  if (fix.status !== 0) throw new Error(`Loudness correction failed: ${fix.stderr}`);
  fs.renameSync(tmp, outputPath);
  if (pass < 2) levelLoudness(outputPath, pass + 1);   // re-measure: AAC can bring back a peak
}

function verifyVideo(videoPath) {
  const result = spawnSync(FFmpeg, ['-hide_banner', '-i', path.resolve(videoPath)], { encoding: 'utf8', maxBuffer: 2 * 1024 * 1024 });
  const info = `${result.stderr || ''}\n${result.stdout || ''}`;
  const dimensions = info.match(/(\d{3,4})x(\d{3,4})/);
  const fps = info.match(/(\d+(?:\.\d+)?) fps/);
  const duration = info.match(/Duration: (\d{2}:\d{2}:\d{2}\.\d{2})/);
  const hasAudio = /Audio:/.test(info);
  if (!dimensions || Number(dimensions[1]) !== outSize()[0] || Number(dimensions[2]) !== outSize()[1] || !hasAudio) {
    throw new Error(`Rendered video failed format validation: ${path.basename(videoPath)}`);
  }
  const q = qualityCheck(videoPath);
  return { width: Number(dimensions[1]), height: Number(dimensions[2]), fps: fps ? fps[1] : 'unknown', duration: duration ? duration[1] : 'unknown', hasAudio, ...q };
}

// Broadcast checks on the finished file: loudness close to the -14 LUFS target, no clipping, no black frames.
function qualityCheck(videoPath) {
  const run = (args) => { const r = spawnSync(FFmpeg, ['-hide_banner', '-nostats', '-i', path.resolve(videoPath), ...args, '-f', 'null', '-'], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 }); return r.stderr || ''; };
  const loud = run(['-vn', '-af', 'ebur128=peak=true']);
  const lufs = Number((loud.match(/I:\s+(-?[\d.]+) LUFS/g) || []).pop()?.match(/-?[\d.]+/)[0]);
  const peak = Number((loud.match(/Peak:\s+(-?[\d.inf]+) dBFS/g) || []).pop()?.match(/-?[\d.]+|-inf/)[0]);
  const black = (run(['-an', '-vf', 'blackdetect=d=0.3:pic_th=0.95']).match(/black_start/g) || []).length;
  const problems = [];
  if (!(lufs >= -18 && lufs <= -11)) problems.push(`loudness ${lufs} LUFS (target -14)`);
  if (!(peak <= 0)) problems.push(`clipping (peak ${peak} dBFS)`);
  if (black) problems.push(`${black} black segment(s)`);
  if (problems.length) throw new Error(`Quality check failed for ${path.basename(videoPath)}: ${problems.join('; ')}`);
  return { lufs, peak };
}

const SKILL = {
  speaking: '#1C8AA3', pronunciation: '#B23F78', grammar: '#3E5FD9', test: '#2E9E6A', vocabulary: '#B9790B', reading: '#6A49E2',
};
// Light "dictionary page" theme layered over a template; skill picks the accent colour.
function paperTheme(html, skill) {
  if (process.env.THEME === 'dark') return html;
  const css = fs.readFileSync(path.join(__dirname, 'templates', 'paper.css'), 'utf8');
  return html.replace('</head>', `<style>:root{--c:${SKILL[skill] || SKILL.reading}}</style><style>${css}</style></head>`);
}

module.exports = {
  DPR,
  outSize,
  SKILL,
  paperTheme,
  ROOT,
  OUTPUT,
  FFmpeg,
  startStaticServer,
  fontUrls,
  htmlAssets,
  ensureDirectory,
  renderHtmlPath,
  preparePage,
  renderFrames,
  encodeVideo,
  verifyVideo,
  levelLoudness,
};

const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { spawnSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const OUTPUT = path.resolve(ROOT, '..', '..', 'outputs', 'english-reels-samples');
const FFmpeg = require('ffmpeg-static');

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
  };
}

function htmlAssets(html, baseUrl) {
  const fonts = fontUrls(baseUrl);
  const logo = fs.readFileSync(path.join(ROOT, 'assets', 'icon.svg')).toString('base64');
  return html
    .replaceAll('__INTER_FONT__', fonts.inter)
    .replaceAll('__LITERATA_FONT__', fonts.literata)
    .replaceAll('__ARMENIAN_FONT__', fonts.armenian)
    .replaceAll('__LOGO_DATA__', `data:image/svg+xml;base64,${logo}`);
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
  for (let frame = 0; frame < totalFrames; frame += 1) {
    const second = frame / fps;
    await page.evaluate((time) => window.seek(time), second);
    const framePath = path.join(resolvedFrames, `f${String(frame).padStart(5, '0')}.jpg`);
    const screenshot = await page.screenshot({ path: framePath, type: 'jpeg', quality: 92 });
    if (frame === posterFrame) fs.writeFileSync(posterPath, screenshot);
    if (frame % 90 === 0) process.stdout.write(`  frame ${frame + 1}/${totalFrames}\r`);
  }
  process.stdout.write(`  rendered ${totalFrames} frames.\n`);
  return { totalFrames, fps };
}

// Original background loops from music/make_music.py; picked per video so the feed varies.
function pickMusic(outputPath) {
  if (process.env.NO_MUSIC === '1') return null;
  const dir = path.join(ROOT, 'music');
  const tracks = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.m4a')).sort() : [];
  if (!tracks.length) return null;
  const name = path.basename(outputPath);
  let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return path.join(dir, tracks[h % tracks.length]);
}

function encodeVideo(framesDirectory, audioPath, audioStart, duration, outputPath, fps = 30, sfx = []) {
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
      `[1:a]aresample=48000,apad,volume=${voice},asplit=2[v][sc];` +
      `[2:a]aresample=48000,volume=${audioPath ? 0.16 : 0.45},afade=t=in:d=0.8,afade=t=out:st=${fadeOut}:d=1.2[m];` +
      `[m][sc]sidechaincompress=threshold=0.02:ratio=5:attack=25:release=450[md];` + fxChains +
      `[v][md]${fxLabels}amix=inputs=${2 + fx.length}:duration=first:normalize=0,alimiter=limit=0.95[a]`);
    args.push('-map', '0:v:0', '-map', '[a]');
  } else {
    args.push('-map', '0:v:0', '-map', '1:a:0', '-af', 'apad');
  }
  args.push(
    '-t', duration.toFixed(3),
    '-vf', 'scale=1080:1920:flags=lanczos,setsar=1',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
    '-movflags', '+faststart', path.resolve(outputPath),
  );
  const result = spawnSync(FFmpeg, args, { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 });
  if (result.status !== 0) throw new Error(`Video encoding failed: ${(result.stderr || result.error || '').toString().slice(-2500)}`);
}

function verifyVideo(videoPath) {
  const result = spawnSync(FFmpeg, ['-hide_banner', '-i', path.resolve(videoPath)], { encoding: 'utf8', maxBuffer: 2 * 1024 * 1024 });
  const info = `${result.stderr || ''}\n${result.stdout || ''}`;
  const dimensions = info.match(/(\d{3,4})x(\d{3,4})/);
  const fps = info.match(/(\d+(?:\.\d+)?) fps/);
  const duration = info.match(/Duration: (\d{2}:\d{2}:\d{2}\.\d{2})/);
  const hasAudio = /Audio:/.test(info);
  if (!dimensions || dimensions[1] !== '1080' || dimensions[2] !== '1920' || !hasAudio) {
    throw new Error(`Rendered video failed format validation: ${path.basename(videoPath)}`);
  }
  return { width: Number(dimensions[1]), height: Number(dimensions[2]), fps: fps ? fps[1] : 'unknown', duration: duration ? duration[1] : 'unknown', hasAudio };
}

module.exports = {
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
};

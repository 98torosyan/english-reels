// "Countries in watercolour": an animated 4:5 carousel per country. The cover and the six scenes are short videos with voice
// (each word comes up as it is heard, the key word gets a soft highlight); the quiz is a still.
// Usage: node carousels/render_countries.js <country-id>   -> outputs/english-reels-samples/countries-<id>/01.mp4 … 08.jpg
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('../reels/render_utils');

process.env.VIDEO_SIZE = '1080x1350';
if (!process.env.MUSIC_TRACK) process.env.MUSIC_TRACK = path.join(utils.ROOT, 'music', 'quiet-page.m4a');
const FPS = 30;
const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'carousels/data/countries.json'), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const r3 = (x) => Number(x.toFixed(3));
const img = (id, n) => `data:image/jpeg;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets', 'countries', id, `${n}.jpg`)).toString('base64')}`;

function clip(id, name) {
  const dir = path.join(utils.ROOT, 'assets', 'countries', id);
  const t = JSON.parse(fs.readFileSync(path.join(dir, `${name}.json`), 'utf8'));
  const file = path.join(dir, `${name}.mp3`);
  const det = spawnSync('ffmpeg', ['-hide_banner', '-i', file, '-af', 'silencedetect=n=-35dB:d=0.05', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
  const onset = Number((det.match(/silence_end: ([\d.]+)/) || [])[1]);
  if (Number.isFinite(onset) && Math.abs(onset - t.words[0][0]) < 0.4) t.words[0][0] = Math.min(onset, t.words[0][1] - 0.05);
  const start = t.words[0][0]; const end = t.words.at(-1)[1];
  return { file, start, end, len: end - start, words: t.words.map(([a, b]) => [a - start, b - start]) };
}
const place = (c, at) => ({ at: r3(at), end: r3(at + c.len), words: c.words.map(([a, b]) => [r3(a + at), r3(b + at)]), clip: c });

function css(baseUrl) {
  const f = utils.fontUrls(baseUrl);
  return `@font-face{font-family:Lit;src:url(${f.literata})}@font-face{font-family:Lit;src:url(${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-italic.woff2);font-style:italic}
@font-face{font-family:Inter;src:url(${f.inter})}@font-face{font-family:Arm;src:url(${f.armenian})}
*{box-sizing:border-box;margin:0}
:root{--ink:#2A2A33;--muted:#6E6A70;--accent:#B5651D;--paper:#FBF8F2}
html,body{width:1080px;height:1350px;overflow:hidden;background:var(--paper)}
body{position:relative;color:var(--ink);font-family:Inter}
body:before{content:"";position:absolute;inset:0;opacity:.05;background-image:radial-gradient(#000 .6px,transparent .7px);background-size:3px 3px;pointer-events:none;z-index:9}
.pic{position:absolute;left:0;top:0;width:1080px;height:900px;overflow:hidden}
.pic img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 30%;will-change:transform}
.pic:after{content:"";position:absolute;left:0;right:0;bottom:0;height:230px;background:linear-gradient(transparent,var(--paper))}
.sent{position:absolute;left:80px;right:80px;top:910px;text-align:center}
.sent p{font:500 48px/1.32 Lit;text-wrap:balance}
.sent p .x{display:inline-block;will-change:transform,opacity}
.sent p mark{position:relative;background:none;color:inherit;font-style:italic;font-weight:600;padding:0 3px}
.sent p mark:before{content:"";position:absolute;left:0;right:0;top:58%;bottom:4%;background:#F3C98B;transform-origin:left;transform:scaleX(var(--p,0));z-index:-1;border-radius:4px}
.sent .hy{display:block;margin-top:22px;font:500 31px/1.45 Arm;color:var(--muted)}
.brand{position:absolute;left:0;right:0;bottom:36px;text-align:center;font:800 19px Inter;letter-spacing:6px;color:#2A2A3350}`;
}

function sceneBody(c, k) {
  const sl = c.slides[k]; let open = false;
  const words = sl.en.replace(/'/g, '’').split(/\s+/).map((tok, j) => {
    const starts = tok.includes('['); const ends = tok.includes(']'); const inMark = open || starts;
    if (starts && !ends) open = true; if (ends) open = false;
    const plain = esc(tok.replace(/[[\]]/g, ''));
    return `<span class="x" data-j="${j}">${inMark ? plain.replace(/^([^.,!?:;]+)/, '<mark>$1</mark>') : plain}</span>`;
  }).join(' ');
  return `<div class="pic"><img id="img" src="${img(c.id, k + 1)}"></div>
    <div class="sent"><p id="sp">${words}</p><span class="hy" id="hy">${esc(sl.hy)}</span></div>
    <div class="brand">@ENGLISH.READINGROOM</div>`;
}
const SCENE_SCRIPT = `
const clamp=x=>Math.max(0,Math.min(1,x)), ease=x=>1-Math.pow(1-x,3), io=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
let T; window.configure=t=>{T=t};
window.seek=t=>{
  img.style.transform='scale('+(1.0+.06*ease(clamp(t/T.total)))+') translateY('+(-10*ease(clamp(t/T.total)))+'px)';
  [...sp.querySelectorAll('.x')].forEach((x,j)=>{ const w=T.S.words[j]||T.S.words.at(-1); const p=ease(clamp((t-w[0]+.08)/.3));
    x.style.opacity=.14+.86*p; x.style.transform='translateY('+((1-p)*14)+'px)'; x.style.filter=p<1?'blur('+((1-p)*2)+'px)':'none';
    const m=x.querySelector('mark'); if(m) m.style.setProperty('--p',io(clamp((t-w[0])/Math.max(.3,w[1]-w[0]+.15)))); });
  const h=ease(clamp((t-T.S.end-.1)/.6)); hy.style.opacity=h; hy.style.transform='translateY('+((1-h)*16)+'px)';
};`;

function coverBody(c) {
  return `<div style="position:absolute;inset:0;overflow:hidden"><img id="img" src="${img(c.id, 1)}" style="position:absolute;left:0;top:0;width:1080px;height:1080px;object-fit:cover"></div>
    <div style="position:absolute;left:0;right:0;top:640px;bottom:0;background:linear-gradient(transparent,var(--paper) 42%)"></div>
    <div style="position:absolute;left:70px;right:70px;top:1000px;text-align:center">
      <div id="title" style="font:600 italic 96px/1.02 Lit;letter-spacing:-2px;text-wrap:balance">${esc(c.name)}</div>
      <div style="margin-top:20px;font:600 38px Arm;color:var(--muted)">${esc(c.name_hy)} · 6 փաստ անգլերենով</div>
      <div style="margin-top:34px;display:inline-flex;align-items:center;gap:14px;padding:16px 34px;border-radius:99px;background:var(--ink);color:#FBF8F2;font:700 28px Arm">Թերթի՛ր <span id="arrow" style="display:inline-block;font:600 32px Inter">→</span></div>
    </div><div class="brand">@ENGLISH.READINGROOM</div>`;
}
const COVER_SCRIPT = `
const clamp=x=>Math.max(0,Math.min(1,x)), ease=x=>1-Math.pow(1-x,3);
let T; window.configure=t=>{T=t};
window.seek=t=>{ img.style.transform='scale('+(1+.06*ease(clamp(t/T.total)))+')';
  const w=T.V.words; const p=w.length?Math.sin(Math.PI*clamp((t-w[0][0])/Math.max(.4,w.at(-1)[1]-w[0][0]+.1))):0;
  title.style.transform='translateY('+(-8*p)+'px)'; arrow.style.transform='translateX('+(Math.max(0,Math.sin(t*3.2))*10)+'px)'; };`;

function quizBody(c) {
  const letters = ['A', 'B', 'C'];
  return `<div style="position:absolute;left:0;top:0;width:1080px;height:560px;overflow:hidden"><img src="${img(c.id, 1)}" style="width:100%;height:100%;object-fit:cover;object-position:50% 30%"></div>
    <div style="position:absolute;left:0;right:0;top:330px;height:240px;background:linear-gradient(transparent,var(--paper))"></div>
    <div style="position:absolute;left:80px;right:80px;top:560px;text-align:center">
      <div style="font:800 22px Inter;letter-spacing:7px;color:var(--accent)">QUICK QUIZ</div>
      <div style="margin-top:14px;font:600 58px/1.15 Lit;text-wrap:balance">${esc(c.quiz.q)}</div>
      <div style="margin-top:34px;display:grid;gap:16px;text-align:left">${c.quiz.options.map((o, k) => `<div style="display:flex;align-items:center;gap:22px;padding:20px 28px;border-radius:24px;background:#fff;box-shadow:0 12px 28px #3a2f1414">
        <span style="flex:none;width:54px;height:54px;border-radius:50%;background:var(--ink);color:#FBF8F2;display:flex;align-items:center;justify-content:center;font:700 26px Inter">${letters[k]}</span>
        <span style="font:500 40px Lit">${esc(o)}</span></div>`).join('')}</div>
      <div style="margin-top:32px;font:700 31px Arm">Գրի՛ր պատասխանը մեկնաբանություններում</div>
      <div style="margin-top:10px;font:500 26px Arm;color:var(--muted)">Պահի՛ր գրառումը · Դասեր՝ գրե՛ք Direct-ով</div>
    </div><div class="brand">@ENGLISH.READINGROOM</div>`;
}

function voiceTrack(plays, total, out) {
  const args = ['-y', '-hide_banner', '-loglevel', 'error'];
  plays.forEach((p) => args.push('-i', p.clip.file));
  const chains = plays.map((p, i) => {
    const from = Math.max(0, p.clip.start - 0.06); const ms = Math.round((p.at - (p.clip.start - from)) * 1000);
    return `[${i}:a]aresample=48000,atrim=${from.toFixed(3)}:${(p.clip.end + 0.3).toFixed(3)},asetpts=PTS-STARTPTS,afade=t=out:st=${(p.clip.end - from + 0.1).toFixed(3)}:d=0.2,adelay=${ms}|${ms}[v${i}]`;
  });
  args.push('-filter_complex', `${chains.join(';')};${plays.map((_, i) => `[v${i}]`).join('')}amix=inputs=${plays.length}:normalize=0,apad=whole_dur=${total}[a]`, '-map', '[a]', '-ac', '2', '-c:a', 'pcm_s16le', out);
  const r = spawnSync('ffmpeg', args, { encoding: 'utf8' }); if (r.status !== 0) throw new Error(r.stderr);
}

async function page(browser, baseUrl, name, body, script) {
  const work = path.join(utils.ROOT, '.render-work', `countries-${name}.html`);
  fs.writeFileSync(work, `<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>${css(baseUrl)}</style></head><body>${body}${script ? `<script>${script}</script>` : ''}</body></html>`);
  const p = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(p, `${baseUrl}${utils.renderHtmlPath(work)}`, 1080, 1350);
  await p.evaluate(() => Promise.all([document.fonts.load('500 48px Lit', 'Ab'), document.fonts.load('italic 600 48px Lit', 'Ab'), document.fonts.load('600 38px Arm', 'Աբ'), document.fonts.load('800 20px Inter', 'Ab'), document.fonts.ready, ...[...document.images].map((i) => i.decode().catch(() => null))]));
  const bad = await p.evaluate(() => [...document.querySelectorAll('.sent,#title')].filter((e) => e.getBoundingClientRect().bottom > 1290 || e.scrollWidth > e.clientWidth + 2).map((e) => e.textContent.slice(0, 50)));
  if (errors.length || bad.length) throw new Error(`${name}: ${errors.join(' | ')} ${JSON.stringify(bad)}`);
  return p;
}

async function video(browser, baseUrl, out, name, body, script, T, plays) {
  const p = await page(browser, baseUrl, name, body, script);
  await p.evaluate((t) => { window.configure(t); window.seek(0); }, T);
  const frames = path.join(utils.OUTPUT, `.frames-countries-${name}`); fs.rmSync(frames, { recursive: true, force: true });
  await utils.renderFrames(p, T.total, frames, path.join(out, `${name}-poster.jpg`), T.total - 0.1, FPS);
  await p.close();
  const wav = path.join(utils.ROOT, '.render-work', `countries-${name}.wav`); voiceTrack(plays, T.total, wav);
  const mp4 = path.join(out, `${name}.mp4`); utils.encodeVideo(frames, wav, 0, T.total, mp4, FPS);
  const info = utils.verifyVideo(mp4); fs.rmSync(frames, { recursive: true, force: true });
  console.log(`${name}: ${JSON.stringify(info)}`);
}

async function main() {
  const c = DATA.countries.find((x) => x.id === process.argv[2]);
  if (!c) throw new Error(`Unknown country: ${process.argv[2]}`);
  const out = path.join(utils.OUTPUT, `countries-${c.id}`); fs.rmSync(out, { recursive: true, force: true }); utils.ensureDirectory(out);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try {
    const V = place(clip(c.id, 'title'), 0.8);
    await video(browser, baseUrl, out, '01', coverBody(c), COVER_SCRIPT, { V, total: r3(Math.max(4.5, V.end + 2.4)) }, [V]);
    for (let k = 0; k < c.slides.length; k += 1) {
      const S = place(clip(c.id, `s${k}`), 0.7);
      await video(browser, baseUrl, out, String(k + 2).padStart(2, '0'), sceneBody(c, k), SCENE_SCRIPT, { S, total: r3(S.end + 2.6) }, [S]);
    }
    const q = await page(browser, baseUrl, 'quiz', quizBody(c));
    await q.screenshot({ path: path.join(out, `${String(c.slides.length + 2).padStart(2, '0')}.jpg`), type: 'jpeg', quality: 93 }); await q.close();
    console.log(`done → ${out}`);
  } finally { await browser.close(); server.close(); }
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

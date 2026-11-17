// Animated "A Day in Opposites" carousel: the cover and every pair slide are short 4:5 videos with voice
// (each word lights up as it is spoken, the picture's light moves to the person doing the action); the quiz stays a still.
// Usage: node carousels/render_opposites_video.js <day-id>   -> outputs/english-reels-samples/opposites-<id>-video/01.mp4 … 07.jpg
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('../reels/render_utils');

process.env.VIDEO_SIZE = '1080x1350';
if (!process.env.MUSIC_TRACK) process.env.MUSIC_TRACK = path.join(utils.ROOT, 'music', 'warm-tea.m4a');
const FPS = 30;
const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'carousels/data/opposites.json'), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const quotes = (s) => s.replace(/(^|[\s([])'/g, '$1‘').replace(/'/g, '’');
const r3 = (x) => Number(x.toFixed(3));

// A voice clip with word times moved onto the real first sound (the service runs a little early).
function clip(id, name) {
  const dir = path.join(utils.ROOT, 'assets', 'opposites', id);
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
:root{--ink:#2B1E14;--muted:#6B5646;--accent:#C0652A;--paper:#FAF0E4;--card:#FFF8F0}
html,body{width:1080px;height:1350px;overflow:hidden;background:var(--paper)}
body{position:relative;color:var(--ink);font-family:Inter}
.pic{position:absolute;left:0;top:0;width:1080px;height:860px;overflow:hidden}
.pic img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 38%;will-change:transform}
.spot{position:absolute;inset:0;pointer-events:none}
.pic:after{content:"";position:absolute;left:0;right:0;bottom:0;height:190px;background:linear-gradient(transparent,var(--paper))}
.pair{position:absolute;left:56px;right:56px;top:800px;display:grid;grid-template-columns:1fr 108px 1fr;align-items:center;z-index:4}
.w{text-align:center}
.w b{display:block;font:700 76px/1 Lit;letter-spacing:-1.5px;white-space:nowrap}
.w b .c{display:inline-block;will-change:transform,opacity,filter}
.w .sub span{display:block;margin-top:14px;font:600 36px Arm}
.w small{display:block;margin-top:8px;font:500 27px Arm;color:var(--muted)}
.w small em{font:500 25px Inter;font-style:normal;opacity:.75}
.w .sub{will-change:transform,opacity}
.sw{width:92px;height:92px;margin:0 auto;border-radius:50%;background:var(--ink);color:#FFF8F0;display:flex;align-items:center;justify-content:center;font:600 46px Inter;box-shadow:0 14px 30px #2B1E1440}
.sent{position:absolute;left:70px;right:70px;top:1062px;text-align:center;padding-top:34px}
.sent .rule{position:absolute;top:0;left:50%;width:70px;height:3px;margin-left:-35px;border-radius:3px;background:#C0652A66;transform-origin:center}
.sent p{font:500 41px/1.35 Lit}
.sent p .x{display:inline-block;will-change:transform,opacity}
.sent p mark{position:relative;background:none;color:inherit;font-style:italic;font-weight:600;padding:0 3px}
.sent p mark:before{content:"";position:absolute;left:0;right:0;top:58%;bottom:4%;background:#F3B56599;transform-origin:left;transform:scaleX(var(--p,0));z-index:-1}
.sent > span{display:block;margin-top:14px;font:500 29px/1.45 Arm;color:var(--muted)}
.brand{position:absolute;left:0;right:0;bottom:34px;text-align:center;font:800 19px Inter;letter-spacing:6px;color:#2B1E1455}`;
}

const chars = (s) => [...s].map((c) => (c === ' ' ? ' ' : `<span class="c">${esc(c)}</span>`)).join('');

function pairBody(day, p, i) {
  const img = `data:image/jpeg;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets', 'opposites', day.id, `${i + 2}.jpg`)).toString('base64')}`;
  const w = (x, side) => `<div class="w" id="${side}"><b>${chars(x.en)}</b><div class="sub"><span>${esc(x.hy)}</span><small>«${esc(x.say)}» <em>${esc(x.ipa)}</em></small></div></div>`;
  let open = false;
  const sent = quotes(p.sentence).split(/\s+/).map((tok, j) => {
    const starts = tok.includes('['); const ends = tok.includes(']'); const inMark = open || starts;
    if (starts && !ends) open = true; if (ends) open = false;
    const plain = esc(tok.replace(/[[\]]/g, ''));
    const html = inMark ? plain.replace(/^([^.,!?:;]+)/, '<mark>$1</mark>') : plain;
    return `<span class="x" data-j="${j}">${html}</span>`;
  }).join(' ');
  return `<div class="pic"><img id="img" src="${img}"><div class="spot" id="spot"></div></div>
    <div class="pair">${w(p.left, 'L')}<div class="sw" id="sw">⇄</div>${w(p.right, 'R')}</div>
    <div class="sent" id="sent"><div class="rule" id="rule"></div><p id="sp">${sent}</p><span id="shy">${esc(p.sentence_hy)}</span></div>
    <div class="brand">@ENGLISH.READINGROOM</div>`;
}

// Everything that moves, driven by time t (seconds) so every frame is exact.
const PAIR_SCRIPT = `
const clamp=x=>Math.max(0,Math.min(1,x)), ease=x=>1-Math.pow(1-x,3), back=x=>{const c=1.6;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)}, io=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
let T; window.configure=t=>{T=t};
function word(el,at){ [...el.querySelectorAll('.c')].forEach((c,k)=>{ const p=ease(clamp((window._t-at-k*.035)/.55));
  c.style.opacity=p; c.style.transform='translateY('+((1-p)*46)+'px) rotate('+((1-p)*-6)+'deg)'; c.style.filter='blur('+((1-p)*7)+'px)'; }); }
function sub(el,at){ const p=ease(clamp((window._t-at)/.6)); el.style.opacity=p; el.style.transform='translateY('+((1-p)*18)+'px)'; }
window.seek=t=>{ window._t=t;
  img.style.transform='scale('+(1.07-.07*ease(clamp(t/T.total)))+')';
  // the light follows the word: left person while the left word is said, then the right one, then both
  const lf=clamp((t-T.L.at+.3)/.5)*(1-clamp((t-T.R.at+.3)/.5)), rf=clamp((t-T.R.at+.3)/.5)*(1-clamp((t-T.S.at+.2)/.6));
  const cx=50+(rf-lf)*28, a=.3*Math.max(lf,rf);
  spot.style.background='radial-gradient(60% 85% at '+cx+'% 45%,transparent 45%,rgba(43,30,20,'+a.toFixed(3)+') 100%)';
  word(L.querySelector('b'),T.L.at-.18); sub(L.querySelector('.sub'),T.L.end+.05);
  word(R.querySelector('b'),T.R.at-.18); sub(R.querySelector('.sub'),T.R.end+.05);
  const s=clamp((t-T.L.end-.1)/.55); sw.style.transform='scale('+(s?back(s):0)+') rotate('+((1-ease(s))*-180+ease(clamp((t-T.R.at+.1)/.5))*180)+'deg)';
  // sentence: the line draws, then each word comes up as it is spoken, the highlights sweep under the two verbs
  const rp=io(clamp((t-T.S.at+.5)/.5)); rule.style.transform='scaleX('+rp+')';
  [...sp.querySelectorAll('.x')].forEach((x,j)=>{ const w=T.S.words[j]||T.S.words.at(-1); const p=ease(clamp((t-w[0]+.08)/.28));
    x.style.opacity=.12+.88*p; x.style.transform='translateY('+((1-p)*12)+'px)';
    const m=x.querySelector('mark'); if(m) m.style.setProperty('--p',io(clamp((t-w[0])/Math.max(.3,w[1]-w[0]+.15)))); });
  sp.style.opacity=clamp((t-T.S.at+.6)/.4);
  sub(shy,T.S.end+.15);
};`;

function coverBody(day) {
  const img = `data:image/jpeg;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets', 'opposites', day.id, '1.jpg')).toString('base64')}`;
  const words = [...day.title.split(' ').map((w) => ({ w, em: false })), { w: day.title_em, em: true }];
  return `<div style="position:absolute;inset:0;overflow:hidden"><img id="img" src="${img}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 20%"></div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:640px;background:linear-gradient(transparent,var(--paper) 46%)"></div>
    <div id="glow" style="position:absolute;width:700px;height:700px;border-radius:50%;background:radial-gradient(circle,#FFF1D866,transparent 65%);mix-blend-mode:screen;pointer-events:none"></div>
    <div style="position:absolute;left:70px;right:70px;bottom:120px;text-align:center">
      <div style="font:800 22px Inter;letter-spacing:7px;color:var(--accent)">10 WORDS · 5 PAIRS · ${esc(day.level)}</div>
      <div id="title" style="margin-top:18px;font:700 108px/1 Lit;letter-spacing:-3px">${words.map((x) => `<span class="tw" style="display:inline-block${x.em ? ';color:var(--accent);font-style:italic' : ''}">${esc(x.w)}</span>`).join(' ')}</div>
      <div style="margin-top:22px;font:600 38px Arm;color:var(--muted)">${esc(day.title_hy)}</div>
      <div style="margin-top:38px;display:inline-flex;align-items:center;gap:14px;padding:18px 36px;border-radius:99px;background:var(--ink);color:#FFF8F0;font:700 30px Arm">Թերթի՛ր <span id="arrow" style="display:inline-block;font:600 34px Inter">→</span></div>
    </div><div class="brand">@ENGLISH.READINGROOM</div>`;
}
// The cover is complete from the first frame (it is also the thumbnail); only light and a gentle beat move.
const COVER_SCRIPT = `
const clamp=x=>Math.max(0,Math.min(1,x)), ease=x=>1-Math.pow(1-x,3);
let T; window.configure=t=>{T=t};
window.seek=t=>{
  img.style.transform='scale('+(1+.06*ease(clamp(t/T.total)))+')';
  glow.style.left=(-200+t/T.total*900)+'px'; glow.style.top=(260+Math.sin(t*1.3)*60)+'px';
  [...document.querySelectorAll('.tw')].forEach((el,j)=>{ const w=T.V.words[j]; const p=w?Math.sin(Math.PI*clamp((t-w[0])/Math.max(.25,w[1]-w[0]+.1))):0;
    el.style.transform='translateY('+(-10*p)+'px) scale('+(1+.05*p)+')'; });
  arrow.style.transform='translateX('+(Math.max(0,Math.sin(t*3.2))*10)+'px)';
};`;

function voiceTrack(plays, total, out) {
  const args = ['-y', '-hide_banner', '-loglevel', 'error'];
  plays.forEach((p) => args.push('-i', p.clip.file));
  const chains = plays.map((p, i) => {
    const from = Math.max(0, p.clip.start - 0.06); const ms = Math.round((p.at - (p.clip.start - from)) * 1000);
    return `[${i}:a]aresample=48000,atrim=${from.toFixed(3)}:${(p.clip.end + 0.3).toFixed(3)},asetpts=PTS-STARTPTS,afade=t=out:st=${(p.clip.end - from + 0.1).toFixed(3)}:d=0.2,adelay=${ms}|${ms}[v${i}]`;
  });
  args.push('-filter_complex', `${chains.join(';')};${plays.map((_, i) => `[v${i}]`).join('')}amix=inputs=${plays.length}:normalize=0,apad=whole_dur=${total}[a]`,
    '-map', '[a]', '-ac', '2', '-c:a', 'pcm_s16le', out);
  const r = spawnSync('ffmpeg', args, { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(r.stderr);
}

async function renderVideo(browser, baseUrl, name, body, script, T, plays, out) {
  const work = path.join(utils.ROOT, '.render-work', `${name}.html`);
  fs.writeFileSync(work, `<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>${css(baseUrl)}</style></head><body>${body}<script>${script}</script></body></html>`);
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(work)}`, 1080, 1350);
  await page.evaluate((t) => { window.configure(t); window.seek(0); }, T);
  await page.evaluate(() => Promise.all([document.fonts.load('700 76px Lit', 'Ab'), document.fonts.load('italic 600 41px Lit', 'Ab'), document.fonts.load('500 41px Lit', 'Ab'), document.fonts.load('600 36px Arm', 'Աբ'), document.fonts.load('800 20px Inter', 'Ab'), document.fonts.ready, ...[...document.images].map((i) => i.decode().catch(() => null))]));
  const bad = await page.evaluate(() => [...document.querySelectorAll('.w b,.sent p,#title')].filter((e) => e.getBoundingClientRect().right > 1040 || e.getBoundingClientRect().left < 40).map((e) => e.textContent));
  if (errors.length || bad.length) throw new Error(`${name}: ${errors.join(' | ')} ${JSON.stringify(bad)}`);
  const frames = path.join(utils.OUTPUT, `.frames-${name}`); fs.rmSync(frames, { recursive: true, force: true });
  await utils.renderFrames(page, T.total, frames, path.join(out, `${name}-poster.jpg`), T.total - 0.1, FPS);
  await page.close();
  const wav = path.join(utils.ROOT, '.render-work', `${name}.wav`); voiceTrack(plays, T.total, wav);
  const mp4 = path.join(out, `${name}.mp4`);
  utils.encodeVideo(frames, wav, 0, T.total, mp4, FPS, plays.slice(1).map((p) => ({ file: 'sfx-pop.wav', at: p.at - 0.15, gain: 0.05 })));
  const info = utils.verifyVideo(mp4); fs.rmSync(frames, { recursive: true, force: true });
  console.log(`${name}: ${JSON.stringify(info)}`);
}

async function main() {
  const day = DATA.days.find((d) => d.id === process.argv[2]);
  if (!day) throw new Error(`Unknown day: ${process.argv[2]}`);
  const out = path.join(utils.OUTPUT, `opposites-${day.id}-video`); fs.rmSync(out, { recursive: true, force: true }); utils.ensureDirectory(out);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try {
    const V = place(clip(day.id, 'title'), 0.7);
    await renderVideo(browser, baseUrl, '01', coverBody(day), COVER_SCRIPT, { V, total: r3(Math.max(5, V.end + 2.6)) }, [V], out);
    for (let i = 0; i < day.pairs.length; i += 1) {
      const L = place(clip(day.id, `p${i}l`), 0.6);
      const R = place(clip(day.id, `p${i}r`), L.end + 1.0);
      const S = place(clip(day.id, `p${i}s`), R.end + 1.1);
      const T = { L, R, S, total: r3(S.end + 2.2) };
      await renderVideo(browser, baseUrl, String(i + 2).padStart(2, '0'), pairBody(day, day.pairs[i], i), PAIR_SCRIPT, T, [L, R, S], out);
    }
    // the quiz is a still: reuse the slide from the picture carousel
    const still = path.join(utils.OUTPUT, `opposites-${day.id}`, `${String(day.pairs.length + 2).padStart(2, '0')}.jpg`);
    spawnSync('node', [path.join(__dirname, 'render_opposites.js'), day.id], { stdio: 'inherit' });
    fs.copyFileSync(still, path.join(out, path.basename(still)));
    console.log(`done → ${out}`);
  } finally { await browser.close(); server.close(); }
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

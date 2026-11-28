// Word set reel: 12 painted pictures in a grid; one by one each picture comes forward as a big card with the word,
// its British pronunciation and the Armenian, while the voice says the word twice. At the end the whole grid
// with every word, to pause and repeat.
// Usage: node reels/render_words.js <set-id>        (STILLS=2,7.4,30 saves a few moments as pictures instead)
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/words.json'), 'utf8'));
const FPS = 30;
const r3 = (x) => Number(x.toFixed(3));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const curly = (s) => s.replace(/(^|[\s(])'/g, '$1‘').replace(/'/g, '’');

function seconds(file) {
  const r = spawnSync(utils.FFprobe || 'ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file], { encoding: 'utf8' });
  return Number(r.stdout.trim());
}

// Every moment of the reel, in seconds.
function timeline(set) {
  const dir = path.join(utils.ROOT, 'assets/words', set.id);
  const clip = (name) => { const file = path.join(dir, `${name}.mp3`); if (!fs.existsSync(file)) throw new Error(`${set.id}: no voice ${name}.mp3`); return { file, len: seconds(file) }; };
  const plays = [];
  const intro = clip('intro');
  plays.push({ ...intro, at: 0.5 });
  const INTRO = Math.max(3.6, 0.5 + intro.len + 0.6);
  const cards = [];
  let t = INTRO;
  set.words.forEach((_, k) => {
    const c = clip(String(k + 1).padStart(2, '0'));
    const sayAt = t + 0.55; const again = sayAt + c.len + 0.5;
    plays.push({ ...c, at: sayAt }, { ...c, at: again });
    const len = Math.max(2.9, again + c.len + 0.55 - t);
    cards.push({ at: r3(t), len: r3(len) }); t += len;
  });
  const outro = clip('outro');
  plays.push({ ...outro, at: t + 0.6 });
  const OUTRO = Math.max(4.5, 0.6 + outro.len + 1.6);
  return { intro: r3(INTRO), cards, outroAt: r3(t), total: r3(t + OUTRO), plays };
}

function voiceTrack(T, out) {
  const args = ['-y', '-hide_banner', '-loglevel', 'error'];
  T.plays.forEach((p) => args.push('-i', p.file));
  const chains = T.plays.map((p, i) => { const ms = Math.round(p.at * 1000); return `[${i}:a]aresample=48000,adelay=${ms}|${ms}[v${i}]`; });
  args.push('-filter_complex', `${chains.join(';')};${T.plays.map((_, i) => `[v${i}]`).join('')}amix=inputs=${T.plays.length}:normalize=0,apad=whole_dur=${T.total}[a]`,
    '-map', '[a]', '-ac', '2', '-c:a', 'pcm_s16le', out);
  const r = spawnSync(utils.FFmpeg, args, { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`Voice track failed: ${r.stderr}`);
}

function page(baseUrl, set, T) {
  const f = `${baseUrl}/node_modules/@fontsource-variable`;
  const pics = set.words.map((_, k) => `${baseUrl}/assets/words/${set.id}/${String(k + 1).padStart(2, '0')}.jpg`);
  const tiles = set.words.map((w, k) => `<div class="tile" id="t${k}"><div class="ph"><img src="${pics[k]}"></div><div class="lab">${esc(w[0])}</div></div>`).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:L;src:url(${f}/literata/files/literata-latin-wght-normal.woff2)}
@font-face{font-family:L;font-style:italic;src:url(${f}/literata/files/literata-latin-wght-italic.woff2)}
@font-face{font-family:I;src:url(${f}/inter/files/inter-latin-wght-normal.woff2)}
@font-face{font-family:I;src:url(${f}/inter/files/inter-latin-ext-wght-normal.woff2);unicode-range:U+0100-02AF,U+1D00-1DBF}
@font-face{font-family:A;src:url(${f}/noto-sans-armenian/files/noto-sans-armenian-armenian-wght-normal.woff2)}
*{margin:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden}
body{background:radial-gradient(ellipse 90% 70% at 50% 45%,#FBF6EC 0%,#F3EADB 70%,#EADFCB 100%);font-family:I;color:#17183A;position:relative}
.head{position:absolute;left:0;right:0;top:150px;text-align:center}
.head h1{font:600 86px/1.05 L;letter-spacing:.5px}
.head h1 i{font-style:italic;color:#6A49E2}
.head .hy{margin-top:14px;font:500 40px A;color:#5A3B8C}
.orn{display:flex;align-items:center;justify-content:center;gap:14px;margin:22px auto 0;width:300px}.orn i{flex:1;height:2px;background:linear-gradient(90deg,transparent,#E9C46A,transparent)}.orn b{width:12px;height:12px;background:#E9C46A;transform:rotate(45deg)}
.grid{position:absolute;left:78px;top:440px;width:924px}
.tile{position:absolute;width:286px;height:330px;transform-origin:50% 50%}
.ph{width:286px;height:286px;border-radius:30px;background:#FFFDF8;box-shadow:0 10px 26px rgba(23,24,58,.12),0 2px 6px rgba(23,24,58,.06);overflow:hidden;display:flex;align-items:center;justify-content:center}
.ph img{width:100%;height:100%;object-fit:cover}
.lab{height:44px;margin-top:8px;text-align:center;font:600 34px L;color:#17183A;opacity:0}
.dim{position:absolute;inset:0;background:rgba(246,239,227,.72);opacity:0}
.card{position:absolute;left:90px;top:360px;width:900px;border-radius:52px;background:#FFFDF8;box-shadow:0 40px 90px rgba(23,24,58,.22),0 8px 22px rgba(23,24,58,.1);overflow:hidden;opacity:0;transform-origin:50% 40%}
.card .big{width:900px;height:900px;display:block;object-fit:cover}
.card .tx{padding:34px 40px 52px;text-align:center}
.card .w{font:600 132px/1.0 L;color:#17183A}
.card .ipa{margin-top:18px;font:500 50px I;color:#6A49E2;letter-spacing:.5px}
.card .hy{margin-top:16px;font:500 56px A;color:#5A3B8C}
.end{position:absolute;left:0;right:0;top:160px;text-align:center;opacity:0}
.end .en{font:600 86px/1.05 L}.end .en i{font-style:italic;color:#6A49E2}
.end .hy{margin-top:14px;font:500 40px A;color:#5A3B8C}
</style></head><body>
<div class="head" id="head"><h1>${esc(set.title).replace(/(\S+)$/, '<i>$1</i>')}</h1><div class="hy">${esc(set.title_hy)}</div><div class="orn"><i></i><b></b><i></i></div></div>
<div class="grid" id="grid">${tiles}</div>
<div class="dim" id="dim"></div>
<div class="card" id="card"><img class="big" id="cimg"><div class="tx"><div class="w" id="cw"></div><div class="ipa" id="ci"></div><div class="hy" id="ch"></div></div></div>
<div class="end" id="end"><div class="en">Say them <i>again!</i></div><div class="hy">Պահի՛ր ու կրկնի՛ր</div></div>
<script>
const T=${JSON.stringify({ intro: T.intro, cards: T.cards, outroAt: T.outroAt, total: T.total })};
const W=${JSON.stringify(set.words.map((w) => [curly(w[0]), w[1], w[2]]))};
const P=${JSON.stringify(pics)};
const cl=(x)=>Math.max(0,Math.min(1,x)); const ease=(x)=>{x=cl(x);return x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;}; const back=(x)=>{x=cl(x);const c=1.5;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2);};
const pos=(k)=>({x:(k%3)*319,y:Math.floor(k/3)*345});
// the 12 tiles sit a little tighter during the lesson and open up at the end to show the words under them
const tiles=[...document.querySelectorAll('.tile')];
window.seek=(t)=>{
  const head=document.getElementById('head'); head.style.opacity=ease(t/0.7)*(1-ease((t-T.outroAt)/0.5)); head.style.transform='translateY('+(1-ease(t/0.7))*-30+'px)';
  const open=ease((t-T.outroAt)/0.9);
  tiles.forEach((el,k)=>{const p=pos(k); const ap=0.35+k*0.11; const s=back((t-ap)/0.55); const y=p.y;
    el.style.left=p.x+'px'; el.style.top=y+'px'; el.style.opacity=cl((t-ap)/0.25);
    let sc=0.6+0.4*s; let lab=open;
    T.cards.forEach((c,i)=>{ if(i<k||i>k) return; const u=t-c.at; if(u>-0.2&&u<c.len) sc*=1+0.06*Math.sin(Math.PI*cl(u/0.5)); });
    el.style.transform='scale('+sc+')'; el.querySelector('.lab').style.opacity=lab; });
  // the card of the word being learnt
  let cur=-1,u=0; T.cards.forEach((c,i)=>{ if(t>=c.at&&t<c.at+c.len){cur=i;u=t-c.at;} });
  const card=document.getElementById('card'), dim=document.getElementById('dim');
  if(cur<0){card.style.opacity=0; dim.style.opacity=0; } else {
    const c=T.cards[cur]; const inn=ease(u/0.5), out=ease((u-(c.len-0.42))/0.42); const v=inn*(1-out);
    const p=pos(cur); const gx=78+p.x+143, gy=440+p.y+143;   // centre of its tile
    const cx=540, cy=360+620;
    const x=gx+(cx-gx)*v, y=gy+(cy-gy)*v; const s=0.3+0.7*v;
    card.style.opacity=cl(v*1.6); card.style.transform='translate('+(x-cx)+'px,'+(y-cy)+'px) scale('+s+')';
    dim.style.opacity=v;
    if(card.dataset.k!=cur){ card.dataset.k=cur; document.getElementById('cimg').src=P[cur]; document.getElementById('cw').textContent=W[cur][0]; document.getElementById('ci').textContent=W[cur][1]; document.getElementById('ch').textContent=W[cur][2]; }
    const tx=card.querySelector('.tx'); tx.style.opacity=cl((u-0.3)/0.3)*(1-out);
    const tile=tiles[cur]; tile.style.opacity=1-v; }
  const end=document.getElementById('end'); end.style.opacity=ease((t-T.outroAt-0.5)/0.6); end.style.transform='translateY('+(1-ease((t-T.outroAt-0.5)/0.6))*24+'px)';
};
window.seek(0);
</script></body></html>`;
}

async function main() {
  const id = process.argv[2];
  const set = DATA.sets.find((s) => s.id === id);
  if (!set) throw new Error(`Unknown word set: ${id}`);
  const T = timeline(set);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, args: ['--allow-file-access-from-files'] });
  try {
    const name = `words-${set.id}`;
    const work = path.join(utils.ROOT, '.render-work'); utils.ensureDirectory(work); utils.ensureDirectory(utils.OUTPUT);
    const htmlPath = path.join(work, `${name}.html`);
    fs.writeFileSync(htmlPath, page(baseUrl, set, T), 'utf8');
    const pg = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: utils.DPR });
    const errors = await utils.preparePage(pg, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
    await pg.evaluate(() => Promise.all([document.fonts.load('600 80px L', 'Ab'), document.fonts.load('italic 80px L', 'Ab'), document.fonts.load('40px A', 'Հայ'),
      document.fonts.load('500 50px I', 'Abæʌ')]).then(() => document.fonts.ready));
    await pg.evaluate(() => Promise.all([...document.images].map((i) => (i.complete ? 0 : new Promise((r) => { i.onload = r; i.onerror = r; })))));
    const check = await pg.evaluate(() => ({ armenian: document.fonts.check('40px A', 'Հայ'), broken: [...document.images].filter((i) => i.src && !i.naturalWidth).length }));
    console.log(`${name}: ${JSON.stringify(check)} total ${T.total}s`);
    if (!check.armenian || check.broken) throw new Error(`${name}: fonts or pictures missing`);
    if (process.env.STILLS) {
      for (const at of process.env.STILLS.split(',').map(Number)) {
        await pg.evaluate((x) => window.seek(x), at);
        await pg.screenshot({ path: path.join(utils.OUTPUT, `${name}-at-${at}.jpg`), type: 'jpeg', quality: 88 });
      }
      return;
    }
    const frames = path.join(utils.OUTPUT, `.frames-${name}`);
    const videoPath = path.join(utils.OUTPUT, `${name}.mp4`);
    await utils.renderFrames(pg, T.total, frames, path.join(utils.OUTPUT, `${name}.png`), T.cards[0].at + 1.2, FPS);
    if (errors.length) throw new Error(`Template errors: ${errors.join(' | ')}`);
    const voice = path.join(work, `${name}.wav`);
    voiceTrack(T, voice);
    if (set.music && !process.env.MUSIC_TRACK) process.env.MUSIC_TRACK = path.join(utils.ROOT, 'music', set.music);
    utils.encodeVideo(frames, voice, 0, T.total, videoPath, FPS, T.cards.map((c) => ({ file: 'sfx-pop.wav', at: c.at + 0.08, gain: 0.18 })));
    const info = utils.verifyVideo(videoPath);
    fs.rmSync(frames, { recursive: true, force: true });
    console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  } finally { await browser.close(); server.close(); }
}

if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
module.exports = { timeline };

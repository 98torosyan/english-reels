// Story card layers for an Instagram Story: the picture full screen with a soft shade (bg.png, 2592×4608) and a gold
// book frame with the title, author line and a one-line hook (overlay.png, transparent, 2160×3840).
// Usage: node reels/story_card.js <spec.json> <outdir>   spec: {picture, title, author, hook, line}
const { chromium } = require('playwright-core'); const fs = require('fs'); const path = require('path');
const root = path.resolve(__dirname, '..');
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const out = process.argv[3];
const font = (s) => 'data:font/woff2;base64,' + fs.readFileSync(`${root}/node_modules/@fontsource-variable/playfair-display/files/playfair-display-latin-wght-${s}.woff2`).toString('base64');
const pic = 'data:image/jpeg;base64,' + fs.readFileSync(spec.picture).toString('base64');
const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
const corner = `<svg viewBox="0 0 120 120" width="120" height="120"><g fill="none" stroke="url(#g)" stroke-width="2.4" stroke-linecap="round">
<path d="M8 112 V40 Q8 8 40 8 H112"/><path d="M22 112 V48 Q22 22 48 22 H112" stroke-width="1.2"/><path d="M40 8 Q44 30 22 34"/>
<circle cx="40" cy="40" r="7"/><path d="M47 40 Q70 40 78 22 M40 47 Q40 70 22 78"/><path d="M58 34 q8 -10 18 -6 M34 58 q-10 8 -6 18"/></g>
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F7E3A8"/><stop offset=".6" stop-color="#C9973F"/><stop offset="1" stop-color="#E9C77A"/></linearGradient></defs></svg>`;
const page = (layer) => `<!doctype html><html><head><style>
@font-face{font-family:P;src:url(${font('italic')});font-style:italic}@font-face{font-family:P;src:url(${font('normal')})}
*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;overflow:hidden;position:relative;font-family:P;background:${layer === 'bg' ? '#140c07' : 'transparent'}}
.bg{position:absolute;inset:0;background:url(${pic}) ${spec.focus || '45% 30%'}/cover no-repeat}
.sh{position:absolute;inset:0;background:linear-gradient(rgba(14,9,5,.72) 0,rgba(14,9,5,.35) 12%,rgba(14,9,5,0) 22%,rgba(14,9,5,0) 50%,rgba(14,9,5,.82) 66%,rgba(14,9,5,.9) 100%),radial-gradient(110% 70% at 50% 40%,transparent 55%,rgba(10,6,3,.5))}
.dim{position:absolute;inset:150px 56px 250px;border-radius:6px;box-shadow:0 0 70px 2400px rgba(8,5,3,.62)}
.b1{position:absolute;inset:150px 56px 250px;border:3px solid #C9973F;border-radius:6px;box-shadow:0 0 0 10px rgba(0,0,0,.25),0 0 30px rgba(0,0,0,.4)}
.b2{position:absolute;inset:172px 78px 272px;border:1.2px solid rgba(233,199,122,.7);border-radius:3px}
.c{position:absolute;width:120px;height:120px}.c1{top:134px;left:40px}.c2{top:134px;right:40px;transform:scaleX(-1)}
.c3{bottom:234px;left:40px;transform:scaleY(-1)}.c4{bottom:234px;right:40px;transform:scale(-1)}
.top{position:absolute;top:225px;width:100%;text-align:center;color:#E9C77A;font:600 26px P;letter-spacing:10px;text-shadow:0 0 6px rgba(0,0,0,.9),0 2px 18px rgba(0,0,0,.9)}
.box{position:absolute;bottom:300px;width:100%;padding:0 120px;text-align:center}
h1{font:italic 600 ${spec.title.length > 16 ? 92 : 112}px/1.05 P;background:linear-gradient(#F7E3A8,#C9973F 60%,#E9C77A);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 4px 14px rgba(0,0,0,.6))}
.o{margin:24px auto 0;width:380px;display:flex;align-items:center;gap:16px}
.o i{flex:1;height:1px;background:linear-gradient(90deg,transparent,#C9973F,transparent)}.o b{width:12px;height:12px;background:#C9973F;transform:rotate(45deg)}
p{margin-top:34px;color:#F1E6D2;font:italic 400 50px/1.35 P}.s{margin-top:22px;color:#B9A585;font:400 28px P;letter-spacing:3px}
</style></head><body>${layer === 'bg' ? '<div class=bg></div><div class=sh></div>' : `
<div class=dim></div><div class=b1></div><div class=b2></div>${[1, 2, 3, 4].map((k) => `<div class="c c${k}">${corner}</div>`).join('')}
<div class=top>${esc(spec.author || 'ENGLISH READING ROOM').toUpperCase()}</div>
<div class=box><h1>${esc(spec.title)}</h1><div class=o><i></i><b></b><i></i></div>
<p>${esc(spec.hook).replace(/\n/g, '<br>')}</p><div class=s>${esc(spec.line || 'READ AND LISTEN IN EASY ENGLISH')}</div></div>`}</body></html>`;
(async () => {
  const exe = [process.env.CHROME_PATH, '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].find((p) => p && fs.existsSync(p));
  const b = await chromium.launch(exe ? { executablePath: exe } : {});
  for (const [layer, scale] of [['bg', 2.4], ['overlay', 2]]) {
    const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: scale });
    await p.setContent(page(layer)); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(200);
    await p.screenshot({ path: `${out}/${layer === 'bg' ? 'bg' : 'overlay'}.png`, omitBackground: layer !== 'bg' }); await p.close();
  }
  await b.close();
})();

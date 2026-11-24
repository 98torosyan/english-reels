// Story card layers for an Instagram Story: the picture full screen with a soft shade (bg.png, 2592×4608) and a gold
// book frame with the title, author line and a one-line hook (overlay.png, transparent, 2160×3840).
// Usage: node reels/story_card.js <spec.json> <outdir>   spec: {picture, title, author, hook, line}
const { chromium } = require('playwright-core'); const fs = require('fs'); const path = require('path');
const root = path.resolve(__dirname, '..');
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const out = process.argv[3];
const font = (s) => 'data:font/woff2;base64,' + fs.readFileSync(`${root}/node_modules/@fontsource-variable/playfair-display/files/playfair-display-latin-wght-${s}.woff2`).toString('base64');
const pic = 'data:image/jpeg;base64,' + fs.readFileSync(spec.picture).toString('base64');
const fnt = (pkg, file) => 'data:font/woff2;base64,' + fs.readFileSync(`${root}/node_modules/@fontsource-variable/${pkg}/files/${file}`).toString('base64');
const style = spec.style || (/assets\/reading\/mila-/.test(spec.picture) ? 'mila-c' : /assets\/reading\//.test(spec.picture) ? 'ani-b' : 'book');
const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
const corner = `<svg viewBox="0 0 120 120" width="120" height="120"><g fill="none" stroke="url(#g)" stroke-width="2.4" stroke-linecap="round">
<path d="M8 112 V40 Q8 8 40 8 H112"/><path d="M22 112 V48 Q22 22 48 22 H112" stroke-width="1.2"/><path d="M40 8 Q44 30 22 34"/>
<circle cx="40" cy="40" r="7"/><path d="M47 40 Q70 40 78 22 M40 47 Q40 70 22 78"/><path d="M58 34 q8 -10 18 -6 M34 58 q-10 8 -6 18"/></g>
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F7E3A8"/><stop offset=".6" stop-color="#C9973F"/><stop offset="1" stop-color="#E9C77A"/></linearGradient></defs></svg>`;
const bookPage = (layer) => `<!doctype html><html><head><style>
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
// Ani: a bright page from a diary. The picture melts into cream paper; navy serif title, violet accents.
const aniPage = (layer) => `<!doctype html><html><head><style>
@font-face{font-family:L;src:url(${fnt('literata', 'literata-latin-wght-normal.woff2')})}
@font-face{font-family:L;font-style:italic;src:url(${fnt('literata', 'literata-latin-wght-italic.woff2')})}
@font-face{font-family:I;src:url(${fnt('inter', 'inter-latin-wght-normal.woff2')})}
*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;overflow:hidden;position:relative;background:${layer === 'bg' ? '#F6EFE3' : 'transparent'}}
.bg{position:absolute;left:0;right:0;top:0;height:1290px;background:url(${pic}) ${spec.focus || '50% 35%'}/cover no-repeat;
 -webkit-mask-image:linear-gradient(#000 0,#000 62%,transparent 100%),linear-gradient(90deg,transparent 0,#000 7%,#000 93%,transparent 100%);-webkit-mask-composite:source-in}
.glow{position:absolute;inset:0;background:radial-gradient(900px 520px at 50% 1350px,#A891F726,transparent 70%),radial-gradient(700px 400px at 85% 1800px,#E9C46A2e,transparent 70%)}
.box{position:absolute;left:96px;right:96px;top:1225px;text-align:center}
.k{display:inline-block;width:64px;height:6px;border-radius:6px;background:linear-gradient(90deg,#6A49E2,#A891F7)}
h1{margin-top:34px;font:italic 640 ${spec.title.length > 16 ? 96 : 116}px/1.02 L;color:#17183A;letter-spacing:-1px}
p{margin-top:34px;font:400 46px/1.42 L;color:#3A3A52}
.cta{position:absolute;left:50%;bottom:150px;transform:translateX(-50%);display:flex;align-items:center;gap:18px;padding:24px 44px;border-radius:999px;
 background:#6A49E2;color:#fff;font:600 34px I;letter-spacing:.5px;box-shadow:0 18px 40px #6A49E255;white-space:nowrap}
.cta i{width:0;height:0;border-left:20px solid #fff;border-top:12px solid transparent;border-bottom:12px solid transparent}
</style></head><body>${layer === 'bg' ? '<div class=bg></div><div class=glow></div>' : `
<div class=box><span class=k></span><h1>${esc(spec.title)}</h1><p>${esc(spec.hook).replace(/\n/g, '<br>')}</p></div>
<div class=cta><i></i>Read and listen</div>`}</body></html>`;

// Mila & Leo: a warm picture-book page. The picture melts into amber paper on every side; playful soft serif title.
const milaPage = (layer) => `<!doctype html><html><head><style>
@font-face{font-family:F;src:url(${fnt('fraunces', 'fraunces-latin-soft-normal.woff2')})}
@font-face{font-family:F;font-style:italic;src:url(${fnt('fraunces', 'fraunces-latin-soft-italic.woff2')})}
@font-face{font-family:I;src:url(${fnt('inter', 'inter-latin-wght-normal.woff2')})}
*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;overflow:hidden;position:relative;background:${layer === 'bg' ? '#FBE9CF' : 'transparent'}}
.paper{position:absolute;inset:0;background:radial-gradient(1000px 700px at 20% 10%,#FFF6E6,transparent 70%),radial-gradient(900px 800px at 90% 95%,#F6C98E,transparent 70%),#FBE9CF}
.pic{position:absolute;left:0;right:0;top:0;height:1360px;background:url(${pic}) ${spec.focus || '50% 35%'}/cover no-repeat;
 -webkit-mask-image:radial-gradient(105% 78% at 50% 40%,#000 52%,transparent 82%)}
.band{position:absolute;left:0;right:0;top:1230px;bottom:0}
.box{position:absolute;left:90px;right:90px;top:1350px;text-align:center}
h1{font:italic 700 ${spec.title.length > 16 ? 100 : 122}px/1 F;color:#7A2E12;letter-spacing:-1px;font-variation-settings:"SOFT" 100,"WONK" 1}
.st{margin:26px auto 0;display:flex;justify-content:center;gap:22px}
.st b{width:16px;height:16px;background:#E8A317;clip-path:polygon(50% 0,61% 39%,100% 50%,61% 61%,50% 100%,39% 61%,0 50%,39% 39%)}
.st b:nth-child(2){background:#D9572B;transform:scale(1.35)}
p{margin-top:26px;font:400 46px/1.42 F;color:#4A2A1A;font-variation-settings:"SOFT" 100}
.cta{position:absolute;left:50%;bottom:130px;transform:translateX(-50%);display:flex;align-items:center;gap:18px;padding:24px 46px;border-radius:999px;
 background:#D9572B;color:#FFF6E6;font:600 34px I;letter-spacing:.5px;box-shadow:0 18px 40px #D9572B55;white-space:nowrap}
.cta i{width:0;height:0;border-left:20px solid #FFF6E6;border-top:12px solid transparent;border-bottom:12px solid transparent}
</style></head><body>${layer === 'bg' ? '<div class=paper></div><div class=pic></div>' : `
<div class=box><h1>${esc(spec.title)}</h1><div class=st><b></b><b></b><b></b></div><p>${esc(spec.hook).replace(/\n/g, '<br>')}</p></div>
<div class=cta><i></i>Read and listen</div>`}</body></html>`;
// Three design directions, each with a clearly different Ani and Mila & Leo page.
// Shared pieces: font faces, a title that shrinks until it fits its box, the hook with line breaks.
const faces = {
  L: ['literata', 'literata-latin-wght-normal.woff2', 'literata-latin-wght-italic.woff2'],
  I: ['inter', 'inter-latin-wght-normal.woff2', 'inter-latin-wght-italic.woff2'],
  F: ['fraunces', 'fraunces-latin-full-normal.woff2', 'fraunces-latin-full-italic.woff2'],
  P: ['playfair-display', 'playfair-display-latin-wght-normal.woff2', 'playfair-display-latin-wght-italic.woff2'],
  C: ['cormorant-garamond', 'cormorant-garamond-latin-wght-normal.woff2', 'cormorant-garamond-latin-wght-italic.woff2'],
};
const faceCss = (keys) => keys.map((k) => { const [pkg, n, it] = faces[k];
  return `@font-face{font-family:${k};src:url(${fnt(pkg, n)})}@font-face{font-family:${k};font-style:italic;src:url(${fnt(pkg, it)})}`; }).join('');
const hookHtml = () => esc(spec.hook).replace(/\n/g, '<br>');
const play = (c) => `<svg width="26" height="30" viewBox="0 0 26 30"><path d="M3 3.5v23a1.5 1.5 0 0 0 2.3 1.3l18.4-11.5a1.5 1.5 0 0 0 0-2.6L5.3 2.2A1.5 1.5 0 0 0 3 3.5z" fill="${c}"/></svg>`;
// Title fit: shrink the font until the title fits its width and at most `lines` lines.
const fitJs = `<script>for(const el of document.querySelectorAll('[data-fit]')){const n=+el.dataset.fit;let s=parseFloat(getComputedStyle(el).fontSize);
const lh=()=>parseFloat(getComputedStyle(el).lineHeight)||s*1.05;
while(s>40&&(el.scrollWidth>el.clientWidth+1||el.scrollHeight>lh()*n+4)){s-=2;el.style.fontSize=s+'px'}}</script>`;
const shell = (layer, bgColor, fonts, css, bgHtml, ovHtml) => `<!doctype html><html><head><style>${faceCss(fonts)}
*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;overflow:hidden;position:relative;background:${layer === 'bg' ? bgColor : 'transparent'}}
.pic{position:absolute;background:url(${pic}) ${spec.focus || '50% 40%'}/cover no-repeat}
${css}</style></head><body>${layer === 'bg' ? bgHtml : ovHtml + fitJs}</body></html>`;
const melt = (v, h) => `-webkit-mask-image:${v},${h};-webkit-mask-composite:source-in;mask-image:${v},${h};mask-composite:intersect`;
const rainbow = ['#B23F78', '#7A4FD6', '#3E5FD9', '#1C8AA3', '#2E9E6A'];

// A1 — Ani "Morning page": daylight cream paper, picture floats at the top, left-aligned Literata, violet pill.
const aniA = (layer) => shell(layer, '#FBF7F0', ['L', 'I'], `
.paper{position:absolute;inset:0;background:radial-gradient(900px 700px at 15% 100%,#A891F733,transparent 70%),radial-gradient(800px 600px at 100% 62%,#F2C86B30,transparent 70%),#FBF7F0}
.pic{left:-30px;right:-30px;top:40px;height:1200px;${melt('linear-gradient(transparent 0,#000 15%,#000 64%,transparent 100%)', 'linear-gradient(90deg,transparent 0,#000 13%,#000 87%,transparent 100%)')}}
.box{position:absolute;left:100px;right:100px;bottom:340px}
.k{width:72px;height:7px;border-radius:7px;background:linear-gradient(90deg,#6A49E2,#A891F7)}
h1{margin-top:30px;font:italic 650 112px/1.04 L;color:#17183A;letter-spacing:-1.5px;max-height:240px}
p{margin-top:28px;font:400 44px/1.42 L;color:#3A3A52}
.cta{position:absolute;left:100px;bottom:200px;display:flex;align-items:center;gap:18px;padding:24px 46px 24px 38px;border-radius:999px;
 background:#6A49E2;color:#fff;font:600 34px I;box-shadow:0 18px 40px #6A49E244;white-space:nowrap}`,
  '<div class=paper></div><div class=pic></div>',
  `<div class=box><div class=k></div><h1 data-fit=2>${esc(spec.title)}</h1><p>${hookHtml()}</p></div><div class=cta>${play('#fff')}Read and listen</div>`);

// A2 — Mila & Leo "Story night": deep navy, title on top in gold Fraunces, the picture glows in the middle, gold pill.
const milaA = (layer) => shell(layer, '#17183A', ['F', 'I'], `
.sky{position:absolute;inset:0;background:radial-gradient(900px 900px at 50% 50%,#2A1E4D,transparent 72%),radial-gradient(700px 500px at 50% 100%,#5A3B8C55,transparent 70%),#17183A}
.pic{left:-20px;right:-20px;top:400px;height:1040px;-webkit-mask-image:radial-gradient(closest-side,#000 58%,transparent 100%);mask-image:radial-gradient(closest-side,#000 58%,transparent 100%)}
.top{position:absolute;left:80px;right:80px;top:280px;text-align:center}
h1{font:italic 700 124px/1 F;font-variation-settings:"SOFT" 100,"WONK" 1,"opsz" 144;background:linear-gradient(#FBE3A0,#F2C86B 55%,#E9A84A);-webkit-background-clip:text;color:transparent;padding:0 6px .14em}
.hook{position:absolute;left:90px;right:90px;top:1420px;text-align:center;font:400 46px/1.4 F;font-variation-settings:"SOFT" 100;color:#EDE7FF;text-shadow:0 2px 20px #17183A}
.cta{position:absolute;left:50%;bottom:200px;transform:translateX(-50%);display:flex;align-items:center;gap:18px;padding:24px 48px 24px 40px;border-radius:999px;
 background:linear-gradient(#F7D581,#E9C46A);color:#17183A;font:650 34px I;box-shadow:0 0 50px #E9C46A44;white-space:nowrap}`,
  '<div class=sky></div><div class=pic></div>',
  `<div class=top><h1 data-fit=2>${esc(spec.title)}</h1></div><div class=hook>${hookHtml()}</div><div class=cta>${play('#17183A')}Read and listen</div>`);

// B1 — Ani "Cinema": the picture fills the screen, a violet-navy dusk rises from below, white Playfair, gold line CTA.
const aniB = (layer) => shell(layer, '#17183A', ['P', 'L', 'I'], `
.pic{left:-270px;right:-270px;top:0;height:1620px}
.dusk{position:absolute;inset:0;background:linear-gradient(rgba(23,24,58,.55) 0,rgba(23,24,58,0) 14%,rgba(23,24,58,0) 40%,rgba(42,30,77,.8) 64%,#17183A 82%,#17183A 100%),
 radial-gradient(120% 60% at 50% 45%,transparent 60%,rgba(14,11,29,.5))}
.box{position:absolute;left:96px;right:96px;bottom:390px}
h1{font:600 118px/1.02 P;color:#fff;letter-spacing:-1px;max-height:250px;text-shadow:0 6px 30px rgba(14,11,29,.5)}
.rule{margin:36px 0 30px;width:120px;height:3px;background:linear-gradient(90deg,#F2C86B,#E9C46A00)}
p{font:italic 400 44px/1.42 L;color:#D9D1FA}
.cta{position:absolute;left:96px;bottom:205px;display:flex;align-items:center;gap:20px;color:#F2C86B;font:600 32px I;letter-spacing:4px;text-transform:uppercase;white-space:nowrap}
.cta span{display:flex;align-items:center;justify-content:center;width:74px;height:74px;border-radius:50%;border:2px solid #F2C86B}
.cta span svg{margin-left:5px;transform:scale(.8)}`,
  '<div class=pic></div><div class=dusk></div>',
  `<div class=box><h1 data-fit=2>${esc(spec.title)}</h1><div class=rule></div><p>${hookHtml()}</p></div><div class=cta><span>${play('#F2C86B')}</span>Read and listen</div>`);

// B2 — Mila & Leo "Picture book": airy mint-and-cream page, a round soft picture, rainbow-letter title, green sticker CTA.
const milaB = (layer) => shell(layer, '#F4F8EE', ['F', 'I'], `
.paper{position:absolute;inset:0;background:radial-gradient(900px 700px at 0% 0%,#DDF1EA,transparent 70%),radial-gradient(900px 700px at 100% 100%,#FFF0D2,transparent 70%),#F7F7EE}
.pic{left:30px;width:1020px;top:290px;height:1020px;-webkit-mask-image:radial-gradient(closest-side,#000 62%,transparent 100%);mask-image:radial-gradient(closest-side,#000 62%,transparent 100%)}
.box{position:absolute;left:80px;right:80px;top:1250px;text-align:center}
h1{font:800 128px/1 F;font-variation-settings:"SOFT" 100,"WONK" 0,"opsz" 144;letter-spacing:-1px;max-height:260px}
h1 span:nth-child(5n+1){color:${rainbow[0]}}h1 span:nth-child(5n+2){color:${rainbow[1]}}h1 span:nth-child(5n+3){color:${rainbow[2]}}h1 span:nth-child(5n+4){color:${rainbow[3]}}h1 span:nth-child(5n+5){color:${rainbow[4]}}
p{margin-top:28px;font:500 44px/1.4 F;font-variation-settings:"SOFT" 100;color:#3A3A52}
.cta{position:absolute;left:50%;bottom:200px;transform:translateX(-50%) rotate(-2.5deg);display:flex;align-items:center;gap:18px;padding:26px 50px 26px 42px;border-radius:30px;
 background:#2E9E6A;color:#fff;font:700 34px I;box-shadow:0 8px 0 #1F7A50,0 22px 40px #2E9E6A44;white-space:nowrap}`,
  '<div class=paper></div><div class=pic></div>',
  `<div class=box><h1 data-fit=2>${[...esc(spec.title)].map((c) => c === ' ' ? ' ' : `<span>${c}</span>`).join('')}</h1><p>${hookHtml()}</p></div><div class=cta>${play('#fff')}Read and listen</div>`);

// C1 — Ani "Lavender letter": soft lavender page, an elegant Cormorant title at the top, the picture rises from below.
const aniC = (layer) => shell(layer, '#EFEAFE', ['C', 'L', 'I'], `
.paper{position:absolute;inset:0;background:linear-gradient(#F6F3FF 0,#ECE6FD 45%,#DCD2FA 100%)}
.pic{left:-30px;right:-30px;top:690px;height:1230px;${melt('linear-gradient(transparent 0,#000 26%,#000 76%,transparent 100%)', 'linear-gradient(90deg,transparent 0,#000 14%,#000 86%,transparent 100%)')}}
.top{position:absolute;left:90px;right:90px;top:290px;text-align:center}
h1{font:italic 600 144px/.98 C;color:#17183A;letter-spacing:-1px;max-height:270px}
.orn{margin:30px auto 26px;display:flex;align-items:center;justify-content:center;gap:16px}
.orn i{width:90px;height:1.5px;background:#6A49E2}.orn b{width:11px;height:11px;border:1.5px solid #6A49E2;transform:rotate(45deg)}
p{font:400 42px/1.45 L;color:#3A3A52}
.cta{position:absolute;left:50%;bottom:200px;transform:translateX(-50%);display:flex;align-items:center;gap:18px;padding:24px 48px 24px 40px;border-radius:999px;
 background:#17183A;color:#F6F3FF;font:600 34px I;box-shadow:0 18px 40px #17183A55;white-space:nowrap}`,
  '<div class=paper></div><div class=pic></div>',
  `<div class=top><h1 data-fit=2>${esc(spec.title)}</h1><div class=orn><i></i><b></b><i></i></div><p>${hookHtml()}</p></div><div class=cta>${play('#F2C86B')}Read and listen</div>`);

// C2 — Mila & Leo "Sunny poster": warm gold page, the picture on top, a bold Inter title bottom-left, navy CTA.
const milaC = (layer) => shell(layer, '#F2C86B', ['I'], `
.paper{position:absolute;inset:0;background:radial-gradient(1100px 900px at 30% 20%,#FBE3A0,transparent 70%),radial-gradient(900px 700px at 100% 100%,#E8A317,transparent 70%),#F2C86B}
.pic{left:-20px;right:-20px;top:30px;height:1320px;${melt('linear-gradient(transparent 0,#000 14%,#000 66%,transparent 100%)', 'linear-gradient(90deg,transparent 0,#000 13%,#000 87%,transparent 100%)')}}
.box{position:absolute;left:92px;right:92px;bottom:340px}
h1{font:850 124px/.96 I;color:#17183A;letter-spacing:-4px}
p{margin-top:28px;font:500 42px/1.4 I;color:#2A1E4D;letter-spacing:-.3px}
.cta{position:absolute;left:92px;bottom:200px;display:flex;align-items:center;gap:18px;padding:24px 46px 24px 38px;border-radius:22px;
 background:#17183A;color:#F2C86B;font:700 34px I;white-space:nowrap}`,
  '<div class=paper></div><div class=pic></div>',
  `<div class=box><h1 data-fit=2>${esc(spec.title)}</h1><p>${hookHtml()}</p></div><div class=cta>${play('#F2C86B')}Read and listen</div>`);

const pages = { ani: aniPage, mila: milaPage, 'ani-a': aniA, 'mila-a': milaA, 'ani-b': aniB, 'mila-b': milaB, 'ani-c': aniC, 'mila-c': milaC };
const page = pages[style] || bookPage;

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

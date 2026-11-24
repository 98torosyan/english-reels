// "A Day in Opposites": a cover, one slide per pair (both actions in one picture, Lily left, Sam right) and a short quiz.
// Usage: node carousels/render_opposites.js <day-id>   -> outputs/english-reels-samples/opposites-<id>/01.jpg …
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');
const utils = require('../reels/render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'carousels/data/opposites.json'), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const img = (id, n) => `data:image/jpeg;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets', 'opposites', id, `${n}.jpg`)).toString('base64')}`;
const LOGO = () => `data:image/svg+xml;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets/logo-ig.svg')).toString('base64')}`;
const quotes = (s) => s.replace(/(^|[\s(])'/g, '$1‘').replace(/'/g, '’');

function page(baseUrl, body) {
  const f = utils.fontUrls(baseUrl);
  return `<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>
@font-face{font-family:Lit;src:url(${f.literata})}@font-face{font-family:Lit;src:url(${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-italic.woff2);font-style:italic}
@font-face{font-family:Inter;src:url(${f.inter})}@font-face{font-family:Arm;src:url(${f.armenian})}
*{box-sizing:border-box;margin:0}
:root{--ink:#2B1E14;--muted:#6B5646;--accent:#C0652A;--sage:#5E7A52;--paper:#F8EBDD;--card:#FFF8F0}
html,body{width:1080px;height:1350px;overflow:hidden}
body{position:relative;color:var(--ink);font-family:Inter;background:#FAF0E4}
.pic{position:absolute;left:0;top:0;width:1080px;height:860px;overflow:hidden}
.pic img{width:100%;height:100%;object-fit:cover;object-position:50% 38%}
.pic:after{content:"";position:absolute;left:0;right:0;bottom:0;height:190px;background:linear-gradient(transparent,#FAF0E4)}
.tag{position:absolute;top:680px;z-index:3;display:flex;align-items:center;gap:10px;padding:12px 26px;border-radius:99px;background:#FFF8F0f2;box-shadow:0 14px 34px #4a2a1030;font:700 italic 40px Lit;color:var(--ink)}
.tag i{width:14px;height:14px;border-radius:50%}
.pair{position:absolute;left:56px;right:56px;top:800px;display:grid;grid-template-columns:1fr 108px 1fr;align-items:center;z-index:4}
.w{text-align:center}
.w b{display:block;font:700 76px/1 Lit;letter-spacing:-1.5px}
.w span{display:block;margin-top:14px;font:600 36px Arm;color:var(--ink)}
.w small{display:block;margin-top:8px;font:500 27px Arm;color:var(--muted)}
.w small em{font:500 25px Inter;font-style:normal;opacity:.75}
.sw{width:92px;height:92px;margin:0 auto;border-radius:50%;background:var(--ink);color:#FFF8F0;display:flex;align-items:center;justify-content:center;font:600 46px Inter;box-shadow:0 14px 30px #2B1E1440}
.sent{position:absolute;left:70px;right:70px;top:1062px;text-align:center;padding-top:34px}
.sent:before{content:"";position:absolute;top:0;left:50%;width:70px;height:3px;margin-left:-35px;border-radius:3px;background:#C0652A66}
.sent p{font:500 41px/1.35 Lit}
.sent p mark{background:linear-gradient(transparent 58%,#F3B56599 58%);color:inherit;font-style:italic;font-weight:600;padding:0 3px}
.sent span{display:block;margin-top:14px;font:500 29px/1.45 Arm;color:var(--muted)}
.brand{position:absolute;left:0;right:0;bottom:34px;text-align:center;font:800 19px Inter;letter-spacing:6px;color:#2B1E1455}
</style></head><body>${body}</body></html>`;
}

function slides(day) {
  const out = [];
  // cover: the whole first picture, title over its calm lower part
  out.push(`<div class="pic" style="height:1350px"><img src="${img(day.id, 1)}" style="object-position:50% 20%"></div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:640px;background:linear-gradient(transparent,#FAF0E4 46%)"></div>
    <div style="position:absolute;left:70px;right:70px;bottom:120px;text-align:center">
      <div style="font:800 22px Inter;letter-spacing:7px;color:var(--accent)">10 WORDS · 5 PAIRS · ${esc(day.level)}</div>
      <div style="margin-top:18px;font:700 108px/1 Lit;letter-spacing:-3px">${esc(day.title)} <em style="color:var(--accent)">${esc(day.title_em)}</em></div>
      <div style="margin-top:22px;font:600 38px Arm;color:var(--muted)">${esc(day.title_hy)}</div>
      <div style="margin-top:38px;display:inline-flex;align-items:center;gap:14px;padding:18px 36px;border-radius:99px;background:var(--ink);color:#FFF8F0;font:700 30px Arm">Թերթի՛ր <span style="font:600 34px Inter">→</span></div>
    </div><div class="brand">@ENGLISH.READINGROOM</div>`);
  day.pairs.forEach((p, i) => {
    const w = (x) => `<div class="w"><b>${esc(x.en)}</b><span>${esc(x.hy)}</span><small>«${esc(x.say)}» <em>${esc(x.ipa)}</em></small></div>`;
    const s = esc(quotes(p.sentence)).replace(/\[([^\]]+)\]/g, '<mark>$1</mark>');
    out.push(`<div class="pic"><img src="${img(day.id, i + 2)}"></div>
      <div class="pair">${w(p.left)}<div class="sw">⇄</div>${w(p.right)}</div>
      <div class="sent"><p>${s}</p><span>${esc(p.sentence_hy)}</span></div>
      <div class="brand">@ENGLISH.READINGROOM</div>`);
  });
  // quiz
  out.push(`<div style="position:absolute;left:0;top:0;width:1080px;height:520px;overflow:hidden"><img src="${img(day.id, 6)}" style="width:100%;height:100%;object-fit:cover;object-position:50% 30%;filter:saturate(1.05)"></div>
    <div style="position:absolute;left:0;right:0;top:300px;height:240px;background:linear-gradient(transparent,#FAF0E4)"></div>
    <div style="position:absolute;left:80px;right:80px;top:470px;text-align:center">
      <div style="font:800 22px Inter;letter-spacing:7px;color:var(--accent)">YOUR TURN</div>
      <div style="margin-top:12px;font:700 74px/1.05 Lit;letter-spacing:-2px">Fill in the <em style="color:var(--accent)">gap</em></div>
      <div style="margin-top:12px;font:600 32px Arm;color:var(--muted)">Լրացրո՛ւ բաց թողած բառը</div>
      <div style="margin-top:36px;display:grid;gap:18px;text-align:left">${day.quiz.map((q, k) => `<div style="display:flex;align-items:center;gap:24px;padding:22px 30px;border-radius:26px;background:var(--card);box-shadow:0 14px 30px #4a2a1012">
        <div style="flex:none;width:56px;height:56px;border-radius:50%;background:var(--ink);color:#FFF8F0;display:flex;align-items:center;justify-content:center;font:700 28px Inter">${k + 1}</div>
        <div style="font:500 40px/1.25 Lit">${esc(q.q).replace('___', '<span style="display:inline-block;width:150px;border-bottom:4px solid var(--accent);transform:translateY(-6px)"></span>')}</div></div>`).join('')}</div>
      <div style="margin-top:34px;font:700 32px Arm">Գրի՛ր պատասխաններդ մեկնաբանություններում</div>
      <div style="margin-top:12px;font:500 27px Arm;color:var(--muted)">Պահի՛ր գրառումը, որ կրկնես · Դասեր՝ գրե՛ք Direct-ով</div>
    </div><div class="brand">@ENGLISH.READINGROOM</div>`);
  return out;
}

async function main() {
  const day = DATA.days.find((d) => d.id === process.argv[2]);
  if (!day) throw new Error(`Unknown day: ${process.argv[2]}`);
  const out = path.join(utils.OUTPUT, `opposites-${day.id}`); fs.rmSync(out, { recursive: true, force: true }); utils.ensureDirectory(out);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try {
    const list = slides(day);
    for (let i = 0; i < list.length; i += 1) {
      const work = path.join(utils.ROOT, '.render-work', `opposites-${i}.html`);
      fs.writeFileSync(work, page(baseUrl, list[i]));
      const p = await browser.newPage({ viewport: { width: 1080, height: 1350 } });
      const errors = await utils.preparePage(p, `${baseUrl}${utils.renderHtmlPath(work)}`, 1080, 1350);
      await p.evaluate(() => document.fonts.ready);
      const bad = await p.evaluate(() => {
        const brand = document.querySelector('.brand').getBoundingClientRect().top;
        return [...document.querySelectorAll('.w,.sent,.sw')].filter((e) => e.getBoundingClientRect().bottom > brand - 8 || e.scrollWidth > e.clientWidth + 2).map((e) => e.textContent.slice(0, 40));
      });
      if (errors.length || bad.length) throw new Error(`slide ${i + 1}: ${errors.join(' | ')} ${JSON.stringify(bad)}`);
      await p.screenshot({ path: path.join(out, `${String(i + 1).padStart(2, '0')}.jpg`), type: 'jpeg', quality: 93 });
      await p.close();
    }
    console.log(`${day.id}: ${list.length} slides → ${out}`);
  } finally { await browser.close(); server.close(); }
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

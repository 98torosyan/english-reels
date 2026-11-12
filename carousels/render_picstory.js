// Picture-story carousel: cover, six illustrated story slides (English + Armenian), and a "New words" slide.
// Usage: node carousels/render_picstory.js <story-id>   -> outputs/english-reels-samples/picstory-<id>/01.jpg … 08.jpg
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');
const utils = require('../reels/render_utils');

const DATA = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'carousels/data/picture_stories.json'), 'utf8'));
const PALETTE = ['#B23F78', '#1C8AA3', '#3E5FD9', '#2E9E6A', '#B9790B', '#6A49E2'];
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const img = (id, n) => `data:image/jpeg;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets', 'picstory', id, `${n}.jpg`)).toString('base64')}`;

function page(st, baseUrl, body) {
  const f = utils.fontUrls(baseUrl);
  const ext = `${baseUrl}/node_modules/@fontsource-variable/inter/files/inter-latin-ext-wght-normal.woff2`;
  const c = PALETTE[(st.number - 1) % PALETTE.length];
  return `<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>
@font-face{font-family:Lit;src:url(${f.literata})}@font-face{font-family:Lit;src:url(${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-italic.woff2);font-style:italic}
@font-face{font-family:Inter;src:url(${f.inter})}@font-face{font-family:Arm;src:url(${f.armenian})}
@font-face{font-family:IPA;src:url(${f.inter});unicode-range:U+0000-00FF}@font-face{font-family:IPA;src:url(${ext});unicode-range:U+0100-02FF}
*{box-sizing:border-box;margin:0}
:root{--c:${c};--ink:#17183A;--muted:#5E5B74;--soft:#8C89A0;--paper:#F4EFE4;--card:#FFFCF6}
html,body{width:1080px;height:1350px;overflow:hidden}
body{position:relative;color:var(--ink);font-family:Inter;background:radial-gradient(900px 700px at 85% 0%,#FFFDF7,transparent 70%),linear-gradient(170deg,#F7F2E8,#EFE8DA)}
body:after{content:"";position:absolute;left:0;top:0;bottom:0;width:14px;background:var(--c);z-index:9}
.pic{position:absolute;left:0;top:0;width:1080px;overflow:hidden}
.pic img{width:100%;height:100%;object-fit:cover}
.pic:after{content:"";position:absolute;left:0;right:0;bottom:0;height:150px;background:linear-gradient(transparent,#F4EFE4)}
.pill{position:absolute;top:36px;left:40px;display:flex;align-items:center;gap:12px;padding:8px 20px 8px 8px;border-radius:99px;background:#FFFCF6ee;box-shadow:0 8px 24px #17183A26;z-index:5}
.pill img{width:48px;height:48px;border-radius:13px}.pill b{font:700 21px Lit}.pill span{display:block;font:800 13px Inter;letter-spacing:3px;color:var(--soft)}
.num{position:absolute;top:44px;right:44px;z-index:5;font:800 20px Inter;letter-spacing:3px;color:#fff;background:#17183Acc;padding:8px 16px;border-radius:99px}
.k{font:800 22px Inter;letter-spacing:6px;color:var(--c)}
.en{font:500 50px/1.3 Lit;color:var(--ink)}
.hy{font:500 31px/1.45 Arm;color:var(--muted)}
.foot{position:absolute;left:64px;right:64px;bottom:40px;display:flex;justify-content:space-between;font:700 21px Inter;color:var(--soft)}.foot b{color:var(--c)}
mark{background:linear-gradient(transparent 62%,color-mix(in srgb,var(--c) 28%,transparent) 62%);color:inherit;padding:0 2px}
.wcs{margin-top:26px;display:flex;gap:14px;flex-wrap:wrap}
.wc{display:inline-flex;align-items:baseline;gap:14px;padding:12px 24px;border-radius:18px;background:var(--card);border:2px solid var(--c);box-shadow:0 10px 24px #3a2f1414}
.wc b{font:700 34px Lit}.wc i{font:500 25px IPA;font-style:normal;color:var(--c)}.wc span{font:500 27px Arm;color:var(--muted)}
.swipe{display:inline-flex;align-items:center;gap:12px;background:var(--c);color:#fff;font:800 24px Inter;letter-spacing:3px;padding:16px 30px;border-radius:99px}
</style></head><body>${body}</body></html>`;
}

const LOGO = () => `data:image/svg+xml;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets/logo-ig.svg')).toString('base64')}`;
const pill = () => `<div class="pill"><img src="${LOGO()}"><div><b>Gayane Torosyan</b><span>@ENGLISH.READINGROOM</span></div></div>`;
const foot = (n, total) => `<div class="foot"><span>Gayane Torosyan · English Reading Room</span><b>${n} / ${total}</b></div>`;

// New words are highlighted in the sentence; the first time a word appears, its card (IPA + Armenian) sits under the text.
function marked(st, en, seen) {
  let html = esc(en).replace(/(^|[\s(])'/g, '$1‘').replace(/'/g, '’'); const cards = [];
  for (const w of st.words) {
    const re = new RegExp(`\\b(${w.en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})(s|es|ed|d)?\\b`, 'i');
    if (!re.test(html)) continue;
    html = html.replace(new RegExp(re.source, 'gi'), (m) => `<mark>${m}</mark>`);
    if (!seen.has(w.en)) { seen.add(w.en); cards.push(w); }
  }
  return { html, cards };
}
const wordCard = (w) => `<div class="wc"><b>${esc(w.en)}</b><i>${esc(w.ipa)}</i><span>${esc(w.hy)}</span></div>`;

function slides(st) {
  const total = st.scenes.length + 2;
  const tw = st.title.split(' ');
  const title = `${esc(tw.slice(0, -1).join(' '))} <em style="color:var(--c);font-style:italic">${esc(tw.at(-1))}</em>`;
  const out = [];
  out.push(`<div class="pic" style="height:1000px"><img src="${img(st.id, 1)}"></div>${pill()}
    <div style="position:absolute;left:64px;right:64px;top:930px">
      <div class="k">PICTURE STORY · ${String(st.number).padStart(2, '0')} · ${esc(st.level)}</div>
      <div style="margin-top:14px;font:700 92px/1 Lit;letter-spacing:-2.5px">${title}</div>
      <div class="hy" style="margin-top:14px">${esc(st.title_hy)} · կարդա՛ անգլերեն, հայերենը՝ օգնության համար</div>
      <div style="margin-top:34px" class="swipe">SWIPE <span style="font-size:30px">→</span></div>
    </div>${foot(1, total)}`);
  const seen = new Set();
  st.scenes.forEach((en, i) => {
    const m = marked(st, en, seen);
    out.push(`<div class="pic" style="height:900px"><img src="${img(st.id, i + 1)}" style="object-position:50% 40%"></div>${pill()}
      <div style="position:absolute;left:64px;right:64px;top:860px">
        <div class="en" data-fit>${m.html}</div>
        <div class="hy" style="margin-top:22px">${esc(st.scenes_hy[i])}</div>
        ${m.cards.length ? `<div class="wcs">${m.cards.map(wordCard).join('')}</div>` : ''}
      </div>${foot(i + 2, total)}`);
  });
  out.push(`${pill()}<div style="position:absolute;left:64px;right:64px;top:128px">
      <div class="k">NEW WORDS · ՆՈՐ ԲԱՌԵՐ</div>
      <div style="margin-top:14px;font:700 76px/1.02 Lit;letter-spacing:-2px">Learn these <em style="color:var(--c);font-style:italic">three</em></div>
      <div style="margin-top:30px;display:grid;gap:16px">${st.words.map((w) => `<div style="display:flex;align-items:center;gap:26px;background:var(--card);border:1.5px solid #17183A1a;border-radius:26px;padding:20px 32px;box-shadow:0 14px 30px #3a2f1410">
        <div style="flex:1"><div style="font:700 50px Lit">${esc(w.en)}</div><div style="margin-top:6px;font:500 30px IPA;color:var(--c)">${esc(w.ipa)}</div></div>
        <div class="hy" style="font-size:34px;text-align:right">${esc(w.hy)}</div></div>`).join('')}</div>
      <div style="margin-top:32px;padding:24px 34px;border-radius:26px;background:color-mix(in srgb,var(--c) 10%,var(--card));border:2px solid var(--c)">
        <div class="k" style="letter-spacing:4px">QUESTION · ՀԱՐՑ</div>
        <div style="margin-top:10px;font:600 40px/1.25 Lit">${esc(st.question)}</div>
        <div class="hy" style="margin-top:10px">Պատասխանի՛ր անգլերեն մեկնաբանություններում</div>
      </div>
      <div class="hy" style="margin-top:26px;color:var(--ink);font-weight:700;font-size:28px">Պահի՛ր և ուղարկի՛ր ընկերոջդ · Անհատական և խմբային դասեր՝ գրե՛ք Direct-ով</div>
    </div>${foot(total, total)}`);
  return out;
}

// Story that announces the new carousel: blurred picture behind, the cover card in front.
function storyPage(st, baseUrl) {
  const c = PALETTE[(st.number - 1) % PALETTE.length]; const f = utils.fontUrls(baseUrl);
  const cover = `data:image/jpeg;base64,${fs.readFileSync(path.join(utils.OUTPUT, `picstory-${st.id}`, '01.jpg')).toString('base64')}`;
  return `<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>
@font-face{font-family:Lit;src:url(${f.literata})}@font-face{font-family:Inter;src:url(${f.inter})}@font-face{font-family:Arm;src:url(${f.armenian})}
*{margin:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;background:#17183A}
.bg{position:absolute;inset:-60px;background:url(${img(st.id, 1)}) center/cover;filter:blur(38px) brightness(.62) saturate(1.2)}
.k{position:absolute;top:190px;left:0;right:0;text-align:center;font:800 30px Inter;letter-spacing:8px;color:#fff}
.k i{display:block;margin-top:14px;font:500 36px Arm;letter-spacing:0;font-style:normal;color:#ffffffcc}
.card{position:absolute;left:110px;top:360px;width:860px;height:1075px;border-radius:44px;overflow:hidden;box-shadow:0 50px 110px #0009;transform:rotate(-2deg);border:10px solid #FFFCF6}
.card img{width:100%;height:100%;object-fit:cover}
.go{position:absolute;left:0;right:0;top:1545px;text-align:center}
.go b{display:inline-block;background:${c};color:#fff;font:800 36px Inter;letter-spacing:3px;padding:24px 50px;border-radius:99px;box-shadow:0 20px 50px #0006}
.go span{display:block;margin-top:26px;font:600 34px Arm;color:#fff}
.h{position:absolute;bottom:120px;left:0;right:0;text-align:center;font:800 26px Inter;letter-spacing:5px;color:#ffffffb3}
</style></head><body><div class="bg"></div>
<div class="k">NEW PICTURE STORY<i>Նոր պատմություն նկարներով</i></div>
<div class="card"><img src="${cover}"></div>
<div class="go"><b>READ IT ON OUR PAGE →</b><span>Կարդա՛ անգլերեն՝ մեր էջում</span></div>
<div class="h">@ENGLISH.READINGROOM</div></body></html>`;
}

async function main() {
  const st = DATA.stories.find((s) => s.id === process.argv[2]);
  if (!st || !st.scenes_hy) throw new Error('Unknown or incomplete story');
  const out = path.join(utils.OUTPUT, `picstory-${st.id}`); fs.rmSync(out, { recursive: true, force: true }); utils.ensureDirectory(out);
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try {
    const list = slides(st);
    for (let i = 0; i < list.length; i += 1) {
      const work = path.join(utils.ROOT, '.render-work', `picstory-${i}.html`);
      fs.writeFileSync(work, page(st, baseUrl, list[i]));
      const p = await browser.newPage({ viewport: { width: 1080, height: 1350 } });
      const errors = await utils.preparePage(p, `${baseUrl}${utils.renderHtmlPath(work)}`, 1080, 1350);
      await p.evaluate(() => document.fonts.ready);
      const bad = await p.evaluate(() => {
        for (const el of document.querySelectorAll('[data-fit]')) { let s = 50; while (el.scrollHeight > 200 && s > 38) { s -= 2; el.style.fontSize = `${s}px`; } }
        const foot = document.querySelector('.foot').getBoundingClientRect().top;
        return [...document.querySelectorAll('.en,.hy,.k,.swipe,.wc')].filter((e) => e.getBoundingClientRect().bottom > foot - 6 || e.getBoundingClientRect().right > 1030).map((e) => e.textContent.slice(0, 40));
      });
      if (errors.length || bad.length) throw new Error(`slide ${i + 1}: ${errors.join(' | ')} ${JSON.stringify(bad)}`);
      await p.screenshot({ path: path.join(out, `${String(i + 1).padStart(2, '0')}.jpg`), type: 'jpeg', quality: 92 });
      await p.close();
    }
    const sp = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
    const sw = path.join(utils.ROOT, '.render-work', 'picstory-story.html');
    fs.writeFileSync(sw, storyPage(st, baseUrl));
    const se = await utils.preparePage(sp, `${baseUrl}${utils.renderHtmlPath(sw)}`, 1080, 1920);
    await sp.evaluate(() => document.fonts.ready);
    if (se.length) throw new Error(`story: ${se.join(' | ')}`);
    await sp.screenshot({ path: path.join(out, 'story.jpg'), type: 'jpeg', quality: 93 });
    await sp.close();
    console.log(`${st.id}: ${list.length} slides + story → ${out}`);
  } finally { await browser.close(); server.close(); }
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

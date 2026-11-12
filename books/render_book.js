// Weekly word book: the week's 10-words lists and phrasal verbs as a printable A4 PDF.
// Usage: node books/render_book.js <book-id>   (writes to the sample output folder)
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');
const utils = require('../reels/render_utils');

const BOOKS = JSON.parse(fs.readFileSync(path.join(__dirname, 'books.json'), 'utf8')).books;
const W10 = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/words10.json'), 'utf8')).lists.map((l) => [l.id, l]));
const PV = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/phrasal.json'), 'utf8')).sets.map((s) => [s.id, s]));
const PALETTE = ['#B9790B', '#1C8AA3', '#B23F78', '#3E5FD9', '#2E9E6A', '#6A49E2'];
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');

function html(book, baseUrl) {
  const f = utils.fontUrls(baseUrl);
  const ext = `${baseUrl}/node_modules/@fontsource-variable/inter/files/inter-latin-ext-wght-normal.woff2`;
  const logo = `data:image/svg+xml;base64,${fs.readFileSync(path.join(utils.ROOT, 'assets/logo-ig.svg')).toString('base64')}`;
  const foot = `<div class="foot"><span>Gayane Torosyan · English Reading Room</span><span>Անհատական և խմբային դասեր · գրե՛ք Direct-ով <b>@english.readingroom</b></span></div>`;
  const listHtml = (l) => { const c = PALETTE[(l.number - 1) % PALETTE.length]; const tw = l.theme.split(' ');
    return `<section class="list" style="--c:${c}"><div class="lh"><span class="tag">10 WORDS · ${String(l.number).padStart(2, '0')}</span><span class="lv">${l.level}</span></div>
    <h2>${esc(tw.slice(0, -1).join(' '))} <em>${esc(tw.at(-1))}</em></h2><div class="sub">${esc(l.theme_hy)}</div>
    <table>${l.words.map((w, i) => `<tr><td class="n">${i + 1}</td><td class="en">${esc(w.en)}</td><td class="ipa">${esc(w.ipa)}</td><td class="hy">${esc(w.hy)}</td><td class="chk"></td></tr>`).join('')}</table></section>`; };
  const pvHtml = (s) => { const c = PALETTE[(s.number + 2) % PALETTE.length];
    return `<section class="list pv" style="--c:${c}"><div class="lh"><span class="tag">PHRASAL VERBS · ${String(s.number).padStart(2, '0')}</span><span class="lv">${s.level}</span></div>
    <h2>Phrasal verbs with <em>${s.verb.toLowerCase()}</em></h2>
    ${s.items.map((it) => { const w = it.en.split(' '); return `<div class="pi"><div class="ph"><b>${esc(w[0])} <em>${esc(w.slice(1).join(' '))}</em></b><span>${esc(it.hy)}</span></div><div class="ex">${esc(it.example)}</div><div class="exhy">${esc(it.example_hy)}</div></div>`; }).join('')}</section>`; };
  const lists = book.lists.map((id) => W10[id]); const pvs = book.phrasal.map((id) => PV[id]);
  const pages = [];
  for (let i = 0; i < lists.length; i += 2) pages.push(lists.slice(i, i + 2).map(listHtml).join(''));
  for (let i = 0; i < pvs.length; i += 2) pages.push(pvs.slice(i, i + 2).map(pvHtml).join(''));
  return `<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,"><style>
@font-face{font-family:Lit;src:url(${f.literata})}@font-face{font-family:Inter;src:url(${f.inter})}@font-face{font-family:Arm;src:url(${f.armenian})}
@font-face{font-family:IPA;src:url(${f.inter});unicode-range:U+0000-00FF}@font-face{font-family:IPA;src:url(${ext});unicode-range:U+0100-02FF}
@page{size:A4;margin:0}*{box-sizing:border-box;margin:0}
body{font-family:Inter;color:#17183A}
.page{width:210mm;height:297mm;position:relative;overflow:hidden;background:#F7F2E8;padding:13mm 14mm 18mm 16mm;page-break-after:always}
.page:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4mm;background:#6A49E2}
.cover{display:flex;flex-direction:column;justify-content:center;padding:0 24mm}
.cover img{width:34mm;height:34mm;border-radius:8mm;box-shadow:0 0 0 .5mm #17183A1f;background:#FFFCF6}
.cover .k{margin-top:14mm;font:800 11pt Inter;letter-spacing:4pt;color:#6A49E2}
.cover h1{margin-top:4mm;font:700 54pt/1 Lit;letter-spacing:-1.5pt}.cover h1 em{color:#6A49E2}
.cover .d{margin-top:6mm;font:500 15pt Arm;color:#5E5B74}
.cover .b{margin-top:30mm;font:700 15pt Lit}.cover .m{margin-top:2mm;font:italic 500 12pt Lit;color:#8C89A0}
.cover .how{margin-top:16mm;border-top:.4mm solid #17183A;padding-top:6mm;font:500 11pt/1.6 Arm;color:#3A3A52}
.list{background:#FFFCF6;border:.3mm solid #17183A1a;border-radius:5mm;padding:5mm 7mm;margin-bottom:5mm;border-left:2mm solid var(--c)}
.lh{display:flex;justify-content:space-between;font:800 8.5pt Inter;letter-spacing:2.5pt;color:var(--c)}.lh .lv{color:#17183A;letter-spacing:1pt}
h2{margin-top:1.5mm;font:700 21pt/1.05 Lit;letter-spacing:-.5pt}h2 em{color:var(--c)}
.sub{font:500 11pt Arm;color:#5E5B74;margin-top:1mm}
table{width:100%;border-collapse:collapse;margin-top:3mm}
td{padding:1.25mm 1.5mm;border-bottom:.25mm solid #17183A14;vertical-align:baseline}
td.n{width:7mm;font:italic 600 9pt Lit;color:#8C89A0}td.en{font:700 13pt Lit;white-space:nowrap}td.ipa{font:500 10pt IPA;color:var(--c);white-space:nowrap}
td.hy{font:500 11pt Arm;color:#3A3A52;text-align:right}td.chk{width:6mm}td.chk:after{content:"";display:inline-block;width:3.5mm;height:3.5mm;border:.35mm solid #17183A40;border-radius:1mm;vertical-align:-.5mm}
.pi{padding:2.6mm 0;border-bottom:.25mm solid #17183A14}.pi:last-child{border:0}
.ph{font:700 15pt Lit;display:flex;justify-content:space-between;align-items:baseline}.ph em{color:var(--c)}.ph span{font:500 10.5pt Arm;color:#5E5B74}
.ex{margin-top:1mm;font:500 11.5pt Lit}.exhy{font:500 9.5pt Arm;color:#8C89A0}
.foot{position:absolute;left:16mm;right:16mm;bottom:9mm;display:flex;justify-content:space-between;font:600 8pt Arm;color:#8C89A0}.foot b{color:#6A49E2}
</style></head><body>
<div class="page cover"><img src="${logo}"><div class="k">WORD BOOK · WEEK ${book.number}</div><h1>${lists.length * 10} words<br>and <em>${pvs.length * 4} phrasal verbs</em></h1>
<div class="d">${esc(book.dates_hy)} · ${esc(book.dates)}</div>
<div class="how">Ինչպես օգտագործել. ամեն օր կարդա մեկ թեմա բարձրաձայն, ծածկի՛ր հայերենը և փորձի՛ր հիշել։ Սովորածդ բառը նշի՛ր քառակուսու մեջ։ Ձայնով տարբերակը՝ մեր Reels-ում։</div>
<div class="b">Gayane Torosyan · English Reading Room</div><div class="m">Let's read together</div>${foot}</div>
${pages.map((p) => `<div class="page">${p}${foot}</div>`).join('')}
</body></html>`;
}

async function main() {
  const book = BOOKS.find((b) => b.id === process.argv[2]);
  if (!book) throw new Error('Unknown book');
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try {
    const work = path.join(utils.ROOT, '.render-work', `book-${book.id}.html`);
    fs.writeFileSync(work, html(book, baseUrl));
    const page = await browser.newPage();
    const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(work)}`, 794, 1123);
    const over = await page.evaluate(() => [...document.querySelectorAll('.page')].filter((p) => p.scrollHeight > p.clientHeight + 1).length);
    if (errors.length || over) throw new Error(`book ${book.id}: ${over} overflowing page(s) ${errors.join(' | ')}`);
    const out = path.join(utils.OUTPUT, `english-reading-room-${book.id}.pdf`);
    await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
    console.log(out);
  } finally { await browser.close(); server.close(); }
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

// Designed reel covers for the profile grid: the story's first picture melting into its own paper colour, with the
// title and the Armenian title in the middle 3:4 area that Instagram shows on the profile.
// For every staged reel of the given kinds without a cover: writes cover.jpg into its media folder and sets media.cover_url.
// Usage: node tools/make_covers.js --media-repo ../english-reels-media [--kinds storyvideo,feelstory]
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright-core');
const utils = require('../reels/render_utils');

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const MEDIA = path.resolve(arg('--media-repo', '../english-reels-media'));
const KINDS = arg('--kinds', 'storyvideo,feelstory').split(',');
const BASE = 'https://98torosyan.github.io/english-reels-media';
const DATA = { storyvideo: 'reels/data/storyvideo.json', feelstory: 'reels/data/feelstory.json' };
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');

function paper(file) {
  const r = spawnSync(utils.FFmpeg, ['-v', 'error', '-i', file, '-vf', 'crop=iw:60:0:ih-60,scale=1:1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { encoding: 'buffer' });
  const [R, G, B] = r.stdout; const lift = (c) => Math.round(c + (255 - c) * 0.35);   // a lighter paper keeps the title readable
  return `rgb(${lift(R)},${lift(G)},${lift(B)})`;
}

function html(baseUrl, pic, bg, title, hy) {
  const f = utils.fontUrls(baseUrl);
  return `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Lit;src:url(${f.literata})}@font-face{font-family:Lit;src:url(${baseUrl}/node_modules/@fontsource-variable/literata/files/literata-latin-wght-italic.woff2);font-style:italic}
@font-face{font-family:Arm;src:url(${f.armenian})}@font-face{font-family:Inter;src:url(${f.inter})}
*{margin:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;background:${bg}}
.p{position:absolute;left:0;top:0;width:1080px;height:1300px;overflow:hidden}.p img{width:100%;height:100%;object-fit:cover;object-position:50% 30%}
.p:after{content:"";position:absolute;left:0;right:0;bottom:0;height:520px;background:linear-gradient(transparent,${bg} 88%)}
.t{position:absolute;left:80px;right:80px;top:1150px;text-align:center;color:#2B1E14}
.t h1{font:600 italic 104px/1.02 Lit;letter-spacing:-2px;text-wrap:balance}
.t p{margin-top:26px;font:600 40px Arm;color:#5b4636}
.b{position:absolute;left:0;right:0;bottom:90px;text-align:center;font:800 22px Inter;letter-spacing:6px;color:#2B1E1466}
</style></head><body><div class="p"><img src="${pic}"></div><div class="t"><h1>${esc(title)}</h1><p>${esc(hy)}</p></div><div class="b">@ENGLISH.READINGROOM</div></body></html>`;
}

async function main() {
  const qPath = path.join(utils.ROOT, 'queue.json'); const q = JSON.parse(fs.readFileSync(qPath, 'utf8'));
  const stories = Object.fromEntries(KINDS.filter((k) => DATA[k]).map((k) => [k, Object.fromEntries(JSON.parse(fs.readFileSync(path.join(utils.ROOT, DATA[k]), 'utf8')).stories.map((s) => [s.id, s]))]));
  const force = process.argv.includes('--force');
  const todo = q.items.filter((i) => KINDS.includes(i.kind) && i.format === 'REELS' && i.review_status === 'staged' && !i.published_at && (force || !i.media?.cover_url));
  if (!todo.length) { console.log('no covers needed'); return; }
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  try {
    for (const it of todo) {
      const st = stories[it.kind]?.[it.content_id]; const pic = path.join(utils.ROOT, 'assets', it.kind, it.content_id, '1.jpg');
      if (!st || !fs.existsSync(pic)) { console.log(`skip ${it.id}`); continue; }
      const work = path.join(utils.ROOT, '.render-work', 'cover.html');
      fs.writeFileSync(work, html(baseUrl, `${baseUrl}/assets/${it.kind}/${it.content_id}/1.jpg`, '#F3E6D3', st.title, st.title_hy));   // one warm paper for every cover: a calm, even grid
      const p = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
      await utils.preparePage(p, `${baseUrl}${utils.renderHtmlPath(work)}`, 1080, 1920);
      await p.evaluate(() => Promise.all([document.fonts.load('italic 600 104px Lit', 'Ab'), document.fonts.load('600 40px Arm', 'Աբ'), document.fonts.ready, ...[...document.images].map((i) => i.decode().catch(() => null))]));
      const over = await p.evaluate(() => document.querySelector('.t').getBoundingClientRect().bottom);
      if (over > 1660) throw new Error(`${it.id}: title too long for the grid area`);
      const folder = path.join(MEDIA, it.id); fs.mkdirSync(folder, { recursive: true });
      await p.screenshot({ path: path.join(folder, 'cover.jpg'), type: 'jpeg', quality: 93 }); await p.close();
      it.media.cover_url = `${BASE}/${it.id}/cover.jpg`; delete it.thumb_offset;
      console.log(`cover ${it.id}`);
    }
  } finally { await browser.close(); server.close(); }
  fs.writeFileSync(qPath, `${JSON.stringify(q, null, 2)}\n`);
}
main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });

// Render branded 1080×1920 Instagram Story images from stories/stories.json.
const fs = require('node:fs'); const path = require('node:path');
const { chromium } = require('playwright-core'); const utils = require('../reels/render_utils');
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, 'stories.json'), 'utf8'));
const HTML = (s) => `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Inter;src:url("__INTER_FONT__")}@font-face{font-family:Literata;src:url("__LITERATA_FONT__")}@font-face{font-family:NotoArmenian;src:url("__ARMENIAN_FONT__")}
*{margin:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;color:#fff;font-family:Inter,sans-serif;background:radial-gradient(760px 700px at 85% 8%,#6A49E2aa,transparent 70%),radial-gradient(700px 700px at 0% 80%,#5A3B8C99,transparent 70%),linear-gradient(165deg,#17183A,#2A1E4D 60%,#17183A)}
.top{position:absolute;top:250px;left:90px;right:90px;display:flex;align-items:center;gap:22px}.top img{width:92px;height:92px;border-radius:26px}
.bn{font:700 36px Literata,serif}.bs{margin-top:6px;color:#A891F7;font:800 20px Inter;letter-spacing:5px}
.rb{position:absolute;top:380px;left:92px;display:flex;gap:8px}.rb i{width:42px;height:8px;border-radius:8px}
.tag{position:absolute;top:470px;left:92px;padding:12px 24px;border-radius:99px;border:1.5px solid #A891F766;color:#E9C46A;font:800 24px Inter;letter-spacing:4px}
.card{position:absolute;left:70px;right:70px;top:600px;padding:70px 64px;border-radius:46px;background:linear-gradient(155deg,#6A49E233,#ffffff0a 60%);border:1.5px solid #A891F755;box-shadow:0 30px 80px #07061588}
h1{font:700 96px/1.08 Literata,serif;letter-spacing:-1.5px}h1 em{color:#E9C46A;font-style:italic}
.en{margin-top:44px;font:600 46px/1.35 Literata,serif;color:#fff}.hy{margin-top:34px;padding-top:34px;border-top:1.5px solid #A891F744;font:500 40px/1.5 NotoArmenian,sans-serif;color:#E4DEFA}
.foot{position:absolute;left:0;right:0;bottom:400px;text-align:center}.foot span{display:inline-block;padding:20px 40px;border-radius:99px;background:#E9C46A;color:#17183A;font:800 34px Inter}
.h{position:absolute;bottom:330px;left:0;right:0;text-align:center;color:#A891F7;font:800 24px Inter;letter-spacing:4px}
</style></head><body><div class="top"><img src="__LOGO_DATA__"><div><div class="bn">Gayane Torosyan</div><div class="bs">ENGLISH READING ROOM</div></div></div>
<div class="rb"><i style="background:#B23F78"></i><i style="background:#7A4FD6"></i><i style="background:#3E5FD9"></i><i style="background:#1C8AA3"></i><i style="background:#2E9E6A"></i><i style="background:#E8A317"></i></div>
<div class="tag">${s.tag}</div><div class="card"><h1>${s.title}</h1><div class="en">${s.en}</div><div class="hy">${s.hy}</div></div>
<div class="foot"><span>${s.foot}</span></div><div class="h">@english.readingroom</div></body></html>`;
(async () => {
  const { server, baseUrl } = await utils.startStaticServer();
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  const out = path.join(utils.OUTPUT, 'stories'); utils.ensureDirectory(out);
  const work = path.join(utils.ROOT, '.render-work'); utils.ensureDirectory(work);
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const s of DATA.filter((x) => !process.argv[2] || x.id === process.argv[2])) {
    const f = path.join(work, 'story.html'); fs.writeFileSync(f, utils.htmlAssets(HTML(s), baseUrl));
    await page.goto(`${baseUrl}${utils.renderHtmlPath(f)}`, { waitUntil: 'networkidle' });
    await page.evaluate(() => Promise.all([document.fonts.load('40px NotoArmenian', 'Աբ'), document.fonts.load('40px Literata', 'Ab')]));
    await page.screenshot({ path: path.join(out, `story-${s.id}.jpg`), type: 'jpeg', quality: 93 });
    console.log('story', s.id);
  }
  await browser.close(); server.close();
})();

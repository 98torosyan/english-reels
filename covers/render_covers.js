// Renders .render-work/covers.json into <OUTPUT>/covers/<id>.jpg (JPEG, as Instagram requires).
const fs = require('node:fs'); const path = require('node:path');
const { chromium } = require('playwright-core'); const utils = require('../reels/render_utils');
(async () => {
  const specs = JSON.parse(fs.readFileSync(path.join(utils.ROOT, '.render-work/covers.json'), 'utf8'));
  const only = process.argv.slice(2); const out = path.join(utils.OUTPUT, 'covers'); utils.ensureDirectory(out);
  const { server, baseUrl } = await utils.startStaticServer();
  const fonts = `${baseUrl}/node_modules/@fontsource-variable`;
  const html = utils.htmlAssets(fs.readFileSync(path.join(__dirname, 'cover.html'), 'utf8'), baseUrl)
    .replaceAll('__LITERATA_ITALIC__', `${fonts}/literata/files/literata-latin-wght-italic.woff2`)
    .replaceAll('__INTER_EXT__', `${fonts}/inter/files/inter-latin-ext-wght-normal.woff2`)
    .replaceAll('__INTER_GREEK__', `${fonts}/inter/files/inter-greek-wght-normal.woff2`);
  const htmlPath = path.join(utils.ROOT, '.render-work', 'cover.html'); fs.writeFileSync(htmlPath, html);
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome' });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto(`${baseUrl}${utils.renderHtmlPath(htmlPath)}`);
  await page.evaluate(() => Promise.all([document.fonts.load('700 100px Lit', 'Ab'), document.fonts.load('italic 600 100px Lit', 'Ab'),
    document.fonts.load('40px Arm', 'Աբ'), document.fonts.load('40px IPA', 'ʃɪiːθ'), document.fonts.load('800 20px Inter', 'A')]).then(() => document.fonts.ready));
  for (const s of specs) {
    if (only.length && !only.includes(s.id)) continue;
    await page.setViewportSize({ width: 1080, height: s.h });
    await page.evaluate((x) => window.render(x), s);
    const bad = await page.evaluate(() => [...document.querySelectorAll('h1,.sub,.hy')].some((e) => e.scrollWidth > 885));
    if (bad) console.log(`WARN ${s.id}: text wider than the page`);
    const png = path.join(out, `${s.id}.png`);
    await page.screenshot({ path: png });
    require('node:child_process').execFileSync(utils.FFmpeg, ['-y', '-loglevel', 'error', '-i', png, '-q:v', '2', path.join(out, `${s.id}.jpg`)]);
    fs.unlinkSync(png);
  }
  await browser.close(); server.close(); console.log('covers done');
})();

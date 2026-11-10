const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');
const utils = require('../reels/render_utils');

const RULES = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'carousels/data/rules.json'), 'utf8'));
const LISTS = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'carousels/data/lists.json'), 'utf8'));

const TESTS = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'carousels/data/tests.json'), 'utf8'));

function testPlan(test) {
 const base = { level: 'UFAR · EXAM PREP', total: test.items.length + 3, series: `UFAR MINI-TEST · №${test.num}`, rule: '' };
 return [
 { ...base, kind: 'testhook', title: "Can you pass this <em>UFAR</em> test?", subtitle: 'Իսկական UFAR ձևաչափով 5 հարց։ Լուծի՛ր և ստուգի՛ր պատասխաններդ վերջին սլայդում։', count: test.items.length },
 ...test.items.map((it, i) => ({ ...base, kind: 'q', title: `Question <em>${i + 1}</em>`, q: escapeHtml(it.q), opts: it.o.map(escapeHtml), num: i + 1 })),
 { ...base, kind: 'answers', title: 'Check your <em>answers</em>', answers: test.items.map((it, i) => `${i + 1} — ${String.fromCharCode(65 + it.a)} · ${escapeHtml(it.o[it.a])}`) },
 { ...base, kind: 'save', title: '', rule: 'Քանի՞ ճիշտ պատասխան ունեցար։ Գրի՛ր մեկնաբանություններում Պահպանի՛ր և ուղարկի՛ր քննությանը պատրաստվող ընկերոջդ։' },
 ].map((slide, index) => ({ ...slide, index }));
}

function welcomePlan() {
 const base = { level: 'WELCOME', total: 6, series: 'ENGLISH READING ROOM', rule: '' };
 const li = (en, hy) => `<div class="wl"><div class="wl-en">${en}</div><div class="wl-hy">${hy}</div></div>`;
 return [
 { ...base, kind: 'page', title: 'Welcome to <em>English Reading Room</em>', html: `<div class="big-num" style="font-size:120px">Hello!</div><div class="item-hy" style="font-size:38px">Բարի գալուստ։ Այստեղ անգլերենը սովորում ենք պատմություններով, պարզ կանոններով և ամենօրյա փոքր քայլերով։</div><div class="swipe">Swipe →</div>` },
 { ...base, kind: 'page', title: 'Who <em>teaches</em> here', html: `<div class="item-en" style="font-size:58px">Gayane Torosyan</div><div class="item-hy">Անգլերենի ուսուցիչ · Երևան</div><div class="item-ex" style="font-style:normal;font-size:34px">Դասեր աշակերտների համար, ներառյալ միասնական քննության և UFAR-ի նախապատրաստում։</div>` },
 { ...base, kind: 'page', title: 'What you will <em>find</em>', html: li('Story Time', 'Պատմություններ ձայնով և թարգմանությամբ') + li('Fix it', 'Հայախոսների տարածված սխալներ') + li('5-second quiz', 'Ստուգի՛ր քեզ 5 վայրկյանում') + li('UFAR & exam', 'Իսկական ձևաչափով մինի-թեստեր') },
 { ...base, kind: 'page', title: 'Our <em>week</em>', html: li('Mon · Thu · Sun', 'Story Time՝ նոր պատմության մասեր') + li('Tue · Fri', 'Grammar և UFAR carousel-ներ') + li('Wed · Sat', 'Fix it և Quiz') },
 { ...base, kind: 'page', title: 'Free <em>lessons</em> online', html: `<div class="big-num" style="font-size:150px">150</div><div class="item-hy">դաս A1-ից C1՝ ձայնով, բառարանով և թեստերով</div><div class="item-ex" style="font-style:normal;font-size:34px"> Հղումը՝ bio-ում</div>` },
 { ...base, kind: 'save', title: '', rule: 'Հետևի՛ր էջին, պահպանի՛ր դասերը և ուղարկի՛ր ընկերոջդ, ով նույնպես անգլերեն է սովորում ' },
 ].map((slide, index) => ({ ...slide, index }));
}

function listPlan(set) {
 const n = set.items.length + 2;
 const base = { level: set.chip, total: n, series: set.series, rule: '' };
 return [
 { ...base, kind: 'listhook', title: set.title, subtitle: escapeHtml(set.subtitle_hy), count: set.items.length },
 ...set.items.map((it, i) => ({ ...base, kind: 'item', title: set.title, num: i + 1, en: escapeHtml(it.en), hy: escapeHtml(it.hy), example: escapeHtml(it.example), example_hy: escapeHtml(it.example_hy) })),
 { ...base, kind: 'save', title: '', rule: 'Պահպանի՛ր և կիսվի՛ր ընկերոջդ հետ, ով նույնպես անգլերեն է սովորում։' },
 ].map((slide, index) => ({ ...slide, index }));
}
const CHROME = process.env.CHROME_PATH || [
 'C:/Program Files/Google/Chrome/Application/chrome.exe',
 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));

function escapeHtml(value) {
 return String(value).replace(/[&<>"']/g, (char) => ({
 '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
 })[char]);
}

function slidePlan(rule) {
 const clean = {
 level: escapeHtml(rule.level),
 topic: escapeHtml(rule.title),
 rule: escapeHtml(rule.rule),
 pattern: escapeHtml(rule.pattern),
 example: escapeHtml(rule.example),
 example_hy: escapeHtml(rule.example_hy),
 wrong: escapeHtml(rule.wrong),
 fix: escapeHtml(rule.fix),
 practice: escapeHtml(rule.practice),
 answer: escapeHtml(rule.answer),
 };
 return [
 { kind: 'hook', title: clean.topic, rule: clean.example_hy, example: clean.example, pattern: clean.pattern, series: 'GRAMMAR MADE CLEAR' },
 { kind: 'rule', title: 'The <em>rule</em>', rule: clean.rule, pattern: clean.pattern, series: rule.title },
 { kind: 'pattern', title: 'Build the <em>form</em>', rule: clean.rule, pattern: clean.pattern, series: rule.title },
 { kind: 'example', title: 'In real <em>sentences</em>', rule: clean.rule, example: clean.example, example_hy: clean.example_hy, pattern: clean.pattern, series: rule.title },
 { kind: 'mistake', title: 'Fix one common <em>slip</em>', rule: clean.rule, wrong: clean.wrong, fix: clean.fix, series: rule.title },
 { kind: 'practice', title: 'Your <em>turn</em>', rule: clean.rule, practice: clean.practice, answer: clean.answer, series: rule.title },
 { kind: 'save', title: 'Read · Learn · <em>Remember</em>', rule: 'Պահպանի՛ր այս կանոնը և կրկնիր այն հաջորդ գրելուց առաջ։', series: rule.title },
 ].map((slide, index) => ({ ...clean, ...slide, index }));
}

function measure(page) {
 return page.evaluate(() => {
 const selectors = ['.header', '#title', '#card', '#page', '#save', '.footer'];
 const boxes = Object.fromEntries(selectors.map((selector) => {
 const element = document.querySelector(selector);
 const rect = element.getBoundingClientRect();
 return [selector, {
 x: Math.round(rect.x), y: Math.round(rect.y),
 right: Math.round(rect.right), bottom: Math.round(rect.bottom),
 scrollHeight: element.scrollHeight, clientHeight: element.clientHeight,
 }];
 }));
 return {
 width: document.documentElement.clientWidth,
 height: document.documentElement.clientHeight,
 armenianFont: document.fonts.check('32px NotoArmenian', 'Հայերեն տեքստ'),
 latinFont: document.fonts.check('32px Literata', 'English reading'),
 boxes,
 };
 });
}

async function renderCarousel({ browser, baseUrl, ruleId, outputDirectory }) {
 const test = TESTS.find((item) => item.id === ruleId);
 const list = LISTS.find((item) => item.id === ruleId) || test;
 const rule = RULES.find((item) => item.id === ruleId) || list || (ruleId === 'welcome' ? { id: 'welcome' } : null);
 if (!rule) throw new Error(`Unknown carousel rule: ${ruleId}`);
 const template = fs.readFileSync(path.join(utils.ROOT, 'carousels/templates/carousel.html'), 'utf8');
 const html = utils.htmlAssets(template, baseUrl);
 const working = path.join(utils.ROOT, '.render-work');
 utils.ensureDirectory(working);
 const htmlPath = path.join(working, 'carousel.html');
 fs.writeFileSync(htmlPath, html, 'utf8');

 const target = outputDirectory || path.join(utils.OUTPUT, `carousel-${rule.id}`);
 utils.ensureDirectory(target);
 const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
 const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1350);
 const plan = ruleId === 'welcome' ? welcomePlan() : test ? testPlan(test) : list ? listPlan(list) : slidePlan(rule).map((x) => ({ ...x, total: 7, level: `${rule.level} · GRAMMAR` }));
 const firstLayout = await (async () => {
 await page.evaluate((slide) => window.setSlide(slide), plan[0]);
 await page.evaluate(async () => {
 await document.fonts.load('32px NotoArmenian', 'Հայերեն տեքստ');
 await document.fonts.load('32px Literata', 'English reading');
 await document.fonts.ready;
 });
 return measure(page);
 })();
 console.log(`Carousel ${rule.id} first slide: ${JSON.stringify(firstLayout)}`);
 if (firstLayout.width !== 1080 || firstLayout.height !== 1350 || !firstLayout.armenianFont || !firstLayout.latinFont) {
 throw new Error('Carousel dimensions or required fonts did not load correctly.');
 }

 const slides = [];
 for (const slide of plan) {
 await page.evaluate((data) => window.setSlide(data), slide);
 const state = await page.evaluate(() => ({
 saveHidden: document.getElementById('save').hidden,
 saveDisplay: getComputedStyle(document.getElementById('save')).display,
 cardHidden: document.getElementById('card').hidden,
 }));
 if (slide.kind === 'save' ? (state.saveHidden || state.saveDisplay === 'none' || !state.cardHidden) : (!state.saveHidden || state.saveDisplay !== 'none' || state.cardHidden)) {
 throw new Error(`Carousel slide visibility is incorrect for slide ${slide.index + 1}.`);
 }
 const filename = `${String(slide.index + 1).padStart(2, '0')}-${rule.id}.png`;
 const filePath = path.join(target, filename);
 await page.screenshot({ path: filePath, type: 'png' });
 slides.push(filePath);
 }
 const lastLayout = await measure(page);
 console.log(`Carousel ${rule.id} last slide: ${JSON.stringify(lastLayout)}`);
 await page.close();
 if (errors.length) throw new Error(`Carousel template console errors: ${errors.join(' | ')}`);
 return { rule: rule.id, slideCount: slides.length, width: 1080, height: 1350, slides };
}

async function standalone() {
 if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Install location for Google Chrome was not found. Set CHROME_PATH if it is installed elsewhere.');
 const ruleId = process.argv[2] || 'tenses';
 const { server, baseUrl } = await utils.startStaticServer();
 let browser;
 try {
 browser = await chromium.launch({ executablePath: CHROME, headless: true });
 const result = await renderCarousel({ browser, baseUrl, ruleId });
 console.log(JSON.stringify(result, null, 2));
 } finally {
 if (browser) await browser.close();
 server.close();
 }
}

if (require.main === module) {
 standalone().catch((error) => {
 console.error(error.stack || error.message);
 process.exitCode = 1;
 });
}

module.exports = { renderCarousel, slidePlan };

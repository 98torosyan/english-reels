const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');
const utils = require('./render_utils');

const LESSON_ORDER = ['zoo', 'saturday-market', 'my-garden'];
const TRANSLATIONS = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'assets/lessons/translations.hy.json'), 'utf8'));
const CARDS = JSON.parse(fs.readFileSync(path.join(utils.ROOT, 'reels/data/cards.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));
const FPS = 30;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

function splitSentences(paragraph) {
  return paragraph.trim().split(/(?<=[.!?])["”]?[\s]+/).filter(Boolean);
}

function loadLesson(slug) {
  const directory = path.join(utils.ROOT, 'assets', 'lessons');
  const lesson = JSON.parse(fs.readFileSync(path.join(directory, `${slug}.lesson.json`), 'utf8'));
  const timing = JSON.parse(fs.readFileSync(path.join(directory, `${slug}.json`), 'utf8'));
  const translations = TRANSLATIONS[slug];
  const sentences = [];
  let wordIndex = 0;
  for (let part = 0; part < lesson.text.length; part += 1) {
    const partSentences = splitSentences(lesson.text[part]);
    const partTranslations = translations[part];
    if (partSentences.length !== partTranslations.length) {
      throw new Error(`${slug} part ${part + 1}: Armenian translation count does not match the source sentence count.`);
    }
    if (partTranslations.some((translation) => !String(translation).trim())) {
      throw new Error(`${slug} part ${part + 1}: add and review every Armenian sentence translation before rendering.`);
    }
    for (let sentenceIndex = 0; sentenceIndex < partSentences.length; sentenceIndex += 1) {
      const words = partSentences[sentenceIndex].trim().split(/\s+/);
      const timedWords = words.map((word) => {
        const timingPair = timing.words[wordIndex];
        if (!timingPair) throw new Error(`${slug}: timing data ended before the story text.`);
        wordIndex += 1;
        return [word, Number(timingPair[0]), Number(timingPair[1])];
      });
      sentences.push({ part: part + 1, text: partSentences[sentenceIndex], hy: partTranslations[sentenceIndex], words: timedWords });
    }
  }
  if (wordIndex !== timing.words.length || sentences.length !== timing.starts.length) {
    throw new Error(`${slug}: story text (${sentences.length} sentences, ${wordIndex} words) does not match the audio timings (${timing.starts.length} sentences, ${timing.words.length} words).`);
  }
  return { lesson, sentences, audioPath: path.join(directory, `${slug}.mp3`) };
}

function storyPayload(slug, part) {
  const { lesson, sentences, audioPath } = loadLesson(slug);
  const rows = sentences.filter((sentence) => sentence.part === part);
  const firstOriginal = rows[0].words[0][1];
  const clipStart = Math.max(0, firstOriginal - 4.02);
  const data = {
    s: rows.map((sentence) => ({
      w: sentence.words.map(([word, start, end]) => [word, Number((start - clipStart).toFixed(3)), Number((end - clipStart).toFixed(3))]),
      hy: sentence.hy,
    })),
    end: Number((rows.at(-1).words.at(-1)[2] - clipStart).toFixed(3)),
    keywords: lesson.words.map(([word]) => word.toLowerCase()),
  };
  return {
    lesson,
    part,
    data,
    audioPath,
    audioStart: clipStart,
    duration: Number((data.end + 2.6).toFixed(3)),
  };
}

function buildStoryHtml(payload, baseUrl) {
  const sourcePath = path.join(utils.ROOT, 'reels/source-template/reel.html');
  let html = fs.readFileSync(sourcePath, 'utf8');
  const logoSvg = fs.readFileSync(path.join(utils.ROOT, 'assets/icon.svg'), 'utf8').trim();
  const font = utils.fontUrls(baseUrl);
  html = html.replace(/(<div id="top">)<svg[\s\S]*?<\/svg>/, `$1${logoSvg}`);
  html = html.replace(/<div id="out"><svg[\s\S]*?<\/svg>/, `<div id="out">${logoSvg}`);
  html = html.replace(/@font-face\{font-family:Lit;src:url\(file:\/\/\/tmp\/Literata\.ttf\)\}/, `@font-face{font-family:Lit;src:url(${font.literata}) format('woff2');font-weight:100 900}`);
  html = html.replace(/@font-face\{font-family:Hy;src:url\(file:\/\/\/tmp\/NotoSansArmenian\.ttf\)\}/, `@font-face{font-family:Hy;src:url(${font.armenian}) format('woff2');font-weight:100 900}`);
  html = html.replace('</style>', `@font-face{font-family:Inter;src:url(${font.inter}) format('woff2');font-weight:100 900}</style>`);
  const serialized = JSON.stringify(payload.data).replace(/</g, '\\u003c');
  const dataPattern = /const D=\{[\s\S]*?\}, END=D\.end, TOTAL=END\+2\.6;/;
  if (!dataPattern.test(html)) throw new Error('Could not locate the timing data in the story template.');
  html = html.replace(dataPattern, `const D=${serialized}, END=D.end, TOTAL=END+2.6;`);

  const level = escapeHtml(payload.lesson.level);
  const part = payload.part;
  html = html.replace(/<div id="chip">[\s\S]*?<\/div>/, `<div id="chip"><i class="a">${level}</i><i>SHORT STORY</i><i>PART ${part}</i></div>`);
  const words = payload.lesson.words.slice(0, 3).map(([word, hy]) => `<div><b>${escapeHtml(word)}</b><span>${escapeHtml(hy)}</span></div>`).join('');
  const titleWords = payload.lesson.title.split(/\s+/);
  const last = titleWords.pop();
  const title = `${escapeHtml(titleWords.join(' '))}<br><em>${escapeHtml(last)}</em>`;
  const storyEnd = part < 3 ? `<h2>Part ${part + 1} <em>tomorrow</em></h2>` : '<h2>Story <em>complete</em></h2>';
  html = html.replace(/<div id="title">[\s\S]*?<\/div>/, `<div id="title">${title}</div>`);
  html = html.replace(/<div id="words">[\s\S]*?<\/div><div id="card">/, `<div id="words"><h4>NEW WORDS · ՆՈՐ ԲԱՌԵՐ</h4>${words}</div><div id="card">`);
  html = html.replace(/<h2>Part 2 <em>tomorrow<\/em><\/h2>/, storyEnd);
  html = html.replace('</head>', '<link rel="icon" href="data:,"></head>');
  return html;
}

function sentenceAudio(slug, sentenceNumber) {
  const { lesson, sentences, audioPath } = loadLesson(slug);
  const sentence = sentences[sentenceNumber];
  if (!sentence) throw new Error(`${slug}: audio sentence ${sentenceNumber} is missing.`);
  const firstTime = sentence.words[0][1];
  const clipStart = Math.max(0, firstTime - 4.02);
  const wordTimings = sentence.words.map(([, start, end]) => [
    Number((start - clipStart).toFixed(3)), Number((end - clipStart).toFixed(3)),
  ]);
  const sentenceText = sentence.words.map(([word]) => word).join(' ');
  return {
    lesson,
    sentenceText,
    audioPath,
    audioStart: clipStart,
    wordTimings,
    duration: Number((wordTimings.at(-1)[1] + 2.6).toFixed(3)),
  };
}

function buildCardHtml(baseUrl) {
  const template = fs.readFileSync(path.join(utils.ROOT, 'reels/templates/card.html'), 'utf8');
  return utils.htmlAssets(template, baseUrl);
}

async function measureStory(page) {
  return page.evaluate(() => {
    const ids = ['#top', '#title', '#card', '#en', '#hy', '#out'];
    const boxes = Object.fromEntries(ids.map((selector) => {
      const element = document.querySelector(selector);
      const rect = element.getBoundingClientRect();
      return [selector, { x: Math.round(rect.x), y: Math.round(rect.y), right: Math.round(rect.right), bottom: Math.round(rect.bottom), scrollHeight: element.scrollHeight, clientHeight: element.clientHeight }];
    }));
    return {
      width: document.documentElement.clientWidth,
      height: document.documentElement.clientHeight,
      armenianFont: document.fonts.check('32px Hy', 'Հայերեն տեքստ'),
      latinFont: document.fonts.check('32px Lit', 'English reading'),
      boxes,
    };
  });
}

async function measureCard(page) {
  return page.evaluate(() => {
    const selectors = ['.header', '#headline', '#panel', '#armenian', '#countdown', '#outro'];
    const boxes = Object.fromEntries(selectors.map((selector) => {
      const element = document.querySelector(selector);
      const rect = element.getBoundingClientRect();
      return [selector, { x: Math.round(rect.x), y: Math.round(rect.y), right: Math.round(rect.right), bottom: Math.round(rect.bottom), scrollHeight: element.scrollHeight, clientHeight: element.clientHeight }];
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

async function renderStory(browser, baseUrl, slug, part, outputName) {
  const data = storyPayload(slug, part);
  const working = path.join(utils.ROOT, '.render-work');
  const output = utils.OUTPUT;
  const frames = path.join(output, `.frames-${outputName}`);
  const videoPath = path.join(output, `${outputName}.mp4`);
  const posterPath = path.join(output, `${outputName}.png`);
  utils.ensureDirectory(working);
  utils.ensureDirectory(output);
  const htmlPath = path.join(working, 'story.html');
  fs.writeFileSync(htmlPath, buildStoryHtml(data, baseUrl), 'utf8');

  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  const layout = await measureStory(page);
  console.log(`Story ${slug} part ${part}: ${JSON.stringify(layout)}`);
  if (layout.width !== 1080 || layout.height !== 1920 || !layout.armenianFont || !layout.latinFont) {
    throw new Error('Story dimensions or required fonts did not load correctly.');
  }
  const wordHeight = layout.boxes['#en'].scrollHeight;
  if (wordHeight > layout.boxes['#card'].clientHeight + 6) throw new Error('Story text exceeds its card.');
  await utils.renderFrames(page, data.duration, frames, posterPath, Math.min(data.duration - 1, 7), FPS);
  if (errors.length) throw new Error(`Story template console errors: ${errors.join(' | ')}`);
  await page.close();
  utils.encodeVideo(frames, data.audioPath, data.audioStart, data.duration, videoPath, FPS);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info };
}

async function renderCard(browser, baseUrl, input, audio, outputName, correctIndex = -1) {
  const output = utils.OUTPUT;
  const frames = path.join(output, `.frames-${outputName}`);
  const videoPath = path.join(output, `${outputName}.mp4`);
  const posterPath = path.join(output, `${outputName}.png`);
  const htmlPath = path.join(utils.ROOT, '.render-work', 'card.html');
  fs.writeFileSync(htmlPath, buildCardHtml(baseUrl), 'utf8');
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = await utils.preparePage(page, `${baseUrl}${utils.renderHtmlPath(htmlPath)}`, 1080, 1920);
  const config = { ...input, wordTimings: audio.wordTimings || [], correctIndex };
  await page.evaluate(({ data, duration }) => {
    window.configure(data);
    window.REEL_KIND = data.kind;
    window.REEL_DURATION = duration;
    window.WORD_TIMINGS = data.wordTimings;
    window.CORRECT_INDEX = data.correctIndex;
    window.seek(0);
  }, { data: config, duration: audio.duration });
  const layout = await measureCard(page);
  console.log(`${input.kind} card: ${JSON.stringify(layout)}`);
  if (layout.width !== 1080 || layout.height !== 1920 || !layout.armenianFont || !layout.latinFont) {
    throw new Error(`${input.kind} dimensions or required fonts did not load correctly.`);
  }
  if (input.kind === 'quiz') {
    for (const [time, expected] of [[0.5, '3'], [1.7, '2'], [2.6, '1']]) {
      const actual = await page.evaluate((value) => {
        window.seek(value);
        return document.getElementById('countdown').textContent;
      }, time);
      if (actual !== expected) throw new Error(`Quiz countdown at ${time}s should show ${expected}.`);
    }
  }
  await utils.renderFrames(page, audio.duration, frames, posterPath, input.kind === 'quiz' ? 0.5 : 5.2, FPS);
  if (errors.length) throw new Error(`${input.kind} template console errors: ${errors.join(' | ')}`);
  await page.close();
  utils.encodeVideo(frames, audio.audioPath, audio.audioStart, audio.duration, videoPath, FPS);
  const info = utils.verifyVideo(videoPath);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(`Rendered ${videoPath}: ${JSON.stringify(info)}`);
  return { videoPath, posterPath, info };
}

async function main() {
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Install location for Google Chrome was not found. Set CHROME_PATH if it is installed elsewhere.');
  const { server, baseUrl } = await utils.startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    const story = await renderStory(browser, baseUrl, 'zoo', 1, 'story-zoo-part-1');

    const mistake = CARDS.mistakes.find((item) => item.id === 'plural-subject');
    const mistakeAudio = sentenceAudio(mistake.audio.lesson, mistake.audio.sentence);
    const mistakeResult = await renderCard(browser, baseUrl, {
      kind: 'mistake', eyebrow: 'GRAMMAR · A1', headline: 'Find the<br><span class="gold">mistake</span>',
      wrong: mistake.wrong, correct: mistake.correct, explanation_hy: mistake.explanation_hy,
    }, mistakeAudio, 'mistakes-present-simple');

    const quiz = CARDS.quizzes.find((item) => item.id === 'plural-verb');
    const quizAudio = sentenceAudio(quiz.audio.lesson, quiz.audio.sentence);
    const quizCorrect = quiz.prompt.replace('___', quiz.answer);
    const quizResult = await renderCard(browser, baseUrl, {
      kind: 'quiz', eyebrow: '3-2-1 · QUICK QUIZ', headline: 'Choose the<br><span class="gold">right verb</span>',
      prompt: quiz.prompt, options: quiz.options, correct: quizCorrect, explanation_hy: quiz.explanation_hy,
    }, quizAudio, 'quiz-present-simple', quiz.options.indexOf(quiz.answer));

    const carousel = require('../carousels/render');
    const carouselResult = await carousel.renderCarousel({ browser, baseUrl, ruleId: 'tenses' });
    console.log(JSON.stringify({ story, mistake: mistakeResult, quiz: quizResult, carousel: carouselResult }, null, 2));
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.stack || error.message);
    process.exitCode = 1;
  });
}

module.exports = { loadLesson, storyPayload, sentenceAudio, renderStory, renderCard };

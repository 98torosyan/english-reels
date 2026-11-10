const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright-core');
const { ROOT, OUTPUT, startStaticServer, ensureDirectory } = require('./render_utils');
const { renderStory, renderCard, sentenceAudio } = require('./render_samples');

const CARDS = JSON.parse(fs.readFileSync(path.join(ROOT, 'reels/data/cards.json'), 'utf8'));
const CHROME = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
].find((candidate) => fs.existsSync(candidate));

function findById(items, id, kind) {
  const item = items.find((entry) => entry.id === id);
  if (!item) throw new Error(`Unknown ${kind} item: ${id}`);
  return item;
}

async function main() {
  const [kind, id, partArgument] = process.argv.slice(2);
  if (!kind || !id) throw new Error('Usage: node reels/generate.js story <lesson-id> <1|2|3> | mistake <id> | quiz <id> | word <id>');
  if (!CHROME || !fs.existsSync(CHROME)) throw new Error('Install location for Google Chrome was not found. Set CHROME_PATH if it is installed elsewhere.');
  ensureDirectory(OUTPUT);
  const { server, baseUrl } = await startStaticServer();
  let browser;
  try {
    browser = await chromium.launch({ executablePath: CHROME, headless: true });
    if (kind === 'story') {
      const part = Number(partArgument);
      if (![1, 2, 3].includes(part)) throw new Error('A story part must be 1, 2, or 3.');
      const result = await renderStory(browser, baseUrl, id, part, `story-${id}-part-${part}`);
      console.log(result.videoPath);
      return;
    }

    let item;
    if (kind === 'mistake') item = findById(CARDS.mistakes, id, 'mistake');
    else if (kind === 'quiz') item = findById(CARDS.quizzes, id, 'quiz');
    else if (kind === 'word') item = findById(CARDS.words, id, 'word');
    else throw new Error(`Unknown reel kind: ${kind}`);

    const audio = item.audio
      ? sentenceAudio(item.audio.lesson, item.audio.sentence)
      : { audioPath: null, audioStart: 0, wordTimings: [], duration: 9 };
    let data;
    let correctIndex = -1;
    if (kind === 'mistake') {
      data = {
        kind, eyebrow: 'GRAMMAR · QUICK FIX', headline: 'Find the<br><span class="gold">mistake</span>',
        wrong: item.wrong, correct: item.correct, explanation_hy: item.explanation_hy,
      };
    } else if (kind === 'quiz') {
      data = {
        kind, eyebrow: '5-SECOND QUIZ', headline: 'Choose the<br><span class="gold">right answer</span>',
        prompt: item.prompt, options: item.options,
        correct: item.prompt.replace('___', item.answer), explanation_hy: item.explanation_hy,
      };
      correctIndex = item.options.indexOf(item.answer);
    } else {
      data = {
        kind, eyebrow: 'DAILY ENGLISH · A1', headline: 'Word of the<br><span class="gold">day</span>',
        word: item.word, part_of_speech: item.part_of_speech, armenian: item.armenian,
        example: audio.sentenceText || item.example, example_hy: item.example_hy,
      };
    }
    const result = await renderCard(browser, baseUrl, data, audio, `${kind}-${id}`, correctIndex);
    console.log(result.videoPath);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});

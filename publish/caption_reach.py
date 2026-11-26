"""Captions for a wide, mixed audience: an English first line (what people search for and what shows above "more"),
the Armenian text kept below it, and five hashtags that mix broad English reach with one local tag.
Applied at publish time (run_due.py), so every post gets it; running it twice changes nothing."""
import re

import hashlib

# Instagram allows at most five hashtags per post (since December 2025), so every post gets five, chosen for that post:
# one big learning tag, two that fit the topic, one about the format or level, one for the local audience.
# The choice changes from post to post (seeded by the post's id), so the page reaches different searches.
BROAD = ["#learnenglish", "#englishlearning", "#learningenglish", "#englishonline", "#esl", "#englishteacher", "#studyenglish",
         "#englishclass", "#englishlanguage", "#englishcourse", "#englishstudy", "#englishskills", "#improveyourenglish", "#englishlearners",
         "#efl", "#tefl", "#englishtutor", "#learnenglishonline", "#englishpractice", "#englishfluency"]
TOPICS = {
    "grammar": ["#englishgrammar", "#grammartips", "#englishtips", "#englishmistakes", "#grammar", "#grammarlesson", "#englishrules",
                "#commonmistakes", "#tenses", "#grammarnerd", "#writeinenglish", "#correctenglish"],
    "words": ["#englishvocabulary", "#englishwords", "#vocabulary", "#newwords", "#wordoftheday", "#englishtips", "#vocabularybuilding",
              "#englishexpressions", "#learnwords", "#everydayenglish", "#englishidioms", "#wordsoftheday"],
    "stories": ["#englishstories", "#shortstories", "#storytime", "#readinenglish", "#englishreading", "#easyenglish", "#gradedreaders",
                "#storiesforlearners", "#readingpractice", "#listeningpractice", "#englishlistening", "#storytelling"],
    "speaking": ["#spokenenglish", "#englishconversation", "#speakenglish", "#dailyenglish", "#englishphrases", "#speakingpractice",
                 "#englishspeaking", "#conversationalenglish", "#phrasalverbs", "#realenglish", "#englishdialogue", "#speakfluently"],
    "books": ["#englishliterature", "#classicbooks", "#bookstagram", "#readinenglish", "#booklovers", "#classicliterature",
              "#bookworm", "#readingenglish", "#literature", "#bookish", "#easyreaders", "#booksofinstagram"],
    "travel": ["#travelenglish", "#englishfortravel", "#watercolortravel", "#easyenglish", "#englishvocabulary", "#travelvocabulary",
               "#worldculture", "#countriesoftheworld", "#travelwords", "#watercolor", "#learnwhileyoutravel", "#cultureandlanguage"],
    "quiz": ["#englishquiz", "#englishtest", "#englishpractice", "#englishtips", "#testyourenglish", "#quiztime", "#englishexercise",
             "#englishchallenge", "#grammarquiz"],
}
KIND = {"mistake": "grammar", "rule": "grammar", "quiz": "quiz", "words10": "words", "word": "words", "review": "words", "phrasal": "speaking",
        "dialogue": "speaking", "reading": "stories", "storyvideo": "stories", "story": "stories", "picstory": "stories", "feelstory": "stories",
        "classic": "books", "opposites": "words", "countries": "travel", "motion": "stories"}
FORMAT = {"REELS": ["#englishreels", "#learnenglishwithreels", "#englishlesson", "#a2english", "#englishforbeginners", "#englishvideo",
                    "#reelsenglish", "#b1english", "#englishshorts", "#listenandrepeat"],
          "CAROUSEL": ["#englishlesson", "#englishnotes", "#englishforbeginners", "#a2english", "#englishpractice", "#studynotes",
                       "#englishcards", "#saveforlater", "#b1english", "#swipeandlearn"]}
LOCAL = ["#անգլերեն", "#անգլերենիդասեր", "#անգլերենսովորել", "#yerevan", "#armenia", "#englishinarmenia", "#հայաստան"]


def tags(item):
    h = int(hashlib.sha1(item.get("id", "").encode()).hexdigest(), 16)
    pick = lambda pool, k, skip=(): [t for t in (pool[(h // (7 ** n)) % len(pool)] for n in range(len(pool) * 3)) if t not in skip][:k]
    topic = TOPICS[KIND.get(item.get("kind"), "words")]
    out = pick(BROAD, 1)
    out += [t for t in dict.fromkeys(pick(topic, 4, out))][:2]
    out += pick(FORMAT.get(item.get("format"), FORMAT["REELS"]), 1, out)
    out += pick(LOCAL, 1)
    return list(dict.fromkeys(out))[:5]


HOOK = {"mistake": "Common English mistake: can you spot it?", "rule": "English grammar, made simple: {t}", "quiz": "Quick English quiz: can you get it right?",
        "words10": "10 English words about {t}", "word": "English word of the day: {t}", "review": "Weekly English review: how many do you remember?",
        "phrasal": "Phrasal verbs you will use every day: {t}", "dialogue": "Everyday English conversation: {t}", "reading": "Read and listen in English: {t}",
        "storyvideo": "Learn English with a short story: {t}", "story": "Learn English with a short story: {t}", "picstory": "A picture story in easy English: {t}",
        "feelstory": "A short story in easy English: {t}", "classic": "Classic books in easy English: {t}", "opposites": "English opposites in one picture: {t}",
        "countries": "Learn English and travel: {t}", "motion": "A beautiful story in easy English: {t}"}
ARM = re.compile(r"[Ա-և]")
HOOK_START = tuple(h.split("{t}")[0].split(":")[0] for h in HOOK.values())


def strip_hooks(cap: str) -> str:
    """Drop any English hook lines already at the top, so the hook is never added twice."""
    lines = cap.split("\n")
    while lines and lines[0].startswith(HOOK_START): lines = lines[1:]
    return "\n".join(lines)


def english_title(item):
    """The English name of the post, taken from its own caption (the part without Armenian letters), else from its id."""
    if item.get("kind") == "words10": return str(item.get("content_id", "")).replace("-", " ")
    for line in strip_hooks(item.get("caption", "")).split("\n")[:3]:
        parts = [p.strip() for p in line.split("·") if p.strip() and not ARM.search(p)]
        parts = [p for p in parts if not re.fullmatch(r"(A1|A2|B1|B2|C1)(–(A2|B1|B2))?", p) and p.lower() not in {
            "common english mistakes", "english vocabulary", "english grammar", "english grammar quiz", "weekly review", "daily reading",
            "everyday english dialogue", "english story for learners", "picture story", "classics made easy"}]
        if parts: return re.sub(r"^(Word of the day|Phrasal verbs?|Picture story)\s*:\s*", "", parts[0], flags=re.I)
    return str(item.get("content_id", "")).replace("-", " ").strip().capitalize()


def improve(item):
    """Return the caption for a wide audience (unchanged if already done or not a feed post)."""
    cap = item.get("caption", "")
    if item.get("format") == "STORIES" or not cap.strip(): return cap
    kind = item.get("kind", "")
    hook = HOOK.get(kind, "Learn English: {t}").format(t=english_title(item)).rstrip(": ")
    body = strip_hooks(cap)
    if cap.startswith(hook + "\n") and body == cap[len(hook) + 1:]: return cap
    lines = body.rstrip().split("\n")
    if lines and lines[-1].lstrip().startswith("#"): lines = lines[:-1]
    return f"{hook}\n" + "\n".join(lines).rstrip() + "\n\n" + " ".join(tags(item))


if __name__ == "__main__":   # preview: python publish/caption_reach.py
    import json
    from pathlib import Path
    q = json.loads((Path(__file__).resolve().parents[1] / "queue.json").read_text(encoding="utf-8"))["items"]
    seen = set()
    for i in q:
        if i.get("review_status") == "staged" and i.get("format") != "STORIES" and i["kind"] not in seen:
            seen.add(i["kind"]); c = improve(i); print("==", i["kind"]); print(c.split("\n")[0]); print(c.strip().split("\n")[-1])

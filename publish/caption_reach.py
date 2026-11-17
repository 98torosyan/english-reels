"""Captions for a wide, mixed audience: an English first line (what people search for and what shows above "more"),
the Armenian text kept below it, and five hashtags that mix broad English reach with one local tag.
Applied at publish time (run_due.py), so every post gets it; running it twice changes nothing."""
import re

import hashlib

# Instagram allows at most five hashtags per post (since December 2025), so every post gets five, chosen for that post:
# one big learning tag, two that fit the topic, one about the format or level, one for the local audience.
# The choice changes from post to post (seeded by the post's id), so the page reaches different searches.
BROAD = ["#learnenglish", "#englishlearning", "#learningenglish", "#englishonline", "#esl", "#englishteacher", "#studyenglish"]
TOPICS = {
    "grammar": ["#englishgrammar", "#grammartips", "#englishtips", "#englishmistakes", "#grammar"],
    "words": ["#englishvocabulary", "#englishwords", "#vocabulary", "#newwords", "#wordoftheday", "#englishtips"],
    "stories": ["#englishstories", "#shortstories", "#storytime", "#readinenglish", "#englishreading", "#easyenglish"],
    "speaking": ["#spokenenglish", "#englishconversation", "#speakenglish", "#dailyenglish", "#englishphrases"],
    "books": ["#englishliterature", "#classicbooks", "#bookstagram", "#readinenglish", "#booklovers"],
    "travel": ["#travelenglish", "#englishfortravel", "#watercolortravel", "#easyenglish", "#englishvocabulary"],
    "quiz": ["#englishquiz", "#englishtest", "#englishpractice", "#englishtips"],
}
KIND = {"mistake": "grammar", "rule": "grammar", "quiz": "quiz", "words10": "words", "word": "words", "review": "words", "phrasal": "speaking",
        "dialogue": "speaking", "reading": "stories", "storyvideo": "stories", "story": "stories", "picstory": "stories", "feelstory": "stories",
        "classic": "books", "opposites": "words", "countries": "travel"}
FORMAT = {"REELS": ["#englishreels", "#learnenglishwithreels", "#englishlesson", "#a2english", "#englishforbeginners"],
          "CAROUSEL": ["#englishlesson", "#englishnotes", "#englishforbeginners", "#a2english", "#englishpractice"]}
LOCAL = ["#անգլերեն", "#անգլերենիդասեր", "#անգլերենսովորել"]


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
        "countries": "Learn English and travel: {t}"}
ARM = re.compile(r"[Ա-և]")


def english_title(item):
    """The English name of the post, taken from its own caption (the part without Armenian letters), else from its id."""
    if item.get("kind") == "words10": return str(item.get("content_id", "")).replace("-", " ")
    for line in item.get("caption", "").split("\n")[:3]:
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
    if cap.startswith(hook): return cap
    lines = cap.rstrip().split("\n")
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

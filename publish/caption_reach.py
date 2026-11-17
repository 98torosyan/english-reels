"""Captions for a wide, mixed audience: an English first line (what people search for and what shows above "more"),
the Armenian text kept below it, and five hashtags that mix broad English reach with one local tag.
Applied at publish time (run_due.py), so every post gets it; running it twice changes nothing."""
import re

BROAD = ["#learnenglish", "#englishlearning", "#esl"]
LOCAL = "#անգլերեն"
TOPIC = {"mistake": "#englishgrammar", "rule": "#englishgrammar", "quiz": "#englishquiz", "words10": "#englishvocabulary",
         "word": "#englishvocabulary", "review": "#englishvocabulary", "phrasal": "#phrasalverbs", "dialogue": "#spokenenglish",
         "reading": "#englishreading", "storyvideo": "#englishstories", "story": "#englishstories", "picstory": "#englishstories",
         "feelstory": "#englishstories", "classic": "#englishliterature", "opposites": "#englishvocabulary", "countries": "#englishstories"}
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
    tags = [BROAD[0], TOPIC.get(kind, "#englishvocabulary"), BROAD[1], BROAD[2], LOCAL]
    return f"{hook}\n" + "\n".join(lines).rstrip() + "\n\n" + " ".join(dict.fromkeys(tags))


if __name__ == "__main__":   # preview: python publish/caption_reach.py
    import json
    from pathlib import Path
    q = json.loads((Path(__file__).resolve().parents[1] / "queue.json").read_text(encoding="utf-8"))["items"]
    seen = set()
    for i in q:
        if i.get("review_status") == "staged" and i.get("format") != "STORIES" and i["kind"] not in seen:
            seen.add(i["kind"]); c = improve(i); print("==", i["kind"]); print(c.split("\n")[0]); print(c.strip().split("\n")[-1])

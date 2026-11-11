"""English quality check with LanguageTool (British English, self-hosted in CI).

Checks every English text that appears on screen: cards, dialogues, sounds, stories,
carousels and the 10-words lists (spelling included). Prints a report and exits 1 if
any issue is found, so a bad sentence never reaches Instagram.
LT_URL points to the LanguageTool server (the CI job starts one in Docker)."""
import json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LT = os.environ.get("LT_URL", "https://api.languagetool.org/v2/check")
PUBLIC = "api.languagetool.org" in LT
IGNORE = {"WHITESPACE_RULE", "EN_QUOTES", "DASH_RULE", "UPPERCASE_SENTENCE_START", "PUNCTUATION_PARAGRAPH_END",
          "COMMA_PARENTHESIS_WHITESPACE", "EN_UNPAIRED_BRACKETS", "SENTENCE_FRAGMENT", "I_LOWERCASE",
          "INTERJECTIONS_PUNCTUATION", "SERIAL_COMMA_ON", "PASSIVE_VOICE_SIMPLE"}  # style preferences, not errors
NAMES = {"gayane", "torosyan", "ufar", "yerevan", "armenia", "armenian", "ani", "aram", "lilit", "narek", "mane", "davit", "tigran", "anna", "sona", "hayk", "gor", "sevan"}
load = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).replace("___", "…").strip()

def texts():
    cards = load("reels/data/cards.json")
    for m in cards["mistakes"]: yield f"mistake:{m['id']}", m["correct"]
    for q in cards["quizzes"]: yield f"quiz:{q['id']}", q["prompt"].replace("___", q["answer"])
    for w in cards["words"]: yield f"word:{w['id']}", w["example"]
    for d in load("reels/data/dialogues.json")["dialogues"]:
        for n, l in enumerate(d["lines"]): yield f"dialogue:{d['id']}/{n}", l["en"]
    for s in load("reels/data/sounds.json")["sounds"]: yield f"sound:{s['id']}", s["sentence"]
    for st in load("stories/stories.json"):
        for k, line in enumerate(re.split(r"<br\s*/?>", st.get("en") or "")):
            line = clean(line)
            if line and not line.startswith("Wrong") and "+" not in line and " / " not in line and not re.match(r"^[A-C]\)", line):
                yield f"story:{st['id']}/{k}", line
    for c in load("carousels/data/lists.json") if isinstance(load("carousels/data/lists.json"), list) else load("carousels/data/lists.json").get("lists", []):
        for n, it in enumerate(c.get("items", [])):
            for k in ("en", "example"):
                if it.get(k) and "___" not in it[k]: yield f"carousel:{c['id']}/{n}/{k}", clean(it[k])
    for st in load("reels/data/phrasal.json")["sets"]:
        for n, it in enumerate(st["items"]): yield f"phrasal:{st['id']}/{n}", it["example"]
    for l in load("reels/data/words10.json")["lists"]:
        yield f"words10:{l['id']}", ", ".join(w["en"] for w in l["words"]) + "."

def check(text):
    data = urllib.parse.urlencode({"text": text, "language": "en-GB", "level": "picky" if not PUBLIC else "default"}).encode()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(LT, data=data), timeout=60) as r:
                return [m for m in json.load(r)["matches"] if m["rule"]["id"] not in IGNORE
                        and text[m["offset"]:m["offset"] + m["length"]].lower() not in NAMES]
        except Exception:
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"LanguageTool unreachable for: {text}")

bad = n = 0
for label, text in texts():
    n += 1
    for m in check(text):
        bad += 1
        bit = text[m["offset"]:m["offset"] + m["length"]]
        print(f"✗ {label}: “{text}” [{bit}] → {m['message']} ({m['rule']['id']})")
    if PUBLIC: time.sleep(3.2)
print(f"{bad} issue(s) in {n} texts." if bad else f"✓ English check passed ({n} texts).")
sys.exit(1 if bad else 0)

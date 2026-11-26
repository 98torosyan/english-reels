"""English quality check with LanguageTool (British English, self-hosted in CI).

Checks every English text that appears on screen in the daily readings (spelling included). Prints a report and exits 1 if
any issue is found, so a bad sentence never reaches Instagram.
LT_URL points to the LanguageTool server (the CI job starts one in Docker)."""
import json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LT = os.environ.get("LT_URL", "https://api.languagetool.org/v2/check")
PUBLIC = "api.languagetool.org" in LT
IGNORE = {"WHITESPACE_RULE", "EN_QUOTES", "DASH_RULE", "UPPERCASE_SENTENCE_START", "PUNCTUATION_PARAGRAPH_END",
          "COMMA_PARENTHESIS_WHITESPACE", "EN_UNPAIRED_BRACKETS", "SENTENCE_FRAGMENT", "I_LOWERCASE",
          "INTERJECTIONS_PUNCTUATION", "SERIAL_COMMA_ON", "PASSIVE_VOICE_SIMPLE",
          "EN_UNPAIRED_QUOTES", "RUDE_SARCASTIC"}  # style preferences, not errors
NAMES = {"gayane", "torosyan", "ufar", "yerevan", "armenia", "armenian", "ani", "aram", "lilit", "narek", "mane", "davit", "tigran", "anna", "sona", "hayk", "gor", "sevan", "dilijan", "gata", "toto", "lavash", "leo", "biscuit", "sam", "yuki", "ella", "noah", "lily", "zara", "ben", "mia", "passepartout", "marmee", "morgiana", "bella", "nora", "tonir", "tatev", "lake sevan", "nesbit", "max", "hasmik", "burano", "senso-ji", "abra", "della", "jim", "magi", "johnsy", "behrman", "emma", "clara", "sue", "anahit", "goharik", "nare", "sami", "arman", "kiko", "vahe", "lusine", "arsen", "pumpkin"}
ALLOW = json.loads((ROOT / "qc/data/english_allow.json").read_text(encoding="utf-8"))
load = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
clean = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).replace("___", "…").strip()

def texts():
    for st in load("reels/data/reading.json")["stories"]:
        for k, sent in enumerate(re.split(r"(?<=[.!?'])\s+(?=[A-Z'])", st["en"])): yield f"reading:{st['id']}/{k}", sent

def check(text):
    data = urllib.parse.urlencode({"text": text, "language": "en-GB", "level": "picky" if not PUBLIC else "default"}).encode()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(LT, data=data), timeout=60) as r:
                return [m for m in json.load(r)["matches"] if m["rule"]["id"] not in IGNORE and text not in ALLOW.get(m["rule"]["id"], [])
                        and text[m["offset"]:m["offset"] + m["length"]].lower() not in NAMES]
        except Exception:
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"LanguageTool unreachable for: {text}")

bad = n = 0
ONLY = os.environ.get("ONLY", "")   # e.g. ONLY=talk:the-last-leaf/ checks just one new story
# a new story's character and place names are not in the dictionary: when one story is checked, its capitalised words
# are not reported as spelling mistakes (grammar, lower-case spelling and everything else still are)
STORY_NAMES = {w for label, text in texts() if ONLY and label.startswith(ONLY) for w in re.findall(r"\b[A-Z][a-z]+\b", text)}
for label, text in texts():
    if ONLY and not label.startswith(ONLY): continue
    n += 1
    for m in check(text):
        bit = text[m["offset"]:m["offset"] + m["length"]]
        if m["rule"]["id"].startswith("MORFOLOGIK") and bit in STORY_NAMES: continue
        bad += 1
        print(f"✗ {label}: “{text}” [{bit}] → {m['message']} ({m['rule']['id']})")
    if PUBLIC: time.sleep(3.2)
print(f"{bad} issue(s) in {n} texts." if bad else f"✓ English check passed ({n} texts).")
sys.exit(1 if bad else 0)

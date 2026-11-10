"""English quality check with LanguageTool (public API, British English).

Checks every English sentence that will appear on screen. Prints a report and
exits 1 if any issue is found, so a bad sentence never reaches Instagram.
Set LT_URL to a self-hosted LanguageTool server to avoid public rate limits.
"""
import json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LT = os.environ.get("LT_URL", "https://api.languagetool.org/v2/check")
IGNORE = {"WHITESPACE_RULE", "EN_QUOTES", "DASH_RULE", "UPPERCASE_SENTENCE_START", "MORFOLOGIK_RULE_EN_GB"}

def texts():
    cards = json.loads((ROOT / "reels/data/cards.json").read_text(encoding="utf-8"))
    for m in cards["mistakes"]: yield f"mistake:{m['id']}", m["correct"]
    for q in cards["quizzes"]: yield f"quiz:{q['id']}", q["prompt"].replace("___", q["answer"])
    for w in cards["words"]: yield f"word:{w['id']}", w["example"]

def check(text):
    data = urllib.parse.urlencode({"text": text, "language": "en-GB"}).encode()
    with urllib.request.urlopen(urllib.request.Request(LT, data=data), timeout=30) as r:
        return [m for m in json.load(r)["matches"] if m["rule"]["id"] not in IGNORE]

bad = 0
for label, text in texts():
    issues = check(text); time.sleep(3.2)  # public API: ~20 requests/min
    for m in issues:
        bad += 1
        print(f"✗ {label}: “{text}” → {m['message']} ({m['rule']['id']})")
print(f"{bad} issue(s)." if bad else "✓ English check passed.")
sys.exit(1 if bad else 0)

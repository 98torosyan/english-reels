"""Check every IPA transcription on screen against Britfone (British English, ISC licence).

Stress marks are ignored (Britfone places them before the vowel, we place them before the syllable).
Exits 1 if a transcription differs from the dictionary, unless the word is listed in ALLOW
(checked by hand). Words missing from the dictionary are reported, not failed."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = set(json.loads((ROOT / "qc/data/ipa_allow.json").read_text(encoding="utf-8"))) if (ROOT / "qc/data/ipa_allow.json").exists() else set()

def norm(s):
    s = s.replace("ɐ", "ʌ").replace("ɹ", "r").replace("ɛə", "eə").replace("ɛː", "eə").replace("ɛ", "e").replace("g", "ɡ").replace("ʤ", "dʒ").replace("ʧ", "tʃ")
    s = re.sub(r"[ˈˌ/\s.()]", "", s)
    s = re.sub(r"ə([lnm])$", r"\1", s)
    return s

DICT = {}
for line in (ROOT / "qc/data/britfone.csv").read_text(encoding="utf-8").splitlines():
    head, _, pron = line.partition(",")
    word = re.sub(r"\(\d\)$", "", head.strip()).lower()
    DICT.setdefault(word, set()).add(norm(pron))

def items():
    w10 = json.loads((ROOT / "reels/data/words10.json").read_text(encoding="utf-8"))
    for l in w10["lists"]:
        for w in l["words"]: yield f"words10:{l['id']}", w["en"], w["ipa"]
    for st in json.loads((ROOT / "carousels/data/picture_stories.json").read_text(encoding="utf-8"))["stories"]:
        for w in st.get("words", []): yield f"picstory:{st['id']}", w["en"], w["ipa"]
    snd = json.loads((ROOT / "reels/data/sounds.json").read_text(encoding="utf-8"))
    for s in snd["sounds"]:
        for k in ("a", "b"): yield f"sound:{s['id']}", s[k]["word"], s[k]["ipa"]

bad = missing = 0
for label, word, ipa in items():
    parts, ipas = word.lower().split(), ipa.strip("/").split()
    if word.lower() in ALLOW: continue
    if len(parts) == len(ipas):
        pairs = list(zip(parts, ipas))
    else:
        pairs = [(" ".join(parts), "".join(ipas))]
    for p, i in pairs:
        cands = DICT.get(p)
        if cands is None and " " in p:
            continue
        if cands is None:
            missing += 1; print(f"?  {label}: {p} — not in dictionary"); continue
        if norm(i) not in cands:
            bad += 1; print(f"✗  {label}: {word} {ipa} → dictionary: {' | '.join(sorted(cands))}")
print(f"{bad} mismatch(es), {missing} not found." if bad or missing else "✓ IPA check passed.")
sys.exit(1 if bad else 0)

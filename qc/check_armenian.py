"""Armenian spelling check (report only): every Armenian line that goes on screen or into a caption is checked
with Hunspell and the Eastern Armenian dictionary (wooorm/dictionaries, GPL/LGPL/MPL).
Words in qc/data/armenian_allow.txt (names, page words) are accepted.
Needs: the `hunspell` command and the dictionary at $HY_DICT (path without .aff/.dic)."""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DICT = os.environ.get("HY_DICT", "/tmp/hy/index")
ALLOW = {w.strip() for w in (ROOT / "qc/data/armenian_allow.txt").read_text(encoding="utf-8").split() if w.strip()} \
    if (ROOT / "qc/data/armenian_allow.txt").exists() else set()
ARM = re.compile(r"[Ա-և՛-՟]+")
load = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))


def walk(x, where):
    if isinstance(x, str):
        if ARM.search(x): yield where, x
    elif isinstance(x, dict):
        for k, v in x.items(): yield from walk(v, f"{where}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from walk(v, f"{where}[{i}]")


def texts():
    for p in ["reels/data/feelstory.json", "carousels/data/opposites.json", "reels/data/storyvideo.json", "reels/data/routine.json",
              "carousels/data/picture_stories.json", "carousels/data/classic_carousels.json", "reels/data/words10.json",
              "reels/data/phrasal.json", "reels/data/reading.json", "reels/data/dialogues.json", "reels/data/cards.json"]:
        if (ROOT / p).exists(): yield from walk(load(p), p)
    for it in load("queue.json")["items"]:   # captions of everything still to be published
        if it.get("review_status") == "staged" and not it.get("published_at"):
            yield f"caption:{it['id']}", it.get("caption", "")


def main():
    pairs = list(texts())
    words = {}
    for where, t in pairs:
        for w in ARM.findall(t):
            w = re.sub(r"[՛-՟]", "", w)   # stress, emphasis and question marks sit inside the word
            if len(w) > 1 and w not in ALLOW and w.lower() not in ALLOW: words.setdefault(w, where)
    out = subprocess.run(["hunspell", "-d", DICT, "-l"], input="\n".join(words), capture_output=True, text=True).stdout.split()
    bad = sorted(set(out))
    for w in bad:
        sug = subprocess.run(["hunspell", "-d", DICT, "-a"], input=w, capture_output=True, text=True).stdout.splitlines()
        hint = next((l.split(":", 1)[1].strip() for l in sug if l.startswith("&")), "")
        print(f"? {w}  ({words[w]})" + (f"  → {hint[:80]}" if hint else ""))
    print(f"{len(bad)} unknown word(s) in {len(words)} distinct Armenian words from {len(pairs)} texts.")
    if "--strict" in sys.argv and bad: sys.exit(1)


if __name__ == "__main__":
    main()

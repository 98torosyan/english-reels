"""Level check for the A1–A2 stories (wordfreq, Apache-2.0): flags uncommon words that are not taught as "new words",
and long sentences. Report only — never fails the build; it helps keep every text at the learners' level."""
import json, re
from pathlib import Path
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parents[1]
RARE, LONG = 3.5, 16   # zipf below 3.5 ≈ outside the most common ~20 000 English words; sentences above 16 words


def check(name, level, text, taught=()):
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]
    words = re.findall(r"[^\W\d_](?:(?:[^\W\d_]|['’])*[^\W\d_])?", text)
    rare = sorted({w.lower() for w in words if not w[0].isupper() and w.lower() not in taught and zipf_frequency(w.lower(), "en") < RARE})
    long = [s for s in sents if len(s.split()) > LONG]
    flag = "  " if not rare and not long else "⚠ "
    print(f"{flag}{name:16} {level:3} {len(words) / max(1, len(sents)):4.1f} words/sentence"
          + (f" · uncommon: {', '.join(rare)}" if rare else "") + (f" · {len(long)} long sentence(s)" if long else ""))


def main():
    for s in json.loads((ROOT / "reels/data/reading.json").read_text(encoding="utf-8"))["stories"]:
        check(s["id"], s["level"], s["en"])
    for s in json.loads((ROOT / "carousels/data/picture_stories.json").read_text(encoding="utf-8"))["stories"]:
        check(s["id"], s["level"], " ".join(s["scenes"]), {w["en"] for w in s["words"]})
    for s in json.loads((ROOT / "reels/data/storyvideo.json").read_text(encoding="utf-8"))["stories"]:
        check(s["id"], s.get("level", "A2"), " ".join(s["scenes"]))


if __name__ == "__main__":
    main()

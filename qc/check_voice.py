"""Listen to every generated voice clip with faster-whisper (MIT) and compare what is heard with the text it should say.

Report only: it never blocks or delays publishing. Results are cached by audio hash in qc/data/voice_heard.json,
so only new clips are transcribed. Writes voice_report.md and exits 0 when nothing is clear, 3 when something sounds wrong."""
import difflib, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "qc/data/voice_heard.json"
SERIES = ["words10", "phrasal", "reading", "storyvideo", "dialogues", "stories", "cards"]   # "sounds" are single phonemes: skipped
ALIAS = {"annie": "ani", "anny": "ani", "mum's": "mum's", "mom": "mum", "colour": "color", "neighbour": "neighbor", "favourite": "favorite", "centre": "center", "tyre": "tire", "jewellery": "jewelry", "practise": "practice", "okay": "ok"}
NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}


def words(s):
    s = s.lower().replace("’", "'").replace("-", " ")
    return [ALIAS.get(w, NUM.get(w, w)) for w in re.findall(r"[a-z0-9']+", s)]


def score(expected, heard):
    a, b = [ALIAS.get(w, w) for w in words(expected)], words(heard)
    if not a:
        return 1.0
    if len(a) <= 3:   # single words and short phrases: every word must be heard
        return 1.0 if all(w in b for w in a) else difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() * 0.9
    return difflib.SequenceMatcher(None, a, b).ratio()


def pcm(path):
    """16 kHz mono float audio via ffmpeg (avoids PyAV version issues)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main():
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    flagged = []
    for series in SERIES:
        for mp3 in sorted((ROOT / "assets" / series).rglob("*.mp3")):
            meta = mp3.with_suffix(".json")
            if not meta.exists():
                continue
            text = json.loads(meta.read_text(encoding="utf-8")).get("text", "")
            if not text or not re.search(r"[A-Za-z]", text):
                continue
            key = hashlib.sha1(mp3.read_bytes()).hexdigest()
            if key not in cache:
                segs, _ = model.transcribe(pcm(mp3), language="en", beam_size=5, condition_on_previous_text=False, vad_filter=False)
                cache[key] = " ".join(s.text.strip() for s in segs)
            heard = cache[key]
            sc = score(text, heard)
            limit = 0.999 if len(words(text)) <= 3 else 0.82
            if sc < limit:
                flagged.append((str(mp3.relative_to(ROOT)), text, heard, sc))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    if not flagged:
        print("All voice clips say what they should."); return 0
    rows = "\n".join(f"| `{p}` | {t} | {h} | {s:.2f} |" for p, t, h, s in flagged)
    (ROOT / "voice_report.md").write_text(
        "Այս ձայնային ֆայլերում լսվածը չի համընկնում տեքստի հետ։ Լսե՛ք և, եթե իսկապես սխալ է, ձայնը վերագրանցե՛ք։\n"
        "Հրապարակումները չեն կանգնում, սա միայն զգուշացում է։\n\n| ֆայլ | պետք է ասի | լսվեց | համընկնում |\n|---|---|---|---|\n" + rows + "\n", encoding="utf-8")
    print(rows); return 3


if __name__ == "__main__":
    sys.exit(main())

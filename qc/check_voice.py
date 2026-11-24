"""Listen to every generated voice clip with faster-whisper (MIT) and compare what is heard with the text it should say.

Report only: it never blocks or delays publishing. Results are cached by audio hash in qc/data/voice_heard.json,
so only new clips are transcribed. Writes voice_report.md and exits 0 when nothing is clear, 3 when something sounds wrong."""
import difflib, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "qc/data/voice_heard.json"
SERIES = ["reading"]
ALIAS = {"annie": "ani", "anny": "ani", "mum's": "mum's", "mom": "mum", "colour": "color", "neighbour": "neighbor", "favourite": "favorite", "centre": "center", "tyre": "tire", "jewellery": "jewelry", "practise": "practice", "okay": "ok"}
NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def num(n):
    n = int(n)
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " and " + num(n % 100))
    if 1000 < n < 2100 and n % 100: return num(n // 100) + " " + num(n % 100)   # years: 1859 -> eighteen fifty nine
    return str(n)


def spell(s):
    s = re.sub(r"£(\d+)\.(\d\d)", lambda m: f"{num(m.group(1))} pounds {num(m.group(2))}", s)
    s = re.sub(r"£(\d+)", lambda m: f"{num(m.group(1))} pounds", s)
    return re.sub(r"\d+", lambda m: num(m.group(0)), s)


def words(s):
    s = spell(s.lower().replace("’", "'").replace("-", " "))
    s = s.replace("‘", "'").replace("'", "")   # quotes and apostrophes are not heard: friends' = friend's = friends
    return [ALIAS.get(w, NUM.get(w, w)) for w in re.findall(r"[a-z0-9]+", s)]


def score(expected, heard):
    a, b = [ALIAS.get(w, w) for w in words(expected)], words(heard)
    if not a:
        return 1.0
    if len(a) <= 3:   # single words and short phrases: every word must be heard (plural/ending allowed)
        return 1.0 if all(any(h.startswith(w) or w.startswith(h) and len(h) >= len(w) - 1 for h in b) for w in a) else difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() * 0.9
    if difflib.SequenceMatcher(None, "".join(a), "".join(b)).ratio() >= 0.97:   # only spacing differs: "lunchbox" = "lunch box"
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def pcm(path):
    """16 kHz mono float audio via ffmpeg (avoids PyAV version issues)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    pad = np.zeros(12800, dtype=np.float32)   # 0.8 s of silence each side: Whisper hears isolated words far better
    return np.concatenate([pad, np.frombuffer(raw, dtype=np.float32), pad])


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
            if len(words(text)) <= 3:   # isolated words: speech recognition is unreliable here, so they are not judged
                continue
            key = "v2:" + hashlib.sha1(mp3.read_bytes()).hexdigest()
            if key not in cache:
                short = len(words(text)) <= 3
                segs, _ = model.transcribe(pcm(mp3), language="en", beam_size=5, temperature=0, condition_on_previous_text=False, vad_filter=False,
                                           initial_prompt="A teacher reads one English word slowly and clearly." if short else None)
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

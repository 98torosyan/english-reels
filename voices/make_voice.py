"""Create narration + word timings for lessons that have no audio yet (runs in GitHub Actions).

For every assets/lessons/<id>.lesson.json without <id>.mp3 it writes:
  <id>.mp3   British neural narration (voice from the lesson's "voice" field)
  <id>.json  {start, end, starts, tag, words:[[s,e],…], env, hop} — same format as the site.
Words are matched to the whitespace-separated tokens of the lesson text, so karaoke highlighting works.
"""
import asyncio, json, re, subprocess, sys
from pathlib import Path
import edge_tts

LESSONS = Path(__file__).resolve().parents[1] / "assets" / "lessons"
CLEAN = re.compile(r"[^\w']+", re.UNICODE)

def norm(s): return CLEAN.sub("", s.replace("’", "'")).lower()

async def synth(text, voice, rate, mp3):
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    bounds = []
    with open(mp3, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio": f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                bounds.append((chunk["text"], chunk["offset"] / 1e7, (chunk["offset"] + chunk["duration"]) / 1e7))
    return bounds

def align(tokens, bounds):
    out, j = [], 0
    for tok in tokens:
        target, got, s, e = norm(tok), "", None, None
        while j < len(bounds) and len(got) < len(target):
            w, bs, be = bounds[j]; got += norm(w); s = bs if s is None else s; e = be; j += 1
        if got != target or s is None:
            raise SystemExit(f"alignment failed at token {tok!r} (got {got!r})")
        out.append([round(s, 2), round(e, 2)])
    return out

def envelope(mp3, hop=0.05):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    import array
    a = array.array("h", pcm); n = int(8000 * hop); vals = []
    for i in range(0, len(a), n):
        seg = a[i:i + n]; vals.append((sum(x * x for x in seg) / max(1, len(seg))) ** .5)
    m = max(vals) or 1
    return [round(100 * v / m) for v in vals]

def main():
    made = 0
    for lp in sorted(LESSONS.glob("*.lesson.json")):
        lid = lp.name[:-len(".lesson.json")]
        mp3, tj = LESSONS / f"{lid}.mp3", LESSONS / f"{lid}.json"
        if mp3.exists() and tj.exists(): continue
        lesson = json.loads(lp.read_text(encoding="utf-8"))
        voice = lesson.get("voice", "en-GB-SoniaNeural"); rate = lesson.get("rate", "-10%")
        text = " ".join(lesson["text"])
        bounds = asyncio.run(synth(text, voice, rate, mp3))
        tokens = text.split()
        words = align(tokens, bounds)
        # sentence starts: first token of each sentence
        starts, new = [], True
        for tok, (s, _) in zip(tokens, words):
            if new: starts.append(s)
            new = bool(re.search(r"[.!?][”\"']?$", tok))
        tj.write_text(json.dumps({"start": words[0][0], "end": words[-1][1], "starts": starts, "tag": f"words-1|{voice}",
            "words": words, "env": envelope(mp3), "hop": 0.05}, ensure_ascii=False), encoding="utf-8")
        print(f"voiced {lid}: {len(tokens)} words, {words[-1][1]:.1f}s, {voice}"); made += 1
    # short card sentences (mistake corrections)
    root = LESSONS.parents[1]
    cards = json.loads((root / "reels/data/cards.json").read_text(encoding="utf-8"))
    out = root / "assets" / "cards"; out.mkdir(exist_ok=True)
    for i, m in enumerate(cards["mistakes"]):
        f = (m.get("audio") or {}).get("file")
        if not f: continue
        mp3, tj = root / "assets" / f"{f}.mp3", root / "assets" / f"{f}.json"
        if mp3.exists() and tj.exists(): continue
        voice = ["en-GB-SoniaNeural", "en-GB-RyanNeural", "en-GB-LibbyNeural", "en-GB-ThomasNeural"][i % 4]
        bounds = asyncio.run(synth(m["correct"], voice, "-12%", mp3))
        words = align(m["correct"].split(), bounds)
        tj.write_text(json.dumps({"text": m["correct"], "words": words, "tag": voice}), encoding="utf-8"); made += 1
    print(f"{made} file(s) voiced.")

if __name__ == "__main__":
    main()

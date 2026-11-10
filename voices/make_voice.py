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
KEEP = {"zoo", "saturday-market", "my-garden"}  # original site lessons
GAP = 0.9  # seconds of silence after each sentence

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
            raise ValueError(f"alignment failed at token {tok!r} (got {got!r})")
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
        if mp3.exists() and tj.exists() and (lid in KEEP or json.loads(tj.read_text()).get("pace") == "v2"): continue
        try:
            made += voice_lesson(lp, lid, mp3, tj)
        except Exception as error:  # keep going: one bad lesson must not block the others
            print(f"SKIPPED {lid}: {error}")
            for f in (mp3, tj): f.unlink(missing_ok=True)
    made += voice_cards()
    made += voice_sounds()
    print(f"{made} file(s) voiced.")


def voice_lesson(lp, lid, mp3, tj):
    if True:
        lesson = json.loads(lp.read_text(encoding="utf-8"))
        voice = lesson.get("voice", "en-GB-SoniaNeural"); rate = lesson.get("rate", "-18%")
        text = " ".join(lesson["text"])
        # one sentence at a time + a calm pause after each, so learners can read along
        sents = [x for x in re.split(r'(?<=[.!?])\s+|(?<=[.!?][”"])\s+', text) if x]
        pieces, words, t0 = [], [], 0.0
        for k, sent in enumerate(sents):
            part = mp3.with_suffix(f".{k}.mp3")
            b_ = asyncio.run(synth(sent, voice, rate, part))
            w_ = align(sent.split(), b_)
            words += [[round(a + t0, 2), round(e + t0, 2)] for a, e in w_]
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(part)], capture_output=True, text=True).stdout)
            pieces.append(part); t0 += dur + GAP
        lst = mp3.with_suffix(".txt")
        sil = mp3.with_suffix(".sil.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), "-c:a", "libmp3lame", "-b:a", "48k", str(sil)], check=True)
        lst.write_text("".join(f"file '{p.name}'\nfile '{sil.name}'\n" for p in pieces))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k", str(mp3)], check=True, cwd=str(mp3.parent))
        for p_ in pieces + [lst, sil]: p_.unlink()
        tokens = text.split()
        assert len(words) == len(tokens)
        # sentence starts: first token of each sentence
        starts, new = [], True
        for tok, (s, _) in zip(tokens, words):
            if new: starts.append(s)
            new = bool(re.search(r"[.!?][”\"']?$", tok))
        tj.write_text(json.dumps({"start": words[0][0], "end": words[-1][1], "starts": starts, "tag": f"words-1|{voice}",
            "words": words, "env": envelope(mp3), "hop": 0.05, "pace": "v2"}, ensure_ascii=False), encoding="utf-8")
        print(f"voiced {lid}: {len(tokens)} words, {words[-1][1]:.1f}s, {voice}")
        return 1


def voice_cards():
    made = 0
    # short card sentences (mistake corrections)
    root = LESSONS.parents[1]
    cards = json.loads((root / "reels/data/cards.json").read_text(encoding="utf-8"))
    out = root / "assets" / "cards"; out.mkdir(exist_ok=True)
    for i, m in enumerate(cards["mistakes"]):
        f = (m.get("audio") or {}).get("file")
        if not f: continue
        mp3, tj = root / "assets" / f"{f}.mp3", root / "assets" / f"{f}.json"
        if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("pace") == "v2": continue
        voice = ["en-GB-SoniaNeural", "en-GB-RyanNeural", "en-GB-LibbyNeural", "en-GB-ThomasNeural"][i % 4]
        try:
            bounds = asyncio.run(synth(m["correct"], voice, "-18%", mp3))
            words = align(m["correct"].split(), bounds)
        except Exception as error:
            print(f"SKIPPED card {m['id']}: {error}"); mp3.unlink(missing_ok=True); continue
        tj.write_text(json.dumps({"text": m["correct"], "words": words, "tag": voice, "pace": "v2"}), encoding="utf-8"); made += 1
    return made

def voice_sounds():
    """Sound it out: each word on its own (slow, clear) + the practice sentence with word timings."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/sounds.json").read_text(encoding="utf-8"))
    for item in data["sounds"]:
        out = root / "assets" / "sounds" / item["id"]; out.mkdir(parents=True, exist_ok=True)
        jobs = [("a", item["a"]["word"] + ".", "-15%"), ("b", item["b"]["word"] + ".", "-15%"), ("s", item["sentence"], "-18%")]
        for key, text, rate in jobs:
            mp3, tj = out / f"{key}.mp3", out / f"{key}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text: continue
            try:
                bounds = asyncio.run(synth(text, item["voice"], rate, mp3))
                words = align(text.split(), bounds)
            except Exception as error:
                print(f"SKIPPED sound {item['id']}/{key}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": text, "words": words, "tag": item["voice"]}), encoding="utf-8"); made += 1
    return made

if __name__ == "__main__":
    main()

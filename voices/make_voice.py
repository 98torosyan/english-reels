"""Create narration + word timings for lessons that have no audio yet (runs in GitHub Actions).

For every assets/lessons/<id>.lesson.json without <id>.mp3 it writes:
  <id>.mp3   British neural narration (voice from the lesson's "voice" field)
  <id>.json  {start, end, starts, tag, words:[[s,e],…], env, hop} — same format as the site.
Words are matched to the whitespace-separated tokens of the lesson text, so karaoke highlighting works.
"""
import asyncio, json, re, subprocess
from pathlib import Path
import edge_tts

LESSONS = Path(__file__).resolve().parents[1] / "assets" / "lessons"
CLEAN = re.compile(r"[^\w']+", re.UNICODE)
KEEP = {"zoo", "saturday-market", "my-garden"}  # original site lessons
GAP = 0.9  # seconds of silence after each sentence

def norm(s): return CLEAN.sub("", s.replace("’", "'")).lower().strip("'")

_KOKORO = None

def synth_kokoro(text, voice, rate, mp3):
    """British Kokoro voice (Apache 2.0), e.g. voice="kokoro:bf_emma". Returns word bounds like edge-tts."""
    global _KOKORO
    import numpy as np, soundfile as sf
    if _KOKORO is None:
        from kokoro import KPipeline
        _KOKORO = KPipeline(lang_code="b")
    speed = 1 + int(rate.rstrip("%")) / 100 if rate else 1.0
    audio, bounds, t0 = [], [], 0.0
    for res in _KOKORO(text, voice=voice.split(":", 1)[1], speed=speed):
        a = res.audio.numpy() if hasattr(res.audio, "numpy") else np.asarray(res.audio)
        for tok in res.tokens or []:
            if tok.start_ts is not None and tok.end_ts is not None and norm(tok.text):
                bounds.append((tok.text, t0 + tok.start_ts, t0 + tok.end_ts))
        audio.append(a); t0 += len(a) / 24000
    wav = str(mp3) + ".wav"
    sf.write(wav, np.concatenate(audio), 24000)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", "adelay=100|100", "-b:a", "160k", str(mp3)], check=True)
    Path(wav).unlink()
    # Kokoro's last token often runs into the trailing silence: clamp every end to where speech really stops
    det = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp3), "-af", "silencedetect=n=-40dB:d=0.08", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", det) if float(x) > 0.3]
    speech_end = starts[-1] + 0.05 if starts else None
    out = [(w, s + 0.1, e + 0.1) for w, s, e in bounds]
    if speech_end:
        out = [(w, min(s, speech_end - 0.05), min(e, speech_end)) for w, s, e in out]
    return out

async def synth(text, voice, rate, mp3):
    if voice.startswith("kokoro:"):
        return synth_kokoro(text, voice, rate, mp3)
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    bounds = []
    with open(mp3, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio": f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                bounds.append((chunk["text"], chunk["offset"] / 1e7, (chunk["offset"] + chunk["duration"]) / 1e7))
    return bounds

def align(tokens, bounds):
    """Word timings for each token. Works at character level, so a boundary that covers several
    tokens (e.g. "fifteen green street" read as one chunk) is split in proportion to their length."""
    chars = []  # (start, end) for every normalised character, in order
    for w, bs, be in bounds:
        n = norm(w)
        for k in range(len(n)):
            chars.append((bs + (be - bs) * k / len(n), bs + (be - bs) * (k + 1) / len(n)))
    total = "".join(norm(w) for w, _, _ in bounds)
    out, pos = [], 0
    for tok in tokens:
        target = norm(tok)
        if not target:
            out.append(out[-1] if out else [0.0, 0.0]); continue
        if total[pos:pos + len(target)] != target:
            raise ValueError(f"alignment failed at token {tok!r} (got {total[pos:pos + len(target) + 10]!r})")
        s0, e0 = chars[pos][0], chars[pos + len(target) - 1][1]
        out.append([round(s0, 2), round(e0, 2)]); pos += len(target)
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
    made += voice_dialogues()
    made += voice_stories()
    made += voice_words10()
    made += voice_phrasal()
    made += voice_reading()
    made += voice_storyvideo()
    made += voice_routine()
    made += voice_feelstory()
    made += voice_opposites()
    made += voice_countries()
    made += voice_talk()
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

def voice_dialogues():
    """Everyday English: every dialogue line on its own, in the speaker's voice."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/dialogues.json").read_text(encoding="utf-8"))
    for d in data["dialogues"]:
        out = root / "assets" / "dialogues" / d["id"]; out.mkdir(parents=True, exist_ok=True)
        for n, line in enumerate(d["lines"]):
            voice = d["speakers"][line["s"]]["voice"]
            mp3, tj = out / f"{n}.mp3", out / f"{n}.json"
            if mp3.exists() and tj.exists():
                old = json.loads(tj.read_text())
                if old.get("text") == line["en"] and old.get("tag") == voice: continue
            try:
                bounds = asyncio.run(synth(line["en"], voice, "-15%", mp3))
                words = align(line["en"].split(), bounds)
            except Exception as error:
                print(f"SKIPPED dialogue {d['id']}/{n}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": line["en"], "words": words, "tag": voice}), encoding="utf-8"); made += 1
    return made

def story_texts(st):
    clean = lambda x: re.sub(r"<[^>]+>", "", x).replace("“", "").replace("”", "").replace("’", "'").replace(" — ", " ").strip()
    return clean(st["title"]), clean(st["en"])


def voice_stories():
    """Word / phrase of the day stories: the word, then the example, read calmly."""
    made = 0
    root = LESSONS.parents[1]
    stories = json.loads((root / "stories/stories.json").read_text(encoding="utf-8"))
    for n, st in enumerate(s for s in stories if re.match(r"[wp]-", s["id"])):
        out = root / "assets" / "stories" / st["id"]; out.mkdir(parents=True, exist_ok=True)
        voice = ["en-GB-SoniaNeural", "en-GB-RyanNeural"][n % 2]
        for key, text in zip(("t", "e"), story_texts(st)):
            mp3, tj = out / f"{key}.mp3", out / f"{key}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text: continue
            try:
                bounds = asyncio.run(synth(text, voice, "-12%", mp3))
            except Exception as error:
                print(f"SKIPPED story {st['id']}/{key}: {error}"); mp3.unlink(missing_ok=True); continue
            start, end = (bounds[0][1], bounds[-1][2]) if bounds else (0.0, 0.0)
            tj.write_text(json.dumps({"text": text, "start": start, "end": end, "tag": voice}), encoding="utf-8"); made += 1
    return made

def voice_words10():
    """10 words: each English word on its own, slow and clear."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/words10.json").read_text(encoding="utf-8"))
    for lst in data["lists"]:
        out = root / "assets" / "words10" / lst["id"]; out.mkdir(parents=True, exist_ok=True)
        for n, w in enumerate(lst["words"]):
            text = w["en"] + "."
            mp3, tj = out / f"{n}.mp3", out / f"{n}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text and json.loads(tj.read_text()).get("tag") == lst["voice"]: continue
            try:
                bounds = asyncio.run(synth(text, lst["voice"], "-15%", mp3))
                words = align(text.split(), bounds)
            except Exception as error:
                print(f"SKIPPED words10 {lst['id']}/{n}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": text, "words": words, "tag": lst["voice"]}), encoding="utf-8"); made += 1
    return made

def voice_phrasal():
    """Phrasal verbs: the phrasal verb on its own, then the example with word timings."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/phrasal.json").read_text(encoding="utf-8"))
    for st in data["sets"]:
        out = root / "assets" / "phrasal" / st["id"]; out.mkdir(parents=True, exist_ok=True)
        for n, it in enumerate(st["items"]):
            for key, text, rate in ((f"{n}p", it["en"] + ".", "-18%"), (f"{n}e", it["example"], "-12%")):
                mp3, tj = out / f"{key}.mp3", out / f"{key}.json"
                if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text and json.loads(tj.read_text()).get("tag") == st["voice"]: continue
                try:
                    bounds = asyncio.run(synth(text, st["voice"], rate, mp3))
                    words = align(text.split(), bounds)
                except Exception as error:
                    print(f"SKIPPED phrasal {st['id']}/{key}: {error}"); mp3.unlink(missing_ok=True); continue
                tj.write_text(json.dumps({"text": text, "words": words, "tag": st["voice"]}), encoding="utf-8"); made += 1
    return made

def voice_reading():
    """Daily reading: sentence by sentence at a learner's pace, with a pause after each sentence,
    joined into one track with word timings for the highlight."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/reading.json").read_text(encoding="utf-8"))
    PAUSE = 0.65
    for st in data["stories"]:
        out = root / "assets" / "reading" / st["id"]; out.mkdir(parents=True, exist_ok=True)
        mp3, tj = out / "p.mp3", out / "p.json"
        pace = "v2-slow"
        if mp3.exists() and tj.exists():
            old = json.loads(tj.read_text())
            if old.get("text") == st["en"] and old.get("tag") == st["voice"] and old.get("pace") == pace: continue
        sents = re.split(r"(?<=[.!?'])\s+(?=[A-Z'])", st["en"])
        try:
            parts, words, t = [], [], 0.0
            for k, sent in enumerate(sents):
                part = out / f"s{k}.mp3"
                b = asyncio.run(synth(sent, st["voice"], "-18%", part))
                w = align(sent.split(), b)
                end = w[-1][1] + 0.15
                words += [[round(a + t, 2), round(c + t, 2)] for a, c in w]
                parts.append((part, end)); t += end + PAUSE
            inputs, chains = [], []
            for k, (part, end) in enumerate(parts):
                inputs += ["-i", str(part)]
                chains.append(f"[{k}:a]aresample=24000,atrim=0:{end:.3f},apad=pad_dur={PAUSE},asetpts=PTS-STARTPTS[a{k}]")
            subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains) + ";" + "".join(f"[a{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[o]",
                            "-map", "[o]", "-b:a", "160k", str(mp3)], check=True)
            for part, _ in parts: part.unlink()
            if len(words) != len(st["en"].split()): raise ValueError("word count mismatch")
        except Exception as error:
            print(f"SKIPPED reading {st['id']}: {error}"); mp3.unlink(missing_ok=True); continue
        tj.write_text(json.dumps({"text": st["en"], "words": words, "tag": st["voice"], "pace": pace}), encoding="utf-8"); made += 1
    return made

def voice_storyvideo():
    """Story video: each scene voiced separately (calm pace); one track with scene starts and word timings."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/storyvideo.json").read_text(encoding="utf-8"))
    PAUSE = 0.8
    for st in data["stories"]:
        out = root / "assets" / "storyvideo" / st["id"]; out.mkdir(parents=True, exist_ok=True)
        mp3, tj = out / "p.mp3", out / "p.json"
        text = " ".join(st["scenes"])
        if mp3.exists() and tj.exists():
            old = json.loads(tj.read_text())
            if old.get("text") == text and old.get("tag") == st["voice"]: continue
        try:
            parts, words, scenes, t = [], [], [], 0.0
            for k, sc in enumerate(st["scenes"]):
                part = out / f"s{k}.mp3"
                b = asyncio.run(synth(sc, st["voice"], "-15%", part))
                w = align(sc.split(), b)
                end = w[-1][1] + 0.15
                scenes.append(round(t, 2)); words += [[round(a + t, 2), round(c + t, 2)] for a, c in w]
                parts.append((part, end)); t += end + PAUSE
            inputs, chains = [], []
            for k, (part, end) in enumerate(parts):
                inputs += ["-i", str(part)]
                chains.append(f"[{k}:a]aresample=24000,atrim=0:{end:.3f},apad=pad_dur={PAUSE},asetpts=PTS-STARTPTS[a{k}]")
            subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains) + ";" + "".join(f"[a{k}]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[o]",
                            "-map", "[o]", "-b:a", "160k", str(mp3)], check=True)
            for part, _ in parts: part.unlink()
        except Exception as error:
            print(f"SKIPPED storyvideo {st['id']}: {error}"); mp3.unlink(missing_ok=True); continue
        tj.write_text(json.dumps({"text": text, "words": words, "scenes": scenes, "tag": st["voice"]}), encoding="utf-8"); made += 1
    return made

def voice_routine():
    """My day: the opening question and each sentence as its own clip (brackets removed), with word timings."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/routine.json").read_text(encoding="utf-8"))
    for st in data["stories"]:
        out = root / "assets" / "routine" / st["id"]; out.mkdir(parents=True, exist_ok=True)
        per = st.get("voices") or []   # optional: a different speaker for each picture
        for key, raw, voice in [("q", st["question"], st["voice"])] + [(str(n), l, per[n] if n < len(per) else st["voice"]) for n, l in enumerate(st["lines"])]:
            text = raw.replace("[", "").replace("]", "")
            mp3, tj = out / f"v{key}.mp3", out / f"v{key}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text and json.loads(tj.read_text()).get("tag") == voice: continue
            try:
                bounds = asyncio.run(synth(text, voice, "-12%", mp3))
                words = align(text.split(), bounds)
            except Exception as error:
                print(f"SKIPPED routine {st['id']}/{key}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": text, "words": words, "tag": voice}), encoding="utf-8"); made += 1
    return made

def voice_feelstory():
    """Emotional stories: every line its own clip, read slowly and softly."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/feelstory.json").read_text(encoding="utf-8"))
    for st in data["stories"]:
        out = root / "assets" / "feelstory" / st["id"]; out.mkdir(parents=True, exist_ok=True)
        lines = [l for sc in st["scenes"] for l in sc]
        for n, raw in enumerate(lines):
            text = raw.replace("[", "").replace("]", "")
            mp3, tj = out / f"v{n}.mp3", out / f"v{n}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text and json.loads(tj.read_text()).get("tag") == st["voice"]: continue
            try:
                bounds = asyncio.run(synth(text, st["voice"], "-16%", mp3))
                words = align(text.split(), bounds)
            except Exception as error:
                print(f"SKIPPED feelstory {st['id']}/{n}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": text, "words": words, "tag": st["voice"]}), encoding="utf-8"); made += 1
    return made

def voice_talk():
    """Emma & Sam dialogues: every line its own clip, in the speaker's own voice, at a natural, slightly slow pace."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "reels/data/talk.json").read_text(encoding="utf-8"))
    for t in data["talks"]:
        out = root / "assets" / "talk" / t["id"]; out.mkdir(parents=True, exist_ok=True)
        lines = [l for sc in t["scenes"] for l in sc["lines"]]
        for n, (who, raw) in enumerate(lines):
            text = raw.replace("[", "").replace("]", ""); voice = data["people"][who]["voice"]
            mp3, tj = out / f"v{n}.mp3", out / f"v{n}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text and json.loads(tj.read_text()).get("tag") == voice: continue
            try:
                bounds = asyncio.run(synth(text, voice, "-8%", mp3))
                words = align(text.split(), bounds)
            except Exception as error:
                print(f"SKIPPED talk {t['id']}/{n}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": text, "words": words, "tag": voice}), encoding="utf-8"); made += 1
    return made

def voice_opposites():
    """A Day in Opposites: each word of a pair and the example sentence, one clip each."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "carousels/data/opposites.json").read_text(encoding="utf-8"))
    for day in data["days"]:
        voice = day.get("voice", "en-GB-SoniaNeural")
        out = root / "assets" / "opposites" / day["id"]; out.mkdir(parents=True, exist_ok=True)
        jobs = [("title", f"{day['title']} {day['title_em']}.", "-8%")]
        for i, p in enumerate(day["pairs"]):
            jobs += [(f"p{i}l", p["left"]["en"], "-12%"), (f"p{i}r", p["right"]["en"], "-12%"),
                     (f"p{i}s", p["sentence"].replace("[", "").replace("]", ""), "-6%")]
        for name, text, rate in jobs:
            mp3, tj = out / f"{name}.mp3", out / f"{name}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text and json.loads(tj.read_text()).get("tag") == voice: continue
            try:
                bounds = asyncio.run(synth(text, voice, rate, mp3))
                words = align(text.split(), bounds)
            except Exception as error:
                print(f"SKIPPED opposites {day['id']}/{name}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": text, "words": words, "tag": voice}), encoding="utf-8"); made += 1
    return made

def voice_countries():
    """Countries in watercolour: the country's name and every slide's sentence, one clip each."""
    made = 0
    root = LESSONS.parents[1]
    data = json.loads((root / "carousels/data/countries.json").read_text(encoding="utf-8"))
    for c in data["countries"]:
        voice = c.get("voice", "en-GB-SoniaNeural")
        out = root / "assets" / "countries" / c["id"]; out.mkdir(parents=True, exist_ok=True)
        jobs = [("title", c["name"] + ".", "-8%")] + [(f"s{i}", sl["en"].replace("[", "").replace("]", ""), "-8%") for i, sl in enumerate(c["slides"])]
        for name, text, rate in jobs:
            mp3, tj = out / f"{name}.mp3", out / f"{name}.json"
            if mp3.exists() and tj.exists() and json.loads(tj.read_text()).get("text") == text and json.loads(tj.read_text()).get("tag") == voice: continue
            try:
                bounds = asyncio.run(synth(text, voice, rate, mp3))
                words = align(text.split(), bounds)
            except Exception as error:
                print(f"SKIPPED countries {c['id']}/{name}: {error}"); mp3.unlink(missing_ok=True); continue
            tj.write_text(json.dumps({"text": text, "words": words, "tag": voice}), encoding="utf-8"); made += 1
    return made

if __name__ == "__main__":
    main()

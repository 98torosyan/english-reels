"""Create narration + word timings for lessons that have no audio yet (runs in GitHub Actions).

For every assets/lessons/<id>.lesson.json without <id>.mp3 it writes:
  <id>.mp3   British neural narration (voice from the lesson's "voice" field)
  <id>.json  {start, end, starts, tag, words:[[s,e],…], env, hop} — same format as the site.
Words are matched to the whitespace-separated tokens of the lesson text, so karaoke highlighting works.
"""
import asyncio, json, re, subprocess
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
LESSONS = Path(__file__).resolve().parents[1] / "assets" / "lessons"
CLEAN = re.compile(r"[^\w']+", re.UNICODE)
GAP = 0.9  # seconds of silence after each sentence

def norm(s): return CLEAN.sub("", s.replace("’", "'")).lower().strip("'")

_CHATTER = None


_EAR = None


def best_take(text, make, sr, tries=4):
    """The storyteller voice is expressive and sometimes says a word wrongly ("laughs" -> "loves"): every take is
    listened to (faster-whisper) and the clearest one is kept; a perfect take ends the search."""
    global _EAR
    import re, numpy as np
    try:
        from faster_whisper import WhisperModel
        if _EAR is None: _EAR = WhisperModel("small.en", device="cpu", compute_type="int8")
    except Exception:
        return make()
    norm = lambda x: re.findall(r"[a-z0-9]+", x.lower().replace("'", ""))
    want = norm(text); best = (-1, None)
    for k in range(tries):
        w = make()
        a = np.interp(np.arange(0, len(w), sr / 16000), np.arange(len(w)), w).astype(np.float32)
        heard = " ".join(seg.text for seg in _EAR.transcribe(a, language="en", beam_size=5, vad_filter=False)[0])
        got = norm(heard)
        import difflib
        sc = difflib.SequenceMatcher(None, want, got).ratio()
        if sc > best[0]: best = (sc, w)
        if sc >= 0.999: break
        print(f"    take {k + 1}: {sc:.2f} heard «{heard.strip()}»", flush=True)
    return best[1]


def synth_chatterbox(text, voice, rate, mp3):
    """Chatterbox storyteller voice (Resemble AI, MIT), voice="chatterbox:builtin". It gives no word timings, so the
    spoken span is found from the sound itself and the words are spread over it (the reels use the span)."""
    global _CHATTER
    import subprocess, tempfile, numpy as np, soundfile as sf, torch
    if _CHATTER is None:
        from chatterbox.tts import ChatterboxTTS
        torch.set_num_threads(4); _CHATTER = ChatterboxTTS.from_pretrained(device="cpu")
    kw = dict(exaggeration=0.55, cfg_weight=0.45)
    name = voice.split(":", 1)[1]
    if name != "builtin":   # "chatterbox:sonia" = the storyteller's delivery in the clear voice of en-GB-SoniaNeural
        ref = ROOT / "assets" / "voice-ref" / f"{name}.mp3"
        if not ref.exists():
            ref.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["edge-tts", "--voice", {"sonia": "en-GB-SoniaNeural"}[name],
                            "--rate=-6%", "--text", "Good morning. Today I will read you a short and happy story about a little girl and her family.",
                            "--write-media", str(ref)], check=True)
        kw = dict(audio_prompt_path=str(ref), exaggeration=0.5, cfg_weight=0.5)
    sr = _CHATTER.sr; w = best_take(text, lambda: _CHATTER.generate(text, **kw).squeeze().cpu().numpy(), sr)
    env = np.convolve(np.abs(w), np.ones(int(sr * .02)) / int(sr * .02), "same"); on = np.where(env > env.max() * 0.04)[0]
    a, b = max(0, on[0] - int(sr * .05)), min(len(w), on[-1] + int(sr * .12)); w = w[a:b]
    pad = int(sr * .05); w = np.concatenate([np.zeros(pad), w, np.zeros(pad)])
    try: tempo = max(0.88, min(1.0, 1 + float(str(rate).rstrip("%")) / 200))   # "-18%" (a learner's pace) -> 0.91
    except ValueError: tempo = 1.0
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        sf.write(tmp.name, w, sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp.name, "-af", f"atempo={tempo}", "-ar", "24000", "-c:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True)
    s0, s1 = pad / sr / tempo, (len(w) - pad) / sr / tempo; words = text.split(); total = sum(len(x) for x in words)
    bounds, t = [], s0
    for x in words:
        d = (s1 - s0) * len(x) / total; bounds.append((x, t, t + d)); t += d
    return bounds


VOICES = {"chatterbox:sonia", "en-GB-SoniaNeural", "en-GB-LibbyNeural", "en-GB-RyanNeural"}   # the only voices the page uses


async def synth(text, voice, rate, mp3):
    if voice not in VOICES: raise ValueError(f"voice {voice} is not one of the page's voices: {sorted(VOICES)}")
    if voice.startswith("chatterbox:"):
        return synth_chatterbox(text, voice, rate, mp3)
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
    made = voice_reading()
    print(f"{made} file(s) voiced.")


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


if __name__ == "__main__":
    main()

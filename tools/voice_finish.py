"""Finish voice clips in CI after voices/make_voice.py:
1. polish: a gentle studio chain (Spotify Pedalboard, GPL-3) - soft compression, warmth, a touch of room, safe peak;
2. align: exact word times from the sound itself (ctc-forced-aligner, wav2vec2/MMS forced alignment), so every
   word on screen lights up exactly when it is heard.
Each clip's JSON records what was done ("fx", "aligned"), so a clip is never processed twice.
Usage: python tools/voice_finish.py [--budget MINUTES]"""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = ["reading"]
FX, ALIGN = "pb1", "ctc1"


def clips():
    for d in DIRS:
        for js in sorted((ROOT / "assets" / d).rglob("*.json")):
            mp3 = js.with_suffix(".mp3")
            if not mp3.exists(): continue
            try: meta = json.loads(js.read_text(encoding="utf-8"))
            except Exception: continue
            if isinstance(meta, dict) and meta.get("text") and isinstance(meta.get("words"), list):
                yield js, mp3, meta


def polish(mp3):
    from pedalboard import Pedalboard, HighpassFilter, LowShelfFilter, PeakFilter, Compressor, Reverb, Limiter
    from pedalboard.io import AudioFile
    with AudioFile(str(mp3)) as f:
        audio, sr = f.read(f.frames), f.samplerate
    board = Pedalboard([HighpassFilter(70), LowShelfFilter(cutoff_frequency_hz=180, gain_db=1.2), PeakFilter(3000, 1.5, 0.9),
                        Compressor(threshold_db=-20, ratio=2.2, attack_ms=8, release_ms=160),
                        Reverb(room_size=0.12, damping=0.6, wet_level=0.045, dry_level=1.0, width=0.6), Limiter(threshold_db=-1.5)])
    out = board(audio, sr)
    tmp = mp3.with_suffix(".tmp.mp3")
    with AudioFile(str(tmp), "w", sr, out.shape[0], quality="V0") as f:
        f.write(out)
    tmp.replace(mp3)


class Aligner:
    def __init__(self):
        import torch
        from ctc_forced_aligner import load_alignment_model
        torch.set_num_threads(4)
        self.model, self.tok = load_alignment_model("cpu", dtype=torch.float32)

    def words(self, mp3, text):
        from ctc_forced_aligner import load_audio, generate_emissions, preprocess_text, get_alignments, get_spans, postprocess_results
        wav = load_audio(str(mp3), self.model.dtype, self.model.device)
        emissions, stride = generate_emissions(self.model, wav, batch_size=4)
        tokens, starred = preprocess_text(text, romanize=True, language="eng")
        segments, scores, blank = get_alignments(emissions, tokens, self.tok)
        spans = get_spans(tokens, segments, blank)
        return [(float(w["start"]), float(w["end"])) for w in postprocess_results(starred, spans, stride, scores)]


def clamp_to_speech(mp3, words):
    """Forced alignment lets the last word run into the silence after it: end every word where the speech really ends."""
    import re, subprocess
    det = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp3), "-af", "silencedetect=n=-35dB:d=0.12", "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", det) if float(x) > 0.3]
    if not starts: return words
    end = starts[-1] + 0.04
    out = [[min(a, end - 0.05), min(b, end)] for a, b in words]
    return [[round(a, 3), round(max(b, a + 0.03), 3)] for a, b in out]


def main():
    budget = float(sys.argv[sys.argv.index("--budget") + 1]) * 60 if "--budget" in sys.argv else 1e9
    t0 = time.monotonic(); polished = aligned = kept = 0; aligner = None
    for js, mp3, meta in clips():
        if time.monotonic() - t0 > budget: print("out of time; the rest next run"); break
        changed = False
        if meta.get("fx") != FX:
            try: polish(mp3); meta["fx"] = FX; polished += 1; changed = True
            except Exception as error: print(f"polish skipped {js.relative_to(ROOT)}: {error}")
        n = len(meta["text"].split())
        if meta.get("aligned") != ALIGN and n == len(meta["words"]):
            try:
                aligner = aligner or Aligner()
                new = aligner.words(mp3, meta["text"])
                old = [tuple(w[:2]) for w in meta["words"]]
                ok = len(new) == n and all(a < b for a, b in new) and all(new[i][0] >= new[i - 1][0] for i in range(1, n))
                drift = sum(abs(a[0] - b[0]) for a, b in zip(new, old)) / n if ok else 99
                if ok and drift < 0.5:   # sanity: never replace good times with a bad alignment
                    meta["words"] = [[round(a, 3), round(b, 3)] for a, b in new]; aligned += 1
                else:
                    kept += 1
                meta["aligned"] = ALIGN; changed = True
            except Exception as error:
                print(f"align skipped {js.relative_to(ROOT)}: {error}")
        if meta.get("clamped") != 1 and meta.get("aligned") == ALIGN:
            meta["words"] = clamp_to_speech(mp3, meta["words"]); meta["clamped"] = 1; changed = True
        if changed: js.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"polished {polished}, aligned {aligned}, kept original times {kept}")


if __name__ == "__main__":
    main()

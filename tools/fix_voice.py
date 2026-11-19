"""Re-make voice clips that the listening check flagged: each clip is read again at a few paces, every take is
listened to (faster-whisper), and the take that says its text most clearly is kept. The clip loses its "fx"/"aligned"
marks, so tools/voice_finish.py polishes and aligns it again. Clips that are already clear are left alone.
Usage: python tools/fix_voice.py assets/feelstory/city-london/v3.mp3 ...   (or --report voice_report.md)"""
import asyncio, json, re, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "qc")); sys.path.insert(0, str(ROOT / "voices")); sys.path.insert(0, str(ROOT / "tools"))
from check_voice import pcm   # noqa: E402
from make_voice import synth, align   # noqa: E402
from story_listen import fair_score, PASS   # noqa: E402

PACES = ["-16%", "-10%", "-22%", "-4%"]


def main():
    args = sys.argv[1:]
    if args[:1] == ["--report"]:
        args = re.findall(r"`(assets/[^`]+\.mp3)`", (ROOT / args[1]).read_text(encoding="utf-8"))
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    hear = lambda p: " ".join(s.text for s in model.transcribe(pcm(p), language="en", beam_size=5, vad_filter=False)[0]).strip()
    fixed = 0
    for rel in args:
        mp3 = ROOT / rel; tj = mp3.with_suffix(".json"); meta = json.loads(tj.read_text(encoding="utf-8"))
        text, voice = meta["text"], meta["tag"]
        best = (fair_score(text, hear(mp3)), None, None); print(f"{rel}: now {best[0]:.2f}")
        if best[0] >= PASS: continue
        tmp = Path(tempfile.mkdtemp())
        for k, pace in enumerate(PACES):
            out = tmp / f"t{k}.mp3"
            try: bounds = asyncio.run(synth(text, voice, pace, out))
            except Exception as error: print("  take failed:", error); continue
            sc = fair_score(text, hear(out)); print(f"  {pace}: {sc:.2f}")
            if sc > best[0]: best = (sc, out, bounds)
            if sc >= 0.95: break
        if best[1]:
            shutil.copy2(best[1], mp3)
            tj.write_text(json.dumps({"text": text, "words": align(text.split(), best[2]), "tag": voice}), encoding="utf-8"); fixed += 1
            print(f"  kept {best[0]:.2f}")
    print(f"fixed {fixed} of {len(args)}")


if __name__ == "__main__":
    main()

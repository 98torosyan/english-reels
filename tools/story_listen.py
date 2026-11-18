"""Listen to a story's narration with faster-whisper (MIT) and make sure every clip says exactly its sentence.
A clip that sounds wrong is made again once (slightly different pace); if it is still wrong the run fails, so a
mumbled or cut sentence never reaches a reel. Usage: python tools/story_listen.py <id>"""
import asyncio, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "qc")); sys.path.insert(0, str(ROOT / "voices"))
from check_voice import score, pcm   # noqa: E402

PASS = 0.86


def main():
    sid = sys.argv[1]
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    data = json.loads((ROOT / "reels/data/talk.json").read_text(encoding="utf-8"))
    t = next(x for x in data["talks"] if x["id"] == sid)
    out = ROOT / "assets" / "talk" / sid; failed = []
    lines = [l for sc in t["scenes"] for l in sc["lines"]]

    def heard(n):
        segs, _ = model.transcribe(pcm(out / f"v{n}.mp3"), language="en", beam_size=5, vad_filter=False)
        return " ".join(s.text for s in segs).strip()

    for n, (who, raw) in enumerate(lines):
        text = raw.replace("[", "").replace("]", ""); h = heard(n); sc = score(text, h)
        if sc < PASS:
            print(f"redo {n}: wanted «{text}», heard «{h}» ({sc:.2f})")
            from make_voice import synth, align
            voice = data["people"][who]["voice"]
            words = align(text.split(), asyncio.run(synth(text, voice, "-6%", out / f"v{n}.mp3")))
            (out / f"v{n}.json").write_text(json.dumps({"text": text, "words": words, "tag": voice}), encoding="utf-8")
            h = heard(n); sc = score(text, h)
        print(f"{'ok ' if sc >= PASS else 'BAD'} {n} {sc:.2f} {text}")
        if sc < PASS: failed.append(n)
    if failed: raise SystemExit(f"narration clips still wrong: {failed}")


if __name__ == "__main__":
    main()

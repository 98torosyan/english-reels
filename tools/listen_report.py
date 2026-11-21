"""Listen to finished voice tracks and report how clearly each says its text (faster-whisper), without changing them.
Usage: python tools/listen_report.py assets/reading/gata/p.mp3 ...   -> exit 1 when one is below the bar"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "qc")); sys.path.insert(0, str(ROOT / "tools"))
from check_voice import pcm   # noqa: E402
from story_listen import fair_score, PASS   # noqa: E402


def main():
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8"); bad = []
    for rel in sys.argv[1:]:
        mp3 = ROOT / rel; text = json.loads(mp3.with_suffix(".json").read_text(encoding="utf-8"))["text"]
        heard = " ".join(s.text for s in model.transcribe(pcm(mp3), language="en", beam_size=5, vad_filter=False)[0]).strip()
        sc = fair_score(text, heard); print(f"{'ok ' if sc >= PASS else 'BAD'} {sc:.2f} {rel}")
        if sc < PASS: print("   wanted:", text, "\n   heard: ", heard); bad.append(rel)
    if bad: raise SystemExit(f"unclear: {bad}")


if __name__ == "__main__":
    main()

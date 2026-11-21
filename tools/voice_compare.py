"""Read the same short passage with several high-quality British voices so the owner can choose by ear.
Writes trial/compare-<n>-<name>.mp3 (raw voice, no effects). Usage: python tools/voice_compare.py <reading id>"""
import asyncio, json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "voices"))
from make_voice import synth   # noqa: E402

VOICES = [("storyteller", "chatterbox:builtin"), ("sonia", "en-GB-SoniaNeural"), ("libby", "en-GB-LibbyNeural"),
          ("ryan", "en-GB-RyanNeural"), ("emma", "kokoro:bf_emma"), ("sonia-storyteller", "chatterbox:sonia")]


def main():
    st = next(s for s in json.loads((ROOT / "reels/data/reading.json").read_text(encoding="utf-8"))["stories"] if s["id"] == sys.argv[1])
    import re
    text = " ".join(re.split(r"(?<=[.!?'])\s+(?=[A-Z'])", st["en"])[:3])
    out = ROOT / "trial"; out.mkdir(exist_ok=True)
    ref = Path(tempfile.mkdtemp()) / "sonia.mp3"
    asyncio.run(synth("Good morning. Today I will read you a short and happy story about a little girl and her family.", "en-GB-SoniaNeural", "-6%", ref))
    for k, (name, voice) in enumerate(VOICES, 1):
        mp3 = out / f"compare-{k}-{name}.mp3"
        try:
            if voice == "chatterbox:sonia":
                import make_voice as mv, soundfile as sf, numpy as np
                if mv._CHATTER is None: asyncio.run(synth("Hello.", "chatterbox:builtin", "-10%", out / "warm.mp3"))
                w = mv._CHATTER.generate(text, audio_prompt_path=str(ref), exaggeration=0.5, cfg_weight=0.5).squeeze().cpu().numpy()
                wav = out / "tmp.wav"; sf.write(wav, w, mv._CHATTER.sr)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", "atempo=0.93", "-c:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True); wav.unlink()
            else:
                asyncio.run(synth(text, voice, "-10%", mp3))
            print("ok", k, name)
        except Exception as error:
            print("failed", name, error)
    (out / "warm.mp3").unlink(missing_ok=True)


if __name__ == "__main__":
    main()

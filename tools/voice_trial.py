"""Trial: read a story with Chatterbox (Resemble AI, MIT) — an expressive storyteller voice — to compare with the
current narration. Writes trial/<id>-<variant>.wav, one sentence after another with natural pauses.
Usage: python tools/voice_trial.py <story id>"""
import json, sys
from pathlib import Path
import numpy as np, soundfile as sf, torch

ROOT = Path(__file__).resolve().parents[1]
torch.set_num_threads(4)


def lines(sid):
    t = next(x for x in json.loads((ROOT / "reels/data/talk.json").read_text(encoding="utf-8"))["talks"] if x["id"] == sid)
    return [l.replace("[", "").replace("]", "") for sc in t["scenes"] for _, l in sc["lines"]]


def read(model, texts, sr, **kw):
    out = []
    for k, s in enumerate(texts):
        w = model.generate(s, **kw).squeeze().cpu().numpy()
        out += [w, np.zeros(int(sr * (0.9 if k == 0 else 0.45)))]
        print("ok", k, s, flush=True)
    return np.concatenate(out)


def main():
    sid = sys.argv[1]; texts = lines(sid); out = ROOT / "trial"; out.mkdir(exist_ok=True)
    ref = ROOT / "assets" / "talk" / sid / "v1.mp3"   # the current narrator's own sentence, so the voice stays the same person
    from chatterbox.tts import ChatterboxTTS
    m = ChatterboxTTS.from_pretrained(device="cpu")
    sf.write(out / f"{sid}-warm.wav", read(m, texts, m.sr, audio_prompt_path=str(ref), exaggeration=0.6, cfg_weight=0.4), m.sr)
    sf.write(out / f"{sid}-builtin.wav", read(m, texts, m.sr, exaggeration=0.55, cfg_weight=0.45), m.sr)


if __name__ == "__main__":
    main()

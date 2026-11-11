"""Voice comparison: the same short dialogue in the British Kokoro voices (Apache 2.0)."""
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

OUT = Path(__file__).resolve().parents[1] / "assets" / "voice-test"; OUT.mkdir(parents=True, exist_ok=True)
TEXT = "Excuse me, is this seat free? Yes, of course. Please, sit down. Passport, ticket, luggage."
pipe = KPipeline(lang_code="b")  # British English
for v in ["bf_emma", "bf_isabella", "bm_george", "bm_fable", "bm_lewis", "bf_alice"]:
    audio = np.concatenate([a for _, _, a in pipe(TEXT, voice=v, speed=0.9)])
    sf.write(OUT / f"kokoro-{v}.wav", audio, 24000); print("ok", v)

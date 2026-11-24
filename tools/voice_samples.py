"""Same short reading in every British voice the system can make, at the reading pace, for the owner to compare."""
import asyncio, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "voices"))
import make_voice as mv

ROOT = Path(__file__).resolve().parents[1]
TEXT = ("It is a cold, snowy day. Mila and Leo play in the park. They throw snowballs and laugh. "
        "Then Leo looks at his hands. 'Oh no, my red mitten is lost!' Then Toffee runs to them. 'Good girl, Toffee!' says Leo.")
VOICES = sys.argv[1:] if __name__ == "__main__" else []
out = ROOT / "samples"; out.mkdir(exist_ok=True)
for v in VOICES if __name__ == "__main__" else []:
    name = v.replace(":", "-"); parts = []
    try:
        for k, sent in enumerate(re.split(r"(?<=[.!?'])\s+(?=[A-Z'])", TEXT)):
            p = out / f"{name}-{k}.mp3"; asyncio.run(mv.synth(sent, v, "-18%", p)); parts.append(p)
        ins = sum((["-i", str(p)] for p in parts), [])
        chain = "".join(f"[{k}:a]aresample=24000,apad=pad_dur=0.6[a{k}];" for k in range(len(parts)))
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", chain + "".join(f"[a{k}]" for k in range(len(parts))) +
                        f"concat=n={len(parts)}:v=0:a=1,loudnorm=I=-16:TP=-1.5[o]", "-map", "[o]", "-b:a", "192k", str(out / f"{name}.mp3")], check=True)
        print("ok", v, flush=True)
    except Exception as e:
        print("SKIPPED", v, e, flush=True)
    for p in parts: p.unlink(missing_ok=True)

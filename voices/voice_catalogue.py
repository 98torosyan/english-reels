"""Voice catalogue: one teacher sentence in every British voice we can use for free.
edge-tts (all en-GB voices), Piper (MIT, rhasspy/piper-voices en_GB) and Kokoro (Apache-2.0, British)."""
import asyncio, json, subprocess, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "assets" / "voice-test" / "catalogue"; OUT.mkdir(parents=True, exist_ok=True)
TEXT = "Hello, everyone! Today we will learn ten new words. Listen and repeat: passport, ticket, luggage. Well done!"
done = []


async def edge():
    import edge_tts
    for v in await edge_tts.list_voices():
        if not v["ShortName"].startswith("en-GB-"): continue
        name = v["ShortName"].split("-")[2].replace("Neural", "")
        try:
            await edge_tts.Communicate(TEXT, v["ShortName"], rate="-8%").save(str(OUT / f"edge-{name}.mp3"))
            done.append({"file": f"edge-{name}.mp3", "engine": "Microsoft", "name": name, "gender": v.get("Gender", "")})
        except Exception as e:
            print("skip", name, e)


def piper():
    base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB"
    for name, q in [("cori", "high"), ("jenny_dioco", "medium"), ("alba", "medium"), ("alan", "medium"), ("northern_english_male", "medium"), ("southern_english_female", "low")]:
        try:
            for ext in ("onnx", "onnx.json"):
                urllib.request.urlretrieve(f"{base}/{name}/{q}/en_GB-{name}-{q}.{ext}", f"/tmp/p.{ext}")
            wav = OUT / f"piper-{name}.wav"
            subprocess.run(["piper", "--model", "/tmp/p.onnx", "--length_scale", "1.08", "--output_file", str(wav)], input=TEXT.encode(), check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "128k", str(wav.with_suffix(".mp3"))], check=True); wav.unlink()
            done.append({"file": f"piper-{name}.mp3", "engine": "Piper", "name": name.replace("_", " ").title(), "gender": ""})
        except Exception as e:
            print("skip piper", name, e)


def kokoro():
    import numpy as np, soundfile as sf
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="b")
    for v in ["bf_emma", "bf_isabella", "bf_alice", "bf_lily", "bm_george", "bm_fable", "bm_lewis", "bm_daniel"]:
        try:
            audio = np.concatenate([a for _, _, a in pipe(TEXT, voice=v, speed=0.92)])
            wav = OUT / f"kokoro-{v}.wav"; sf.write(wav, audio, 24000)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "128k", str(wav.with_suffix(".mp3"))], check=True); wav.unlink()
            done.append({"file": f"kokoro-{v}.mp3", "engine": "Kokoro", "name": v.split("_")[1].title(), "gender": "Female" if v[1] == "f" else "Male"})
        except Exception as e:
            print("skip kokoro", v, e)


asyncio.run(edge()); piper(); kokoro()
(OUT / "index.json").write_text(json.dumps(done, indent=1)); print(len(done), "voices")

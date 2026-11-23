"""Voices for the "Say it right" reels (runs in GitHub Actions).

For every line of reels/data/sayit.json writes assets/sayit/<id>/<voice>/<k>.mp3 and <k>.json
({text, words: [[start, end], ...]}) for each candidate voice, so the owner can pick one by ear.
"""
import asyncio, json, subprocess, sys
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
VOICES = {"hy": [("anahit", "hy-AM-AnahitNeural"), ("hayk", "hy-AM-HaykNeural")],
          "en": [("ryan", "en-GB-RyanNeural"), ("sonia", "en-GB-SoniaNeural")]}
RATE = {"hy": "-6%", "en": "-12%"}


async def speak(text, voice, rate, mp3):
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for c in com.stream():
            if c["type"] == "audio":
                f.write(c["data"])
            elif c["type"] == "WordBoundary":
                s = c["offset"] / 1e7
                words.append([round(s, 3), round(s + c["duration"] / 1e7, 3), c["text"]])
    return words


async def main(only):
    data = json.loads((ROOT / "reels/data/sayit.json").read_text(encoding="utf-8"))
    for item in data["items"]:
        if only and item["id"] not in only:
            continue
        for line in item["lines"]:
            for name, voice in VOICES[line["lang"]]:
                out = ROOT / "assets/sayit" / item["id"] / name
                out.mkdir(parents=True, exist_ok=True)
                mp3 = out / f"{line['k']}.mp3"
                try:
                    words = await speak(line["text"], voice, RATE[line["lang"]], mp3)
                except Exception as e:  # voice not offered: try the next one
                    print("skip", voice, type(e).__name__, flush=True); mp3.unlink(missing_ok=True); continue
                if not words:  # no boundaries: take the sound itself
                    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                                             capture_output=True, text=True).stdout)
                    words = [[0.05, round(d - 0.05, 3), line["text"]]]
                (out / f"{line['k']}.json").write_text(json.dumps({"text": line["text"], "voice": voice, "words": words}, ensure_ascii=False), encoding="utf-8")
                print(item["id"], name, line["k"], len(words), "words", flush=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

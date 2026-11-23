"""Narration for one story (or dialogue) from reels/data/talk.json: one clip per sentence, in the speaker's voice,
with word timings. Only what is missing or changed is made. Usage: python tools/story_voice.py <id>"""
import asyncio, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "voices"))
from make_voice import synth, align   # noqa: E402


def main():
    sid = sys.argv[1]
    data = json.loads((ROOT / "reels/data/talk.json").read_text(encoding="utf-8"))
    t = next(x for x in data["talks"] if x["id"] == sid)
    out = ROOT / "assets" / "talk" / sid; out.mkdir(parents=True, exist_ok=True)
    rate = "-10%" if t.get("kind") == "story" else "-8%"
    lines = [l for sc in t["scenes"] for l in sc["lines"]]
    for n, (who, raw) in enumerate(lines):
        text = raw.replace("[", "").replace("]", ""); voice = data["people"][who]["voice"]
        speed = data["people"][who].get("rate", rate)   # a speaker may read slower (the narrator: calm and clear)
        own = t.get("voices", {}).get(who)   # a story may give a speaker another voice: {"Narrator": {"voice": ..., "rate": ...}}
        if own: voice, speed = own["voice"], own.get("rate", rate)
        mp3, tj = out / f"v{n}.mp3", out / f"v{n}.json"
        if mp3.exists() and tj.exists():
            j = json.loads(tj.read_text())
            if j.get("text") == text and j.get("tag") == voice and j.get("rate", rate) == speed: continue
        for attempt in range(3):   # the speech service sometimes drops a request
            try:
                words = align(text.split(), asyncio.run(synth(text, voice, speed, mp3))); break
            except Exception as error:
                if attempt == 2: raise SystemExit(f"voice {n} failed: {error}")
        tj.write_text(json.dumps({"text": text, "words": words, "tag": voice, "rate": speed}), encoding="utf-8")
        print(f"voiced {n}: {text}")


if __name__ == "__main__":
    main()

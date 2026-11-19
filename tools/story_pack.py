"""Story packs: one moving painted story = a short JSON (title, six scenes of English sentences, mood) + six clips.

  check   python tools/story_pack.py check inbox/<id>/story.json   -> prints problems, exit 1 if any
  add     python tools/story_pack.py add inbox/<id>                 -> validates, writes the story into reels/data/talk.json,
                                                                       moves the clips to assets/motion/<id>/in1..6.mp4
The JSON may be pasted together with other text: anything around the {...} block is ignored.
Format: {"id": "the-last-leaf", "title": "The Last Leaf", "level": "A2", "mood": "sad",
         "scenes": [["sentence", "sentence"], ... six scenes, 1-3 sentences each],
         "question": "optional question for the comments", "hashtags": ["optional", "five"]}"""
import json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TALK = ROOT / "reels" / "data" / "talk.json"
# mood -> (music track, page colour behind the picture)
MOODS = {
    "sad": ("new/evening-strings.m4a", "#1C1511"),
    "warm": ("new/piano-glow.m4a", "#F3EADB"),
    "winter": ("new/snow-celesta.m4a", "#16203A"),
    "magic": ("new/harp-dream.m4a", "#1A1630"),
    "romantic": ("new/book-waltz.m4a", "#F2E6E0"),
    "adventure": ("new/warm-guitar.m4a", "#1E1A14"),
    "funny": ("new/kalimba-steps.m4a", "#F4EEDC"),
}
LEVELS = {"A1", "A2", "B1", "B2", "C1"}


def parse(text):
    """The first balanced {...} block in the text, as JSON (tolerates code fences and curly quotes)."""
    text = text.replace("’", "'").replace("‘", "'")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start: raise ValueError("no { … } block found")
    block = text[start:end + 1]
    try:
        st = json.loads(block)
    except json.JSONDecodeError:   # curly quotes used as JSON quotes
        st = json.loads(block.replace("“", '"').replace("”", '"'))
    # curly quotes inside sentences become plain ones, so the voice and the screen agree
    if isinstance(st.get("scenes"), list):
        q = lambda l: l.replace("“", '"').replace("”", '"') if isinstance(l, str) else l
        st["scenes"] = [[q(l) for l in sc] if isinstance(sc, list) else sc for sc in st["scenes"]]
    return st


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "story"


def problems(st):
    out = []
    if not isinstance(st.get("title"), str) or not st["title"].strip(): out.append("title is missing")
    if st.get("level", "A2") not in LEVELS: out.append(f"level must be one of {sorted(LEVELS)}")
    if st.get("mood", "warm") not in MOODS: out.append(f"mood must be one of {sorted(MOODS)}")
    q = st.get("question")
    if q is not None and (not isinstance(q, str) or len(q) > 120): out.append("question must be one short sentence")
    sc = st.get("scenes")
    if not isinstance(sc, list) or not 4 <= len(sc) <= 6: out.append("there must be 4 to 6 scenes"); return out
    for k, lines in enumerate(sc, 1):
        if not isinstance(lines, list) or not 1 <= len(lines) <= 3: out.append(f"scene {k}: 1 to 3 sentences"); continue
        for l in lines:
            if not isinstance(l, str) or not l.strip(): out.append(f"scene {k}: empty sentence"); continue
            if len(l) > 110: out.append(f"scene {k}: sentence too long for the screen ({len(l)} letters, max 110): {l[:40]}…")
            if re.search(r"[^\x20-\x7EÀ-ÿ—–]", l): out.append(f"scene {k}: only plain English letters please: {l[:40]}")
            if not re.search(r"[.!?\"']$", l.strip()): out.append(f"scene {k}: sentence must end with . ! or ?: {l[:40]}")
    return out


def entry(st):
    music, paper = MOODS[st.get("mood", "warm")]
    title = st["title"].strip()
    scenes = [list(x) for x in st["scenes"]]
    scenes[0] = [title.rstrip(".") + "."] + scenes[0]   # the narrator says the title first
    return {"id": st["id"], "kind": "story", "title": title, "level": st.get("level", "A2"), "music": music, "paper": paper,
            "scenes": [{"at": {}, "lines": [["Narrator", l.strip()] for l in lines]} for lines in scenes], "recap": [],
            "question": (st.get("question") or "").strip(), "hashtags": [h.lstrip("#") for h in st.get("hashtags", []) if isinstance(h, str)][:5]}


def add(folder):
    folder = Path(folder); st = parse((folder / "story.json").read_text(encoding="utf-8"))
    st["id"] = slug(st.get("id") or st.get("title", ""))
    bad = problems(st)
    clips = sorted(folder.glob("clip*.mp4"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    if len(clips) != len(st.get("scenes") or []): bad.append(f"need one clip per scene, found {len(clips)}")
    if bad: raise SystemExit("\n".join(bad))
    data = json.loads(TALK.read_text(encoding="utf-8"))
    data.setdefault("people", {}).setdefault("Narrator", {"voice": "en-GB-SoniaNeural", "colour": "#7A4A2A"})
    data["talks"] = [t for t in data["talks"] if t["id"] != st["id"]] + [entry(st)]
    TALK.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dest = ROOT / "assets" / "motion" / st["id"]; dest.mkdir(parents=True, exist_ok=True)
    for k, c in enumerate(clips, 1): shutil.copy2(c, dest / f"in{k}.mp4")
    shutil.rmtree(folder)
    print(st["id"])


def main():
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "check":
        bad = problems(parse(Path(arg).read_text(encoding="utf-8")))
        print("\n".join(bad) or "ok"); sys.exit(1 if bad else 0)
    if cmd == "add": add(arg)


if __name__ == "__main__":
    main()

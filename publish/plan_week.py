"""Week plan 11–17 Nov 2026: daily 12:00 carousel, 17:00 Everyday English dialogue, 20:00 main reel, 2 stories.
Adds new items as "approved" (stage_media renders them) and moves a few staged items so each day is balanced."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
LISTS = {s["id"]: s for s in json.loads((ROOT / "carousels/data/lists.json").read_text(encoding="utf-8"))}
DIALOGUES = {d["id"]: d for d in json.loads((ROOT / "reels/data/dialogues.json").read_text(encoding="utf-8"))["dialogues"]}
SOUNDS = {s["id"]: s for s in json.loads((ROOT / "reels/data/sounds.json").read_text(encoding="utf-8"))["sounds"]}
LINK = "Ամբողջական դասերը ձայնով՝ bio-ի հղումով։"
TAG = "#EnglishReadingRoom #Անգլերեն #անգլերենիդասեր {} #Yerevan"


def list_caption(cid):
    s = LISTS[cid]
    title = s["title"].replace("<em>", "").replace("</em>", "")
    head = "Անգլերեն բառակապակցություններ · English collocations" if s["series"] == "COLLOCATIONS" else "Խոսակցական անգլերեն · Spoken English phrases"
    first = s["items"][0]
    rows = "\n".join(f"{i['en']} — {i['hy'].rstrip('։')}" for i in s["items"])
    tag = "#EnglishVocabulary" if s["series"] == "COLLOCATIONS" else "#SpokenEnglish"
    return (f"{head}\n\n{title}\n\n{s['subtitle_hy'].rstrip('։')}։\n\n{rows}\n\n"
            f"Օրինակ՝ “{first['example']}” — «{first['example_hy'].rstrip('։')}»։\n\n"
            f"Պահպանի՛ր և ուղարկի՛ր ընկերոջդ։\n\n{LINK}\n\n{TAG.format(tag)}")


def dialogue_caption(cid):
    d = DIALOGUES[cid]
    lines = "\n".join(f"{l['s']}: {l['en']}" for l in d["lines"])
    return (f"Խոսակցական անգլերեն · Everyday English dialogue\n\n{' '.join(d['title'])} · {d['title_hy']} · {d['level']}\n\n{lines}\n\n"
            f"Նախ լսի՛ր, հետո դու ես B-ն. ասա՛ քո տողերը բարձրաձայն։\n\n"
            f"Պահպանի՛ր և կրկնի՛ր, մինչև ազատ ասես։\n\n{LINK}\n\n{TAG.format('#SpokenEnglish')}")


def sound_caption(cid):
    s = SOUNDS[cid]
    a, b = s["a"], s["b"]
    return (f"Անգլերենի արտասանություն · English pronunciation\n\n"
            f"{a['word'].capitalize()} or {b['word']}? Can you hear the difference?\n\n"
            f"{a['word']} {a['ipa']} — {a['hy']}. {a['tip_hy']}\n{b['word']} {b['ipa']} — {b['hy']}. {b['tip_hy']}\n\n"
            f"Լսի՛ր, ընտրի՛ր A կամ B, ապա բարձրաձայն կրկնի՛ր.\n{s['sentence']}\n\n"
            f"Գրի՛ր մեկնաբանություններում՝ A, թե B։\n\n{LINK}\n\n{TAG.format('#EnglishPronunciation')}")


def item(date, time, kind, cid, title):
    reel = kind in {"dialogue", "sound"}
    cap = {"dialogue": dialogue_caption, "sound": sound_caption}.get(kind, list_caption)(cid)
    return {"id": f"{date}-{kind if kind != 'rule' else 'list'}-{cid}", "date": date, "time": time, "timezone": "Asia/Yerevan",
            "type": "REEL" if reel else "CAROUSEL", "format": "REELS" if reel else "CAROUSEL", "kind": kind, "content_id": cid,
            "title": title, "caption": cap, "review_status": "approved",
            **({"thumb_offset": 7000 if kind == "sound" else 6000} if reel else {})}


NEW = [
    item("2026-11-10", "23:00", "dialogue", "cafe", "Everyday English 01"),
    item("2026-11-11", "12:00", "rule", "get", "Collocations: get"),
    item("2026-11-11", "17:00", "dialogue", "directions", "Everyday English 02"),
    item("2026-11-12", "12:00", "rule", "pay", "Collocations: pay"),
    item("2026-11-12", "17:00", "dialogue", "meeting", "Everyday English 03"),
    item("2026-11-13", "17:00", "dialogue", "clothes-shop", "Everyday English 04"),
    item("2026-11-14", "17:00", "dialogue", "doctor", "Everyday English 05"),
    item("2026-11-14", "20:00", "sound", "three-tree", "Sound it out 02"),
    item("2026-11-15", "17:00", "dialogue", "phone", "Everyday English 06"),
    item("2026-11-16", "12:00", "rule", "polite", "Ask politely"),
    item("2026-11-16", "17:00", "dialogue", "restaurant", "Everyday English 07"),
    item("2026-11-17", "12:00", "rule", "catch", "Collocations: catch"),
    item("2026-11-17", "17:00", "dialogue", "hotel", "Everyday English 08"),
]
STORIES = [(f"2026-11-{d}", t, f"{k}-2026-11-{d}") for d in (15, 16, 17) for t, k in (("09:00", "w"), ("18:00", "p"))]
MOVE = {  # id: (date, time, approve?)
    "2026-11-11-list-make-do": ("2026-11-15", "12:00", False),
    "2026-11-14-mistake-does-base-form": ("2026-11-17", "20:00", False),
    "2026-11-15-word-sky": ("2026-11-18", "12:00", False),
    "2026-11-16-story-saturday-market-part-1": ("2026-11-15", "20:00", True),
    "2026-11-19-story-saturday-market-part-2": ("2026-11-16", "20:00", True),
    "2026-11-22-story-saturday-market-part-3": ("2026-11-18", "20:00", True),
}

q = json.loads(QUEUE.read_text(encoding="utf-8"))
items = q["items"]
have = {i["id"] for i in items}
for i in items:
    if i["id"] in MOVE:
        date, time, approve = MOVE[i["id"]]
        i["date"], i["time"] = date, time
        if approve and i.get("review_status") == "draft":
            i["review_status"] = "approved"
for n in NEW:
    if n["id"] not in have:
        items.append(n)
for date, time, sid in STORIES:
    iid = f"{date}-story-{sid}"
    if iid not in have:
        items.append({"id": iid, "date": date, "time": time, "timezone": "Asia/Yerevan", "type": "STORY", "format": "STORIES",
                      "kind": "story-image", "content_id": sid, "title": sid, "caption": "", "review_status": "approved"})
items.sort(key=lambda i: (i["date"], i["time"], i["id"]))
QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(items), "items")

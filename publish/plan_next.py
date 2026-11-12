"""Fill 18–26 Nov: one Everyday English dialogue a day (18:30) with the remaining dialogues,
and approve the prepared drafts of 18–25 Nov so stage_media renders them."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "queue.json"
DIALOGUES = {d["id"]: d for d in json.loads((ROOT / "reels/data/dialogues.json").read_text(encoding="utf-8"))["dialogues"]}
LINK = "Ամբողջական դասերը ձայնով՝ bio-ի հղումով։"


def dialogue_caption(cid):  # same text as publish/plan_week.py
    d = DIALOGUES[cid]
    lines = "\n".join(f"{l['s']}: {l['en']}" for l in d["lines"])
    return (f"Խոսակցական անգլերեն · Everyday English dialogue\n\n{' '.join(d['title'])} · {d['title_hy']} · {d['level']}\n\n{lines}\n\n"
            f"Նախ լսի՛ր, հետո դու ես B-ն. ասա՛ քո տողերը բարձրաձայն։\n\n"
            f"Պահպանի՛ր և կրկնի՛ր, մինչև ազատ ասես։\n\n{LINK}\n\n#EnglishReadingRoom #Անգլերեն #անգլերենիդասեր #SpokenEnglish #Yerevan")
DM = "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։"
DAYS = ["2026-11-18", "2026-11-19", "2026-11-20", "2026-11-21", "2026-11-22", "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26"]
ORDER = ["birthday", "post-office", "pharmacy", "weekend", "hairdresser", "pizza", "library", "lost-keys", "homework"]

q = json.loads(QUEUE.read_text(encoding="utf-8"))
have = {i["id"] for i in q["items"]}
for day, cid in zip(DAYS, ORDER):
    iid = f"{day}-dialogue-{cid}"
    if iid in have: continue
    cap = dialogue_caption(cid)
    if DM not in cap: cap = cap.replace("Ամբողջական դասերը ձայնով", f"{DM}\nԱմբողջական դասերը ձայնով", 1)
    q["items"].append({"id": iid, "date": day, "time": "18:30", "timezone": "Asia/Yerevan", "type": "REEL", "format": "REELS",
                       "kind": "dialogue", "content_id": cid, "title": f"Everyday English · {cid}", "caption": cap, "review_status": "approved"})
n = 0
for i in q["items"]:
    if i.get("review_status") == "draft" and "2026-11-18" <= i["date"] <= "2026-11-25":
        i["review_status"] = "approved"; n += 1
        if DM not in i.get("caption", ""): i["caption"] = i["caption"].replace("Ամբողջական դասերը ձայնով", f"{DM}\nԱմբողջական դասերը ձայնով", 1)
q["items"].sort(key=lambda i: (i["date"], i["time"], i["id"]))
QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("approved", n, "drafts + dialogues")

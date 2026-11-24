"""Build queue.json: launch burst (first 5 days) + weekly rhythm, reusing reviewed captions."""
import json, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
old = {i["content_id"] + i["kind"]: i["caption"] for i in json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]}
cards = json.loads((ROOT / "reels/data/cards.json").read_text(encoding="utf-8"))
rules = json.loads((ROOT / "carousels/data/rules.json").read_text(encoding="utf-8"))
lists = json.loads((ROOT / "carousels/data/lists.json").read_text(encoding="utf-8"))
TAGS = "#EnglishReadingRoom #Անգլերեն #LearnEnglish #EnglishPractice"
LIST_CAP = {
 "dont-know": "Stop saying “I don’t know” 🙌\n\n6 բնական տարբերակ, որոնք խոսքդ ավելի վստահ և բնական կդարձնեն։\nՕրինակ՝ “I’m not sure. Maybe tomorrow?” — «Վստահ չեմ։ Գուցե վա՞ղը»։\n\nՊահպանի՛ր 📌 և ուղարկի՛ր ընկերոջդ ✈️",
 "make-do": "Make or do? 🤔\n\nMAKE՝ երբ ինչ-որ բան ստեղծում ենք, DO՝ գործերի և առաջադրանքների համար։\nՕրինակ՝ “Everyone makes mistakes.” — «Բոլորն էլ սխալվում են»։\n\nՊահպանի՛ր 📌 և գրի՛ր մեկնաբանություններում քո օրինակը 👇",
 "feelings": "6 feelings beyond happy and sad 💜\n\nԶգացմունքներ նկարագրող 6 բառ՝ B1 մակարդակի համար։\nՕրինակ՝ “I was relieved when the test was over.” — «Թեթևացա, երբ թեստն ավարտվեց»։\n\nՈ՞ր բառն է այսօր քո մասին 👇",
 "cafe": "Order in a café like a local ☕\n\n6 արտահայտություն, որ պետք կգան ճամփորդելիս։\nՕրինակ՝ “Could I have the bill, please?” — «Կարո՞ղ եմ հաշիվը ստանալ, խնդրում եմ»։\n\nՊահպանի՛ր 📌 հաջորդ ճամփորդության համար",
}
CQ = {q["id"]: q for q in cards["quizzes"]}; CM = {m["id"]: m for m in cards["mistakes"]}; CW = {w["id"]: w for w in cards["words"]}
def card_cap(kind, cid):
    if kind == "quiz":
        q = CQ[cid]; opts = " / ".join(f"{chr(65+i)} {o}" for i, o in enumerate(q["options"]))
        return f"5-second quiz ⏱\n\n{q['prompt']}\n{opts}\n\nԳրի՛ր պատասխանդ մեկնաբանություններում 👇 Ճիշտ պատասխանը՝ տեսանյութի վերջում։"
    if kind == "mistake":
        m = CM[cid]
        return f"Find the mistake 🔎\n\n❌ {m['wrong']}\n✅ {m['correct']}\n\n{m['explanation_hy']}\n\nՊահպանի՛ր 📌 և ուղարկի՛ր ընկերոջդ ✈️"
    if kind == "word":
        w = CW[cid]
        return f"Word of the day: {w['word']} ✨\n\n{w['word']} ({w['part_of_speech']}) — {w['armenian']}\n“{w['example']}” — «{w['example_hy'].rstrip('։')}»։\n\nՕգտագործի՛ր այս բառը քո նախադասությունում 👇"
    return None
def cap(kind, cid, fallback):
    c = card_cap(kind, cid) if kind in {"quiz", "mistake", "word"} else None
    if c: return f"{c}\n\n{TAGS}"
    c = old.get(cid + kind) or LIST_CAP.get(cid) or fallback
    if kind == "story":
        part = int(cid.rsplit("-", 1)[1]); c = c.split("\n\n#")[0]
        c += ("\n\nՇարունակությունը՝ շուտով։ Հետևի՛ր էջին, որ բաց չթողնես 🔔" if part < 3 else "\n\nՎերջ 💜 Ո՞ր մասն էր ամենահետաքրքիրը 👇")
    return c if "#" in c else f"{c}\n\n{TAGS}"
items = []
def add(day, time, kind, cid, title):
    fmt = "CAROUSEL" if kind in {"rule", "list"} else "REELS"
    items.append({"id": f"{day}-{kind}-{cid}", "date": day, "time": time, "timezone": "Asia/Yerevan",
        "type": "CAROUSEL" if fmt == "CAROUSEL" else "REEL", "format": fmt, "kind": "rule" if kind == "list" else kind,
        "content_id": cid, "title": title, "caption": cap("rule" if kind == "list" else kind, cid, title), "review_status": "draft"})
d0 = dt.date(2026, 11, 10)
D = lambda n: (d0 + dt.timedelta(days=n)).isoformat()
stories = [("zoo", "A Day at the Zoo"), ("saturday-market", "The Saturday Market"), ("my-garden", "My Little Garden")]
quizzes = [q["id"] for q in cards["quizzes"]]; mistakes = [m["id"] for m in cards["mistakes"]]; words = [w["id"] for w in cards["words"]]
rule_ids = [r["id"] for r in rules]
# launch burst
add(D(0), "19:00", "list", "dont-know", "Stop saying “I don’t know”")
add(D(0), "20:00", "story", "zoo-part-1", "A Day at the Zoo")
add(D(0), "21:00", "quiz", quizzes.pop(0), "Quiz")
add(D(1), "13:00", "list", "make-do", "Make or do?")
add(D(1), "17:00", "mistake", mistakes.pop(0), "Fix it")
add(D(1), "20:00", "story", "zoo-part-2", "A Day at the Zoo")
add(D(2), "13:00", "rule", rule_ids.pop(0), "Grammar")
add(D(2), "17:00", "word", words.pop(0), "Word of the day")
add(D(2), "20:00", "story", "zoo-part-3", "A Day at the Zoo")
add(D(3), "13:00", "list", "feelings", "6 feelings")
add(D(3), "20:00", "quiz", quizzes.pop(0), "Quiz")
add(D(4), "13:00", "list", "cafe", "Order in a café")
add(D(4), "20:00", "mistake", mistakes.pop(0), "Fix it")
# weekly rhythm from day 5 (Sun 15 Nov)
st = 1
for n in range(5, 31):
    day = d0 + dt.timedelta(days=n); wd = day.weekday()  # Mon=0
    if wd == 0 and st < len(stories): add(D(n), "19:00", "story", f"{stories[st][0]}-part-1", stories[st][1])
    if wd == 3 and st < len(stories): add(D(n), "19:00", "story", f"{stories[st][0]}-part-2", stories[st][1])
    if wd == 6 and n > 5 and st < len(stories): add(D(n), "19:00", "story", f"{stories[st][0]}-part-3", stories[st][1]); st += 1
    if wd in (1, 4) and rule_ids: add(D(n), "13:00", "rule", rule_ids.pop(0), "Grammar")
    if wd == 2 and mistakes: add(D(n), "19:00", "mistake", mistakes.pop(0), "Fix it")
    if wd == 5 and quizzes: add(D(n), "12:00", "quiz", quizzes.pop(0), "Quiz")
    if wd == 6 and words: add(D(n), "12:00", "word", words.pop(0), "Word of the day")
q = {"brand": "Gayane Torosyan · English Reading Room", "motto": "Let's read together", "timezone": "Asia/Yerevan", "items": items}
(ROOT / "queue.json").write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(items), "items")

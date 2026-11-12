"""Cover specs (dictionary-page style) for every unpublished feed post in queue.json."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SKILL = {"speaking": "#1C8AA3", "pronunciation": "#B23F78", "grammar": "#3E5FD9", "test": "#2E9E6A", "vocabulary": "#B9790B", "reading": "#6A49E2"}
load = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
DIAL = {d["id"]: d for d in load("reels/data/dialogues.json")["dialogues"]}
SND = {s["id"]: s for s in load("reels/data/sounds.json")["sounds"]}
CARDS = load("reels/data/cards.json")
MIS = {c["id"]: c for c in CARDS["mistakes"]}; QUIZ = {c["id"]: c for c in CARDS["quizzes"]}; WORD = {c["id"]: c for c in CARDS["words"]}
LISTS = {s["id"]: s for s in load("carousels/data/lists.json")}
r = load("carousels/data/rules.json"); RULES = {x["id"]: x for x in (r if isinstance(r, list) else next(iter(r.values())))}
t = load("carousels/data/tests.json"); TESTS = {x["id"]: x for x in (t if isinstance(t, list) else next(iter(t.values())))}

from html import escape as E

def accent(title):  # italicise the last word: "At the café" -> At the <i>café</i>
    w = E(title).rsplit(" ", 1)
    return f"{w[0]} <i>{w[1]}</i>" if len(w) == 2 else f"<i>{E(title)}</i>"

def first_sentence(text, limit=150):
    parts = re.split(r"(?<=[.!?])\s+|(?<=[.!?][\"”])\s+", text.strip())
    s = parts[0]
    for p in parts[1:]:
        if len(s) + 1 + len(p) > limit: break
        s += " " + p
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"

def spec(i, n):
    k, cid = i["kind"], i["content_id"]
    if k == "dialogue":
        d = DIAL[cid]; a = next(l for l in d["lines"] if l["s"] == "A")
        me = "B"
        body = (f'<div class="q">“</div><h1>{E(d["title"][0])} <i>{E(d["title"][1])}</i></h1><div class="hy t">{E(d["title_hy"])}</div>'
                f'<div class="script"><b>{a["s"]} ·</b><div>{E(a["en"])}</div><b class="me">{me} ·</b><div class="me">Your turn …</div></div>')
        return dict(c=SKILL["speaking"], layout="dlg", label="EVERYDAY ENGLISH", right=d["level"], body=body, num=f"No. {d['number']:02d}")
    if k == "sound":
        s = SND[cid]; a, b = s["a"], s["b"]
        col = lambda x, ab: f'<div><span class="ab">{ab}</span><b>{E(x["word"])}</b><div class="ipa">{E(x["ipa"])}</div><div class="hy">{E(x["hy"])}</div></div>'
        body = f'<div class="ask">Can you hear<br>the <i>difference?</i></div><div class="pair">{col(a, "A")}<div class="bar"></div>{col(b, "B")}</div>'
        return dict(c=SKILL["pronunciation"], layout="snd", label="SOUND IT OUT", right=s["focus"], body=body, num=f"No. {s['number']:02d}")
    if k == "mistake":
        m = MIS[cid]; w, c = m["wrong"].split(), m["correct"].split()
        j = next((x for x in range(min(len(w), len(c))) if w[x] != c[x]), 0)
        before, after = " ".join(w[:j]), " ".join(w[j + 1:])
        # the cover marks where the mistake is, but never gives the answer away
        proof = f'{E(before)} <span style="position:relative;display:inline-block;text-decoration:underline wavy #B23F78;text-decoration-thickness:4px;text-underline-offset:12px">{E(w[j])}<span class="fix" style="left:20%;top:0">?</span></span> {E(after)}'
        body = f'<h1>Find the<br><i>mistake</i></h1><div class="proof">{proof}</div><div class="hy">Գտի՛ր սխալը և ասա ճիշտ ձևը</div>'
        return dict(c=SKILL["grammar"], layout="mis", label="FIND THE MISTAKE", right="", body=body, num=f"No. {n:02d}")
    if k == "quiz":
        q = QUIZ[cid]
        opts = "".join(f'<div><b>{"ABC"[x]}</b>{E(o)}</div>' for x, o in enumerate(q["options"][:3]))
        body = f'<div class="timer">5</div><h1>Choose the <i class="c">right</i> answer</h1><div class="qst" data-fit>{E(q["prompt"]).replace("___", "_____")}</div><div class="opts">{opts}</div>'
        return dict(c=SKILL["test"], layout="qz", label="5-SECOND QUIZ", right="", body=body, num=f"No. {n:02d}")
    if k == "word":
        w = WORD[cid]
        body = (f'<div class="tab">{E(w["word"][0].upper())}</div><h1 data-fit>{E(w["word"])}</h1><div class="pos">{E(w["part_of_speech"])}</div>'
                f'<div class="tr hy">{E(w["armenian"])}</div><div class="ex">“{E(w["example"])}”</div>')
        return dict(c=SKILL["vocabulary"], layout="word", label="WORD OF THE DAY", right="", body=body, num=f"No. {n:02d}")
    if k == "story":
        lesson, part = re.match(r"(.+)-part-(\d+)", cid).groups()
        L = load(f"assets/lessons/{lesson}.lesson.json")
        body = (f'<div class="chap">PART {int(part)}</div><div class="orn"></div><h1>{accent(L["title"])}</h1>'
                f'<div class="open">{E(first_sentence(L["text"][int(part) - 1]))}</div><div class="page">— {int(part)} —</div>')
        return dict(c=SKILL["reading"], layout="sty", label="STORY TIME", right=f"{L['level']} · SHORT STORY", body=body, num=f"No. {n:02d}")
    if k == "rule":
        if cid in LISTS:
            s = LISTS[cid]; colloc = s["series"] in ("COLLOCATIONS", "NEW WORDS")
            m = re.search(r"<em>(.*?)</em>", s["title"]); key = m[1] if m else ""
            if s["series"] == "COLLOCATIONS" and key and len(key) <= 8:
                rest = re.sub(r"\s*<em>.*?</em>\s*", " ", s["title"]).strip()
                idx = "".join(f'<div>{E(x["en"])}</div>' for x in s["items"][:6])
                body = f'<div class="key" data-fit>{E(key)}</div><div class="kt">{E(rest)}</div><div class="idx">{idx}</div>'
                return dict(c=SKILL["vocabulary"], layout="glo", label=s["series"], right=s["chip"].split(" · ")[0], body=body, num=f"No. {n:02d}")
            title = s["title"].replace("<em>", "<i>").replace("</em>", "</i>")
            alts = "".join(f'<div>{E(x["en"])}</div>' for x in s["items"][:3])
            body = f'<h1>{title}</h1><div class="alts">{alts}</div><div class="hy">{E(s["subtitle_hy"])}</div>'
            return dict(c=SKILL["vocabulary" if colloc else "speaking"], layout="say", label=s["series"], right=s["chip"].split(" · ")[0], body=body, num=f"No. {n:02d}")
        if cid in RULES:
            x = RULES[cid]
            body = f'<h1>{accent(x["title"])}</h1><div class="box"><small>THE RULE</small>{E(x["pattern"])}</div><div class="hy">{E(x["armenian_title"])}</div>'
            return dict(c=SKILL["grammar"], layout="rul", label="GRAMMAR MADE CLEAR", right=x["level"], body=body, num=f"No. {n:02d}")
        if cid in TESTS:
            x = TESTS[cid]
            body = ('<h1>Test<br><i>yourself</i></h1><div class="sheet"><div>Name<span></span></div><div>Score<span></span>/ 5</div></div>'
                    '<div class="hy">5 հարց UFAR-ի ձևաչափով · պատասխանները վերջում</div>')
            return dict(c=SKILL["test"], layout="ufr", label="UFAR PRACTICE", right=f"TEST {x['num']:02d}", body=body, num=f"No. {x['num']:02d}")
    raise KeyError(f"{k}/{cid}")

def series_key(i):
    k, cid = i["kind"], i["content_id"]
    if k == "rule": return "list-" + LISTS[cid]["series"] if cid in LISTS else ("rule" if cid in RULES else "test")
    return k

if __name__ == "__main__":
    q = load("queue.json")["items"]
    feed = sorted((i for i in q if i["format"] in ("REELS", "CAROUSEL")), key=lambda i: (i["date"], i["time"], i["id"]))
    counts, out = {}, []
    for i in feed:
        if i["kind"] in ("words10", "phrasal", "review"): continue  # these series render their own cover frame
        key = series_key(i); counts[key] = counts.get(key, 0) + 1
        if i.get("review_status") == "published": continue
        s = spec(i, counts[key]); s.update(id=i["id"], h=1920 if i["format"] == "REELS" else 1350)
        out.append(s)
    (ROOT / ".render-work").mkdir(exist_ok=True)
    (ROOT / ".render-work/covers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "covers")

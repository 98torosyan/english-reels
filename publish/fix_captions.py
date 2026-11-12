"""Caption polish for reach (idempotent): keyword-rich first line, one comment question, 5 focused hashtags.
Run after any plan_* script: python publish/fix_captions.py"""
import json
from pathlib import Path

QUEUE = Path(__file__).resolve().parents[1] / "queue.json"
SERIES_TAG = {"words10": "#EnglishVocabulary", "phrasal": "#PhrasalVerbs", "reading": "#EnglishReading", "review": "#EnglishVocabulary",
              "dialogue": "#SpokenEnglish", "story": "#EnglishStories", "sound": "#EnglishPronunciation", "mistake": "#EnglishGrammar",
              "quiz": "#EnglishQuiz", "word": "#EnglishVocabulary", "rule": None, "routine": "#SpokenEnglish"}
ASK = {"words10": "Ո՞ր բառն էր քեզ համար նոր։ Գրի՛ր մեկնաբանություններում։",
       "phrasal": "Կազմի՛ր քո նախադասությունը այս դարձվածներից մեկով և գրի՛ր մեկնաբանություններում։",
       "reading": "Ո՞ր բառն էր քեզ համար նոր։ Գրի՛ր մեկնաբանություններում։"}
DM = "Անհատական և խմբային դասերի համար գրե՛ք Direct-ով։"


def fix(i):
    cap, kind = i["caption"], i.get("kind")
    lines = cap.rstrip().split("\n")
    if lines[-1].startswith("#"):
        old = lines[-1].split()
        series = SERIES_TAG.get(kind) or next((t for t in old if t not in ("#EnglishReadingRoom", "#Անգլերեն", "#անգլերենիդասեր", "#Yerevan", "#learnenglish", "#անգլերեն")), "#EnglishGrammar")
        if "#UFAR" in old:
            lines[-1] = "#UFAR #միասնականքննություն #անգլերեն #learnenglish #Yerevan"
        else:
            lines[-1] = f"#learnenglish #անգլերեն #անգլերենիդասեր {series} #Yerevan"
    if kind == "words10" and lines[0].startswith("10 բառ · "): lines[0] = lines[0].replace("10 բառ · ", "10 անգլերեն բառ · ", 1)
    if kind == "phrasal" and lines[0].startswith("Phrasal verbs · "): lines[0] = lines[0].replace("Phrasal verbs · ", "Անգլերեն phrasal verb-եր · ", 1)
    cap = "\n".join(lines)
    ask = ASK.get(kind)
    if ask and ask not in cap and DM in cap: cap = cap.replace(DM, f"{ask}\n\n{DM}", 1)
    return cap


q = json.loads(QUEUE.read_text(encoding="utf-8"))
n = 0
for i in q["items"]:
    if i.get("review_status") in ("staged", "approved", "draft") and i.get("format") != "STORIES" and i.get("caption"):
        new = fix(i)
        if new != i["caption"]: i["caption"] = new; n += 1
QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(n, "captions updated")

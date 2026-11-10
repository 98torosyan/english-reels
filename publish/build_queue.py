from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / "carousels" / "data" / "rules.json").read_text(encoding="utf-8"))
CARDS = json.loads((ROOT / "reels" / "data" / "cards.json").read_text(encoding="utf-8"))
LESSON_ORDER = ["zoo", "saturday-market", "my-garden"]
STORY_DAYS = [0, 4, 7]
HASHTAGS = ["#EnglishReadingRoom", "#Անգլերեն", "#EnglishPractice", "#LearnEnglish"]


def caption_for_story(lesson: dict, part: int) -> str:
    paragraph = lesson["text"][part - 1]
    sentence = paragraph.split(". ", 1)[0].rstrip(".!?") + "."
    hy = json.loads((ROOT / "assets" / "lessons" / "translations.hy.json").read_text(encoding="utf-8"))
    paragraph_hy = hy[lesson["id"]][part - 1][0].rstrip("։.!?")
    ordinal = {1: "1-ին", 2: "2-րդ", 3: "3-րդ"}[part]
    return (
        f"{lesson['title']} · {lesson['level']} reading\n\n"
        f"Կարդա՛ և լսի՛ր պատմության {ordinal} մասը։ {paragraph_hy}։\n"
        f"Օրինակ՝ “{sentence}” — «{paragraph_hy}»։\n\n"
        + " ".join(HASHTAGS)
    )


def caption_for_mistake(item: dict) -> str:
    return (
        f"{item['keyword']}\n\n{item['explanation_hy']}\n"
        f"Օրինակ՝ “{item['wrong']}” → “{item['correct']}”.\n\n"
        + " ".join(HASHTAGS)
    )


def caption_for_quiz(item: dict) -> str:
    return (
        f"{item['keyword']}\n\nՓորձի՛ր ընտրել ճիշտ պատասխանը։ {item['explanation_hy']}\n"
        f"Օրինակ՝ “{item['prompt'].replace('___', item['answer'])}”։\n\n"
        + " ".join(HASHTAGS)
    )


def caption_for_word(item: dict) -> str:
    return (
        f"{item['word']} · {item['part_of_speech']}\n\n"
        f"Նշանակում է «{item['armenian']}»։ Օրինակ՝ “{item['example']}” — «{item['example_hy']}»։\n\n"
        + " ".join(HASHTAGS)
    )


def caption_for_rule(rule: dict) -> str:
    return (
        f"{rule['title']}\n\n{rule['rule']}\n"
        f"Օրինակ՝ “{rule['example']}” — «{rule['example_hy']}»։\n\n"
        + " ".join(["#EnglishReadingRoom", "#Անգլերեն", "#ԱնգլերենիՔերականություն", "#EnglishGrammar"])
    )


def main() -> None:
    today = date.fromisoformat(os.environ.get("QUEUE_START_DATE", date.today().isoformat()))
    lessons = {
        slug: json.loads((ROOT / "assets" / "lessons" / f"{slug}.lesson.json").read_text(encoding="utf-8"))
        for slug in LESSON_ORDER
    }
    items: list[dict] = []
    counts = {"story": 0, "mistake": 0, "quiz": 0, "word": 0, "carousel": 0}
    for day_index in range(30):
        current = today + timedelta(days=day_index)
        slot = day_index % 10
        if slot in STORY_DAYS:
            story_order = STORY_DAYS.index(slot)
            part = day_index // 10 + 1
            lesson = lessons[LESSON_ORDER[story_order]]
            item = {
                "id": f"{current.isoformat()}-story-{lesson['id']}-part-{part}",
                "date": current.isoformat(), "time": "19:00", "timezone": "Asia/Yerevan",
                "type": "REEL", "format": "REELS", "kind": "story",
                "content_id": f"{lesson['id']}-part-{part}", "title": lesson["title"],
                "part": part, "caption": caption_for_story(lesson, part),
                "review_status": "draft", "requires_human_review": True,
                "asset_status": "local lesson audio and timings"
            }
            counts["story"] += 1
        elif slot in (1, 5, 8):
            item_data = CARDS["mistakes"][counts["mistake"] % len(CARDS["mistakes"])]
            item = {
                "id": f"{current.isoformat()}-mistake-{item_data['id']}",
                "date": current.isoformat(), "time": "19:00", "timezone": "Asia/Yerevan",
                "type": "REEL", "format": "REELS", "kind": "mistake",
                "content_id": item_data["id"], "title": item_data["keyword"],
                "content": item_data, "caption": caption_for_mistake(item_data),
                "review_status": "draft", "requires_human_review": True,
                "asset_status": "voice track needed" if "audio" not in item_data else "voice track available"
            }
            counts["mistake"] += 1
        elif slot in (2, 6):
            item_data = CARDS["quizzes"][counts["quiz"] % len(CARDS["quizzes"])]
            item = {
                "id": f"{current.isoformat()}-quiz-{item_data['id']}",
                "date": current.isoformat(), "time": "19:00", "timezone": "Asia/Yerevan",
                "type": "REEL", "format": "REELS", "kind": "quiz",
                "content_id": item_data["id"], "title": item_data["keyword"],
                "content": item_data, "caption": caption_for_quiz(item_data),
                "review_status": "draft", "requires_human_review": True,
                "asset_status": "voice track needed" if "audio" not in item_data else "voice track available"
            }
            counts["quiz"] += 1
        else:
            item_data = CARDS["words"][counts["word"] % len(CARDS["words"])]
            item = {
                "id": f"{current.isoformat()}-word-{item_data['id']}",
                "date": current.isoformat(), "time": "19:00", "timezone": "Asia/Yerevan",
                "type": "REEL", "format": "REELS", "kind": "word",
                "content_id": item_data["id"], "title": item_data["word"],
                "content": item_data, "caption": caption_for_word(item_data),
                "review_status": "draft", "requires_human_review": True,
                "asset_status": "voice track available"
            }
            counts["word"] += 1
        items.append(item)

        if current.weekday() in {1, 3, 5}:
            rule = RULES[counts["carousel"] % len(RULES)]
            items.append({
                "id": f"{current.isoformat()}-carousel-{rule['id']}",
                "date": current.isoformat(), "time": "13:00", "timezone": "Asia/Yerevan",
                "type": "CAROUSEL", "format": "CAROUSEL", "kind": "rule",
                "content_id": rule["id"], "title": rule["title"],
                "caption": caption_for_rule(rule),
                "review_status": "draft", "requires_human_review": True,
                "asset_status": "template ready; image files not yet hosted"
            })
            counts["carousel"] += 1

    items.sort(key=lambda entry: (entry["date"], entry["time"], entry["type"]))
    output = {
        "brand": "Gayane Torosyan · English Reading Room",
        "motto": "Let's read together",
        "range": {"start": today.isoformat(), "end": (today + timedelta(days=29)).isoformat()},
        "timezone": "Asia/Yerevan",
        "status": "draft; scheduling and publishing are disabled",
        "counts": {"reels": 30, "carousels": counts["carousel"]},
        "items": items,
    }
    (ROOT / "queue.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Draft queue created: {counts['story']} stories, {counts['mistake']} mistakes, {counts['quiz']} quizzes, {counts['word']} words, {counts['carousel']} carousels.")


if __name__ == "__main__":
    main()

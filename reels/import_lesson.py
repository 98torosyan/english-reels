from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def split_sentences(paragraph: str) -> list[str]:
    return [part for part in re.split(r'(?<=[.!?])["”]?\s+', paragraph.strip()) if part]


def load_essays(path: Path) -> list[dict]:
    source = path.read_text(encoding="utf-8")
    data = json.loads(source[source.index("["):source.rindex("]") + 1])
    if not isinstance(data, list):
        raise ValueError("The lesson source does not contain a lesson list.")
    return data


def import_lesson(site_root: Path, slug: str) -> None:
    essay_source = site_root / "essays.js"
    audio_source = site_root / "audio"
    if not essay_source.is_file() or not audio_source.is_dir():
        raise FileNotFoundError("The source folder must contain essays.js and audio/.")
    lesson = next((item for item in load_essays(essay_source) if item.get("id") == slug), None)
    if lesson is None:
        raise ValueError(f"Lesson id not found: {slug}")

    destination = ROOT / "assets" / "lessons"
    destination.mkdir(parents=True, exist_ok=True)
    for suffix in (".json", ".mp3"):
        source = audio_source / f"{slug}{suffix}"
        if not source.is_file():
            raise FileNotFoundError(f"Lesson media file is missing: {source.name}")
        shutil.copy2(source, destination / f"{slug}{suffix}")
    (destination / f"{slug}.lesson.json").write_text(
        json.dumps(lesson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    translations_path = destination / "translations.hy.json"
    translations = json.loads(translations_path.read_text(encoding="utf-8")) if translations_path.exists() else {}
    translations[slug] = [[""] * len(split_sentences(paragraph)) for paragraph in lesson["text"]]
    translations_path.write_text(
        json.dumps(translations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Imported {lesson['title']} ({lesson['level']}).")
    print("Add and review each Armenian sentence in assets/lessons/translations.hy.json before rendering.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import one lesson and its voice timings for a story reel.")
    parser.add_argument("--site-repo", required=True, type=Path)
    parser.add_argument("--id", required=True)
    args = parser.parse_args()
    import_lesson(args.site_repo.resolve(), args.id)


if __name__ == "__main__":
    main()

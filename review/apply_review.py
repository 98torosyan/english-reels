"""Apply review.json decisions to queue.json (approved / fix + note)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
dec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
q = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))
n = 0
for it in q["items"]:
    d = dec.get(it["id"])
    if d and it.get("review_status") in {"draft", "fix", "approved"}:
        it["review_status"] = d["v"]; it["review_note"] = d.get("note", ""); n += 1
(ROOT / "queue.json").write_text(json.dumps(q, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{n} decision(s) applied")

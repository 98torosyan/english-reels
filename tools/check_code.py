"""Code health check (runs in CI on every push and every night):
1. every Python file compiles; ruff finds no real bugs (undefined names, unused imports, likely mistakes);
2. every JavaScript file and every <script> inside the HTML templates parses;
3. every data file is valid JSON and every story/carousel has what its renderer needs;
4. every queue item that is still to be published passes the publisher's own validation.
Exit code 1 with a list of problems if anything is wrong."""
import json, py_compile, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publish"))
problems = []
bad = problems.append
tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()

# 1. Python
for f in [f for f in tracked if f.endswith(".py")]:
    try: py_compile.compile(str(ROOT / f), doraise=True)
    except py_compile.PyCompileError as e: bad(f"python: {f}: {e.msg.strip()[:200]}")
r = subprocess.run(["ruff", "check", "--select", "F,E9,PLE,B", "--ignore", "E701,E702,E731,B006,B007,B008,B904,B905,F841",
                    "--output-format", "concise", "--quiet", "."], cwd=ROOT, capture_output=True, text=True)
if r.returncode not in (0, 1): bad(f"ruff could not run: {r.stderr[:200]}")
for line in r.stdout.splitlines():
    if line.strip() and "node_modules" not in line: bad(f"python: {line}")

# 2. JavaScript, including the scripts inside the templates
for f in [f for f in tracked if f.endswith(".js")]:
    r = subprocess.run(["node", "--check", str(ROOT / f)], capture_output=True, text=True)
    if r.returncode: bad(f"js: {f}: {r.stderr.strip().splitlines()[-1][:200] if r.stderr.strip() else 'syntax error'}")
for f in [f for f in tracked if f.endswith(".html") and ("templates" in f or "source-template" in f)]:
    for k, code in enumerate(re.findall(r"<script>([\s\S]*?)</script>", (ROOT / f).read_text(encoding="utf-8"))):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as t: t.write(code)
        r = subprocess.run(["node", "--check", t.name], capture_output=True, text=True)
        if r.returncode: bad(f"js: {f} <script> {k + 1}: {r.stderr.strip().splitlines()[-1][:200]}")

# 3. Data files
for f in [f for f in tracked if f.endswith(".json") and not f.startswith(("node_modules", "assets/"))]:
    try: json.loads((ROOT / f).read_text(encoding="utf-8"))
    except Exception as e: bad(f"json: {f}: {e}")
def need(path, key, fields):
    p = ROOT / path
    if not p.exists(): return
    for s in json.loads(p.read_text(encoding="utf-8"))[key]:
        for k in fields:
            if not s.get(k): bad(f"data: {path} '{s.get('id')}' has no {k}")
need("reels/data/feelstory.json", "stories", ["id", "title", "title_hy", "voice", "scenes", "scenes_hy"])
need("reels/data/storyvideo.json", "stories", ["id", "title", "title_hy", "scenes"])
for s in json.loads((ROOT / "reels/data/storyvideo.json").read_text(encoding="utf-8"))["stories"]:
    if not (s.get("scenes_hy") or s.get("hy")): bad(f"data: storyvideo '{s['id']}' has no Armenian text")
need("carousels/data/opposites.json", "days", ["id", "title", "pairs"])
for s in json.loads((ROOT / "reels/data/feelstory.json").read_text(encoding="utf-8"))["stories"]:
    if len(s["scenes"]) != len(s["scenes_hy"]) or any(len(a) != len(b) for a, b in zip(s["scenes"], s["scenes_hy"])):
        bad(f"data: feelstory '{s['id']}': English and Armenian lines do not match one to one")
    for sc in s["scenes"]:
        for line in sc:
            if line.count("[") != line.count("]"): bad(f"data: feelstory '{s['id']}': unbalanced [ ] in “{line}”")

# 4. Queue: everything still to be published must pass the publisher's validation
import publish  # noqa: E402
q = json.loads((ROOT / "queue.json").read_text(encoding="utf-8"))["items"]
seen = set()
for i in q:
    if i["id"] in seen: bad(f"queue: duplicate id {i['id']}")
    seen.add(i["id"])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", i.get("date", "")) or not re.fullmatch(r"\d{2}:\d{2}", i.get("time", "")): bad(f"queue: {i['id']}: bad date/time")
    if i.get("review_status") != "staged" or i.get("published_at"): continue
    content = {"kind": i["format"], "caption": i.get("caption", ""), **(i.get("media") or {})}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as t: json.dump(content, t, ensure_ascii=False)
    try: publish.load_content(Path(t.name))
    except publish.PublishError as e: bad(f"queue: {i['id']}: {e}")
    if len(i.get("caption", "")) > 2200: bad(f"queue: {i['id']}: caption longer than Instagram allows")
    if i.get("caption", "").count("#") > 30: bad(f"queue: {i['id']}: more than 30 hashtags")

print("\n".join(problems) if problems else "code check: all good")
print(f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)

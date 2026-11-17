"""Bring 'Story in a minute' pictures into the system: sNN-K.jpg (story NN, picture K of 6) becomes
assets/minute/sNN-K/src.png (+ 'single' marker), trimmed of any light paper margin; story n=NN then shows its
pictures in order (only when all of them are there). Usage: python tools/ingest_minute.py <folder with sNN-K.jpg>"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def trim(im):
    """Cut a pale paper margin or a drawn frame, if the picture has one (a few percent at most per side)."""
    g = np.asarray(im.convert("L")).astype(int); h, w = g.shape
    def edge(lines, size):
        for i in range(int(size * .12)):
            if lines[i].std() > 22 or lines[i].mean() < 225: return min(i + int(size * .006), int(size * .12))
        return 0
    t = edge(g, h); b = edge(g[::-1], h); l = edge(g.T, w); r = edge(g.T[::-1], w)
    m = max(t, b, l, r, int(min(w, h) * .02))   # same cut on every side keeps the shape; at least 2% removes soft paper edges
    return im.crop((m, m, w - m, h - m))


def main(folder):
    data_p = ROOT / "reels/data/feelstory.json"; data = json.loads(data_p.read_text(encoding="utf-8"))
    stories = data if isinstance(data, list) else data["stories"]
    by_n = {s["n"]: s for s in stories if s["id"].startswith("minute-")}
    got = {}
    for f in sorted(Path(folder).glob("s[0-9][0-9]-[0-9].*")):
        n, k = int(f.stem[1:3]), int(f.stem[4:]); d = ROOT / f"assets/minute/s{n:02d}-{k}"; d.mkdir(parents=True, exist_ok=True)
        trim(Image.open(f).convert("RGB")).save(d / "src.png"); (d / "single").touch(); got.setdefault(n, set()).add(k)
    for n, ks in sorted(got.items()):
        have = sorted(k for k in range(1, 7) if (ROOT / f"assets/minute/s{n:02d}-{k}/src.png").exists())
        if len(have) >= 5: by_n[n]["pics"] = [f"minute/s{n:02d}-{k}/1.jpg" for k in have]
        print(by_n[n]["id"], "pictures:", have)
    data_p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])

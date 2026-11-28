"""Word sets: cut the 3 x 4 picture sheet into 12 sharp pictures and make the voice clips.

    python tools/words_assets.py pictures   # assets/words/<id>/01.jpg … 12.jpg (Real-ESRGAN, like the reading panels)
    python tools/words_assets.py voices     # intro.mp3, 01.mp3 … 12.mp3 (each word said twice), outro.mp3
Only what is missing is made.
"""
import asyncio, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "reels/data/words.json").read_text(encoding="utf-8"))


def cells(im, cols=3, rows=4):
    """Cut along the white gutters; fall back to an even grid a little inside each cell."""
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(int); white = a.min(axis=2) > 232

    def lines(v, n):
        idx = [i for i, x in enumerate(v) if x > 0.96]; groups = []
        for i in idx:
            if groups and i == groups[-1][1] + 1: groups[-1][1] = i
            else: groups.append([i, i])
        edges = [g for g in groups if 0 < (g[0] + g[1]) / 2 / len(v) < 1]
        inner = [g for g in edges if 0.08 < (g[0] + g[1]) / 2 / len(v) < 0.92]
        return inner if len(inner) == n - 1 else None

    W, H = im.size
    vx, vy = lines(white.mean(axis=0), cols), lines(white.mean(axis=1), rows)
    xs = [0] + [c for g in vx for c in g] + [W] if vx else None
    ys = [0] + [c for g in vy for c in g] + [H] if vy else None
    out = []
    for r in range(rows):
        for c in range(cols):
            if xs and ys:
                box = (xs[2 * c] + 6, ys[2 * r] + 6, xs[2 * c + 1] - 6, ys[2 * r + 1] - 6)
            else:
                cw, ch = W / cols, H / rows; m = 0.03
                box = (round(c * cw + cw * m), round(r * ch + ch * m), round((c + 1) * cw - cw * m), round((r + 1) * ch - ch * m))
            out.append(im.crop(box))
    return out


def pictures():
    import numpy as np, torch
    from PIL import Image
    from spandrel import ModelLoader
    net = None
    for s in DATA["sets"]:
        d = ROOT / "assets/words" / s["id"]
        if not (d / "sheet.png").exists() or (d / "12.jpg").exists(): continue
        net = net or ModelLoader().load_from_file(str(ROOT / "weights" / "realesr-animevideov3.pth")).eval()
        for k, p in enumerate(cells(Image.open(d / "sheet.png")), 1):
            x = torch.from_numpy(np.asarray(p.convert("RGB")).copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)
            with torch.inference_mode():
                y = net(x).clamp(0, 1)[0].permute(1, 2, 0).mul(255).round().byte().numpy()
            big = Image.fromarray(y).resize((1600, round(1600 * p.height / p.width)), Image.LANCZOS)
            Image.blend(big, p.convert("RGB").resize(big.size, Image.LANCZOS), 0.3).save(d / f"{k:02d}.jpg", quality=93)
        print(s["id"], "12 pictures")


def voices():
    sys.path.insert(0, str(ROOT / "voices"))
    from make_voice import synth
    for s in DATA["sets"]:
        d = ROOT / "assets/words" / s["id"]; d.mkdir(parents=True, exist_ok=True)
        jobs = [("intro", s["intro"])] + [(f"{k:02d}", f"{w[0][:1].upper() + w[0][1:]}.") for k, w in enumerate(s["words"], 1)] + [("outro", s["outro"])]
        for name, text in jobs:
            mp3 = d / f"{name}.mp3"
            if mp3.exists(): continue
            asyncio.run(synth(text, DATA["voice"], "-8%", mp3))
            print(s["id"], name)


if __name__ == "__main__":
    {"pictures": pictures, "voices": voices}[sys.argv[1]]()

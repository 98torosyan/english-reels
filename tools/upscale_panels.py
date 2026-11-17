"""Cut a 2x3 or 3x3 storyboard (src.png) into square panels and sharpen them with Real-ESRGAN (BSD-3, anime-6B weights for illustrations; loaded with spandrel, MIT).

For every assets/picstory/<id>/src.png and assets/storyvideo/<id>/src.png whose panels are missing or older
than the source, writes 1.jpg … 6.jpg (or 9.jpg) at 1080x1080. Runs in CI (GitHub Actions) where PyTorch is available.
Without --sharp it only cuts and resizes (used locally)."""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def panels(src):
    im = Image.open(src).convert("RGB"); a = np.asarray(im).astype(int); white = a.min(axis=2) > 232
    def runs(v, th=.95):
        out, s = [], None
        for i, x in enumerate(v):
            if x > th and s is None: s = i
            if x <= th and s is not None: out.append((s, i)); s = None
        if s is not None: out.append((s, len(v)))
        return out
    def spans(g, n):
        e, p = [], 0
        for s, t in g:
            if s > p: e.append((p, s))
            p = t
        if p < n: e.append((p, n))
        return [x for x in e if x[1] - x[0] > 200]
    cols, rows = spans(runs(white.mean(axis=0)), im.size[0]), spans(runs(white.mean(axis=1)), im.size[1])
    if (len(cols), len(rows)) not in ((2, 3), (3, 2), (3, 3), (2, 4), (2, 5), (5, 2)): raise ValueError(f"{src}: expected a 2x3, 3x3 or 2x4 grid, found {len(cols)}x{len(rows)}")
    pick = src.parent / "pick"   # optional: which panels to keep (1-based), e.g. when the grid repeats a picture
    keep = [int(x) for x in pick.read_text().split()] if pick.exists() else None
    cells = []
    for r in rows:
        for c in cols:
            p = im.crop((c[0] + 3, r[0] + 3, c[1] - 3, r[1] - 3)); w, h = p.size; s = min(w, h)
            cells.append(p.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)))
    yield from ([cells[k - 1] for k in keep] if keep else cells)   # the pick order is the story order


def main():
    sharp = "--sharp" in sys.argv
    import time
    budget = float(sys.argv[sys.argv.index("--budget") + 1]) * 60 if "--budget" in sys.argv else 1e9   # seconds
    t0 = time.monotonic(); left = 0
    model = None
    if sharp:
        import torch
        from spandrel import ModelLoader
        torch.set_num_threads(4)
        nets = {"art": ModelLoader().load_from_file("weights/RealESRGAN_x4plus_anime_6B.pth").eval(),
                "photo": ModelLoader().load_from_file("weights/RealESRGAN_x4plus.pth").eval()}
        def _up(p, kind):
            x = torch.from_numpy(np.asarray(p).copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)
            with torch.inference_mode():
                y = nets[kind](x).clamp(0, 1)[0].permute(1, 2, 0).mul(255).round().byte().numpy()
            out = Image.fromarray(y)
            if kind == "photo":   # keep natural skin and texture: half model, half plain resize
                out = Image.blend(out, p.resize(out.size, Image.LANCZOS), 0.45)
            return out
        model = _up
    done = 0
    for src in sorted(p for d in ("picstory", "storyvideo", "routine", "feelstory") for p in ROOT.glob(f"assets/{d}/*/src.png")):
        d = src.parent; mark = d / "panels.json"; h = hashlib.sha1(src.read_bytes() + ((d / "pick").read_bytes() if (d / "pick").exists() else b"")).hexdigest()
        kind = "photo" if (d / "photo").exists() else "art"   # photorealistic storyboards get the natural-photo model
        want = {"src": h, "sharp": sharp, "model": kind}
        if mark.exists() and all(json.loads(mark.read_text()).get(k, "art" if k == "model" else None) == v for k, v in want.items()): continue
        if time.monotonic() - t0 > budget:   # out of time: the workflow saves what is done and starts again
            left += 1; continue
        for n, p in enumerate(panels(src), 1):
            if model is not None: p = model(p, kind)
            p.resize((1080, 1080), Image.LANCZOS).save(d / f"{n}.jpg", quality=93)
        mark.write_text(json.dumps(want)); done += 1; print("panels:", d.name, kind, "sharp" if sharp else "plain")
    print(done, "storyboard(s) processed,", left, "left")
    Path("panels_left.txt").write_text(str(left))


if __name__ == "__main__":
    main()

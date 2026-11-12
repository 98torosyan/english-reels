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
    if (len(cols), len(rows)) not in ((2, 3), (3, 2), (3, 3)): raise ValueError(f"{src}: expected a 2x3 or 3x3 grid, found {len(cols)}x{len(rows)}")
    for r in rows:
        for c in cols:
            p = im.crop((c[0] + 3, r[0] + 3, c[1] - 3, r[1] - 3)); w, h = p.size; s = min(w, h)
            yield p.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))


def main():
    sharp = "--sharp" in sys.argv
    model = None
    if sharp:
        import torch
        from spandrel import ModelLoader
        torch.set_num_threads(4)
        net = ModelLoader().load_from_file("weights/RealESRGAN_x4plus_anime_6B.pth").eval()
        def _up(p):
            x = torch.from_numpy(np.asarray(p).copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)
            with torch.inference_mode():
                y = net(x).clamp(0, 1)[0].permute(1, 2, 0).mul(255).round().byte().numpy()
            return Image.fromarray(y)
        model = _up
    done = 0
    for src in sorted(p for d in ("picstory", "storyvideo", "routine") for p in ROOT.glob(f"assets/{d}/*/src.png")):
        d = src.parent; mark = d / "panels.json"; h = hashlib.sha1(src.read_bytes()).hexdigest()
        if mark.exists() and json.loads(mark.read_text()).get("src") == h and json.loads(mark.read_text()).get("sharp") == sharp: continue
        for n, p in enumerate(panels(src), 1):
            if model is not None: p = model(p)
            p.resize((1080, 1080), Image.LANCZOS).save(d / f"{n}.jpg", quality=93)
        mark.write_text(json.dumps({"src": h, "sharp": sharp})); done += 1; print("panels:", d.name, "sharp" if sharp else "plain")
    print(done, "storyboard(s) processed")


if __name__ == "__main__":
    main()

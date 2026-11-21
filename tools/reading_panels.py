"""A reading's 6-scene sheet -> six 4K pictures assets/reading/<id>/1.jpg … 6.jpg (cut at the white gutters, sharpened
with Real-ESRGAN half and half with Lanczos, colours brought together), so the picture can change with the text.
Usage: python tools/reading_panels.py <reading-id> <sheet.png>"""
import shutil, sys
from pathlib import Path
import numpy as np, torch
from PIL import Image
from spandrel import ModelLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from upscale_panels import panels, harmonise   # noqa: E402


def keep_shape(sheet):
    """Cut the six-panel grid (3 × 2 or 2 × 3) at its white gutters keeping each panel's own shape (wide panels stay wide: the reel shows
    a wide 1080 × 760 picture, so nothing important is cropped away). None when the gutters are not clear."""
    im = Image.open(sheet).convert("RGB"); W, H = im.size; white = np.asarray(im).min(axis=2) > 232

    def cuts(line, n, k=None):
        idx = np.where(line > 0.9)[0]; runs = []
        for i in idx:
            if runs and i == runs[-1][1] + 1: runs[-1][1] = i
            else: runs.append([i, i])
        runs = [r for r in runs if 0 < r[0] and r[1] < n - 1]
        if k is not None and len(runs) != k - 1: return None
        edges = [0] + [x for r in runs for x in (r[0], r[1] + 1)] + [n]
        return [(edges[j], edges[j + 1]) for j in range(0, len(edges), 2)]
    xs, ys = cuts(white.mean(axis=0), W), cuts(white.mean(axis=1), H)   # 3 × 2 or 2 × 3
    if not xs or not ys or len(xs) * len(ys) != 6: return None
    return [im.crop((x0 + 2, y0 + 2, x1 - 2, y1 - 2)) for y0, y1 in ys for x0, x1 in xs]


def main():
    rid, sheet = sys.argv[1], Path(sys.argv[2])
    dest = ROOT / "assets" / "reading" / rid; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sheet, dest / "sheet.png")
    torch.set_num_threads(int(__import__("os").environ.get("THREADS", "2")))
    net = ModelLoader().load_from_file(str(ROOT / "weights" / "realesr-animevideov3.pth")).eval()
    ps = keep_shape(dest / "sheet.png") or list(panels(dest / "sheet.png"))
    if len(ps) != 6:   # gutters not found (a snowy or very light picture): cut the 3 × 2 grid evenly, a little inside each cell
        im = Image.open(dest / "sheet.png").convert("RGB"); W, H = im.size; cw, ch = W / 3, H / 2; m = 0.02
        ps = [im.crop((round(c * cw + cw * m), round(r * ch + ch * m), round((c + 1) * cw - cw * m), round((r + 1) * ch - ch * m)))
              for r in range(2) for c in range(3)]
        print(rid, "even grid cut")

    def up(p):
        x = torch.from_numpy(np.asarray(p.convert("RGB")).copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)
        with torch.inference_mode():
            y = net(x).clamp(0, 1)[0].permute(1, 2, 0).mul(255).round().byte().numpy()
        return Image.fromarray(y)

    out = []
    for p in ps:
        size = (2160, round(2160 * p.height / p.width))
        a = up(p).resize(size, Image.LANCZOS)
        out.append(Image.blend(a, p.convert("RGB").resize(size, Image.LANCZOS), 0.35))
    for k, a in enumerate(harmonise(out, .5), 1):
        a.save(dest / f"{k}.jpg", quality=93)
    print(rid, "6 pictures")


if __name__ == "__main__":
    main()

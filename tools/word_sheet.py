"""Cut a word-picture sheet (boxes with thin grey borders on white), drop any printed labels, remove the white background.
Usage: python tools/word_sheet.py <list-id> <sheet image> [keep order, e.g. 1 2 3 4 5 6 7 10 11 12]"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]


def boxes(im):
    a = np.asarray(im.convert("RGB")).astype(int); dark = a.min(axis=2) < 225
    def segs(v, n):
        gut = v < 3; out, s = [], None
        for i in range(n):
            if not gut[i] and s is None: s = i
            if gut[i] and s is not None: out.append((s, i)); s = None
        if s is not None: out.append((s, n))
        return [x for x in out if x[1] - x[0] > 100]
    rows = segs(dark.sum(axis=1), a.shape[0]); cols = segs(dark.sum(axis=0), a.shape[1])
    return [(c[0], r[0], c[1], r[1]) for r in rows for c in cols]


def clean(cell):
    w, h = cell.size; cell = cell.crop((8, 8, w - 8, h - 8)); w, h = cell.size
    a = np.asarray(cell.convert("RGB")).astype(int)
    bgish = (a.min(axis=2) > 230) & (a.max(axis=2) - a.min(axis=2) < 22)
    lab, _ = ndimage.label(bgish)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = ~np.isin(lab, list(edge))
    # printed labels: small blobs lying entirely in the top or bottom band
    fl, n = ndimage.label(ndimage.binary_dilation(fg, iterations=1))
    for i, sl in enumerate(ndimage.find_objects(fl), 1):
        y0, y1 = sl[0].start, sl[0].stop
        if (y1 - y0) < 0.12 * h and (y1 < 0.24 * h or y0 > 0.76 * h):
            fg[fl == i] = False
    alpha = Image.fromarray((fg * 255).astype("uint8")).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    out = cell.convert("RGBA"); out.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    if box: out = out.crop(box)
    out = out.resize((out.width * 2, out.height * 2), Image.LANCZOS); out.thumbnail((240, 240), Image.LANCZOS)
    return out


def main():
    lid, sheet = sys.argv[1], Path(sys.argv[2]); keep = [int(x) for x in sys.argv[3:]]
    im = Image.open(sheet).convert("RGB"); bx = boxes(im)
    if keep: bx = [bx[k - 1] for k in keep]
    if len(bx) != 10: raise SystemExit(f"{lid}: found {len(bx)} boxes, expected 10")
    out = ROOT / "assets/words10_art" / lid; out.mkdir(parents=True, exist_ok=True)
    im.save(out / "sheet.jpg", quality=92)
    for n, b in enumerate(bx): clean(im.crop(b)).save(out / f"{n}.png")
    print(lid, "ok")


if __name__ == "__main__":
    main()

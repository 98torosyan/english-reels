"""10 words: cut a 2x5 sheet of word pictures (one object per panel, white background), remove the white background,
and save assets/words10_art/<list-id>/<n>.png (transparent, 240 px) in word order.
Usage: python tools/word_pictures.py <list-id> <sheet.png>"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from upscale_panels import panels  # noqa: E402


def cut_out(im):
    """White background -> transparent, with a soft edge; then crop to the object."""
    a = np.asarray(im.convert("RGB")).astype(int)
    white = (a.min(axis=2) > 236) & (a.max(axis=2) - a.min(axis=2) < 14)
    alpha = Image.fromarray(np.where(white, 0, 255).astype("uint8")).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    out = im.convert("RGBA"); out.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    if box: out = out.crop(box)
    out.thumbnail((240, 240), Image.LANCZOS)
    return out


def main():
    list_id, sheet = sys.argv[1], Path(sys.argv[2])
    out = ROOT / "assets" / "words10_art" / list_id; out.mkdir(parents=True, exist_ok=True)
    ps = list(panels(sheet))
    if len(ps) != 10: raise SystemExit(f"expected 10 pictures, found {len(ps)}")
    for n, p in enumerate(ps):
        cut_out(p).save(out / f"{n}.png")
    print("saved", len(ps), "pictures to", out)


if __name__ == "__main__":
    main()

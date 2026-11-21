"""Living pictures: a still picture gets a soft, real-looking depth movement (near things move a little more than far
ones, like a slow breath of the camera), so the reading's pictures feel alive without inventing anything new.
Depth comes from Depth Anything V2 Small (Apache-2.0). The movement is a smooth loop, so any length works.
Writes <out>/p<k>/0000.jpg … and <out>/live.json {frames, fps}.
Usage: python tools/living_pictures.py <reading-id> <out-dir> [--frames 120 --fps 15 --amp 0.012]"""
import argparse, json, math
from pathlib import Path
import cv2, numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def depth_of(pipe, img):
    d = np.asarray(pipe(Image.fromarray(img[:, :, ::-1]).resize((518, 518)))["depth"], dtype=np.float32)
    d = cv2.resize(d, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)
    d = (d - d.min()) / max(1e-6, d.max() - d.min())          # 1 = near
    return cv2.GaussianBlur(d, (0, 0), img.shape[1] / 180)     # soft edges: no tearing around people


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("id"); ap.add_argument("out")
    ap.add_argument("--frames", type=int, default=120); ap.add_argument("--fps", type=int, default=15); ap.add_argument("--amp", type=float, default=0.012)
    a = ap.parse_args()
    from transformers import pipeline
    pipe = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device="cpu")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pics = []; k = 1
    while (ROOT / "assets" / "reading" / a.id / f"{k}.jpg").exists():
        pics.append(ROOT / "assets" / "reading" / a.id / f"{k}.jpg"); k += 1
    for k, src in enumerate(pics, 1):
        img = cv2.imread(str(src)); H, W = img.shape[:2]; d = depth_of(pipe, img) - 0.5
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        dest = out / f"p{k}"; dest.mkdir(exist_ok=True)
        for f in range(a.frames):
            ph = 2 * math.pi * f / a.frames
            dx, dy = a.amp * W * math.sin(ph), 0.45 * a.amp * H * math.sin(2 * ph)   # a slow figure-of-eight
            z = 1.012 + 0.006 * math.sin(ph)                                         # and a little breath
            mx = (xs - W / 2) / z + W / 2 - d * dx; my = (ys - H / 2) / z + H / 2 - d * dy
            frame = cv2.remap(img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
            cv2.imwrite(str(dest / f"{f:04d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(a.id, f"p{k}", a.frames, "frames")
    (out / "live.json").write_text(json.dumps({"frames": a.frames, "fps": a.fps, "count": len(pics)}))


if __name__ == "__main__":
    main()

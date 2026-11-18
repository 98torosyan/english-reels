"""Depth maps for the 3D-parallax reels: for every assets/talk/<id>/<n>.jpg without an up-to-date <n>-depth.png, estimate
depth (Depth Anything V2 Small, Apache-2.0) and save it as an 8-bit greyscale picture (white = near). Runs in the
"Sharpen panels" workflow right after the panels are cut. Usage: python tools/make_depth.py"""
import hashlib, json
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]


def main():
    todo = []
    for pic in sorted(ROOT.glob("assets/talk/*/[0-9].jpg")):
        dep = pic.with_name(f"{pic.stem}-depth.png"); mark = pic.with_name(f"{pic.stem}-depth.json")
        h = hashlib.sha1(pic.read_bytes()).hexdigest()
        if dep.exists() and mark.exists() and json.loads(mark.read_text()).get("src") == h: continue
        todo.append((pic, dep, mark, h))
    if not todo: print("depth: nothing to do"); return
    from transformers import pipeline
    est = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")
    for pic, dep, mark, h in todo:
        im = Image.open(pic).convert("RGB")
        d = est(im)["depth"].convert("L").resize(im.size, Image.BICUBIC)
        d = d.filter(ImageFilter.GaussianBlur(radius=max(2, im.size[0] // 300)))   # soft edges: no tearing around outlines
        d.save(dep); mark.write_text(json.dumps({"src": h})); print("depth:", pic.relative_to(ROOT))


if __name__ == "__main__":
    main()

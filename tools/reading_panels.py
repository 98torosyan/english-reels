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


def main():
    rid, sheet = sys.argv[1], Path(sys.argv[2])
    dest = ROOT / "assets" / "reading" / rid; dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sheet, dest / "sheet.png")
    torch.set_num_threads(int(__import__("os").environ.get("THREADS", "2")))
    net = ModelLoader().load_from_file(str(ROOT / "weights" / "realesr-animevideov3.pth")).eval()
    ps = list(panels(dest / "sheet.png"))
    if len(ps) != 6: raise SystemExit(f"{rid}: found {len(ps)} pictures, expected 6")

    def up(p):
        x = torch.from_numpy(np.asarray(p.convert("RGB")).copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)
        with torch.inference_mode():
            y = net(x).clamp(0, 1)[0].permute(1, 2, 0).mul(255).round().byte().numpy()
        return Image.fromarray(y)

    out = []
    for p in ps:
        a = up(p).resize((2160, 2160), Image.LANCZOS)
        out.append(Image.blend(a, p.convert("RGB").resize((2160, 2160), Image.LANCZOS), 0.35))
    for k, a in enumerate(harmonise(out, .5), 1):
        a.save(dest / f"{k}.jpg", quality=93)
    print(rid, "6 pictures")


if __name__ == "__main__":
    main()

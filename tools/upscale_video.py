"""Sharpen a short painted clip to 4K width, frame by frame: Real-ESRGAN (compact model) blended half and half with a
plain Lanczos resize, so brushstrokes stay painterly instead of looking flat.
With --fps 48 the clip is first made twice as smooth, so slowed-down scenes still glide: with RIFE
(rife-ncnn-vulkan, MIT; set RIFE=/path/to/rife-ncnn-vulkan-folder) when available, else ffmpeg's motion interpolation. Usage: python tools/upscale_video.py in.mp4 out.mp4 [--size 1872] [--fps 48]"""
import os, subprocess, sys
from pathlib import Path
import numpy as np, torch
from PIL import Image
from spandrel import ModelLoader


def main():
    src, dst = sys.argv[1], sys.argv[2]
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 1872
    smooth = sys.argv[sys.argv.index("--fps") + 1] if "--fps" in sys.argv else None
    torch.set_num_threads(int(__import__("os").environ.get("THREADS", "4")))
    net = ModelLoader().load_from_file("weights/realesr-animevideov3.pth").eval()
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                            "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h, fps = int(probe[0]), int(probe[1]), probe[2]
    inp = ["-i", src]
    vf = ["-vf", f"minterpolate=fps={smooth}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"] if smooth else []
    rife = os.environ.get("RIFE")
    if smooth and rife and Path(rife, "rife-ncnn-vulkan").exists():
        import tempfile
        tmp = Path(tempfile.mkdtemp()); (tmp / "in").mkdir(); (tmp / "out").mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-i", src, str(tmp / "in" / "%06d.png")], check=True)
        n = len(list((tmp / "in").glob("*.png"))); num, den = (fps.split("/") + ["1"])[:2]
        target = round(n * float(smooth) / (float(num) / float(den)))
        r = subprocess.run([str(Path(rife, "rife-ncnn-vulkan")), "-i", str(tmp / "in"), "-o", str(tmp / "out"), "-m", str(Path(rife, "rife-v4.6")),
                            "-n", str(target), "-j", "2:2:2"], capture_output=True, text=True)
        if r.returncode == 0 and len(list((tmp / "out").glob("*.png"))) == target:
            inp, vf = ["-framerate", smooth, "-i", str(tmp / "out" / "%08d.png")], []
            print(f"smooth: RIFE {n} -> {target} frames", flush=True)
        else:
            print("RIFE unavailable, using ffmpeg interpolation:", r.stderr[-300:], flush=True)
    if smooth: fps = smooth
    W, H = size, round(size * h / w / 2) * 2
    dec = subprocess.Popen(["ffmpeg", "-v", "error", *inp, *vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", fps, "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
    n = 0
    while True:
        buf = dec.stdout.read(w * h * 3)
        if len(buf) < w * h * 3: break
        p = Image.fromarray(np.frombuffer(buf, np.uint8).reshape(h, w, 3))
        x = torch.from_numpy(np.asarray(p).copy()).permute(2, 0, 1).float().div(255).unsqueeze(0)
        with torch.inference_mode():
            y = net(x).clamp(0, 1)[0].permute(1, 2, 0).mul(255).round().byte().numpy()
        a = Image.fromarray(y).resize((W, H), Image.LANCZOS)
        out = Image.blend(a, p.resize((W, H), Image.LANCZOS), 0.45)
        enc.stdin.write(np.asarray(out).tobytes()); n += 1
        if n % 24 == 0: print(n, flush=True)
    enc.stdin.close(); enc.wait(); dec.wait()
    if enc.returncode: raise SystemExit("encode failed")
    print("frames", n)


if __name__ == "__main__":
    main()

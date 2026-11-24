"""An Instagram Story video for a reel: the picture full screen with a slow camera move, a gold book frame with the
title and a one-line hook fading in, and the reel's music. 1080×1920 (Instagram's Story size), 12 s.
Usage: python tools/story_card.py <spec.json> <out.mp4>
spec: {"picture": "x.jpg", "title": "...", "author": "O. Henry", "hook": "line one\\nline two", "music": "music/new/x.m4a"}"""
import json, subprocess, sys, tempfile
from pathlib import Path
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
OW, OH, FPS, T = 1080, 1920, 30, 12
MOTION = {"mila-b": "float", "ani-c": "rise", "mila-c": "pull"}   # other styles: push-in


def main():
    spec_path, out = Path(sys.argv[1]), Path(sys.argv[2]); spec = json.loads(spec_path.read_text(encoding="utf-8"))
    work = Path(tempfile.mkdtemp(prefix="storycard-"))
    subprocess.run(["node", str(ROOT / "reels" / "story_card.js"), str(spec_path), str(work)], check=True)
    im = cv2.imread(str(work / "bg.png")); H, W = im.shape[:2]; N = T * FPS
    music = ROOT / spec.get("music", "music/new/piano-glow.m4a")
    tmp = out.with_name(out.stem + ".part.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
        "-loop", "1", "-i", str(work / "overlay.png"), "-i", str(music), "-filter_complex",
        f"[1:v]format=rgba,scale={OW}:{OH}:flags=lanczos,fade=t=in:st=0.7:d=1.4:alpha=1,trim=0:{T}[o];"
        f"[0:v][o]overlay=0:0:shortest=1,fade=t=in:st=0:d=0.6,fade=t=out:st={T - 0.8}:d=0.8,format=yuv420p[v];"
        f"[2:a]atrim=0:{T},afade=t=in:d=1,afade=t=out:st={T - 1.5}:d=1.5,loudnorm=I=-15:TP=-1.5[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-profile:v", "high", "-level", "4.1",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", str(T), str(tmp)], stdin=subprocess.PIPE)
    pic = str(spec.get("picture", "")); auto = "mila-c" if "assets/reading/mila-" in pic else "ani-b" if "assets/reading/" in pic else ""
    motion = spec.get("motion") or MOTION.get(spec.get("style") or auto, "push")
    for i in range(N):   # eased, sub-pixel camera move (no shaking); default: slow push-in
        t = i / (N - 1); e = t * t * (3 - 2 * t); dy = 0.0
        if motion == "rise": z = 1.06; dy = 46 * (1 - 2 * e)                               # the picture slowly rises
        elif motion == "pull": z = 1.08 - 0.07 * e                                          # slow pull-back
        elif motion == "float": z = 1.035 + 0.02 * e; dy = 12 * np.sin(2 * np.pi * t)       # gentle bob
        else: z = 1.0 + 0.07 * e
        s = OW / W * z
        M = np.array([[s, 0, OW / 2 - s * W / 2], [0, s, OH * 0.45 - s * H * 0.45 + dy]])
        p.stdin.write(cv2.warpAffine(im, M, (OW, OH), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT).tobytes())
    p.stdin.close()
    if p.wait(): raise SystemExit("ffmpeg failed")
    tmp.replace(out); print(out)


if __name__ == "__main__":
    main()

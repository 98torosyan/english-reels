"""Guard for animated clips: finds sudden jumps (a face or object that suddenly changes, a hidden cut) with
PySceneDetect (BSD-3) and keeps only the longest clean stretch, so a clip that starts well and then goes wrong is
still usable. Also drops a stuck first frame. Writes the cleaned clip and prints what it did.
Usage: python tools/clip_guard.py in.mp4 out.mp4"""
import json, subprocess, sys


def duration(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True, check=True).stdout)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    from scenedetect import detect, ContentDetector
    total = duration(src)
    cuts = [(s[0].seconds if hasattr(s[0], "seconds") else s[0].get_seconds()) for s in detect(src, ContentDetector(threshold=22.0, min_scene_len=8))][1:]
    edges = [0.0] + cuts + [total]
    spans = sorted(((b - a, a, b) for a, b in zip(edges, edges[1:])), reverse=True)
    length, a, b = spans[0]
    if not cuts or length >= total - 0.05:
        subprocess.run(["cp", src, dst], check=True); print(json.dumps({"clip": src, "cuts": [], "kept": [0, round(total, 2)]})); return
    if length < 2.0: raise SystemExit(f"{src}: no clean stretch of 2 s (jumps at {cuts}); please make this clip again")
    a, b = a + 0.04, b - 0.04   # stay clear of the jump frames
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, "-an",
                    "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p", dst], check=True)
    print(json.dumps({"clip": src, "cuts": [round(c, 2) for c in cuts], "kept": [round(a, 2), round(b, 2)]}))


if __name__ == "__main__":
    main()

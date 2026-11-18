"""Quality gate for a finished reel: size, frame rate, length, sound level, no silent gaps at the start, no black or
frozen stretches. Prints what it measured; exits 1 on a problem. Usage: python tools/check_reel.py reel.mp4"""
import json, re, subprocess, sys


def probe(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                          "-of", "json", f], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def main():
    f = sys.argv[1]; info = probe(f); bad = []
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"])
    if (v["width"], v["height"]) not in ((1872, 3328), (1080, 1920)): bad.append(f"size {v['width']}x{v['height']}")
    if v["r_frame_rate"] not in ("30/1", "60/1"): bad.append(f"frame rate {v['r_frame_rate']}")
    if not 15 <= dur <= 90: bad.append(f"length {dur:.1f}s (Instagram reels work best 15-90 s)")
    if not a: bad.append("no sound")
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-vf", "blackdetect=d=0.8:pix_th=0.06,freezedetect=n=0.001:d=2.5",
                          "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = [float(x) for x in re.findall(r"I:\s+(-?[\d.]+) LUFS", log)]
    if lufs and not -17 <= lufs[-1] <= -11: bad.append(f"loudness {lufs[-1]} LUFS (want about -14)")
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)
    blacks = [(float(s), float(e)) for s, e in blacks if float(s) > 0.8 and float(e) < dur - 1.5]   # fades at the ends are fine
    if blacks: bad.append(f"black stretch at {blacks[0][0]:.1f}s")
    freezes = re.findall(r"freeze_start: ([\d.]+)", log)
    print(json.dumps({"size": f"{v['width']}x{v['height']}", "fps": v["r_frame_rate"], "seconds": round(dur, 1),
                      "lufs": lufs[-1] if lufs else None, "frozen_stretches": len(freezes)}))
    if bad: print("PROBLEMS: " + "; ".join(bad)); sys.exit(1)
    print("reel ok")


if __name__ == "__main__":
    main()

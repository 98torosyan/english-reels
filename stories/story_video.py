"""Turn a word / phrase of the day story image into a short story video:
gentle slow zoom, the word and the example read in a British voice, soft music underneath.
Usage: python stories/story_video.py <story-id> [...]   (images come from stories/make_stories.js)"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples" / "stories").resolve()
FF = str(ROOT / "node_modules/ffmpeg-static/ffmpeg")
TRACKS = sorted((ROOT / "music").glob("*.m4a"))


def render(sid: str) -> Path:
    img = OUT / f"story-{sid}.jpg"
    if not img.exists():
        subprocess.run(["node", "stories/make_stories.js", sid], cwd=ROOT, check=True)
    vdir = ROOT / "assets" / "stories" / sid
    t, e = (json.loads((vdir / f"{k}.json").read_text()) for k in ("t", "e"))
    t_at = 1.0                                   # the word, after the card settles
    e_at = t_at + (t["end"] - t["start"]) + 1.1  # calm pause, then the example
    total = max(8.0, e_at + (e["end"] - e["start"]) + 2.4)
    music = TRACKS[sum(map(ord, sid)) % len(TRACKS)]
    out = OUT / f"story-{sid}.mp4"
    frames = int(total * 30)
    vf = (f"[0:v]scale=2160:3840,zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30,"
          f"fade=t=in:st=0:d=0.5,format=yuv420p[v]")
    def clip(i, j, at):
        a = max(0, j["start"] - 0.05); ms = int((at - (j["start"] - a)) * 1000)
        return f"[{i}:a]aresample=48000,atrim={a:.3f}:{j['end'] + 0.3:.3f},asetpts=PTS-STARTPTS,adelay={ms}|{ms}[c{i}]"
    af = (f"{clip(1, t, t_at)};{clip(2, e, e_at)};[c1][c2]amix=inputs=2:normalize=0,apad,asplit=2[voice][sc];"
          f"[3:a]aresample=48000,volume=0.2,afade=t=in:d=1,afade=t=out:st={total - 1.4:.2f}:d=1.4[m];"
          f"[m][sc]sidechaincompress=threshold=0.02:ratio=5:attack=25:release=450[md];"
          f"[voice][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-i", str(img),
           "-i", str(vdir / "t.mp3"), "-i", str(vdir / "e.mp3"), "-stream_loop", "-1", "-i", str(music),
           "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(f"{out.name}: {total:.1f}s, music {music.stem}")
    return out


if __name__ == "__main__":
    for s in sys.argv[1:]:
        render(s)

"""A painted story that moves: six short motion clips (assets/motion/<id>/out-<n>.mp4, sharpened to 4K width) melt into a
warm paper page; one calm narrator tells the story and each sentence appears under the picture while it is spoken.
Text and voice come from reels/data/talk.json (kind "story"); voice clips from assets/talk/<id>.
Usage: python reels/render_motion.py <id>"""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = (ROOT / ".." / ".." / "outputs" / "english-reels-samples").resolve()
W, H, PIC_H, FPS = 1872, 3328, 2520, 30
PAPER = (243, 234, 219)
TEXT_Y = 2320            # top of the text band (in output pixels)


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr[-3000:])
    return r.stdout


def timeline(t):
    lines, scenes, at = [], [], 0.7
    vdir = ROOT / "assets" / "talk" / t["id"]; n = 0
    for s, sc in enumerate(t["scenes"]):
        if s: at += 0.75
        s0 = at
        for _, text in sc["lines"]:
            j = json.loads((vdir / f"v{n}.json").read_text())
            assert j["text"] == text.replace("[", "").replace("]", ""), f"voice {n} is for another text"
            a, b = j["words"][0][0], j["words"][-1][1]
            lines.append({"n": n, "text": text, "scene": s, "at": at, "end": at + (b - a), "from": a, "to": b, "title": n == 0})
            at += (b - a) + (0.85 if n == 0 else 0.5); n += 1
        scenes.append(s0)
    total = lines[-1]["end"] + 2.6
    return lines, scenes, total


def mask(path, pic_h=PIC_H, fade=760):
    y = np.arange(pic_h)[:, None].astype(float)
    def ss(e0, e1, v):
        x = np.clip((v - e0) / (e1 - e0), 0, 1); return x * x * (3 - 2 * x)
    m = ss(0, 140, y) * (1 - ss(pic_h - fade, pic_h, y))
    x = np.arange(W)[None, :].astype(float)
    m = m * (0.86 + 0.14 * ss(0, 90, x) * ss(0, 90, W - x))   # a breath of softness at the sides too
    Image.fromarray((m * 255).astype(np.uint8), "L").save(path)


def text_pngs(lines, work, dark=False):
    """Each sentence as a transparent PNG, set by the browser (best type rendering): sentences in Playfair Display italic
    on warm ivory, the title in gold with a small ornament under it."""
    script = r"""
const { chromium } = require('playwright-core'); const fs = require('fs');
(async () => {
  const [lines, dir, root, dark] = JSON.parse(fs.readFileSync(0, 'utf8'));
  const b = await chromium.launch({ executablePath: process.env.CHROME_PATH });
  const p = await b.newPage({ viewport: { width: 1080, height: 520 }, deviceScaleFactor: 26 / 15 });
  const f = (s) => 'data:font/woff2;base64,' + fs.readFileSync(`${root}/node_modules/@fontsource-variable/playfair-display/files/playfair-display-latin-wght-${s}.woff2`).toString('base64');
  await p.setContent(`<!doctype html><style>@font-face{font-family:P;src:url(${f('normal')})}@font-face{font-family:P;font-style:italic;src:url(${f('italic')})}
   html,body{margin:0;background:transparent}#t{width:1080px;height:520px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
   #s{max-width:920px;font:italic 400 66px/1.36 P;color:#3A2A1F;letter-spacing:.2px;text-shadow:0 0 18px rgba(243,234,219,.9),0 0 4px rgba(243,234,219,.8)}
   #s em{font-style:normal;color:#9A6B1F}
   #h{display:none;font:italic 600 104px/1.1 P;letter-spacing:1px;padding:0 20px;
      background:linear-gradient(180deg,#FBE3A1 0%,#E9C46A 45%,#B98A35 100%);-webkit-background-clip:text;background-clip:text;color:transparent;
      filter:drop-shadow(0 3px 10px rgba(0,0,0,.55))}
   #o{display:none;align-items:center;justify-content:center;gap:20px;margin-top:22px}
   #o i{display:block;width:140px;height:2px;background:linear-gradient(90deg,transparent,#E9C46A)}#o i:last-child{background:linear-gradient(90deg,#E9C46A,transparent)}
   #o b{width:14px;height:14px;background:#E9C46A;transform:rotate(45deg)}
   #t.title #s{display:none}#t.title #h{display:block}#t.title #o{display:flex}
   body.dark #s{color:#F6EBD9;text-shadow:0 2px 26px rgba(10,7,5,.95),0 0 6px rgba(10,7,5,.85)}
   body.dark #s em{color:#E9C46A}</style><div id=t><div id=h></div><div id=o><i></i><b></b><i></i></div><div id=s></div></div>`);
  if (dark) await p.evaluate(() => document.body.classList.add('dark'));
  await p.evaluate(() => document.fonts.load('italic 400 66px P').then(() => document.fonts.load('italic 600 104px P')).then(() => document.fonts.load('400 66px P')));
  for (const l of lines) {
    await p.evaluate(([txt, title]) => {
      const t = document.getElementById('t'); t.className = title ? 'title' : '';
      if (title) { document.getElementById('h').textContent = txt; return; }
      const s = document.getElementById('s'); s.textContent = '';
      let open = true; txt = txt.replace(/"/g, () => (open = !open) ? '\u201D' : '\u201C').replace(/'/g, '\u2019');
      // [words] in the story text are the phrase to notice: shown in gold, spoken normally
      txt.split(/(\[[^\]]+\])/).forEach((part) => { if (!part) return;
        if (part.startsWith('[')) { const e = document.createElement('em'); e.textContent = part.slice(1, -1); s.append(e); } else s.append(part); });
    }, [l.title ? l.text.replace(/[.\[\]]/g, '') : l.text, l.title]);
    await p.screenshot({ path: `${dir}/line${l.n}.png`, omitBackground: true });
  }
  await b.close();
})();"""
    js = ROOT / ".render-work" / "motion-text.js"; js.parent.mkdir(exist_ok=True); js.write_text(script)
    subprocess.run(["node", str(js)], input=json.dumps([lines, str(work), str(ROOT), dark]), text=True, check=True, cwd=ROOT)


def main():
    sid = sys.argv[1]
    t = next(x for x in json.loads((ROOT / "reels/data/talk.json").read_text())["talks"] if x["id"] == sid)
    lines, scenes, total = timeline(t)
    mdir = ROOT / "assets" / "motion" / sid; XF = 1.0
    first = mdir / f"out-{sid}-1.mp4"
    if not first.exists(): first = mdir / "out-1.mp4"
    cw, ch = map(int, run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(first)]).split(","))
    tall = ch / cw > 1.2                     # vertical clips fill the screen; square ones sit on the page
    pic_h = round(W * ch / cw / 2) * 2 if tall else PIC_H
    text_y = pic_h - 570 if tall else TEXT_Y
    paper = tuple(int(t["paper"][i:i + 2], 16) for i in (1, 3, 5)) if t.get("paper") else PAPER
    dark = sum(paper) < 384
    work = Path(tempfile.mkdtemp(prefix=f"motion-{sid}-")); mask(work / "mask.png", pic_h, 900 if tall else 760); text_pngs(lines, work, dark)
    # each picture runs from its scene start (minus half a cross-fade) to the next one; clips are slowed gently if needed
    starts = [0.0] + [s - 0.55 for s in scenes[1:]]
    ends = starts[1:] + [total]
    args = ["ffmpeg", "-v", "error", "-y"]; fc = []
    fit = f"scale={W}:{pic_h}:flags=lanczos," if tall else f"scale={PIC_H}:{PIC_H}:flags=lanczos,crop={W}:{PIC_H},"
    for k in range(len(scenes)):
        need = ends[k] - starts[k] + (XF if k < len(scenes) - 1 else 0)
        clip = mdir / f"out-{sid}-{k + 1}.mp4"
        if not clip.exists(): clip = mdir / f"out-{k + 1}.mp4"
        dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)]))
        f = max(1.0, need / (dur - 0.1))
        args += ["-i", str(clip)]
        fc.append(f"[{k}:v]setpts={f:.4f}*PTS,framerate=fps={FPS},{fit}trim=0:{need:.3f},setpts=PTS-STARTPTS,format=yuv420p[c{k}]")
    prev, off = "c0", 0.0
    for k in range(1, len(scenes)):
        off = starts[k]
        fc.append(f"[{prev}][c{k}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]"); prev = f"x{k}"
    nv = len(scenes)
    args += ["-loop", "1", "-i", str(work / "mask.png")]; mi = nv
    fc.append(f"[{mi}:v]format=gray,trim=0:{total:.3f}[m]")
    fc.append(f"[{prev}]format=rgba,trim=0:{total:.3f}[pv];[pv][m]alphamerge[pa]")
    fc.append(f"color=c=0x{''.join(f'{c:02X}' for c in paper)}:s={W}x{H}:r={FPS}:d={total:.3f}[bg];[bg][pa]overlay=0:0:shortest=1[v0]")
    cur = "v0"
    for i, l in enumerate(lines):
        idx = nv + 1 + i
        # one sentence on screen at a time: the old one fades out and the new one fades in, back to back, in the pause between them
        mid = lambda k: (lines[k - 1]["end"] + lines[k]["at"]) / 2
        a = max(0, l["at"] - 0.3) if i == 0 else mid(i)
        b = mid(i + 1) if i + 1 < len(lines) else total
        args += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(work / f"line{l['n']}.png")]
        fade_out = f",fade=t=out:st={b - 0.26:.3f}:d=0.26:alpha=1" if i + 1 < len(lines) else f",fade=t=out:st={total - 1.2:.3f}:d=1.0:alpha=1"
        fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={a:.3f}:d=0.3:alpha=1{fade_out}[t{i}]")
        fc.append(f"[{cur}][t{i}]overlay=0:{text_y}:enable='between(t,{a:.3f},{b:.3f})'[v{i + 1}]"); cur = f"v{i + 1}"
    fc.append(f"[{cur}]fade=t=in:st=0:d=0.6,format=yuv420p[vout]")
    # sound: the narrator, and soft music under it
    ai = nv + 1 + len(lines); vdir = ROOT / "assets" / "talk" / sid; chains = []
    for i, l in enumerate(lines):
        args += ["-i", str(vdir / f"v{l['n']}.mp3")]
        fr = max(0, l["from"] - 0.06); ms = int(round((l["at"] - (l["from"] - fr)) * 1000))
        chains.append(f"[{ai + i}:a]aresample=48000,atrim={fr:.3f}:{l['to'] + 0.35:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={l['to'] - fr + 0.15:.3f}:d=0.2,adelay={ms}|{ms}[a{i}]")
    mus = ai + len(lines)
    args += ["-stream_loop", "-1", "-i", str(ROOT / "music" / t["music"])]
    fc += chains
    fc.append(f"{''.join(f'[a{i}]' for i in range(len(lines)))}amix=inputs={len(lines)}:normalize=0,apad=whole_dur={total:.3f}[voice]")
    fc.append(f"[{mus}:a]aresample=48000,atrim=0:{total:.3f},volume=0.20,afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.3f}:d=2.5[mus]")
    fc.append("[voice][mus]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[aout]")
    OUT.mkdir(parents=True, exist_ok=True); dst = OUT / f"motion-{sid}.mp4"; tmp = OUT / f".motion-{sid}.tmp.mp4"
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M", "-profile:v", "high", "-level", "5.1",
             "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)]
    run(args); tmp.rename(dst)
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{lines[0]['end'] + 0.2:.2f}", "-i", str(dst), "-frames:v", "1", "-q:v", "2", str(OUT / f"motion-{sid}-cover.jpg")])
    print("rendered", dst, f"{total:.1f}s")


if __name__ == "__main__":
    main()

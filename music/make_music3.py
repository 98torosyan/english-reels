"""Original background music played on real sampled instruments (FluidR3 GM SoundFont, MIT licence).
Each track is composed here (chords, accompaniment, a simple singable melody), rendered with FluidSynth,
then mastered (gentle EQ, compression, reverb, loudness) and saved as music/new/<name>.m4a (candidates: the renderer only uses music/*.m4a, so a track goes live once it is moved up).
Needs: apt install fluidsynth fluid-soundfont-gm; pip install pretty_midi numpy.
Usage: python music/make_music3.py [name ...]"""
import random, subprocess, sys, tempfile
from pathlib import Path

import pretty_midi as pm

HERE = Path(__file__).resolve().parent
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
MAJ = [0, 2, 4, 5, 7, 9, 11]; MIN = [0, 2, 3, 5, 7, 8, 10]
QUAL = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "sus2": [0, 2, 7], "add9": [0, 4, 7, 14]}


def chord(sym, key, scale):
    """Roman numeral in the track's scale: upper case = major triad, lower case = minor ('I', 'vi', 'VII')."""
    deg = ["I", "II", "III", "IV", "V", "VI", "VII"].index(sym.upper())
    return (key + scale[deg]) % 12, QUAL["m" if sym.islower() else ""]


def add(inst, pitch, start, dur, vel):
    inst.notes.append(pm.Note(velocity=int(max(1, min(127, vel))), pitch=int(pitch), start=start, end=start + dur))


def melody(inst, prog, key, scale, beat, bar, beats_per_bar, low, rng, vel=78, density=1.0):
    """AABA phrases over 2-bar cells: chord tones on strong beats, stepwise passing notes between, held phrase ends."""
    rhythms = [[1, .5, .5, 1, 1], [1.5, .5, 1, 1], [.5, .5, 1, 2], [1, 1, 2], [2, 1, 1], [1, .5, .5, 2]] if beats_per_bar == 4 else [[1, 1, 1], [2, 1], [1, .5, .5, 1], [3]]
    scale_notes = [p for p in range(low, low + 20) if (p - key) % 12 in scale]
    def cell(bar_i, seed_r):
        r = rng if seed_r is None else random.Random(seed_r)
        out = []; t = 0; last = None
        for b in range(2):
            root, ints = prog[(bar_i + b) % len(prog)]
            ct = [p for p in scale_notes if (p - root) % 12 in [i % 12 for i in ints]]
            rh = r.choice(rhythms) if density >= 1 or r.random() < density else [beats_per_bar]
            for k, d in enumerate(rh):
                if k == 0 or d >= 1:
                    cand = ct
                else:
                    cand = scale_notes
                if last is None: p = r.choice(cand[len(cand) // 3: 2 * len(cand) // 3] or cand)
                else: p = min(cand, key=lambda x: abs(x - last) + (0 if x != last else 1.5) + r.random() * 2.2)
                out.append((t, d, p)); last = p; t += d
        return out
    cells = {}
    n_bars = len(prog) * 2
    form = "AABA" * 4
    for c in range(n_bars // 2):
        name = form[c % len(form)]
        if name not in cells or c % 8 >= 6: cells[name] = cell(c * 2, None)
        for (t, d, p) in cells[name]:
            start = c * 2 * bar + t * beat
            add(inst, p, start, d * beat * .95, vel + rng.randint(-8, 6) + (6 if t == 0 else 0))


def arpeggio(inst, prog, beat, bar, bpb, octave, pattern, vel, rng, hold=1.0):
    for i, (root, ints) in enumerate(prog * 2):
        tones = sorted({octave + root + x for x in ints} | {octave + root + 12})
        for j, k in enumerate(pattern):
            if k is None: continue
            p = tones[k % len(tones)] + (12 if k >= len(tones) else 0)
            step = bar / len(pattern)
            add(inst, p, i * bar + j * step, step * (1 + hold), vel + rng.randint(-6, 4))


def block(inst, prog, bar, octave, vel, rng, hits=None):
    for i, (root, ints) in enumerate(prog * 2):
        for (off, dur) in (hits or [(0, 1.0)]):
            for x in ints[:4]:
                add(inst, octave + root + x, i * bar + off * bar, dur * bar * .98, vel + rng.randint(-5, 3))


def bass(inst, prog, bar, octave, vel, rng, pattern=((0, .5), (.5, .5))):
    for i, (root, _) in enumerate(prog * 2):
        for (off, dur) in pattern:
            p = octave + root + (7 if off == .5 and len(pattern) > 2 else 0)
            add(inst, p, i * bar + off * bar, dur * bar * .9, vel + rng.randint(-5, 3))


def drums(mid, prog_len, bar, beat, kind, vel=70, rng=None):
    d = pm.Instrument(program=0, is_drum=True)
    for i in range(prog_len * 2):
        s = i * bar
        if kind == "lofi":
            for t, n, v in ((0, 36, vel), (1.5, 36, vel - 15), (1, 37, vel - 10), (3, 37, vel - 10), (2.5, 36, vel - 20)):
                add(d, n, s + t * beat, .2, v)
            for k in range(8): add(d, 42, s + k * beat / 2 + (beat * .06 if k % 2 else 0), .1, vel - 25 + rng.randint(-6, 6))
        elif kind == "shaker":
            for k in range(8): add(d, 82, s + k * beat / 2, .1, vel - 30 + (10 if k % 2 == 0 else 0))
            add(d, 75, s + 2 * beat, .1, vel - 25)
        elif kind == "brush":
            for k in range(4): add(d, 42, s + k * beat, .1, vel - 35)
            add(d, 36, s, .2, vel - 20)
        elif kind == "bells":
            for k in range(8): add(d, 81, s + k * beat / 2, .1, vel - 40 + (8 if k % 2 == 0 else 0))
    mid.instruments.append(d)


def P(n): return pm.instrument_name_to_program(n)


TRACKS = {
    # name: (bpm, key, beats per bar, progression, builder)
    "piano-glow":     (72, 0, 4, ["I", "V", "vi", "IV"], "piano"),
    "nylon-garden":   (84, 7, 4, ["I", "vi", "IV", "V"], "guitar"),
    "snow-celesta":   (92, 5, 4, ["I", "vi", "ii", "V"], "xmas"),
    "jingle-lights":  (108, 2, 4, ["I", "IV", "I", "V"], "xmas2"),
    "marimba-sunrise": (100, 2, 4, ["I", "V", "vi", "IV"], "marimba"),
    "lofi-desk":      (78, 9, 4, ["i", "VI", "III", "VII"], "lofi"),
    "evening-strings": (66, 3, 4, ["I", "iii", "vi", "IV"], "strings"),
    "kalimba-steps":  (96, 0, 4, ["I", "IV", "vi", "V"], "kalimba"),
    "book-waltz":     (120, 7, 3, ["I", "vi", "ii", "V"], "waltz"),
    "cafe-accordion": (112, 2, 4, ["I", "vi", "ii", "V"], "cafe"),
    "harp-dream":     (70, 10, 4, ["I", "IV", "vi", "V"], "harp"),
    "warm-guitar":    (90, 4, 4, ["I", "V", "vi", "IV"], "strum"),
}


def compose(name, seed=7):
    bpm, key, bpb, roman, kind = TRACKS[name]
    rng = random.Random(f"{name}-{seed}")
    beat = 60 / bpm; bar = beat * bpb
    scale = MIN if roman[0][0].islower() else MAJ
    prog = [chord(r, key, scale) for r in roman] * 4          # 16 bars, played twice -> 32 bars (~60-100 s)
    mid = pm.PrettyMIDI(initial_tempo=bpm)
    I = lambda prog_name, **kw: pm.Instrument(program=P(prog_name), **kw)
    if kind == "piano":
        acc = I("Acoustic Grand Piano"); arpeggio(acc, prog, beat, bar, bpb, 48, [0, 1, 2, 3, 2, 1, 2, 1], 52, rng, hold=1.5)
        mel = I("Acoustic Grand Piano"); melody(mel, prog, key, scale, beat, bar, bpb, 64, rng, vel=74, density=.85)
        pad = I("String Ensemble 2"); block(pad, prog, bar, 48, 34, rng)
        mid.instruments += [acc, mel, pad]
    elif kind == "guitar":
        acc = I("Acoustic Guitar (nylon)"); arpeggio(acc, prog, beat, bar, bpb, 45, [0, 2, 1, 3, 2, 1, 3, 2], 62, rng)
        mel = I("Flute"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=64, density=.7)
        b = I("Acoustic Bass"); bass(b, prog, bar, 36, 58, rng)
        mid.instruments += [acc, mel, b]
    elif kind == "xmas":
        acc = I("Celesta"); arpeggio(acc, prog, beat, bar, bpb, 60, [0, 1, 2, 3, 2, 1, 2, 1], 60, rng)
        mel = I("Music Box"); melody(mel, prog, key, scale, beat, bar, bpb, 72, rng, vel=70)
        pad = I("String Ensemble 1"); block(pad, prog, bar, 48, 40, rng)
        b = I("Pizzicato Strings"); bass(b, prog, bar, 36, 60, rng)
        mid.instruments += [acc, mel, pad, b]; drums(mid, len(prog), bar, beat, "bells", 70, rng)
    elif kind == "xmas2":
        acc = I("Glockenspiel"); arpeggio(acc, prog, beat, bar, bpb, 72, [0, None, 2, None, 1, None, 2, None], 50, rng)
        mel = I("Celesta"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=78)
        pi = I("Acoustic Grand Piano"); block(pi, prog, bar, 48, 46, rng, hits=[(0, .25), (.25, .25), (.5, .25), (.75, .25)])
        b = I("Acoustic Bass"); bass(b, prog, bar, 36, 64, rng, pattern=((0, .25), (.25, .25), (.5, .25), (.75, .25)))
        mid.instruments += [acc, mel, pi, b]; drums(mid, len(prog), bar, beat, "bells", 78, rng)
    elif kind == "marimba":
        acc = I("Marimba"); arpeggio(acc, prog, beat, bar, bpb, 55, [0, 2, 1, 2, 0, 2, 1, 2], 64, rng)
        mel = I("Vibraphone"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=66)
        pz = I("Pizzicato Strings"); bass(pz, prog, bar, 43, 62, rng, pattern=((0, .25), (.5, .25), (.75, .25)))
        mid.instruments += [acc, mel, pz]; drums(mid, len(prog), bar, beat, "shaker", 72, rng)
    elif kind == "lofi":
        ep = I("Electric Piano 1"); block(ep, prog, bar, 55, 50, rng, hits=[(0, .45), (.625, .35)])
        mel = I("Vibraphone"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=56, density=.6)
        b = I("Electric Bass (finger)"); bass(b, prog, bar, 33, 66, rng, pattern=((0, .4), (.5, .2), (.75, .2)))
        mid.instruments += [ep, mel, b]; drums(mid, len(prog), bar, beat, "lofi", 62, rng)
    elif kind == "strings":
        st = I("String Ensemble 1"); block(st, prog, bar, 48, 50, rng)
        hp = I("Orchestral Harp"); arpeggio(hp, prog, beat, bar, bpb, 55, [0, 1, 2, 3, 4, 3, 2, 1], 54, rng)
        mel = I("Cello"); melody(mel, prog, key, scale, beat, bar, bpb, 55, rng, vel=70, density=.6)
        mid.instruments += [st, hp, mel]
    elif kind == "kalimba":
        k = I("Kalimba"); arpeggio(k, prog, beat, bar, bpb, 60, [0, 2, 1, 3, 0, 2, 1, 3], 66, rng)
        mel = I("Pan Flute"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=58, density=.7)
        b = I("Acoustic Bass"); bass(b, prog, bar, 36, 60, rng)
        mid.instruments += [k, mel, b]; drums(mid, len(prog), bar, beat, "shaker", 64, rng)
    elif kind == "waltz":
        pi = I("Acoustic Grand Piano")
        for i, (root, ints) in enumerate(prog * 2):
            add(pi, 36 + root, i * bar, beat * .9, 60)
            for b2 in (1, 2):
                for x in ints[:3]: add(pi, 55 + root + x, i * bar + b2 * beat, beat * .8, 46)
        mel = I("Violin"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=66, density=.8)
        mid.instruments += [pi, mel]
    elif kind == "cafe":
        ac = I("Accordion"); melody(ac, prog, key, scale, beat, bar, bpb, 67, rng, vel=62)
        gt = I("Acoustic Guitar (nylon)"); block(gt, prog, bar, 52, 50, rng, hits=[(0, .2), (.25, .2), (.5, .2), (.75, .2)])
        b = I("Acoustic Bass"); bass(b, prog, bar, 36, 62, rng, pattern=((0, .25), (.25, .25), (.5, .25), (.75, .25)))
        mid.instruments += [ac, gt, b]; drums(mid, len(prog), bar, beat, "brush", 66, rng)
    elif kind == "harp":
        hp = I("Orchestral Harp"); arpeggio(hp, prog, beat, bar, bpb, 48, [0, 1, 2, 3, 4, 5, 4, 3], 58, rng, hold=2)
        mel = I("Flute"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=60, density=.6)
        pad = I("Pad 2 (warm)"); block(pad, prog, bar, 48, 32, rng)
        mid.instruments += [hp, mel, pad]
    elif kind == "strum":
        gt = I("Acoustic Guitar (steel)")
        for i, (root, ints) in enumerate(prog * 2):
            for j, (off, down) in enumerate(((0, 1), (.25, 1), (.375, 0), (.5, 0), (.75, 1), (.875, 0))):
                tones = [52 + root + x for x in ints[:3]] + [64 + root]
                for n, p in enumerate(tones if down else tones[::-1]):
                    add(gt, p, i * bar + off * bar + n * .012, bar * .2, 54 - (8 if not down else 0) + rng.randint(-4, 4))
        mel = I("Acoustic Grand Piano"); melody(mel, prog, key, scale, beat, bar, bpb, 67, rng, vel=62, density=.7)
        b = I("Acoustic Bass"); bass(b, prog, bar, 36, 58, rng)
        mid.instruments += [gt, mel, b]
    return mid


def render(name):
    mid = compose(name)
    with tempfile.TemporaryDirectory() as td:
        m = Path(td) / "a.mid"; w = Path(td) / "a.wav"; mid.write(str(m))
        subprocess.run(["fluidsynth", "-ni", "-g", "0.7", "-r", "44100", "-o", "synth.reverb.active=1", "-o", "synth.reverb.room-size=0.62",
                        "-o", "synth.reverb.level=0.55", "-o", "synth.chorus.active=1", "-F", str(w), SF2, str(m)], check=True, capture_output=True)
        length = mid.get_end_time() + 2.5
        # mastering: tidy lows, soft top, glue compression, loudness for a background bed, fade in/out
        af = (f"atrim=0:{length:.2f},highpass=f=45,lowpass=f=15000,equalizer=f=300:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=1.5,"
              f"acompressor=threshold=-20dB:ratio=2.5:attack=20:release=250,loudnorm=I=-18:TP=-2:LRA=9,afade=t=in:d=1.2,afade=t=out:st={length - 3:.2f}:d=3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(w), "-af", af, "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
                        str(HERE / "new" / f"{name}.m4a")], check=True)
    print(name, f"{length:.0f}s")


if __name__ == "__main__":
    for n in sys.argv[1:] or TRACKS: render(n)

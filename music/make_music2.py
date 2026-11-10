"""Second set of original background loops: different instruments so the feed never sounds the same.
No third-party audio: every sound is synthesised here. Usage: python music/make_music2.py [out_dir]"""
import numpy as np, wave, sys, os
SR = 44100

def hz(n): return 440 * 2 ** ((n - 69) / 12)

def lowpass(x, cut):
    a = np.exp(-2 * np.pi * cut / SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y

def lp_fast(x, cut):  # vectorised 2-pass smoothing via FFT (for long buffers)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cut) ** 4)
    return np.fft.irfft(X, len(x))

def t_(dur): return np.arange(int(dur * SR)) / SR

def soft_attack(s, a=.006):
    n = min(len(s), int(a * SR)); s[:n] *= np.linspace(0, 1, n); return s

# ---------- instruments ----------
def felt_piano(f, dur=2.5):
    t = t_(dur); s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (1.4 + k * .9)) for k, a in ((1, 1), (2, .38), (3, .14), (4, .06), (5, .03)))
    return soft_attack(s, .012)

def epiano(f, dur=2.4):
    t = t_(dur); idx = 1.6 * np.exp(-t * 3)
    s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) * np.exp(-t * 1.6)
    s += .25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)
    return soft_attack(s * (1 + .15 * np.sin(2 * np.pi * 4.5 * t)), .01)

def marimba(f, dur=1.2):
    t = t_(dur); s = np.sin(2 * np.pi * f * t) * np.exp(-t * 5) + .25 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 14)
    return soft_attack(s, .003)

def celesta(f, dur=2.2):
    t = t_(dur); s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.2) + .35 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t * 3.5) + .12 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t * 6)
    return soft_attack(s, .004)

def guitar(f, dur=2.0, seed=0):  # Karplus-Strong
    rng = np.random.default_rng(seed); n = int(dur * SR); p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p); buf = np.convolve(buf, np.ones(4) / 4, 'same'); out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = .4985 * (buf[i % p] + buf[(i + 1) % p])
    return soft_attack(out, .002)

def strings(freqs, dur):
    t = t_(dur); s = np.zeros_like(t)
    for f in freqs:
        for det in (-.0025, 0, .0025):
            ph = 2 * np.pi * f * (1 + det) * t + .002 * np.sin(2 * np.pi * 5 * t) * 2 * np.pi * f / 5
            s += sum(np.sin(k * ph) / k ** 1.6 for k in range(1, 6))
    n = len(t); e = np.minimum(1, t / 1.4) * np.minimum(1, (dur - t) / 1.4)
    return lp_fast(s * e / (3 * len(freqs)), 1800)

def pad(freqs, dur):
    t = t_(dur); s = sum(np.sin(2 * np.pi * f * t + .5 * np.sin(2 * np.pi * .25 * t)) + .2 * np.sin(4 * np.pi * f * t) for f in freqs)
    e = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return s * e / len(freqs)

def kick(dur=.35):
    t = t_(dur); f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)

def brush(dur=.12, seed=1):
    rng = np.random.default_rng(seed); t = t_(dur); n = rng.uniform(-1, 1, len(t))
    n = n - lp_fast(n, 4000); return n * np.exp(-t * 35) * .5

def shaker(dur=.09, seed=2):
    rng = np.random.default_rng(seed); t = t_(dur); n = rng.uniform(-1, 1, len(t))
    n = n - lp_fast(n, 6000); return n * np.sin(np.pi * t / dur) * .35

# ---------- arrangement ----------
def place(mix, s, at, g=1.0):
    i = int(at * SR)
    if i >= len(mix): return
    j = min(len(mix), i + len(s)); mix[i:j] += g * s[:j - i]

def reverb(x, wet=.28):
    y = x.copy()
    for d, g in ((.029, .5), (.043, .42), (.061, .36), (.089, .3), (.127, .24), (.181, .18), (.257, .12)):
        k = int(d * SR); z = np.zeros_like(x); z[k:] = x[:-k]; y += wet * g * z
    return y

def song(name, root, bpm, prog, lead, style, bars=16, seed=0):
    rng = np.random.default_rng(seed); beat = 60 / bpm; bar = beat * 4
    L = bars * bar; mix = np.zeros(int((L + 3) * SR)); drums = np.zeros_like(mix)
    scale = [0, 2, 4, 7, 9, 12, 14, 16]  # major pentatonic-ish, always consonant
    for b in range(bars):
        chord = [root + i for i in prog[b % len(prog)]]; t0 = b * bar
        if style in ('strings',):
            place(mix, strings([hz(c - 12) for c in chord], bar + 1.6), t0, .55)
        else:
            place(mix, pad([hz(c - 12) for c in chord], bar + 1.2), t0, .22)
        place(mix, felt_piano(hz(chord[0] - 24), bar) if style != 'lofi' else epiano(hz(chord[0] - 24), bar), t0, .45)
        # accompaniment pattern
        if style == 'lofi':
            for k in (0, 1.5, 2.5): place(mix, epiano(hz(chord[1]), 1.6) + epiano(hz(chord[2]), 1.6) * .8 + epiano(hz(chord[3] if len(chord) > 3 else chord[0] + 12), 1.6) * .6, t0 + k * beat, .16)
            for k in range(4):
                if k in (0, 2): place(drums, kick(), t0 + k * beat, .55)
                place(drums, brush(seed=b * 4 + k), t0 + (k + .5) * beat, .35)
                if k in (1, 3): place(drums, brush(.2, seed=99 + b), t0 + k * beat, .45)
        elif style == 'guitar':
            pat = [0, 2, 1, 3, 2, 1, 3, 2]
            for k in range(8): place(mix, guitar(hz(chord[pat[k] % len(chord)]), 1.8, seed=b * 8 + k), t0 + k * beat / 2, .22)
            for k in range(8): place(drums, shaker(seed=k + b), t0 + k * beat / 2, .25 if k % 2 else .4)
        elif style == 'marimba':
            for k in range(8):
                if rng.random() < .25: continue
                place(mix, marimba(hz(chord[[0, 2, 1, 2, 3, 2, 1, 2][k] % len(chord)] + 12), 1.0), t0 + k * beat / 2, .26)
            for k in (0, 2): place(drums, kick(), t0 + k * beat, .3)
        elif style in ('piano', 'strings', 'celesta'):
            for k in (0, 1, 2, 3):
                place(mix, felt_piano(hz(chord[[1, 2, 3, 2][k] % len(chord)]), 2.2), t0 + k * beat, .14)
        # lead melody: calm, mostly on beats, from the scale over the chord root
        inst = {'piano': felt_piano, 'lofi': epiano, 'marimba': marimba, 'celesta': celesta, 'guitar': felt_piano, 'strings': celesta}[style]
        if b % 4 != 3 and lead:
            steps = rng.choice([0, 1, 2, 3], p=[.15, .45, .25, .15])
            pos = [0, 1.5, 2, 3][:steps + 1] if steps else [0]
            for k in pos:
                deg = scale[rng.integers(0, 6)]
                place(mix, inst(hz(root + 12 + deg)), t0 + k * beat, .2)
    mix = reverb(mix) + drums * .8
    mix = lp_fast(mix, 7000)[:int(L * SR)]
    fade = int(SR * 2); mix[-fade:] *= np.linspace(1, 0, fade); mix[:int(SR * .4)] *= np.linspace(0, 1, int(SR * .4))
    return mix / (np.max(np.abs(mix)) * 1.12)

TRACKS = {  # name: (root, bpm, progression, lead melody?, style)
    'felt-piano':    (60, 74, [[0, 4, 7, 11], [-3, 0, 4, 7], [5, 9, 12, 16], [7, 11, 14, 17]], True, 'piano'),
    'lofi-notes':    (57, 78, [[0, 3, 7, 10], [5, 8, 12, 15], [-2, 2, 5, 9], [3, 7, 10, 14]], True, 'lofi'),
    'marimba-walk':  (65, 100, [[0, 4, 7, 9], [-3, 0, 4, 7], [5, 9, 12, 14], [7, 11, 14, 17]], True, 'marimba'),
    'garden-guitar': (55, 84, [[0, 4, 7, 12], [-5, -1, 2, 7], [-3, 0, 4, 9], [5, 9, 12, 16]], False, 'guitar'),
    'snow-celesta':  (67, 70, [[0, 4, 7, 11], [-5, -1, 2, 9], [-3, 0, 4, 7], [-7, -3, 0, 4]], True, 'celesta'),
    'evening-strings': (55, 62, [[0, 4, 7, 11], [-3, 0, 4, 7], [-7, -3, 0, 4], [-5, -1, 2, 7]], True, 'strings'),
    'coffee-lofi':   (62, 84, [[0, 4, 7, 11], [2, 5, 9, 12], [-3, 0, 4, 7], [-5, -1, 2, 5]], True, 'lofi'),
    'sunny-marimba': (60, 108, [[0, 4, 7, 9], [5, 9, 12, 16], [-5, -1, 2, 7], [0, 4, 7, 12]], False, 'marimba'),
}
if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    only = sys.argv[2:]
    for i, (name, (root, bpm, prog, lead, style)) in enumerate(TRACKS.items()):
        if only and name not in only: continue
        d = song(name, root, bpm, prog, lead, style, seed=100 + i)
        st = np.stack([d, np.roll(d, int(.011 * SR))], 1)
        with wave.open(os.path.join(out, f'{name}.wav'), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((st * 32767 * .9).astype('<i2').tobytes())
        print(name, round(len(d) / SR, 1), 's')

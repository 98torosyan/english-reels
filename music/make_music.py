"""Original soft background loops for reels (no third-party audio)."""
import numpy as np, wave, sys, os
SR = 44100
def note(n):  # MIDI -> Hz
    return 440 * 2 ** ((n - 69) / 12)
def env(length, a, r):
    t = np.arange(length) / SR
    e = np.minimum(1, t / a) * np.minimum(1, (length / SR - t) / r)
    return np.clip(e, 0, 1)
def pad(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for f in freqs:
        for k, amp in ((1, 1), (2, .25), (3, .08)):
            out += amp * np.sin(2 * np.pi * f * k * t + np.sin(2 * np.pi * .3 * t) * .6)
    return out * env(n, 1.2, 1.4) / len(freqs)
def pluck(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (3 + k * 2)) for k, a in ((1, 1), (2, .45), (3, .2), (4, .1)))
    return s * np.minimum(1, t / .005)
def track(root, bpm, prog, bars=16, seed=0):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm; bar = beat * 4; total = int(bars * bar * SR) + SR * 3
    mix = np.zeros(total)
    for b in range(bars):
        chord = [root + i for i in prog[b % len(prog)]]
        start = int(b * bar * SR)
        p = pad([note(c - 12) for c in chord], bar + 1.5)
        mix[start:start + len(p)] += .55 * p
        bass = pluck(note(chord[0] - 24), bar) * .7
        mix[start:start + len(bass)] += bass
        for s in range(8):  # gentle arpeggio, 8th notes
            if rng.random() < .22: continue
            c = chord[[0, 2, 1, 3, 2, 1, 3, 2][s] % len(chord)] + 12
            pl = pluck(note(c), 1.6) * (.32 + .1 * rng.random())
            i = start + int(s * beat / 2 * SR); mix[i:i + len(pl)] += pl[:max(0, total - i)]
    # soft room reverb (comb echoes)
    for d, g in ((.11, .25), (.23, .16), (.37, .1)):
        k = int(d * SR); mix[k:] += g * mix[:-k]
    mix = mix[:int(bars * bar * SR)]
    fade = int(SR * 2); mix[-fade:] *= np.linspace(1, 0, fade); mix[:int(SR*.5)] *= np.linspace(0, 1, int(SR*.5))
    mix /= np.max(np.abs(mix)) * 1.12
    return mix
TRACKS = {
    'calm-study':   (60, 76, [[0, 4, 7, 11], [-3, 0, 4, 7], [-7, -3, 0, 4], [-5, -1, 2, 5]]),
    'bright-day':   (62, 92, [[0, 4, 7, 9], [-5, -1, 2, 7], [-3, 0, 4, 7], [-7, -3, 0, 5]]),
    'soft-evening': (57, 70, [[0, 3, 7, 10], [-4, 0, 3, 7], [-7, -4, 0, 3], [-2, 2, 5, 9]]),
    'morning-walk': (64, 96, [[0, 4, 7, 11], [5, 9, 12, 16], [-3, 0, 4, 7], [7, 11, 14, 17]]),
    'library-rain': (55, 66, [[0, 4, 7, 14], [-3, 0, 4, 11], [5, 9, 12, 16], [-5, -1, 2, 9]]),
    'little-steps': (67, 104, [[0, 4, 7, 9], [-5, -1, 2, 7], [-3, 0, 4, 9], [-7, -3, 0, 5]]),
    'warm-tea':     (60, 82, [[0, 4, 7, 10], [5, 9, 12, 15], [-1, 2, 5, 9], [-3, 0, 4, 7]]),
    'quiet-page':   (62, 72, [[0, 3, 7, 10], [5, 8, 12, 15], [-2, 2, 5, 9], [3, 7, 10, 14]]),
}
out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__)
for i, (name, (root, bpm, prog)) in enumerate(TRACKS.items()):
    d = track(root, bpm, prog, seed=i)
    st = np.stack([d, np.roll(d, int(.012 * SR))], 1)
    with wave.open(os.path.join(out, f'{name}.wav'), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767 * .9).astype('<i2').tobytes())
    print(name, round(len(d) / SR, 1), 's')

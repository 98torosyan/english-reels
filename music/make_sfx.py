"""Original short sound effects (tick, ding, whoosh, pop) for reels."""
import numpy as np, wave, os, sys
SR = 48000
def save(name, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * .8
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype('<i2').tobytes())
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__)
t = lambda d: np.arange(int(d * SR)) / SR
a = t(.09); save('sfx-tick.wav', np.sin(2*np.pi*1800*a) * np.exp(-a*60) + .4*np.sin(2*np.pi*3600*a)*np.exp(-a*90))
a = t(1.2); save('sfx-ding.wav', sum(g*np.sin(2*np.pi*f*a)*np.exp(-a*k) for f,g,k in ((1318.5,1,3.5),(1975.5,.55,4.5),(2637,.3,6),(659.3,.35,3))))
a = t(.45); n = np.random.default_rng(1).standard_normal(len(a)); env = np.sin(np.pi*np.clip(a/.45,0,1))**2
f = np.convolve(n, np.ones(40)/40, 'same'); save('sfx-whoosh.wav', f*env)
a = t(.18); save('sfx-pop.wav', np.sin(2*np.pi*(500+900*np.exp(-a*30))*a) * np.exp(-a*25))
print('sfx ok')

"""How clearly each sample is heard: faster-whisper (medium.en) word error rate against the text."""
import re
from pathlib import Path
from faster_whisper import WhisperModel
TEXT = ("It is a cold, snowy day. Mila and Leo play in the park. They throw snowballs and laugh. "
        "Then Leo looks at his hands. 'Oh no, my red mitten is lost!' Then Toffee runs to them. 'Good girl, Toffee!' says Leo.")
norm = lambda s: re.sub(r"[^a-z' ]", " ", s.lower().replace("’", "'")).split()
ref = norm(TEXT); m = WhisperModel("medium.en", compute_type="int8")
def wer(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, y in enumerate(b, 1): p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (x != y))
    return d[-1] / len(a)
for f in sorted(Path("samples").glob("*.mp3")):
    segs, info = m.transcribe(str(f), language="en", beam_size=5)
    segs = list(segs); hyp = norm(" ".join(s.text for s in segs))
    conf = sum(s.avg_logprob for s in segs) / max(1, len(segs))
    print(f"RESULT {f.stem:24} wer={wer(ref, hyp):.3f} logprob={conf:.3f}", flush=True)

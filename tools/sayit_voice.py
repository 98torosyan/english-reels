"""Voices for the "Say it right" reels (runs in GitHub Actions).

For every line of reels/data/sayit.json writes assets/sayit/<id>/<voice>/<k>.mp3 and <k>.json
({text, words: [[start, end], ...]}) for each candidate voice, so the owner can pick one by ear.
"""
import asyncio, json, subprocess, sys
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
VOICES = {"hy": [("kore", "gemini:Kore"), ("aoede", "gemini:Aoede"), ("charon", "gemini:Charon")],
          "en": [("ryan", "en-GB-RyanNeural"), ("sonia", "en-GB-SoniaNeural")]}
RATE = {"hy": "-6%", "en": "-12%"}


_MMS = {}


def speak_mms(text, model_id, mp3, speed=0.92):
    import torch, soundfile as sf
    from transformers import VitsModel, AutoTokenizer
    if model_id not in _MMS:
        _MMS[model_id] = (VitsModel.from_pretrained(model_id), AutoTokenizer.from_pretrained(model_id))
    model, tok = _MMS[model_id]
    model.speaking_rate = speed; model.noise_scale = 0.6
    if getattr(tok, "is_uroman", False):
        import uroman as ur
        text = ur.Uroman().romanize_string(text)
    torch.manual_seed(7)
    with torch.no_grad():
        wav = model(**tok(text, return_tensors="pt")).waveform[0].numpy()
    sf.write(str(mp3) + ".wav", wav, model.config.sampling_rate)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3) + ".wav", "-af", "adelay=80|80", "-b:a", "160k", str(mp3)], check=True)
    Path(str(mp3) + ".wav").unlink()
    return []


def speak_gtts(text, lang, mp3):
    from gtts import gTTS
    gTTS(text, lang=lang, lang_check=False).save(str(mp3))
    return []


def speak_t5(text, model_id, mp3):
    import torch, soundfile as sf
    from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
    from huggingface_hub import list_repo_files, hf_hub_download
    import numpy as np
    if model_id not in _MMS:
        proc = SpeechT5Processor.from_pretrained(model_id); model = SpeechT5ForTextToSpeech.from_pretrained(model_id)
        voc = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")
        emb = torch.zeros(1, 512)
        for space in ("Edmon02/SpeechT5_hy",):
            try:
                f = [x for x in list_repo_files(space, repo_type="space") if x.endswith(".npy")][0]
                emb = torch.tensor(np.load(hf_hub_download(space, f, repo_type="space"))).reshape(1, -1)
            except Exception as e:
                print("no speaker embedding", e)
        _MMS[model_id] = (proc, model, voc, emb)
    proc, model, voc, emb = _MMS[model_id]
    with torch.no_grad():
        wav = model.generate_speech(proc(text=text, return_tensors="pt")["input_ids"], emb, vocoder=voc).numpy()
    sf.write(str(mp3) + ".wav", wav, 16000)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3) + ".wav", "-b:a", "160k", str(mp3)], check=True)
    Path(str(mp3) + ".wav").unlink()
    return []


GEMINI_MODELS = ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts", "gemini-3.1-flash-tts-preview"]
STYLE = ("Read this in natural Eastern Armenian, as a warm, friendly English teacher talking to her followers: "
         "clear, calm pace, smiling voice. Words in «» are said exactly as written. Text: ")


def speak_gemini(text, voice, mp3):
    import base64, os, time, urllib.request, urllib.error
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("secret GEMINI_API_KEY is empty")
    body = json.dumps({"contents": [{"parts": [{"text": STYLE + text}]}],
                       "generationConfig": {"responseModalities": ["AUDIO"],
                                            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}).encode()
    last = None
    for model in GEMINI_MODELS:
        for attempt in range(3):
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                         data=body, headers={"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    part = json.load(r)["candidates"][0]["content"]["parts"][0]["inlineData"]
                pcm = base64.b64decode(part["data"])
                rate = int((part.get("mimeType", "").split("rate=") + ["24000"])[1].split(";")[0])
                raw = str(mp3) + ".pcm"; Path(raw).write_bytes(pcm)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", raw,
                                "-af", "adelay=80|80", "-b:a", "192k", str(mp3)], check=True)
                Path(raw).unlink(); print("  model", model, flush=True)
                return []
            except urllib.error.HTTPError as e:
                last = f"{model}: {e.code} {e.read()[:200]!r}"
                if e.code == 429: time.sleep(25); continue
                break
            except Exception as e:
                last = f"{model}: {e}"; break
    raise RuntimeError(last)


async def speak(text, voice, rate, mp3):
    if voice.startswith("gemini:"):
        return speak_gemini(text, voice[7:], mp3)
    if voice.startswith("t5:"):
        return speak_t5(text, voice[3:], mp3)
    if voice.startswith("mms:"):
        return speak_mms(text, voice[4:], mp3)
    if voice.startswith("gtts:"):
        return speak_gtts(text, voice[5:], mp3)
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for c in com.stream():
            if c["type"] == "audio":
                f.write(c["data"])
            elif c["type"] == "WordBoundary":
                s = c["offset"] / 1e7
                words.append([round(s, 3), round(s + c["duration"] / 1e7, 3), c["text"]])
    return words


async def main(only):
    data = json.loads((ROOT / "reels/data/sayit.json").read_text(encoding="utf-8"))
    for item in data["items"]:
        if only and item["id"] not in only:
            continue
        for line in item["lines"]:
            for name, voice in VOICES[line["lang"]]:
                out = ROOT / "assets/sayit" / item["id"] / name
                out.mkdir(parents=True, exist_ok=True)
                mp3 = out / f"{line['k']}.mp3"
                try:
                    words = await speak(line["text"], voice, RATE[line["lang"]], mp3)
                except Exception as e:  # voice not offered: try the next one
                    print("skip", voice, type(e).__name__, str(e)[:300], flush=True); mp3.unlink(missing_ok=True); continue
                if not words:  # no boundaries: take the sound itself
                    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                                             capture_output=True, text=True).stdout)
                    words = [[0.05, round(d - 0.05, 3), line["text"]]]
                (out / f"{line['k']}.json").write_text(json.dumps({"text": line["text"], "voice": voice, "words": words}, ensure_ascii=False), encoding="utf-8")
                print(item["id"], name, line["k"], len(words), "words", flush=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

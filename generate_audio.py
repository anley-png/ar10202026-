"""Generate the game's audio with SILMA TTS (Apache-2.0 weights).

Run on a machine with Python 3.10+, ffmpeg and ideally a GPU (Google Colab works):
    apt-get install -y ffmpeg
    pip install silma-tts
    python tools/generate_audio.py --ref my_voice.wav --ref-text "exact words spoken in my_voice.wav"

SILMA clones the style of a reference recording. Use a recording of a native speaker who agreed
(in writing) to the use of their voice in your app. Without --ref it falls back to the sample that
ships with the package, which is only for testing.

Options:  --only l5,v5_0,w3   regenerate just these      --seed 7    change the random take
          --speed 0.9         slower speech               --force     overwrite existing files
Output: audio/l<i>.mp3 (letter), audio/v<i>_<0-6>.mp3 (vowel syllable), audio/w<k>.mp3 (word).
Names and order come straight from index.html, so they always match the game. LISTEN to every file:
single letters and bare consonants (sukoon) are hard for any TTS; redo bad ones with --only and --seed.
"""
import argparse, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")
LET = re.search(r'const LET="([^"]+)"', html).group(1)
words = re.findall(r'\["([^"]+)","([^"]+)","([^"]+)","([^"]+)"\]', re.search(r"const W=\[(.*?)\]\.map", html, re.S).group(1))
MK = re.compile("[\u064B-\u0652]")
voweled = {MK.sub("", v): v for v in re.search(r'const VW="([^"]+)"', html).group(1).split()}
VOW = ["\u064e", "\u064f", "\u0650", "\u0652", "\u064e\u0627", "\u064f\u0648", "\u0650\u064a"]  # a u i (none) aa uu ee

jobs = {}
for i, c in enumerate(LET):
    jobs[f"l{i}"] = ("أ" if i == 0 else c) + "\u064e"
    for q, v in enumerate(VOW):
        jobs[f"v{i}_{q}"] = c + v
for k, w in enumerate(words):
    jobs[f"w{k}"] = voweled.get(w[0], w[0])  # fully vowelled text when we have it

ap = argparse.ArgumentParser()
ap.add_argument("--ref"); ap.add_argument("--ref-text")
ap.add_argument("--only"); ap.add_argument("--seed", type=int); ap.add_argument("--speed", type=float, default=0.9)
ap.add_argument("--force", action="store_true")
a = ap.parse_args()

import silma_tts
from silma_tts.api import SilmaTTS

ref = a.ref or str(pathlib.Path(silma_tts.__file__).parent / "infer" / "ref_audio_samples" / "ar.ref.24k.wav")
ref_text = a.ref_text or "ويدقق النظر في القرآن الكريم وسائر الكتب السماوية ويتبع مسالك الرسل العظام عليهم الصلاة والسلام."
only = set(a.only.split(",")) if a.only else None
out = ROOT / "audio"; out.mkdir(exist_ok=True)
tts = SilmaTTS()
trim = "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse"
for name, text in jobs.items():
    if only and name not in only: continue
    mp3 = out / f"{name}.mp3"
    if mp3.exists() and not a.force: continue
    wav = out / f"{name}.wav"
    tts.infer(ref_file=ref, ref_text=ref_text, gen_text=text, file_wave=str(wav), seed=a.seed, speed=a.speed)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", trim, "-codec:a", "libmp3lame", "-qscale:a", "5", str(mp3)], check=True)
    wav.unlink()
    print("ok", name, text)

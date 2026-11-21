#!/usr/bin/env python3
"""Compare des voix gratuites sur un même extrait. Usage : tts_compare.py CHAPITRE.md [nb_segments]

À lancer avec .venv-tts. Écrit des MP3 dans audio/_essais/.
"""
import subprocess
import sys
import time
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
import tts_text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio" / "_essais"
OUT.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def to_mp3(samples, rate, name):
    wav = OUT / f"{name}.wav"
    sf.write(wav, samples, rate)
    mp3 = OUT / f"{name}.mp3"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "4", str(mp3)], check=True)
    wav.unlink()
    return mp3


def silence(rate, sec):
    return np.zeros(int(rate * sec), dtype=np.float32)


def piper(voice, texts):
    from piper import PiperVoice
    v = PiperVoice.load(ROOT / "models" / "piper" / f"{voice}.onnx")
    parts, rate = [], v.config.sample_rate
    for t in texts:
        for chunk in v.synthesize(t):
            parts.append(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768)
        parts.append(silence(rate, 0.35))
    return np.concatenate(parts), rate


def kokoro(voice, texts):
    from kokoro_onnx import Kokoro
    k = Kokoro(str(ROOT / "models/kokoro/kokoro-v1.0.onnx"), str(ROOT / "models/kokoro/voices-v1.0.bin"))
    parts, rate = [], 24000
    for t in texts:
        s, rate = k.create(t, voice=voice, speed=1.0, lang="fr-fr")
        parts += [s, silence(rate, 0.35)]
    return np.concatenate(parts), rate


if __name__ == "__main__":
    segs = tts_text.chapter_segments(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    texts = [t for _, t in segs[1:1 + n]]
    print(f"{sum(len(t) for t in texts)} caractères")
    for name, fn, voice in [("piper-siwis", piper, "fr_FR-siwis-medium"), ("piper-upmc", piper, "fr_FR-upmc-medium"),
                            ("piper-tom", piper, "fr_FR-tom-medium"), ("kokoro-siwis", kokoro, "ff_siwis")]:
        t0 = time.time()
        try:
            audio, rate = fn(voice, texts)
            mp3 = to_mp3(audio, rate, name)
            print(f"{name}: {len(audio)/rate:.0f}s d'audio en {time.time()-t0:.0f}s -> {mp3.name} ({mp3.stat().st_size//1024} Ko)")
        except Exception as e:
            print(f"{name}: ÉCHEC {type(e).__name__}: {e}")

#!/usr/bin/env python3
"""Génère l'audio (MP3) de chaque chapitre d'un livre avec Piper (voix fr_FR-siwis-medium).

Usage (avec .venv-tts) : tools/tts_generate.py <slug> [id-chapitre …]
Sortie : audio/<slug>/<id-chapitre>.mp3 (chapitres déjà présents ignorés, sauf --force)
"""
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
import yaml
from piper import PiperVoice

sys.path.insert(0, str(Path(__file__).parent))
import tts_text

ROOT = Path(__file__).resolve().parent.parent
VOICE = "fr_FR-siwis-medium"
PAUSE = {"titre": 1.0, "para": 0.7, "signature": 0.7, "cont": 0.3}  # secondes avant le segment


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    slug, only = args[0], set(args[1:])
    book = yaml.safe_load((ROOT / "content" / slug / "book.yaml").read_text(encoding="utf-8"))
    out = ROOT / "audio" / slug
    out.mkdir(parents=True, exist_ok=True)
    voice = PiperVoice.load(ROOT / "models" / "piper" / f"{VOICE}.onnx")
    rate = voice.config.sample_rate
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    files = sorted((ROOT / "content" / slug / "chapitres").glob("*.md"))
    for n, f in enumerate(files, 1):
        if only and f.stem not in only:
            continue
        mp3 = out / f"{f.stem}.mp3"
        if mp3.exists() and not force:
            print(f"= {f.stem} déjà fait")
            continue
        t0 = time.time()
        segs = tts_text.chapter_segments(f)
        parts = []
        for kind, text in segs:
            parts.append(np.zeros(int(rate * PAUSE[kind]), dtype=np.float32))
            for ch in voice.synthesize(text):
                parts.append(np.frombuffer(ch.audio_int16_bytes, dtype=np.int16).astype(np.float32) / 32768)
        audio = np.concatenate(parts[1:])
        wav = out / f"{f.stem}.wav"
        sf.write(wav, audio, rate)
        title = segs[0][1]
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "4",
                        "-metadata", f"title={title}", "-metadata", f"artist={book['auteur']}",
                        "-metadata", f"album={book['titre']}", "-metadata", f"track={n}/{len(files)}",
                        "-metadata", "comment=Voix de synthèse Piper fr_FR-siwis-medium (CC BY 4.0)", str(mp3)], check=True)
        wav.unlink()
        print(f"+ {f.stem}: {len(audio)/rate/60:.1f} min d'audio en {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

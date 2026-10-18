#!/usr/bin/env python3
"""Pruebas gratuitas de voces masculinas neuronales Kokoro (español).
Genera muestras; no modifica el juego.
"""
from pathlib import Path
import json, subprocess
import soundfile as sf
from kokoro import KPipeline
out=Path("voice-casting-kokoro-v4")
out.mkdir(exist_ok=True)
p=KPipeline(lang_code="e")
samples={"definicion_B":"Be. Instrumento utilizado para medir la presión atmosférica.","veredicto":"Correcto. Incorrecto. Era barómetro."}
report=[]
for voice in ("em_alex","em_santa"):
    for label,text in samples.items():
        chunks=[]
        for _,_,audio in p(text,voice=voice,speed=1.04,split_pattern=r"\n+"):
            chunks.append(audio)
        import numpy as np
        wav=out/f"{voice}_{label}.wav"
        mp3=out/f"{voice}_{label}.mp3"
        sf.write(wav,np.concatenate(chunks),24000)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(wav),"-codec:a","libmp3lame","-b:a","112k",str(mp3)],check=True)
        assert mp3.stat().st_size>4000
        report.append({"voice":voice,"sample":label,"text":text,"file":mp3.name})
        wav.unlink()
(out/"samples.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print("PASS",json.dumps(report,ensure_ascii=False),flush=True)

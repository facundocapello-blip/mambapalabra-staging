#!/usr/bin/env python3
"""Solo casting de voces masculinas Kokoro; no modifica STAGING ni producción."""
import json, subprocess
from pathlib import Path
import soundfile as sf
from kokoro_onnx import Kokoro
out=Path("voice-casting-kokoro-v5");out.mkdir(exist_ok=True)
tts=Kokoro("kokoro-v1.0.int8.onnx","voices-v1.0.bin")
voices={"A_Alex":"em_alex","B_Santa":"em_santa"}
texts={"definicion":"Be. Instrumento utilizado para medir la presión atmosférica.","veredicto":"Correcto. Incorrecto. Era barómetro."}
report=[]
for name,voice in voices.items():
    assert voice in tts.get_voices(),f"Voz ausente: {voice}"
    for kind,text in texts.items():
        samples,sr=tts.create(text,voice=voice,speed=1.07,lang="es")
        wav=out/f"{name}_{kind}.wav"
        mp3=out/f"{name}_{kind}.mp3"
        sf.write(str(wav),samples,sr)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(wav),"-codec:a","libmp3lame","-b:a","112k",str(mp3)],check=True)
        assert mp3.stat().st_size>2000
        report.append({"voice":voice,"sample":kind,"file":mp3.name,"bytes":mp3.stat().st_size})
        wav.unlink()
(out/"samples.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False))

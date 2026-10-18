#!/usr/bin/env python3
"""Casting aislado: tres voces masculinas Piper con exactamente los mismos textos.
No altera el juego, el banco de preguntas ni la versión aprobada V2.
"""
import json
import os
from pathlib import Path
import subprocess

piper=Path(os.environ.get("PIPER_BIN","/tmp/mamba-piper/piper/piper"))
models=Path(os.environ.get("PIPER_MODELS","/tmp/mamba-piper/models"))
out=Path("voice-casting-v3")
out.mkdir(parents=True,exist_ok=True)
samples={
    "definicion_B":"Be. Instrumento utilizado para medir la presión atmosférica.",
    "veredicto":"Correcto. Incorrecto. Era barómetro.",
}
voices=[
    ("A_davefx_es", "es_ES-davefx-medium", None),
    ("B_sharvard_es", "es_ES-sharvard-medium", 0),
    ("C_ald_mx", "es_MX-ald-medium", None),
]
report=[]
for label,model,speaker in voices:
    for key,text in samples.items():
        wav=out/f"{label}_{key}.wav"
        mp3=out/f"{label}_{key}.mp3"
        cmd=[str(piper),"--model",str(models/(model+".onnx")),"--output_file",str(wav),"--length_scale","0.90","--sentence_silence","0.08"]
        if speaker is not None:cmd.extend(["--speaker",str(speaker)])
        subprocess.run(cmd,input=text,encoding="utf-8",check=True,env=os.environ,timeout=120)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(wav),"-codec:a","libmp3lame","-b:a","112k",str(mp3)],check=True,timeout=60)
        probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(mp3)],capture_output=True,text=True,check=True)
        seconds=float(probe.stdout.strip())
        assert seconds>1 and mp3.stat().st_size>5000,(mp3,seconds)
        report.append({"option":label,"model":model,"speaker":speaker,"sample":key,"text":text,"file":mp3.name,"seconds":round(seconds,2)})
        wav.unlink()
(out/"samples.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))

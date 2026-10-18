#!/usr/bin/env python3
"""Casting V4 neural, solo muestras; no modifica los 811 audios ni el juego."""
import asyncio
import json
from pathlib import Path
import edge_tts

OUT=Path("voice-casting-neural-v4")
OUT.mkdir(exist_ok=True)
TEXTS={
    "definicion":"Be. Instrumento utilizado para medir la presión atmosférica.",
    "veredicto":"Correcto. Incorrecto. Era barómetro."
}
VOICES={
    "A_Tomas_argentino":("es-AR-TomasNeural","+5%","-6Hz"),
    "B_Gonzalo_colombiano":("es-CO-GonzaloNeural","+7%","-8Hz"),
    "C_Lorenzo_chileno":("es-CL-LorenzoNeural","+5%","-6Hz")
}
async def main():
    report=[]
    for name,(voice,rate,pitch) in VOICES.items():
        for key,text in TEXTS.items():
            dest=OUT/f"{name}_{key}.mp3"
            await edge_tts.Communicate(text,voice,rate=rate,pitch=pitch).save(str(dest))
            assert dest.stat().st_size>3000,(dest,dest.stat().st_size)
            report.append({"option":name,"voice":voice,"rate":rate,"pitch":pitch,"text":text,"file":dest.name,"bytes":dest.stat().st_size})
    (OUT/"samples.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
asyncio.run(main())

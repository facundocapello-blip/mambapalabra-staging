#!/usr/bin/env python3
"""Casting aislado de voces neuronales rioplatenses/latinoamericanas.
No modifica el juego ni los 811 audios aprobados. Requiere edge-tts y ffprobe.
"""
import asyncio, json, pathlib, subprocess
import edge_tts

out=pathlib.Path("voice-casting-argentine-v4")
out.mkdir(exist_ok=True)
voices=[
    ("A_Tomas_AR_natural","es-AR-TomasNeural","+0%","+0Hz","Argentina, natural"),
    ("B_Tomas_AR_grave","es-AR-TomasNeural","+5%","-12Hz","Argentina, más grave y ágil"),
    ("C_Mateo_UY_grave","es-UY-MateoNeural","+3%","-8Hz","Uruguay, rioplatense"),
    ("D_Lorenzo_CL_grave","es-CL-LorenzoNeural","+2%","-10Hz","Chile, latinoamericano"),
]
phrases={
    "definicion_B":"Be. Instrumento utilizado para medir la presión atmosférica.",
    "veredicto":"Correcto. Incorrecto. Era barómetro.",
}
async def main():
    available={v["ShortName"] for v in await edge_tts.list_voices()}
    report=[]
    for label,voice,rate,pitch,region in voices:
        assert voice in available, f"No está disponible {voice}"
        for key,phrase in phrases.items():
            path=out/f"{label}_{key}.mp3"
            await edge_tts.Communicate(phrase,voice,rate=rate,pitch=pitch).save(str(path))
            assert path.stat().st_size>4000, f"MP3 vacío: {path}"
            p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True,check=True,timeout=15)
            dur=float(p.stdout.strip())
            assert dur>1
            report.append({"option":label,"voice":voice,"region":region,"rate":rate,"pitch":pitch,"sample":key,"text":phrase,"file":path.name,"seconds":round(dur,2)})
            print(label,key,round(dur,2),flush=True)
    (out/"samples.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("QA OK:",len(report),"MP3",flush=True)
asyncio.run(main())

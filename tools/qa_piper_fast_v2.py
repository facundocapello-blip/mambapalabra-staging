#!/usr/bin/env python3
"""QA: direct letter prefix, all 398 approved, 811 MP3, and measured speed-up."""
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import urllib.request

root=pathlib.Path("piper-audio")
manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
spec=importlib.util.spec_from_file_location("generator","tools/generate_piper_bank.py")
generator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
rows,bank_hash=generator.bank()
expected,jobs=generator.prepare(rows,bank_hash)
assert manifest==expected,"El manifiesto publicado no coincide con los textos de síntesis"
assert manifest["approved"]==398 and manifest["clips"]==811
assert manifest["voice_style"]=="letra-directa-v2"
assert manifest["length_scale"]==0.90
assert len(list(root.glob("*.mp3")))==811
qjobs={k:v for k,v in jobs if k.startswith("q")}
for i,row in enumerate(manifest["rows"],1):
    letter=row["letter"]
    spoken=qjobs[f"q{i:04d}.mp3"]
    if row["rule"]=="CONTIENE":
        assert spoken.startswith(f"Contiene la {generator.LETTER_NAMES[letter]}. "), (letter,spoken)
    else:
        assert spoken.startswith(f"{generator.LETTER_NAMES[letter]}. "), (letter,spoken)
    assert "Con la letra" not in spoken, (letter,spoken)
assert len(set(r["letter"] for r in manifest["rows"]))==27
def duration(filename):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(filename)],capture_output=True,text=True,check=True,timeout=10)
    return float(r.stdout.strip())
oldbase="https://raw.githubusercontent.com/facundocapello-blip/mambapalabra-staging/qa/piper-audio-398/piper-audio/"
comparisons=[]
for name in ["q0001.mp3","q0015.mp3","q0080.mp3","q0175.mp3","q0250.mp3","q0398.mp3","w0001.mp3","w0080.mp3","fixed01.mp3"]:
    with tempfile.NamedTemporaryFile(suffix=".mp3") as old:
        with urllib.request.urlopen(oldbase+name,timeout=45) as response:
            old.write(response.read())
        old.flush()
        old_duration=duration(old.name)
    new_duration=duration(root/name)
    comparisons.append((name,round(old_duration,2),round(new_duration,2)))
    assert new_duration<old_duration, f"El audio no se aceleró: {name}, antes {old_duration}, ahora {new_duration}"
print(json.dumps({"approved":398,"letters":27,"mp3":811,"duration_comparisons":comparisons},ensure_ascii=False))

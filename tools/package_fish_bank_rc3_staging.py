#!/usr/bin/env python3
"""Package Fish 811-clip voice bank only after complete hash-checked coverage."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generate_fish_bank import all_jobs, EXPECTED_SHA, MODEL, VOICE_ID

BASE=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH_VOCES_INTROS_RC1_STAGING.zip")
OUT=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC3_STAGING.zip")
BANK=Path("artifacts/fish-bank")
VERSION="B1.13.1-UX1-FISH398-VOZ-UNICA-RC3-STAGING"
original=json.loads(Path("piper-audio/manifest.json").read_text())
expected=all_jobs(original)
casting=json.loads((BANK/"manifest.json").read_text())
assert not casting.get("fixture_only") or os.getenv("FISH_PACKAGE_TEST_FIXTURE")=="1", "Refusing fixture audio in real package"
assert casting["model"]==MODEL and casting["voice_id"]==VOICE_ID
assert casting["source_bank_sha256"]==EXPECTED_SHA
clips=casting["clips"]
assert len(clips)==811 and len(set(x["file"] for x in clips))==811
index={x["file"]:x for x in clips}
mapping={}
for filename,spoken,key in expected:
 assert filename in index,filename
 entry=index[filename]
 assert entry["phrase"]==key and entry["text"]==spoken,filename
 blob=(BANK/filename).read_bytes()
 assert len(blob)>1000 and hashlib.sha256(blob).hexdigest()==entry["sha256"],filename
 assert key not in mapping,key
 mapping[key]="fish-bank/"+filename
assert len(mapping)==811
with ZipFile(BASE) as z:
 s=z.read("index.html").decode("utf-8")
 assert z.read("FISH_CASTING_RELEASE.json")
 marker='for(const [phrase,url] of Object.entries(FISH_CASTING_MAP)){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}'
 assert s.count(marker)==1
 s=s.replace(marker,marker+'\n  const FISH_BANK_VERSION="'+VERSION+'";\n  const FISH_BANK_MAP='+json.dumps(mapping,ensure_ascii=False,separators=(",",":"))+';\n  for(const [phrase,url] of Object.entries(FISH_BANK_MAP)){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}')
 # Prevent all legacy and OS speech: only Fish Audio paths are eligible.
 strict_marker='for(const [phrase,url] of Object.entries(FISH_BANK_MAP)){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}'
 assert s.count(strict_marker)==1
 s=s.replace(strict_marker,strict_marker+'\n  STATIC_AUDIO["Empate. Vamos a muerte súbita."]="fish-audio/08_muerte_subita.mp3";\n  NEW_VOICE_AUDIO.clear();\n  for(const url of Object.values(FISH_CASTING_MAP))NEW_VOICE_AUDIO.add(url);\n  for(const url of Object.values(FISH_BANK_MAP))NEW_VOICE_AUDIO.add(url);\n  NEW_VOICE_AUDIO.add("fish-audio/08_muerte_subita.mp3");')
 old='if(!paths.length)return deviceSpeak(text,opts,seq);'
 assert s.count(old)==1
 s=s.replace(old,'if(!paths.length){setVoiceStatus("error","No hay grabación Fish Audio para esta frase. Podés continuar leyendo.");return {status:SPEECH_RESULT.FAILED,started:false};}')
 old='if(result.status===SPEECH_RESULT.FAILED)return deviceSpeak(text,opts,seq);'
 assert s.count(old)==1
 s=s.replace(old,'if(result.status===SPEECH_RESULT.FAILED){setVoiceStatus("error","Falló el audio Fish. Podés continuar leyendo o repetir.");return result;}')
 old='try{const u=new SpeechSynthesisUtterance(" ");u.lang="es-AR";window.speechSynthesis.speak(u);}catch(e){}'
 assert s.count(old)==1
 s=s.replace(old,'// Fish Audio only: never prime or play a device-synthesized voice.')
 assert s.count('return deviceSpeak(')==0
 release=json.loads(z.read("PIPER_RELEASE.json"))
 release.update(version=VERSION,fish_bank_mp3=811,fish_voice=VOICE_ID,fish_model=MODEL,voice_overlay="Fish only: 811 bank clips, 3 intros, sudden death; no neutral voice fallback",production_untouched=True)
 with ZipFile(OUT,"w",ZIP_DEFLATED,compresslevel=4) as out:
  for item in z.infolist():
   if item.filename.startswith("piper-audio/"):
    continue
   if item.filename=="index.html":out.writestr(item,s.encode("utf-8"))
   elif item.filename=="PIPER_RELEASE.json":out.writestr(item,json.dumps(release,ensure_ascii=False,indent=2))
   else:out.writestr(item,z.read(item.filename))
  for filename,_,_ in expected:out.writestr("fish-bank/"+filename,(BANK/filename).read_bytes())
  out.writestr("fish-audio/08_muerte_subita.mp3",Path("fish-extra/08_muerte_subita.mp3").read_bytes())
  out.writestr("FISH_BANK_RELEASE.json",json.dumps({"version":VERSION,"model":MODEL,"voice_id":VOICE_ID,"bank_sha256":EXPECTED_SHA,"fish_clips":811,"casting_intro_clips":8,"scope":"STAGING only"},ensure_ascii=False,indent=2))
with ZipFile(OUT) as z:
 assert sum(x.startswith("fish-bank/") and x.endswith(".mp3") for x in z.namelist())==811
 assert sum(x.startswith("fish-audio/") and x.endswith(".mp3") for x in z.namelist())==8
 assert sum(x.startswith("piper-audio/") and x.endswith(".mp3") for x in z.namelist())==0
 assert z.read("index.html").decode()==s
 assert "return deviceSpeak(" not in s
print("Fish 398 full bank STAGING ZIP:",OUT,"bytes:",OUT.stat().st_size)

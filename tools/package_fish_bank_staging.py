#!/usr/bin/env python3
"""Package Fish 811-clip voice bank only after complete hash-checked coverage."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generate_fish_bank import all_jobs, EXPECTED_SHA, MODEL, VOICE_ID

BASE=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH_VOCES_INTROS_RC1_STAGING.zip")
OUT=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC2_STAGING.zip")
BANK=Path("artifacts/fish-bank")
VERSION="B1.13.1-UX1-FISH398-VOZ-UNICA-RC2-STAGING"
original=json.loads(Path("piper-audio/manifest.json").read_text())
expected=all_jobs(original)
casting=json.loads((BANK/"manifest.json").read_text())
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
 release=json.loads(z.read("PIPER_RELEASE.json"))
 release.update(version=VERSION,fish_bank_mp3=811,fish_voice=VOICE_ID,fish_model=MODEL,voice_overlay="Fish bank 811 clips, plus 3 Fish introductions",production_untouched=True)
 with ZipFile(OUT,"w",ZIP_DEFLATED,compresslevel=4) as out:
  for item in z.infolist():
   if item.filename=="index.html":out.writestr(item,s.encode("utf-8"))
   elif item.filename=="PIPER_RELEASE.json":out.writestr(item,json.dumps(release,ensure_ascii=False,indent=2))
   else:out.writestr(item,z.read(item.filename))
  for filename,_,_ in expected:out.writestr("fish-bank/"+filename,(BANK/filename).read_bytes())
  out.writestr("FISH_BANK_RELEASE.json",json.dumps({"version":VERSION,"model":MODEL,"voice_id":VOICE_ID,"bank_sha256":EXPECTED_SHA,"fish_clips":811,"casting_intro_clips":7,"scope":"STAGING only"},ensure_ascii=False,indent=2))
with ZipFile(OUT) as z:
 assert sum(x.startswith("fish-bank/") and x.endswith(".mp3") for x in z.namelist())==811
 assert sum(x.startswith("fish-audio/") and x.endswith(".mp3") for x in z.namelist())==7
 assert sum(x.startswith("piper-audio/") and x.endswith(".mp3") for x in z.namelist())==811
 assert z.read("index.html").decode()==s
print("Fish 398 full bank STAGING ZIP:",OUT,"bytes:",OUT.stat().st_size)

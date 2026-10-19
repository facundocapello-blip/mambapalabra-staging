#!/usr/bin/env python3
"""Packaging-only fixture: Piper bytes in Fish paths. NEVER publish this fixture."""
from pathlib import Path
import hashlib,json,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from generate_fish_bank import all_jobs,MODEL,VOICE_ID,EXPECTED_SHA
source=json.loads(Path("piper-audio/manifest.json").read_text())
jobs=all_jobs(source)
dest=Path("artifacts/fish-bank")
dest.mkdir(parents=True,exist_ok=True)
clips=[]
for filename,spoken,phrase in jobs:
 origin=Path("piper-audio")/filename
 assert origin.is_file(),filename
 target=dest/filename
 shutil.copyfile(origin,target)
 blob=target.read_bytes()
 clips.append({"file":filename,"text":spoken,"phrase":phrase,"sha256":hashlib.sha256(blob).hexdigest(),"bytes":len(blob),"fixture_only":True})
(dest/"manifest.json").write_text(json.dumps({"schema":1,"voice_id":VOICE_ID,"model":MODEL,"source_bank_sha256":EXPECTED_SHA,"start":1,"count":398,"fixed":True,"clips":clips,"complete":True,"fixture_only":True},ensure_ascii=False,indent=2))
print("TEST FIXTURE ONLY: prepared",len(clips),"audio files; these are NOT Fish Audio")

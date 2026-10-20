#!/usr/bin/env python3
"""Repackage verified RC4 with a tiny definition-only speed adjustment (1.08 -> 1.12)."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json
src=Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC4_STAGING.zip')
dst=Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC5_STAGING.zip')
old='B1.13.1-UX1-FISH398-VOZ-UNICA-RC4-STAGING'
new='B1.13.1-UX1-FISH398-VOZ-UNICA-RC5-STAGING'
with ZipFile(src) as z,ZipFile(dst,'w',ZIP_DEFLATED,compresslevel=4) as out:
 assert z.read('FISH_SPEED_RELEASE.json')
 for info in z.infolist():
  data=z.read(info.filename)
  if info.filename=='index.html':
   s=data.decode()
   assert s.count('const FISH_DEFINITION_SPEED_MULTIPLIER=1.08;')==1
   assert s.count(old)>=1
   s=s.replace('const FISH_DEFINITION_SPEED_MULTIPLIER=1.08;','const FISH_DEFINITION_SPEED_MULTIPLIER=1.12;').replace(old,new)
   data=s.encode()
  elif info.filename.endswith('RELEASE.json'):
   try:
    obj=json.loads(data)
    if obj.get('version')==old:obj['version']=new
    if obj.get('definition_speed_multiplier')==1.08:obj['definition_speed_multiplier']=1.12
    data=json.dumps(obj,ensure_ascii=False,indent=2).encode()
   except (ValueError,TypeError):pass
  out.writestr(info,data)
with ZipFile(src) as a,ZipFile(dst) as b:
 changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
 assert 'index.html' in changed
 assert not any(n.endswith('.mp3') for n in changed)
 assert b.read('index.html').decode().count('FISH_DEFINITION_SPEED_MULTIPLIER=1.12')==1
 print('PASS RC5 +12% definition multiplier; all MP3 identical; changed:',changed)

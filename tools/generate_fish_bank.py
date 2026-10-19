#!/usr/bin/env python3
"""Incremental Fish voice bank casting. Isolated output; never changes production.

Usage: python tools/generate_fish_bank.py --start 1 --count 12
       python tools/generate_fish_bank.py --start 1 --count 398 --all
No automatic fallback to a paid model.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_fish_voice_free_api import MODEL, VOICE_ID, generate

MANIFEST=Path("piper-audio/manifest.json")
OUT=Path("artifacts/fish-bank")
EXPECTED_SHA="35b96d6920647bbe6d17cdf208a5990ea3e2a890c549d308bd93d58abe3e9aa8"
LETTER_NAMES={"A":"a","B":"be","C":"ce","D":"de","E":"e","F":"efe","G":"ge","H":"hache","I":"i","J":"jota","K":"ka","L":"ele","M":"eme","N":"ene","Ñ":"eñe","O":"o","P":"pe","Q":"cu","R":"erre","S":"ese","T":"te","U":"u","V":"ve","W":"doble ve","X":"equis","Y":"i griega","Z":"zeta"}
FIXED=[
"Correcto.","Facu.","Mamba.","Ahora vamos con el otro jugador.","Seguimos.",
"Arrancamos. Vamos con la primera.","Bueno, empezamos. Atención al rosco.",
"Vamos con vos. Primera palabra.","Cuando quieras. Arrancamos.",
"Volvemos a las que quedaron pendientes.","Vamos con las pendientes.",
"Retomamos las que pasaste.","Tiempo.","Se terminó el tiempo.",
"Se terminó el rosco. Vamos a los resultados.",
]

def all_jobs(manifest):
 rows=manifest["rows"]
 assert manifest["bank_sha256"]==EXPECTED_SHA, "Bank changed; revalidate source before generating"
 assert len(rows)==398 and manifest["approved"]==398
 jobs=[]
 for row in rows:
  letter=row["letter"]
  assert letter in LETTER_NAMES
  spoken=(f"Contiene la {LETTER_NAMES[letter]}. " if row["rule"]=="CONTIENE" else f"{LETTER_NAMES[letter]}. ")+row["definition"]
  jobs.append((row["question_file"],spoken,row["question_key"]))
  jobs.append((row["wrong_file"],f"Incorrecto. Era {row['answer']}.",row["wrong_key"]))
 for i,phrase in enumerate(FIXED,1):
  jobs.append((f"fixed{i:02d}.mp3",phrase,phrase))
 assert len(jobs)==811
 assert len(set(x[0] for x in jobs))==811
 return jobs

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--start",type=int,default=1,help="1-based approved definition index")
 ap.add_argument("--count",type=int,default=12,help="number of definitions, each 2 clips")
 ap.add_argument("--all",action="store_true",help="include all fixed conductor phrases")
 ap.add_argument("--max-requests",type=int,default=40,help="hard cap to prevent unexpected usage")
 args=ap.parse_args()
 assert MODEL=="s2.1-pro-free", "Refusing non-free model"
 assert VOICE_ID=="c4a325176443465ab0ba1b0cfa979995"
 assert 1<=args.start<=398 and 1<=args.count<=398 and args.start+args.count-1<=398
 jobs=all_jobs(json.loads(MANIFEST.read_text(encoding="utf-8")))
 selected=jobs[2*(args.start-1):2*(args.start+args.count-1)]
 if args.all:selected+=jobs[796:]
 assert len(selected)<=args.max_requests, "Request count exceeds explicit cap"
 key=os.getenv("FISH_API_KEY","").strip()
 assert key, "FISH_API_KEY missing"
 OUT.mkdir(parents=True,exist_ok=True)
 # generate() writes to its own OUT; switch to isolated directory without changing its API semantics
 import test_fish_voice_free_api as fish
 fish.OUT=OUT
 completed=[]
 for index,(file,text,phrase) in enumerate(selected,1):
  name=Path(file).stem
  target=OUT/file
  if target.exists() and target.stat().st_size>1000:
   audio=target.read_bytes()
   result={"file":file,"text":text,"sha256":hashlib.sha256(audio).hexdigest(),"bytes":len(audio),"cached":True}
  else:
   result=generate(name,text,key)
   result["cached"]=False
  result["phrase"]=phrase
  completed.append(result)
  print(f"Clip {index}/{len(selected)}: {file}",flush=True)
  if index<len(selected):time.sleep(0.8)
 (OUT/"manifest.json").write_text(json.dumps({
  "schema":1,"voice_id":VOICE_ID,"model":MODEL,"source_bank_sha256":EXPECTED_SHA,
  "start":args.start,"count":args.count,"fixed":args.all,
  "clips":completed,"complete":len(completed)==811,
  "scope":"STAGING only; no bank changes or production deployment"
 },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Fish batch completed: {len(completed)} clips",flush=True)

if __name__=="__main__":main()

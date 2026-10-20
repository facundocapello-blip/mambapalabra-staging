#!/usr/bin/env python3
"""Fish RC3 full local match -> 0:0 tie -> sudden death -> winner -> restart.

Uses accelerated Audio mock; checks control flow, NOT acoustic playback duration.
"""
import ast, http.server, json, os
from pathlib import Path
from threading import Thread
from zipfile import ZipFile
from playwright.sync_api import sync_playwright
ZIP=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC3_STAGING.zip")
SITE=Path("dist/fish-sudden-qa-site");SITE.mkdir(parents=True,exist_ok=True)
with ZipFile(ZIP) as z:z.extractall(SITE)
manifest=json.loads(Path("piper-audio/manifest.json").read_text())
answers={row["definition"]:row["answer"] for row in manifest["rows"]}
source=ast.parse(Path("tools/qa_fish_intro_staging.py").read_text())
MOCK=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="MOCK" for t in n.targets))
MOCK=MOCK.replace("},300);return Promise.resolve()","},12);return Promise.resolve()")
os.chdir(SITE)
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Quiet)
Thread(target=server.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{server.server_address[1]}/"
with sync_playwright() as p:
 for name in ("chromium","webkit"):
  browser=getattr(p,name).launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if name=="chromium" else [])
  context=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,locale="es-AR")
  page=context.new_page();errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.add_init_script(MOCK)
  page.goto(url,wait_until="domcontentloaded")
  page.locator("#startBtn").click()
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  for n in range(54):
   page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=12000)
   assert not page.locator("#game").is_hidden(),("premature end",n)
   page.locator("#textAnswer").fill("QA_NO_ES_LA_RESPUESTA_12345")
   page.locator("#sendTextBtn").click()
  page.wait_for_function('document.querySelector("#activeName").textContent.includes("Muerte súbita")',timeout=12000)
  page.wait_for_function('window.__fishLoads.some(x=>x.includes("08_muerte_subita.mp3"))',timeout=12000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  page.locator("#textAnswer").fill("QA_NO_ES_LA_RESPUESTA_12345")
  page.locator("#sendTextBtn").click()
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  clue=page.locator("#questionText").inner_text().strip()
  assert clue in answers,clue
  page.locator("#textAnswer").fill(answers[clue])
  page.locator("#sendTextBtn").click()
  page.wait_for_function('!document.querySelector("#endScreen").hidden',timeout=12000)
  assert "Gana" in page.locator("#winnerText").inner_text()
  page.locator("#playAgainBtn").click()
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  assert page.locator("#timer1").inner_text()=="02:30"
  assert page.evaluate("window.__deviceTTSCalls")==0
  assert not errors,errors
  print(name,"PASS: full 54 wrong answers, tie, Fish sudden-death intro, winner, local restart, no neutral TTS",flush=True)
  context.close();browser.close()
server.shutdown()

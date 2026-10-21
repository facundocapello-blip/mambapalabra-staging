#!/usr/bin/env python3
"""Smoke test the actual isolated GitHub Pages STAGING deployment, not local ZIP."""
import ast,json,os,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="https://facundocapello-blip.github.io/mambapalabra-staging/"
with urllib.request.urlopen(BASE+"STAGING_BUILD.json",timeout=30) as response:
 info=json.load(response)
assert info["version"]==os.getenv("EXPECTED_FISH_VERSION","B1.13.1-UX1-FISH398-VOZ-UNICA-RC3-STAGING"),info
assert info["fish_mp3"]==821,info
assert info["definition_playback_rate"]==1.22,info
assert info["short_turn_cues"]==2,info
print("Live staging build manifest PASS:",info["version"],flush=True)
source=ast.parse(Path("tools/qa_fish_intro_staging.py").read_text())
MOCK=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="MOCK" for t in n.targets))
with sync_playwright() as p:
 for name in ("chromium","webkit"):
  browser=getattr(p,name).launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if name=="chromium" else [])
  context=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,locale="es-AR")
  page=context.new_page()
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.add_init_script(MOCK)
  page.goto(BASE,wait_until="domcontentloaded",timeout=45000)
  assert page.locator("#startBtn").is_visible()
  page.locator("#startBtn").click()
  page.wait_for_function('window.__fishLoads.some(x=>x.includes("03_intro_inicio.mp3"))',timeout=15000)
  assert page.locator("#timer1").inner_text()=="02:30"
  page.wait_for_function('window.__fishLoads.some(x=>x.includes("04_intro_solo.mp3"))',timeout=15000)
  page.wait_for_function('window.__fishLoads.some(x=>x.includes("fish-bank/q"))',timeout=15000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  assert page.evaluate("window.__deviceTTSCalls")==0
  assert not page.evaluate('window.__fishLoads.some(x=>x.includes("piper-audio/"))')
  assert not errors,errors
  request=context.request.get(BASE+"fish-bank/q0001.mp3",timeout=30000)
  assert request.ok and len(request.body())>1000,(request.status,len(request.body()))
  print(name,"PASS: live HTTPS staging, intro, Fish definition, playable turn, MP3 fetch, no neutral TTS",flush=True)
  context.close();browser.close()

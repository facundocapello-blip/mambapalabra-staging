#!/usr/bin/env python3
"""RC6 short-cue real STAGING Supabase room test: two independent HTTPS browser sessions.

Creates a temporary QA room through the existing public staging UI. Audio is
mocked only to shorten playback; online room backend is NOT mocked.
"""
import ast,json,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE="https://facundocapello-blip.github.io/mambapalabra-staging/"
manifest=json.loads(Path("piper-audio/manifest.json").read_text())
answers={row["definition"]:row["answer"] for row in manifest["rows"]}
source=ast.parse(Path("tools/qa_fish_intro_staging.py").read_text())
MOCK=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="MOCK" for t in n.targets))
suffix=uuid.uuid4().hex[:5]
with sync_playwright() as p:
 for name in ("chromium","webkit"):
  browser=getattr(p,name).launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if name=="chromium" else [])
  contexts=[browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,locale="es-AR") for _ in range(2)]
  host,guest=[c.new_page() for c in contexts]
  errors=[]
  for page in (host,guest):
   page.on("pageerror",lambda e:errors.append(str(e)))
   page.add_init_script(MOCK)
   page.goto(BASE,wait_until="domcontentloaded",timeout=45000)
   page.wait_for_function('!!(window.supabase&&typeof window.supabase.createClient==="function")',timeout=20000)
  host.evaluate(f'document.querySelector("#onlineName").value="QAHost{suffix}"')
  host.locator("#createOnlineBtn").click()
  host.wait_for_function('document.querySelector("#roomCode").textContent.length===6',timeout=30000)
  code=host.locator("#roomCode").inner_text()
  print(name,"created staging room",code,flush=True)
  guest.locator("#showJoinBtn").click()
  guest.locator("#onlineName").fill("QAGuest"+suffix)
  guest.locator("#roomCodeInput").fill(code)
  guest.locator("#joinOnlineBtn").click()
  host.wait_for_function('!document.querySelector("#game").hidden',timeout=35000)
  guest.wait_for_function('!document.querySelector("#game").hidden',timeout=35000)
  host.wait_for_function('window.__fishLoads.some(x=>x.includes("05_intro_online.mp3"))',timeout=20000)
  guest.wait_for_function('window.__fishLoads.some(x=>x.includes("05_intro_online.mp3"))',timeout=20000)
  assert guest.locator("#timer1").inner_text()=="02:30"
  host.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=20000)
  assert guest.locator("#micBtn").is_disabled()
  clue=host.locator("#questionText").inner_text().strip()
  assert clue in answers,clue
  host.locator("#textAnswer").fill(answers[clue])
  host.locator("#sendTextBtn").click()
  host.wait_for_function('document.querySelector("#scoreMamba").textContent==="1"',timeout=15000)
  guest.wait_for_function('document.querySelector("#scoreMamba").textContent==="1"',timeout=30000)
  host.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=20000)
  host.locator("#textAnswer").fill("QA_WRONG_987654")
  host.locator("#sendTextBtn").click()
  guest.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=35000)
  assert guest.evaluate('window.__fishLoads.some(x=>x.includes("09_incorrecto_corto.mp3"))'),"Guest missed short Incorrecto handoff"
  assert not guest.evaluate('window.__fishLoads.some(x=>x.includes("fish-bank/w"))'),"Guest played long incorrect answer"
  assert host.locator("#micBtn").is_disabled()
  guest.locator("#passBtn").click()
  host.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=35000)
  assert host.evaluate('window.__fishLoads.some(x=>x.includes("10_pasapalabra_corto.mp3"))'),"Host missed short Pasapalabra handoff"
  assert guest.locator("#micBtn").is_disabled()
  assert not errors,errors
  assert host.evaluate("window.__deviceTTSCalls")==0
  assert guest.evaluate("window.__deviceTTSCalls")==0
  print(name,"PASS: real staging Supabase create/join, Fish intros, score sync, wrong handoff, guest pass, return, zero device TTS",flush=True)
  for c in contexts:c.close()
  browser.close()

#!/usr/bin/env python3
"""Chromium/WebKit RC6: clue speed, short pass/wrong cues, turn and timer regressions."""
import ast, http.server, os
from pathlib import Path
from threading import Thread
from zipfile import ZipFile
from playwright.sync_api import sync_playwright

PACKAGE=Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC6_STAGING.zip').resolve()
SITE=Path('dist/fish-rc6-qa-site').resolve()
SITE.mkdir(parents=True,exist_ok=True)
with ZipFile(PACKAGE) as z:z.extractall(SITE)
source=ast.parse(Path('tools/qa_fish_definition_speed_rc4.py').read_text())
MOCK=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MOCK' for t in n.targets))
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
os.chdir(SITE)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_address[1]}/'
with sync_playwright() as p:
 for name in ('chromium','webkit'):
  browser=getattr(p,name).launch(headless=True,args=['--autoplay-policy=no-user-gesture-required'] if name=='chromium' else [])
  context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,locale='es-AR')
  page=context.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script(MOCK)
  page.goto(url,wait_until='domcontentloaded',timeout=30000)
  page.locator('#startBtn').click()
  page.wait_for_function('window.__rates.some(x=>x.path.includes("fish-bank/q"))',timeout=15000)
  assert page.locator('#timer1').inner_text()=='02:30'
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  rates=page.evaluate('window.__rates')
  questions=[r for r in rates if 'fish-bank/q' in r['path']]
  assert questions and all(abs(r['rate']-1.22)<.00001 and r['pitch'] for r in questions),questions
  first_len=len(rates)
  page.locator('#passBtn').click()
  page.wait_for_function('document.querySelector("#activeName").textContent==="Facu"&&!document.querySelector("#micBtn").disabled',timeout=15000)
  segment=page.evaluate('window.__rates')[first_len:]
  paths=[r['path'] for r in segment]
  assert sum('10_pasapalabra_corto.mp3' in x for x in paths)==1,paths
  assert not any('fixed04.mp3' in x or 'fixed02.mp3' in x or 'v33_name_facu.mp3' in x for x in paths),paths
  assert all(abs(r['rate']-1.22)<.00001 for r in segment if 'fish-bank/q' in r['path']),segment
  assert page.locator('#timer1').inner_text()=='02:30'
  first_len=len(page.evaluate('window.__rates'))
  page.locator('#textAnswer').fill('QA_WRONG_987654')
  page.locator('#sendTextBtn').click()
  page.wait_for_function('document.querySelector("#wrongFacu").textContent==="1"&&!document.querySelector("#micBtn").disabled',timeout=15000)
  segment=page.evaluate('window.__rates')[first_len:]
  paths=[r['path'] for r in segment]
  assert sum('09_incorrecto_corto.mp3' in x for x in paths)==1,paths
  assert not any('fish-bank/w' in x or '07_incorrecto.mp3' in x or 'fixed04.mp3' in x or 'fixed02.mp3' in x for x in paths),paths
  assert all(abs(r['rate']-1.22)<.00001 for r in segment if 'fish-bank/q' in r['path']),segment
  page.evaluate('document.querySelector("#repeatBtn").click()')
  page.wait_for_function('document.querySelector("#micBtn").disabled',timeout=3000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=12000)
  assert not errors,errors
  assert page.evaluate('window.__deviceTTSCalls')==0
  assert not page.evaluate('window.__fishLoads.some(x=>x.includes("piper-audio/"))')
  print(name,'PASS: 1.22x clues, short pass/incorrect, no name/answer recitation, timer, repeat, zero TTS',flush=True)
  context.close();browser.close()
server.shutdown()

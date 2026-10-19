#!/usr/bin/env python3
"""Chromium/WebKit isolated staging regression: Fish intro -> first clue -> correct/pass/wrong/restart."""
from pathlib import Path
from zipfile import ZipFile
import http.server, threading, json, os
from playwright.sync_api import sync_playwright

zip_path=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH_VOCES_INTROS_RC1_STAGING.zip")
site=Path("dist/fish-qa-site")
site.mkdir(parents=True,exist_ok=True)
with ZipFile(zip_path) as z:
 z.extractall(site)
 manifest=json.loads(Path("piper-audio/manifest.json").read_text())
 answers={x["definition"]:x["answer"] for x in manifest["rows"]}
os.chdir(site)
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),http.server.SimpleHTTPRequestHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{server.server_address[1]}/"
MOCK=r"""(() => {
window.__fishLoads=[];
const originalFetch=window.fetch.bind(window);
window.fetch=(input,...args)=>{const path=typeof input==="string"?input:input?.url||"";if(path.includes("fish-audio/")||path.includes("piper-audio/"))window.__fishLoads.push(path);return originalFetch(input,...args)};
class MockAudio {
 constructor(){this._src="";this.volume=1;this.playbackRate=1;this.currentTime=0;this.duration=1;this.paused=true;this.onplaying=null;this.onended=null;this.onerror=null;this._timer=null;}
 set src(v){this._src=v;this.currentTime=0;}
 get src(){return this._src;}
 setAttribute(){}
 pause(){this.paused=true;clearTimeout(this._timer)}
 play(){this.paused=false;setTimeout(()=>{if(!this.paused&&this.onplaying)this.onplaying()},8);clearTimeout(this._timer);this._timer=setTimeout(()=>{if(!this.paused){this.currentTime=this.duration;if(this.onended)this.onended()}},300);return Promise.resolve()}
}
window.Audio=MockAudio;
})();"""
with sync_playwright() as p:
 for name in ("chromium","webkit"):
  engine=getattr(p,name)
  browser=engine.launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if name=="chromium" else [])
  context=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,locale="es-AR")
  page=context.new_page()
  errors=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.add_init_script(MOCK)
  page.goto(url,wait_until="domcontentloaded",timeout=60000)
  page.locator("#startBtn").click()
  page.wait_for_function('window.__fishLoads.some(x=>x.includes("03_intro_inicio.mp3"))',timeout=15000)
  state=page.evaluate('({turn:game.turnState,time:game.players[0].timeMs})')
  assert state=={"turn":"SWITCHING","time":150000},state
  page.wait_for_function('window.__fishLoads.some(x=>x.includes("04_intro_solo.mp3"))',timeout=15000)
  state=page.evaluate('({turn:game.turnState,time:game.players[0].timeMs})')
  assert state=={"turn":"SWITCHING","time":150000},state
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=20000)
  assert page.evaluate('window.__fishLoads.some(x=>x.includes("piper-audio/"))')
  first=page.evaluate('currentItem().answer')
  assert first
  page.locator("#textAnswer").fill(first)
  page.locator("#sendTextBtn").click()
  page.wait_for_function('window.__fishLoads.some(x=>x.includes("06_correcto.mp3"))',timeout=12000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled&&document.querySelector("#scoreMamba").textContent==="1"',timeout=15000)
  # Repeat: direct handler invocation because original V2 hides the recovery button in normal play.
  page.evaluate('document.querySelector("#repeatBtn").click()')
  page.wait_for_function('game.turnState==="READING"',timeout=4000)
  before=page.evaluate('game.players[0].timeMs')
  page.wait_for_timeout(80)
  after=page.evaluate('game.players[0].timeMs')
  assert before==after,(before,after)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=12000)
  page.locator("#passBtn").click()
  page.wait_for_function('document.querySelector("#activeName").textContent==="Facu"&&!document.querySelector("#micBtn").disabled',timeout=15000)
  page.locator("#textAnswer").fill("RESPUESTA_INVALIDA_98765")
  page.locator("#sendTextBtn").click()
  page.wait_for_function('document.querySelector("#wrongFacu").textContent==="1"',timeout=7000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  count=page.evaluate('window.__fishLoads.filter(x=>x.includes("03_intro_inicio.mp3")).length')
  solo=page.evaluate('window.__fishLoads.filter(x=>x.includes("04_intro_solo.mp3")).length')
  page.on('dialog',lambda dialog:dialog.accept())
  page.evaluate('document.querySelector("#restartBtn").click()')
  page.wait_for_function(f'window.__fishLoads.filter(x=>x.includes("04_intro_solo.mp3")).length>{solo}',timeout=12000)
  page.wait_for_function('game.turnState==="ANSWERING"',timeout=15000)
  assert page.evaluate('window.__fishLoads.filter(x=>x.includes("03_intro_inicio.mp3")).length')==count
  assert not errors,errors
  print(f"{name} PASS: intro/clock/first clue/correct/repeat/pass/wrong/restart; loads={page.evaluate('window.__fishLoads.length')}",flush=True)
  context.close()
  browser.close()
server.shutdown()
print("Fish staging Chromium+WebKit regression passed")

#!/usr/bin/env python3
"""Browser regression for selective Fish definition speed, local play and controls."""
import http.server
import os
import threading
from pathlib import Path
from zipfile import ZipFile
from playwright.sync_api import sync_playwright

PACKAGE=Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC4_STAGING.zip').resolve()
SITE=Path('dist/fish-rc4-qa-site').resolve()
SITE.mkdir(parents=True,exist_ok=True)
with ZipFile(PACKAGE) as z:z.extractall(SITE)

MOCK=r'''(() => {
window.__rates=[];window.__fishLoads=[];window.__deviceTTSCalls=0;
window.__blobPaths=new WeakMap();window.__urlPaths=new Map();
if(window.speechSynthesis){window.speechSynthesis.speak=()=>{window.__deviceTTSCalls++}}
const originalFetch=window.fetch.bind(window),originalObjectURL=URL.createObjectURL.bind(URL);
window.fetch=async(input,...args)=>{const path=typeof input==="string"?input:input?.url||"";if(path.includes("fish-audio/")||path.includes("fish-bank/")||path.includes("piper-audio/"))window.__fishLoads.push(path);const response=await originalFetch(input,...args);const originalBlob=response.blob.bind(response);response.blob=async()=>{const blob=await originalBlob();window.__blobPaths.set(blob,path);return blob;};return response;};
URL.createObjectURL=blob=>{const url=originalObjectURL(blob);window.__urlPaths.set(url,window.__blobPaths.get(blob)||"");return url;};
class MockAudio {
 constructor(){this._src="";this.volume=1;this.playbackRate=1;this.currentTime=0;this.duration=1;this.paused=true;this.onplaying=null;this.onended=null;this.onerror=null;this._timer=null;this.preservesPitch=true;}
 set src(v){this._src=v;this.currentTime=0;}
 get src(){return this._src;}
 setAttribute(){}
 pause(){this.paused=true;clearTimeout(this._timer)}
 play(){window.__rates.push({path:window.__urlPaths.get(this.src)||this.src,rate:this.playbackRate,pitch:this.preservesPitch});this.paused=false;setTimeout(()=>{if(!this.paused&&this.onplaying)this.onplaying()},8);clearTimeout(this._timer);this._timer=setTimeout(()=>{if(!this.paused){this.currentTime=this.duration;if(this.onended)this.onended()}},110);return Promise.resolve()}
}
window.Audio=MockAudio;
})();'''

class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

os.chdir(SITE)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Quiet)
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE=f'http://127.0.0.1:{server.server_address[1]}/'
with sync_playwright() as p:
 for name in ('chromium','webkit'):
  launch_kwargs={'headless':True}
  if name=='chromium':launch_kwargs['args']=['--autoplay-policy=no-user-gesture-required']
  browser=getattr(p,name).launch(**launch_kwargs)
  ctx=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,locale='es-AR')
  page=ctx.new_page();errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.add_init_script(MOCK)
  page.goto(BASE,wait_until='domcontentloaded',timeout=30000)
  page.locator('#startBtn').click()
  page.wait_for_function('window.__rates.some(x=>/fish-bank\/q\d{4}\.mp3/.test(x.path))',timeout=15000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  rates=page.evaluate('window.__rates')
  intros=[r for r in rates if 'fish-audio/0' in r['path']]
  questions=[r for r in rates if 'fish-bank/q' in r['path']]
  assert intros and questions,rates
  assert all(abs(r['rate']-.92)<.00001 for r in intros),intros
  assert all(abs(r['rate']-(.92*1.08))<.00001 and r['pitch'] for r in questions),questions
  assert page.locator('#timer1').inner_text()=='02:30'
  page.locator('#textAnswer').fill('QA_RESPUESTA_INVALIDA_12345')
  page.locator('#sendTextBtn').click()
  page.wait_for_function('window.__rates.some(x=>/fish-bank\/w\d{4}\.mp3/.test(x.path))',timeout=15000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  rates=page.evaluate('window.__rates')
  wrong=[r for r in rates if 'fish-bank/w' in r['path']]
  assert wrong and all(abs(r['rate']-.92)<.00001 for r in wrong),wrong
  page.evaluate('document.querySelector("#repeatBtn").click()')
  page.wait_for_function('document.querySelector("#micBtn").disabled',timeout=3000)
  page.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=12000)
  assert not errors,errors
  assert page.evaluate('window.__deviceTTSCalls')==0
  assert not page.evaluate('window.__fishLoads.some(x=>x.includes("piper-audio/"))')
  print(name,'PASS: +8% definitions, unchanged intro/wrong answer, pitch preserved, turn/repeat/clock, no device TTS',flush=True)
  ctx.close();browser.close()
server.shutdown()

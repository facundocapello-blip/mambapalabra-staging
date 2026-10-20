#!/usr/bin/env python3
"""Two independent mobile browser sessions with simulated shared room backend.

No real Supabase calls. This is an automated online flow regression, not a live
backend or physical iPhone validation.
"""
from pathlib import Path
from zipfile import ZipFile
from threading import Lock, Thread
from copy import deepcopy
import ast, http.server, json, os, uuid
from playwright.sync_api import sync_playwright

ZIP=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC3_STAGING.zip")
SITE=Path("dist/fish-online-qa-site")
SITE.mkdir(parents=True,exist_ok=True)
with ZipFile(ZIP) as z:z.extractall(SITE)
source=ast.parse(Path("tools/qa_fish_intro_staging.py").read_text())
AUDIO_MOCK=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="MOCK" for t in n.targets))
manifest=json.loads(Path("piper-audio/manifest.json").read_text())
answers={row["definition"]:row["answer"] for row in manifest["rows"]}

class Backend:
 def __init__(self):
  self.lock=Lock()
  self.room=None
 def call(self,payload):
  with self.lock:
   action=payload["action"]
   if action=="create":
    code="QA"+uuid.uuid4().hex[:4].upper()
    self.room={"code":code,"host_name":payload["name"],"guest_name":None,"version":1,"game_state":payload.get("game_state",{}),"status":"waiting"}
    return {"code":code,"token":str(uuid.uuid4())}
   if not self.room or payload.get("code")!=self.room["code"]:
    return {"error":"room_not_found"}
   if action=="join":
    self.room["guest_name"]=payload["name"]
    self.room["version"]+=1
    return {"code":self.room["code"],"token":str(uuid.uuid4())}
   if action=="get":return {"room":deepcopy(self.room)}
   if action=="sync":
    self.room["version"]+=1
    self.room["game_state"]=deepcopy(payload["game_state"])
    self.room["status"]=payload.get("status","playing")
    return {"version":self.room["version"]}
   if action=="resume":return {"room":deepcopy(self.room)}
   return {"error":"unsupported_action"}
backend=Backend()
SUPABASE_STUB="""window.supabase={createClient:()=>({
 functions:{invoke:async(name,{body})=>({data:await window.__qaRoomCall(body),error:null})},
 channel:()=>({on(){return this},subscribe(fn){Promise.resolve().then(()=>fn('SUBSCRIBED'));return this}}),
 removeChannel:async()=>{}
})};"""
os.chdir(SITE)
class QuietHandler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),QuietHandler)
Thread(target=server.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{server.server_address[1]}/"

with sync_playwright() as p:
 for browser_name in ("chromium","webkit"):
  browser=getattr(p,browser_name).launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if browser_name=="chromium" else [])
  host_ctx=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,locale="es-AR")
  guest_ctx=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,locale="es-AR")
  host=host_ctx.new_page();guest=guest_ctx.new_page()
  errors=[]
  for page in (host,guest):
   page.on("pageerror",lambda e:errors.append(str(e)))
   page.add_init_script(AUDIO_MOCK)
   page.expose_binding("__qaRoomCall",lambda source,payload:backend.call(payload))
   page.route("**/supabase.min.js",lambda route:route.fulfill(status=200,content_type="text/javascript",body=SUPABASE_STUB))
   page.goto(url,wait_until="domcontentloaded")
  host.evaluate('document.querySelector("#onlineName").value="QA Anfitrion"')
  host.locator("#createOnlineBtn").click()
  host.wait_for_function('document.querySelector("#roomCode").textContent.length===6',timeout=12000)
  code=host.locator("#roomCode").inner_text()
  guest.locator("#showJoinBtn").click()
  guest.locator("#onlineName").fill("QA Invitado")
  guest.locator("#roomCodeInput").fill(code)
  guest.locator("#joinOnlineBtn").click()
  host.wait_for_function('!document.querySelector("#game").hidden',timeout=20000)
  guest.wait_for_function('!document.querySelector("#game").hidden',timeout=20000)
  host.wait_for_function('window.__fishLoads.some(x=>x.includes("05_intro_online.mp3"))',timeout=15000)
  guest.wait_for_function('window.__fishLoads.some(x=>x.includes("05_intro_online.mp3"))',timeout=15000)
  assert host.locator("#timer1").inner_text()=="02:30"
  assert guest.locator("#timer1").inner_text()=="02:30"
  host.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  assert guest.locator("#micBtn").is_disabled()
  clue=host.locator("#questionText").inner_text().strip()
  assert clue in answers,clue
  host.locator("#textAnswer").fill(answers[clue])
  host.locator("#sendTextBtn").click()
  host.wait_for_function('document.querySelector("#scoreMamba").textContent==="1"',timeout=12000)
  guest.wait_for_function('document.querySelector("#scoreMamba").textContent==="1"',timeout=18000)
  host.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=15000)
  host.locator("#textAnswer").fill("RESPUESTA_INVALIDA_98765")
  host.locator("#sendTextBtn").click()
  guest.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=20000)
  assert host.locator("#micBtn").is_disabled()
  guest.locator("#passBtn").click()
  host.wait_for_function('!document.querySelector("#micBtn").disabled',timeout=20000)
  assert guest.locator("#micBtn").is_disabled()
  assert not errors,errors
  assert host.evaluate("window.__deviceTTSCalls")==0
  assert guest.evaluate("window.__deviceTTSCalls")==0
  print(browser_name,"PASS: independent sessions, both Fish intros, paused clock, score sync, wrong handoff, guest pass, return, zero device TTS",flush=True)
  host_ctx.close();guest_ctx.close();browser.close()
  backend.room=None
server.shutdown()

#!/usr/bin/env python3
"""Check spoken verdict actually starts after voice recognition in STAGING."""
import json
import pathlib
from playwright.sync_api import sync_playwright

URL="https://mambapalabra-b1131-ux1-staging.floot.app/"
m=json.loads(pathlib.Path("piper-audio/manifest.json").read_text(encoding="utf-8"))
answers={r["definition"]:r["answer"] for r in m["rows"]}
MOCK="""(() => {
class FakeSR{
 constructor(){this.ended=false;}
 start(){window.__sr=this;queueMicrotask(()=>this.onstart?.());}
 stop(){setTimeout(()=>this.finish(),80);}
 abort(){setTimeout(()=>this.finish(),20);}
 finish(){if(this.ended)return;this.ended=true;this.onend?.();}
 emit(text){const g=[{transcript:text}];g.isFinal=false;this.onresult?.({resultIndex:0,results:[g]});this.onspeechend?.();}
}
window.SpeechRecognition=FakeSR;window.webkitSpeechRecognition=FakeSR;
})();"""

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"])
    context=browser.new_context(viewport={"width":1280,"height":720},locale="es-AR")
    page=context.new_page()
    page.add_init_script(MOCK)
    errors=[]
    audio=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.on("response",lambda r:audio.append((r.url,r.status)) if "/piper-audio/" in r.url and r.url.endswith(".mp3") else None)
    try:
        page.goto(URL,wait_until="domcontentloaded",timeout=90000)
        page.frame_locator("iframe").locator("#lobby").wait_for(state="visible",timeout=90000)
        f=next(f for f in page.frames if f != page.main_frame and f.locator("#lobby").count())
        f.locator("#startBtn").click()
        f.locator("#game").wait_for(state="visible",timeout=40000)
        f.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=60000)
        f.evaluate("""() => {
          window.__verdictEvents=[];
          new MutationObserver(()=>{
            window.__verdictEvents.push([performance.now(),document.querySelector('#voiceNote').textContent]);
          }).observe(document.querySelector('#voiceNote'),{childList:true,characterData:true,subtree:true});
        }""")
        def say(text,tag,timeout=15000):
            f.locator("#micBtn").click()
            f.wait_for_function("() => document.querySelector('#micBtn').textContent.includes('ESCUCHANDO')",timeout=4000)
            t0=f.evaluate("""text=>{
              window.__verdictEvents=[];
              const start=performance.now();
              window.__sr.emit(text);
              return start;
            }""",text)
            try:
                f.wait_for_function("""() => {
                  const e=window.__verdictEvents;
                  return e.some(x=>x[1].includes('Cargando audio'))&&
                         e.some(x=>x[1].includes('Voz del conductor grabada.'));
                }""",timeout=timeout)
            except Exception:
                print("DEBUG verdict",tag,f.evaluate("""() => ({
                  events:window.__verdictEvents,voice:document.querySelector('#voiceNote').textContent,
                  transcript:document.querySelector('#transcript').textContent,
                  score:document.querySelector('#scoreMamba').textContent,
                  phaseMicDisabled:document.querySelector('#micBtn').disabled,
                  speechButton:document.querySelector('#soundBtn').textContent
                })"""),"MP3",audio[-8:],"JS errors",errors,flush=True)
                raise
            events=f.evaluate("window.__verdictEvents")
            started=next(x[0] for x in events if "Voz del conductor grabada." in x[1])
            elapsed=started-t0
            print(f"{tag}: {elapsed:.0f} ms fin de voz -> reproducción de conductor",flush=True)
            return elapsed
        clue=f.locator("#questionText").inner_text().strip()
        assert clue in answers,clue
        correct=say(answers[clue],"Correcto")
        f.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=60000)
        wrong=say("respuesta inexistente","Incorrecto")
        assert any("/fixed01.mp3" in url and status==200 for url,status in audio),"Falta audio Correcto"
        assert any("/w" in url and status==200 for url,status in audio),"Falta audio Incorrecto"
        assert correct<10000 and wrong<10000
        assert not errors,errors
        print("Spoken audio QA PASS",flush=True)
    finally:
        context.close()
        browser.close()

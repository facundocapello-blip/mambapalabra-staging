#!/usr/bin/env python3
"""VR1: reproduce old voice-latency bug and verify faster verdict in real STAGING."""
import json
import pathlib
import threading
import time
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from playwright.sync_api import sync_playwright

STAGING="https://mambapalabra-b1131-ux1-staging.floot.app/"
ZIP=pathlib.Path("dist/MAMBAPALABRA_B1.13.1_UX1_PIPER398_STAGING.zip")
MANIFEST=json.loads(pathlib.Path("piper-audio/manifest.json").read_text(encoding="utf-8"))
ANSWERS={r["definition"]:r["answer"] for r in MANIFEST["rows"]}
ROOT=pathlib.Path("artifacts/voice-baseline")
ROOT.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
    (ROOT/"index.html").write_bytes(z.read("index.html"))
    (ROOT/"new-audio").mkdir(exist_ok=True)
    (ROOT/"new-audio/unlock.mp3").write_bytes(z.read("new-audio/unlock.mp3"))
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
BASELINE=f"http://127.0.0.1:{server.server_port}/index.html"

MOCK=r"""(() => {
class FakeSpeechRecognition {
 constructor(){this.ended=false;this.stopped=false;}
 start(){window.__voiceMock=this;queueMicrotask(()=>this.onstart?.());}
 stop(){this.stopped=true;setTimeout(()=>this.finish(),900);}
 abort(){this.stopped=true;setTimeout(()=>this.finish(),20);}
 finish(){if(this.ended)return;this.ended=true;this.onend?.();}
 emit(text,final=false){const group=[{transcript:text,confidence:.96}];group.isFinal=final;this.onresult?.({resultIndex:0,results:[group]});}
 endSpeech(){this.onspeechend?.();}
}
window.SpeechRecognition=FakeSpeechRecognition;
window.webkitSpeechRecognition=FakeSpeechRecognition;
})();"""

def wait(page,fn,timeout=5000):
    page.wait_for_function(fn,timeout=timeout)

def setup(engine,label,baseline=False):
    browser=engine.launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if label=="chromium" else [])
    context=browser.new_context(viewport={"width":1280,"height":720},locale="es-AR")
    page=context.new_page()
    page.add_init_script(MOCK)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(BASELINE if baseline else STAGING,wait_until="domcontentloaded",timeout=90000)
    if baseline:
        frame=page.main_frame
    else:
        page.frame_locator("iframe").locator("#lobby").wait_for(state="visible",timeout=90000)
        frame=next(f for f in page.frames if f != page.main_frame and f.locator("#lobby").count())
    frame.evaluate("document.querySelector('#soundBtn').click()")
    frame.locator("#startBtn").click(timeout=20000)
    frame.locator("#game").wait_for(state="visible",timeout=40000)
    frame.locator("#micBtn").wait_for(state="visible",timeout=40000)
    frame.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=30000)
    return browser,context,page,frame,errors

def voice(frame,text,final=False):
    frame.locator("#micBtn").click()
    frame.wait_for_function("() => document.querySelector('#micBtn').textContent.includes('ESCUCHANDO')",timeout=4000)
    return frame.evaluate("""({text,final})=>{
      const rec=window.__voiceMock;
      rec.emit(text,final);
      const at=performance.now();
      rec.endSpeech();
      return at;
    }""",{"text":text,"final":final})

def change(frame,selector,old,timeout=1200):
    frame.wait_for_function("""([sel,old])=>document.querySelector(sel).textContent.trim()!==old""",arg=[selector,old],timeout=timeout)
    return frame.evaluate("performance.now()")

with sync_playwright() as p:
    # Reproducción en el HTML anterior: solo hay resultado parcial y el motor
    # no entrega final. El score permanece igual incluso tras terminar de hablar.
    browser,context,page,frame,errors=setup(p.chromium,"chromium",baseline=True)
    try:
        clue=frame.locator("#questionText").inner_text().strip()
        assert clue in ANSWERS
        old=frame.locator("#scoreMamba").inner_text()
        t0=voice(frame,ANSWERS[clue])
        page.wait_for_timeout(520)
        assert frame.locator("#scoreMamba").inner_text()==old, "La base antigua no reproduce el retraso"
        print("[BASELINE] Bug reproducido: sin valoración 520 ms después del fin de voz",flush=True)
        page.wait_for_timeout(700)
        assert frame.locator("#scoreMamba").inner_text()==old, "La base antigua aceptó inesperadamente el parcial"
        assert not errors,errors
    finally:
        context.close()
        browser.close()
    for label in ("chromium","webkit"):
        engine=getattr(p,label)
        browser,context,page,frame,errors=setup(engine,label)
        try:
            clue=frame.locator("#questionText").inner_text().strip()
            assert clue in ANSWERS,clue
            old=frame.locator("#scoreMamba").inner_text()
            t0=voice(frame,ANSWERS[clue])
            elapsed=change(frame,"#scoreMamba",old)-t0
            assert elapsed<350,f"Correcto tardó {elapsed:.0f} ms"
            print(f"[{label}] Correcto con parcial: {elapsed:.0f} ms",flush=True)
            frame.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=3000)
            old=frame.locator("#wrongMamba").inner_text()
            t0=voice(frame,"palabra equivocada")
            timer=frame.locator("#timer1").inner_text()
            page.wait_for_timeout(150)
            assert frame.locator("#timer1").inner_text()==timer,"Reloj avanzó durante VALIDATING"
            elapsed=change(frame,"#wrongMamba",old)-t0
            assert 180<=elapsed<650,f"Incorrecto tardó {elapsed:.0f} ms"
            print(f"[{label}] Incorrecto con parcial: {elapsed:.0f} ms",flush=True)
            frame.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=3000)
            before=frame.locator("#activeName").inner_text().strip()
            t0=voice(frame,"pasapalabra")
            frame.wait_for_function("""old=>document.querySelector('#activeName').textContent.trim()!==old""",arg=before,timeout=700)
            elapsed=frame.evaluate("performance.now()")-t0
            assert elapsed<350,f"Pasapalabra tardó {elapsed:.0f} ms"
            print(f"[{label}] Pasapalabra por voz: {elapsed:.0f} ms",flush=True)
            frame.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=3000)
            clue=frame.locator("#questionText").inner_text().strip()
            assert clue in ANSWERS,clue
            old=frame.locator("#scoreMamba").inner_text()
            wrong_before=frame.locator("#wrongMamba").inner_text()
            frame.locator("#micBtn").click()
            frame.wait_for_function("() => document.querySelector('#micBtn').textContent.includes('ESCUCHANDO')",timeout=4000)
            frame.evaluate("""answer=>{
              const rec=window.__voiceMock;
              rec.emit("respuesta incorrecta",false);
              rec.endSpeech();
              setTimeout(()=>rec.emit(answer,true),130);
            }""",ANSWERS[clue])
            change(frame,"#scoreMamba",old,700)
            assert frame.locator("#wrongMamba").inner_text()==wrong_before,"Parcial incorrecto ganó al resultado final"
            print(f"[{label}] Final correcto prevalece sobre parcial incorrecto",flush=True)
            frame.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=3000)
            correct_before=frame.locator("#scoreMamba").inner_text()
            wrong_before=frame.locator("#wrongMamba").inner_text()
            frame.locator("#micBtn").click()
            frame.wait_for_function("() => document.querySelector('#micBtn').textContent.includes('ESCUCHANDO')",timeout=4000)
            frame.evaluate("window.__voiceMock.endSpeech()")
            page.wait_for_timeout(1150)
            assert frame.locator("#scoreMamba").inner_text()==correct_before
            assert frame.locator("#wrongMamba").inner_text()==wrong_before
            frame.wait_for_function("() => !document.querySelector('#micBtn').disabled",timeout=2000)
            print(f"[{label}] Silencio: sin falso resultado; vuelve a ANSWERING",flush=True)
            assert not errors,errors
            print(f"[{label}] QA VR1 PASS",flush=True)
        finally:
            context.close()
            browser.close()
server.shutdown()

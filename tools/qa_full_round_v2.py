#!/usr/bin/env python3
"""E2E STAGING: inicio -> acierto -> fin de ambos relojes -> resultado -> reinicio."""
import json
import urllib.request
from playwright.sync_api import sync_playwright

URL="https://mambapalabra-b1131-ux1-staging.floot.app/"
MANIFEST="https://raw.githubusercontent.com/facundocapello-blip/mambapalabra-staging/qa/piper-fast-letter-v2/piper-audio/manifest.json"
with urllib.request.urlopen(MANIFEST,timeout=30) as r:
    answers={x["definition"]:x["answer"] for x in json.load(r)["rows"]}

with sync_playwright() as p:
    for engine_name in ("chromium","webkit"):
        engine=getattr(p,engine_name)
        browser=engine.launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if engine_name=="chromium" else [])
        context=browser.new_context(viewport={"width":1280,"height":720},locale="es-AR")
        page=context.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        try:
            page.goto(URL,wait_until="domcontentloaded",timeout=90000)
            f=page.frame_locator("iframe")
            f.locator("#lobby").wait_for(state="visible",timeout=90000)
            frame=next(fr for fr in page.frames if fr!=page.main_frame and fr.locator("#lobby").count())
            frame.evaluate("document.querySelector('#soundBtn').click()")
            frame.evaluate("""() => {
              const sel=document.querySelector("#timerSelect");
              const option=document.createElement("option");
              option.value="5";option.textContent="5 segundos QA";sel.appendChild(option);sel.value="5";
            }""")
            f.get_by_role("button",name="Jugar local").click()
            f.locator("#game").wait_for(state="visible",timeout=40000)
            frame.wait_for_function("() => !document.querySelector('#sendTextBtn').disabled",timeout=15000)
            clue=f.locator("#questionText").inner_text().strip()
            assert clue in answers,clue
            f.locator("#textAnswer").fill(answers[clue])
            f.locator("#sendTextBtn").click()
            frame.wait_for_function("() => +document.querySelector('#scoreMamba').textContent >= 1",timeout=5000)
            print(f"[{engine_name}] Acierto en flujo completo",flush=True)
            f.locator("#endScreen").wait_for(state="visible",timeout=30000)
            assert "RESULTADO FINAL" in f.locator("#endScreen").inner_text()
            assert f.locator("#finalMamba").inner_text().strip()=="1"
            print(f"[{engine_name}] Fin de tiempo y resultado final",flush=True)
            f.locator("#playAgainBtn").click()
            f.locator("#game").wait_for(state="visible",timeout=25000)
            frame.wait_for_function("() => document.querySelector('#questionText').textContent.trim().length>0",timeout=25000)
            assert f.locator("#scoreMamba").inner_text().strip()=="0"
            print(f"[{engine_name}] Reinicio con marcadores a cero",flush=True)
            assert not errors,errors
        finally:
            context.close()
            browser.close()
print("Full flow V2 QA PASSED")

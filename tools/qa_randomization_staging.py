#!/usr/bin/env python3
"""E2E real: reiniciar Mambapalabra y comprobar definiciones distintas en la A."""
import json
import urllib.request
from playwright.sync_api import sync_playwright

URL = "https://mambapalabra-b1131-ux1-staging.floot.app/"
MANIFEST = "https://raw.githubusercontent.com/facundocapello-blip/mambapalabra-staging/qa/piper-audio-398/piper-audio/manifest.json"
with urllib.request.urlopen(MANIFEST,timeout=30) as response:
    rows=json.load(response)["rows"]
definitions={r["definition"]:r for r in rows}

def run(engine, name):
    browser=engine.launch(headless=True,args=["--autoplay-policy=no-user-gesture-required"] if name=="chromium" else [])
    context=browser.new_context(viewport={"width":1280,"height":720},locale="es-AR")
    page=context.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    answers=[]
    try:
        for round_number in range(5):
            page.goto(URL,wait_until="domcontentloaded",timeout=90000)
            game=page.frame_locator("iframe")
            game.locator("#lobby").wait_for(state="visible",timeout=90000)
            game.get_by_role("button",name="Jugar local").click(timeout=20000)
            game.locator("#game").wait_for(state="visible",timeout=40000)
            game.locator("#questionText").wait_for(state="visible",timeout=40000)
            clue=game.locator("#questionText").inner_text().strip()
            if not clue:
                page.wait_for_timeout(1000)
                clue=game.locator("#questionText").inner_text().strip()
            assert clue in definitions, f"Definición no encontrada en el banco aprobado: {clue}"
            row=definitions[clue]
            assert row["letter"]=="A", f"Primera letra inesperada: {row}"
            answers.append(row["answer"])
            print(f"[{name}] Partida {round_number+1}: A = {row['answer']} / {clue[:75]}",flush=True)
        assert len(set(answers))==5, f"Palabras repetidas en la A antes de completar ciclo: {answers}"
        assert not errors, errors
        print(f"[{name}] OK: 5 partidas reales, 5 respuestas A distintas, sin errores JS",flush=True)
    finally:
        context.close()
        browser.close()

with sync_playwright() as p:
    run(p.chromium,"chromium")
    run(p.webkit,"webkit")

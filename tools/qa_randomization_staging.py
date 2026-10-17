#!/usr/bin/env python3
"""Comprueba la rotación de 398 palabras en la web real STAGING."""
import json
from playwright.sync_api import sync_playwright

URL = "https://mambapalabra-b1131-ux1-staging.floot.app/"

def run(engine, name):
    browser = engine.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"] if name == "chromium" else [])
    context = browser.new_context(viewport={"width":1280,"height":720}, locale="es-AR")
    page = context.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    try:
        page.goto(URL,wait_until="domcontentloaded",timeout=90000)
        page.frame_locator("iframe").locator("#lobby").wait_for(state="visible",timeout=90000)
        page.frame_locator("iframe").get_by_role("button",name="Jugar local").click(timeout=20000)
        page.frame_locator("iframe").locator("#game").wait_for(state="visible",timeout=40000)
        frame=next((f for f in page.frames if f != page.main_frame and f.locator("#game").count()),None)
        assert frame is not None,"Iframe del juego ausente"
        frame.wait_for_function("() => typeof game !== 'undefined' && !!game && Array.isArray(game.players) && game.players.length === 2", timeout=30000)
        result=frame.evaluate("""() => {
          // Se crea una partida real desde el menú. Luego se simulan 7 reinicios
          // con el mismo selector que utiliza resetGame(), sin esperar los audios.
          const rows=[];
          const first = game.players.map(p=>p.items.map(q=>({letter:q.letter,answer:q.answer,clue:q.clue})));
          rows.push(first);
          for(let i=0;i<7;i++){
            resetQuestionDraw();
            const g=newGame("Mamba","Facu",150);
            rememberQuestionDraw();
            rows.push(g.players.map(p=>p.items.map(q=>({letter:q.letter,answer:q.answer,clue:q.clue}))));
          }
          const sample=letter=>rows.flatMap(r=>r.map(p=>p.find(q=>q.letter===letter).answer));
          const a=sample("A"), b=sample("B");
          const saved=localStorage.getItem("mamba:questionRotation:v2");
          return {games:rows.length,a,b,uniqueA:new Set(a).size,uniqueB:new Set(b).size,
            stored:!!saved,storedLength:saved?.length,firstA:rows[0][0][0].answer,
            firstB:rows[0][0][1].answer};
        }""")
        print(f"[{name}] {json.dumps(result,ensure_ascii=False)}",flush=True)
        assert result["games"]==8
        assert result["uniqueA"]==16, "Se repitieron palabras A antes de completar el ciclo"
        assert result["uniqueB"]==16, "Se repitieron palabras B antes de completar el ciclo"
        assert result["stored"],"La rotación no se guardó en localStorage"
        assert not errors,errors
        page.reload(wait_until="domcontentloaded",timeout=90000)
        page.frame_locator("iframe").locator("#lobby").wait_for(state="visible",timeout=90000)
        frame=next(f for f in page.frames if f != page.main_frame and f.locator("#lobby").count())
        persisted=frame.evaluate("""() => {
          resetQuestionDraw();
          const g=newGame("Mamba","Facu",150);
          rememberQuestionDraw();
          return {a:g.players[0].items[0].answer,b:g.players[0].items[1].answer,
            persisted:!!localStorage.getItem("mamba:questionRotation:v2")};
        }""")
        print(f"[{name}] Tras recargar: {json.dumps(persisted,ensure_ascii=False)}",flush=True)
        assert persisted["persisted"]
        assert persisted["a"] not in result["a"],"A se repitió antes de agotar 17 opciones"
        assert persisted["b"] not in result["b"],"B se repitió antes de agotar 19 opciones"
        print(f"[{name}] Rotación comprobada en navegador real",flush=True)
    finally:
        context.close()
        browser.close()

with sync_playwright() as p:
    run(p.chromium,"chromium")
    run(p.webkit,"webkit")

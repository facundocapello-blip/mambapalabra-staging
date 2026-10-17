#!/usr/bin/env python3
"""Browser QA of published Mambapalabra Piper STAGING. No production mutations."""
import json
import pathlib
import time
import urllib.request
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL = "https://mambapalabra-b1131-ux1-staging.floot.app/"
MANIFEST = "https://raw.githubusercontent.com/facundocapello-blip/mambapalabra-staging/qa/piper-audio-398/piper-audio/manifest.json"
ARTIFACTS = pathlib.Path("artifacts/piper-browser")
ARTIFACTS.mkdir(parents=True, exist_ok=True)

with urllib.request.urlopen(MANIFEST, timeout=30) as resp:
    manifest = json.load(resp)
assert manifest["approved"] == 398 and manifest["clips"] == 811
assert len(manifest["entries"]) == 811
answers = {r["definition"]: r["answer"] for r in manifest["rows"]}

def until(check, seconds=35, label="condition", pump=None):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        if pump is not None:
            pump.wait_for_timeout(300)  # procesa los eventos de red de Playwright
        else:
            time.sleep(.3)
    raise AssertionError(f"Timeout waiting for {label}")

def run(browser_type, label):
    kwargs = {"headless": True}
    if label == "chromium":
        kwargs["args"] = ["--autoplay-policy=no-user-gesture-required"]
    browser = browser_type.launch(**kwargs)
    context = browser.new_context(
        viewport={"width": 844 if label == "webkit" else 1280, "height": 390 if label == "webkit" else 720},
        locale="es-AR",
        is_mobile=(label == "webkit"),
        has_touch=(label == "webkit"),
        device_scale_factor=2 if label == "webkit" else 1,
    )
    page = context.new_page()
    audio_responses = []
    errors = []
    page.on("response", lambda r: audio_responses.append((r.url, r.status)) if "/piper-audio/" in r.url and r.url.endswith(".mp3") else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        print(f"[{label}] Abriendo {URL}", flush=True)
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        game = page.frame_locator("iframe")
        game.locator("#lobby").wait_for(state="visible", timeout=90000)
        print(f"[{label}] Banco cargado en iframe", flush=True)
        game.get_by_role("button", name="Jugar local").click(timeout=20000)
        game.locator("#game").wait_for(state="visible", timeout=40000)
        until(lambda: bool(game.locator("#questionText").inner_text().strip()), 40, "primera definición")
        first = game.locator("#questionText").inner_text().strip()
        assert first in answers, f"Definición no aprobada: {first}"
        print(f"[{label}] Primera definición: {first[:60]}", flush=True)
        until(lambda: any(status == 200 and "/q" in url for url, status in audio_responses), 40, "audio de definición HTTP 200", pump=page)
        print(f"[{label}] Audio Piper de pregunta HTTP 200", flush=True)
        game.locator("#passBtn").wait_for(state="visible", timeout=20000)
        until(lambda: game.locator("#passBtn").is_enabled(), 45, "estado ANSWERING / PASAPALABRA")
        assert game.locator("#activeName").inner_text().strip() == "Mamba"
        game.locator("#passBtn").click()
        until(lambda: game.locator("#activeName").inner_text().strip() == "Facu", 15, "cambio de jugador por PASAPALABRA")
        print(f"[{label}] PASAPALABRA -> Facu", flush=True)
        until(lambda: game.locator("#passBtn").is_enabled(), 45, "pregunta de Facu lista")
        # Wrong answer triggers the recorded "Incorrecto. Era ..." and switches player.
        game.locator("#textAnswer").fill("Respuesta inexistente XYZ")
        game.locator("#sendTextBtn").click()
        until(lambda: int(game.locator("#wrongFacu").inner_text()) >= 1, 20, "respuesta incorrecta")
        until(lambda: any(status == 200 and "/w" in url for url, status in audio_responses), 40, "audio incorrecto HTTP 200", pump=page)
        print(f"[{label}] Respuesta incorrecta + audio Piper HTTP 200", flush=True)
        until(lambda: game.locator("#activeName").inner_text().strip() == "Mamba", 25, "regreso a Mamba")
        until(lambda: game.locator("#passBtn").is_enabled(), 45, "pregunta Mamba lista")
        clue = game.locator("#questionText").inner_text().strip()
        assert clue in answers, f"Definición actual no aprobada: {clue}"
        game.locator("#textAnswer").fill(answers[clue])
        game.locator("#sendTextBtn").click()
        until(lambda: int(game.locator("#scoreMamba").inner_text()) >= 1, 20, "respuesta correcta")
        print(f"[{label}] Respuesta correcta y siguiente letra", flush=True)
        assert not [e for e in errors if "Error" in e or "ReferenceError" in e], errors
        page.screenshot(path=str(ARTIFACTS / f"{label}-piper.png"), full_page=True)
        print(f"[{label}] QA OK: {len(audio_responses)} solicitudes MP3; errores JS: {len(errors)}", flush=True)
    except Exception:
        page.screenshot(path=str(ARTIFACTS / f"{label}-failed.png"), full_page=True)
        print(f"[{label}] MP3 responses: {audio_responses[:12]}", flush=True)
        print(f"[{label}] JS errors: {errors[:12]}", flush=True)
        raise
    finally:
        context.close()
        browser.close()

with sync_playwright() as p:
    run(p.chromium, "chromium")
    run(p.webkit, "webkit")
print("Browser QA completed", flush=True)

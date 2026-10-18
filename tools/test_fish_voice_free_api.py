#!/usr/bin/env python3
"""Isolated Fish Audio free-tier voice casting. Never prints or stores credentials."""
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

VOICE_ID = "c4a325176443465ab0ba1b0cfa979995"
MODEL = "s2.1-pro-free"
OUT = Path("artifacts/fish-voice-free-test")
SAMPLES = {
    "01_definicion": "Empieza con A: Montaña más alta de América, ubicada en la cordillera de los Andes.",
    "02_correcto": "Correcto. Seguimos con la siguiente letra.",
    "03_incorrecto": "Incorrecto. Era Rodaje.",
}

def generate(name, text, api_key):
    body = json.dumps({
        "text": text,
        "reference_id": VOICE_ID,
        "format": "mp3",
        "mp3_bitrate": 128,
        "prosody": {"speed": 1.0},
        "latency": "normal"
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.fish.audio/v1/tts",
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "model": MODEL,
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            audio = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        # Do not echo response headers/body, which could contain sensitive data.
        raise RuntimeError(f"Fish API returned HTTP {exc.code} for {name}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network connection failed for {name}: {type(exc.reason).__name__}") from None
    if len(audio) < 1000 or not (audio.startswith(b"ID3") or audio[:2] in (b"\\xff\\xfb", b"\\xff\\xf3", b"\\xff\\xf2")):
        raise RuntimeError(f"Unexpected audio response for {name}; size={len(audio)}, type={content_type.split(';')[0]}")
    path = OUT / f"{name}.mp3"
    path.write_bytes(audio)
    print(f"Generated {path.name}: {len(audio)} bytes")
    return {"file": path.name, "text": text, "sha256": hashlib.sha256(audio).hexdigest(), "bytes": len(audio)}

def main():
    key = os.getenv("FISH_API_KEY", "").strip()
    if not key:
        raise RuntimeError("FISH_API_KEY is missing in GitHub Actions secrets")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, text in SAMPLES.items():
        manifest.append(generate(name, text, key))
    (OUT / "manifest.json").write_text(json.dumps({
        "model": MODEL, "reference_id": VOICE_ID, "samples": manifest,
        "note": "Casting only. No bank changes, no production publication."
    }, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Genera el conductor Piper de las 398 definiciones APROBADAS, sin servicios de pago.

Salida aislada: piper-audio/ en la rama qa/piper-audio-398 del repositorio STAGING.
No modifica el banco ni la versión publicada del juego.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import tempfile
import unicodedata
import urllib.request
import wave

SOURCE = "https://docs.google.com/spreadsheets/d/1BdB1GrSfQ0cFmfWC7nidqycvQvrlig9bHwl1rU1VNkU/gviz/tq?tqx=out:csv&sheet=Banco"
BASE = "https://raw.githubusercontent.com/facundocapello-blip/mambapalabra-staging/qa/piper-audio-398/piper-audio/"
EXPECTED = 398
LETTERS = set("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")
LETTER_NAMES = {
    "A": "a", "B": "be", "C": "ce", "D": "de", "E": "e", "F": "efe",
    "G": "ge", "H": "hache", "I": "i", "J": "jota", "K": "ka", "L": "ele",
    "M": "eme", "N": "ene", "Ñ": "eñe", "O": "o", "P": "pe", "Q": "cu",
    "R": "erre", "S": "ese", "T": "te", "U": "u", "V": "ve", "W": "doble ve",
    "X": "equis", "Y": "i griega", "Z": "zeta",
}
FIXED = {
    "Correcto.": "Correcto.",
    "Facu.": "Facu.",
    "Mamba.": "Mamba.",
    "Ahora vamos con el otro jugador.": "Ahora vamos con el otro jugador.",
    "Seguimos.": "Seguimos.",
    "Arrancamos. Vamos con la primera.": "Arrancamos. Vamos con la primera.",
    "Bueno, empezamos. Atención al rosco.": "Bueno, empezamos. Atención al rosco.",
    "Vamos con vos. Primera palabra.": "Vamos con vos. Primera palabra.",
    "Cuando quieras. Arrancamos.": "Cuando quieras. Arrancamos.",
    "Volvemos a las que quedaron pendientes.": "Volvemos a las que quedaron pendientes.",
    "Vamos con las pendientes.": "Vamos con las pendientes.",
    "Retomamos las que pasaste.": "Retomamos las que pasaste.",
    "Tiempo.": "Tiempo.",
    "Se terminó el tiempo.": "Se terminó el tiempo.",
    "Se terminó el rosco. Vamos a los resultados.": "Se terminó el rosco. Vamos a los resultados.",
}

def normalized(s):
    s = str(s).casefold().replace("ñ", "__enie__")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    return s.replace("__enie__", "ñ")

def bank():
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mambapalabra-Piper/1.0"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = resp.read()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not rows or not {"ID", "Letra", "Respuesta", "Definición", "Estado", "Tipo_Regla"}.issubset(rows[0]):
        raise ValueError("Columnas del banco inesperadas")
    approved = [r for r in rows if r["Estado"] == "APROBADA"]
    if len(approved) != EXPECTED:
        raise ValueError(f"Se esperaban {EXPECTED} aprobadas; llegaron {len(approved)}")
    seen = set()
    for r in approved:
        letter, answer, definition = r["Letra"].strip().upper(), r["Respuesta"].strip(), r["Definición"].strip()
        if letter not in LETTERS or not answer or not definition:
            raise ValueError("Fila aprobada incompleta: " + str(r))
        key = normalized(answer)
        if key in seen:
            raise ValueError("Respuesta aprobada duplicada: " + answer)
        seen.add(key)
        rule = r["Tipo_Regla"].strip()
        if rule not in ("EMPIEZA", "CONTIENE"):
            rule = "EMPIEZA" if normalized(answer).upper().startswith(normalized(letter).upper()) else "CONTIENE"
        norm_ans, norm_letter = normalized(answer), normalized(letter)
        if not (norm_ans.startswith(norm_letter) if rule == "EMPIEZA" else norm_letter in norm_ans):
            raise ValueError("Respuesta no corresponde a letra: " + answer)
        r["_rule"] = rule
    return approved, hashlib.sha256(raw).hexdigest()

def prepare(rows, bank_sha):
    entries, items, jobs = {}, [], []
    for i, r in enumerate(rows, 1):
        letter, answer, clue, rule = (r["Letra"].strip().upper(), r["Respuesta"].strip(), r["Definición"].strip(), r["_rule"])
        question_key = f"Contiene {letter}: {clue}" if rule == "CONTIENE" else f"{letter}: {clue}"
        spoken = f"Contiene la {LETTER_NAMES[letter]}. {clue}" if rule == "CONTIENE" else f"Con la letra {LETTER_NAMES[letter]}. {clue}"
        wrong_key = f"Incorrecto. Era {answer}."
        q_file, w_file = f"q{i:04d}.mp3", f"w{i:04d}.mp3"
        if question_key in entries or wrong_key in entries:
            raise ValueError("Clave de audio duplicada: " + answer)
        entries[question_key], entries[wrong_key] = BASE + q_file, BASE + w_file
        jobs.extend(((q_file, spoken), (w_file, wrong_key)))
        items.append({"id": r["ID"], "letter": letter, "answer": answer, "rule": rule, "definition": clue, "question_key": question_key, "wrong_key": wrong_key, "question_file": q_file, "wrong_file": w_file})
    for i, (key, spoken) in enumerate(FIXED.items(), 1):
        if key in entries:
            raise ValueError("Frase fija duplicada")
        file = f"fixed{i:02d}.mp3"
        entries[key] = BASE + file
        jobs.append((file, spoken))
    if len(jobs) != EXPECTED * 2 + len(FIXED):
        raise ValueError("Cantidad inesperada de clips")
    return {
        "schema": 1, "voice": "es_MX-claude-high", "engine": "Piper",
        "voice_dataset_license": "Apache-2.0", "approved": EXPECTED,
        "clips": len(jobs), "bank_sha256": bank_sha,
        "entries": entries, "rows": items,
    }, jobs

def synthesize(piper, model, jobs, out_dir, bitrate):
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="piper-wav-") as tmp:
        tmp = pathlib.Path(tmp)
        inputs = []
        for filename, spoken in jobs:
            output = tmp / (pathlib.Path(filename).stem + ".wav")
            inputs.append(json.dumps({"text": spoken, "output_file": str(output)}, ensure_ascii=False))
        print("Generando", len(inputs), "WAV con una sola sesión de Piper", flush=True)
        with subprocess.Popen([str(piper), "--model", str(model), "--json-input", "--output_dir", str(tmp), "--length_scale", "1.08", "--sentence_silence", "0.12"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True) as proc:
            _, stderr = proc.communicate("\n".join(inputs) + "\n", timeout=1500)
            if proc.returncode:
                raise RuntimeError("Piper falló: " + stderr[-2000:])
        wavs = list(tmp.glob("*.wav"))
        if len(wavs) != len(jobs):
            raise ValueError(f"Piper generó {len(wavs)}/{len(jobs)} WAV")
        def encode(job):
            filename, _ = job
            source = tmp / (pathlib.Path(filename).stem + ".wav")
            dest = out_dir / filename
            with wave.open(str(source), "rb") as w:
                duration = w.getnframes() / w.getframerate()
            if not (0.3 <= duration <= 40):
                raise ValueError(f"Duración inesperada {filename}: {duration}")
            subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-ac", "1", "-ar", "22050", "-b:a", bitrate, str(dest)], check=True, timeout=30)
            if dest.stat().st_size < 1200:
                raise ValueError(f"MP3 vacío: {filename}")
            return filename, dest.stat().st_size, duration
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            stats = list(executor.map(encode, jobs))
    print("MP3:", len(stats), "Tamaño:", round(sum(x[1] for x in stats)/1024/1024, 2), "MiB; duración:", round(sum(x[2] for x in stats)/60, 2), "minutos", flush=True)
    return stats

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--piper", type=pathlib.Path)
    parser.add_argument("--model", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("piper-audio"))
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--bitrate", default="64k")
    args = parser.parse_args()
    rows, bank_sha = bank()
    manifest, jobs = prepare(rows, bank_sha)
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.manifest_only:
        if not args.piper or not args.model:
            parser.error("--piper y --model son obligatorios salvo --manifest-only")
        synthesize(args.piper, args.model, jobs, args.out, args.bitrate)
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Banco SHA256:", bank_sha, "preguntas:", len(rows), "clips:", len(jobs), flush=True)
    if not args.manifest_only:
        missing = [file for file, _ in jobs if not (args.out / file).is_file()]
        if missing:
            raise ValueError("Faltan MP3: " + repr(missing[:8]))

if __name__ == "__main__":
    main()

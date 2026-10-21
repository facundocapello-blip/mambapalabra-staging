#!/usr/bin/env python3
"""Generate exactly two short turn cues with existing Fish voice; free model only."""
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_fish_voice_free_api import MODEL, VOICE_ID, generate
import test_fish_voice_free_api as fish

OUT = Path('artifacts/fish-rc6-turn-clips')
CLIPS = [('09_incorrecto_corto', 'Incorrecto.'), ('10_pasapalabra_corto', 'Pasapalabra.')]

def main():
    assert MODEL == 's2.1-pro-free', 'No paid model allowed'
    assert VOICE_ID == 'c4a325176443465ab0ba1b0cfa979995', 'Voice identity changed'
    assert len(CLIPS) == 2
    key = os.getenv('FISH_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Missing FISH_API_KEY; do not substitute another voice')
    OUT.mkdir(parents=True, exist_ok=True)
    fish.OUT = OUT
    items = []
    for name, phrase in CLIPS:
        file = OUT / (name + '.mp3')
        if file.exists() and file.stat().st_size > 1000:
            data = file.read_bytes()
            item = {'file': file.name, 'text': phrase, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'cached': True}
        else:
            item = generate(name, phrase, key)
            item['cached'] = False
        assert item['text'] == phrase
        items.append(item)
    (OUT / 'manifest.json').write_text(json.dumps({'model': MODEL, 'voice_id': VOICE_ID, 'clips': items, 'scope': 'RC6 STAGING only; 2 free model calls maximum'}, ensure_ascii=False, indent=2))
    print('PASS: 2 short Fish cues generated with free model', flush=True)

if __name__ == '__main__':
    main()

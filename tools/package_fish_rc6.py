#!/usr/bin/env python3
"""Patch verified RC5 only: 1.22x definitions and short turn cues; preserve existing assets."""
import hashlib
import json
import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

SOURCE = Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC5_STAGING.zip')
TARGET = Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC6_STAGING.zip')
AUDIO_DIR = Path('artifacts/fish-rc6-turn-clips')
RC5 = 'B1.13.1-UX1-FISH398-VOZ-UNICA-RC5-STAGING'
RC6 = 'B1.13.1-UX1-FISH398-VOZ-UNICA-RC6-STAGING'
NEW_AUDIO = {'fish-audio/09_incorrecto_corto.mp3': 'Incorrecto.', 'fish-audio/10_pasapalabra_corto.mp3': 'Pasapalabra.'}

def replace_once(s, old, new, expected=1):
    found = s.count(old)
    assert found == expected, f'Expected {expected} occurrences, found {found}: {old[:130]!r}'
    return s.replace(old, new)

def patch_html(s):
    s = replace_once(s, f'const FISH_BANK_VERSION="{RC5}";', f'const FISH_BANK_VERSION="{RC6}";')
    s = replace_once(s, 'const FISH_DEFINITION_SPEED_MULTIPLIER=1.12; // Only Fish question clips; preserves pitch.',
                     'const FISH_DEFINITION_PLAYBACK_RATE=1.22; // Absolute rate in local and online; preserves pitch.')
    s = replace_once(s,
        'audio.playbackRate=(online.enabled?1:HOST_PLAYBACK_RATE)*(/^fish-bank\\/q\\d{4}\\.mp3$/.test(path)?FISH_DEFINITION_SPEED_MULTIPLIER:1);',
        'audio.playbackRate=/^fish-bank\\/q\\d{4}\\.mp3$/.test(path)?FISH_DEFINITION_PLAYBACK_RATE:(/^fish-audio\\/(?:09_incorrecto_corto|10_pasapalabra_corto)\\.mp3$/.test(path)?1.12:(online.enabled?1:HOST_PLAYBACK_RATE));')
    anchor = 'for(const [phrase,url] of Object.entries(FISH_CASTING_MAP)){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}'
    s = replace_once(s, anchor, anchor + '\n  // RC6: two short cues in the same Fish voice, never device TTS.\n  for(const [phrase,url] of Object.entries({"Incorrecto.":"fish-audio/09_incorrecto_corto.mp3","Pasapalabra.":"fish-audio/10_pasapalabra_corto.mp3"})){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}')
    s = replace_once(s, 'const expected=item.answer,wrongLead=`Incorrecto. Era ${expected}.`,other=1-previousOwner;',
                     'const expected=item.answer,wrongLead="Incorrecto.",other=1-previousOwner;')
    s = replace_once(s, 'turnPrompt(CUSTOM_AUDIO.pass?"__CUSTOM_PASS__":"",true);', 'turnPrompt("Pasapalabra.",true);', expected=2)
    s = replace_once(s, 'turnPrompt("Seguimos.");', 'turnPrompt("Pasapalabra.");')
    s = replace_once(s, 'if(announcePlayer){const result=await hostSpeak(playerAnnouncement(p.name));',
                     'if(announcePlayer&&!lead){const result=await hostSpeak(playerAnnouncement(p.name));')
    s = replace_once(s, 'if(!speechOn)return valid();\n    await new Promise(resolve=>setTimeout(resolve,ms));',
                     'if(!speechOn||ms<=0)return valid();\n    await new Promise(resolve=>setTimeout(resolve,ms));')
    s = replace_once(s, 'presenterBeat(PRESENTER_PAUSE_MS.result,stillValid)',
                     'presenterBeat(lead==="Incorrecto."||lead==="Pasapalabra."?0:PRESENTER_PAUSE_MS.result,stillValid)')
    s = replace_once(s, 'hostSpeak(ok?"Correcto.":`Incorrecto. Era ${q.answer}.`);',
                     'hostSpeak(ok?"Correcto.":"Incorrecto.");')
    s = replace_once(s,
        'const nameResult=await hostSpeak(playerAnnouncement(player().name));if(!valid()||!readingCanFinish(nameResult)||!await presenterBeat(PRESENTER_PAUSE_MS.player,valid))return;',
        'if(game.suddenRound===1&&game.active===0){const nameResult=await hostSpeak(playerAnnouncement(player().name));if(!valid()||!readingCanFinish(nameResult)||!await presenterBeat(PRESENTER_PAUSE_MS.player,valid))return;}')
    assert 'return deviceSpeak(' not in s
    assert s.count('FISH_DEFINITION_PLAYBACK_RATE') == 2
    return s

def main():
    assert SOURCE.exists(), 'Missing verified RC5 package'
    manifest = json.loads((AUDIO_DIR / 'manifest.json').read_text())
    assert manifest['model'] == 's2.1-pro-free' and manifest['voice_id'] == 'c4a325176443465ab0ba1b0cfa979995'
    assert {x['text'] for x in manifest['clips']} == set(NEW_AUDIO.values())
    for name, phrase in NEW_AUDIO.items():
        data = (AUDIO_DIR / Path(name).name).read_bytes()
        assert len(data) > 1000 and (data.startswith(b'ID3') or data[:1] == b'\xff'), name
        entry = next(x for x in manifest['clips'] if x['text'] == phrase)
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(AUDIO_DIR / Path(name).name), '-f', 'null', '-'], check=True, capture_output=True)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SOURCE) as src, ZipFile(TARGET, 'w', ZIP_DEFLATED, compresslevel=4) as dst:
        assert src.read('FISH_SPEED_RELEASE.json')
        assert sum(n.startswith('fish-bank/') and n.endswith('.mp3') for n in src.namelist()) == 811
        assert sum(n.startswith('fish-audio/') and n.endswith('.mp3') for n in src.namelist()) == 8
        assert sum(n.startswith('new-audio/') and n.endswith('.mp3') for n in src.namelist()) == 188
        assert RC5 in src.read('index.html').decode()
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == 'index.html':
                data = patch_html(data.decode()).encode()
            elif info.filename.endswith('RELEASE.json'):
                obj = json.loads(data)
                if obj.get('version') == RC5:
                    obj['version'] = RC6
                if 'definition_speed_multiplier' in obj:
                    del obj['definition_speed_multiplier']
                obj['definition_playback_rate'] = 1.22
                obj['speed_scope'] = 'Fish question clips local and online; pitch preserved'
                if info.filename == 'FISH_SPEED_RELEASE.json':
                    obj['base'] = RC5
                    obj['changed_audio_files'] = 0
                    obj['added_audio_files'] = 2
                    obj['short_turn_cues'] = ['Incorrecto.', 'Pasapalabra.']
                data = json.dumps(obj, ensure_ascii=False, indent=2).encode()
            dst.writestr(info, data)
        for name in NEW_AUDIO:
            assert name not in src.namelist(), name
            dst.write(AUDIO_DIR / Path(name).name, name)
        dst.writestr('FISH_TURN_RELEASE.json', json.dumps({'version': RC6, 'source': RC5, 'model': manifest['model'], 'voice_id': manifest['voice_id'], 'clips': manifest['clips'], 'turn_handoff': 'short cues only, no answer recitation or player announcement', 'definition_playback_rate': 1.22, 'scope': 'STAGING only'}, ensure_ascii=False, indent=2))
    with ZipFile(SOURCE) as old, ZipFile(TARGET) as new:
        changes = [n for n in old.namelist() if old.read(n) != new.read(n)]
        assert set(changes) <= {'index.html', 'PIPER_RELEASE.json', 'FISH_BANK_RELEASE.json', 'FISH_SPEED_RELEASE.json'}
        assert 'index.html' in changes
        assert all(old.read(n) == new.read(n) for n in old.namelist() if n.endswith('.mp3'))
        assert sum(n.startswith('fish-audio/') and n.endswith('.mp3') for n in new.namelist()) == 10
        assert RC6 in new.read('index.html').decode()
        assert json.loads(new.read('FISH_TURN_RELEASE.json'))['definition_playback_rate'] == 1.22
        print('PASS: RC6 source RC5, 1.22 absolute rate, two new free Fish cues, original 1007 MP3 byte-identical', flush=True)
        print('Modified:', changes, 'Added:', sorted(set(new.namelist()) - set(old.namelist())), flush=True)
    print('Created:', TARGET, TARGET.stat().st_size, flush=True)

if __name__ == '__main__':
    main()

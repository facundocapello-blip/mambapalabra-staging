#!/usr/bin/env python3
"""Speed up Fish definition MP3 playback by 8%, without touching audio bytes.

Input: verified RC3 STAGING package (GitHub Actions artifact 12237667442).
Output: isolated RC4 STAGING package. No audio API, bank or production changes.
"""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

SOURCE = Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC3_STAGING.zip')
TARGET = Path('dist/MAMBAPALABRA_B1.13.1_UX1_FISH398_VOZ_UNICA_RC4_STAGING.zip')
RC3 = 'B1.13.1-UX1-FISH398-VOZ-UNICA-RC3-STAGING'
RC4 = 'B1.13.1-UX1-FISH398-VOZ-UNICA-RC4-STAGING'
SOURCE_SHA256 = 'c62f1c0f6958c3fcc65112d917e3c567cc420d4ab24bb234779284227881411a'
RATE_BEFORE = 'audio.src=url;audio.volume=1;audio.playbackRate=online.enabled?1:HOST_PLAYBACK_RATE;if("preservesPitch" in audio)audio.preservesPitch=true;'
RATE_AFTER = ('audio.src=url;audio.volume=1;'
              'audio.playbackRate=(online.enabled?1:HOST_PLAYBACK_RATE)*'
              '(/^fish-bank\\/q\\d{4}\\.mp3$/.test(path)?FISH_DEFINITION_SPEED_MULTIPLIER:1);'
              'if("preservesPitch" in audio)audio.preservesPitch=true;')

def patch_html(html):
    assert html.count('const HOST_PLAYBACK_RATE=.92;') == 1
    assert html.count(RATE_BEFORE) == 1
    assert html.count('const FISH_BANK_VERSION="'+RC3+'";') == 1
    html = html.replace('const HOST_PLAYBACK_RATE=.92;',
                        'const HOST_PLAYBACK_RATE=.92;\n  const FISH_DEFINITION_SPEED_MULTIPLIER=1.08; // Only Fish question clips; preserves pitch.')
    html = html.replace(RATE_BEFORE, RATE_AFTER)
    html = html.replace('const FISH_BANK_VERSION="'+RC3+'";', 'const FISH_BANK_VERSION="'+RC4+'";')
    assert html.count('FISH_DEFINITION_SPEED_MULTIPLIER') == 2
    assert 'return deviceSpeak(' not in html
    return html

def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256, 'RC3 artifact differs from verified source'
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SOURCE) as src, ZipFile(TARGET, 'w', ZIP_DEFLATED, compresslevel=4) as dst:
        names = src.namelist()
        assert sum(n.startswith('fish-bank/') and n.endswith('.mp3') for n in names) == 811
        assert sum(n.startswith('fish-audio/') and n.endswith('.mp3') for n in names) == 8
        assert sum(n.startswith('new-audio/') and n.endswith('.mp3') for n in names) == 188
        for info in src.infolist():
            name = info.filename
            content = src.read(name)
            if name == 'index.html':
                content = patch_html(content.decode('utf-8')).encode('utf-8')
            elif name in ('PIPER_RELEASE.json', 'FISH_BANK_RELEASE.json'):
                release = json.loads(content)
                assert release['version'] == RC3
                release['version'] = RC4
                release['definition_speed_multiplier'] = 1.08
                release['speed_scope'] = 'fish-bank/qNNNN.mp3 only, normal and sudden death; pitch preserved'
                content = json.dumps(release, ensure_ascii=False, indent=2).encode('utf-8')
            dst.writestr(info, content)
        dst.writestr('FISH_SPEED_RELEASE.json', json.dumps({
            'version': RC4, 'base': RC3, 'source_sha256': SOURCE_SHA256,
            'definition_speed_multiplier': 1.08,
            'changed_audio_files': 0, 'scope': 'STAGING only',
        }, indent=2))
    with ZipFile(SOURCE) as old, ZipFile(TARGET) as new:
        assert set(new.namelist()) - set(old.namelist()) == {'FISH_SPEED_RELEASE.json'}
        allowed = {'index.html', 'PIPER_RELEASE.json', 'FISH_BANK_RELEASE.json'}
        changed = [name for name in old.namelist() if old.read(name) != new.read(name)]
        assert set(changed) == allowed, changed
        assert json.loads(new.read('FISH_SPEED_RELEASE.json'))['changed_audio_files'] == 0
        assert RC4 in new.read('index.html').decode()
        assert json.loads(new.read('FISH_BANK_RELEASE.json'))['version'] == RC4
    print('PASS RC4: definitions +8%, intros/results unchanged, all 1007 MP3 bytes identical, no production changes')
    print('Created', TARGET, TARGET.stat().st_size)

if __name__ == '__main__':
    main()

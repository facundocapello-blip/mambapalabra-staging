#!/usr/bin/env python3
"""Build isolated Fish intro overlay from the verified V2 ZIP and seven audio samples."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, os

BASE=Path("dist/MAMBAPALABRA_B1.13.1_UX1_PIPER398_VR1_LECTURA_V2_STAGING.zip")
OUT=Path("dist/MAMBAPALABRA_B1.13.1_UX1_FISH_VOCES_INTROS_RC1_STAGING.zip")
AUDIO=Path("fish-casting")
VERSION="B1.13.1-UX1-PIPER398-VR1-LECTURA-V2-FISH-INTRO-RC1-STAGING"
INTRO={
 "general":"Bienvenidos a Mambapalabra. Veintisiete letras, un desafío. ¿Estás listo para jugar?",
 "solo":"El rosco está preparado. Concentración, que empieza el desafío. ¡Vamos con la A!",
 "online":"¡Ya están los dos jugadores! El duelo está por comenzar. Dos participantes, veintisiete letras y un solo ganador. ¡Que comience Mambapalabra!",
}
FILES={
 INTRO["general"]:"fish-audio/03_intro_inicio.mp3",
 INTRO["solo"]:"fish-audio/04_intro_solo.mp3",
 INTRO["online"]:"fish-audio/05_intro_online.mp3",
 "Correcto.":"fish-audio/06_correcto.mp3",
 "Incorrecto. Era Rodaje.":"fish-audio/07_incorrecto.mp3",
}
def replace_once(s,old,new):
 assert s.count(old)==1, ("marker",old[:80],s.count(old))
 return s.replace(old,new,1)

with ZipFile(BASE) as z:
 s=z.read("index.html").decode()
 release=json.loads(z.read("PIPER_RELEASE.json"))
 assert release["version"]=="B1.13.1-UX1-PIPER398-VR1-LECTURA-V2"
 assert release["approved"]==398 and release["piper_mp3"]==811
marker='for(const [phrase,url] of Object.entries(PIPER_AUDIO_MAP)){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}'
s=replace_once(s,marker,marker+'\n  const FISH_INTEGRATION_VERSION="'+VERSION+'";\n  const FISH_CASTING_MAP='+json.dumps(FILES,ensure_ascii=False,separators=(',',':'))+';\n  for(const [phrase,url] of Object.entries(FISH_CASTING_MAP)){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}')
s=replace_once(s,'  let speechOn=true,fxOn=true,recognition=null,','''  const FISH_INTRO={general:"'''+INTRO["general"]+'''",solo:"'''+INTRO["solo"]+'''",online:"'''+INTRO["online"]+'''"};
  let generalIntroPlayed=false,onlineIntroPlayingMatch=null;
  const introMatchesPlayed=new Set();
  let speechOn=true,fxOn=true,recognition=null,''')
s=replace_once(s,'    stopRecognition();pauseTimer();cancelHostSpeech();\n    game={audioFailed:', '''    stopRecognition();pauseTimer();
    if(!(onlineIntroPlayingMatch===st.matchId&&online.role==="guest"&&Number(st.active)!==online.slot))cancelHostSpeech();
    game={audioFailed:''')
s=replace_once(s,'  function readingCanFinish(result){','''  async function playMatchIntro(mode,match){
    if(!match||game!==match||match.over||!speechOn)return;
    if(mode==="general"){
      if(generalIntroPlayed)return;
      generalIntroPlayed=true;
    }else{
      if(introMatchesPlayed.has(match.matchId))return;
      introMatchesPlayed.add(match.matchId);
    }
    if(mode==="online")onlineIntroPlayingMatch=match.matchId;
    try{
      if(match.turnState!==TURN_STATE.SWITCHING)return;
      await hostSpeak(FISH_INTRO[mode]);
    }finally{
      if(mode==="online"&&onlineIntroPlayingMatch===match.matchId)onlineIntroPlayingMatch=null;
    }
  }
  function readingCanFinish(result){''')
s=replace_once(s,'''    if(document.hidden){game.paused=true;updatePauseControl();updateTurnControls();return;}
    turnPrompt();
  }

  els.start.addEventListener''','''    if(document.hidden){game.paused=true;updatePauseControl();updateTurnControls();return;}
    const started=game;
    if(withCountdown){await playMatchIntro("general",started);if(game!==started)return;}
    await playMatchIntro("solo",started);
    if(game!==started)return;
    turnPrompt();
  }

  els.start.addEventListener''')
s=replace_once(s,'''      scheduleOnlineSync();await onlineSyncNow();if(!online.restoring)turnPrompt();return;''','''      scheduleOnlineSync();await onlineSyncNow();
      if(!online.restoring){const started=game;await playMatchIntro("online",started);if(game===started)turnPrompt();}
      return;''')
s=replace_once(s,'''      try{onlineHydrate(row.game_state);}finally{online.applying=false;}
      if(!online.restoring&&!game.over&&online.authority&&game.turnState===TURN_STATE.SWITCHING){''','''      try{onlineHydrate(row.game_state);}finally{online.applying=false;}
      if(!online.restoring&&!game.over&&online.role==="guest"&&game.turnState===TURN_STATE.SWITCHING){
        void playMatchIntro("online",game);
      }
      if(!online.restoring&&!game.over&&online.authority&&game.turnState===TURN_STATE.SWITCHING){''')
s=replace_once(s,'''renderRoscos();syncUI();await onlineSyncNow();turnPrompt();
  }

  let resetSequence''','''renderRoscos();syncUI();await onlineSyncNow();const started=game;await playMatchIntro("online",started);if(game===started)turnPrompt();
  }

  let resetSequence''')
clips={}
for f in sorted(AUDIO.glob("*.mp3")):
 clips["fish-audio/"+f.name]=f.read_bytes()
assert len(clips)==7 and all(len(x)>1000 for x in clips.values())
assert set(FILES.values()).issubset(clips)
release.update(version=VERSION,voice_overlay="Fish Audio 7 samples, Piper bank preserved",fish_samples=7,intro_modes=list(INTRO),production_untouched=True)
with ZipFile(BASE) as z, ZipFile(OUT,"w",ZIP_DEFLATED,compresslevel=4) as out:
 for item in z.infolist():
  if item.filename=="index.html":out.writestr(item,s.encode())
  elif item.filename=="PIPER_RELEASE.json":out.writestr(item,json.dumps(release,ensure_ascii=False,indent=2))
  else:out.writestr(item,z.read(item.filename))
 for name,blob in clips.items():out.writestr(name,blob)
 out.writestr("FISH_CASTING_RELEASE.json",json.dumps({"version":VERSION,"base_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),"clips_sha256":{k:hashlib.sha256(v).hexdigest() for k,v in clips.items()},"scope":"STAGING only"},indent=2))
with ZipFile(OUT) as z:
 assert sum(x.startswith("piper-audio/") and x.endswith(".mp3") for x in z.namelist())==811
 assert sum(x.startswith("fish-audio/") and x.endswith(".mp3") for x in z.namelist())==7
 assert z.read("index.html").decode()==s
print("Fish staging ZIP:",OUT,"bytes",OUT.stat().st_size)

#!/usr/bin/env node
// Paquete completo y reproducible B1.13.1 UX1 + 398 aprobadas + Piper 811.
// Solo genera ZIP de STAGING. No modifica producción.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import JSZip from 'jszip';
import { applyPatch } from 'diff';

const SOURCE = 'https://raw.githubusercontent.com/facundocapello-blip/Mambapalabra/8648098/Mambapalabra-B1.13.1-RC1.zip';
const PATCH_BASE = 'https://raw.githubusercontent.com/facundocapello-blip/mambapalabra-staging/ux/b1131-presenter-iphone/qa/';
const PATCHES = [
  ['B1.13.1-RC1-UX1.patch', '39a5641ac0fc161ab5eb69ddfcfef462897a7898ab33b7667330627c662e58dd'],
  ['B1.13.1-UX1-BANCO194.patch', 'e9f03e8c0fb62d4cec6867efc2c4e4e03d8b8f1edf8cb7d5027794d1044d6546'],
  ['B1.13.1-UX1-BANCO194-ROTATION.patch', 'a205da4ed5d7bde101a038fc7e854c0431ad41ef81f7ea6689745d0d73ab3b3e'],
];
const CSV = 'https://docs.google.com/spreadsheets/d/1BdB1GrSfQ0cFmfWC7nidqycvQvrlig9bHwl1rU1VNkU/gviz/tq?tqx=out:csv&sheet=Banco';
const sha = x => crypto.createHash('sha256').update(x).digest('hex');
const get = async u => {
  const r = await fetch(u);
  if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + u);
  return r;
};
function parseCsv(csv) {
  const rows = [];
  let row = [], cell = '', quoted = false;
  for (let i = 0; i < csv.length; i++) {
    const ch = csv[i];
    if (ch === '"') {
      if (quoted && csv[i+1] === '"') { cell += '"'; i++; }
      else quoted = !quoted;
    } else if (ch === ',' && !quoted) { row.push(cell); cell = ''; }
    else if ((ch === '\n' || ch === '\r') && !quoted) {
      if (ch === '\r' && csv[i+1] === '\n') i++;
      row.push(cell); if (row.some(Boolean)) rows.push(row);
      row = []; cell = '';
    } else cell += ch;
  }
  if (quoted) throw new Error('CSV incompleto');
  row.push(cell); if (row.some(Boolean)) rows.push(row);
  return rows;
}
function approvedQuestions(csv) {
  const [header, ...rows] = parseCsv(csv);
  if (!header || header[1] !== 'Letra' || header[2] !== 'Respuesta' || header[3] !== 'Definición' || header[5] !== 'Estado') throw new Error('Columnas cambiaron');
  const normalize = s => s.toUpperCase().replace(/Ñ/g, '__ENIE__').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/__ENIE__/g, 'Ñ');
  const questions = rows.filter(r => r[5] === 'APROBADA').map(r => {
    const letter = r[1]?.trim().toUpperCase(), answer = r[2]?.trim(), definition = r[3]?.trim();
    const norm = normalize(answer || ''), nl = normalize(letter || '');
    const rule = r[15] === 'EMPIEZA' || r[15] === 'CONTIENE' ? r[15] : norm.startsWith(nl) ? 'EMPIEZA' : 'CONTIENE';
    if (!letter || !answer || !definition || !(rule === 'EMPIEZA' ? norm.startsWith(nl) : norm.includes(nl))) throw new Error('Letra incompatible: ' + answer);
    return [letter, answer, definition, [], rule];
  });
  if (questions.length !== 398) throw new Error('No hay 398 aprobadas');
  return questions;
}
async function main() {
  const manifest = JSON.parse(fs.readFileSync('piper-audio/manifest.json', 'utf8'));
  if (manifest.approved !== 398 || manifest.clips !== 811 || Object.keys(manifest.entries).length !== 811) throw new Error('Manifiesto incompleto');
  const [zipBytes, csvText] = await Promise.all([(await get(SOURCE)).arrayBuffer(), (await get(CSV)).text()]);
  if (sha(Buffer.from(zipBytes)) !== '89fa0a512c42d66f58aa29e82e99ce40d62e315fbf314838fd54446e7ba70fcf') throw new Error('ZIP original alterado');
  if (sha(csvText) !== manifest.bank_sha256) throw new Error('Banco y MP3 desincronizados');
  const questions = approvedQuestions(csvText);
  const z = await JSZip.loadAsync(zipBytes);
  let html = await z.file('index.html').async('string');
  if (sha(html) !== '465e091e3ae8d55416565fe8c7b81b30f9f937d00338d527b98fd991abf741c8') throw new Error('HTML original alterado');
  for (const [patch, expected] of PATCHES) {
    html = applyPatch(html, await (await get(PATCH_BASE + patch)).text());
    if (!html || sha(html) !== expected) throw new Error('Parche alterado: ' + patch);
  }
  const oldMp3 = Object.keys(z.files).filter(x => x.startsWith('new-audio/') && x.endsWith('.mp3'));
  if (oldMp3.length !== 188) throw new Error('Audios originales incompletos');
  const marker = 'const ACTIVE_QUESTION_POOL=QUESTION_POOL.slice();';
  if (html.split(marker).length !== 2 || html.indexOf('const NEW_VOICE_AUDIO=') > html.indexOf(marker)) throw new Error('Punto de inserción inválido');
  const insertBank = [
    'const MASTER_APPROVED_POOL=' + JSON.stringify(questions).replace(/</g, '\\u003c') + ';',
    'const approvedKeys=new Set(MASTER_APPROVED_POOL.map(q=>normalize(q[1])));',
    'for(let i=QUESTION_POOL.length-1;i>=0;i--){if(!approvedKeys.has(normalize(QUESTION_POOL[i][1])))QUESTION_POOL.splice(i,1);}',
    'const existingKeys=new Set(QUESTION_POOL.map(q=>normalize(q[1])));',
    'for(const q of MASTER_APPROVED_POOL){const key=normalize(q[1]);if(!existingKeys.has(key)){QUESTION_POOL.push(q);existingKeys.add(key);}}',
    'if(MASTER_APPROVED_POOL.length!==398)throw new Error("Banco incompleto");',
  ].join('\n');
  for (let i = 0; i < questions.length; i++) {
    const [letter, answer, definition, , rule] = questions[i], row = manifest.rows[i];
    const key = rule === 'CONTIENE' ? 'Contiene ' + letter + ': ' + definition : letter + ': ' + definition;
    if (row.letter !== letter || row.answer !== answer || row.definition !== definition || row.rule !== rule || row.question_key !== key || !manifest.entries[key] || !manifest.entries['Incorrecto. Era ' + answer + '.']) throw new Error('Audio desincronizado: ' + answer);
  }
  const portableMap = Object.fromEntries(Object.entries(manifest.entries).map(([key, url]) => {
    if (!url.startsWith('https://raw.githubusercontent.com/facundocapello-blip/mambapalabra-staging/qa/piper-audio-398/piper-audio/')) throw new Error('URL externa inesperada');
    return [key, 'piper-audio/' + url.split('/').at(-1)];
  }));
  const insertAudio = [
    'const PIPER_AUDIO_MAP=' + JSON.stringify(portableMap).replace(/</g, '\\u003c') + ';',
    'for(const [phrase,url] of Object.entries(PIPER_AUDIO_MAP)){STATIC_AUDIO[phrase]=url;NEW_VOICE_AUDIO.add(url);}',
  ].join('\n');
  html = html.replace(marker, insertBank + '\n' + insertAudio + '\n' + marker);
  html = html.replaceAll('/Mambapalabra/new-audio/', 'new-audio/').replaceAll('/Mambapalabra/_cdn/', '_cdn/');
  z.file('index.html', html);
  const hashes = {};
  for (const file of new Set(Object.values(portableMap))) {
    if (!fs.existsSync(file)) throw new Error('Falta MP3: ' + file);
    const bytes = fs.readFileSync(file);
    if (bytes.length < 1200) throw new Error('MP3 vacío: ' + file);
    hashes[file] = sha(bytes);
    z.file(file, bytes);
  }
  if (Object.keys(hashes).length !== 811) throw new Error('811 MP3 requeridos');
  z.file('PIPER_RELEASE.json', JSON.stringify({base:'B1.13.1-RC1+UX1+BANCO194+ROTATION',approved:398,piper_mp3:811,original_mp3:188,bank_sha256:manifest.bank_sha256,voice:manifest.voice,voice_license:'Apache-2.0',note:'STAGING, no publicar en producción sin QA'},null,2));
  z.file('PIPER_ASSETS_SHA256.json', JSON.stringify(hashes,null,2));
  const out = 'dist/MAMBAPALABRA_B1.13.1_UX1_PIPER398_STAGING.zip';
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,await z.generateAsync({type:'nodebuffer',compression:'DEFLATE',compressionOptions:{level:4}}));
  const check = await JSZip.loadAsync(fs.readFileSync(out));
  const count = Object.keys(check.files).filter(x=>x.startsWith('piper-audio/')&&x.endsWith('.mp3')).length;
  if (count !== 811 || !check.file('index.html')) throw new Error('ZIP final incompleto');
  console.log(JSON.stringify({zip:out,bytes:fs.statSync(out).size,sha256:sha(fs.readFileSync(out)),piper_mp3:count,old_mp3:oldMp3.length,approved:questions.length}));
}
await main();

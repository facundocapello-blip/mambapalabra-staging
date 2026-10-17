# Mambapalabra · B1.13.1 UX1 PIPER398 VR1 · Lectura V2 (STAGING)

## Alcance aprobado
- Base: VR1 aprobada por el usuario (valoración rápida por voz).
- Cambiar exclusivamente la locución pregrabada del conductor Piper: **menos pausas y lectura más ágil**.
- Regla EMPIEZA: de «Con la letra be. [definición]» a «Be. [definición]».
- Regla CONTIENE: «Contiene la be. [definición]», conservando la pista necesaria para no cambiar las reglas.
- Motor Piper `es_MX-claude-high`: `length_scale=0.90` (anterior 1.08), `sentence_silence=0.08` (anterior 0.12).
- La voz actual es **provisional**: elegir otro timbre en una etapa separada, sin mezclar cambios.
- 398 definiciones, 398 mensajes de error, 15 frases fijas = 811 MP3. Los 188 MP3 anteriores del ZIP se conservan.
- Producción `facundocapello-blip.github.io/Mambapalabra/`: **sin modificaciones**.

## Pruebas de aceptación y regresión
| ID | Caso | Estado |
| --- | --- | --- |
| V2-01 | Fuente: exactamente 398 APROBADAS, 27 letras y hash del banco idéntico a V1 | PASÓ — banco SHA256 `35b96d…e9aa8`, 398 aprobadas, 27 letras |
| V2-02 | Los 339 clips EMPIEZA comienzan con el nombre de letra sin «Con la letra» | PASÓ — 339 EMPIEZA sin «Con la letra» |
| V2-03 | Los 59 clips CONTIENE mantienen indicación de regla | PASÓ — 59 CONTIENE mantienen la regla |
| V2-04 | 811 MP3 válidos, duración reducida frente a V1 (muestra preguntas, errores y frases) | PASÓ — 811/811 MP3 decodificables por ffprobe; 9 muestras más cortas; ~47 min MP3 |
| V2-05 | Inicio, primera definición, correcta, incorrecta, Pasapalabra, cambio de turno | PASÓ — Chromium y WebKit en STAGING |
| V2-06 | VR1: valoración rápida por voz, transcripción final, no duplicación, reloj pausado en VALIDATING | PASÓ — pruebas de VR1 y reproducción del audio en Chromium; reconocimiento simulado |
| V2-07 | Rotación de palabras entre partidas, sin repetir antes de agotar ciclo | PASÓ — 5 partidas Chromium + 5 WebKit, rotación distinta |
| V2-08 | Fin de tiempo, resultado y reinicio desde partida iniciada | PASÓ — Chromium y WebKit, temporizador de 5 s solo en QA |
| V2-08b | Repetir definición y muerte súbita | PENDIENTE |
| V2-09 | Online en dos sesiones: sincronización, turno, resultado, revancha | PENDIENTE |
| V2-10 | Safari iPhone físico: micrófono, volumen, pronunciación, pausas y cronómetros | PENDIENTE |

No declarar que la versión está validada en iPhone físico a partir de WebKit automatizado.

## Evidencia de ejecución
- [Síntesis de 811 MP3 V2](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39038338392): PASÓ.
- [QA de pronunciación, duración y ZIP íntegro](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39038893217): PASÓ; ZIP SHA256 `8e1590809ba0da04e2e2d8ab0f901a957e00179f8099aa0d8c3cd0bdb6c7ee8d`.
- [QA de navegadores Chromium/WebKit, VR1 y rotación](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39038929869): PASÓ.
- Contenedor local: `ffprobe` inspeccionó los 811 MP3 del ZIP completo; 811 válidos, 0 corruptos, ~47 minutos en MP3.
- Navegador del contenedor local bloqueó URL localhost y file:// por política; se usó GitHub Actions con Chromium y WebKit como alternativa. No se considera prueba física de Safari.
- La versión pública de GitHub Pages sigue intacta.

- [Flujo completo de partida y reinicio](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39039551242): PASÓ en Chromium y WebKit, acierto → agotamiento de ambos relojes → resultado final → reinicio con marcador cero. Temporizador de 5 segundos configurado únicamente en el navegador de prueba.

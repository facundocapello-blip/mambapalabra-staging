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
| V2-01 | Fuente: exactamente 398 APROBADAS, 27 letras y hash del banco idéntico a V1 | PENDIENTE |
| V2-02 | Los 339 clips EMPIEZA comienzan con el nombre de letra sin «Con la letra» | PENDIENTE |
| V2-03 | Los 59 clips CONTIENE mantienen indicación de regla | PENDIENTE |
| V2-04 | 811 MP3 válidos, duración reducida frente a V1 (muestra preguntas, errores y frases) | PENDIENTE |
| V2-05 | Inicio, primera definición, correcta, incorrecta, Pasapalabra, cambio de turno | PENDIENTE |
| V2-06 | VR1: valoración rápida por voz, transcripción final, no duplicación, reloj pausado en VALIDATING | PENDIENTE |
| V2-07 | Rotación de palabras entre partidas, sin repetir antes de agotar ciclo | PENDIENTE |
| V2-08 | Repetir definición, fin de tiempo, resultado, reinicio y muerte súbita | PENDIENTE |
| V2-09 | Online en dos sesiones: sincronización, turno, resultado, revancha | PENDIENTE |
| V2-10 | Safari iPhone físico: micrófono, volumen, pronunciación, pausas y cronómetros | PENDIENTE |

No declarar que la versión está validada en iPhone físico a partir de WebKit automatizado.

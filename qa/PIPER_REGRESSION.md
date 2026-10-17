# Mambapalabra B1.13.1 UX1 STAGING — Regresión de audio Piper

## Alcance y fuente de verdad
- **Producción:** `https://facundocapello-blip.github.io/Mambapalabra/` — NO modificada.
- **STAGING jugable:** `https://mambapalabra-b1131-ux1-staging.floot.app/`.
- **Base HTML aprobada:** ZIP B1.13.1-RC1, SHA256 `89fa0a512c42d66f58aa29e82e99ce40d62e315fbf314838fd54446e7ba70fcf`, más tres parches verificados.
- **Banco:** 398 definiciones APROBADAS; CSV SHA256 `35b96d6920647bbe6d17cdf208a5990ea3e2a890c549d308bd93d58abe3e9aa8`.
- **Motor:** Piper, voz `es_MX-claude-high`, licencia del dataset Apache-2.0. Sin pagos, API ni créditos de generación.
- **Archivos:** 398 preguntas + 398 mensajes de error + 15 frases del conductor = **811 MP3** (25,94 MiB). La rama `qa/piper-audio-398` no reemplaza producción.

## Pruebas reproducibles
| ID | Caso / resultado esperado | Evidencia | Estado |
| --- | --- | --- | --- |
| A01 | ZIP original y HTML tras cada parche coinciden con SHA256 aprobados | Verificación Node.js en Floot VM | PASÓ |
| A02 | Banco tiene exactamente 398 aprobadas y coincide con manifiesto Piper | SHA256 CSV y 398 claves comprobadas | PASÓ |
| A03 | Existen 811 MP3 no vacíos, generados por Piper sin API paga | GitHub Actions [generación](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39016956233) | PASÓ |
| A04 | MP3 de principio, final y frases fijas responden HTTP 200, tipo audio/mpeg, CORS * | Solicitudes HEAD a q0001, w0001, q0398, w0398, fixed15 | PASÓ |
| A05 | El HTML final inyectado tiene JavaScript sintácticamente válido | Node vm.Script | PASÓ |
| A06 | El host Floot STAGING compila sin errores TypeScript | Floot typecheck | PASÓ |
| A07 | Inicio local, primera definición, audio, Pasapalabra, cambio de jugador, error y acierto | [QA Chromium/WebKit](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39018054472) | Chromium PASÓ; WebKit PASÓ tras retirar solo en QA el badge Floot |
| A08 | PASAPALABRA por botón y por voz; repetir definición; fin de tiempo; resultado; reinicio; muerte súbita | QA funcional adicional | PENDIENTE |
| A09 | Online con dos sesiones independientes, turnos, resultado y revancha | QA con dos contextos y backend STAGING | PENDIENTE |
| A10 | Safari en iPhone físico: reproducción de audio, permisos, relojes y latencia | Dispositivo real | PENDIENTE |\n| A11 | En WebKit horizontal 844×390, ENVIAR no debe quedar tapado por el badge Floot | [Reproducción](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39017646748) | FALLA: overlay de Floot intercepta el botón; corregir distribución sin pagar ni ocultar el badge |
| A12 | Cinco partidas reales consecutivas conservando almacenamiento: primera palabra A distinta en cada una | [QA Chromium y WebKit](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39018998654) | PASÓ: 5/5 distintas en ambos navegadores; sin errores JS |
| A13 | Valoración por voz VR1: parcial correcto inmediato; incorrecto a 320 ms; Pasapalabra por voz; final tardío prevalece; silencio no da falso error; reloj pausado | [QA Chromium y WebKit](https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39024555814) | PASÓ: 6 ms/27 ms correcto, 333 ms/335 ms incorrecto, 9 ms/17 ms Pasapalabra |

## Regla de relojes
Los cronómetros de ambos jugadores deben avanzar **únicamente en ANSWERING**. Se mantienen pausados en READING, VALIDATING y SWITCHING, incluido el audio Piper y el cambio de turno.

## Regla de regresión
Para cada cambio posterior, repetir A01–A07 y agregar el caso específico. No modificar producción ni reemplazar los 188 MP3 originales del ZIP hasta completar la validación funcional y aprobar la publicación.

## Evidencia complementaria
- Los **811 MP3** del ZIP fueron examinados con `ffprobe` en contenedor local: **811/811 válidos**, 0 archivos corruptos, 56,24 minutos totales de audio.
- ZIP íntegro B1.13.1 UX1 Piper: SHA256 `66157d89dd076ac5cc2fd27743d599d014fcf44e3efaec6d5d570e9869099f49`, 36.159.406 bytes, 811 MP3 nuevos + 188 originales.
- Prueba WebKit en GitHub Actions: audios de definición y error HTTP 200, sin excepciones JS; el distintivo Floot se retiró únicamente en el navegador de QA para poder pulsar ENVIAR. **Eso no corrige A11.**

## Aleatoriedad y palabras antiguas
- Banco de 398 aprobadas: **193 palabras del banco anterior** y **205 nuevas**. Las antiguas siguen siendo candidatas válidas; verlas no significa que el sorteo esté fijo.
- La rotación elige sin repetición por letra hasta agotar sus opciones; el número de opciones varía: A=17, B=19, K=6, W=7.
- Simulación del selector exacto: 12 partidas × 2 jugadores × 27 letras = **648 selecciones**, sin repetición dentro de cada ciclo por letra.
- QA de navegador: 5 partidas en Chromium y 5 en WebKit; en ambos, las cinco primeras respuestas de A fueron diferentes.
- **La web de producción no recibió la versión STAGING**; si se juega desde el enlace habitual, no se está verificando el banco Piper de 398.

## B1.13.1-UX1-PIPER398-VR1 — 17/10/2026
- **Reproducción:** versión anterior sin valoración tras 520 ms desde `onspeechend` si Web Speech solo devolvía un parcial y ningún resultado final; seguía sin valorar al cerrar el motor.
- **Causa:** `onresult` ignoraba los resultados parciales; `onspeechend` esperaba hasta 1500 ms; `onend` descartaba el texto provisional.
- **Corrección acotada:** `startRecognition` conserva el último parcial; acepta un correcto o `pasapalabra` al finalizar la voz, prioriza el resultado final y acepta un parcial no final tras 320 ms (o al cerrarse el motor). Si no hay texto, conserva la espera de seguridad de 1500 ms y no inventa una respuesta.
- **Prueba automática real:** Chromium y WebKit, con SpeechRecognition simulado para reproducir temporizaciones controladas, sobre STAGING publicada. Se comprobaron aciertos, errores, Pasapalabra, prevalencia del final, ausencia de duplicados, silencio y relojes pausados en VALIDATING. **No es una prueba de reconocimiento acústico en micrófono real.**
- **Evidencia:** https://github.com/facundocapello-blip/mambapalabra-staging/actions/runs/39024555814
- **Pendiente:** Safari iPhone físico y pruebas online completas con dos sesiones; A11 overlay Floot horizontal sigue sin corregirse.

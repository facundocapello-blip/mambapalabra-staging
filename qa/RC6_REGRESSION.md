# RC6 — regresión de conductor y cambios de turno

Base obligatoria: RC5 aprobada, paquete QA GitHub Actions 39438581046. Solo STAGING.

## Reproducción de errores de RC5
- Local: `HOST_PLAYBACK_RATE=.92` × `1.12` = `1.0304` para definiciones. El aumento era apenas perceptible.
- Online: definición a `1.12`, diferente de local.
- Incorrecta: `wrongLead="Incorrecto. Era <respuesta>."`, luego `playerAnnouncement` y recién la siguiente definición.
- Pasapalabra: `CUSTOM_AUDIO.pass=null`; no había locución breve Fish de «Pasapalabra», pero sí anuncio de jugador.
- Muerte súbita: incorrecta recitaba la respuesta y se anunciaba el siguiente jugador.

## Criterios RC6
- Definición Fish `fish-bank/qNNNN.mp3`: `playbackRate=1.22` tanto local como online; `preservesPitch=true`.
- Incorrecta: solo `fish-audio/09_incorrecto_corto.mp3`; respuesta correcta sigue visible, no se recita ni se anuncia jugador.
- Pasapalabra por botón y por comando de voz: solo `fish-audio/10_pasapalabra_corto.mp3`; siguiente definición sin anuncio de jugador.
- Se conserva la voz Fish original; se generan únicamente dos clips nuevos con `s2.1-pro-free`, sin fallback pago.
- Se conservan los 811 MP3 de preguntas/respuestas, los 8 Fish de RC5 y los 188 históricos byte a byte.
- Los relojes solo avanzan en ANSWERING, nunca durante READING, VALIDATING o SWITCHING.
- Sin cambios en producción.

## Lista reutilizable de pruebas
- [ ] Sintaxis JS y comparación byte a byte de todos los MP3 de RC5.
- [ ] Decodificación, duración, identidad de voz declarada y hashes distintos de los dos clips.
- [ ] Chromium + WebKit: intro → primera definición 1.22 → respuesta correcta → siguiente letra.
- [ ] Chromium + WebKit: incorrecta → solo «Incorrecto» → cambio de jugador → nueva definición.
- [ ] Chromium + WebKit: Pasapalabra botón → solo «Pasapalabra» → cambio de jugador.
- [ ] Pasapalabra por reconocimiento de voz real en Safari iPhone (pendiente de dispositivo físico).
- [ ] Repetir definición; reloj pausado durante reproducción.
- [ ] Fin de tiempo, resultados y reinicio.
- [ ] Partida local completa → empate → muerte súbita → ganador → reinicio.
- [ ] Online con dos navegadores independientes y Supabase STAGING real: crear/unirse, puntuación, error, pasapalabra, cambio de turno y sincronización.
- [ ] Revancha online; no alterar producción.
- [ ] Comprobación HTTPS del manifiesto RC6 y descarga real de MP3.
- [ ] Safari físico: naturalidad de velocidad y calidad de voz (pendiente de escucha del usuario).

La automatización de audio acelera/simula la duración de los clips para las pruebas funcionales; no sustituye escucha acústica humana.

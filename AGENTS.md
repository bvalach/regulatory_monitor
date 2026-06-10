Regulatory monitor — vigilancia normativa España/UE para la industria cárnica (CNAE 10.13)

OBJETIVO: Demostrar expertise técnica y uso avanzado de agentes de IA para consultoría y empleabilidad, mediante un repositorio y site públicos.

Site público en GitHub Pages que vigila regulación de España y la UE con impacto en la elaboración de productos cárnicos y de volatería (CNAE 10.13). Un pipeline Python determinista, ejecutado semanalmente por GitHub Actions, consulta fuentes públicas (BOE, EUR-Lex, EFSA), filtra por términos configurables con pesos, clasifica por temas mediante reglas y publica un digest semanal más un histórico filtrable. Front-end estático en HTML/CSS/JS vanilla servido desde `docs/`. Sin servidor, sin base de datos, sin secretos.

**Sin IA generativa en runtime.** El pipeline no invoca ningún LLM. La IA generativa se usó en la fase de diseño y construcción, y eso se documenta públicamente en la página de metodología del site.

Documentos de referencia (leer antes de implementar):
- `REQUISITOS.md` — requisitos funcionales y no funcionales, incluido el front-end.
- `ARQUITECTURA.md` — diseño técnico, estructura del repo, fuentes, workflow y plan de implementación.

Demuestra monitoring autónomo sin infraestructura compleja.


---
# Normas y directrices

## 1. Piensa antes de programar

**No des nada por sentado. No ocultes la confusión. Analiza las ventajas y desventajas.**

Antes de implementar:
- Indica tus suposiciones explícitamente. Si tienes dudas, pregunta.
- Si existen varias interpretaciones, preséntalas; no elijas una sin darte cuenta.
- Si existe un enfoque más sencillo, menciónalo. Si es necesario, cuestiona las alternativas.
- Si algo no está claro, detente. Identifica lo que te confunde. Pregunta.

## 2. Prioriza la simplicidad

**Código mínimo que resuelva el problema. Nada especulativo.**
- Sin funcionalidades adicionales a las solicitadas.
- Sin abstracciones para código de un solo uso.
- Sin "flexibilidad" ni "configurabilidad" que no se hayan solicitado.
- Sin manejo de errores para escenarios imposibles.
- Si escribes 200 líneas de código y podrías escribir 50, reescríbelas.

Pregúntate: "¿Un ingeniero sénior diría que esto es demasiado complicado?" Si la respuesta es sí, simplifique.

## 3. Cambios quirúrgicos

**Toque solo lo necesario. Limpie únicamente sus propios errores.**

Al editar código existente:
- No «mejoreS» el código, los comentarios ni el formato adyacentes.
- No refactoriceS lo que no esté roto.
- Mantén el estilo existente, incluso si lo harías de forma diferente.
- Si detectas código muerto no relacionado, menciónalo; no lo borres.

Cuando sus cambios creen elementos huérfanos:

- Elimina las importaciones, variables y funciones que tus cambios hayan dejado sin usar.
- No elimines código muerto preexistente a menos que te lo pida.

La prueba: Cada línea modificada debe estar directamente relacionada con mi solicitud.

## 4. Ejecución orientada a objetivos

**Define los criterios de éxito.** Repetir hasta verificar.**

Transformar las tareas en objetivos verificables:

- "Añadir validación" → "Escribir pruebas para entradas no válidas y luego hacer que pasen".
- "Corregir el error" → "Escribir una prueba que lo reproduzca y luego hacer que pase".
- "Refactorizar X" → "Asegurar que las pruebas pasen antes y después".

Para tareas de varios pasos, indicar un plan breve:

1. [Paso] → verificar: [comprobar]
2. [Paso] → verificar: [comprobar]
3. [Paso] → verificar: [comprobar]

Los criterios de éxito sólidos permiten repetir el proceso de forma independiente. 
Los criterios débiles ("hacer que funcione") requieren aclaraciones constantes.
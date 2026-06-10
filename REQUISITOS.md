# REQUISITOS.md — Regulatory Monitor (CNAE 10.13)

> Documento de requisitos para la implementación. Léase junto con `ARQUITECTURA.md` y `AGENTS.md`.
> Audiencia: el modelo/desarrollador que escribirá el código.

## 1. Objetivo del producto

Sitio web público (GitHub Pages) que vigila la regulación y la evidencia científico-regulatoria a nivel **España y Unión Europea** que afecta a la industria alimentaria, concretamente al **CNAE 10.13 — Elaboración de productos cárnicos y de volatería**.

Doble propósito:

1. **Utilidad real**: digest semanal y archivo histórico navegable de novedades normativas y científico-regulatorias relevantes para un elaborador cárnico español (PYME tipo: embutidos, curados, cocidos).
2. **Pieza de portfolio**: demostrar capacidad de diseñar y operar un sistema de monitoring autónomo, y documentar públicamente **cómo se usó IA generativa para construirlo** — sin que el sistema use IA generativa en ejecución.

### 1.1 Restricción central: sin GenAI en runtime

El pipeline es **100 % determinista**: ingesta de fuentes públicas, filtrado por términos configurables y clasificación por reglas. **Ningún LLM se invoca durante la ejecución.** El uso de IA generativa pertenece a la fase de construcción y se documenta en la página de metodología (RF-12).

## 2. Usuarios y casos de uso

| Usuario | Caso de uso |
|---------|-------------|
| Responsable de calidad/operaciones de una PYME cárnica | "¿Qué ha salido esta semana que me afecte?" → lee el digest. |
| Consultor / técnico agroalimentario | "¿Qué se ha publicado sobre nitritos desde 2026?" → filtra el histórico. |
| Reclutador / cliente potencial de Bea | "¿Cómo está hecho esto y qué papel jugó la IA?" → lee la metodología. |

## 3. Requisitos funcionales

### 3.1 Pipeline de datos (backend, Python)

- **RF-1 — Ingesta de fuentes públicas sin credenciales.** El pipeline consulta, como mínimo:
  - **BOE** — API de datos abiertos de sumarios diarios (`https://www.boe.es/datosabiertos/api/boe/sumario/{AAAAMMDD}`, XML/JSON, sin key).
  - **EUR-Lex / DOUE** — acceso programático público (SPARQL de CELLAR o feeds RSS del DOUE; ver `ARQUITECTURA.md` §3.2). Acotado a actos publicados en el periodo consultado.
  - **EFSA** — feeds RSS de publicaciones de EFSA y/o portal OpenEFSA (opiniones científicas y evidencia de evaluación de riesgo, sin key). EFSA debe mostrarse como fuente científico-regulatoria, no como fuente de actos normativos.
  - Ninguna fuente puede requerir registro, API key ni scraping que viole sus términos de uso.
- **RF-2 — Ventana temporal con solape.** Cada ejecución consulta los últimos **N días (por defecto 9)** para una cadencia semanal con solape de seguridad. La ventana de consulta no define por sí sola la semana del digest: sirve para capturar retrasos y reintentos. La deduplicación por `id` garantiza idempotencia: re-ejecutar no duplica ítems.
- **RF-3 — Filtrado por términos configurables.** Un fichero `config/terminos.yaml` define:
  - Términos con **peso** (p. ej. `nitritos: 10`, `embutido: 8`, `etiquetado: 5`, `listeria: 9`…), agrupados por **tema** de la taxonomía (§3.2).
  - Términos de **exclusión absoluta** (descartan el ítem aunque puntúe). Si una exclusión necesita excepciones, no debe modelarse como exclusión absoluta en v1.
  - **Umbral mínimo** de puntuación para inclusión.
  - El matching es sobre texto normalizado (minúsculas, sin tildes), por frase exacta normalizada o palabra completa, sobre **título y sumario/extracto oficial**. Coincidencia en título pondera ×2. No hay lematización automática en v1; plurales, variantes y equivalentes EN se declaran explícitamente en YAML.
- **RF-4 — Clasificación temática por reglas.** Cada ítem incluido se etiqueta con uno o más temas de la taxonomía según los términos que lo activaron. Sin clasificadores estadísticos ni LLM.
- **RF-5 — Generación del digest semanal.** Cada ejecución produce:
  - `docs/data/digests/AAAA-Wss.json` — ítems publicados en la semana ISO `AAAA-Wss`, agrupados por tema, con metadatos de la ejecución.
  - `digests/AAAA-Wss.md` — versión Markdown legible directamente en GitHub (mismo contenido).
  - Actualización de `docs/data/items-AAAA.json` (histórico anual acumulado), `docs/data/items-index.json` (años disponibles), `docs/data/digests/index.json` (semanas disponibles) y `docs/data/meta.json` (fecha de última ejecución, estado de cada fuente, recuentos).
  - En ejecución programada, siempre se genera o regenera el digest de la última semana ISO completa. Si la ventana con solape captura ítems de otras semanas, el pipeline puede regenerar también esos digest para mantener coherente el histórico.
  - Una semana sin novedades relevantes produce un digest válido que lo dice explícitamente.
- **RF-6 — Degradación elegante por fuente.** El fallo de una fuente (timeout, cambio de formato) no aborta la ejecución: se registra en `meta.json` (`"estado": "degradada"` + mensaje) y el digest se genera con las fuentes disponibles. El front-end muestra el aviso.

### 3.2 Taxonomía temática (v1, configurable)

1. Higiene y seguridad alimentaria (Reg. 852/853/2073, controles oficiales)
2. Aditivos y contaminantes (nitritos/nitratos, Reg. 1333/2008, límites máximos)
3. Etiquetado e información al consumidor (Reg. 1169/2011, normas de calidad RD)
4. Bienestar animal y sanidad animal (PPA, influenza aviar, transporte)
5. Subproductos y SANDACH
6. Envases y sostenibilidad (PPWR, residuos)
7. Comercio exterior y aranceles
8. Ayudas, subvenciones y fiscalidad sectorial
9. Otros (cajón de relevancia transversal)

### 3.3 Esquema de datos de un ítem

```json
{
  "id": "boe-BOE-A-2026-01234",
  "fuente": "BOE",
  "tipo": "real_decreto",
  "titulo": "Real Decreto .../2026, por el que se ...",
  "url": "https://www.boe.es/...",
  "fecha_publicacion": "2026-06-03",
  "fecha_captura": "2026-06-08",
  "temas": ["aditivos_contaminantes"],
  "terminos": ["nitritos", "derivados cárnicos"],
  "score": 28,
  "extracto": "Texto del sumario o título oficial; nunca texto generado."
}
```

- `id` es estable y derivado del identificador oficial (BOE-A-…, CELEX, DOI EFSA).
- `tipo` ∈ {reglamento, directiva, decision, real_decreto, orden, resolucion, anuncio, opinion_cientifica, otro}.
- `extracto` procede **siempre** de la fuente oficial (sumario, título largo, abstract); nunca es texto generado.

### 3.4 Contratos de datos públicos

- **RF-7 — Contratos de datos públicos.** Además de los ítems históricos, el front-end depende de contratos JSON estables:
  - `docs/data/meta.json`: última ejecución, ventana consultada, digest más reciente, años disponibles, recuentos y estado por fuente.
  - `docs/data/items-index.json`: lista ordenada de años disponibles para que el histórico no dependa de listar directorios en GitHub Pages.
  - `docs/data/digests/index.json`: lista ordenada de semanas disponibles, con `id`, periodo, ruta JSON pública y ruta Markdown relativa al repositorio. Los Markdown de `digests/` son legibles en GitHub, no necesariamente servidos por GitHub Pages.
  - `docs/data/digests/AAAA-Wss.json`: metadatos de la semana, estado de fuentes e ítems agrupados por tema.
  - El histórico público debe conservar, como mínimo, los últimos **24 meses** de ítems filtrados y metadatos de fuente.

La forma exacta de estos JSON se fija en `ARQUITECTURA.md`, pero debe mantenerse compatible entre pipeline y front-end.

### 3.5 Automatización (GitHub Actions)

- **RF-8 — Ejecución programada.** Workflow con `schedule` (cron semanal, lunes 06:00 UTC) y `workflow_dispatch` (manual). Ejecuta el pipeline, y si hay cambios en `docs/data/`, `digests/` los commitea a `main`. GitHub Pages (deploy from branch, carpeta `/docs`) publica automáticamente.
- **RF-9 — Transparencia operativa.** El log del workflow es público; `meta.json` expone fecha/hora de la última ejecución y el estado por fuente.

### 3.6 Front-end (site estático en `docs/`)

Stack: **HTML + CSS + JavaScript vanilla**, sin frameworks, sin paso de build, sin dependencias npm. Los datos se cargan con `fetch` desde `docs/data/`.

- **RF-10 — Página principal (`index.html`).**
  - Cabecera: nombre del proyecto, una frase de propósito, fecha de última actualización (de `meta.json`) y aviso si alguna fuente está degradada.
  - **Último digest** renderizado: ítems agrupados por tema, cada uno con badge de fuente (BOE/EUR-Lex/EFSA), tipo, fecha, título enlazado a la fuente oficial y extracto.
  - Navegación a digests anteriores (lista por semana, desde un índice `docs/data/digests/index.json`).
- **RF-11 — Histórico filtrable (`historico.html`).**
  - Tabla/listado de todos los ítems del año seleccionado (carga `items-index.json` para descubrir años y `items-AAAA.json` bajo demanda; selector de año).
  - Filtros combinables en cliente: **fuente, tipo, tema, búsqueda de texto libre** (sobre título y extracto).
  - Ordenación por fecha (defecto, descendente) y por score. Contador de resultados visible. Paginación o render incremental en cliente (50 ítems por bloque).
  - Estado vacío explícito ("ningún resultado con estos filtros").
- **RF-12 — Página de metodología (`metodologia.html`).** Contenido estático que explica:
  - El pipeline completo (diagrama SVG estático del flujo fuentes → filtrado → digest → Pages).
  - Las fuentes consultadas, con endpoints y limitaciones, distinguiendo actos normativos (BOE, EUR-Lex/DOUE) de evidencia científico-regulatoria (EFSA).
  - Los criterios de filtrado: taxonomía, términos y pesos (puede renderizar `terminos.yaml` o resumirlo), umbral, y por qué es un sistema de reglas y no un LLM.
  - **Sección "Cómo se usó IA generativa"**: relato honesto del proceso — especificación y arquitectura diseñadas en conversación con Claude (este repo conserva `AGENTS.md`, `REQUISITOS.md` y `ARQUITECTURA.md` como evidencia), código generado por un modelo a partir de la especificación, revisión y decisiones humanas. Enlaces a esos ficheros en GitHub.
  - Limitaciones conocidas (cobertura no exhaustiva, dependencia de sumarios oficiales, no es asesoramiento jurídico).

### 3.7 Contenido transversal del site

- **RF-13 — Idioma:** todo el UI en **español** (`lang="es"`, fechas formato es-ES). Títulos de normas en su idioma original de la fuente.
- **RF-14 — Footer en todas las páginas:** disclaimer legal ("Este sitio es informativo y no constituye asesoramiento jurídico; verifique siempre la fuente oficial"), enlace al repositorio de GitHub, autoría y licencia.

## 4. Requisitos no funcionales

- **RNF-1 — Simplicidad.** Sin servidor, sin base de datos, sin build del front. Los JSON commiteados *son* la base de datos. Regla del `AGENTS.md`: si algo se puede resolver con menos código, se resuelve con menos código.
- **RNF-2 — Rendimiento.** Histórico particionado por año para que ninguna carga inicial supere ~200 KB de JSON. Sin librerías JS externas; CSS propio.
- **RNF-3 — Accesibilidad.** HTML semántico, contraste AA, formularios de filtro etiquetados (`label`), navegable por teclado, foco visible.
- **RNF-4 — Responsive.** Usable en móvil (el digest es lectura de lunes por la mañana); la tabla del histórico colapsa a tarjetas en pantallas estrechas.
- **RNF-5 — Privacidad.** Sin cookies, sin analítica, sin recursos de terceros (fuentes tipográficas del sistema).
- **RNF-6 — Buenas prácticas de ingesta.** `User-Agent` identificado con URL del repo, timeouts y reintentos con backoff suave, respeto de los términos de cada fuente. Volumen de peticiones trivial (semanal).
- **RNF-7 — Calidad.** Tests `pytest` con fixtures locales (XML/JSON de muestra de cada fuente): parsers, scoring, dedupe, generación de digest. El workflow de Actions ejecuta los tests antes del pipeline.
- **RNF-8 — Licencias.** Código bajo MIT. Los textos normativos y sumarios pertenecen a sus fuentes oficiales y se enlazan, no se republican íntegros.

## 5. Fuera de alcance (v1)

- Integración de IA generativa en el pipeline (resúmenes automáticos, clasificación LLM) — posible v2, documentado como evolución en la metodología.
- Dashboard de tendencias/gráficos.
- Suscripción por email / notificaciones.
- Versión en inglés del UI.
- Más fuentes (AESAN, DOG/BOPA autonómicos) — listadas como evolución.

## 6. Criterios de aceptación

1. `python -m pipeline` en local genera digest por semana ISO, histórico anual, índices (`docs/data/items-index.json`, `docs/data/digests/index.json`) y `meta.json` válidos contra fixtures y contra las fuentes reales.
2. El workflow programado se ejecuta de principio a fin y publica cambios en Pages sin intervención manual.
3. Con una fuente caída (simulada), el digest se genera igualmente y el site muestra el aviso de degradación.
4. Las tres páginas funcionan sin consola de errores, sin red salvo los `fetch` a `docs/data/`, y pasan validación HTML básica.
5. Una persona ajena puede entender en la página de metodología qué hace el sistema, qué no hace, y qué papel jugó la IA generativa.

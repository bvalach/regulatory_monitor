# ARQUITECTURA.md — Regulatory Monitor (CNAE 10.13)

> Diseño técnico para la implementación. Los requisitos están en `REQUISITOS.md`; las normas de trabajo, en `AGENTS.md`.

## 1. Visión general

Arquitectura **estática y sin servidor**: un pipeline Python ejecutado semanalmente por GitHub Actions consulta fuentes públicas, filtra por reglas, y commitea los resultados como JSON/Markdown al propio repositorio. GitHub Pages sirve un front-end vanilla desde `docs/`. No hay base de datos, ni API propia, ni LLM en ejecución.

El monitor combina actos normativos (BOE y EUR-Lex/DOUE) con evidencia científico-regulatoria (EFSA). EFSA se muestra siempre como señal de evaluación de riesgo o contexto técnico, no como acto normativo.

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│     BOE     │   │   EUR-Lex   │   │    EFSA     │
│ (API datos  │   │  (CELLAR /  │   │ (RSS / Open │
│  abiertos)  │   │  RSS DOUE)  │   │    EFSA)    │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       └─────────────────┼─────────────────┘
                         ▼
          GitHub Actions (cron semanal + manual)
                         │
            pipeline Python (determinista)
   ingesta → normalización → filtrado/score → temas
                         │
                         ▼
        commit a main:  docs/data/*.json  +  digests/*.md
                         │
                         ▼
          GitHub Pages (from branch, carpeta /docs)
                         │
                         ▼
        front-end vanilla: index / histórico / metodología
```

Por qué así: el repositorio público **es** la infraestructura y a la vez la evidencia del portfolio — datos versionados, logs públicos, cero coste de operación, cero secretos.

## 2. Estructura del repositorio

```
regulatory_monitor/
├── AGENTS.md                  # normas de trabajo para agentes
├── REQUISITOS.md              # qué construir
├── ARQUITECTURA.md            # este documento
├── README.md                  # presentación del proyecto (crear en implementación)
├── LICENSE                    # MIT
├── requirements.txt           # dependencias del pipeline (mínimas)
├── config/
│   └── terminos.yaml          # términos, pesos, temas, exclusiones, umbral
├── pipeline/
│   ├── __init__.py
│   ├── __main__.py            # entrypoint: python -m pipeline [--desde AAAA-MM-DD]
│   ├── modelos.py             # dataclasses Item + ResultadoFuente + JSON
│   ├── fuentes/
│   │   ├── __init__.py        # interfaz común: obtener(ventana) -> ResultadoFuente
│   │   ├── boe.py
│   │   ├── eurlex.py
│   │   └── efsa.py
│   ├── filtrado.py            # normalización de texto, matching, score, temas
│   ├── almacen.py             # carga/merge/dedupe de items-AAAA.json e índices
│   └── digest.py              # agrupación semanal por fecha_publicacion
├── tests/
│   ├── fixtures/              # XML/JSON/RSS de muestra por fuente
│   └── test_*.py
├── digests/                   # digest semanal en Markdown (lectura en GitHub)
│   └── 2026-W23.md
├── docs/                      # ← raíz de GitHub Pages
│   ├── index.html             # último digest + archivo de digests
│   ├── historico.html         # buscador/filtros del histórico
│   ├── metodologia.html       # pipeline, criterios, uso de GenAI
│   ├── assets/
│   │   ├── estilos.css
│   │   ├── app.js             # utilidades comunes (fetch, formato fechas, render)
│   │   ├── historico.js       # lógica de filtros/orden/paginación
│   │   └── pipeline.svg       # diagrama estático para metodología
│   └── data/
│       ├── meta.json          # última ejecución, estado por fuente, recuentos
│       ├── items-index.json   # años disponibles para el histórico
│       ├── items-2026.json    # histórico anual
│       └── digests/
│           ├── index.json     # lista de semanas disponibles
│           └── 2026-W23.json
└── .github/
    └── workflows/
        └── monitor.yml        # tests + pipeline + commit
```

Decisiones de estructura:

- **El site vive en `docs/`** porque Pages "deploy from branch" solo admite raíz o `/docs`; así no hace falta workflow de despliegue.
- **Datos dentro de `docs/data/`** para que el front los lea con `fetch` relativo, sin CORS ni configuración.
- **`digests/*.md` en la raíz** duplica el contenido del digest en formato legible en GitHub: barato y útil para quien navega el repo.
- **Retención mínima de 24 meses**: el histórico anual en `docs/data/items-AAAA.json` se conserva como dato versionado. En v1 no hay purga automática; si en el futuro se añade, no debe reducir el histórico público por debajo de 24 meses.

## 3. Pipeline (Python ≥ 3.11)

Dependencias mínimas: `httpx` (o `requests`), `PyYAML`, `pytest` para tests. Nada más salvo justificación. La librería estándar cubre XML (`xml.etree`), fechas y JSON. Si EUR-Lex se resuelve por SPARQL, la query va por HTTP plano (sin cliente SPARQL dedicado).

### 3.1 Flujo de una ejecución

1. **Ventana y semana objetivo**: calcular `[hoy − N días, hoy]` (N=9 por defecto, override por CLI para backfill) y la última semana ISO completa. En ejecución ordinaria del lunes, esa semana es el lunes-domingo inmediatamente anterior.
2. **Ingesta**: cada módulo de `fuentes/` devuelve un `ResultadoFuente` con ítems brutos normalizados al esquema común (`modelos.Item`) y estado de la fuente. Cada fuente atrapa sus propias excepciones; un fallo se traduce en `estado="degradada"` sin abortar (RF-6).
3. **Filtrado** (`filtrado.py`):
   - Normalizar texto: minúsculas + eliminación de tildes (NFD) sobre título y extracto.
   - Matching por frase exacta normalizada o palabra completa de los términos de `terminos.yaml`; coincidencia en título pondera ×2.
   - `score = Σ pesos`; descartar si aparece un término de exclusión absoluta o si `score < umbral`.
   - `temas` = temas de los grupos cuyos términos coincidieron.
4. **Merge** (`almacen.py`): cargar `items-AAAA.json`, fusionar por `id` (los nuevos no machacan `fecha_captura` original), reescribir ordenado por `fecha_publicacion` desc y actualizar `items-index.json`.
5. **Digest** (`digest.py`): generar o regenerar el digest de la semana ISO objetivo a partir de `fecha_publicacion`; si la ventana incluye ítems relevantes de otras semanas ya completas, regenerar también esas semanas afectadas. En ejecuciones manuales a mitad de semana no se publica un digest parcial de la semana ISO en curso. Salidas: `docs/data/digests/AAAA-Wss.json`, `digests/AAAA-Wss.md`, `docs/data/digests/index.json` y `docs/data/meta.json`.
6. La ejecución es **idempotente**: relanzarla el mismo día regenera los mismos ficheros sin duplicados y con orden estable.

### 3.2 Fuentes — detalle de implementación

| Fuente | Acceso | Notas |
|--------|--------|-------|
| **BOE** | `GET https://www.boe.es/datosabiertos/api/boe/sumario/{AAAAMMDD}` (header `Accept: application/json`) | Una petición por día de la ventana. Recorrer secciones y normalizar nodos que pueden venir como objeto único o lista; mapear `tipo` desde sección/epígrafe/título. `id = "boe-" + identificador BOE-A-…`. Es la fuente más estable: implementarla primero. |
| **EUR-Lex** | SPARQL público de CELLAR (`https://publications.europa.eu/webapi/rdf/sparql`) — documentos por rango de fecha de publicación, con título en ES mediante `cdm:expression_belongs_to_work`. | El filtrado fino lo hace `filtrado.py`; la query solo acota por fechas. `id = "celex-" + CELEX`. |
| **EFSA** | RSS público de publicaciones de EFSA (`https://www.efsa.europa.eu/en/publications/rss`) | `tipo = "opinion_cientifica"`. Título/abstract en inglés: los términos de `terminos.yaml` deben incluir equivalentes EN (p. ej. `nitrites`, `poultry meat`). `id = "efsa-" + DOI` si existe DOI; si no, usar un identificador estable de la publicación. |

Cliente HTTP común: `User-Agent: regulatory-monitor (+https://github.com/<usuario>/regulatory_monitor)`, timeout 30 s, 2 reintentos con backoff.

### 3.3 `config/terminos.yaml` — forma

```yaml
umbral: 8
ventana_dias: 9
temas:
  aditivos_contaminantes:
    etiqueta: "Aditivos y contaminantes"
    terminos:
      - {t: "nitritos", peso: 10, en: "nitrites"}
      - {t: "nitratos", peso: 8, en: "nitrates"}
  higiene_seguridad:
    etiqueta: "Higiene y seguridad alimentaria"
    terminos:
      - {t: "listeria", peso: 10}
      - {t: "productos cárnicos", peso: 9, en: "meat products"}
  # ... resto de la taxonomía de REQUISITOS.md §3.2
exclusiones:
  - "alimentación animal"   # exclusión absoluta: no usar aquí si necesita excepciones
```

(La forma exacta puede ajustarse en implementación; lo invariable: pesos por término, agrupación por tema, equivalentes EN para EFSA, exclusiones y umbral en un único YAML editable sin tocar código.)

### 3.4 Contratos JSON generados

El front-end no debe inferir ficheros disponibles mediante listado de directorios. Todo lo que necesita debe estar en JSON explícitos y versionados.

`docs/data/meta.json`:

```json
{
  "ultima_ejecucion": "2026-06-08T06:04:12Z",
  "ventana_consulta": {"desde": "2026-05-30", "hasta": "2026-06-08"},
  "digest_reciente": "2026-W23",
  "anios_disponibles": [2026],
  "recuentos": {"items_total": 42, "items_nuevos": 5},
  "fuentes": {
    "BOE": {"estado": "ok", "items": 12},
    "EUR-Lex": {"estado": "ok", "items": 4},
    "EFSA": {"estado": "degradada", "items": 0, "detalle": "timeout"}
  }
}
```

`docs/data/items-index.json`:

```json
{
  "anios": [
    {"anio": 2026, "path": "data/items-2026.json", "items": 42}
  ]
}
```

`docs/data/digests/index.json`:

```json
{
  "ultimo": "2026-W23",
  "digests": [
    {
      "id": "2026-W23",
      "desde": "2026-06-01",
      "hasta": "2026-06-07",
      "json": "data/digests/2026-W23.json",
      "markdown_repo_path": "digests/2026-W23.md",
      "items": 5
    }
  ]
}
```

`docs/data/digests/AAAA-Wss.json`:

```json
{
  "id": "2026-W23",
  "desde": "2026-06-01",
  "hasta": "2026-06-07",
  "generado_en": "2026-06-08T06:04:12Z",
  "estado_fuentes": {},
  "sin_novedades": false,
  "temas": [
    {
      "id": "aditivos_contaminantes",
      "etiqueta": "Aditivos y contaminantes",
      "items": []
    }
  ]
}
```

Los ejemplos son contratos mínimos: se pueden añadir campos, pero no retirar ni cambiar significado sin actualizar pipeline y front-end a la vez.

## 4. GitHub Actions — `monitor.yml`

```yaml
on:
  schedule:
    - cron: "0 6 * * 1"   # lunes 06:00 UTC
  workflow_dispatch:

permissions:
  contents: write

concurrency: monitor   # nunca dos ejecuciones solapadas
```

Pasos: checkout → setup Python con cache pip → `pytest` → `python -m pipeline` → si `git status` muestra cambios en `docs/data/`, `digests/`, commit y push a `main` (autor "regulatory-monitor bot"). Sin secretos: el `GITHUB_TOKEN` implícito basta.

## 5. Front-end (vanilla)

### 5.1 Principios

- Tres páginas HTML independientes con `assets/estilos.css` y JS compartido; **sin SPA, sin router, sin framework, sin build**.
- Render por manipulación del DOM a partir de los JSON (`fetch` relativo a `data/`). Plantillas con `<template>` HTML nativo.
- Tipografías del sistema; paleta sobria (un color de acento + badges por fuente: BOE / EUR-Lex / EFSA con colores distinguibles y accesibles).
- `lang="es"`, fechas con `Intl.DateTimeFormat("es-ES")`.

### 5.2 Comportamiento por página

- **`index.html`**: carga `meta.json` (fecha de actualización + avisos de fuente degradada) y el último digest según `data/digests/index.json`. Render agrupado por tema; cada ítem = badge fuente + tipo + fecha + título-enlace + extracto. Selector/lista de semanas anteriores que carga otro digest sin cambiar de página (mismo render).
- **`historico.html`**: carga `items-index.json`, construye el selector de año y después hace `fetch` de `items-AAAA.json`. Filtros (fuente, tipo, tema como `<select>`; texto libre como `<input type="search">` con debounce) aplicados en memoria. Orden por fecha o score. Render incremental de 50 en 50 con botón "mostrar más". Contador "N resultados". Los filtros se reflejan en la query string (`?fuente=BOE&tema=…`) para que un filtrado sea enlazable.
- **`metodologia.html`**: contenido estático (HTML escrito a mano) + `pipeline.svg`. Incluye la sección de uso de GenAI con enlaces a `AGENTS.md`, `REQUISITOS.md` y `ARQUITECTURA.md` en GitHub (RF-12).

### 5.3 Accesibilidad y responsive

- HTML semántico (`header/nav/main/section/footer`), un `h1` por página, foco visible, `label` en todos los controles de filtro, `aria-live="polite"` en el contador de resultados.
- Breakpoint único (~720 px): el listado del histórico pasa de filas a tarjetas; los filtros se apilan.

## 6. Manejo de errores y observabilidad

- `meta.json` es el contrato de estado operativo. El front muestra fecha de ejecución, digest reciente y fuentes degradadas; los logs completos quedan en Actions (públicos).
- El pipeline termina con exit code 0 si al menos una fuente respondió; ≠ 0 solo si todas fallan (el workflow queda en rojo y GitHub avisa por email al owner).

## 7. Plan de implementación sugerido (orden con verificación)

1. **Esqueleto + modelos + config** → verificar: `pytest` corre, YAML carga.
2. **Fuente BOE con fixtures** → verificar: test de parser con sumario real guardado.
3. **Filtrado y scoring** → verificar: tests de matching, exclusiones, umbral, tildes.
4. **Almacén + digest** → verificar: ejecución repetida = sin duplicados; MD y JSON bien formados.
5. **EUR-Lex y EFSA** (validar acceso real; decidir opción A/B de EUR-Lex) → verificar: fixtures + ejecución real.
6. **Front index + estilos** → verificar: render del digest real en local (`python -m http.server` en `docs/`).
7. **Histórico con filtros** → verificar: filtros combinados, query string, estado vacío.
8. **Metodología + SVG + README** → verificar: enlaces correctos al repo.
9. **Workflow Actions + Pages** → verificar: ejecución manual (`workflow_dispatch`) end-to-end publica el site.

## 8. Evolución prevista (no implementar en v1)

- v2: capa GenAI opcional y claramente separada (resumen ejecutivo del digest con LLM, etiquetado asistido), manteniendo el pipeline determinista como base verificable.
- Más fuentes: AESAN, boletines autonómicos (BOPA), RASFF.
- Dashboard de tendencias sobre los mismos JSON.

# Monitor regulatorio cárnico

Observatorio público de vigilancia normativa y científico-regulatoria para la industria cárnica española, centrado en el CNAE 10.13: elaboración de productos cárnicos y de volatería.

El proyecto combina un pipeline Python determinista con un site estático servido desde GitHub Pages. No usa servidor, base de datos, secretos ni IA generativa en ejecución.

## Qué publica

- Digest semanal en `docs/data/digests/AAAA-Wss.json`.
- Versión Markdown del digest en `digests/AAAA-Wss.md`.
- Histórico anual en `docs/data/items-AAAA.json`.
- Índices públicos en `docs/data/items-index.json`, `docs/data/digests/index.json` y `docs/data/meta.json`.
- Site estático en `docs/` con digest, histórico filtrable y metodología.

## Fuentes

- BOE: API pública de sumarios diarios.
- EUR-Lex / DOUE: endpoint SPARQL público de CELLAR.
- EFSA: RSS público de publicaciones, tratado como evidencia científico-regulatoria.

## Uso local

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
python -m pipeline
python -m http.server 8000 --directory docs
```

El site queda disponible en `http://127.0.0.1:8000/`.

## Configuración

Los temas, términos, pesos, equivalentes en inglés, exclusiones y ventana temporal se editan en `config/terminos.yaml`.

## Transparencia sobre IA

El pipeline semanal no invoca ningún modelo de lenguaje. La IA generativa se usó en la fase de especificación, arquitectura y construcción asistida del código. La página `docs/metodologia.html` explica ese papel y las limitaciones del sistema.

## Aviso

Este proyecto es informativo y no constituye asesoramiento jurídico. Verifique siempre la fuente oficial antes de tomar decisiones regulatorias.

# Buscador de sentencias de seguros

Genera `sentencias/` (exigetuseguro.cl/sentencias/) a partir de las sentencias que la CMF publica en
https://www.cmfchile.cl/institucional/inc/sentencias/resultado_sentencias.php

## Cómo funciona

El flujo `.github/workflows/sentencias.yml` corre todos los días:

| Paso | Archivo | Qué hace |
|---|---|---|
| 1 | `cmf.py` | Revisa el listado de la CMF, descarga solo lo nuevo, extrae el texto y aplica OCR (Tesseract, 300 dpi) a los PDF escaneados. Guarda los textos originales en el repositorio privado `sentencias-datos`. |
| 2 | `crear_base.py` | Arma una base SQLite temporal con los metadatos y textos. |
| 3 | `proc.py` | Detecta tribunal e instancia desde el texto, fecha, rol, carátula; clasifica ramo, temas jurídicos, normas citadas y lo resuelto; limpia el texto. |
| 4 | `links.py` | Vincula sentencias por rol citado o compartido, detecta duplicados y separa los precedentes citados. |
| 5 | `integrate.py` | Reconstruye los expedientes (el ID de causa de la CMF a veces mezcla juicios distintos), las instancias no incluidas y las alertas. |
| 6 | `publicar.py` | Oculta los datos personales (`anonimizar.py`) y genera `sentencias/datos/indice.js` y `sentencias/datos/t/NN.json`. Se detiene si queda algún RUT visible. |

Al final abre un Pull Request con los cambios en `sentencias/datos/`.

## Datos personales

Los textos originales **nunca** se suben a este repositorio público: viven en el repositorio privado
`contacto-lang/sentencias-datos`. Lo publicado oculta nombres de partes, abogados y representantes
(iniciales), RUT, domicilios, patentes, teléfonos, correos y números de operaciones. Se mantienen
compañías, tribunales y autoridades (ministros, jueces, árbitros, fiscales, secretarios).

## Correr en local

```bash
pip install -r herramientas/sentencias/requirements.txt   # y tesseract-ocr + tesseract-ocr-spa + poppler
python herramientas/sentencias/cmf.py --datos ../sentencias-datos
python herramientas/sentencias/ejecutar.py --datos ../sentencias-datos --salida sentencias/datos
```

Para repetir el OCR de documentos mal leídos: Actions > Sentencias CMF > Run workflow, e indicar
los documentos (por ejemplo `22_3_1 45_3_1`).

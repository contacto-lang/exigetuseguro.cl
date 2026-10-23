"""
Descarga diaria de sentencias de la CMF.

Revisa el listado público de la CMF, descarga solo los documentos nuevos,
extrae su texto (pdfplumber) y, si el PDF es escaneado, aplica OCR con
Tesseract en español. Guarda todo en la carpeta de datos privados:

    <datos>/manifest.csv          metadatos de la CMF, un documento por fila
    <datos>/textos/<id>_<sec>_<doc>.txt   texto original (sin anonimizar)

También actualiza los metadatos de los documentos que ya estaban (por ejemplo,
cuando una sentencia pasa a "Ejecutoriada").

Basado en chequear_nuevas_sentencias.py.

Uso:
    python cmf.py --datos ../../datos-privados
    python cmf.py --datos ../../datos-privados --reocr 22_3_1 45_3_1   (repetir OCR)
"""
import argparse
import csv
import io
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.cmfchile.cl/institucional/inc/sentencias/"
LISTING_URL = BASE_URL + "resultado_sentencias.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; exigetuseguro-jurisprudencia/1.0; +https://www.exigetuseguro.cl/sentencias/)"}
DELAY_SECONDS = 1.0
DOC_LINK_RE = re.compile(r"sen_identificador=(\d+)&sen_secuencia=(\d+)&sen_id_sec_doc=(\d+)")
FIELDS = ["sen_identificador", "sen_secuencia", "sen_id_sec_doc", "compania", "rol_causa", "tipo_tribunal",
          "tribunal", "fecha_notificacion", "resultado", "estado", "tipo_seguro", "materia", "doc_url",
          "archivo_local", "metodo_texto", "fecha_descarga"]


def get(url, timeout=60, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == tries - 1:
                raise
            print(f"  reintento {i + 1} tras error: {e}")
            time.sleep(5 * (i + 1))


def parse_rows(html):
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        raise RuntimeError("No se encontró la tabla. La estructura de la página de la CMF pudo haber cambiado.")
    docs = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 13:
            continue
        t = [c.get_text(strip=True) for c in cells]
        base = dict(compania=t[-12], rol_causa=t[-11], tipo_tribunal=t[-10], tribunal=t[-8], fecha_notificacion=t[-7],
                    resultado=t[-5], estado=t[-4], tipo_seguro=t[-3], materia=t[-2])
        for a in cells[-1].find_all("a", href=True):
            m = DOC_LINK_RE.search(a["href"])
            if not m:
                continue
            sid, seq, doc = m.groups()
            docs.append(dict(base, sen_identificador=sid, sen_secuencia=seq, sen_id_sec_doc=doc,
                             doc_url=urljoin(BASE_URL, a["href"])))
    return docs


def texto_pdf(pdf_bytes):
    import pdfplumber
    partes = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    partes.append(t)
    except Exception as e:
        print(f"  no se pudo leer el PDF: {e}")
    return "\n".join(partes)


def ocr_pdf(pdf_bytes):
    """OCR con Tesseract (español) a 300 dpi."""
    import pytesseract
    from pdf2image import convert_from_bytes
    paginas = convert_from_bytes(pdf_bytes, dpi=300)
    out = []
    for i, img in enumerate(paginas, 1):
        out.append(pytesseract.image_to_string(img, lang="spa", config="--psm 6"))
        print(f"    OCR página {i}/{len(paginas)}")
    return "\n".join(out)


def texto_util(t):
    return len(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{3,}", t or "")) >= 40 and t.count("(cid:") < 20


def leer_manifest(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {(r["sen_identificador"], r["sen_secuencia"], r["sen_id_sec_doc"]): r for r in csv.DictReader(f)}


def guardar_manifest(path, filas):
    orden = sorted(filas.values(), key=lambda r: (int(r["sen_identificador"]), int(r["sen_secuencia"]), int(r["sen_id_sec_doc"])))
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in orden:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    os.replace(tmp, path)


def procesar_doc(doc, carpeta_textos, forzar_ocr=False):
    nombre = f"{doc['sen_identificador']}_{doc['sen_secuencia']}_{doc['sen_id_sec_doc']}"
    r = get(doc["doc_url"])
    contenido = r.content
    if not contenido.startswith(b"%PDF"):
        print(f"  {nombre}: la CMF no devolvió un PDF, se omite por ahora")
        return None, None
    texto, metodo = ("", "") if forzar_ocr else (texto_pdf(contenido), "pdf")
    if not texto_util(texto):
        print(f"  {nombre}: PDF escaneado, aplicando OCR...")
        try:
            texto, metodo = ocr_pdf(contenido), "ocr-tesseract"
        except Exception as e:
            print(f"  {nombre}: OCR falló ({e})")
            texto, metodo = texto or "", "sin-texto"
    with open(os.path.join(carpeta_textos, nombre + ".txt"), "w", encoding="utf-8") as f:
        f.write(texto)
    return nombre + ".pdf", metodo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True, help="carpeta de datos privados")
    ap.add_argument("--reocr", nargs="*", default=[], help="documentos a los que repetir el OCR (id_sec_doc)")
    ap.add_argument("--max", type=int, default=200, help="máximo de documentos nuevos por corrida")
    a = ap.parse_args()

    manifest_path = os.path.join(a.datos, "manifest.csv")
    carpeta_textos = os.path.join(a.datos, "textos")
    os.makedirs(carpeta_textos, exist_ok=True)
    existentes = leer_manifest(manifest_path)

    print("Revisando el listado de la CMF...")
    docs = parse_rows(get(LISTING_URL, timeout=90).text)
    print(f"  {len(docs)} documentos en el listado; {len(existentes)} ya guardados.")
    if len(docs) < 0.8 * len(existentes):
        print("El listado vino mucho más corto que lo guardado; se aborta para no perder datos.")
        sys.exit(1)

    hoy = datetime.now().strftime("%Y-%m-%d")
    nuevos, actualizados = [], 0
    for d in docs:
        k = (d["sen_identificador"], d["sen_secuencia"], d["sen_id_sec_doc"])
        if k in existentes:
            viejo = existentes[k]
            cambios = {c: d[c] for c in ("compania", "rol_causa", "tipo_tribunal", "tribunal", "fecha_notificacion",
                                         "resultado", "estado", "tipo_seguro", "materia") if d[c] and d[c] != viejo.get(c)}
            if cambios:
                viejo.update(cambios); actualizados += 1
        else:
            nuevos.append(d)

    print(f"  {len(nuevos)} nuevos, {actualizados} con metadatos actualizados.")
    for i, d in enumerate(nuevos[:a.max], 1):
        print(f"[{i}/{min(len(nuevos), a.max)}] {d['compania']} | {d['tribunal']} | {d['fecha_notificacion']}")
        try:
            archivo, metodo = procesar_doc(d, carpeta_textos)
        except requests.RequestException as e:
            print(f"  error de descarga: {e}")
            continue
        if not archivo:
            continue
        d.update(archivo_local=archivo, metodo_texto=metodo, fecha_descarga=hoy)
        existentes[(d["sen_identificador"], d["sen_secuencia"], d["sen_id_sec_doc"])] = d
        guardar_manifest(manifest_path, existentes)   # guarda a medida que avanza
        time.sleep(DELAY_SECONDS)

    for nombre in a.reocr:
        sid, seq, doc = nombre.replace(".pdf", "").split("_")
        fila = existentes.get((sid, seq, doc))
        if not fila:
            print(f"{nombre}: no está en el manifest"); continue
        print(f"Repitiendo OCR de {nombre}...")
        _, metodo = procesar_doc(fila, carpeta_textos, forzar_ocr=True)
        fila["metodo_texto"] = metodo

    guardar_manifest(manifest_path, existentes)
    with open(os.path.join(a.datos, "ultima_revision.txt"), "w", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='minutes')} · {len(nuevos)} nuevos · {actualizados} actualizados\n")
    print("Listo.")


if __name__ == "__main__":
    main()

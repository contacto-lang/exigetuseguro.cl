"""
Paso 4: oculta los datos personales y genera los archivos públicos que lee
sentencias/index.html:

    sentencias/datos/indice.js     fichas de todas las sentencias (sin textos)
    sentencias/datos/t/NN.json     textos íntegros anonimizados, en 64 bloques estables

Los bloques se asignan por un hash fijo del ID de la sentencia: una sentencia
nueva solo modifica su bloque, así el historial del repositorio crece poco.

Uso (desde la carpeta de trabajo con sentencias_proc.json):
    python publicar.py --salida ../../sentencias/datos
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anonimizar as A  # noqa: E402

NB = 64
CMF_DOC = "https://www.cmfchile.cl/institucional/inc/sentencias/sentencias_visualiza_doc.php?sen_identificador={}&sen_secuencia={}&sen_id_sec_doc={}"


def bucket(i):
    return int(hashlib.md5(i.encode()).hexdigest(), 16) % NB


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default="sentencias_proc.json")
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    S = json.load(open(a.entrada, encoding="utf-8"))

    # 1) autoridades de toda la colección (se mantienen visibles)
    oficiales = set()
    for s in S:
        oficiales |= A.collect_officials(s["texto"])
        oficiales |= set(re.findall(A.NAME, s["tribunal"] or ""))
    claves = A.official_keys(oficiales)

    # 2) personas detectadas en cualquier sentencia se ocultan en todas
    detect = {s["id"]: A.detectar_personas(s, claves)[0] for s in S}
    globales = set()
    for v in detect.values():
        globales |= {p for p in v if len(A._toks(p)) >= 2}
    por_token = {}
    for p in globales:
        por_token.setdefault(A._toks(p)[-1], []).append(p)
    def extras(s):
        blob = " ".join(x for x in (s["texto"], s["caratula"] or "", s["materia"] or "", s["resolutiva"] or "") if x)
        toks = set(A.deacc(w).lower() for w in re.findall(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+", blob))
        out = []
        for t, ps in por_token.items():
            if t in toks:
                for p in ps:
                    if all(x in toks for x in A._toks(p)) and (p in blob or p.upper() in blob):
                        out.append(p)
        return out
    anon = {s["id"]: A.anonimizar_sentencia(s, (), claves, extras(s)) for s in S}
    n_pers = sum(len(v["_personas"]) for v in anon.values())
    rut_rest = sum(len(re.findall(r"(?<!\d)\d{1,2}\.\d{3}\.\d{3}\s*-\s*[\dkK]\b", v["texto"])) for v in anon.values())
    print(f"Anonimización: {n_pers} menciones de personas ocultas; RUT residuales: {rut_rest}")
    if rut_rest:
        sys.exit("Quedaron RUT sin ocultar; se detiene la publicación.")

    # índice de roles para enlazar jurisprudencia citada
    rolidx = {}
    for s in S:
        for r in (s["rol"], s["rol_informado"]):
            for mm in re.finditer(r"(\d{1,3}(?:\.\d{3})+|\d{1,7})\s*[-–/]\s*(\d{4})", r or ""):
                rolidx.setdefault(f"{int(mm.group(1).replace('.', ''))}-{mm.group(2)}", s["id"])

    idx, textos = [], {k: {} for k in range(NB)}
    for s in sorted(S, key=lambda s: (str(s["expediente"]), s["id"])):
        z = anon[s["id"]]
        k = bucket(s["id"])
        docs = []
        for d in s["docs"]:
            m = re.match(r"(\d+)_(\d+)_(\d+)", d)
            docs.append(CMF_DOC.format(*m.groups()) if m else "")
        idx.append(dict(
            i=s["id"], c=s["causa"], q=s["secuencia"], o=s["org"], tr=s["tribunal"], ci=s["ciudad"] or "", ins=s["instancia"],
            pr=s["procedimiento"], rol=s["rol"] or "", car=z["caratula"] or "", f=s["fecha_sentencia"] or "", fn=s["fecha_notificacion"] or "",
            a=s["anio"] or 0, g=s["grupo"], cia=s["compania"], ts=s["tipo_seguro"], r=s["ramo"], r2=s["ramos_sec"], t=s["temas"],
            m=z["materia"], rc=s["resultado_cmf"], e=s["estado"], d=s["desenlace"], ql=s["calidad_texto"],
            n=sorted(s["normas"], key=lambda q: -s["normas"][q]), res=z["resolutiva"], ch=len(z["texto"]), docs=s["docs"], pdf=docs,
            tri="", x=str(s["expediente"]), re=s["resultado_expediente"], het=s["cmf_heterogeneo"], v=s["vinculos"],
            ni=[{kk: vv for kk, vv in m.items() if kk != "ctx"} for m in s["instancias_no_incluidas"]], al=s["alerta_superior"],
            dup=s["duplicado_de"], cob=s["cobertura"],
            pc=[dict(t=p["tribunal"], r=p["rol"], id=rolidx.get(p["rol"], "")) for p in s["precedentes_citados"]],
            k=k))
        textos[k][s["id"]] = z["texto"]

    os.makedirs(os.path.join(a.salida, "t"), exist_ok=True)
    meta = dict(generado=max((x["fn"] for x in idx), default=""), n=len(idx), nb=NB)
    with open(os.path.join(a.salida, "indice.js"), "w", encoding="utf-8") as f:
        f.write("window.SENT_META=" + json.dumps(meta, ensure_ascii=False) + ";\n")
        f.write("window.SENT_DATA=" + json.dumps(idx, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    for k, d in textos.items():
        with open(os.path.join(a.salida, "t", f"{k:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(dict(sorted(d.items())), f, ensure_ascii=False, separators=(",", ":"))
    print(f"Publicadas {len(idx)} sentencias en {a.salida}")


if __name__ == "__main__":
    main()

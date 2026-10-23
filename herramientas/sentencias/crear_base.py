"""
Arma crudo.db (mismo formato que el sentencias.db original) a partir de la
carpeta de datos privados: manifest.csv + textos/*.txt.

Uso:
    python crear_base.py --datos ../../datos-privados --salida crudo.db
"""
import argparse, csv, os, sqlite3

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    ap.add_argument("--salida", default="crudo.db")
    a = ap.parse_args()
    if os.path.exists(a.salida): os.remove(a.salida)
    con = sqlite3.connect(a.salida)
    con.execute("""CREATE TABLE sentencias (id INTEGER PRIMARY KEY, sen_identificador TEXT, sen_secuencia TEXT, sen_id_sec_doc TEXT,
        compania TEXT, rol_causa TEXT, tribunal TEXT, fecha_notificacion TEXT, resultado TEXT, estado TEXT, tipo_seguro TEXT,
        materia TEXT, archivo_local TEXT, texto TEXT, tipo_tribunal TEXT)""")
    n = 0
    with open(os.path.join(a.datos, "manifest.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nombre = f"{r['sen_identificador']}_{r['sen_secuencia']}_{r['sen_id_sec_doc']}"
            p = os.path.join(a.datos, "textos", nombre + ".txt")
            texto = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
            con.execute("INSERT INTO sentencias (sen_identificador, sen_secuencia, sen_id_sec_doc, compania, rol_causa, tribunal, "
                        "fecha_notificacion, resultado, estado, tipo_seguro, materia, archivo_local, texto, tipo_tribunal) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (r["sen_identificador"], r["sen_secuencia"], r["sen_id_sec_doc"], r["compania"], r["rol_causa"], r["tribunal"],
                         r["fecha_notificacion"], r["resultado"], r["estado"], r["tipo_seguro"], r["materia"],
                         r.get("archivo_local") or nombre + ".pdf", texto, r.get("tipo_tribunal") or None))
            n += 1
    con.commit(); con.close()
    print(f"crudo.db con {n} documentos")

if __name__ == "__main__":
    main()

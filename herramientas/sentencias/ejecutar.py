"""
Corre todo el procesamiento, de los datos privados a los archivos públicos.

    python ejecutar.py --datos ../../datos-privados --salida ../../sentencias/datos

Pasos: crear_base -> proc (clasificación) -> links (vínculos) -> integrate
(expedientes) -> publicar (anonimización y archivos de la página).
La carpeta de trabajo (_trabajo/) contiene textos sin anonimizar: no se sube.
"""
import argparse, os, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))

def run(script, *args, cwd):
    print(f"\n=== {script} ===", flush=True)
    subprocess.run([sys.executable, os.path.join(AQUI, script), *args], cwd=cwd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True)
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    datos, salida = os.path.abspath(a.datos), os.path.abspath(a.salida)
    trabajo = os.path.join(AQUI, "_trabajo"); os.makedirs(trabajo, exist_ok=True)
    run("crear_base.py", "--datos", datos, "--salida", "crudo.db", cwd=trabajo)
    run("proc.py", cwd=trabajo)
    run("links.py", cwd=trabajo)
    run("integrate.py", cwd=trabajo)
    run("publicar.py", "--salida", salida, cwd=trabajo)

if __name__ == "__main__":
    main()

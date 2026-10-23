"""
Oculta datos de personas naturales en las sentencias antes de publicarlas.

Se ocultan: nombres de partes, abogados y representantes (se reemplazan por
iniciales), RUT/RUN, domicilios y direcciones, patentes de vehículos,
teléfonos, correos y números de operaciones bancarias.

Se mantienen: compañías y otras personas jurídicas, tribunales, y los nombres
de jueces, ministros, árbitros, fiscales judiciales, secretarios y actuarios
(actúan como autoridad).

Criterio inspirado en el protocolo de anonimización del Poder Judicial
(Acta 44-2022), que oculta a las personas cuyos datos de salud aparecen en el fallo.
"""
import re
import unicodedata

def deacc(x):
    return ''.join(c for c in unicodedata.normalize('NFD', x) if unicodedata.category(c) != 'Mn')

UP = "A-ZÁÉÍÓÚÑÜ"
LO = "a-záéíóúñü"
WORD = rf"(?:[{UP}][{LO}]+(?:-[{UP}][{LO}]+)?|[{UP}]{{2,}}(?:-[{UP}]{{2,}})?)"
PART = r"(?:de\s+la|de\s+los|de\s+las|del|de|y|van|von|da|dos|mc)"
NAME = rf"{WORD}(?:\s+(?:{PART}\s+)?(?:{WORD}|[{UP}]\.)){{1,5}}"

PREFIX = (r"(?i:\bdon|\bdoña|\bdona|\bdoñ a|\bseñora?|\bsrta?\.?|\bsra\.?|\bsr\.|\bcomparecen?|\bcomparecieron|"
          r"en\s+representaci[oó]n\s+(?:convencional\s+|legal\s+|judicial\s+)?de|"
          r"en\s+favor\s+de|a\s+favor\s+de|"
          r"\b(?:el|la|los|las)\s+(?:asegurad[oa]s?|causante|fallecid[oa]|c[oó]nyuge|hij[oa]s?|"
          r"querellantes?|demandantes?|recurrentes?|actor(?:a|es)?|denunciantes?|beneficiari[oa]s?|"
          r"deudor(?:a)?|tomador(?:a)?|contratante|conductor(?:a)?|propietari[oa]|viuda|viudo|madre|padre))")
QUALIF = (r"(?:abogad[oa]s?|chilen[oa]s?|casad[oa]|solter[oa]|viud[oa]|divorciad[oa]|emplead[oa]|estudiante|"
          r"ingenier[oa]|m[eé]dic[oa]|profesor(?:a)?|comerciante|empresari[oa]|jubilad[oa]|pensionad[oa]|"
          r"due[ñn]a\s+de\s+casa|t[eé]cnic[oa]|contador(?:a)?|transportista|agricultor(?:a)?|"
          r"c[eé]dula|C\.?\s?I\.?|R\.?U\.?[TN]\.?|run|rut|domiciliad[oa]s?|mayor\s+de\s+edad|ya\s+individualizad[oa])")
OFFICIAL = (r"(ministr[oa]s?(?:\s+(?:suplente|presidente|presidenta|interin[oa]|titular))?|ministro\s*\(s\)|"
            r"jue(?:z|za|ces)(?:\s+(?:titular|suplente|subrogante|interin[oa]|[aá]rbitro|partidor|de\s+letras))?|"
            r"[aá]rbitro(?:\s+(?:arbitrador|mixto|de\s+derecho))?|fiscal(?:es)?\s+judicial(?:es)?|"
            r"abogad[oa]s?\s+integrantes?|secretari[oa](?:\s+(?:titular|subrogante|abogad[oa]))?|actuari[oa]|"
            r"relator(?:a)?|ministro\s+de\s+fe|redacci[oó]n\s+(?:del|de\s+la)\s+(?:ministr[oa]|abogad[oa]\s+integrante)|"
            r"pronunciad[oa]\s+por|integrada\s+por|presidida\s+por|resolvi[oó]|provey[oó]|autoriza|dict[oó])")
ORG_MARK = re.compile(r"\b(S\.?\s?A\.?|SpA|S\.?p\.?A|Ltda|Limitada|E\.?I\.?R\.?L|Seguros?|Compa[ñn][ií]a|C[ií]a\.?|Banco|Sociedad|"
                      r"Inversiones|Corredor(?:es|a)|Comercial|Transportes?|Constructora|Inmobiliaria|Agr[ií]cola|"
                      r"Servicios?|Empresas?|Corporaci[oó]n|Fundaci[oó]n|Universidad|Municipalidad|Cl[ií]nica|Hospital|"
                      r"Instituto|Club|Asociaci[oó]n|Cooperativa|Holding|Group|Grupo|Chile|Generales|Vida|Exportadora|"
                      r"Industrial|Ingenier[ií]a|Comunidad|Condominio|Junta|Iglesia|Colegio|Liceo|Escuela|Ilustre|"
                      r"Juzgado|Corte|Tribunal|C[oó]digo|Ley|Rep[uú]blica|Servicio|Superintendencia|Comisi[oó]n|Fisco|"
                      r"Estado|Consejo|Ministerio|Carabineros|Polic[ií]a|Tesorer[ií]a|Registro|Notar[ií]a|Conservador|"
                      r"Consolidada|Chilena|Santander|Consorcio|Mapfre|Zurich|Liberty|Reale|Cardif|Metlife|Bice|Chubb|Hdi|Orion|Sura|Penta|"
                      r"Euroamerica|Confuturo|Bci|Renta|Nacional|Continental|Solunion|Coface|Magallanes|Zenit|Help|Colmena)\b", re.I)
STOPTOK = set(deacc(w).lower() for w in """
santiago concepcion valparaiso temuco valdivia osorno chillan talca rancagua antofagasta iquique arica serena
copiapo calama coquimbo vina mar puerto montt punta arenas coyhaique talcahuano providencia condes vitacura
maipu nunoa florida independencia chile chilena region metropolitana comuna ciudad avenida calle pasaje
primero segundo tercero cuarto quinto sexto septimo octavo noveno decimo vistos considerando resuelve
corte suprema apelaciones juzgado civil policia local tribunal arbitral sala ministro juez fiscal secretario
codigo ley articulo seguros compania banco poliza santander consorcio zurich mapfre liberty reale cardif
metlife bice chubb consolidada chilena generales vida nacional estado fisco republica don dona senor senora
enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre lunes martes
miercoles jueves viernes sabado domingo uf utm ipc rol causa fojas folio
""".split())

RE_PREFIX_NAME = re.compile(rf"({PREFIX})\s*[:,]?\s*({NAME})")
RE_NAME_QUALIF = re.compile(rf"(?<![{LO}])({NAME})\s*,\s*(?i:{QUALIF})")
RE_NAME_QUALIF_CAPS = re.compile(rf"\b([{UP}]{{2,}}(?:\s+[{UP}]{{2,}}){{1,5}})\b\s*,?\s*(?i:{QUALIF})")
RE_OFFICIAL_BEFORE = re.compile(OFFICIAL + r"[\s:,]*(?:(?:se[ñn]or(?:a)?|sr\.?|sra\.?|don|do[ñn]a)\s+)?$", re.I)
RE_CARAT_PARTS = re.compile(r"\s+con\s+|/|\s+c/\s+|\s+contra\s+|\s+y\s+otros?", re.I)

RUT = re.compile(r"(?:(?<!\d)\d{1,2}\.\d{3}\.\d{3}\s*-\s*[\dkK]\b)|(?:(?:R\.?U\.?[TN]\.?|C\.?\s?I\.?|c[eé]dula(?:\s+(?:nacional\s+)?de\s+identidad)?|identidad)\s*(?:N[°º.']*|n[uú]mero)?\s*:?\s*)(\d{7,8}\s*-\s*[\dkK])\b", re.I)
DOMIC = re.compile(r"((?:domiciliad[oa]s?|con\s+domicilio|domicilio)\s+(?:para\s+(?:estos|todos\s+los)\s+efectos\s+)?(?:legal\s+)?(?:en\s+)?)"
                   r"([^;\n]{4,160}?)(?=,\s*(?:comuna|ciudad|regi[oó]n|quien|quienes|en\s+representaci|ambos|y\s+en\s+contra|que\s)|;|\.\s|\n|,\s*(?:deduce|interpone|viene)|$)", re.I)
DIREC = re.compile(r"\b((?:calle|avenida|avda\.|av\.|pasaje|psje\.|camino|parcela|villa|poblaci[oó]n|block|depto\.?|departamento)\s+)"
                   r"([^,;\n]{2,60}?\s*(?:N[°º'?o]?\.?\s*|n[uú]mero\s+|#\s*)?\d{1,5}[A-Za-z]?)", re.I)
PATENTE = re.compile(r"((?:placa\s+patente(?:\s+[uú]nica)?|patente(?:\s+[uú]nica)?|P\.?P\.?U\.?)\s*(?:N[°º.]*\s*)?[:\-]?\s*)"
                     r"([A-Z]{2,4}[\s.\-·]*\d{2,4}(?:[\s.\-]*[\dkK])?)", re.I)
FONO = re.compile(r"(?i:(?:tel[eé]fonos?|fono|celular|cel\.|tel\.|m[oó]vil|whatsapp)\s*(?:N[°º.]*\s*)?:?\s*)(\+?\(?\d[\d\s().-]{6,16}\d)|\+56[\s.-]?\d[\d\s.-]{7,11}\d")
MAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
CUENTA = re.compile(r"((?:operaci[oó]n|cr[eé]dito(?:\s+de\s+consumo|\s+hipotecario)?|cuenta(?:\s+corriente|\s+vista)?|tarjeta(?:\s+de\s+cr[eé]dito)?)\s*(?:N[°º.]*|n[uú]mero|nro\.?)\s*:?\s*)(\d[\d.\-]{6,})", re.I)

STOPLEGAL = set(deacc(w).lower() for w in """juez jueza arbitro arbitral accion demanda demandada demandante tribunal sentencia causa recurso
autos fojas folio considerando vistos resuelve resolucion corte suprema sala ministro ministra secretario secretaria
actuario fiscal abogado abogada integrante relator notifico certifico lo la el los las en de del que por para con
parte partes primera segunda tercera cuarta quinta sexta septima octava novena decima instancia juicio ordinario
sumario policia local civil letras garantia juzgado protecion proteccion apelacion casacion queja forma fondo""".split())

SIG_SEG = re.compile(r"(?i:integrad[oa]\s+por|provei?d[oa]\s+por|provey[oó]|ministros?\s+en\s+propiedad|ministros?\s*:|pronunciad[oa]\s+por|presidid[oa]\s+por|firmad[oa]\s+por|"
                     r"acordad[oa]\s+(?:con|por)|redacci[oó]n\s+(?:del|de\s+la)|ministros?\s*\(as\)|ministros?\s+se[ñn]ores?|sres\.)"
                     r"([^\n]{0,400}?)(?=Santiago,|[A-ZÁÉÍÓÚ][a-záéíóú]+,\s+(?:a\s+)?[a-z]+\s+de\s+[a-z]+\s+de|\n\n|$)")
ROLE_AFTER = re.compile(rf"({NAME})\s*\n?\s*(?:MINISTR[OA]|Ministr[oa]|JUEZ|Juez|ABOGAD[OA]\s+INTEGRANTE|Abogad[oa]\s+Integrante|"
                        r"SECRETARI[OA]|Secretari[oa]|FISCAL\s+JUDICIAL|Fiscal\s+Judicial|ACTUARI[OA]|Actuari[oa]|"
                        r"Juez\s+[AÁ]rbitro|JUEZ\s+[AÁ]RBITRO|Ministro\(I\)|MINISTRO\(S\))")

DOCTRINA = re.compile(r"(?i:profesor(?:a)?|autor(?:a|es)?|tratadista|doctrina|jurista|obra|seg[uú]n|cita(?:do|da)?\s+por|"
                      r"ense[ñn]a|sostiene|explica|comenta|siguiendo\s+a|como\s+lo\s+(?:se[ñn]ala|indica))[^.;]{0,40}$")
AUTORES = [deacc(a).lower() for a in """alessandri|somarriva|vodanovic|abeliuk|claro solar|meza barros|ramos pazos|barros bourie|corral talciani|
pe[ñn]ailillo|baeza pinto|sandoval lopez|contreras strauch|rios ossa|achurra|halperin|garrigues|vivante|stiglitz|ossa gomez|
dominguez aguila|pizarro wilson|vidal olivares|tapia rodriguez|puga vial|lopez santa maria|fueyo|ducci|rioseco|tomasello|
diez schwerter|figueroa yanez|orrego acu|bahamondez|gonzalez von marees|ruiz tagle|espinoza fuentes|palma rodriguez""".replace('\n','').split('|')]
AUTORES = [a.replace('[ñn]', 'n') for a in AUTORES]

def collect_officials(text):
    of = set()
    for m in SIG_SEG.finditer(text):
        for n in re.findall(NAME, m.group(1)):
            of.add(re.sub(r"\s+", " ", n).strip(" ,."))
    for m in ROLE_AFTER.finditer(text):
        of.add(re.sub(r"\s+", " ", m.group(1)).strip(" ,."))
    for m in re.finditer(rf"(?i:{OFFICIAL})[\s:,]*(?i:(?:se[ñn]or(?:a)?|sr\.?|sra\.?|sres\.?|don|do[ñn]a)\s+)?({NAME})", text):
        of.add(re.sub(r"\s+", " ", m.group(m.lastindex)).strip(" ,."))
    # quitar falsos oficiales evidentes (organizaciones)
    return {o for o in of if not ORG_MARK.search(o) and len(o.split()) >= 2}

GIVEN = set(deacc(w) for w in """maria jose juan luis carlos jorge pedro pablo francisco javier manuel antonio miguel andres
alejandro eduardo fernando ricardo rodrigo sergio patricio cristian christian claudio gonzalo felipe diego daniel raul
hernan mario oscar victor hugo alberto enrique ignacio tomas sebastian matias nicolas gabriel rafael roberto arturo
ana elena isabel carmen teresa cecilia patricia claudia carolina andrea paula daniela francisca javiera camila valentina
gloria rosa veronica jacqueline marcela alejandra soledad angelica eugenia luisa ines pilar beatriz victoria adriana
susana monica silvia lorena paola karina macarena constanza fernanda catalina antonia josefa ximena""".split())

def _toks(n):
    t = [deacc(x).lower().strip('.') for x in n.split() if not re.fullmatch(PART, x, re.I)]
    return [x for x in t if x]

def official_keys(names):
    """Claves (nombre, primer apellido) para reconocer a una autoridad aunque aparezca abreviada."""
    keys = set()
    for n in names:
        t = _toks(n)
        if len(t) < 2: continue
        cands = [x for x in t[1:] if len(x) > 1 and x not in GIVEN]
        if len(t) >= 4: cands = [t[-2]]
        for sur in cands[:2]: keys.add((t[0], sur))
    return keys

def initials(name):
    toks = [t for t in re.split(r"\s+", name) if t and not re.fullmatch(PART, t, re.I)]
    return '.'.join(t[0].upper() for t in toks) + '.'

def is_org(span, after=''):
    return bool(ORG_MARK.search(span) or ORG_MARK.match(after.strip()[:25] or 'x' if False else ''))

def collect_names(text, extra_officials=()):
    """Devuelve (personas, oficiales) encontradas en el texto."""
    personas, oficiales = set(), set(x for x in extra_officials if x)
    def consider(name, start):
        name = re.sub(r"\s+", " ", name).strip(" ,.")
        if len(name) < 5 or len(name.split()) < 2: return
        if ORG_MARK.search(name): return
        after = text[start + len(name): start + len(name) + 30]
        if re.match(r"\s*(S\.?\s?A\b|SpA|Ltda|Limitada|y\s+C[ií]a)", after, re.I): return
        before = text[max(0, start - 70): start]
        if DOCTRINA.search(before[-60:]) or any(a in deacc(name).lower() for a in AUTORES):
            return
        if RE_OFFICIAL_BEFORE.search(before):
            oficiales.add(name); return
        toks = [deacc(t).lower() for t in name.split() if not re.fullmatch(PART, t, re.I)]
        if all(t in STOPTOK for t in toks): return
        if any(t in STOPLEGAL for t in toks): return
        personas.add(name)
    for m in RE_PREFIX_NAME.finditer(text): consider(m.group(2), m.start(2))
    for m in RE_NAME_QUALIF.finditer(text): consider(m.group(1), m.start(1))
    for m in RE_NAME_QUALIF_CAPS.finditer(text): consider(m.group(1), m.start(1))
    # quienes aparecen como oficiales en las firmas no se ocultan
    for m in re.finditer(rf"(?i:{OFFICIAL})[\s:,]*(?i:(?:se[ñn]or(?:a)?|sr\.?|sra\.?|don|do[ñn]a)\s+)?({NAME})", text):
        oficiales.add(re.sub(r"\s+", " ", m.group(m.lastindex)).strip(" ,."))
    return personas, oficiales

def caratula_persons(car):
    if not car: return []
    out = []
    for part in RE_CARAT_PARTS.split(car):
        part = part.strip(" .,“”\"")
        if not part or ORG_MARK.search(part) or re.search(r"\d", part): continue
        if len(part) >= 3: out.append(part)
    return out

def build_replacer(personas, oficiales):
    of_toks = set()
    for o in oficiales:
        for t in o.split(): of_toks.add(deacc(t).lower())
    full = sorted(personas, key=len, reverse=True)
    surn = set()
    for p in personas:
        toks = [t for t in p.split() if not re.fullmatch(PART, t, re.I)]
        for t in toks[1:] if len(toks) > 2 else toks[-1:]:
            d = deacc(t).lower()
            if len(d) >= 4 and d not in STOPTOK and d not in of_toks: surn.add(t)
    pats = []
    for p in full:
        if p in oficiales: continue
        rx = r"\s+".join(re.escape(t) for t in p.split())
        rxu = r"\s+".join(re.escape(t.upper()) for t in p.split())
        pats.append((re.compile(rf"(?<![\w])(?:{rx}|{rxu})(?![\w])"), initials(p)))
    for t in sorted(surn, key=len, reverse=True):
        alts = {t, t[:1].upper() + t[1:].lower(), t.upper()}
        pats.append((re.compile(r"(?<![\w.])(?:" + "|".join(re.escape(a) for a in alts) + r")(?![\w])"), t[0].upper() + '.'))
    return pats

def apply(text, pats):
    if not text: return text
    for rx, rep in pats:
        text = rx.sub(rep, text)
    text = RUT.sub(lambda m: (m.group(0)[:m.start(1) - m.start(0)] + '[RUT]') if m.group(1) else '[RUT]', text)
    text = DOMIC.sub(lambda m: m.group(1) + '[domicilio]', text)
    text = re.sub(r"\[domicilio\]\.\s*\d+[A-Za-z]?\b", "[domicilio]", text)
    text = re.sub(r"\[domicilio\](?:[.,]?\s*(?:dpto|depto|departamento|oficina|of|piso|casa|block|torre|local|parcela|sitio)\.?\s*(?:N[°º]\s*)?[\dA-Z][\w-]*)+", "[domicilio]", text, flags=re.I)
    text = DIREC.sub(lambda m: m.group(1).split()[0] + ' [dirección]', text)
    text = PATENTE.sub(lambda m: m.group(1) + '[patente]', text)
    text = CUENTA.sub(lambda m: m.group(1) + '[número]', text)
    text = MAIL.sub('[correo]', text)
    text = FONO.sub(lambda m: (m.group(0)[:m.start(1) - m.start(0)] + '[teléfono]') if m.group(1) else '[teléfono]', text)
    return text

def detectar_personas(s, claves_oficiales=frozenset()):
    """Personas naturales detectadas en una sentencia (sin autoridades)."""
    texto = s.get('texto') or ''
    personas, oficiales = collect_names(texto)
    for p in caratula_persons(s.get('caratula') or ''):
        if p not in oficiales: personas.add(p)
    for o in re.findall(NAME, s.get('tribunal') or ''): oficiales.add(o)
    oficiales |= collect_officials(texto)
    ok = official_keys(oficiales) | set(claves_oficiales)
    def es_oficial(p):
        if p in oficiales or any(p.lower() in o.lower() for o in oficiales): return True
        t = _toks(p)
        return any((t[0], x) in ok for x in t[1:] if len(x) > 1)
    return {p for p in personas if not es_oficial(p)}, oficiales


def anonimizar_sentencia(s, oficiales_globales=(), claves_oficiales=frozenset(), extra_personas=()):
    """s: dict con texto, caratula, materia, resolutiva, tribunal. Devuelve dict con campos anonimizados.
    extra_personas: nombres detectados en otras sentencias que también deben ocultarse aquí."""
    personas, oficiales = detectar_personas(s, claves_oficiales)
    personas |= set(extra_personas)
    pats = build_replacer(personas, oficiales)
    out = {k: apply(s.get(k) or '', pats) for k in ('texto', 'caratula', 'materia', 'resolutiva')}
    out['_personas'] = sorted(personas)
    return out

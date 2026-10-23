"""Paso 1: normaliza metadatos, detecta tribunal e instancia, clasifica ramo, temas, normas y lo resuelto, y limpia el texto."""
import sqlite3, re, json, collections, unicodedata, statistics, os

SRC = os.environ.get('SENT_CRUDO', 'crudo.db')
con = sqlite3.connect(SRC)
con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute('select * from sentencias order by cast(sen_identificador as int), cast(sen_secuencia as int), cast(sen_id_sec_doc as int)')]

def deacc(s):
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')

# ---------------------------------------------------------------- fechas en palabras
UNI = {'un':1,'uno':1,'una':1,'primero':1,'dos':2,'tres':3,'cuatro':4,'cinco':5,'seis':6,'siete':7,'ocho':8,'nueve':9,'diez':10,
 'once':11,'doce':12,'trece':13,'catorce':14,'quince':15,'dieciseis':16,'diecisiete':17,'dieciocho':18,'diecinueve':19,'veinte':20,
 'veintiuno':21,'veintiun':21,'veintidos':22,'veintitres':23,'veinticuatro':24,'veinticinco':25,'veintiseis':26,'veintisiete':27,
 'veintiocho':28,'veintinueve':29,'treinta':30}
MES = {m:i+1 for i,m in enumerate(['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'])}
MES['setiembre'] = 9
def words2num(s):
    s = deacc(s.lower()).replace('-', ' ')
    toks = [t for t in re.split(r'\s+', s) if t and t != 'y']
    total = 0
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == 'mil': total = (total or 1) * 1000
        elif t == 'treinta': total += 30
        elif t in UNI: total += UNI[t]
        else: return None
        i += 1
    return total
DATE_RE = re.compile(r'(?:a\s+)?([a-záéíóú]+(?:\s+y\s+[a-záéíóú]+)?|\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(dos\s+mil(?:\s+[a-záéíóú]+){0,2}|\d{4})', re.I)
CITYDATE_RE = re.compile(r'([A-ZÁÉÍÓÚ][a-záéíóúñ]+(?:\s+(?:del?\s+)?[A-ZÁÉÍÓÚ][a-záéíóúñ]+){0,3})\s*,\s*(?:a\s+)?(?:\d{1,2}|[a-záéíóú]+(?:\s+y\s+[a-záéíóú]+)?)\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)', re.I)
def best_date(text, notif):
    cands = []
    for zone in (text[:3500], text[-4000:]):
        for m in CITYDATE_RE.finditer(zone):
            d = find_date(zone[m.start():m.start()+160], 160)
            if d: cands.append(d)
    any_d = find_date(text, 2500)
    if any_d: cands.append(any_d)
    for d in cands:
        if not notif: return d
        if int(d[:4]) >= int(notif[:4]) - 8 and int(d[:4]) <= int(notif[:4]) + 1: return d
    return None
def find_date(text, limit=2500):
    for m in DATE_RE.finditer(text[:limit]):
        d = m.group(1); y = m.group(3)
        d = int(d) if d.isdigit() else words2num(d)
        if y.isdigit(): y = int(y)
        else:
            toks = y.split(); y = None
            while toks and y is None:
                y = words2num(' '.join(toks)); toks = toks[:-1]
        mo = MES[deacc(m.group(2).lower())]
        if d and y and 1 <= d <= 31 and 1990 <= y <= 2027:
            return f'{y:04d}-{mo:02d}-{d:02d}'
    return None

# ---------------------------------------------------------------- tribunal
CIUDADES = ['Santiago','San Miguel','Concepción','Valparaíso','Valdivia','Temuco','Puerto Montt','La Serena','Antofagasta','Rancagua',
 'Talca','Chillán','Arica','Iquique','Copiapó','Punta Arenas','Coyhaique','Viña del Mar','Osorno','Los Ángeles','Coquimbo','Calama',
 'Talcahuano','Quilpué','Villa Alemana','San Antonio','San Fernando','Curicó','Los Andes','Parral','Mariquina','Traiguén','Bulnes',
 'Constitución','Coronel','Curanilahue','Carahue','Puente Alto','Vallenar','Huasco','Lautaro','Algarrobo','Chimbarongo','Buin',
 'Las Condes','Vitacura','Providencia','Lo Barnechea','Huechuraba','Maipú','La Florida','Quilicura','Recoleta','Cerrillos',
 'La Cisterna','El Bosque','Lo Espejo','Peñalolén','Colina','San Bernardo','Talagante']
CIU_N = {deacc(c.lower()): c for c in CIUDADES}
CIU_N['stgo'] = 'Santiago'; CIU_N['santaigo'] = 'Santiago'; CIU_N['concepcon'] = 'Concepción'; CIU_N['conpcepcion'] = 'Concepción'
CIU_N['santiaog'] = 'Santiago'
def city_in(s):
    sd = re.sub(r'constitucion\s+politica', ' ', deacc(s.lower()))
    best = None
    for k, v in sorted(CIU_N.items(), key=lambda kv: -len(kv[0])):
        if re.search(r'\b' + re.escape(k) + r'\b', sd):
            pos = re.search(r'\b' + re.escape(k) + r'\b', sd).start()
            if best is None or pos < best[0]: best = (pos, v)
    return best[1] if best else None

def norm_meta_tribunal(t, tipo):
    """Normaliza el campo tribunal informado."""
    s = deacc((t or '').lower())
    if re.search(r'suprema', s): return 'CS', None
    if re.search(r'corte|\bica\b|^ca$|c\.a|apelaci', s): return 'CA', city_in(t or '')
    if re.search(r'policia|polica|\bjpl\b|\bjlp\b|jp local|policiia', s): return 'JPL', city_in(t or '')
    if re.search(r'juzgado|juzado|civil|letras|\bjc\b|\bjl\b|sjl|jdo', s): return 'JC', city_in(t or '')
    if tipo == 'Arbitral' or (re.match(r"^[a-záéíóúñ'\\. ]+$", s) and len(s.split()) >= 2 and not city_in(t or '')): return 'ARB', None
    return None, city_in(t or '')

def detect_court(text, meta_t, tipo):
    head = text[:1800]; tail = text[-3500:]
    hd = deacc(head.lower()); tl = deacc(tail.lower())
    last = tl[-700:]
    if re.search(r'juez(a)? [aá]rbitro|[aá]rbitro (arbitrador|mixto|de derecho)|actuario', last) and not re.search(r'\bministr[oa]s?\b(?!\s+de\s+fe)|pronunciad[oa] por', last):
        return 'ARB', None
    # Firma electrónica PJUD: lo más confiable
    m = re.search(r'pronunciad[oa] por (?:la |el )?(.{0,120})', tl.replace('\n', ' '))
    if m:
        seg = m.group(1)
        if 'suprema' in seg: return 'CS', None
        if re.search(r'c\.\s?a\.|corte de apelaciones|iltma', seg):
            ci = city_in(seg) or city_in(tail[tail.lower().find('pronunciad'):][:200])
            return 'CA', ci
    CS_SIG = r'(sala de (la|esta) (excma\.? )?corte suprema|corte suprema integrada|esta corte suprema|tercera sala de la corte suprema|primera sala de la corte suprema|segunda sala de la corte suprema|cuarta sala de la corte suprema)'
    if re.search(r'\bministr[oa]s?\b(?!\s+de\s+fe)|abogad[oa]s? integrante|fiscal judicial', tl):
        if re.search(CS_SIG, tl) or (re.search(CS_SIG, hd) and not re.search(r'corte de apelaciones|c\.a\.', tl)):
            return 'CS', None
        if re.search(r'corte de apelaciones|c\.\s?a\.|iltma|ilustr[ií]sima|esta corte', tl) or True:
            seg = tail[max(0, tl.find('apelaciones') - 30):][:200] if 'apelaciones' in tl else tail
            return 'CA', city_in(head[:160]) or city_in(seg) or city_in(head[:400])
    if re.search(r'corte suprema', tl) and re.search(r'(sala|ministros?)', tl) and not re.search(r'corte de apelaciones|c\.a\. de', tl[-1500:]):
        if re.search(r'casaci[oó]n|recurso de queja|apelaci[oó]n|protecci[oó]n|unificaci', deacc(text.lower())):
            return 'CS', None
    if re.search(r'c\.\s?a\.\s+de\s+\w+|corte de apelaciones', hd[:200]) or re.search(r'pronunciad[oa] por la .{0,40}(c\.a\.|corte de apelaciones)', tl):
        return 'CA', city_in(head[:300]) or city_in(tail)
    # primera instancia
    if re.search(r'juzgado\s*:?\s*.{0,40}polic[ií]a local|juzgado de polic[ií]a local|polic[ií]a local', hd):
        return 'JPL', city_in(re.search(r'polic[ií]a local.{0,60}', hd).group(0)) or city_in(head)
    if re.search(r'juez(a)? [aá]rbitro|[aá]rbitro (arbitrador|mixto|de derecho)|sentencia arbitral|juicio arbitral|tribunal arbitral|arbitraje', hd):
        return 'ARB', None
    if re.search(r'juzgado (civil|de letras)|\d+\s*[°º]?\s*juzgado|juzgado\s*:', hd):
        mm = re.search(r'juzgado.{0,60}', head, re.I)
        return 'JC', city_in(mm.group(0)) if mm else city_in(head)
    # señales en el cuerpo
    full = deacc(text.lower())
    if 'policia local' in tl: return 'JPL', city_in(tail)
    if re.search(r'excma\. corte suprema|esta corte suprema', full): return 'CS', None
    mt, ci = norm_meta_tribunal(meta_t, tipo)
    if mt: return mt, ci
    if re.search(r'[aá]rbitro', full[:5000]): return 'ARB', None
    if re.search(r'esta corte|ilustr[ií]sima corte|iltma', full): return 'CA', city_in(head)
    return 'ND', ci

ORG_LABEL = {'CS': 'Corte Suprema', 'CA': 'Corte de Apelaciones', 'JC': 'Juzgado Civil / de Letras', 'JPL': 'Juzgado de Policía Local', 'ARB': 'Tribunal arbitral', 'ND': 'No determinado'}

# ---------------------------------------------------------------- compañías
def grupo_cia(c):
    s = deacc((c or '').upper())
    pairs = [('ZURICH', 'Zurich'), ('BCI', 'BCI'), ('REALE', 'Reale'), ('CHILENA CONSOLIDADA', 'Chilena Consolidada'), ('LIBERTY', 'Liberty'),
      ('CARDIF', 'BNP Paribas Cardif'), ('METLIFE', 'MetLife'), ('BICE', 'BICE Vida'), ('CLC', 'Seguros CLC'), ('HDI', 'HDI'),
      ('CONSORCIO', 'Consorcio'), ('MAPFRE', 'Mapfre'), ('EUROAMERICA', 'EuroAmerica'), ('RENTA NACIONAL', 'Renta Nacional'),
      ('ZENIT', 'Zenit'), ('HELP', 'Help'), ('CONTINENTAL', 'Continental'), ('SAVE', 'Save'), ('SURA', 'Sura'), ('CONFUTURO', 'Confuturo'),
      ('PENTA', 'Penta Vida'), ('CHUBB', 'Chubb'), ('ACE ', 'Chubb'), ('SOLUNION', 'Solunion'), ('CN LIFE', 'CN Life'), ('BANCHILE', 'Banchile'),
      ('RSA', 'RSA'), ('COLMENA', 'Colmena'), ('SCOTIA', 'Scotia'), ('ORION', 'Orión'), ('OHIO', 'Ohio National'), ('COFACE', 'Coface'),
      ('ITAU', 'Itaú'), ('CORPVIDA', 'Corpvida'), ('PORVENIR', 'Porvenir'), ('4 LIFE', '4 Life'), ('ORSAN', 'Orsan'), ('MUTUAL', 'Mutual de Seguros'),
      ('FID', 'FID'), ('CONTEMPORA', 'Contempora')]
    for k, v in pairs:
        if k in s: return v
    return (c or '').title()

# ---------------------------------------------------------------- ramos
RAMOS = [
 ('Vehículos motorizados', [r'veh[ií]culo', r'autom[oó]vil', r'camioneta', r'placa patente', r'patente [úu]nica', r'colisi[oó]n', r'volcamiento', r'choque', r'seguro automotriz', r'motocicleta', r'cami[oó]n\b']),
 ('Desgravamen', [r'desgravamen']),
 ('Salud / gastos médicos', [r'gastos m[eé]dicos', r'seguro de salud', r'complementario de salud', r'catastr[oó]fico', r'oncol[oó]gico', r'hospitalizaci[oó]n', r'reembolso de gastos', r'cl[ií]nica las condes']),
 ('Vida', [r'seguro de vida', r'fallecimiento', r'beneficiari[oa]s?', r'capital asegurado por muerte']),
 ('Invalidez / accidentes personales', [r'invalidez', r'accidentes personales', r'incapacidad total', r'desmembramiento', r'muerte accidental']),
 ('Incendio, sismo y hogar', [r'incendio', r'sismo', r'terremoto', r'seguro de hogar', r'hogar', r'inmueble asegurado', r'vivienda', r'da[ñn]os? por agua', r'filtraci[oó]n', r'inundaci[oó]n', r'estallido social', r'riesgos? de la naturaleza']),
 ('Robo (no vehicular)', [r'robo con fuerza', r'robo en (el )?(domicilio|local|bodega)', r'p[oó]liza de robo', r'seguro de robo', r'hurto']),
 ('Perjuicio por paralización', [r'perjuicio por paralizaci[oó]n', r'paralizaci[oó]n', r'lucro cesante.{0,30}p[oó]liza']),
 ('Garantía, crédito y caución', [r'seguro de cr[eé]dito', r'p[oó]liza de garant[ií]a', r'seguro de garant[ií]a', r'venta en verde', r'cauci[oó]n', r'afianzad', r'garant[ií]a de (fiel|correcta)', r'insolvencia del deudor']),
 ('Responsabilidad civil', [r'responsabilidad civil']),
 ('Transporte y carga', [r'transporte', r'mercader[ií]as?', r'carga', r'mar[ií]timo', r'contenedor']),
 ('Ingeniería y construcción', [r'todo riesgo construcci[oó]n', r'montaje', r'equipo m[oó]vil', r'maquinaria', r'avería de maquinaria', r'\bTRC\b']),
 ('Agrícola', [r'agr[ií]cola', r'cosecha', r'helada', r'cultivo', r'granizo', r'plantaci[oó]n']),
 ('Cesantía / desempleo', [r'cesant[ií]a', r'desempleo', r'p[eé]rdida (involuntaria )?(del|de) empleo']),
 ('Fraude / tarjetas', [r'uso fraudulento', r'fraude (con|en) tarjeta', r'tarjetas? de cr[eé]dito', r'clonaci[oó]n', r'transferencias? no autorizad']),
 ('Rentas vitalicias / ahorro', [r'renta vitalicia', r'ahorro previsional', r'\bAPV\b', r'cuenta [úu]nica de inversi[oó]n', r'seguro con ahorro']),
 ('SOAP (accidentes de tránsito)', [r'\bSOAP\b', r'seguro obligatorio de accidentes personales', r'ley 18\.?490']),
 ('Fidelidad funcionaria', [r'fidelidad funcionaria', r'infidelidad']),
 ('Asistencia en viaje', [r'asistencia en viaje', r'seguro de viaje']),
]
RAMO_RES = [(n, [re.compile(p, re.I) for p in pats]) for n, pats in RAMOS]

def clasif_ramo(materia, text, tipo_seguro):
    head = (materia or '') + '\n' + text[:12000]
    sc = {}
    for n, pats in RAMO_RES:
        s = 0
        for p in pats:
            s += 4 * len(p.findall(materia or '')) + 1.5 * len(p.findall(text[:12000])) + 0.2 * len(p.findall(text))
        if s: sc[n] = s
    # coherencia con tipo de seguro de la CMF
    personas = {'SOAP (accidentes de tránsito)', 'Desgravamen', 'Salud / gastos médicos', 'Vida', 'Invalidez / accidentes personales', 'Cesantía / desempleo', 'Rentas vitalicias / ahorro', 'Asistencia en viaje'}
    for n in list(sc):
        if tipo_seguro == 'Personas' and n not in personas and n != 'Fraude / tarjetas': sc[n] *= 0.35
        if tipo_seguro and tipo_seguro.startswith('Daños') and n in personas and n not in ('Cesantía / desempleo',): sc[n] *= 0.35
    # señales débiles que inflan
    if 'Vida' in sc and 'Desgravamen' in sc and sc['Desgravamen'] >= 3: sc['Vida'] *= 0.4
    if 'Transporte y carga' in sc and 'Vehículos motorizados' in sc: sc['Transporte y carga'] *= 0.4
    if not sc: return 'Otros / no determinado', []
    ordered = sorted(sc.items(), key=lambda kv: -kv[1])
    prim = ordered[0][0] if ordered[0][1] >= 2 else 'Otros / no determinado'
    sec = [n for n, s in ordered[1:] if s >= max(4, ordered[0][1] * 0.45)][:2]
    return prim, sec

# ---------------------------------------------------------------- temas
TEMAS = [
 ('Declaración de salud y preexistencias', [r'declaraci[oó]n (personal )?de (salud|estado de salud)', r'preexistencia', r'preexistente', r'requisitos de asegurabilidad'], 2),
 ('Reticencia o inexactitud en la declaración del riesgo', [r'reticencia', r'inexactitud', r'declaraci[oó]n (falsa|inexacta)', r'art[ií]culo 525', r'omiti[óo] declarar'], 2),
 ('Exclusiones de cobertura', [r'exclusi[oó]n', r'excluid[oa]s?', r'riesgo excluido', r'no (se encuentra|est[aá]) cubiert'], 4),
 ('Conducción bajo influencia del alcohol', [r'estado de ebriedad', r'alcoholemia', r'bajo la influencia del alcohol', r'gramos por mil', r'alcohol en la sangre', r'prueba respiratoria', r'alcotest'], 2),
 ('Licencia de conducir / uso del vehículo', [r'licencia de conducir', r'licencia (no )?vigente', r'uso (comercial|distinto)', r'transporte de pasajeros', r'\buber\b'], 2),
 ('Mora en la prima y terminación del contrato', [r'no pago de (la )?prima', r'mora en el pago', r'art[ií]culo 528', r'terminaci[oó]n (anticipada )?del (contrato|seguro)', r'falta de pago de la prima', r'p[oó]liza (caducada|terminada)'], 2),
 ('Prescripción', [r'prescripci[oó]n', r'prescrit[oa]', r'art[ií]culo 541'], 3),
 ('Liquidación del siniestro e informe del liquidador', [r'informe de liquidaci[oó]n', r'liquidador', r'impugnaci[oó]n del informe', r'procedimiento de liquidaci[oó]n', r'reglamento de auxiliares', r'impugnaci[oó]n del informe', r'objeci[oó]n (del|al) informe', r'impugn[oó] (el|dicho) informe'], 9),
 ('Monto de la indemnización (infraseguro, deducible, valor)', [r'infraseguro', r'deducible', r'regla proporcional', r'valor comercial', r'sobreseguro', r'monto de la indemnizaci[oó]n', r'p[eé]rdida total', r'valor de reposici[oó]n', r'menor valor'], 3),
 ('Agravación del riesgo', [r'agravaci[oó]n del riesgo', r'agravamiento del riesgo', r'art[ií]culo 526'], 1),
 ('Dolo, fraude o simulación del asegurado', [r'siniestro (simulado|provocado|intencional)', r'autoatentado', r'dolo del asegurado', r'fraude al seguro', r'actuar doloso', r'intencionalidad'], 1),
 ('Culpa grave del asegurado', [r'culpa grave', r'negligencia grave'], 1),
 ('Prueba del siniestro y carga de la prueba', [r'carga de la prueba', r'art[ií]culo 539', r'se presume que el siniestro', r'acreditar la ocurrencia', r'onus probandi', r'peso de la prueba'], 2),
 ('Aviso o denuncia del siniestro', [r'denuncia (oportuna|tard[ií]a|del siniestro)', r'aviso (oportuno|del siniestro)', r'plazo para denunciar', r'deber de denunciar'], 2),
 ('Protección al consumidor (Ley 19.496)', [r'19\.?496', r'ley (de|del) (protecci[oó]n (al|de los derechos de los) )?consumidor', r'proveedor', r'infracci[oó]n a la ley'], 4),
 ('Daño moral', [r'da[ñn]o moral'], 3),
 ('Lucro cesante / daño emergente', [r'lucro cesante', r'da[ñn]o emergente'], 3),
 ('Interpretación de la póliza (pro asegurado)', [r'interpretaci[oó]n (del contrato|de la p[oó]liza|de las cl[aá]usulas)', r'1566', r'contra proferentem', r'pro asegurado', r'favorable al asegurado', r'cl[aá]usulas? ambigu'], 2),
 ('Rol del corredor de seguros', [r'corredor(a)? de seguros', r'art[ií]culo 57 del d\.?f\.?l', r'intermediario'], 3),
 ('Competencia arbitral', [r'incompetencia', r'cl[aá]usula (de )?(compromisoria|arbitral)', r'designaci[oó]n de [aá]rbitro', r'competencia del (tribunal|juez) [aá]rbitro', r'excepci[oó]n de incompetencia'], 2),
 ('Seguro colectivo / adhesión', [r'p[oó]liza colectiva', r'seguro colectivo', r'certificado de cobertura', r'adhesi[oó]n'], 3),
 ('Alza o modificación unilateral de prima', [r'alza (de|del precio de) la prima', r'ajuste de primas?', r'modificaci[oó]n unilateral', r'readecuaci[oó]n', r'reajuste de la prima', r'incremento de la prima'], 1),
 ('Suicidio', [r'suicidio'], 2),
 ('Subrogación de la aseguradora', [r'subrogaci[oó]n', r'art[ií]culo 534', r'subrogad'], 2),
 ('Robo vs. hurto / apropiación', [r'\bhurto\b', r'apropiaci[oó]n indebida', r'robo con fuerza', r'robo con violencia'], 2),
 ('Intereses, reajustes y costas', [r'intereses corrientes', r'reajustes?', r'intereses moratorios'], 5),
]
TEMA_RES = [(n, [re.compile(p, re.I) for p in pats], th) for n, pats, th in TEMAS]
def clasif_temas(text, materia):
    out = []
    for n, pats, th in TEMA_RES:
        k = sum(len(p.findall(text)) for p in pats) + 3 * sum(len(p.findall(materia or '')) for p in pats)
        if k >= th: out.append((n, k))
    out.sort(key=lambda x: -x[1])
    return [n for n, _ in out]

# ---------------------------------------------------------------- normas
LEYES = [
 ('CCom', r'C[oó]d(igo|\.)\s*(de\s+)?Comercio|C\.\s?(de\s)?Com\.?'),
 ('CC', r'C[oó]d(igo|\.)\s*Civil|C\.\s?C\.'),
 ('CPC', r'C[oó]d(igo|\.)\s*(de\s+)?Procedimiento\s+Civil|C\.\s?P\.\s?C\.?'),
 ('Ley 19.496', r'Ley\s*(N[°º]\s*|n[uú]mero\s*)?19\.?496|Ley (sobre|de) Protecci[oó]n (de los Derechos de los|al) Consumidor'),
 ('DFL 251', r'D\.?\s?F\.?\s?L\.?\s*(N[°º]\s*)?251'),
 ('Ley 18.287', r'Ley\s*(N[°º]\s*)?18\.?287'),
 ('Ley 15.231', r'Ley\s*(N[°º]\s*)?15\.?231'),
 ('CPR', r'Constituci[oó]n Pol[ií]tica'),
 ('DS 1055', r'(D\.?\s?S\.?|Decreto Supremo)\s*(N[°º]\s*)?1\.?055'),
]
LEY_RES = [(k, re.compile(p, re.I)) for k, p in LEYES]
ART_RE = re.compile(r'\b(art[ií]culos?|arts?\.)\s', re.I)
def extract_normas(text):
    found = collections.Counter()
    laws_present = collections.Counter()
    for k, rx in LEY_RES:
        for m in rx.finditer(text):
            laws_present[k] += 1
            # ventana hacia atrás hasta el último "artículo"
            start = max(0, m.start() - 220)
            win = text[start:m.start()]
            arts = list(ART_RE.finditer(win))
            if not arts: continue
            seg = win[arts[-1].end():]
            if re.search(r'C[oó]digo|Ley|D\.F\.L|Constituci', seg, re.I): continue  # pertenece a otra ley
            seg = re.split(r'\b(N[°º]|inciso|n[uú]mero)\b', seg)[0] if False else seg
            seg = re.sub(r'(N[°º]\s*\d+|inciso\s+\w+|numeral\s+\d+|letra\s+\w\))', ' ', seg, flags=re.I)
            nums = re.findall(r'\b(\d{1,4})(?:\s*(?:bis|ter))?\b', seg)
            rng = re.findall(r'\b(\d{1,4})\s*(?:al|a)\s*(\d{1,4})\b', seg)
            sset = set(int(n) for n in nums)
            for a, b in rng:
                a, b = int(a), int(b)
                if 0 < b - a <= 15: sset.update(range(a, b + 1))
            for n in sset:
                if 1 <= n <= 2600: found[(k, n)] += 1
    return found, laws_present

# ---------------------------------------------------------------- procedimiento / resultado de la resolución
def tipo_procedimiento(text, org):
    t = deacc(text[:20000].lower())
    full = deacc(text.lower())
    if re.search(r'recurso de protecci|accion de protecci|accion constitucional de protecci', t): return 'Recurso de protección'
    if org == 'CS':
        if 'unificacion de jurisprudencia' in t: return 'Unificación de jurisprudencia'
        if 'casacion en el fondo' in t and 'casacion en la forma' in t: return 'Casación en la forma y en el fondo'
        if 'casacion en el fondo' in t: return 'Casación en el fondo'
        if 'casacion en la forma' in t: return 'Casación en la forma'
        if 'recurso de queja' in t: return 'Recurso de queja'
        if 'apelacion' in t: return 'Apelación'
        return 'Otro (Corte Suprema)'
    if org == 'CA':
        if 'recurso de queja' in t[:4000]: return 'Recurso de queja'
        if 'casacion en la forma' in t and 'apelacion' in t: return 'Apelación y casación en la forma'
        if 'casacion en la forma' in t: return 'Casación en la forma'
        if 'recurso de hecho' in t[:4000]: return 'Recurso de hecho'
        return 'Apelación'
    if org == 'JPL': return 'Juicio de consumidor (JPL)'
    if org == 'ARB': return 'Juicio arbitral'
    if org == 'JC':
        if re.search(r'gestion preparatoria|medida prejudicial', t[:3000]): return 'Gestión preparatoria / prejudicial'
        if re.search(r'designacion de arbitro', t[:5000]): return 'Designación de árbitro'
        if re.search(r'juicio sumario|procedimiento sumario', t): return 'Juicio sumario'
        return 'Juicio ordinario / civil'
    return 'No determinado'

RESOL_MARK = re.compile(r'(SE\s+RESUELVE|RESUELVO|SE\s+DECLARA|SE\s+DECIDE|se\s+resuelve\s*:|se\s+declara\s*:|se\s+decide\s*:|se\s+confirma|se\s+revoca|se\s+rechaza|se\s+acoge|se\s+declara\s+inadmisible|no\s+ha\s+lugar|se\s+desestima|se\s+tiene\s+por\s+no\s+interpuesto|se\s+declara\s+desierto|se\s+aprueba|declarando:|resolviendo:|se\s+condena)', re.I)
END_MARK = re.compile(r'(Reg[ií]strese|An[oó]tese|Notif[ií]quese|Comun[ií]quese|Devu[eé]lvase|Arch[ií]vese|Redacci[oó]n (del|de la)|Pronunciad[oa] por)', re.I)
def parte_resolutiva(text):
    text = re.sub(r'(Este\s*documento\s*tiene\s*firma\s*electr[oó]nica|Estedocumentotienefirma)[\s\S]{0,700}?(horaoficial\.cl\.?|C[oó]digo:\s*[A-Z]{8,12}|tramitaci[oó]n de la causa\.?)', ' ', text, flags=re.I)
    text = re.sub(r'CERTIFICO:?[\s\S]{0,400}?(firme y ejecutoriada|ejecutoriada)[^\n]*', ' ', text, flags=re.I)
    # busca el inicio de la parte resolutiva en el último 40% del texto
    n = len(text)
    zone_start = int(n * 0.45) if n > 4000 else 0
    zone = text[zone_start:]
    # preferir marcadores fuertes
    strong = list(re.finditer(r'(SE\s+RESUELVE|RESUELVO|SE\s+DECLARA|se\s+resuelve\s*:|se\s+declara\s*:|se\s+decide\s*:|resolviendo\s*:|declarando\s*:)', zone))
    m = strong[-1] if strong else None
    if not m:
        cands = list(RESOL_MARK.finditer(zone))
        m = cands[0] if cands else None
        # elegir el primero después del último "Considerando"/"Por estas consideraciones"
        pm = list(re.finditer(r'(por (estas|tales|todas estas|las) (consideraciones|razones|motivaciones|fundamentos)|y visto(s)?,? (adem[aá]s|tambi[eé]n)?,? lo dispuesto|y de conformidad (adem[aá]s )?con lo)', zone, re.I))
        if pm:
            m = pm[-1]
    if not m: return ''
    s = zone[m.start():]
    # incluir frase previa "Por estas consideraciones..."
    pre = zone[max(0, m.start() - 600):m.start()]
    pmatch = list(re.finditer(r'(Por (estas|tales|todas estas|las) (consideraciones|razones|motivaciones|fundamentos)|Y visto|De conformidad|Atendido)', pre, re.I))
    if pmatch: s = pre[pmatch[-1].start():] + s
    e = END_MARK.search(s, 40)
    if e: s = s[:e.start()]
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:2200]

def desenlace(resol, org, proc):
    r = deacc(resol.lower())
    if not r: return 'No identificado'
    if re.search(r'inadmisible|se tiene por no interpuest|desierto|no ha lugar al recurso de queja|improcedente el recurso', r): return 'Recurso inadmisible / desierto'
    if 'protecci' in deacc(proc.lower()):
        if re.search(r'(se )?acoge|ha lugar', r) and not re.search(r'se rechaza el recurso|no ha lugar al recurso|se rechaza la accion|rechaza.{0,40}protecci', r): return 'Protección acogida'
        if re.search(r'revoca', r) and re.search(r'acoge', r): return 'Protección acogida'
        return 'Protección rechazada' if re.search(r'rechaz|no ha lugar|confirma', r) else 'Otro'
    if org == 'CS':
        if re.search(r'(se )?rechaza(n)?,?.{0,80}(recurso|casacion)', r) or re.search(r'no ha lugar.{0,40}(recurso|casacion)', r): return 'Casación / recurso rechazado'
        if re.search(r'(se )?acoge.{0,80}(recurso|casacion)|se invalida|se anula', r): return 'Casación / recurso acogido'
        if 'confirma' in r: return 'Confirma'
        if 'revoca' in r: return 'Revoca'
    if org == 'CA':
        conf = re.search(r'se confirma|confirma(n)?(se)?(\s|,)', r); rev = re.search(r'se revoca|revoca(n)?(se)?(\s|,)', r)
        if rev and conf: return 'Revoca en parte / confirma en lo demás'
        if conf and re.search(r'con declaraci[oó]n|se declara que|se eleva|se reduce|se rebaja|se aumenta|con la (sola )?declaraci', r): return 'Confirma con declaración'
        if conf: return 'Confirma'
        if rev: return 'Revoca'
        if re.search(r'(acoge|rechaza).{0,80}casacion', r): return 'Resuelve casación en la forma'
    if re.search(r'abandono del procedimiento|abandonado el procedimiento', r) and re.search(r'acoge|declara', r): return 'Abandono del procedimiento'
    if re.search(r'acoge.{0,20}(la )?incompetencia', r): return 'Incompetencia declarada'
    if re.search(r'(acoge|ha lugar a).{0,40}excepcion de incompetencia|me declaro incompetente|se declara incompetente|declarandose.{0,40}incompetencia|se declarara incompetente', r) and not re.search(r'rechaza.{0,30}excepcion de incompetencia', r): return 'Incompetencia declarada'
    if re.search(r'avenimiento|desist|transaccion|conciliacion|finiquito', r) and not re.search(r'(acoge|rechaza).{0,40}demanda', r): return 'Avenimiento / desistimiento / otro término'
    r = re.sub(r'se desecha(n)?|desechase|se niega lugar|niega(se)? lugar|se desestima(n)?|desestimase|no se da lugar( a)?|no ha lugar( a)?', 'se rechaza', r)
    r = re.sub(r'no ha lugar (al|a la) (denuncio|denuncia|querella|demanda|accion)', 'se rechaza la demanda', r)
    r = re.sub(r'resuelve acoger', 'se acoge', r)
    r = re.sub(r'absuelv[ea]se|se absuelve|absolviendo', 'se rechaza la demanda; absuelve', r)
    r = re.sub(r'demanda(s)? reconvencional(es)?', 'reconvencion', r)
    r = re.sub(r'no se hace lugar( a)?|no se da lugar( a)?|no ha lugar( a)?', 'se rechaza', r)
    # primera instancia
    if re.search(r'(se )?acoge(n)?\s+(parcialmente|en parte)|acoge(n)?se\s+parcialmente|solo en cuanto|s[oó]lo en cuanto', r): return 'Demanda acogida parcialmente'
    ACO = r'(se )?acoge(n)?.{0,60}(demanda|denuncia|querella|accion)(s|es)?\b|ha lugar a la demanda|\bha lugar (a )?(la |el )?(denuncia|demanda|querella|denuncio)|condenase|condenandose|condenando a|se condena a la (demandada|denunciada|querellada|compania)|(la|que la) (demandada|denunciada|querellada) (incumplio|debera (pagar|dar cobertura|indemnizar))'
    if re.search(r'(se )?rechaza(n)?.{0,60}(demanda|denuncia|querella|accion)(s|es)?\b|no ha lugar a la demanda|no ha lugar.{0,40}(demanda|denuncia|querella)', r) and not re.search(ACO, r): return 'Demanda rechazada'
    if re.search(ACO, r):
        if re.search(r'(se )?rechaza.{0,60}(demanda|denuncia|querella|accion)(s|es)?\b|en lo demas', r): return 'Demanda acogida parcialmente'
        return 'Demanda acogida'
    if re.search(r'se condena', r): return 'Demanda acogida'
    if re.search(r'aprueba|avenimiento|transaccion|conciliacion', r): return 'Aprueba acuerdo / otro'
    return 'Otro'

# ---------------------------------------------------------------- rol y partes
def extract_rol(text, org):
    t = text
    for rx in [r'Rol\s*(?:N[°º]\.?|Nro\.?|n[uú]mero)?\s*:?\s*((?:[A-Z]{1,2}|Civil|Protecci[oó]n|Policia Local|Polic[ií]a Local)\s*-\s*)?(\d{1,3}(?:\.\d{3})*|\d+)\s*[-–]\s*(\d{4})',
               r'N[°º]\s*((?:Civil|Protecci[oó]n|Policia Local|Polic[ií]a Local|Laboral)\s*-\s*)(\d+)\s*-\s*(\d{4})',
               r'\b([CV]\s*-\s*)(\d{1,6})\s*-\s*(\d{4})']:
        ms = list(re.finditer(rx, t[-3000:], re.I)) + list(re.finditer(rx, t[:1500], re.I))
        if ms:
            m = ms[0]
            pre = (m.group(1) or '').replace(' ', '')
            return f"{pre}{m.group(2).replace('.', '')}-{m.group(3)}"
    return None
def extract_caratula(text):
    m = re.search(r'CARATULADO\s*:?\s*([^\n]{3,120})', text[:2000])
    if m: return m.group(1).strip()
    m = re.search(r'caratulad[oa]s?,?\s*[“"«]([^”"»]{5,160})[”"»]', text[:6000], re.I)
    if m: return re.sub(r'\s+', ' ', m.group(1)).strip()
    m = re.search(r'[“"«]([^”"»\n]{3,80}\s+con\s+[^”"»]{3,90})[”"»]', text[:6000])
    if m: return re.sub(r'\s+', ' ', m.group(1)).strip()
    return None

# ---------------------------------------------------------------- limpieza de texto
BOILER = [
 r'^Este\s*documento\s*tiene\s*firma\s*electr[oó]nica.*$', r'^y su original puede ser\s*(validado)?.*$', r'^validado en http.*$', r'^puede ser validado en.*$',
 r'^.*verificadoc\.pjud\.cl.*$', r'^tramitaci[oó]n de la causa\.?$', r'^A contar del .{0,40}la hora.*$', r'^visualizada corresponde.*$', r'^corresponde al horario.*$',
 r'^en Chile Continental\..*$', r'^Continental\. Para Chile Insular.*$', r'^de Pascua e Isla Salas.*$', r'^Para Chile Insular.*$', r'^e Isla Salas y G[oó]mez.*$', r'^informaci[oó]n consulte http.*$',
 r'^m[aá]s informaci[oó]n consulte.*$', r'^horaoficial\.cl.*$', r'^En aquellos documentos en que se visualiza.*$', r'^esta corresponde al horario.*$', r'^Isla Salas y G[oó]mez restar.*$',
 r'^Fecha:\s*\d{2}/\d{2}/\d{4}.*$', r'^[A-Z]{8,12}$', r'^C[oó]digo:\s*[A-Z]{8,12}$', r'^Est?e?documento\w*$', r'^Pascua e Isla Salas.*$', r'^Insular Occidental.*$',
 r'^Chile Continental\.?.*$', r'^\d+\s*$', r'^\d{1,2}:\d{1,2}(:\d{1,2})?$', r'^horario de verano establecido.*$', r'^corresponde al horario de (verano|invierno).*$', r'^la hora visualizada.*$',
]
BOILER_RE = [re.compile(p, re.I) for p in BOILER]
HEAD_RE = re.compile(r'^\s*(VISTOS?( Y TENIENDO PRESENTE)?|CONSIDERANDO|Y CONSIDERANDO|TENIENDO PRESENTE|SE RESUELVE|RESUELVO|SE DECLARA|EN CUANTO A LA (FORMA|EXCEPCI[OÓ]N|TACHA|OBJECI[OÓ]N|DEMANDA|ACCI[OÓ]N|INFRACCI[OÓ]N|CASACI[OÓ]N|APELACI[OÓ]N)[^\n]{0,60}|EN CUANTO AL FONDO|I+\.\-?\s*[A-ZÁÉÍÓÚ][^\n]{0,80}|PARTE EXPOSITIVA|PARTE CONSIDERATIVA|PARTE RESOLUTIVA)\s*[:.\-]*\s*$', re.I)
NUMBERED_RE = re.compile(r'^\s*((PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|S[EÉ]PTIMO|OCTAVO|NOVENO|D[EÉ]CIMO|UND[EÉ]CIMO|DUOD[EÉ]CIMO|VIG[EÉ]SIMO|TRIG[EÉ]SIMO|DECIMO\w*|D[EÉ]CIMO\s*\w+|VIG[EÉ]SIMO\s*\w+)\s*[:.\-]|\d{1,3}\s*[°ºo]?\s*[\.\-\)]{1,3}\s|\d{1,3}\s*[°º]\s*[:.\-\)]?|[a-zñ]\)\s|[IVX]{1,5}\.\-?\s|Vistos?\s*[:.,]|Considerando\s*[:.]?|Se resuelve|Por estas consideraciones|Y visto|Reg[ií]strese|Atendido)', re.I)

def clean_text(raw):
    lines = raw.replace('\r', '').split('\n')
    lines = [re.sub(r'[ \t ]+', ' ', l).strip() for l in lines]
    keep = []
    for l in lines:
        if not l: keep.append(''); continue
        if any(rx.match(l) for rx in BOILER_RE): continue
        keep.append(l)
    lens = [len(l) for l in keep if len(l) > 20]
    full = statistics.quantiles(lens, n=10)[7] if len(lens) >= 10 else 80
    paras = []
    cur = ''
    def flush():
        nonlocal cur
        if cur.strip(): paras.append(cur.strip())
        cur = ''
    for i, l in enumerate(keep):
        if not l:
            flush(); continue
        if HEAD_RE.match(l) or NUMBERED_RE.match(l):
            flush(); cur = l
            if HEAD_RE.match(l): flush()
            continue
        if not cur:
            cur = l; continue
        if cur.endswith('-') and l[:1].islower():
            cur = cur[:-1] + l
        else:
            cur = cur + ' ' + l
        # fin de párrafo si la línea es corta y termina en puntuación
        if re.search(r'[.:;]["”»]?$', l) and len(l) < full * 0.72:
            flush()
    flush()
    return '\n\n'.join(paras)

# ================================================================ procesamiento
groups = collections.OrderedDict()
for r in rows:
    key = (r['sen_identificador'], r['sen_secuencia'])
    groups.setdefault(key, []).append(r)

sentencias = []
norm_rows = []
for (cid, seq), docs in groups.items():
    docs.sort(key=lambda d: int(d['sen_id_sec_doc'] or 0))
    d0 = docs[0]
    raw = '\n\n'.join((d['texto'] or '') for d in docs)
    text_main = docs[0]['texto'] or ''
    org, city = detect_court(text_main if text_main.strip() else raw, d0['tribunal'], d0['tipo_tribunal'])
    proc = tipo_procedimiento(raw, org)
    ramo, ramo2 = clasif_ramo(d0['materia'], raw, d0['tipo_seguro'])
    temas = clasif_temas(raw, d0['materia'])
    normas, leyes = extract_normas(raw)
    resol = parte_resolutiva(text_main) if len(text_main) > 200 else ''
    if not resol and len(docs) > 1:
        resol = parte_resolutiva(raw)
    des = desenlace(resol, org, proc)
    fn = d0['fecha_notificacion']
    fn_iso = f'{fn[6:10]}-{fn[3:5]}-{fn[0:2]}' if fn and re.match(r'\d{2}/\d{2}/\d{4}', fn) else None
    fecha = best_date(text_main, fn_iso) or best_date(raw, fn_iso)
    if org == 'CS': inst = 'Corte Suprema'
    elif org == 'CA': inst = 'Protección (Corte de Apelaciones)' if proc == 'Recurso de protección' else 'Segunda instancia'
    elif org in ('JC', 'JPL', 'ARB'): inst = 'Primera instancia'
    else: inst = 'No determinada'
    if proc == 'Recurso de protección' and org == 'CS': inst = 'Corte Suprema'
    if org == 'CA': tribunal_n = f'Corte de Apelaciones de {city}' if city else 'Corte de Apelaciones'
    elif org == 'CS': tribunal_n = 'Corte Suprema'
    elif org == 'JPL': tribunal_n = f'Juzgado de Policía Local de {city}' if city else 'Juzgado de Policía Local'
    elif org == 'JC': tribunal_n = f'Juzgado Civil / de Letras de {city}' if city else 'Juzgado Civil / de Letras'
    elif org == 'ARB':
        nm = d0['tribunal'] if d0['tipo_tribunal'] == 'Arbitral' and not re.search(r'corte|juzgado|ica|civil', (d0['tribunal'] or ''), re.I) else None
        tribunal_n = f'Árbitro {nm.strip().title()}' if nm else 'Tribunal arbitral'
    else: tribunal_n = d0['tribunal'] or 'No determinado'
    rol = extract_rol(text_main, org) or d0['rol_causa']
    s = dict(
        id=f'{cid}-{seq}', causa=int(cid), secuencia=int(seq), n_docs=len(docs),
        docs=[d['archivo_local'] for d in docs], ids_origen=[d['id'] for d in docs],
        compania=d0['compania'], grupo=grupo_cia(d0['compania']),
        tipo_seguro=d0['tipo_seguro'], materia=re.sub(r'\s+', ' ', d0['materia'] or '').strip(),
        resultado_cmf=d0['resultado'], estado=d0['estado'], tipo_tribunal_cmf=d0['tipo_tribunal'],
        tribunal_informado=d0['tribunal'], rol_informado=d0['rol_causa'],
        organo=ORG_LABEL[org], org=org, ciudad=city, tribunal=tribunal_n, instancia=inst, procedimiento=proc,
        rol=rol, caratula=extract_caratula(text_main), fecha_sentencia=fecha, fecha_notificacion=fn_iso,
        anio=int((fecha or fn_iso or '0000')[:4]) or None,
        ramo=ramo, ramos_sec=ramo2, temas=temas,
        normas={f'{k} art. {n}': v for (k, n), v in sorted(normas.items(), key=lambda kv: (kv[0][0], kv[0][1]))},
        leyes=dict(leyes), resolutiva=resol, desenlace=des,
        chars=len(raw),
    )
    s['texto'] = clean_text(raw) if raw.strip() else ''
    sentencias.append(s)

# ---------------------------------------------------------------- calidad del texto
WORD_RE = re.compile(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]{2,}')
COMMON = set('que de la el en los del las por con para una se al su lo como mas sin sobre este esta fue son ser dicho dicha seguro poliza demanda compania sentencia tribunal parte articulo contrato asegurado siniestro corte recurso costas no ha lugar'.split())
def calidad(t):
    if not t.strip(): return 'Sin texto'
    if t.count('(cid:') > 20: return 'Ilegible (codificación PDF)'
    words = WORD_RE.findall(t)
    if not words: return 'Ilegible (codificación PDF)'
    known = sum(1 for w in words if deacc(w.lower()) in COMMON)
    ratio = known / len(words)
    junk = len(re.findall(r'[#~@{}\[\]<>^|$]', t)) / max(1, len(t))
    if ratio < 0.12 or junk > 0.01: return 'OCR deficiente'
    return 'Buena'
for s in sentencias:
    s['calidad_texto'] = calidad(s['texto'])
    s['normas'] = {k: v for k, v in s['normas'].items() if not (re.match(r'(CC|CPC|CCom) art\. \d$', k))}

# ---------------------------------------------------------------- ramo a nivel de causa
by_causa = collections.defaultdict(list)
for s in sentencias: by_causa[s['causa']].append(s)
for cid, ss in by_causa.items():
    raw_all = '\n'.join(x['texto'] for x in ss)
    mats = ' | '.join(sorted(set(x['materia'] for x in ss if x['materia'])))
    ramo, ramo2 = clasif_ramo(mats, raw_all, ss[0]['tipo_seguro'])
    for x in ss:
        x['ramo'] = ramo; x['ramos_sec'] = ramo2
        x['temas_causa'] = sorted(set(t for y in ss for t in y['temas']))

json.dump(sentencias, open('sentencias_proc.json', 'w'), ensure_ascii=False)
print(len(sentencias))

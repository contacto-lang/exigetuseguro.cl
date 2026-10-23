"""Paso 2: vínculos entre sentencias por rol citado o compartido, duplicados y precedentes."""
import json, re, collections, unicodedata, difflib
S = json.load(open('sentencias_proc.json'))
D = {s['id']: s for s in S}
def deacc(x): return ''.join(c for c in unicodedata.normalize('NFD', x) if unicodedata.category(c) != 'Mn')
def key(n, y): return f"{int(n.replace('.', ''))}-{y}"
NUMY = r'(\d{1,3}(?:\.\d{3})+|\d{1,7})\s*[-–/]\s*((?:19|20)\d{2})'
def own_keys(s):
    ks = set()
    for r in (s['rol'], s['rol_informado']):
        for m in re.finditer(NUMY, r or ''): ks.add(key(m.group(1), m.group(2)))
    return ks
OWN = {s['id']: own_keys(s) for s in S}
ROLRE = re.compile(r'\b(?:rol(?:es)?|ingreso|autos|causa|N[°º]\.?|reclamaci[oó]n|protecci[oó]n|civil|polic[ií]a local)\b[^0-9\n]{0,25}?(?:[A-Z]{1,2}\s*-\s*)?' + NUMY, re.I)
CROL = re.compile(r'\b[CV]\s*-\s*(\d{1,6})\s*-\s*((?:19|20)\d{2})')
COURT = [('CS', r'corte suprema|casaci[oó]n en el fondo'), ('CA', r'corte de apelaciones|c\.\s?a\.|iltma|ilustr|apelaci[oó]n|segunda instancia|protecci[oó]n'),
         ('JPL', r'polic[ií]a local|j\.?p\.?l'), ('ARB', r'[aá]rbitr'), ('JC', r'juzgado|tribunal de (primera|1)|primera instancia|letras|civil')]
def court_of(ctx):
    c = deacc(ctx.lower())
    best = None
    for k, p in COURT:
        for m in re.finditer(p, c):
            if best is None or m.end() > best[1]: best = (k, m.end())
    return best[0] if best else None
CITY = ['Santiago','San Miguel','Concepción','Valparaíso','Valdivia','Temuco','Puerto Montt','La Serena','Antofagasta','Rancagua','Talca','Chillán','Arica','Iquique','Copiapó','Punta Arenas','Coyhaique','Viña del Mar','Osorno','Los Ángeles','Coquimbo','Calama','Talcahuano','Las Condes','Vitacura','Providencia','Parral','Curanilahue','Traiguén']
def court_name(ctx, k):
    c = ctx
    m = re.search(r'((?:\d+\s*[°º]?|primer|segundo|tercer|cuarto|quinto|s[eé]ptimo|octavo|noveno|d[eé]cimo\w*|und[eé]cimo|duod[eé]cimo|vig[eé]simo\w*)?\s*juzgado[^,.;\n]{0,60}|(?:i(?:ltma|lustr[ií]sima)?\.?\s*)?corte de apelaciones de [A-ZÁÉÍÓÚ][\wáéíóúñ]+(?: [A-ZÁÉÍÓÚ][\wáéíóúñ]+)?|corte suprema|(?:juez )?[aá]rbitro[^,.;\n]{0,50})', c, re.I)
    if m:
        t = re.sub(r'\s+', ' ', m.group(0)).strip(' ,')
        t = re.split(r',| en los autos| rol| en causa| caratulad| de fecha| que ', t, flags=re.I)[0]
        return t[:80]
    return {'CS':'Corte Suprema','CA':'Corte de Apelaciones','JPL':'Juzgado de Policía Local','ARB':'Tribunal arbitral','JC':'Juzgado de primera instancia'}.get(k, 'Tribunal no identificado')

PREC = re.compile(r'jurisprudencia|ha (resuelto|fallado|sostenido|declarado|se[ñn]alado)|han (resuelto|fallado|sostenido)|en el mismo sentido|as[ií] lo|as[ií] se|v[eé]ase|cfr|citad[oa]|precedente|criterio|fallo de (la )?(excma|iltma|ilustr)|sentencia de (la )?(excma\.? |iltma\.? |e\. |i\. )?corte (suprema|de apelaciones) de (fecha )?\d|resolvi[oó] de forma|an[aá]loga|reiterad|doctrina|tambi[eé]n se rechaza|como lo ha|seg[uú]n lo ha|por ejemplo|otra causa|otro juicio|juicio .{0,40} con ', re.I)
SAME = re.compile(r'sentencia apelada|a quo|apelad[oa]|de primera instancia|estos autos|la presente causa|de autos|en contra de la sentencia|recurso de (casaci[oó]n|apelaci[oó]n|queja|hecho)|que inciden en|acumulad|se confirma|se revoca|devu[eé]lvase|elevad|tr[aá]igase|vistos|dictada por el (tribunal|juzgado|se[ñn]or [aá]rbitro|juez)|pronunciada por|ejecutoriada|certifico', re.I)
def ctx_kind(ctx, pos, n, org, ck):
    c = deacc(ctx.lower())
    if PREC.search(c): return 'precedente'
    if SAME.search(c): return 'misma'
    if org in ('CA','CS') and ck in ('JC','JPL','ARB','CA') and (pos < 2500 or pos > n - 2500): return 'misma'
    return None
def surnames(s):
    toks = set()
    for src in (s['caratula'] or '', s['texto'][:1500]):
        for w in re.findall(r'\b[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ]{3,}\b', src):
            w = deacc(w.upper())
            if w not in STOP: toks.add(w)
    return toks
STOP = set('SEGUROS SEGURO COMPANIA GENERALES VIDA CHILE SANTIAGO SENTENCIA JUZGADO CORTE APELACIONES SUPREMA CIVIL POLICIA LOCAL CAUSA CARATULADO NOMENCLATURA VISTOS FOJAS FOJA BANCO SANTANDER ZURICH LIBERTY REALE CONSORCIO NACIONAL MAPFRE CHILENA CONSOLIDADA METLIFE BICE CARDIF PARIBAS DEMANDA DEMANDANTE DEMANDADA QUE PARA CONTRA CON DON DONA RECURSO PROTECCION ARBITRO JUEZ ABOGADO REGION METROPOLITANA COMUNA CONDES PROVIDENCIA SECRETARIA ROL TRIBUNAL TERCER SEGUNDO PRIMER LETRAS ARBITRAL EXCMA ILTMA TERCERA PRIMERA SEGUNDA SALA'.split())
SUR = {s['id']: surnames(s) for s in S}

idx = collections.defaultdict(set)
for s in S:
    for k in OWN[s['id']]: idx[k].add(s['id'])

def sh(t):
    w = re.findall(r'\w+', deacc(t.lower()))
    return set(' '.join(w[i:i+5]) for i in range(len(w)-4))
def sim(a, b):
    A, B = sh(D[a]['texto']), sh(D[b]['texto'])
    if not A or not B: return 0
    return len(A & B) / min(len(A), len(B))

links = {}   # (a,b) -> dict
mentions = collections.defaultdict(list)
precs = collections.defaultdict(list)
for s in S:
    seen = set()
    for m in list(ROLRE.finditer(s['texto'])) + list(CROL.finditer(s['texto'])):
        k = key(m.group(1), m.group(2))
        if k in OWN[s['id']] or k in seen: continue
        ctx = s['texto'][max(0, m.start() - 220): m.end() + 40]
        ck = court_of(ctx[:260])
        kind = ctx_kind(s['texto'][max(0, m.start() - 320): m.end() + 60], m.start(), len(s['texto']), s['org'], ck)
        targets = [t for t in idx.get(k, ()) if t != s['id']]
        if targets:
            for t in targets:
                same_g = D[t]['grupo'] == s['grupo']
                common = SUR[s['id']] & SUR[t]
                if kind == 'precedente' or not same_g: conf = None
                elif kind == 'misma' and common: conf = 'alta'
                elif kind == 'misma' or len(common) >= 2: conf = 'media'
                else: conf = None
                if conf:
                    a, b = sorted([s['id'], t])
                    links[(a, b)] = dict(a=a, b=b, rol=k, via=f"{s['id']} cita el rol {k}", conf=conf)
            seen.add(k); continue
        if ck and kind and int(k.split('-')[1]) <= int((s['fecha_sentencia'] or s['fecha_notificacion'] or '2100')[:4]):
            (mentions if kind == 'misma' else precs)[s['id']].append(dict(rol=k, tipo=ck, tribunal=court_name(ctx, ck), ctx=re.sub(r'\s+', ' ', ctx[-200:]).strip()))
        seen.add(k)
# mismo rol propio en causas distintas
for k, ids in idx.items():
    ids = sorted(ids)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            common = SUR[a] & SUR[b]
            if D[a]['grupo'] != D[b]['grupo'] and len(common) < 2: continue
            fi = ('JC','JPL','ARB')
            if D[a]['org'] in fi and D[b]['org'] in fi and D[a]['tribunal'] != D[b]['tribunal'] and len(common) < 2: continue
            if not common and D[a]['tribunal'] != D[b]['tribunal']: continue
            links.setdefault((a, b), dict(a=a, b=b, rol=k, via=f"ambas tienen el rol {k}", conf='alta' if D[a]['grupo'] == D[b]['grupo'] else 'media'))
# coherencia procesal: dos cortes de apelaciones distintas, o dos tribunales de primera instancia distintos, no son instancias del mismo caso
FI=('JC','JPL')
def coherent(a,b):
    A,B=D[a],D[b]
    if A['org']=='CA' and B['org']=='CA' and A['ciudad'] and B['ciudad'] and A['ciudad']!=B['ciudad']: return False
    if A['org'] in FI and B['org'] in FI and A['tribunal']!=B['tribunal']: return False
    return True
links={k:v for k,v in links.items() if coherent(v['a'],v['b'])}
# duplicados
for (a, b), L in links.items():
    if D[a]['org'] == D[b]['org'] and (D[a]['tribunal'] == D[b]['tribunal']) and sim(a, b) > 0.8:
        L['dup'] = True
# expedientes: unión de causas por vínculos
parent = {s['causa']: s['causa'] for s in S}
def f(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
for L in links.values():
    ra, rb = f(D[L['a']]['causa']), f(D[L['b']]['causa'])
    if ra != rb: parent[max(ra, rb)] = min(ra, rb)
exp = collections.defaultdict(set)
for s in S: exp[f(s['causa'])].add(s['causa'])
multi = {k: sorted(v) for k, v in exp.items() if len(v) > 1}
# mentions: quedarse con las de tribunal distinto al propio (otra instancia) y deduplicar por rol
for i in list(mentions):
    out = []; ks = set()
    for m in mentions[i]:
        if m['rol'] in ks: continue
        ks.add(m['rol']); out.append(m)
    mentions[i] = out[:6]
for i in list(precs):
    out=[]; ks=set()
    for m in precs[i]:
        if m['rol'] in ks: continue
        ks.add(m['rol']); out.append(m)
    precs[i]=out[:10]
print('sentencias que citan precedentes', len(precs), 'total', sum(len(v) for v in precs.values()))
json.dump(dict(links=list(links.values()), expedientes=multi, mentions=mentions, precedentes=precs), open('links.json', 'w'), ensure_ascii=False, indent=0)
print('vínculos', len(links), collections.Counter(L['conf'] for L in links.values()), 'duplicados', sum(1 for L in links.values() if L.get('dup')))
print('expedientes multi-causa', len(multi), 'causas involucradas', sum(len(v) for v in multi.values()))
print('sentencias con instancias mencionadas no incluidas', len([m for m in mentions.values() if m]), 'total menciones', sum(len(m) for m in mentions.values()))
print(collections.Counter(m['tipo'] for v in mentions.values() for m in v))

"""Paso 3: reconstruye expedientes, instancias no incluidas, alertas y jurisprudencia citada."""
import json, re, collections, unicodedata, os
S = json.load(open('sentencias_proc.json')); J = json.load(open('links.json'))
D = {s['id']: s for s in S}
def deacc(x): return ''.join(c for c in unicodedata.normalize('NFD', x) if unicodedata.category(c) != 'Mn')
INS = {'Primera instancia':1,'Protección (Corte de Apelaciones)':2,'Segunda instancia':2,'Corte Suprema':3,'No determinada':4}
LVL = {'JC':1,'JPL':1,'ARB':1,'CA':2,'CS':3,'ND':0}
# expediente
STOPP=set('SEGUROS SEGURO COMPANIA GENERALES VIDA CHILE SANTIAGO OTROS OTRO LIMITADA LTDA SPA CIA DE DEL LA LAS LOS Y CON S A SA BANCO INSCRITA POLIZAS REGISTRO FOLIO'.split())
def parties(s):
    c = s['caratula'] or ''
    m = re.search(r'caratulad[oa]s?,?\s*[“"«]([^”"»]{5,160})[”"»]', s['texto'][:8000], re.I)
    if not c and m: c = m.group(1)
    if not c: return None
    c = deacc(c.upper())
    left = re.split(r'\s+CON\s+|/|\s+C/\s+|\s+CONTRA\s+', c)[0]
    toks = {w for w in re.findall(r'[A-Z]{3,}', left) if w not in STOPP}
    return toks or None
P = {s['id']: parties(s) for s in S}
def yr(s): 
    f = s['fecha_sentencia'] or s['fecha_notificacion']; return int(f[:4]) if f else None
LV = {'JC':1,'JPL':1,'ARB':1,'CA':2,'CS':3,'ND':0}
def coherent(a, b):
    A, B = D[a], D[b]
    if A['org']=='CA' and B['org']=='CA' and A['ciudad'] and B['ciudad'] and A['ciudad']!=B['ciudad']: return False
    if A['org'] in ('JC','JPL') and B['org'] in ('JC','JPL') and A['tribunal']!=B['tribunal']: return False
    ya, yb = yr(A), yr(B)
    if ya and yb and abs(ya-yb) > 9: return False
    return True
par = {s['id']: s['id'] for s in S}
def F(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
def U(a, b, why, ev):
    EV.append((a, b, why)); ra, rb = F(a), F(b)
    if ra != rb: par[max(ra, rb)] = min(ra, rb)
EV = []
# 1) vínculos por rol (citado o compartido)
for L in J['links']:
    if coherent(L['a'], L['b']): U(L['a'], L['b'], L['via'], 'rol')
# 2) misma "causa" CMF: se confía en la agrupación salvo que las partes difieran
bycm = collections.defaultdict(list)
for s in S: bycm[s['causa']].append(s['id'])
hetero = set()
for c, ids in bycm.items():
    ps = [P[i] for i in ids if P[i]]
    if any(not (a & b) for i, a in enumerate(ps) for b in ps[i+1:]): hetero.add(c)
for c, ids in bycm.items():
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            a, b = ids[i], ids[j]
            pa, pb = P[a], P[b]
            if c not in hetero:
                A, B = D[a], D[b]; ya, yb = yr(A), yr(B)
                lo, hi = (A, B) if LV[A['org']] <= LV[B['org']] else (B, A)
                ylo, yhi = yr(lo), yr(hi)
                ok = coherent(a, b) and (LV[A['org']] != LV[B['org']] or (A['rol'] and A['rol'] == B['rol']) or (pa and pb and pa & pb))
                if ok and ylo and yhi and (yhi < ylo - 1 or yhi - ylo > 6): ok = False
                if ok: U(a, b, 'misma causa CMF', 'cmf')
            elif pa and pb and (pa & pb) and coherent(a, b):
                U(a, b, 'misma causa CMF y mismas partes', 'cmf')
# 3) mismas partes y misma compañía en causas CMF distintas
ids = [s['id'] for s in S]
for i in range(len(ids)):
    a = ids[i]
    if not P[a]: continue
    for j in range(i+1, len(ids)):
        b = ids[j]
        if not P[b] or D[a]['causa'] == D[b]['causa'] or D[a]['grupo'] != D[b]['grupo']: continue
        if len(P[a] & P[b]) >= 2 and LV[D[a]['org']] != LV[D[b]['org']] and coherent(a, b):
            U(a, b, 'mismas partes y compañía', 'partes')
by_exp = collections.defaultdict(list)
for s in S: by_exp[F(s['id'])].append(s)
# numerar expedientes: E + causa menor del grupo
exp_name = {}
for root, ss in by_exp.items():
    exp_name[root] = min(s['causa'] for s in ss)
cnt = collections.Counter(exp_name.values()); k2 = collections.Counter()
for root in sorted(by_exp, key=lambda r: (exp_name[r], r)):
    base = exp_name[root]
    if cnt[base] > 1:
        k2[base] += 1; exp_name[root] = f"{base}.{k2[base]}"
    else: exp_name[root] = f"{base}"
for root, ss in by_exp.items():
    for s in ss: s['expediente'] = exp_name[root]
by_exp = {exp_name[r]: v for r, v in by_exp.items()}
EVID = collections.defaultdict(list)
for a, b, why in EV:
    EVID[a].append((b, why)); EVID[b].append((a, why))
print('grupos CMF heterogéneos', len(hetero), 'expedientes', len(by_exp), 'con varias sentencias', sum(len(v) > 1 for v in by_exp.values()))
link_of = collections.defaultdict(list)
for L in J['links']:
    link_of[L['a']].append(L); link_of[L['b']].append(L)
dupset = set()
for L in J['links']:
    if L.get('dup'):
        # el de mayor causa se marca como duplicado del otro
        a, b = sorted([L['a'], L['b']], key=lambda i: (D[i]['causa'], i))
        dupset.add(b); D[b]['duplicado_de'] = a
MESES = '(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)'
def lower_mention(s):
    t = s['texto'][:4000]; td = t
    if s['org'] == 'CA' and s['procedimiento'] != 'Recurso de protección':
        m = re.search(r'(?:dictad[oa]|pronunciad[oa]|expedid[oa])\s+por\s+(?:el|la)\s+((?:señor\s+|sr\.\s+)?(?:juez\s+)?[^,.;\n]{4,90})', t, re.I)
        trib = None
        if m:
            trib = re.split(r',| en (los )?autos| rol| en la causa| caratulad| que | con fecha', m.group(1), flags=re.I)[0].strip()
            if re.search(r'sala|esta corte|ministr|corte', trib, re.I): trib = None
        if not trib:
            m2 = re.search(r'(\d+\s*[°º]?\s*juzgado[^,.;\n]{3,60}|juzgado de polic[ií]a local[^,.;\n]{0,40}|juez [aá]rbitro[^,.;\n]{0,50}|tribunal arbitral)', t, re.I)
            trib = m2.group(1).strip() if m2 else None
        f = re.search(r'sentencia\s+(?:apelada\s+|definitiva\s+|de primera instancia\s+)?de\s+(?:fecha\s+)?([a-záéíóú\d]+ de ' + MESES + r' de [a-záéíóú\d ]{4,30}?)(?=[,.;]| escrita| dictada| pronunciada| que| por)', t, re.I)
        return dict(nivel='Primera instancia', tribunal=trib or 'Tribunal de primera instancia (no identificado)', fecha=f.group(1).strip() if f else '')
    if s['org'] == 'CS':
        m = re.search(r'(?:Iltma\.?\s+|Ilustr[ií]sima\s+)?Corte de Apelaciones de ([A-ZÁÉÍÓÚ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚ][a-záéíóúñ]+)?)', t)
        return dict(nivel='Corte de Apelaciones', tribunal=('Corte de Apelaciones de ' + m.group(1)) if m else 'Corte de Apelaciones (no identificada)', fecha='')
    if s['org'] == 'CA' and s['procedimiento'] == 'Recurso de protección':
        return None  # la protección nace en la Corte
    return None
for exp, ss in by_exp.items():
    ss.sort(key=lambda s: (LVL.get(s['org'], 0), s['fecha_sentencia'] or s['fecha_notificacion'] or '', s['id']))
    levels = {LVL.get(x['org'], 0) for x in ss if x['id'] not in dupset}
    for s in ss:
        s['vinculos'] = []
        for o, why in EVID.get(s['id'], []):
            if not any(v['id'] == o for v in s['vinculos']):
                s['vinculos'].append(dict(id=o, via=why))
        # instancias no incluidas
        no_incl = []
        for m in J['mentions'].get(s['id'], []):
            tn = deacc(m['tribunal'].lower())
            niv = 'Corte Suprema' if 'suprema' in tn else 'Corte de Apelaciones' if 'apelaciones' in tn else 'Primera instancia' if re.search(r'juzgado|arbitr|policia', tn) else {'JC':'Primera instancia','JPL':'Primera instancia','ARB':'Primera instancia','CA':'Corte de Apelaciones','CS':'Corte Suprema'}[m['tipo']]
            if niv == {'CS':'Corte Suprema','CA':'Corte de Apelaciones'}.get(s['org']) and s['org'] == 'CS': continue
            if {'Primera instancia':1,'Corte de Apelaciones':2,'Corte Suprema':3}[niv] >= LVL.get(s['org'], 0): continue  # solo instancias inferiores
            no_incl.append(dict(nivel=niv, tribunal=m['tribunal'], rol=m['rol'], fecha='', fuente='rol citado en el texto'))
        lm = lower_mention(s)
        need = {'Primera instancia': 1, 'Corte de Apelaciones': 2}.get(lm['nivel']) if lm else None
        if lm and need not in levels and not any(x['nivel'] == lm['nivel'] for x in no_incl):
            lm['rol'] = ''; lm['fuente'] = 'mencionada en el texto'; no_incl.append(lm)
        # no repetir menciones de niveles que sí están en el expediente con el mismo rol
        have_rols = set()
        for x in ss:
            for r in (x['rol'], x['rol_informado']):
                for mm in re.finditer(r'(\d{1,3}(?:\.\d{3})+|\d{1,7})\s*[-–/]\s*(\d{4})', r or ''): have_rols.add(f"{int(mm.group(1).replace('.',''))}-{mm.group(2)}")
        s['instancias_no_incluidas'] = [x for x in no_incl if x.get('rol') not in have_rols or not x.get('rol')]
        s['precedentes_citados'] = J['precedentes'].get(s['id'], [])
    # alerta de instancia superior posible
    only_first = levels == {1}
    for s in ss:
        s['alerta_superior'] = ''
        if only_first and s['org'] in ('JC','JPL','ARB') and s['id'] not in dupset:
            rc = s['resultado_cmf']; d = s['desenlace']
            contra = (d == 'Demanda acogida' and rc == 'Rechaza demanda') or (d == 'Demanda rechazada' and rc.startswith('Acoge')) or (d == 'Demanda acogida parcialmente' and rc == 'Rechaza demanda')
            if contra: s['alerta_superior'] = f"Esta sentencia aparece como «{d}» (clasificación automática), pero el resultado final informado a la CMF es «{rc}». O fue modificada en una instancia superior que no está en la colección, o la clasificación automática se equivocó: revisa la parte resolutiva."
            elif s['estado'] == 'No Ejecutoriada': s['alerta_superior'] = 'Sentencia no ejecutoriada: puede haber recursos pendientes o resueltos en una instancia superior que no está en la colección.'
# ramo a nivel de expediente
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proc.py')).read()
exec(src.split('# ---------------------------------------------------------------- ramos')[1].split('# ---------------------------------------------------------------- temas')[0])
for k, ss in by_exp.items():
    mats = ' | '.join(sorted(set(x['materia'] for x in ss if x['materia'])))
    ramo, ramo2 = clasif_ramo(mats, '\n'.join(x['texto'] for x in ss), ss[0]['tipo_seguro'])
    for x in ss: x['ramo'] = ramo; x['ramos_sec'] = ramo2
for c, ids in bycm.items():
    if c in hetero: continue
    und = [i for i in ids if D[i]['ramo'].startswith('Otros')]
    if und:
        ss = [D[i] for i in ids]
        mats = ' | '.join(sorted(set(x['materia'] for x in ss if x['materia'])))
        ramo, ramo2 = clasif_ramo(mats, '\n'.join(x['texto'] for x in ss), ss[0]['tipo_seguro'])
        for i in und: D[i]['ramo'] = ramo; D[i]['ramos_sec'] = ramo2
for s in S:
    s['duplicado_de'] = s.get('duplicado_de', '')
    exp = by_exp[s['expediente']]
    lv = sorted({LVL.get(x['org'], 0) for x in exp if not x.get('duplicado_de')})
    s['n_instancias'] = len([x for x in exp if not x.get('duplicado_de')])
    s['cobertura'] = ('Varias instancias en la colección' if len(lv) > 1 else 'Una sola instancia en la colección')
    top = [x for x in exp if not x.get('duplicado_de')] or exp
    s['resultado_expediente'] = sorted(top, key=lambda x: (LVL.get(x['org'],0), x['fecha_sentencia'] or x['fecha_notificacion'] or ''))[-1]['resultado_cmf']
    s['cmf_heterogeneo'] = s['causa'] in hetero
json.dump(S, open('sentencias_proc.json', 'w'), ensure_ascii=False)
c = collections.Counter()
for s in S:
    if s['instancias_no_incluidas']: c['con instancias no incluidas'] += 1
    if s['alerta_superior'].startswith('Esta'): c['contradice CMF'] += 1
    elif s['alerta_superior']: c['no ejecutoriada'] += 1
    if s['vinculos']: c['con vinculos'] += 1
    if s['duplicado_de']: c['duplicados'] += 1
    if s['precedentes_citados']: c['citan precedentes'] += 1
print(c, collections.Counter(s['cobertura'] for s in S))
for s in S:
    if s['instancias_no_incluidas'] and s['org']=='CA':
        print(s['id'], s['instancias_no_incluidas'][:1]); break


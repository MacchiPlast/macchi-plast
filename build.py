#!/usr/bin/env python3
"""
build.py — Macchi Plast
Legge il CSV da Notion, applica tutte le correzioni,
e genera il file docs/index.html pronto per GitHub Pages.
"""

import pandas as pd
import re
import json
import statistics
import numpy as np
from collections import defaultdict, Counter
from datetime import date
import os

# ── Percorsi ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'data', 'ordini.csv')
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.html')
OUT_DIR = os.path.join(BASE_DIR, 'docs')
OUT_PATH = os.path.join(OUT_DIR, 'index.html')

os.makedirs(OUT_DIR, exist_ok=True)

# ── Carica configurazione ────────────────────────────────────────────────────
with open(CONFIG_PATH, encoding='utf-8') as f:
    CFG = json.load(f)

# ── Leggi CSV ────────────────────────────────────────────────────────────────
print(f"Lettura CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, sep=None, engine='python')
df.columns = [c.lstrip('\ufeff') for c in df.columns]
print(f"  Righe: {len(df)}")

# ── Funzioni di pulizia ──────────────────────────────────────────────────────
def clean(val):
    if pd.isna(val): return None
    return re.sub(r'\s*\(https://[^\)]+\)', '', str(val)).strip()

def parse_date(val):
    if pd.isna(val): return None
    val = re.sub(r'\s*\(GMT[^\)]+\)', '', str(val)).strip()
    try: return pd.to_datetime(val).strftime('%d/%m/%Y')
    except: return None

def parse_ore(val):
    if pd.isna(val): return None
    m = re.search(r'(-?\d+)\s*giorni?\s*(\d+)\s*ore?\s*(\d+)\s*minut', str(val))
    if m:
        g, h, mn = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return round(g*24 + h + mn/60, 2)
    return None

# ── Pulizia dati ─────────────────────────────────────────────────────────────
df['Articolo'] = df['Articolo'].apply(clean)
df['Pressa']   = df['Pressa'].apply(clean)
df['Criticità'] = df['Criticità'].apply(clean)

# Rinomina articoli
for old, new in CFG['articolo_rinominato'].items():
    df.loc[df['Articolo'] == old, 'Articolo'] = new

# Correzioni pesi
for art, regola in CFG['correzioni_peso'].items():
    mask = (df['Articolo'] == art) & (df['Peso medio'] > regola['max_valido'])
    if regola['sostituisci_con'] is not None:
        df.loc[mask, 'Peso medio'] = regola['sostituisci_con']
    else:
        df.loc[mask, 'Peso medio'] = np.nan

# Correzioni clienti
for prefisso, cliente in CFG['cliente_per_prefisso'].items():
    if prefisso.endswith('A') or len(prefisso) > 4:
        df.loc[df['Articolo'] == prefisso, 'Cliente'] = cliente
    else:
        df.loc[df['Articolo'].str.startswith(prefisso, na=False), 'Cliente'] = cliente

# ── Costruisci lista ODL ─────────────────────────────────────────────────────
odl_list = []
for _, row in df.iterrows():
    odl_list.append({
        'odl':        str(row['ODL']) if pd.notna(row['ODL']) else '',
        'articolo':   row['Articolo'],
        'cliente':    str(row['Cliente']) if pd.notna(row['Cliente']) else None,
        'pressa':     row['Pressa'],
        'data_inizio': parse_date(row['Data di Inizio']),
        'data_fine':   parse_date(row['Data di Fine']),
        'pezzi':      int(row['Pezzi da produrre']) if pd.notna(row['Pezzi da produrre']) else None,
        'kg':         round(float(row['Kg da utilizzare']), 2) if pd.notna(row['Kg da utilizzare']) else None,
        'ore':        parse_ore(row['Ore di Produzione']),
        'peso_medio': round(float(row['Peso medio']), 4) if pd.notna(row['Peso medio']) else None,
        'criticita':  row['Criticità'],
        'materiale':  str(row['Materiale']) if pd.notna(row['Materiale']) else None,
        'lotto':      str(row['Lotto Materiale']) if pd.notna(row['Lotto Materiale']) else None,
    })

# ── Calcola soglie ore mediane ───────────────────────────────────────────────
ore_per_art = defaultdict(list)
for o in odl_list:
    if o['ore'] and o['ore'] > 0:
        ore_per_art[o['articolo']].append(o['ore'])
soglie = {art: round(statistics.median(vals), 2) for art, vals in ore_per_art.items()}

# ── Calcola ore per pezzo mediana ────────────────────────────────────────────
orePP = defaultdict(list)
for o in odl_list:
    if o['ore'] and o['ore'] > 0 and o['pezzi'] and o['pezzi'] > 0:
        orePP[o['articolo']].append(o['ore'] / o['pezzi'])
orepp_med = {}
for art, vals in orePP.items():
    vals.sort(); mid = len(vals) // 2
    orepp_med[art] = vals[mid] if len(vals) % 2 else (vals[mid-1] + vals[mid]) / 2

# ── Calcola affidabilità pressa ──────────────────────────────────────────────
eq = CFG['presse_equivalenti']
def norm_pressa(p):
    if not p or not isinstance(p, str): return p
    return eq.get(p.strip(), p.strip())

presse_art = defaultdict(list)
for o in odl_list:
    if o['articolo'] and o['pressa'] and isinstance(o['pressa'], str):
        presse_art[o['articolo']].append(norm_pressa(o['pressa']))

aff = {}
for art, presse in presse_art.items():
    cnt = Counter(presse)
    top = cnt.most_common(1)[0]
    pct = round(top[1] / len(presse) * 100, 1)
    aff[art] = {'pct': pct, 'n': len(presse), 'n_presse': len(cnt)}

# ── Serializza JSON ──────────────────────────────────────────────────────────
def jdump(obj):
    return json.dumps(obj, ensure_ascii=True, separators=(',', ':'))

ODL_JSON       = jdump(odl_list)
SOGLIE_JSON    = jdump(soglie)
OREPP_JSON     = jdump(orepp_med)
AFF_JSON       = jdump(aff)
LOOKUP_JSON    = jdump(CFG['lookup'])
STAMPI_JSON    = jdump(CFG['scaffali'])
STAMPI_ART_JSON = jdump(CFG['stampi_art'])
OVERRIDE_JSON  = jdump(CFG['override_pressa'])

# ── Info header ──────────────────────────────────────────────────────────────
n_ordini = len(odl_list)
oggi = date.today().strftime('%d/%m/%Y')
date_valide = [o['data_inizio'] for o in odl_list if o['data_inizio']]
ultima_data = max(date_valide) if date_valide else '?'

print(f"  ODL totali: {n_ordini}")
print(f"  Ultima data: {ultima_data}")
print(f"  Articoli unici: {len(set(o['articolo'] for o in odl_list if o['articolo']))}")

# ── Leggi template e sostituisci placeholder ─────────────────────────────────
with open(TEMPLATE_PATH, encoding='utf-8') as f:
    html = f.read()

html = html.replace('%%ODL%%',        ODL_JSON)
html = html.replace('%%SOGLIE%%',     SOGLIE_JSON)
html = html.replace('%%OREPP%%',      OREPP_JSON)
html = html.replace('%%AFF%%',        AFF_JSON)
html = html.replace('%%LOOKUP%%',     LOOKUP_JSON)
html = html.replace('%%SCAFFALI%%',   STAMPI_JSON)
html = html.replace('%%STAMPIART%%',  STAMPI_ART_JSON)
html = html.replace('%%OVERRIDE%%',   OVERRIDE_JSON)
html = html.replace('%%N_ORDINI%%',   str(n_ordini))
html = html.replace('%%OGGI%%',       oggi)

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\nHTML generato: {OUT_PATH}")
print(f"Dimensione: {len(html):,} caratteri")

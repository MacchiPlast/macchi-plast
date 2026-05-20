#!/usr/bin/env python3
import pandas as pd
import re
import json
import os
from datetime import date

# ── Percorsi ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'data', 'ordini.csv')
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'template.html')
# Assicuriamoci che la cartella docs esista
OUT_DIR = os.path.join(BASE_DIR, 'docs')
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, 'index.html')

# ── Funzione di pulizia (Gestisce URL Notion e virgole) ──────────────────────
def clean_notion_field(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    # Rimuove l'URL tra parentesi
    cleaned = re.sub(r'\s\(https://.*?\)', '', str(val))
    return cleaned.strip()

# ── 1. Caricamento Dati ─────────────────────────────────────────────────────
print(f"Lettura CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, sep=None, engine='python', encoding='utf-8-sig')
df.columns = [c.lstrip('\ufeff') for c in df.columns]

# Pulizia colonne
for col in ['Articolo', 'Pressa']:
    if col in df.columns:
        df[col] = df[col].apply(clean_notion_field)

# ── 2. Caricamento Configurazione ───────────────────────────────────────────
with open(CONFIG_PATH, encoding='utf-8') as f:
    CFG = json.load(f)

# ── 3. Trasformazione dati (Placeholder per la tua logica) ───────────────────
# Qui puoi continuare a costruire i tuoi JSON per il template
odl_list = df.to_dict(orient='records')
# Esempio: ODL_JSON = json.dumps(odl_list, ensure_ascii=False)

# ── 4. Generazione Output ────────────────────────────────────────────────────
with open(TEMPLATE_PATH, encoding='utf-8') as f:
    html = f.read()

# Esempio di sostituzione (aggiungi le tue variabili qui)
# html = html.replace('%%ODL%%', ODL_JSON)

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Build completata! File creato in: {OUT_PATH}")

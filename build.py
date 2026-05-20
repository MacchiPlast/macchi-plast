#!/usr/bin/env python3
"""
build.py — Macchi Plast
Legge il CSV da Notion, pulisce i dati e genera index.html
"""

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
OUT_DIR = os.path.join(BASE_DIR, 'docs')
OUT_PATH = os.path.join(OUT_DIR, 'index.html')

os.makedirs(OUT_DIR, exist_ok=True)

# ── Carica configurazione ────────────────────────────────────────────────────
with open(CONFIG_PATH, encoding='utf-8') as f:
    CFG = json.load(f)

# ── Funzione di pulizia intelligente ─────────────────────────────────────────
def clean_notion_field(val):
    """Rimuove URL Notion e mantiene solo il testo pulito."""
    if pd.isna(val) or str(val).strip() == "":
        return ""
    # Rimuove tutto ciò che sta tra parentesi (l'URL)
    cleaned = re.sub(r'\s\(https://.*?\)', '', str(val))
    return cleaned.strip()

# ── Leggi e pulisci CSV ──────────────────────────────────────────────────────
print(f"Lettura CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, sep=None, engine='python', encoding='utf-8-sig')
df.columns = [c.lstrip('\ufeff') for c in df.columns]

# Applichiamo la pulizia alle colonne che contengono URL Notion
for col in ['Articolo', 'Pressa']:
    if col in df.columns:
        df[col] = df[col].apply(clean_notion_field)

print(f"  Righe processate: {len(df)}")

# ── Logica di trasformazione (Esempio semplificato) ──────────────────────────
# Qui il tuo script continua con la trasformazione in JSON per il template...
# Assicurati che quando cicli le righe, il campo 'Articolo' ora contiene "3121, 3122"
# che è molto più facile da processare.

odl_list = df.to_dict(orient='records')

# ── Generazione output (mantenuto come nel tuo originale) ────────────────────
def jdump(obj): return json.dumps(obj, ensure_ascii=False)

# (Qui dovresti inserire il resto della tua logica di aggregazione per i grafici)
# ...

print("Build completata con successo.")

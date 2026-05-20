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
OUT_DIR = os.path.join(BASE_DIR, 'docs')
OUT_PATH = os.path.join(OUT_DIR, 'index.html')

os.makedirs(OUT_DIR, exist_ok=True)

# ── Carica configurazione ────────────────────────────────────────────────────
with open(CONFIG_PATH, encoding='utf-8') as f:
    CFG = json.load(f)

# ── Funzioni di Pulizia ──────────────────────────────────────────────────────
def clean_notion_field(val):
    """Rimuove URL Notion (es. https://...) e spazi extra."""
    if pd.isna(val) or str(val).strip() == "":
        return ""
    # Rimuove tutto ciò che sta tra parentesi (l'URL di Notion)
    cleaned = re.sub(r'\s\(https://.*?\)', '', str(val))
    return cleaned.strip()

# ── Leggi e pulisci CSV ──────────────────────────────────────────────────────
print(f"Lettura CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, sep=None, engine='python', encoding='utf-8-sig')
# Rimuove eventuali caratteri invisibili BOM dal CSV
df.columns = [c.lstrip('\ufeff') for c in df.columns]

# Applichiamo la pulizia alle colonne Articolo e Pressa
for col in ['Articolo', 'Pressa']:
    if col in df.columns:
        df[col] = df[col].apply(clean_notion_field)

print(f"  Righe processate: {len(df)}")

# ── Trasformazione Dati per il Template ──────────────────────────────────────
# Convertiamo il dataframe in una lista di dizionari per il frontend
odl_list = df.to_dict(orient='records')
ODL_JSON = json.dumps(odl_list, ensure_ascii=False)

# ── Lettura Template e Iniezione Dati ────────────────────────────────────────
with open(TEMPLATE_PATH, encoding='utf-8') as f:
    html = f.read()

# Sostituzione dei segnaposto nel template
# Assicurati che nel tuo template.html ci sia la stringa "%%ODL%%"
html = html.replace('%%ODL%%', ODL_JSON)

# Salvataggio file finale
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Build completata con successo in: {OUT_PATH}")

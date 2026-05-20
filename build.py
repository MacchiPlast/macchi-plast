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
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, 'index.html')

# ── Caricamento Configurazione ─────────────────────────────────────────────
with open(CONFIG_PATH, encoding='utf-8') as f:
    CFG = json.load(f)

# ── Funzioni di Pulizia e Match ───────────────────────────────────────────
def clean_notion_field(val):
    """Rimuove URL Notion e pulisce la stringa."""
    if pd.isna(val) or str(val).strip() == "": return ""
    # Rimuove tutto tra parentesi (l'URL di Notion)
    cleaned = re.sub(r'\s\(https://.*?\)', '', str(val))
    return cleaned.strip()

def get_stampo_info(articoli_str):
    """Cerca lo stampo basandosi sulla stringa pulita dell'articolo."""
    if not articoli_str: return "N/D", "N/D"
    # Gestisce più articoli separati da virgola
    lista_art = [a.strip() for a in articoli_str.split(',')]
    for art in lista_art:
        if art in CFG.get('stampi_art', {}):
            info = CFG['stampi_art'][art]
            return info.get('stampo', 'N/D'), info.get('pos', 'N/D')
    return "Non trovato", "N/D"

# ── 1. Elaborazione Dati ──────────────────────────────────────────────────
print(f"Lettura CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, sep=None, engine='python', encoding='utf-8-sig')
df.columns = [c.lstrip('\ufeff') for c in df.columns]

# Pulizia colonne critiche
for col in ['Articolo', 'Pressa']:
    if col in df.columns:
        df[col] = df[col].apply(clean_notion_field)

# ── 2. Arricchimento dati ────────────────────────────────────────────────
# Aggiungiamo le info stampo/pos basandoci sul config.json
df[['stampo_info', 'pos_info']] = df['Articolo'].apply(
    lambda x: pd.Series(get_stampo_info(x))
)

# ── 3. Generazione Output ──────────────────────────────────────────────────
# (Qui la tua logica originale per popolare i template JSON)
odl_list = df.to_dict(orient='records')
# ... (inserisci qui la tua logica di conversione JSON per i grafici) ...

with open(TEMPLATE_PATH, encoding='utf-8') as f:
    html = f.read()

# Placeholder (Esempio: sostituisci le tue variabili)
# html = html.replace('%%ODL%%', json.dumps(odl_list, ensure_ascii=False))

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Build completata con successo in {OUT_PATH}")

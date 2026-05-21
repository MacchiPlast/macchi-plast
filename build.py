#!/usr/bin/env python3
import pandas as pd
import re
import json
import os
from datetime import datetime

# ── Percorsi ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATHS = {
    "csv": os.path.join(BASE_DIR, 'data', 'ordini.csv'),
    "config": os.path.join(BASE_DIR, 'config.json'),
    "out_dir": os.path.join(BASE_DIR, 'docs'),
    "data_json": os.path.join(BASE_DIR, 'docs', 'data.json')
}

os.makedirs(PATHS["out_dir"], exist_ok=True)

# ── Funzioni di Supporto ──────────────────────────────────────────────────────
def parse_ore(val):
    if not isinstance(val, str): return 0.0
    try:
        giorni = float(re.search(r'(\d+)\s+giorni', val).group(1)) if 'giorni' in val else 0
        ore = float(re.search(r'(\d+)\s+ore', val).group(1)) if 'ore' in val else 0
        minuti = float(re.search(r'(\d+)\s+minuti', val).group(1)) if 'minuti' in val else 0
        return (giorni * 24) + ore + (minuti / 60)
    except: return 0.0

def normalize(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', str(text).replace("\u200b", "").replace("\ufeff", "").upper().strip())

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    try:
        # Caricamento
        with open(PATHS["config"], encoding='utf-8') as f: cfg = json.load(f)
        df = pd.read_csv(PATHS["csv"], sep=None, engine='python', encoding='utf-8-sig')
        df.columns = [c.lstrip('\ufeff') for c in df.columns]

        # Preparazione Dati
        odl = []
        for _, row in df.iterrows():
            # Conversione ore
            ore_num = parse_ore(row.get('Ore di Produzione', ''))
            
            odl.append({
                "ODL": str(row.get('ODL', '')).strip(),
                "Articolo": str(row.get('Articolo', '')).strip(),
                "Cliente": str(row.get('Cliente', '')).strip(),
                "Pressa": str(row.get('Pressa', '')).strip(),
                "Data_Inizio": str(row.get('Data di Inizio', '')).strip(),
                "Data_Fine": str(row.get('Data di Fine', '')).strip(),
                "Pezzi": int(row.get('Pezzi da produrre', 0)) if pd.notna(row.get('Pezzi da produrre')) else 0,
                "Kg": float(row.get('Kg da utilizzare', 0)) if pd.notna(row.get('Kg da utilizzare')) else 0.0,
                "Ore": float(ore_num),
                "Materiale": str(row.get('Materiale', '')).strip(),
                "Criticita": str(row.get('Criticità', '')).strip()
            })
        
        # Struttura finale JSON
        data = {
            "odl": odl,
            "scaffali": cfg.get('scaffali', {}),
            "meta": {"generated": datetime.now().isoformat()}
        }
        
        # Salvataggio
        with open(PATHS["data_json"], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"🚀 Build completata con successo in {PATHS['data_json']}")
        
    except Exception as e:
        print(f"💥 ERRORE durante il build: {e}")

if __name__ == "__main__":
    main()
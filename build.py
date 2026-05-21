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

# ── PARSER ORE (Nuova funzione) ────────────────────────────────────────────────
def parse_ore(val):
    """Converte stringhe tipo '0 giorni 14 ore 35 minuti' in totale ore (float)"""
    if not isinstance(val, str): return 0.0
    try:
        # Estrae i numeri prima delle parole chiavi
        giorni = float(re.search(r'(\d+)\s+giorni', val).group(1)) if 'giorni' in val else 0
        ore = float(re.search(r'(\d+)\s+ore', val).group(1)) if 'ore' in val else 0
        minuti = float(re.search(r'(\d+)\s+minuti', val).group(1)) if 'minuti' in val else 0
        return (giorni * 24) + ore + (minuti / 60)
    except:
        return 0.0

# ── NORMALIZZAZIONE ───────────────────────────────────────────────────────────
def normalize(text):
    if not text: return ""
    text = str(text).replace("\u200b", "").replace("\ufeff", "")
    text = text.replace("–", "-").replace("—", "-").upper().strip()
    return re.sub(r'\s+', ' ', text)

# ── PULIZIA NOTION ────────────────────────────────────────────────────────────
def clean_notion_field(val):
    if pd.isna(val): return ""
    return re.sub(r'\s*\(https://.*?\)', '', str(val)).strip()

# ── BUILD LOOKUP ──────────────────────────────────────────────────────────────
def build_lookup(scaffali):
    lookup = {}
    for scaffale, articoli in scaffali.items():
        for art in articoli:
            art = art.strip()
            parts = art.split("/")
            expanded = []
            if len(parts) > 1:
                suffix_match = re.search(r'\s+(NEW|OLD|[A-Z]+)$', art)
                suffix = suffix_match.group(1) if suffix_match else ""
                for p in parts:
                    p = re.sub(r'\s*(NEW|OLD|[A-Z]+)$', '', p).strip()
                    expanded.append(f"{p} {suffix}".strip())
            else:
                expanded = [art]
            for item in expanded:
                key = normalize(item)
                lookup.setdefault(key, set()).add(scaffale)
    return {k: list(v) for k, v in lookup.items()}

# ── CSV LOADER ────────────────────────────────────────────────────────────────
def load_csv(path):
    if not os.path.exists(path): raise FileNotFoundError(f"CSV non trovato: {path}")
    print(f"📄 Lettura CSV: {path}")
    df = pd.read_csv(path, sep=None, engine='python', encoding='utf-8-sig')
    df.columns = [c.lstrip('\ufeff') for c in df.columns]
    
    # Pulizia colonne
    for col in ['Articolo', 'Pressa']:
        if col in df.columns: df[col] = df[col].apply(clean_notion_field)
    
    # Conversione ore in numerico
    if 'Ore di Produzione' in df.columns:
        df['Ore_Numeriche'] = df['Ore di Produzione'].apply(parse_ore)
    
    print(f"✅ Righe processate: {len(df)}")
    return df

# ── CALCOLA METRICHE ──────────────────────────────────────────────────────────
def calc_metrics(df):
    soglie = {}
    orepp = {}
    for articolo in df['Articolo'].unique():
        subset = df[df['Articolo'] == articolo]
        
        # Soglia = mediana ore numeriche
        ore_vals = subset['Ore_Numeriche']
        valid = ore_vals[ore_vals > 0]
        if not valid.empty:
            soglie[articolo] = float(valid.median())
        
        # Ore per pezzo
        valid_orepp = subset[(subset['Ore_Numeriche'] > 0) & (subset['Pezzi da produrre'] > 0)]
        if not valid_orepp.empty:
            orepp[articolo] = float(valid_orepp['Ore_Numeriche'].sum() / valid_orepp['Pezzi da produrre'].sum())
            
    return soglie, orepp

# ── CALCOLA AFFIDABILITA ──────────────────────────────────────────────────────
def calc_affidabilita(df):
    aff = {}
    for articolo in df['Articolo'].unique():
        subset = df[df['Articolo'] == articolo]
        n = len(subset)
        if n < 1: continue
        pressa_prin = subset['Pressa'].mode()
        if len(pressa_prin) > 0:
            n_stessa = len(subset[subset['Pressa'] == pressa_prin[0]])
            aff[articolo] = {"pct": round((n_stessa / n) * 100, 1), "n": n, "n_presse": len(subset['Pressa'].unique())}
    return aff

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    try:
        with open(PATHS["config"], encoding='utf-8') as f: cfg = json.load(f)
        df = load_csv(PATHS["csv"])
        lookup = build_lookup(cfg.get('scaffali', {}))
        soglie, orepp = calc_metrics(df)
        aff = calc_affidabilita(df)
        
        odl = []
        for _, row in df.iterrows():
            odl.append({
                "odl": str(row.get('ODL', '')).strip(),
                "articolo": str(row.get('Articolo', '')).strip(),
                "pezzi": int(row.get('Pezzi da produrre', 0)) if pd.notna(row.get('Pezzi da produrre')) else 0,
                "ore": float(row.get('Ore_Numeriche', 0)),
                "pressa": str(row.get('Pressa', '')).strip()
            })
        
        data = {"odl": odl, "lookup": lookup, "soglie": soglie, "orepp": orepp, "aff": aff, "meta": {"generated": datetime.now().isoformat()}}
        with open(PATHS["data_json"], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"🚀 Build completata! File salvato in {PATHS['data_json']}")
        
    except Exception as e:
        print(f"💥 ERRORE: {e}")

if __name__ == "__main__":
    main()
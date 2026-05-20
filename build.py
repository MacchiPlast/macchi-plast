#!/usr/bin/env python3
import pandas as pd
import re
import json
import os
from collections import defaultdict

# ── Percorsi ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "csv": os.path.join(BASE_DIR, 'data', 'ordini.csv'),
    "config": os.path.join(BASE_DIR, 'config.json'),
    "out_dir": os.path.join(BASE_DIR, 'docs'),
    "data_json": os.path.join(BASE_DIR, 'docs', 'data.json')
}

os.makedirs(PATHS["out_dir"], exist_ok=True)


# ── NORMALIZZAZIONE ───────────────────────────────────────────────────────────
def normalize(text):
    if not text:
        return ""
    text = str(text)
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = text.replace("–", "-").replace("—", "-")
    text = text.upper().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


# ── PULIZIA NOTION ────────────────────────────────────────────────────────────
def clean_notion_field(val):
    if pd.isna(val):
        return ""
    val = str(val)
    val = re.sub(r'\s*\(https://.*?\)', '', val)
    return val.strip()


# ── BUILD LOOKUP ──────────────────────────────────────────────────────────────
def build_lookup(scaffali):
    lookup = {}
    for scaffale, articoli in scaffali.items():
        for art in articoli:
            art = art.strip()
            parts = art.split("/")
            expanded = []
            
            if len(parts) > 1:
                # Estrai suffisso SOLO se è preceduto da spazio
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
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV non trovato: {path}")
    
    print(f"Lettura CSV: {path}")
    df = pd.read_csv(path, sep=None, engine='python', encoding='utf-8-sig')
    df.columns = [c.lstrip('\ufeff') for c in df.columns]
    
    for col in ['Articolo', 'Pressa']:
        if col in df.columns:
            df[col] = df[col].apply(clean_notion_field)
    
    print(f"Righe processate: {len(df)}")
    return df


# ── CALCOLA SOGLIE E ORE ──────────────────────────────────────────────────────
def calc_metrics(df):
    soglie = {}
    orepp = {}
    
    for articolo in df['Articolo'].unique():
        subset = df[df['Articolo'] == articolo]
        
        # Soglia = mediana ore
        ore_vals = subset['Ore di Produzione'].dropna()
        if len(ore_vals) > 0:
            soglie[articolo] = float(ore_vals.median())
        
        # Ore per pezzo
        valid = subset[(subset['Ore di Produzione'].notna()) & (subset['Pezzi da produrre'] > 0)]
        if len(valid) > 0:
            orepp[articolo] = float((valid['Ore di Produzione'].sum() / valid['Pezzi da produrre'].sum()))
    
    return soglie, orepp


# ── CALCOLA AFFIDABILITA ─────────────────────────────────────────────────────
def calc_affidabilita(df, soglie):
    aff = {}
    
    for articolo in df['Articolo'].unique():
        subset = df[df['Articolo'] == articolo]
        n = len(subset)
        
        if n < 1:
            continue
        
        presse = subset['Pressa'].unique()
        pressa_prin = subset['Pressa'].mode()
        if len(pressa_prin) > 0:
            pressa_prin = pressa_prin[0]
            n_stessa = len(subset[subset['Pressa'] == pressa_prin])
            pct = (n_stessa / n) * 100 if n > 0 else 0
            
            aff[articolo] = {
                "pct": round(pct, 1),
                "n": n,
                "n_presse": len(presse)
            }
    
    return aff


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    try:
        # Carica config
        with open(PATHS["config"], encoding='utf-8') as f:
            cfg = json.load(f)
        
        # Carica CSV
        df = load_csv(PATHS["csv"])
        
        # Build lookup
        lookup = build_lookup(cfg.get('scaffali', {}))
        
        # Calcola metriche
        soglie, orepp = calc_metrics(df)
        aff = calc_affidabilita(df, soglie)
        
        # Prepara ODL records
        odl = []
        for _, row in df.iterrows():
            odl.append({
                "odl": str(row.get('ODL', '')),
                "articolo": str(row.get('Articolo', '')),
                "cliente": str(row.get('Cliente', '')),
                "pressa": str(row.get('Pressa', '')),
                "data_inizio": str(row.get('Data di Inizio', '')),
                "data_fine": str(row.get('Data di Fine', '')),
                "pezzi": int(row.get('Pezzi da produrre', 0)) if pd.notna(row.get('Pezzi da produrre')) else 0,
                "kg": float(row.get('Kg da utilizzare', 0)) if pd.notna(row.get('Kg da utilizzare')) else 0,
                "ore": float(row.get('Ore di Produzione', 0)) if pd.notna(row.get('Ore di Produzione')) else 0,
                "peso_medio": float(row.get('Peso medio', 0)) if pd.notna(row.get('Peso medio')) else 0,
                "materiale": str(row.get('Materiale', '')),
                "lotto": str(row.get('Lotto Materiale', '')),
                "criticita": str(row.get('Criticità', '')) if pd.notna(row.get('Criticità')) else ""
            })
        
        # Prepara data.json
        data = {
            "odl": odl,
            "lookup": lookup,
            "soglie": soglie,
            "orepp": orepp,
            "aff": aff,
            "scaffali": cfg.get('scaffali', {}),
            "meta": {
                "generated": pd.Timestamp.now().isoformat(),
                "total_ordini": len(odl),
                "total_articoli": len(lookup)
            }
        }
        
        # Scrivi data.json
        with open(PATHS["data_json"], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Build completata: {PATHS['data_json']}")
        print(f"- {len(odl)} ordini")
        print(f"- {len(lookup)} articoli")
        
    except Exception as e:
        print(f"ERRORE: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

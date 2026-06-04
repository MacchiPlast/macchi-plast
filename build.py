#!/usr/bin/env python3
"""
Build script per Macchi Plast - Storico ODL
Legge ordini.csv e genera data.json per index.html
Mantiene compatibilità con il dataset originale
"""
import pandas as pd
import re
import json
import os
from datetime import datetime

# ── Percorsi ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATHS = {
    "csv": os.path.join(BASE_DIR, 'data', 'ordini.csv'),  # ← Cerca in data/
    "config": os.path.join(BASE_DIR, 'config.json'),
    "out_dir": os.path.join(BASE_DIR),
    "data_json": os.path.join(BASE_DIR, 'data.json')
}

os.makedirs(PATHS["out_dir"], exist_ok=True)

# ── Funzioni di Supporto ──────────────────────────────────────────────────────
def parse_ore(val):
    """Converte stringhe tipo '3 giorni 2 ore 30 minuti' in ore decimali"""
    if not isinstance(val, str): 
        return 0.0
    try:
        giorni = float(re.search(r'(\d+)\s+giorni', val).group(1)) if 'giorni' in val else 0
        ore = float(re.search(r'(\d+)\s+ore', val).group(1)) if 'ore' in val else 0
        minuti = float(re.search(r'(\d+)\s+minuti', val).group(1)) if 'minuti' in val else 0
        return (giorni * 24) + ore + (minuti / 60)
    except: 
        return 0.0

def normalize(text):
    """Normalizza il testo (maiuscolo, spazi, caratteri invisibili)"""
    if not text: 
        return ""
    return re.sub(r'\s+', ' ', str(text).replace("\u200b", "").replace("\ufeff", "").upper().strip())

def _float(val):
    """Converte a float in sicurezza"""
    try:
        if pd.isna(val): return 0.0
        s = str(val).replace(',', '.')
        return float(s)
    except:
        return 0.0

def _int(val):
    """Converte a int in sicurezza"""
    try:
        if pd.isna(val): return 0
        return int(float(str(val).replace(',', '.')))
    except:
        return 0

def clean_articolo(art):
    """Rimuove link Notion dall'articolo"""
    if not isinstance(art, str):
        return str(art).strip()
    # Rimuove URL Notion se presenti
    art = re.sub(r'\s*\(https://app\.notion\.com/[^)]+\)', '', art)
    # Rimuove spazi extra
    art = re.sub(r'\s+', ' ', art).strip()
    return art

def clean_pressa(pressa):
    """Rimuove link Notion dalla pressa"""
    if not isinstance(pressa, str):
        return str(pressa).strip()
    # Rimuove URL Notion se presenti
    pressa = re.sub(r'\s*\(https://app\.notion\.com/[^)]+\)', '', pressa)
    # Rimuove spazi extra
    pressa = re.sub(r'\s+', ' ', pressa).strip()
    return pressa

def parse_date(date_str):
    """
    Converte date da formati diversi a dd/mm/yyyy
    Accetta:
    - "March 25, 2026 17:45 (GMT+1)"
    - "January 8, 2026 1:35 (GMT+1)"
    - Formato riconosciuto da datetime
    """
    if not date_str or pd.isna(date_str):
        return ""
    
    date_str = str(date_str).strip()
    
    # Rimuovi la parte (GMT+X)
    date_str = re.sub(r'\s*\(GMT[^)]*\).*$', '', date_str)
    date_str = date_str.strip()
    
    # Mappa mesi inglesi
    mesi_en = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07',
        'august': '08', 'september': '09', 'october': '10',
        'november': '11', 'december': '12'
    }
    
    # Prova a parsare il formato "Month Day, Year Time"
    match = re.match(r'(\w+)\s+(\d{1,2}),\s+(\d{4})', date_str)
    if match:
        mese_nome, giorno, anno = match.groups()
        mese_num = mesi_en.get(mese_nome.lower(), '')
        if mese_num:
            return f"{int(giorno):02d}/{mese_num}/{anno}"
    
    # Se niente funziona, restituisci la stringa originale
    return date_str

# ── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("🚀 Inizio build Macchi Plast...")
    
    try:
        # Caricamento config.json (contiene la mappa scaffali)
        config = {}
        if os.path.exists(PATHS["config"]):
            with open(PATHS["config"], encoding='utf-8') as f:
                config = json.load(f)
                print(f"✓ Config caricata ({len(config.get('scaffali', {}))} scaffali)")

        # Caricamento CSV
        print(f"📄 Leggo CSV: {PATHS['csv']}")
        df = pd.read_csv(PATHS["csv"], sep=None, engine='python', encoding='utf-8-sig')
        df.columns = [c.lstrip('\ufeff') for c in df.columns]
        print(f"✓ CSV caricato: {len(df)} righe")

        # Preparazione Dati
        odl_list = []
        db_articoli = {}  # Per calcolare medie
        
        for idx, row in df.iterrows():
            # Conversione ore
            ore_str = str(row.get('Ore di Produzione', '0')).strip()
            if ',' in ore_str:
                ore_num = _float(ore_str.replace(',', '.'))
            else:
                ore_num = parse_ore(ore_str)
            
            # Pulizia articolo (rimuove URL Notion)
            articolo_raw = clean_articolo(row.get('Articolo', ''))
            
            # Gestisci articoli multipli (divisi da virgola, non da URL)
            # Es: "3121, 3122" → ["3121", "3122"]
            articoli_list = [a.strip() for a in articolo_raw.split(',') if a.strip()]
            if not articoli_list:
                articoli_list = [articolo_raw] if articolo_raw else []
            
            pezzi = _int(row.get('Pezzi da produrre', 0))
            peso_medio = _float(row.get('Peso medio', 0))
            kg = _float(row.get('Kg da utilizzare', 0))
            
            # Converti date a dd/mm/yyyy
            data_inizio_raw = str(row.get('Data di Inizio', '')).strip()
            data_fine_raw = str(row.get('Data di Fine', '')).strip()
            data_inizio = parse_date(data_inizio_raw)
            data_fine = parse_date(data_fine_raw)
            
            # Crea un ordine per OGNI articolo della lista
            for articolo in articoli_list:
                if not articolo:
                    continue
                
                odl_obj = {
                    "odl": str(row.get('ODL', '')).strip(),
                    "articolo": articolo,
                    "cliente": str(row.get('Cliente', '')).strip(),
                    "pressa": clean_pressa(row.get('Pressa', '')),
                    "data_inizio": data_inizio,
                    "data_fine": data_fine,
                    "pezzi": pezzi,
                    "kg": kg,
                    "ore": float(ore_num),
                    "materiale": str(row.get('Materiale', '')).strip(),
                    "lotto": str(row.get('Lotto Materiale', '')).strip(),
                    "criticita": str(row.get('Criticità', '')).strip(),
                    "peso_medio": peso_medio
                }
                
                odl_list.append(odl_obj)
                
                # Accumula dati per articolo
                if articolo:
                    if articolo not in db_articoli:
                        db_articoli[articolo] = {
                            'ordini': [],
                            'ore_tot': 0,
                            'pezzi_tot': 0,
                            'n': 0,
                            'presse': set()
                        }
                    db_articoli[articolo]['n'] += 1
                    db_articoli[articolo]['ore_tot'] += ore_num
                    db_articoli[articolo]['pezzi_tot'] += pezzi
                    db_articoli[articolo]['ordini'].append(odl_obj)
                    if odl_obj['pressa']:
                        db_articoli[articolo]['presse'].add(odl_obj['pressa'])

        # Calcola soglie e ore/pezzo per articolo
        soglie = {}      # ore mediane per articolo
        orepp = {}       # ore per pezzo per articolo
        
        for art, data in db_articoli.items():
            ordini = data['ordini']
            
            # Soglia = mediana ore (percentile 50)
            if ordini:
                ore_list = sorted([o['ore'] for o in ordini])
                soglie[art] = ore_list[len(ore_list)//2]
            
            # Ore per pezzo = media ore / pezzi
            if data['pezzi_tot'] > 0:
                orepp[art] = data['ore_tot'] / data['pezzi_tot']
        
        # Genera lookup: articolo → scaffale + nome (da config.json)
        lookup = {}
        unmapped_articles = []
        
        for scaffale, articoli_in_scaffale in config.get('scaffali', {}).items():
            for art_obj in articoli_in_scaffale:
                # Supporta sia formato vecchio (stringa) che nuovo (dict)
                if isinstance(art_obj, dict):
                    art_codice = art_obj.get('codice', '')
                    art_nome = art_obj.get('nome', '')
                else:
                    art_codice = art_obj
                    art_nome = ''
                
                # Normalizza l'articolo per la ricerca
                art_key = normalize(art_codice)
                if art_key not in lookup:
                    lookup[art_key] = {'scaffale': scaffale, 'nome': art_nome}
        
        # Crea anche un lookup inverso per il matching fuzzy
        for art_csv in db_articoli.keys():
            art_csv_norm = normalize(art_csv)
            if art_csv_norm not in lookup:
                # Prova a trovare un match parziale
                found = False
                for art_config_norm in lookup.keys():
                    # Se uno contiene l'altro o hanno molto in comune
                    if art_csv_norm in art_config_norm or art_config_norm in art_csv_norm:
                        if art_csv_norm not in lookup:
                            lookup[art_csv_norm] = lookup[art_config_norm]
                        found = True
                        break
                
                if not found:
                    unmapped_articles.append(art_csv)
        
        if unmapped_articles:
            print(f"\n⚠️  Articoli non mappati ({len(unmapped_articles)}):")
            for art in unmapped_articles[:20]:  # Mostra i primi 20
                print(f"   - {art}")
            if len(unmapped_articles) > 20:
                print(f"   ... e altri {len(unmapped_articles) - 20}")
        
        # Genera aff: affidabilità pressa per articolo
        # Calcola: % di ordini sulla pressa più usata per quell'articolo
        aff = {}
        for art, data in db_articoli.items():
            ordini = data['ordini']
            if not ordini:
                continue
            
            # Conta ordini per pressa
            presse_count = {}
            for odl in ordini:
                pressa = odl['pressa']
                if pressa:
                    presse_count[pressa] = presse_count.get(pressa, 0) + 1
            
            if presse_count:
                # Pressa più usata
                pressa_top = max(presse_count, key=presse_count.get)
                n_top = presse_count[pressa_top]
                n_total = len(ordini)
                pct = (n_top / n_total * 100) if n_total > 0 else 0
                
                aff[art] = {
                    'pct': round(pct, 1),
                    'n': n_total,
                    'n_presse': len(presse_count)
                }
        
        # Struttura finale JSON (come richiesto dall'HTML originale)
        data = {
            "odl": odl_list,
            "scaffali": config.get('scaffali', {}),
            "lookup": lookup,      # Articoli → {scaffale, nome}
            "aff": aff,            # Affidabilità pressa per articolo
            "soglie": soglie,      # Soglie ore per articolo
            "orepp": orepp,        # Ore per pezzo per articolo
            "meta": {
                "generated": datetime.now().isoformat(),
                "total_ordini": len(odl_list),
                "total_articoli": len(db_articoli),
                "total_pezzi": sum(o['pezzi'] for o in odl_list),
                "total_ore": sum(o['ore'] for o in odl_list),
                "total_kg": sum(o['kg'] for o in odl_list),
                "unmapped_count": len(unmapped_articles)
            }
        }
        
        # Salvataggio JSON
        with open(PATHS["data_json"], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        size_kb = os.path.getsize(PATHS["data_json"]) / 1024
        print(f"✓ JSON salvato: {PATHS['data_json']} ({size_kb:.1f} KB)")
        print(f"\n📊 Riepilogo:")
        print(f"   • {len(odl_list)} ordini (ODL)")
        print(f"   • {len(db_articoli)} articoli unici")
        print(f"   • {len(lookup)} articoli mappati")
        print(f"   • {len(unmapped_articles)} articoli NON mappati")
        print(f"   • {data['meta']['total_pezzi']:,} pezzi totali")
        print(f"   • {data['meta']['total_ore']:,.1f} ore stimate")
        print(f"   • {data['meta']['total_kg']:,.1f} kg totali")
        print(f"\n✅ Build completato con successo!")
        
    except Exception as e:
        print(f"💥 ERRORE durante il build:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()

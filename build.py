#!/usr/bin/env python3
import pandas as pd
import re
import json
import os

# ── Percorsi ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATHS = {
    "csv": os.path.join(BASE_DIR, 'data', 'ordini.csv'),
    "config": os.path.join(BASE_DIR, 'config.json'),
    "template": os.path.join(BASE_DIR, 'template.html'),
    "out_dir": os.path.join(BASE_DIR, 'docs'),
    "out": os.path.join(BASE_DIR, 'docs', 'index.html')
}

os.makedirs(PATHS["out_dir"], exist_ok=True)

# ── Utility ──────────────────────────────────────────────────────────────────
def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Config non trovato: {path}")
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def normalize(text):
    """Normalizza stringhe per confronti robusti"""
    if not text:
        return ""
    text = str(text).upper().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def clean_notion_field(val):
    """Rimuove URL Notion e pulisce stringhe"""
    if pd.isna(val):
        return ""
    val = str(val)
    val = re.sub(r'\s*\(https://.*?\)', '', val)
    return val.strip()


# 🔥 BUILD LOOKUP INTELLIGENTE
def build_lookup(scaffali):
    """Costruisce lookup articolo -> scaffali con supporto '/'"""
    lookup = {}

    for scaffale, articoli in scaffali.items():
        for art in articoli:
            art = art.strip()

            parts = art.split("/")
            expanded = []

            if len(parts) > 1:
                # trova suffisso (NEW, OLD ecc)
                suffix_match = re.search(r'(NEW|OLD|[A-Z]+)$', art)
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


def load_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ CSV non trovato: {path}")

    print(f"📄 Lettura CSV: {path}")

    df = pd.read_csv(path, sep=None, engine='python', encoding='utf-8-sig')

    # rimuove BOM
    df.columns = [c.lstrip('\ufeff') for c in df.columns]

    for col in ['Articolo', 'Pressa']:
        if col in df.columns:
            df[col] = df[col].apply(clean_notion_field)

    print(f"✅ Righe processate: {len(df)}")
    return df


def enrich_with_scaffali(df, lookup):
    """Aggiunge colonna Scaffali"""

    def match_scaffali(articolo):
        key = normalize(articolo)
        return lookup.get(key, [])

    if "Articolo" in df.columns:
        df["Scaffali"] = df["Articolo"].apply(match_scaffali)
    else:
        print("⚠️ Colonna 'Articolo' non trovata")

    return df


def inject_template(template_path, output_path, data_json):
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"❌ Template non trovato: {template_path}")

    with open(template_path, encoding='utf-8') as f:
        html = f.read()

    html = html.replace('%%ODL%%', data_json)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"🚀 Build completata: {output_path}")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    try:
        # carica config
        cfg = load_json(PATHS["config"])

        # genera lookup dinamico
        lookup = build_lookup(cfg.get('scaffali', {}))

        # carica CSV
        df = load_csv(PATHS["csv"])

        # 🔥 arricchimento scaffali
        df = enrich_with_scaffali(df, lookup)

        # export JSON
        odl_list = df.to_dict(orient='records')
        odl_json = json.dumps(odl_list, ensure_ascii=False)

        # genera HTML
        inject_template(PATHS["template"], PATHS["out"], odl_json)

    except Exception as e:
        print(f"💥 ERRORE: {e}")


if __name__ == "__main__":
    main()

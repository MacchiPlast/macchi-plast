#!/usr/bin/env python3
import pandas as pd
import re
import json
import os

# ── Costanti Percorsi ────────────────────────────────────────────────────────
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
    if pd.isna(val):
        return ""
    val = str(val)
    val = re.sub(r'\s*\(https://.*?\)', '', val)
    return val.strip()


def build_lookup(scaffali):
    """Costruisce lookup articolo -> scaffali"""
    lookup = {}

    for scaffale, articoli in scaffali.items():
        for art in articoli:
            key = normalize(art)
            lookup.setdefault(key, set()).add(scaffale)

    # convert set → list
    return {k: list(v) for k, v in lookup.items()}


def load_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ CSV non trovato: {path}")

    print(f"📄 Lettura CSV: {path}")

    df = pd.read_csv(path, sep=None, engine='python', encoding='utf-8-sig')

    df.columns = [c.lstrip('\ufeff') for c in df.columns]

    for col in ['Articolo', 'Pressa']:
        if col in df.columns:
            df[col] = df[col].apply(clean_notion_field)

    print(f"✅ Righe processate: {len(df)}")
    return df


def enrich_with_scaffali(df, lookup):
    """Aggiunge colonna Scaffali basata su lookup"""

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
        cfg = load_json(PATHS["config"])

        # lookup dinamico
        lookup = build_lookup(cfg.get('scaffali', {}))

        df = load_csv(PATHS["csv"])

        # 🔥 QUI AVVIENE LA MAGIA
        df = enrich_with_scaffali(df, lookup)

        odl_list = df.to_dict(orient='records')
        odl_json = json.dumps(odl_list, ensure_ascii=False)

        inject_template(PATHS["template"], PATHS["out"], odl_json)

    except Exception as e:
        print(f"💥 ERRORE: {e}")


if __name__ == "__main__":
    main()

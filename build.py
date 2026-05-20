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


# ── NORMALIZZAZIONE ULTRA ROBUSTA ───────────────────────────────────────────
def normalize(text):
    if not text:
        return ""

    text = str(text)

    # rimuove caratteri invisibili (CRUCIALI)
    text = text.replace("\u200b", "")   # zero-width space
    text = text.replace("\ufeff", "")    # BOM

    # uniforma trattini (IMPORTANTISSIMO)
    text = text.replace("–", "-").replace("—", "-")

    text = text.upper().strip()
    text = re.sub(r'\s+', ' ', text)

    return text


# ── PULIZIA NOTION ──────────────────────────────────────────────────────────
def clean_notion_field(val):
    if pd.isna(val):
        return ""
    val = str(val)
    val = re.sub(r'\s*\(https://.*?\)', '', val)
    return val.strip()


# ── LOOKUP SCALA INDUSTRIALE ────────────────────────────────────────────────
def build_lookup(scaffali):
    lookup = {}

    for scaffale, articoli in scaffali.items():
        for art in articoli:
            art = art.strip()

            parts = art.split("/")
            expanded = []

            if len(parts) > 1:
                # estrai suffisso (NEW, OLD ecc)
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


# ── CSV LOADER ─────────────────────────────────────────────────────────────
def load_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ CSV non trovato: {path}")

    print(f"📄 Lettura CSV: {path}")

    df = pd.read_csv(path, sep=None, engine='python', encoding='utf-8-sig')

    # rimuove BOM colonne
    df.columns = [c.lstrip('\ufeff') for c in df.columns]

    for col in ['Articolo', 'Pressa']:
        if col in df.columns:
            df[col] = df[col].apply(clean_notion_field)

    print(f"✅ Righe processate: {len(df)}")
    return df


# ── ENRICH SCATOLE ──────────────────────────────────────────────────────────
def enrich_with_scaffali(df, lookup):

    def match_scaffali(articolo):
        key = normalize(articolo)

        # debug intelligente (solo se non trova match)
        if key not in lookup:
            print(f"⚠️ NON TROVATO: '{articolo}' -> '{key}'")

        return lookup.get(key, [])

    if "Articolo" in df.columns:
        df["Scaffali"] = df["Articolo"].apply(match_scaffali)
    else:
        print("⚠️ Colonna 'Articolo' non trovata")

    return df


# ── TEMPLATE INJECTION ──────────────────────────────────────────────────────
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
        # config
        with open(PATHS["config"], encoding='utf-8') as f:
            cfg = json.load(f)

        # lookup
        lookup = build_lookup(cfg.get('scaffali', {}))

        # csv
        df = load_csv(PATHS["csv"])

        # enrich
        df = enrich_with_scaffali(df, lookup)

        # json output
        odl_json = json.dumps(
            df.to_dict(orient='records'),
            ensure_ascii=False
        )

        # html build
        inject_template(PATHS["template"], PATHS["out"], odl_json)

    except Exception as e:
        print(f"💥 ERRORE: {e}")


if __name__ == "__main__":
    main()

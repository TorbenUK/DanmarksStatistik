# pip install requests pandas
import requests
import pandas as pd
from io import StringIO

BASE = "https://api.statbank.dk/v1"

def _guess_from_time_id(all_ids, year=2024):
    """Gæt start-id for tidsvariablen (år/kvartal/måned)."""
    if not all_ids:
        raise ValueError("Ingen tids-id'er fundet.")
    sample = all_ids[0]
    if "M" in sample:
        return f"{year}M01"
    if "K" in sample:   # dansk kvartal
        return f"{year}K1"
    if "Q" in sample:   # engelsk kvartal
        return f"{year}Q1"
    return f"{year}"    # årlig

def _pick_total_value(var):
    """Vælg 'i alt/total' for ikke-tids-variabler (ellers første værdi)."""
    candidates = []
    for val in var.get("values", []):
        vid = str(val.get("id", "")).lower()
        vtxt = str(val.get("text", "")).lower()
        if vid in {"*","tot","total","alle","ialt","i_alt","0"}:
            return val["id"]
        if any(t in vtxt for t in ["i alt","total","alle","industry, total","all sectors"]):
            candidates.append(val["id"])
    return candidates[0] if candidates else var["values"][0]["id"]

def _find_unit_var_and_yoy_id(variables, lang="da"):
    """
    Find 'Unit/Enhed'-variablen og ID'et for 'ændring ift. samme kvartal året før (pct.)'.
    Gør det robust ved at tjekke både variabel-id, variabel-tekst og værdiernes tekster.
    """
    # Måltekster for YoY-værdien (begge sprog)
    targets_da = [
        "ændring i forhold til samme kvartal året før",
        "samme kvartal året før",
        "pct.)",  # hjælper i praksis
    ]
    targets_en = [
        "percentage change compared to the same quarter last year",
        "same quarter last year",
    ]
    yoy_targets = targets_da if (lang or "da").startswith("da") else targets_en

    # 1) Forsøg: find variabel med id/text = enhed/unit
    for var in variables:
        code = str(var.get("id","")).lower()
        text = str(var.get("text","")).lower()
        if code in {"enhed","unit"} or text in {"enhed","unit"}:
            for val in var.get("values", []):
                vtxt = str(val.get("text","")).lower()
                if any(t in vtxt for t in yoy_targets):
                    return var, val["id"]

    # 2) Fallback: gennemsøg alle variable for en værdi, der ligner YoY-teksten
    for var in variables:
        for val in var.get("values", []):
            vtxt = str(val.get("text","")).lower()
            if any(t in vtxt for t in yoy_targets):
                return var, val["id"]

    raise ValueError("Kunne ikke finde 'Unit/Enhed' med YoY-procent i metadata.")

def fetch_sblon1_yoy_pct_from_2024(lang: str = "da") -> pd.DataFrame:
    """
    Hent SBLON1: 'Ændring i forhold til samme kvartal året før (pct.)' fra og med 2024.
    Vælger 'i alt/total' for andre dimensioner for et kompakt udtræk.
    """
    # 1) Metadata
    meta_resp = requests.get(
        f"{BASE}/tableinfo/SBLON1",
        params={"contentType": "JSON", "lang": lang},
        timeout=30,
    )
    meta_resp.raise_for_status()
    meta = meta_resp.json()
    variables = meta["variables"]

    # 2) Find tidsvariabel og perioder fra 2024+
    time_var = next(v for v in variables if v.get("time"))
    time_code = time_var["id"]
    all_time_ids = [v["id"] for v in time_var["values"]]
    from_id = _guess_from_time_id(all_time_ids, 2024)
    sel_time_ids = [t for t in all_time_ids if t >= from_id]
    if not sel_time_ids:
        raise ValueError(f"Ingen perioder fundet fra og med {from_id}.")

    # 3) Find Unit/Enhed og YoY-id
    unit_var, yoy_id = _find_unit_var_and_yoy_id(variables, lang=lang)

    # 4) Byg payload
    payload_vars = []
    for var in variables:
        code = var["id"]
        if var.get("time"):
            payload_vars.append({"code": code, "values": sel_time_ids})
        elif code == unit_var["id"]:
            payload_vars.append({"code": code, "values": [yoy_id]})
        else:
            payload_vars.append({"code": code, "values": [_pick_total_value(var)]})

    url = f"{BASE}/data/SBLON1/CSV"
    payload = {"table": "SBLON1", "format": "CSV", "variables": payload_vars}

    # 5) Hent data
    r = requests.post(url, params={"lang": lang}, json=payload, timeout=60)
    print("[data] URL:", r.url)
    r.raise_for_status()

    # 6) Læs CSV
    df = pd.read_csv(StringIO(r.text), sep=";")

    # 7) Vis pænt
    print("\n[Å/Å %-ændring – alle rækker]")
    with pd.option_context("display.max_columns", None,
                           "display.max_rows", None,
                           "display.width", 200,
                           "display.float_format", "{:.2f}".format):
        print(df)
    return df

if __name__ == "__main__":
    _ = fetch_sblon1_yoy_pct_from_2024(lang="da")
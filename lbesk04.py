# pip install requests pandas
import requests
import pandas as pd
from io import StringIO

BASE = "https://api.statbank.dk/v1"

def fetch_lbesk04_from_2024(lang="da"):
    # 1) Hent metadata og find tidsvariablen (LBESK04 bruger 'Tid')
    meta = requests.get(
        f"{BASE}/tableinfo/LBESK04",
        params={"contentType": "JSON", "lang": lang},
        timeout=30
    ).json()

    tidsvar = next(v for v in meta["variables"] if v.get("time"))
    all_months = [val["id"] for val in tidsvar["values"]]
    months = [m for m in all_months if m >= "2024M01"]

    print(f"[tableinfo] tidsvariabel = {tidsvar['id']}, antal måneder valgt = {len(months)}")

    # 2) Hent data (CSV) via POST med alle måneder eksplicit
    url = f"{BASE}/data/LBESK04/CSV"
    payload = {
        "table": "LBESK04",
        "format": "CSV",
        "variables": [
            {"code": "SEKTOR", "values": ["1000"]},    # 'Sektorer i alt'
            {"code": tidsvar["id"], "values": months}  # alle måneder fra 2024M01 og frem
        ]
    }
    r = requests.post(url, params={"lang": lang}, json=payload, timeout=60)
    print("[data] URL:", r.url)
    if r.status_code >= 400:
        print("[data] Fejltekst:", r.text[:1000])
        r.raise_for_status()

    df = pd.read_csv(StringIO(r.text), sep=";")

    # 3) Print ALT, uden truncation
    print("\n[Data – alle rækker]")
    with pd.option_context("display.max_columns", None,
                           "display.max_rows", None,
                           "display.width", 200):
        print(df)

if __name__ == "__main__":
    fetch_lbesk04_from_2024(lang="da")
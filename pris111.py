# pip install --upgrade denstatbank pandas
from denstatbank import StatBankClient
import pandas as pd
import re
import warnings
warnings.filterwarnings("ignore")

TABLE_ID  = "PRIS111"   # Prisindeks for indenlandsk vareforsyning (2021=100)
UNIT_MODE = "pct"       # "pct" for YoY-ændring i %, "indeks" for selve indeksværdien
GROUP_PREF_REGEX = r"\b(samlet|i\s*alt|total|hele)\b"  # vælg total-agtig varegruppe

sbc = StatBankClient(lang='da')

# 1) Hent metadata
meta = sbc.tableinfo(TABLE_ID, variables_df=True).copy()
if meta is None or meta.empty:
    raise RuntimeError(f"Kunne ikke hente metadata for {TABLE_ID}.")

# Normaliser kolonner
meta["variable_u"] = meta["variable"].astype(str).str.upper()
meta["text"] = meta["text"].astype(str).fillna("")
meta["id"] = meta["id"].astype(str)

# 2) Find variabelnavne (helt deterministisk for PRIS111)
def find_var_exact_or_contains(wanted_list):
    # Returnér første præcise match, ellers første contains-match; ellers None
    for w in wanted_list:
        exact = meta.loc[meta["variable_u"] == w.upper(), "variable"]
        if not exact.empty:
            return exact.iloc[0]
    for w in wanted_list:
        contains = meta.loc[meta["variable_u"].str.contains(re.escape(w), case=False, regex=True), "variable"]
        if not contains.empty:
            return contains.iloc[0]
    return None

VN_TID   = find_var_exact_or_contains(["TID", "TIME"])
VN_ENHED = find_var_exact_or_contains(["ENHED", "UNIT"])
VN_GROUP = find_var_exact_or_contains(["VAREGR", "VAREGRUPPE", "COMMODITY", "GROUP", "VARE"])

if VN_TID is None or VN_ENHED is None or VN_GROUP is None:
    print("Tilgængelige variabler i metadata:", sorted(meta["variable"].unique()))
    missing = []
    if VN_TID is None: missing.append("TID")
    if VN_ENHED is None: missing.append("ENHED")
    if VN_GROUP is None: missing.append("VAREGR(UPPE)")
    raise RuntimeError("Kunne ikke identificere: " + ", ".join(missing))

# 3) Tidsfilter fra 2024M01
all_times = meta.loc[meta["variable"] == VN_TID, "id"].tolist()
times_from_2024 = [t for t in all_times if re.match(r"^\d{4}M\d{2}$", t) and t >= "2024M01"]
if not times_from_2024:
    raise RuntimeError("Ingen måneds-koder >= 2024M01 i tabellen.")

# 4) Vælg ENHED (pct vs indeks)
if UNIT_MODE.lower() == "pct":
    # “Ændring i forhold til samme måned året før (pct.)”
    enhed_mask = (
        (meta["variable"] == VN_ENHED) &
        (
            meta["text"].str.contains(r"ændring.*samme måned.*året før.*pct", case=False) |
            meta["text"].str.contains(r"(y\s*/\s*y|yoy|change.*same month.*previous year)", case=False)
        )
    )
    enhed_rows = meta.loc[enhed_mask, ["id", "text"]].drop_duplicates()
    if enhed_rows.empty:
        raise RuntimeError("Kunne ikke finde enhed 'Ændring i forhold til samme måned året før (pct.)'.")
    enhed_id = enhed_rows["id"].iloc[0]
else:
    # “Indeks (2021=100)”
    enhed_rows = meta.loc[
        (meta["variable"] == VN_ENHED) & (meta["text"].str.contains(r"\bindeks\b", case=False)),
        ["id", "text"]
    ].drop_duplicates()
    if enhed_rows.empty:
        # fallback: første værdi under ENHED
        enhed_rows = meta.loc[meta["variable"] == VN_ENHED, ["id", "text"]].drop_duplicates()
    enhed_id = enhed_rows["id"].iloc[0]

# 5) Vælg varegruppe = 'Samlet/Total …' (eller fallback første)
grp_rows = meta.loc[
    (meta["variable"] == VN_GROUP) & (meta["text"].str.contains(GROUP_PREF_REGEX, case=False)),
    ["id", "text"]
].drop_duplicates()
if grp_rows.empty:
    # prøv kendte total-ID'er
    grp_rows = meta.loc[
        (meta["variable"] == VN_GROUP) & (meta["id"].str.upper().isin(["TOT", "IALT", "TOTAL", "ALL"])),
        ["id", "text"]
    ].drop_duplicates()
if grp_rows.empty:
    # sidste fallback: første værdi i varegruppen
    grp_rows = meta.loc[meta["variable"] == VN_GROUP, ["id", "text"]].drop_duplicates()

grp_id = grp_rows["id"].iloc[0]

# 6) Hent data
sbc_vars = [
    sbc.variable_dict(VN_ENHED, [enhed_id]),
    sbc.variable_dict(VN_GROUP, [grp_id]),
    sbc.variable_dict(VN_TID,   times_from_2024),
]
df = sbc.data(TABLE_ID, variables=sbc_vars)
if df is None or df.empty:
    raise RuntimeError("Ingen data returneret – tjek udvalg eller variabler.")

# 7) Udskriv
def label_for(varname, id_):
    r = meta[(meta["variable"] == varname) & (meta["id"] == id_)]
    return r["text"].iloc[0] if not r.empty else id_

print(f"Tabel: {TABLE_ID}")
print("Valgte variabler:")
print(f"  {VN_ENHED}: {enhed_id} ({label_for(VN_ENHED, enhed_id)})")
print(f"  {VN_GROUP}: {grp_id} ({label_for(VN_GROUP, grp_id)})")
print("  TID: fra 2024M01 til seneste")

serie = df.iloc[:, 0]
for tid, value in serie.items():
    try:
        val = float(value)
        print(f"{tid}: {val:.2f}")
    except Exception:
        print(f"{tid}: {value}")
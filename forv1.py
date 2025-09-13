# pip install --upgrade denstatbank pandas
from denstatbank import StatBankClient
import pandas as pd
import re

TABLE_ID = "FORV1"   # <— kan skiftes til andre tabeller

sbc = StatBankClient(lang='da')

# 1) Hent metadata
meta = sbc.tableinfo(TABLE_ID, variables_df=True)

# 2) Find alle tidskoder og filtrér fra 2024M01 og frem
tid_rows = meta[meta['variable'].str.lower().isin(['tid', 'time'])]
all_times = tid_rows['id'].tolist()
times_from_2024 = [t for t in all_times if t >= '2024M01']
if not times_from_2024:
    raise RuntimeError("Ingen måneds-koder >= 2024M01 i tabellen (tjek at FORV1 har månedsfrekvens).")

# 3) Hjælpere til at vælge 'total/samlet' for hver variabel
TOTAL_ID_CANDIDATES = {'TOT', 'IALT', 'TOTAL', 'ALL', 'SAMLET'}
TOTAL_LABEL_RX = re.compile(r"\b(I\s*alt|Total|Samlet|Begge|Hele landet|Alle)\b", re.IGNORECASE)
SEASONAL_RX = re.compile(r"sæson|season", re.IGNORECASE)

def pick_one_value(rows: pd.DataFrame, varname: str) -> str:
    """Vælg én ID for variablen: helst total/samlet; hvis sæsonvalg findes, vælg sæsonkorrigeret; ellers første."""
    ids = rows['id'].tolist()
    texts = rows['text'].fillna("")

    # 1) Direkte total-ID'er
    for idc in TOTAL_ID_CANDIDATES:
        if idc in ids:
            return idc

    # 2) Label med 'I alt/Total/Samlet/Begge/Hele landet/Alle'
    hits = rows[texts.str.contains(TOTAL_LABEL_RX)]
    if not hits.empty:
        return hits['id'].iloc[0]

    # 3) Hvis variablen ligner sæsonvalg, prøv at finde sæsonkorrigeret
    if SEASONAL_RX.search(varname) or any(SEASONAL_RX.search(str(t)) for t in texts):
        # almindelige kandidater for sæsonkorrigeret
        ses_label_rx = re.compile(r"sæsonkorrigeret|seasonally adjusted", re.IGNORECASE)
        ses_hits = rows[texts.str.contains(ses_label_rx)]
        if not ses_hits.empty:
            return ses_hits['id'].iloc[0]

    # 4) Hvis kun én værdi → tag den
    if len(ids) == 1:
        return ids[0]

    # 5) Fallback: første værdi (minimer data)
    return ids[0]

# 4) Byg variabelliste (vælg én værdi pr. ikke-TID variabel)
chosen = {}  # til udskrift
variable_dicts = []

# Bevar metadataens variabel-rækkefølge
var_order = meta['variable'].str.upper().drop_duplicates().tolist()

for varname in var_order:
    if varname in ('TID', 'TIME'):
        continue
    rows = meta[meta['variable'].str.upper() == varname]
    val = pick_one_value(rows, varname)
    chosen[varname] = val
    variable_dicts.append(sbc.variable_dict(varname, [val]))

# Tilføj TID sidst
variable_dicts.append(sbc.variable_dict('TID', times_from_2024))

# 5) Hent data
df = sbc.data(TABLE_ID, variables=variable_dicts)
if df is None or df.empty:
    raise RuntimeError("Ingen data returneret – prøv at justere de valgte variabler.")

# 6) Vis hvad vi valgte, og print tid/indhold
print(f"Tabel: {TABLE_ID}")
print("Valgte variabler (ID):")
for k, v in chosen.items():
    # slå label op for pæn udskrift
    lab = meta[(meta['variable'].str.upper()==k) & (meta['id']==v)]['text'].iloc[0]
    print(f"  {k}: {v} ({lab})")
print("  TID: fra 2024M01 til seneste")

# df har typisk én kolonne (værdier) pga. vores “én-værdi pr. variabel”-valg
serie = df.iloc[:, 0]

for tid, value in serie.items():
    print(f"{tid}: {value:,}".replace(",", "."))
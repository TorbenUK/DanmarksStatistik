# pip install --upgrade denstatbank pandas
from denstatbank import StatBankClient
import pandas as pd
import re
import warnings
warnings.filterwarnings("ignore")

TABLE_ID  = "PRIS4321"
UNIT_MODE = "pct"   # vælg "pct" for år-til-år ændring i %, eller "indeks" for selve indeksværdien

sbc = StatBankClient(lang='da')

# 1) Metadata
meta = sbc.tableinfo(TABLE_ID, variables_df=True).copy()
if meta is None or meta.empty:
    raise RuntimeError(f"Kunne ikke hente metadata for {TABLE_ID}.")

meta['variable_u'] = meta['variable'].str.upper()
meta['text'] = meta['text'].fillna("")

def first_eq_or_contains(candidates):
    """Find faktisk variabelnavn i meta for første kandidat (først exact, så contains)."""
    u = meta['variable_u']
    for c in candidates:
        hits = u[u == c.upper()]
        if not hits.empty:
            return meta.loc[hits.index[0], 'variable']
    for c in candidates:
        hits = u[u.str.contains(re.escape(c), case=False)]
        if not hits.empty:
            return meta.loc[hits.index[0], 'variable']
    return None

def infer_time_variable():
    cand = meta[meta['id'].str.match(r'^\d{4}M\d{2}$', na=False)]
    if not cand.empty:
        return cand['variable'].value_counts().idxmax()
    return first_eq_or_contains(["TID","TIME"])

def infer_market_variable():
    rx = re.compile(r"\b(hjemmemarked|eksport|import|samlet|total)\b", re.I)
    cand = meta.groupby('variable').filter(lambda df: df['text'].str.contains(rx).any())
    if not cand.empty:
        counts = cand.groupby('variable')['text'].apply(lambda s: s.str.contains(rx).sum())
        return counts.sort_values(ascending=False).index[0]
    return first_eq_or_contains(["MARKED","MARKET"])

def infer_unit_variable():
    # både indeks og pct.-tekster ligger under samme variabel
    rx = re.compile(r"\bindeks\b|^100$|pct|\bpercent|\bpercentage|\bchange|\bændring", re.I)
    cand = meta.groupby('variable').filter(lambda df: df['text'].str.contains(rx).any())
    if not cand.empty:
        counts = cand.groupby('variable')['text'].apply(lambda s: s.str.contains(rx).sum())
        return counts.sort_values(ascending=False).index[0]
    return first_eq_or_contains(["ENHED","UNIT"])

def infer_industry_groups_variable():
    rx_bcde = re.compile(r"^BCDE\b", re.I)
    cand_bcde = meta[meta['text'].str.contains(rx_bcde)]
    if not cand_bcde.empty:
        return cand_bcde['variable'].value_counts().idxmax()
    return first_eq_or_contains(["BRANCHEHOVEDGRUPPER","INDUSTRY (GROUPS)","INDUSTRY","BRANCHE"])

# 2) Robust identifikation af variabler
VN_TID   = infer_time_variable()
VN_MARK  = infer_market_variable()
VN_ENHED = infer_unit_variable()
VN_BHG   = infer_industry_groups_variable()

missing = [name for name in [("TID",VN_TID),("MARKED",VN_MARK),("ENHED",VN_ENHED),("BRANCHEHOVEDGRUPPER",VN_BHG)] if name[1] is None]
if missing:
    print("Tilgængelige variabler i metadata:", sorted(meta['variable'].unique()))
    raise RuntimeError(f"Kunne ikke identificere disse variabler: {', '.join([m[0] for m in missing])}")

# 3) Tidsfilter fra 2024M01
all_times = meta.loc[meta['variable'] == VN_TID, 'id'].tolist()
times_from_2024 = [t for t in all_times if re.match(r'^\d{4}M\d{2}$', t) and t >= '2024M01']
if not times_from_2024:
    raise RuntimeError("Ingen måneds-koder >= 2024M01 i tabellen.")

# 4) Vælg ENHED efter UNIT_MODE
if UNIT_MODE.lower() == "pct":
    # “Ændring i forhold til samme måned året før (pct.)”
    enhed_row = meta[
        (meta['variable'] == VN_ENHED) &
        (meta['text'].str.contains(r"ændring.*samme måned.*året før.*pct", case=False, regex=True) |
         meta['text'].str.contains(r"(y\s*/\s*y|yoy|change.*same month.*previous year)", case=False, regex=True))
    ]
    if enhed_row.empty:
        raise RuntimeError("Kunne ikke finde enhed 'Ændring i forhold til samme måned året før (pct.)'.")
    enhed_id = enhed_row['id'].iloc[0]
else:
    # “Indeks (2021=100)” som fallback/alternativ
    enhed_row = meta[
        (meta['variable'] == VN_ENHED) &
        (meta['text'].str.contains(r"\bindeks\b", case=False, regex=True))
    ]
    if enhed_row.empty:
        # sidste desperationsforsøg: ID'er som 100/200/300
        enhed_row = meta[(meta['variable']==VN_ENHED) & (meta['id'].isin(["100","200","300"]))]
    if enhed_row.empty:
        # allersidste fallback: første værdi
        enhed_row = meta[meta['variable'] == VN_ENHED].head(1)
    enhed_id = enhed_row['id'].iloc[0]

# 5) Marked = 'Samlet' (eller 'Total' som alternativ)
mark_row = meta[
    (meta['variable'] == VN_MARK) &
    (meta['text'].str.contains(r"\bsamlet\b|\btotal\b", case=False, regex=True))
]
marked_id = mark_row['id'].iloc[0] if not mark_row.empty else meta[meta['variable']==VN_MARK]['id'].iloc[0]

# 6) Branche = 'BCDE …'
bcde_row = meta[
    (meta['variable'] == VN_BHG) &
    (meta['id'].str.fullmatch(r"BCDE", case=False) | meta['text'].str.contains(r"^BCDE\b", case=False, regex=True))
]
if bcde_row.empty:
    raise RuntimeError("Kunne ikke finde branchegruppen 'BCDE'.")
bcde_id = bcde_row['id'].iloc[0]

# 7) Hent data
variables = [
    sbc.variable_dict(VN_ENHED,  [enhed_id]),
    sbc.variable_dict(VN_MARK,   [marked_id]),
    sbc.variable_dict(VN_BHG,    [bcde_id]),
    sbc.variable_dict(VN_TID,    times_from_2024),
]
df = sbc.data(TABLE_ID, variables=variables)
if df is None or df.empty:
    raise RuntimeError("Ingen data returneret – tjek udvalg eller variabler.")

# 8) Udskriv valg + serie
def label_for(varname, id_):
    r = meta[(meta['variable']==varname) & (meta['id']==id_)]
    return r['text'].iloc[0] if not r.empty else id_

print(f"Tabel: {TABLE_ID}")
print("Valgte variabler:")
print(f"  {VN_ENHED}: {enhed_id} ({label_for(VN_ENHED, enhed_id)})")
print(f"  {VN_MARK}: {marked_id} ({label_for(VN_MARK, marked_id)})")
print(f"  {VN_BHG}: {bcde_id} ({label_for(VN_BHG, bcde_id)})")
print("  TID: fra 2024M01 til seneste")

serie = df.iloc[:, 0]
for tid, value in serie.items():
    # pct. bør udskrives som tal med komma, ikke tusindtalsseparatorer
    try:
        val = float(value)
        print(f"{tid}: {val:.2f}")
    except Exception:
        print(f"{tid}: {value}")

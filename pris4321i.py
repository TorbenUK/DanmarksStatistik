# pip install --upgrade denstatbank pandas
from denstatbank import StatBankClient
import pandas as pd
import re
import warnings
warnings.filterwarnings("ignore")

TABLE_ID  = "PRIS4321"
UNIT_MODE = "pct"  # år-til-år ændring i %
TIME_FROM = "2024M01" # første måned der hentes (inkl.)

# (valgfrit) branchehovedgruppe-id; default er 'BCDE' (Hele industrien mv.)
# Sæt til None for automatisk at tage 'BCDE'
BRANCHE_ID_OVERRIDE = None

sbc = StatBankClient(lang='da')

# 1) Metadata
meta = sbc.tableinfo(TABLE_ID, variables_df=True).copy()
if meta is None or meta.empty:
    raise RuntimeError(f"Kunne ikke hente metadata for {TABLE_ID}.")

meta['variable_u'] = meta['variable'].str.upper()
meta['text'] = meta['text'].fillna("")

def first_eq_or_contains(candidates):
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
    rx = re.compile(r"\b(import|hjemmemarked|eksport|samlet|total)\b", re.I)
    cand = meta.groupby('variable').filter(lambda df: df['text'].str.contains(rx).any())
    if not cand.empty:
        counts = cand.groupby('variable')['text'].apply(lambda s: s.str.contains(rx).sum())
        return counts.sort_values(ascending=False).index[0]
    return first_eq_or_contains(["MARKED","MARKET"])

def infer_unit_variable():
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

# 2) Identificér variabler
VN_TID   = infer_time_variable()
VN_MARK  = infer_market_variable()
VN_ENHED = infer_unit_variable()
VN_BHG   = infer_industry_groups_variable()

missing = [name for name in [("TID",VN_TID),("MARKED",VN_MARK),("ENHED",VN_ENHED),("BRANCHEHOVEDGRUPPER",VN_BHG)] if name[1] is None]
if missing:
    print("Tilgængelige variabler i metadata:", sorted(meta['variable'].unique()))
    raise RuntimeError(f"Kunne ikke identificere disse variabler: {', '.join([m[0] for m in missing])}")

# 3) Tidsfilter fra TIME_FROM
all_times = meta.loc[meta['variable'] == VN_TID, 'id'].tolist()
times_from = [t for t in all_times if re.match(r'^\d{4}M\d{2}$', t) and t >= TIME_FROM]
if not times_from:
    raise RuntimeError(f"Ingen måneds-koder >= {TIME_FROM} i tabellen.")

# 4) ENHED efter UNIT_MODE  (lidt mere robust matching)
if UNIT_MODE.lower() == "pct":
    enhed_row = meta[
        (meta['variable'] == VN_ENHED) &
        (
            # dansk: "Ændring i forhold til samme måned året før (pct.)"
            meta['text'].str.contains(r"ændring.*samme måned.*året før.*pct", case=False, regex=True)
            |
            # engelsk fallback: "Change compared to the same month of the previous year (%)"
            meta['text'].str.contains(r"change.*same month.*previous year.*(%|pct)", case=False, regex=True)
            |
            # generisk fallback: noget med pct og (året før|previous year)
            (meta['text'].str.contains(r"(pct|%)", case=False, regex=True) &
             meta['text'].str.contains(r"(året før|previous year)", case=False, regex=True))
        )
    ]
    if enhed_row.empty:
        # sidste fallback: tag en ENHED der indeholder pct/% i teksten
        enhed_row = meta[(meta['variable'] == VN_ENHED) &
                         meta['text'].str.contains(r"(pct|%)", case=False, regex=True)]
    if enhed_row.empty:
        raise RuntimeError("Kunne ikke finde enhed for 'Å/Å (pct)'.")
    enhed_id = enhed_row['id'].iloc[0]
else:
    enhed_row = meta[
        (meta['variable'] == VN_ENHED) &
        (meta['text'].str.contains(r"\bindeks\b", case=False, regex=True))
    ]
    if enhed_row.empty:
        fallback = meta[(meta['variable']==VN_ENHED) & (meta['id'].isin(["100","200","300"]))]
        enhed_row = fallback if not fallback.empty else meta[meta['variable']==VN_ENHED].head(1)
    enhed_id = enhed_row['id'].iloc[0]

# 5) Marked = 'Import' (kun importprisindeks)
mark_row = meta[
    (meta['variable'] == VN_MARK) &
    (meta['text'].str.contains(r"\bimport\b", case=False, regex=True))
]
if mark_row.empty:
    raise RuntimeError("Kunne ikke finde 'Import' under MARKED.")
marked_id = mark_row['id'].iloc[0]

# 6) Branche = 'BCDE …' eller override
if BRANCHE_ID_OVERRIDE:
    bcde_row = meta[
        (meta['variable'] == VN_BHG) &
        (meta['id'].str.fullmatch(re.escape(BRANCHE_ID_OVERRIDE), case=False))
    ]
    if bcde_row.empty:
        raise RuntimeError(f"Kunne ikke finde branche-id '{BRANCHE_ID_OVERRIDE}'.")
else:
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
    sbc.variable_dict(VN_MARK,   [marked_id]),   # <- IMPORT!
    sbc.variable_dict(VN_BHG,    [bcde_id]),
    sbc.variable_dict(VN_TID,    times_from),
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
print(f"  {VN_TID}: fra {TIME_FROM} til seneste")

# df har normalt én kolonne med værdier; index = tid
serie = df.iloc[:, 0]
for tid, value in serie.items():
    try:
        val = float(value)
        if UNIT_MODE.lower() == "pct":
            print(f"{tid}: {val:.2f}")
        else:
            # Indeks typisk med én decimal
            print(f"{tid}: {val:.1f}")
    except Exception:
        print(f"{tid}: {value}")

# (valgfrit) få det som DataFrame med kolonner
out = df.reset_index()
# print(out.head())